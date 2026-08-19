"""Apple's `CONST` and `TYPE` blocks: UCSD II.0's, with the edits the binary forces.

Both `varblock.py` and `srcskel.py` need these, and they need the *same* ones:
a declaration only allocates Apple's offsets if it is laid out under Apple's
constants. `MAXPROCNUM` alone moves 105 words in 1.3.

Every entry below is a number the binary states or a field the binary reads
at an offset UCSD's declaration does not reach. Nothing here is a preference,
and nothing is here to make a size come out: finding 76 is what happens when
a size is fitted rather than explained.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a2pascal.reclayout import Layout

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "evidence" / "reference" / "ucsd-ii0-compiler" / "compglbls.text"

# Constants Apple changed, per release.
CONSTS = {
    "1.1": {},
    "1.3": {
        # Finding 40a: COMPINIT compares NEXTJTAB against 36 where 1.1
        # compares against 24, and JTAB grows 25 -> 37 words to match.
        "MAXJTAB": (36, "finding 40a; 1.1 keeps 24"),
        # Finding 40: PROCTABLE goes 150 -> 255 words, so the bound goes
        # 149 -> 254. A procedure number is a byte, so 254 is its ceiling.
        "MAXPROCNUM": (254, "finding 40; 1.1 keeps 149"),
        # Finding 75: the code buffer doubles. All three `NEW(CODEP)` sites
        # in 1.3 ask for 1000 words where 1.1 asks for 650, and 650 is
        # exactly (1299+1) DIV 2 -- so 1.3's bound is 1999.
        "MAXCODE": (1999, "finding 75; 1.1 keeps 1299"),
    },
}

# Nothing is dropped from UCSD's TYPE block. Finding 54b once removed
# `PUBLIC` and `IMPORTED` to make four `identifier` variants a word smaller;
# finding 76 shows those sizes were never evidence of a missing field -- they
# are what a *tagged* NEW allocates -- and the binary reads `PUBLIC` at its
# declared offset in both releases, so the deletion was wrong.

# Fields Apple's records have that UCSD's do not. Both releases, so these
# are not keyed by version.
TYPE_EDITS = (
    # Findings 76b, 79c and 80b. Apple's MODULE variant is five words where
    # UCSD's is one, and three independent measurements agree on it:
    #
    #   * WRITELINKERINFO's MODULE arm reads `IND 10` and `IND 11`, both as
    #     BOOLEANs, ANDed into the test that decides whether a used unit
    #     gets a MODDULE record. Two words that must be there.
    #   * MARKRESIDENT's `NEW(...,MODULE)` asks for 13 words, which is the
    #     fixed part plus four -- so a fourth word follows those two.
    #   * DECLARATIONPART asks for 14 or 13 on one condition, the two arms
    #     of a single IF, and UNITDECLARATION asks for 14 flat. A tagged NEW
    #     allocates by the tag list it is given (finding 76), so the fourth
    #     word is a BOOLEAN tag and the fifth is its TRUE arm.
    #
    # That fifth word is allocated and never touched; the tag is written --
    # FALSE at both creation sites, TRUE in UNITDECLARATION's intrinsic
    # DATA arm. The names are ours: nothing recovered any of the four.
    # They are declared separately rather than as one list so that they
    # allocate forward (finding 33).
    ("MODULE: (SEGID: INTEGER)",
     "MODULE: (SEGID: INTEGER;\n"
     "\t\t\t     MODUNK10: BOOLEAN;\n"
     "\t\t\t     MODUNK11: BOOLEAN;\n"
     "\t\t\t     CASE MODUNK12: BOOLEAN OF\n"
     "\t\t\t       TRUE: (MODUNK13: INTEGER))",
     "findings 76b/79c/80b; four words at 10..13"),
)


def section(text: str, kw: str, stop: str, after: int = 0) -> str:
    """The `kw` block that precedes `stop`, verbatim, starting past `after`.

    `after` matters: compglbls.text opens with a one-line `TYPE PHYLE =
    FILE;` a hundred lines before the compiler's own TYPE block, and taking
    the first match swallows the segment declarations and the CONST block
    along with it.
    """
    m = re.search(rf"\n{kw}\b", text[after:])
    if not m:
        raise SystemExit(f"no {kw} block after offset {after}")
    start = after + m.end()
    return text[start:text.index(f"\n{stop}", start)]


def blocks(ver: str) -> tuple[str, str, list[str]]:
    """(CONST body, TYPE body, the edits made), for one release."""
    text = SRC.read_text(encoding="ascii", errors="replace")
    at = text.index("\nCONST")
    consts = section(text, "CONST", "TYPE", at)
    types = section(text, "TYPE", "VAR", at)
    notes = []
    for name, (val, why) in CONSTS[ver].items():
        pat = re.compile(rf"\b{name}\s*=\s*(\d+)")
        m = pat.search(consts)
        if not m:
            raise SystemExit(f"{name} is not in the II.0 CONST block")
        notes.append(f"{name} {m.group(1)} -> {val}   {{ {why} }}")
        consts = pat.sub(f"{name} = {val}", consts, count=1)
    for old, new, why in TYPE_EDITS:
        if types.count(old) != 1:
            raise SystemExit(f"{old!r}: {types.count(old)} matches in the "
                             f"TYPE block, want 1")
        types = types.replace(old, new, 1)
        notes.append(f"added to {old.split(':')[0]}   {{ {why} }}")
    return consts, types, notes


def layout(ver: str, inline: dict[str, str] | None = None) -> Layout:
    """A layout under Apple's constants, not UCSD's."""
    consts, types, _ = blocks(ver)
    lay = Layout("CONST" + consts + "\nTYPE" + types + "\nVAR\n")
    if inline:
        lay.types.update(inline)
    return lay
