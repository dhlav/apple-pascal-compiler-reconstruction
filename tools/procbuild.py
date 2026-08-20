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


# The compiler's phases, as nested SEGMENT PROCEDUREs of PASCALCOMPILER, in
# Apple's declaration order -- which is what fixes their segment numbers,
# exactly as declaration order fixes procedure numbers (finding 61).
#
# Two things are read straight off the binary and neither is a choice. The
# segment NUMBER is the last byte of each segment's code, and the LEX LEVEL
# of its procedure 1 says how deep it is declared: 1 for a phase declared
# directly in PASCALCOMPILER, 2 for one inside a phase, 3 for one inside
# that. ROUTINE and STATEMENT are lex 2, so they are declared inside
# BODYPART; CASESTAT, FORSTATE, BODY1 and BODY3 are lex 3, so each is inside
# one of BODYPART's own procedures. Which one is fixed by who calls it:
# CASESTAT and FORSTATE are `CXP 12,1` and `CXP 13,1` from inside STATEMENT,
# BODY1 and BODY3 are `CXP 14,1` and `CXP 15,1` from BODYPART.24:BODY. A
# segment procedure is only in scope where it is declared, so that settles
# it -- and the segment numbers then follow from the declaration order,
# STATEMENT and its two coming before BODY and its two.
#
# Under `$U-` segment procedures number from 1, so PASCALCOMPILER is 1 and
# the phases would follow at 2. They have to start at 7, because SYSTEM.PASCAL
# ignores segments 0 and 2..6 when it loads a codefile -- those belong to the
# operating system. `(*$NS 7*)` moves the counter, and is what Apple Pascal
# 1.1 added in place of declaring five dummy segment procedures to fill the
# gap. See finding 68.
# `$NS` is Apple Pascal 1.1 and later; `ucsdpsys_compile` targets II.0/II.1
# and rejects it. So the fast tier compiles without it and its phases come
# out five low, which SEGOFFSET accounts for. Apple's own compiler is the
# one that has to get this right, and it is the authority anyway.
NS_FIRST = 7
USE_NS = False


def segoffset() -> int:
    return 0 if USE_NS else NS_FIRST - 2
#
# Signatures are held to Apple's PARAM SIZE and to the call sites in
# segment 1. Where a phase is called from nowhere in segment 1 its
# parameters are placeholders of the right width.
# (segment, name, header, children)
SEGDECLS = [
    (7, "COMPINIT", "SEGMENT PROCEDURE COMPINIT;", []),
    (8, "DECLARAT",
     "SEGMENT PROCEDURE DECLARATIONPART(FSYS: SETOFSYS);", []),
    (9, "BODYPART",
     "SEGMENT PROCEDURE BODYPART(FSYS: SETOFSYS; FPROCP: CTP);", [
         (10, "ROUTINE",
          "SEGMENT PROCEDURE ROUTINE(FSYS: SETOFSYS;\n"
          "                            FWASLPAR: BOOLEAN; LKEY: INTEGER);",
          []),
         (11, "STATEMEN", "SEGMENT PROCEDURE STATEMENT(FSYS: SETOFSYS);", [
             (12, "CASESTAT", "SEGMENT PROCEDURE CASESTATEMENT;", []),
             (13, "FORSTATE", "SEGMENT PROCEDURE FORSTATEMENT;", []),
         ]),
         (14, "BODY1", "SEGMENT PROCEDURE BODY1;", []),
         (15, "BODY3", "SEGMENT PROCEDURE BODY3;", []),
     ]),
    (16, "WRITELIN", "SEGMENT PROCEDURE WRITELINKERINFO;", []),
    (17, "UNITPART", "SEGMENT PROCEDURE UNITPART(FSYS: SETOFSYS);", []),
    (18, "COMPOPTI",
     "SEGMENT FUNCTION COMPOPTIONS(STOPPER: CHAR): BOOLEAN;", []),
    (19, "NUMSTRIN",
     "SEGMENT PROCEDURE NUMSTRING(FISNUM: BOOLEAN; VAR FVP: CSP);", []),
    (20, "FINISHUP", "SEGMENT PROCEDURE FINISHUP;", []),
]


