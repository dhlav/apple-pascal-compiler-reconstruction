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
are one word over. Finding 54b closed that gap by deleting two fields,
`PUBLIC` and `IMPORTED`. Finding 76 shows the gap was never a missing field
at all: **a record is not allocated by its type, it is allocated by the tag
list the `NEW` call supplies**. Every one of those four `klass` values is
created by a `NEW` whose last tag selects the *empty* arm of a trailing
`CASE BOOLEAN OF TRUE: (...)`, so the word is not there in the allocation
even though it is there in the declaration. A tag list that merely runs out
allocates the largest remaining arm instead -- finding 80b, measured against
Apple's own compiler -- so it is the empty label doing the work here and not
the shortness of the list.

The probe reads the tag lists out of II.0's own `NEW` call sites rather than
supplying them, sizes `identifier` along each, and requires that the result
is the binary's seven sizes with the declaration untouched. It also requires
that the untagged rule -- `record_variants`, which takes the largest arm --
does *not* reproduce them, so the tag path is doing the work; and it pins
`PUBLIC` at word 11, which is where both releases' `WRITELIN` reads it.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.reclayout import Layout, _strip_comments

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "evidence" / "reference" / "ucsd-ii0-compiler" / "compglbls.text"

# IDCLASS, in declaration order, which is the order the binary numbers it.
IDCLASS = ["TYPES", "KONST", "FORMALVARS", "ACTUALVARS", "FIELD",
           "PROC", "FUNC", "MODULE"]
AS_WRITTEN = [9, 10, 12, 12, 13, 19, 19, 10]
# Finding 22c, from the binary. klass 7 (MODULE) is never observed.
BINARY = [9, 10, 11, 11, 13, 18, 18]
# The two fields finding 54b deleted and finding 76 puts back. Each is the
# whole of a trailing `CASE BOOLEAN OF TRUE: (name: BOOLEAN)`.
EXTENSIONS = ("PUBLIC", "IMPORTED")
# Where the binary reads `PUBLIC`: `WRITELIN.4` does `IND 11` on the
# identifier in its FORMALVARS/ACTUALVARS arm, in 1.1 and in 1.3 alike, and
# the two `IND` around it are VLEV at 9 and VADDR at 10.
PUBLIC_AT = 11
# The sources whose `NEW` calls build identifier records. COMPINIT is the
# standard-identifier initialiser, which is where finding 22c's sizes were
# observed; the others are read so a tag list found nowhere in the compiler
# cannot creep into the table below.
NEW_SOURCES = ("compinit.text", "decpart.a.text", "decpart.b.text",
               "decpart.c.text", "procs.a.text", "procs.b.text",
               "bodypart.a.text", "unitpart.text", "block.text")

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

# The tag lists are read out of the compiler, not supplied here: whatever
# `NEW` II.0 actually writes for each klass is what the p-machine allocated.
NEW_CALL = re.compile(r"\bNEW\s*\(\s*\w+\s*((?:,\s*\w+\s*)+)\)", re.I)
tagged: dict[str, set[tuple[str, ...]]] = {}
for fname in NEW_SOURCES:
    text = _strip_comments((SRC.parent / fname).read_text(encoding="ascii",
                                                          errors="replace"))
    for m in NEW_CALL.finditer(text):
        tags = tuple(t.strip().upper() for t in m.group(1).split(",")
                     if t.strip())
        if tags[0] in IDCLASS:
            tagged.setdefault(tags[0], set()).add(tags)

# Every klass the binary shows must be built somewhere, or the table below
# would be quietly incomplete rather than wrong.
for name in IDCLASS[:len(BINARY)]:
    check(name in tagged, f"no NEW(...,{name},...) anywhere in the compiler")

# A klass is built more than one way -- `PROC` four ways, and only
# `NEW(...,DECLARED,ACTUAL,FALSE)` is 18 words -- so the claim is
# membership, not equality: the size the binary shows for a klass must be
# one a tag list in the compiler actually produces. That is still a check
# the declaration can fail. Delete `IMPORTED` and the longest `PROC` path
# becomes 17, so 18 is reachable by nothing; delete `PUBLIC` and 12
# disappears from `ACTUALVARS`.
alloc = {name: sorted({lay.new_size(lay.types["IDENTIFIER"], *tags)
                       for tags in tagged[name]})
         for name in IDCLASS[:len(BINARY)]}
for name, want in zip(IDCLASS, BINARY):
    check(want in alloc[name],
          f"the binary allocates {want} words for klass {name}, but UCSD's "
          f"own NEW calls only ever ask for {alloc[name]}")

# The tag path must be what closes the gap. If the untagged rule reproduced
# the binary too, finding 76 would be explaining something that needs no
# explanation.
check(got[:len(BINARY)] != BINARY,
      "the untagged rule already matches the binary, so the tag path is "
      "not what accounts for the four short variants")

# And the deletion must not be needed. Both fields stay in the declaration,
# so `PUBLIC` has to be at the word the binary reads it from.
cut = klass_sizes(without(raw, *EXTENSIONS))
check(cut[:len(BINARY)] == BINARY,
      f"deleting {' and '.join(EXTENSIONS)} gives {cut[:len(BINARY)]}; the "
      f"deletion is a second way to reach {BINARY} and finding 54b took it")
with_public = lay.new_size(lay.types["IDENTIFIER"], "ACTUALVARS", "TRUE")
check(with_public - 1 == PUBLIC_AT,
      f"PUBLIC lands at word {with_public - 1}, but WRITELIN reads IND "
      f"{PUBLIC_AT}")

# Every size `vardecl.py` once carried as a written-down number must come
# out of the engine. Those numbers were each derived by hand, several of
# them corroborated against Apple's own spacing between neighbouring
# offsets, so this is seventeen independent checks and not a tautology --
# the engine never saw any of them.
import vardecl                                    # noqa: E402

vb = vardecl.var_block()
lay2 = Layout(raw)
lay2.types.update(vardecl.INLINE)
for tname, (want, why) in vardecl.SIZES.items():
    got_t = lay2.size(tname)
    check(got_t == want, f"{tname} lays out as {got_t}, hand-derived {want} ({why})")
for vname, (want, why) in vardecl.BY_NAME.items():
    typ = next((t for ids, t in vb if vname in ids), None)
    check(typ is not None, f"{vname} is not declared in the VAR block")
    if typ is None:
        continue
    got_t = lay2.size(typ)
    check(got_t == want,
          f"{vname}: {typ} lays out as {got_t}, hand-derived {want} ({why})")

print(f"{len(vardecl.SIZES)} type sizes and {len(vardecl.BY_NAME)} variable "
      f"sizes reproduced from the declarations")
print(f"identifier: as written {got}, binary {BINARY}")
for name in IDCLASS[:len(BINARY)]:
    print(f"  {name:12s} NEW asks for {alloc[name]}")
print(f"{checks} checks, {len(fails)} failures")
for f in fails[:20]:
    print("  FAIL", f)
sys.exit(1 if fails else 0)
