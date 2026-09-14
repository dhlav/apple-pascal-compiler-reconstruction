"""Drive Apple's own compiler, assembler and linker over the remote console.

    python tools/emuremote.py compile  PASCALSY
    python tools/emuremote.py assemble SEARCH
    python tools/emuremote.py link --host FORMATTR --lib FMTNATIV --out FORMATTR
    python tools/emuremote.py observe A --seconds 40      # what does it prompt?
    python tools/emuremote.py librarian --input COMPLINK --out LIBTEST \
        --slots 1-15 --notice "COPYRIGHT ..."            # finding 267
    python tools/emuremote.py run MAKEFMT                # X(ecute, finding 275

The `emu*.ps1` scripts type into AppleWin's window with SendKeys and capture
a screenshot. They still work and are still the fallback, but they carry
three costs this does not:

  * **They cannot tell when the work finished.** `-Boot`, `-Compile`,
    `-Assemble`, `-Link` are fixed sleeps, so every run is padded to the
    worst case and a run that goes long is simply lost.
  * **They need the foreground.** `emukeys.ps1` refuses to type unless
    AppleWin is the foreground window -- correctly, since SendKeys goes to
    whatever holds focus -- so a run dies if anything steals focus.
  * **The result is a picture**, so error numbers and line numbers have to
    be read off a PNG by eye.

`emulink.ps1` carries a fourth, written into its own module note: its
prompts are answered on a timer it cannot confirm, which scrambled a
filename into `NK.CODE` more than once, and its note ends "that race is not
fully solved". It is solved here by not racing -- every answer waits for
the prompt it answers. The Linker needs that more than the others because
**its prompt sequence depends on the data**: a host file with no unresolved
`EXTERNAL` skips the library list entirely and goes straight to "All
segments linked", so a fixed script of answers lands on whatever comes
next. Here the driver waits to see which prompt actually arrived.

**How the channel gets armed.** `REDIRIO.CODE` is installed on SYSHD as
`SYSTEM.STARTUP`, which Apple Pascal runs at the end of boot, so the console
is on the socket before anything needs typing. It is removed in a `finally`
and defensively on the way in. That matters: **a SYSHD left armed with
nobody listening is indistinguishable from a disk that will not boot** --
blank screen, dead keyboard, no error.

**Bootstrapping.** The only way to get a codefile onto SYSHD is to compile
it there, so REDIRIO itself goes through the SendKeys path once after every
volume rebuild:

    powershell -File tools/emucompile.ps1 -Name REDIRIO

A transcript is always written, including when a run fails or times out --
that is what makes `observe` rarely necessary, since a missed prompt leaves
the real text on disk to read.

**When the transcript comes back EMPTY, check the port reservation first.**
An empty transcript with `never saw 'Command:'` is not a Pascal problem and
not a REDIRIO problem: screenshot the emulator and REDIRIO will be sitting
there having printed `console -> REMIN:/REMOUT: now`, exactly as it should.
What has happened is that AppleWin could not bind 1977 and did not say so,
so no listener ever appears and this client polls `SYN_SENT` until the
deadline. Port 1977 is inside Windows' TCP dynamic range, which WinNAT and
Hyper-V allocate blocks out of, and a machine that has been rebooted or has
had a container feature enabled can lose the port at any time:

    netsh int ipv4 show excludedportrange protocol=tcp   # 1977 must be here
    netsh int ipv4 show dynamicport tcp                  # starts at 1025

The fix is an administered reservation for 1977 (finding 236). Two things
that will mislead while diagnosing this: a **closed** loopback port on
Windows times out rather than refusing, so a connect timeout says nothing
either way; and stray background runs of this script pile up, each racing
the others over `HD1.hdv` and `SYSTEM.STARTUP` in its own `finally`, so kill
them before drawing any conclusion.
"""
import argparse
import codecs
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CP2 = Path(r"C:\CiderPress2\cp2.exe")
HD1 = ROOT / "build" / "disks" / "HD1.hdv"
PORT = 1977
STARTUP = "SYSTEM.STARTUP"
VOL = "SYSHD:"

PROMPT = b"Command:"
ESC = "\x1b"

# `[*]` on every codefile created here. A single Pascal volume gives a new
# file all the free space there is and only shrinks it back on a clean
# close, so an output file and a system tool's own scratch file on the same
# volume race for it -- the manual's fix for a one-drive system (ch. 3/5),
# and the `emu*.ps1` scripts all do the same.
SIZED = "[*]"

