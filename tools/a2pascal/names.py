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
    12: "NEXTLINE",      # advance LINENUMBER and CHINDEX, echo the progress
                         # dot, write the listing line                  fdg 26
    14: "SKIP",          # `while not (SY in fsys) do INSYMBOL` -- Pascal-P's
                         # error recovery, called after 37 of the ERROR sites
    # --- finding 27 ---------------------------------------------------------
    3:  "NEXTBLOCK",     # read the next two source blocks into SOURCEBUF;
                         # error 401 "Unexpected end of input" if it cannot
    10: "BUMPSEG",       # (var n; limit, err) -- bounded increment. Both call
                         # sites are segment counters and both pass error 354,
                         # "Too many segments for segment dictionary".
    11: "NEWSEGMENT",    # allocate the next segment number and codefile slot
    19: "COMPTYPES",     # Pascal-P's comptypes(fsp1, fsp2): boolean -- 35 call
                         # sites, recursive on `form`, with a pair list to
                         # terminate on mutually recursive pointer types
    21: "EMITWORD",      # emit one word, byte-swapped under {$F+}
    24: "BLOCK",         # the outer block: dispatches `unitsy` to UNITPART and
                         # raises error 408, "(*$S+*) needed to compile units"
    26: "COMMENT",       # scan a comment to its closing delimiter, which is the
                         # argument; a leading `$` goes to COMPOPTI.1
    18: "CONSTANT",      # parse a constant (fsys; var lsp, lvalu)
    20: "EMIT",          # the code-byte emitter (finding 12, VERIFIED)
    22: "FLUSHBUFFER",   # code-buffer flush (finding 12)
    27: "ENTERUNDECL",   # undeclared-identifier reporter (finding 12)
    # --- finding 28 ---------------------------------------------------------
    13: "MAKESEGINFO",   # build a segment dictionary's SEGINFO word: segment
                         # number in bits 0-7, machine type in 8-11 (2 =
                         # p-code LSB, or 1 = MSB under {$F+}), 0 in bit 12,
                         # version 2 in 13-15. The layout matches the one
                         # tools/a2pascal/codefile.py reads at block 0.
    23: "ENDSEGMENT",    # close the current segment: emit the procedure
                         # dictionary from PROCDICT, then the segment number
                         # and procedure count, record the segment's length
                         # and reset LCBASE. See tools/probes/probe_segtail.py
    25: "COMPILE",       # stamp the start time, call BLOCK with the outermost
                         # fsys, then FINISHUP.1 -- the whole compilation
    28: "COMPILERESIDENT",   # hold DECLARAT, BODYPART, NUMSTRIN, STATEMEN,
                         # CASESTAT, FORSTATE, BODY1 and BODY3 in memory
                         # across the call to COMPILE. PASCALCO.1 takes this
                         # path unless {$S+}.
    29: "COMPILEHOLDINGROUTINE",  # ...and ROUTINE as well, when the second
                         # swapping flag {$S++} is off
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

# --- finding 28b: the rest of the code-generation tail ---------------------
#
# These three keep their numbers across releases (correspondence table:
# BODYPART.13 -> .13, BODYPART.16 -> .16, BODY3.1 -> BODY3.1).
CODEGEN: dict[tuple[str, int], str] = {
    ("BODYPART", 13): "ALLOCPROCNUM",  # assign the next procedure number to
                                       # an identifier record; ERROR(251) at
                                       # 149. Clears its PROCDICT slot.
    ("BODYPART", 16): "EMITJUMP",      # (op, target) -- short displacement if
                                       # it fits in 0..127, otherwise a slot
                                       # in JTABLE and a negative index
    ("BODY3", 1):     "ENDPROC",       # close a procedure: pad, then the
                                       # long-jump table, data size, param
                                       # size, exit IC, enter IC, procedure
                                       # number and LEX LEVEL -- the whole
                                       # attribute table, low address first
}

