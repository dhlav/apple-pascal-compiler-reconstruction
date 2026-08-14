"""Do the recovered names survive Apple Pascal's 8-character rule?

Apple Pascal keeps only the first eight significant characters of an
identifier. The 1.3 manual's *Identifiers* section states all four parts
of the rule:

    An identifier must begin with a letter. After the initial letter, it
    may contain any number of letters, digits, or underscore characters
    ... Only the first 8 characters (ignoring underscores) are
    significant. Capital and lowercase letters are equivalent.

    Thus the following six identifiers are equivalent and
    interchangeable: MYNUMBER  mynumber  MY_NUMBER  My_Number
    MY_NUMBER_VALUE ...

and the binary cannot do otherwise: finding 22 recovered the symbol-table
entry with the name in words 0-3, and the reserved-word table inside 1.3's
native IDSEARCH stores each word in exactly eight bytes. Eight characters
is all there is room for.

This matters for the deliverable rather than for the analysis. Every name
in `tools/a2pascal/names.py` is a name the reconstructed source will
carry, and two of them agreeing in eight significant characters are *one*
identifier to the compiler -- a duplicate-declaration error at best, and a
silent aliasing of two different variables at worst. So:

  * no two names may collide once folded to eight significant characters;
  * no name may fold onto an Apple Pascal reserved word -- the manual is
    explicit that *"the Compiler will refuse to accept it"*;
  * no name may fold onto a predeclared identifier (Table F-2B) either,
    because *"the Compiler will accept it but the original Pascal
    identifier will become unavailable within the scope of the new
    meaning"* -- a silent breakage rather than a diagnostic. The one
    exception is spelled out at the check itself: a *nested* procedure
    whose name II.0 also uses for a procedure, where the scope of the new
    meaning cannot reach the outermost one;
  * every name longer than eight characters is listed, because what we
    write is not what the compiler will see. Those are allowed only where
    the spelling is forced by evidence (Pascal-P's, or Apple's own).

Globals, procedures and the two enumerations are checked together, since
in a single Pascal program they all live in the same outermost scope.

Finding 29.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.names import (GLOBALS_11, GLOBALS_13, OPERATORS, PROC_NAMES,
                            SYMBOLS, procname)

DISKS = {
    "1.1": "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk",
    "1.3": "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk",
}

ROOT = Path(__file__).resolve().parent.parent.parent
NATIVE = ROOT / "analysis" / "native" / "PASCALCO-1.3-native.asm.txt"

# Long spellings are allowed only where the evidence forces them rather
# than our choosing them. That set is not hard-coded: it is read out of the
# UCSD II.0 compiler source in evidence/, so a name claimed to be UCSD's
# has to actually appear there (finding 32). A handful predate it.
II0_SOURCE = ROOT / "evidence" / "reference" / "ucsd-ii0-compiler"

EXTRA_BACKED = {
    "TREESEARCH",       # Apple's own, off the 1.3 native code (finding 19)
    "IMPLEMENTATIONSY", # (kept only so the finding-29 text stays checkable)
}


def ucsd_identifiers() -> set[str]:
    """Every identifier that appears in the UCSD II.0 compiler source."""
    out: set[str] = set()
    for f in sorted(II0_SOURCE.glob("*.text")):
        out |= set(re.findall(r"[A-Z][A-Z0-9]{2,}",
                              f.read_text(errors="replace").upper()))
    return out


# Apple Pascal's predeclared identifiers, Table F-2B of the 1.3 manual,
# transcribed in full. Legal to redeclare, but doing so costs the original
# meaning -- which the compiler cannot afford for STRING (LIBNAME and
# CODECOMMENT are STRING-typed) or for the types it declares variables of.
PREDECLARED = """
ABS BLOCKREAD BLOCKWRITE BOOLEAN BYTESTREAM CHAR CHR CLOSE CONCAT COPY
DELETE EOF EOLN EXIT FALSE FILLCHAR GET GOTOXY HALT INPUT INSERT INTEGER
INTERACTIVE IORESULT KEYBOARD LENGTH MARK MAXINT MEMAVAIL MOVELEFT
MOVERIGHT NEW ODD ORD OUTPUT PAGE POS PRED PUT PWROFTEN READ READLN REAL
RELEASE RESET REWRITE ROUND SCAN SEEK SIZEOF SQR STR STRING SUCC TEXT
TRUE TRUNC UNITBUSY UNITCLEAR UNITREAD UNITSTATUS UNITWAIT UNITWRITE
WORDSTREAM WRITE WRITELN
""".split()

# Predeclared identifiers we deliberately shadow, with the reason. Empty:
# nothing in the naming currently needs to.
def ucsd_procedures() -> set[str]:
    """Identifiers II.0 declares as a procedure or a function."""
    out: set[str] = set()
    for f in sorted(II0_SOURCE.glob("*.text")):
        out |= set(re.findall(r"(?:PROCEDURE|FUNCTION)[ 	]+([A-Z][A-Z0-9]*)",
                              f.read_text(errors="replace").upper()))
    return out


def apple_lex_levels() -> dict[str, dict[str, int]]:
    """release -> name -> the lexical level Apple declares it at."""
    out: dict[str, dict[str, int]] = {}
    for ver, dsk in DISKS.items():
        disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / dsk)
        e = disk.find("SYSTEM.COMPILER")
        cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))
        out[ver] = {}
        for seg in cf.segments:
            for p in seg.procedures:
                nm = procname(seg.name, p.number, ver)
                if nm:
                    out[ver][nm] = p.lex_level
    return out


def fold(name: str) -> str:
    """The identifier as Apple Pascal sees it."""
    return name.replace("_", "").upper()[:8]


def reserved_words() -> set[str]:
    """The reserved words, from the table inside 1.3's native IDSEARCH."""
    return set(re.findall(r"\.ascii '([A-Z]+) *'\s+\.byte \$[0-9A-F]{2}",
                          NATIVE.read_text()))


