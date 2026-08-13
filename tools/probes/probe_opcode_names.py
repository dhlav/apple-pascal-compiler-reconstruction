"""Diff the decoder's opcode table against the 1.4 interpreter's XFRTBL.

pcode.py's table was assembled from Hyde's "P-Source" plus inference, and
validated only by a sync check (every procedure's instruction stream lands
exactly on its end address). That check is blind to any disagreement that
does not change an instruction's *length* -- which is how the short-form
off-by-eight in finding 7 survived it.

Interp.s carries the dispatch table with a mnemonic in a comment on every
one of the 128 entries $80-$FF, so it settles the naming independently.
Reads the interpreter source directly; nothing is copied into the repo.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.pcode import OPCODES as OPS

INTERP = Path(r"C:\JohnBrooks\pascal13Src\pascal13\Interp.s")

# ;$80 ABI	ABS int: ABS(TOS)
ENTRY = re.compile(r"^\s*dw\s+\S+\s*;\$([0-9A-F]{2})\s+(\S+)")

# Names that differ only by the interpreter's spelling convention.
ALIAS = {
    "LAND": "LAND", "LOR": "LOR", "LNOT": "LNOT",
    "SLD1": "SLDL", "SLO1": "SLDO", "SIND1": "SIND",
}

src = INTERP.read_text(errors="replace").splitlines()
table = {}
for line in src:
    m = ENTRY.match(line)
    if m:
        op = int(m.group(1), 16)
        if op not in table:            # XFRTBL first, CSPTBL reuses $00-$28
            table[op] = m.group(2)
    if "CSPTBL" in line:
        break

print(f"read {len(table)} opcode entries from Interp.s XFRTBL\n")

agree = differ = missing = 0
for op in sorted(table):
    theirs = table[op]
    # collapse the interpreter's per-slot short-form names
    base = re.sub(r"\d+$", "", theirs)
    if base in ("SLD", "SLO", "SIND"):
        theirs = {"SLD": "SLDL", "SLO": "SLDO", "SIND": "SIND"}[base]
    ours = OPS.get(op, (None,))[0]
    if ours is None:
        # short forms and SLDC are decoded structurally, not via OPS
        if op < 0x80 or 0xD8 <= op <= 0xFF:
            continue
        print(f"  ${op:02X}  {theirs:<8} -- MISSING from decoder")
        missing += 1
    elif ours == theirs:
        agree += 1
    else:
        print(f"  ${op:02X}  interpreter {theirs:<8} decoder {ours:<8}  DIFFER")
        differ += 1

print(f"\n{agree} agree, {differ} differ, {missing} missing")

# The short forms are the ones the sync check could not see. Check the
# ranges structurally against the dispatch table's own slot numbering.
print("\nshort-form ranges as the interpreter dispatches them:")
for lo, hi, kind in ((0xD8, 0xE7, "SLD"), (0xE8, 0xF7, "SLO"),
                     (0xF8, 0xFF, "SIND")):
    names = [table[o] for o in range(lo, hi + 1) if o in table]
    if not names:
        continue
    first = re.sub(r"^\D+", "", names[0])
    last = re.sub(r"^\D+", "", names[-1])
    print(f"  ${lo:02X}-${hi:02X}  {kind}{first}..{kind}{last}"
          f"   => operand = opcode - ${lo - int(first):02X}")
