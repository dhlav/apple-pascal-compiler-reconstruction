"""Size UCSD's compiler records, and hold them against Apple's binary.

A type declaration is a claim about code bytes. Every field access in the
binary carries an offset, so a record declared one word wrong moves every
field after it and changes the emitted code. Finding 22c read seven record
sizes straight out of `SYSTEM.COMPILER` -- the `identifier` entry is 9, 10,
11, 11, 13, 18 or 18 words depending on its `klass` -- without knowing what
the fields were. `evidence/reference/ucsd-ii0-compiler/compglbls.text`
declares them. `a2pascal/reclayout.py` lays the declarations out and this
compares the two.

Three sizes match with nothing adjusted, from three unrelated records:

    ATTR        5 words   the compiler's GATTR (varblock.py)
    STRUCTURE   9 words   the "nine words of the standard descriptor" of 22c
    ALPHA       4 words   PACKED ARRAY [1..8] OF CHAR, two chars to the word

For `identifier`, three of the seven `klass` sizes match as written and four
are one word over. Removing exactly two fields makes all seven exact --
`PUBLIC` and `IMPORTED`, which are the same construct twice: a trailing
`CASE BOOLEAN OF TRUE: (...)` bolted onto the end of a variant, and both of
them UCSD unit features.

The probe requires that neither removal alone is enough, so the pair is
doing real work rather than one of them absorbing the other's word.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.reclayout import Layout

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "evidence" / "reference" / "ucsd-ii0-compiler" / "compglbls.text"

# IDCLASS, in declaration order, which is the order the binary numbers it.
IDCLASS = ["TYPES", "KONST", "FORMALVARS", "ACTUALVARS", "FIELD",
           "PROC", "FUNC", "MODULE"]
AS_WRITTEN = [9, 10, 12, 12, 13, 19, 19, 10]
# Finding 22c, from the binary. klass 7 (MODULE) is never observed.
BINARY = [9, 10, 11, 11, 13, 18, 18]
# The two fields Apple's compiler does not have. Each is the whole of a
# trailing `CASE BOOLEAN OF TRUE: (name: BOOLEAN)` and removing it removes
# exactly one word.
EXTENSIONS = ("PUBLIC", "IMPORTED")

fails = []
checks = 0


def check(cond, what):
    global checks
    checks += 1
    if not cond:
        fails.append(what)


def without(text: str, *names: str) -> str:
    """Drop `CASE BOOLEAN OF TRUE: (name: BOOLEAN)` for each name given."""
    for name in names:
        pat = re.compile(r"CASE\s+BOOLEAN\s+OF\s+TRUE\s*:\s*\(\s*" + name +
                         r"\s*:\s*BOOLEAN\s*\)", re.I | re.S)
        new, n = pat.subn(" ", text)
        if n != 1:
            fails.append(f"{name}: {n} matches in the source, want exactly 1")
        text = new
    return text


def klass_sizes(text: str) -> list[int]:
    lay = Layout(text)
    v = lay.record_variants(lay.types["IDENTIFIER"])
    return [v.get(name, v[""]) for name in IDCLASS]


raw = SRC.read_text(encoding="ascii", errors="replace")
lay = Layout(raw)

# Sizes the binary pins independently, with nothing adjusted.
for name, want, why in (("ATTR", 5, "the compiler's GATTR"),
                        ("STRUCTURE", 9, "finding 22c's nine-word descriptor"),
                        ("ALPHA", 4, "PACKED ARRAY [1..8] OF CHAR")):
    got = lay.size(name)
    check(got == want, f"{name} lays out as {got} words, but {why} is {want}")

got = klass_sizes(raw)
check(got == AS_WRITTEN,
      f"identifier as UCSD writes it is {got}, expected {AS_WRITTEN}")

cut = klass_sizes(without(raw, *EXTENSIONS))
check(cut[:len(BINARY)] == BINARY,
      f"identifier without {' and '.join(EXTENSIONS)} is {cut[:len(BINARY)]}, "
      f"but the binary has {BINARY}")

# Neither removal alone may account for it. If one did, the other would be
# unmotivated and the pair would be a fit rather than a finding.
for name in EXTENSIONS:
    one = klass_sizes(without(raw, name))
    check(one[:len(BINARY)] != BINARY,
          f"removing {name} alone already matches the binary, so "
          f"{EXTENSIONS} is over-specified")

print(f"identifier: as written {got}, "
      f"without {'/'.join(EXTENSIONS)} {cut[:len(BINARY)]}, "
      f"binary {BINARY}")
print(f"{checks} checks, {len(fails)} failures")
for f in fails[:20]:
    print("  FAIL", f)
sys.exit(1 if fails else 0)
