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


# CSP (call standard procedure) operand -> name, UCSD II.0 assignment.
# 0-11 are the documented UCSD II.0 set. The compiler also issues CSP 21,
# 22, 23, 24, 32, 33, 34, 36 and 40, which are outside that set and are
# presumed Apple additions; see docs/FINDINGS.md finding 10.
CSP = {
    0: "IOCHECK", 1: "NEW", 2: "MOVELEFT", 3: "MOVERIGHT", 4: "EXIT",
    5: "UNITREAD", 6: "UNITWRITE", 7: "IDSEARCH", 8: "TREESEARCH",
    9: "TIME", 10: "FILLCHAR", 11: "SCAN",
}


def csp_name(n: int) -> str:
    return f"CSP {n} {CSP[n]}" if n in CSP else f"CSP {n}"


# Parameter word counts for the UCSD calling convention.
#   VAR parameter            -> 1 word (an address)
#   value scalar / pointer   -> 1 word
#   value REAL               -> 2 words
#   value structured (STRING, records) -> 1 word (address; callee copies)
_REAL = {"REAL"}


def _param_words(decl: str) -> int:
    """Word count of one 'a,b: TYPE' group, given VAR-ness is handled by caller."""
    names, _, typ = decl.partition(":")
    n = len([x for x in names.split(",") if x.strip()])
    return n * (2 if typ.strip().upper() in _REAL else 1)


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
                words += _param_words(re.sub(r"^VAR\s+", "", grp, flags=re.I))
        out[n] = (name, words, is_fn)
        n += 1
    return out