PROC_NAMES: dict[str, dict[tuple[str, int], str]] = {
    "1.1": {("PASCALCO", n): s for n, s in PASCALCO_11.items()}
           | {("BODYPART", n): s for n, s in BODYPART_EMIT.items()}
           | CODEGEN
           | {("COMPINIT", 7): "ENTERSTDIDENTS"},
    # BODYPART keeps these numbers in 1.3 except 27, which becomes 28; the
    # correspondence table matches 3..6 and 25 to themselves.
    "1.3": {("PASCALCO", n): s for n, s in PASCALCO_13.items()}
           | {("BODYPART", (n + 1 if n == 27 else n)): s
              for n, s in BODYPART_EMIT.items()}
           | CODEGEN
           | {("COMPINIT", 7): "ENTERSTDIDENTS"},
}

# --- the scanner's two enumerations (finding 26) ---------------------------
#
# `SY` (global 15) and `OP` (global 16) are set together by the scanner for
# every token. Both enumerations are recovered complete, and neither has a
# gap: SYMBOLS covers 0..54 with nothing left over, OPERATORS covers 0..15.
#
# Where each code comes from:
#   * 6..13, 19..34, 38..46, 49..54 -- the reserved-word table embedded in
#     1.3's native IDSEARCH, which stores `SY` and `OP` beside each word
#     (finding 19). Those are the binary's own bytes.
#   * 0..5, 14..18, 35, 37, 39..41, 47 -- `PASCALCO.6:INSYMBOL`, whose body
#     is one `case` over the source character with a `SY := n` in each arm.
#     Reading the arm's character off the case table names the code.
#   * 36, 48 -- `NUMSTRIN`, the number scanner: the float path sets 36, the
#     BCD path that errors 203 past 36 digits sets 48.
#
# The spellings are the Zurich P2 / Pascal-P ones, which is inference, not
# evidence -- but see finding 26 for how far the structure corroborates it:
# six symbol *sets* land on the errors the vendor's table says they should,
# and OPERATORS matches Pascal-P's `operator` enumeration 16 for 16 in
# order.
SYMBOLS: dict[int, str] = {
    0:  "ident",
    1:  "comma",        2:  "colon",        # `..` also scans as colon
    3:  "semicolon",    4:  "lparent",      5:  "rparent",
    6:  "dosy",         7:  "tosy",         8:  "downtosy",
    9:  "endsy",        10: "untilsy",      11: "ofsy",
    12: "thensy",       13: "elsesy",       14: "becomes",
    15: "lbrack",       16: "rbrack",       17: "arrow",
    18: "period",
    19: "beginsy",      20: "ifsy",         21: "casesy",
    22: "repeatsy",     23: "whilesy",      24: "forsy",
    25: "withsy",       26: "gotosy",       27: "labelsy",
    28: "constsy",      29: "typesy",       30: "varsy",
    31: "procsy",       32: "funcsy",
    33: "progsy",       # PROGRAM and SEGMENT share this code
    34: "forwardsy",
    35: "intconst",     36: "realconst",    37: "stringconst",
    38: "notsy",        39: "mulop",        40: "addop",
    41: "relop",        42: "setsy",        43: "packedsy",
    44: "arraysy",      45: "recordsy",     46: "filesy",
    47: "othersy",      # anything illegal; INSYMBOL then raises error 400
    48: "longconst",    # INTEGER[n] literal -- an Apple/UCSD extension
    49: "usessy",       50: "unitsy",       51: "interfacesy",
    52: "implementationsy",
    53: "externalsy",   54: "otherwisesy",  # OTHERWISE is 1.3-only
}

# `OP` qualifies `mulop`/`addop`/`relop`, and is 15 for everything else.
# This is Pascal-P's `operator` enumeration in its published order, all
# sixteen members, which is the single strongest piece of evidence that
# this compiler is that compiler's descendant.
OPERATORS: dict[int, str] = {
    0:  "mul",      # *
    1:  "rdiv",     # /
    2:  "andop",    # AND
    3:  "idiv",     # DIV
    4:  "imod",     # MOD
    5:  "plus",     # +
    6:  "minus",    # -
    7:  "orop",     # OR
    8:  "ltop",     # <
    9:  "leop",     # <=
    10: "geop",     # >=
    11: "gtop",     # >
    12: "neop",     # <>
    13: "eqop",     # =
    14: "inop",     # IN
    15: "noop",     # no operator
}

