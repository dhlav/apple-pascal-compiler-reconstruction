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

Identifiers are deliberately not required to match: they are not
recoverable from the binary and they do not change a byte. The procedure
*number* is a different matter and IS required to match. UCSD assigns it
when it parses the header, so declaration order is the numbering, and a
`CGP n` in one body is only right if every procedure ahead of the callee is
declared too. Each segment file therefore holds the whole segment, with
`(*STUB*)` bodies standing in for what is not written yet, and the order is
checked as a result in its own right (finding 61).

Usage:
    python tools/procbuild.py                 # the fast tier, all segments
    python tools/procbuild.py PAOFCHAR        # diff just one body
    python tools/procbuild.py --emu           # put the source on WORK.dsk
    python tools/procbuild.py --emu-check     # diff what Apple's compiler made
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


HEADER = re.compile(r"(?m)^[ \t]*(?:PROCEDURE|FUNCTION)\s+(\w+)")


def sources(ver: str) -> list[tuple[str, str, list]]:
    """(segment, source text, declared procedures) for each segment file.

    One file per segment, named for it, holding **the whole segment** -- not
    just the procedures that have been reconstructed. That is not
    bookkeeping: UCSD assigns a procedure its number when it parses the
    header, so declaration order *is* the numbering, and a `CGP n` in one
    body is only right if every procedure declared before the callee is
    also present. Procedures still to be written are declared with an empty
    body and marked `(*STUB*)`; they hold their number and nothing else.

    A name is counted at its **first** header. A `FORWARD` or `EXTERNAL`
    declaration is where the number is assigned, and the body that follows
    later re-states the header without allocating anything new.

    Numbers run from 2 in that order, the segment procedure itself being 1.
    """
    out = []
    for path in sorted(SRC.glob(f"{ver}/*.text")):
        text = path.read_text(encoding="ascii", errors="replace")
        lines = text.split("\n")
        order, stub = [], {}
        for m in HEADER.finditer(text):
            name = m.group(1).upper()
            if name not in stub:
                order.append(name)
            # The marker sits on the header line, or on the next one when
            # the header is long enough to have been wrapped. It goes on the
            # header of the *body*, which for a forward-declared procedure
            # is not the header that fixed its number -- so take the marker
            # from whichever of a name's headers carries it.
            i = text.count("\n", 0, m.start())
            here = "\n".join(lines[i:i + 2])
            stub[name] = stub.get(name, False) or "(*STUB*)" in here
        procs = [(n, stub[n]) for n in order]
        out.append((path.stem.upper(), text, procs))
    return out


def spliced(ver: str, segs) -> str:
    """The skeleton with these segment sources declared at lex 1."""
    text = (SKEL / f"skeleton-{ver}.text").read_text(encoding="ascii",
                                                     errors="replace")
    # The skeleton ends with the segment procedure's body and then the host
    # program's: "BEGIN END;" followed by "BEGIN END." (finding 60). Bodies
    # belong inside PASCALCOMPILER, so splice before the *first* of those two
    # -- past it they are declared in the host program, where none of the
    # compiler's own types are in scope.
    at = text.rindex("\nBEGIN\nEND;")
    return text[:at] + "\n" + "\n".join(s for _n, s, _p in segs) + text[at:]


def write_for_emulator(ver: str, segs) -> Path:
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

    src = expand_tabs(spliced(ver, segs))
    src = src[:-1] if src.endswith("\n") else src
    nproc = sum(len(p) for _n, _t, p in segs)
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
          f"{nproc} procedures) to {dsk.relative_to(ROOT)}")
    return dsk


