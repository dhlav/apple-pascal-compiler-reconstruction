"""Extract the reserved-word table embedded in 1.3's native IDSEARCH.

Disassembling PASCALCO.2 turned up a block of plain ASCII in the middle of
the code. It is the compiler's reserved-word table, and in front of it sits
a 26-entry index -- one slot per initial letter.

Hypothesis under test:

  index[0..25]   little-endian offsets from the procedure's start ($11F2),
                 one per letter A..Z; letters with no reserved word all
                 point at the same empty slot.
  each list      a one-byte count, then that many entries.
  each entry     ten bytes: the name padded to eight with spaces, then the
                 symbol class the scanner returns and an operator sub-code.

Every part of that is falsifiable. The count for each letter must equal the
number of Pascal reserved words starting with it; the seven letters with no
reserved word (H J K Q X Y Z) must share one pointer; the names recovered
must be exactly the reserved words of UCSD Pascal and nothing else; and the
lists must tile the region without gaps or overlaps.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile

ROOT = Path(__file__).resolve().parents[2]
IMG = ROOT / "evidence" / "disks" / \
    "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk"

d = PascalDisk.from_file(IMG)
e = d.find("SYSTEM.COMPILER")
seg = CodeFile(d.read_blocks(e.first_block, e.blocks)).segments[0]
data = seg.data

BASE = 0x11F2          # PASCALCO.2 enter_ic
INDEX = 0x12E0         # start of the 26-entry index
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

ptr = [int.from_bytes(data[INDEX + 2 * i:INDEX + 2 * i + 2], "little")
       for i in range(26)]

print("index (offset from $11F2 -> absolute):")
for i, p in enumerate(ptr):
    print(f"  {LETTERS[i]}  ${p:04X} -> ${BASE + p:04X}   count byte "
          f"${data[BASE + p]:02X}")

empty = [LETTERS[i] for i, p in enumerate(ptr) if p == ptr[7]]
print(f"\nletters sharing the H pointer: {''.join(empty)}")

print("\nparse:")
words = {}
spans = []
for i, p in enumerate(ptr):
    if LETTERS[i] in empty:
        continue
    a = BASE + p
    n = data[a]
    a += 1
    got = []
    for _ in range(n):
        name = data[a:a + 8].decode("ascii", "replace").rstrip()
        sy, op = data[a + 8], data[a + 9]
        a += 10
        got.append((name, sy, op))
        words[name] = (sy, op)
    spans.append((BASE + p, a, LETTERS[i]))
    print(f"  {LETTERS[i]} ({n}): " +
          ", ".join(f"{w}=${s:02X}/{o:02X}" for w, s, o in got))

# The lists must tile the region with no gaps and no overlaps.
spans.sort()
print("\ntiling:")
gaps = 0
for (s1, e1, l1), (s2, _, l2) in zip(spans, spans[1:]):
    if e1 != s2:
        gaps += 1
        print(f"  {l1} ends ${e1:04X} but {l2} starts ${s2:04X}"
              f"   ({s2 - e1:+d})")
print(f"  {len(spans)} lists, ${spans[0][0]:04X}..${spans[-1][1]:04X}, "
      f"{gaps} gaps/overlaps")

# --- the falsifiable part -------------------------------------------------
EXPECTED = {
    "AND", "ARRAY", "BEGIN", "CASE", "CONST", "DIV", "DO", "DOWNTO",
    "ELSE", "END", "EXTERNAL", "FILE", "FOR", "FORWARD", "FUNCTION",
    "GOTO", "IF", "IMPLEMENTATION", "IN", "INTERFACE", "LABEL", "MOD",
    "NOT", "OF", "OR", "OTHERWISE", "PACKED", "PROCEDURE", "PROGRAM",
    "RECORD", "REPEAT", "SEGMENT", "SET", "THEN", "TO", "TYPE", "UNIT",
    "UNTIL", "USES", "VAR", "WHILE", "WITH",
}
got = set(words)
print(f"\n{len(got)} names recovered")
missing = EXPECTED - got
extra = got - EXPECTED
# Names are truncated to 8 characters in the table, so match on that.
trunc = {w[:8] for w in EXPECTED}
really_extra = {w for w in extra if w[:8] not in trunc}
really_missing = {w for w in missing if w[:8] not in {g[:8] for g in got}}
print(f"  not found: {sorted(really_missing) or 'none'}")
print(f"  unexpected: {sorted(really_extra) or 'none'}")
