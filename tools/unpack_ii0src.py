"""Unpack ii0src.sdk (NuFX/ShrinkIt) to a raw disk image and verify it."""
import sys, struct
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from a2pascal.nufx import NuFX, expand_lzw1

ROOT = Path(__file__).resolve().parent.parent
src = ROOT / "evidence" / "disks" / "ii0src.sdk"
arc = NuFX(src.read_bytes())

for rec in arc.records:
    print(f"record {rec.name!r} storage_type={rec.storage_type} "
          f"extra_type={rec.extra_type} -> {rec.storage_type * rec.extra_type} bytes")
    for t in rec.threads:
        print(f"  thread class={t.cls} kind={t.kind} fmt={t.fmt} eof={t.eof} len={t.comp_len}")
    disk = [t for t in rec.threads if t.cls == "data"][0]
    total = rec.storage_type * rec.extra_type
    raw, crc, volume, esc, consumed = expand_lzw1(arc.thread_bytes(disk), total)
    print(f"  lzw1: crc=0x{crc:04X} volume={volume} rle_esc=0x{esc:02X} "
          f"consumed={consumed}/{disk.comp_len} produced={len(raw)}/{total}")

    out = ROOT / "build" / "ii0src.po"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(raw)
    print(f"  wrote {out}")

    # sanity: does it look like a UCSD Pascal volume? (block 2 = directory)
    blk2 = raw[2 * 512:3 * 512]
    first, last, kind, namelen = struct.unpack_from("<HHHB", blk2, 0)
    name = blk2[7:7 + min(namelen, 7)]
    print(f"  block2: first={first} last={last} kind={kind} namelen={namelen} name={name!r}")
