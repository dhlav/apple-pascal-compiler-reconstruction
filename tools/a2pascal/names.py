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
    4:  "PRINTLINE", # listing-file error writer (finding 12, VERIFIED)
    5:  "ENTERID",       # enter an identifier record into the symbol table
    6:  "INSYMBOL",      # the scanner (finding 12)
    7:  "SEARCHSECTION", # single-scope identifier search (finding 12)
    8:  "SEARCHID",      # full symbol-table search (finding 12)
    9:  "GETBOUNDS",     # (fsp; var fmin, fmax)              finding 22
    15: "PAOFCHAR",      # is fsp a packed array of char?     finding 22
                         # Pascal-P calls this `string`, which Apple could
                         # not: STRING is predeclared, and shadowing it would
                         # take the *type* away from LIBNAME and CODECOMMENT.
                         # Finding 29.
    16: "STRGTYPE",    # is fsp a *declared* STRING?        finding 22
    17: "DECSIZE",      # words for an n-digit long integer  finding 22
    12: "CHECKEND",      # II.0's CHECKEND (procs.a.text:142), line for
                         # line: SCREENDOTS + 1, SYMCURSOR + 1, the
                         # progress dot and `<nnnn>` every 50 under NOISY,
                         # PRINTLINE under LIST, BPTONLINE := false,
                         # GETNEXTPAGE at end of buffer, then the tab and
                         # blank scan and LINEINFO := LC or IC. Was called
                         # NEXTLINE here, which described it but was not
                         # its name -- finding 37b.
    14: "SKIP",          # `while not (SY in fsys) do INSYMBOL` -- Pascal-P's
                         # error recovery, called after 37 of the ERROR sites
    # --- finding 27 ---------------------------------------------------------
    3:  "GETNEXTPAGE",     # read the next two source blocks into SOURCEBUF;
                         # error 401 "Unexpected end of input" if it cannot
    10: "BUMPSEG",       # (var n; limit, err) -- bounded increment. Both call
                         # sites are segment counters and both pass error 354,
                         # "Too many segments for segment dictionary".
    11: "NEWSEG",    # allocate the next segment number and codefile slot
    19: "COMPTYPES",     # Pascal-P's comptypes(fsp1, fsp2): boolean -- 35 call
                         # sites, recursive on `form`, with a pair list to
                         # terminate on mutually recursive pointer types
    21: "GENWORD",      # emit one word, byte-swapped under {$F+}
    24: "BLOCK",         # the outer block: dispatches `unitsy` to UNITPART and
                         # raises error 408, "(*$S+*) needed to compile units"
    26: "COMMENTER",       # scan a comment to its closing delimiter, which is the
                         # argument; a leading `$` goes to COMPOPTI.1
    18: "CONSTANT",      # parse a constant (fsys; var lsp, lvalu)
    20: "GENBYTE",          # the code-byte emitter (finding 12, VERIFIED)
    22: "WRITECODE",   # code-buffer flush (finding 12)
    27: "FINDFORW",   # undeclared-identifier reporter (finding 12)
    # --- finding 28 ---------------------------------------------------------
    13: "SEGINFO",       # build a segment dictionary's SEGINFO word: segment
                         # number in bits 0-7, machine type in 8-11 (2 =
                         # p-code LSB, or 1 = MSB under {$F+}), 0 in bit 12,
                         # version 2 in 13-15. The layout matches the one
                         # tools/a2pascal/codefile.py reads at block 0.
    23: "FINISHSEG",    # close the current segment: emit the procedure
                         # dictionary from PROCDICT, then the segment number
                         # and procedure count, record the segment's length
                         # and reset LCBASE. See tools/probes/probe_segtail.py
    25: "COMPILE",       # stamp the start time, call BLOCK with the outermost
                         # fsys, then FINISHUP.1 -- the whole compilation
    28: "HOLDMOST",      # hold DECLARAT, BODYPART, NUMSTRIN, STATEMEN,
                         # CASESTAT, FORSTATE, BODY1 and BODY3 in memory
                         # across the call to COMPILE. PASCALCO.1 takes this
                         # path unless {$S+}.
    29: "HOLDROUT",      # ...and ROUTINE as well, when the second
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
    3:  "GEN0",     # (op)             opcode alone; pads with NOP before LSA
    4:  "GENLDC",  # (v)              push integer v: short SLDC, or LDCI+NGI
    5:  "GEN1",    # (op, arg)        opcode + one operand byte
    6:  "GEN2",    # (op, lex, off)   picks the short form when it can
    25: "BODY",       # emits FINIT per file variable and the unit-init CXPs,
                      # then loops over statements while SY starts one
    27: "GENBIG",    # (n)  the BIG encoding: one byte, or two with bit 7 set
}

# --- finding 30: the segment procedures name themselves --------------------
#
# Procedure 1 of every segment is that segment's SEGMENT procedure, and the
# 1.3 manual says the codefile's SEGNAME field holds "the first eight
# characters of the user program, unit, SEGMENT procedure, SEGMENT function,
# or assembly-language procedure name that was translated into the
# corresponding segment". So these fifteen names are read straight off the
# segment dictionary. They are exact wherever the identifier was eight
# characters or fewer -- BODY1, BODY3 and ROUTINE -- and exact as far as
# Apple Pascal can tell for the rest, which is what matters, since the
# compiler distinguishes nothing beyond eight characters.
SEGMENT_PROCS: dict[str, str] = {
    "PASCALCO": "PASCALCOMPILER",   # the program itself; PASCALCO.1 is lex 0
    "COMPINIT": "COMPINIT", "DECLARAT": "DECLARATIONPART", "BODYPART": "BODYPART",
    "ROUTINE":  "ROUTINE",  "STATEMEN": "STATEMENT", "CASESTAT": "CASESTATEMENT",
    "FORSTATE": "FORSTATEMENT", "BODY1":    "BODY1",    "BODY3":    "BODY3",
    "WRITELIN": "WRITELINKERINFO", "UNITPART": "UNITPART", "COMPOPTI": "COMPOPTI",
    "NUMSTRIN": "NUMSTRIN", "FINISHUP": "FINISHUP",
}

# --- finding 31: the expression parser and the statement parser ------------
#
# Pascal-P spellings throughout. What licenses them is not resemblance but
# the segment dictionary: `CASESTAT` and `FORSTATE` are the first eight
# characters of two SEGMENT procedures (finding 30), and Pascal-P's names
# for those are `casestatement` and `forstatement`, which truncate to
# exactly that. Apple kept Zurich's statement names, so their siblings are
# Zurich's too.
#
# The expression chain is confirmed by the lexical levels rather than by
# the names: BODYPART.11 calls .33 calls .34 calls .35, at lex 2, 3, 4 and
# 5 -- each declared inside the one before, which is Pascal-P's nesting of
# expression / simpleexpression / term / factor exactly. `factor` recurses
# into `expression` for a parenthesised subexpression, and into itself.
STATEMENTS: dict[tuple[str, int], str] = {
    ("STATEMEN", 2): "ASSIGNMENT",   # the only child that parses a variable
                                     # and takes its identifier record
    ("STATEMEN", 3): "GOTOSTATEMENT",      # no expression, one EMITJUMP
    ("STATEMEN", 4): "COMPOUNDSTATEMENT",  # ERROR/INSYMBOL/STATEMENT only
    ("STATEMEN", 5): "IFSTATEMENT",        # thensy or ERROR(52); elsesy arm
    ("STATEMEN", 6): "REPEATSTATEMENT",    # untilsy or ERROR(53)
    ("STATEMEN", 7): "WHILESTATEMENT",     # dosy or ERROR(54)
    ("STATEMEN", 8): "WITHSTATEMENT",      # SEARCHID for the record fields
}

