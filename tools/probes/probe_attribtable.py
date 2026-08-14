"""How are procedures laid out, and what are the two bytes at JTAB?

Finding 4 read the attribute table as `JTAB+0` procedure number, `JTAB+1`
lexical level. `PASCALCO.23` is the routine that writes it, and its last
two instructions are `EMIT(G13)` then `EMIT(G96 - 1)`. Which byte each of
those lands on depends on a layout fact that had never been checked: that
a procedure's attribute table is the *end* of it, with the next procedure's
body starting immediately after.

This probe checks three things over every p-code procedure on both disks.

  * **Contiguity.** Sorted by `enter_ic`, each procedure's `jtab + 2` is
    the next one's `enter_ic`. That is what makes the two `EMIT`s land on
    `JTAB+0` and `JTAB+1` in that order, which is what pins `G13` to the
    procedure-number byte and `G96 - 1` to the lex-level byte.
  * **`JTAB+0` is the procedure number**, running 1..N within each segment
    -- never the segment number, which would make every procedure in
    `COMPINIT` read 7.
  * **`JTAB+1` is small.** A lexical level is 0, 1 or 2 in this compiler;
    a jump-table entry count would not be.

Together these are the evidence for the open question in finding 27: the
behaviour finding 23c attributed to global 13 is global 96's.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile

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

        procs = gaps = 0
        levels: dict[int, int] = {}
        for seg in cf.segments:
            ps = sorted((p for p in seg.procedures if not p.is_native),
                        key=lambda p: p.enter_ic)
            if not ps:
                continue
            procs += len(ps)
            for a, b in zip(ps, ps[1:]):
                if a.jtab + 2 != b.enter_ic:
                    gaps += 1
                    if gaps <= 3:
                        bad.append(f"{ver} {seg.name}.{a.number}: jtab+2 = "
                                   f"${a.jtab + 2:04X}, next procedure starts "
                                   f"at ${b.enter_ic:04X}")
            # JTAB+0 must be the procedure number, not the segment number
            wrong = [p.number for p in ps if seg.data[p.jtab] != p.number]
            if wrong:
                bad.append(f"{ver} {seg.name}: JTAB+0 is not the procedure "
                           f"number for {wrong[:5]}")
            for p in ps:
                levels[seg.data[p.jtab + 1]] = levels.get(
                    seg.data[p.jtab + 1], 0) + 1

        # A lexical level and a jump-table entry count are both small
        # non-negative numbers, so the test has to be the *shape* of the
        # distribution, not its range. Nesting depth gives exactly one
        # procedure at 0 -- the program block -- then a hump and a thin
        # tail. A count of jump-table entries would put dozens of
        # procedures at 0, since most procedures have no backward branch.
        if levels.get(0, 0) != 1:
            bad.append(f"{ver}: {levels.get(0, 0)} procedures have JTAB+1 = 0. "
                       f"A lexical level gives exactly one (the program "
                       f"block); this looks like a count instead.")
        if max(levels) > 10:
            bad.append(f"{ver}: JTAB+1 reaches {max(levels)}, too deep to be "
                       f"a lexical level in a 15-segment program")
        print(f"{ver}: {procs} procedures, {gaps} layout gaps; "
              f"JTAB+1 distribution " +
              " ".join(f"{k}:{v}" for k, v in sorted(levels.items())))

    if bad:
        print("\n".join(bad))
        return 1
    print("attribtable-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
