"""Compile reconstructed procedure bodies and diff them against the binary.

The declarations are done and verified (finding 57b). This is the tool for
the part that is left: writing the 147 procedure bodies, one at a time, and
finding out immediately whether each one is right.

The method is the only one that means anything here. A procedure is written
as Pascal, dropped into the verified declaration skeleton at its own lexical
level, compiled, and the resulting p-code is compared **instruction for
instruction against Apple's**. There is no partial credit: either the
compiler emits what Apple's compiler emitted or the source is not what Apple
wrote.

That comparison is sharper than it looks, because so much rides on the
declarations. `FSP^.AELTYPE` and `FSP^.INXTYPE` are the same expression to a
reader and different bytes to a compiler -- `SIND 3` against `SIND 2` -- so
a field list in the wrong order fails here even though it compiles cleanly
and reads correctly. The same goes for every enumeration's member order,
every record's size, and every global's offset.

What is compared is the disassembled instruction text from `enter_ic` to the
return, using this repo's own decoder on both sides, so a difference is
reported as an opcode and not as a byte offset. The exit sweep is included:
UCSD puts the case jump tables past the return and they are part of the
procedure.

Two things this deliberately does *not* require to match, because neither is
recoverable from the binary and neither changes a byte: identifiers, and the
procedure's *number*. A leaf's number never appears in its own code. A
procedure that calls another does emit `CGP n`, and for those the harness
maps our numbering onto Apple's before comparing.

Usage:
    python tools/procbuild.py                 # every reconstructed procedure
    python tools/procbuild.py PAOFCHAR        # just one
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.names import PROC_NAMES
from a2pascal.pcode import disassemble, sweep_exit
from a2pascal.srcfmt import WIDTH, over_width
import xcompile

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "pascal"
SKEL = ROOT / "analysis" / "reconstruction"
DISKS = {"1.3": "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk",
         "1.1": "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk"}
END = ("RNP", "RBP", "XIT")


def apple_segment(ver: str, segname: str):
    d = PascalDisk.from_file(ROOT / "evidence" / "disks" / DISKS[ver])
    e = d.find("SYSTEM.COMPILER")
    return CodeFile(d.read_blocks(e.first_block, e.blocks)).segment(segname)


def listing(seg, p) -> list[str]:
    """Every instruction of a procedure, up to and including its return."""
    ins = (disassemble(seg.data, p.enter_ic, p.exit_ic, p.jtab)[0]
           + sweep_exit(seg.data, p.exit_ic, p.jtab - 8, p.jtab)[0])
    out = []
    for i in ins:
        out.append(i.text)
        if i.mnemonic in END:
            break
    return out


def strip_targets(text: str) -> str:
    """Drop absolute jump addresses, which are placement, not content.

    `FJP $092A` and `FJP $0417` are the same instruction in two different
    codefiles. What has to match is the *structure*, and the structure is
    already pinned by the instruction sequence around it -- a jump to the
    wrong place lands the following instructions in the wrong order and the
    listings diverge there instead.
    """
    return re.sub(r"\$[0-9A-F]{4}( \(jtab-\d+\))?", "$----", text)


def sources(ver: str) -> list[tuple[str, str, str]]:
    """(segment, name, source text) for every reconstructed procedure.

    One file per segment, named for it, holding the procedures in the order
    they are declared. A procedure begins at a line starting `PROCEDURE` or
    `FUNCTION` in column 1 and runs to the line before the next one.
    """
    out = []
    for path in sorted(SRC.glob(f"{ver}/*.text")):
        segname = path.stem.upper()
        text = path.read_text(encoding="ascii", errors="replace")
        starts = [m.start() for m in
                  re.finditer(r"(?m)^(?:PROCEDURE|FUNCTION)\s+(\w+)", text)]
        for i, at in enumerate(starts):
            end = starts[i + 1] if i + 1 < len(starts) else len(text)
            body = text[at:end].rstrip() + "\n"
            name = re.match(r"^\w+\s+(\w+)", body).group(1).upper()
            out.append((segname, name, body))
    return out


def spliced(ver: str, procs) -> str:
    """The skeleton with these procedure bodies declared at lex 1."""
    text = (SKEL / f"skeleton-{ver}.text").read_text(encoding="ascii",
                                                     errors="replace")
    # The skeleton ends with the segment procedure's body and then the host
    # program's: "BEGIN END;" followed by "BEGIN END." (finding 60). Bodies
    # belong inside PASCALCOMPILER, so splice before the *first* of those two
    # -- past it they are declared in the host program, where none of the
    # compiler's own types are in scope.
    at = text.rindex("\nBEGIN\nEND;")
    return text[:at] + "\n" + "\n".join(b for _s, _n, b in procs) + text[at:]


def write_for_emulator(ver: str, procs) -> Path:
    """Put the spliced source on the work disk for Apple's own compiler.

    The fast tier cannot settle every procedure. It short-circuits boolean
    operators where Apple's compiler evaluates both sides and emits `LAND`,
    and there is no feature switch for it (finding 58), so any body with an
    `AND` or `OR` in it diverges there no matter how the source is written.
    Apple's compiler is the authority; this is how the source reaches it.
    """
    from a2pascal.diskwrite import PascalWriter
    from a2pascal.srcfmt import expand_tabs
    from a2pascal.textfile import encode_text

    src = expand_tabs(spliced(ver, procs))
    src = src[:-1] if src.endswith("\n") else src
    name = f"BODY{ver.replace('.', '')}.TEXT"
    dsk = ROOT / "build" / "disks" / "WORK.dsk"
    w = PascalWriter.from_file(dsk)
    for stale in (name, name.replace(".TEXT", ".CODE")):
        try:
            w.remove_file(stale)
        except KeyError:
            pass
    w.add_file(name, encode_text(src), "textfile")
    w.save(dsk)
    print(f"wrote WORK:{name} ({len(src.splitlines())} lines, "
          f"{len(procs)} procedures) to {dsk.relative_to(ROOT)}")
    return dsk


def report(ver: str, procs, mine, who: str) -> int:
    """Diff each compiled procedure against Apple's. Returns the failures."""
    bad = 0
    order = [n for _s, n, _b in procs]
    for segname, name, _body in procs:
        num = next((k[1] for k, v in PROC_NAMES[ver].items()
                    if k[0] == segname and v == name), None)
        if num is None:
            print(f"[{ver}] {name}: no such procedure in {segname}")
            bad += 1
            continue
        apple = apple_segment(ver, segname)
        a = next((x for x in apple.procedures if x.number == num), None)
        # Ours are numbered from 2 in declaration order, the program itself
        # being procedure 1.
        b = next((x for x in mine.procedures
                  if x.number == 2 + order.index(name)), None)
        if a is None or b is None:
            print(f"[{ver}] {name}: not found "
                  f"(apple={a is not None}, ours={b is not None})")
            bad += 1
            continue

        frame = ((a.param_size, a.data_size, a.lex_level)
                 == (b.param_size, b.data_size, b.lex_level))
        la = [strip_targets(x) for x in listing(apple, a)]
        lb = [strip_targets(x) for x in listing(mine, b)]
        if frame and la == lb:
            print(f"[{ver}] {segname}.{num} {name}: {len(la)} instructions, "
                  f"IDENTICAL  ({who})")
            continue
        bad += 1
        print(f"[{ver}] {segname}.{num} {name}: DIFFERS  ({who})")
        if not frame:
            print(f"    frame: Apple param {a.param_size} / data "
                  f"{a.data_size} / lex {a.lex_level}, ours param "
                  f"{b.param_size} / data {b.data_size} / lex {b.lex_level}")
        for i in range(max(len(la), len(lb))):
            x = la[i] if i < len(la) else "-"
            y = lb[i] if i < len(lb) else "-"
            print(f"    {'  ' if x == y else '->'} {x:<24} {y}")
    return bad


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    emu = "--emu" in sys.argv
    check = "--emu-check" in sys.argv
    want = {a.upper() for a in args}
    if not emu and not check and not xcompile.available():
        print("SKIPPED: ucsdpsys_compile is not built "
              "(thirdparty/ucsd-psystem-xc/build.sh)")
        return 0

    total = bad = 0
    for ver in ("1.3", "1.1"):
        procs = [p for p in sources(ver) if not want or p[1] in want]
        if not procs:
            continue
        total += len(procs)
        if emu:
            write_for_emulator(ver, procs)
            total -= len(procs)
            continue
        if check:
            # Apple's own compiler produced this, in the emulator, from the
            # source `--emu` put on the disk. It is the authority: where the
            # fast tier and this disagree, this is right.
            dsk = PascalDisk.from_file(ROOT / "build" / "disks" / "WORK.dsk")
            e = dsk.find(f"BODY{ver.replace('.', '')}.CODE")
            mine = CodeFile(dsk.read_blocks(e.first_block,
                                            e.blocks)).segment("PASCALCO")
            bad += report(ver, procs, mine, "Apple's compiler")
            continue

        source = spliced(ver, procs)
        long = over_width(source.split("\n"))
        if long:
            print(f"[{ver}] {len(long)} lines over {WIDTH} columns: {long[:3]}")
            bad += 1
        try:
            cf = CodeFile(xcompile.compile_text(source))
        except xcompile.CompileError as exc:
            print(f"[{ver}] did not compile:" + chr(10) + str(exc))
            return 1
        bad += report(ver, procs, cf.segment("PASCALCO"), "fast tier")

    print(chr(10) + f"{total} procedures, {total - bad} matching Apple's p-code")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
