"""Names for the runtime routines the compiler calls.

Segment 0 is the resident operating system (PASCALSYSTEM). Compiled code
reaches it with CXP 0,n, where n is a procedure number assigned in
declaration order within segment 0. GLOBALS.TEXT of the UCSD II.0 source
carries the block those numbers come from, labelled:

    (* SYSTEM PROCEDURE FORWARD DECLARATIONS *)
    (* THESE ARE ADDRESSED BY OBJECT CODE... *)
    (*  DO NOT MOVE WITHOUT CAREFUL THOUGHT  *)

so the numbering is recovered by parsing that block in order, with
procedure 1 reserved for the segment's outer block (PASCALSYSTEM itself).

This is a VERIFIED SOURCE FACT for UCSD II.0. Apple's runtime is a
derivative and could in principle differ; the mapping is corroborated
against the binary in analysis/ (e.g. PASCALCO.1 opens its four files with
CXP 0,3 = FINIT(f, window, -2) and closes them with CXP 0,6 = FCLOSE(f, 0)).
"""

from __future__ import annotations

import re
from pathlib import Path

_DECL = re.compile(r"^\s*(?:PROCEDURE|FUNCTION)\s+([A-Z_][A-Z_0-9]*)", re.I)
_START = "SYSTEM PROCEDURE FORWARD DECLARATIONS"


def segment0_procedures(globals_text: Path) -> dict[int, str]:
    """Recover the segment-0 procedure number -> name mapping."""
    lines = globals_text.read_text(encoding="ascii", errors="replace").splitlines()
    try:
        start = next(i for i, l in enumerate(lines) if _START in l)
    except StopIteration:
        return {}
    names = {1: "PASCALSYSTEM"}
    n = 2
    for line in lines[start:]:
        m = _DECL.match(line)
        if m:
            names[n] = m.group(1).upper()
            n += 1
    return names


# CSP (call standard procedure) operand -> name.
#
# VERIFIED SOURCE FACT. This is the whole CSPTBL dispatch table read straight
# out of John Brooks' Apple Pascal 1.4 interpreter source (Interp.s), which
# is a maintained descendant of the 1.3 interpreter and dispatches the same
# p-machine. Entries are listed there in hex; these keys are the decimal
# operand byte the compiler actually emits.
#
# This supersedes the guess in finding 10 that CSP 21..40 were "Apple
# additions outside the documented set". They are ordinary UCSD standard
# procedures that simply sit above the range Hyde tabulates. Two of them are
# reserved holes ($0D-$14) that the compiler never emits.
CSP = {
    0: "IOCHECK", 1: "NEW", 2: "MOVELEFT", 3: "MOVERIGHT", 4: "EXIT",
    5: "UNITREAD", 6: "UNITWRITE", 7: "IDSEARCH", 8: "TREESEARCH",
    9: "TIME", 10: "FILLCHAR", 11: "SCAN", 12: "UNITSTATUS",
    21: "LOADSEGMENT", 22: "UNLOADSEGMENT", 23: "TRUNC", 24: "ROUND",
    25: "SIN", 26: "COS", 27: "LOG", 28: "ATAN", 29: "LN", 30: "EXP",
    31: "SQRT",
    32: "MARK", 33: "RELEASE", 34: "IORESULT", 35: "UNITBUSY",
    36: "PWROFTEN", 37: "UNITWAIT", 38: "UNITCLEAR", 39: "HALT",
    40: "MEMAVAIL",
}


def csp_name(n: int) -> str:
    return f"CSP {n} {CSP[n]}" if n in CSP else f"CSP {n}"


# Parameter word counts for the UCSD calling convention.
#   value scalar / pointer   -> 1 word
#   value REAL               -> 2 words
#   VAR parameter            -> 1 word (an address)
#
# A type-based rule for wider VAR parameters was tried and rejected. The
# CSPs do pass packed references as (base, index) pairs, so the same was
# expected here, and FBLOCKIO's call sites do push eight words against six
# declared parameters. But no assignment of two-word types reproduces the
# call sites: making FIB two words fixes FBLOCKIO and immediately breaks
# FCLOSE, whose sites supply two words for the same declaration.
#
# The resolution is finding 8. GLOBALS.TEXT is the *generic UCSD II.0*
# operating system, not Apple's. Where Apple's segment 0 disagrees with it,
# the call sites are the evidence and the declaration is not. Individual
# routines are therefore overridden below from call-site evidence rather
# than by inventing a rule that fits one routine and breaks another.
_REAL = {"REAL"}
VAR_TWO_WORD: set[str] = set()