# The globals that hold a `set of symbol`, and are therefore the ones whose
# members should be printed by name. Each is initialised once in COMPINIT
# and then tested against `SY`. See SYMBOL_SETS below for the numbers.
SYMBOL_SET_NAMES = {
    "CONSTBEGSYS", "SIMPTYPEBEGSYS", "TYPEBEGSYS", "TYPEDELS",
    "BLOCKBEGSYS", "SELECTSYS", "FACBEGSYS", "STATBEGSYS",
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

    # The scanner's working set (finding 26). All six carry the same
    # operand number in 1.3 except LINENUMBER.
    1:   "SOURCEBUF",   # the source line buffer, indexed by CHINDEX
    2:   "CODEBUF",     # the code the compiler is generating, byte-indexed by
                        # CODEINX; FLUSHBUFFER writes it out 512 bytes at a
                        # time and raises error 402 if the write fails
    9:   "CODEINX",     # bytes currently in CODEBUF; EMIT appends one
    21:  "SEGSLOT",     # codefile slot for the segment being compiled, 0..15
    86:  "LCBASE",      # bytes of this procedure already flushed, so the
                        # current location counter is LCBASE + CODEINX
    90:  "SOURCEBLOCK", # next block number to read from the source file
    14:  "CHINDEX",     # scan position within SOURCEBUF
    16:  "OP",          # the operator qualifying SY; see OPERATORS
    22:  "LGTH",        # length of the scanned string or long constant
    23:  "VAL",         # the scanned value, or a pointer to it
    92:  "LINENUMBER",  # what `< n >` prints, and what {$D+} emits

    # The six `set of symbol` follow-sets, initialised in COMPINIT.9 and
    # each identified by the error its guard raises (finding 26).
    98:  "TYPEDELS",     # error 10, "Error in type"
    102: "STATBEGSYS",   # the statement loops
    106: "FACBEGSYS",    # error 58, "Error in factor (bad expression)"
    110: "SELECTSYS",    # error 59, "Error in variable"
    114: "BLOCKBEGSYS",  # error 18, "Error in declaration part"
    118: "TYPEBEGSYS",    # error 10, at the head of the type parser
    122: "SIMPTYPEBEGSYS",  # error 1, "Error in simple type"
    126: "CONSTBEGSYS",  # error 50, "Error in constant"

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

    # --- finding 28: the compiled-listing columns ----------------------------
    #
    # PASCALCO.4:ERRORWITHTEXT writes the listing line, and Part II of the
    # 1.3 manual says what its columns are: "the line number, the segment
    # number, the procedure number, and the number of bytes or words (bytes
    # for code, words for data) ... a D for declaration, or an integer from
    # 0 through 9 to designate the lexical level (the level of statement
    # nesting within the code part)". The routine writes exactly that, in
    # that order, so five globals are named by the vendor's own column
    # headings.
    13:  "SEGNUM",      # column 2. Was called LEVEL; see finding 28. This is
                        # what `SEGNUM := NEXTSEG` assigns, what indexes
                        # G479 to reach a codefile slot, and what
                        # ENDSEGMENT emits as the segment tail's low byte.
    97:  "PROCNUM",     # column 3, the procedure being compiled
    38:  "DP",          # true in a declaration part -- Pascal-P's `dp`.
                        # Selects the 'D' in column 4 and LC over CODEINX
                        # for column 5.
    79:  "LISTLEVEL",   # column 4's digit, `(LISTLEVEL mod 10) + 48`
    93:  "LISTCOUNT",   # column 5: LC in a declaration part, CODEINX in a
                        # body
    78:  "STATLEVEL",   # the live statement-nesting counter LISTLEVEL is
                        # latched from; +1/-1 around a structured statement
    10:  "LC",          # the data location counter, in words
    25:  "LCMAX",       # high-water mark of LC: `if LC > LCMAX then
                        # LCMAX := LC` at four sites, reset from LC at the
                        # head of each body. Zurich's `lcmax`; it becomes
                        # the procedure's data size in the attribute table.

    # --- finding 28: procedure numbering and the lexical level ---------------
    77:  "LEVEL",       # Zurich's `level`. 0 before the program heading, 1
                        # for the program block, +1 on entering a nested
                        # procedure and capped at 8, saved and restored
                        # across nesting. It is the LEX operand BODYPART.6
                        # emits into every LOD/LDA/STR, and BODY3.1 emits
                        # `LEVEL - 1` into the attribute table's LEX LEVEL
                        # byte -- which matches the manual's convention of
                        # 0 for a user program (IV-24).
    96:  "NEXTPROC",    # next free procedure number in this segment, 1-based
                        # and capped by ERROR(251) "Too many nested
                        # procedures or functions" at 149. ENDSEGMENT emits
                        # `NEXTPROC - 1` as the segment's procedure count.
    185: "PROCDICT",    # PROCDICT[n] is procedure n's attribute-table
                        # address, filled in by BODY3.1 and turned into
                        # self-relative pointers by ENDSEGMENT
    509: "JTABINX",     # next free long-jump slot, 1..24; ERROR(253)
                        # "Procedure too long" when it fills
    510: "JTABLE",      # the long-jump targets, emitted below JTAB-10

    # The four file variables (finding 10 listed them; finding 23 names them)
    535: "INFOFILE",   # *SYSTEM.INFO, the unit symbol-table work file
    586: "LIBFILE",    # SYSTEM.LIBRARY, or whatever $U filename named
    626: "SOURCEFILE",  # the program text, and the $I include file
    666: "LISTFILE",   # *SYSTEM.LST.TEXT, or whatever $L filename named
}

