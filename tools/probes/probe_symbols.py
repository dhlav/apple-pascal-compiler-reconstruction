"""Are the `SY` and `OP` enumerations named right?

`tools/a2pascal/names.py` gives a name to all 55 symbol codes and all 16
operator codes. The names are the Zurich P2 / Pascal-P ones, which is
inference -- but what each code *is* comes from three places in the binary,
and each of them can contradict the naming.

  A. The reserved-word table embedded in 1.3's native IDSEARCH stores a
     `SY` and an `OP` beside every reserved word. Almost every entry should
     satisfy `SYMBOLS[sy] == word.lower() + "sy"` -- a rule the table did
     not have to obey. The exceptions are the words that are *operators*
     rather than keywords, and those must land on the right OPERATORS
     entry instead: AND on `andop`, DIV on `idiv`, MOD on `imod`, OR on
     `orop`, IN on `inop`.

  B. `INSYMBOL` is one `case` over the source character. Each arm assigns a
     symbol code, so the character names the code: `[` must be `lbrack`,
     `;` must be `semicolon`, a digit must be `intconst`. This is checked
     against a table written from the characters, not from the codes.

  C. Eight globals hold a `set of symbol`, and each is tested against `SY`
     at the head of a parser that raises a specific error when the test
     fails. The Apple Pascal error list (II-3E) says what those errors
     mean, so the error number is an independent statement of what the set
     is for. `constbegsys` had better guard "Error in constant".

Finding 26.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.names import OPERATORS, SYMBOLS, GLOBALS_11

ROOT = Path(__file__).resolve().parent.parent.parent
NATIVE = ROOT / "analysis" / "native" / "PASCALCO-1.3-native.asm.txt"
LIFTED = ROOT / "analysis" / "lifted" / "SYSTEM.COMPILER-1.1.pas.txt"

# (A) reserved words whose symbol code is not `word.lower() + "sy"`.
# Everything not listed here must follow that rule.
WORD_EXCEPTIONS = {
    "AND": ("mulop", "andop"), "DIV": ("mulop", "idiv"),
    "MOD": ("mulop", "imod"),  "OR":  ("addop", "orop"),
    "IN":  ("relop", "inop"),
    "PROGRAM": ("progsy", None),
    "SEGMENT": ("progsy", None),        # shares PROGRAM's code
    # These four cannot use the `<word>sy` spelling: folded to eight
    # significant characters it would *be* the reserved word. Finding 29.
    "INTERFAC": ("intersy", None),      # the table stores 8 characters
    "EXTERNAL": ("externlsy", None),
    "IMPLEMEN": ("implesy", None),
    "OTHERWIS": ("otherwsy", None),
    "PROCEDUR": ("procsy", None),
    "FUNCTION": ("funcsy", None),
}

# (B) source character -> every symbol INSYMBOL's arm for it can produce.
# Written from the characters; the codes come out of the binary. Three of
# these arms look one character further ahead and so have two outcomes:
# `.` is `period` alone but `colon` in `..`, `:` is `colon` alone but
# `becomes` in `:=`, and `(` is `lparent` unless it opens a `(*` comment.
CHAR_SYMBOL = {
    "(": {"lparent"}, ")": {"rparent"}, ",": {"comma"}, ";": {"semicolon"},
    "[": {"lbrack"}, "]": {"rbrack"}, "^": {"arrow"},
    ".": {"period", "colon"}, ":": {"becomes", "colon"},
    "*": {"mulop"}, "/": {"mulop"}, "+": {"addop"}, "-": {"addop"},
    "<": {"relop"}, "=": {"relop"}, ">": {"relop"},
    "0": {"intconst"}, "9": {"intconst"},
}

# (B) and the operator each of those punctuation marks carries.
CHAR_OPERATOR = {
    "*": "mul", "/": "rdiv", "+": "plus", "-": "minus",
    "<": "ltop", "=": "eqop",
}

# (C) symbol-set global (1.1 numbering) -> (members, guarding error).
# The error numbers are the Apple Pascal compiler's, II-3E:
#   1  Error in simple type      10  Error in type
#   18 Error in declaration part  50  Error in constant
#   58 Error in factor            59  Error in variable
SYMBOL_SETS = {
    126: (["ident", "intconst", "realconst", "stringconst", "addop",
           "longconst"], 50),
    122: (None, 1),        # simptypebegsys -- membership is built at runtime
    118: (None, 10),       # typebegsys     -- likewise
    98:  (["setsy", "arraysy", "recordsy", "filesy"], 10),
    114: (["beginsy", "labelsy", "constsy", "typesy", "varsy", "procsy",
           "funcsy", "progsy", "usessy"], 18),
    110: (["lbrack", "arrow", "period"], 59),
    106: (["ident", "lparent", "lbrack", "intconst", "realconst",
           "stringconst", "notsy", "longconst"], 58),
    102: (["beginsy", "ifsy", "casesy", "repeatsy", "whilesy", "forsy",
           "withsy", "gotosy"], None),      # drives the statement loops
}


def reserved_words():
    """(word, sy, op) from the table inside 1.3's native IDSEARCH."""
    text = NATIVE.read_text()
    return [(w, int(sy, 16), int(op, 16)) for w, sy, op in re.findall(
        r"\.ascii '([A-Z]+) *'\s+\.byte \$([0-9A-F]{2}),\$([0-9A-F]{2})", text)]


