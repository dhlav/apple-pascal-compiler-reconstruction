"""Test which reading of the LZW/1 chunk-length word walks the thread exactly.

Result: NEITHER reading as a compressed-byte count works. That is what
established that the length word is the pre-RLE output size instead.
"""
import sys, struct
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.nufx import NuFX

ROOT = Path(__file__).resolve().parents[2]
arc = NuFX((ROOT / "evidence" / "disks" / "ii0src.sdk").read_bytes())
rec = arc.records[0]
print(f"storage_type={rec.storage_type} extra_type={rec.extra_type} "
      f"=> {rec.storage_type * rec.extra_type} bytes uncompressed")
t = [x for x in rec.threads if x.cls == "data"][0]
data = arc.thread_bytes(t)
print(f"thread len={len(data)} eof={t.eof}")
print("header:", data[:4].hex(' '))

for label, includes_header in (("len excludes 3-byte header", False),
                               ("len includes 3-byte header", True)):
    p, n, bad = 4, 0, None
    while p + 3 <= len(data):
        ln, flag = struct.unpack_from("<HB", data, p)
        if flag not in (0, 1) or ln == 0 or ln > 4096 + 64:
            bad = (n, p, ln, flag)
            break
        p += ln if includes_header else ln + 3
        n += 1
    status = "walked to end" if p == len(data) else f"stopped at {p}/{len(data)}"
    print(f"  {label}: chunks={n} {status} bad={bad}")
