"""Compile a SYSTEM.LIBRARY unit and diff it against Apple's, procedure by
procedure.

The library reconstruction starts from a better place than the compiler did.
Each unit's INTERFACE is in the library as Apple's own source text (finding
92a), so the headings, the parameter names and the types are given rather
than inferred -- and, because a unit's interface headings are what assign the
procedure numbers, the interface also fixes the numbering before a line of
implementation is written.

    python tools/unitbuild.py TRANSCEND            # fast tier, 1.3
    python tools/unitbuild.py TRANSCEND --ver=1.1
    python tools/unitbuild.py --emu TRANSCEND      # write it to WORK: instead

Sources live in src/pascal/units/{ver}/{UNIT}.text. The fast tier is
`ucsdpsys_compile`, and it can falsify a body but never accept one (finding
55); the emulator tier settles it, exactly as for the compiler.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import procbuild
import xcompile
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile

# Eight characters, because that is what a Pascal volume directory holds for
# the stem and what the emulator has to be able to type.
EMUNAME = {"TRANSCEND": "TRANSCND", "CHAINSTUFF": "CHAINSTF",
           "LONGINTIO": "LONGINTI", "PASCALIO": "PASCALIO",
           "TURTLEGRAPHICS": "TURTLEGR", "APPLESTUFF": "APPLESTF"}

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "pascal" / "units"
LIB = {
    "1.1": "UCSD Pascal 1.1_1.dsk",
    "1.3": "Apple II Pascal 1.3 APPLE1_ 680-0283-A.dsk",
}
# The unit's own name against the eight characters the dictionary holds.
SEGNAME = {"TRANSCEND": "TRANSCEN", "CHAINSTUFF": "CHAINSTU",
           "LONGINTIO": "LONGINTI", "PASCALIO": "PASCALIO",
           "TURTLEGRAPHICS": "TURTLEGR", "APPLESTUFF": "APPLESTU"}


def apple_unit(ver: str, unit: str):
    disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / LIB[ver])
    e = disk.find("SYSTEM.LIBRARY")
    cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))
    want = SEGNAME[unit]
    for s in cf.segments:
        if s.name.strip() == want and s.procedures:
            return s
    raise SystemExit(f"{unit}: no code segment named {want} in {ver}'s library")


def write_for_emulator(ver: str, unit: str, path: Path) -> None:
    """Put the unit source on WORK: for Apple's own compiler.

    The fast tier gets the shape of a body right and cannot settle it. Five
    things it does differently have nothing to do with the source: it
    allocates locals forward where Apple allocates backwards (finding 61),
    it folds `2*JMAX+1` and the constant subrange check Apple emits anyway,
    it keeps a FOR loop's limit in no temporary where Apple spends a word on
    one, it renders a real literal `0.0` as `SLDC 0; FLT`, and it floats an
    integer operand with FLT before the real constant where Apple pushes the
    constant and floats underneath it with FLO. None of those is visible in
    the source and all of them show as DIFFERS. Apple's compiler is the
    authority; this is how the source reaches it.
    """
    from a2pascal.diskwrite import PascalWriter
    from a2pascal.srcfmt import expand_tabs
    from a2pascal.textfile import encode_text

    src = expand_tabs(procbuild.uncomment(path.read_text(encoding="ascii",
                                                         errors="replace")))
    src = src[:-1] if src.endswith(chr(10)) else src
    name = EMUNAME[unit] + ".TEXT"
    dsk = ROOT / "build" / "disks" / "WORK.dsk"
    w = PascalWriter.from_file(dsk)
    for stale in [e.name for e in w.entries()]:
        if stale.startswith(("BODY", EMUNAME[unit])):
            w.remove_file(stale)
    w.add_file(name, encode_text(src))
    w.save(dsk)
    print(f"wrote WORK:{name} ({len(src.splitlines())} lines); "
          f"{w.free_blocks()} blocks left on WORK: for the codefile")


def emu_codefile(unit: str):
    """The codefile Apple's compiler wrote, from whichever volume has it."""
    name = EMUNAME[unit] + ".CODE"
    for vol in ("WORK.dsk", "WORK2.dsk"):
        dsk = ROOT / "build" / "disks" / vol
        if not dsk.exists():
            continue
        d = PascalDisk.from_file(dsk)
        e = d.find(name)
        if e is not None:
            print(f"reading {vol}:{name} ({e.blocks} blocks)")
            return CodeFile(d.read_blocks(e.first_block, e.blocks))
    raise SystemExit(f"{name} is on neither WORK: nor WORK2: -- the emulator "
                     f"run did not produce it")