def check_segments(ver: str, cf) -> int:
    """Every phase at Apple's segment number, offset, and its lex level.

    The lex level is the sharp part: it says how deep a phase is declared,
    and nothing else recovers that. ROUTINE and STATEMENT come out lex 2
    only if they are declared inside BODYPART; CASESTAT and FORSTATE lex 3
    only if they are inside STATEMENT, and BODY1 and BODY3 lex 3 only if
    they are inside BODYPART's own BODY.
    """
    apple = {}
    d = PascalDisk.from_file(ROOT / "evidence" / "disks" / DISKS[ver])
    e = d.find("SYSTEM.COMPILER")
    for s in CodeFile(d.read_blocks(e.first_block, e.blocks)).segments:
        p = next((x for x in s.procedures if x.number == 1), None)
        apple[s.name.upper()] = (s.data[s.length - 2],
                                 p.lex_level if p else None)
    bad = 0
    for num, name in flat_segdecls():
        want = apple.get(name.upper())
        got = next((s for s in cf.segments if s.name.upper() == name.upper()),
                   None)
        if want is None or got is None:
            print(f"[{ver}] segment {name}: "
                  f"apple={want is not None} ours={got is not None}")
            bad += 1
            continue
        p = next((x for x in got.procedures if x.number == 1), None)
        mine = (got.data[got.length - 2], p.lex_level if p else None)
        if (mine[0] + segoffset(), mine[1]) != want:
            print(f"[{ver}] segment {name}: ours {mine[0]}+{segoffset()}/"
                  f"lex {mine[1]}, Apple {want[0]}/lex {want[1]}")
            bad += 1
        if want[0] != num:
            print(f"[{ver}] segment {name}: table says {num}, "
                  f"Apple has {want[0]}")
            bad += 1
    return bad


def flat_segdecls(decls=None):
    """(segment number, name) for every phase, in declaration order."""
    out = []
    for num, name, _hdr, kids in (SEGDECLS if decls is None else decls):
        out.append((num, name))
        out += flat_segdecls(kids)
    return out


def phase_body(ver: str, name: str) -> str | None:
    """A phase segment's own source, or None while it is still empty.

    Phase bodies live in `src/pascal/<ver>/phases/` and not beside
    `PASCALCO.text`, because `sources()` globs that directory and would
    splice anything there a second time at the outer level.

    The file is the whole segment procedure from its own declarations down
    to its `END;` -- procedure 1 of the segment is the segment procedure
    itself, so unlike the files `sources()` reads there is nothing above it
    to declare.
    """
    path = SRC / ver / "phases" / (name + ".text")
    if not path.exists():
        return None
    return path.read_text(encoding="ascii", errors="replace").rstrip("\n")


def render_segdecls(ver: str, decls=None, depth: int = 0) -> str:
    """The phase declarations as Pascal, bodies from src/pascal/<ver>/."""
    pad = "  " * depth
    out = []
    for num, name, hdr, kids in (SEGDECLS if decls is None else decls):
        if USE_NS and num == NS_FIRST and depth == 0:
            out += [pad + "(*$NS " + str(NS_FIRST) + "*)", ""]
        out.append(pad + hdr + "  { segment " + str(num) + " }")
        out.append("")
        if hdr.endswith("FORWARD;"):
            continue
        body = phase_body(ver, name)
        # A phase that declares phases of its own says where each one goes,
        # with `{SEGMENT <name>}`. The position is not cosmetic: BODYPART's
        # nested ROUTINE and STATEMENT call back into BODYPART with
        # `CXP 9,n`, so every procedure they call has to be declared --
        # forward is enough -- before the SEGMENT PROCEDURE that calls it;
        # BODY has to come after STATEMENT because it calls it; and BODY1
        # and BODY3 are declared *inside* BODY, which is the only place
        # they are in scope and the only way their procedure 1 comes out at
        # lex 3. Whatever the body does not place goes first, which is
        # where PASCALCO's own children belong.
        rendered = [(nm, render_segdecls(ver, [kid], depth + 1))
                    for kid in kids for nm in (kid[1],)]
        if body is not None:
            for nm, text in rendered:
                if "{SEGMENT " + nm + "}" in body:
                    body = body.replace("{SEGMENT " + nm + "}", text)
                    rendered = [(n, t) for n, t in rendered if n != nm]
        kidtext = "\n".join(t for _n, t in rendered)
        if kidtext:
            out.append(kidtext)
        if body is not None:
            # The file supplies the statement part too, so there is no
            # empty one to add after it.
            out += [body, ""]
        else:
            out += [pad + "BEGIN", pad + "END;", ""]
    return "\n".join(out)


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