# BODYPART, 1.1 numbering. .33/.34/.35 shift by +1 in 1.3; the rest keep
# their numbers (the correspondence table matches .11 and .17 to
# themselves, and .8/.18/.19 are byte-identical at the same numbers).
EXPRESSIONS: dict[int, str] = {
    8:  "LOAD",        # Pascal-P's `load`: bring GATTR onto the stack. A
                       # case over GATKIND -- a constant becomes EMITCONST,
                       # NIL an LDCN, a real or a set a multi-word LDC, a
                       # variable `LOD GATLEVEL, GATDPLMT`.
    11: "EXPRESSION",  # parses through SIMPLEEXPRESSION, then a relational
                       # operator if SY = relop
    17: "GENFJP",      # LOAD, then ERROR(135) "Type of operand must be
                       # boolean" unless GATTYPTR = BOOLPTR, then FJP to the
                       # label. The spelling is ours; Pascal-P splits it.
    18: "GENLABEL",    # NEW(l, 3): a 3-word label record, undefined, with
                       # 28000 as the end-of-chain sentinel
    19: "PUTLABEL",    # define the label at CODEINX and walk its chain of
                       # forward references, patching each
    33: "SIMPLEEXPRESSION",
    34: "TERM",
    35: "FACTOR",
}

# --- finding 28b: the rest of the code-generation tail ---------------------
#
# These keep their numbers across releases (correspondence table:
# BODYPART.13 -> .13, BODYPART.16 -> .16).
#
# BODY3.1 is *not* in here. It emits the whole attribute table -- long-jump
# table, data size, param size, exit IC, enter IC, procedure number and LEX
# LEVEL, low address first -- so "ENDPROC" described it well, but it is the
# SEGMENT procedure of segment BODY3 and the codefile therefore names it:
# it is `BODY3`. Finding 30.
CODEGEN: dict[tuple[str, int], str] = {
    ("BODYPART", 13): "NEWPROC",       # assign the next procedure number to
                                       # an identifier record; ERROR(251) at
                                       # 149. Clears its PROCDICT slot.
    ("BODYPART", 16): "GENJMP",      # (op, target) -- short displacement if
                                       # it fits in 0..127, otherwise a slot
                                       # in JTABLE and a negative index
}

# --- finding 34: the declaration part -------------------------------------
#
# DECLARAT has twenty procedures in both releases, at the same numbers.
# Seventeen of them are UCSD II.0's, matched by parameter size, lexical
# nesting and call set (decpart.a/b/c.text); the other three are Apple's
# own factorings and carry spellings of ours, marked below.
#
# The lexical skeleton is II.0's exactly:
#
#     DECLARATIONPART(FSYS)                       lex 1
#       CHECKSYM(FSYS)                            lex 2   Apple's
#       TYP(FSYS; var FSP; var FSIZE)             lex 2
#         SIMPLETYPE(FSYS; var FSP; var FSIZE)    lex 3
#         PACKABLE(FSP): boolean                  lex 3
#         FIELDLIST(FSYS; var FRECVAR)            lex 3
#           ALLOCATE(FCP)                         lex 4
#           VARIANTLIST                           lex 4
#         POINTERTYPE                             lex 3
#       USESDECLARATION                           lex 2
#         ONEUNIT(var LNAME)                      lex 3   Apple's
#           GETTEXT(var FOUND)                    lex 4
#             FINDSEG(...)                        lex 5   Apple's
#               SEGSRCH(...)                      lex 6   Apple's
#       LABELDECLARATION                          lex 2
#       CONSTDECLARATION                          lex 2
#       TYPEDECLARATION                           lex 2
#       VARDECLARATION                            lex 2
#       PROCDECLARATION(FSY; SEGDEC)              lex 2
#         PARAMETERLIST(FSY; var FPAR; FCP)       lex 3
DECLARATIONS: dict[int, str] = {
    2:  "CHECKSYM",     # OURS. `if not (sy in fsys) then begin error(6);
                        # skip(fsys) end`, which II.0 writes inline at
                        # twenty-two sites. Twenty-one bytes, no locals,
                        # calls ERROR and SKIP and nothing else; the only
                        # procedure of that shape on either disk.
    3:  "TYP",          # 12 bytes of parameters; recursive; called by
                        # FIELDLIST, TYPEDECLARATION and VARDECLARATION
    4:  "SIMPLETYPE",   # 12 bytes; called by TYP alone
    5:  "PACKABLE",     # boolean function, recursive, and the only caller
                        # of GETBOUNDS in the segment -- II.0's PACKABLE
                        # calls GETBOUNDS twice and itself once
    6:  "FIELDLIST",    # setofsys + var stp = 10 bytes; calls TYP,
                        # ALLOCATE and VARIANTLIST
    7:  "ALLOCATE",     # (FCP: CTP); the only caller of PACKABLE besides
                        # PACKABLE itself
    8:  "VARIANTLIST",  # no parameters, calls FIELDLIST back
    9:  "POINTERTYPE",  # no parameters, called by TYP alone
    10: "USESDECLARATION",  # 514 bytes of locals: SEGDICT, the 512-byte
                        # library segment dictionary it BLOCKREADs into.
                        # II.0's MAGIC parameter is gone -- Apple has no
                        # implicit `uses turtlegraphics`.
    11: "ONEUNIT",      # OURS. Apple factored the else-arm of the repeat
                        # loop -- one unit of the uses list -- into a
                        # procedure taking ID by reference. Its first act
                        # is `MOV 4` of that address into local 2, II.0's
                        # `LNAME := ID`, and it then writes
                        # `<name> [nnnnn words]` exactly as II.0 does.
    12: "GETTEXT",      # (var FOUND); the only file I/O in the segment --
                        # RESET, CLOSE and BLOCKREAD of LIBRARY
    13: "FINDSEG",      # OURS. Calls SEGSRCH twice with different segment
                        # kinds and then sets up the text address.
    14: "SEGSRCH",      # OURS. `while (i <= MAXSEG) and not found` over
                        # SEGDICT.SEGNAME, with SEGDICT reached three lex
                        # levels up; II.0 writes this loop inline in
                        # GETTEXT.
    15: "LABELDECLARATION",  # no TYP, no ENTERID: labels only
    16: "CONSTDECLARATION",  # the only caller of CONSTANT here
    17: "TYPEDECLARATION",   # calls TYP and ENTERID
    18: "VARDECLARATION",    # calls TYP and ENTERID, and is the larger of
                        # the two -- it also runs the address-assignment
                        # walk of finding 33
    19: "PROCDECLARATION",   # (FSY: symbol; SEGDEC: boolean) = 4 bytes;
                        # the only caller of BUMPSEG and NEWSEG here, which
                        # is what `segment procedure` needs
    20: "PARAMETERLIST",     # 12 bytes; called by PROCDECLARATION alone
}

