"""SYSTEM.LINKER, the whole file, byte for byte.

src/pascal/programs/1.3/LINKER.text compiled by Apple's compiler
(acceptance/2026-09-12-linker-complete), then slot 1 copied into a fresh
codefile by Apple's LIBRARY.CODE with the copyright notice -- the release
step finding 267 found for every system program. No native code, so no
assembler and no Linker: two of Apple's tools and this repository's source.

Claims, each of which the binary can fail:

  1. **LIBLINK.CODE equals shipped SYSTEM.LINKER in all 12800 bytes.**
     A copy with one byte changed must be caught, or the comparison is
     not looking.
  2. **Slot 1 is the reconstruction's bytes**: the compile's LINKER
     segment, the Librarian's and Apple's are the same 11804 bytes, and
     the segment holds all 51 procedures.
  3. **The Librarian did its part**: the compile alone is not Apple's
     file -- PASCALSY in slot 0, no notice.
  4. **The source in the tree is the source that was verified**: the
     LINKER.text kept with the run equals src/, line endings aside, so an
     edit to src/ that was never compiled fails here rather than riding
     on this result.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from a2pascal.disk import PascalDisk
from oscmp import DISKS_13

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "acceptance" / "2026-09-12-linker-librarian" / "LIBLINK.CODE"
COMPILE = ROOT / "acceptance" / "2026-09-12-linker-complete"
INPUT = COMPILE / "LINKER.CODE"
KEPT_SOURCE = COMPILE / "LINKER.text"
SOURCE = ROOT / "src" / "pascal" / "programs" / "1.3" / "LINKER.text"
TARGET = "SYSTEM.LINKER"
NOTICE = (b"COPYRIGHT 1979,1980,1983-1985 APPLE COMPUTER, INC. "
          b"ALL RIGHTS RESERVED")

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


def words(b: bytes, off: int, n: int) -> list[int]:
    return [b[off + 2 * i] | b[off + 2 * i + 1] << 8 for i in range(n)]


def segment(b: bytes, slot: int) -> bytes:
    addr, leng = words(b, 4 * slot, 2)
    return b[addr * 512: addr * 512 + leng]


def differing(a: bytes, b: bytes) -> list[int]:
    return ([i for i in range(min(len(a), len(b))) if a[i] != b[i]]
            + list(range(min(len(a), len(b)), max(len(a), len(b)))))


def main() -> int:
    for p in (RUN, INPUT, KEPT_SOURCE, SOURCE):
        if not p.exists():
            print(f"{p} is missing -- acceptance runs are kept verbatim")
            return 1
    apple = shipped(TARGET)
    ours = RUN.read_bytes()
    compiled = INPUT.read_bytes()

    print("=== the Librarian's output against Apple's shipped file ===")
    check(len(ours) == len(apple) == 12800,
          f"both are {len(apple)} bytes, 25 blocks (ours {len(ours)})")
    diff = differing(ours, apple)
    check(not diff, f"every byte identical ({len(diff)} differ"
                    + (f", first at {diff[0]}" if diff else "") + ")")
    mutant = bytearray(ours)
    mutant[512 + 11804 // 2] ^= 0x01
    check(differing(bytes(mutant), apple) == [512 + 11804 // 2],
          "a copy with one code byte flipped is caught, at that byte")
    check(ours[0:4] == b"\x00\x00\x00\x00" and ours[64:72] == b" " * 8,
          "slot 0 is blank: no address, no length, no name")
    check(ours[432] == len(NOTICE) and ours[433:433 + len(NOTICE)] == NOTICE,
          f"the notice is a Pascal string, length byte {len(NOTICE)} first")

    print("=== slot 1 is the reconstruction's own bytes ===")
    mine = segment(compiled, 1)
    check(len(mine) == 11804 and segment(ours, 1) == mine
          == segment(apple, 1),
          f"LINKER: compile == Librarian output == shipped "
          f"({len(mine)} bytes)")
    check(bool(mine) and mine[-1] == 51,
          f"its procedure dictionary holds 51 procedures "
          f"({mine[-1] if mine else 0})")

    print("=== and the compile alone was not Apple's file ===")
    check(compiled != apple, "LINKER.CODE differs from SYSTEM.LINKER")
    check(compiled[64:72] == b"PASCALSY" and compiled[432] == 0,
          "LINKER.CODE has PASCALSY in slot 0 and no notice")

    print("=== the verified source is the source in the tree ===")
    kept = KEPT_SOURCE.read_bytes().replace(b"\r\n", b"\n")
    tree = SOURCE.read_bytes().replace(b"\r\n", b"\n")
    check(kept == tree, "acceptance LINKER.text equals "
                        "src/pascal/programs/1.3/LINKER.text")

    print()
    if fail:
        print(f"linker whole-file: {len(fail)} check(s) failed")
        return 1
    print("SYSTEM.LINKER: 12800 of 12800 bytes, by Apple's compiler and "
          "Librarian")
    print("linker-whole-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
