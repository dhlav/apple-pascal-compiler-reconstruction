"""Do the library's reconstructed native sources assemble back to Apple's bytes?

Three of the six SYSTEM.LIBRARY units are part 6502, and `src/native/`
carries all fourteen of those procedures:

    APPLESTF.TEXT   APPLESTUFF's six
    TURTLEGR.TEXT   TURTLEGRAPHICS' seven
    LONGINTS.TEXT   LONGINTIO's one, the long-integer engine

The acceptance test is `SYSTEM.ASSMBLER` under an emulator (finding 44e).
This is the fast tier of the same test, the way `probe_native_asm.py` is for
`SYSTEM.COMPILER`: `tools/asm6502.py` assembles the source and lays each
procedure out as the Linker would -- code, four relocation tables, ENTER IC
and the attribute word -- and the result is compared byte for byte against
the library on the disk.

The comparison covers the whole procedure, `enter_ic` through `jtab + 2`, so
the relocation tables have to come out right as well as the instructions.
They are generated from the source's symbolic operands and are never written
down, so a reference written as a constant where Apple wrote a label fails
here even when it assembles.

Two things in the layout are the Linker's rather than the assembler's, and
this is where they come from:

* the base a `.REF` resolves to. A symbol one procedure exports and another
  imports lands at an offset within the *segment*, which depends on what
  else the Linker put in front of it -- including the Pascal procedures. The
  bases come from the shipped image, exactly as the Linker would supply
  them; what is being checked is that the reference is symbolic at all, and
  that its offset within the defining procedure is right.

* RELOCSEG, the high byte of the attribute word. The manual (IV-36) fixes
  it: 0 means base-relative relocation goes through the BASE register, and a
  non-zero value names the data segment it goes through instead, with 1 for
  an Intrinsic Unit that has no data segment. So APPLESTUFF and LONGINTIO
  are 1, TURTLEGRAPHICS is 21 because that is its DATA segment, and the
  probe checks the disk against that rule rather than reading the byte off
  the disk and handing it back.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from asm6502 import assemble_file, AsmError
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile, RELOC_KINDS

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "native"
IMG = ROOT / "evidence" / "disks" / \
    "Apple II Pascal 1.3 APPLE1_ 680-0283-A.dsk"

# file -> segment, RELOCSEG, and the procedures in the order the source
# declares them, which is the order they sit in the shipped segment
# (finding 96c). Each is (procedure number, name, .PROC or .FUNC,
# declared parameter words).
UNITS = [
    ("APPLESTF.TEXT", "APPLESTU", 1, [
        (2, "PADDLE", "FUNC", 1), (3, "BUTTON", "FUNC", 1),
        (4, "TTLOUT", "PROC", 2), (8, "NOTE", "PROC", 2),
        (6, "RANDOM", "FUNC", 0), (7, "RANDOMIZE", "PROC", 0)]),
    ("TURTLEGR.TEXT", "TURTLEGR", 21, [
        (30, "HIRES", "PROC", 0), (31, "CLIP", "FUNC", 4),
        (20, "MOVEABS", "PROC", 2), (21, "MOVEREL", "PROC", 2),
        (22, "FILLIT", "PROC", 0), (15, "SCREENBIT", "FUNC", 2),
        (16, "DRAWBLOCK", "PROC", 9)]),
    ("LONGINTS.TEXT", "LONGINTI", 1, [
        (4, "DECOPS", "PROC", 0)]),
]


def main() -> int:
    bad, checked = [], 0

    def check(cond, msg):
        nonlocal checked
        checked += 1
        if not cond:
            bad.append(msg)

    d = PascalDisk.from_file(IMG)
    e = d.find("SYSTEM.LIBRARY")
    cf = CodeFile(d.read_blocks(e.first_block, e.blocks))

    for fname, segname, relocseg, want in UNITS:
        seg = next((s for s in cf.segments
                    if s.name.strip() == segname and s.procedures), None)
        if seg is None:
            bad.append(f"{segname}: not in SYSTEM.LIBRARY")
            continue
        byn = {q.number: q for q in seg.native_procedures}
        check(sorted(byn) == sorted(n for n, *_ in want),
              f"{segname}: disk has native procedures {sorted(byn)}, "
              f"{fname} has {sorted(n for n, *_ in want)}")

        # The Linker's job: where each procedure lands in the segment.
        bases = {name: byn[n].enter_ic for n, name, *_ in want if n in byn}
        try:
            procs = assemble_file(SRC / fname, bases=bases)
        except AsmError as ex:
            bad.append(f"{fname} does not assemble:\n{ex}")
            continue
        check([p.name for p in procs] == [name for _, name, *_ in want],
              f"{fname} declares {[p.name for p in procs]}, expected "
              f"{[name for _, name, *_ in want]} -- the order is the order "
              f"they sit in the segment")

        by_name = {p.name: p for p in procs}
        for num, name, kind, words in want:
            p, a = byn.get(num), by_name.get(name)
            if p is None or a is None:
                bad.append(f"{segname}.{num} {name}: missing")
                continue
            check(a.kind == kind,
                  f"{name} is declared .{a.kind}, expected .{kind}")
            check(a.words == words,
                  f"{name} declares {a.words} parameter words, "
                  f"expected {words}")
            check(seg.data[p.jtab] == 0,
                  f"{name}: PROCEDURE NUMBER is {seg.data[p.jtab]}, and 0 is "
                  f"what marks a procedure native")
            check(seg.data[p.jtab + 1] == relocseg,
                  f"{name}: RELOCSEG on the disk is {seg.data[p.jtab + 1]}, "
                  f"and the manual's rule gives {relocseg}")

            disk = seg.data[p.enter_ic:p.jtab + 2]
            got = a.image(relocseg=relocseg)
            check(len(got) == len(disk),
                  f"{name}: assembled {len(got)} bytes, disk has {len(disk)}")
            if len(got) == len(disk):
                diffs = [i for i, (x, y) in enumerate(zip(disk, got))
                         if x != y]
                check(not diffs,
                      f"{name}: {len(diffs)} byte(s) differ, first at "
                      f"+${diffs[0]:04X} (${p.enter_ic + diffs[0]:04X}): "
                      f"disk {disk[diffs[0]]:02x}, assembled "
                      f"{got[diffs[0]]:02x}" if diffs else "")

            # Not implied by the byte compare: that the relocation entries
            # the assembler generated are the ones the disk names, kind by
            # kind. A coincidence of lengths cannot pass this.
            mine = {"procedure": a.reloc, "segment": a.segreloc,
                    "interp": a.interpreloc, "base": []}
            for k in RELOC_KINDS:
                check(sorted(mine[k]) == sorted(t - p.enter_ic
                                                for t in p.reloc[k]),
                      f"{name}: {k}-relative -- assembler relocates "
                      f"{sorted(mine[k])}, disk relocates "
                      f"{sorted(t - p.enter_ic for t in p.reloc[k])}")

    if bad:
        print("\n".join(bad))
        return 1
    print(f"{checked} checks, all passed")
    print("lib-native-asm-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
