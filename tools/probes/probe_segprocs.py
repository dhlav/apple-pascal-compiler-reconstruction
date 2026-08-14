"""The segment procedures name themselves, and give the source's nesting.

The 1.3 manual, describing the codefile's segment dictionary:

    Each element of the SEGNAME array is an eight-character array that
    contains the first eight characters of the user program, unit, SEGMENT
    procedure, SEGMENT function, or assembly-language procedure name that
    was translated into the corresponding segment. If the name is shorter
    than eight characters, it is padded on the right by spaces.

So the names in the segment dictionary are not labels somebody chose for
this project -- they are identifiers out of Apple's source, and since Apple
Pascal distinguishes nothing past the eighth character, an eight-character
SEGNAME *is* the identifier as far as the compiler is concerned. Where the
name is shorter than eight the padding proves there was nothing more:
BODY1, BODY3 and ROUTINE are exact.

This probe checks the three claims that turns into.

  * **Procedure 1 of every segment is the segment procedure.** Checked
    through the lexical levels: PASCALCO.1 is the program at lex 0, every
    other segment's procedure 1 sits at lex >= 1, and within each segment
    no procedure has a lower lex level than procedure 1 -- which is what
    "everything else here is nested inside it" means.
  * **`names.py` assigns exactly the dictionary's names**, so the registry
    cannot drift from the disk.
  * **The lex levels are a consistent nesting**: every level from 0 up to
    the deepest is occupied, with no gap, in both releases. A gap would
    mean a procedure declared inside nothing.

The lex level of each segment procedure is the depth at which Apple
declared it, which is why this probe prints the table -- it is the
skeleton the reconstruction has to reproduce. Finding 30.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.names import procname

ROOT = Path(__file__).resolve().parent.parent.parent
DISKS = {
    "1.1": "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk",
    "1.3": "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk",
}


def main() -> int:
    bad = []
    for ver, dsk in DISKS.items():
        disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / dsk)
        e = disk.find("SYSTEM.COMPILER")
        cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))

        depths, rows = set(), []
        for seg in cf.segments:
            ps = {p.number: p for p in seg.procedures}
            first = ps.get(1)
            if first is None:
                bad.append(f"{ver} {seg.name}: no procedure 1")
                continue

            # Procedure 1 is the outermost thing in its segment.
            deeper = [p.number for p in seg.procedures
                      if not p.is_native and p.lex_level < first.lex_level]
            if deeper:
                bad.append(f"{ver} {seg.name}: procedure(s) {deeper} sit at a "
                           f"shallower lexical level than procedure 1, so "
                           f"procedure 1 is not the segment procedure")

            want = seg.name
            # The program block is the only thing at lex 0; a SEGMENT
            # procedure is declared inside something, so lex >= 1.
            expect = "== 0" if seg.name == "PASCALCO" else ">= 1"
            if (first.lex_level != 0) == (seg.name == "PASCALCO"):
                bad.append(f"{ver} {seg.name}: procedure 1 is at lex "
                           f"{first.lex_level}, expected {expect}")

            got = procname(seg.name, 1, ver)
            if got != want:
                bad.append(f"{ver} {seg.name}: names.py calls procedure 1 "
                           f"{got!r}, the segment dictionary says {want!r}")

            depths.add(first.lex_level)
            rows.append((first.lex_level, seg.name, first.param_size // 2))

        if depths and sorted(depths) != list(range(max(depths) + 1)):
            bad.append(f"{ver}: segment procedures occupy levels "
                       f"{sorted(depths)} -- a gap means one is declared "
                       f"inside nothing")

        print(f"{ver}: 15 segment procedures, nesting depth 0..{max(depths)}")
        for lex, name, params in sorted(rows):
            print(f"    {'  ' * lex}{name:<9s} lex {lex}  "
                  f"{params} param word(s)")

    if bad:
        print("\n".join(bad))
        return 1
    print("segprocs-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
