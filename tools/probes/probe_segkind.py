"""SEGKIND across the disk set, and what it says about FIOPRIMS (finding 200).

The segment dictionary's SEGKIND word (0x0C0 + 2*slot) is the only field
that distinguishes a unit from a segment procedure: name, SEGINFO, mtype
and the procedure dictionary are identical either way. `codefile.py`
documented the field in its own header from the start and never parsed it,
and that gap is exactly why `FIOPRIMS` was modelled as a `SEGMENT
PROCEDURE` through findings 190 and 194 -- five source shapes tried against
Apple's own compiler, all failing, none of them a unit.

Each check below is one the binary can fail on its own terms:

  1. Every segment of the 128K 1.3 operating system is LINKED except FIOPRIMS,
     which is LINKED_INTRINS. If that ever reads LINKED, the claim that
     FIOPRIMS is an intrinsic unit is wrong.
  2. Every code segment of SYSTEM.LIBRARY is LINKED_INTRINS too (its one
     data segment is DATASEG) -- the units this project has already
     reconstructed read back the same way FIOPRIMS does, which is what
     makes FIOPRIMS's own value mean "unit" rather than "odd".

The 1.1 comparison this probe used to make -- 1.1's operating system has
no FIOPRIMS, its segment 2 is DEBUGGER -- went with the 1.1 disks into
evidence/archive/1.1, as did the 64K SYSTEM.PASCAL row: the target is the
128K 1.3 system only.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile

ROOT = Path(__file__).resolve().parents[2]
DISKS = ROOT / "evidence" / "disks"

OS_13 = [
    ("1.3 128K", "Apple II Pascal 1.3 APPLE3_ 680-0290-A.dsk", "128K.PASCAL"),
]
LIBRARY = ("Apple II Pascal 1.3 APPLE1_ 680-0283-A.dsk", "SYSTEM.LIBRARY")

fail = []


def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what)
    if not ok:
        fail.append(what)


def segments(dsk, name):
    return CodeFile(PascalDisk.from_file(DISKS / dsk).read_file(name)).segments


print("=== 1.3: FIOPRIMS is the operating system's one intrinsic unit ===")
for label, dsk, name in OS_13:
    segs = segments(dsk, name)
    intrinsic = [s.name for s in segs if s.is_intrinsic_unit]
    check(intrinsic == ["FIOPRIMS"],
          f"{label}: exactly FIOPRIMS is intrinsic, got {intrinsic}")
    fio = next(s for s in segs if s.name == "FIOPRIMS")
    check(fio.segkind == "LINKED_INTRINS",
          f"{label}: FIOPRIMS segkind is LINKED_INTRINS, got {fio.segkind}")
    others = {s.segkind for s in segs if s.name != "FIOPRIMS"}
    check(others == {"LINKED"},
          f"{label}: every other segment is LINKED, got {sorted(others)}")

print("=== SYSTEM.LIBRARY's units read back the same way ===")
segs = segments(*LIBRARY)
code = [s for s in segs if s.segkind != "DATASEG"]
check(all(s.is_intrinsic_unit for s in code),
      "every SYSTEM.LIBRARY code segment is LINKED_INTRINS: "
      + ", ".join(f"{s.name}={s.segkind}" for s in code))

print()
if fail:
    print(f"SEGKIND: {len(fail)} check(s) failed")
    sys.exit(1)
print("SEGKIND: every check passed")
print("segkind-ok")
