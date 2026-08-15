"""1.1's reserved-word table, in the interpreter where it actually lives.

Finding 19 established that 1.3 dropped `CSP 7`/`CSP 8` and hand-coded
`IDSEARCH` and `TREESEARCH` into `SYSTEM.COMPILER` instead. The other half
of that claim -- that in 1.1 the two routines are *in the interpreter* --
had nothing to test against, because no interpreter was in `evidence/`.
Both boot disks are now, and `SYSTEM.APPLE` is a raw 6502 image that loads
at `$D000`.

The claim under test, in three parts:

  * **1.1's `SYSTEM.APPLE` contains the reserved-word table and 1.3's does
    not.** That is a prediction finding 19 makes and cannot itself check,
    and it fails loudly either way: the table contains plain ASCII names.
  * **The table's format changed.** 1.1 stores a run of *eleven*-byte
    records -- a leading byte, `NAME[8]`, `SY`, `OP` -- where the leading
    byte carries the letter's count on the first record of a letter and 0
    on the rest. 1.3 hoists that into one count byte followed by ten-byte
    records. The layout is checked by requiring the 26-entry letter index
    to tile the table exactly under it, which an eleven-byte stride does
    and a ten-byte stride does not.
  * **The symbol codes did not change.** Every reserved word common to the
    two releases must carry identical `SY` and `OP`. This matters because
    `SYMBOL` and `OPERATOR` (finding 26) were recovered from 1.3's table
    and carried to 1.1 through the correspondence table; here 1.1's own
    binary says them independently.

And the one difference, which finding 32 predicted from the II.0 source
before either table was read this way: 1.1 has `SEPARATE` where 1.3 has
`OTHERWISE`, and **both are `SY = 54`**. 1.3 reused the code rather than
extending the enumeration, so `SYMBOL` has 55 members in both releases.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile

ROOT = Path(__file__).resolve().parents[2]
BOOT_11 = "UCSD Pascal 1.1_1.dsk"
BOOT_13 = "Apple II Pascal 1.3 APPLE1_ 680-0283-A.dsk"
PROG_13 = "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk"
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
INTERP_BASE = 0xD000          # SYSTEM.APPLE loads into the language card
# 1.3's table, already established by probe_reserved_words.py
IDX_13, SENTINEL_13, PROC_13 = 0x12E0, 0x1314, 0x11F2
EMPTY = set("HJKQXYZ")


def read(img: str, name: str) -> bytes:
    d = PascalDisk.from_file(ROOT / "evidence" / "disks" / img)
    e = d.find(name)
    return d.read_blocks(e.first_block, e.blocks)[:e.size]


def table_11(raw: bytes):
    """Parse the 1.1 interpreter's table. Returns {letter: [(name, sy, op)]}."""
    # The empty-letter sentinel is the one three-byte slot, and it sits
    # immediately before the "A" list.
    i = raw.find(b"\x00\x40\x23\x02AND     ")
    if i < 0:
        return None, None, None
    idx = i - 52                      # 26 words of index sit just below it
    ptr = [int.from_bytes(raw[idx + 2 * k:idx + 2 * k + 2], "little")
           for k in range(26)]
    bounds = sorted(set(ptr))
    end = max(ptr) + 11 * 2           # W has two entries; checked below
    out, spans = {}, []
    for k, p in enumerate(ptr):
        if p == i + INTERP_BASE:
            continue
        hi = min([x for x in bounds if x > p] + [end])
        if (hi - p) % 11:
            return None, None, None
        o, n = p - INTERP_BASE, (hi - p) // 11
        out[LETTERS[k]] = [
            (raw[o + 11 * j + 1:o + 11 * j + 9].decode("ascii", "replace"),
             raw[o + 11 * j + 9], raw[o + 11 * j + 10]) for j in range(n)]
        spans.append((p, hi, LETTERS[k]))
    return out, ptr, sorted(spans)


def table_13(seg: bytes):
    out = {}
    for k in range(26):
        off = PROC_13 + int.from_bytes(seg[IDX_13 + 2 * k:IDX_13 + 2 * k + 2],
                                       "little")
        if off == SENTINEL_13:
            continue
        n, a = seg[off], off + 1
        out[LETTERS[k]] = [
            (seg[a + 10 * j:a + 10 * j + 8].decode("ascii", "replace"),
             seg[a + 10 * j + 8], seg[a + 10 * j + 9]) for j in range(n)]
    return out


