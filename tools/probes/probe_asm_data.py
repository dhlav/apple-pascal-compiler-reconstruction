"""6502.OPCODES and 6502.ERRORS, written by Apple's compiler and system.

acceptance/2026-09-13-asm-data holds the run: MAKEOPS and MAKEERRS
compiled by SYSTEM.COMPILER and run under the 1.3 system, reading
OPS6502.TEXT and ERRS6502.TEXT, and the two data files they wrote, as
whole disk blocks (finding 276).

Claims, each of which the binary can fail:

  1. **6502.OPCODES is identical**, all 1024 bytes of its two blocks,
     unused tail included; a flipped byte is caught.
  2. **6502.ERRORS has Apple's 85 records and zero tail**, and differs
     in exactly the 287 bytes that still hold the record window's first
     fill: a record copies only its length byte and characters into the
     window, so each record keeps what the one before it left, back to
     whatever memory the window started as.
  3. **That fill is the whole difference**: putting Apple's 40 fill bytes
     into ours gives Apple's file exactly, and a changed message is not
     absorbed by it.
  4. **Record 65 went in afterwards**: in Apple's file records 66-81
     carry record 64's leftovers, which a chain through "Too many .PROCS
     and/or .FUNCS" could not leave. Writing it in the loop instead is
     caught.
  5. **The kept sources are the sources in the tree.**
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from a2pascal.disk import PascalDisk
from oscmp import DISKS_13

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "acceptance" / "2026-09-13-asm-data"
PROGS = ROOT / "src" / "pascal" / "programs" / "1.3"
SOURCES = {
    "OPS6502.TEXT": ROOT / "src" / "data" / "OPS6502.TEXT",
    "ERRS6502.TEXT": ROOT / "src" / "data" / "ERRS6502.TEXT",
    "MAKEOPS.text": PROGS / "MAKEOPS.text",
    "MAKEERRS.text": PROGS / "MAKEERRS.text",
}
REC = 42
PATCHED = 65

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


def lf(p: Path) -> bytes:
    return p.read_bytes().replace(b"\r\n", b"\n")


def first_fill(lengths: list[int]) -> set[int]:
    """File offsets whose byte is still the window's first fill.

    Record k writes window bytes 0..lengths[k]; a byte no record has yet
    written keeps the fill. Record 65 is taken at its placeholder length,
    since it was read back and rewritten rather than chained."""
    written = [False] * REC
    out = set()
    for k, n in enumerate(lengths):
        for j in range(n + 1):
            written[j] = True
        out.update(k * REC + j for j in range(REC) if not written[j])
    return out


def differing(a: bytes, b: bytes) -> set[int]:
    return {i for i in range(max(len(a), len(b)))
            if i >= len(a) or i >= len(b) or a[i] != b[i]}


def main() -> int:
    missing = [n for n in ["OPCODES.DATA", "ERRORS.DATA", "MAKEOPS.CODE",
                           "MAKEERRS.CODE", *SOURCES] if not (RUN / n).exists()]
    if missing:
        print(f"missing from {RUN.name}: {missing}")
        return 1

    print("=== 6502.OPCODES ===")
    apple = shipped("6502.OPCODES")
    ours = (RUN / "OPCODES.DATA").read_bytes()
    check(len(apple) == 1024 and ours == apple,
          f"all {len(apple)} bytes identical, the tail past 720 included")
    mutant = bytearray(ours)
    mutant[12 * 30 + 8] ^= 1
    check(differing(apple, bytes(mutant)) == {12 * 30 + 8},
          "a flipped opcode value is caught")
    check(ours[:12] == bytes(8) + b"\x01\x00\x00\x00"
          and ours[720:] == bytes(304),
          "record 0 is the byte-sex mark; 59 records follow, then zeros")

    print("=== 6502.ERRORS ===")
    apple = shipped("6502.ERRORS")
    ours = (RUN / "ERRORS.DATA").read_bytes()
    count = 3570 // REC
    lengths = [apple[k * REC] for k in range(count)]
    check(len(apple) == len(ours) == 3584 and count == 85
          and [ours[k * REC] for k in range(count)] == lengths
          and lengths[-1] == 0 and apple[3570:] == ours[3570:] == bytes(14),
          "85 records with Apple's lengths, the last empty, zeros after")
    placeholder = lengths.copy()
    placeholder[PATCHED] = 1
    fill = first_fill(placeholder)
    diff = differing(apple, ours)
    check(diff == fill and len(diff) == 287,
          f"{len(diff)} bytes differ, and they are the {len(fill)} "
          "that still hold the window's first fill")
    substituted = bytearray(ours)
    for p in fill:
        substituted[p] = apple[p % REC]
    check(bytes(substituted) == apple,
          "ours with Apple's 40 fill bytes is Apple's file")
    mutant = bytearray(ours)
    mutant[10 * REC + 3] ^= 1
    check(not differing(apple, bytes(mutant)) <= fill,
          "a changed message character is not absorbed by the fill")
    print(f"       our first fill: {ours[2:REC]!r}")

    print("=== record 65 was rewritten in place ===")
    # Record 65's 29 characters would have covered bytes 1-29 of the
    # window; those are where 64's text shows through instead.
    check(all(apple[k * REC + 2:k * REC + 30]
              == apple[64 * REC + 2:64 * REC + 30]
              != apple[65 * REC + 2:65 * REC + 30] for k in range(66, 76)),
          "records 66-75 show record 64's text in bytes 2-29, not 65's")
    # Rebuild the whole file from its messages and Apple's fill, the way
    # MAKEERRS writes it and the way a single loop would.
    def simulate(patch: bool) -> bytes:
        window = bytearray(apple[:REC])
        out = bytearray()
        for k in range(count):
            n = 1 if (patch and k == PATCHED) else lengths[k]
            src = b"\x01 " if (patch and k == PATCHED) else \
                apple[k * REC:k * REC + n + 1]
            window[:n + 1] = src
            out += window
        if patch:
            rec = bytearray(out[PATCHED * REC:(PATCHED + 1) * REC])
            n = lengths[PATCHED]
            rec[:n + 1] = apple[PATCHED * REC:PATCHED * REC + n + 1]
            out[PATCHED * REC:(PATCHED + 1) * REC] = rec
        return bytes(out) + bytes(3584 - len(out))
    check(simulate(True) == apple,
          "85 messages written through one window, 65 rewritten after, "
          "is Apple's file")
    check(simulate(False) != apple,
          "the same with 65 written in the loop is not")

    print("=== the kept sources are the sources in the tree ===")
    for name, path in SOURCES.items():
        check(lf(RUN / name) == lf(path),
              f"{name} equals {path.relative_to(ROOT)}")

    print()
    if fail:
        print(f"asm data: {len(fail)} check(s) failed")
        return 1
    print("6502.OPCODES identical; 6502.ERRORS all but its window's "
          "first fill, 3297 of 3584")
    print("asm-data-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