# --- finding 35: ROUTINE, the standard procedures and functions -----------
#
# The segment names itself (finding 30), and it is II.0's `ROUTINE(LKEY)`
# from bodypart.b.text -- but Apple could not leave it nested inside
# `CALL`, because a SEGMENT procedure that swaps in and out has to sit
# directly inside BODYPART. So ROUTINE.1 is at lex 2 and takes 12 bytes
# where II.0's takes 2: `FSYS` and `FCP` came down with it.
#
# Sixteen procedures sit at lex 3 beneath it. Twelve are II.0's, and each
# is fixed by the p-code it emits -- the CSP and CXP numbers are literal
# operands to GEN1 and GEN2, so the source's own comments name them:
#
#     ROUTINE.5   GEN1(30,1)                        CSP 1   NEW
#     ROUTINE.6   GEN1(30,10) (30,2) (30,3)         FLC MVL MVR
#     ROUTINE.7   GEN1(30,4)                        XIT
#     ROUTINE.8   GEN1(30,5) (30,6)                 UNITREAD UNITWRITE
#     ROUTINE.9   GEN2(56,0,LLC) ... CXP 0,23       SCONCAT
#     ROUTINE.10  CXP 0,25  0,29  0,26              SCOPY GOTOXY SDELETE
#     ROUTINE.11  GENLDC(18) GENLDC(12) + GENNR     DCVT DSTR
#     ROUTINE.12  CXP 0,6                           FCLOSE
#     ROUTINE.13  CXP 0,7  0,8  0,17                FGET FPUT
#     ROUTINE.14  GEN1(30,11)                       SCN
#     ROUTINE.15  CXP 0,28                          BLOCKIO
#     ROUTINE.16  (39 bytes, one CTP local)         SIZEOF
#
# in the source's own declaration order, which is also Apple's numbering.
ROUTINES: dict[int, str] = {
    2:  "GETCOMMA",   # OURS. 14 bytes: `if sy = comma then insymbol else
                      # error(20)`, which II.0 writes inline everywhere.
    3:  "CHECKINT",   # OURS. 9 bytes: `if GATTR.TYPTR <> INTPTR then
                      # error(125)`. Apple drops II.0's `<> nil` guard.
    4:  "STRGVAR",    # (fsys; mustbevar) = 10 bytes. EXPRESSION, STRGTYPE,
                      # LOADADDRESS, error 154 -- II.0's body exactly.
                      # II.0 declares it in CALL; Apple moved it in here,
                      # because four of ROUTINE's handlers need it.
    5:  "NEWSTMT",    # `new`, `mark`, `release`
    6:  "MOVE",       # `moveleft`, `moveright`, `fillchar`
    7:  "EXIT",       # SEARCHID for the procedure, then CSP 4
    8:  "UNITIO",     # `unitread`, `unitwrite`, `unitbusy`, `unitwait`
    9:  "CONCAT",
    10: "COPYDELETE", # `copy`, `delete`, `insert`, and `gotoxy`
    11: "STR",
    12: "CLOSE",
    13: "GETPUTETC",
    14: "SCAN",
    15: "BLOCKIO",
    16: "SIZEOF",
    17: "SPECIALS",   # OURS. II.0 writes these cases inline in CALL, in
                      # the `else` arm of `if LKEY in [...] then ROUTINE`:
                      # eof/eoln, pred/succ, ord, sqr, abs, length, insert,
                      # pos, idsearch, treesearch, time, open/reset/rewrite
                      # and trunc. Its 762 bytes emit CXP 0,10 0,11 0,24
                      # 0,27 0,4 0,5 and CSP 7 8 9 0 23 12, and GEN0 of
                      # ADI, SBI, SQI, SQR, ABI and ABR -- the source's
                      # cases in the source's order.
}

# --- finding 35b: the BODYPART routines ROUTINE's call sets force --------
#
# Each of these is pinned by which of ROUTINE's handlers calls it, matched
# against which of II.0's handlers calls what. LOADADDRESS and BYTEADDRESS
# are the pair worth spelling out: MOVE and SCAN call one, CLOSE and
# GETPUTETC call the other, BLOCKIO calls both in that order -- exactly as
# bodypart.b.text has them.
BODYPART_MORE: dict[int, str] = {
    2:  "LINKERREF",   # (klass; id, addr) = 6 bytes; the only BLOCKIO in
                       # BODYPART -- it appends to REFFILE. Called by GEN1
                       # and by EXIT, both of which II.0 has calling it.
    7:  "GENNR",       # II.0's role, not II.0's body: it records a
                       # non-resident support segment and emits the call
                       # to it. Apple emits `GEN2(77 CXP, seg, proc)` and
                       # tracks the segments in a two-word set at global
                       # 183, where II.0 emits `GEN1(79 CGP, PFNUMOF[..])`
                       # and keeps PFNUMOF. Apple has no PFNUMOF -- see
                       # finding 33c's open question. Called from LOAD,
                       # EXPRESSION, SIMPLEEXPRESSION, TERM, ASSIGNMENT,
                       # STR and the read/write handlers: II.0's GENNR
                       # sites exactly.
    9:  "LOADADDRESS",
    10: "BYTEADDRESS",
    12: "VARIABLE",    # (fsys) = 8 bytes, 39 bytes long: SEARCHID, else
                       # error(2) and UVARPTR, then SELECTOR. Four lines
                       # in II.0 and four here.
    22: "SELECTOR",    # (fsys; fcp) = 10 bytes, and the largest procedure
                       # in BODYPART; VARIABLE's only callee
}

# --- finding 36: the rest of BODYPART ------------------------------------
#
# With these, all 37 of BODYPART's procedures are named (38 in 1.3).
#
# The shape of the segment is II.0's, with one large exception. II.0's
# `BODY` is a single procedure; Apple split it into four, and named two of
# the pieces itself: the codefile carries SEGMENT procedures BODY1 and
# BODY3 (finding 30). All three pieces sit at lex 3 as siblings inside
# BODYPART.24, which holds the 38 bytes of locals they share -- so
# BODYPART.24 is `BODY`, and the middle piece, between BODY1 and BODY3,
# is BODY2. That is inference from the two names Apple did leave behind,
# not a reading of the binary.
def bp13(n: int) -> int:
    """1.1's BODYPART numbering in 1.3.

    1.3 has 38 procedures where 1.1 has 37, and the insertion is at 26: a
    26-byte procedure at lex 4 nested inside BODY2, with no counterpart in
    1.1. Everything from 1.1's 26 upward therefore shifts by one, which is
    what the attribute tables show pair for pair -- 1.1's HOLDSTMT (0
    params, lex 3, 4 bytes) is 1.3's 27, GENBIG (2 params, 31 bytes) its
    28, and READ, WRITE and CALLNONSPECIAL its 29, 30 and 31.
    """
    return n + 1 if n >= 26 else n