# What each tool says when it has finished, and the shapes of its
# complaints. Anchors are kept short so a wording difference between
# releases does not silently turn into a timeout.
COMPILE_DONE = b"Smallest available space"
COMPILE_ERR = re.compile(rb"Line (\d+), error (\d+)")
# Every one of Apple's three tools stops on this same prompt when it
# cannot continue, and waits for a keystroke -- which over a socket
# means hanging until the timeout unless it is answered.
HALT = b"(continue)"
# The halt prompt shares its line with the tool's message -- the
# compiler writes "Line 6, error 104: <sp>(continue)..." -- so the
# message is found by splitting on the prompt's own start, not on
# HALT, which would leave "<sp>" behind as the last "line".
HALT_LINE = "<sp>(continue)"
LINK_DONE = b"segments linked"


def cp2(*args: str, allow_fail: bool = False, cwd: Path | None = None) -> str:
    # `cp2 extract` has no output-directory option; it writes into the
    # working directory, so extraction has to be run from one.
    r = subprocess.run([str(CP2), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace",
                       cwd=None if cwd is None else str(cwd))
    if r.returncode and not allow_fail:
        raise SystemExit(f"cp2 {' '.join(args)} failed:\n{r.stdout}{r.stderr}")
    return r.stdout


def visible(data: bytes) -> str:
    """Readable transcript: the guest sends screen-control bytes as data."""
    out = []
    for b in data:
        if b == 13:
            out.append("\n")
        elif b == 10:
            pass                      # CR already broke the line
        elif 32 <= b < 127:
            out.append(chr(b))
        elif b in (7, 11, 12, 25, 28, 29):
            pass                      # bell, cursor and clear control
        else:
            out.append(f"<{b:02X}>")
    return "".join(out)


def arm() -> None:
    """Install REDIRIO.CODE as SYSTEM.STARTUP so boot arms the channel."""
    if "REDIRIO.CODE" not in cp2("catalog", str(HD1)):
        raise SystemExit(
            "REDIRIO.CODE is not on SYSHD -- the remote console cannot be\n"
            "armed without it. Compile it once with the SendKeys path:\n"
            "    powershell -File tools/emucompile.ps1 -Name REDIRIO")
    disarm()
    tmp = Path(tempfile.mkdtemp(prefix="emuremote-"))
    try:
        cp2("extract", "--raw", "--strip-paths", str(HD1), "REDIRIO.CODE",
            cwd=tmp)
        (tmp / "REDIRIO.CODE").rename(tmp / STARTUP)
        cp2("add", "--raw", "--no-strip-ext", "--strip-paths", str(HD1),
            str(tmp / STARTUP))
        cp2("set-attr", str(HD1), "type=PCD", STARTUP)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if STARTUP not in cp2("catalog", str(HD1)):
        raise SystemExit(f"{STARTUP} is not on the volume after add")


def disarm() -> None:
    cp2("delete", str(HD1), STARTUP, allow_fail=True)


def launch() -> None:
    subprocess.Popen([sys.executable, str(ROOT / "tools" / "runemu.py"),
                      "--ssc"], cwd=str(ROOT),
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def shutdown() -> None:
    """Close AppleWin politely, then not.

    AppleWin holds HD1.hdv open and does not flush it until it exits, so a
    hard kill first would lose whatever the run just wrote.
    """
    subprocess.run(["taskkill", "/IM", "AppleWin.exe"],
                   capture_output=True, text=True)
    time.sleep(2.5)
    subprocess.run(["taskkill", "/F", "/IM", "AppleWin.exe"],
                   capture_output=True, text=True)
    time.sleep(0.8)


class Console:
    """The socket, with the poll-connect the SSC requires.

    AppleWin creates the listening socket only when the guest first touches
    an SSC register, so there is nothing to connect to until Pascal's own
    boot-time slot probe runs. Connecting once and giving up always loses
    that race (finding 210).
    """

    def __init__(self, deadline: float, echo: bool):
        self.sock = None
        self.rx = bytearray()
        self.mark = 0
        self.deadline = deadline
        self.echo = echo

    def _pump(self) -> None:
        if self.sock is None:
            s = socket.socket()
            s.settimeout(0.2)
            try:
                s.connect(("127.0.0.1", PORT))
            except OSError:
                s.close()
                time.sleep(0.2)
                return
            self.sock = s
        try:
            data = self.sock.recv(4096)
        except socket.timeout:
            return
        except OSError:
            self.sock = None
            return
        if data:
            self.rx += data
            if self.echo:
                sys.stdout.write(visible(data))
                sys.stdout.flush()

    def wait(self, *patterns: bytes) -> bytes | None:
        """Pump until one of `patterns` appears in newly arrived bytes.

        Only bytes since the previous match count, so a prompt still
        sitting in the log cannot satisfy two different steps.
        """
        while time.monotonic() < self.deadline:
            self._pump()
            fresh = bytes(self.rx[self.mark:])
            for p in patterns:
                if p in fresh:
                    self.mark = len(self.rx)
                    return p
        return None

    def idle(self, seconds: float) -> None:
        end = time.monotonic() + seconds
        while time.monotonic() < min(end, self.deadline):
            self._pump()

    def send(self, text: str) -> None:
        while self.sock is None and time.monotonic() < self.deadline:
            self._pump()
        if self.sock is None:
            raise Fault("never connected to the remote console")
        time.sleep(0.4)
        self.sock.sendall(text.encode("ascii"))

    def expect(self, *patterns: bytes) -> bytes:
        hit = self.wait(*patterns)
        if hit is None:
            names = " / ".join(p.decode("ascii") for p in patterns)
            raise Fault(f"never saw {names!r} -- read the transcript for "
                        "what actually arrived")
        return hit

    def text(self) -> str:
        return visible(bytes(self.rx))


class Fault(Exception):
    """A run that did not get where it was going. The transcript is kept."""


def message_before(text: str, marker: str) -> str:
    """The last non-empty line before `marker` -- the tool's complaint.

    Apple's compiler puts `Line 6, error 104:` immediately before its halt
    prompt; the assembler puts a named message there instead (`invalid
    structure`). Either way the line above the prompt is what went wrong.
    """
    head = text.split(marker)[0]
    for line in reversed(head.splitlines()):
        if line.strip():
            return line.strip().rstrip(":")
    return "no message"


def lines(text: str) -> str:
    """', N lines' if the tool reported a count, else nothing.

    The compiler puts it on a line of its own and the assembler puts it
    after `Assembly complete:`, so this is deliberately not anchored -- and
    it takes the *last* match, since the count comes at the end and the
    prompts before it are not guaranteed to be free of digits.
    """
    found = re.findall(r"(\d+)\s+lines", text)
    return f", {found[-1]} lines" if found else ""


def write_transcript(label: str, text: str) -> Path:
    out = ROOT / "build" / "acceptance" / f"{label}-console.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="ascii", errors="replace", newline="\n")
    return out


def do_compile(con: Console, args) -> int:
    name = args.name
    con.expect(PROMPT)
    con.send("C")
    con.expect(b"Compile what")
    con.send(f"{VOL}{name}.TEXT\r")
    con.expect(b"To what codefile")
    con.send(f"{VOL}{name}.CODE{SIZED}\r")
    con.expect(b"Listing file")
    con.send("\r")

    if con.expect(COMPILE_DONE, HALT) != COMPILE_DONE:
        # Sitting on <sp>(continue), <esc>(terminate). Terminate:
        # continuing only reports later errors against a codefile that
        # will not be written anyway.
        con.send(ESC)
        con.wait(PROMPT)
        m = COMPILE_ERR.search(bytes(con.rx))
        where = (f"line {m.group(1).decode()}, error {m.group(2).decode()}"
                 if m else message_before(con.text(), HALT_LINE))
        print(f"\nCOMPILE FAILED: {where}")
        return 1

    con.wait(PROMPT)
    print(f"\ncompiled clean{lines(con.text())}")
    return 0


def do_assemble(con: Console, args) -> int:
    name = args.name
    con.expect(PROMPT)
    con.send("A")
    con.expect(b"Assemble what")
    con.send(f"{VOL}{name}.TEXT\r")
    con.expect(b"To what codefile")
    con.send(f"{VOL}{name}.CODE{SIZED}\r")
    con.expect(b"listing")
    con.send("\r")

    # The assembler reports its own error count rather than stopping on the
    # first one, so completion and success are two separate questions. The
    # count is the only thing that says whether it worked, so a regex that
    # cannot match must be a failure, not a silent pass -- the first version
    # of this looked for lowercase "errors" against Apple's "0   Errors
    # flagged on this Assembly", never matched, and would have called every
    # broken assembly clean.
    # It halts on the same prompt the compiler does when it cannot go on --
    # waiting only for the completion line means a broken source burns the
    # whole timeout and reports the wrong thing.
    if con.expect(b"Assembly complete", HALT) == HALT:
        con.send(ESC)
        con.wait(PROMPT)
        print("\nASSEMBLY FAILED: "
              f"{message_before(con.text(), HALT_LINE)}")
        return 1
    con.wait(PROMPT)
    text = con.text()
    m = re.search(r"(\d+)\s+Errors?\s+flagged", text, re.I)
    if m is None:
        print("\nASSEMBLY FAILED: no error count in the output -- read the "
              "transcript; the wording this looks for may have changed")
        return 1
    if m.group(1) != "0":
        print(f"\nASSEMBLY FAILED: {m.group(1)} errors flagged")
        return 1
    print(f"\nassembled clean{lines(text)}")
    return 0


def do_link(con: Console, args) -> int:
    con.expect(PROMPT)
    con.send("L")
    con.expect(b"Link what host codefile")
    con.send(f"{VOL}{args.host}.CODE\r")

    # Data-dependent from here, which is the whole reason this waits rather
    # than scripting a fixed sequence: the first library prompt and the
    # later ones are worded differently ("Using what library file?" then
    # "Another library file (<ret> for none)?"), and a host with no
    # unresolved EXTERNAL of its own skips the library list entirely and
    # goes straight to "All segments linked". A fixed script of answers
    # lands on whatever came instead -- which is how emulink.ps1 turned an
    # output filename into "NK.CODE".
    libs = list(args.lib)
    while True:
        hit = con.expect(b"Using what library file", b"Another library file",
                         b"Map file", b"Output file", HALT)
        if hit == HALT:
            con.send(ESC)
            con.wait(PROMPT)
            print(f"\nLINK FAILED: {message_before(con.text(), HALT_LINE)}")
            return 1
        if hit in (b"Using what library file", b"Another library file"):
            con.send(f"{VOL}{libs.pop(0)}.CODE\r" if libs else "\r")
        elif hit == b"Map file":
            con.send("\r")
        else:                                   # Output file
            con.send(f"{VOL}{args.out}.CODE{SIZED}\r")
            break

    # The Linker does its real work *after* the output filename, so this is
    # where an unresolved reference actually surfaces -- `Func FORMATDI
    # undefined`, then the same halt prompt. Waiting only for the Command
    # prompt here hangs until the timeout and blames the wrong thing.
    if con.expect(PROMPT, HALT) == HALT:
        con.send(ESC)
        con.wait(PROMPT)
        print(f"\nLINK FAILED: {message_before(con.text(), HALT_LINE)}")
        return 1
    if libs:
        print(f"\nLINK FAILED: never asked for {', '.join(libs)}")
        return 1
    return 0


def verify_linked(name: str) -> int:
    """A link that leaves a HOSTSEG behind did not do its job.

    Reaching the end of the prompts is not proof: a failed link still
    writes an output file, sized to whatever was free (finding 91's table),
    so the file existing says nothing. What does say something is the
    segment dictionary -- a compile alone leaves any segment with an
    unresolved EXTERNAL marked HOSTSEG, and only the Linker turns it into
    the LINKED kind Apple shipped. This is the check that can fail.
    """
    sys.path.insert(0, str(ROOT / "tools"))
    from a2pascal.codefile import CodeFile

    tmp = Path(tempfile.mkdtemp(prefix="emuremote-"))
    try:
        out = cp2("extract", "--raw", "--strip-paths", str(HD1),
                  f"{name}.CODE", cwd=tmp, allow_fail=True)
        blob = tmp / f"{name}.CODE"
        if not blob.exists():
            print(f"\nLINK FAILED: {VOL}{name}.CODE was never written\n{out}")
            return 1
        cf = CodeFile(blob.read_bytes())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    unresolved = [s.name for s in cf.segments
                  if s.length and s.segkind == "HOSTSEG"]
    if unresolved:
        print(f"\nLINK FAILED: still HOSTSEG after linking: "
              f"{', '.join(unresolved)}")
        return 1
    kinds = ", ".join(f"{s.name}={s.segkind}" for s in cf.segments if s.length)
    print(f"\nlinked clean -> {VOL}{name}.CODE  [{kinds}]")
    return 0


def do_run(con: Console, args) -> int:
    """X(ecute a program that asks nothing, and wait for the Command prompt.

    For the build steps Apple ran as programs rather than tools -- the
    ones that assemble a data file out of codefile blocks. A run-time
    error stops at a prompt that is not Command:, so that is a failure.
    """
    con.expect(PROMPT)
    con.send("X")
    con.expect(b"Execute what file")
    con.send(f"{VOL}{args.name}\r")
    hit = con.expect(PROMPT, b"Type <space>", b"No file")
    if hit != PROMPT:
        print(f"\nRUN FAILED: {message_before(con.text(), hit.decode())}")
        return 1
    print(f"\nran {args.name}")
    return 0


def do_observe(con: Console, args) -> int:
    """Send a key and log whatever comes back. For converting the next tool."""
    con.expect(PROMPT)
    # Escapes decoded so a whole prompt sequence can be sent as
    # type-ahead: over the socket there is no keystroke race, so the
    # system consumes each answer as its prompt appears and one run
    # captures every prompt text at once.
    con.send(codecs.decode(args.keys, "unicode_escape"))
    con.idle(args.seconds)
    print("\nobserved; nothing was answered")
    return 0


LIB_COPY = re.compile(rb"Copy slot\D{0,12}?(\d+)\s*\?")


def slots_in(spec: str) -> set[int]:
    """`1-15` or `0,3-5` -> the slot numbers it names."""
    out: set[int] = set()
    for part in spec.split(","):
        lo, _, hi = part.partition("-")
        out.update(range(int(lo), int(hi or lo) + 1))
    return out


def slot_pairs(spec: str) -> list[tuple[int, int]] | None:
    """`1:1,7:2` -> [(1, 1), (7, 2)], in the order given; None if no `:`."""
    if ":" not in spec:
        return None
    return [(int(a), int(b)) for a, b in
            (part.split(":") for part in spec.split(","))]


def dictionary(name: str) -> bytes:
    """Block 0 of a codefile on SYSHD."""
    with tempfile.TemporaryDirectory() as tmp:
        cp2("extract", "--raw", "--strip-paths", str(HD1), codename(name),
            cwd=Path(tmp))
        return (Path(tmp) / codename(name)).read_bytes()[:512]


def nonzero_slots(name: str) -> list[int]:
    """The slots LIBRARY.CODE's `?` mode will ask about, read off SYSHD.

    It asks once for every slot whose length is non-zero, in slot order,
    and prints nothing after the last question. Knowing the list up front
    is what tells the driver when the questions are over, and lets it check
    that each question it sees is the one it expected.
    """
    b = dictionary(name)
    return [s for s in range(16) if b[2 + 4 * s] | b[3 + 4 * s] << 8]


def codename(name: str) -> str:
    """`ASSMBLER` -> `ASSMBLER.CODE`; `SYSTEM.ASSMBLER` is already a name."""
    return name if "." in name else f"{name}.CODE"


def do_librarian(con: Console, args) -> int:
    """Copy chosen slots of a codefile into a new one with Apple's Librarian.

    Finding 267: block 0 of every shipped system program was written by
    LIBRARY.CODE, not the compiler -- slot 0 left blank, segments in the
    order they were copied, and the copyright notice as a Pascal string.
    This reproduces that release step with Apple's own tool.
    """
    if len(args.input) != len(args.slots):
        raise SystemExit("give one --slots for every --input, in order")
    plan = [(name, slots_in(spec) if slot_pairs(spec) is None
             else slot_pairs(spec), dictionary(name))
            for name, spec in zip(args.input, args.slots)]
    con.expect(PROMPT)
    con.send("X")
    con.expect(b"Execute what file")
    con.send(f"{VOL}LIBRARY\r")
    con.expect(b"Output file ->")
    con.send(f"{VOL}{args.out}.CODE{SIZED}\r")
    report = []
    for n, (name, wanted, block0) in enumerate(plan):
        if n:
            # N(ew file ends this input's MAINLOOP; GETINPUT asks again.
            con.send("N")
        con.expect(b"Input File ->")
        con.send(f"{VOL}{codename(name)}\r")
        con.expect(b"N(ew file")
        if isinstance(wanted, list):
            # `7 ` names a source slot; CONFIRM then asks where it goes
            # (READ of an integer, and one more READ eats the terminator).
            # A copy ends by redisplaying the output table, so the source
            # segment's name arriving is the sign the next pair may go.
            for src, dst in wanted:
                segname = block0[0x40 + 8 * src:0x48 + 8 * src].rstrip()
                con.send(f"{src} ")
                con.expect(b"Slot to copy into?")
                con.send(f"{dst} ")
                con.expect(segname)
            report.append(f"{name} " + ",".join(f"{s}->{d}"
                                                for s, d in wanted))
            continue
        asked = [s for s in range(16)
                 if block0[2 + 4 * s] | block0[3 + 4 * s] << 8]
        con.send("?")
        for expected in asked:
            con.expect(b"Copy slot")
            # `mark` is the end of everything received at the match, not
            # the end of the match, so the number may already be behind it.
            start = con.rx.rfind(b"Copy slot")
            while True:
                m = LIB_COPY.search(bytes(con.rx[start:]))
                if m:
                    break
                if time.monotonic() > con.deadline:
                    raise Fault("never saw the slot number after 'Copy slot'")
                con._pump()
            if int(m.group(1)) != expected:
                raise Fault(f"Librarian asked about slot "
                            f"{m.group(1).decode()}, expected {expected}")
            con.send("Y" if expected in wanted else "N")
        report.append(f"{name} {sorted(set(asked) & wanted)}")
    # Type-ahead: the Q waits in the keyboard buffer until the last copy
    # finishes and GETCOMMAND reads it.
    con.send("Q")
    if con.expect(b"Notice?", b"Type <space> to continue") != b"Notice?":
        print(f"\nLIBRARIAN FAILED: {message_before(con.text(), 'Type')}")
        return 1
    con.send(f"{args.notice}\r")
    if con.expect(PROMPT, b"Code write error") != PROMPT:
        print("\nLIBRARIAN FAILED: Code write error")
        return 1
    print(f"\nlibrarian: into {args.out}, copied " + "; ".join(report))
    return 0


ACTIONS = {"compile": do_compile, "assemble": do_assemble,
           "link": do_link, "observe": do_observe,
           "librarian": do_librarian, "run": do_run}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--timeout", type=float, default=480.0,
                    help="seconds for boot plus the run (default 480)")
    ap.add_argument("--quiet", action="store_true",
                    help="do not echo the console while it runs")
    sub = ap.add_subparsers(dest="action", required=True)

    for verb in ("compile", "assemble"):
        p = sub.add_parser(verb)
        p.add_argument("name", help=f"source on SYSHD, without .TEXT")

    p = sub.add_parser("link")
    p.add_argument("--host", required=True)
    p.add_argument("--lib", action="append", default=[],
                   help="repeatable; may be omitted entirely")
    p.add_argument("--out", required=True)

    p = sub.add_parser("librarian")
    p.add_argument("--input", action="append", required=True,
                   help="codefile on SYSHD; repeat for a second input")
    p.add_argument("--out", required=True)
    p.add_argument("--slots", action="append", required=True,
                   help="e.g. 1-15, answered with ?; or 1:1,7:2 to copy "
                        "slot 7 into slot 2, in that order; one per --input")
    p.add_argument("--notice", default="",
                   help="the answer to Notice? -- the codefile comment")

    p = sub.add_parser("run")
    p.add_argument("name", help="codefile on SYSHD, without .CODE")

    p = sub.add_parser("observe")
    p.add_argument("keys", help="sent verbatim once the Command prompt shows")
    p.add_argument("--seconds", type=float, default=30.0)

    args = ap.parse_args()
    label = {"link": lambda: f"{args.out}-link",
             "librarian": lambda: f"{args.out}-librarian",
             "observe": lambda: "observe",
             "run": lambda: f"{args.name}-run"}.get(
                 args.action, lambda: f"{args.name}-{args.action}")()

    if not HD1.exists():
        raise SystemExit(f"{HD1.relative_to(ROOT)} has not been built "
                         "(python tools/mkharddisks.py)")
    if not CP2.exists():
        raise SystemExit(f"{CP2} not found -- CiderPress II is required")

    shutdown()          # nothing else may hold HD1.hdv open
    arm()
    con = Console(time.monotonic() + args.timeout, not args.quiet)
    rc = 1
    try:
        launch()
        rc = ACTIONS[args.action](con, args)
    except Fault as exc:
        print(f"\nFAILED: {exc}")
    finally:
        out = write_transcript(label, con.text())
        print(f"transcript: {out.relative_to(ROOT)}")
        shutdown()
        disarm()
        print("closed; HD1.hdv (SYSHD) flushed, SYSTEM.STARTUP removed")

    # Only now, with AppleWin gone and HD1.hdv flushed, can the result be
    # read back off the volume.
    if args.action == "link" and rc == 0:
        rc = verify_linked(args.out)
    return rc


if __name__ == "__main__":
    sys.exit(main())
