"""FORMATTER.DATA: 3583 of 3584 bytes, built by Apple's own tools.

acceptance/2026-09-13-formatter-data holds the whole chain: ASMFORMAT,
BOOTII and BOOTPD assembled by SYSTEM.ASSMBLER, MAKEBOOT and MAKEFMT
compiled by SYSTEM.COMPILER and run under the 1.3 system, and the two
data files they wrote (finding 275).

Claims, each of which the binary can fail:

  1. **FORMATTER.DATA equals Apple's in every byte but $9FF**, where
     Apple's has $BB and ours $DB; a flipped code byte is caught.
  2. **Each block is the piece it is said to be**: blocks 0-2 are
     ASMFORMAT.CODE's blocks 1-3, blocks 3-4 are BOOTII.CODE's 1-2,
     block 5 is a directory header for volume BLANK, 280 blocks, dated
     7-Nov-84 and nothing else, block 6 is BOOTPD.CODE's block 1.
  3. **The Disk II boot is every 1.3 disk's boot**: blocks 0-1 of all
     three evidence disks equal Apple's blocks 3-4.
  4. **ASMFORMAT is the note's 1082 bytes**, its four relocation tables
     are empty, and the stale end of its last block repeats block 1's
     bytes $24A-$3FF -- in Apple's file and in ours.
  5. **The odd byte is the assembler's**: SYSTEM.ASSMBLER's source clears
     its code buffer with FILLCHAR(G72^, BUFLIMIT, ...) and BUFLIMIT is
     1023, so byte 1023 of the boot's two-block window is never written.
  6. **The kept sources are the sources in the tree.**
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from a2pascal.disk import PascalDisk
from oscmp import DISKS_13

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "acceptance" / "2026-09-13-formatter-data"
SOURCES = {
    "ASMFORMAT.TEXT": ROOT / "src" / "native" / "ASMFORMAT.TEXT",
    "BOOTII.TEXT": ROOT / "src" / "native" / "BOOTII.TEXT",
    "BOOTPD.TEXT": ROOT / "src" / "native" / "BOOTPD.TEXT",
    "MAKEBOOT.text": ROOT / "src" / "pascal" / "programs" / "1.3" / "MAKEBOOT.text",
    "MAKEFMT.text": ROOT / "src" / "pascal" / "programs" / "1.3" / "MAKEFMT.text",
}
ASSEMBLER = ROOT / "src" / "pascal" / "programs" / "1.3" / "ASSMBLER.text"
ODD = 0x9FF

fail = []


def check(ok: bool, label: str) -> None:
    print(("  ok   " if ok else "  FAIL ") + label)
    if not ok:
        fail.append(label)


def disks():
    for fname in DISKS_13:
        yield fname, PascalDisk.from_file(ROOT / "evidence" / "disks" / fname)


def shipped(name: str) -> bytes:
    for _, d in disks():
        try:
            e = d.find(name)
        except Exception:
            continue
        if e is not None:
            return bytes(d.read_blocks(e.first_block, e.blocks))
    raise SystemExit(f"{name} is on none of the 1.3 disks")


def lf(p: Path) -> bytes:
    return p.read_bytes().replace(b"\r\n", b"\n")


def main() -> int:
    need = ["FORMATTER.DATA", "BOOTTRACKS.DATA", "ASMFORMAT.CODE",
            "BOOTII.CODE", "BOOTPD.CODE", *SOURCES]
    missing = [n for n in need if not (RUN / n).exists()]
    if missing:
        print(f"missing from {RUN.name}: {missing}")
        return 1
    apple = shipped("FORMATTER.DATA")
    ours = (RUN / "FORMATTER.DATA").read_bytes()
    asm = (RUN / "ASMFORMAT.CODE").read_bytes()
    boot2 = (RUN / "BOOTII.CODE").read_bytes()
    bootpd = (RUN / "BOOTPD.CODE").read_bytes()
    tracks = (RUN / "BOOTTRACKS.DATA").read_bytes()

    print("=== FORMATTER.DATA against Apple's ===")
    diff = [i for i in range(max(len(apple), len(ours)))
            if i >= len(apple) or i >= len(ours) or apple[i] != ours[i]]
    check(len(apple) == len(ours) == 3584 and diff == [ODD]
          and apple[ODD] == 0xBB and ours[ODD] == 0xDB,
          f"3584 bytes, differing only at ${ODD:X} (Apple's "
          f"${apple[ODD]:02X}, ours ${ours[ODD]:02X}); {len(diff)} differ")
    mutant = bytearray(ours)
    mutant[0x100] ^= 0x01
    check([i for i in range(3584) if apple[i] != mutant[i]] == [0x100, ODD],
          "a flipped code byte is caught, at that byte")

    print("=== each block is the piece it is said to be ===")
    check(ours[0:1536] == asm[512:2048],
          "blocks 0-2 are ASMFORMAT.CODE's blocks 1-3")
    check(ours[1536:2560] == boot2[512:1536],
          "blocks 3-4 are BOOTII.CODE's blocks 1-2")
    head = bytes([0, 0, 6, 0, 0, 0, 5]) + b"BLANK" + bytes(2) + \
        bytes([0x18, 0x01, 0, 0, 0, 0, 0x7B, 0xA8])
    check(ours[2560:3072] == head + bytes(512 - len(head))
          and apple[2560:3072] == ours[2560:3072],
          "block 5 is the directory of BLANK: blocks 0-6, 280 blocks, "
          "no files, 7-Nov-84, zeros after")
    check(ours[3072:3584] == bootpd[512:1024],
          "block 6 is BOOTPD.CODE's block 1")
    check(ours[1536:] == tracks, "blocks 3-6 are BOOTTRACKS.DATA")

    print("=== the Disk II boot is every 1.3 disk's boot ===")
    for fname, d in disks():
        check(bytes(d.read_blocks(0, 2)) == apple[1536:2560],
              f"{fname}: blocks 0-1 equal Apple's FORMATTER.DATA 3-4")

    print("=== ASMFORMAT's segment ===")
    w = lambda b, o: b[o] | b[o + 1] << 8
    for who, b in (("Apple's", apple), ("ours", ours)):
        check(w(b, 0x442) == 0x442 and b[0x43A:0x442] == bytes(8)
              and b[0x448:0x44A] == b"\x01\x01",
              f"{who}: 1082 bytes of code, four empty relocation tables, "
              "segment 1 of one procedure")
        check(b[0x44A:0x600] == b[0x24A:0x400],
              f"{who}: bytes $44A-$5FF repeat block 1's $24A-$3FF")

    print("=== the odd byte is the assembler's ===")
    src = lf(ASSEMBLER).decode("ascii")
    check("BUFLIMIT = 1023;" in src
          and "FILLCHAR(G72^, BUFLIMIT, CHR(0));" in src,
          "SYSTEM.ASSMBLER clears 1023 of its 1024-byte code buffer")
    check(boot2[512 + 0x370:512 + 0x3FF] == bytes(0x8F)
          and apple[1536 + 0x370:1536 + 0x3FF] == bytes(0x8F),
          "past the boot's segment both windows are zero up to that byte")

    print("=== the kept sources are the sources in the tree ===")
    for name, path in SOURCES.items():
        check(lf(RUN / name) == lf(path), f"{name} equals {path.relative_to(ROOT)}")

    print()
    if fail:
        print(f"formatter data: {len(fail)} check(s) failed")
        return 1
    print("FORMATTER.DATA: 3583 of 3584 bytes, by Apple's assembler, "
          "compiler and system")
    print("formatter-data-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
