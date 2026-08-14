"""Lay out the UCSD II.0 VAR block and diff it against Apple's globals.

The reconstruction has to reproduce Apple's global offsets exactly: every
`LDO`/`SRO` in the binary carries one, so a `VAR` block that allocates
differently produces different code bytes. This lays out II.0's VAR block
under the compiler's own allocation rule and reports, offset by offset,
where Apple agrees and where it does not.

Two rules govern the layout, both read out of the source in evidence/.

  * **Allocation starts at word 1.** Finding 17: `LDO n` addresses
    `BASE + 2n + 10`, and word 0 is never referenced on either disk.
  * **Within one declaration, identifiers are allocated in reverse order
    of appearance.** `VARDECLARATION` (decpart.b.text) builds the list by
    prepending -- `NEW(LCP); LCP^.NEXT := NXT; NXT := LCP` -- and then
    walks that list assigning `VADDR := LC; LC := LC + LSIZE`. So
    `VAR LC,IC: ADDRRANGE` puts IC first. Finding 33.

Type sizes come from the TYPE block of compglbls.text; the ones that are
not one word are listed in SIZES below with their derivation.

Writes analysis/global_map/vardecl-ii0.txt.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a2pascal.names import GLOBALS_11

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "evidence" / "reference" / "ucsd-ii0-compiler" / "compglbls.text"
OUT = ROOT / "analysis" / "global_map" / "vardecl-ii0.txt"

# Everything not listed is one word. Each entry says why.
SIZES = {
    "ALPHA":    (4,  "PACKED ARRAY [1..8] OF CHAR, CHRSPERWD = 2"),
    "ATTR":     (5,  "TYPTR, KIND, CVAL/ACCESS, VLEVEL, DPLMT"),
    "SETOFSYS": (4,  "SET OF SYMBOL: 55 members, BITSPERWD = 16"),
    "SETOFIDS": (1,  "SET OF IDCLASS: 8 members"),
    "VALU":     (1,  "variant record over INTEGER and a pointer"),
    "NONRESPFLIST": (6, "ARRAY [NONRESIDENT] OF INTEGER, 6 members"),
}

# Aggregates whose size the type name alone does not give. Each is
# corroborated by Apple's own spacing between the two neighbouring
# offsets we have recovered, noted in brackets.
BY_NAME = {
    "DISPLAY":   (52,  "ARRAY [0..DISPLIMIT] OF a 4-word record, 13 x 4"),
    "PROCTABLE": (150, "ARRAY [0..MAXPROCNUM] OF INTEGER "
                       "[Apple: 335 - 185 = 150]"),
    "SEGTABLE":  (128, "ARRAY [0..MAXSEG] OF an 8-word record; Apple's "
                       "entry is 9 words, indexed SEGTABLE[slot*9]"),
    "SYSTEMLIB": (21,  "STRING[40] = 41 bytes [Apple: 509 - 488 = 21]"),
    "JTAB":      (25,  "ARRAY [0..MAXJTAB] OF INTEGER "
                       "[Apple: 535 - 510 = 25]"),
    "REFFILE":   (40,  "a FILE variable = NILFILESIZE "
                       "[Apple: 626 - 586 = 40]"),
    "INCLFILE":  (40,  "likewise"),
    "LIBRARY":   (40,  "likewise"),
    "LP":        (40,  "a TEXT file"),
    "DISKBUF":   (256, "PACKED ARRAY [0..511] OF CHAR"),
    "REFLIST":   (1,   "a pointer to REFARRAY, not the array"),
}


def var_block() -> list[tuple[list[str], str]]:
    """(identifiers, type) per declaration, in source order."""
    text = SRC.read_text(errors="replace")
    body = text[text.index("\nVAR\n") + 5:text.index("(* FORWARD DECLARED")]
    body = re.sub(r"\(\*.*?\*\)", " ", body, flags=re.S)      # comments
    # Collapse inline RECORD ... END so its fields do not read as
    # declarations of their own.
    while True:
        m = re.search(r"RECORD.*?END", body, flags=re.S)
        if not m:
            break
        body = body[:m.start()] + " AGGREGATE " + body[m.end():]
    out = []
    for decl in body.split(";"):
        decl = " ".join(decl.split())
        if ":" not in decl:
            continue
        names, _, typ = decl.partition(":")
        ids = [n.strip() for n in names.split(",") if n.strip()]
        if ids and all(re.fullmatch(r"[A-Z][A-Z0-9]*", i) for i in ids):
            out.append((ids, typ.strip()))
    return out


def size_of(typ: str, name: str = "") -> tuple[int, str]:
    if name in BY_NAME:
        return BY_NAME[name]
    base = typ.split("[")[0].strip().rstrip(";")
    if base.startswith("^") or base in ("CTP", "STP", "CSP", "TESTP", "LBP",
                                        "LABELP"):
        return 1, "pointer"
    if base in SIZES:
        return SIZES[base]
    return 1, "scalar"


def main() -> int:
    # Apple's offset for each recovered name.
    apple = {name: off for off, name in GLOBALS_11.items()}

    rows, off = [], 1
    for ids, typ in var_block():
        for name in reversed(ids):            # <-- the rule
            words, why = size_of(typ, name)
            rows.append((off, name, words, apple.get(name), why))
            off += words

    lines = [
        "UCSD II.0 compiler VAR block, laid out under the compiler's own",
        "allocation rule, aligned by name against Apple Pascal 1.1.",
        "",
        "Allocation starts at word 1, and identifiers within one declaration",
        "are allocated in REVERSE order of appearance: VARDECLARATION",
        "prepends them to a list, then walks it assigning VADDR := LC",
        "(finding 33). So `VAR LC,IC: ADDRRANGE` puts IC at the lower",
        "offset, which is what the binary shows.",
        "",
        "Apple's compiler is a standalone program, not a segment of",
        "PASCALSYSTEM, and its VAR block is edited -- so the useful column",
        "is DRIFT. A run of equal drift means Apple kept II.0's order for",
        "that stretch; each step up is a variable Apple inserted.",
        "",
        f"{'II.0':>5} {'name':<16} {'wds':>3} {'Apple':>6} {'drift':>6}",
        "-" * 60,
    ]
    named = drift_runs = 0
    last = None
    for o, name, words, a, _why in rows:
        d = "" if a is None else f"{a - o:+d}"
        if a is not None:
            named += 1
            if (a - o) != last:
                drift_runs += 1
                last = a - o
        lines.append(f"{o:>5} {name:<16} {words:>3} {a or '-':>6} {d:>6}")
    lines += ["-" * 60,
              f"{len(rows)} II.0 variables; {named} of them are names we have "
              f"recovered in Apple, in {drift_runs} runs of constant drift."]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(rows)} II.0 variables, "
          f"{named} matched to Apple, {drift_runs} drift runs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
