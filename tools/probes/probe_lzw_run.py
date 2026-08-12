"""Instrumented single-chunk trace of the LZW/1 expander.

Historical: like probe_lzw_chunks2, it does not reset the LZW table between
chunks and so RAISES by design at chunk 2.
"""
import sys, struct
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.nufx import NuFX, _BitReader, _LZW1, _rle_expand

ROOT = Path(__file__).resolve().parents[2]
arc = NuFX((ROOT / "evidence" / "disks" / "ii0src.sdk").read_bytes())
rec = arc.records[0]
t = [x for x in rec.threads if x.cls == "data"][0]
data = arc.thread_bytes(t)

crc, volume, esc = struct.unpack_from("<HBB", data, 0)
print(f"crc=0x{crc:04X} vol={volume} esc=0x{esc:02X}")

lzw = _LZW1()
p = 4
for c in range(6):
    rle_len, flag = struct.unpack_from("<HB", data, p)
    p += 3
    print(f"chunk {c}: at 0x{p - 3:X} rle_len={rle_len} lzw={flag}")
    if flag:
        br = _BitReader(data[p:])
        rle = lzw.decode_chunk(br, rle_len)
        print(f"   lzw produced {len(rle)} bytes, consumed {br.pos}, "
              f"table next={lzw.next_code} width={lzw.width}")
        p += br.pos
    else:
        rle = data[p:p + rle_len]
        p += rle_len
    out = _rle_expand(rle, esc, 4096)
    print(f"   rle -> {len(out)} bytes: {out[:32].hex(' ')}")