OSFWD = re.compile(r"(?m)^((?:PROCEDURE|FUNCTION) .*?;) FORWARD;   \{ CXP 0,"
                   r"(\d+) \}\n")


def defang_forwards(text: str) -> str:
    """Replace the OS forwards with one stub, for the fast tier only.

    An unresolved FORWARD is how a `(*$U-*)` program names the operating
    system, and Apple's compiler accepts it; `ucsdpsys_compile` reports
    every one of them as "declared forward, but has not been defined" and
    gives up. Only `OSPROC43` is ever called, so the fast tier gets that one
    with an empty body and none of the numbering.

    The cost is confined and known: the fast tier's `CXP 0,n` for it comes
    out at whatever number the stub lands on rather than 43. That is two
    instructions in COMPOPTIONS, on a tier that already differs from Apple's
    compiler at every `AND` (finding 58), and Apple's compiler is the one
    this is checked against.
    """
    keep = [m.group(1) for m in OSFWD.finditer(text) if m.group(2) == "43"]
    return OSFWD.sub("", text).replace(
        "\n{ The operating system enters segment 1",
        "\n" + "\n".join(f"{d} BEGIN END;" for d in keep) +
        "\n\n{ The operating system enters segment 1", 1)


RESIDENT_OPT = re.compile(r"\(\*\$R (?![-+])[^*]*\*\)")


def defang_resident(text: str) -> str:
    """Drop Apple's resident-segment option, for the fast tier only.

    `(*$R+*)` and `(*$R-*)` are UCSD's range-check switch and both
    compilers take them. `(*$R name,name*)` and `(*$R 8,9*)` are Apple's
    own overload of the same letter -- the list of segments to hold in
    memory across a block -- and `ucsdpsys_compile` has never heard of it.

    The cost is exactly the LOADSEGMENT/UNLOADSEGMENT bracket around three
    procedure bodies, on a tier that already differs from Apple's at every
    `AND`. Apple's own compiler is the one that has to get this right.
    """
    return RESIDENT_OPT.sub("", text)


def spliced(ver: str, segs, fast: bool = False) -> str:
    """The skeleton with these segment sources declared at lex 1.

    `fast` is for `ucsdpsys_compile`, which cannot take the OS forwards.
    """
    text = (SKEL / f"skeleton-{ver}.text").read_text(encoding="ascii",
                                                     errors="replace")
    if fast:
        text = defang_forwards(text)
    # The skeleton ends with the segment procedure's body and then the host
    # program's: "BEGIN END;" followed by "BEGIN END." (finding 60). Bodies
    # belong inside PASCALCOMPILER, so splice before the *first* of those two
    # -- past it they are declared in the host program, where none of the
    # compiler's own types are in scope.
    empty = "\nBEGIN\nEND;"
    at = text.rindex(empty)
    body = "\n".join(s for _n, s, _p in segs)
    # The phases are nested SEGMENT PROCEDUREs and have to be declared before
    # anything calls them: COMMENTER's `CXP 18,1` and INSYMBOL's `CXP 19,1`
    # will not compile otherwise. PASCALCO.text marks the spot.
    body = body.replace("{SEGMENTS}", render_segdecls(ver))
    if fast:
        body = defang_resident(body)
    # ...and PASCALCOMPILER's own statement part, if the file supplies one,
    # goes where the skeleton's empty `BEGIN END;` is. That is procedure 1
    # of segment 1, and it is the only body a segment file cannot hold in
    # the ordinary way: `sources()` numbers a file's procedures from 2,
    # because procedure 1 of a segment is the segment procedure itself.
    outer = empty
    if "{PASCALCOMPILER}" in body:
        body, outer = body.split("{PASCALCOMPILER}", 1)
        outer = "\n" + outer.strip("\n")
    return text[:at] + "\n" + body + outer + text[at + len(empty):]