def ours(path: Path, unit: str):
    cf = CodeFile(xcompile.compile_text(path.read_text(encoding="ascii",
                                                       errors="replace")))
    want = SEGNAME[unit]
    for s in cf.segments:
        if s.name.strip().upper().startswith(want[:8]):
            return s
    raise SystemExit(f"{unit}: our codefile has no segment named {want}; "
                     f"it has {[s.name for s in cf.segments]}")


def unit_bytes(ver: str, unit: str, apple, mine) -> int:
    """The unit's bytes against Apple's -- jump tables and constants included.

    `diff_proc` blanks two things it has to blank: an absolute jump target,
    because the same procedure at a different address would differ at every
    branch, and a real constant, because the disassembler prints those as
    `$---- $----`. Both are exactly where a reconstruction goes wrong
    quietly. A backward branch's destination is a word in the jump table and
    not in the instruction stream at all (finding 90), and a real literal is
    four bytes the listing never shows -- and Apple's compiler converts
    decimal by accumulating digits in single precision (NUMSTRIN.NUMBER), so
    a constant can be a ulp off and read as identical.

    So this compares `enter_ic .. jtab + 2` byte for byte, and then the
    segment as a whole image.
    """
    same = bad = 0
    for a in apple.procedures:
        b = next((x for x in mine.procedures if x.number == a.number), None)
        if b is None or a.is_native:
            continue
        x = apple.data[a.enter_ic:a.jtab + 2]
        y = mine.data[b.enter_ic:b.jtab + 2]
        if x == y:
            same += 1
            continue
        bad += 1
        if len(x) != len(y):
            print(f"[{ver}] {unit}.{a.number}: {len(x)} bytes against "
                  f"{len(y)}")
            continue
        off = [i for i, (u, v) in enumerate(zip(x, y)) if u != v]
        print(f"[{ver}] {unit}.{a.number}: {len(off)} byte(s) differ in "
              f"{len(x)}")
        for i in off[:12]:
            at = a.enter_ic + i
            if at >= a.jtab - 8:
                where = "attribute table"
            elif at >= a.exit_ic:
                where = f"jump table, jtab{at - a.jtab:d}"
            else:
                where = "code"
            print(f"      ${at:04X} ({where}): Apple ${x[i]:02X}, "
                  f"ours ${y[i]:02X}")
    whole = len(apple.data) == len(mine.data) and apple.data == mine.data
    print(f"[{ver}] {unit}: {same} of {same + bad} procedures byte-identical"
          + (", and the whole segment end to end" if whole
             else f"; the segment images differ "
                  f"({len(apple.data)} bytes against {len(mine.data)})"))
    return bad + (0 if whole else 1)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    ver = next((a.split("=", 1)[1] for a in sys.argv
                if a.startswith("--ver=")), "1.3")
    if not args:
        raise SystemExit(__doc__)
    emu = "--emu" in sys.argv
    check = "--emu-check" in sys.argv
    if not emu and not check and not xcompile.available():
        print("SKIPPED: ucsdpsys_compile is not built")
        return 0

    bad = done = 0
    for unit in (a.upper() for a in args):
        if unit not in SEGNAME:
            raise SystemExit(f"{unit}: not one of {', '.join(SEGNAME)}")
        path = SRC / ver / f"{unit}.text"
        if not path.exists():
            print(f"[{ver}] {unit}: no source at {path.relative_to(ROOT)}")
            bad += 1
            continue
        if emu:
            write_for_emulator(ver, unit, path)
            continue
        apple = apple_unit(ver, unit)
        if check:
            cf = emu_codefile(unit)
            mine = next(s for s in cf.segments if s.procedures)
            who = "Apple's compiler"
        else:
            who = "fast tier"
            try:
                mine = ours(path, unit)
            except xcompile.CompileError as exc:
                print(f"[{ver}] {unit} did not compile:\n{exc}")
                return 1

        if len(mine.procedures) != len(apple.procedures):
            print(f"[{ver}] {unit}: {len(mine.procedures)} procedures "
                  f"against Apple's {len(apple.procedures)} -- the numbering "
                  f"is wrong before any body is")
            bad += 1
        for a in apple.procedures:
            b = next((x for x in mine.procedures if x.number == a.number),
                     None)
            label = f"[{ver}] {unit}.{a.number}"
            if b is None:
                print(f"{label}: missing from ours")
                bad += 1
                continue
            if a.is_native:
                print(f"{label}: native 6502, {a.jtab - a.enter_ic} bytes -- "
                      f"the assembler tier's (finding 44e)")
                continue
            done += 1
            bad += procbuild.diff_proc(label, apple, a, mine, b, who)
        if check:
            bad += unit_bytes(ver, unit, apple, mine)
    if emu:
        return 0
    print(f"\n{done} p-code procedures compared, {done - bad} matching "
          f"Apple's")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
