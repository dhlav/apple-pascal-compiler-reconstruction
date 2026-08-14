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

# --- the code emitters, in BODYPART (finding 24c) --------------------------
#
# These four sit on top of PASCALCO.20:EMIT (which writes one byte) and are
# the compiler's whole code-generation interface. What identifies them is
# that their opcode argument is the opcode *minus 128*: BODYPART.5's 15
# distinct literal arguments all land on one-operand opcodes, and the
# `+20` and `-13` adjustments inside BODYPART.6 map each two-operand
# addressing opcode onto its short form ($B3 LDC -> $C7 LDCI, $B2 LDA ->
# $C6 LLA, $B6 LOD -> $CA LDL, $B8 STR -> $CC STL, and the six comparisons
# onto their integer variants). See tools/probes/probe_emitters.py.
#
# The spellings are ours; the arities and behaviour are the binary's.
BODYPART_EMIT: dict[int, str] = {
    3:  "EMITOP",     # (op)             opcode alone; pads with NOP before LSA
    4:  "EMITCONST",  # (v)              push integer v: short SLDC, or LDCI+NGI
    5:  "EMITOP1",    # (op, arg)        opcode + one operand byte
    6:  "EMITOP2",    # (op, lex, off)   picks the short form when it can
    25: "BODY",       # emits FINIT per file variable and the unit-init CXPs,
                      # then loops over statements while SY starts one
    27: "EMITBIG",    # (n)  the BIG encoding: one byte, or two with bit 7 set
}

PROC_NAMES: dict[str, dict[tuple[str, int], str]] = {
    "1.1": {("PASCALCO", n): s for n, s in PASCALCO_11.items()}
           | {("BODYPART", n): s for n, s in BODYPART_EMIT.items()}
           | {("COMPINIT", 7): "ENTERSTDIDENTS"},
    # BODYPART keeps these numbers in 1.3 except 27, which becomes 28; the
    # correspondence table matches 3..6 and 25 to themselves.
    "1.3": {("PASCALCO", n): s for n, s in PASCALCO_13.items()}
           | {("BODYPART", (n + 1 if n == 27 else n)): s
              for n, s in BODYPART_EMIT.items()}
           | {("COMPINIT", 7): "ENTERSTDIDENTS"},
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

    # Compiler-option state (finding 23). COMPOPTI.1 switches on the
    # upper-cased option letter, so each of these is tied to its letter by
    # the case table itself; the spellings are ours, the letters are not.
    13:  "LEVEL",       # Zurich's `level`; 1 for the program block, and the
                        # emitted LEX LEVEL byte is one less
    28:  "SYSCOMP",     # $U-, compile at the system lexical level
    30:  "OPT_F",       # $F, emit byte-swapped p-code (finding 24a)
    # Unit-compilation state. Written only in UNITPART, and UNITPART.3 --
    # which errors 182 if INUNIT is already set, i.e. no nested units --
    # saves LEVEL and the segment counter and then sets INUNIT, clears
    # ININTERFACE. ININTERFACE goes true between the unit heading and
    # `SY = IMPLEMENTATION`. Finding 24b.
    31:  "ININTERFACE",
    32:  "INUNIT",
    33:  "SWAPMORE",    # $S++, the second swapping flag
    34:  "SWAPPING",    # $S, selects PASCALCO.25 over PASCALCO.28
    35:  "NOLOAD",      # $N
    39:  "VARSTRING",   # $V
    42:  "OPT_T",       # $T, undocumented
    43:  "LISTING",     # $L
    45:  "OPT_E",       # $E, undocumented
    47:  "IOCHECK",     # $I
    49:  "SHOWPROGRESS",  # NOT $Q -- true when quiet compiling is off
    50:  "OPT_D",       # $D, undocumented
    51:  "RANGECHECK",  # $R
    52:  "GOTOOK",      # $G
    85:  "NEXTSEG",     # $NS n, default 7, rejected unless < 31
    487: "CODECOMMENT",  # $C, the 80-character codefile comment
    488: "LIBNAME",    # $U filename, the library to search for units

    # The four file variables (finding 10 listed them; finding 23 names them)
    535: "INFOFILE",   # *SYSTEM.INFO, the unit symbol-table work file
    586: "LIBFILE",    # SYSTEM.LIBRARY, or whatever $U filename named
    626: "SOURCEFILE",  # the program text, and the $I include file
    666: "LISTFILE",   # *SYSTEM.LST.TEXT, or whatever $L filename named
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

    # Finding 23, carried across by the correspondence table -- every one of
    # these pairs is a 1.00-similarity match, and the 1.3 $U- arm sets the
    # shifted numbers in the same order.
    13:  "LEVEL",
    28:  "SYSCOMP",
    30:  "OPT_F",
    32:  "ININTERFACE",   # 1.1 global 31, +1
    33:  "INUNIT",        # 1.1 global 32, +1
    34:  "SWAPMORE",
    35:  "SWAPPING",
    36:  "NOLOAD",
    40:  "VARSTRING",
    43:  "OPT_T",
    44:  "LISTING",
    46:  "OPT_E",
    48:  "IOCHECK",
    50:  "SHOWPROGRESS",
    51:  "OPT_D",
    52:  "RANGECHECK",
    53:  "GOTOOK",
    88:  "NEXTSEG",
    605: "CODECOMMENT",
    606: "LIBNAME",
    665: "INFOFILE",
    716: "LIBFILE",
    756: "SOURCEFILE",
    796: "LISTFILE",
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
