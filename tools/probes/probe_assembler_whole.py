"""SYSTEM.ASSMBLER, the whole file, byte for byte -- with one borrowed slot.

The same release step finding 267e verified for SYSTEM.COMPILER, run with
Apple's own LIBRARY.CODE: segments 1 to 6 copied from the reconstruction's
ASSMBLER.CODE (acceptance/2026-09-12-assembler-complete, every procedure
already instruction-identical, finding 266), then `N(ew file` and slot 0
copied from shipped SYSTEM.ASSMBLER itself, then the notice.

That slot 0 is PASCALIO, which nothing on the 1.3 disks can rebuild
(finding 235b). Its 572 code bytes and its interface-text block are
therefore Apple's, copied, and match by construction -- this probe claims
nothing about them. What it does claim, each of which can fail:

  1. **All 25600 bytes equal shipped SYSTEM.ASSMBLER**: block 0, the six
     reconstructed segments including their slack, and the layout that
     puts PASCALIO's text at block 47 and its code at 48, copied last.
  2. **Slots 1 to 6 are the reconstruction's bytes, not Apple's**: they
     are compared against ASSMBLER.CODE, the compile, as well as against
     the shipped file.
  3. **The Librarian did the work**: ASSMBLER.CODE itself is not Apple's
     file -- PASCALSY in slot 0, no notice, innermost-first layout.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from a2pascal.disk import PascalDisk
from oscmp import DISKS_13

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "acceptance" / "2026-09-12-assembler-librarian" / "LIBASM.CODE"
INPUT = (ROOT / "acceptance" / "2026-09-12-assembler-complete"
         / "ASSMBLER.CODE")
TARGET = "SYSTEM.ASSMBLER"

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


def main() -> int:
    for p in (RUN, INPUT):
        if not p.exists():
            print(f"{p} is missing -- acceptance runs are kept verbatim")
            return 1
    apple = shipped(TARGET)
    ours = RUN.read_bytes()
    compiled = INPUT.read_bytes()

    print("=== the Librarian's output against Apple's shipped file ===")
    check(len(ours) == len(apple) == 25600,
          f"both are {len(apple)} bytes (ours {len(ours)})")
    diff = [i for i in range(min(len(ours), len(apple)))
            if ours[i] != apple[i]]
    check(not diff, f"every byte identical ({len(diff)} differ)")
    check(ours[64:72] == b"PASCALIO" and words(ours, 0, 2) == [48, 572]
          and words(ours, 224, 1) == [47],
          "PASCALIO in slot 0, text at block 47, code at 48 -- copied last")

    print("=== slots 1-6 are the reconstruction's own bytes ===")
    for slot in range(1, 7):
        name = bytes(ours[64 + 8 * slot:72 + 8 * slot]).decode()
        mine = segment(compiled, slot)
        check(segment(ours, slot) == mine == segment(apple, slot) and mine,
              f"slot {slot} {name}: compile == Librarian output == shipped "
              f"({len(mine)} bytes)")

    print("=== and the compile alone was not Apple's file ===")
    check(compiled != apple, "ASSMBLER.CODE differs from SYSTEM.ASSMBLER")
    check(compiled[64:72] == b"PASCALSY" and compiled[432] == 0,
          "ASSMBLER.CODE has PASCALSY in slot 0 and no notice")

    print()
    if fail:
        print(f"assembler whole-file: {len(fail)} check(s) failed")
        return 1
    print("SYSTEM.ASSMBLER: 25600 of 25600 bytes; slots 1-6 reconstructed, "
          "slot 0 is Apple's PASCALIO, copied")
    print("assembler-whole-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