def main() -> int:
    bad, checked = [], 0

    def check(cond, msg):
        nonlocal checked
        checked += 1
        if not cond:
            bad.append(msg)

    i11 = read(BOOT_11, "SYSTEM.APPLE")
    i13 = read(BOOT_13, "SYSTEM.APPLE")
    check(len(i11) == len(i13) == 16384,
          f"interpreters are {len(i11)} and {len(i13)} bytes, expected 16384")

    # -- where the table is, and is not -----------------------------------
    marks = (b"DOWNTO  ", b"IMPLEMEN", b"INTERFAC", b"FUNCTION")
    n11 = sum(i11.count(m) for m in marks)
    n13 = sum(i13.count(m) for m in marks)
    check(n11 >= 4,
          f"1.1's SYSTEM.APPLE holds {n11} reserved-word strings; finding 19 "
          f"says IDSEARCH lives in the 1.1 interpreter")
    check(n13 == 0,
          f"1.3's SYSTEM.APPLE still holds {n13} reserved-word strings; "
          f"finding 19 says 1.3 moved IDSEARCH into SYSTEM.COMPILER")

    t11, ptr, spans = table_11(i11)
    check(t11 is not None,
          "1.1's table does not parse as 11-byte records tiled by the index")
    if t11 is None:
        print("\n".join(bad))
        return 1

    # -- the index and the tiling -----------------------------------------
    sent = i11.find(b"\x00\x40\x23\x02AND     ") + INTERP_BASE
    empty = {LETTERS[k] for k, p in enumerate(ptr) if p == sent}
    check(empty == EMPTY,
          f"letters sharing the sentinel are {sorted(empty)}, expected "
          f"{sorted(EMPTY)}")
    for (lo, hi, a), (lo2, _, b) in zip(spans, spans[1:]):
        check(hi == lo2,
              f"1.1 list {a} ends ${hi:04X} but {b} starts ${lo2:04X}")
    # An 11-byte stride is not an arbitrary choice: a 10-byte one would have
    # to divide every span too, and does not.
    tens = [a for lo, hi, a in spans if (hi - lo) % 10 == 0
            and (hi - lo) // 10 != (hi - lo) // 11]
    check(len(tens) < len(spans),
          "every 1.1 list is also a whole number of 10-byte records, so the "
          "record size is not pinned by the tiling")

    # -- 1.3's table, for comparison --------------------------------------
    d = PascalDisk.from_file(ROOT / "evidence" / "disks" / PROG_13)
    e = d.find("SYSTEM.COMPILER")
    seg = CodeFile(d.read_blocks(e.first_block, e.blocks)).segment("PASCALCO")
    t13 = table_13(seg.data)

    m11 = {n.strip(): (sy, op) for es in t11.values() for n, sy, op in es}
    m13 = {n.strip(): (sy, op) for es in t13.values() for n, sy, op in es}
    check(len(m11) == 42, f"1.1 has {len(m11)} reserved words, expected 42")
    check(len(m13) == 42, f"1.3 has {len(m13)} reserved words, expected 42")
    check(set(m11) - set(m13) == {"SEPARATE"},
          f"only in 1.1: {sorted(set(m11) - set(m13))}, expected SEPARATE")
    check(set(m13) - set(m11) == {"OTHERWIS"},
          f"only in 1.3: {sorted(set(m13) - set(m11))}, expected OTHERWIS")

    shared = sorted(set(m11) & set(m13))
    check(len(shared) == 41, f"{len(shared)} words in common, expected 41")
    disagree = [(k, m11[k], m13[k]) for k in shared if m11[k] != m13[k]]
    check(not disagree,
          f"SY/OP differ between releases for {disagree}")

    check(m11["SEPARATE"] == m13["OTHERWIS"] == (54, 0),
          f"SEPARATE is {m11['SEPARATE']} in 1.1 and OTHERWIS is "
          f"{m13['OTHERWIS']} in 1.3; finding 32 says 1.3 reused the code")

    # -- the per-letter counts agree except where the words do -------------
    for k in LETTERS:
        a, b = t11.get(k, []), t13.get(k, [])
        want = len(a) + (1 if k == "O" else 0) - (1 if k == "S" else 0)
        check(len(b) == want,
              f"letter {k}: 1.1 has {len(a)} words, 1.3 has {len(b)}, "
              f"expected {want}")

    reordered = [k for k in LETTERS
                 if {n for n, _, _ in t11.get(k, [])}
                 == {n for n, _, _ in t13.get(k, [])}
                 and [n for n, _, _ in t11.get(k, [])]
                 != [n for n, _, _ in t13.get(k, [])]]
    print(f"1.1 interpreter table at ${spans[0][0]:04X}..${spans[-1][1]:04X}, "
          f"{len(m11)} words in 11-byte records")
    print(f"1.3 compiler table, {len(m13)} words in 10-byte records; "
          f"{len(shared)} shared, 0 SY/OP disagreements")
    print(f"letters whose words are the same but reordered: "
          f"{reordered or 'none'}")

    if bad:
        print("\n".join(bad))
        return 1
    print(f"{checked} checks, all passed")
    print("interp-words-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