def main() -> int:
    bad, over = [], {}
    words = reserved_words()
    predeclared = {fold(w) for w in PREDECLARED}
    # Redeclaring a predeclared identifier is legal -- the manual says the
    # compiler "will accept it" -- and costs the original meaning only
    # *within the scope of the new meaning*. So a shadow is allowed when
    # both halves of that are evidenced: II.0 declares a procedure of the
    # name (Apple's own compiler accepted the source), and Apple declares
    # it at lexical level 2 or deeper, so the shadow cannot reach the
    # program's outermost scope where the intrinsic is needed. Seven names
    # qualify -- CLOSE, CONCAT, EXIT, SCAN, SIZEOF, STR and STRING, the
    # standard procedures' own handlers, named after what they compile.
    # Both halves are required: an invented name fails the first, and a
    # global fails the second. Finding 35c, extended by finding 37.
    lex = apple_lex_levels()
    ucsd_procs = {fold(w) for w in ucsd_procedures()}
    if len(words) < 40:
        bad.append(f"only {len(words)} reserved words found -- has the "
                   f"native listing changed?")

    for rel, glob in (("1.1", GLOBALS_11), ("1.3", GLOBALS_13)):
        # Everything that would be declared in the program's outermost
        # scope: globals, procedures, and both enumerations' members.
        pool: dict[str, set[str]] = {}
        whence: dict[str, set[str]] = {}
        sources = (
            [(s, f"global {n}") for n, s in glob.items()]
            + [(s, f"{seg}.{n}") for (seg, n), s in PROC_NAMES[rel].items()]
            + [(s.upper(), "SYMBOL") for s in SYMBOLS.values()]
            + [(s.upper(), "OPERATOR") for s in OPERATORS.values()]
        )
        for name, where in sources:
            pool.setdefault(fold(name), set()).add(name)
            whence.setdefault(name, set()).add(where)
            if len(name.replace("_", "")) > 8:
                over.setdefault(name, where)

        for folded, spellings in sorted(pool.items()):
            if len(spellings) > 1:
                bad.append(f"{rel}: {sorted(spellings)} are the same "
                           f"identifier -- all fold to {folded}")
            if folded in words:
                bad.append(f"{rel}: {sorted(spellings)} folds to {folded}, "
                           f"which is a reserved word -- the compiler would "
                           f"refuse the declaration")
            shadow_ok = (folded in ucsd_procs
                         and all(not w.startswith("global ")
                                 for n in spellings for w in whence[n])
                         and all(lex[rel].get(n, 0) >= 2 for n in spellings))
            if folded in predeclared and not shadow_ok:
                bad.append(f"{rel}: {sorted(spellings)} folds to {folded}, "
                           f"a predeclared identifier -- declaring it takes "
                           f"the original meaning away for the whole scope")

        print(f"{rel}: {len(pool)} distinct identifiers from "
              f"{len(sources)} names, no two alike in 8 characters, none "
              f"folding onto any of {len(words)} reserved words or "
              f"{len(predeclared)} predeclared identifiers except where "
              f"II.0 names a procedure the same and Apple declares it at "
              f"lex 2 or deeper")

    backed = ucsd_identifiers() | EXTRA_BACKED
    unvetted = sorted(set(over) - backed)
    print(f"{len(over)} names exceed 8 characters; "
          f"{len(over) - len(unvetted)} of "
          f"those spellings are UCSD's own, {len(unvetted)} are ours:")
    for name in unvetted:
        print(f"    {name:22s} -> {fold(name):8s}  ({over[name]})")

    if bad:
        print("\n".join(bad))
        return 1
    print("identifiers-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