# name -> parameter words, where Apple's segment 0 demonstrably differs from
# the UCSD II.0 declaration. Both entries this once held are gone, because
# `SYSTEM.PASCAL` now parses (finding 50) and states its own parameter sizes:
#
#   FBLOCKIO was overridden from the declared 6 to 8. The binary says 8, so
#   the number was right, but the reason was not -- Apple did not extend it.
#   A function's frame carries the two-word result slot as well as the
#   arguments, so a declared 6 *is* a frame of 8. That is now a rule below
#   rather than a special case here, and it covers all nine of segment 0's
#   functions instead of the one whose call sites happened to be countable.
#
#   FOPEN was overridden from the declared 4 to 7, on 13 call sites with a
#   margin of 4. It is 4. Apple's own attribute table says 4 in both
#   releases, the call sites push exactly four words when read by hand
#   (UNITPART.2 pushes @G665, the string, SLDC 0, SLDC 0), and lifting the
#   whole compiler with 4 is byte-identical to lifting it with 7 -- so the
#   margin was never evidence of anything. Removed.
OS_WORD_OVERRIDE: dict[str, int] = {}

# proc number -> frame words, read directly from Apple's `SYSTEM.PASCAL`
# where the II.0 declaration is refuted rather than merely absent.
OS_FRAME_FROM_BINARY: dict[int, tuple[str, int, bool]] = {
    # GLOBALS.TEXT's 43rd forward declaration is COMMAND, which takes no
    # parameters. Apple's proc 43 takes three words, in both releases, and
    # the compiler's five call sites push exactly three -- an address, then
    # SLDC 1, then SLDC 40 or SLDC 80. So it is not COMMAND, and the caution
    # that used to sit here was right: the numbering agrees with II.0 through
    # 42 and parts company at 43 (finding 51). The name is withheld because
    # nothing here recovers it.
    43: ("OS.43", 3, False),
}


def _param_words(decl: str, is_var: bool = False) -> int:
    """Word count of one 'a,b: TYPE' group."""
    names, _, typ = decl.partition(":")
    n = len([x for x in names.split(",") if x.strip()])
    t = typ.strip().upper()
    if is_var:
        return n * (2 if t in VAR_TWO_WORD else 1)
    return n * (2 if t in _REAL else 1)


def segment0_signatures(globals_text: Path) -> dict[int, tuple[str, int, bool]]:
    """proc number -> (name, parameter words, is_function).

    Parsed from the same forward-declaration block as segment0_procedures,
    so the numbering is identical. VERIFIED SOURCE FACT for UCSD II.0.
    """
    text = globals_text.read_text(encoding="ascii", errors="replace")
    try:
        body = text.split(_START, 1)[1]
    except IndexError:
        return {}
    # Rejoin declarations that wrap across lines, then split on FORWARD.
    flat = " ".join(body.split())
    out: dict[int, tuple[str, int, bool]] = {1: ("PASCALSYSTEM", 0, False)}
    n = 2
    for chunk in re.split(r"\bFORWARD\s*;", flat, flags=re.I):
        m = re.search(r"\b(PROCEDURE|FUNCTION)\s+([A-Z_][A-Z_0-9]*)\s*(\(([^)]*)\))?"
                      r"\s*(:\s*[A-Z_][A-Z_0-9]*)?\s*;?\s*$", chunk, re.I)
        if not m:
            continue
        is_fn = m.group(1).upper() == "FUNCTION"
        name = m.group(2).upper()
        words = 0
        if m.group(4):
            for grp in m.group(4).split(";"):
                grp = grp.strip()
                if not grp:
                    continue
                stripped = re.sub(r"^VAR\s+", "", grp, flags=re.I)
                words += _param_words(stripped, is_var=stripped != grp)
        # A UCSD activation record holds the two-word function result slot
        # inside the parameter area, so the frame a caller must account for
        # is the declared arguments plus two. Checked against Apple's own
        # attribute tables for all nine of segment 0's functions (finding 51).
        frame = OS_WORD_OVERRIDE.get(name, words) + (2 if is_fn else 0)
        out[n] = OS_FRAME_FROM_BINARY.get(n, (name, frame, is_fn))
        n += 1
    return out
