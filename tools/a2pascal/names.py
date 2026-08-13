"""Names recovered for the compiler's own procedures and globals.

Everything here is evidence-backed and cross-referenced to a finding in
`docs/FINDINGS.md`. Nothing goes in on plausibility alone: a name is added
only once the binary forces it, and where the evidence supports the
*behaviour* but not the historical spelling, the comment says so.

Names are recorded per release. The 1.3 numbering is not guessed: 1.3
inserts the two native procedures as PASCALCO.2 and .3, and the procedure
correspondence in `analysis/global_map/correspondence-1.1-to-1.3.txt`
shows every later PASCALCO procedure shifted by exactly +2, with no
reordering. Globals are listed out in full for both releases rather than
shifted, because the ~130-word growth is not uniform.
"""

# --- PASCALCO service routines (findings 12, 22) ---------------------------
#
# 1.1 numbering. These are the routines the whole compiler calls; naming
# them is what makes the other segments readable.
PASCALCO_11: dict[int, str] = {
    2:  "ERROR",         # the error reporter (finding 12, VERIFIED)
    4:  "ERRORWITHTEXT", # listing-file error writer (finding 12, VERIFIED)
    5:  "ENTERID",       # enter an identifier record into the symbol table
    6:  "INSYMBOL",      # the scanner (finding 12)
    7:  "SEARCHSECTION", # single-scope identifier search (finding 12)
    8:  "SEARCHID",      # full symbol-table search (finding 12)
    9:  "GETBOUNDS",     # (fsp; var fmin, fmax)              finding 22
    15: "STRING",        # is fsp a packed array of char?     finding 22
    16: "STRINGTYPE",    # is fsp a *declared* STRING?        finding 22
    17: "LONGSIZE",      # words for an n-digit long integer  finding 22
    18: "CONSTANT",      # parse a constant (fsys; var lsp, lvalu)
    20: "EMIT",          # the code-byte emitter (finding 12, VERIFIED)
    22: "FLUSHBUFFER",   # code-buffer flush (finding 12)
    27: "ENTERUNDECL",   # undeclared-identifier reporter (finding 12)
}

# 1.3: the two natives take slots 2 and 3, everything from 1.1's 2 upward
# moves by two.
PASCALCO_13: dict[int, str] = {
    2: "IDSEARCH",       # native 6502 (finding 19)
    3: "TREESEARCH",     # native 6502 (finding 19)
    **{n + 2: s for n, s in PASCALCO_11.items()},
}

PROC_NAMES: dict[str, dict[tuple[str, int], str]] = {
    "1.1": {("PASCALCO", n): s for n, s in PASCALCO_11.items()},
    "1.3": {("PASCALCO", n): s for n, s in PASCALCO_13.items()},
}

# --- compiler globals ------------------------------------------------------
#
# Operand numbers as they appear in `LDO n` / `SRO n`. The standard type
# descriptors and the standard identifiers come straight out of COMPINIT's
# two initialisation procedures, which name each descriptor by storing
# `LPA 'INTEGER '` next to the pointer that refers to it -- see
# `tools/probes/probe_stdtypes.py` and finding 22.
GLOBALS_11: dict[int, str] = {
    12: "INTPTR",       # INTEGER   size 1 word, form scalar, standard
    15: "SY",           # current symbol; written 20x in INSYMBOL, read 256x
    54: "STRINGPTR",    # STRING    the standard string[80] descriptor
    55: "INTERPTR",     # INTERACTIVE
    56: "NILPTR",       # form pointer, element type nil
    57: "TEXTPTR",      # TEXT
    58: "BOOLPTR",      # BOOLEAN   scalar, scalkind = declared
    59: "CHARPTR",      # CHAR
    60: "LONGPTR",      # the default long-integer type, form 3
    61: "REALPTR",      # REAL      size 2 words
    66: "OUTPUTPTR",    # the OUTPUT file's identifier record
    67: "INPUTPTR",     # the INPUT file's identifier record
}

GLOBALS_13: dict[int, str] = {
    12: "INTPTR",
    55: "STRINGPTR",
    56: "INTERPTR",
    57: "BYTESTREAMPTR",   # 1.3 only -- a packed char array that is not a
    58: "WORDSTREAMPTR",   # 1.3 only -- STRING, and an unpacked integer one
    59: "NILPTR",
    60: "TEXTPTR",
    61: "BOOLPTR",
    62: "CHARPTR",
    63: "LONGPTR",
    64: "REALPTR",
    69: "OUTPUTPTR",
    70: "INPUTPTR",
}

GLOBAL_NAMES = {"1.1": GLOBALS_11, "1.3": GLOBALS_13}

# --- record layouts --------------------------------------------------------
#
# Word offsets within the two central symbol-table records, read off the
# initialisation code (finding 22). Commentary only; nothing depends on it.
STRUCTURE_FIELDS = {           # the type descriptor, `structure`
    0: "size",                 # in words
    1: "form",
}
STRUCTFORM = {                 # the `form` enumeration
    0: "scalar", 1: "subrange", 2: "pointer", 3: "longint", 4: "power",
    5: "arrays", 6: "records", 7: "files", 8: "tagfld", 9: "variant",
}
IDENTIFIER_FIELDS = {          # the symbol-table entry, `identifier`
    0: "name",                 # words 0..3, eight characters
    4: "llink", 5: "rlink", 6: "idtype", 7: "next", 8: "klass",
}
IDCLASS = {                    # `klass`, with the record size it implies
    0: ("types", 9), 1: ("konst", 10), 2: ("vars", 11), 3: ("field", 11),
    4: ("klass4", 13), 5: ("proc", 18), 6: ("func", 18),
}


def procname(segname: str, number: int, release: str = "1.1"):
    return PROC_NAMES.get(release, {}).get((segname, number))


def globalname(number: int, release: str = "1.1"):
    return GLOBAL_NAMES.get(release, {}).get(number)
