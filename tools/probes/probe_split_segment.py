"""The operating system's segment 0 is stored in two pieces (finding 50).

`PASCALSY` occupies dictionary slot 0 *and* an unnamed slot 15. There is one
procedure dictionary, at the end of slot 0, and it covers both pieces: the
entries whose target lies in slot 15 are ordinary self-relative pointers that
resolve short by a constant, because the two pieces are far apart when the
loader places them. That constant is not fitted -- it is forced by requiring
the highest crossing pointer to land on slot 15's last word.

What makes the reading safe is that the result is over-determined. Nothing
here was tuned to make it come out; the shift is one number per file, and
every check below is a consequence:

  * all 57 / 58 / 58 procedure numbers land on a byte holding their own index;
  * the procedures tile both pieces with no gap and no overlap;
  * slot 0's leftover is exactly the 2 + 2n bytes of dictionary;
  * slot 15's leftover is exactly zero -- it ends on a JTAB and so carries no
    dictionary of its own, which is what makes it a piece and not a segment.

The controls matter as much: every other codefile across the six evidence
disks must come out unsplit and parse exactly as it did before, and a single
corrupted crossing pointer must make the join refuse rather than shift to
some other constant that happens to fit.
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile

ROOT = Path(__file__).resolve().parent.parent.parent
DISKS = ROOT / "evidence" / "disks"

# The operating system build this project targets. Apple ships two memory
# maps of the same system and they split it at different points -- which is
# the best evidence the split is a property of the build, not the source --
# but only 128K.PASCAL is a target now; the 64K SYSTEM.PASCAL and 1.1's OS
# are archived.
SPLIT = [
    ("1.3 128K.PASCAL",
     "Apple II Pascal 1.3 APPLE3_ 680-0290-A.dsk", "128K.PASCAL", 58, 16, 42),
]

# Still inside the APPLE1 image, which cannot change, and still split -- but
# archived rather than a target, so the sweep neither expects nor objects to
# its join.
ARCHIVED = {("Apple II Pascal 1.3 APPLE1_ 680-0283-A.dsk", "SYSTEM.PASCAL")}

fails = []
checks = 0


def check(cond, what):
    global checks
    checks += 1
    if not cond:
        fails.append(what)


def load(dsk, fn):
    d = PascalDisk.from_file(DISKS / dsk)
    e = d.find(fn)
    return d.read_blocks(e.first_block, e.blocks)


for label, dsk, fn, nproc, n0, n15 in SPLIT:
    seg = CodeFile(load(dsk, fn)).segments[0]
    check(seg.name == "PASCALSY", f"{label}: slot 0 is not PASCALSY")
    check(seg.is_split, f"{label}: not recognised as split")
    check(len(seg.chunks) == 2, f"{label}: {len(seg.chunks)} chunks, want 2")
    check(len(seg.procedures) == nproc,
          f"{label}: {len(seg.procedures)} procedures, want {nproc}")
    for p in seg.procedures:
        check(p.consistent, f"{label}: procedure {p.number} inconsistent")
        check(p.proc_num == p.number,
              f"{label}: procedure {p.number} numbered {p.proc_num}")
        check(seg.in_chunk(p.jtab),
              f"{label}: procedure {p.number} JTAB {p.jtab} is in the padding")

    # The pieces, low (the continuation) then high (the named slot).
    (c_at, c_len, c_slot), (o_at, o_len, o_slot) = sorted(seg.chunks)
    check(c_slot == 15 and o_slot == 0,
          f"{label}: chunks came from slots {c_slot} and {o_slot}")
    check(c_at == 0, f"{label}: continuation is not at 0")
    check(o_at >= c_len, f"{label}: the two pieces overlap")

    for name, (lo, hi), want, expect in (
            ("continuation", (c_at, c_at + c_len), n15, 0),
            ("named slot", (o_at, o_at + o_len), n0, 2 + 2 * nproc)):
        ps = sorted((p.enter_ic, p.jtab, p.number)
                    for p in seg.procedures if lo <= p.jtab < hi)
        check(len(ps) == want,
              f"{label}: {len(ps)} procedures in the {name}, want {want}")
        cur = lo
        for enter, jtab, num in ps:
            check(enter == cur,
                  f"{label}: procedure {num} starts at {enter}, "
                  f"but the previous one ended at {cur}")
            cur = jtab + 2
        # Slot 0's leftover is the dictionary; the continuation has none,
        # and that is the whole reason it is a piece rather than a segment.
        check(hi - cur == expect,
              f"{label}: {hi - cur} bytes after the last JTAB of the {name}, "
              f"want {expect}")

# Control: nothing else on the six disks is split, and every codefile still
# parses. If the join were loose enough to fire on an ordinary segment this
# is where it would show.
seen = split_elsewhere = 0
for dsk in sorted(DISKS.glob("*.dsk")):
    d = PascalDisk.from_file(dsk)
    for e in d.directory():
        try:
            cf = CodeFile(d.read_blocks(e.first_block, e.blocks))
        except Exception:
            continue                      # data files are not codefiles
        if not cf.segments or not any(s.procedures for s in cf.segments):
            continue
        seen += 1
        expect = (any(fn == e.name and dk == dsk.name
                      for _, dk, fn, *_ in SPLIT)
                  or (dsk.name, e.name) in ARCHIVED)
        for s in cf.segments:
            if s.is_split and not expect:
                split_elsewhere += 1
                fails.append(f"{dsk.name} {e.name}: segment {s.name} "
                             f"was joined but should not have been")
            check(all(p.consistent for p in s.procedures),
                  f"{dsk.name} {e.name}: segment {s.name} has "
                  f"inconsistent procedures")

# Mutation: break one crossing pointer. The shift is derived from the highest
# such pointer, so damaging any *other* one must leave that entry unable to
# find its own procedure number, and the join must then refuse outright
# rather than settle on a different constant.
for label, dsk, fn, nproc, n0, n15 in SPLIT:
    raw = bytearray(load(dsk, fn))
    blk, leng = struct.unpack_from("<HH", raw, 0)
    dict_end = blk * 512 + leng
    seg = CodeFile(bytes(raw)).segments[0]
    lo = min(p.jtab for p in seg.procedures)          # deepest in the piece
    victim = next(p.number for p in seg.procedures if p.jtab == lo)
    at = dict_end - 2 - 2 * victim
    struct.pack_into("<H", raw, at, struct.unpack_from("<H", raw, at)[0] ^ 2)
    s = CodeFile(bytes(raw)).segments[0]
    check(not s.is_split or not all(p.consistent for p in s.procedures),
          f"{label}: corrupting entry {victim} still produced a clean join")

print(f"{checks} checks, {len(fails)} failures "
      f"({seen} codefiles swept, {split_elsewhere} unexpected splits)")
for f in fails[:20]:
    print("  FAIL", f)
sys.exit(1 if fails else 0)
