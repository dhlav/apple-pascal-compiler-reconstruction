"""Hex/structure dump of block 0 (segment dictionary) of SYSTEM.COMPILER."""
import sys, struct
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk

ROOT = Path(__file__).resolve().parents[2]

for img in sorted((ROOT / "evidence" / "disks").glob("*.dsk")):
    disk = PascalDisk.from_file(img)
    e = disk.find("SYSTEM.COMPILER")
    blk = disk.read_block(e.first_block)
    print("==", img.name, f"(file blocks {e.first_block}..{e.next_block - 1})")
    for row in range(0, 512, 32):
        chunk = blk[row:row + 32]
        txt = "".join(chr(c) if 32 <= c < 127 else "." for c in chunk)
        print(f"  {row:03X}  {chunk.hex(' ')}  |{txt}|")
    print()
