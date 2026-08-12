"""Determine the UCSD procedure-dictionary / attribute-table layout empirically.

Tries both candidate attribute-table orientations against every p-code segment
of SYSTEM.COMPILER and scores them on internal consistency.
"""
import sys, struct
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk

ROOT = Path(__file__).resolve().parents[2]
img = ROOT / "evidence" / "disks" / "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk"
disk = PascalDisk.from_file(img)
e = disk.find("SYSTEM.COMPILER")
code = disk.read_blocks(e.first_block, e.blocks)


def w(b, o):
    return struct.unpack_from("<H", b, o)[0]


def segments():
    d = code[:512]
    for i in range(16):
        addr, leng = struct.unpack_from("<HH", d, i * 4)
        name = d[64 + i * 8:72 + i * 8].decode("ascii").strip()
        info = w(d, 0x100 + i * 2)
        if leng:
            yield i, name, addr, leng, info


for idx, name, addr, leng, info in segments():
    seg = code[addr * 512: addr * 512 + leng]
    tail = w(seg, leng - 2)
    nproc, segnum = tail & 0xFF, tail >> 8
    print(f"seg[{idx:2}] {name:<8} blk={addr:<3} len={leng:<6} segnum={segnum:<3} "
          f"nproc={nproc:<3} mtype={info & 0xF} ver={info >> 5} tail={seg[-16:].hex(' ')}")
print()

# Focus on COMPINIT
idx, name, addr, leng, info = [s for s in segments() if s[1] == "COMPINIT"][0]
seg = code[addr * 512: addr * 512 + leng]
nproc = w(seg, leng - 2) & 0xFF
print(f"COMPINIT: len={leng} nproc={nproc}")

print("\nprocedure dictionary (self-relative pointers, ptr at leng-2-2*i):")
jtab = {}
for i in range(1, nproc + 1):
    p = leng - 2 - 2 * i
    v = w(seg, p)
    target = p - v
    jtab[i] = target
    print(f"  proc {i:2}  ptrat=0x{p:04X} val=0x{v:04X} -> JTAB=0x{target:04X}"
          f"  {'OK' if 0 <= target < leng else 'OUT OF RANGE'}")

print("\nattribute tables, orientation A (procnum/lex at JTAB, fields below):")
for i in range(1, nproc + 1):
    j = jtab[i]
    if not (10 <= j < leng - 1):
        print(f"  proc {i:2}  JTAB out of range")
        continue
    pn, lex = seg[j], seg[j + 1]
    enter_p, exit_p = j - 2, j - 4
    enter = enter_p - w(seg, enter_p)
    exitv = exit_p - w(seg, exit_p)
    param = w(seg, j - 6)
    data = w(seg, j - 8)
    print(f"  proc {i:2}  JTAB=0x{j:04X} pn={pn:<3} lex={lex:<3} "
          f"enter=0x{enter:04X} exit=0x{exitv:04X} param={param:<5} data={data}")
