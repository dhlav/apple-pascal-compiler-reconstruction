"""128K.PASCAL: the whole file, but for three slack tails of another tool's.

acceptance/2026-09-14-128k-pascal holds the run: MAKEOS compiled by
SYSTEM.COMPILER and run under the 1.3 system, reading the compile kept in
2026-09-14-pascalsystem-intrinsic, and the 128K.PASCAL it wrote
(finding 284).

Claims, each of which the binary can fail:

  1. **Every byte outside three slack tails is Apple's**: the tails after
     slot 0's piece, slot 15's piece and slot 1 are the only bytes that
     differ. Those tails are measured from Apple's own dictionary, not
     listed by hand, and a flipped byte anywhere else is caught.
  2. **Those tails were another tool's memory** (finding 282d): slot 0's
     is INITIALI's bytes 2866-2963, and slot 1's holds unit names. So no
     source could reproduce them.
  3. **The input is the kept compile**: MAKEOS's input is the probed run,
     and the file size and block map follow from it.
  4. **MAKEOS does what finding 284 says**: a host rendering of the same
     steps turns the kept compile into the kept output byte for byte. The
     same rendering with a crossing-pointer top one byte off does not.
  5. **The kept source is the tree's.**
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from oscmp import shipped_codefile

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "acceptance" / "2026-09-14-128k-pascal"
COMPILE = (ROOT / "acceptance" / "2026-09-14-pascalsystem-intrinsic"
           / "PASCALSY.CODE")
SOURCE = ROOT / "src" / "pascal" / "programs" / "1.3" / "MAKEOS.text"
B = 512
NOTICE = (b"COPYRIGHT 1979,1980,1983-1985 "
          b"APPLE COMPUTER, INC. ALL RIGHTS RESERVED")

fail = []


def check(ok: bool, label: str) -> None:
    print(("  ok   " if ok else "  FAIL ") + label)
    if not ok:
        fail.append(label)


def w(b: bytes, o: int) -> int:
    return struct.unpack_from("<H", b, o)[0]


def blocks(n: int) -> int:
    return (n + B - 1) // B


def finish(src: bytes, top0=0xFDFC, top15=0xC000, capacity=1453) -> bytes:
    """MAKEOS's steps, on the host."""
    addr, length = w(src, 0), w(src, 2)
    seg = src[addr * B:addr * B + length]
    n = seg[length - 1]
    jtab = {i: (length - 2 - 2 * i) - w(seg, length - 2 - 2 * i)
            for i in range(1, n + 1)}
    start = {i: max([jtab[j] + 2 for j in jtab if jtab[j] < jtab[i]],
                    default=0) for i in jtab}
    total, p0, p15, new, in0 = 2 + 2 * n, bytearray(), bytearray(), {}, set()
    for i in range(1, n + 1):
        body = seg[start[i]:jtab[i] + 2]
        if total + len(body) <= capacity:
            total += len(body)
            in0.add(i)
            p0 += body
            new[i] = len(p0) - 2
        else:
            p15 += body
            new[i] = len(p15) - 2
    p0 += bytes(2 + 2 * n)
    len0, len15 = len(p0), len(p15)
    shift = (top0 - top15) - len0 + len15
    for i in range(1, n + 1):
        at = len0 - 2 - 2 * i
        v = at - new[i] + (0 if i in in0 else shift)
        struct.pack_into("<H", p0, at, v & 0xFFFF)
    p0[len0 - 2:len0] = seg[length - 2:length]

    dic = bytearray(B)
    dic[0x40:0xC0] = src[0x40:0xC0]
    out = bytearray(B)
    for slot, piece in ((0, p0), (15, p15)):
        struct.pack_into("<HH", dic, 4 * slot, len(out) // B, len(piece))
        out += piece + bytes(blocks(len(piece)) * B - len(piece))
    dic[0xC0:0xC2] = src[0xC0:0xC2]
    dic[0x100:0x102] = src[0x100:0x102]
    used = 0
    for s in range(1, 16):
        a, ln = w(src, 4 * s), w(src, 4 * s + 2)
        if not ln:
            continue
        struct.pack_into("<HH", dic, 4 * s, len(out) // B, ln)
        out += src[a * B:(a + blocks(ln)) * B]
        dic[0xC0 + 2 * s:0xC2 + 2 * s] = src[0xC0 + 2 * s:0xC2 + 2 * s]
        dic[0x100 + 2 * s:0x102 + 2 * s] = src[0x100 + 2 * s:0x102 + 2 * s]
        if w(src, 0xC0 + 2 * s) == 6:
            used += 1 << src[0x100 + 2 * s]
    struct.pack_into("<H", dic, 0x120, used)
    dic[0x1B0] = len(NOTICE)
    dic[0x1B1:0x1B1 + len(NOTICE)] = NOTICE
    out[0:B] = dic
    return bytes(out)


def tails(data: bytes) -> list[tuple[int, int, int]]:
    """(slot, first byte, end) of the slack after slots 0, 15 and 1."""
    out = []
    for slot in (0, 15, 1):
        a, ln = w(data, 4 * slot), w(data, 4 * slot + 2)
        out.append((slot, a * B + ln, (a + blocks(ln)) * B))
    return out


def main() -> int:
    apple = shipped_codefile().data
    ours = (RUN / "128K.PASCAL").read_bytes()
    src = COMPILE.read_bytes()

    print("=== the whole file ===")
    check(len(ours) == len(apple) == 45 * B,
          f"45 blocks both: {len(ours)} and {len(apple)}")
    t = tails(apple)
    inside = lambda i: any(lo <= i < hi for _, lo, hi in t)
    diff = [i for i in range(len(apple)) if ours[i] != apple[i]]
    outside = [i for i in diff if not inside(i)]
    span = sum(hi - lo for _, lo, hi in t)
    check(not outside, f"no byte differs outside the three tails: "
          f"{outside[:8]}")
    check(len(diff) == 571 and span == 594,
          f"{len(apple) - len(diff)} of {len(apple)} bytes identical; the "
          f"{len(diff)} that differ lie in {span} bytes of tail {t}")
    mutant = bytearray(ours)
    mutant[0x1B5] ^= 1                              # inside the notice
    check(any(mutant[i] != apple[i] and not inside(i)
              for i in range(len(apple))), "a flipped notice byte is caught")

    print("=== those tails were another tool's memory ===")
    (_, lo0, hi0), _, (_, lo1, hi1) = t
    initiali = next(s for s in shipped_codefile().segments
                    if s.name == "INITIALI").data
    check(apple[lo0:hi0] == initiali[2866:2866 + (hi0 - lo0)],
          "slot 0's tail is INITIALI's bytes 2866 onward")
    check(b"SYSTERM" in apple[lo1:hi1] and b"REMOUT" in apple[lo1:hi1],
          "slot 1's tail holds unit names")

    print("=== the input is the kept compile ===")
    check(w(src, 2) == 6518 and w(ours, 2) + w(ours, 62) == 6518,
          f"slot 0's 6518 bytes become {w(ours, 2)} + {w(ours, 62)}; the "
          f"118-byte dictionary moves with slot 0")
    for s in range(1, 7):
        a, ln = w(src, 4 * s), w(src, 4 * s + 2)
        b0 = w(ours, 4 * s)
        check(ours[b0 * B:(b0 + blocks(ln)) * B] == src[a * B:(a + blocks(ln))
                                                        * B],
              f"slot {s}: {blocks(ln)} blocks copied whole from the compile")

    print("=== MAKEOS's steps, rendered on the host ===")
    check(finish(src) == ours, "the host rendering equals the kept output")
    check(all(finish(src, capacity=c) == ours for c in (1438, 1457)),
          "capacities 1438 and 1457 give the same file")
    check(finish(src, capacity=1437) != ours
          and finish(src, capacity=1458) != ours,
          "1437 and 1458 do not")
    check(finish(src, top0=0xFDFD) != ours,
          "a slot 0 top one byte off does not")

    print("=== the kept source is the tree's ===")
    kept = (RUN / "MAKEOS.text").read_bytes().replace(b"\r\n", b"\n")
    tree = SOURCE.read_bytes().replace(b"\r\n", b"\n")
    check(kept == tree, "MAKEOS.text")

    print()
    if fail:
        print(f"128K.PASCAL: {len(fail)} check(s) failed")
        return 1
    print(f"128K.PASCAL: {len(apple) - len(diff)} of {len(apple)} bytes, "
          f"the rest another tool's slack")
    print("128k-pascal-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
