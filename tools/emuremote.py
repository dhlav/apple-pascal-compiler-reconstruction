"""Run Apple's own compiler over the remote console and bring back text.

    python tools/emuremote.py PASCALSY
    python tools/emuremote.py REMTEST --timeout 240

The acceptance tier's other entry point, `emucompile.ps1`, types into
AppleWin's window with SendKeys and captures a screenshot. That works, and
it is still there, but it has three costs this does not:

  * **It cannot tell when the compile finished.** `-Boot` and `-Compile`
    are fixed sleeps, so every run is padded to the worst case and a run
    that takes longer than the guess is simply lost.
  * **It needs the foreground.** `emukeys.ps1` refuses to type unless
    AppleWin is the foreground window -- correctly, since SendKeys goes to
    whatever holds focus -- so a run dies if anything steals focus, and no
    two runs can overlap.
  * **The result is a picture.** Error numbers, line numbers and the
    procedure list have to be read off a PNG by eye.

Here the system's console is redirected to a TCP socket (findings 210,
211), so the compiler's output arrives as bytes: this waits for the real
completion text instead of sleeping, fails on the compiler's own error
prompt instead of leaving it on screen, and writes a transcript.

**How the channel gets armed.** `REDIRIO.CODE` is installed on SYSHD as
`SYSTEM.STARTUP`, which Apple Pascal runs automatically at the end of
boot, so the redirect happens with no keystrokes at all -- nothing is ever
typed into the window and the emulator never needs focus. It is removed
again afterwards in a `finally`, and removed defensively on the way in too,
so a crashed run cannot leave the volume booting into a redirect nobody is
listening to. That failure mode is worth being careful about: a SYSHD that
redirects its console at boot with no client attached looks exactly like a
machine that will not boot.

**Bootstrapping.** REDIRIO has to be a codefile on the volume before any of
this works, and the only way to get one there is to compile it there, which
needs the SendKeys path. `mkharddisks.py` puts REDIRIO.TEXT on the volume;
compile it once with `emucompile.ps1 -Name REDIRIO` after every rebuild.
This script says so by name if the codefile is missing.
"""
import argparse
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

# What the compiler says when it is done, and what it says when it is not.
# "Smallest available space" is the last line of a clean compile; the error
# prompt is the compiler waiting for a keystroke, which over this channel
# would otherwise hang until the timeout.
DONE = b"Smallest available space"
ERROR = re.compile(rb"Line (\d+), error (\d+)")
ESC = b"\x1b"


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
        elif b in (25, 29, 28, 11, 12):
            pass                      # cursor/clear control, not content
        else:
            out.append(f"<{b:02X}>")
    return "".join(out)


def arm() -> None:
    """Install REDIRIO.CODE as SYSTEM.STARTUP so boot arms the channel."""
    catalog = cp2("catalog", str(HD1))
    if "REDIRIO.CODE" not in catalog:
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
    """Close AppleWin the way emucompile.ps1 does -- politely, then not.

    AppleWin holds HD1.hdv open and does not flush it until it exits, so a
    hard kill first would lose the codefile the compile just wrote.
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
        """Pump until one of `patterns` appears in newly arrived bytes."""
        while time.monotonic() < self.deadline:
            self._pump()
            fresh = bytes(self.rx[self.mark:])
            for p in patterns:
                if p in fresh:
                    self.mark = len(self.rx)
                    return p
        return None

    def send(self, text: str) -> None:
        while self.sock is None and time.monotonic() < self.deadline:
            self._pump()
        if self.sock is None:
            raise SystemExit("never connected to the remote console")
        time.sleep(0.4)
        self.sock.sendall(text.encode("ascii"))


def compile_one(name: str, timeout: float, echo: bool) -> int:
    deadline = time.monotonic() + timeout
    con = Console(deadline, echo)

    if con.wait(b"Command:") is None:
        raise SystemExit(
            "no Command prompt on the socket. Either the redirect never ran "
            "(is REDIRIO.CODE current?) or the boot did not finish in time.")

    con.send("C")
    if con.wait(b"Compile what") is None:
        raise SystemExit("the compiler never asked for a source file")
    con.send(f"SYSHD:{name}.TEXT\r")

    if con.wait(b"To what codefile") is None:
        raise SystemExit("the compiler never asked for an output file")
    # [*] is required on this single merged volume: a new file otherwise
    # claims all free space and the compiler's own scratch can starve it.
    con.send(f"SYSHD:{name}.CODE[*]\r")

    if con.wait(b"Listing file") is None:
        raise SystemExit("the compiler never asked about a listing file")
    con.send("\r")

    hit = con.wait(DONE, b", error ")
    if hit is None:
        raise SystemExit(f"the compile did not finish within {timeout:.0f}s")

    if hit != DONE:
        # The compiler is sitting on <sp>(continue), <esc>(terminate).
        # Terminate: continuing would report the same run's later errors
        # against a codefile that will not be written anyway.
        con.send(ESC.decode("latin-1"))
        con.wait(b"Command:")
        text = visible(bytes(con.rx))
        m = ERROR.search(bytes(con.rx))
        where = f"line {m.group(1).decode()}, error {m.group(2).decode()}" \
            if m else "an error"
        write_transcript(name, text)
        print(f"\nCOMPILE FAILED: {where}")
        return 1

    con.wait(b"Command:")
    text = visible(bytes(con.rx))
    write_transcript(name, text)
    m = re.search(r"^\s*(\d+) lines", text, re.M)
    print(f"\ncompiled clean{f', {m.group(1)} lines' if m else ''}")
    return 0


def write_transcript(name: str, text: str) -> None:
    out = ROOT / "build" / "acceptance" / f"{name}-console.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="ascii", errors="replace", newline="\n")
    print(f"\ntranscript: {out.relative_to(ROOT)}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("name", help="source on SYSHD, without .TEXT")
    ap.add_argument("--timeout", type=float, default=420.0,
                    help="seconds for boot plus compile (default 420)")
    ap.add_argument("--quiet", action="store_true",
                    help="do not echo the console while it runs")
    args = ap.parse_args()

    if not HD1.exists():
        raise SystemExit(f"{HD1.relative_to(ROOT)} has not been built "
                         "(python tools/mkharddisks.py)")
    if not CP2.exists():
        raise SystemExit(f"{CP2} not found -- CiderPress II is required")

    shutdown()          # nothing else may hold HD1.hdv open
    arm()
    try:
        launch()
        return compile_one(args.name, args.timeout, not args.quiet)
    finally:
        shutdown()
        disarm()
        print("closed; HD1.hdv (SYSHD) flushed, SYSTEM.STARTUP removed")


if __name__ == "__main__":
    sys.exit(main())
