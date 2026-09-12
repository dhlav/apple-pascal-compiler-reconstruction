"""SYSTEM.COMPILER, the whole file, byte for byte.

Finding 267: Apple's release step for a system program was LIBRARY.CODE,
run after the compiler and the Linker -- copy segments 1 to n, in slot
order, into a fresh codefile, and answer `Notice?` with the copyright line.
That is what leaves slot 0 blank (finding 105a's "missing" segment 0), puts
the segments on disk in slot order, zeroes the SEGSUSED words, and writes
the comment as a Pascal string with its length byte.

The kept run is Apple's own Librarian, driven by `emuremote.py librarian`,
applied to COMPLINK.CODE -- the reconstruction compiled by Apple's compiler,
its native SEARCH assembled by Apple's assembler, and the two linked by
Apple's Linker (2026-08-25-compiler-linked-v2). So every byte of the
result came out of Apple's four tools and this repository's source.

Claims, each of which the binary can fail:

  1. **LIBCOMP.CODE equals shipped SYSTEM.COMPILER in all 39936 bytes** --
     block 0, every segment, and the slack after each segment's end.
  2. **The Librarian did the part finding 267 says it did.** Its input,
     COMPLINK.CODE, is NOT identical to Apple's file: it still has
     PASCALSY in slot 0, its segments sit in a different physical order,
     and it carries no notice. If the comparison in (1) could not see a
     difference, it would pass this input too, and this check fails.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from a2pascal.disk import PascalDisk
from oscmp import DISKS_13

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "acceptance" / "2026-09-12-compiler-librarian" / "LIBCOMP.CODE"
INPUT = (ROOT / "acceptance" / "2026-08-25-compiler-linked-v2"
         / "COMPLINK.CODE")
TARGET = "SYSTEM.COMPILER"
NOTICE = b"COPYRIGHT 1979,1980,1983-1985 APPLE COMPUTER, INC. ALL RIGHTS RESERVED"

fail = []


def check(ok: bool, label: str) -> None:
    print(("  ok   " if ok else "  FAIL ") + label)
    if not ok:
        fail.append(label)


def shipped(name: str) -> bytes:
    for fname in DISKS_13:
        d = PascalDisk.from_file(ROOT / "evidence" / "disks" / fname)
        try:
            e = d.find(name)
        except Exception:
            continue
        if e is not None:
            return bytes(d.read_blocks(e.first_block, e.blocks))
    raise SystemExit(f"{name} is on none of the 1.3 disks")


def main() -> int:
    for p in (RUN, INPUT):
        if not p.exists():
            print(f"{p} is missing -- acceptance runs are kept verbatim")
            return 1
    apple = shipped(TARGET)
    ours = RUN.read_bytes()
    before = INPUT.read_bytes()

    print("=== the Librarian's output against Apple's shipped file ===")
    check(len(ours) == len(apple) == 39936,
          f"both are {len(apple)} bytes, 78 blocks (ours {len(ours)})")
    diff = [i for i in range(min(len(ours), len(apple)))
            if ours[i] != apple[i]]
    check(not diff, f"every byte identical ({len(diff)} differ"
                    + (f", first at {diff[0]}" if diff else "") + ")")
    check(ours[0:4] == b"\x00\x00\x00\x00" and ours[64:72] == b" " * 8,
          "slot 0 is blank: no address, no length, no name")
    check(ours[432] == len(NOTICE) and ours[433:433 + len(NOTICE)] == NOTICE,
          f"the notice is a Pascal string, length byte {len(NOTICE)} first")

    print("=== and its input was not already Apple's file ===")
    check(before != apple, "COMPLINK.CODE differs from SYSTEM.COMPILER")
    check(before[64:72] == b"PASCALSY",
          "COMPLINK.CODE still has PASCALSY in slot 0")
    check(before[432] == 0, "COMPLINK.CODE carries no notice")

    print()
    if fail:
        print(f"compiler whole-file: {len(fail)} check(s) failed")
        return 1
    print("SYSTEM.COMPILER: 39936 of 39936 bytes, by Apple's own four tools")
    print("compiler-whole-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
