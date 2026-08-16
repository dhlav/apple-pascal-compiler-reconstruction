"""Apple's `CONST` and `TYPE` blocks: UCSD II.0's, with the edits the binary forces.

Both `varblock.py` and `srcskel.py` need these, and they need the *same* ones:
a declaration only allocates Apple's offsets if it is laid out under Apple's
constants. `MAXPROCNUM` alone moves 105 words in 1.3.

Every entry below is a number the binary states or an absence the binary's
record sizes require. Nothing here is a preference.
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
    },
}

# Fields UCSD declares that Apple's records do not have. Finding 54b: each is
# a whole trailing `CASE BOOLEAN OF TRUE: (name: BOOLEAN)`, worth one word,
# and without both the identifier record is a word too big in four of its
# seven variants.
DROP_FIELDS = ("PUBLIC", "IMPORTED")


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
    for name in DROP_FIELDS:
        pat = re.compile(r"\s*CASE\s+BOOLEAN\s+OF\s+TRUE\s*:\s*\(\s*" + name +
                         r"\s*:\s*BOOLEAN\s*\)", re.I | re.S)
        types, n = pat.subn("", types)
        if n != 1:
            raise SystemExit(f"{name}: {n} matches in the TYPE block, want 1")
        notes.append(f"dropped {name}   {{ finding 54b }}")
    return consts, types, notes


def layout(ver: str, inline: dict[str, str] | None = None) -> Layout:
    """A layout under Apple's constants, not UCSD's."""
    consts, types, _ = blocks(ver)
    lay = Layout("CONST" + consts + "\nTYPE" + types + "\nVAR\n")
    if inline:
        lay.types.update(inline)
    return lay