GLOBALS_13: dict[int, str] = {
    12: "INTPTR",
    15: "SY",

    # Finding 26. The scanner's globals did not move between releases
    # except the line counter; the six symbol sets all shifted by +3.
    1:   "SOURCEBUF",
    2:   "CODEBUF",
    9:   "CODEINX",
    14:  "CHINDEX",
    16:  "OP",
    21:  "SEGSLOT",
    22:  "LGTH",
    23:  "VAL",
    89:  "LCBASE",       # 1.1 global 86, +3
    93:  "SOURCEBLOCK",  # 1.1 global 90, +3
    95:  "LINENUMBER",   # 1.1 global 92, +3
    101: "TYPEDELS",     # 1.1 global 98,  +3
    105: "STATBEGSYS",   # 1.1 global 102, +3
    109: "FACBEGSYS",    # 1.1 global 106, +3
    113: "SELECTSYS",    # 1.1 global 110, +3
    117: "BLOCKBEGSYS",  # 1.1 global 114, +3
    121: "TYPEBEGSYS",     # 1.1 global 118, +3
    125: "SIMPTYPEBEGSYS",  # 1.1 global 122, +3
    129: "CONSTBEGSYS",  # 1.1 global 126, +3

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
    13:  "SEGNUM",
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

    # Finding 28, carried across by the correspondence table (every pair
    # below is a 1.00-similarity match).
    10:  "LC",
    25:  "LCMAX",
    39:  "DP",          # 1.1 global 38,  +1
    80:  "LEVEL",       # 1.1 global 77,  +3
    81:  "STATLEVEL",   # 1.1 global 78,  +3
    82:  "LISTLEVEL",   # 1.1 global 79,  +3
    96:  "LISTCOUNT",   # 1.1 global 93,  +3
    99:  "NEXTPROC",    # 1.1 global 96,  +3
    100: "PROCNUM",     # 1.1 global 97,  +3
    190: "PROCDICT",    # 1.1 global 185, +5
    627: "JTABINX",     # 1.1 global 509, +118
    628: "JTABLE",      # 1.1 global 510, +118
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
