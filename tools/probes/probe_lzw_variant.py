"""Find the exact ShrinkIt LZW/1 variant.

Ground truth: the first 4096 bytes of the image are disk blocks 0-7, and
block 2 (offset 0x400) is the UCSD volume directory, which must begin
00 00 06 00 00 00 <namelen 1..7> <ASCII name>.
"""
import sys, struct, itertools
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.nufx import NuFX, _BitReader

ROOT = Path(__file__).resolve().parents[2]
arc = NuFX((ROOT / "evidence" / "disks" / "ii0src.sdk").read_bytes())
rec = arc.records[0]
t = [x for x in rec.threads if x.cls == "data"][0]
data = arc.thread_bytes(t)
esc = data[3]
payload = data[7:]          # skip 4-byte thread header + 3-byte chunk header


def lzw(payload, want, first_code, early, maxbits=12):
    prefix = [0] * 0x1000
    suffix = [0] * 0x1000
    nxt, width = first_code, 9
    br = _BitReader(payload)
    out = bytearray()
    old, first = None, 0

    def expand(c):
        s = bytearray()
        guard = 0
        while c >= 0x100:
            if guard > 0x1000:
                return None
            s.append(suffix[c]); c = prefix[c]; guard += 1
        s.append(c); s.reverse()
        return bytes(s)

    while len(out) < want:
        code = br.read(width)
        if code is None:
            break
        if code < nxt or old is None:
            s = expand(code)
        else:
            s = expand(old)
            if s is None:
                break
            s = s + bytes([first])
        if s is None:
            break
        first = s[0]
        out += s
        if old is not None and nxt < 0x1000:
            prefix[nxt], suffix[nxt] = old, first
            nxt += 1
            limit = (1 << width) - 1 if early else (1 << width)
            if nxt >= limit and width < maxbits:
                width += 1
        old = code
    return bytes(out), br.pos


def rle(d, esc, want):
    out = bytearray(); i = 0
    while i < len(d) - 2 and len(out) < want:
        if d[i] == esc:
            out += bytes([d[i + 1]]) * (d[i + 2] + 1); i += 3
        else:
            out.append(d[i]); i += 1
    return bytes(out)


print(f"{'first':>5} {'early':>5}  dir@0x400 bytes                       verdict")
for first_code, early in itertools.product((0x100, 0x101), (False, True)):
    raw, used = lzw(payload, 6000, first_code, early)
    img = rle(raw, esc, 4096)
    d = img[0x400:0x410]
    okhdr = d[:6] == b"\x00\x00\x06\x00\x00\x00" and 1 <= d[6] <= 7
    print(f"{first_code:>5X} {str(early):>5}  {d.hex(' ')}  "
          f"{'*** MATCH ' + repr(bytes(d[7:7 + d[6]])) if okhdr else 'no'}")
