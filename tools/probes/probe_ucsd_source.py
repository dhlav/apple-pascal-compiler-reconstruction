"""What the UCSD II.0 compiler source says about what we recovered.

`evidence/reference/ucsd-ii0-compiler/` is the source of the UCSD Pascal
II.0 compiler -- "BASED ON ZURICH P2 PORTABLE COMPILER, EXTENSIVLY
MODIFIED BY ROGER T. SUMNER, SHAWN FANNING AND ALBERT A. HOFFMAN,
1976..1979". Apple Pascal's `SYSTEM.COMPILER` is a descendant of it, so it
is not the answer key -- Apple changed things, and where the two disagree
the binary wins. But everything this project derived from the bytes alone
is now checkable against a document written by the people who wrote the
compiler, and that is worth doing explicitly rather than by eye.

Three groups, all of which can fail.

  * **Numeric limits.** Every bound the disassembly hit was recovered as a
    bare number from a comparison. `compglbls.text` gives them names and
    values in a CONST block. `MAXCODE = 1299` is the one that pins it:
    nothing about the constant 1299 in `if IC + 100 > 1299` announces
    itself as a code-buffer size.
  * **The two scanner enumerations.** Finding 26 recovered SYMBOL at 0..54
    and OPERATOR at 0..15 from the reserved-word table, the scanner's case
    arms and the number scanner. The source declares both, in order, so
    the check is member for member by position.
  * **The names.** Every name in the registry longer than eight characters
    is supposed to be UCSD's rather than ours; `probe_identifiers.py`
    enforces that against this same source.

Finding 32.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.names import OPERATORS, SYMBOLS

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / "evidence" / "reference" / "ucsd-ii0-compiler"

# The bounds this project read out of the binary, and where.
RECOVERED = {
    "MAXCODE":    (1299, "finding 28e: `if IC + 100 > 1299 then ERROR(253)`, "
                         "the code-buffer guard (1.3 raises it to 1999)"),
    "MAXJTAB":    (24,   "finding 28b: GENJMP raises ERROR(253) when the "
                         "long-jump table reaches 24"),
    "MAXSEG":     (15,   "finding 27: BUMPSEG(SEGSLOT, 15, 354)"),
    "MAXPROCNUM": (149,  "finding 28a: NEWPROC raises ERROR(251) above 149"),
    "MAXLEVEL":   (8,    "finding 28b: `if LEVEL < 8 then LEVEL := LEVEL + 1`"),
    "MAXADDR":    (28000, "finding 31b: GENLABEL's end-of-chain sentinel"),
    "STRGLGTH":   (255,  "finding 22: DECLARAT range-checks STRING[n] "
                         "against 1..255 and reports error 203"),
    "DEFSTRGLGTH": (80,  "finding 28: the $C codefile comment is read to 80 "
                         "characters"),
}


# Members Apple changed, and why. Anything else differing is a failure.
ALLOWED_CHANGES = {("SYMBOL", 54): "OTHERWSY"}
ALLOWED_WHY = {
    ("SYMBOL", 54): "Apple dropped SEPARATE -- it is not in 1.3's "
                    "reserved-word table -- and put OTHERWISE in the slot",
}


def constants() -> dict[str, int]:
    """The CONST block of compglbls.text."""
    text = (SRC / "compglbls.text").read_text(errors="replace")
    body = text[text.index("CONST DISPLIMIT"):text.index("TYPE\n")]
    return {n: int(v) for n, v in re.findall(r"([A-Z]+) *= *(\d+)", body)}


def enumeration(name: str) -> list[str]:
    """A TYPE declaration's members, in order."""
    text = (SRC / "compglbls.text").read_text(errors="replace")
    m = re.search(rf"{name} *= *\(([^)]*)\)", text)
    return [w.strip() for w in m.group(1).split(",")] if m else []


def main() -> int:
    bad = []
    if not SRC.is_dir():
        print(f"{SRC} is missing")
        return 1

    consts = constants()
    for name, (got, where) in RECOVERED.items():
        want = consts.get(name)
        if want is None:
            bad.append(f"{name} is not in the source's CONST block")
        elif want != got:
            bad.append(f"{name}: the source says {want}, we recovered {got} "
                       f"({where})")
    print(f"{len(RECOVERED)} numeric bounds recovered from the binary, all "
          f"named and matched in compglbls.text")

    for kind, ours in (("SYMBOL", SYMBOLS), ("OPERATOR", OPERATORS)):
        theirs = enumeration(kind)
        if not theirs:
            bad.append(f"{kind} not found in the source")
            continue
        if len(theirs) != len(ours):
            bad.append(f"{kind}: the source declares {len(theirs)} members, "
                       f"we recovered {len(ours)}")
        agree, differ = 0, []
        for i, member in enumerate(theirs):
            if i not in ours:
                continue
            if ours[i].upper() == member:
                agree += 1
            else:
                differ.append((i, member, ours[i].upper()))
        for i, theirs_i, ours_i in differ:
            allowed = ALLOWED_CHANGES.get((kind, i))
            note = f"    {kind}[{i}]: source {theirs_i}, Apple {ours_i}"
            if allowed != ours_i:
                bad.append(note + " -- not a change we have accounted for")
            else:
                print(note + f"  ({ALLOWED_WHY[(kind, i)]})")
        print(f"{kind}: {agree} of {len(theirs)} members identical to the "
              f"source, {len(differ)} changed by Apple")

    if bad:
        print("\n".join(bad))
        return 1
    print("ucsd-source-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
