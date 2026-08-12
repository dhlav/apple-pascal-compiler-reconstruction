"""With LZW fixed, measure what the chunk-header length word actually counts.

Historical: this decodes past a chunk boundary without resetting the LZW
table, and so RAISES by design. That failure is what established that this
archive resets the string table at the start of every chunk (finding 8).
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
esc = data[3]

lzw = _LZW1()
br = _BitReader(data[7:])
rle_len = struct.unpack_from("<H", data, 4)[0]
print(f"chunk 0 header: rle_len={rle_len} flag={data[6]}")

# decode plenty, then see where 4096 output bytes land
raw = lzw.decode_chunk(br, 8000)
img = _rle_expand(raw, esc, 4096)
print(f"decoded {len(raw)} pre-RLE bytes -> {len(img)} post-RLE (capped at 4096)")
for n in range(1, len(raw) + 1):
    if len(_rle_expand(raw[:n], esc, 1 << 20)) >= 4096:
        print(f"  exactly {n} pre-RLE bytes yield >=4096 post-RLE "
              f"({len(_rle_expand(raw[:n], esc, 1 << 20))})")
        break
print(f"  header said {rle_len}; escapes in first {rle_len} bytes: {raw[:rle_len].count(esc)}")
print(f"  escapes in first {n} bytes: {raw[:n].count(esc)}")