def insymbol_arms():
    """character -> symbol code, off INSYMBOL's case table."""
    lines = LIFTED.read_text().split("\n")
    i = next(k for k, l in enumerate(lines)
             if l.startswith("procedure PASCALCO.6:INSYMBOL"))
    j = next(k for k in range(i + 1, len(lines))
             if lines[k].startswith(("procedure ", "function ")))
    body = lines[i:j]

    # label -> every `SY := n` in its block, plus the first goto out of it
    at_label, sy_at, goto_at = None, {}, {}
    for l in body:
        t = l.strip()
        m = re.match(r"^(L[0-9A-F]{4}):", t)
        if m:
            at_label = m.group(1)
            sy_at.setdefault(at_label, set())
            continue
        if at_label is None:
            continue
        m = re.search(r"\bSY := (\d+);", t)
        if m:
            sy_at[at_label].add(int(m.group(1)))
        m = re.search(r"goto (L[0-9A-F]{4});", t)
        if m and at_label not in goto_at:
            goto_at[at_label] = m.group(1)

    def resolve(label, seen=()):
        """Codes assigned in this block, following one goto if it has none."""
        if label in seen:
            return set()
        got = sy_at.get(label, set())
        if got or label not in goto_at:
            return got
        return resolve(goto_at[label], (*seen, label))

    arms = {}
    for l in body:
        m = re.match(r"(\d+): goto (L[0-9A-F]{4});", l.strip())
        if m and int(m.group(1)) >= 32:
            got = resolve(m.group(2))
            if got:
                arms[chr(int(m.group(1)))] = got
    return arms


def set_members_and_error(gnum: int):
    """The literal a symbol-set global is initialised to, and the error
    number raised where it guards a parser."""
    text = LIFTED.read_text()
    name = GLOBALS_11[gnum]
    members = None
    m = re.search(rf"@{name}\^ := adjust\(\{{([^}}]*)\}}", text)
    if m:
        members = m.group(1).split(",")
    lines = text.split("\n")
    errs = set()
    for i, l in enumerate(lines):
        if "SY in " in l and f"@{name}^" in l and "not" in l:
            for k in range(i + 1, min(len(lines), i + 4)):
                e = re.search(r"ERROR\((\d+)\)", lines[k])
                if e:
                    errs.add(int(e.group(1)))
                    break
    return members, errs


def main() -> int:
    bad = []

    # (A) reserved words
    words = reserved_words()
    if len(words) < 40:
        bad.append(f"only {len(words)} reserved words found -- has the native "
                   f"listing changed?")
    for word, sy, op in words:
        want_sy, want_op = WORD_EXCEPTIONS.get(word, (word.lower() + "sy", None))
        got = SYMBOLS.get(sy)
        if got != want_sy:
            bad.append(f"reserved word {word}: SY={sy} is named {got!r}, "
                       f"expected {want_sy!r}")
        if want_op and OPERATORS.get(op) != want_op:
            bad.append(f"reserved word {word}: OP={op} is named "
                       f"{OPERATORS.get(op)!r}, expected {want_op!r}")
        if not want_op and op != 0 and word not in ("SEGMENT",):
            bad.append(f"reserved word {word}: unexpected OP={op}")

    # (B) the scanner's case table
    arms = insymbol_arms()
    for ch, want in CHAR_SYMBOL.items():
        if ch not in arms:
            bad.append(f"INSYMBOL has no arm for {ch!r}")
            continue
        got = {SYMBOLS.get(c, str(c)) for c in arms[ch]}
        if got != want:
            bad.append(f"INSYMBOL {ch!r} -> {sorted(got)}, "
                       f"expected {sorted(want)}")

    # (C) symbol sets and the errors they guard
    for gnum, (want_members, want_err) in SYMBOL_SETS.items():
        name = GLOBALS_11.get(gnum)
        members, errs = set_members_and_error(gnum)
        if name is None:
            bad.append(f"global {gnum} has no name")
            continue
        if want_members is not None:
            if members != want_members:
                bad.append(f"{name}: members are {members}, "
                           f"expected {want_members}")
        if want_err is not None and want_err not in errs:
            bad.append(f"{name}: guards error(s) {sorted(errs) or 'none'}, "
                       f"expected {want_err}")

    if bad:
        print("\n".join(bad))
        return 1
    print(f"{len(words)} reserved words, {len(arms)} scanner arms and "
          f"{len(SYMBOL_SETS)} symbol sets all agree with the naming")
    print(f"SYMBOLS covers {min(SYMBOLS)}..{max(SYMBOLS)} with "
          f"{len(SYMBOLS)} entries and no gap: "
          f"{sorted(SYMBOLS) == list(range(len(SYMBOLS)))}")
    print(f"OPERATORS covers 0..{max(OPERATORS)} with {len(OPERATORS)} "
          f"entries and no gap: "
          f"{sorted(OPERATORS) == list(range(len(OPERATORS)))}")
    print("symbols-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