BODYPART_REST: dict[int, str] = {
    14: "LOADIDADDR",  # (fcp) -- `if klass = actualvars then GEN2(50 LDA,
                       # ...) else GEN2(54 LOD, ...)`, II.0's body with the
                       # VLEV = 1 short forms dropped. Called by READ,
                       # WRITE and SPECIALS -- II.0's three call sites.
    15: "MASKBOOL",    # OURS. 16 bytes: `if GATTR.TYPTR = BOOLPTR then
                       # begin GENBYTE(1); GENBYTE(132) end`, which emits
                       # `SLDC 1; LAND` -- a boolean masked to 0/1 before
                       # it is used as an ordinal. Called from EXPRESSION,
                       # SELECTOR, FACTOR, CASESTATEMENT and
                       # FORSTATEMENT. II.0 has no counterpart.
    20: "STORE",       # (var fattr) = 2 bytes; called by ASSIGNMENT and
                       # FORSTATEMENT, II.0's two call sites
    21: "STRGTOPA",    # (fic) = 2 bytes, and calls nothing at all -- it
                       # patches code already emitted. Called from
                       # EXPRESSION, CALLNONSPECIAL and ASSIGNMENT.
    23: "CALL",        # (fsys; fcp) = 10 bytes; calls READ, WRITE,
                       # CALLNONSPECIAL and ROUTINE.1 -- II.0's CALL
                       # exactly, minus the arms that went into ROUTINE
    24: "BODY",        # 38 bytes of locals, and calls BODY1, BODY2 and
                       # BODY3 in that order
    25: "BODY2",       # the middle of Apple's split; the NOISY
                       # `<name> [nnnnn words]` line and the statement loop
    26: "HOLDSTMT",    # OURS. LOADSEGMENT(11 = STATEMEN); BODY2;
                       # UNLOADSEGMENT(11). BODY takes this path under
                       # {$S+}. Compare PASCALCO.28 HOLDMOST.
    28: "READ",
    29: "WRITE",       # the only caller of DECSIZE here -- writing a long
                       # integer needs its digit count -- and of PAOFCHAR
    30: "CALLNONSPECIAL",  # calls LINKERREF and NEWPROC, which is what a
                       # call to a not-yet-declared or separate procedure
                       # needs; 640 bytes, the largest of the three
    31: "FLOATIT",     # (var fsp; forcefloat) = 4 bytes
    32: "STRETCHIT",   # (var fsp) = 2 bytes
    36: "MAKEPA",      # (var strgfsp; pafsp) = 4 bytes
    37: "HOLDRTN",     # OURS. LOADSEGMENT(10 = ROUTINE); BODY;
                       # UNLOADSEGMENT(10). BODYPART.1 takes this path when
                       # swapping is on and {$S++} is off -- the same
                       # division PASCALCO.28/.29 make one level up.
}

# --- finding 37: the remaining segments -----------------------------------
#
# COMPINIT is II.0's, procedure for procedure and in II.0's order: the
# segment procedure calls exactly seven nested procedures, which is what
# compinit.text declares. The two that are not II.0's, .5 and .6, are one
# space optimisation -- rather than an eight-byte string constant per
# standard identifier, Apple packs the names into one dotted literal and
# pulls them out again.
COMPINITS: dict[int, str] = {
    2:  "ENTSTDTYPES",   # calls DECSIZE, which the long-integer
                         # descriptor needs, and nothing else
    3:  "ENTSTDNAMES",   # 14 string literals, and ENTERID
    4:  "ENTUNDECL",     # builds the `undeclared` records; the only one
                         # of the seven that calls nothing at all
    5:  "PUTNAMES",      # OURS. Append a literal batch of `.`-separated
                         # names to the pool at local 1, bounded at 511.
                         # ENTSPCPROCS calls it five times, ENTSTDPROCS
                         # twice, each with one string constant.
    6:  "NEXTNAME",      # OURS. (var name) -- blank the eight characters,
                         # SCAN to the next `.`, MOVELEFT the name out,
                         # step the cursor past it. Called once each, from
                         # inside the loop.
    7:  "ENTSPCPROCS",
    8:  "ENTSTDPROCS",
    9:  "INITSCALARS",   # stores into 40-odd scalar globals and calls
                         # nothing
    10: "INITSETS",      # `LAO 126; LDC 4w; STM 4` and the rest -- the
                         # eight `set of symbol` follow-sets, four words
                         # each. Finding 26c said COMPINIT.9; it is .10.
}

# WRITELIN is II.0's WRITELINKERINFO with its two nested procedures, and
# the nesting is the giveaway: GETNEXTBLOCK is the only thing at lex 3 in
# the segment and the only BLOCKIO, and GLOBALSEARCH recurses -- it walks
# the symbol tree -- and calls GETREFS, which is II.0's arrangement.
WRITELINS: dict[int, str] = {
    2: "GETREFS",        # (id, length) in II.0; Apple passes one word
    3: "GETNEXTBLOCK",
    4: "GLOBALSEARCH",   # (fcp), recursive, and WRITELINKERINFO's only
                         # callee here
}

UNITPARTS: dict[int, str] = {
    2: "OPENREFFILE",    # the only FOPEN in the segment
    3: "UNITDECLARATION",  # (fsys; var umarkp) = 10 bytes
    4: "UNITBODY",       # OURS. II.0 compiles the implementation inline
                         # in UNITPART's body; Apple factored it out. The
                         # only caller of BODYPART outside PASCALCO.
}

# NUMSTRIN is the scanner's two sub-scanners, made a segment of their own:
# II.0's STRING and NUMBER (procs.a.text:265 and :302), which INSYMBOL
# calls. NUMSTRIN.1 is a two-line dispatcher, `if flag then NUMBER else
# STRING`, and INSYMBOL passes 0 at one site and 1 at the other.
#
# STRING shadows the predeclared type name, which is legal here and safer
# than it was in II.0: Apple has it at lex 2 inside NUMSTRIN, so the
# shadow cannot reach the STRING-typed globals. See finding 35c.
NUMSTRINS: dict[int, str] = {
    2: "STRING",         # calls ERROR and CHECKEND, II.0's STRING exactly
                         # -- `error(202); CHECKEND; goto 1` on an
                         # unterminated string. 90 bytes of locals for
                         # II.0's `T: packed array [1..80] of char`.
    3: "NUMBER",         # calls ERROR alone; 643 bytes, the real and
                         # long-integer conversion
}

# COMPOPTI has no counterpart at all: II.0 handles compiler options inline
# in COMMENTER. All three spellings are ours.
# BODY3 is the tail of II.0's BODY, from `if sy = endsy` to WRITECODE,
# and BODY3.1 emits it in II.0's order step for step. BODY3.2 is Apple's:
# it emits GEN1(30, 21 GETSEG) and GEN1(30, 22 RELSEG) for the units in
# USINGLIST, four of each, with GENLABEL/PUTLABEL/GENJMP(57 UJP) around
# them. II.0 emits the GETSEG loop at the head of BODY and the RELSEG loop
# at the tail; Apple emits both from here.
BODY3S: dict[int, str] = {2: "UNITSEGS"}      # OURS

COMPOPTIS: dict[int, str] = {
    2: "BADOPT",         # OURS. Eight bytes: clear a flag in COMPOPTI's
                         # frame, then `CSP 4` EXIT of segment 18
                         # procedure 1 -- abandon the option
    3: "OPTWORD",        # OURS. SCAN past blanks, then to the delimiter
                         # in the parameter, and hand back the substring
    4: "OPTLIST",        # OURS. INSYMBOL round a list, taking intconst
                         # and identifiers; the only SEARCHID here
}

