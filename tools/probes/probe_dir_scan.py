"""Scan a raw .dsk for a UCSD Pascal volume-directory header, in any sector order."""
import re, sys, struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

for img in sorted((ROOT / "evidence" / "disks").glob("*.dsk")):
    data = img.read_bytes()
    print("==", img.name, len(data))
    # Volume entry: firstblk=0, lastblk=6, kind=0, namelen 1..7, then name.
    for m in re.finditer(rb"\x00\x00\x06\x00\x00\x00[\x01-\x07]", data):
        off = m.start()
        namelen = data[off + 6]
        name = data[off + 7:off + 7 + namelen]
        if not all(32 <= c < 127 for c in name):
            continue
        total, nfiles = struct.unpack_from("<HH", data, off + 14)
        sector = off // 256
        print(f"  off=0x{off:05X} sector={sector} (trk {sector//16} sec {sector%16} off {off%256}) "
              f"name={name.decode()} blocks={total} files={nfiles}")
    # Also look for plain volume-name-ish strings
    for m in re.finditer(rb"APPLE[0-9]", data):
        print(f"     APPLEn at 0x{m.start():05X}")
    print()
