"""128K.APPLE: identical, from three assemblies joined on the 1.3 system.

acceptance/2026-09-13-128k-apple holds the run: INTERP, TOP and BANK1
assembled by SYSTEM.ASSMBLER from src/native/interp/, MAKEINTP compiled by
SYSTEM.COMPILER and run under the 1.3 system, and the INTERP.DATA it wrote
(finding 279).

Claims, each of which the binary can fail:

  1. **All 16384 bytes are Apple's**; a flipped byte is caught.
  2. **The file is three codefiles' blocks**: INTERP.CODE's blocks 1-23
     are file blocks 0-22, TOP.CODE's block 1 is block 23, BANK1.CODE's
     blocks 1-8 are blocks 24-31.
  3. **Where the trailers are says how it was cut**: Apple's file holds
     exactly one assembler trailer, INTERP's, ending on block 23. TOP's
     code is exactly 512 bytes and BANK1's exactly 4096, so their trailers
     fall in the next block, which the file does not have.
  4. **The load map is the boot's**: BOOTII.TEXT loads 48 sectors into
     bank 2 at D000 and then 16 more into bank 1 from 24 blocks on, and
     jumps through FFF8, which holds FEEC, a TOP entry.
  5. **The dispatch table at bank 1 D000**: 141 words, the 107 below E000
     bank 1 handlers and the other 34 in common code, as the hints say.
  6. **The sources are the generator's**: tools/absdis.py with
     src/native/interp/128K.hints writes the three sources in the tree
     byte for byte, and the kept ones equal them.

What it cannot check: an absolute assembly has no relocation, so a label
and a constant, or code and .BYTE, give the same bytes. The trace's
reading of the code is not tested here.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from a2pascal.disk import PascalDisk
from oscmp import DISKS_13

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "acceptance" / "2026-09-13-128k-apple"
INTERP = ROOT / "src" / "native" / "interp"
SOURCES = {
    "INTERP.TEXT": INTERP / "INTERP.TEXT",
    "TOP.TEXT": INTERP / "TOP.TEXT",
    "BANK1.TEXT": INTERP / "BANK1.TEXT",
    "MAKEINTP.text": ROOT / "src" / "pascal" / "programs" / "1.3" / "MAKEINTP.text",
}
BOOT = ROOT / "src" / "native" / "BOOTII.TEXT"
B = 512

fail = []


def check(ok: bool, label: str) -> None:
    print(("  ok   " if ok else "  FAIL ") + label)
    if not ok:
        fail.append(label)


def shipped(name: str) -> bytes:
    for fname in DISKS_13:
        d = PascalDisk.from_file(ROOT / "evidence" / "disks" / fname)
        for e in d.directory():
            if e.name == name:
                return bytes(d.read_blocks(e.first_block, e.blocks))
    raise SystemExit(f"{name} is on none of the 1.3 disks")


def lf(p: Path) -> bytes:
    return p.read_bytes().replace(b"\r\n", b"\n")


def trailers(b: bytes) -> list[int]:
    """Offsets of `01 01` ending an .ABSOLUTE trailer: eight zero bytes of
    relocation tables, a self-relative word, then `00 00 02 00 01 01`."""
    return [i for i in range(14, len(b) - 1)
            if b[i:i + 2] == b"\x01\x01" and b[i - 14:i - 6] == bytes(8)
            and b[i - 4:i] == b"\x00\x00\x02\x00"]


def main() -> int:
    missing = [n for n in ["INTERP.DATA", "INTERP.CODE", "TOP.CODE",
                           "BANK1.CODE", "MAKEINTP.CODE", *SOURCES]
               if not (RUN / n).exists()]
    if missing:
        print(f"missing from {RUN.name}: {missing}")
        return 1
    apple = shipped("128K.APPLE")
    ours = (RUN / "INTERP.DATA").read_bytes()
    interp = (RUN / "INTERP.CODE").read_bytes()
    top = (RUN / "TOP.CODE").read_bytes()
    bank1 = (RUN / "BANK1.CODE").read_bytes()

    print("=== 128K.APPLE against Apple's ===")
    check(len(apple) == len(ours) == 16384 and ours == apple,
          "all 16384 bytes identical")
    mutant = bytearray(ours)
    mutant[0x3000] ^= 1
    check([i for i in range(16384) if mutant[i] != apple[i]] == [0x3000],
          "a flipped byte in the dispatch table is caught")

    print("=== the file is three codefiles' blocks ===")
    check(interp[B:B + 23 * B] == apple[:23 * B],
          "INTERP.CODE blocks 1-23 are blocks 0-22")
    check(top[B:2 * B] == apple[23 * B:24 * B], "TOP.CODE block 1 is block 23")
    check(bank1[B:9 * B] == apple[24 * B:32 * B],
          "BANK1.CODE blocks 1-8 are blocks 24-31")

    print("=== where the trailers are ===")
    check(trailers(apple) == [23 * B - 2],
          "Apple's file has one trailer, ending on block 23")
    w = lambda b, o: b[o] | b[o + 1] << 8
    check(w(apple, 23 * B - 8) == 23 * B - 8,
          "its self-relative word is its own offset: INTERP starts the file")
    check(trailers(top[B:]) == [B + 14] and top[2 * B:2 * B + 8] == bytes(8),
          "TOP's trailer opens block 2: its code is exactly 512 bytes")
    check(trailers(bank1[B:]) == [8 * B + 14]
          and bank1[9 * B:9 * B + 8] == bytes(8),
          "BANK1's trailer opens block 9: its code is exactly 4096 bytes")

    print("=== the load map is the boot's ===")
    boot = lf(BOOT).decode("ascii")
    check(all(s in boot for s in (
        "LDA  0C081", "LDA  #0D0", "LDA  #30", "LDA  0C089", "ADC  #18",
        "LDA  #10", "JMP  @0FFF8", "L0939   .BYTE 41,50,50,4C,45,20,0C,53")),
        "BOOTII loads 48 sectors via C081, then 16 via C089 from block +24, "
        "and jumps through FFF8")
    check(w(apple, 0xFFF8 - 0xD000) == 0xFEEC
          and all(w(apple, v - 0xD000) == 0xFEE6 for v in (0xFFFA, 0xFFFC, 0xFFFE)),
          "FFF8 holds FEEC; NMI, RESET and IRQ all FEE6")

    print("=== the dispatch table ===")
    table = [w(apple, 0x3000 + 2 * k) for k in range(141)]
    check(sum(1 for t in table if 0xD000 <= t < 0xE000) == 107
          and sum(1 for t in table if 0xE000 <= t < 0xFE00) == 34
          and not 0xD000 <= w(apple, 0x3000 + 282) < 0xFE00,
          "141 words: 107 into bank 1, 34 into common code, then not an address")

    print("=== the sources are the generator's ===")
    with tempfile.TemporaryDirectory() as tmp:
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "absdis.py"),
                            str(INTERP / "128K.hints"), "--out-dir", tmp],
                           capture_output=True, text=True)
        check(r.returncode == 0, "absdis.py runs")
        for n in ("INTERP.TEXT", "TOP.TEXT", "BANK1.TEXT"):
            gen = Path(tmp) / "src" / "native" / "interp" / n
            check(gen.exists() and lf(gen) == lf(INTERP / n),
                  f"absdis.py writes src/native/interp/{n}")
    for name, path in SOURCES.items():
        check(lf(RUN / name) == lf(path),
              f"{name} equals {path.relative_to(ROOT)}")

    print()
    if fail:
        print(f"128k apple: {len(fail)} check(s) failed")
        return 1
    print("128K.APPLE: all 16384 bytes, by Apple's assembler, compiler and system")
    print("128k-apple-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
