"""Is each statement parser the statement it is named for?

`STATEMEN` has eight procedures. Procedure 1 is the segment procedure
(finding 30); the other seven are the arms of Pascal's statement grammar,
minus `case` and `for`, which Apple moved into segments of their own.

Naming them from resemblance would be weak. What makes it strong is that
each one can be identified *twice over, independently*:

  * by the **reserved word it demands**, through the `SY` code it tests --
    and the SYMBOL enumeration is recovered and checked separately
    (finding 26);
  * by the **error number it raises when that word is missing** -- and the
    Apple Pascal error list says in plain English what every number means,
    so the compiler is quoting its own documentation.

The two have to agree, and they have to agree with the name. `IFSTATEMENT`
must test for `thensy` and raise 52, which Apple's list glosses "'THEN'
expected". Nothing forces a `while` parser to raise 54 rather than 52
except its being a `while` parser.

Two of the seven have no keyword of their own and are pinned by other
means: `ASSIGNMENT` demands `becomes` and raises 51 "':=' expected", and
`WITHSTATEMENT` raises 250 "Too many scopes of nested identifiers",
which only a construct that *opens a scope* can.

The two exiled statements are checked the same way, from their own
segments. Finding 31.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.names import SYMBOLS, procname

ROOT = Path(__file__).resolve().parent.parent.parent
LIFTED = {
    "1.1": ROOT / "analysis" / "lifted" / "SYSTEM.COMPILER-1.1.pas.txt",
    "1.3": ROOT / "analysis" / "lifted" / "SYSTEM.COMPILER-1.3.pas.txt",
}

# procedure -> (name, symbol it demands, error when missing, Apple's gloss)
# Error texts are quoted from the 1980 Apple Pascal Language Reference,
# Appendix: Compiler error messages.
CLAIMS = [
    ("STATEMEN", 2, "ASSIGNMENT",        "becomes",  51, "':=' expected"),
    ("STATEMEN", 3, "GOTOSTATEMENT",     "intconst", 15, "Integer expected"),
    ("STATEMEN", 4, "COMPOUNDSTATEMENT", "endsy",    13, "'END' expected"),
    ("STATEMEN", 5, "IFSTATEMENT",       "thensy",   52, "'THEN' expected"),
    ("STATEMEN", 6, "REPEATSTATEMENT",   "untilsy",  53, "'UNTIL' expected"),
    ("STATEMEN", 7, "WHILESTATEMENT",    "dosy",     54, "'DO' expected"),
    ("STATEMEN", 8, "WITHSTATEMENT",     "dosy",     54, "'DO' expected"),
    ("CASESTAT", 1, "CASESTATEMENT",          "ofsy",      8, "'OF' expected"),
    ("FORSTATE", 1, "FORSTATEMENT",          "dosy",     54, "'DO' expected"),
]

# Errors each one must *also* raise, where that is what distinguishes it
# from its siblings rather than the keyword.
ALSO = {
    ("STATEMEN", 8): [(250, "Too many scopes of nested identifiers -- WITH "
                            "opens a scope, and none of its siblings do"),
                      (140, "Type of variable must be record")],
    ("FORSTATE", 1): [(55, "'TO' or 'DOWNTO' expected in for statement"),
                      (51, "':=' expected"),
                      (143, "Illegal type of loop control variable")],
    ("STATEMEN", 3): [(167, "Undeclared label")],
    ("CASESTAT", 1): [(13, "'END' expected"), (156, "Multidefined case label")],
}

SYM = {name: code for code, name in SYMBOLS.items()}


def body(text: str, seg: str, num: int, release: str) -> list[str]:
    """The lifted lines of one procedure."""
    name = procname(seg, num, release)
    head = f"{seg}.{num}:{name}(" if name else f"{seg}.{num}("
    lines = text.split("\n")
    i = next((k for k, l in enumerate(lines)
              if l.startswith(("procedure ", "function ")) and head in l), None)
    if i is None:
        return []
    j = next((k for k in range(i + 1, len(lines))
              if lines[k].startswith(("procedure ", "function "))), len(lines))
    return lines[i:j]


def main() -> int:
    bad = []
    for rel, path in LIFTED.items():
        text = path.read_text(encoding="utf-8", errors="replace")
        for seg, num, want_name, sym, err, gloss in CLAIMS:
            # 1.3 keeps every one of these procedure numbers.
            got_name = procname(seg, num, rel)
            if got_name != want_name:
                bad.append(f"{rel} {seg}.{num}: names.py says {got_name!r}, "
                           f"this probe claims {want_name!r}")
            lines = body(text, seg, num, rel)
            if not lines:
                bad.append(f"{rel} {seg}.{num}: not found in the listing")
                continue
            blob = "\n".join(lines)

            code = SYM[sym]
            if not re.search(rf"\bSY = {code}\b", blob):
                bad.append(f"{rel} {want_name}: does not test SY = {code} "
                           f"({sym}), which is the word it must demand")
            raised = {int(m) for m in re.findall(r"ERROR\((\d+)\)", blob)}
            if err not in raised:
                bad.append(f"{rel} {want_name}: raises {sorted(raised)}, not "
                           f"{err} \"{gloss}\"")
            for also_err, why in ALSO.get((seg, num), []):
                if also_err not in raised:
                    bad.append(f"{rel} {want_name}: does not raise {also_err} "
                               f"({why})")
        print(f"{rel}: {len(CLAIMS)} statement parsers, each demanding the "
              f"right reserved word and raising Apple's error for it")

    if bad:
        print("\n".join(bad))
        return 1
    print("statements-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
