"""Probe a .dsk for the sector ordering that yields a Pascal volume directory."""
import sys, struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PASCAL_TO_DOS = [0, 13, 11, 9, 7, 5, 3, 1, 14, 12, 10, 8, 6, 4, 2, 15]
IDENT = list(range(16))
DOS_TO_PASCAL = [PASCAL_TO_DOS.index(i) for i in range(16)]

ORDERS = {"dos": PASCAL_TO_DOS, "prodos": IDENT, "dos_inv": DOS_TO_PASCAL}


def read_block(data, m, n):
    track, half = divmod(n, 8)
    out = b""
    for logical in (half * 2, half * 2 + 1):
        off = (track * 16 + m[logical]) * 256
        out += data[off:off + 256]
    return out


for img in sorted((ROOT / "evidence" / "disks").glob("*.dsk")):
    data = img.read_bytes()
    print("==", img.name)
    for name, m in ORDERS.items():
        blk = read_block(data, m, 2)
        first, last, kind, namelen = struct.unpack_from("<HHHB", blk, 0)
        vname = blk[7:7 + min(namelen, 7)]
        print(f"  {name:<8} first={first} last={last} kind={kind} namelen={namelen} "
              f"name={vname!r} head={blk[:24].hex(' ')}")
    print()
