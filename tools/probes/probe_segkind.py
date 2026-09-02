"""SEGKIND across the disk set, and what it says about FIOPRIMS (finding 200).

The segment dictionary's SEGKIND word (0x0C0 + 2*slot) is the only field
that distinguishes a unit from a segment procedure: name, SEGINFO, mtype
and the procedure dictionary are identical either way. `codefile.py`
documented the field in its own header from the start and never parsed it,
and that gap is exactly why `FIOPRIMS` was modelled as a `SEGMENT
PROCEDURE` through findings 190 and 194 -- five source shapes tried against
Apple's own compiler, all failing, none of them a unit.

Each check below is one the binary can fail on its own terms:

  1. Every segment of both 1.3 operating systems is LINKED except FIOPRIMS,
     which is LINKED_INTRINS. If that ever reads LINKED, the claim that
     FIOPRIMS is an intrinsic unit is wrong.
  2. Every code segment of SYSTEM.LIBRARY is LINKED_INTRINS too (its one
     data segment is DATASEG) -- the units this project has already
     reconstructed read back the same way FIOPRIMS does, which is what
     makes FIOPRIMS's own value mean "unit" rather than "odd".
  3. 1.1's operating system has no FIOPRIMS at all: segment 2 is DEBUGGER,
     and it is LINKED. The unit is a 1.2/1.3 addition, and it took the
     segment slot the debugger used to hold.
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
    ("1.3 64K", "Apple II Pascal 1.3 APPLE1_ 680-0283-A.dsk", "SYSTEM.PASCAL"),
]
LIBRARY = ("Apple II Pascal 1.3 APPLE1_ 680-0283-A.dsk", "SYSTEM.LIBRARY")
OS_11 = ("UCSD Pascal 1.1_1.dsk", "SYSTEM.PASCAL")

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

print("=== 1.1 has no FIOPRIMS: segment 2 is the debugger ===")
segs = segments(*OS_11)
by_num = {s.number: s for s in segs}
check("FIOPRIMS" not in {s.name for s in segs},
      "1.1: no FIOPRIMS segment at all")
check(2 in by_num and by_num[2].name == "DEBUGGER",
      f"1.1: segment 2 is DEBUGGER, got {by_num.get(2) and by_num[2].name}")
check(2 in by_num and not by_num[2].is_intrinsic_unit,
      "1.1: that debugger segment is not intrinsic")

print()
if fail:
    print(f"SEGKIND: {len(fail)} check(s) failed")
    sys.exit(1)
print("SEGKIND: every check passed")
print("segkind-ok")
