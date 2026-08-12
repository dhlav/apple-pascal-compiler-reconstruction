"""Raw bytes around the $D0 / $D7 sites.

Char codes are all < $80, i.e. all decode as one-byte SLDC, so a
variable-length instruction whose payload is text would keep the stream in
sync while being decoded as a run of SLDCs. Look at the actual bytes.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile

ROOT = Path(__file__).resolve().parents[2]
disk = PascalDisk.from_file(ROOT / "evidence" / "disks" /
                            "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk")
e = disk.find("SYSTEM.COMPILER")
cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))


def dump(segname, lo, hi):
    seg = cf.segment(segname)
    d = seg.data[lo:hi]
    txt = "".join(chr(c) if 32 <= c < 127 else "." for c in d)
    print(f"{segname} ${lo:04X}..${hi:04X}")
    print("  " + d.hex(" "))
    print("  |" + txt + "|")


print("=== $D0 sites (COMPINIT.3 builds something with 8-char payloads)")
dump("COMPINIT", 0x0104, 0x0140)
dump("COMPINIT", 0x0150, 0x0180)
print()
print("=== $D7 sites next to LSA strings")
dump("PASCALCO", 0x0080, 0x00C0)
dump("COMPINIT", 0x0A68, 0x0AB0)