PROC_NAMES: dict[str, dict[tuple[str, int], str]] = {
    "1.1": {(seg, 1): s for seg, s in SEGMENT_PROCS.items()}
           | {("PASCALCO", n): s for n, s in PASCALCO_11.items()}
           | {("BODYPART", n): s for n, s in BODYPART_EMIT.items()}
           | {("BODYPART", n): s for n, s in EXPRESSIONS.items()}
           | {("BODYPART", n): s for n, s in BODYPART_REST.items()}
           | STATEMENTS
           | CODEGEN
           | {("DECLARAT", n): s for n, s in DECLARATIONS.items()}
           | {("ROUTINE", n): s for n, s in ROUTINES.items()}
           | {("COMPINIT", n): s for n, s in COMPINITS.items()}
           | {("WRITELIN", n): s for n, s in WRITELINS.items()}
           | {("UNITPART", n): s for n, s in UNITPARTS.items()}
           | {("NUMSTRIN", n): s for n, s in NUMSTRINS.items()}
           | {("COMPOPTI", n): s for n, s in COMPOPTIS.items()}
           | {("BODY3", n): s for n, s in BODY3S.items()}
           | {("BODYPART", n): s for n, s in BODYPART_MORE.items()}
           ,
    # BODYPART keeps these numbers in 1.3 except 27, which becomes 28; the
    # correspondence table matches 3..6 and 25 to themselves.
    # The segment procedures keep procedure number 1 in 1.3 too: the two
    # natives take PASCALCO.2 and .3, not .1.
    "1.3": {(seg, 1): s for seg, s in SEGMENT_PROCS.items()}
           | {("PASCALCO", n): s for n, s in PASCALCO_13.items()}
           | {("BODYPART", bp13(n)): s for n, s in BODYPART_EMIT.items()}
           | {("BODYPART", bp13(n)): s for n, s in EXPRESSIONS.items()}
           | {("BODYPART", bp13(n)): s for n, s in BODYPART_REST.items()}
           | STATEMENTS
           | CODEGEN
           | {("DECLARAT", n): s for n, s in DECLARATIONS.items()}
           | {("ROUTINE", n): s for n, s in ROUTINES.items()}
           | {("COMPINIT", n): s for n, s in COMPINITS.items()}
           | {("WRITELIN", n): s for n, s in WRITELINS.items()}
           | {("UNITPART", n): s for n, s in UNITPARTS.items()}
           | {("NUMSTRIN", n): s for n, s in NUMSTRINS.items()}
           | {("COMPOPTI", n): s for n, s in COMPOPTIS.items()}
           | {("BODY3", n): s for n, s in BODY3S.items()}
           | {("BODYPART", n): s for n, s in BODYPART_MORE.items()}
           ,
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
    49: "usessy",       50: "unitsy",
    # These four cannot follow Pascal-P's `<word>sy` convention, because
    # Apple Pascal keeps only the first eight significant characters and
    # `interfacesy` etc. would then *be* the reserved words INTERFACE,
    # IMPLEMENTATION, EXTERNAL and OTHERWISE -- unwritable as identifiers.
    # Abbreviating is in keeping with the convention rather than against
    # it: Pascal-P already writes `progsy`, `procsy` and `funcsy` for
    # PROGRAM, PROCEDURE and FUNCTION. The four spellings below are
    # SPECULATION; that the originals were *not* the unabbreviated forms
    # is a VERIFIED BINARY FACT. See finding 29.
    51: "intersy",      52: "implesy",
    53: "externlsy",     54: "otherwsy",     # OTHERWISE is 1.3-only
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
    1:   "SYMBUFP",   # the source line buffer, indexed by CHINDEX
    2:   "CODEP",     # the code the compiler is generating, byte-indexed by
                        # CODEINX; FLUSHBUFFER writes it out 512 bytes at a
                        # time and raises error 402 if the write fails
    9:   "IC",     # bytes currently in CODEBUF; EMIT appends one
    21:  "SEGSLOT",     # codefile slot for the segment being compiled, 0..15
    86:  "SEGINX",      # bytes of this procedure already flushed, so the
                        # current location counter is LCBASE + CODEINX
    90:  "SYMBLK", # next block number to read from the source file
    14:  "SYMCURSOR",     # scan position within SOURCEBUF
    16:  "OP",          # the operator qualifying SY; see OPERATORS
    22:  "LGTH",        # length of the scanned string or long constant
    23:  "VAL",         # the scanned value, or a pointer to it
    92:  "SCREENDOTS",  # what `< n >` prints, and what {$D+} emits

    # The eight `set of symbol` follow-sets, initialised in
    # COMPINIT.10:INITSETS -- finding 26c said .9, which is INITSCALARS
    # (finding 37a) -- and each identified by the error its guard raises.
    98:  "TYPEDELS",     # error 10, "Error in type"
    102: "STATBEGSYS",   # the statement loops
    106: "FACBEGSYS",    # error 58, "Error in factor (bad expression)"
    110: "SELECTSYS",    # error 59, "Error in variable"
    114: "BLOCKBEGSYS",  # error 18, "Error in declaration part"
    118: "TYPEBEGSYS",    # error 10, at the head of the type parser
    122: "SIMPTYPEBEGSYS",  # error 1, "Error in simple type"
    126: "CONSTBEGSYS",  # error 50, "Error in constant"

    54: "STRGPTR",    # STRING    the standard string[80] descriptor
    55: "INTRACTVPTR",     # INTERACTIVE
    56: "NILPTR",       # form pointer, element type nil
    57: "TEXTPTR",      # TEXT
    58: "BOOLPTR",      # BOOLEAN   scalar, scalkind = declared
    59: "CHARPTR",      # CHAR
    60: "LONGINTPTR",      # the default long-integer type, form 3
    61: "REALPTR",      # REAL      size 2 words
    66: "OUTPUTPTR",    # the OUTPUT file's identifier record
    67: "INPUTPTR",     # the INPUT file's identifier record

    # --- finding 34c: four globals the II.0 alignment predicted -------------
    # Each was placed by reading DECLARAT.10:USESDECLARATION against II.0's
    # source line for line, and each lands exactly where the drift column of
    # analysis/global_map/vardecl-ii0.txt said it would.
    91:  "STARTDOTS",   # II.0 85, drift +6 -- the dot count when the page
                        # began; CHECKEND breaks the line every 50 dots
                        # since it
    44:  "LINKINFO",    # OURS. Apple merged II.0's two flags into one:
                        # PROCDECLARATION and USESDECLARATION set it, which
                        # is II.0's DLINKERINFO, and NEWPROC sets it too,
                        # which is II.0's CLINKERINFO. Cleared by COMPINIT
                        # and by WRITELINKERINFO; read by BLOCK, UNITPART
                        # and FINISHUP. Finding 36c.
    11:  "TEST",        # II.0 11, drift +0 -- the parsers' loop flag
    36:  "USING",       # II.0 35, drift +1 -- inside a `uses` of a unit that
                        # the enclosing program already listed
    63:  "USINGLIST",   # II.0 59, drift +4 -- the units named so far
    68:  "MODPTR",      # II.0 64, drift +4 -- the units already compiled;
                        # GETTEXT walks it looking for LNAME

    # Compiler-option state (finding 23). COMPOPTI.1 switches on the
    # upper-cased option letter, so each of these is tied to its letter by
    # the case table itself; the spellings are ours, the letters are not.
    28:  "SYSCOMP",     # $U-, compile at the system lexical level
    30:  "FLIPBYTES",       # $F, emit byte-swapped p-code (finding 24a)
    # Unit-compilation state. Written only in UNITPART, and UNITPART.3 --
    # which errors 182 if INUNIT is already set, i.e. no nested units --
    # saves LEVEL and the segment counter and then sets INUNIT, clears
    # ININTERFACE. ININTERFACE goes true between the unit heading and
    # `SY = IMPLEMENTATION`. Finding 24b.
    31:  "ININTERFACE",
    32:  "INMODULE",
    33:  "SWAPMORE",    # $S++, the second swapping flag
    34:  "SWAPPING",    # $S, selects PASCALCO.25 over PASCALCO.28
    35:  "NOLOAD",      # $N
    39:  "VARSTRG",   # $V
    42:  "TINY",       # $T, undocumented
    43:  "LIST",     # $L
    45:  "OPT_E",       # $E, undocumented
    47:  "IOCHECK",     # $I
    49:  "NOISY",  # NOT $Q -- true when quiet compiling is off
    50:  "DEBUGGING",       # $D, undocumented
    51:  "RANGECHECK",  # $R
    52:  "GOTOOK",      # $G
    85:  "NEXTSEG",     # $NS n, default 7, rejected unless < 31
    487: "COMMENT",  # $C, the 80-character codefile comment
    488: "SYSTEMLIB",    # $U filename, the library to search for units

    # --- finding 31: GATTR, Pascal-P's `gattr` -------------------------------
    #
    # The global map had already sized word 3 as a 5-word record "MOV 5
    # word(s) x7 ... words 4..7 are also addressed individually, so these
    # are its fields", at 202 accesses -- the most-used global in the
    # compiler. BODYPART.8:LOAD says what the fields are: it switches on
    # word 4 and, in the variable arm, emits `LOD <word 6>, <word 7>`,
    # which only a lexical level and an offset can be. That is Pascal-P's
    #     attr = record typtr: stp; case kind: attrkind of
    #                    cst:   (cval: valu);
    #                    varbl: (vlevel: levrange; dplmt: addrrange) end
    # field for field and in order. The GAT prefix is ours; the fields are
    # Pascal-P's.
    3:   "GATTYPTR",   # the type of the expression built so far
    4:   "GATKIND",    # 0 = cst, and the case selector in LOAD
    5:   "GATCVAL",    # a constant's value
    6:   "GATVLEV",   # a variable's lexical level -- LOD's first operand
    7:   "GATDPLMT",   # ...and its offset -- LOD's second

    # --- finding 32: named from the UCSD II.0 compiler source ---------------
    8:   "TOP",         # top of DISPLAY -- DISPLAY[TOP] is indexed by it
    46:  "BPTONLINE",   # PRINTLINE prints '*' instead of ':' when set
    48:  "CODEINSEG",   # FINISHSEG clears it; true once a segment has code
    95:  "LINESTART",   # SYMBUFP index where the current line begins
    131: "DISPLAY",     # ARRAY [DISPRANGE] OF a 4-word record, indexed by TOP
    335: "SEGTABLE",    # ARRAY [SEGRANGE] OF (DISKADDR, CODELENG, SEGNAME,
                        # SEGKIND, TEXTADDR); Apple's entry is 9 words
    479: "SEGMAP",   # Apple-only: SEG -> SEGTABLE index, 4 bits per entry.
                        # II.0 needs none, because SEGRANGE is 0..MAXSEG and
                        # SEG indexes SEGTABLE directly; Apple lets segment
                        # numbers run past 15 (finding 27a) and so must map.

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
    13:  "SEG",      # column 2. Was called LEVEL; see finding 28. This is
                        # what `SEGNUM := NEXTSEG` assigns, what indexes
                        # G479 to reach a codefile slot, and what
                        # ENDSEGMENT emits as the segment tail's low byte.
    97:  "CURPROC",     # column 3, the procedure being compiled
    38:  "DP",          # true in a declaration part -- Pascal-P's `dp`.
                        # Selects the 'D' in column 4 and LC over CODEINX
                        # for column 5.
    79:  "BEGSTMTLEV",   # column 4's digit, `(LISTLEVEL mod 10) + 48`
    93:  "LINEINFO",   # column 5: LC in a declaration part, CODEINX in a
                        # body
    78:  "STMTLEV",   # the live statement-nesting counter LISTLEVEL is
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
    185: "PROCTABLE",    # PROCDICT[n] is procedure n's attribute-table
                        # address, filled in by BODY3.1 and turned into
                        # self-relative pointers by ENDSEGMENT
    509: "NEXTJTAB",     # next free long-jump slot, 1..24; ERROR(253)
                        # "Procedure too long" when it fills
    510: "JTAB",      # the long-jump targets, emitted below JTAB-10

    # The four file variables (finding 10 listed them; finding 23 names them)
    535: "REFFILE",   # *SYSTEM.INFO, the unit symbol-table work file
    586: "LIBRARY",    # SYSTEM.LIBRARY, or whatever $U filename named
    626: "INCLFILE",  # the program text, and the $I include file
    666: "LP",   # *SYSTEM.LST.TEXT, or whatever $L filename named

    # --- finding 38: the source-switching block, 575..585 --------------------
    #
    # Eleven consecutive words holding II.0's ten (compglbls.text 344-351)
    # plus exactly one Apple insertion. Every II.0 name lands, and none of
    # them was placed by declaration order: the six save slots were assigned
    # by which global each one is copied back into (SYMBLK 90, SYMCURSOR 14,
    # LINESTART 95) and by which routine saves it. GETNEXTPAGE restores
    # PREV* when USING goes false and OLD* when INCLUDING does; GETTEXT
    # (DECLARAT.12) saves the PREV set and COMPOPTI.1's `$I` arm saves the
    # OLD set, exactly as procs.a.text and decpart.b.text do it. Laid out
    # that way they come out in II.0's reverse-allocated declaration order
    # at a constant drift of +27, which is the check that could have failed.
    575: "REFBLK",    # next *SYSTEM.INFO block to write; LINKERREF flushes
                      # REFLIST^ to it and bumps it
    576: "NREFS",     # entries used in REFLIST^, 1-based, reset to 1 on flush
    577: "REFLIST",   # ^REFARRAY -- the only one of the three whose address
                      # is taken, and only to pass to NEW
    578: "TEXTSTRT",  # OURS. Apple-only, and the one insertion in this run.
                      # SYMBUFP offset of the first interface-text byte not
                      # yet captured. II.0's GETNEXTPAGE calls WRITETEXT at
                      # the bottom; Apple's hoists it to the top and copies
                      # SYMBUFP^[TEXTSTRT] onward into CODEP^ first, then
                      # clears it. UNITPART sets it to SYMCURSOR to start
                      # the capture and ends with IC := SYMCURSOR-TEXTSTRT+10.
    579: "PREVSYMBLK",      # PREVSYMBLK := SYMBLK - 2 in GETTEXT -- the
                            # `SLDC 2; SBI` is in the binary
    580: "OLDSYMBLK",       # likewise OLDSYMBLK := SYMBLK - 2, in COMPOPTI
    581: "PREVLINESTART",
    582: "PREVSYMCURSOR",
    583: "OLDLINESTART",
    584: "OLDSYMCURSOR",
    585: "USEFILE",   # II.0's UNITFILE = (WORKCODE,SYSLIBRARY); Apple adds a
                      # third enumerator. GETTEXT stores 0 for a unit already
                      # in the workfile, 2 when the $U library's segment
                      # dictionary reads, and 1 after falling back to
                      # '*SYSTEM.LIBRARY'. Only `= WORKCODE` is ever tested.

    # --- finding 38: the segments-used set, and what it replaced ------------
    #
    # II.0 declares PFNUMOF: NONRESPFLIST here, six words, and BODYPART's
    # GENNR emits `GEN1(79 CGP, PFNUMOF[extproc])`. Apple emits
    # `GEN2(77 CXP, seg, proc)` instead and has no PFNUMOF at all; in its
    # place, at the same declaration position, sits a two-word set of the
    # segments the code emitted so far calls into. That is the whole of the
    # +6 -> +2 drift step at PROCTABLE: -6 words of PFNUMOF, +2 of set.
    183: "SEGSUSED",  # OURS. SET OF 0..31. BODYPART.7's entire body is
                      # `SEGSUSED := SEGSUSED + [seg]` followed by the
                      # GEN2(77) that needs it; ONEUNIT adds SEG and
                      # NEXTSEG's slot; UNITSEGS walks it downward emitting
                      # GETSEG/RELSEG; FINISHUP tests `31 in SEGSUSED`.

    37:  "INCLUDING",  # II.0 36, drift +1 -- inside a $I include file.
                       # GETNEXTPAGE's `if not (INCLUDING or USING)` is
                       # `LDO 37; LDO 36; LOR; LNOT` in the binary.

    # --- finding 39: the stretches between the matched drift runs ------------
    #
    # Each of these sits in a gap the drift column bounds on both sides, so
    # the count of Apple words equals the count of II.0 names and the order
    # is forced. The comment on each is the behaviour that confirms it
    # independently of that arithmetic.
    17:  "ID",         # ALPHA, 4 words. compglbls.text says of the four
                       # before it: "SCANNER GLOBALS...NEXT FOUR VARS MUST
                       # BE IN THIS ORDER FOR IDSEARCH" -- SYMCURSOR, SY,
                       # OP, ID, which is Apple's 14, 15, 16, 17 exactly.
    24:  "DISX",       # SEARCHID is `for DISX := TOP downto 0 do LCP :=
                       # DISPLAY[DISX].FNAME`: `SLDO 8; SRO 24` then
                       # `LAO 131; LDO 24; IXA 4; SIND 0`
    26:  "GETSTMTLEV", # INSYMBOL opens with `if GETSTMTLEV then begin
                       # BEGSTMTLEV := STMTLEV; GETSTMTLEV := false end`
                       # -- `LDO 26; FJP; LDO 78; SRO 79; SLDC 0; SRO 26`
    27:  "PUBLICPROCS",  # set under `ININTERFACE and not USING` in
                         # DECLARATIONPART, cleared by UNITDECLARATION,
                         # tested by UNITPART
    29:  "LIBNOTOPEN",   # GETTEXT's `if LIBNOTOPEN then RESET(LIBRARY...)`,
                         # cleared on success; COMPINIT sets it true
    40:  "LSEPPROC",   # GETTEXT sets it from the used unit's SEGKIND and
                       # then `if not LSEPPROC then begin SEG := NEXTSEG;
                       # NEXTPROC := 1 end`
    41:  "INTRINSIC",  # OURS, but Apple's word: UNITDECLARATION sets it
                       # where the binary compares ID against the literal
                       # 'INTRINSI'. It stands in II.0's SEPPROC slot and
                       # inherits its uses -- SEGKIND, the LINKERREF guard,
                       # cleared beside INMODULE at the end of UNITPART --
                       # but Apple drives it from `INTRINSIC CODE n DATA m`,
                       # not from II.0's `SEPARATE`. See [[finding-39]].
    62:  "RESIDENT",   # OURS, but the manual's word. Apple-only, and the
                       # one insertion between REALPTR and USINGLIST.
                       # COMPOPTI.1's XJP runs 'C'..'V' and the 'R' arm is
                       # `if (SW='+') or (SW='-') then RANGECHECK := (SW='+')
                       # else OPTLIST` -- the manual's second $R:
                       # "$R unit name or $R segment number ... Load
                       # segment", and "can be applied to more than one
                       # segment, by separating the names ... with commas",
                       # which is why OPTLIST loops taking identifiers and
                       # intconsts. "The resident option must immediately
                       # follow the BEGIN that starts the procedure body",
                       # and BODY1 reads this list at exactly that point;
                       # BLOCK and UNITBODY clear it to NIL per body.
    53:  "PRTERR",     # SEARCHID ends `if PRTERR then ERROR(104)`, which is
                       # "Undeclared identifier"
    64:  "FWPTR",      # the forward-declaration list head
    65:  "OUTERBLOCK", # `NEW(g65, 18)` -- a PROC record, the largest
                       # variant -- and BLOCK's
                       # `TOS^.PREVLEXSTACKP^.DFPROCP = OUTERBLOCK`

    # ENTUNDECL NEWs the six undeclared-id pointers in one run, and the
    # record size it asks for names each one: TYPES 9, KONST 10,
    # ACTUALVARS 11, FIELD 13, PROC 18, FUNC 18. Apple's run is
    # `NEW(75,9); NEW(74,10); NEW(73,11); NEW(71,13); NEW(70,18);
    # NEW(69,18)`, in II.0's declaration order.
    69:  "UFCTPTR",
    70:  "UPRCPTR",
    71:  "UFLDPTR",
    # 72 is declared but never referenced -- no LDO/SRO/LAO touches it on
    # either disk. It is the one word of this stretch Apple added, and the
    # binary cannot say what for.
    73:  "UVARPTR",
    74:  "UCSTPTR",
    75:  "UTYPPTR",
    76:  "GLOBTESTP",  # II.0's "LAST TESTPOINTER"

    # The lex stack, all four confirmed inside PASCALCO.24 BLOCK, which is
    # block.text line for line.
    80:  "MARKP",      # the only `CSP 32 MARK` in the compiler
    81:  "TOS",        # `RELEASE(TOS^.DMARKP); TOS := TOS^.PREVLEXSTACKP`
                       # = `LDO 81; INC 8; CSP 33 RELEASE; LDO 81; IND 10;
                       # SRO 81`
    82:  "GLEV",
    83:  "NEWBLOCK",   # BLOCK's `NEWBLOCK := true; if not NEWBLOCK then`
    84:  "DATASEG",    # OURS. Apple-only, and the one insertion in this
                       # stretch. UNITDECLARATION's `DATA` clause reads a
                       # constant into it, errors 203 unless it is in
                       # 0..31, defaults it to SEG+1, and then does
                       # SEGMAP[DATASEG] := SEGSLOT. SEG is the unit's code
                       # segment; this is its data segment.

    87:  "SCONST",     # `NEW(SCONST, 130)` -- INSYMBOL's string result
    88:  "STRGCSTIC",  # `STRGCSTIC := IC`, the address of the last string
                       # placed in the code
    89:  "SMALLESTSPACE",   # `CSP 40 MEMAVAIL; SRO 89`
    94:  "LOWTIME",    # the only `CSP 9 TIME`, which takes it by reference
    130: "VARS",       # SETOFIDS, one word: built by COMPINIT with
                       # `ADJ 1; SRO 130` and tested with `LDO 130; SLDC 1;
                       # INN`

    967: "CURBLK",     # COMPINIT's `CURBLK := 1; CURBYTE := 0` is
    968: "CURBYTE",    # `SLDC 1; SRO 967; SLDC 0; SRO 968`, right after
                       # `NEXTSEG := 10` -- compinit.text line 258 in order
    969: "DISKBUF",    # PACKED ARRAY [0..511] OF CHAR: CURBYTE is compared
                       # against 512 and used as its byte index
}