def uncomment(text: str) -> str:
    """The same program with its commentary removed.

    A Disk II volume is 280 blocks and cannot grow, and the reconstruction
    passed the point where the source and Apple's codefile both fit on one.
    Comments are the part of a source file that provably cannot change a
    byte of the output, so they are what goes. The repository keeps the
    commented text; this is what the emulator is handed.

    Two comments are not commentary and stay: `{$...}` and `(*$...*)` are
    compiler options, and `(*$R STATEMENT*)` in particular is the whole
    reason BODYPART.24 emits a LOADSEGMENT. Each comment that goes is
    replaced by one space, because `50(*LDA*),0` must not become `50,0`
    with the digits run together somewhere else.
    """
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c == "'":
            j = i + 1
            while j < n:
                if text[j] == "'":
                    if text[j + 1:j + 2] == "'":
                        j += 2
                        continue
                    break
                j += 1
            out.append(text[i:j + 1])
            i = j + 1
        elif c == "{":
            j = text.index("}", i)
            out.append(text[i:j + 1] if text[i + 1:i + 2] == "$" else " ")
            i = j + 1
        elif text.startswith("(*", i):
            j = text.index("*)", i + 2)
            out.append(text[i:j + 2] if text[i + 2:i + 3] == "$" else " ")
            i = j + 2
        else:
            out.append(c)
            i += 1
    lines = [x.rstrip() for x in "".join(out).split("\n")]
    return "\n".join(x for k, x in enumerate(lines)
                     if x or (k and lines[k - 1]))


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

    global USE_NS
    USE_NS = True
    src = expand_tabs(uncomment(spliced(ver, segs)))
    src = src[:-1] if src.endswith("\n") else src
    nproc = sum(len(p) for _n, _t, p in segs)
    name = f"BODY{ver.replace('.', '')}.TEXT"
    dsk = ROOT / "build" / "disks" / "WORK.dsk"
    w = PascalWriter.from_file(dsk)
    # A Disk II volume is 280 blocks and that is the whole budget: the
    # source, the codefile Apple's compiler writes beside it, and whatever
    # else mkworkdisk.py put there. The skeletons are 82 blocks of it and
    # this run has no use for them -- the body source already carries the
    # declarations -- so they go, and the codefile gets the room. A failed
    # compile here reports error 402 at the last line, which is what a full
    # output file looks like from inside the compiler. mkworkdisk.py puts
    # them back, and build_all.py runs it.
    for stale in (name, name.replace(".TEXT", ".CODE"),
                  "SKEL13.TEXT", "SKEL11.TEXT", "SEARCH.TEXT"):
        try:
            w.remove_file(stale)
        except KeyError:
            pass
    w.add_file(name, encode_text(src), "textfile")
    w.save(dsk)
    used = sum(e.blocks for e in PascalDisk.from_file(dsk).directory())
    free = PascalDisk.from_file(dsk).volume().total_blocks - 6 - used
    print(f"wrote WORK:{name} ({len(src.splitlines())} lines, "
          f"{nproc} procedures) to {dsk.relative_to(ROOT)}; "
          f"{free} blocks left for the codefile")
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

        bad += diff_proc(f"[{ver}] {segname}.{num} {name}",
                         apple, a, mine, b, who)
    return bad


def diff_proc(label: str, apple, a, mine, b, who: str) -> int:
    """One procedure against Apple's. Prints, and returns 1 if it differs."""
    frame = ((a.param_size, a.data_size, a.lex_level)
             == (b.param_size, b.data_size, b.lex_level))
    la = [strip_targets(x) for x in listing(apple, a)]
    lb = [strip_targets(x) for x in listing(mine, b)]
    if frame and la == lb:
        print(f"{label}: {len(la)} instructions, IDENTICAL  ({who})")
        return 0
    print(f"{label}: DIFFERS  ({who})")
    if not frame:
        print(f"    frame: Apple param {a.param_size} / data "
              f"{a.data_size} / lex {a.lex_level}, ours param "
              f"{b.param_size} / data {b.data_size} / lex {b.lex_level}")
    for k in range(max(len(la), len(lb))):
        x = la[k] if k < len(la) else "-"
        y = lb[k] if k < len(lb) else "-"
        print(f"    {'  ' if x == y else '->'} {x:<24} {y}")
    return 1


