"""LIBRARY.CODE, the whole file, byte for byte.

src/pascal/programs/1.3/LIBRARY.text compiled by Apple's compiler
(acceptance/2026-09-12-library-complete), then slot 1 copied into a fresh
codefile by Apple's LIBRARY.CODE with the copyright notice -- the release
step finding 267 found for every system program, here applied by the
shipped Librarian to the Librarian's own reconstruction.

Claims, each of which the binary can fail:

  1. **LIBLIB.CODE equals shipped LIBRARY.CODE in all 4096 bytes.**
     A copy with one byte changed must be caught, or the comparison is
     not looking.
  2. **The jump table is part of it.** The first compile was 16 of 16
     procedures instruction-identical and still two bytes short: a label
     placed one statement late swapped two jump-table slots (finding
     269b). A copy with those two operands exchanged must be caught.
  3. **Slot 1 is the reconstruction's bytes**: the compile's LIBRARIA
     segment, the Librarian's and Apple's are the same 3518 bytes, and
     the segment holds all 16 procedures.
  4. **The Librarian did its part**: the compile alone is not Apple's
     file -- the host in slot 0, no notice.
  5. **The source in the tree is the source that was verified**: the
     LIBRARY.text kept with the run equals src/, line endings aside.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from a2pascal.disk import PascalDisk
from oscmp import DISKS_13

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "acceptance" / "2026-09-12-library-librarian" / "LIBLIB.CODE"
COMPILE = ROOT / "acceptance" / "2026-09-12-library-complete"
INPUT = COMPILE / "LIBR13.CODE"
KEPT_SOURCE = COMPILE / "LIBRARY.text"
SOURCE = ROOT / "src" / "pascal" / "programs" / "1.3" / "LIBRARY.text"
TARGET = "LIBRARY.CODE"
NOTICE = (b"COPYRIGHT 1979,1980,1983-1985 APPLE COMPUTER, INC. "
          b"ALL RIGHTS RESERVED")
SEGLEN = 3518
NPROC = 16
# LINKCODE's two jumps to its UNTIL: the IF CONFIRM's FJP and the
# GOTO 1 out of the copy-all loop, file offsets of their operand bytes.
JTAB_OPERANDS = (512 + 0x0A95, 512 + 0x0AD2)

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
    check(len(ours) == len(apple) == 4096,
          f"both are {len(apple)} bytes, 8 blocks (ours {len(ours)})")
    diff = differing(ours, apple)
    check(not diff, f"every byte identical ({len(diff)} differ"
                    + (f", first at {diff[0]}" if diff else "") + ")")
    mutant = bytearray(ours)
    mutant[512 + SEGLEN // 2] ^= 0x01
    check(differing(bytes(mutant), apple) == [512 + SEGLEN // 2],
          "a copy with one code byte flipped is caught, at that byte")
    a, b = JTAB_OPERANDS
    swapped = bytearray(ours)
    swapped[a], swapped[b] = swapped[b], swapped[a]
    check(ours[a] != ours[b]
          and differing(bytes(swapped), apple) == [a, b],
          "the first compile's swapped jump-table slots are caught, "
          "at both operands")
    check(ours[0:4] == b"\x00\x00\x00\x00" and ours[64:72] == b" " * 8,
          "slot 0 is blank: no address, no length, no name")
    check(ours[432] == len(NOTICE) and ours[433:433 + len(NOTICE)] == NOTICE,
          f"the notice is a Pascal string, length byte {len(NOTICE)} first")

    print("=== slot 1 is the reconstruction's own bytes ===")
    mine = segment(compiled, 1)
    check(len(mine) == SEGLEN and segment(ours, 1) == mine
          == segment(apple, 1),
          f"LIBRARIA: compile == Librarian output == shipped "
          f"({len(mine)} bytes)")
    check(bool(mine) and mine[-1] == NPROC,
          f"its procedure dictionary holds {NPROC} procedures "
          f"({mine[-1] if mine else 0})")

    print("=== and the compile alone was not Apple's file ===")
    check(compiled != apple, "LIBR13.CODE differs from LIBRARY.CODE")
    # The host is I.5's PROGRAM PLIBRARIAN. The Librarian drops it, so
    # the shipped file cannot say what Apple called it.
    check(compiled[64:72] == b"PLIBRARI" and compiled[432] == 0,
          "LIBR13.CODE has the host PLIBRARI in slot 0 and no notice")

    print("=== the verified source is the source in the tree ===")
    kept = KEPT_SOURCE.read_bytes().replace(b"\r\n", b"\n")
    tree = SOURCE.read_bytes().replace(b"\r\n", b"\n")
    check(kept == tree, "acceptance LIBRARY.text equals "
                        "src/pascal/programs/1.3/LIBRARY.text")

    print()
    if fail:
        print(f"library whole-file: {len(fail)} check(s) failed")
        return 1
    print("LIBRARY.CODE: 4096 of 4096 bytes, by Apple's compiler and "
          "Librarian")
    print("library-whole-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