GLOBALS_13: dict[int, str] = {
    12: "INTPTR",
    15: "SY",

    # Finding 26. The scanner's globals did not move between releases
    # except the line counter; the six symbol sets all shifted by +3.
    1:   "SYMBUFP",
    2:   "CODEP",
    9:   "IC",
    14:  "SYMCURSOR",
    16:  "OP",
    21:  "SEGSLOT",
    22:  "LGTH",
    23:  "VAL",
    89:  "SEGINX",       # 1.1 global 86, +3
    93:  "SYMBLK",  # 1.1 global 90, +3
    95:  "SCREENDOTS",   # 1.1 global 92, +3
    101: "TYPEDELS",     # 1.1 global 98,  +3
    105: "STATBEGSYS",   # 1.1 global 102, +3
    109: "FACBEGSYS",    # 1.1 global 106, +3
    113: "SELECTSYS",    # 1.1 global 110, +3
    117: "BLOCKBEGSYS",  # 1.1 global 114, +3
    121: "TYPEBEGSYS",     # 1.1 global 118, +3
    125: "SIMPTYPEBEGSYS",  # 1.1 global 122, +3
    129: "CONSTBEGSYS",  # 1.1 global 126, +3

    55: "STRGPTR",
    56: "INTRACTVPTR",
    # 1.3 only: a packed char array that is not a STRING, and an unpacked
    # integer one. Not BYTESTREAMPTR/WORDSTREAMPTR -- folded to eight
    # significant characters those are the predeclared type names
    # themselves (finding 29). Shortened to match INTPTR and REALPTR.
    57: "BYTEPTR",
    58: "WORDPTR",
    59: "NILPTR",
    60: "TEXTPTR",
    61: "BOOLPTR",
    62: "CHARPTR",
    63: "LONGINTPTR",
    64: "REALPTR",
    69: "OUTPUTPTR",
    70: "INPUTPTR",

    # Finding 34c. TEST does not move; the other three carry the same +1/+3
    # shift as their neighbours, and 1.3's DECLARAT.10/.12 confirm all four.
    94:  "STARTDOTS",   # 1.1 global 91, +3
    45:  "LINKINFO",    # 1.1 global 44, +1 -- confirmed in 1.3's NEWPROC
    11:  "TEST",
    37:  "USING",
    66:  "USINGLIST",
    71:  "MODPTR",

    # Finding 23, carried across by the correspondence table -- every one of
    # these pairs is a 1.00-similarity match, and the 1.3 $U- arm sets the
    # shifted numbers in the same order.
    13:  "SEG",
    28:  "SYSCOMP",
    30:  "FLIPBYTES",
    32:  "ININTERFACE",   # 1.1 global 31, +1
    33:  "INMODULE",        # 1.1 global 32, +1
    34:  "SWAPMORE",
    35:  "SWAPPING",
    36:  "NOLOAD",
    40:  "VARSTRG",
    43:  "TINY",
    44:  "LIST",
    46:  "OPT_E",
    48:  "IOCHECK",
    50:  "NOISY",
    51:  "DEBUGGING",
    52:  "RANGECHECK",
    53:  "GOTOOK",
    88:  "NEXTSEG",
    605: "COMMENT",
    606: "SYSTEMLIB",
    665: "REFFILE",
    716: "LIBRARY",
    756: "INCLFILE",
    796: "LP",

    # Findings 28 and 31, carried across by the correspondence table (every
    # pair below is a 1.00-similarity match). GATTR keeps words 3..7 in
    # 1.3, with the same 5-word record shape in the global map.
    3:   "GATTYPTR",
    4:   "GATKIND",
    5:   "GATCVAL",
    6:   "GATVLEV",
    7:   "GATDPLMT",
    8:   "TOP",
    47:  "BPTONLINE",   # 1.1 global 46, +1
    49:  "CODEINSEG",   # 1.1 global 48, +1
    98:  "LINESTART",   # 1.1 global 95, +3
    10:  "LC",
    25:  "LCMAX",
    39:  "DP",          # 1.1 global 38,  +1
    80:  "LEVEL",       # 1.1 global 77,  +3
    81:  "STMTLEV",   # 1.1 global 78,  +3
    82:  "BEGSTMTLEV",   # 1.1 global 79,  +3
    96:  "LINEINFO",   # 1.1 global 93,  +3
    99:  "NEXTPROC",    # 1.1 global 96,  +3
    100: "CURPROC",     # 1.1 global 97,  +3
    190: "PROCTABLE",    # 1.1 global 185, +5
    627: "NEXTJTAB",     # 1.1 global 509, +118
    628: "JTAB",      # 1.1 global 510, +118

    # Finding 38, carried across by the correspondence table: 575..585 move
    # as a block to 705..715 (+130, every pair a 1.00 match), and the three
    # segment-numbering objects widen exactly as a 32 -> 64 segment limit
    # would make them. 1.3's own code confirms each shape independently.
    705: "REFBLK",
    706: "NREFS",
    707: "REFLIST",
    708: "TEXTSTRT",
    709: "PREVSYMBLK",
    710: "OLDSYMBLK",
    711: "PREVLINESTART",
    712: "PREVSYMCURSOR",
    713: "OLDLINESTART",
    714: "OLDSYMCURSOR",
    715: "USEFILE",
    38:  "INCLUDING",  # 1.1 global 37, +1
    134: "DISPLAY",     # 1.1 global 131, +3 -- unchanged at 52 words, and
                       # 1.3 indexes it with the same IXA 4
    445: "SEGTABLE",    # 1.1 global 335, +110 -- unchanged at 16 x 9
    186: "SEGSUSED",   # 1.1 global 183, +3 -- SET OF 0..63 here: BODYPART.7
                       # is the same nine instructions with LDM/ADJ/STM 4
                       # and SLDC 4 where 1.1 has 2
    589: "SEGMAP",     # 1.1 global 479, +110 -- still IXP 4,4, but 16 words
                       # instead of 8, so 64 nibbles instead of 32

    # Finding 39, carried across by the correspondence table -- every pair
    # below is a 1.00-similarity match. MARKP is the one exception: it is
    # touched once in each release, too little for the matcher, so it is
    # placed by the +3 shift its neighbours carry and confirmed directly --
    # 1.3's `LAO 83; CSP 32 MARK` is followed by `LAO 84` for NEW(TOS),
    # exactly as 1.1's 80/81 are.
    17:  "ID",              # +0
    24:  "DISX",            # +0
    26:  "GETSTMTLEV",      # +0
    27:  "PUBLICPROCS",     # +0
    29:  "LIBNOTOPEN",      # +0
    41:  "LSEPPROC",        # 1.1 global 40, +1
    42:  "INTRINSIC",       # 1.1 global 41, +1
    54:  "PRTERR",          # 1.1 global 53, +1
    65:  "RESIDENT",        # 1.1 global 62, +3
    67:  "FWPTR",           # 1.1 global 64, +3
    68:  "OUTERBLOCK",      # 1.1 global 65, +3
    72:  "UFCTPTR",         # 1.1 global 69, +3
    73:  "UPRCPTR",
    74:  "UFLDPTR",
    76:  "UVARPTR",         # 1.1 global 73, +3 -- and 75, like 1.1's 72,
                            # is never touched
    77:  "UCSTPTR",
    78:  "UTYPPTR",
    79:  "GLOBTESTP",
    83:  "MARKP",           # 1.1 global 80, +3
    84:  "TOS",
    85:  "GLEV",
    86:  "NEWBLOCK",
    87:  "DATASEG",         # 1.1 global 84, +3
    90:  "SCONST",          # 1.1 global 87, +3
    91:  "STRGCSTIC",
    92:  "SMALLESTSPACE",
    97:  "LOWTIME",         # 1.1 global 94, +3
    133: "VARS",            # 1.1 global 130, +3
    1097: "CURBLK",         # 1.1 global 967, +130
    1098: "CURBYTE",
    1099: "DISKBUF",
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