def report_phases(ver: str, cf, who: str) -> tuple[int, int, int]:
    """Diff every procedure of each written phase, its own body included.

    `sources()` numbers a file's procedures from 2, because procedure 1 of
    a segment is the segment procedure itself and is not declared in the
    file it reads. A phase file is the whole segment procedure, so its
    nested procedures are numbered from 2 by the compiler exactly as any
    other segment's are, and all of them are checked here.

    A missing procedure is a failure and not a stub: the file is either
    written or it is not, and if it is written it has to declare every
    procedure Apple's segment has, in Apple's order (finding 61).
    """
    done = stubs = bad = 0
    for _num, name in flat_segdecls():
        if phase_body(ver, name) is None:
            stubs += 1
            continue
        apple = apple_segment(ver, name)
        mine = cf.segment(name)
        ours = {x.number: x for x in mine.procedures}
        for a in sorted(apple.procedures, key=lambda x: x.number):
            done += 1
            b = ours.get(a.number)
            if b is None:
                print(f"[{ver}] {name}.{a.number}: Apple has it, we do not")
                bad += 1
                continue
            bad += diff_proc(f"[{ver}] {name}.{a.number} {name}",
                             apple, a, mine, b, who)
        for num in sorted(set(ours) - {x.number for x in apple.procedures}):
            print(f"[{ver}] {name}.{num}: we have it, Apple does not")
            bad += 1
    return done, stubs, bad


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
            # What is on the disk was built with `$NS`, because `--emu`
            # turns it on. The check has to assume the same.
            global USE_NS
            USE_NS = True
            # Apple's own compiler produced this, in the emulator, from the
            # source `--emu` put on the disk. It is the authority: where the
            # fast tier and this disagree, this is right.
            # The codefile is on WORK2 once the source stopped leaving room
            # for it on WORK (finding 82). Take whichever volume has it, and
            # prefer the newer if somehow both do.
            name = f"BODY{ver.replace('.', '')}.CODE"
            cf = None
            for vol in ("WORK2.dsk", "WORK.dsk"):
                path = ROOT / "build" / "disks" / vol
                if not path.exists():
                    continue
                dsk = PascalDisk.from_file(path)
                try:
                    e = dsk.find(name)
                except KeyError:
                    continue
                cf = CodeFile(dsk.read_blocks(e.first_block, e.blocks))
                break
            if cf is None:
                raise SystemExit(f"{name} is on neither WORK: nor WORK2: -- "
                                 f"the emulator run did not produce it")
            who = "Apple's compiler"
        else:
            source = spliced(ver, segs, fast=True)
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

        bad += check_segments(ver, cf)
        for segname, _text, procs in segs:
            # Filtering by name is for reading the output, not for the
            # compile: every procedure stays declared either way, because
            # dropping one would renumber all the rest.
            shown = [(n, s or (bool(want) and n not in want))
                     for n, s in procs]
            done += sum(1 for _n, s in shown if not s)
            stubs += sum(1 for _n, s in shown if s)
            bad += report(ver, segname, shown, cf.segment(segname), who)
            if segname == "PASCALCO" and "{PASCALCOMPILER}" in _text:
                # Procedure 1 of segment 1: the outer block's statement
                # part. Three statements, and the eight file operations
                # around them are not source at all -- BODY2 and BODY3
                # emit a FINIT on entry and an FCLOSE on exit for every
                # FILE declared in the block.
                apple = apple_segment(ver, segname)
                mine = cf.segment(segname)
                a = next(x for x in apple.procedures if x.number == 1)
                b = next(x for x in mine.procedures if x.number == 1)
                done += 1
                bad += diff_proc(f"[{ver}] {segname}.1 PASCALCOMPILER",
                                 apple, a, mine, b, who)
        pdone, pstubs, pbad = report_phases(ver, cf, who)
        done += pdone
        stubs += pstubs
        bad += pbad

    if emu:
        return 0
    print(chr(10) + f"{done + stubs} procedures declared, {done - bad} of "
          f"{done} reconstructed bodies matching Apple's p-code, "
          f"{stubs} still stubs")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