def report(ver: str, segname: str, procs, mine, who: str) -> int:
    """Diff each compiled procedure against Apple's. Returns the failures."""
    bad = 0
    apple = apple_segment(ver, segname)
    for i, (name, stub) in enumerate(procs):
        num = next((k[1] for k, v in PROC_NAMES[ver].items()
                    if k[0] == segname and v == name), None)
        if num is None:
            print(f"[{ver}] {name}: no such procedure in {segname}")
            bad += 1
            continue
        # Declaration order is the numbering, so ours must land on Apple's
        # number. This is the check on the *order*, and it is separate from
        # whether any body is right: a segment full of stubs still has to
        # number them the way Apple did, or every CGP will be wrong later.
        if 2 + i != num:
            print(f"[{ver}] {segname}.{num} {name}: declared at number "
                  f"{2 + i}, Apple has it at {num}")
            bad += 1
            continue
        a = next((x for x in apple.procedures if x.number == num), None)
        if stub:
            # A stub has no body to compare, but it does have a *place*, and
            # the lexical level says whether it is nested where Apple nests
            # it. That is worth checking on its own: COMMENTER and FINDFORW
            # are lex 2 in the binary, which is what says they belong to
            # INSYMBOL and BLOCK rather than to PASCALCOMPILER.
            b = next((x for x in mine.procedures if x.number == num), None)
            if a and b and not a.is_native and a.lex_level != b.lex_level:
                print(f"[{ver}] {segname}.{num} {name}: lex {b.lex_level}, "
                      f"Apple has lex {a.lex_level}")
                bad += 1
            continue
        if a is not None and a.is_native:
            # 6502, not p-code. IDSEARCH and TREESEARCH are `EXTERNAL` and
            # are held to Apple's bytes by the assembler acceptance tier
            # instead; all this source can do is reserve their numbers.
            print(f"[{ver}] {segname}.{num} {name}: native, checked by the "
                  f"assembler tier")
            continue
        b = next((x for x in mine.procedures if x.number == num), None)
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
        for k in range(max(len(la), len(lb))):
            x = la[k] if k < len(la) else "-"
            y = lb[k] if k < len(lb) else "-"
            print(f"    {'  ' if x == y else '->'} {x:<24} {y}")
    return bad


def main() -> int:
    # Disassembly text is ASCII, but a mismatch can print a byte the decoder
    # renders outside cp1252 and Windows' default console encoding then
    # raises instead of showing the diff that was the point of the run.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    emu = "--emu" in sys.argv
    check = "--emu-check" in sys.argv
    want = {a.upper() for a in args}
    if not emu and not check and not xcompile.available():
        print("SKIPPED: ucsdpsys_compile is not built "
              "(thirdparty/ucsd-psystem-xc/build.sh)")
        return 0

    done = stubs = bad = 0
    for ver in ("1.3", "1.1"):
        segs = sources(ver)
        if not segs:
            continue
        if emu:
            write_for_emulator(ver, segs)
            continue

        if check:
            # Apple's own compiler produced this, in the emulator, from the
            # source `--emu` put on the disk. It is the authority: where the
            # fast tier and this disagree, this is right.
            dsk = PascalDisk.from_file(ROOT / "build" / "disks" / "WORK.dsk")
            e = dsk.find(f"BODY{ver.replace('.', '')}.CODE")
            cf = CodeFile(dsk.read_blocks(e.first_block, e.blocks))
            who = "Apple's compiler"
        else:
            source = spliced(ver, segs)
            long = over_width(source.split("\n"))
            if long:
                print(f"[{ver}] {len(long)} lines over {WIDTH} columns: "
                      f"{long[:3]}")
                bad += 1
            try:
                cf = CodeFile(xcompile.compile_text(source))
            except xcompile.CompileError as exc:
                print(f"[{ver}] did not compile:" + chr(10) + str(exc))
                return 1
            who = "fast tier"

        for segname, _text, procs in segs:
            # Filtering by name is for reading the output, not for the
            # compile: every procedure stays declared either way, because
            # dropping one would renumber all the rest.
            shown = [(n, s or (bool(want) and n not in want))
                     for n, s in procs]
            done += sum(1 for _n, s in shown if not s)
            stubs += sum(1 for _n, s in shown if s)
            bad += report(ver, segname, shown, cf.segment(segname), who)

    if emu:
        return 0
    print(chr(10) + f"{done + stubs} procedures declared, {done - bad} of "
          f"{done} reconstructed bodies matching Apple's p-code, "
          f"{stubs} still stubs")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
