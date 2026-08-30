# Established facts and corrections

Everything here was re-derived from the disk images in `evidence/` by the
code in `tools/`. Where a claim from the inherited ChatGPT handoff is
contradicted, the correction is stated explicitly.

Evidence hashes (SHA-256), unchanged from the inherited archive:

| file | sha256 |
|---|---|
| Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk | `88b67683f3ac645a91e0139d987a8b8fd8725b6b4045d38eb272e4cb91341adf` |
| Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk | `873b9e41c40cef539c06b4f5e2dafe475b0fec5c52c71e241c2cf8ad0f6f05a9` |
| ii0src.sdk | `1dfab0b03dbd8b72c863bf6ce805e4493ccad70aa6dee78d493a310603ef3015` |
| Undocumented Secrets of Apple Pascal.html | `4416a361644a16cfba9eea5eb1030e5a3146f169e29a847444b25758d985184c` |

---

## 1. COMPINIT has 10 procedures, not 29 — and the "29" map is PASCALCO's

**VERIFIED BINARY FACT.** The inherited handoff leads with an "IMPORTANT
CORRECTION" stating that COMPINIT contains 29 procedures rather than 10, and
gives a 29-line procedure map. That correction is wrong, and the map is
mislabelled.

COMPINIT (segment 7) contains **10** procedures. The 29-entry table in
`CLAUDE_HANDOFF.md` and `COMPINIT-PROCEDURE-MAP-CORRECTED.txt` is a
byte-for-byte match for the procedure map of **PASCALCO (segment 1)**, which
does have 29 procedures in 1.1. Compare the handoff's "COMPINIT procedure 1
— entry $10E0 exit $1122 data 2444 params 4 lex 0" against
`analysis/procedure_maps/SYSTEM.COMPILER-1.1-map.txt`, where those are
PASCALCO's proc 1 attributes exactly.

Consequences:

* The Phase 4 and Phase 5 "COMPINIT P9/P10" analyses actually describe
  **PASCALCO procedures 9 and 10**. Their conclusions are not about COMPINIT
  at all.
* Phase 1's original figure of 10 procedures for COMPINIT was correct, as was
  its COMPINIT proc 1 record (entry `$0A46`, exit `$0C71`, data 518,
  params 0, lex 1).

The root cause is visible in the inherited `decode_compinit.py`: it slices
the segment at `comp[10*512 : 10*512+0xc9a]`, which is right for COMPINIT,
but the procedure-count byte was read from the wrong half of the segment's
trailing word (see finding 3).

## 2. Sector interleave

**VERIFIED BINARY FACT.** Both `.dsk` images are 143,360-byte DOS-3.3-order
images of a UCSD Pascal volume. The Pascal/ProDOS logical sector to DOS
physical sector map is

```
0 14 13 12 11 10 9 8 7 6 5 4 3 2 1 15
```

confirmed by the volume directory (Pascal block 2) landing on track 0
physical sectors 11 and 10, where it actually is. The inherited script used
the same mapping; it is recorded here because a plausible-looking
alternative table (`0 13 11 9 7 …`) does not work and will silently produce
garbage.

## 3. Segment trailer layout — the source of the procedure-count error

**VERIFIED BINARY FACT.** The last word of a segment is

```
low byte  = segment number
high byte = number of procedures
```

The inherited work read it the other way round. Reading it backwards yields
"29 procedures" for a segment whose number is 29, and so on. The correct
reading is cross-checked two ways: the low byte agrees with `SEGINFO` in the
segment dictionary for all 15 segments on both disks, and the high byte
yields a procedure dictionary in which every entry's stored procedure-number
byte equals its dictionary index.

## 4. Codefile and procedure-attribute layout

**VERIFIED BINARY FACT**, documented in `tools/a2pascal/codefile.py`. Block 0
is the segment dictionary (`DISKINFO`, `SEGNAME`, `SEGKIND`, `SEGINFO`,
copyright string at 0x1B0). Each procedure's attribute table sits at the end
of its code:

```
JTAB+0  procedure number (byte)   JTAB-4  exit IC   (self-relative)
JTAB+1  lexical level    (byte)   JTAB-6  parameter size
JTAB-2  enter IC (self-relative)  JTAB-8  data size
JTAB-10, -12, …  jump table, addressed by negative branch displacements
```

Self-relative pointers are subtracted from the address of the pointer word.

## 5. SYSTEM.COMPILER contents

**VERIFIED BINARY FACT.** Both disks are volume `APPLE2:`, 280 blocks.

| | 1.1 | 1.3 |
|---|---|---|
| SYSTEM.COMPILER blocks | 6..80 (75, 38,400 B) | 56..133 (78, 39,936 B) |
| copyright string | `(C)Apple Computer Inc. 1979,1980 (C)U.C.Regents 1979` | `COPYRIGHT 1979,1980,1983-1985 APPLE COMPUTER, INC. ALL RIGHTS RESERVED` |
| codefile version | 2 | 6 |

Segments and procedure counts:

| seg | name | 1.1 nproc | 1.3 nproc |
|----:|------|----:|----:|
| 1 | PASCALCO | 29 | 31 |
| 7 | COMPINIT | 10 | 11 |
| 8 | DECLARAT | 20 | 20 |
| 9 | BODYPART | 37 | 38 |
| 10 | ROUTINE | 17 | 17 |
| 11 | STATEMEN | 8 | 8 |
| 12 | CASESTAT | 1 | 1 |
| 13 | FORSTATE | 1 | 1 |
| 14 | BODY1 | 1 | 1 |
| 15 | BODY3 | 2 | 2 |
| 16 | WRITELIN | 4 | 4 |
| 17 | UNITPART | 4 | 4 |
| 18 | COMPOPTI | 4 | 5 |
| 19 | NUMSTRIN | 3 | 3 |
| 20 | FINISHUP | 1 | 1 |

## 6. Only two procedures in the whole compiler are native 6502

**VERIFIED BINARY FACT.** The handoff states that segment 1, PASCALCO, is
native 6502. It is not, in either version.

* 1.1: `SEGINFO` mtype = 2 (p-code LSB); all 29 procedures are p-code.
* 1.3: `SEGINFO` mtype = 7 (6502), but only **2 of its 31** procedures are
  native. The other 29 disassemble cleanly as p-code and correspond
  one-for-one with 1.1's 29.

A segment's mtype is stamped 6502 if it contains *any* native code, so it
is not a per-procedure test. The per-procedure marker is the procedure
number byte at `JTAB+0`: native procedures store **0** there instead of
their dictionary index, and their exit-IC word is a null self-relative
pointer, since native code has no EXIT target. `Procedure.is_native`
implements this. Across both disks that yields 287 p-code procedures, all
of which decode cleanly, and 2 native ones.

The two native procedures both begin with the 6502 sequence
`68 85 7E 68 85 7F 68 A8 68 AA` — `PLA/STA/PLA/STA/PLA/TAY/PLA/TAX`,
pulling arguments off the p-machine stack.

## 6a. The two native procedures are IDSEARCH and TREESEARCH

> **See finding 19**, which disassembles both, establishes which is which
> from the call sites, and decodes the reserved-word table inside IDSEARCH.


**STRONG INFERENCE**, from matched call sites; see
`tools/probes/probe_idsearch_13.py`.

1.1 issues `CSP 7` (IDSEARCH) once and `CSP 8` (TREESEARCH) four times.
1.3 issues neither, and instead calls its two new native procedures
`PASCALCO.2` and `PASCALCO.3` exactly once and four times respectively.
The sites correspond one-for-one, in the correspondingly renumbered
procedures, with identical argument setup:

| 1.1 | 1.3 |
|---|---|
| `PASCALCO.6: LAO 14; SLDO 9; CSP 7` | `PASCALCO.8: LAO 14; SLDO 9; CGP 2` |
| `PASCALCO.5: LLA 2; SLDL 9; CSP 8` | `PASCALCO.7: LLA 2; SLDL 9; SLDC 0; SLDC 0; CGP 3` |
| `PASCALCO.7: SLDL 10; SLDL 9; LAO 17; CSP 8` | `PASCALCO.9: (same); SLDC 0; SLDC 0; CGP 3` |
| `PASCALCO.8: SLDL 11; LLA 3; LAO 17; CSP 8` | `PASCALCO.10: (same); SLDC 0; SLDC 0; CGP 3` |

So Apple hand-coded the compiler's two hottest inner loops — the scanner's
reserved-word lookup and the symbol-table search — in 6502 for 1.3,
promoting them from p-machine intrinsics to ordinary procedures of the base
segment. `TREESEARCH` gained two extra parameters.

For a 1.3 reconstruction this is useful twice over: it names both native
routines, and 1.1's intrinsic-based call sites document the semantics they
have to reproduce.

## 7. The p-code opcode table

**VERIFIED BINARY FACT**, and since it was cross-checked against a
published reference, **VERIFIED SOURCE FACT** for the parts cited below.

The opcode set is in `tools/a2pascal/pcode.py`. `tools/validate_pcode.py`
disassembles every p-code procedure on both disks and requires (a) the
linear sweep from `enter_ic` to land exactly on `exit_ic`, (b) the exit
sequence to reach `RNP`/`RBP`, and (c) no unknown opcodes. Result: **287 of
287 procedures pass**.

That check is necessary but *not sufficient*, and two real errors survived
it before being caught:

**The short-form ranges were off by eight.** Every byte in `$D0-$FF` is a
one-byte instruction however the range boundaries are drawn, so a wrong
split still synchronises perfectly. It has to be tested semantically. The
test that caught it (`tools/probes/probe_short_form_base.py`) is the
increment idiom `<short load X>; SLDC 1; ADI; <long store X>`: the long
store's operand is unambiguous, so it pins the short load's base. Every
instance disagreed by exactly +8. The correct ranges, since confirmed
against Hyde's *P-Source* pp. 160, 168 and 184:

| range | instruction | book page |
|---|---|---|
| `$00-$7F` | SLDC 0..127 | 154 |
| `$D8-$E7` | SLDL 1..16 | 160 |
| `$E8-$F7` | SLDO 1..16 | 168 |
| `$F8-$FF` | SIND 0..7 | 184 |

**`$D0` is LPA, a variable-length instruction.** `LPA UB,<bytes>` (*P-Source*
p.220) loads the address of an inline packed-array constant. It was being
decoded as a one-byte unknown followed by its length byte and payload as a
run of `SLDC`s — which keeps the stream in sync only because character
bytes are all below `$80`. Fixing it removed 504 phantom `SLDC`s.
`$D7` is a `NOP` the compiler emits to word-align constants (*P-Source*
p.95: "The NOP that follows is used to align the string that follows on a
word boundary"); the book does not give its opcode number, so that
identification is STRONG INFERENCE. No other opcode in `$D1-$D6` occurs.

`LDC` and `XJP` inline blocks *do* self-align to a word boundary:
`tools/probes/probe_alignment.py` re-runs the whole-corpus sync check with
the assumption flipped and gets 263/24 instead of 287/0.

These corrections matter downstream — they changed which global is the
compiler's busiest (finding 10).

For reference, the opcode table in the inherited `decode_compinit.py` is
substantially wrong in other ways too: it maps `$A1` to "UJP/FJP", `$F6` to
`SLDO`, `$F8` to `SIND`, and marks roughly a quarter of the range `???`.

## 7a. Reference: Hyde, *P-Source* (1983)

Randall Hyde, *P-Source: A Guide to the Apple Pascal System*, 1983. A
scanned copy (462 pages, no text layer) is the authoritative reference for
this project's p-machine questions. It documents **Apple II Pascal 1.1**
specifically, which is the version we analyse first.

Most useful parts:

* Ch. 5, pp. 151-306 — every p-code instruction with syntax, opcode number
  and operation. PDF page number equals printed page number.
* Ch. 6, p. 307 — inside the interpreter; zero-page/register layout.
* p. 352 — the interpreter's jump table lives at `$D000` and holds 128
  addresses, one per non-SLDC opcode.
* Index, pp. 453-462 — fastest way to locate a mnemonic.

`tools/pdfpage.py` renders pages to PNG for reading. The scan is in
`evidence/reference/manuals/` and has **no text layer**, so it cannot be
grepped — page numbers and the index are the way in.

## 8. ii0src.sdk is the UCSD II.0 *operating system*, not the compiler

**VERIFIED SOURCE FACT.** The handoff describes `ii0src.sdk` as "the UCSD
Pascal II.0 source disk used as the source-side comparison artifact",
implying compiler source. It is not. Unpacked, it is volume `II0SRC:`
containing seven text files that together are `PROGRAM PASCALSYSTEM` — the
UCSD II.0 operating system and its runtime:

```
SYSTEM.TEXT  SYSTEM.A.TEXT  SYSTEM.B.TEXT  SYSTEM.C.TEXT
SYSSEGS.A.TEXT  SYSSEGS.B.TEXT  GLOBALS.TEXT
```

No compiler source is present on it. The plan item "cross-reference the UCSD
II.0 source" therefore cannot validate compiler internals directly. What it
*can* do is decode the compiler's environment, which is finding 9.

`ii0src.sdk` is a NuFX (ShrinkIt) archive holding an LZW/1-compressed
143,360-byte disk image. `tools/a2pascal/nufx.py` unpacks it. Two format
details had to be established empirically and are noted in that file: the
first assignable LZW code is 0x101 with an "early" width change, and the
string table is reset at the start of each 4096-byte chunk (despite LZW/1
nominally sharing the table across chunks). Validation: 35 chunks, exactly
143,360 bytes out, the whole 40,076-byte thread consumed, and the result
carries a well-formed Pascal volume directory.

## 9. The compiler's calls into the runtime are now named

**VERIFIED SOURCE FACT, corroborated against the binary.** `CXP 0,n` calls
procedure `n` of segment 0, the resident OS. `GLOBALS.TEXT` contains the
block that fixes those numbers, labelled in the source itself:

```
(* SYSTEM PROCEDURE FORWARD DECLARATIONS *)
(* THESE ARE ADDRESSED BY OBJECT CODE... *)
(*  DO NOT MOVE WITHOUT CAREFUL THOUGHT  *)
```

Parsing that block in declaration order, with procedure 1 reserved for
`PASCALSYSTEM` itself, gives 3 = `FINIT`, 4 = `FRESET`, 5 = `FOPEN`,
6 = `FCLOSE`, 13 = `FWRITEINT`, 16 = `FREADCHAR`, 17 = `FWRITECHAR`,
19 = `FWRITESTRING`, 20 = `FWRITEBYTES`, 22 = `FWRITELN`, 28 = `FBLOCKIO`,
and so on. Corroboration from the binary: `PASCALCO.1` opens its four files
with `CXP 0,3` on argument lists of the shape `LAO <fib>; LAO <window>;
LDCI 1/2; NGI` — that is `FINIT(f, window, -1|-2)` — and closes them in its
exit code with `CXP 0,6` on `LAO <fib>; SLDC 0`, that is
`FCLOSE(f, CNORMAL)`. The listings and call graph in `analysis/` are
annotated with these names.

## 10. The global data map

**VERIFIED BINARY FACT** for access counts, **STRONG INFERENCE** for object
extents. `analysis/global_map/globals-{1.1,1.3}.txt`.

All segments of a UCSD program share one global data area: the activation
record of the outermost block. Its size is that block's data size — 1222
words (2444 bytes) in 1.1, 1355 words (2710 bytes) in 1.3. Four
instructions address it, all by word offset: `SLDO`/`LDO` (read), `SRO`
(write), `LAO` (take address).

133 distinct offsets are touched in 1.1, 139 in 1.3, and the inferred
objects account for 1221 of the 1222 words. Scalars are identified by only
ever being loaded and stored whole; aggregates by having their address
taken, with the instruction that consumes the address revealing the shape
(`IXA` = array with element size, `MOV`/`LDM`/`STM` = exact word count,
`SIND`/`LDB` = dereference, a call = passed by reference).

Identifications so far (all counts are post-correction; the figures before
finding 7's opcode fixes were wrong, and named a different global as the
busiest):

* **word 17, 4 words** — the current identifier. `MOV 4` at 13 sites, ten
  8-byte block compares, and its address passed to `CSP 8` TREESEARCH and
  `CSP 7` IDSEARCH. This is the compiler's `ID: PACKED ARRAY[1..8] OF CHAR`.
* **word 15** — the busiest global in the compiler: 256 reads, 24 writes,
  touched by 60 of the ~140 procedures, never address-taken. This is the
  current-symbol/token variable that every parser dispatch tests.
* **word 3, 5 words** — a record, copied whole with `MOV 5` at 7 sites and
  passed to `CSP 1` NEW, while words 4..7 are also loaded and stored
  individually. So words 3..7 are one record whose fields are addressed
  directly. 202 reads and 62 writes across 32 procedures.
* **word 131, 52 words** — an array indexed with `IXA element=4 words` at
  28 sites, i.e. 13 entries of 4 words. 4 words is 8 characters, the same
  width as the identifier buffer at word 17, and `PASCALCO.5` and
  `PASCALCO.8` (the TREESEARCH callers) both take its address. A table of
  8-character names.
* **words 535, 586, 626, 666** — four FIBs (file control blocks), each
  paired with a window buffer exactly 300 words higher (835, 886, 926,
  966), all opened by `FINIT(f, window, -1|-2)` in `PASCALCO.1` and closed
  in its exit code. Their roles separate by which runtime routines they
  reach:
  * 666 — the listing/output text file (`FWRITEINT`, `FWRITECHAR`,
    `FWRITESTRING`, `FWRITELN`, `FWRITEBYTES`), and the only one with
    `recwords = -2`.
  * 586, 626 — block-I/O files (`FBLOCKIO` from `PASCALCO.3`): the code
    output.
  * 535 — reached by `FRESET`/`FOPEN` from `UNITPART`: the library/unit
    file.
* **words 1, 2, 12** — pointers whose address is passed to `CSP 1` NEW;
  heap roots.

## 11. 1.1 to 1.3 correspondence

**STRONG INFERENCE.**
`analysis/global_map/correspondence-1.1-to-1.3.txt`, built by
`tools/globaldiff.py`.

1.3 is a recompile of a lightly edited 1.1 source. Aligning procedures on
their `(param_size, data_size, lex_level)` signature and then aligning
their instruction streams on operand-insensitive tokens matches **131
procedure pairs** and yields a global offset mapping for **128 globals with
zero contested entries**.

The shift distribution is the striking part — only seven distinct deltas:

| delta | globals |
|---:|---:|
| +0 | 27 |
| +1 | 25 |
| +3 | 51 |
| +5 | 1 |
| +110 | 2 |
| +118 | 4 |
| +130 | 18 |

That is the signature of a handful of insertions into an otherwise stable
layout, and it confirms that 1.1 and 1.3 are close relatives rather than
independent rewrites. Every fact established about a 1.1 global carries
over to 1.3 through this table.

Most procedures also match at similarity 0.85-1.00, with a number
byte-identical in shape. The heavily changed ones are worth attention as
the places Apple actually edited.

## 12. Naming the PASCALCO service routines

`analysis/procedures/profiles-{1.1,1.3}.txt`, from `tools/procprofile.py`,
gives each procedure's signature, callers, callees, globals touched,
runtime services used, and literal strings.

Functions are distinguished from procedures by the db operand of the
terminating `RNP`/`RBP`, which is the result size in words — 0 for a
procedure. 9 of 142 procedures in 1.1 have a non-zero value, and they are
the ones whose result is consumed at the call site
(`tools/probes/probe_rnp_operand.py`). **STRONG INFERENCE.**

Identifications, in descending confidence:

* **`PASCALCO.2` = the error reporter.** VERIFIED, from its own string
  literals: `'Line '`, `', error '`, `' <<<<'` and
  `' <sp>(continue), <esc>(terminate), E(dit'`. 311 call sites in 73
  procedures — the most-called routine in the compiler. One word of
  parameter (the error number).
* **`PASCALCO.4` = the listing-file error writer.** VERIFIED by its string
  `'>>>>>> Error # '`; writes to the FIB at word 666 via `FWRITEINT` /
  `FWRITECHAR` / `FWRITESTRING`, and calls `CSP 0` IOCHECK twelve times.
* **`PASCALCO.27` = the undeclared-identifier reporter.** VERIFIED by the
  string `' undefined'`; it is recursive (calls itself twice) and is only
  called from `PASCALCO.24`, i.e. it walks the symbol tree at end of
  compilation.
* **`PASCALCO.6` = INSYMBOL, the scanner.** STRONG INFERENCE: 193 call
  sites in 57 procedures, it is the sole user of `CSP 7` IDSEARCH, it calls
  `NUMSTRIN.1` for number conversion, and it writes the token globals
  including word 15.
* **`PASCALCO.8` = SEARCHID.** STRONG INFERENCE: takes the address of the
  identifier buffer (word 17) and the name table (word 131), calls
  `CSP 8` TREESEARCH, and reports errors via `PASCALCO.2` twice — the
  signature of "look this identifier up, complain if absent".
* **`PASCALCO.7` = a single-scope identifier search.** STRONG INFERENCE:
  25 bytes, two parameters, uses TREESEARCH on word 17 and never reports an
  error.
* **`PASCALCO.20` = the code-byte emitter.** VERIFIED from its body, which
  is the whole procedure:
  `SLDO 2; SLDO 9; SLDL 1; STB; SLDO 9; SLDC 1; ADI; SRO 9`
  — that is `buffer^[ix] := ch; ix := ix + 1`, with word 2 the buffer
  pointer and word 9 the index. 51 call sites, all in the code-generating
  segments.
* **`PASCALCO.22` = the code-buffer flush.** STRONG INFERENCE: the only
  other user of word 9's neighbourhood, calls `FBLOCKIO`, and takes the
  address of word 969, inside the block buffer at 966.

~~Not yet resolved: `PASCALCO.9`, `.15`, `.16`, `.17`.~~ **Resolved by
finding 22** — they are `GETBOUNDS`, `STRING`, `STRINGTYPE` and
`LONGSIZE`, and the "3-word parameter list" they share turned out to be
the clue: it is one real argument plus the two-word function result area.

## 13. Lifting p-code to pseudo-Pascal

`analysis/lifted/SYSTEM.COMPILER-{1.1,1.3}.pas.txt`, from
`tools/a2pascal/lift.py`. `tools/liftproc.py SEGMENT.N` lifts one procedure.

The p-machine is a plain stack machine, so symbolically executing the
evaluation stack recovers expressions directly: pushes build expression
trees and the store instructions turn them into statements. Storage is
named as addressed — `G<n>` global word, `L<n>` local, `I<lex>,<n>`
intermediate — deliberately, so that no source identifier is invented in
an artifact that cannot carry a confidence level.

**128 of 142 procedures in 1.1 and 128 of 145 in 1.3 lift with the
evaluation stack fully tracked and balanced.** The remainder are blocked
only by CSPs of unknown arity (finding 14).

Callee arities come from three places: intra-file calls from the codefile's
own `param_size`; segment-0 calls from the UCSD source, by parsing the
declaration block in `GLOBALS.TEXT` (`segment0_signatures`, a VERIFIED
SOURCE FACT — it independently reproduces `FINIT`=3 words, `FCLOSE`=2,
`FWRITESTRING`=3, all of which were already confirmed against the binary);
and CSPs from the table in finding 14.

Validation, and an example of the output. `PASCALCO.20` was predicted from
its raw p-code to be the code-byte emitter; it lifts to exactly that:

```
procedure PASCALCO.20(params 1 words);  { locals 0 words, lex 1 }
  G2^[G9] := L1;
  G9 := (G9+1);
```

`PASCALCO.22` lifts to a recognisable buffer flush — fill a 512-byte
buffer at `G969` through index `G968`, and when it is full call `FBLOCKIO`,
report error 402 on failure, and advance the block number `G967` —
confirming the finding-12 hypothesis.

**Known limitation.** The stack is modelled per basic block, carried across
a fallthrough edge only when the successor has exactly one predecessor. An
argument list that straddles a control-flow join is therefore mis-attributed;
the leftover operands are printed as `{ left on stack: ... }` rather than
silently dropped, so affected sites are visible. `PASCALCO.22`'s `FBLOCKIO`
call is one. Fixing this needs a proper dataflow join (merge predecessor
stacks when they agree).

## 14. CSP arities recovered by balance testing

> **Superseded in part by finding 17.** The whole CSP table is now available
> as source. Everything below stands as the record of what balance testing
> alone could establish, and two of its results — CSP 34 and CSP 40 — turned
> out to be exactly right, which is the main reason to trust the method
> elsewhere. The one claim below that finding 17 *overturns* is `CSP 31 =
> MARK`, taken from Hyde p.228; the interpreter puts MARK at 32.


`tools/probes/probe_csp_arity.py`. A procedure only lifts cleanly if every
stack effect is known *and* the stack ends empty with no underflow, so the
correct (pops, pushes) for an unknown CSP should be the one that makes the
most procedures balance. Solved greedily, reporting the margin over the
runner-up.

* **CSP 34 → 0 pops, 1 push** (85 balanced vs 83 for the runner-up)
* **CSP 40 → 0 pops, 1 push** (81 vs 79)

Both are zero-argument, word-returning functions, which fits `IORESULT` and
`MEMAVAIL`; Hyde documents both as interpreter routines in Apple Pascal 1.1
(pp. 347 and 342). **STRONG INFERENCE** for the arities, SPECULATION for
which name goes with which number.

* **CSP 31 = MRK (MARK)** — VERIFIED SOURCE FACT, Hyde p.228 gives the
  encoding as `158,31` (`$9E,$1F`) and says it "expects a single word on
  TOS", so 1 pop, 0 pushes. The compiler does not use it.
* **CSP 21 = load segment** — Hyde p.95 describes generated code where "30
  is pushed onto the stack, special procedure number twenty-one is called"
  to load an intrinsic unit from disk. In SYSTEM.COMPILER, `CSP 21` and
  `CSP 22` occur 11 times each, always as `SLDC <segnum>; CSP 2x`, and the
  `CSP 21` path re-enters the procedure body while the `CSP 22` path falls
  through to `RNP`. **STRONG INFERENCE:** 21 loads a segment, 22 unloads it.
  Arities not yet confirmed by the solver, which could not separate them.

Unresolved: CSP 6, 22, 23, 24, 32, 33, 36. CSP 36 tied in the solver; the
rest occur only inside procedures already blocked for another reason.

An earlier run of the solver produced confident-looking but meaningless
answers because `pop()` returned a placeholder on underflow instead of
failing, so an over-large pop count was never penalised — every candidate
tied. Recorded because it is the same class of mistake as finding 7: a
check that cannot fail proves nothing.

## 15. TommyGoog's Wizardry reconstruction — methodology cross-check

The inherited handoff named TommyGoog's comp.sys.apple2 posts as the
methodological reference. Having now read them, they corroborate this
project's approach and contribute several concrete items.

Agreements with what we independently established:

* **Segment numbering.** He notes Apple Pascal assigns "system segments
  0-6, then declared segments starting at 7". That is exactly the layout in
  SYSTEM.COMPILER: `PASCALCO` is segment 1 (the user-program slot) and the
  phase segments run 7..20 (finding 5). It also explains why segment number
  and directory-entry number differ.
* **Same primary reference.** He used Hyde's *P-Source* (finding 7a), plus
  a document he cites as "Apple 2 Pascal 11 PCodeIntDism.pdf", a
  disassembly of the p-code interpreter. Worth locating.
* **Unknown standard procedures.** His decompiler emitted "UNKNOWN STANDARD
  PROCEDURE" — the same gap we hit at finding 14. He resolved his by
  cross-referencing `LIBMAP` output against `SYSTEM.LIBRARY`.
* **Two-stage lift.** He produced "a rough interpretation (pseudo-Pascal
  code)" first and converted it to compilable Pascal years later. That is
  the pipeline here: finding 13 is stage one.
* **Mixed 6502.** He extracted native procedures separately via the monitor
  and hand-translated them — the approach finding 6a's two native routines
  will need.

New, actionable:

* **`LIBMAP.CODE` and `LIBRARY.CODE` are on our own 1.3 disk** (blocks
  167..177 and 159..166; see the directory listing). If any intrinsic-unit
  reference needs resolving, the map is already in `evidence/`.
* **Validation setup.** He recompiled under AppleWin, having modified it to
  support **four disk drives**, which the Apple Pascal compiler needs. That
  is a concrete starting configuration for plan step 7.
* **Diffing method.** He generated decompiler listings from both the
  original and the recompiled output and compared them with WinDiff. Our
  equivalent is cheaper: run `tools/disasm.py` over both and diff, since
  the decoder is the same on each side.

## 17. John Brooks' Apple Pascal 1.4 interpreter source

`C:\JohnBrooks\pascal13Src\pascal13\` — `Interp.s` (10,126 lines) and
`Common.s`. This is the p-machine itself in 6502 assembly: a maintained,
commented descendant of the 1.3 interpreter, running the same p-code the
compiler on our evidence disks emits. **It is not in this repo** — it is
third-party source read in place, like Hyde's book. Probes reference the
absolute path and will report it missing on another machine.

It answers, as VERIFIED SOURCE FACT, questions this project had been
inferring. Everything below was re-checked against the binary rather than
adopted on authority.

**The complete CSP table.** `CSPTBL` lists all 41 entries with mnemonics.
This retires the standing guess that CSP 21-40 were "Apple additions
outside the documented set" — they are ordinary UCSD standard procedures
sitting above the range Hyde tabulates:

```
 0 IOCHECK    5 UNITREAD   10 FILLCHAR  23 TRUNC   33 RELEASE   38 UNITCLEAR
 1 NEW        6 UNITWRITE  11 SCAN      24 ROUND   34 IORESULT  39 HALT
 2 MOVELEFT   7 IDSEARCH   12 UNITSTATUS 25-31 transcendental   40 MEMAVAIL
 3 MOVERIGHT  8 TREESEARCH 21 LOADSEGMENT   35 UNITBUSY
 4 EXIT       9 TIME       22 UNLOADSEGMENT 36 PWROFTEN  37 UNITWAIT
                                        32 MARK
```

`$0D`-`$14` are reserved holes; 25-31 and the holes are never emitted.

**The arities, counted off the handlers.** These are *stack words*, not
Pascal arguments — the two differ whenever an argument is a packed-array
reference, which the compiler passes as a (base, index) pair. That
distinction is what four of the twelve hand-built entries had wrong:
`MOVELEFT` and `MOVERIGHT` pop 5 words, not 3; `FILLCHAR` 4, not 3; `SCAN`
6, not 4. See `tools/a2pascal/lift.py`.

**Checked against the binary, not assumed.**
`tools/probes/probe_csp_check.py` lifts all 287 procedures under the old
and new tables. Cleanly-balancing procedures go **83 → 115**, and end-to-end
`liftall.py` goes **256 → 283 of 287** procedures lifted with the stack
fully tracked. Per entry, five arities are independently corroborated (the
true value balances strictly more procedures than any of the 20 alternatives
— `NEW` by +16, `MOVELEFT` by +20), and the rest tie, meaning they occur
only in procedures blocked for other reasons. Two disagree:

* **CSP 8 TREESEARCH.** Never source-verified — every version of `Interp.s`
  dispatches IDSEARCH and TREESEARCH to "not implemented", since they exist
  only for the compiler and the runtime-only system drops them (`Common.s`
  says so explicitly). The binary prefers `(2,0)` over the inherited
  `(3,0)` by +2 across four call sites, so `(2,0)` is now used. STRONG
  INFERENCE, still.
* **CSP 24 ROUND.** Source is unambiguous — `PopFPAcc` takes a 4-byte real,
  the handler pushes 2 bytes, so `(2,1)`. The probe reports `(0,0)`
  balancing one procedure more, across two call sites in the whole
  compiler. That is the finding 13 join-straddling limitation showing
  through, not evidence about ROUND. Source kept.

**Hyde is wrong about MARK.** *P-Source* p.228 gives `MRK` as `158,31`. The
interpreter puts `MRK` at `$20` = 32 and `SQRT` at 31. The interpreter's
numbering is the one to trust here, and not merely because it is source:
balance testing had *independently* solved CSP 34 and CSP 40 as
zero-argument word-returning functions (finding 14), and the interpreter
names exactly those two `IORESULT` and `MEMAVAIL`. Two independent methods
agreeing on the numbering, against a book that is off by one.

**CSP 21/22 are the phase dispatch, and they are not in the procedure
bodies.** This is why the balance solver could never resolve them:
`disassemble(enter_ic, exit_ic)` does not cover them. They live in the
*exit* sequences, in a shape now readable end to end:

```
  10B4 9e 16   CSP 22          ; UNLOADSEGMENT
  10B6 b9 1a   UJP $10D2
  10B8 08      SLDC 8
  10B9 9e 15   CSP 21          ; LOADSEGMENT
  10BB 09      SLDC 9
  10BC 9e 15   CSP 21
  ...          (segments 8, 9, 19, 11, 12, 13, 14, 15)
  10D0 b9 f6   UJP $1094 (jtab-10)
  10D2 ad 00   RNP 0
```

That is PASCALCO swapping compiler phases in and out — the thing plan step 5
said "cannot be expressed" without resolving these CSPs.

**Confirmations of earlier inferences.** Each of these was previously
labelled inference and is now source-backed:

* `$D7 = NOP`. Hyde describes a word-alignment NOP (p.95) but never numbers
  it. The interpreter dispatches both `$D2` and `$D7` to `IncIPC1`.
* **Native procedures are marked by procedure number 0.** `CallProc`'s
  comment: "Assembly language routines are denoted by the fact that the
  procedure number ... is zero." This was `codefile.py`'s heuristic.
* **The short-form ranges of finding 7.** `SLDL` = op−`$D7` (1..16),
  `SLDO` = op−`$E7` (1..16), `SIND` = op−`$F8` (0..7). Note the interpreter's
  *comments* number the SIND slots 1..8 while its handler label is
  `OpF8_SIND0` and the code dereferences at offset 0 — the code is right and
  the comment is off by one. Arithmetic: the handlers enter with A =
  opcode×2, so `SLDO $E8` computes `$D0 − $C3 = 13`, and `LDO 1` computes
  `2×1 + 10 = 12..13`. Same slot. The off-by-eight correction holds.
* **Decoder edge cases.** `LDC`'s and `XJP`'s word alignment, `CXP`'s
  operand order (segment, then procedure), `LDE`'s `(UB, BIG)` shape — all
  match `pcode.py` exactly. `tools/probes/probe_opcode_names.py` diffs all
  128 dispatch entries: 74 agree outright, 8 differ only in spelling
  (`CEQ`/`EQU`, `CGE`/`GEQ`, …), 6 were missing and are now filled in.

**Two things newly available and not yet exploited.**

* **`$D1`-`$D6` identified** — `STE`, `NOP`, `EFJ`, `NFJ`, `BPT`, `XIT`.
  Closes an open question below. None occur in SYSTEM.COMPILER.
* **`RNP`'s operand is the function-result word count**, pushed from
  `MP+10` upward on return. So it states, for every procedure, whether it
  is a procedure or a function and how wide the result is. Across both
  disks: **266 `RNP 0`, 19 `RNP 1`, 2 `RBP 0`** — nineteen functions, all
  returning a single word, and no real-valued functions anywhere in the
  compiler. Directly usable for the reconstruction's headers.
* **Activation records.** `LDO n` addresses `BASE + 2n + 10`; `LDL n` the
  same off `MP`. Global word 0 is never referenced by any instruction on
  either disk (lowest operand emitted is 1), so the first declared global
  is at operand 1 — an anchor for plan step 2.

**What it does not give.** No IDSEARCH/TREESEARCH implementation exists in
any of the four `Interp*.s` copies or the `Kernel128*` variants; all
dispatch to "not implemented". Plan step 6's native-code track gets no help
here.

## 21. Control-flow structuring, and an XJP layout error it exposed

Plan step 8's second half. `tools/a2pascal/structure.py` turns the lifted
block graph back into `if`/`while`/`repeat`/`case`, by recursive descent
over the blocks in address order — which works because a Pascal compiler
emits structured source as linear code with forward branches out of each
construct.

Nothing is forced. A region that does not match a pattern exactly stays as
the blocks and gotos it always was, so the output remains faithful and the
unstructured remainder stays countable.

**Checked before measured.** Rewriting a goto graph is exactly the kind of
transformation that can look better and say something different, so
`tools/probes/probe_structure.py` asserts two invariants on all 287
procedures before reporting any success rate: every block's statements
appear in the output (nothing dropped, nothing duplicated into two arms),
and every surviving `goto` has a label. Both now pass at **0 violations**.
The first pass of the structurer failed the first invariant 703 times — it
was dropping the block that carried a construct's terminal jump, along with
whatever real statements sat ahead of that jump. Constructs now *absorb*
the jump and still emit the block.

**Result: 200 of 287 procedures (69%) come out with no goto at all**, and
1392 gotos remain across 6252 basic blocks.

*Superseded by finding 41.* The `case` recogniser named above never
matched anything — it had the jump table on the wrong side of the arms.
Fixing it takes this to 229 of 287 (79%) and 156 gotos.

### 21a. XJP has no "otherwise" pointer

Chasing the last dangling gotos found a decoder error that had been live
since the beginning. `pcode.py` read the two bytes after XJP's min/max as a
self-relative pointer to the default case. They are not.

`Interp.s` `OpAC_XJP` handles an out-of-range selector with
`addq.w #5; ZpIPC; JMP GetOp` — it advances IPC by five and **executes what
is there**. The compiler puts a two-byte `UJP` in that slot. The jump table
starts at +7, which the handler's `adc #7` confirms.

The instruction's total length is identical either way, which is precisely
why the 287/287 sync check never caught it — the same blind spot as the
short-form off-by-eight in finding 7. What it produced instead was garbage
targets: `XJP 9..123 else $-EA6F`, `else $-4A3`. Those now read `else
$0732`, `else $0C28`.

A second detail falls out: an arm may target the default slot itself, which
just means that value has no case of its own. Those are resolved to the
same destination as the default, so no arm points into the middle of the
XJP instruction. That was the source of every remaining dangling goto.

Case dispatch was also simply invisible in the rendered output before this
— `render` emitted nothing at all for an XJP block.

### 21b. What the output looks like now

The compiler's number scanner, recovered end to end:

```
  L5 := G1^[G14];
  L4 := 0;
  L3 := 0;
  while ((L5 in [$03FF,$0000,$0000,$0000]) and (L4 < 4)) do begin
    L3 := ((L3*10)+(L5-48));
    L4 := (L4+1);
    L5 := G1^[(G14+L4)];
  end;
```

`48` is `'0'`, and the set is the digit set. And the symbol-table insert,
built on the native TREESEARCH of finding 19:

```
  L4 := CSP8(L3, @L2, L1);
  while (L4 = 0) do begin
    PASCALCO.2(101);
    if (L2^.f4 = nil) then begin
      L4 := 1;
    end else begin
      L4 := CSP8(L2^.f4, @L2, L1);
    end;
  end;
```

**A caution about reading these.** In the handful of procedures where the
stack model has already broken down, a packed store could render as
`8 := 2` — an assignment to a literal, which reads like a fact about the
program and is not one. Those now render as `{ unmodelled packed store }`
instead. There were 5 per release out of ~1900 statements.

## 20. Merging evaluation stacks at control-flow joins

Plan step 8's first half. The lifter used to carry a stack forward only
along a single-predecessor fallthrough edge, so every argument list that
spanned a branch was abandoned and printed as `{ left on stack: ... }`.
A block's entry stack is now the merge of its predecessors' exit stacks,
computed to a fixed point over the CFG.

The merge rule: identical stacks merge to themselves; equal-depth stacks
whose slots differ merge slotwise to `phi(a, b)`, a real value the program
computes two ways; unequal-depth stacks are **not** reconciled, because
that means the model has lost track on at least one path. Those are
reported as `{ paths disagree on stack depth here }` rather than papered
over. `Block.entry_stack` / `exit_stack` are kept for diagnosis.

That reporting immediately paid for itself: a depth disagreement is almost
never a real property of the program, it is a wrong callee arity upstream,
and it points at the guilty join. Two came out of it.

### 20a. Apple's segment 0 is not UCSD II.0's

`FBLOCKIO` is declared in `GLOBALS.TEXT` with six parameters. Its 24 call
sites all push eight words, leaving its first two arguments stranded.

The tempting fix — VAR parameters of packed types take two words, as the
CSPs do (finding 17) — is wrong, and `tools/probes/probe_var_words.py`
keeps the record. Making `FIB` two words fixes `FBLOCKIO` and breaks
`FCLOSE`, which carries the same `VAR F: FIB` and whose sites supply one
word. No rule can be right and wrong about one declaration.

The explanation is finding 8. `GLOBALS.TEXT` is the *generic* UCSD II.0
operating system; Apple's segment 0 is a derivative. Its declarations are
a good default, not evidence about these disks.

So each routine is checked against the call sites instead, by
`tools/probes/probe_os_arity.py`. Of the 15 segment-0 routines the compiler
calls, **12 are confirmed exactly as declared** — GLOBALS.TEXT is right
about Apple far more often than not. Two are overridden:

* `FBLOCKIO` 6 → **8** words. 24 call sites, margin 20. Not in doubt.
* `FOPEN` 4 → **7** words. 13 call sites, margin 4. Weaker, and adopted as
  STRONG INFERENCE.

Not adopted: `CXP 0,43`, called five times. `GLOBALS.TEXT`'s 43rd forward
declaration is `COMMAND`, but the segment-0 numbering is only *verified* to
29 (finding 18, against Miller's table), so proc 43's identity is an
extrapolation, and its best arity wins by a margin of 1. Left as declared
and recorded here as open.

> **Superseded by finding 51.** `SYSTEM.PASCAL` now parses (finding 50) and
> states these sizes itself. `FBLOCKIO` is 8, but not because Apple changed
> it — it is a function, and 6 arguments plus the two-word result slot is a
> frame of 8. **`FOPEN` is 4, as declared**; the override to 7 was wrong, and
> the margin of 4 turned out to discriminate nothing, since lifting the whole
> compiler either way gives identical output. Both overrides are gone.
> `CXP 0,43` was right to be left alone: it takes three words, so it is *not*
> `COMMAND`. The numbering is now verified through 42.

### 20b. A set's length word belongs to the set

A UCSD set sits on the stack as its data words with a **length word pushed
on top** — visible directly in `Interp.s`, where `Op8B_INN` and `OpA0_ADJ`
both pop that length before touching the data. The lifter modelled the data
as one slot but the length as a second slot, so `UNI`/`INT`/`DIF` paired
the wrong operands: they unioned a set with a length word.

Now a constant push whose value equals the width of the slot just pushed is
recognised as that slot's length word and absorbed, making a raw set
exactly one slot like every other value. Slot widths are tracked for this;
`LDM n` also now pops its source address, which `OpBC_LDM` does and the
model did not.

Set expressions come out as Pascal after this. One that previously left a
dangling address now reads:

```
  @L14^ := adjust((@L14^<8w> + [L12..L13]), 8)  { 8 words };
```

### Effect

Across all 287 procedures, unattributed stack values fall from **542 to
22**, and the newly-reported depth disagreements settle at **95**. One
procedure, `BODYPART.35`, goes from 9 disagreements to 1.

What remains is genuinely hard rather than merely unfinished: UCSD sets are
variable-length at runtime, so a static word-count model cannot always know
a set's size, and the residual cases are mostly that. Control-flow
structuring — `if`/`while`/`repeat`/`case` in place of the current
conditional gotos — is still open, and is the other half of plan step 8.

## 19. The 1.3 native procedures, disassembled

`analysis/native/PASCALCO-1.3-native.asm.txt`, from
`tools/disasm6502.py` over a plain NMOS 6502 decoder in
`tools/a2pascal/m6502.py`. This is plan step 6's first track.

**Which is which.** PASCALCO procedure 2 is `IDSEARCH` (794 bytes) and
procedure 3 is `TREESEARCH` (142 bytes). VERIFIED BINARY FACT, by
correspondence rather than by reading the code: 1.1 issues `CSP 7` once and
`CSP 8` four times, and 1.3 has exactly five matching call sites at the same
offsets in the same segment, `CGP 2` where 1.1 had `CSP 7 IDSEARCH` and
`CGP 3` at all four `CSP 8 TREESEARCH` sites.

```
   1.1                              1.3
   $0553  CSP 7  IDSEARCH           $058B  CGP 2
   $038A  CSP 8  TREESEARCH         $039E  CGP 3
   $03A6  CSP 8                     $03BC  CGP 3
   $076F  CSP 8                     $07AB  CGP 3
   $07AC  CSP 8                     $07EA  CGP 3
```

**They are linked into PASCALCO, not an intrinsic unit.** Worth stating
because the natural assumption is otherwise. They are procedures 2 and 3 of
the `PASCALCO` segment itself, reached by `CGP` — call *global* procedure,
same segment. An intrinsic unit would be a separate segment reached by `CXP`
with its own segment number, and would need a `SYSTEM.LIBRARY`, which is on
neither evidence disk. `LIBRARY.CODE` and `LIBMAP.CODE` on the 1.3 disk are
the librarian utilities, whose segments are named `LIBRARIA` and `LIBMAP`.
The build almost certainly did assemble them separately and merge them with
the UCSD Linker — that is exactly what produces native procedures inside a
Pascal segment, and it is what the procedure-number-zero marker denotes
(finding 17) — but the artifact on the disk has them inside PASCALCO.

**The reserved-word table.** IDSEARCH carries its own data, and a linear
sweep walks straight into it. Carved out and decoded in
`tools/probes/probe_reserved_words.py`:

* `$12E0`-`$1313` — 26 little-endian offsets from `$11F2`, one per initial
  letter. The seven letters that begin no Pascal reserved word — H J K Q X
  Y Z — all point at one shared 3-byte slot at `$1314` whose count is 1 and
  whose name field is `$40 $23 ...`, unmatchable by construction.
* `$1317`-`$14CE` — per letter, a one-byte count then that many 10-byte
  entries: the name padded to eight characters, a symbol class `SY`, and an
  operator sub-code `OP`.

The parse is checked four ways and passes all of them: every count equals
the number of Pascal reserved words for its letter, the 19 lists tile
`$1317..$14CE` with **zero gaps and zero overlaps**, and the 42 names
recovered are exactly the reserved words of UCSD Pascal — none missing,
none extra.

The `SY`/`OP` values are the compiler's own symbol enumeration, which is
otherwise very hard to recover and which a reconstruction has to declare.
They are internally consistent in a way that argues they are read
correctly: `AND`, `DIV` and `MOD` all carry `SY=$27` with `OP` 2, 3 and 4 —
one symbol class for the multiplying operators, distinguished by operator
code — while `OR` is `$28/07`, `IN` is `$29/0E` and `NOT` is `$26/00`,
each its own class. `PROGRAM` and `SEGMENT` share `$21`.

**Independent corroboration.** Dave Tribby disassembled the 1.2
`SYSTEM.APPLE` versions of both routines and published commented 6502
source (`evidence/reference/`). It is a different release, so it is
corroboration and not authority — where the two differ, the 1.3 binary
wins. Comparing it against the table extracted here:

* **41 of 41 of his entries match exactly**, name, `SY` and `OP`.
* **1.3 adds one reserved word: `OTHERWISE`, `SY=$36`.** A genuine 1.2 → 1.3
  language change, visible only by having both.
* His empty-letter sentinel `NUM0 .BYTE 001,040,023` is byte-for-byte the
  unexplained 3-byte slot at `$1314` above, which it now explains.
* His entry code — `PLA STA RTN / PLA STA RTN+1 / PLA TAY / PLA TAX / PLA
  STA PARAM1 / PLA STA PARAM1+1` — matches the 1.3 disassembly instruction
  for instruction, with `RTN` = `$7E` and `PARAM1` = `$94`. The zero-page
  *allocation* differs: 1.3 puts its scratch in `$7E`-`$8F`, the
  interpreter's floating-point accumulator area, where 1.2 used a low base.

**It settles CSP 7 and 8, which nothing else could.** Tribby's declarations
are `.PROC IDSearch,2` and `.FUNC TreeSearch,3`. So `IDSEARCH` is `(2, 0)`
and `TREESEARCH` is a three-argument *function*, `(3, 1)`.

The binary cannot separate `(3,1)` from `(2,0)`: both are a net −1 word,
both balance 117 procedures, and balance testing sees only the net. That is
worth recording as the method's ceiling — finding 14's technique constrains
a CSP's net stack effect and never its split. Adopting `(3,1)` keeps the
best score the binary allows and matches the only source that states the
signature.

~~**Still open.** Both procedures carry a block of word data between their
last `RTS` and their attribute table.~~ **Resolved by finding 44**, and the
guess recorded here was right: they are the four relocation tables the 1.3
manual documents, and the 26 index words are indeed among the references
they fix up. What had not fitted was the arithmetic — the pointers are
self-relative *downward*, `target = a - v`, and the areas run
`$14CE`-`$150E` and `$1592`-`$15A2`, one word higher at the top than
guessed here, because a native procedure has no EXIT IC word to skip.

With the data carved out, IDSEARCH disassembles to 138 instructions with no
undecodable bytes, landing exactly on its end address.

## 18. Peter Miller's `ucsd-psystem-xc`

<https://github.com/dhlav/ucsd-psystem-xc> — a UCSD p-System Pascal cross
compiler, cross assembler, disassembler, linker and librarian, in C++ under
GPL-2. **Not in this repo**; read from a scratch clone. Its value here is
twofold.

**As a third independent opinion on the p-machine.** `lib/pcode.h` carries
the opcode enum and a CSP enum, hand-built by Miller from the UCSD
documentation — a lineage independent of both Hyde's book and Brooks'
interpreter. It agrees with this project's decoder on all 128 opcodes
*including the two places where the other sources were shaky*:

* `SIND_0` at `$F8`, confirming the numbering against `Interp.s`'s comments,
  which label the same slots 1..8 (finding 17).
* The comparison-operator spellings `EQU`/`GEQ`/`GTR`/`LEQ`/`LES`/`NEQ`,
  which is what `pcode.py` already used; `Interp.s` spells them
  `CEQ`/`CGE`/`CGT`/`CLE`/`CLS`/`CNE`. Cosmetic, but it settles which
  convention belongs to II.0.

Its CSP enum matches `Interp.s` entry for entry across 21-40, so the CSP
numbering in finding 17 now rests on **three** independent sources — and
against Hyde's `MRK = 31`, which stays the outlier. (The two disagree on one
never-emitted entry: `27` is `TAN` to Miller, `LOG` to Brooks.)

Its `CXP_0_*` enum of segment-0 procedure numbers agrees with the table
`syscall.py` derives by parsing `GLOBALS.TEXT` — **28 of 28, no
differences**. Finding 9 was a one-source result until now.

**It also supplies the version dimension this project had been ignoring.**
Miller annotates opcodes per p-machine release (I.3, I.5, II.0, II.1), which
none of the other references do. Four opcodes turn out to be release-
dependent, and SYSTEM.COMPILER is II.0:

| op | II.0 | II.1 | I.3 / I.5 |
|----|------|------|-----------|
| `$9D` | not implemented | `LDE` | `S2P` |
| `$A7` | not implemented | `LAE` | `LDO` |
| `$D1` | not implemented | `STE` | `IXB` |
| `$D2` | not implemented | not implemented | `BYT` |

`pcode.py` lists `LDE`, `LAE` and `STE` at those slots, which is the II.1
reading. Harmless — the binary emits none of them (`IND` 339 times and `IXP`
25, but `LDE`/`LAE`/`STE` zero) — and it is now recorded rather than latent.
`$D2 = NOP` in finding 17 came from `Interp.s`, a 1.4 interpreter; Miller
has `$D2` unimplemented in II.0/II.1 alike. Neither occurs.

**As a possible validation path.** `ucsdpsys_compile` compiles UCSD Pascal
to codefiles and `ucsdpsys_disassemble` reads them back, on a modern host.
That is a far cheaper loop than plan step 7's emulator.

**It cannot be the acceptance test, though**, and it would be a serious
error to treat it as one. It is a modern reimplementation, not Apple's
compiler: it will make its own register-allocation and code-shape choices,
so equivalent source will not produce byte-identical p-code. What it can do
is fail fast — reconstructed source that will not compile, or that compiles
to obviously different structure, is wrong without needing an emulator. The
acceptance test stays what plan step 7 says: recompile under Apple Pascal
itself and diff.

Neither tool has been built or run yet; this finding is from reading the
source.

## 22. The compiler's own symbol table, read out of COMPINIT

Two initialisation procedures in COMPINIT turn out to be the most
informative code in the whole compiler, because they build the compiler's
central data structures out of *constants* and then, immediately
afterwards, attach names to them. `tools/probes/probe_stdtypes.py`
recovers both mechanically from either disk.

### 22a. A function call reserves a two-word result area

**VERIFIED BINARY FACT.** This is the key that unlocked the rest.
`PASCALCO.15` declares six parameter bytes — three words — but its body
only ever reads the third of them, and every call site looks like

```
  SLDL 3 / SLDC 0 / SLDC 0 / CGP 15
```

The two zeros are not arguments. They are the result area the caller
reserves: two words, enough for a `real`, sitting at the top of the
callee's parameter block, and `RNP n` says how many of them carry a value
back.

`tools/probes/probe_funcresult.py` tests it with a control. Across both
releases, **154 of 154 call sites whose target ends in `RNP n`, n > 0, are
preceded by two pushes of zero — and 0 of 2961 procedure call sites are.**
No function declares fewer than two parameter words. A cleaner separation
is hard to ask for.

Consequences, both now in the lifter:

* A function's real argument count is `param_size/2 - 2`. Listings say
  `args`, not `params`, and no longer print the placeholder zeros.
* `TREESEARCH`'s native signature was wrong. Tribby's 1.2 listing declares
  `.FUNC TreeSearch,3`, which was taken as three words popped; the
  convention makes it three *arguments* plus the result area, so five.
  With that fixed the call reads `TREESEARCH(L3, @L3, @G17)` — exactly the
  three operands 1.1 passes to `CSP 8` — and one more procedure structures
  cleanly.

### 22b. The standard types, and the `structform` enumeration

**VERIFIED BINARY FACT** for the mapping, since the compiler states it
itself: the standard-identifier initialiser stores `LPA 'INTEGER '` into a
symbol-table entry and then stores the type pointer into the same record.

| 1.1 | 1.3 | name | descriptor |
|-----|-----|------|------------|
| G12 | G12 | `INTEGER` | size 1, form 0 scalar, standard |
| G61 | G64 | `REAL` | size 2, form 0 scalar, standard |
| G59 | G62 | `CHAR` | size 1, form 0 scalar, standard |
| G58 | G61 | `BOOLEAN` | size 1, form 0 scalar, scalkind 1 declared |
| G54 | G55 | `STRING` | size 41, form 5 arrays, packed, elt `CHAR`, len 80 |
| G57 | G60 | `TEXT` | size 301, form 7 files, elt `CHAR` |
| G55 | G56 | `INTERACTIVE` | size 301, form 7 files, elt `CHAR` |
| G56 | G59 | (`nil`'s type) | size 1, form 2 pointer, elt nil |
| G60 | G63 | (long integer) | form 3, size `LONGSIZE(5)` |
| —   | G57 | `BYTESTREAM` | **1.3 only.** form 5 arrays, packed, elt `CHAR`, string flag **0** |
| —   | G58 | `WORDSTREAM` | **1.3 only.** form 5 arrays, unpacked, elt `INTEGER` |

The forms observed — 0, 1, 2, 3, 5, 7 — fix the enumeration as

```
  (scalar, subrange, pointer, longint, power, arrays, records, files, ...)
```

which is Zurich's list with `longint` inserted after `pointer`. That is
**STRONG INFERENCE** on the two members never observed (`power` at 4,
`records` at 6), and VERIFIED for the six that are. It matters: a
reconstruction has to declare this type in the right order or every
`form` comparison in the compiler shifts.

`longint` being a distinct form is right for Apple Pascal, which has
`integer[n]` long integers. `PASCALCO.17` sizes them: `((n+3) div 4) + 1`
words for `n` decimal digits — four digits per word plus a header word.
Its two constant arguments corroborate it. The default long-integer type
is built with `n = (16-1)*100 div 332 + 1` = 5, the digits a 16-bit word
holds (100/332 ≈ log₁₀2), and the one other constant call site passes
**36**, UCSD's documented maximum long-integer length.

### 22c. The two record layouts

**VERIFIED BINARY FACT**, from the field offsets the initialiser writes.

The type descriptor (`structure`): word 0 `size` in words, word 1 `form`,
variant part from word 2. For `arrays` the variant is index type (2),
element type (3), packed flag (4), element bits (5), elements per word
(6), **string flag (7)**, declared length (8).

Word 7 is the field that separates a declared `STRING` from any other
packed array of char, and 1.3 proves it: `BYTESTREAM` is byte-for-byte a
packed char array like `STRING` but sets word 7 to **0**. DECLARAT's
`STRING[n]` handler confirms the rest — it `MOV`s all nine words of the
standard descriptor, then overwrites word 8 with `n` and word 0 with
`(n+2) div 2`, after range-checking `n` against 1..255 and reporting
error 203.

The symbol-table entry (`identifier`): words 0–3 the eight-character name,
4 `llink`, 5 `rlink`, 6 `idtype`, 7 `next`, 8 `klass`, variant from 9.
This is Zurich's record exactly, and it independently corroborates finding
19 — the native `TREESEARCH` walks words 4 and 5 as its left and right
subtree links. `klass` values 0..6 are all observed, with record sizes
9, 10, 11, 11, 13, 18, 18 words; 0 = `types`, 1 = `konst`, 2 = `vars`
(`INPUT` and `OUTPUT` are entered with it), 5 and 6 the two 18-word
classes, i.e. `proc` and `func`.

### 22d. Four more service routines named

**STRONG INFERENCE** for all four; each matches a routine of the published
Zurich/UCSD compiler line for line.

* **`PASCALCO.9` = `GETBOUNDS(fsp; var fmin, fmax)`.** Sets both to 0;
  for `form = subrange` reads the bounds out of the descriptor; for
  `fsp = CHARPTR` sets `fmax := 255`; otherwise takes the last enumeration
  constant's value from `fsp^.fconst^.values`. That last branch is what
  identified word 9 of an `identifier` as the `konst` variant.
* **`PASCALCO.15` = `STRING(fsp)`** — form is `arrays`, packed, element
  type `CHAR`. The classic Zurich predicate.
* **`PASCALCO.16` = `STRINGTYPE(fsp)`** — `STRING(fsp)` *and* the word-7
  string flag. Used as a boolean at every call site.
* **`PASCALCO.17` = `LONGSIZE(n)`** — see 22b. The name is invented; the
  arithmetic is not.

Two more fell out of reading the same code: **`PASCALCO.5` = `ENTERID`**
(the standard-identifier initialiser builds a record and hands it to this
routine, once per name) and **`PASCALCO.18` = `CONSTANT(fsys; var lsp,
lvalu)`** (called with a symbol set and two `VAR` addresses to parse the
bracketed length in `STRING[n]`). Also **`G15` = `SY`**, the current
symbol: written 20 times inside `INSYMBOL` and nowhere else of substance,
read 256 times.

All of this now lives in `tools/a2pascal/names.py`, and the lifter uses
it, so `analysis/lifted/` reads `PASCALCO.10:SEARCHID` and `CHARPTR`
instead of bare numbers.

## 23. The Apple Pascal 1.3 manual, and the compiler's own option table

**Source.** The Apple Pascal 1.3 manual set, scanned with an OCR text layer,
932 pages —
`evidence/reference/manuals/Image071217212805.pdf.duplex_text.pdf`, with the
OCR flattened to `analysis/reference/apple-ii-pascal-1.3-manual.txt` by
`tools/reference_text.py`. Page citations below
are the manual's own part/page numbers, which is what to quote. The OCR is
usable but not clean: it renders `{$S-}` as `{$5 --}` and mangles the option
list on II-155 badly enough that the page had to be re-read as an image.
Check anything load-bearing against the rendered page.

This is the first vendor documentation in the project, and it lands on
three things the binary had left open.

### 23a. The procedure attribute table, and the function result area

IV-33 gives the attribute-table layout field for field, and it matches the
reader in `codefile.py` exactly. Two fields are worth quoting.

**PARAMETER SIZE** — "This field specifies the number of bytes of
parameters passed to a procedure from its calling procedure. *If the
procedure is a function, this number includes the number of bytes to be
reserved for the returned value.*" That is finding 22a, from the vendor,
independently of the 154-out-of-154 census. VERIFIED SOURCE FACT.

**RNP** (IV-73) — "DB is the number of words that should be returned as a
function value (0 for procedures, 1 for nonreal functions, and 2 for real
functions)." Consistent with the `RNP` census: all 19 functions in the
compiler return one word, so none of them returns a real. Note the
refinement the binary adds and the manual does not state: the caller
reserves **two** words regardless — every one of the 19 has
`param_size/2 - 2` real argument words, not `- 1`.

**LEX LEVEL** — "the lexical level of the Pascal operating system is -1,
the lexical level of a user program is 0, that of the first nested
procedure is 1, and so forth." That closes the last open question in
finding 16.

### 23b. CGP is same-segment — a lifter bug

IV-73: `CGP` is "Call global procedure. Call procedure number UB, which is
at lexical level 1 **and in the same segment as the currently executing
procedure**." The lifter had been resolving `CGP` against segment 1
throughout, which is indistinguishable from the manual's rule everywhere in
the compiler except one site — and that site exists:

    DECLARAT.11, 1.1 $104D / 1.3 $106B
        SLDC 4 / LDCI 512 / SLDC 1 / UNI / ADJ 4     { a four-word set }
        CGP 1

`DECLARAT.1` takes 8 bytes of parameters; `PASCALCO.1` takes 4. The set
being pushed is four words. So the call is `DECLARAT.1`, the phase's own
entry point, taking a symbol set — and the lifter had been rendering it as
`PASCALCO.1` with the arguments truncated. Fixed; the one join in each
release where the paths disagreed on stack depth at that point went away
with it (91 → 89). VERIFIED BINARY FACT, and a good argument for reading
the vendor documentation earlier than this.

`CBP` (lex -1 or 0) never occurs in the compiler, so nothing rests on it.

### 23c. `{$U-}`, and what the compiler was actually compiled with

II-155: `{$U-}` "Tells the Compiler to compile the program at the system
lexical level. Also sets certain other options as follows: R-, G+, I-, V-."

`COMPOPTI.1` is a `case` on the upper-cased option letter over 67..86,
`'C'`..`'V'`, and its `'U'` arm is that sentence in p-code:

    85 'U':  if (L5 = '+') or (L5 = '-') then begin
               SYSCOMP    := (L5 = '-');
               RANGECHECK := not SYSCOMP;      { R- }
               IOCHECK    := RANGECHECK;       { I- }
               VARSTRING  := RANGECHECK;       { V- }
               GOTOOK     := SYSCOMP;          { G+ }
             end else ...open the $U library file...

Four flags, exactly the four the manual names, each with the polarity the
manual gives — and each is independently confirmed as that option's flag by
its own arm of the same `case`: `'R'` writes `RANGECHECK`, `'I'` writes
`IOCHECK`, `'V'` writes `VARSTRING`, `'G'` writes `GOTOOK`. Reading the
letter-to-global mapping off the case table is a VERIFIED BINARY FACT; the
spellings above are ours.

That mapping names a block of globals. 1.1 numbering, 1.3 in
`tools/a2pascal/names.py`:

| letter | 1.1 global | meaning | default set by COMPINIT.9 |
|---|---|---|---|
| `$C` | 487 | codefile comment, `string[80]` | `nil` |
| `$D` | 50 | debug: `BPT` before every statement (24a) | 0 |
| `$E` | 45 | file variables in a unit's implementation (24a) | 0 |
| `$F` | 30 | flip: byte-swap emitted words (24a) | 0 |
| `$G` | 52 | goto allowed | 0 — manual says `{$G-}` |
| `$I` | 47 | I/O check (or include file) | 1 — `{$I+}` |
| `$L` | 43 | listing | 0 — `{$L-}` |
| `$N` | 35 | no load | 0 — `{$N-}` |
| `$NS` | 85 | next segment number | 7 |
| `$Q` | 49 | *inverted*: true when quiet is off | from `I3,14` |
| `$R` | 51 | range check (or resident) | 1 — `{$R+}` |
| `$S` | 34, 33 | swapping, and the `$S++` second flag | 0 — `{$S-}` |
| `$T` | 42 | tiny: omit 15 built-ins (24a) | 0 |
| `$U` | 28 | compile at system level | 0 — `{$U+}` |
| `$V` | 39 | varstring check | 1 — `{$V+}` |

Every documented default in that last column is the manual's default. Four
letters — `D`, `E`, `F`, `T` — are boolean option flags with no entry in
the manual. They were named `OPT_D` and so on rather than guessed at; what
they do is finding 24a.

`$NS` is the sharpest of these. II-152: "the letters NS followed by an
unsigned integer which should be in the range 7..57 for a 128K system and
7..31 for a 64K system." The code parses at most two digits and accepts the
value only `if (n > NEXTSEG) and (n < 31)` in **1.1** — the 64K bound, on
the nose, with the default sitting at the bottom of the documented range.
1.3 raises it to 63, the 128K bound; see finding 27a, which corrects the
version confusion in an earlier draft of this paragraph.

**And the compiler itself was not compiled with `{$U-}`.** `PASCALCO.1` has
`lex=0`, which 23a says is the *user program* level; system level would be
-1. The mechanism is visible in the compiler's own state: `G13` is Zurich's
`level`, initialised to 1 by `COMPINIT.9` and reset to 0 in the `SYSCOMP`
branch of `COMPINIT.1`, just before the program heading is parsed, and the
emitted LEX LEVEL byte is one
less than it. So `{$U-}` would have produced `lex=-1` for the outermost
block. It did not. Nothing in either codefile carries a negative lex level
— every system utility on both disks (`SYSTEM.LINKER`, `SYSTEM.ASSMBLER`,
`LIBRARY.CODE`, `LIBMAP.CODE`) has exactly the same shape, one lex-0 main
and everything else at 1 or deeper. STRONG INFERENCE, one step short of
verified only because neither disk carries `SYSTEM.PASCAL`, which is the
one artifact on hand that *was* built `{$U-}` (`GLOBALS.TEXT` line 2). If a
boot disk is ever added to `evidence/`, that is the check to run.

What the compiler *was* built with is partly recoverable the same way.
There is not one `CHK` instruction in 18,458 p-code instructions across the
1.1 compiler, against 85 `IXA` array indexings — `{$R+}` is the default and
would have emitted them everywhere. So the source carries an explicit
`{$R-}`, and given that it is full of `goto`, a `{$G+}` as well. Both are
directives the reconstruction has to reproduce.

### 23d. The four file variables

Finding 16 listed four FIBs at words 535, 586, 626, 666 without knowing
which was which. `PASCALCO.1` opens the whole program with four `FINIT`
calls, and the option handler and the reader loops say what each one is:

| 1.1 | 1.3 | file |
|---|---|---|
| 535 | 665 | `*SYSTEM.INFO[*]`, the unit symbol-table work file (`UNITPART.2`) |
| 586 | 716 | the library — `SYSTEM.LIBRARY`, or the `$U filename` argument |
| 626 | 756 | the source text, read two blocks at a time into `G1`; also what `$I filename` reopens |
| 666 | 796 | the listing — `*SYSTEM.LST.TEXT`, or the `$L filename` argument |

The window buffers keep the +300 offset in 1.1 (835, 886, 926, 966) and in
1.3 (965, 1016, 1056, 1096). The internal layout of a FIB is still not
resolved; only the identities are.

`PASCALCO.1` in full is now four `FINIT`s, `COMPINIT.1`, a two-way branch on
`SWAPPING` into `PASCALCO.28` or `PASCALCO.25`, and four `FCLOSE`s. That is
the whole program body, and it confirms `G34` as the `$S` flag from a second
direction.

### 23e. Two more manuals, and what they confirm about 1.1

Both are now in `evidence/reference/manuals/`, with OCR text in
`analysis/reference/`:

* `Apple_Pascal_Update_v1.1_text.pdf` — the Version 1.1 update notice
  bound with the 1.2 addendum. Two-column, readable.
* `Apple Pascal Language Reference Manual.pdf` — the 1980 edition,
  Apple product #A2L0027, 120 pages of two-up scans. This is the 1.1-era
  language reference, so it is the right authority for the standard-
  identifier table in finding 22b. It has since been OCRed.

  Its option summary (p. 70) is the 1.0 set — ten letters, `C G I L N P Q
  R S U`, with neither `$V` nor `$NS`, which is what dates it: the update
  notice lists both as new in 1.1. Like the 1.3 manual it documents none of
  `$D`, `$E`, `$F`, `$T`, so those four were undocumented from the
  beginning rather than dropped from the documentation later. With one
  slip: the page's syntax example for combining options is

  > `(*$option,option*)` Example: `(*$F-,S+,G+*)`

  — `$F`, in a manual that never says what `$F` is.

Three things in the update notice line up with the 1.1 binary:

* "Compiler options are no longer required to be capitalized." That is the
  `if (L6 > 96) then L6 := L6 - 32` at the head of `COMPOPTI.1` — the arm
  dispatch happens on the upper-cased letter, in both releases.
* `$V` and `$NS` are both listed as *new in 1.1*, and both arms are present
  in the 1.1 binary (`VARSTRING`, `NEXTSEG`).
* 1.1 raised the codefile limit to 16 segments, "one for the program itself,
  and up to 15" for the rest, against 6 before. `SYSTEM.COMPILER` has 15,
  and could not have been built by its predecessor.

## 24. The undocumented option letters, the code emitters, and `LDC`'s word order

**Source.** Neil Parker, *Undocumented Secrets of Apple Pascal*,
`evidence/reference/Undocumented Secrets of Apple Pascal.html`. Parker
worked from the UCSD II.0 source; the compiler binary is the check, and in
one place below it contradicts him.

This finding closes the four-open-letters question left by finding 23c, and
it turned up a decoder bug that had been silently corrupting every set
constant in the corpus.

### 24a. `$D`, `$E`, `$F`, `$T`

They are undocumented in the strong sense. Table 14-1, III-241, is the
manual's complete option summary, and it lists thirteen forms — `$C`, `$G`,
`$I±`, `$I filename`, `$L±`, `$L filename`, `$N`, `$NS`, `$P`, `$Q`, `$R±`,
`$R name`, `$S`, `$U±`, `$U filename`, `$V`. Not one of `D`, `E`, `F`, `T`
appears anywhere in it. All four nevertheless have live arms in
`COMPOPTI.1` in **both** releases (1.1 lines 7580-7680 of the lifted
listing), each writing its own boolean, each defaulted to 0 by `COMPINIT.9`.

**`$D` — Debug. VERIFIED BINARY FACT.** `STATEMEN.1`, immediately after the
statement's leading symbol is consumed:

    if OPT_D then begin
      BODYPART.5:EMITOP1(85, (G92+1));
      G46 := 1;
    end;

`85 + 128 = 213 = $D5 = BPT`, and IV-76 gives `BPT 213 B` —
"Breakpoint. Not used (acts as a NOP)" — one `B` parameter, which is
exactly the one operand `EMITOP1` emits. `G92` is the line counter. So
`{$D+}` emits `BPT <line>` before every statement, which is Parker's
description confirmed instruction for instruction. The corollary is a fact
about the artifact rather than the option: **there is not one `BPT` in
either release**, so `SYSTEM.COMPILER` was compiled `{$D-}`.

**`$T` — Tiny. VERIFIED BINARY FACT, and the omit list is now recovered.**
Parker could only say Apple's list was "probably similar" to II.0's.
`COMPINIT.7` spells the standard identifiers out as a run of `LSA` string
literals, 44 names in order, then walks them with a 1-based counter:

    if OPT_T then begin
      if not ((L2 in {2,7,10,13,17,18,19,20,32,34,35,40,42,43,44}))
        then goto L067E;
    end else begin
    L067E:
      ...enter the identifier...

Being *in* the set means falling past the enter block, so the set is the
omit list. Resolved against the names, Apple omits fifteen:

> `COPY DELETE GET GOTOXY INSERT PAGE POS PRED PUT READLN SEEK SQR STR
> UNITREAD UNITSTAT`

II.0's fifteen, as Parker gives them, differ in exactly two places: II.0
omits `SUCC` and Apple does not, and Apple omits `UNITSTAT`, which does not
exist in II.0. Everything else matches, which is a good sign for both
lists.

**`$F` — Flip. VERIFIED BINARY FACT for the mechanism.** `PASCALCO.21`, the
routine that emits one *word* into the code buffer, ends:

    if OPT_F then begin
      L2 := G2^[G9];
      G2^[G9] := G2^[(G9+1)];
      G2^[(G9+1)] := L2;
    end;

— a byte swap of the word just written, which is Parker's "opposite byte
order from that normally used by the host computer". `OPT_F` is read at one
other site, `PASCALCO.13`, where it inverts a boolean rather than swapping
anything; that site is not yet understood and is not claimed here.

**`$E` — not in Parker, and not in any manual on hand.** Both of its uses
are about file variables inside units, and both make sense only together:

* `DECLARAT.3` and `.4`, on `SY = 46` (`FILE`, from the reserved-word table
  of finding 19) — `if INUNIT then if not (ININTERFACE or OPT_E) then
  ERROR(191)`. A file variable may be declared in a unit's *interface*
  freely, but in its implementation part only under `{$E+}`.
* `BODYPART.25`, the block-body generator —
  `if (not INUNIT or OPT_E) then` … walk the block's file variables and
  emit `FINIT` for each. Inside a unit, no `FINIT` is generated unless
  `{$E+}`.

So `$E` is a single switch over "this unit may own file variables, and is
responsible for initialising them". Naming it is left open; `OPT_E` is what
`names.py` calls it. STRONG INFERENCE for the reading, VERIFIED BINARY FACT
for the two gates.

### 24b. `ININTERFACE` and `INUNIT`

**VERIFIED BINARY FACT.** 1.1 globals 31 and 32; 1.3 globals 32 and 33,
carried across by the correspondence table. Both are written only in
`UNITPART`. `UNITPART.3` raises error 182 if `INUNIT` is already set —
units do not nest — then saves `LEVEL` and the segment counter, sets
`INUNIT` and clears `ININTERFACE`. `ININTERFACE` is true between the unit
heading and `SY = IMPLEMENTATION` (`$34 = 52`). They are what `$E` above is
tested against, and they are the state the reconstruction needs for
`UNITPART` to be writable at all.

### 24c. The code emitters

**VERIFIED BINARY FACT.** `PASCALCO.20:EMIT(b)` writes one byte
(finding 12). Sitting on top of it, in `BODYPART`, is the compiler's entire
code-generation interface — five routines whose *opcode argument is the
opcode minus 128*:

| 1.1 | 1.3 | name | signature |
|---|---|---|---|
| `BODYPART.3` | `.3` | `EMITOP` | `(op)` — opcode alone; pads with `NOP` before `LSA` |
| `BODYPART.4` | `.4` | `EMITCONST` | `(v)` — push integer `v`: short `SLDC`, or `LDCI`+`NGI` |
| `BODYPART.5` | `.5` | `EMITOP1` | `(op, arg)` — opcode + one operand byte |
| `BODYPART.6` | `.6` | `EMITOP2` | `(op, lex, off)` — picks the short form when it can |
| `BODYPART.27` | `.28` | `EMITBIG` | `(n)` — the `B` encoding |

The spellings are ours. The numbering claim is the binary's, and
`tools/probes/probe_emitters.py` is two checks it could fail:

* **`EMITOP1`'s literal opcodes.** It emits exactly one operand byte, so
  every literal `op` passed to it must name a one-operand instruction.
  Only 37 of the 128 opcodes in `$80-$FF` qualify. All **15** distinct
  literals in each release land inside those 37.
* **`EMITOP2`'s `+20`.** When the operand it would emit is the degenerate
  one — lex level 0, or an integer comparison — it adds 20 to the opcode
  and emits the short form instead. That is a claim about the *encoding*,
  and the encoding either has that structure or it does not:

  `LDA $B2 → LLA $C6`, `LDC $B3 → LDCI $C7`, `LOD $B6 → LDL $CA`,
  `STR $B8 → STL $CC`, and `EQU/GEQ/GRT/LEQ/LES/NEQ $AF-$B7 →
  EQUI/GEQI/GRTI/LEQI/LESI/NEQI $C3-$CB`.

  Ten pairs, all exactly 20 apart. (The `-13` in the same routine is the
  second adjustment on the same path.)

`EMITBIG` reproduces the `B` encoding the decoder assumes: one byte for
values under 128, otherwise two with bit 7 set on the first. IV-58 states
the same rule, with an OCR flaw — it says bit 7 "is cleared", where both
the binary and the two-byte case's own arithmetic say set.

`BODYPART.25:BODY` is the block-body generator that uses them. It emits
`BODYPART.6(77, 0, 3)` — `CXP 0,3`, `FINIT` — once per file variable, with
the `+300` window-buffer offset of finding 23d visible in the second
`EMITOP2` of each pair, then the `CXP seg,1` unit-initialisation calls,
then loops over statements while `SY` is in `G102`.

### 24d. `LDC` stores its words in reverse — and every set constant was wrong

**VERIFIED BINARY FACT, and VERIFIED SOURCE FACT.** `LDC UB` is followed by
`UB` words of inline constant. The decoder was reading the first word in
the code stream as word 0 of the value. It is the last one.

For a set that renames every member — word *j* carries members
*16j..16j+15* — so the error was invisible in a sync check and total in the
output. Four independent readings, each gibberish under the old order:

* **`COMPINIT.7`'s two sets** are indexed by position in a 44-name list the
  same procedure spells out in ASCII. The old order put members at 0, 45
  and 47; the new one puts all 32 inside 1..44. And `SET2` comes out as
  *exactly* the seventeen value-returning built-ins — `EOF EOLN PRED SUCC
  ORD SQR ABS CONCAT LENGTH COPY POS TREESEAR SCAN BLOCKREA BLOCKWRI TRUNC
  SIZEOF` — which is a fact about Pascal, decided nowhere in this decoder.
* **`G102`**, tested at the head of every statement loop, is exactly the
  eight reserved words that can start a statement: `BEGIN IF CASE REPEAT
  WHILE FOR WITH GOTO`.
* **`G114`** is exactly the nine that can open a declaration part:
  `BEGIN LABEL CONST TYPE VAR PROCEDURE FUNCTION PROGRAM/SEGMENT USES`
  (`$21` is both `PROGRAM` and `SEGMENT`), and `UNITPART` later adds `UNIT`
  to it — `G114 := G114 + {50}`.
* **`G98`** is exactly the four structured-type words: `SET ARRAY RECORD
  FILE`.
* **`BODYPART.6`'s** comparison set is exactly `EQU GEQ GRT LEQ LES NEQ`.

`tools/probes/probe_ldc_order.py` runs the first of those and additionally
asserts the *opposite* order fails, so the probe cannot pass vacuously.

Apple then states it outright. IV-61, "Formats of Constants in P-Code":

> All reals, sets, and long integers are word-aligned and in REVERSE word
> order, that is, the higher-order bits of the real or set are in
> lower-numbered memory locations.

and IV-64 for the instruction itself: "`LDC 179 UB,<data>` — Load
multiple-word constant. Fetch the word-aligned `<data>` of UB words **in
reverse word order**, and push the data." `LDM` and `STM` say the same. The
binary was read first and the manual agrees with it.

The renderer in `tools/a2pascal/lift.py` now prints set members rather than
words. `LDC` also loads two-word `REAL` constants, so members are shown
only where the constant cannot be one: three words or more, a procedure
with no real arithmetic anywhere in it, or — for the single site that has
both — an instruction that consumes the value as a set before anything
consumes it as a real. There are nine real-arithmetic instructions in the
entire compiler, so almost every procedure takes the readable path.

### 24e. Parker on `{$U-}`, and why he is wrong about this binary

Parker lists `SYSTEM.COMPILER` among the codefiles compiled `{$U-}`, and
gives four criteria for telling: a `{$U-}` program has its main body at lex
−1 in **segment 0**, its segment procedures numbered from 1, exits through
`XIT` rather than `RBP`, and takes no argument words.

Every one of them says the opposite here. `PASCALCO` is segment **1**; the
phase segments are **7-20**, not 1, 2, 3…; `PASCALCO.1` is **lex 0**, the
user-program level of 23a; and it ends in `RBP`. Finding 23c reached the
same conclusion from `COMPOPTI.1`'s `'U'` arm and the absence of `CHK`.
Parker is corroborated on the *criteria* and contradicted on the *file*.

One thing he supplies that nothing else did: a `{$U+}` main program is
passed "two useless words" of arguments. That is `PASCALCO.1`'s 4-byte
parameter block, which finding 22a had counted but not explained.

## 25. The decoder's opcode table, against Apple's

**VERIFIED SOURCE FACT.** Everything in `tools/a2pascal/pcode.py` came from
Hyde's *P-Source*, John Brooks' 1.4 interpreter and semantic probes against
the binaries (finding 7) — no vendor documentation. Part IV, Chapter 4 of
the 1.3 manual, "The P-Machine Instruction Set" (IV-57..IV-76), is vendor
documentation: every opcode by decimal number with its parameter list, then
repeated as Table 4-1 in numerical order.

`tools/probes/probe_manual_opcodes.py` transcribes Apple's table and holds
the decoder against it. **85 numbered opcodes and all four short-form
ranges agree, mnemonic and parameters.** Nothing had to be changed. That
covers both corrections of finding 7 — the `$D8`/`$E8`/`$F8` boundaries and
`$D0 LPA` — and promotes `$D7 NOP`, previously STRONG INFERENCE, to stated
fact (215 NOP, "sometimes used to reserve space in the code for later
additions").

Three decoder entries are *not* in Apple's table: `$D2 NOP`, `$D3 EFJ`,
`$D4 NFJ`, carried from Brooks so an unexpected byte reports as itself.
None occurs in `SYSTEM.COMPILER`, and 210-212 are simply unassigned in the
manual, so there is no conflict — but they remain the weakest rows.

Details the manual settles that the decoder had inferred:

* The comparison type codes are Apple's: `2` reals, `4` strings, `6`
  booleans, `8` sets, `10` byte arrays, `12` words — matching `CMP_TYPES`
  exactly. It also confirms that `10` and `12` alone carry an extra `B`
  operand (the byte count), which is the conditional branch in the `cmp`
  decoder.
* `XJP`'s layout (IV-72) is the one finding 21 recovered from the
  interpreter: `W1` min, `W2` max, the case table of `W2-W1+1`
  self-relative words, `W3` past the table — and out-of-range points IPC at
  `W3`, not at a default pointer.
* `RNP DB` is "0 for procedures, 1 for nonreal functions, 2 for real
  functions", already quoted in 23a.
* Sets on the evaluation stack carry a length word that `ADJ` strips before
  a store; sets in an activation record do not. That is why every set
  constant in the listing is followed by `adjust(…, n)`.

## 26. The scanner's two enumerations, and eight symbol sets

**VERIFIED BINARY FACT** for every code below; the *spellings* are the
Zurich P2 / Pascal-P ones and are STRONG INFERENCE, for the reasons in 26c.

`SY` (global 15) and `OP` (global 16) are written together by the scanner
for every token, and between them they are the compiler's whole idea of
what it is looking at. Both enumerations are now recovered **complete and
with no gap**: `SYMBOLS` covers 0..54 with 55 entries, `OPERATORS` covers
0..15 with 16. `tools/probes/probe_symbols.py` checks all of it.

### 26a. `SYMBOL`, from three places at once

No single source names all 55. Three do, between them, and they overlap
enough to cross-check:

* **6..13, 19..34, 38..46, 49..54** — the reserved-word table embedded in
  1.3's native `IDSEARCH` (finding 19) stores an `SY` and an `OP` beside
  each of its 42 words. Those are the binary's own bytes.
* **0..5, 14..18, 35, 37, 39..41, 47** — `PASCALCO.6:INSYMBOL` is one
  `case` over the source character, with a `SY := n` in each arm. The
  character names the code: the arm for `[` assigns 15, so 15 is `lbrack`.
* **36, 48** — `NUMSTRIN`, the number scanner. The floating path sets 36;
  the BCD path — the one that raises error 203 past 36 digits, which is
  `INTEGER[n]` — sets 48.

Three of the arms look one character ahead and so have two outcomes each,
and all three are the classic Pascal ambiguities: `.` is `period` alone
but `colon` in `..`, `:` is `colon` alone but `becomes` in `:=`, and `(`
is `lparent` unless it opens a `(*` comment. `SY := 47` is what an
unrecognised character gets, and `INSYMBOL` immediately tests for 47 and
raises **error 400, "Illegal character in text"** — which is the vendor
naming `othersy` for us.

Two details worth carrying into the reconstruction. `PROGRAM` and
`SEGMENT` **share** code 33, so they are one enumeration constant, not
two. And 48, `longconst`, has no counterpart in Pascal-P at all; it is the
UCSD/Apple long-integer literal.

### 26b. `OPERATOR` is Pascal-P's, verbatim

`OP` qualifies `mulop`, `addop` and `relop`, and is 15 otherwise. Reading
it off the reserved-word table (`AND`=2, `DIV`=3, `MOD`=4, `OR`=7,
`IN`=14) and off the scanner (`*`=0, `/`=1, `+`=5, `-`=6, `<`=8, `<=`=9,
`>=`=10, `>`=11, `<>`=12, `=`=13) gives every slot from 0 to 15:

| 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|
| `mul` | `rdiv` | `andop` | `idiv` | `imod` | `plus` | `minus` | `orop` |

| 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 |
|---|---|---|---|---|---|---|---|
| `ltop` | `leop` | `geop` | `gtop` | `neop` | `eqop` | `inop` | `noop` |

That is Pascal-P's `operator` enumeration in its published order, all
sixteen members, nothing added and nothing moved. It is the strongest
single piece of evidence so far that this compiler is a direct descendant
of the Zurich P2 compiler, and it is why the spellings elsewhere in this
finding are worth more than a guess.

### 26c. Eight symbol sets, each pinned by the error it guards

Eight globals hold a `set of symbol`. `COMPINIT.10` does nothing but
initialise them — one `LAO`/`LDC`/`ADJ 4`/`STM 4` each — and each is then
tested against `SY` at the head of a parser that raises a *specific* error
when the test fails. The Apple Pascal error list (II-3E) says what those
errors mean, so the error number is an independent statement of what each
set is for, from the vendor, with no inference in between:

| 1.1 | 1.3 | name | members | guard raises |
|---|---|---|---|---|
| 126 | 129 | `constbegsys` | ident intconst realconst stringconst addop longconst | **50** "Error in constant" |
| 122 | 125 | `simptypebegsys` | `constbegsys + [lparent]` | **1** "Error in simple type" |
| 118 | 121 | `typebegsys` | `simptypebegsys + [arrow, setsy, packedsy, arraysy, recordsy, filesy]` | **10** "Error in type" |
| 98 | 101 | `typedels` | setsy arraysy recordsy filesy | **10**, after `PACKED` |
| 114 | 117 | `blockbegsys` | beginsy labelsy constsy typesy varsy procsy funcsy progsy usessy | **18** "Error in declaration part" |
| 110 | 113 | `selectsys` | lbrack arrow period | **59** "Error in variable" |
| 106 | 109 | `facbegsys` | ident lparent lbrack intconst realconst stringconst notsy longconst | **58** "Error in factor (bad expression)" |
| 102 | 105 | `statbegsys` | beginsy ifsy casesy repeatsy whilesy forsy withsy gotosy | — drives the statement loops |

Error 10 does not separate `typebegsys` from `typedels` — `DECLARAT.3`
raises it twice, once at entry and once after `PACKED` — but their
memberships do, and `typedels` is exactly Pascal-P's. `statbegsys` has no
error of its own because it is a loop condition rather than a guard; its
membership is the eight statement-starting words and nothing else.

Two of these are built at run time out of the one below them, which is why
their rows give an expression rather than a list. That nesting —
`constbegsys` ⊂ `simptypebegsys` ⊂ `typebegsys` — is itself Pascal-P's
structure, and it means the reconstruction has to emit them in that order.

`UNITPART` later adds `unitsy` to `blockbegsys`, which is visible as
`BLOCKBEGSYS := BLOCKBEGSYS + [unitsy]`.

### 26d. What this changes in the listings

`tools/a2pascal/lift.py` now prints set members by symbol name, but only
where the constant is genuinely a symbol set: the value has to be pushed
on top of `SY` (an `SY in ...` test) or on top of one of the eight globals
(the `COMPINIT` setup). That restriction matters — the scanner tests
source characters against `{48..57}` and `COMPINIT.7` indexes its
standard-identifier table with two more sets, and naming *those* members
would be actively wrong. The compiler now reads as, for instance,

    until (SY in (STATBEGSYS + {endsy,unitsy,implsy}));

Named with them: `PASCALCO.14:SKIP`, whose entire body is
`while not (SY in fsys) do INSYMBOL` — Pascal-P's `skip`, and the routine
called immediately after 37 of the compiler's `ERROR` sites; and
`PASCALCO.12:NEXTLINE`, which advances `LINENUMBER`, echoes the progress
dot and writes the listing line. Plus the scanner's working set:
`SOURCEBUF` (global 1), `CHINDEX` (14), `OP` (16), `LGTH` (22), `VAL` (23)
and `LINENUMBER` (92 in 1.1, 95 in 1.3).

### 26e. A stack-model gap this exposed

A set small enough to build inline is pushed as immediate `SLDC`s — data
word first, then the length word — rather than as an `LDC` block. The
lifter models a set as one stack slot, so those two words desynchronise
it, and `COMPINIT.10` comes out with `16^ := adjust((1 + CONSTBEGSYS),4)`
where the target should be `SIMPTYPEBEGSYS`. The p-code is unambiguous and
the table above is read from it directly; it is the *rendering* that is
wrong. This is the same class as the 89 depth conflicts of finding 20 and
is recorded here rather than papered over.

Also unresolved, and deliberately not named: 1.1 global 130 is
initialised in `COMPINIT.10` to a one-word set `{2,3}` and then passed to
`SEARCHID`. Pascal-P's `searchid` takes a `set of idclass`, so those are
almost certainly `klass` codes 2 and 3 — `vars` and `field` — and not
symbols at all. It is left alone until the `klass` enumeration of finding
22 is settled.

## 27. Eight more PASCALCO routines, and a name that was wrong

Naming continued from finding 26, using the vendor's error list as the
lever: a routine that raises error 354 is doing something about segment
numbers whatever else it does. **VERIFIED BINARY FACT** for every
behaviour; spellings are ours except `COMPTYPES`, which is Pascal-P's.

| 1.1 | 1.3 | name | what forces it |
|---|---|---|---|
| `.3` | `.5` | `NEXTBLOCK` | reads two blocks into `SOURCEBUF` from the include file, the source or the workfile; raises **401** "Unexpected end of input" |
| `.10` | `.12` | `BUMPSEG` | `if n^ < limit then n^ := n^ + 1 else ERROR(e)`; both call sites pass **354** "Too many segments for segment dictionary" |
| `.11` | `.13` | `NEWSEGMENT` | bumps `NEXTSEG` and `SEGSLOT`, then records `SEGSLOT` in a packed 4-bit table |
| `.19` | `.21` | `COMPTYPES` | 35 call sites; recursive on `form`, with a pair list to terminate on mutually recursive pointers |
| `.21` | `.23` | `EMITWORD` | emits one word, byte-swapped under `{$F+}` (finding 24a) |
| `.24` | `.26` | `BLOCK` | dispatches `unitsy` to `UNITPART`; raises **408** "(*$S+*) needed to compile units" |
| `.26` | `.28` | `COMMENT` | scans to the closing delimiter it is passed — `}` or `*` — and sends a leading `$` to `COMPOPTI.1` |

`COMPTYPES` is the highest-confidence name in the project after `EMIT`. It
is Pascal-P's `comptypes(fsp1, fsp2): boolean` instruction for
instruction, including the detail that matters most: a list of
already-compared type pairs, threaded through global 76, which is what
stops it looping on `type p = ^rec; rec = record next: p end`.

Globals named with them: `CODEBUF` (2) and `CODEINX` (9), the code buffer
and the count of bytes in it that `EMIT` appends to and `FLUSHBUFFER`
writes out 512 bytes at a time — raising **402** "Error in write to code
file" — plus `LCBASE` (86 / 89), the bytes of the current procedure
already flushed, so that the location counter is `LCBASE + CODEINX`;
`SOURCEBLOCK` (90 / 93); and `SEGSLOT` (21 in both).

### 27a. 1.3 raises the segment limit from 31 to 63

**VERIFIED BINARY FACT**, and a clean 1.1 → 1.3 delta. Both places that
bound a segment number move together:

| | 1.1 | 1.3 |
|---|---|---|
| `NEWSEGMENT`'s call to `BUMPSEG` | `(@NEXTSEG, 31, 354)` | `(@NEXTSEG, 63, 354)` |
| `COMPOPTI.1`'s `$NS` arm | `if (n > NEXTSEG) and (n < 31)` | `if (n > NEXTSEG) and (n < 63)` |

The codefile-slot bound stays at 15 in both, which is the 16-segment
codefile limit finding 23e found in the 1.1 update notice.

This **corrects finding 23c**, which quoted the 1.3 manual's "7..57 for a
128K system and 7..31 for a 64K system" against the *1.1* binary's 31 and
called it "the 64K bound, on the nose". It is the 64K bound, but it is
1.1's; 1.3 uses the 128K bound, and the manual's 57 is simply more
conservative than the code's 63.

### 27b. Global 13 is not the lexical level — an open contradiction

> **SUPERSEDED by finding 28.** The premise below — that `PASCALCO.23`
> writes a procedure attribute table — is wrong. It writes the *segment*
> tail. Global 13 is the segment number and global 96 the procedure
> counter; neither is the lexical level, which is global 77. The
> contiguity and `JTAB` results in this section are still correct and
> still checked; only the identification of what `PASCALCO.23` emits, and
> everything drawn from it, is retracted. Kept for the record because the
> error is instructive: a layout fact was verified, the routine that
> supposedly produced it was not.

Finding 23c named global 13 `LEVEL`, "Zurich's `level`; 1 for the program
block, and the emitted LEX LEVEL byte is one less". That description is
accurate. It is **global 96** that answers to it.

Three things establish this, and `tools/probes/probe_attribtable.py`
checks all of them across both disks:

* **Procedures are laid out contiguously**, body then attribute table:
  sorted by `enter_ic`, every procedure's `jtab + 2` is the next one's
  `enter_ic`, 287 for 287 with **0 gaps**. So the last two bytes a
  procedure emits are `JTAB+0` and `JTAB+1`, in that order.
* `PASCALCO.23`'s last two instructions are `EMIT(G13)` then
  `EMIT(G96 - 1)`. With the layout above, `G13` supplies `JTAB+0` and
  `G96 - 1` supplies `JTAB+1`.
* **`JTAB+0` is the procedure number** — 1..N within each segment, never
  the segment number, which would make all ten of `COMPINIT`'s read 7.
  And **`JTAB+1` is the lexical level**, which the *shape* of its
  distribution settles rather than its range:

      JTAB+0   1:15  2:11  3:10  4:9  5:6 ... 37:1     a per-segment index
      JTAB+1   0:1   1:33  2:57  3:43  4:5  5:2  6:1   a nesting histogram

  Exactly **one** procedure in the whole compiler has `JTAB+1 = 0`, and it
  is the program block. A count of jump-table entries would put dozens
  there, since most procedures have no backward branch.

Global 96 behaves accordingly everywhere else too: 1 for the main program,
2 on entering a segment procedure, `+1` and `-1` around nesting, saved and
restored across it, and loaded from an identifier record's field 2 when a
procedure is re-entered. That is `level`.

What global 13 *is* remains unresolved, and one site fits neither reading:
`LEVEL := NEXTSEG`, at three places, assigns a segment number to it. It
also indexes a packed 4-bit table that `NEWSEGMENT` writes the codefile
slot into, which would make it a segment number — but then `EMIT(G13)`
could not be producing a procedure number. **The name is left in place
rather than changed**, with a caution in `names.py`, so the listings do
not churn twice; changing it is worth doing once the answer is actually
known. Note that finding 23c's `{$U-}` argument does not rest on this: it
rests on `PASCALCO.1`'s recorded `lex=0` and on segment numbering, neither
of which is affected.

## 28. `PASCALCO.23` writes the segment tail — and what that fixes

The last five PASCALCO procedures are named, which closes task #5's first
half at **29 of 29**. Doing it overturned finding 27b.

### 28a. What `PASCALCO.23` actually emits

VERIFIED BINARY FACT. The routine is:

```
  CODEINX := 0;
  for i := NEXTPROC - 1 downto 1 do
    if PROCDICT[i] = 0 then EMITWORD(0)
    else EMITWORD((LCBASE + CODEINX) - PROCDICT[i]);
  EMIT(SEGNUM);
  EMIT(NEXTPROC - 1);
  SEGTABLE[slot of SEGNUM] := LCBASE + CODEINX;
  FLUSHBUFFER(true);  LCBASE := 0;
```

That is the UCSD **procedure dictionary**, which `tools/a2pascal/codefile.py`
has been reading since the first week of the project and describes in its
own header: *"high byte = number of procedures. Preceding it, growing
downward, is the procedure dictionary: NPROC self-relative pointers."*
Finding 27b read the two `EMIT`s as a procedure's `JTAB+0`/`JTAB+1`
instead. They are the segment's last word.

`tools/probes/probe_segtail.py` settles it in the form that can fail:
**rebuild each segment's last `2*nproc + 2` bytes from the procedure list
alone** — pointers in descending procedure order, each holding
`its_own_address - jtab`, then the segment number, then the count — and
compare with the disk. All **30 segment tails across both releases match
byte for byte**. The segment number used in the reconstruction comes from
the dictionary at block 0, which `PASCALCO.23` never touches, so the low
byte agreeing is a fact about `G13` and not an artefact. Reversing the
pointer order, swapping the two trailing bytes, or negating the
self-relative sense each breaks it.

So `PASCALCO.23` is **`ENDSEGMENT`**, and:

* **global 13 is the segment number**, not the lexical level. This is what
  `SEGNUM := NEXTSEG` at three sites was doing all along — the site
  finding 27b flagged as fitting neither reading. It is also what indexes
  the packed 4-bit table `NEWSEGMENT` writes codefile slots into.
* **global 96 is the next free procedure number** in the current segment,
  so `NEXTPROC - 1` is the procedure count. `BODYPART.13` bumps it and
  raises `ERROR(251)` — "Too many nested procedures or functions" — at
  149.

### 28b. The lexical level is global 77

VERIFIED BINARY FACT, vendor-confirmed. The real attribute-table writer is
**`BODY3.1`**, and its tail emits the layout `codefile.py` documents, in
ascending-address order:

| emitted | lands on | value |
|---|---|---|
| `EMITWORD(CODEINX - JTABLE[i])`, `i` down from `JTABINX-1` | `JTAB-10` and below | the long-jump table |
| `EMITWORD((LCMAX - proc.parambase) * 2)` | `JTAB-8` | data size |
| `EMITWORD((proc.parambase - 1) * 2)` | `JTAB-6` | param size |
| `EMITWORD(CODEINX - enterpoint)` | `JTAB-4` | exit IC |
| `EMITWORD(CODEINX)` | `JTAB-2` | enter IC |
| `EMIT(PROCNUM)` | `JTAB+0` | procedure number |
| `EMIT(LEVEL - 1)` | `JTAB+1` | LEX LEVEL |

and then `PROCDICT[PROCNUM] := LCBASE - 2`, which is the entry
`ENDSEGMENT` later turns into a self-relative pointer. Global 77 is the
`LEVEL` here: 0 before the program heading, 1 for the program block,
incremented on entering a nested procedure and capped at 8, saved and
restored across nesting. Two independent confirmations:

* It is the **LEX operand** `BODYPART.6:EMITOP2` emits into every
  `LOD`/`LDA`/`STR` — `EMITOP2(54, LEVEL, offset)`. Nothing but a lexical
  level can go there.
* `LEVEL - 1` in the `JTAB+1` byte matches the manual's stated convention
  (IV, "LEX LEVEL"): *"the lexical level of a user program is 0, that of
  the first nested procedure is 1"*.

Finding 27b's contiguity and distribution results stand unaltered; they
were measurements of the codefile, and they were right. What was wrong was
attributing them to `PASCALCO.23`. The lesson is narrow and worth keeping:
**a probe that verifies a property of the output does not verify your
claim about which code produced it.** `probe_attribtable.py` could not
have caught this, because every assertion in it is still true.

### 28c. Five listing columns, named by the manual

VERIFIED SOURCE FACT (Apple's, Part II Ch. 5) against VERIFIED BINARY
FACT. The manual describes the compiled listing as carrying, next to each
source line, *"the line number, the segment number, the procedure number,
and the number of bytes or words (bytes for code, words for data) required
by that procedure's declarations or code to that point ... whether the
line lies within the actual code ... by printing a D for declaration, or
an integer from 0 through 9 to designate the lexical level (the level of
statement nesting within the code part)."*

`PASCALCO.4:ERRORWITHTEXT` writes exactly those columns, in exactly that
order, so five globals are named by the vendor's own description of its
output:

```
  if DP then L2 := 68 { 'D' } else L2 := (LISTLEVEL mod 10) + 48;
  FWRITEINT(LISTFILE, LINENUMBER, 6);
  FWRITEINT(LISTFILE, SEGNUM,     4);
  FWRITEINT(LISTFILE, PROCNUM,    5);
  FWRITECHAR(LISTFILE, L1, 0);   { ':' normally, '*' on an error line }
  FWRITECHAR(LISTFILE, L2, 0);
  FWRITEINT(LISTFILE, LISTCOUNT,  6);
```

with `LISTCOUNT := LC` when `DP` and `:= CODEINX` otherwise — the
manual's "words for data, bytes for code" on the nose. `DP` is
Pascal-P's `dp`, one more name that transfers rather than being invented.
`STATLEVEL` is the live counter `LISTLEVEL` is latched from.

Global 25 comes with them: `if LC > LCMAX then LCMAX := LC` at four
sites, reset from `LC` at the head of every body, and emitted as the
attribute table's data size. That is Zurich's `lcmax` — another name that
transfers rather than being invented.

### 28d. `PASCALCO.13` builds the SEGINFO word

STRONG INFERENCE. `PASCALCO.13` writes four packed fields into a word and
returns it:

| field | width | at bit | value |
|---|---|---|---|
| segment number | 8 | 0 | `SEGTABLE[slot].segnum` |
| machine type | 4 | 8 | 2, or **1 under `{$F+}`** |
| — | 1 | 12 | 0 |
| version | 3 | 13 | 2 |

That is the segment-dictionary `SEGINFO` layout `codefile.py` parses at
block 0, derived there from the codefile format and not from this routine
— so the two agreeing is a genuine cross-check, and it also fixes the
operand order of `STP`'s packed-field pointer as (address, width, right
bit). Machine type 2 is p-code LSB and 1 is p-code MSB, which is the
codefile-level consequence of `{$F+}` (finding 24a) that was previously
only inferred from the byte-swapping in `EMITWORD`. Named
**`SEGINFO`**; the spelling is ours.

### 28e. Two error numbers, and a 1.1 → 1.3 split

VERIFIED BINARY FACT. The 1980 language reference lists `253 Procedure too
long` and `254 Too many long constants in this procedure`; the 1.3 manual
lists 253 as *"Procedure too long [when it overflows the internal code
buffer used by the Compiler]"* and 254 as *"Procedure too complex [when it
generates too many long jumps]"*. The binaries show Apple changing this
between releases:

| site | 1.1 | 1.3 |
|---|---|---|
| code buffer nearly full: `if CODEINX + 100 > N` | `ERROR(253)`, N = 1299 | `ERROR(253)`, N = **1999** |
| long-jump table full at 24 entries | `ERROR(253)` | `ERROR(254)` |

So 1.1 reported both conditions as 253, 1.3 separated them — which is
precisely why the 1.3 manual carries a distinct 254 with a distinct gloss,
and why the 1980 manual's 254 means something else entirely. The
1.1 → 1.3 code-buffer headroom also grew from 1300 to 2000 bytes.

### 28f. What is left

`COMPILE`, `HOLDMOST` and `HOLDROUT` (`PASCALCO.25`,
`.28`, `.29`) are the compilation driver and two nested wrappers whose
only job is to hold phase segments in memory across it:

```
  PASCALCO.1:  if SWAPPING then COMPILE else HOLDMOST
  HOLDMOST:    load 8,9,19,11,12,13,14,15
               if SWAPMORE then COMPILE else HOLDROUT
               unload them in reverse
  HOLDROUT:    load 10; COMPILE; unload 10
```

The load order — `DECLARAT, BODYPART, NUMSTRIN, STATEMEN, CASESTAT,
FORSTATE, BODY1, BODY3`, with `ROUTINE` held back — is a fact about the
source text and goes straight into the reconstruction. `{$S+}` swaps
everything, `{$S++}` swaps `ROUTINE` as well.

## 29. Eight significant characters, and four names that were impossible

A constraint that had been overlooked, and it bites the *reconstruction*
rather than the analysis: Apple Pascal keeps only the first eight
significant characters of an identifier. Two names agreeing in eight
characters are one identifier, so a naming registry that ignores this
produces source the compiler cannot compile — or, worse, compiles wrongly.

### 29a. The rule, from the manual and from the 6502

VERIFIED SOURCE FACT. The 1.3 manual's *Identifiers* section:

> An identifier must begin with a letter. After the initial letter, it may
> contain any number of letters, digits, or underscore characters ...
> **Only the first 8 characters (ignoring underscores) are significant.**
> Capital and lowercase letters are equivalent.
>
> Thus the following six identifiers are equivalent and interchangeable:
> `MYNUMBER  mynumber  MY_NUMBER  My_Number  MY_NUMBER_VALUE ...`

and it states the two consequences separately:

> If a new identifier is the same as an Apple Pascal **reserved word**, the
> Compiler will refuse to accept it.
>
> If a new identifier is the same as a **predeclared** identifier, the
> Compiler will accept it but the original Pascal identifier will become
> unavailable within the scope of the new meaning.

VERIFIED BINARY FACT. 1.3's native `IDSEARCH` implements all of it in
sixteen instructions. It blank-fills an eight-byte buffer at `$88`
(`LDA #$20 / LDX #$07 / STA $88,X`), then:

```
  1244 CMP #$5F     ; '_'
  1246 BNE $1255    ;   anything else non-alphanumeric ends the identifier
  1248 BEQ $1229    ;   underscore -> next character, X *not* incremented
  124A SBC #$20     ; lowercase -> uppercase
  124C INX
  124D CPX #$08
  124F BCS $1229    ; already stored 8 -> consume the character, discard it
  1251 STA $88,X
```

Underscores are skipped rather than counted, case is folded, and the ninth
and later characters are read and thrown away. That eight-byte buffer is
then what the reserved-word lookup compares against (`LDA $88 / ASL / TAY`
into a per-initial-letter bucket table, then `CMP $88,X`), so **an
identifier whose first eight significant characters spell a reserved word
*is* that reserved word.** Finding 22's symbol-table entry agrees from the
other side: the name occupies words 0–3, and there is nowhere to put a
ninth character.

### 29b. Four symbol names the original source cannot have used

Finding 26a recovered the `SYMBOL` enumeration and spelled it with
Pascal-P's convention, one `<word>sy` per reserved word. For four of
Apple's reserved words that convention is unusable:

| Pascal-P spelling | folds to | which is |
|---|---|---|
| `interfacesy` | `INTERFAC` | the reserved word INTERFACE |
| `implementationsy` | `IMPLEMEN` | the reserved word IMPLEMENTATION |
| `externalsy` | `EXTERNAL` | the reserved word EXTERNAL |
| `otherwisesy` | `OTHERWIS` | the reserved word OTHERWISE |

Writing `externalsy` in Apple Pascal source does not declare an
identifier; it scans as `EXTERNAL`. So **the original source used
something else for these four**, and that much is forced. What it used is
not recoverable — enumeration constant names leave no trace in the
codefile — so the four spellings now in `names.py` are SPECULATION:
`intersy`, `implsy`, `externsy`, `otherwsy`. Abbreviating is in keeping
with the convention rather than a departure from it: Pascal-P already
writes `progsy`, `procsy` and `funcsy` rather than spelling out PROGRAM,
PROCEDURE and FUNCTION.

The other eleven long names from Pascal-P survive intact, which is worth
noting because it need not have been so: `constbegsys`, `simptypebegsys`,
`typebegsys`, `typedels`, `blockbegsys`, `selectsys`, `facbegsys` and
`statbegsys` fold to `CONSTBEG`, `SIMPTYPE`, `TYPEBEGS`, `TYPEDELS`,
`BLOCKBEG`, `SELECTSY`, `FACBEGSY` and `STATBEGS` — eight distinct
identifiers. Apple could keep Zurich's names for the symbol sets, and had
to invent for the symbols.

### 29c. `STRING` was the wrong name for `PASCALCO.15`

Finding 22 named `PASCALCO.15` after Pascal-P's `string(fsp): boolean`.
Apple cannot have: `STRING` is predeclared, and by the manual's second
rule declaring a function of that name takes the *type* away for the rest
of the program. The compiler needs the type — `LIBNAME` is a 21-word
aggregate passed straight to `FOPEN`, and `CODECOMMENT` is `NEW`'d at 41
words and then filled to 80 characters, i.e. `string[40]` and
`^string[80]`. Renamed **`ISSTRING`**.

The probe caught two more of the same kind the moment it was written.
1.3 adds `BYTESTREAM` and `WORDSTREAM` as predeclared types (Table F-2B),
and the globals holding their type descriptors had been named
`BYTESTREAMPTR` and `WORDSTREAMPTR` — which fold to `BYTESTRE` and
`WORDSTRE`, i.e. to the type names themselves. Renamed `BYTEPTR` and
`WORDPTR`, matching `INTPTR` and `REALPTR`.

Nothing else in the registry shadows a predeclared identifier. Note that
`IDSEARCH` and `TREESEARCH` do *not* appear in Table F-2B — they are CSPs
the compiler emits, not names a program can see — so 1.3 declaring its two
native routines under those names shadows nothing.

### 29d. The rule is now enforced, not observed

`tools/probes/probe_identifiers.py` folds every name in the registry —
globals, procedures, and both enumerations, which in a single Pascal
program share the outermost scope — and fails if any two are the same
identifier, if any lands on one of the 42 reserved words read out of the
native table, or if any lands on one of the 66 predeclared identifiers
transcribed from Table F-2B. It also lists every name over eight
characters, separating the 21 whose spelling is forced by evidence from
the 24 that are ours; those are unambiguous but the listing keeps them
visible. 176 identifiers in 1.1, 180 in 1.3, all distinct.

Four of our own invented names were renamed because their truncation was
misleading rather than merely ugly: `COMPILERESIDENT` folded to
`COMPILER`, which reads as something else entirely, and
`COMPILEHOLDINGROUTINE` to `COMPILEH`, which reads as nothing. They are
now `HOLDMOST` and `HOLDROUT`, with `SEGINFO` and `NEWPROC` for
`MAKESEGINFO` and `ALLOCPROCNUM`. **Working rule from here: a name we
invent is eight significant characters or fewer, so that what we write is
what the compiler sees.**

## 30. The segment procedures name themselves, and give the source's shape

Fifteen names that did not have to be inferred at all: they have been
sitting in the segment dictionary since the first week of the project,
and finding 29's work on the 8-character rule is what showed they were
identifiers rather than labels.

### 30a. SEGNAME is an identifier out of Apple's source

VERIFIED SOURCE FACT. The 1.3 manual, on the codefile's segment
dictionary:

> Each element of the SEGNAME array is an eight-character array that
> contains the first eight characters of the user program, unit, SEGMENT
> procedure, SEGMENT function, or assembly-language procedure name that
> was translated into the corresponding segment. If the name is shorter
> than eight characters, it is padded on the right by spaces; if the name
> is longer than eight characters, it is truncated to the first eight
> characters.

Combine that with finding 29 — the compiler distinguishes nothing past
the eighth character — and an eight-character SEGNAME *is* the identifier,
not an abbreviation of it. Where the name is shorter, the padding proves
there was nothing more, so `BODY1`, `BODY3` and `ROUTINE` are exact and
complete.

`tools/probes/probe_segprocs.py` checks that procedure 1 of every segment
is the segment procedure — no procedure in a segment sits at a shallower
lexical level than procedure 1, `PASCALCO.1` alone is at lex 0 — and that
`names.py` assigns exactly the dictionary's spelling, so the registry
cannot drift from the disk.

### 30b. A name of mine was already taken

Finding 28b named `BODY3.1` **`ENDPROC`** for what it does: it emits the
whole attribute table. But `BODY3.1` is the segment procedure of segment
`BODY3`, so the codefile has been telling us its name all along. It is
`BODY3`, and the description belongs in a comment. Retracted and
corrected; the behaviour in 28b is unaffected.

That is the second time in three findings that a conclusion about naming
was reached without checking what the codefile already said. The rule to
take from it: **before inventing a name, ask whether the artifact carries
one.** Segment procedures do. So does the program.

### 30c. The compiler's declaration skeleton

VERIFIED BINARY FACT for the depths; the parents are STRONG INFERENCE from
the call graph. Each segment procedure's lexical level is the depth at
which Apple declared it, and both releases give the identical shape:

```
  PASCALCO                                    lex 0   the program
    COMPINIT  DECLARAT  BODYPART  WRITELIN    lex 1   declared in the program
    UNITPART  COMPOPTI  NUMSTRIN  FINISHUP
      ROUTINE   STATEMEN                      lex 2
        BODY1  BODY3  CASESTAT  FORSTATE      lex 3
```

with every level from 0 to 3 occupied and no gap — a gap would mean a
segment procedure declared inside nothing. All 29 of PASCALCO's other
procedures are at lex 1, which is what makes them the service layer: they
are declared in the program block, so every phase can see them.

The parents follow from the call graph. `ROUTINE` and `STATEMEN` are
reached only from `BODYPART.23` and `BODYPART.25`, both inside
`BODYPART.1`, so both are declared there. `CASESTAT` and `FORSTATE` are
called only by `STATEMEN.1` — the `case` and `for` arms of the statement
parser lifted out into their own segments. `BODY1` and `BODY3` are called
only by `BODYPART.24`, a 16-byte procedure with 38 words of locals that
does nothing but call them; the shared frame is why `BODY3` reaches its
caller's variables as intermediate-level references.

This is the outline the reconstruction has to reproduce, and it is
stronger evidence than it looks: the lexical level is emitted into every
`LOD`/`LDA`/`STR` and into every attribute table, so getting the nesting
wrong changes the code bytes and the recompile fails.

Note also what the depths rule *out*. `ROUTINE` at lex 2 cannot be a
procedure of the program block, so the reconstruction cannot declare it
beside `DECLARAT`; and `BODY1`/`BODY3` at lex 3 cannot sit beside
`BODYPART.25` unless `BODYPART.25` is itself at lex 3, which it is.

## 31. The statement grammar, the expression chain, and `GATTR`

Seventeen names in the phase segments, and the first real block of task
#6's typed declaration order.

### 31a. Each statement parser identifies itself twice

VERIFIED BINARY FACT for the identifications; the spellings are STRONG
INFERENCE. `STATEMEN` has eight procedures: procedure 1 is the segment
procedure (finding 30) and the other seven are the arms of Pascal's
statement grammar — minus `case` and `for`, which Apple moved into
segments of their own, leaving exactly seven. Each one is pinned
*twice, independently*: by the reserved word it demands, through a
recovered `SY` code, and by the error number it raises when that word is
missing, which Apple's own error list glosses in English.

| procedure | demands | raises | Apple's gloss |
|---|---|---|---|
| `STATEMEN.2` `ASSIGNMENT` | `becomes` | 51 | "':=' expected" |
| `STATEMEN.3` `GOTOSTATEMENT` | `intconst` | 15, 167 | "Integer expected", "Undeclared label" |
| `STATEMEN.4` `COMPOUNDSTATEMENT` | `endsy` | 13 | "'END' expected" |
| `STATEMEN.5` `IFSTATEMENT` | `thensy` | 52 | "'THEN' expected" |
| `STATEMEN.6` `REPEATSTATEMENT` | `untilsy` | 53 | "'UNTIL' expected" |
| `STATEMEN.7` `WHILESTATEMENT` | `dosy` | 54 | "'DO' expected" |
| `STATEMEN.8` `WITHSTATEMENT` | `dosy` | 54, 140, **250** | …, "Type of variable must be record", "Too many scopes of nested identifiers" |
| `CASESTAT.1` | `ofsy` | 8, 13, 156 | "'OF' expected", …, "Multidefined case label" |
| `FORSTATE.1` | `becomes`, `dosy` | 51, **55**, 54, 143 | …, "'TO' or 'DOWNTO' expected in for statement", … |

Nothing forces a `while` parser to raise 54 rather than 52 except its
being a `while` parser. Two of the seven have no keyword of their own and
fall to the second column alone: `ASSIGNMENT` demands `becomes` and raises
51, and `WITHSTATEMENT` raises **250**, "Too many scopes of nested
identifiers" — which only a construct that *opens a scope* can, and none
of its siblings do. `tools/probes/probe_statements.py` checks all nine
across both releases; mutating either the demanded symbol or the expected
error fails it.

The spellings are Pascal-P's, and what licenses them is not resemblance
but the segment dictionary. `CASESTAT` and `FORSTATE` are the first eight
characters of two SEGMENT procedures (finding 30), and Pascal-P's names
for those statements are `casestatement` and `forstatement`, which
truncate to exactly those eight characters. Apple kept Zurich's names for
this family, so their siblings are Zurich's too.

### 31b. The expression chain, confirmed by lexical level

VERIFIED BINARY FACT. `BODYPART.11` calls `.33` calls `.34` calls `.35`,
and the four sit at lexical levels 2, 3, 4 and 5 — each declared inside
the one before. That is Pascal-P's

```
  expression → simpleexpression → term → factor
```

nesting and all, with `factor` recursing into `expression` for a
parenthesised subexpression and into itself. `expression` parses through
`simpleexpression` and then handles a relational operator if `SY = relop`,
which is the same routine's shape in Pascal-P. The lexical levels are
independent of the names: they are bytes in the attribute tables.

Three more came with them. `BODYPART.18:GENLABEL` is `NEW(l, 3)` — a
three-word label record, marked undefined, with 28000 as the
end-of-chain sentinel. `BODYPART.19:PUTLABEL` defines the label at
`CODEINX` and walks its chain of forward references, patching each.
`BODYPART.17:GENFJP` calls `LOAD`, raises 135 "Type of operand must be
boolean" unless the type is `BOOLPTR`, and emits `FJP` to a label; the
spelling is ours, since Pascal-P splits that into two.

### 31c. Globals 3–7 are `gattr`

STRONG INFERENCE, from two directions that were derived separately.

The global map has said since finding 10 that word 3 is a five-word record
— *"MOV 5 word(s) x7 … spans 5 words but words 4..7 are also addressed
individually, so these are its fields"* — at **202 accesses in 1.1 and 216
in 1.3, the most-used global in the compiler.** That is what a Pascal-P
compiler's `gattr` looks like, and nothing else does.

`BODYPART.8:LOAD` then says what the fields are. It switches on word 4 and,
in the variable arm, emits `LOD <word 6>, <word 7>` — and `EMITOP2`'s
operands are `(op, lex, offset)` (finding 24c), so word 6 can only be a
lexical level and word 7 an offset. The constant arm reads word 5:
`EMITCONST(word 5)` for an ordinal, `LDCN` when the type is `NILPTR`, a
two-word `LDC` for a real and a five-word one for a set. So:

```
  attr = record
           typtr:  stp;              { global 3  GATTYPTR }
           case kind: attrkind of    { global 4  GATKIND, 0 = cst }
             cst:   (cval: valu);    { global 5  GATCVAL }
             varbl: (vlevel: levrange;   { global 6  GATLEVEL }
                     dplmt: addrrange)   { global 7  GATDPLMT }
         end
```

field for field and in order. The `GAT` prefix is ours — the reconstruction
will write `GATTR.TYPTR` once the lifter can render record fields — but
the field names and their order are Pascal-P's, and the order is forced by
the offsets rather than chosen.

This is the second record recovered field by field, after finding 22's
`structure` and `identifier`, and it is the one the code generator runs
on: every `LOAD`, every comparison, every assignment reads it.

## 32. The UCSD II.0 compiler source

Dave supplied the source of the UCSD Pascal II.0 compiler — *"BASED ON
ZURICH P2 PORTABLE COMPILER, EXTENSIVLY MODIFIED BY ROGER T. SUMNER,
SHAWN FANNING AND ALBERT A. HOFFMAN, 1976..1979"* — now in
`evidence/reference/ucsd-ii0-compiler/`, 15 files. Apple Pascal's
`SYSTEM.COMPILER` is a descendant of it.

**It is not an answer key.** Apple changed things, and where the two
disagree the binary wins. Its value is twofold: it settles spellings the
binary can never carry, and it is an independent document against which
everything derived from the bytes alone can be checked.

### 32a. What the check found

`tools/probes/probe_ucsd_source.py`. Every numeric bound this project hit
as a bare constant in a comparison is named in `compglbls.text`, and
**all eight match**:

| recovered from | value | source name |
|---|---|---|
| `if IC + 100 > 1299 then ERROR(253)` (finding 28e) | 1299 | `MAXCODE` |
| the long-jump table filling (finding 28b) | 24 | `MAXJTAB` |
| `BUMPSEG(SEGSLOT, 15, 354)` (finding 27) | 15 | `MAXSEG` |
| `ERROR(251)` above 149 procedures (finding 28a) | 149 | `MAXPROCNUM` |
| `if LEVEL < 8 then LEVEL := LEVEL + 1` (finding 28b) | 8 | `MAXLEVEL` |
| `GENLABEL`'s end-of-chain sentinel (finding 31b) | 28000 | `MAXADDR` |
| `STRING[n]` range-checked against 1..255 (finding 22) | 255 | `STRGLGTH` |
| the `$C` comment read to 80 characters | 80 | `DEFSTRGLGTH` |

Nothing about the constant 1299 announces itself as a code-buffer size.

The two scanner enumerations of finding 26, recovered from the
reserved-word table and the scanner's case arms: **`OPERATOR` matches
16 of 16, `SYMBOL` matches 54 of 55**, member for member by position. The
one difference is Apple's: slot 54 is `SEPARATSY` in II.0 and OTHERWISE in
Apple, and 1.3's reserved-word table has no SEPARATE. The probe declares
that one change explicitly and fails on any other.

Finding 22's `identifier` record is confirmed field for field —
`NAME: ALPHA; LLINK, RLINK: CTP; IDTYPE: STP; NEXT: CTP; CASE KLASS` — as
is finding 31c's reading of `GATTR`. Finding 28a's `FINISHSEG` turns out
to be reproducible line by line:

```
  PROCEDURE FINISHSEG;                     our lift of PASCALCO.23
  BEGIN IC := 0;                             IC := 0;
    FOR I := NEXTPROC-1 DOWNTO 1 DO          for i := NEXTPROC-1 downto 1
      IF PROCTABLE[I] = 0 THEN GENWORD(0)      if PROCTABLE[i] = 0 ...
      ELSE GENWORD(SEGINX+IC-PROCTABLE[I]);    else GENWORD(SEGINX+IC-...)
    GENBYTE(SEG); GENBYTE(NEXTPROC-1);       GENBYTE(SEG); GENBYTE(...)
    SEGTABLE[SEG].CODELENG := SEGINX+IC;     SEGTABLE[...] := SEGINX+IC
    WRITECODE(TRUE); SEGINX := 0;            WRITECODE(1); SEGINX := 0
```

and `PRINTLINE` matches finding 28c's column reading field width for field
width:

```
  WRITE(LP,SCREENDOTS:6,SEG:4,CURPROC:5,STARORC,DORLEV,LINEINFO:6,' ');
```

### 32b. Names corrected

Some inferences were exactly right — `GENLABEL`, `PUTLABEL`, `GENFJP`,
`LOAD`, `EXPRESSION`, `SIMPLEEXPRESSION`, `TERM`, `BODY`, `ROUTINE`,
`ERROR`, `ENTERID`, `INSYMBOL`, `SEARCHSECTION`, `SEARCHID`, `GETBOUNDS`,
`SKIP`, `CONSTANT`, `COMPTYPES`, `BLOCK`, `LCMAX`, `LEVEL`, `DP`,
`GOTOOK`, `RANGECHECK`, `IOCHECK`, `SYSCOMP`, `ININTERFACE`, `NEXTSEG`,
`NEXTPROC`, `LINESTART`, all eight symbol-set globals, and all nine
statement parsers including `CASESTATEMENT` and `FORSTATEMENT`, which
finding 31a had predicted from the segment names.

Fifty-six were not. The substantive ones:

| ours | UCSD's | note |
|---|---|---|
| `EMIT` / `EMITWORD` | `GENBYTE` / `GENWORD` | |
| `EMITOP` `EMITCONST` `EMITOP1` `EMITOP2` `EMITBIG` `EMITJUMP` | `GEN0` `GENLDC` `GEN1` `GEN2` `GENBIG` `GENJMP` | finding 24c's whole emitter family |
| `FLUSHBUFFER` | `WRITECODE` | and its argument is `FORCEBUF` |
| `ENDSEGMENT` | `FINISHSEG` | |
| `ERRORWITHTEXT` | `PRINTLINE` | |
| `NEXTBLOCK` | `GETNEXTPAGE` | |
| `COMMENT` | `COMMENTER` | its argument is `STOPPER: CHAR` |
| `ENTERUNDECL` | `FINDFORW` | it reports undefined **forward** declarations |
| `ISSTRING` | `PAOFCHAR` | |
| `STRINGTYPE` / `LONGSIZE` | `STRGTYPE` / `DECSIZE` | |
| `CODEBUF` / `SOURCEBUF` | `CODEP` / `SYMBUFP` | |
| `CODEINX` / `SEGNUM` / `PROCNUM` | `IC` / `SEG` / `CURPROC` | |
| `LCBASE` | `SEGINX` | |
| `PROCDICT` / `JTABLE` / `JTABINX` | `PROCTABLE` / `JTAB` / `NEXTJTAB` | |
| `LINENUMBER` / `LISTCOUNT` | `SCREENDOTS` / `LINEINFO` | the listing columns |
| `STATLEVEL` / `LISTLEVEL` | `STMTLEV` / `BEGSTMTLEV` | |
| `OPT_F` `OPT_T` `OPT_D` `LISTING` `SHOWPROGRESS` | `FLIPBYTES` `TINY` `DEBUGGING` `LIST` `NOISY` | finding 24a's option flags |
| `INUNIT` | `INMODULE` | II.0 calls units *modules* |
| `LISTFILE` `LIBFILE` `INFOFILE` | `LP` `LIBRARY` `REFFILE` | |
| `ENTERSTDIDENTS` | `ENTSPCPROCS` | 43 names in the same order; Apple adds `UNITSTAT` as the 44th, which is exactly the difference finding 24a recorded |

`probe_identifiers.py` no longer hard-codes which long spellings are
allowed. It reads the II.0 source and requires that any name over eight
characters actually appear there, so a name claimed to be UCSD's has to be
UCSD's. **All 53 now are; none are ours.**

### 32c. A correction to finding 29c

Finding 29c argued that `PASCALCO.15` could not be called `STRING`
because the type is predeclared and the compiler needs it. The rename was
right — UCSD calls it `PAOFCHAR` — but the argument was too strong. II.0
*does* declare `PROCEDURE STRING`, and legally: it comes after every
`STRING`-typed declaration in a one-pass language, so nothing later needs
the type. It is a different routine from `PAOFCHAR` — the scanner's
string-literal reader, which Apple moved into the `NUMSTRIN` segment
along with `NUMBER`.

### 32d. What Apple changed

Worth recording, because these are the places the reconstruction cannot
copy II.0:

* **Segmentation.** II.0 declares six segment procedures —
  `PASCALCOMPILER`, `COMPINIT`, `DECLARATIONPART`, `BODYPART`,
  `WRITELINKERINFO`, `UNITPART`. Apple has fifteen, promoting `ROUTINE`,
  `STATEMENT`, `CASESTATEMENT`, `FORSTATEMENT`, `BODY`, the compiler
  options, `NUMBER`/`STRING` and the finish-up code into segments of
  their own to fit the Apple II. `WRITELIN` is `WRITELINKERINFO` — a name
  no amount of staring at the binary would have produced.
* **Segment numbering.** II.0's `SEGRANGE` is `0..MAXSEG` and `SEG`
  indexes `SEGTABLE` directly. Apple lets segment numbers run past 15
  (finding 27a) and adds a packed 4-bit `SEG` → slot map, global 479.
* **The option letters.** `$E` has no II.0 counterpart: II.0 raises error
  191 unconditionally for a file variable in a module's private part,
  where Apple gates it on a flag (finding 24a).
* **`OTHERWISE` for `SEPARATE`**, as above.

### 32e. The files, and their hashes

SHA-256, first 16 hex digits. `.gitattributes` now marks
everything under `evidence/` as never-normalised, so these
round-trip byte for byte on any platform.

| file | bytes | sha256 |
|---|---|---|
| `block.text` | 4,621 | `fa6d3089af9ec72b…` |
| `bodypart.a.text` | 13,049 | `0e2c168ced3a4de5…` |
| `bodypart.b.text` | 10,037 | `5ef338ac63916f77…` |
| `bodypart.c.text` | 12,672 | `5793eaa81d5c16e6…` |
| `bodypart.d.text` | 12,706 | `a4f31f712aeaeb4e…` |
| `bodypart.e.text` | 16,543 | `0ec84f2f0318735f…` |
| `compglbls.text` | 12,033 | `356ccc776eeaec39…` |
| `compiler.text` | 414 | `a61a6ce00d7cb0e9…` |
| `compinit.text` | 12,172 | `8922e2b104fb41b5…` |
| `decpart.a.text` | 14,844 | `85e1370cb510acfd…` |
| `decpart.b.text` | 8,675 | `5de9f58cf0a927f0…` |
| `decpart.c.text` | 10,627 | `270922e55d203ebb…` |
| `procs.a.text` | 14,295 | `55445808d41f5919…` |
| `procs.b.text` | 8,060 | `66a9e676f23671a7…` |
| `unitpart.text` | 10,585 | `380bc74229b0b941…` |

## 33. A `VAR` declaration allocates backwards

The rule the reconstruction's `VAR` block has to obey, and the one thing
that would have made it impossible to get right by guessing.

### 33a. The rule

VERIFIED SOURCE FACT. `VARDECLARATION`, in `decpart.b.text`, collects the
identifiers of one declaration by **prepending** them to a list:

```
  NXT := NIL;
  REPEAT ...
    NEW(LCP);
    WITH LCP^ DO BEGIN NAME := ID; NEXT := NXT; ... END;
    ENTERID(LCP); NXT := LCP;
  UNTIL TEST;
```

and then walks that list assigning addresses:

```
  WHILE NXT <> NIL DO
    WITH NXT^ DO BEGIN IDTYPE := LSP; VADDR := LC;
                       LC := LC + LSIZE; NXT := NEXT END;
```

The last identifier written is the head of the list, so it gets the
*lowest* address. **`VAR LC,IC: ADDRRANGE` allocates IC first.**

This matters because every `LDO` and `SRO` in the binary carries a global
offset. A reconstruction that writes `VAR CURPROC, NEXTPROC` where Apple
wrote it the other way round produces different code bytes and fails the
recompile — and the failure would be silent in the source, since the
declaration reads identically either way.

### 33b. The binary agrees, 86 times

VERIFIED BINARY FACT. This is a prediction about Apple's globals, not just
a fact about UCSD's source, and `tools/probes/probe_vardecl.py` tests it:
for every II.0 declaration where two or more identifiers are names this
project recovered independently, their Apple offsets must come out in
reverse declaration order. **18 declaration groups, 86 names, all
reversed, across both releases.**

None of those names came from declaration order. They came from
behaviour, from error numbers, and from the listing columns. Four that
had puzzled me are now explained rather than merely observed:

| declared | allocated | how the name was recovered |
|---|---|---|
| `LC,IC` | IC 9, LC 10 | IC from `CODEP^[IC] := byte`; LC from the listing's word count |
| `BEGSTMTLEV,STMTLEV` | STMTLEV 78, BEGSTMTLEV 79 | `BEGSTMTLEV := STMTLEV` in `PRINTLINE` |
| `CURPROC,NEXTPROC` | NEXTPROC 96, CURPROC 97 | `CURPROC` is the listing's third column; `NEXTPROC` is bounded by ERROR(251) |
| the eight `SETOFSYS` | TYPEDELS 98 … CONSTBEGSYS 126 | finding 26c, each by the error its guard raises |

The eight symbol sets are the sharpest of these. One declaration, eight
identifiers, and finding 26c assigned every one of them from the error
list — `constbegsys` guards "Error in constant", `facbegsys` guards "Error
in factor", and so on. They come out in **exactly** reverse declaration
order, all eight. Two entirely independent methods, the same answer.

It also explains the one thing that had looked like Apple reordering the
head of the block: II.0 declares `CODEP` and `SYMBUFP` on separate lines,
in that order, but Apple has `SYMBUFP` at 1 and `CODEP` at 2. Under the
rule that is not a reordering — it is Apple merging the two into one
declaration, `VAR CODEP, SYMBUFP: ...`, which allocates `SYMBUFP` first.

### 33c. The whole `VAR` block, aligned

`tools/vardecl.py` (now a `build_all.py` step) lays out II.0's `VAR` block
under the rule and aligns it by name against Apple's recovered globals,
writing `analysis/global_map/vardecl-ii0.txt`. 118 II.0 variables, **83 of
them matched to a name we recovered in Apple**, and — the useful part —
the offsets differ only by a *drift* that never decreases through the
scalar region:

```
  offsets 1..16    drift  0   TOP, IC, LC, INTPTR, SEG, SYMCURSOR, SY, OP
  LGTH..DP         drift +1   Apple has one extra word after ID
  TINY..REALPTR    drift +3   two more option flags ($V, $E)
  OUTPUTPTR        drift +4
  LEVEL..STMTLEV   drift +5
  NEXTSEG..DISPLAY drift +6   including all eight symbol sets
```

A run of constant drift means Apple kept II.0's order for that whole
stretch; each step up is a variable Apple inserted. The first sixteen
words of Apple's global area are II.0's, in order.

The aggregate sizes fall out of Apple's own spacing and corroborate II.0's
types independently: `PROCTABLE` is 335 − 185 = **150** words
(`ARRAY [0..MAXPROCNUM] OF INTEGER`), `SYSTEMLIB` is 509 − 488 = **21**
(`STRING[40]`, 41 bytes), `JTAB` is 535 − 510 = **25**
(`ARRAY [0..MAXJTAB]`), and the file variables are 40 words apart —
II.0's `NILFILESIZE = 40`.

The drift steps *down* after `DISPLAY`, which means Apple removed
something around `PFNUMOF`. **Finding 38 settles it, and the count it
first reported here was wrong**: `vardecl.py` was parsing the fields of
the two inline `RECORD … END` types as if they were variables of their
own, which shifted every II.0 offset past `DISPLAY` and made the step read
as −2. With that fixed the step is −4, and finding 38 accounts for it
exactly — `PFNUMOF` (6 words) deleted, a two-word set put in its place.
Nothing else in the block is unaccounted for.

## 34. The declaration part, all twenty procedures

*Confidence: VERIFIED BINARY FACT for the shapes; STRONG INFERENCE for the
seventeen II.0 spellings; SPECULATION for the four that are ours.
`tools/probes/probe_declarat.py`.*

### 34a. Seventeen of the twenty are II.0's, and the fit is joint

`decpart.a/b/c.text` declares `DECLARATIONPART` and seventeen procedures
nested inside it. Apple's `DECLARAT` has twenty, at **identical numbers in
both releases**. Matching the seventeen is not a matter of picking
plausible labels: the codefile fixes each procedure's parameter size, its
lexical level and its call set, and II.0's source fixes all three
independently. They agree everywhere, at once:

```
  #   name                param  lex   what pins it
  1   DECLARATIONPART       8     1    setofsys; calls the six parsers
  2   CHECKSYM              8     2    OURS -- see 34b
  3   TYP                  12     2    setofsys + 2 var params; recursive
  4   SIMPLETYPE           12     3    same signature; called by TYP alone
  5   PACKABLE              6     3    recursive AND calls GETBOUNDS
  6   FIELDLIST            10     3    setofsys + var stp
  7   ALLOCATE              2     4    the only other caller of PACKABLE
  8   VARIANTLIST           0     4    calls FIELDLIST back
  9   POINTERTYPE           0     3    SEARCHID + ERROR, never TYP
 10   USESDECLARATION       0     2    514 bytes of locals -- see 34c
 11   ONEUNIT               2     3    OURS -- see 34b
 12   GETTEXT               2     4    the only file I/O in the segment
 13   FINDSEG               4     5    OURS
 14   SEGSRCH             12/16   6    OURS
 15   LABELDECLARATION      0     2    no TYP, no ENTERID
 16   CONSTDECLARATION      0     2    the only caller of CONSTANT
 17   TYPEDECLARATION       0     2    TYP + ENTERID, never stores LC
 18   VARDECLARATION        0     2    TYP + ENTERID, and stores LC
 19   PROCDECLARATION       4     2    symbol + boolean; NEWSEG, BUMPSEG
 20   PARAMETERLIST        12     3    called by PROCDECLARATION alone
```

The pairs that a weaker method would confuse are separated by evidence
that cannot be traded: `ALLOCATE` calls `PACKABLE` and `PACKABLE` does not
call `ALLOCATE`; `CONSTDECLARATION` calls `CONSTANT` and `TYPEDECLARATION`
does not; and `TYPEDECLARATION` and `VARDECLARATION`, which have the *same*
call set, are told apart by finding 33's own mechanism — `VARDECLARATION`
is the one that stores into `LC`, the data location counter, because it is
the one that assigns addresses. `PROCDECLARATION` is the only caller of
`NEWSEG` and `BUMPSEG`, which is exactly what `segment procedure` needs.

Every leg of the probe was mutation-tested and every leg fails when
mutated.

### 34b. Four procedures are Apple's, not II.0's

`DECLARAT.2` is twenty-one bytes long, takes a `setofsys`, has no locals,
and its whole body is

```pascal
if not (sy in fsys) then begin error(6); skip(fsys) end
```

II.0 writes that inline at twenty-two sites and never factors it. Apple
did, and the factoring is real: it is the **only procedure of that shape on
either disk** — the sole one taking eight bytes of parameters, under forty
bytes long, calling `ERROR` and `SKIP` and nothing else. The spelling
`CHECKSYM` is ours, chosen to sit beside II.0's own `CHECKEND`.

`ONEUNIT`, `FINDSEG` and `SEGSRCH` are likewise Apple's. `ONEUNIT` is the
`else` arm of `USESDECLARATION`'s `repeat` loop — one unit of the `uses`
list — lifted into a procedure that takes `ID` by reference; its first
instruction is a `MOV 4` of that address into local 2, which is II.0's
`LNAME := ID`. `FINDSEG` and `SEGSRCH` are the library segment-dictionary
search that II.0 writes inline inside `GETTEXT`; `SEGSRCH` walks
`SEGDICT.SEGNAME[0..MAXSEG]` reached three lexical levels up, with the
`i <= 15` bound compiled in. All four spellings are ours and all four are
eight characters or fewer, so nothing about them can collide.

### 34c. `USESDECLARATION`, line for line, and four globals it names

`DECLARAT.10` reproduces II.0's `USESDECLARATION` in order:

```
  LDO 77 > 1                 -> ERROR(189)        level > 1
  INMODULE and not ININTERFACE -> ERROR(192)      decpart.b.text:95
  if not USING then USINGLIST := nil               :97
  sy <> ident -> ERROR(2)                          :100
  walk USINGLIST for ID, else ERROR(188)           :101-106
  ...                        -> CLP 11 (ONEUNIT)   the else arm
  INSYMBOL; TEST := sy <> comma                    :146-147
  sy <> semicolon -> ERROR(20)                     :149
  until TEST
  if sy = semicolon then INSYMBOL else ERROR(14)   :155
  if not USING then ... CLOSE(LIBRARY); LIBNOTOPEN :157-162
```

Its 514 bytes of locals are II.0's `SEGDICT`: a 512-byte record of
`DANDC`, `SEGNAME`, `SEGKIND`, `TEXTADDR` and `FILLER`, which is exactly
one block, `BLOCKREAD` from `SYSTEM.LIBRARY`. `SEGSRCH` reaches it at
offsets 34 and 98 — `SEGNAME` at 2+32, `SEGKIND` at 2+32+64 — three levels
up. II.0's `MAGIC` parameter is gone: Apple has no implicit
`uses turtlegraphics`.

Reading that against the source names four globals, and each one lands
**exactly** where finding 33's drift column predicted before the code was
read:

| global (1.1) | name | II.0 offset | predicted drift | 1.3 |
|---|---|---|---|---|
| 11 | `TEST` | 11 | +0 | 11 |
| 36 | `USING` | 35 | +1 | 37 |
| 63 | `USINGLIST` | 59 | +4 | 66 |
| 68 | `MODPTR` | 64 | +4 | 71 |

That is four falsifiable predictions from the alignment, all four
confirmed by the p-code, and the 1.3 offsets confirmed independently in
1.3's own `DECLARAT.10` and `DECLARAT.12`. `TEST` is the strongest: the
first sixteen words carry drift 0, so the alignment said global 11 and
nothing else, and `SRO 11` immediately after `TEST := sy <> comma` is what
the binary does — in *both* releases, where it does not move.


## 35. `ROUTINE`, the standard procedures, named by the code they emit

*Confidence: VERIFIED BINARY FACT for the emitted opcodes; STRONG
INFERENCE for the fourteen II.0 spellings; SPECULATION for the three that
are ours. `tools/probes/probe_routine.py`.*

### 35a. Each handler emits its own run-time call

`ROUTINE(LKEY)` in `bodypart.b.text` is a `case` over the standard
procedures, and every arm ends by emitting the p-code that calls the
run-time. Those opcodes are **literal operands in Apple's binary** —
`GEN1(30(*CSP*), 4(*XIT*))` compiles to `SLDC 30; SLDC 4; CXP 9,5` — so
the source's own comments name the arms, and the binary can disagree.

It does not. Every distinctive run-time number is emitted by **exactly
one** procedure, and it is the one the source says:

```
  CSP  1   NEW                ROUTINE.5   NEWSTMT
  CSP  10, 2, 3               ROUTINE.6   MOVE      fillchar, moveleft/right
  CSP  4   XIT                ROUTINE.7   EXIT
  CSP  5, 6                   ROUTINE.8   UNITIO    unitread, unitwrite
  CXP 0,23 SCONCAT            ROUTINE.9   CONCAT
  CXP 0,25 0,26 0,29          ROUTINE.10  COPYDELETE  scopy, sdelete, gotoxy
  GENLDC 18 DCVT, 12 DSTR     ROUTINE.11  STR
  CXP 0,6  FCLOSE             ROUTINE.12  CLOSE
  CXP 0,7  0,8  FGET FPUT     ROUTINE.13  GETPUTETC
  CSP  11  SCN                ROUTINE.14  SCAN
  CXP 0,28 BLOCKIO            ROUTINE.15  BLOCKIO
  (39 bytes, one CTP local)   ROUTINE.16  SIZEOF
```

Ownership is the point. This is not "ROUTINE.7 looks like `EXIT`" — it is
"ROUTINE.7 is the only procedure in the segment that emits CSP 4, and CSP
4 is XIT", which no rearrangement of the names survives. `ROUTINE.11` is
confirmed further, line for line: `COMPTYPES(LONGINTPTR, TYPTR)`, then
`GENLDC(18)` and `GENNR` on the integer path, `TYPTR := LONGINTPTR`, error
125, the comma, `STRGVAR(fsys + [rparent], true)`, `STRGTYPE`,
`GENLDC(MAXLENG)`, `GENLDC(12)`, `GENNR`, error 116.

### 35b. Apple moved `ROUTINE` out of `CALL`

II.0 declares `ROUTINE(LKEY: INTEGER)` inside `CALL`, at lexical level 3.
Apple could not: a SEGMENT procedure that swaps in and out has to sit
directly inside `BODYPART`. So `ROUTINE.1` is at **lex 2 and takes 12
bytes** where II.0's takes 2 — `FSYS` and `FCP` came down with it — and
`STRGVAR`, which II.0 declares as `ROUTINE`'s sibling in `CALL`, moved
inside, because four of the handlers need it.

Three of the seventeen are Apple's own factorings:

* **`GETCOMMA`** (ours), 14 bytes:
  `if sy = comma then insymbol else error(20)`. II.0 writes it inline.
* **`CHECKINT`** (ours), 9 bytes:
  `if GATTR.TYPTR <> INTPTR then error(125)`. Apple drops II.0's
  `<> nil` guard, so a type that is already in error raises 125 again.
* **`SPECIALS`** (ours), 762 bytes: the cases II.0's `CALL` keeps inline,
  in the `else` arm of `if LKEY in [...] then ROUTINE(LKEY)`. Its emitted
  constants are that `case` in order — `CXP 0,10`/`0,11` for eof and
  eoln, `GEN0` of ADI, SBI, SQI, SQR, ABI and ABR for pred/succ, sqr and
  abs, `CXP 0,24` and `0,27` for idsearch and pos, `CSP 9` for time,
  `CXP 0,4`/`0,5` for reset and open, `CSP 23` and `GENLDC(20)` for trunc.

`READ`, `WRITE` and `CALLNONSPECIAL` are *not* here: `ROUTINE.1` calls
only `.5`…`.17`, and no procedure in the segment emits the FREADINT /
FWRITEINT family. They stayed in `BODYPART` with `CALL`.

### 35c. Six of the names shadow predeclared identifiers, legally

`CLOSE`, `CONCAT`, `EXIT`, `SCAN`, `SIZEOF` and `STR` are all Apple
Pascal *intrinsics*, and II.0 names its handlers after the procedures
they compile. That is legal — the manual says the compiler "will accept
it", and only the *scope of the new meaning* loses the original — and
Apple demonstrably compiled that source.

So `probe_identifiers.py` was too strict: it assumed a single outermost
scope. It now allows a shadowing name when the name is one II.0 itself
declares as a **nested** procedure, read out of the source rather than
listed, and only for a procedure name — a global that shadows an
intrinsic still fails, and so does an invented procedure name. Both
confirmed by mutation.

### 35d. Five more `BODYPART` names fall out

`ROUTINE`'s handlers call into `BODYPART`, and which handler calls what
identifies the callee against II.0:

| | | |
|---|---|---|
| `BODYPART.2` | `LINKERREF` | `(klass; id, addr)` = 6 bytes; the only `BLOCKIO` in the segment, and called by `GEN1` and by `EXIT` — II.0's two call sites |
| `BODYPART.9` | `LOADADDRESS` | called by `STRGVAR`, `CLOSE`, `GETPUTETC` |
| `BODYPART.10` | `BYTEADDRESS` | called by `MOVE`, `UNITIO`, `SCAN` |
| `BODYPART.12` | `VARIABLE` | `(fsys)` = 8 bytes, 39 bytes long: `SEARCHID`, else `error(2)` and `UVARPTR`, then `SELECTOR` |
| `BODYPART.22` | `SELECTOR` | `(fsys; fcp)` = 10 bytes, the largest procedure in `BODYPART`, and `VARIABLE`'s only callee |

`LOADADDRESS` and `BYTEADDRESS` are the pair worth spelling out, because
nothing about either procedure alone would separate them: `MOVE` and
`SCAN` call one, `CLOSE` and `GETPUTETC` call the other, and **`BLOCKIO`
calls both** — `VARIABLE; LOADADDRESS` then `VARIABLE; BYTEADDRESS`,
which is exactly how `bodypart.b.text` writes it.

`BODYPART.7` is `GENNR`'s *role* but not II.0's body, and the difference
matters. II.0 emits `GEN1(79 CGP, PFNUMOF[extproc])` and keeps a
`PFNUMOF` table; Apple emits `GEN2(77 CXP, seg, proc)` and instead adds
the segment to a two-word set at global 183. **Apple has no `PFNUMOF`** —
which is finding 33c's open question about the words missing around
`DISPLAY`. Finding 38 closes it: the set *is* what stands in `PFNUMOF`'s
declaration slot, and −6 + 2 is the whole of the step.

## 36. `BODYPART`, all of it, and what Apple did to II.0's `BODY`

*Confidence: VERIFIED BINARY FACT for the shapes and the emitted
constants; STRONG INFERENCE for the II.0 spellings and for `BODY2`;
SPECULATION for `MASKBOOL`, `HOLDSTMT` and `HOLDRTN`.
`tools/probes/probe_bodypart.py`.*

### 36a. Apple split II.0's `BODY` into four

II.0's `BODY` is one procedure. Apple made it four, and **named two of
them itself**: the codefile carries SEGMENT procedures `BODY1` and
`BODY3` (finding 30). The binary fixes the rest of the shape:

* `BODYPART.24` calls **`BODY1`, then a local procedure, then `BODY3`**,
  in that order, and nothing else;
* it carries **38 bytes of locals** where the piece it calls carries 4 —
  that frame is what the three pieces share;
* `BODY1.1`, `BODYPART.25` and `BODY3.1` all sit at the **same lexical
  level, one deeper than 24**. They are siblings declared inside it.

So `BODYPART.24` is `BODY` and `BODYPART.25` is the sibling between
`BODY1` and `BODY3`. Naming it **`BODY2`** is the inference; everything
else here is read off the attribute tables. This also **corrects a name**:
`BODYPART.25` was recorded as `BODY`, and `BODY` is its parent.

Two more procedures exist only to control swapping, and they follow the
division `PASCALCO.28`/`.29` make one level up:

```
  BODYPART.1   if (not SWAPPING) or SWAPMORE then BODY else HOLDRTN
  BODYPART.37  HOLDRTN   LOADSEGMENT(10 ROUTINE);  BODY;   UNLOADSEGMENT
  BODYPART.26  HOLDSTMT  LOADSEGMENT(11 STATEMEN); BODY2;  UNLOADSEGMENT
  BODYPART.24  BODY      BODY1; if SWAPPING then HOLDSTMT else BODY2; BODY3
```

Both spellings are ours. The segment numbers are not: the probe resolves
10 and 11 through the codefile's own dictionary, so holding the wrong
segment fails.

### 36b. The other thirteen

| | | what pins it |
|---|---|---|
| `.14` | `LOADIDADDR` | emits `GEN2(50 LDA, …)` or `GEN2(54 LOD, …)` on `klass = actualvars` — II.0's body with the `VLEV = 1` short forms dropped. Called by `READ`, `WRITE` and `SPECIALS`: II.0's three sites |
| `.15` | `MASKBOOL` | **ours.** 16 bytes: `if GATTR.TYPTR = BOOLPTR then begin GENBYTE(1); GENBYTE(132) end` — it emits `SLDC 1; LAND`, masking a boolean to 0/1 before it is used as an ordinal. II.0 has no counterpart |
| `.20` | `STORE` | `(var fattr)`; called by `ASSIGNMENT` and `FORSTATEMENT`, II.0's two sites |
| `.21` | `STRGTOPA` | `(fic)`, and **calls nothing at all** — it patches code already emitted |
| `.23` | `CALL` | `(fsys; fcp)`; calls `READ`, `WRITE`, `CALLNONSPECIAL` and `ROUTINE` — II.0's `CALL` minus the arms that went into `ROUTINE` |
| `.28` | `READ` | |
| `.29` | `WRITE` | one of only two callers of `DECSIZE` in the segment, which is what writing a long integer needs; `READ` is not among them |
| `.30` | `CALLNONSPECIAL` | calls `LINKERREF` and `NEWPROC` — what a call to a not-yet-declared or separate procedure needs |
| `.31` | `FLOATIT` | `(var fsp; forcefloat)` = 4 bytes |
| `.32` | `STRETCHIT` | `(var fsp)` = 2 bytes |
| `.36` | `MAKEPA` | `(var strgfsp; pafsp)`; calls `GETBOUNDS` |

That completes the segment: **37 of 37 in 1.1**. 1.3 has 38, and the
insertion is at **26** — a 26-byte procedure at lex 4 nested inside
`BODY2`, with no counterpart in 1.1. Everything from 1.1's 26 upward
shifts by one, which is what the attribute tables show pair for pair, so
`names.py` now carries a single `bp13()` shift for the whole segment
instead of the two ad-hoc rules it had. 1.3's new `.26` is deliberately
left unnamed.

### 36c. Apple merged the two linker-info flags

II.0 keeps `DLINKERINFO` and `CLINKERINFO`: the first set by
`USESDECLARATION` and `PROCDECLARATION`, the second by `GENNR`'s
`ASSIGN`, both cleared by `WRITELINKERINFO`, and `block.text` tests them
separately. Apple has **one** flag. Global 44 (45 in 1.3) is stored into
by exactly the union of II.0's two sets —

```
  INITSCALARS := false        ONEUNIT         := true   (DLINKERINFO)
  WRITELINKERINFO := false    PROCDECLARATION := true   (DLINKERINFO)
                              NEWPROC         := true   (CLINKERINFO)
                              UNITPART        := true
```

— and read by `BLOCK`, `UNITPART` and `FINISHUP`. Since it is neither of
II.0's names, it gets one of ours: `LINKINFO`.

`BODYPART.13`, already called `NEWPROC`, is now placed exactly: it is
II.0's `ASSIGN` generalised from the six non-resident support routines to
any identifier record — `LCP^.PFNAME := NEXTPROC`, `error(251)` above
`MAXPROCNUM = 149`, `PROCTABLE[PFNAME] := 0`, `LINKINFO := true`.

### 36d. What `{$E}` does

Chasing global 44 settled half of finding 24's second loose end. Global
45 (46 in 1.3) is `OPT_E`, set by `COMPOPTI` from the option letter, and
it is read in exactly three places. Two of them are `TYP` and
`SIMPLETYPE`, where II.0 writes

```pascal
IF INMODULE THEN IF NOT ININTERFACE THEN ERROR(191); (*NO PRIVATE FILES*)
```

and Apple writes `if INMODULE then if not (ININTERFACE or OPT_E) then
error(191)`. So **`{$E+}` permits a file variable private to a unit's
implementation**, which the p-System otherwise forbids. The third reader
is `BODY`. The letter is still all we have for the name.

## 37. The last five segments — every procedure in 1.1 now has a name

*Confidence: VERIFIED BINARY FACT for the shapes; STRONG INFERENCE for
the II.0 spellings; SPECULATION for the seven that are ours.
`tools/probes/probe_segments_rest.py`.*

### 37a. COMPINIT calls exactly II.0's seven

`compinit.text` declares seven procedures inside `COMPINIT`. Apple's
segment has nine, and the segment procedure calls **exactly seven** of
them — the other two are called only from `ENTSPCPROCS` and
`ENTSTDPROCS`. So the seven are II.0's, in II.0's order:

```
  .2 ENTSTDTYPES   the only caller of DECSIZE, which the long-integer
                   descriptor needs
  .3 ENTSTDNAMES   fourteen string literals and ENTERID
  .4 ENTUNDECL     the only one of the seven that calls nothing at all
  .7 ENTSPCPROCS   .8 ENTSTDPROCS
  .9 INITSCALARS   stores into forty-odd scalar globals
 .10 INITSETS      `LAO 126; LDC 4w; STM 4` and its seven siblings
```

The two that are not II.0's are one space optimisation. Rather than an
eight-byte string constant per standard identifier, `PUTNAMES` (ours)
appends a `.`-separated batch of names to a pool — `ENTSPCPROCS` calls it
five times, `ENTSTDPROCS` twice, each with one string constant — and
`NEXTNAME` (ours) takes them out one at a time, blanking eight characters
and `SCAN`ning to the next `.`. Each is called once, inside the loop.

**This corrects finding 26c on one point.** It said the eight follow-sets
were initialised in `COMPINIT.9`. They are initialised in `COMPINIT.10`:
`.9` is `INITSCALARS` and writes single words with `SRO`, `.10` is
`INITSETS` and writes four-word sets with `LAO`/`STM`. The assignment of
each set to its *name*, which was the substance of 26c, is untouched.

### 37b. `PASCALCO.12` is `CHECKEND`, not `NEXTLINE`

`NEXTLINE` was a name of ours that described the behaviour. The routine
is II.0's `CHECKEND` (`procs.a.text:142`), and it reproduces it line for
line:

```
  SCREENDOTS := SCREENDOTS + 1;  SYMCURSOR := SYMCURSOR + 1;
  if NOISY then begin write('.');
      if (SCREENDOTS - STARTDOTS) mod 50 = 0 then
        begin writeln; write('<', SCREENDOTS:4, '>') end end;
  if LIST then PRINTLINE;
  BPTONLINE := false;
  if SYMBUFP^[SYMCURSOR] = chr(0) then GETNEXTPAGE else ...
```

`'.'` is `SLDC 46`, `'<'` and `'>'` are 60 and 62, the field width is 4
and the modulus 50 — all literals in the p-code. It also names **global
91 (94 in 1.3) as `STARTDOTS`**, II.0's offset 85 at the +6 drift the
alignment predicted, and `CHECKEND` is its only reader on either disk
apart from `FINISHUP`, which II.0 has not got.

### 37c. The rest

| segment | | |
|---|---|---|
| `WRITELIN` | `GETREFS`, `GETNEXTBLOCK`, `GLOBALSEARCH` | `GETNEXTBLOCK` is the only thing at lex 3 in the segment and the only `BLOCKIO`; `GLOBALSEARCH` recurses — it walks the symbol tree — and calls `GETREFS`, which is II.0's arrangement |
| `UNITPART` | `OPENREFFILE`, `UNITDECLARATION`, `UNITBODY` | `OPENREFFILE` is the only `FOPEN`; `UNITDECLARATION` takes `(fsys; var umarkp)` = 10 bytes; `UNITBODY` is **ours** — II.0 compiles the implementation inline in `UNITPART`'s body, and it is the only caller of `BODYPART` outside `PASCALCO` |
| `NUMSTRIN` | `STRING`, `NUMBER` | the scanner's two sub-scanners, made a segment. `.1` is a two-line dispatcher. `STRING` calls `ERROR` and `CHECKEND` — II.0's `error(202); CHECKEND; goto 1` on an unterminated string — and has 90 bytes of locals for II.0's `T: packed array [1..80] of char`. `NUMBER` calls `ERROR` alone |
| `COMPOPTI` | `BADOPT`, `OPTWORD`, `OPTLIST` | **all ours.** II.0 handles options inline in `COMMENTER`. `BADOPT` is eight bytes: clear a flag in `COMPOPTI`'s frame, then `CSP 4` EXIT of segment 18 procedure 1 |
| `BODY3` | `UNITSEGS` | **ours.** It emits `GEN1(30, 21 GETSEG)` and `GEN1(30, 22 RELSEG)` four times each, and is the **only** procedure on either disk that emits either. II.0 emits the GETSEG loop at the head of `BODY` and the RELSEG loop at its tail; Apple emits both from here |

`BODY3.1` is confirmed as the tail of II.0's `BODY` in the process — its
emissions run `INSYMBOL`/`ERROR(13)`, `GEN2(50 LDA)`, `GENLDC(0)`,
`GEN2(77,0,6 FCLOSE)`, `UNITSEGS`, `GEN0(86 XIT)`, the `RBP`/`RNP`,
`ERROR(168)` and then the `GENWORD` sequence and `WRITECODE`, which is
`bodypart.e.text:516-573` step for step.

### 37d. The count

**142 of 142 procedures in Apple Pascal 1.1 now have a name.** 1.3 has
147; the three without one — `COMPINIT.11`, `BODYPART.26` and
`COMPOPTI.5` — are new in 1.3, and the probe checks that two of them are
*appended* at the end of their segments rather than inserted, which is
why 1.1's numbering carries over unshifted.

`STRING` forced the shadowing rule of finding 35c to be stated properly.
A predeclared identifier may be redeclared — the manual says the
compiler "will accept it" — and the cost falls only *within the scope of
the new meaning*. So `probe_identifiers.py` now allows a shadow when both
halves of that are evidenced: II.0 names a procedure the same (Apple's
compiler accepted that source) **and** Apple declares it at lexical level
2 or deeper, read from the attribute tables, so the shadow cannot reach
the outermost scope. An invented name fails the first test and a global
fails the second; both confirmed by mutation. Seven names qualify:
`CLOSE`, `CONCAT`, `EXIT`, `SCAN`, `SIZEOF`, `STR` and `STRING`.

Separately, `tools/show.py` was printing the **wrong procedure** for the
last one in every segment: the disassembly's `SEGMENT` header sits at the
end of the previous procedure's block, so each segment's last procedure
was being filed under the next segment's name. Fixed; that was the
long-standing "`COMPINIT.10` not found".

## 38. The `VAR` block accounted for: `PFNUMOF`, `SEGMAP`, and the block that switches source files

*Confidence: VERIFIED BINARY FACT for every shape and offset; STRONG
INFERENCE for the II.0 spellings, which are the source's own; SPECULATION
only for the two names that are ours, `SEGSUSED` and `TEXTSTRT`.
`tools/probes/probe_globalmap.py`, 48 checks, twelve mutation-tested legs.*

Finding 33c left the alignment of II.0's `VAR` block against Apple's
globals with three unexplained drift steps and 48 unnamed offsets. All
three steps are now closed, and the whole tail of the block is named.

### 38a. A parser bug in `vardecl.py`, and why it mattered

The alignment tool collapses inline `RECORD … END` types so their fields
do not read as declarations of their own. The regex that does it had three
literal backspace bytes (`0x08`) embedded in the pattern — invisible to
`grep` and to a plain read of the file, visible only to `cat -A` — so the
collapse never fired. Seven record fields (`FLABEL`, `CREC`, `CDSPL`,
`VREC` out of `DISPLAY`; `SEGNAME`, `SEGKIND`, `TEXTADDR` out of
`SEGTABLE`) were being laid out as variables, which shifted every II.0
offset past `DISPLAY` and corrupted the drift column from there on. The
step at `PROCTABLE` read −2 when it is −4, and the step at `COMMENT` read
+16 when it is +24.

That is the second time an invisible-state bug has produced a plausible
wrong answer in this project — the first was a stale `__pycache__` masking
a mutation test. The lesson is the same both times: when something
*obviously* matches and demonstrably does not, check the bytes before
re-reading the logic.

`analysis/global_map/vardecl-ii0.txt` now reports **118 II.0 variables, 83
of them matched to a recovered Apple name, in 11 runs of constant drift**,
and the whole tail from `REFFILE` to `LP` aligns word for word.

### 38b. Apple deleted `PFNUMOF` and put a set of segment numbers in its slot

`DISPLAY` is II.0's, untouched. `DISPLIMIT = 12` gives thirteen four-word
entries = 52 words, and the binary indexes it with `IXA 4` at every one of
its index sites in 1.1 and again in 1.3 — a stride the binary could have
contradicted and does not.

II.0 declares `PFNUMOF: NONRESPFLIST` immediately after it: six words,
`ARRAY [NONRESIDENT] OF INTEGER` over six enumerators. Apple has, at
exactly that declaration position, **a two-word set** — global 183 in 1.1,
186 in 1.3. Finding 35d already showed why: II.0's `GENNR` emits
`GEN1(79 CGP, PFNUMOF[extproc])` and needs the table; Apple emits
`GEN2(77 CXP, seg, proc)` and needs instead to remember which segments the
code calls into. `BODYPART.7` is that substitution and nothing else — its
entire body, thirteen instructions:

```
0488  LAO 183 ; LAO 183 ; LDM 2 ; SLDC 2 ; SLDL 2 ; SGS ; UNI ; ADJ 2 ; STM 2
0498  SLDC 77 ; SLDL 2 ; SLDL 1 ; CIP 6
```

which is `SEGSUSED := SEGSUSED + [seg]; GEN2(77 (*CXP*), seg, proc)`. The
other users are `DECLARAT.11 ONEUNIT` (adds `SEG`, and the slot `NEXTSEG`
just took), `BODY3.2 UNITSEGS` (walks the set downward emitting
`GENLDC(i); GEN1(30 CSP, 22 RELSEG)` — the `GETSEG`/`RELSEG` emission
finding 37 attributed to it), `BODY3.1`, `UNITPART.1` and `FINISHUP.1`
(`31 in SEGSUSED`). Two words is `SET OF 0..31`, and the probe measures
the width from every reference rather than assuming it.

So the drift step at `PROCTABLE` is **−6 + 2 = −4**, exactly the observed
`+6 → +2`. `PROCTABLE` itself is then 150 words, which is `MAXPROCNUM =
149` unchanged.

`SEGSUSED` is our name; Apple's is unrecoverable, since nothing in the
codefile or the manuals mentions it.

### 38c. The step at `COMMENT` is `SEGTABLE`'s ninth word plus `SEGMAP`

II.0's `SEGTABLE` entry is eight words. Apple's is nine — `IXA 9`
everywhere, sixteen entries, so **+16** — and the extra word is the
codefile's `SEGINFO` (finding 28).

The other eight are `SEGMAP` at 479, which II.0 has no counterpart for,
because II.0's `SEGRANGE = 0..MAXSEG` lets a segment number index
`SEGTABLE` directly. Apple lets segment numbers run past 15 (finding 27a)
and so must map:

```
LAO 479 ; SLDO 13 (SEG) ; IXP 4,4 ; LDP ; LAO 335 ; … ; IXA 9
```

`IXP 4,4` is four fields per word, four bits wide: a `PACKED ARRAY OF
0..15`, and eight words is 32 nibbles. **16 + 8 = 24 = the observed
`+2 → +26`**, with nothing left over — so Apple inserted exactly one new
variable in the whole stretch between `SEGTABLE` and `COMMENT`.

### 38d. The source-switching block, 575..585

`REFFILE` ends at 574 and `LIBRARY` begins at 586, so eleven words hold
II.0's ten (`compglbls.text` 344–351) and exactly one Apple insertion —
the `+26 → +27` step.

The three reference-file words come out of `BODYPART.2 LINKERREF`:

```
LDO 576 > 128  →  LAO 535 (REFFILE) ; LDO 577 ; 0 ; 1 ; LDO 575 ; 0;0;0 ; CXP OS.28
                  575 := 575 + 1 ; 576 := 1
LDO 577 ; LDO 576 ; SLDC 1 ; SBI ; IXA 2
```

— a block number, a 1-based count into a two-word-element array, and the
array pointer, which is the only one of the three whose address is taken
and only to pass to `NEW`. That is `REFBLK`, `NREFS`, `REFLIST`, at drift
+26.

The six save slots were placed **by behaviour alone**, using nothing about
declaration order. `PASCALCO.3` is II.0's `GETNEXTPAGE` line for line, and
it says which global each one shadows:

```
LDO 579 → SRO 90 (SYMBLK) ; LDO 582 → SRO 14 (SYMCURSOR) ; LDO 581 → SRO 95 (LINESTART)
LDO 580 → SRO 90          ; LDO 584 → SRO 14            ; LDO 583 → SRO 95
```

and which set is which, because II.0 restores `PREV*` when `USING` goes
false and `OLD*` when `INCLUDING` does. The binary carries both flags —
`LDO 37; LDO 36; LOR; LNOT` is `if not (INCLUDING or USING)`, which names
global 37 `INCLUDING` alongside the already-recovered 36 `USING`. The
savers agree: `DECLARAT.12 GETTEXT` writes `{582, 581, 579}` and
`COMPOPTI`'s `$I` arm writes `{584, 583, 580}`, exactly as
`decpart.b.text` and `procs.a.text` write them — including
`PREVSYMBLK := SYMBLK - 2`, which is `LDO 90; SLDC 2; SBI; SRO 579` in the
binary.

Laid out that way, all six land at a **constant drift of +27, in exactly
the order II.0's two declarations allocate them backwards**:

| II.0 | | Apple 1.1 | 1.3 |
|---|---|---|---|
| 552 | `PREVSYMBLK` | 579 | 709 |
| 553 | `OLDSYMBLK` | 580 | 710 |
| 554 | `PREVLINESTART` | 581 | 711 |
| 555 | `PREVSYMCURSOR` | 582 | 712 |
| 556 | `OLDLINESTART` | 583 | 713 |
| 557 | `OLDSYMCURSOR` | 584 | 714 |
| 558 | `USEFILE` | 585 | 715 |

Nothing in the reasoning that placed them used declaration order, so this
is the check that could have failed. It is also a second, independent
confirmation of finding 33's backwards-allocation rule.

`USEFILE` is II.0's `UNITFILE = (WORKCODE,SYSLIBRARY)` **with a third
enumerator**. `GETTEXT` stores 0 for a unit already in the workfile, 2
when the `$U` library's segment dictionary reads, and 1 after falling back
to opening `'*SYSTEM.LIBRARY'` by name. Only `= WORKCODE` is ever tested,
which is why the third value has no observable effect — but three distinct
constants are stored, and the probe fails if only two are.

The insertion is therefore **578**, between `REFLIST` and `PREVSYMBLK`,
and it is a cursor. Apple restructured `GETNEXTPAGE`: II.0 calls
`WRITETEXT` at the bottom, inside `if SYMCURSOR = 0`; Apple hoists it to
the top and buffers first —

```
if INMODULE and ININTERFACE and not USING then
  begin MOVELEFT(SYMBUFP^[578], CODEP^[0], 1024); WRITETEXT(true); 578 := 0 end
```

— so 578 is the `SYMBUFP` offset of the first interface-text byte not yet
captured. `UNITPART` sets it to `SYMCURSOR` to start the capture and ends
with `IC := SYMCURSOR - 578 + 10`. We call it `TEXTSTRT`; the name is
ours.

### 38e. What this settles in 1.3

The same three objects carry across, and each widens exactly as raising
the segment limit from 32 to 64 would make it:

| | 1.1 | 1.3 | |
|---|---|---|---|
| `SEGSUSED` | 2 words, `SET OF 0..31` | 4 words, `SET OF 0..63` | +2 |
| `SEGMAP` | 8 words = 32 nibbles | 16 words = 64 nibbles | +8 |
| `PROCTABLE` | 150 | 255 | +105 |

1.3's `BODYPART.7` is the same thirteen instructions with `LDM/ADJ/STM 4`
and `SLDC 4` where 1.1 has 2; 1.3's `SEGMAP` is still `IXP 4,4`. `DISPLAY`
and `SEGTABLE` are unchanged. That is **+115 of 1.3's roughly 130 words of
global growth**, previously open under task 10.

## 39. The rest of the `VAR` block — 1.1's global map is finished but for the file windows

*Confidence: VERIFIED BINARY FACT for every placement; STRONG INFERENCE
for the II.0 spellings, which are the source's own; SPECULATION only for
the three names that are ours, and two of those are Apple's own words.
`tools/probes/probe_globalmap.py`, 88 checks, twenty mutation-tested legs.*

Finding 38 closed the three drift steps. What was left was the 35 touched
offsets in 1.1 that still had no name — and with the alignment corrected,
almost all of them are boxed in on both sides.

### 39a. The drift column as a sieve

Once a stretch of the alignment has a *verified* Apple name at each end
and the same number of words as II.0 has names between them, the
assignment inside is forced: II.0 allocates in declaration order (finding
33), so there is only one way to fill the gap. Five gaps are of that
shape, and between them they place fourteen names without any appeal to
what the code does.

That is a prediction, not a derivation, so every one was then confirmed
from behaviour — and the confirmations are what the probe checks. The two
arguments are independent: nothing that identified `GETSTMTLEV` from
`INSYMBOL`'s opening three instructions used the fact that II.0 declares
it between `PUBLICPROCS` and `LCMAX`.

| Apple 1.1 | | what the binary says |
|---|---|---|
| 17 | `ID` | `compglbls.text` says of the four before it: *"SCANNER GLOBALS...NEXT FOUR VARS MUST BE IN THIS ORDER FOR IDSEARCH"* — `SYMCURSOR`, `SY`, `OP`, `ID` = Apple's 14, 15, 16, 17, and `ID` is four words wide |
| 24 | `DISX` | `SEARCHID` is `for DISX := TOP downto 0 do LCP := DISPLAY[DISX].FNAME`: `SLDO 8; SRO 24`, then `LAO 131; LDO 24; IXA 4; SIND 0` |
| 26 | `GETSTMTLEV` | `INSYMBOL` opens `LDO 26; FJP; LDO 78; SRO 79; SLDC 0; SRO 26` = `if GETSTMTLEV then begin BEGSTMTLEV := STMTLEV; GETSTMTLEV := false end` |
| 27 | `PUBLICPROCS` | set under `ININTERFACE and not USING`, cleared by `UNITDECLARATION`, tested by `UNITPART` — `decpart.c` 370, `unitpart` 279 and 333 |
| 29 | `LIBNOTOPEN` | `GETTEXT`'s `if LIBNOTOPEN then RESET(LIBRARY, SYSTEMLIB)`, cleared on success; `COMPINIT` sets it true |
| 40 | `LSEPPROC` | `GETTEXT` sets it from the used unit's `SEGKIND` and then `if not LSEPPROC then begin SEG := NEXTSEG; NEXTPROC := 1 end` |
| 53 | `PRTERR` | `SEARCHID` ends `if PRTERR then ERROR(104)` — *"Undeclared identifier"* |
| 64 | `FWPTR` | the forward-declaration list head |
| 65 | `OUTERBLOCK` | `NEW(g65, 18)`, a `PROC` record, and `BLOCK`'s `TOS^.PREVLEXSTACKP^.DFPROCP = OUTERBLOCK` |
| 76 | `GLOBTESTP` | II.0's *"LAST TESTPOINTER"* |
| 87 | `SCONST` | `NEW(SCONST, 130)` — `INSYMBOL`'s string result |
| 88 | `STRGCSTIC` | `STRGCSTIC := IC`, the address of the last string placed in the code |
| 89 | `SMALLESTSPACE` | the compiler's only `CSP 40 MEMAVAIL` |
| 94 | `LOWTIME` | the compiler's only `CSP 9 TIME`, which takes it by reference |
| 130 | `VARS` | `SETOFIDS`, one word: built with `ADJ 1; SRO 130`, tested with `LDO 130; SLDC 1; INN` |

### 39b. `ENTUNDECL` names six pointers by the record size it asks for

II.0's `ENTUNDECL` creates the six undeclared-identifier pointers in one
run, each with the variant tag its `klass` needs, and Apple's `COMPINIT.4`
is that run verbatim:

```
NEW(75, 9) ; NEW(74, 10) ; NEW(73, 11) ; NEW(71, 13) ; NEW(70, 18) ; NEW(69, 18)
```

Six `NEW`s, one procedure, in II.0's order — `UTYPPTR` (`TYPES`),
`UCSTPTR` (`KONST`), `UVARPTR` (`ACTUALVARS`), `UFLDPTR` (`FIELD`),
`UPRCPTR` (`PROC`), `UFCTPTR` (`FUNC`) — and the sizes rise exactly as the
variants do, with `PROC` and `FUNC` equal because their field lists are.
The same six sizes appear in the same order in 1.3.

Note the hole: the run is 69, 70, 71, **73**, 74, 75. Global 72 is
declared and *never referenced on either disk* — no `LDO`, `SRO` or `LAO`
touches it. It is the one word Apple inserted into this stretch, and the
binary cannot say what for. (1.3's is at 75, by the same +3 shift.)

### 39c. The lex stack, out of `BLOCK`

`PASCALCO.24` is `block.text` line for line, which places four more:

```
80  MARKP     the compiler's only CSP 32 MARK
81  TOS       RELEASE(TOS^.DMARKP); TOS := TOS^.PREVLEXSTACKP
              = LDO 81; INC 8; CSP 33 RELEASE; LDO 81; IND 10; SRO 81
82  GLEV      one of only three globals that index DISPLAY -- TOP, DISX, GLEV,
              which is what "GLOBAL LEVEL OF DISPLAY" means
83  NEWBLOCK  BLOCK's opening `NEWBLOCK := true; if not NEWBLOCK then`
```

### 39d. The disk buffer

`compinit.text` 258 reads `SEG := 1; NEXTSEG := 10; CURBLK := 1; CURBYTE
:= 0; LSEPPROC := FALSE;`. Apple's `COMPINIT.9` has `SRO 85` (`NEXTSEG`)
immediately followed by `SLDC 1; SRO 967; SLDC 0; SRO 968` — so **967 =
`CURBLK`, 968 = `CURBYTE`**, and 969 is `DISKBUF`, whose byte index is
compared against 512 and whose address goes to `FBLOCKIO` and `MOVELEFT`.
They sit at drift +288, past the file-window block.

### 39e. Three names that are ours

**41 = `INTRINSIC`.** It stands in II.0's `SEPPROC` slot and inherits its
uses — the `SEGKIND` choice in `UNITPART`, the `LINKERREF` guard in
`ROUTINE` and `WRITELINKERINFO`, cleared beside `INMODULE` at the end of
the unit — but Apple drives it from a different keyword. `UNITPART.3`
compares the scanned identifier against the literal `'INTRINSI'`, which
is Apple's `UNIT name; INTRINSIC CODE n DATA m`, not II.0's `SEPARATE`.
The spelling is Apple's word, read off the literal; that it names a
*variable* is ours.

**84 = `DATASEG`.** Apple-only, and the one insertion between `NEWBLOCK`
and `NEXTSEG`. The `DATA` clause of that same declaration reads a constant
into it, raises error 203 unless it is in `0..31` (the test is against a
two-word set of all ones), defaults it to `SEG + 1`, and then does
`SEGMAP[DATASEG] := SEGSLOT`. `SEG` is the intrinsic unit's code segment;
this is its data segment. `SEGMAP` — finding 38's nibble array — is
indexed by it, which is what makes it a segment number rather than a slot.

**62 = `RESIDENT`, and the vendor's manual settles it.** `COMPOPTI.1`
switches on the option letter with one `XJP` over `'C'..'V'`, and the `R`
arm is

```
if (SW = '+') or (SW = '-') then RANGECHECK := (SW = '+') else OPTLIST
```

— an option letter with *two* forms. The *Language Reference* lists both:

> `$R+ $R-` … Range checking on/off
> `$R unit name or $R segment number` … Load segment

and describes the second:

> This option forces the code of a specified UNIT or SEGMENT procedure to
> be kept in memory, for as long as the procedure that contains the option
> is active … **The resident option must immediately follow the BEGIN that
> starts the procedure body** … the "Resident" option can be applied to
> more than one segment, by separating the names of segments with commas,
> as in `(*$R ALPHA,BETA,GAMMA*)`

Every clause of that is in the binary. `OPTLIST` loops taking identifiers
*and* integer constants, because the manual allows a unit name or a
segment number. `PASCALCO.24 BLOCK` and `UNITPART.4 UNITBODY` set global
62 to `NIL`, once per body. And `BODY1` reads it at the very top of the
body — where the manual says the option must appear — emitting two `NOP`s
and a label to reserve the patch site when the list is non-empty.

The 1.1 *Update* pamphlet then confirms the reading from the other side,
listing among the bugs 1.2 fixed: *"A regular unit using `(*$R segname*)`
or `(*$R unitname*)` was not linked properly"*, and *"If the Compiler
Resident option (`$R`) was done on an intrinsic unit which has a data
segment, the code segment was loaded before the data segment"* — which is
this global and `DATASEG` in one sentence.

### 39f. Where the map stands

**1.1: 129 of the 133 touched globals are named.** The four that are not
are the file-window buffers at 835, 886, 926 and 966, which are section
16's open question about the file-variable block layout, not a naming
problem.

On the II.0 side the account is complete: of 118 variables, 111 land on an
Apple name, and every one of the seven that does not is explained —
`GATTR` became five separately addressed fields (finding 31),
`DLINKERINFO` and `CLINKERINFO` were merged into `LINKINFO` (finding 36c),
`PFNUMOF` was deleted (finding 38), and `STARTINGUP`, `SEPPROC` and
`NOSWAP` are the three booleans Apple dropped, with `SWAPMORE`,
`SWAPPING` and `NOLOAD` occupying that space.

1.3 has eight unnamed: the four window buffers, one new scalar at 31, and
three new words at 1355–1357 past `DISKBUF`. Those belong to task 10.

## 40. 1.3's global growth, word for word

*Confidence: VERIFIED BINARY FACT for the ledger and for every constant in
it; STRONG INFERENCE for what the three new tail words are for;
SPECULATION for their four spellings, which are ours.
`tools/probes/probe_globalmap.py`, 95 checks.*

1.3's global area is 1357 words against 1.1's 1224 (finding 46 corrected both endpoints; the difference is unchanged). The correspondence
table localises the insertions — its shift column steps six times, and
each step says how many words went in and where. Findings 38 and 39 named
enough of both maps to say *what*, and the total comes out exact.

| step | at | words | what |
|---|---|---|---|
| +0 → +1 | `ININTERFACE` | 1 | `ISPROG` |
| +1 → +3 | `NILPTR` | 2 | `BYTEPTR` and `WORDPTR` (finding 22b) |
| +3 → +5 | `PROCTABLE` | 2 | `SEGSUSED`, `SET OF 0..31` → `SET OF 0..63` |
| +5 → +110 | `SEGTABLE` | 105 | `PROCTABLE`, 150 → 255 |
| +110 → +118 | `COMMENT` | 8 | `SEGMAP`, 32 nibbles → 64 |
| +118 → +130 | `REFFILE` | 12 | `JTAB`, 25 → 37 |
| past the table | after `DISKBUF` | 3 | `HAS128K`, `CONLIST`, `LSTOPEN` |

**1 + 2 + 2 + 105 + 8 + 12 + 3 = 133 = 1357 − 1224.** Nothing is left
over, and nothing is double-counted. Four of the seven were already
explained (findings 22b and 38); this finding is the other three.

### 40a. `JTAB` grew, and the binary carries the bound

The step at `REFFILE` is II.0's long-jump table. `GENJMP` allocates a slot
and refuses when it runs out — in 1.1:

```
LDO 509 (NEXTJTAB) ; SLDC 24 ; EQUI ; FJP ; LDCI 253 ; CXP 1,2 (ERROR)
```

and in 1.3 the same three instructions with **36**, and `ERROR(254)`
rather than 253. `MAXJTAB` went 24 → 36, so `ARRAY [0..MAXJTAB] OF
INTEGER` went 25 → 37 words, which is the +12 exactly. The probe checks
the constant and the measured extent against each other in both releases,
so either one being wrong shows up.

The error number moving with it is worth noting for the reconstruction:
1.3 renumbered at least one compiler error, so error numbers are not
invariant across releases and cannot be used to carry a name from 1.1 to
1.3 without checking.

### 40b. `ISPROG` — 1.3 latches `not INMODULE`

1.3's `BLOCK` opens with one instruction pair 1.1 does not have:

```
LDO 33 (INMODULE) ; LNOT ; SRO 31
```

immediately before the `NEWBLOCK := true` that 1.1's `BLOCK` starts with.
`FINISHUP` then guards on it: where 1.1 unconditionally clears `SEGSUSED`,
writes `PROCTABLE[0]` and `PROCTABLE[1]` to the codefile and walks the
segments-used set, 1.3 wraps all of that in `if ISPROG then`. So the word
is a latch — `INMODULE` is cleared before `FINISHUP` runs, and 1.3 needs
to know whether what was compiled was a program or a unit.

(1.3's `MOVELEFT` in that block moves **8** bytes where 1.1 moves 4, which
is finding 38's set widening seen from a third direction.)

### 40c. The three new words are 1.3's startup

`COMPINIT.11` is one of the three procedures 1.3 adds, and it is a version
gate. It reads the byte at **$BF21**, and if it is not 4 it prints

> `Version 1.3 of SYSTEM.COMPILER cannot run`
> `with a non-1.3 version of SYSTEM.PASCAL`

and exits. $BF21 is `VERSION` in the interpreter's low-memory vector
table, *"Apple Pascal version number. 0=1.0, 2=1.1, 3=1.2, 4=1.3"*. Having
passed, it reads **bit 6 of the word at $BF22**, `FLAVOR`, into a global.
Bits 6 and 5 of `FLAVOR` are the memory size — `00`=64K, `01`=48K,
`10`=128K — so bit 6 set is a 128K machine. We call the global
**`HAS128K`**.

What it is for is in `BLOCK`. 1.1 compiles a unit only under `$S+`:

```
if SY = UNITSY and not INMODULE then
  if SWAPPING then UNITPART(...) else ERROR(408)
```

and error 408 is, in the manual's own words, *"(\*$S+\*) needed to compile
units"*. 1.3's test is `if SWAPPING or HAS128K` — on a 128K machine the
symbol table has room, so the option is no longer required.

The other two are 1.3's listing-file prompt, which 1.1 does not have.
`COMPINIT` asks for a file name; if the answer is `'CONSOLE:'` or `'#1:'`
it clears `NOISY` and sets **`CONLIST`**, and if the `OPEN` of `LP`
succeeds it sets `LIST` and **`LSTOPEN`**. Both are then read where they
matter: `ERROR` copies the message to the listing only `if LIST and not
CONLIST` — the listing is already on the screen — and `COMPOPTI`'s `$L`
arm opens `*SYSTEM.LST.TEXT[*]` only `if LIST and not LSTOPEN`, so the
option cannot reopen the file over the one startup already opened.

All four spellings are ours; `HAS128K` follows the name the `FLAVOR` table
gives that field.

### 40d. What is left of the 1.3 delta

The globals half of task 10 is closed. 1.3 has eight touched offsets
without a name, and four of them are the file-window buffers that 1.1
lacks names for too (section 16). The other four are named here.

Still open on that track: the two native procedures as reassemblable
source, the word-data block each carries after its last `RTS`, and the
three procedures 1.3 adds — of which `COMPINIT.11` is now identified as
the version gate, leaving `BODYPART.26` and `COMPOPTI.5`.

## 41. `case` was never recognised — the jump table is *after* the arms

*Confidence: VERIFIED BINARY FACT for the layout, which holds for all 54
case statements across both releases. `tools/probes/probe_structure.py`.*

Finding 21 listed `case` among the constructs the structurer recovers. It
did not recover a single one. Instrumenting the refusals turned up
**0 of 54 accepted**, all for the same reason, and it was not a near miss:
the recogniser had the layout backwards.

### 41a. What UCSD actually emits

`_case` looked at the `XJP` block and expected the arms to follow it. UCSD
puts the jump table at the *end*:

```
        <selector>
        UJP  Lxjp
  arm1: ...
        UJP  Lend
  arm2: ...
        UJP  Lend
  Lxjp: XJP  lo, hi, Lend, <table>
  Lend:
```

which makes sense once you look at `XJP`'s encoding — the table is inline,
immediately after the opcode, so it cannot sit in the middle of executable
code without being jumped over anyway. Putting it past the last arm costs
nothing and saves the jump.

So every arm target is at a *lower* address than the `XJP`, and the old
check "no arm may precede the XJP" rejected all 54. The construct has to be
recognised at the `UJP` that reaches the table, not at the table.

The shape is completely uniform, which is what makes it safe to key on. Of
54 `XJP` blocks across both disks:

* **54** carry no statements of their own — the block is the table;
* **54** have exactly one predecessor, and it ends in `UJP`;
* **54** have their `otherwise` target at the block immediately after the
  table;
* **54** have every arm target strictly between that predecessor and the
  table, once the arms that point at `otherwise` are set aside — those are
  selector values with no limb of their own, Pascal's "no such label", not
  case arms;
* **54** have the first arm immediately after the predecessor.

### 41b. Arms never fall through, and the check for it is now explicit

Wrapping a run of blocks in `begin … end` limbs is only sound if no arm
falls out of its own range into the next one — Pascal has no fall-through.
Unlike an escaping jump, a fall-through leaves nothing behind to notice:
the statements are all still emitted exactly once, so the coverage
invariant would pass while the output said something different.

All 54 end every arm with a jump, so it never happens. `_case` now checks
it anyway and refuses rather than mis-render, because the old code had the
same hole and only luck kept it from mattering.

### 41c. Escapes are allowed out of a case, and only out of a case

Every other construct refuses a region that jumps outside it. `case` no
longer does, and the asymmetry is deliberate.

What the escape rule protects against is *absorbing* a jump that mattered
— `while` swallows its latch's back edge, `if/else` swallows the jump over
the else. The only jump `case` absorbs is an arm's own `UJP <end>`, which
is the thing the limb boundary replaces. Any other edge out of an arm
survives into the output as a `goto` with a label, so the graph is
unchanged and the rendering is *more* faithful, not less: a `goto` out of a
case limb is what the source says. II.0's `INSYMBOL` has a literal `GOTO 1`
in one of its limbs, and that is one of the four.

### 41d. The measurement

| | before | after |
|---|---|---|
| fully structured | 201 / 287 (70%) | **229 / 287 (79%)** |
| gotos remaining | 1390 | **156** |
| per basic block | 0.22 | 0.02 |

Both correctness invariants stay at zero violations. 50 of the 54 cases
come out as `case` statements; the other four keep the gotos their arms
really contain.

The 54 accounted for 840 of the 1390 gotos, which is why this one change
moves the number so far — and why plan step 8's guess that short-circuit
booleans were the biggest remaining win was wrong. The compiler does not
short-circuit at all: `and` and `or` compile to `LAND` and `LOR` on values,
and the chains of `FJP` to a common target that look like short-circuiting
are nested `if`s in the source, which the structurer already handled.

What is left is thin and genuine. Of 246 loop headers 224 are recovered;
the 22 that are not are multi-exit loops — a `while` whose body jumps out,
which Pascal itself writes with a `goto` or an `EXIT`. The 156 residual
gotos are spread over 58 procedures with a maximum of 9 in any one, so
there is no further single win of this size available.

### 41e. What the output reads like

`INSYMBOL`'s scanner dispatch, which was 116 gotos and is now this:

```pascal
case SYMBUFP^[SYMCURSOR] of   { table 9..123 }
  39: begin
    NUMSTRIN(0, @L1);
  end;
  48, 49, 50, 51, 52, 53, 54, 55, 56, 57: begin
    L5 := SYMBUFP^[SYMCURSOR];
    ...
  end;
  61: begin
    SY := 41;
    OP := 13;
  end;
  62: begin
    SY := 41;
    if (SYMBUFP^[(SYMCURSOR+1)] = 61) then begin
      OP := 10;
```

39 is `'`, 48..57 the digits, 61 `=`, 62 `>` — and the nested case inside
the `>` limb is the two-character `>=` and `<>`.

## 42. The three procedures 1.3 adds — every routine in both binaries now has a name

*Confidence: VERIFIED BINARY FACT for what each one does and for the 1.1
code it replaces; SPECULATION for the three spellings, which are ours.
`tools/probes/probe_13_only.py`, 21 checks.*

`bp13()` has known since finding 19 that 1.3 inserts a procedure at
`BODYPART.26` — "a 26-byte procedure at lex 4 nested inside `BODY2`, with
no counterpart in 1.1" — without knowing what it was. With `COMPINIT.11`
and `COMPOPTI.5` it was the last of the unnamed routines. All three are
now placed, and **1.1's 142 procedures and 1.3's 147 are named without
exception**.

Comparing the two releases by *name* rather than by number — 1.3 renumbers,
since the natives take `PASCALCO.2` and `.3` and `BODYPART`'s insertion
shifts everything above 26 — 1.3 adds exactly five routines: the two
native ones of finding 19, plus these three.

### 42a. `BODYPART.26` is `INITUNIT`, and it is a bug fix the vendor documents

1.1's `BODY2` ends the declaration part of a level-1 body by walking
`USINGLIST` and emitting each used unit's initialisation call:

```
p := USINGLIST;
while p <> nil do begin
  if p^[10] then GEN2(77 (*CXP*), p^[9], 1);      { call unit's proc 1 }
  p := p^[7]                                       { next }
end
```

1.3's `BODY2` does none of that. It passes `USINGLIST` by reference to a
new procedure whose whole body is:

```
if p <> nil then begin
  INITUNIT(p^^[7]);                                { recurse on next }
  if p^^[10] then GEN2(77 (*CXP*), p^^[9], 1)
end
```

Same emission, same list, same fields — but the recursive call comes
*before* the emission, so the list is walked to its end and unwound. That
matters because `USINGLIST` is built by prepending, so a forward walk
emits the calls in reverse declaration order. Which is exactly what the
1.1 *Update* pamphlet lists among the compiler bugs 1.2 fixed:

> Initialization sections of nested units were (incorrectly) executed in
> the reverse order. Now they are executed in the correct order.

This is the first place the project has recovered *both sides* of a
documented Apple bug fix from the two binaries, and the shape of the fix
is worth noting for the reconstruction: 1.2 did not rewrite the loop, it
lifted it into a recursive procedure. Whatever we write for 1.3's
`BODY2` has to be a call, not a loop, or the code bytes differ.

The probe asserts both halves. That 1.3 recurses proves nothing on its own
— what makes the pairing real is that **1.1 does the emission itself and
1.3's `BODY2` no longer reads `USINGLIST` at all**, with a control check
that 1.3 reads `USINGLIST` somewhere, so the absence is not vacuous.

### 42b. `COMPINIT.11` is `CHECKVER`

Finding 40 identified it: the version gate that reads `$BF21` and refuses
to run under a `SYSTEM.PASCAL` older than 1.3, then takes the 128K bit out
of `$BF22` into `HAS128K`. It is the only writer of that global.

### 42c. `COMPOPTI.5` is `ADDRESID`

One node of finding 39's `$R` resident-segment list:

```
NEW(p, 13);
p^[9]  := <the scanned unit name or segment number>;
p^[7]  := RESIDENT;
p^[11] := (SY = ident) and INMODULE and not INTRINSIC;
RESIDENT := p
```

13 words is `IDCLASS` 4, the same identifier variant `UFLDPTR` uses
(finding 39b). 1.1's `OPTLIST` builds the identical node inline; 1.3 split
it out, and 1.3's `OPTLIST` calls it where 1.1's does the work itself.

### 42d. Where the naming track stands

Both binaries are fully named: 142 procedures in 1.1, 147 in 1.3, and 129
of 1.1's 133 touched globals (finding 39f). The remaining unnamed things
are the four file-window buffers in each release, which are a layout
question rather than a naming one.

## 43. The file variables: three of the four "window buffers" are not objects at all

*Confidence: VERIFIED SOURCE FACT for the two constants and the emission;
VERIFIED BINARY FACT for the offsets it predicts.
`tools/probes/probe_globalmap.py`, 106 checks.*

Section 16 has carried this since finding 10: four FIBs at 535, 586, 626,
666 with spacings 51, 40, 40, and four "window buffers" at 835, 886, 926,
966 with *identical* internal spacing and a constant +300 between the two
groups — "the parallel structure of the two groups is unexplained. Do not
assume these are two arrays."

They are not two arrays, and the second group is not a group. Two lines of
II.0 source settle it.

### 43a. `FILESIZE = 300`, and the window is emitted unconditionally

`compglbls.text:72`:

```pascal
FILESIZE = 300; NILFILESIZE = 40;
```

`decpart.a.text:508`, sizing a file type:

```pascal
IF LSP1 <> NIL THEN LSP^.SIZE := FILESIZE + LSP1^.SIZE
ELSE LSP^.SIZE := NILFILESIZE
```

So a `FILE OF T` is `300 + sizeof(T)` words and a bare `FILE` is **40**.
`TEXT` is `FILESIZE + CHARSIZE` = **301** (`compinit.text:26`).

And `bodypart.e.text:496`, the loop that initialises a block's file
variables:

```pascal
LCP := DISPLAY[TOP].FFILE;
WHILE LCP <> NIL DO
  BEGIN
    GEN2(50(*LDA*),0,VADDR);
    GEN2(50(*LDA*),0,VADDR+FILESIZE);
    ...
    GEN2(77(*CXP*),0(*SYS*),3(*FINIT*));
```

The window argument is **`VADDR + FILESIZE`, a fixed +300 — emitted for
every file variable, typed or not.** For an untyped `FILE` the variable is
40 words, so `VADDR + 300` points 260 words past the end of it, into
whatever the layout happens to have there. That is harmless: an untyped
file is only ever used with `BLOCKREAD`/`BLOCKWRITE`, never `f^`, so the
pointer is never dereferenced.

### 43b. What that predicts, and what the binary has

II.0 declares `REFFILE: FILE`, `INCLFILE, LIBRARY: FILE` — all untyped, 40
words each — and `LP: TEXT`, 301. So:

| | words | Apple 1.1 | window emitted | real? |
|---|---|---|---|---|
| `REFFILE` | 40 | 535..574 | 835 | no |
| `LIBRARY` | 40 | 586..625 | 886 | no |
| `INCLFILE` | 40 | 626..665 | 926 | no |
| `LP` | **301** | **666..966** | **966** | **yes** — `LP`'s own last word |

`LP` runs 666..966, and **835, 886 and 926 all fall inside it**. The
"second group" is three addresses pointing into the middle of `LP`'s
buffer plus one real window, and it mirrors the first group's spacing for
the trivial reason that each entry is its FIB plus a constant.

The check that could have failed: `CURBLK`, the next variable II.0
declares after `LP`, must then sit at `666 + 301 = 967`. It does — in 1.1
at 967 and in 1.3 at 1097, which is `796 + 301`.

### 43c. The alignment now runs flat to the end of the block

`tools/vardecl.py` had `LP` down as 40 words, "a TEXT file", which put
II.0's `CURBLK` at 679 against Apple's 967 and reported a drift of **+288**
for the last three variables — a step of +261 out of nowhere, which should
have been the clue. With `LP` at 301 the tail reads:

```
  559 LIBRARY           40    586    +27
  599 INCLFILE          40    626    +27
  639 LP               301    666    +27
  940 CURBLK             1    967    +27
  941 CURBYTE            1    968    +27
  942 DISKBUF          256    969    +27
```

**+27 from `PREVSYMBLK` all the way to the end of the `VAR` block**, 12
drift runs instead of 13. Everything after finding 38's insertion is
Apple keeping II.0's declaration order exactly.

### 43d. The last of section 16's global-map questions

That was the last unexplained thing in the global map. 133 offsets are
touched in 1.1; 129 have names, and the four that do not are these
addresses, three of which are not variables and the fourth of which is a
word of `LP`. The same holds in 1.3.

Worth keeping as a general caution: **an address the binary computes is
not evidence that an object lives there.** The map builds its object list
from touched offsets, and `LAO 835` looked exactly like a variable for as
long as nobody asked what emitted it.

## 44. The native procedures' trailing data: relocation tables, and every byte of both now accounted for

*Confidence: VERIFIED SOURCE FACT for the format (the 1.3 manual documents
it); VERIFIED BINARY FACT for everything it decodes to.
`tools/probes/probe_native_reloc.py`, 131 checks.*

`IDSEARCH` and `TREESEARCH` each carry a block of word data between their
last `RTS` and their attribute table, and `tools/disasm6502.py` has been
dumping it as raw bytes with the note "unidentified trailing data ... UCSD
stores relocation lists for assembled procedures, which is the obvious
guess, but the values have not been made to fit that". The guess was
right; what did not fit was the arithmetic.

### 44a. The format, from the vendor's own manual

Part IV chapter 4 of the 1.3 manual, "Assembly-Language Procedure
Attribute Tables" and "Relocation Tables", gives it in full:

> The highest word in the attribute table of an assembly-language procedure
> always has a 0 in its PROCEDURE NUMBER field. ... The RELOCSEG NUMBER
> field contains either a 0 or a positive number. ... The second highest
> word of the attribute table is, as in P-code procedure attribute tables,
> the ENTER IC field. ... Following this are four relocation tables ...
> From high address to low address, they are base-relative,
> segment-relative, procedure-relative, and Interpreter-relative.
>
> The format of all four relocation tables is the same: the highest word of
> each table specifies the number of entries (possibly 0) that follow (at
> lower disk addresses) in the table. The remainder of each table comprises
> that number of one-word **self-relative pointers** to locations in the
> procedure code that must be "fixed."

So an assembly procedure has **no EXIT IC, no parameter size and no data
size** — those three words are the top of the relocation area instead.
That is why `codefile.py`'s `exit_ic` was landing on JTAB-4 for both of
them: it was decoding the base-relative *count* as a self-relative
pointer, and the count is 0.

The reading that had failed earlier was of the pointer values themselves.
They are self-relative *downward*: a pointer stored at address `a` with
value `v` designates the word at **`a - v`**, the same convention as the
procedure dictionary (finding 4).

### 44b. What the two procedures actually declare

| | base | segment | procedure | interp |
|---|---|---|---|---|
| `IDSEARCH` | 0 | 0 | **28** | 0 |
| `TREESEARCH` | 0 | 0 | **4** | 0 |

Three of the four tables are empty in both, which is the informative part:
`.PUBLIC`/`.PRIVATE` (base-relative), `.REF`/`.DEF` (segment-relative) and
`.INTERP` are all unused, so **neither routine touches a global or calls
into the Interpreter**. They are self-contained, and everything they
reference is inside themselves.

`TREESEARCH`'s four entries are its four `JMP` operands:

```
  159A .word $0022   ;   fix up $1578      1577 4c 6e 00  JMP $006E -> $1580
  1598 .word $0027   ;   fix up $1571      1570 4c 6e 00  JMP $006E -> $1580
  1596 .word $002C   ;   fix up $156A      1569 4c 1c 00  JMP $001C -> $152E
  1594 .word $0041   ;   fix up $1553      1552 4c 1c 00  JMP $001C -> $152E
```

`JMP $001C` is not a jump to page zero; it is a jump to **procedure + $1C**,
which the loader completes, and procedure + $1C is `$152E` — the top of
the eight-byte compare loop. `JMP $006E` reaches `$1580`, the common store-
and-return tail. Both were unlabelled in the listing until now, because
the disassembler had no way to know the operand was relative.

`IDSEARCH`'s 28 are its two absolute operands plus **all 26 words of the
letter index**:

```
  14D2 .word $0263   ;   fix up $126F      126E b9 6d 00  LDA $006D,Y
  14D0 .word $0266   ;   fix up $126A      1269 b9 6c 00  LDA $006C,Y
  1506..14D4  26 entries, all .word $01F4, fixing up $1312 down to $12E0
```

The 26 identical values are what made the block look like nonsense: the
letter index is 26 consecutive words and the relocation entries are 26
consecutive words, so every self-relative distance between them is the
same constant, 500.

### 44c. Why `$006C` is nowhere near the table it reads

The two code operands look wrong until the relocation is applied. The
scanner does:

```
  1265 a5 88     LDA $88        ; first character of the identifier, uppercased
  1267 0a        ASL A          ; index = 2 * ord(c)
  1268 a8        TAY
  1269 b9 6c 00  LDA $006C,Y    ; procedure-relative base
  126E b9 6d 00  LDA $006D,Y
```

`$006C` is a base to be indexed, not an address, and the index is never
small: `'A'` is $41, so the smallest index is $82. Procedure + $6C + $82 =
procedure + $EE = **`$12E0`**, the first word of the letter index; `'Z'`
gives procedure + $6C + $B4 = `$1312`, the last. The base is offset
backwards by exactly `2 * ord('A')` so that the character code can be used
raw. Both of those are checks the binary could fail and does not.

### 44d. Every byte of both procedures is now accounted for

The relocation area tiles the gap exactly, with nothing left over at
either end:

```
  IDSEARCH    $11F2..$12E0 code    $12E0..$1314 letter index
              $1314..$14CE reserved words       $14CE..$150E relocation
              $150E..$1512 attribute table
  TREESEARCH  $1512..$1592 code    $1592..$15A2 relocation
              $15A2..$15A6 attribute table
```

The walk from JTAB-4 downward through four tables stops on `$14CE` and
`$1592` respectively — which are, independently, the byte after the last
reserved-word entry and the byte after the last `RTS`. That is the check
that could have failed: get any count wrong, read the pointers upward, or
put the tables in the wrong order, and the walk lands somewhere else.
Reversing `RELOC_KINDS`, adding a word to `content_end`, dropping one
entry per table and starting the walk at JTAB-6 were all tried and all
fail.

### 44e. Consequences for the reconstruction

The relocation tables are not something the reconstruction writes; they
are what Apple's assembler *emitted*, and reproducing them is the test
that the reassembled source is right. Concretely, source that reassembles
to the same bytes has to produce these tables, which means:

* both procedures are a single `.PROC` with no `.PUBLIC`, `.PRIVATE`,
  `.REF`, `.DEF` or `.INTERP` — every one of those would add an entry to a
  table that is empty;
* the letter index has to be written as 26 `.WORD` directives naming
  labels *inside the same procedure*, since that is what makes them
  procedure-relative;
* the two `LDA` bases and the four `JMP`s have to be written as label
  references, not as constants — `JMP $001C` assembled literally would
  produce no relocation entry at all and jump into page zero at run time.

That last point is the useful one: the relocation tables are a
machine-checkable summary of which operands in the source are symbolic.
There are exactly 32 of them across both procedures, and the disassembly
now marks each one `[reloc: procedure]`.

And the tool that has to produce them is on the evidence disk already:
**`SYSTEM.ASSMBLER`, Apple's own 6502 assembler**, ships on both 1.1 and
1.3 (with `6500.OPCODES`/`6502.OPCODES` beside it). Do not hand-build a
relocation table and do not reach for a modern assembler: write `.PROC`
source with symbolic operands, assemble it with Apple's assembler in the
emulator, and let it emit the tables. Reproducing this section's bytes —
counts, order and self-relative values — is then the acceptance test for
the reassembled source, exactly as recompiled p-code is for the Pascal
half. It also fixes the assembler's version: 1.3's `SYSTEM.ASSMBLER` is
dated 03-09-1985, the same day as its `SYSTEM.COMPILER`.

## 45. The first reconstructed source: both native procedures reassemble to the exact bytes

*Confidence: VERIFIED BINARY FACT — the reconstruction is compared byte for
byte against the disk. `tools/probes/probe_native_asm.py`, 18 checks, run
by `tools/build_all.py`.*

`src/native/SEARCH.TEXT` is the first piece of actual reconstructed source
in the repo: 1.3's `IDSEARCH` and `TREESEARCH` written in the Apple Pascal
Assembler's language, as `.PROC IDSEARCH,2` and `.FUNC TREESEARCH,3`.

It assembles to **800 and 148 bytes that are identical to Apple's**, over
the whole procedure — `enter_ic` through `jtab+2`, so instructions, the
letter index, the reserved-word table, all four relocation tables, `ENTER
IC` and the procedure-number word.

### 45a. Why the relocation tables make this a real test

Nothing in the source names a relocation entry. The tables are *derived*
from which operands mention a label, so getting them right means having
written every reference the way Apple did:

* `JMP CHKNAME`, not `JMP 001C`. The constant form assembles — to a
  different instruction, since `JMP` has no zero-page mode — and produces
  no relocation entry at all, so at run time it would jump into page zero.
* `.WORD NUMB`, not `.WORD 013A`. Same value, one fewer entry, and the
  procedure comes out two bytes short.
* `LDA ADRTBL-082,Y`, where `082` is `2*"A"`. The base is biased back by
  twice the character code of `A` so that the raw character can index the
  table; write the bias as anything else and the operand byte is wrong.

All three were tried as mutations and all three fail, as do swapping two
reserved words, changing the empty-letter sentinel's count and dropping one
`PLA` from the `.FUNC` stack bias.

### 45b. What the bytes do *not* settle

The identifiers are ours — Apple's label names are not in the codefile, and
nothing recovers them. So are the comments, the layout, and the spelling of
constants: `#" "` and `#20` assemble identically, as do `#123.` and `#7B`.
Where a choice was free the source follows **Dave Tribby's 1.2
disassembly**, since he read the same routines and his names are already
in `evidence/`. That is a convenience, not evidence, and the two differ
where it matters: 1.3 adds the reserved word `OTHERWISE` (`SY=$36`), and
1.3's zero-page scratch is `$7E`-`$97` where Tribby's replacement used a
low base.

Two things the byte comparison *does* fix that were otherwise free:

* **`TREESEARCH` is a `.FUNC`, not a `.PROC`.** The four bare `PLA`s after
  the return address are the two words the caller pushes for a function
  result (1.3 manual, `.FUNC`), and the result is pushed back at `GOBACK`.
  Written as a `.PROC` the routine would have four bytes fewer and every
  relocation offset would shift, which is what mutation 5 shows.
* **The zero-page maps of the two routines overlap on purpose.**
  `IDSEARCH` puts its return address at `$7E`, which is `TREESEARCH`'s
  `NODEPTR`; they are never active at once. So they are two independent
  maps of one region, not one shared layout, and the source declares them
  separately.

### 45c. This is the fast tier, not acceptance

`tools/asm6502.py` is a minimal assembler for exactly the subset these two
routines use, written for this check; it raises on anything else. It is
*not* the authority. **The acceptance test is Apple's own
`SYSTEM.ASSMBLER`**, which is on both evidence disks — it is the program
that generated these relocation tables in 1985, and running the
reconstruction through it under the emulator is what finally settles the
native half. What this probe rules out is the whole class of errors that
would fail there too, in a second and with no emulator, and it is wired
into `build_all.py` so a regression is visible rather than silent.

## 46. The global area was two words short, and `DISKBUF` says so

*Confidence: VERIFIED BINARY FACT, measured over all 287 procedures.
`tools/probes/probe_frame_size.py`, 22 checks.*

The global map has been reporting "Words accounted for by inferred objects:
1225 of 1222" since finding 10, and that overshoot was treated as rounding
in the object inference. It was not. The area was wrong.

### 46a. A frame is PARAM SIZE plus DATA SIZE

A UCSD activation record holds the block's parameters and its locals in
**one offset space beginning at 1**, and the attribute table's `DATA SIZE`
word counts only the locals. So the highest valid offset is

```
    (PARAM SIZE + DATA SIZE) / 2
```

This is a claim about every procedure, so it is measured rather than
argued. Over the 114 procedures in 1.1 that touch a local at all:

| | `DATA SIZE`/2 | `(PARAM+DATA)`/2 |
|---|---|---|
| exceeded by some offset | **68** | **0** |
| reached exactly | — | **105** |

Never exceeded *and* reached exactly by 105 of 114 is what makes it the
frame rather than merely an upper bound: a bound nothing reaches could be
any large number. The nine that fall short each end in an aggregate whose
interior words are never addressed individually; the largest gap, 256
words, is a disk buffer. 1.3 gives the same picture: 0 over, 108 of 117
exact.

### 46b. What it fixes in the global map

The outer block declares 4 bytes of parameters, so the global area is two
words larger than reported: **1224 words in 1.1 and 1357 in 1.3**, offsets
1..N. Two things fall into place that had not:

* **`DISKBUF` is 256 words — a 512-byte disk block — in both releases.**
  In 1.1 it starts at 969 and runs to 1224, the last word of the frame. In
  1.3 it starts at 1099 and the next touched offset is 1355, again exactly
  256 words later. Under the old area it came out at 253 in 1.1, which is
  not a sensible size for a buffer that is `BLOCKREAD` into.
* **1.3's three added globals are inside the frame, not past it.**
  `HAS128K`, `CONLIST` and `LSTOPEN` at 1355, 1356 and 1357 were three
  words *beyond* a 1355-word area, which would have meant the compiler
  writing over its own caller's stack. 1357 is now the last word.

The growth ledger of finding 40 is unaffected: 1357 − 1224 = 133, the same
number, and its seven entries still sum to it. Only the two endpoints move.

### 46c. Globals 1 and 2 are the outer block's parameters

The 4 bytes of parameters are not a formality — offsets 1 and 2 are both
touched, and the map has always had them as `scalar-byref`, addresses taken
only to be passed to `NEW`. So the compiler's two lowest globals occupy the
words a caller would have pushed. What pushed them, and whether Apple's
source declares them as parameters of the program block or the p-machine
simply reserves them, is not settled here.

### 46d. The lesson, which is the same one as finding 43

A total that does not balance is evidence, not noise. "1225 of 1222" was
printed at the top of the global map for thirty-odd findings and read as an
artifact of the object inference every time, because the inference really
does over-count elsewhere — the record at offset 3 has its five words
counted again as four separately addressed fields, which is a genuine +4.
Two overlapping explanations, one of them wrong, and the wrong one was
never separated out because the number was never required to come out
exactly. It is now: the probe demands zero procedures over the bound.

## 47. The full disk sets: `{$U-}` observed, with its source, and why APPLE0 is excluded

*Confidence: VERIFIED BINARY FACT throughout; the `{$U-}` mapping is also a
VERIFIED SOURCE FACT, from the manual and from `HAZELGOTO.TEXT`.
`tools/probes/probe_disk_copies.py`, 14748 checks over 6 images, 39
codefiles and 1490 procedures.*

`evidence/disks/` now holds both complete three-disk sets:

| | 1.1 | 1.3 | contents |
|---|---|---|---|
| **APPLE1** | `UCSD Pascal 1.1_1.dsk` | `680-0283-A` | boot: `SYSTEM.APPLE` (the 6502 interpreter), `SYSTEM.PASCAL`, `EDITOR`, `FILER`, `LIBRARY` |
| **APPLE2** | `680-0005-01` | `680-0284-A` | second drive: `SYSTEM.COMPILER`, `LINKER`, `ASSMBLER` |
| **APPLE3** | `UCSD Pascal 1.1_3.dsk` | `680-0290-A` | utilities and examples, plus a second `SYSTEM.APPLE` |

APPLE1 boots and APPLE2 goes in the second drive; that is also the
configuration the compiler needs (finding 15). **The APPLE0 images are not
used.** They are a merged subset, and 1.3's is a positive reason to leave
it out — see 47c.

### 47a. `{$U-}` produces lex level −1, and the source says so

Section 16 carried this as inferred and never seen. It is now both
observed and read in Pascal.

The lex-level byte is `$FF` on **7 of the 39 codefiles**, and on the outer
block in every case:

```
  SYSTEM.PASCAL     1.1 and 1.3   the operating system
  128K.PASCAL       1.3           its 128K variant
  SETUP.CODE        1.1 and 1.3   the reconfiguration utility
  SOROCGOTO.CODE    1.1           a GOTOXY replacement
  HAZELGOTO.CODE    1.1           a GOTOXY replacement
```

The two `GOTOXY` files are the decisive ones, because the manual says how
they were built and their **source is on the same disk**. Part I ch. 12,
"Changing GOTOXY Communication":

> `(*$U-*)` should be the first thing in the GOTOXY file

and `HAZELGOTO.TEXT`, all 23 lines of it, begins:

```pascal
(*$U-*)
PROGRAM GOXY;

PROCEDURE FGOTOXY(X,Y:INTEGER);
...
BEGIN (* DUMMY MAIN *)
END.
```

`HAZELGOTO.CODE` has one segment, `GOXY`, whose procedure 1 carries
`lex = -1`. Directive in, lex level out, with nothing in between to
misread.

The other 32 codefiles do not have it — **`SYSTEM.COMPILER` included, in
both releases**. Finding 24e reached that conclusion against Neil Parker
by absence; it now has a positive control, which is what it was missing.
Finding 23c's directive list stands: the reconstruction does not carry
`{$U-}`.

Worth noting what `lex = -1` is *not*: it is not a property of every
procedure in a `{$U-}` program. Exactly one procedure per such codefile
has it, and it is always the outer block.

### 47b. A source-and-binary pair, which the project did not have

`HAZELGOTO.TEXT` and `HAZELGOTO.CODE` are the same program in both forms,
compiled by the compiler being reconstructed. It is 23 lines and two
procedures — far too small to prove anything about the compiler at large,
and exactly the right size for calibrating the validation loop before
pointing it at 40 kilobytes. Task 7 should start here: it is the one place
on the disks where a p-code listing can be read against the Pascal that
produced it, and any pipeline that cannot reproduce `HAZELGOTO.CODE` from
`HAZELGOTO.TEXT` is not ready for `SYSTEM.COMPILER`.

`SYSTEM.PASCAL` is the larger version of the same opportunity — the II.0
operating system, whose source is already in `reference_source/ucsd_ii0/`.
Neither is used yet.

### 47c. Why APPLE0 is excluded: seven corrupt bytes the sweep cannot see

1.3's APPLE0 image also carries a `SYSTEM.COMPILER`, the same length as
APPLE2's, differing in **seven bytes** inside `BODY3.1`:

```
  APPLE2 (the artifact of record)     APPLE0
  0335 a9 50   LDO 80                 0335 dd      SLDL 6
  0337 01      SLDC 1                 0336 24      SLDC 36
  0338 95      SBI                    0337 75      SLDC 117
  0339 cd 01 16 CXP 1,22              0338 e1      SLDL 10
                                      0339 b9 75   UJP $03B0
                                      033B 62      SLDC 98
```

`LDO 80; SLDC 1; SBI; CXP 1,22` is ordinary code — "emit(global 80 − 1)"
through `PASCALCO.22`, the same call three instructions earlier. The
APPLE0 bytes mean nothing and merely re-synchronise at `$033C`.

"Merely re-synchronise" is the point, and it is the reason this finding
exists. **The linear sweep that validates all 287 procedures cannot see
this.** Both copies sweep from `enter_ic` and land exactly on `exit_ic`,
because seven bytes were replaced by seven bytes. The 287/287 result is
worth nothing here — the same trap finding 7 recorded, in a new place.

What sees it is a check the damage cannot survive: **every branch target
must land on the first byte of a decoded instruction inside its own
procedure.** Jump targets do not re-synchronise. Over the six disks in the
set, 1490 procedures, it fails nowhere; on the excluded APPLE0 image it
fails once, on a `UJP` to `$03B0` when `JTAB` is at `$037E` — past the
procedure's own attribute table, which cannot be code the compiler emitted.

Nothing established needs revisiting: `BODY3.1` was read from the APPLE2
copy throughout. 1.1's `SYSTEM.COMPILER` is byte-identical on its APPLE2
disk and on the 1.1 APPLE0 image, so the same question does not arise
there.

## 48. 1.1's reserved-word table is in the interpreter, and it dates the `SYMBOL` enumeration

*Confidence: VERIFIED BINARY FACT.
`tools/probes/probe_interp_words.py`, 57 checks.*

Finding 19 said that in 1.1 `IDSEARCH` and `TREESEARCH` are `CSP 7` and
`CSP 8` — standard procedures implemented *in the interpreter* — and that
1.3 dropped them and hand-coded the pair into `SYSTEM.COMPILER`. The
compiler side of that was solid. The interpreter side was untested,
because no interpreter was in `evidence/`. Now both are.

`SYSTEM.APPLE` is a raw 16384-byte 6502 image that loads at `$D000`, and
it is the same file on APPLE1 and APPLE3 within each release.

### 48a. The prediction, and it holds

**1.1's `SYSTEM.APPLE` contains the reserved-word table; 1.3's contains no
part of it.** The table is plain ASCII, so this fails loudly in either
direction, and it is the first direct evidence for the half of finding 19
that the compiler alone could not reach.

1.1's table sits at **`$DE2C..$DFFA`**, with its 26-word letter index just
below at `$DDF5` and the empty-letter sentinel at `$DE29`. The same seven
letters share the sentinel — H J K Q X Y Z.

### 48b. Apple compacted the format when they moved it

The record layouts differ:

```
  1.1 (interpreter)   [count-or-0][NAME 8][SY][OP]        11 bytes each,
                      the count on the first record of a letter, 0 on the rest
  1.3 (compiler)      [count] then [NAME 8][SY][OP]       1 + 10 bytes each
```

The eleven-byte stride is not a reading imposed on the bytes: the 26-entry
index has to tile the table exactly, and it does under eleven and not
under ten. 1.3 saved one byte per record — 42 bytes — by hoisting the
count out of the records, which is the kind of economy a routine written
to fit inside a compiler segment would want and one living in a 16K
interpreter would not bother with.

### 48c. The symbol codes are unchanged, and 1.1 now says so itself

Both tables hold **42 reserved words**. All 41 in common carry **identical
`SY` and `OP`** — zero disagreements. `SYMBOL` and `OPERATOR` (finding 26)
were recovered from 1.3's table and carried back to 1.1 through the
correspondence table; 1.1's own binary now states them independently,
which removes the correspondence table from that argument entirely.

The one difference is the one finding 32 predicted from the II.0 source
before either table had been read this way:

```
  1.1  SEPARATE   SY = 54, OP = 0
  1.3  OTHERWIS   SY = 54, OP = 0
```

**1.3 reused the code rather than extending the enumeration.** So `SYMBOL`
has 55 members in both releases, and the reconstruction declares 55 either
way — with `SEPARATE` at 54 for a 1.1 target and `OTHERWISE` at 54 for
1.3. That is a one-identifier edit in the `TYPE` block and nothing else,
which is what makes the two releases' scanners the same program.

### 48d. Apple reordered five letters' lists

The words are the same but their order within a letter differs for D, F,
I, P and U:

```
  D   1.1  DIV, DO, DOWNTO            1.3  DO, DIV, DOWNTO
  F   1.1  FOR, FILE, FORWARD, FUNCTION   1.3  FOR, FUNCTION, FILE, FORWARD
  I   1.1  IF, IMPLEMEN, IN, INTERFAC 1.3  IF, IN, IMPLEMEN, INTERFAC
  P   1.1  PROCEDUR, PROGRAM, PACKED  1.3  PROCEDUR, PACKED, PROGRAM
  U   1.1  UNIT, UNTIL, USES          1.3  UNTIL, USES, UNIT
```

The search is a linear scan from the front of a letter's list, so order is
performance and nothing else — no `SY` moves. 1.3 puts `DO` ahead of
`DIV`, `IN` ahead of `IMPLEMENTATION` and `UNTIL` ahead of `UNIT`, which
is the more common word first in each case; that reads as a deliberate
reordering, but it is **STRONG INFERENCE at best** and the counter-example
is in the same table — `F` moves `FUNCTION` up past `FILE`.

What matters for the reconstruction is only that the order is *data*, laid
out by the assembler in the order the source lists it, so `src/native/`
must list 1.3's order and not 1.1's. It does.

## 49. The lifter, checked against Pascal Apple compiled

*Confidence: VERIFIED BINARY FACT compared against VERIFIED SOURCE FACT —
the source is on the same disk as the binary.
`tools/probes/probe_calibrate.py`, 42 checks, run by `tools/build_all.py`.*

Everything in this repo reads binaries and argues backwards. Nothing had
ever been held against source that Apple's compiler actually compiled,
because no source-and-binary pair was in `evidence/`. `HAZELGOTO` and
`SOROCGOTO` on the APPLE3 disks are two (finding 47b): 23 lines of Pascal
and a 1024-byte codefile each, the `GOTOXY` replacements the manual tells
users to write.

They are far too small to prove anything about the compiler at large. What
they do is **calibrate** — the decoder, the stack model, the expression
reconstruction and the structuriser all run end to end against an answer
key, and any disagreement is a defect here rather than a question about
Apple.

### 49a. The result

`HAZELGOTO.TEXT`:

```pascal
PROCEDURE FGOTOXY(X,Y:INTEGER);
VAR SEND: PACKED ARRAY[0..3] OF 0..255;
BEGIN
  IF X>79 THEN X:=79
  ELSE IF X<0 THEN X:=0;
  IF Y>23 THEN Y:=23
  ELSE IF Y<0 THEN Y:=0;
  SEND[0]:=126; (* LEAD-IN *)
  SEND[1]:=17;  (* DC1 *)
  IF X<30 THEN SEND[2]:=X+96
           ELSE SEND[2]:=X;
  SEND[3]:=Y+96;
  UNITWRITE(2,SEND,4);
END;
```

`HAZELGOTO.CODE`, lifted and structured by this repo, with the offsets
named as 49b predicts:

```pascal
  if (X > 79) then begin X := 79;
  end else begin if (X < 0) then begin X := 0; end; end;
  if (Y > 23) then begin Y := 23;
  end else begin if (Y < 0) then begin Y := 0; end; end;
  SEND[0] := 126;
  SEND[1] := 17;
  if (X < 30) then begin SEND[2] := (X+96);
  end else begin SEND[2] := X; end;
  SEND[3] := (Y+96);
  UNITWRITE(2, @SEND, 0, 4, 0, 0);
```

Statement for statement, condition for condition, in order, with **zero
gotos**. `SOROCGOTO` likewise, including `SEND[1] := ORD('=')` arriving as
`61` and `SEND[2] := 32+Y` keeping its operand order rather than being
normalised to `Y+32`.

The probe does not compare prose. It extracts from *both* texts, by the
same rules, the ordered sequence of conditions, of assignment targets, of
right-hand sides and of integer literals, and requires all four to be
equal. The source side is read off the disk, not written into the probe.

### 49b. The layout is *predicted*, not fitted

The name map used for that comparison is not read out of the binary. It is
derived beforehand from two rules established elsewhere:

* parameters occupy the low offsets and locals follow, in one space
  starting at 1 (finding 46);
* a declaration allocates its identifiers **backwards** (finding 33).

`PROCEDURE FGOTOXY(X,Y:INTEGER)` with a local `SEND` therefore gives
`Y` = 1, `X` = 2, `SEND` = 3. That is what the binary has — the offset
compared against 79 is 2, the one compared against 23 is 1, and the only
offset whose address is taken is 3 — and if either rule were wrong the
whole statement comparison would fail rather than quietly re-fit. Swapping
the predicted `X` and `Y` is one of the mutations, and it fails on the
first condition.

Finding 33 was recovered from `VARDECLARATION`'s own code and had only ever
been tested on `VAR` blocks. This is the first time it has been checked on
**parameters**, and against a declaration rather than against another
inference. Finding 46's frame model gets the same treatment: `PARAM SIZE`
is 4 and `DATA SIZE` is 4, so the frame is 4 words, and 4 is exactly the
highest offset the code touches.

### 49c. `UNITWRITE`'s arity, checked against a declaration for once

The 41 standard-procedure stack effects in `CSP_EFFECT` were fixed by
finding 17 from interpreter source and by balance-fitting across the
compiler's call sites. Here one of them is checked against a *call written
in Pascal*.

The source says `UNITWRITE(2,SEND,4)` — three arguments. `CSP_EFFECT[6]`
says six words. The emitted call is

```
  UNITWRITE(2, @SEND, 0, 4, 0, 0)
```

— the unit number, then `SEND` as an **address/offset pair**, then the
length, then the two arguments the declaration defaults. Six words, and
each one accounted for. Dropping the table entry to five is the second
mutation, and it fails four ways.

That it had to come from outside the compiler is the point.
`probe_csp_check.py` scores every CSP arity against the compiler's own call
sites, and its verdict on this one is `margin +0 -- tie with (0, 0), binary
gives no signal`: `SYSTEM.COMPILER` calls `UNITWRITE` exactly once, and one
call site cannot separate a six-word effect from a zero-word one. The
GOTOXY samples settle in one line what 40 kilobytes of compiler could not
say at all. Seven more entries carry the same verdict, and four are
recorded as CONTRADICTED — those are the ones a second source would be
worth most on.

### 49d. Two defects it found

Neither is in a conclusion; both are in the tooling, which is what a
calibration run is for.

* **The lifter applied `SYSTEM.COMPILER`'s recovered global names to a
  foreign codefile.** `X`, `Y` and `SEND` came out as `CODEP`, `SYMBUFP`
  and `GATTYPTR`. Harmless while the only input was the compiler, and
  actively misleading the moment it was not. `lift()` now documents that
  `release` selects the name tables and that `""` means none, and the probe
  passes `""`.
* **A procedure whose body is `BEGIN END` was flagged inconsistent.** The
  attribute-table check required `enter_ic < exit_ic`, but an empty body
  compiles to nothing at all and the two are equal. Both samples' dummy
  main is exactly that, and their source says so. Relaxed to `<=`. It
  affects **33 procedures across the six disks** — none in
  `SYSTEM.COMPILER`, so nothing established changes, but the reader was
  wrong about a third of `SETUP.CODE`'s segment procedures and most of
  `SYSTEM.LIBRARY`'s.

The listings also gained something in passing: `CSP n` calls now render by
name, so `CSP2(...)` reads `MOVELEFT(...)` and `CSP6(...)` `UNITWRITE(...)`
throughout both compiler listings.

### 49e. What this does and does not license

It licenses the pipeline: two whole procedures in, two whole procedures
out, exact. It does not license any *naming* in `SYSTEM.COMPILER`, and it
says nothing about the constructs these samples do not use — no loops, no
`case`, no sets, no calls between procedures, no `with`, no records. The
next calibration target is `SYSTEM.PASCAL`, whose source is already in
`reference_source/ucsd_ii0/`; it is a hundred times the size and exercises
all of them. It would not parse when this was written; **finding 50 fixes
that**, and it now lifts.

## 50. `SYSTEM.PASCAL`'s segment 0 is stored in two pieces, and one dictionary spans both

The operating system's `PASCALSY` would not parse: it claims 57 or 58
procedures and only 28, 32 or 16 of the dictionary pointers landed anywhere
inside it, and every build carried an unnamed slot 15 with `SEGINFO` 0 whose
size looked like the complement of slot 0's. That was recorded in section 16
as a blocker, and it was the wrong shape of question. Slot 15 is not a
segment that failed to parse. It is the rest of segment 0.

### 50a. The measurement that settles it

VERIFIED BINARY FACT. Slot 0 and slot 15 are physically adjacent in every
build, and together they tile the file exactly up to the first ordinary
segment:

| | slot 0 `PASCALSY` | slot 15 | procedures |
|---|---|---|---|
| 1.1 `SYSTEM.PASCAL` | blocks 1..7, 3150 bytes | blocks 8..14, 4226 | 57 |
| 1.3 `SYSTEM.PASCAL` | blocks 1..7, 3158 | blocks 8..14, 3360 | 58 |
| 1.3 `128K.PASCAL` | blocks 1..3, 1438 | blocks 4..13, 5080 | 58 |

There is exactly one procedure dictionary and it sits at the end of slot 0,
where the layout in section 1 says it should: `2 + 2n` bytes, 116 in 1.1 and
118 in both 1.3 builds, immediately above the last JTAB in that piece. Slot
15 has **no** dictionary — its last word *is* a JTAB. That is what makes it a
piece rather than a segment, and it is the check that distinguishes the two.

The dictionary entries fall into two groups. Those whose target lies in slot
0 are ordinary self-relative pointers and always were. Those whose target
lies in slot 15 are ordinary self-relative pointers too, but they resolve
short by a constant, because the loader places the two pieces far apart:

    target = (at - v) + S       S = 21396 (1.1), 20522 (1.3), 21046 (128K)

`S` is not fitted. It is forced, by one line: the highest crossing pointer
must land on slot 15's last word, because slot 15 ends on a JTAB. One number
per file comes out of that requirement, and then everything else follows
without a further choice:

* all 57, 58 and 58 entries land on a byte holding **their own procedure
  number** — 29 + 26 + 42 = 97 crossing entries, no exceptions;
* the procedures tile **both** pieces with no gap and no overlap;
* every one passes the ordinary attribute check — `enter <= exit <= JTAB`,
  parameter and data sizes even, lex level in range;
* slot 0's leftover is exactly the dictionary and slot 15's is exactly zero.

`probe_split_segment.py` makes all of that gating: 871 checks. It also
sweeps the other 36 codefiles across the six evidence disks and requires
that **none** of them is joined and that all still parse, and it corrupts one
crossing pointer per build and requires the join to refuse. It does refuse —
flipping a single bit makes the reader decline the whole segment rather than
settle on some other constant that happens to fit, which is the failure mode
worth guarding against.

### 50b. The split is packing, not truncation

VERIFIED BINARY FACT, and it rules out the obvious alternative reading. If
the file had simply been cut in half, the pieces would hold contiguous runs
of procedure numbers. 1.1's does — 1..28 in slot 0, 29..57 in slot 15 — but
1.3's does not:

    1.3 SYSTEM.PASCAL   slot 0: 1-30, 32, 34      slot 15: 31, 33, 35-58
    1.3 128K.PASCAL     slot 0: 1-12, 14-16, 19   slot 15: 13, 17-18, 20-58

Procedures 32 and 34 stayed behind while 31 and 33 moved, and 128K's split is
interleaved throughout. Something filled slot 0 up to a block boundary and
sent the remainder across — a build step choosing what fits, not a cut.

That also explains the measurement recorded in section 16 as suggestive: 1.3's
`SYSTEM.PASCAL` and `128K.PASCAL` really do hold the same 6518 bytes of
segment 0, split at different points. They are two memory maps of one system,
and the different split is the point of the two files rather than a puzzle
about them. Their `S` values differ accordingly.

### 50c. What is *not* claimed

`S` is a difference of load addresses, and this does not identify them.
Written as one, the last byte of slot 0's piece sits 16736 ($4160) bytes
above the last byte of slot 15's in both `SYSTEM.PASCAL` builds and 15868
($3DFC) in `128K.PASCAL` — the same for the two files that share a memory map
and different for the one that does not, which is consistent, but no absolute
address is recovered here and none is needed. SPECULATION, flagged as such
and not relied on anywhere: the separation is about the right size for one
piece to live in the language card and the other in main RAM, which would
also explain why the 128K build moves the boundary. The reader does not
depend on it.

The reader represents the join as a sparse image with the two pieces at the
separation the pointers imply, because that is the only geometry in which the
plain `target = at - v` rule holds throughout; `Segment.in_chunk` says which
bytes are real, and nothing walks the padding. The padding is this reader's
invention and is not evidence of anything having been there.

### 50d. What it unblocks

`SYSTEM.PASCAL` now parses completely — 105 procedures in 1.1's, 111 in
1.3's, zero inconsistent — and lifts. Segment 0 procedure 33 of 1.3 comes out
as the filename parser: upcase, strip blanks, then the `*`, `%`, `:` and `[`
cases, with `SPOS`, `SCOPY` and `SDELETE` named and the call into `FILEPROC`
resolved across segments. That is the calibration target finding 49e asked
for and could not have — loops, nested conditionals, string intrinsics,
inter-segment calls — against source that is already in
`reference_source/ucsd_ii0/`. Finding 8 still applies: that source is the
*generic* UCSD II.0 operating system and Apple's is not, so this will be a
close comparison rather than the exact one the GOTOXY samples allowed.

## 51. Apple's segment 0 against UCSD's declarations: the numbering holds to 42, and two overrides dissolve

Finding 50 made `SYSTEM.PASCAL` parse. The first thing worth doing with it
is the comparison that was impossible before: UCSD II.0's `GLOBALS.TEXT`
forward-declares segment 0's procedures in order, and Apple's binary states
every one of their parameter sizes in its own attribute tables. Two
independent lists of the same thing.

### 51a. They agree through 42

VERIFIED BINARY FACT against VERIFIED SOURCE FACT. For procedures 1..42 the
declared name order, the parameter word count and the procedure-versus-
function kind all match, in 1.1's `SYSTEM.PASCAL`, in 1.3's, and in
`128K.PASCAL` -- 3 builds x 42 procedures, no exceptions. `probe_os_signatures.py`
gates it: 392 checks.

That extends the *verified* segment-0 numbering from 29 to 42. Finding 18
had it to 29, against Peter Miller's table; this reaches further and comes
from a different direction, so the two do not share a failure mode.

One adjustment is needed before the lists are comparable, and it is the same
one finding 46 established for the compiler's own frames: **a UCSD activation
record carries the two-word function result slot inside the parameter area**,
so a declared argument count of *n* is a frame of *n* + 2. Ten of the 43 are
functions, and all ten come out exactly right under that rule and exactly two
words short without it. That is ten independent confirmations of the result
slot from a source that knew nothing about it.

### 51b. `FBLOCKIO` was right for the wrong reason, and `FOPEN` was wrong

`OS_WORD_OVERRIDE` held two entries, both inferred from counting words at the
compiler's call sites because there was nothing better. The binary settles
both, and the table is now empty.

* **`FBLOCKIO`**, overridden from the declared 6 to 8 "by a margin of 20".
  The binary says 8, so the number was right -- but the reason recorded with
  it was not. Apple did not extend `FBLOCKIO`. It is a function, and 6
  declared arguments plus the result slot *is* a frame of 8. What was a
  special case for the one routine whose call sites happened to be countable
  is now a rule covering all ten.
* **`FOPEN`**, overridden from the declared 4 to 7 "with a margin of 4".
  It is 4. Three readings agree and the override has none of them: Apple's
  attribute table says 4 in both releases; the call sites push four words when
  read by hand -- `UNITPART.2` pushes `LAO 665`, the address of the string
  literal, `SLDC 0`, `SLDC 0`, which is exactly `VAR F`, `VAR FTITLE`,
  `FOPENOLD`, `JUNK`; and lifting the entire compiler with 4 gives output
  identical to lifting it with 7, byte for byte, 142/142 and 145/145 with the
  stack fully tracked either way. So the margin never discriminated anything.
  It is removed.

The lesson is worth keeping separately from the fix: a scoring probe that
reports a margin is reporting how its own objective ranks the candidates, not
how much evidence there is. Both overrides scored well. One was right by
coincidence and one was wrong.

### 51c. Where it parts company: procedure 43 is not `COMMAND`

VERIFIED BINARY FACT. `GLOBALS.TEXT`'s 43rd forward declaration is
`PROCEDURE COMMAND;`, which takes no parameters. Apple's procedure 43 takes
three words, in all three builds, and the compiler's five call sites each
push exactly three -- an address, then `SLDC 1`, then `SLDC 40` or `SLDC 80`:

    COMPINIT.1   LLA 259  SLDC 1  SLDC 80   CXP 0,43
    COMPOPTI.1   LLA 7    SLDC 1  SLDC 40   CXP 0,43

So the identification is refuted, not merely unproven, and the caution that
used to sit in `OS_WORD_OVERRIDE` -- "proc 43's identity is an
extrapolation" -- was right to be there. The name is withheld: nothing here
recovers it, and the 40/80 argument suggests a console width rather than
anything `COMMAND` does. The probe requires 43 to keep disagreeing, because a
check that only confirms agreement would pass just as well on a table
someone had quietly aligned.

STRONG INFERENCE on the shape of the divergence: Apple's segment 0 has 57
procedures in 1.1 and 58 in 1.3 against II.0's 43, so 14 or 15 are Apple's
own. They begin at 43, not at 44, which means Apple inserted rather than
appended -- consistent with finding 8's picture of a fork that grew inside
the original rather than beside it.

### 51d. What it unblocks

The operating system now lifts almost completely: 96 of 97 procedures in
1.1, 104 of 105 in 1.3 and 110 of 111 in the 128K build come out with the
stack fully tracked, the single holdout in each being the one procedure
containing `XIT`, which legitimately ends tracking. `tools/liftos.py` writes
the listings. The compiler's own lift is unchanged by all of this -- 142/142,
145/145, 78 gotos, the same output as before -- which is the regression check
that matters, since `OS_SIG` feeds both.

## 52. The lifter checked against the operating system: loops and calls, 41 procedures

Finding 49 calibrated the whole pipeline against two 23-line GOTOXY programs
and was exact. It also said plainly what it did not cover: no loops, no calls
between procedures, no `with`, no records — the samples use none of them.
Finding 50 made `SYSTEM.PASCAL` parse and finding 51 aligned its segment 0
with UCSD II.0's declarations for procedures 1..42, so 41 procedures now have
source. This is that comparison.

It cannot be exact, and the reason is finding 8: the II.0 source is the
*generic* UCSD operating system and Apple's is a fork. An exact diff would
measure Apple's edits, not this repo's defects. So the probe checks two
properties that survive a fork, and — the part that makes it a check rather
than a statistic — requires the disagreements to be a **named list**, not a
count.

### 52a. Loops

VERIFIED SOURCE FACT against VERIFIED BINARY FACT. Every `WHILE`, `REPEAT`
and `FOR` in a body must become a back edge in the control-flow graph, and
nothing else may. Back edges are counted off `lift()`'s blocks *before* the
structuriser runs, so a loop the structuriser failed to render as `while`
would still be counted and could not hide.

    1.1   37 of 41 procedures agree exactly
    1.3   34 of 41

### 52b. Calls, and the built-in mapping that fell out of it

Every segment-0 routine a procedure calls must be admissible from its source
body — named there outright, or reachable through a standard identifier the
compiler lowers to one. Recovering that mapping was not the aim and is the
more useful half of the result:

| the source says | the binary calls |
|---|---|
| `COPY`, `DELETE`, `POS`, `CONCAT`, `INSERT` | `SCOPY`, `SDELETE`, `SPOS`, `SCONCAT`, `SINSERT` |
| `WRITE` | `FWRITESTRING` / `FWRITECHAR` / `FWRITEINT` / `FWRITEBYTES`, by argument type |
| `WRITELN` | the above, then `FWRITELN` |
| `READ`, `READLN` | `FREADCHAR` / `FREADINT` / `FREADSTRING`, then `FREADLN` |
| `EOF`, `EOLN` | `FEOF`, `FEOLN` |
| `RESET`, `REWRITE`, `CLOSE`, `GET`, `PUT`, `SEEK` | `FRESET`, `FOPEN`, `FCLOSE`, `FGET`, `FPUT`, `XSEEK` |
| `BLOCKREAD`, `BLOCKWRITE` | `FBLOCKIO` |

`SCANTITLE` is the clearest case: it calls `SCOPY`, `SDELETE` and `SPOS`, and
its source says `COPY`, `DELETE` and `POS`. With the mapping applied,

    1.1   39 of 41 procedures call only what their source admits
    1.3   38 of 41

Calls are read as `CBP` — the sibling call, 72 of them in segment 0 — and
`CXP 0,n`. `CLP` is the call *into a nested* procedure, and there are eight:
`EXECERROR` issues `CLP 52`, which is the lex-1 procedure 52, exactly as II.0
nests `PRINTLOCS` inside `EXECERROR`.

### 52c. Why the subset test is not vacuous

A "calls only what the source admits" check gets weaker the looser the alias
table is, and at the limit it passes on anything. So the probe measures its
own discriminating power: every procedure's binary call set is tried against
every *other* procedure's source body, and it fails if too many of those wrong
pairings are admitted. Measured, **7.3% in 1.1 and 7.5% in 1.3**, against a
15% ceiling. Loosening `ALIAS` into a rubber stamp would raise that number
and stop the probe passing, which is the property worth having.

### 52d. The two measures agree about Apple

They are independent — one is control flow, one is naming — and they point
at the same procedures.

* **`EXECERROR`** and **`CLEARLINE`** are flagged by both, in both releases.
  `CLEARLINE` is the legible one: II.0's is a single call to `PUTPREFIXED`,
  which is not one of the 43, and Apple's writes directly and carries
  `PUTPREFIXED`'s loop — Apple inlined it.
* **`FWRITESTRING`** is flagged by both in 1.3 and by neither in 1.1: Apple
  moved its loop into `FWRITEBYTES` between releases, which shows up as
  `FWRITESTRING` losing a back edge, `FWRITEBYTES` gaining one, and
  `FWRITESTRING` calling `FWRITEBYTES`.
* 1.1 differs from II.0 in fewer places than 1.3 does, by both measures.
  That is the direction a fork accumulating changes predicts, and nothing in
  the probe arranges it.

### 52e. What this licenses, and what it still does not

It licenses loop recovery, the call graph within a segment, and the
built-in-to-segment-0 mapping above, across 41 procedures written by someone
else. Together with finding 49 the pipeline is now checked against source on
assignments, conditions, nested `if`, `while`, `repeat`, `for`, sibling calls,
nested calls and cross-segment calls.

It does not check `case`. Segment 0's 41 aligned procedures contain not a
single `CASE` statement, so this probe cannot reach one — but the construct
itself is recognised, and the reachable target is one segment over. Finding 41
did not leave `case` unrecognised; it *fixed* the recogniser, by keying on the
`UJP` that reaches the table rather than expecting the table first. 50 of 54
in the compiler come out as `case` statements, and the operating system lifts
six more, one of which is `PRINTERROR`'s 16-arm table of error messages —
with UCSD's source for it sitting in `SYSSEGS.A.TEXT`. That is the next check
to write, and it is cheap.

`with` and records are the real gap. The II.0 source uses `WITH` constantly
and segment 0 is full of record field access, but both measures here are blind
to it: a `with` generates no control flow and no call. Checking it needs a
third measure — field offsets, which the II.0 type declarations fix
independently of anything in the binary.

## 53. `case` against source: 31 error messages recovered from p-code, unchanged

Finding 52 could not reach a `case` — segment 0 does not contain one — and
finding 52e named `PRINTERROR` as the cheap next target. This is it.

`PRINTERROR` is slot 3 of the same `SYSTEM.PASCAL`, and UCSD's source for it
is 45 lines of `SYSSEGS.A.TEXT`. It is a 15-arm `CASE` on the execution error
code, with a second 19-arm `CASE` on `IORESULT` nested inside arm 10, and
every arm does one thing: assign a string literal. That makes the strings an
answer key, which is what a `case` check normally lacks. A jump table read one
off, an arm attributed to the neighbouring label, or an `LSA` mis-sized would
all show up as a message landing on the wrong error *number*, and error
numbers are not interchangeable.

### 53a. The result

VERIFIED BINARY FACT against VERIFIED SOURCE FACT.

    1.1   15 + 17 arms, 31 of them carrying UCSD's message character for character
    1.3   16 + 19 arms, 21 of them carrying UCSD's message character for character

The structure matches exactly in both: the default `S := 'Unknown run-time
error'` before the case, all fifteen of II.0's outer labels present, the
second table nested inside arm 10 and nowhere else, zero gotos.

Most of the non-identical arms are Apple spelling the same message out —

| II.0 | Apple |
|---|---|
| `'No proc in seg-table'` | `'No procedure in segment-table'` |
| `'Exit from uncalled proc'` | `'Exit from uncalled procedure'` |
| `'dup dir entry'` | `'duplicate directory entry'` |
| `'file lost in dir'` | `'file lost in directory'` |
| `'illegal unit #'` | `'illegal volume #'` |

— which is Apple's house style showing through, not a decoding question. The
probe requires a reworded arm to share at least one word with UCSD's, so a
message that had genuinely moved to another error number would still fail.

### 53b. Apple's real departures

Held as a named list per release, and each must *stay* a departure:

* **1.3 only:** outer label 16 and inner label 20 are Apple's own; inner 19
  is redefined from `'bad init record'` to `'must read a multiple of 512
  bytes'`, which is a Disk II constraint that generic UCSD had no reason to
  have.
* **Both:** inner 15, II.0's `'ring buffer overflow'`, is absent. Inner 18 is
  redefined from `'bad byte count'` to `'illegal buffer address'`.
* 1.1 lacks inner 19 as well, and adds nothing at all.

1.1 is again nearer to II.0 than 1.3 — 31 identical arms against 21, no
additions against two — the same direction finding 52d measured by two other
means entirely.

### 53c. What it licenses

`XJP` and the whole `case` path, end to end, on a nested table: the jump table
that follows its arms (finding 41), the arm-to-label attribution, `LSA` string
literals of 12 different lengths, and the structuriser's rendering, all
against source someone else wrote. Sets, `with` and records remain unchecked
against any source.


## 54. UCSD's record declarations, laid out and checked against the binary

A type declaration is a claim about code bytes. Every field access carries an
offset, so a record declared one word wrong moves every field after it and
changes what the compiler emits. Finding 22c read seven record sizes straight
out of `SYSTEM.COMPILER` without knowing what the fields were; the UCSD II.0
compiler source declares them. `tools/a2pascal/reclayout.py` lays UCSD Pascal
declarations out in words — packed char arrays two to the word, one word for
a named variant tag and none for an anonymous `CASE BOOLEAN OF`, a variant
record having one size per variant rather than one size — and
`probe_record_layout.py` holds the results against the binary.

### 54a. Three records that match with nothing adjusted

VERIFIED SOURCE FACT sized, against VERIFIED BINARY FACT.

| | laid out | the binary |
|---|---|---|
| `ATTR` | 5 words | `GATTR` is 5 (finding 43, `varblock.py`) |
| `STRUCTURE` | 9 words | "all nine words of the standard descriptor" (22c) |
| `ALPHA` | 4 words | the eight-character name at words 0..3 of an `identifier` (22c) |

None of the three was fitted. `STRUCTURE` is the satisfying one: finding 22c
got nine words by watching `DECLARAT`'s `STRING[n]` handler `MOV` a
descriptor, and the declaration comes to nine by arithmetic over fields that
finding knew nothing about.

### 54b. `identifier`, and the two fields Apple does not have

> **RETRACTED by finding 76.** Both fields are there. The four sizes below
> are what a *tagged* `NEW` allocates, not what the record measures, and
> `WRITELIN` reads `PUBLIC` at its declared offset in both releases. What
> follows is left as written because the reasoning it records -- a size
> agreeing with a deletion -- is the mistake worth keeping legible.

Finding 22c observed `klass` 0..6 with sizes **9, 10, 11, 11, 13, 18, 18**.
UCSD's declaration, laid out as written, gives

    TYPES KONST FORMALVARS ACTUALVARS FIELD PROC FUNC MODULE
      9    10       12         12      13    19   19    10

Three of the seven match immediately — `TYPES` 9, `KONST` 10, `FIELD` 13 —
and four are over by exactly one word. Removing two fields makes all seven
exact:

* **`PUBLIC`**, the whole of `CASE BOOLEAN OF TRUE: (PUBLIC: BOOLEAN)` at the
  end of the `FORMALVARS`/`ACTUALVARS` variant;
* **`IMPORTED`**, the whole of `CASE BOOLEAN OF TRUE: (IMPORTED: BOOLEAN)` at
  the end of the `DECLARED`/`ACTUAL` path of the `PROC`/`FUNC` variant.

With those two gone the layout is **9, 10, 11, 11, 13, 18, 18** — every
observed `klass`, exactly. The probe also requires that *neither removal alone*
suffices, so the pair is doing real work rather than one absorbing the other's
word.

The arithmetic is VERIFIED. The identification is **STRONG INFERENCE**, and
the reason it is strong rather than a fit: three of the seven sizes needed no
adjustment at all, and the two fields removed are the same construct twice —
a trailing anonymous-boolean extension bolted onto the end of a variant — and
both are UCSD *unit* features. Nothing else in the record has that shape.

What would settle it is offsets rather than sizes: if Apple lacks `IMPORTED`
the fields before it keep their offsets, and if it lacked some other word they
would all shift. The binary's own field accesses can decide that, and this
does not.

### 54c. Seventeen hand-derived sizes, now derived

`vardecl.py` carried a table of seventeen sizes the type name alone does not
give — `DISPLAY` 52, `SEGTABLE` 128, `SYSTEMLIB` 21, `DISKBUF` 256, the three
untyped `FILE`s at 40, `LP` at 301 — each worked out by hand and several
corroborated against Apple's own spacing between neighbouring offsets. **The
engine reproduces all seventeen**, with nothing tabulated, once three more
UCSD rules are in it:

* `STRING[n]` is `(n + 2) div 2` words — a length byte and the characters,
  packed two to the word. Finding 22c watched `DECLARAT`'s `STRING[n]`
  handler write exactly that into word 0 of the descriptor.
* an untyped `FILE` is `NILFILESIZE` = 40 words; `FILE OF T` is `FILESIZE` +
  the component, and `TEXT` is `FILESIZE + CHARSIZE` = 301. Finding 43.
* an inline `RECORD ... END` in the `VAR` block has to be *kept* rather than
  collapsed. `vardecl.py` had been replacing it with the token `AGGREGATE`,
  which is why `DISPLAY` and `SEGTABLE` could only ever be hand-sized: the
  only description of their elements was being thrown away before anything
  could read it.

`SIZES` and `BY_NAME` stay in the file, because the derivations written
against them are worth keeping, but they are now **assertions rather than
inputs** — `probe_record_layout.py` requires the engine to reproduce every
one, and `vardecl-ii0.txt` comes out byte-identical to before. The one place
they disagree is already documented and now visible rather than hidden:
`SEGTABLE` lays out at 128 words from II.0's eight-word entry, and Apple's is
144, because Apple's entry is nine words and is indexed `SEGTABLE[slot*9]`.

### 54d. `klass` 2, 3 and 4 now have names

Finding 22c named `klass` 0, 1, 5 and 6 and left the middle open; section 16
recorded "`klass` 3 and 4 both need one". The declaration order of `IDCLASS`
supplies them, and the sizes confirm the alignment rather than assuming it —
`FORMALVARS` and `ACTUALVARS` are 11 words *both*, which is why 22c saw
"11, 11" and could not separate them, and `FIELD` is the 13-word class 22c
singled out.

    0 TYPES   1 KONST   2 FORMALVARS   3 ACTUALVARS
    4 FIELD   5 PROC    6 FUNC         7 MODULE (never observed)

`MODULE` lays out at 10 words and does not occur in either binary, which is
consistent: it is the unit class, and the same two removals say Apple's fork
predates or drops UCSD's unit extensions.


## 55. The fast tier exists, and it reproduces Apple's p-code

Task 7's plan has always had two tiers: an acceptance test — Apple's own
compiler, in an emulator — and a fast tier that runs on the host in seconds.
The fast tier had never been built. It is Peter Miller's `ucsd-psystem-xc`,
and `thirdparty/ucsd-psystem-xc/build.sh` now builds it reproducibly.

The expectation recorded in `PLAN.md` was modest: *"This catches source that
does not compile or that compiles to visibly wrong structure."* It does much
better than that.

### 55a. Calibrated against Apple's own output

`evidence/` holds exactly two programs where the compiler's *input* and
*output* are both on the disk — `HAZELGOTO` and `SOROCGOTO`, the GOTOXY
replacements. Compiled with `ucsdpsys_compile -H apple` and read back with
this repo's own decoder:

| | segment length | p-code | segment bytes differing |
|---|---|---|---|
| `HAZELGOTO` | 112 = Apple's 112 | identical | 2 of 112 |
| `SOROCGOTO` | 100 = Apple's 100 | identical | 2 of 100 |

Identical means instruction for instruction, operand for operand, jump target
for jump target, and the same `PARAM SIZE`, `DATA SIZE` and lexical level on
every procedure. The four differing bytes are **one alignment byte per
procedure**, sitting past the `RBP` or `XIT` that ends it, where Apple writes
`0` and `ucsdpsys_compile` writes `$D7`, which is `NOP`. Nothing executes
them.

`probe_xcompile.py` gates all of that, and pins the padding by position *and*
value so that a new difference anywhere else fails and a padding byte that
stops differing fails too. It skips, loudly, when the toolchain is absent.

This is two programs of about sixty instructions each. It is not proof that
`ucsdpsys_compile` matches Apple everywhere, and where they disagree the
binary still wins. What it establishes is that the fast tier is worth
believing on the constructs those programs use — and that every future
comparison is itself another test of it.

### 55b. It compiles the reconstruction, and immediately found a defect

`analysis/reconstruction/skeleton-1.3.text` — `PROGRAM`, `CONST`, `TYPE` and
132 global declarations — **compiles**. That is the first time any
reconstructed Pascal in this repo has been through a compiler.

It came out two words too large, and finding the two words is the point:

    reconstruction   param 4   data 2714   frame 1359
    Apple 1.3        param 4   data 2710   frame 1357

Three measurements made with the new tool, all VERIFIED:

* `DATA SIZE` is exactly twice the declared global words, and `PARAM SIZE` is
  4 for any program main, declared parameters or not.
* Under `ucsdpsys_compile`, a program's declared globals start at offset
  **3**: `PROGRAM T; VAR A,B,C: INTEGER` compiles `A:=1; B:=2; C:=3` to
  `SRO 5; SRO 4; SRO 3`. (Which re-confirms finding 33 in passing — `A`,
  declared first, allocates highest.)
* `{$U-}` changes the kind of storage, not just the lexical level. The same
  program with `(*$U-*)` compiles to `STL 3; STL 2; STL 1` — the outer
  block's variables become *locals*, and `PARAM SIZE` is 0. That is why
  `HAZELGOTO`'s main has a zero frame.

### 55c. The two words: `SYMBUFP` and `CODEP` are parameters, not variables

The skeleton came out two words wide, and the fast tier settled it in three
runs. VERIFIED BINARY FACT throughout.

**Every Apple-compiled program starts its declared globals at offset 3.**
Twenty-one programs across the six disks, swept for the lowest global operand
any of them uses, and the answer is 3 every time. `LINEFEED.CODE` is the
clean case, because its source is on the same disk: `PROGRAM LINEFEED; VAR
CHEAT: TWOFACE;` — one variable, one word, `DATA SIZE` 2 — and it compiles to
`SRO 3`. Offsets 1 and 2 are the outer block's parameter area, which a UCSD
program main is given whatever its header says. `ucsdpsys_compile` does the
same thing, which is how this was noticed at all.

`SYSTEM.COMPILER` is the **only** program of the twenty-two that uses those
two words, and what it keeps there is not in doubt:

    COMPINIT.9   LAO 1 ; LDCI 512 ; CSP 1      NEW(SYMBUFP, 512)
    DECLARAT.1   LAO 2 ; LDCI 650 ; CSP 1      NEW(CODEP, 650)

512 is `SYMBUFARRAY`, `PACKED ARRAY [0..MAXCURSOR] OF CHAR` with `MAXCURSOR`
1023; 650 is `CODEARRAY` with `MAXCODE` 1299. Both to the word, and 1.3's
second call allocates 1000, giving `MAXCODE` = 1999.

So `SYMBUFP` and `CODEP` occupy the parameter words, and they are **not `VAR`
declarations**. `varblock.py` was writing them as declarations, which is
exactly the two words. Leaving them out and compiling gives:

    1.1   param 4  data 2444  frame 1224      Apple: param 4  data 2444  frame 1224
    1.3   param 4  data 2710  frame 1357      Apple: param 4  data 2710  frame 1357

Both releases, exactly. `probe_xcompile.py` requires it.

**Finding 46 is confirmed, not overturned.** Its reading — that the frame is
`(PARAM SIZE + DATA SIZE) / 2` and that "the outer block declares two words of
parameters" — is precisely right, and `DISKBUF` really does end on the last
word of the frame. What was wrong was only the reconstruction, which turned
those two parameter words into declarations.

Still open, and narrower than before: **how Apple's source names them.**
UCSD's program-parameter syntax is the obvious candidate and cannot be tested
here — `ucsdpsys_compile` rejects `PROGRAM T(A,B)` outright. The allocation is
settled; the spelling is not.

### 55d. What the fast tier is worth

It compiled the declarations, and in doing so validated them against the
binary more sharply than any amount of reading had: **the reconstructed `VAR`
block of both releases compiles to Apple's global frame to the byte.** That is
124 and 130 declarations, their types, their sizes and their order, checked
end to end through a real compiler against a real binary.

It also found the defect that made that possible. Thirty findings of reading
p-code had not caught two words in the wrong place; one compile did.

## 56. Writing Pascal volumes, and the 80-column limit that came with it

**VERIFIED BINARY FACT** for the format claims, **VERIFIED SOURCE FACT** for
the assembler's line limit, **STRONG INFERENCE** for the compiler's.

The acceptance tier needs the reconstruction on a disk Apple's own tools will
mount, and nothing here could write a Pascal volume -- only read one.
`tools/a2pascal/diskwrite.py` now writes them, and `mkworkdisk.py` produces
`build/disks/WORK.dsk` carrying `SEARCH.TEXT` and both declaration skeletons.
`probes/probe_diskwrite.py` gates it at 331 checks.

The format needed no reverse engineering; what needed care was proving the
encoder is Apple's and not merely self-consistent.

### 56a. The check that matters: Apple's own directories, re-encoded

The directory encoder is written as the exact inverse of the reader, and the
requirement is that **every evidence disk's four directory blocks come back
byte for byte from nothing but its parsed entries** -- 81 entries over six
volumes. That pins the name length byte and its padding, the file kind word,
`DLASTBYTE`, the date word, the volume entry's block and file counts, and the
26-byte stride, all against directories Apple built. A separate check
re-encodes with an empty template, so the original bytes cannot be leaking
through and doing the work.

Seven deliberate defects were each confirmed to break it: a transposed
interleave entry, a scrubbed name pad, an off-by-one `DLASTBYTE`, a
transposed day/month, an unsorted directory, a line split across a page, and
a dropped kind word.

### 56b. The residue in a directory entry is not a field

The first run failed on bytes 20-21 of every file entry. They are not a
field: bytes 6..21 are a Pascal `STRING[15]`, and the FILER's assignment
copies the length byte and the characters and leaves the rest of the buffer
alone. On all six disks the residue is the same two bytes, `24 67`,
right-aligned at 20-21 whatever the name's length -- one buffer, reused.

`DirEntry` now carries it so a rewritten directory reproduces it verbatim.
Scrubbing bytes we cannot explain is not the same as reproducing the volume,
and re-committing any evidence disk's directory now leaves all 143,360 bytes
unchanged.

### 56c. 80 columns, and where that is actually stated

Setting the disk up is what surfaced this. The generated skeleton had lines
of **266 characters and literal tabs**, inherited from the II.0 declarations,
and `ucsdpsys_compile` had accepted all of it without complaint.

* **The assembler states its limit.** Error 54 in the 1.3 manual's assembler
  error list is *"Input line over 80 characters"*. `SEARCH.TEXT` would have
  been rejected outright had it been over; it peaks at 60.
* **The Editor cannot show more than 79.** Past that it prints `!` in the
  last visible position and the rest of the line cannot be reached without
  reformatting the paragraph.
* **Nothing Apple shipped is over 80.** The longest line in any `.TEXT` on
  the six disks is 77 (`GRAFDEMO.TEXT`); the longest in the UCSD II.0 source
  is exactly 80.

Whether `SYSTEM.COMPILER` itself enforces 80 is **not established** -- the
compiler's error list has no counterpart to assembler error 54, and no line
on any disk is long enough to have tested it. What is established is that 80
is the width every surviving source was written to, so generated source is
held to it. `a2pascal/srcfmt.py` expands tabs and wraps at whitespace outside
strings and comments; both skeletons now fit, and `probe_xcompile.py`
confirms the reformatted source still compiles to Apple's exact frame, so the
wrapping provably did not change the program.

Also worth carrying: **a tab in a `.TEXT` is an anachronism.** UCSD stores
indentation as a DLE pair and there is no tab in any file on the six disks.
The two in the skeleton came from a modern editor by way of the II.0 source.

### 56d. A second opinion, and the defect it found

Everything above is this repo checking itself. `ucsd-psystem-fs` -- Peter
Miller's companion to the fast tier's compiler, and an independent
implementation of the same format -- was pointed at the disk this repo built.
`ucsdpsys_fsck` passes it exactly as it passes Apple's own volumes,
`ucsdpsys_disk --list` reports the volume, all three files, their sizes,
kinds and dates, and the free-space accounting, and its own idea of the
directory capacity agrees at 77 files.

It also found the one real defect the self-checks could not: **every file had
gained a blank line.** A host file's trailing newline terminates its last
line, but UCSD writes a CR after every line including the last, so passing it
through adds an empty one. The self-checks were blind to it because a string
that came out of `decode_text` never ends in a newline, so the round-trip
never exercised the case. The fix is at the caller and deliberately not in
`encode_text`: **ten of the 21 `.TEXT` files on the evidence disks genuinely
do end with a blank line**, and normalising it away would stop the encoder
being the reader's inverse.

With that fixed, all three files extract from the disk byte-identical to the
source they came from.

### 56e. What this does and does not establish

It establishes that the volume is well formed by two independent readers and
that its encoding matches Apple's own directories field for field. It does
not establish that Apple's FILER will mount it -- both implementations could
be wrong about the same thing in the same direction, and no amount of
agreement between them fixes that. That is the acceptance tier's question,
and it is now the only thing standing between the reconstruction and Apple's
own compiler.

## 57. The acceptance tier ran, and both tests passed

**VERIFIED BINARY FACT.** Apple II Pascal 1.3, under AppleWin, on the
reconstruction. This is the tier the whole project was built toward and it
had never been run.

### 57a. `SYSTEM.ASSMBLER` reproduces both native procedures, byte for byte

`src/native/SEARCH.TEXT` was assembled by **Apple's own 6502 Assembler
[1.3]**, from the work disk, with the output written back to that disk:

    Assembly complete:  519 lines
    0  Errors flagged on this Assembly

Read back and compared against `SYSTEM.COMPILER`:

| procedure | Apple | ours | result |
|---|---|---|---|
| `IDSEARCH` (PASCALCO.2) | 800 bytes | 800 bytes | **identical, every byte** |
| `TREESEARCH` (PASCALCO.3) | 148 bytes | 148 bytes | **identical, every byte** |

The comparison runs `enter_ic` through `jtab+2`, so it covers the code, the
four relocation tables, the ENTER IC and the procedure-number word, and the
procedure-relative relocation entries were checked to be the same set. This
closes finding 44e: the tables were *generated* by the assembler from
symbolic operands, which is the only way those bytes can be produced, and
they came out right.

`probe_native_asm.py` had already got this result with `tools/asm6502.py`.
What is new is that it no longer depends on our assembler being right about
anything.

### 57b. `SYSTEM.COMPILER` compiles the declaration skeleton to Apple's frame

Apple Pascal Compiler [1.3] on `SKEL13.TEXT`: **465 lines, no errors**,
reporting `PASCALCO [12649 words]`. The segment names itself `PASCALCO`
because the program header is `PROGRAM PASCALCOMPILER;` and only the first
eight characters survive -- the same mechanism that gave finding 30 its
names, seen from the other side.

|  | segment | seg num | PARAM SIZE | DATA SIZE | lex |
|---|---|---|---|---|---|
| Apple's `SYSTEM.COMPILER` | `PASCALCO` | 1 | 4 | 2710 | 0 |
| ours, compiled by Apple   | `PASCALCO` | 1 | 4 | 2710 | 0 |

So **130 declarations, their types, their sizes and their order are correct
by the only authority that counts.** Finding 46's frame model, finding 33's
backwards allocation, finding 54's record sizes and finding 55c's two
parameter words are all now confirmed against Apple's own compiler rather
than against a reimplementation of it.

### 57c. Two things the fast tier had been silent about

Neither would ever have surfaced without running the real thing.

**The 64K system cannot do this work at all.** Booting `APPLE1` announces
*"Pascal system size is 64K"*, and on it the compiler dies with a runtime
**stack overflow** -- and not only on the reconstruction. It dies the same
way on `HILBERT.TEXT`, one of Apple's own shipped samples, at `S# 0, P# 17`.
A configuration that cannot compile the sample programs on the disk beside
it is not the configuration Apple used. `128K.APPLE` and `128K.PASCAL` on
`APPLE3` are the answer; `tools/mkbootdisk.py` builds `BOOT128.dsk`, which is
`APPLE1` with those two substituted in, and it boots reporting *"Pascal
system size is 128K"* and compiles without complaint. **Run the acceptance
tier on 128K.** Anything else is measuring the wrong machine.

**A trailing `;` before `)` in a field list is not legal Pascal here.** The
compiler stops at *error 19, "Error in `<field-list>`"*. `ucsdpsys_compile`
accepts it without comment. It was our own debris rather than UCSD's -- the
`PUBLIC`/`IMPORTED` removal of finding 54b left the semicolon that had
separated the dropped variant -- but the lesson generalises: **the fast tier
is more permissive than Apple's compiler, so "it compiles" from the fast tier
is not the same claim.**

### 57d. How it was driven, and the one hazard in it

AppleWin's command line mounts disks and boots but has no keystroke switch,
and `-screenshot-and-exit` is documented for `-load-state`, so it fires
before a cold boot finishes. `tools/runemu.py` launches with the four-drive
layout; `tools/emukeys.ps1` sends keys and captures the window, which closes
the loop -- type, screenshot, read, decide.

Two settings make that loop workable, and **neither has a command-line
switch**, so `runemu.py` writes them to the registry before each launch:
maximum emulation speed, and a **monochrome** video mode. The second is not
cosmetic -- colour-TV artefacts blur 40-column text into something barely
readable in a screenshot, and monochrome renders it cleanly. Passing `-conf`
would defeat both, because it makes AppleWin read an INI instead of the
registry, and `-clock-multiplier` would defeat the first by pinning the
speed.

**The values and their types are version-specific, and guessing them fails
quietly.** Under 1.32: `Video Mode` is a `REG_DWORD` of **9** for monochrome
-- 5 is monochrome under 1.30 but *Color (RGB Card/Monitor)* under 1.32 --
and `Emulation Speed` is a **`REG_SZ`** of `"40"`, so writing it as a
`REG_DWORD` leaves a value AppleWin does not read and no error anywhere.
Verify against the running build rather than assuming: launched with
`-power-on`, AppleWin names the video mode in its own title bar.

The hazard is that **SendKeys types into whatever holds focus**, not into a
window of our choosing. A window activation lost the race once and half a
filename went into the operator's terminal instead of the emulator.
`emukeys.ps1` now refuses to send unless AppleWin is foreground and fails
loudly if focus moves during a send. Never assume the emulator received what
was sent; read the screen back.

Note also that **AppleWin does not flush a written disk image until the disk
is ejected or the emulator exits.** Immediately after the assembly the
directory still showed `SEARCH.CODE` occupying all 188 remaining blocks;
after closing AppleWin it read correctly as 4. Close before reading.

### 57e. What this does and does not settle

It settles the declarations, completely, and both native procedures,
completely. It says nothing yet about a single procedure *body*, because
none has been written. What it changes is the cost of writing them: there is
now a working path from reconstructed source to Apple's own p-code, and the
answer comes back in minutes.

## 58. The first procedure bodies, and the limit of the fast tier

**VERIFIED BINARY FACT.** Two of PASCALCO's leaves are reconstructed and
compile, under Apple's own 1.3 compiler, to p-code identical to the binary's
instruction for instruction. `tools/procbuild.py` is the harness.

### 58a. `DECSIZE` and `PAOFCHAR`

```pascal
FUNCTION DECSIZE(N: INTEGER): INTEGER;
BEGIN
  DECSIZE := (N + 3) DIV 4 + 1
END;

FUNCTION PAOFCHAR(FSP: STP): BOOLEAN;
BEGIN
  PAOFCHAR := FALSE;
  IF FSP <> NIL THEN
    IF FSP^.FORM = ARRAYS THEN
      PAOFCHAR := FSP^.AISPACKD AND (FSP^.AELTYPE = CHARPTR)
END;
```

9 and 20 instructions, both **IDENTICAL**. Nothing about the identifiers is
recovered -- parameter names, comments and layout never reach the codefile --
but everything that does reach it is forced.

`PAOFCHAR` is worth more than its twenty instructions, because three
independent claims had to be right simultaneously for it to match:

* **`ARRAYS` is 5, not 4.** Apple inserted `LONGINT` into `STRUCTFORM` at
  index 3. Writing the member name rather than the number is what makes the
  enumeration's order testable, and `SLDC 5` is the test passing.
* **Two nested `IF`s, not one `AND`.** Apple's compiler does not
  short-circuit (finding 41), so an `AND` compiles to `LAND` over two
  evaluated values. The two guards Apple emits as separate `FJP`s therefore
  have to be two `IF`s in the source, while the final conjunction -- which
  Apple *does* emit as `LAND` -- is an `AND`. Getting that backwards changes
  the bytes.
* **Record field lists allocate backwards.** See below.

### 58b. Finding 33's rule extends to record fields

This is the plan's number-one unchecked item, and `PAOFCHAR` settles it.

UCSD declares `AELTYPE,INXTYPE: STP` in the `ARRAYS` variant. Read in
declaration order that puts `AELTYPE` at offset 2 and `INXTYPE` at 3. The
binary compares the field at **offset 3** against `CHARPTR`, and for a
routine named *packed array of char* that field can only be the element
type. So the identifier list is allocated in reverse, exactly as finding 33
established for `VAR` -- **in a record exactly as in a variable block.**

And it is a check that can fail: written the other way the source still
compiles, still reads correctly, and emits `SIND 2` where Apple has
`SIND 3`.

### 58c. The fast tier cannot settle a boolean expression

`ucsdpsys_compile` got `PAOFCHAR`'s first thirteen instructions exactly right
and then diverged, for a reason no wording of the source can fix:

| Apple | `ucsdpsys_compile` |
|---|---|
| `SIND 4`, `SIND 3`, `LDO 62`, `EQUI`, `LAND`, `STL 1` | `SIND 4`, `FJP`, ..., `EQUI`, `FJP`, `SLDC 1`, `UJP`, `SLDC 0`, `STL 1` |

It short-circuits boolean operators, **including in an assignment**, where
Apple evaluates both sides and emits `LAND`. There is a feature switch for
many things but not for this; `-f no-efj-nfj` is a separate matter (below)
and does not help here.

So: **the fast tier can falsify a body but cannot accept one that contains
`AND` or `OR`.** Apple's compiler in the emulator is the authority, and
`procbuild.py --emu` / `--emu-check` is that loop -- it puts the spliced
source on the work disk and diffs the codefile that comes back. Both
procedures above are green under `--emu-check` and only one of them is green
under the fast tier.

This qualifies finding 55d. The fast tier reproduced the GOTOXY pair byte for
byte, and that remains true; what it means is narrower than it looked,
because neither program contains a boolean operator.

### 58d. `EFJ` and `NFJ`: turn them off

Peter Miller's manual states that these fused compare-and-branch opcodes
"were present in the p-machine used by Apple Pascal, but were never generated
by the Apple Pascal native compiler." The binary agrees -- neither opcode
occurs anywhere in either release. `xcompile.py` now passes
**`-f no-efj-nfj`** on every compile. It costs nothing (the GOTOXY
byte-for-byte result is unchanged) and it removed six spurious differences
from `PAOFCHAR` alone.

## 59. `CODEP` and `SYMBUFP` are NEW'd global pointers, and they sit below `DATA SIZE`

**VERIFIED SOURCE FACT** for what they are, **VERIFIED BINARY FACT** for where
they are, **UNRESOLVED** for how source puts them there. This supersedes
finding 55c's description of them as "the outer block's parameter words",
which was right about the location and wrong about the nature.

### 59a. What they are

`evidence/reference/ucsd-ii0-compiler/compinit.text:256`:

```pascal
NEW(SCONST); NEW(SYMBUFP); NEW(CODEP);
```

Ordinary global pointers, heap-allocated at start-up -- not parameters, and
not anything the operating system passes in. `compglbls.text:252-253`
declares them `CODEP: ^CODEARRAY` and `SYMBUFP: ^SYMBUFARRAY`, the first two
variables of the compiler's `VAR` block.

The `NEW` *order* confirms the offsets independently: the binary's two heap
allocations are 512 and 650 words on globals 1 and 2 respectively, and II.0
allocates `SYMBUFP` before `CODEP`. So **global 1 is `SYMBUFP` and global 2
is `CODEP`**, which is what the map already said from a completely different
direction (the II.0 declaration alignment).

Their access profile fits nothing else: across 1.3, offset 1 is read 70 times
and offset 2 read 33 times, `SRO 1` never occurs and `SRO 2` occurs exactly
once, and both have their address taken (`LAO`). Set once, read everywhere.
`COMPINIT.9` touches both, which is where the `NEW`s are.

### 59b. Where they are: below `DATA SIZE`, in both releases

| release | PARAM | DATA | words in DATA | touched offsets | DATA covers |
|---|---|---|---|---|---|
| 1.3 | 4 | 2710 | 1355 | 1..1357 | 3..1357 |
| 1.1 | 4 | 2444 | 1222 | 1..969  | 3..1224 |

The reconstructed `VAR` block is 130 declarations totalling exactly 1355
words, and Apple's own compiler compiles it to `DATA SIZE` 2710 (finding
57b). So the declared variables occupy 3..1357 and **offsets 1 and 2 are not
declared variables**. That is not an inference from the arithmetic alone:
`PAOFCHAR` emits `LDO 62` for `CHARPTR` in both Apple's binary and our
compile (finding 58), which pins the whole block from offset 3 upward. Two
more declarations at the front would move `CHARPTR` to 64.

### 59c. Three constructs tested, none of them it

All tested against **Apple's own 1.3 compiler**, not the fast tier.

* **A plain program.** `PROGRAM T;` with four globals puts them at
  **3,4,5,6**. Declared globals never start below 3.
* **A program parameter list.** `PROGRAM T(CODEP,SYMBUFP);` with both also
  declared in `VAR` allocates them at **3 and 4** exactly as before. The
  parameter list is decorative -- its only effect is two extra `NOP`s at the
  start of the outer block. It does not allocate.
* **`(*$U-*)`.** Produces **segment 0, `PARAM SIZE` 0, lex -1**, and turns the
  outer block's variables into *locals* addressed `STL`/`SLDL`, the first at
  offset **1**. `SYSTEM.COMPILER` is segment 1, lex 0, `PARAM SIZE` 4, and
  addresses these two with `SLDO`/`SRO`. So it is **not** `$U-` -- finding
  23c's conclusion stands, and is now tested rather than inferred.

That last one is tantalising and is not the answer: `$U-` is the one
construct that starts allocation at offset 1, and II.0's compiler *is*
`(*$U-*)`, which is exactly why its `CODEP` is the first variable. But Apple's
build is not `$U-` by four independent measurements.

### 59d. What is left

Something puts two words at global offsets 1 and 2, below `DATA SIZE`, in a
segment-1 lex-0 program. Candidates not yet tested:

* an intrinsic-unit or `USES` arrangement, where a unit's globals are
  allocated ahead of the host program's;
* a compiler option other than `$U`;
* the possibility that `SYSTEM.COMPILER` was not produced by a stock
  compiler at all. Note that `SYSTEM.EDITOR`, `SYSTEM.FILER`,
  `SYSTEM.LINKER` and `SYSTEM.ASSMBLER` never touch globals 1-2, while
  `SYSTEM.COMPILER`, `SYSTEM.PASCAL`, `128K.PASCAL` and `LIBMAP.CODE` all
  do -- so whatever it is, it is not universal to Apple's system programs.
  `LIBMAP.CODE` is small (1510 words) and is the cheapest place to look next.

Until it is resolved, every procedure touching globals 1 or 2 is blocked.
`GENBYTE` (`PASCALCO.22`) is the smallest of them, at nine instructions:
`CODEP^[IC] := B; IC := IC + 1`.

## 60. The compiler is a SEGMENT PROCEDURE, not a PROGRAM

> Finding 67 briefly retracted this. **Finding 68 reinstates it in full**:
> the structure below is right, and the segment numbering that finding 67
> tripped over is `{$NS 7}`.


**VERIFIED SOURCE FACT**, and it resolves finding 59's open question.

`evidence/reference/ucsd-ii0-compiler/compglbls.text` line 66:

```pascal
SEGMENT PROCEDURE PASCALCOMPILER(VAR USERINFO: INFOREC);
```

preceded at line 39 by a dummy `SEGMENT PROCEDURE USERPROGRAM` containing
eight further dummy segment procedures, all inside `(*$U-*) PROGRAM
PASCALSYSTEM`. The compiler is not a program at all.

### 60a. What that explains

Tested against Apple's own 1.3 compiler with a small model program:

* **A segment procedure's own variables are the global data segment.** With
  `param=2`, its locals came out at offsets 2 and 3 addressed `SRO 2`,
  `SLDO 3` -- *global* addressing, not `STL`/`SLDL`. That is why every one of
  the compiler's variables is reached with `LDO`/`SRO`.
* **They are laid out after the parameter words.** One parameter word put the
  first local at 2. Apple's `PARAM SIZE 4` is two words at offsets **1 and
  2**, so its locals start at **3** -- exactly where `GATTR` is.
* **So `SYMBUFP` and `CODEP` are the two parameters.** The OS enters segment 1
  as `USERPROGRAM(NIL,NIL)` (`SYSTEM.C.TEXT:568`) -- two words -- and the
  compiler `NEW`s its own buffers into them. That matches the access profile
  of finding 59a exactly: address taken on both, stored to once, read
  constantly.
* **Segment 1 and lex 0.** A segment procedure declared first in a `$U-`
  host program is segment 1, and its body is lex 0. Both match `PASCALCO.1`.
* **The segment-number gap.** Apple's phases are 7-20 with nothing at 2-6,
  which is what a block of dummy segment procedures is for.

### 60b. The frame comes out exactly right

`srcskel.py` now emits the structure, and the reconstruction compiles to:

|  | segment | name | PARAM | DATA | lex |
|---|---|---|---|---|---|
| Apple's binary | 1 | `PASCALCO` | 4 | 2710 | 0 |
| ours | 1 | `PASCALCO` | 4 | 2710 | 0 |

`DECSIZE` and `PAOFCHAR` still compile to the same p-code under the new
structure, `LDO 62` for `CHARPTR` included -- so global addressing survives
the move, as 60a predicts.

Finding 55c's description of offsets 1-2 as "the outer block's parameter
words" was therefore right about *what they are* and wrong about *whose*:
they are `PASCALCOMPILER`'s parameters, not a program main's.

**One thing here is wrong and finding 63 corrects it.** The skeleton's
comment said the host program could declare no variables, because a segment
procedure's variables are the global data segment and anything declared in
the host would collide with them. It does not collide: the host block
compiles at lex **-1**, which is a different data segment -- the operating
system's -- and the compiler reads ten offsets in it.

### 60c. Resolved: error 400 was our `.TEXT` writer, not the restructure

The fast tier compiled the restructured skeleton and gave Apple's exact
frame. Apple's own compiler stopped at the same place with or without
procedure bodies --

```
  FACBEGSYS       : SETOFSYS;
  <<<<
Line 406, error 400
```

-- and error 400 is *"Illegal character in text"*, of which the file had
none: printable ASCII, no tabs, every line inside 80 columns, and the same
`VAR` block had compiled cleanly under the old `PROGRAM PASCALCOMPILER`
structure (finding 57b). The restructure was not the cause. **The cause was
`encode_text`**, and the compiler's own source says so.

The compiler reads source a page at a time (`GETNEXTPAGE`, `BLOCKREAD(...,
SYMBUFP^, 2, SYMBLK)`) and finds the end of a page in exactly one way, at
every end of line -- `CHECKEND`, `procs.a.text`:

```pascal
IF SYMBUFP^[SYMCURSOR]=CHR(0) THEN GETNEXTPAGE
ELSE LINESTART := SYMCURSOR;
```

**The terminating NUL is load-bearing.** A page packed to exactly 1024
content bytes has none, so `SYMCURSOR` reaches 1024, the test reads past the
end of the buffer, the fetch never happens, and the byte found there is not
a symbol -- `SY := OTHERSY`, and then `procs.a.text`:

```pascal
IF SY=OTHERSY THEN
  IF SYMBUFP^[SYMCURSOR] = CHR(EOL) THEN ...
  ELSE ERROR(400);
```

Our writer packed with `len(page) + len(enc) > PAGE`, which permits the
exactly-full page. The 1.3 skeleton's page 11 was one, and its last line was
the reported one:

```
page 10  pad 30
page 11  pad  0   ...  '  FACBEGSYS       : SETOFSYS;\r'
page 12  pad 27
```

So the diagnostic was honest and the "illegal character" was real -- it was
just past the end of the file, in whatever `SYMBUFP^[1024]` overlays.

**VERIFIED BINARY FACT.** Apple's own editor keeps the same invariant: of the
159 text pages in the 21 `.TEXT` files across the six evidence disks, the
least-padded page has **one** NUL, and none has zero. A page holds at most
1023 bytes of line data.

Fixed by changing both tests in `encode_text` to `>= PAGE`.
`probe_diskwrite.py` now checks it two ways -- no re-encoded Apple page may
be full, and four constructed cases pack lines to exactly 1024 on purpose
and require the writer to split them. Reverting the fix fails 12 of those
checks, three of them on Apple's own files.

### 60d. Verified: Apple's compiler accepts the restructured skeleton

With the writer fixed, Apple's 1.3 compiler compiles `BODY13.TEXT` clean --
513 lines, no errors, `DECSIZE`, `PAOFCHAR` and `PASCALCO` all reported --
and both reconstructed bodies come back **byte-identical to the binary**:

```
[1.3] PASCALCO.19 DECSIZE:   9 instructions, IDENTICAL  (Apple's compiler)
[1.3] PASCALCO.17 PAOFCHAR: 20 instructions, IDENTICAL  (Apple's compiler)
```

`PAOFCHAR` is the one the fast tier can never settle: it short-circuits the
`AND` where Apple evaluates both sides and emits `LAND` (finding 58). Under
Apple's own compiler the divergence is gone. That closes the loop --
`procbuild.py --emu` writes the source to the work disk, Apple's compiler
builds it, `--emu-check` diffs the result -- and it is now the authority for
every remaining body.

## 61. Declaration order is the numbering, and II.0 preserves it

A procedure's number is not free. UCSD assigns it when it parses the
header, so **declaration order is the numbering**, and the numbering is what
every `CGP n` in every other body has to agree with. A segment can have
every body right and still be wrong if the order is wrong.

Apple's order for segment 1 is recoverable, and the source of it is UCSD
II.0's forward-declaration block, `compglbls.text:362-402`. Lining that
block up against Apple's 1.3 numbers:

| # | Apple 1.3 | II.0 forward block |
|---|-----------|--------------------|
| 2 | IDSEARCH | (native, EXTERNAL) |
| 3 | TREESEARCH | (native, EXTERNAL) |
| 4-11 | ERROR, GETNEXTPAGE, PRINTLINE, ENTERID, INSYMBOL, SEARCHSECTION, SEARCHID, GETBOUNDS | identical, same order |
| 12-15 | BUMPSEG, NEWSEG, CHECKEND, SEGINFO | **inserted by Apple** |
| 16-23 | SKIP, PAOFCHAR, STRGTYPE, DECSIZE, CONSTANT, COMPTYPES, GENBYTE, GENWORD | identical, same order |
| — | — | WRITETEXT **dropped by Apple** |
| 24 | WRITECODE | same |
| 25 | FINISHSEG | **inserted by Apple** |
| 26 | BLOCK | same |
| 27-31 | COMPILE, COMMENTER, FINDFORW, HOLDMOST, HOLDROUT | declared after the forward block |

Nineteen names in the same relative order, with five insertions and one
deletion. The insertions are not arbitrary either: `BUMPSEG`, `NEWSEG`,
`SEGINFO` and `FINISHSEG` are all segment bookkeeping, which is exactly what
Apple extended. `WRITETEXT` is UNIT interface text, which Apple's segment 1
does not do.

**The independent confirmation is PARAM SIZE.** Every II.0 signature in that
block reproduces Apple's parameter size exactly, with nothing adjusted:

```
ERROR(ERRORNUM: INTEGER)                            2   SKIP(FSYS: SETOFSYS)          8
ENTERID(FCP: CTP)                                   2   PAOFCHAR(FSP: STP): BOOLEAN   6
SEARCHSECTION(FCP: CTP; VAR FCP1: CTP)              4   DECSIZE(I: INTEGER): INTEGER  6
SEARCHID(FIDCLS: SETOFIDS; VAR FCP: CTP)            4   COMPTYPES(FSP1,FSP2: STP)     8
GETBOUNDS(FSP: STP; VAR FMIN,FMAX: INTEGER)         6   CONSTANT(...)                12
GENBYTE(FBYTE: INTEGER)                             2   BLOCK(FSYS: SETOFSYS)         8
```

Twelve signatures, twelve exact hits, including the four-word set parameters
and the two-word function return area. A function's frame is 2 words of
return space plus its parameters, which is why `DECSIZE(I: INTEGER):
INTEGER` is 6 and `GENBYTE(FBYTE: INTEGER)` is 2.

`FINDFORW` at 29 sits between `COMMENTER` at 28 and `HOLDMOST` at 30 and has
lex level 2, so it is **nested inside COMMENTER** -- a nested procedure takes
the next number after its parent's header. `HOLDROUT` at 31, lex 2, is
nested inside `HOLDMOST` the same way.

`src/pascal/1.3/PASCALCO.text` now declares all thirty in that order, with
empty `(*STUB*)` bodies for the twenty-two not yet written; they exist to
hold their numbers. `procbuild.py` checks the order as a thing in its own
right -- our number must equal Apple's for every procedure, stub or not --
and all thirty pass.

### 61b. Parameters are allocated in reverse, like every other list

Finding 33 found that Apple's compiler allocates an identifier list back to
front. It does the same to a **parameter list**, and to the parameter list
as a whole rather than within each group.

Measured, not assumed. `BUMPSEG` written as

```pascal
PROCEDURE BUMPSEG(FERRNUM,FMAX: INTEGER; VAR FVALUE: INTEGER);
```

put `FVALUE` at local 1 and `FERRNUM` at local 3 under Apple's own compiler.
The binary has them the other way round -- `SLDL 3 / SIND 0` for the VAR
parameter and `SLDL 1` for the argument to `ERROR`. Reversing the source
order fixes it and the procedure comes out identical:

```pascal
PROCEDURE BUMPSEG(VAR FVALUE: INTEGER; FMAX,FERRNUM: INTEGER);
BEGIN
  IF FVALUE < FMAX THEN FVALUE := FVALUE+1
  ELSE ERROR(FERRNUM)
END;
```

Read as one flat sequence, source `[FERRNUM, FMAX, FVALUE]` gave offsets
`[3, 2, 1]`: a straight reversal, with the group boundary making no
difference.

**This settles the order of the two parameter words**, which finding 60 left
as a guess. `GENBYTE` is the measurement -- `CODEP^[IC] := CHR(FBYTE)`
compiles to `SLDO 2`, so `CODEP` is global **2** and `SYMBUFP` is global 1.
Under reverse allocation that forces `CODEP` to be declared **first**:

```pascal
SEGMENT PROCEDURE PASCALCOMPILER(CODEP: CODEPTR;
                                 SYMBUFP: SYMBUFPTR);
```

which is UCSD II.0's own order at `compglbls.text:252-253`, where the two
are the first two variables. The skeleton had them the other way round and
`GENBYTE` was the first body written that could tell.

Their types have to be declared in the host program, not in
`PASCALCOMPILER`: a parameter list is outside the block it heads and cannot
see that block's `TYPE` section. `srcskel.py` restates `CODEARRAY` and
`SYMBUFARRAY` there, bounded by the same `MAXCODE` and `MAXCURSOR` it reads
back out of the `CONST` block so the two cannot drift apart.

### 61c. Eight bodies verified

Under Apple's own 1.3 compiler, against Apple's own p-code:

```
[1.3] PASCALCO.12 BUMPSEG:  15 instructions, IDENTICAL
[1.3] PASCALCO.16 SKIP:     10 instructions, IDENTICAL
[1.3] PASCALCO.17 PAOFCHAR: 20 instructions, IDENTICAL
[1.3] PASCALCO.18 STRGTYPE: 11 instructions, IDENTICAL
[1.3] PASCALCO.19 DECSIZE:   9 instructions, IDENTICAL
[1.3] PASCALCO.22 GENBYTE:   9 instructions, IDENTICAL
```

`SKIP`, `PAOFCHAR`, `STRGTYPE` and `DECSIZE` are UCSD II.0's bodies
unchanged. `GENBYTE` is too. `BUMPSEG` is Apple's own and was recovered from
the p-code. `IDSEARCH` and `TREESEARCH` are declared `EXTERNAL` to hold
numbers 2 and 3; they are 6502 and the assembler acceptance tier holds them
to Apple's bytes instead.

One tooling consequence: an unlinked `EXTERNAL` leaves a **zero** in the
procedure dictionary, and a self-relative pointer of zero is an empty slot,
not a pointer to itself. `codefile.py` now reads it that way. Apple's
shipped codefiles are all linked and contain none, so nothing had forced the
question before.

## 62. SEGMAP is nibbles, and NEWSEG is what says so

`SEGMAP` was one of the objects the global map sized but could not shape:
16 words in 1.3, 8 in 1.1, emitted as `ARRAY [0..15] OF INTEGER` with the
note *"shape not recovered"*. It allocates the right number of words and
compiles every access to it wrong.

Every reference to it in either binary is an **`IXP 4,4`** -- index packed
array, four entries to the word, four bits each. So the 16 words are 64
entries, not 16, and what fits in four bits is a `SEGRANGE` (0..15). It is a
map from segment number to segment-table slot:

```pascal
SEGMAP : PACKED ARRAY [0..63] OF SEGRANGE;     { 1.3, 16 words }
SEGMAP : PACKED ARRAY [0..31] OF SEGRANGE;     { 1.1,  8 words }
```

**`NEWSEG` is the measurement.** Its last statement is one store into
`SEGMAP`, and the store only compiles to Apple's bytes if the declaration is
the packed one:

```pascal
PROCEDURE NEWSEG(*FNEWSEG: BOOLEAN*);
BEGIN
  IF FNEWSEG THEN
    BEGIN BUMPSEG(NEXTSEG,63,354); BUMPSEG(SEGSLOT,15,354) END;
  SEGMAP[SEG] := SEGSLOT
END;
```

```
LAO 589 / SLDO 13 / IXP 4,4 / LDO 21 / STP
```

The two `BUMPSEG` calls corroborate the ranges independently: `NEXTSEG` is
bounded at **63** and `SEGSLOT` at **15**, which are exactly the index range
and the element range of the array. Sixty-four segment numbers mapping into
sixteen physical slots is the whole point of the structure, and it is Apple's
extension -- 1.1 maps thirty-two.

Sizing this needed one addition to `reclayout.py`, which only knew how to
pack `CHAR`. UCSD packs any scalar into the fewest bits that hold its range
and puts `16 div bits` of them in a word -- which is what the two operands of
`IXP` are. `CHAR` is the same rule (0..255, eight bits, two to the word), so
the special case is now an instance of the general one.

### 62b. Twelve bodies verified

Under Apple's own 1.3 compiler, against Apple's own p-code:

```
[1.3] PASCALCO.9  SEARCHSECTION: 22 instructions, IDENTICAL
[1.3] PASCALCO.11 GETBOUNDS:     42 instructions, IDENTICAL
[1.3] PASCALCO.12 BUMPSEG:       15 instructions, IDENTICAL
[1.3] PASCALCO.13 NEWSEG:        16 instructions, IDENTICAL
[1.3] PASCALCO.16 SKIP:          10 instructions, IDENTICAL
[1.3] PASCALCO.17 PAOFCHAR:      20 instructions, IDENTICAL
[1.3] PASCALCO.18 STRGTYPE:      11 instructions, IDENTICAL
[1.3] PASCALCO.19 DECSIZE:        9 instructions, IDENTICAL
[1.3] PASCALCO.22 GENBYTE:        9 instructions, IDENTICAL
[1.3] PASCALCO.23 GENWORD:       35 instructions, IDENTICAL
```

Eight are UCSD II.0's bodies unchanged. `BUMPSEG` and `NEWSEG` are Apple's
own and were recovered from the p-code. `GENWORD` is II.0's with one Apple
edit the binary states: where II.0 writes `IF ODD(IC) THEN IC := IC + 1`,
Apple writes `IF ODD(IC) THEN GENBYTE(0)` -- `SLDC 0 / CGP 22` -- so the pad
byte is actually written into the code buffer instead of skipped over.

Two of them, `SEARCHSECTION` and `GETBOUNDS`, are cases the fast tier cannot
settle, for reasons that are new and worth naming alongside finding 58's
`LAND`:

* `SEARCHSECTION` has II.0's empty `THEN` -- `IF TREESEARCH(...) = 0 THEN
  (*NADA*) ELSE FCP1 := NIL`. Apple's compiler emits it literally, `EQUI`
  and a `UJP` over nothing. The fast tier inverts the test to `NEQI` and
  drops the jump.
* `GETBOUNDS` has `WITH FSP^ DO`. Apple's compiler materialises the `WITH`
  pointer into a local -- `SLDL 3 / STL 4`, which is where its `DATA SIZE`
  of 2 comes from -- and addresses the fields through it. The fast tier
  eliminates the temporary and re-loads `FSP` at each field, giving `DATA
  SIZE` 0.

Both are cosmetic to a reader and are the difference between matching Apple's
bytes and not.

### 62c. Parameter order, and how to get it wrong

Finding 61b's reverse rule has a trap in it, and I walked into it twice.
UCSD II.0's signatures are already in the order that reverses onto Apple's
offsets, because Apple compiled II.0's source. `SEARCHSECTION(FCP: CTP; VAR
FCP1: CTP)` reverse-allocates to `FCP1` at 1 and `FCP` at 2, which is what
the binary has; "correcting" it to `(VAR FCP1; FCP)` produces the mirror
image and fails. The rule applies when a signature is being *recovered from
the p-code* -- `BUMPSEG`, which II.0 does not have -- and not to signatures
taken from II.0, which need no adjustment at all.

## 63. The host program's variables are the operating system's globals

`PASCALCOMPILER` reaches **below lex 0**, and until now nothing in the
reconstruction could produce those references. Sweeping every `LOD`, `STR`
and `LDA` in both binaries for a target below the segment procedure's own
level gives 103 references in 1.3 and 89 in 1.1, at ten distinct offsets --
and the same ten in both releases:

```
lex -1 offset   2   LOD x2     COMPINIT
lex -1 offset   3   LOD x81    9 procedures, all of them WRITE/WRITELN
lex -1 offset   4   LOD x1     ERROR
lex -1 offset   8   LOD x4     GETNEXTPAGE, WRITECODE, UNITPART
lex -1 offset   9   LOD x1     GETNEXTPAGE
lex -1 offset  10   LOD x2 STR x1   ERROR, PRINTLINE, WRITECODE
lex -1 offset  11   LOD x2 STR x4   ERROR, PRINTLINE, FINISHUP
lex -1 offset  12   LOD x2 STR x1   ERROR, PRINTLINE
lex -1 offset  13   LOD x1     ERROR
lex -1 offset  14   LOD x1     COMPINIT
lex -1 offset  15   LOD x1     ERROR          (1.1 only)
```

Under `(*$U-*)` the outer block compiles at **lex -1**, which is the
operating system's own data segment. So the host program's `VAR` block *is*
the system's globals -- and it does not collide with the compiler's globals
at lex 0, because they are different segments. Finding 60's skeleton comment
said the host "declares nothing" for fear of a collision; that was wrong,
and the frame is unchanged either way (`probe_xcompile` still gives Apple's
`PARAM 4 / DATA 2710 / lex 0` with the declarations added).

**UCSD II.0's `GLOBALS.TEXT:228-231` accounts for every offset**, laid out
from 1:

```pascal
SYSCOM:   ^SYSCOMREC;               { 1     }
GFILES:   ARRAY [0..5] OF FIBP;     { 2..7  -- 0=INPUT, 1=OUTPUT }
USERINFO: INFOREC;                  { 8..   }
```

* **2** is `GFILES[0]`, INPUT. **3** is `GFILES[1]`, OUTPUT -- and all 81
  references to it are `CXP 0,17`, `CXP 0,22` or `CXP 0,13`, which are
  write-char, write-line and write-integer. **4** is `GFILES[2]`, KEYBOARD,
  read exactly once, by `ERROR`, which is the one place II.0 does
  `READ(KEYBOARD,CH)`.
* **8 onwards is `USERINFO`**, and the record that fits is the compiler's
  own nine-word `INFOREC` from `compglbls.text:30-35`, not the system's
  longer one.

The field mapping is an independent re-proof of finding 33, because it only
works if identifier lists allocate **back to front** within each group while
the groups themselves go forward:

| offset | field | II.0 declaration order | what uses it |
|---|---|---|---|
| 8 | `WORKCODE` | 2nd of `WORKSYM,WORKCODE` | `BLOCKWRITE` in WRITECODE, UNITPART |
| 9 | `WORKSYM` | 1st of the same list | `BLOCKREAD` in GETNEXTPAGE |
| 10 | `ERRNUM` | 3rd of `ERRSYM,ERRBLK,ERRNUM` | `ERRNUM := ERRORNUM`; `IF ERRNUM = 0` |
| 11 | `ERRBLK` | 2nd | four stores, which is exactly II.0's count |
| 12 | `ERRSYM` | 1st | two loads and one store, likewise |
| 13 | `STUPID` | 2nd of `SLOWTERM,STUPID` | `IF STUPID THEN CH := 'E'` |
| 14 | `SLOWTERM` | 1st | COMPINIT |
| 15 | `ALTMODE` | on its own | `UNTIL ... OR (CH = ALTMODE)` -- **1.1 only** |

Eight fields, eight matches, including the store/load counts. And 15 being
1.1-only is consistent on its own terms: 1.3's `ERROR` dropped the
`<sp>/<esc>/E` prompt, which is the only thing that ever read `ALTMODE`.

`srcskel.py` now emits the host declarations. `WRITECODE` is the body that
measures them -- `LOD 2,10` for `USERINFO.ERRNUM` and `LOD 2,8` for
`USERINFO.WORKCODE^` both come out right.

### 63b. Fifteen bodies verified -- half of segment 1

Under Apple's own 1.3 compiler, against Apple's own p-code:

```
[1.3] PASCALCO.7  ENTERID:       67 instructions, IDENTICAL
[1.3] PASCALCO.9  SEARCHSECTION: 22 instructions, IDENTICAL
[1.3] PASCALCO.10 SEARCHID:      99 instructions, IDENTICAL
[1.3] PASCALCO.11 GETBOUNDS:     42 instructions, IDENTICAL
[1.3] PASCALCO.12 BUMPSEG:       15 instructions, IDENTICAL
[1.3] PASCALCO.13 NEWSEG:        16 instructions, IDENTICAL
[1.3] PASCALCO.16 SKIP:          10 instructions, IDENTICAL
[1.3] PASCALCO.17 PAOFCHAR:      20 instructions, IDENTICAL
[1.3] PASCALCO.18 STRGTYPE:      11 instructions, IDENTICAL
[1.3] PASCALCO.19 DECSIZE:        9 instructions, IDENTICAL
[1.3] PASCALCO.22 GENBYTE:        9 instructions, IDENTICAL
[1.3] PASCALCO.23 GENWORD:       35 instructions, IDENTICAL
[1.3] PASCALCO.24 WRITECODE:     67 instructions, IDENTICAL
```

Thirteen bodies plus the two native procedures: fifteen of segment 1's
thirty. `ENTERID`, `SEARCHID` and `WRITECODE` are UCSD II.0's, unchanged.

A third fast-tier limit turned up in `ENTERID` and `SEARCHID`, alongside
finding 58's `LAND` and finding 62b's two: indexing `DISPLAY`, whose element
is a four-word record, Apple emits `IXA 4` and the fast tier emits `SLDC 4 /
MPI / IXA 1`. `SEARCHID` adds a fourth -- Apple materialises a `FOR` loop's
limit into a local (`SLDC 0 / STL 4`, which is where its `DATA SIZE` of 4
comes from) and the fast tier keeps it on the stack.

### 63c. And a sharper account of error 400

Finding 60c blamed the exactly-full `.TEXT` page, correctly. Apple's
`CHECKEND` shows there are **two** ways it could have surfaced, because
Apple rewrote II.0's page-end test into a validation:

```pascal
IF SYMBUFP^[SYMCURSOR] = CHR(0) THEN
  BEGIN
    IF NOT <g37> THEN
      BEGIN
        SYMCURSOR := SYMCURSOR + SCAN(1024-SYMCURSOR,<>CHR(0),
                                      SYMBUFP^[SYMCURSOR]);
        IF SYMCURSOR <> 1024 THEN ERROR(400)
      END;
    GETNEXTPAGE
  END
ELSE LINESTART := SYMCURSOR
```

II.0 has only `IF SYMBUFP^[SYMCURSOR]=CHR(0) THEN GETNEXTPAGE ELSE LINESTART
:= SYMCURSOR`. Apple additionally scans the tail and **requires the rest of
the page to be NUL**, reporting error 400 if it is not. With `SYMCURSOR` at
1024 the test reads `SYMBUFP^[1024]`, one past the end of a `[0..1023]`
array: whichever way that byte falls, the result is error 400 -- from this
site if it happens to be non-zero further on, from `INSYMBOL`'s `OTHERSY` if
the scan runs into the next page's text. The diagnosis stands and the
mechanism is now exact.

## 64. BYTEPTR and WORDPTR are structure pointers, and COMPTYPES says so

Two of 1.3's new globals, 57 and 58, were named by the global map and left
untyped -- `render_type` called them `INTEGER` because II.0 has no
declaration to borrow. That allocates the one word each occupies and
compiles nothing correctly.

`COMPTYPES` settles it. Apple's `ARRAYS` arm ends with a comparison II.0
does not have:

```
SLDL 4 / LDO 57 / NEQI / LAND      { FSP1 <> BYTEPTR }
SLDL 3 / LDO 57 / NEQI / LAND      { FSP2 <> BYTEPTR }
SLDL 4 / LDO 58 / NEQI / LAND      { FSP1 <> WORDPTR }
SLDL 3 / LDO 58 / NEQI / LAND      { FSP2 <> WORDPTR }
```

`FSP1` and `FSP2` are `STP`, so 57 and 58 are `STP` -- the standard-type
pointers that sit beside `CHARPTR`, `INTPTR` and `REALPTR` in the same
block. Declared `INTEGER` the source will not compile at all.

The whole edit, against II.0's

```pascal
IF COMP AND NOT STRGTYPE(FSP1) THEN
  COMP := (FSP1^.SIZE = FSP2^.SIZE);
```

is

```pascal
IF COMP THEN
  IF NOT STRGTYPE(FSP1)
     AND (FSP1 <> BYTEPTR) AND (FSP2 <> BYTEPTR)
     AND (FSP1 <> WORDPTR) AND (FSP2 <> WORDPTR) THEN
    COMP := (FSP1^.SIZE = FSP2^.SIZE);
```

and the **nesting is not cosmetic**. Apple's compiler emits `LAND` for
`AND` (finding 58), so `IF COMP AND ...` would have produced a `LAND` on
`COMP`; the binary has `SLDL 7 / FJP`, a branch. Only a nested `IF` gives
that. Writing it flat left exactly five instructions different out of 281 --
which is the whole method working: the difference between two readings that
no reader would distinguish, decided by the bytes.

The reason for the edit is legible from the change itself. Two array types
of the same element type and packing but different `SIZE` are normally
incompatible; Apple exempts arrays of `BYTE` and `WORD` from the size check,
which is what you need if those types are to interoperate with arrays
declared at other lengths.

### 64b. Nineteen bodies verified, and CHECKEND's error-400 validation

Under Apple's own 1.3 compiler, all nineteen reconstructed procedures of
segment 1 now match Apple's p-code exactly. The four added here:

```
[1.3] PASCALCO.14 CHECKEND:  121 instructions, IDENTICAL
[1.3] PASCALCO.21 COMPTYPES: 281 instructions, IDENTICAL
[1.3] PASCALCO.25 FINISHSEG:  59 instructions, IDENTICAL
[1.3] PASCALCO.27 COMPILE:    16 instructions, IDENTICAL
```

`CHECKEND` confirms finding 63c's reading of the page-end validation, which
was reconstructed from the p-code and is Apple's, not II.0's. `FINISHSEG` is
II.0's with one edit -- `SEGTABLE[SEG].CODELENG` becomes
`SEGTABLE[SEGMAP[SEG]].CODELENG`, the segment-to-slot indirection of finding
62 -- and its field displacement re-proves finding 33 once more:
`DISKADDR,CODELENG: INTEGER` reversed puts `CODELENG` at offset 0, which is
the `IXA 9 / STO` with no field offset that the binary has.

`COMPILE` turns out to be two statements lifted out of II.0's
`BEGIN (*PASCALCOMPILER*)` prologue:

```pascal
PROCEDURE COMPILE;
BEGIN
  TIME(LGTH,LOWTIME);
  BLOCK(BLOCKBEGSYS+STATBEGSYS-[CASESY])
END;
```

Two more constant-folding facts the emulator settled, both of which cost a
round trip each: Apple's compiler does **not** fold `MAXCURSOR+1` into 1024
(the binary has a plain `LDCI 1024`, so Apple's source has the literal), and
it writes a one-character literal in a `WRITE` as a `CHAR` (`CXP 0,17`)
where the fast tier makes it a one-character `STRING` (`CXP 0,19`).

### 64c. CONSTANT: II.0's body is close but not Apple's

`CONSTANT` is back to a stub, with what is known recorded on it. II.0's body
reproduces Apple's p-code for all of it *except* the `LONGCONST` arm, where
the binary does something II.0 does not:

```
SLDL 1 / SIND 0 / MOV 130          { a 130-word structured copy }
SLDC 1 / STL 11                    { a FOR loop counter }
SLDL 10 / SIND 2 / STL 12          { its limit, from the value's own field }
SLDL 11 / SLDL 12 / LEQI / FJP     { FOR ... TO limit DO }
  ... IXA 1 ... NGI ...            { negate word by word }
```

II.0 negates `LONGVAL[1]` alone. Apple loops over every word of the long
constant. The frame says the same thing independently: Apple's `DATA SIZE`
is 12, six words, and its `WITH` temporary lands at local **12**, so five
locals are declared where II.0 declares four.

## 65. The lexical level says where a procedure is declared

`COMMENTER` and `FINDFORW` are **lex 2**, not lex 1. Neither is a procedure
of `PASCALCOMPILER` at all -- each is nested inside one of its procedures --
and that, with their numbers, pins a piece of Apple's file layout that
nothing else would have shown.

The numbers are 28 and 29, after `COMPILE` at 27. A nested procedure takes
its number when its header is parsed, so whatever they are nested in must be
*declared* before 28 and have its **body** after 27. Only a forward-declared
procedure can do both. So:

* `COMMENTER` belongs to **`INSYMBOL`** -- forward-declared at 8, body after
  `COMPILE`. `INSYMBOL` is the only thing that scans comments, and Apple's
  `COMMENTER` confirms it: it steps `SYMCURSOR`, calls `CHECKEND` at each
  end of line, stops on `STOPPER`, and treats `*)` and `}` alike.
* `FINDFORW` belongs to **`BLOCK`** -- forward-declared at 26, body after
  that. Its p-code says what it is: it walks the symbol tree recursively
  (`CIP 29`, a call to itself), tests four fields of each entry, and on a
  hit writes the eight-character name followed by the literal
  `' undefined'`. It is the undefined-`FORWARD` diagnostic, which is
  exactly `BLOCK`'s business and has nothing to do with comments.

Finding 61's guess that `FINDFORW` was nested in `COMMENTER` -- made from
the numbering alone, and flagged at the time as the weak part -- was wrong.
The lexical level is what settles it, and `procbuild.py` now checks the lex
level of every procedure including the stubs, so a nesting error is caught
without needing a body. Un-nesting `COMMENTER` to test the check gives
`PASCALCO.28 COMMENTER: lex 1, Apple has lex 2`.

### 65b. PRINTLINE is the one procedure with I/O checking on

Apple emits `CSP 0` -- `IOCHECK` -- after every `WRITE` in `PRINTLINE` and
after no other I/O in the segment. `CHECKEND` writes to `OUTPUT` with no
check at all, and matches.

II.0 has it bracketed exactly so, `procs.a.text:94` and `:120`:

```
(*$I+*)
PROCEDURE PRINTLINE;
  ...
(*$I-*)
```

The reconstruction needed the same two lines and nothing else -- our default
already produces unchecked I/O, which is what `compiler.text:3`'s global
`(*$T+*)` does in Apple's build.

### 65c. GETNEXTPAGE: four Apple edits and a variable that is never used

Every instruction matched before the frame did. Apple's `DATA SIZE` is 2 --
one word of locals -- and **no instruction in the procedure references it**.
II.0's `GETNEXTPAGE` declares no locals at all. So Apple's source declares a
variable and never uses it, and the only evidence it exists is the frame.
It is declared and named `I` here; the name is not recoverable.

The four real edits, all of which the binary states:

* **`WRITETEXT` is inlined and moved to the top.** Apple dropped `WRITETEXT`
  from the procedure list (finding 61) and put its work at the head of
  `GETNEXTPAGE`, before the file is read rather than after
  `SYMCURSOR = 0`: `MOVELEFT(SYMBUFP^[TEXTSTRT],CODEP^[0],1024);
  WRITECODE(TRUE); TEXTSTRT := 0`. II.0 wrote the block itself with
  `BLOCKWRITE` and kept its own `CURBLK`; Apple routes it through
  `WRITECODE` and keeps a separate `TEXTSTRT` cursor.
* **An `IORESULT` check on the include file.** Where the `BLOCKREAD` of
  `INCLFILE` comes up short, Apple first does `IF IORESULT <> 0 THEN
  ERROR(403)` and then closes; II.0 just closes.
* **The `USEFILE = SYSLIBRARY` test is gone.** `UNITFILE` has two values, so
  Apple wrote the second arm as a plain `ELSE`.
* **An empty `THEN`.** `IF NOT USING THEN <restore>` is written `IF USING
  THEN (*NADA*) ELSE <restore>`. The binary has `LDO 37 / FJP else / UJP
  end` with no `LNOT`, where the two other `IF NOT USING` tests in the same
  procedure both have one. Same idiom as `SEARCHSECTION`.

### 65d. Twenty-one bodies verified, nine to go

Under Apple's own 1.3 compiler, all twenty-one reconstructed procedures of
segment 1 match Apple's p-code exactly. Added here:

```
[1.3] PASCALCO.5 GETNEXTPAGE: 135 instructions, IDENTICAL
[1.3] PASCALCO.6 PRINTLINE:   134 instructions, IDENTICAL
```

Nine stubs remain: `ERROR`, `INSYMBOL`, `SEGINFO`, `CONSTANT`, `BLOCK`,
`COMMENTER`, `FINDFORW`, `HOLDMOST`, `HOLDROUT`.

### 65e. Two open shapes

**`SEGINFO`** builds one packed word and returns it. The four `STP` stores
partition a 16-bit word exactly -- width 8 at bit 0, width 4 at bit 8,
width 1 at bit 12, width 3 at bit 13 -- which is the p-System codefile's
segment-info word: a segment number, a machine type, a spare bit and a
version. It stores machine type 2, then 1 instead if a test involving
`FLIPBYTES` passes, then the segment number from `SEGTABLE[FSEG]`, then
version 6. What is not yet explained is the test: it reads byte 0 of the
result word *before* anything has been stored there.

**`HOLDMOST` and `HOLDROUT`** have a shape no ordinary statement produces:

```
        UJP Lload
Lbody:  <the body>
        UNLOADSEGMENT 15,14,13,12,11,19,9,8
        UJP Lend
Lload:  LOADSEGMENT 8,9,19,11,12,13,14,15
        UJP Lbody
Lend:   RNP 0
```

The loads and unloads nest perfectly, and the load block sits *after* the
body in the code stream with an entry jump over it -- which is what a
one-pass compiler does when it only learns the segment set after compiling
the body. `HOLDROUT` is the same with segment 10 alone, and `HOLDMOST`'s
body is `IF <g34> THEN COMPILE ELSE HOLDROUT`. `(*$S+*)`, swapping mode, is
on in `compiler.text:3`. What is not yet identified is the source
construct that names those eight segments, since neither body calls a
segment procedure.

## 66. HOLDMOST and HOLDROUT hold exactly what their names say

The segments the two of them keep resident are recoverable, because each
segment carries its own number in the last byte of its code. The
correspondence between the codefile's dictionary slots and the compiler's
segment numbers is:

| slot | name | segment | slot | name | segment |
|---|---|---|---|---|---|
| 1 | PASCALCO | 1 | 9 | BODY1 | 14 |
| 2 | COMPINIT | 7 | 10 | BODY3 | 15 |
| 3 | DECLARAT | 8 | 11 | WRITELIN | 16 |
| 4 | BODYPART | 9 | 12 | UNITPART | 17 |
| 5 | ROUTINE | 10 | 13 | COMPOPTI | 18 |
| 6 | STATEMEN | 11 | 14 | NUMSTRIN | 19 |
| 7 | CASESTAT | 12 | 15 | FINISHUP | 20 |
| 8 | FORSTATE | 13 | | | |

`HOLDMOST` loads **8, 9, 19, 11, 12, 13, 14, 15** -- `DECLARAT`,
`BODYPART`, `NUMSTRIN`, `STATEMEN`, `CASESTAT`, `FORSTATE`, `BODY1`,
`BODY3`. That is most of the compiler: everything the body of a compilation
touches repeatedly. `HOLDROUT` loads **10** alone, which is `ROUTINE` --
the name is literal, "hold ROUTine".

`HOLDMOST`'s body is `IF SWAPMORE THEN COMPILE ELSE HOLDROUT`, so the two
differ by exactly one segment: when memory is tight enough that the system
must swap more, `ROUTINE` is not held; otherwise it is held too. Neither
holds `COMPINIT` (7, which has already run), `WRITELIN` (16), `UNITPART`
(17), `COMPOPTI` (18) or `FINISHUP` (20).

The generator is Apple's, not UCSD's. **II.0's compiler never emits `CSP
21` or `CSP 22` at all** -- searching its source for the `GEN1(30,21)` that
would do it finds nothing. Searching the 1.3 *binary* finds it in
`BODY3.2 UNITSEGS`, which emits `GEN1(30,22)` several times over. So the
prologue is generated by a procedure whose name is about units, and the
shape it produces --

```
        UJP Lload
Lbody:  <the body>
        UNLOADSEGMENT 15,14,13,12,11,19,9,8
        UJP Lend
Lload:  LOADSEGMENT 8,9,19,11,12,13,14,15
        UJP Lbody
Lend:   RNP 0
```

-- with the loads emitted *after* the body and jumped over on entry, and
unloads in exact reverse order, is what a one-pass compiler does when it
only learns the segment set after compiling the body. `(*$S+*)` is on in
`compiler.text:3`. **Still open:** what the source writes to name those
eight segments, since neither body calls a segment procedure. Reconstructing
`UNITSEGS` will answer it, so this is blocked on segment `BODY3` and not on
anything in segment 1.

### 66b. SWAPMORE and CONLIST are BOOLEAN

Two more 1.3-only globals that the map named and left as `INTEGER`.
`SWAPMORE` (34) is the condition in `HOLDMOST`, reached by `FJP`; `CONLIST`
(1356) is negated in `ERROR`, `LNOT`. Neither compiles as an `INTEGER`.

### 66c. ERROR, and five Apple edits

```
[1.3] PASCALCO.4 ERROR: 183 instructions, IDENTICAL
```

Against II.0's body:

* **`CONLIST` joins the early-exit test.** `IF LIST AND (ERRORNUM <= 400)
  THEN EXIT(ERROR)` becomes `IF LIST AND NOT CONLIST AND (ERRORNUM <= 400)`
  -- a listing going to the console still stops to report, one going to a
  file does not.
* **The prompt is unconditional.** II.0 guards `' <sp>(continue),
  <esc>(terminate), E(dit'` with `IF NOISY`; Apple always writes it.
* **`ALTMODE` is gone**, replaced by the literal `CHR(27)`. That is the
  other half of finding 63's observation that 1.1 reads `USERINFO.ALTMODE`
  at lex -1 offset 15 and 1.3 never does -- 1.3 does the same comparison
  against a constant.
* **`CLOSE(LP,LOCK)` before the fatal exit.** Apple closes the listing file
  on the `ERRORNUM > 400` path; II.0 leaves it to the main body.
* The `WRITE(OUTPUT,SYMBUFP^:SYMCURSOR)` calls pass the array's declared
  length as a fourth argument (`LDCI 1024`, `LDCI 180`), which is just how
  `FWRITEBYTES` is called and needs nothing in the source.

Twenty-two of segment 1's thirty now match. Eight stubs remain: `INSYMBOL`,
`SEGINFO`, `CONSTANT`, `BLOCK`, `COMMENTER`, `FINDFORW`, `HOLDMOST`,
`HOLDROUT`.

## 67. WITHDRAWN: "the compiler is an ordinary PROGRAM"

> **Wrong, and superseded by finding 68.** The observation below is real --
> a plain `PROGRAM` does reproduce segment 1 / lex 0 / phases from 7 -- but
> it is not the only thing that does, and it is not what Apple used. Under
> `$U-` the phases number from 2 *unless* `{$NS 7}` moves the counter, which
> is exactly what Apple Pascal 1.1 added for the purpose. With it, the `$U-`
> structure of finding 60 reproduces every segment number and every lex
> level exactly. The reasoning below failed because it treated "dummies or
> nothing" as the only way to close the gap.

### 67a. The original (withdrawn) argument

Two compilations of the same four-line program settle it:

```
(*$U-*) PROGRAM P; ... SEGMENT PROCEDURE S1 ... S2 ...
   ->  P = segment 0, lex -1;  S1 = 1, lex 0;  S2 = 2, lex 0
PROGRAM P; ... SEGMENT PROCEDURE S1 ... S2 ...
   ->  P = segment 1, lex  0;  S1 = 7, lex 1;  S2 = 8, lex 1
```

Apple's `SYSTEM.COMPILER` is the second: `PASCALCO` is **segment 1 at lex
0**, its phases are **7..20 at lex 1**, and there is no segment 0 in the
file. A plain program's segment procedures start at 7 because 0..6 belong
to the operating system, and its main gets `PARAM SIZE 4` -- two words --
whatever its header says. Every measurement finding 60 rested on is
reproduced by a plain `PROGRAM`, and finding 55c, which finding 60
overturned, was right.

Finding 60's structure is not harmless, either: under `$U-` the phases
number from 2, and the five-segment gap cannot be closed by declaring
dummies. Empty segment procedures each take a dictionary slot, and
`1 + 1 + 5 + 14 = 21` slots exceeds the format's 16 -- the compiler says so
outright. `FORWARD` does not help: an undefined forward is a fatal error.

**What keeps the `$U-` scaffold in place is finding 63.** The compiler reads
`USERINFO` at lex -1, offsets 8..15, and a plain program cannot name the
system's globals -- only a `$U-` host block can declare them. So the
reconstruction keeps the host as **scaffolding**, and `procbuild.py` records
the one consequence as `SEGOFFSET = 5` and checks every phase against
Apple's number offset by it. How Apple's own source names `USERINFO` from a
plain program is now the open question; the candidates are UCSD's
program-parameter syntax (which `ucsdpsys_compile` will not parse at all)
and a predeclared identifier set up by `COMPINIT`.

### 67b. The phase nesting, from the lex levels

The lex level of each phase's procedure 1 says how deep it is declared, and
nothing else recovers that. Reconstructed and checked:

```
PASCALCOMPILER                 segment 1, lex 0
  COMPINIT                       7, lex 1
  DECLARATIONPART(FSYS)          8, lex 1
  BODYPART(FSYS, FPROCP)         9, lex 1
    ROUTINE(FSYS, FCP, FPROCP)  10, lex 2
    STATEMENT(FSYS)             11, lex 2
      CASESTATEMENT             12, lex 3
      FORSTATEMENT              13, lex 3
      BODY1                     14, lex 3
      BODY3                     15, lex 3
  WRITELINKERINFO               16, lex 1
  UNITPART(FSYS)                17, lex 1
  COMPOPTIONS(STOPPER): BOOLEAN 18, lex 1
  NUMSTRING(FKIND, VAR FVP)     19, lex 1
  FINISHUP                      20, lex 1
```

All fourteen come out at Apple's number and Apple's lex level. Moving
`ROUTINE` out of `BODYPART` to test the check breaks six segments at once,
because everything declared after it shifts.

The signatures are held to Apple's `PARAM SIZE` and to the eight
cross-segment call sites in segment 1 -- `CXP 7,1` and `CXP 20,1` from the
main body, `CXP 8,1`, `CXP 9,1`, `CXP 16,1` and `CXP 17,1` from `BLOCK`,
`CXP 18,1` from `COMMENTER` and `CXP 19,1` from `INSYMBOL`. Two things fall
out of those: `COMPOPTIONS` is a **`SEGMENT FUNCTION`** returning `BOOLEAN`
(`COMMENTER` pushes one argument and two result words, then `LNOT`s the
result), and `WRITELINKERINFO` has **no parameters** where II.0's takes
`DECSTUFF: BOOLEAN`.

## 68. {$NS 7}, and finding 60 reinstated

Neil Parker's *Undocumented Secrets of Apple Pascal* documents `{$U-}`
directly, and it settles every question findings 60 and 67 were circling.
Under `{$U-}` the compiler switches to **system mode**:

* the outermost lex level is **-1** and the main program goes in segment
  **0**;
* `SEGMENT PROCEDURE`s go into segments **1, 2, 3, ...**;
* no space is reserved in the global data area for the main program's
  arguments;
* the error-checking defaults become **`{$G+,I-,R-,V-}`** instead of
  `{$G-,I+,R+,V+}`.

`SYSTEM.PASCAL` ignores segments 0 and 2..6 when it loads a codefile, so a
`$U-` program's real main must be its **first `SEGMENT PROCEDURE`**, which
becomes segment 1 -- and `SYSTEM.PASCAL` calls it with **two word-sized
arguments**. That is `PASCALCO`, its lex 0, its `PARAM SIZE 4`, and the two
words at globals 1 and 2 that findings 59 and 60 chased. Its locals are the
global data segment and everything nests inside it. All of finding 60 stands.

**The gap from 1 to 7 is `{$NS 7}`.** Anything beyond the first segment
procedure has to skip to at least 7 or `SYSTEM.PASCAL` will ignore it; before
Apple Pascal 1.1 you declared dummy segment procedures to fill the gap, and
from 1.1 you write `(*$NS n*)`. Finding 67 concluded the `$U-` structure was
impossible because dummies overflow the 16-slot dictionary -- true, and
irrelevant, because `$NS` costs no slots at all.

With one `(*$NS 7*)` before `COMPINIT`, Apple's own compiler puts every
phase exactly where Apple's binary has it:

```
PASCALCO 1/lex 0   BODYPART 9/lex 1    BODY3    15/lex 3   COMPOPTI 18/lex 1
COMPINIT 7/lex 1   ROUTINE 10/lex 2    WRITELIN 16/lex 1   NUMSTRIN 19/lex 1
DECLARAT 8/lex 1   STATEMEN 11/lex 2   UNITPART 17/lex 1   FINISHUP 20/lex 1
                   CASESTAT 12/lex 3
                   FORSTATE 13/lex 3
                   BODY1    14/lex 3
```

Fourteen segments, fourteen exact hits on both number and nesting depth, and
all 22 reconstructed bodies still identical. `ucsdpsys_compile` rejects
`$NS` -- it targets II.0/II.1 -- so the fast tier compiles without it and
its phases come out five low; `procbuild.py` accounts for that and Apple's
compiler is the authority regardless.

### 68b. Two corrections that follow

* **`{$I-}` is `$U-`'s default, not `$T+`'s doing.** Finding 65b got the
  effect right -- `PRINTLINE` needs `(*$I+*)` and nothing else does -- but
  attributed the unchecked default to `compiler.text`'s `(*$T+*)`. It is
  `$U-`: system mode defaults to `{$G+,I-,R-,V-}`.
* **Finding 63's `USERINFO` is exactly what `$U-` is *for*.** Parker: a
  `$U-` program declares `SYSTEM.PASCAL`'s globals at the top level and the
  compiler compiles correct lex -1 references to them, which a normal
  program cannot reach at all. His byte offsets confirm the reconstruction
  independently -- `SYSCOM` at 0, `GFILES` at 2, `USERINFO` at **14 bytes =
  word 8** -- and his `INFOREC` listing gives `CODEFIBP` 0, `SYMFIBP` 2,
  `ERRNUM` 4, `ERRBLK` 6, `ERRSYM` 8, `STUPID` 10, `SLOWTERM` 12, `ALTMODE`
  14, which is finding 63's table word for word, backward field allocation
  and all. So the host block is not scaffolding after all: it is what
  Apple's source has.

## 69. COMMENTER and FINDFORW

Both are Apple's own -- II.0 has nothing like either -- and both were
recovered from the p-code alone.

### 69a. COMMENTER

```
[1.3] PASCALCO.28 COMMENTER: 58 instructions, IDENTICAL
```

```pascal
PROCEDURE COMMENTER(STOPPER: CHAR);
  VAR CH: CHAR;
BEGIN
  SYMCURSOR := SYMCURSOR+1;
  IF SYMBUFP^[SYMCURSOR] = '$' THEN
    IF NOT COMPOPTIONS(STOPPER) THEN EXIT(COMMENTER);
  SYMCURSOR := SYMCURSOR-1;
  REPEAT
    REPEAT
      SYMCURSOR := SYMCURSOR+1;
      WHILE SYMBUFP^[SYMCURSOR] = CHR(EOL) DO CHECKEND
    UNTIL SYMBUFP^[SYMCURSOR] = STOPPER
  UNTIL (SYMBUFP^[SYMCURSOR+1] = ')') OR (STOPPER = '}');
  SYMCURSOR := SYMCURSOR+1
END;
```

II.0 scans compiler options inline, with its own `SCANSTRING` and a long
`CASE`. Apple's hands the whole job to segment 18 -- `CXP 18,1` -- and
`EXIT(COMMENTER)`s if it returns false. That call is what identifies
`COMPOPTIONS` as a **`SEGMENT FUNCTION`** returning `BOOLEAN`: one argument
pushed, two result words reserved, and `LNOT` applied to what comes back.

Two shapes had to be got exactly right, and neither is visible to a reader:

* **The two `REPEAT`s are nested, not one `UNTIL A AND B`.** Written flat,
  Apple's compiler emits `LAND` on the two halves; the binary tests the
  first and branches, then tests the second and branches, both to the same
  loop top. That only happens with an inner `REPEAT ... UNTIL A` inside an
  outer `REPEAT ... UNTIL B`. Same lesson as finding 64's nested `IF`.
* **`CH` is declared and never referenced.** Every instruction matched with
  `DATA SIZE` 0 against Apple's 2. II.0's `COMMENTER` declares `CH` first of
  four locals, so it is the likeliest survivor of the rewrite -- but only
  the frame says it is there at all. That is the second such variable in the
  segment, after `GETNEXTPAGE`'s.

### 69b. FINDFORW

```
[1.3] PASCALCO.29 FINDFORW: 56 instructions, IDENTICAL
```

```pascal
FUNCTION FINDFORW(FCP: CTP): BOOLEAN;
BEGIN FINDFORW := FALSE;
  IF FCP <> NIL THEN
    WITH FCP^ DO
      BEGIN
        IF KLASS IN [PROC,FUNC] THEN
          IF PFDECKIND = DECLARED THEN
            IF PFKIND = ACTUAL THEN
              IF FORWDECL THEN
                BEGIN FINDFORW := TRUE;
                  WRITELN(OUTPUT);
                  WRITE(OUTPUT,NAME:8,' undefined')
                END;
        IF FINDFORW(RLINK) OR FINDFORW(LLINK) THEN FINDFORW := TRUE
      END
END;
```

It walks the symbol tree and reports every procedure declared `FORWARD` and
never defined. `CIP 29` -- a call to itself at its own lexical level --
recurses down `RLINK` then `LLINK`, in that order.

The four tests are **four nested `IF`s**, not an `AND` chain: the binary has
four separate `FJP`s to the same label. And they land on the identifier
record exactly where finding 33's reverse allocation puts them --
`IND 8` = `KLASS`, `IND 9` = `PFDECKIND`, `IND 13` = `PFKIND`, `IND 15` =
`FORWDECL` -- with `SIND 4` = `RLINK` and `SIND 5` = `LLINK`, the reversed
pair `LLINK, RLINK: CTP` that `ENTERID` first measured.

Twenty-four of segment 1's thirty now match. Six stubs remain: `INSYMBOL`,
`SEGINFO`, `CONSTANT`, `BLOCK`, `HOLDMOST`, `HOLDROUT`.

## 70. BLOCK, and where SEGTABLE's ninth word went

```
[1.3] PASCALCO.26 BLOCK: 303 instructions, IDENTICAL
```

Structurally II.0's, with six edits the binary states:

* **`SY IN [UNITSY,SEPARATSY]` becomes `SY = UNITSY`**, in both places.
* **The `USES` path is gated on memory.** Where II.0 goes straight into
  `UNITPART`, Apple writes `IF SWAPPING OR HAS128K THEN ... ELSE
  ERROR(408)` -- units need one or the other.
* **`ISPROG := NOT INMODULE`** is new, and so is `RESIDENT := NIL` at the
  head of each block.
* **`FINDFORW` returns a result.** II.0's sets `USERINFO.ERRNUM := 117`
  itself; Apple's returns `BOOLEAN` and the caller writes `IF
  FINDFORW(DISPLAY[TOP].FNAME) THEN ERROR(117)` (finding 69b).
* **The linker-info branch is collapsed.** II.0 tests `DLINKERINFO AND
  (LEVEL = 1)` then `CLINKERINFO`, writing `SEGKIND := 2` and calling
  `WRITELINKERINFO(TRUE)` or `(FALSE)`. Apple has one test, `LINKINFO AND
  (LEVEL = 1)`, sets `SEGKIND := 1`, and calls `WRITELINKERINFO` with no
  argument at all -- which is why its `PARAM SIZE` is 0 (finding 67b).
* **`RELEASE` is guarded**: `IF TOS^.DFPROCP <> OUTERBLOCK THEN
  RELEASE(TOS^.DMARKP)`. II.0 releases unconditionally.

Also gone: II.0's `IF (NOSWAP) AND (STARTINGUP)` shortcut into `BODYPART`,
its `- [ENDSY]` on the `BODYPART` argument, and the `FINISHSEG`/`ERROR(13)`
arms of the `INMODULE` early exit, which Apple reduces to `IF SY IN
[ENDSY,BEGINSY] THEN EXIT(BLOCK)`.

Five globals were retyped from what `BLOCK` does with them: `ISPROG`,
`SWAPPING`, `HAS128K` and `LINKINFO` are `BOOLEAN`, and `RESIDENT` is a
pointer -- it is assigned `NIL`, and nothing recovered yet dereferences it.

### 70b. The ninth word of SEGTABLE is inside the last field list

Finding 54 established that Apple's segment-table entry is nine words where
UCSD's is eight, and `varblock.py` declared the extra word as a tenth field
appended at the end. **It is not appended -- it is inside the last identifier
list.** `BLOCK`'s

```pascal
SEGTABLE[SEGMAP[SEG]].SEGKIND := 1
```

compiles to `INC 8`, and under finding 33's reverse allocation only a
three-name list puts `SEGKIND` at 8:

```pascal
RECORD DISKADDR,CODELENG: INTEGER;      { CODELENG 0, DISKADDR 1 }
       SEGNAME: ALPHA;                  { 2..5 }
       SEGKIND, TEXTADDR, SEGSPARE: INTEGER   { SEGSPARE 6, TEXTADDR 7, SEGKIND 8 }
END
```

`FINISHSEG` pins the other end independently -- `SEGTABLE[...].CODELENG`
compiles to `IXA 9` with no field offset, so `CODELENG` is 0, the reversed
first pair. One instruction out of `BLOCK`'s 303 was the whole difference,
and it moved a field that six earlier bodies had never touched.

Twenty-five of segment 1's thirty now match. Five stubs remain: `INSYMBOL`,
`SEGINFO`, `CONSTANT`, `HOLDMOST`, `HOLDROUT`.

## 71. The word Apple added to SEGTABLE is SEGNUM

Finding 70b found *where* the ninth word sits -- offset 6, a third name on
the last identifier list -- and left it unnamed. It is the **segment
number**, and three independent things say so.

**The compiler reads it in exactly one place.** Sweeping both binaries for
`LAO <SEGTABLE> / <slot> / IXA 9` and the field access that follows gives:

```
        field 0 CODELENG   COMPINIT, GETTEXT, PROCDECLARATION, FINISHSEG, UNITPART x2
        field 1 DISKADDR   BODY3, INITSCALARS, FINISHUP
        field 2 SEGNAME    FINISHUP, UNITDECLARATION
1.1/1.3 field 6 SEGNUM     SEGINFO          (and FINISHUP, in 1.1 only)
        field 7 TEXTADDR   FINISHUP
        field 8 SEGKIND    FINISHUP, BLOCK, UNITPART
```

**`SEGINFO` puts it in bits 0..7 of the codefile's segment-info word.** Its
four `STP` stores partition one 16-bit word exactly, and the codefile
Apple shipped has the matching layout -- reading `SYSTEM.COMPILER`'s own
segment dictionary at byte 256:

```
slot  1 $C701  segnum= 1  mtype=7  ver=6      <- PASCALCO
slot  2 $C207  segnum= 7  mtype=2  ver=6      <- COMPINIT
...
slot 15 $C214  segnum=20  mtype=2  ver=6      <- FINISHUP
```

segment number in bits 0..7, machine type in 8..11, a spare bit at 12,
version 6 in 13..15 -- which is `SEGINFO` store for store, including the
literal 6 and the 0 in the spare bit. `PASCALCO`'s `mtype` is 7 where every
other segment's is 2, because it is the one segment carrying 6502 code
(`IDSEARCH` and `TREESEARCH`), and `SEGINFO` chooses between two machine
types on a test involving `FLIPBYTES`.

**And UCSD had no need of the field.** In II.0 a segment's dictionary slot
*is* its number, so the table never has to record one. Apple's `SEGMAP`
decouples them -- 64 segment numbers into 16 slots (finding 62) -- so each
slot must say which segment occupies it. The added word and `SEGMAP` are
two halves of the same change, and both are already present in 1.1.

```pascal
SEGTABLE: ARRAY [SEGRANGE] OF
            RECORD
              DISKADDR,CODELENG: INTEGER;      { CODELENG 0, DISKADDR 1 }
              SEGNAME: ALPHA;                  { 2..5 }
              SEGKIND, TEXTADDR, SEGNUM: INTEGER  { SEGNUM 6, TEXTADDR 7, SEGKIND 8 }
            END;
```

II.0's list is `SEGKIND, TEXTADDR`; Apple's is the same list with one name
appended, which under reverse allocation moves both of UCSD's fields up by
one and puts the new one at the bottom. All 25 verified bodies still
compile identically with the field renamed, as they must -- a name changes
no bytes.

**Still open:** nothing in the compiler is seen *writing* `SEGNUM` through
that path, so it is set some other way -- most likely as part of a
whole-entry store in `COMPINIT` or `DECLARATIONPART`. And `SEGINFO`'s test
still reads bits 0..7 of its result word before anything has been stored
there, which no reading of the source explains yet.

## 72. INSYMBOL, and a literal tab in the source

```
[1.3] PASCALCO.8 INSYMBOL: 261 instructions, IDENTICAL
```

The scanner. Structurally II.0's, with the three nested procedures gone --
`CHECKEND` promoted to a procedure of its own (number 14), `NUMBER` and
`STRING` moved out to segment 19 -- and one addition.

**Apple inlined a fast path for small integers.** Where II.0's digit arm
just calls `NUMBER`, Apple's accumulates up to four digits itself and only
falls back to the segment when the token cannot be a plain `INTCONST`:

```pascal
'0','1','2','3','4','5','6','7','8','9':
     BEGIN
       LCH := SYMBUFP^[SYMCURSOR];
       LI := 0; LVAL := 0;
       WHILE (LCH IN ['0'..'9']) AND (LI < 4) DO
         BEGIN
           LVAL := LVAL*10 + (ORD(LCH) - ORD('0'));
           LI := LI+1;
           LCH := SYMBUFP^[SYMCURSOR+LI]
         END;
       IF LCH IN ['.','0'..'9','E'] THEN NUMSTRING(1,LVP)
       ELSE
         BEGIN
           SYMCURSOR := SYMCURSOR+LI-1;
           SY := INTCONST; OP := NOOP;
           VAL.IVAL := LVAL
         END
     END;
```

The `['.','0'..'9','E']` set is read straight out of the binary's five-word
set constant -- bits 46, 48..57 and 69 -- and is exactly the characters that
can continue a number into a real or a long. Four digits is what fits without
risking overflow. `NUMSTRING(0,LVP)` handles the string arm and
`NUMSTRING(1,LVP)` the number arm, which is what fixes the sense of that
phase's first parameter.

**A case label cannot be `CHR(9)`, and neither can a constant.** Both were
put to Apple's compiler:

```pascal
CONST TABCH = CHR(9);        { Line 1, error 103 -- at CHR }
  ...  CASE C OF TABCH,' ':  { same, if the CONST were allowed }
```

`error 103` is *"identifier is not of the appropriate class"*. Apple Pascal
wants a **literal** in both places; `CHR(n)` is a function call and is
rejected in a constant definition exactly as it is in a case label, so there
is no way to give the character a name.

One alternative does compile -- `CASE ORD(SYMBUFP^[SYMCURSOR]) OF 9,32,...`
with integer labels throughout, which Apple's compiler accepts. It is not
used here: it would rewrite all sixty-odd labels away from the character
form II.0 uses, and Apple's source descends from II.0's. The literal tab
matches what II.0 has and reproduces Apple's bytes, so it is both the
simpler and the better-evidenced reading.

**Carrying the literal tab.** II.0's whitespace arm is `' ',' '` --
space and a literal *tab*, which the II.0 source file carries as the
character itself. Writing it as `CHR(9)` is a function call, and Apple's
compiler rejects it as a case label with `error 103`. So the reconstruction
has to carry a real 0x09 through the whole pipeline, and two tools had to
learn that:

* `expand_tabs` now leaves a tab alone **inside quotes**. Its job is
  indentation, where UCSD uses a DLE pair and a 0x09 is a modern editor's
  doing; a quoted one is data.
* `encode_text` now accepts TAB, and only TAB, among the control characters.
  It is a legal `.TEXT` byte and `decode_text` already passed it through.

`probe_diskwrite` keeps the refusal check with `BEL` instead and adds a
round-trip for TAB, so the narrower rule is still held to something.

One fast-tier difference worth naming, because it made the diff useless
rather than merely noisy: **the fast tier emits `CASE` arms sorted by label
value, Apple emits them in source order.** With a `'<tab>'` label at 9 the
whole body shifted and 230 of 261 instructions "differed". Apple's jump
table is `XJP 9..123`, and its arm addresses ascend in exactly II.0's source
order.

Twenty-six of segment 1's thirty now match. Four stubs remain: `SEGINFO`,
`CONSTANT`, `HOLDMOST`, `HOLDROUT`.

## 73. CONSTANT, and a field list read back-to-front

**VERIFIED BINARY FACT.** `PASCALCO.20 CONSTANT` now compiles to 320
instructions identical to Apple's, under Apple's own 1.3 compiler.

II.0's body is right for everything except the two long-integer arms, and
one of the two is a bug II.0 shipped and Apple fixed.

### 73a. The extra local is a `FOR` counter

Finding 64c read the frame right: Apple's `DATA SIZE` is 12 (six words) and
the `WITH LCP^` temporary lands at local **12**, so five locals are declared
where II.0 declares four. The fifth is an `INTEGER` at local 11, and it is a
loop counter -- `SLDC 1 / STL 11`, `SLDL 11 / SLDL 12 / LEQI`, `SLDL 11 /
SLDC 1 / ADI / STL 11`. A UCSD `FOR` counter has to be a declared variable,
which is why it is a local and not a temporary; the *limit* is a temporary
and reuses local 12, the same slot the `WITH` uses.

Local order follows the declaration groups going forward -- `LSP` 7, `LCP`
8, `SIGN` 9, `LVP` 10 -- so the new one is declared last:

```pascal
VAR LSP: STP; LCP: CTP; SIGN: (NONE,POS,NEG);
    LVP: CSP; I: INTEGER;
```

Its name is not recoverable from p-code; `I` is a **SPECULATION** that
costs nothing, since the identifier does not reach the codefile.

### 73b. `LLENG,LLAST` allocates back-to-front, and Apple's loop wants LLENG

The negation loop reads its limit with `SIND 2` and addresses the array
with `INC 3`. Writing II.0's `LLAST` produced `SIND 1` instead -- the only
divergence in the whole procedure, in both arms.

`CONSTREC`'s `LONG` variant is

```pascal
LONG: (LLENG,LLAST: INTEGER; LONGVAL: ARRAY[1..9] OF INTEGER);
```

with the named tag `CCLASS` at offset 0. That accounts for `LONGVAL` at 3
and for the `NEW(LVP,LONG)` size of 12 words, both of which matched from the
start. It leaves offsets 1 and 2 for `LLENG` and `LLAST` -- and **finding
33's reverse allocation applies to a record field list**, so the list
`LLENG,LLAST` puts `LLAST` at 1 and `LLENG` at 2.

So Apple's `SIND 2` is `LLENG`, and the loop is

```pascal
FOR I := 1 TO LVP^.LLENG DO
  LVP^.LONGVAL[I] := -LVP^.LONGVAL[I];
```

which is also the reading that makes sense: `LLENG` is how many words the
long constant occupies, and every one of them is negated. This is an
independent confirmation of finding 33 from a record rather than a `VAR`
block -- the check could have failed and did, once, before the field was
corrected.

The same shape appears twice, once on `LVP^` in the `IDENT` arm and once on
`VAL.VALP^` in the `LONGCONST` arm.

### 73c. II.0's LONGCONST arm never handled an unsigned long constant

II.0 has the entire arm inside the sign test:

```pascal
IF SY = LONGCONST THEN
  BEGIN
    IF SIGN = NEG THEN
      BEGIN VAL.VALP^.LONGVAL[1] := - VAL.VALP^.LONGVAL[1];
        NEW(LSP,LONGINT);
        LSP^.SIZE := DECSIZE(LGTH);
        ...
      END
  END
```

so a positive long constant falls out with `LSP` still `NIL`, `FVALU`
unset, and no `INSYMBOL` -- the scanner does not advance. Apple's `FJP` at
`$0AD5` and the loop exit both land on `$0B00`, where the `NEW` is, so only
the negation is conditional:

```pascal
IF SY = LONGCONST THEN
  BEGIN
    IF SIGN = NEG THEN
      FOR I := 1 TO VAL.VALP^.LLENG DO
        VAL.VALP^.LONGVAL[I] := -VAL.VALP^.LONGVAL[I];
    NEW(LSP,LONGINT);
    LSP^.SIZE := DECSIZE(LGTH);
    LSP^.FORM := LONGINT;
    FVALU := VAL;
    INSYMBOL
  END
```

### 73d. The named-constant arm copies the whole record first

II.0 negates in place through a fresh node whose class it sets by hand.
Apple allocates the `LONG` variant, copies the source node over it whole,
then negates:

```pascal
BEGIN NEW(LVP,LONG);
  LVP^ := FVALU.VALP^;
  FOR I := 1 TO LVP^.LLENG DO
    LVP^.LONGVAL[I] := -LVP^.LONGVAL[I];
  FVALU.VALP := LVP
END
```

`NEW(LVP,LONG)` is `SLDC 12`, the size of the `LONG` variant, but the
record assignment is `MOV 130` -- the size of the *whole* variant record,
which is what the `STRG` arm needs and what the untagged `NEW(LVP)` in the
string branch allocates. **Apple's compiler copies 130 words into a
12-word node.** The overrun is real and is Apple's, not a reconstruction
artifact: the bytes are identical. It is harmless in practice only because
the compiler's heap is allocated forward and the node is the most recent
one, so the words past it are unallocated at the moment of the copy.

Twenty-seven of segment 1's thirty now match. Three stubs remain:
`SEGINFO`, `HOLDMOST`, `HOLDROUT`. (`SEGINFO` falls in finding 74.)

## 74. SEGINFO is a function, and it builds the 1.3 dictionary word

**VERIFIED BINARY FACT.** `PASCALCO.15 SEGINFO` now compiles to 47
instructions identical to Apple's. Twenty-eight of segment 1's thirty.

### 74a. The signature was wrong

The forward block carried `PROCEDURE SEGINFO(FSEG: INTEGER; VAR
FADDR,FLENG: INTEGER)`, a guess from the name. The frame says otherwise:
`PARAM SIZE 6`, three words, and the last thing the body does is `SLDL 5 /
STL 1` -- a store into local 1, which for a procedure would be a parameter
and for a function is the result. A UCSD function reserves **two** words for
its result regardless of the result's actual size (`COMPTYPES` returns
`BOOLEAN` and also has two), so three words is two of result plus one
parameter:

```pascal
FUNCTION SEGINFO(FSEG: INTEGER): INTEGER;
```

`FSEG` is local 3, and it indexes `SEGTABLE` with `IXA 9 / SIND 6` --
Apple's stride, and `SEGNUM` at offset 6, exactly as finding 71 has it.

### 74b. The result is the segment dictionary's SEGINFO word

`DATA SIZE 4` is two locals: a `BOOLEAN` at 4 and, at 5, a word that gets
written four times with `STP`. The four stores partition the word exactly:

| width | right bit | bits | value |
|---|---|---|---|
| 8 | 0 | 0..7 | `SEGTABLE[FSEG].SEGNUM` |
| 4 | 8 | 8..11 | 2, or 1 |
| 1 | 12 | 12 | 0 |
| 3 | 13 | 13..15 | 6 |

That is the word Apple 1.3 added to the codefile's segment dictionary, and
`codefile.py` has read the same layout out of the file since long before
this procedure was reconstructed -- "bits 0-7 segnum, bits 8-11 mtype, bits
13-15 version". The two sides were derived independently and agree.

**Incidentally this fixes the operand order for `STP`.** The disassembler
prints the three words below the value as pushed, and only one reading
partitions 16 bits: the *last* push is the right bit and the one before it
is the field width. Read the other way round, the `SLDC 8 / SLDC 0` store
would have width 0.

### 74c. A function cannot return a record, so the record has a word variant

The obvious source -- a `PACKED RECORD` local returned directly -- does not
compile. Apple's own compiler answers `error 120` on

```pascal
FUNCTION F(FSEG: INTEGER): SEGINFOREC;
```

*result type of function must be scalar, subrange or pointer.* So the word
has to be reached through a variant, which is also what `SLDC 0 / STL 5`
(clearing the whole word) and `SLDL 5 / STL 1` (returning it) require:

```pascal
TYPE SEGINFOREC = PACKED RECORD CASE INTEGER OF
                    0: (WORDVAL: INTEGER);
                    1: (SEGNUM: 0..255; MTYPE: 0..15;
                        UNUSED: 0..1; VERSION: 0..7);
                    2: (BYTES: PACKED ARRAY [0..1] OF 0..255)
                  END;
```

The three variants are each forced by a distinct instruction -- the word by
`STL 5`/`SLDL 5`, the bit fields by the four `STP`s, and the byte array by
the `LDB` in 74d. The **field names** are not recoverable from p-code;
`SEGNUM`, `MTYPE` and `VERSION` are the documented names for this word's
fields and are used here, `WORDVAL`, `UNUSED` and `BYTES` are
**SPECULATION** and cost nothing, since no identifier reaches the codefile.
Whether Apple declared the type inside the function or among the globals is
likewise invisible; it is local here because nothing else uses it.

### 74d. The mystery read is dead code, and it is Apple's

The open question from the earlier pass -- *"SEGINFO reads bits 0..7 of its
result word before anything is stored there"* -- is now pinned down
mechanically. The instruction is `LLA 5 / SLDC 0 / LDB`, a **byte** load,
not a packed-field load: reading `LINFO.SEGNUM` compiles to `LDP`, and only
indexing a byte array gives `LDB`. So the source is `LINFO.BYTES[0]`.

What it computes is nothing. The word was cleared two statements earlier and
only bits 8..11 have been written, so byte 0 is 0 and `LMSB` is always
`FALSE`:

```pascal
LINFO.WORDVAL := 0;
LINFO.MTYPE := 2;
LMSB := LINFO.BYTES[0] <> 0;
IF FLIPBYTES THEN LMSB := LMSB = FALSE;
IF LMSB THEN LINFO.MTYPE := 1;
```

The net effect is `MTYPE := 2, or 1 when FLIPBYTES` -- P-code LSB normally,
P-code MSB when the compiler is byte-flipping its output. The three
statements that get there are a residue of something else. This is Apple's
code, not a reconstruction artifact: the bytes are identical, including the
`SLDC 0 / EQU BOOL` that says Apple wrote `LMSB = FALSE` where `NOT LMSB`
would have compiled to a single `LNOT`.

## 75. FINISHUP, the first phase segment, and a constant that doubled

**VERIFIED BINARY FACT.** `FINISHUP`, segment 20, compiles to 323
instructions identical to Apple's. It is the first of the fourteen phases
to be reconstructed, and the first procedure verified that is not in
segment 1.

In UCSD II.0 it is not a procedure at all. It is the tail of
`PASCALCOMPILER`'s own body -- `block.text:120-163`, from `IF SY <> PERIOD
THEN ERROR(21)` to the last `WRITECODE(TRUE)`. Apple lifted it into a
`SEGMENT PROCEDURE` so the code is not resident while the compile runs.

### 75a. MAXCODE 1299 -> 1999: the code buffer doubled

II.0 declares

```pascal
CODEARRAY = PACKED ARRAY [0..MAXCODE] OF CHAR;
```

with `MAXCODE = 1299`, which is 650 words. **1.1 asks `NEW(CODEP)` for
exactly 650**, at all three of its call sites. **1.3 asks for 1000**, at
all three of its. 1000 words is 2000 bytes, so 1.3's bound is 1999.

This is the cleanest sort of constant evidence there is: the same
instruction in the same three places in both releases, differing only in
the operand, and one of the two operands is the arithmetic of a constant we
already had from II.0. It is now in `applesrc.py`'s `CONSTS` alongside
`MAXJTAB` and `MAXPROCNUM`.

### 75b. Apple's edits to II.0's tail

Six, and no more:

1. **`UNITWRITE(3,IC,7)` is gone.** II.0 has it between the `TIME` call and
   the linker-info test; 1.3's `FJP` on `LINKINFO` follows `SRO 97`
   directly.
2. **`DLINKERINFO OR CLINKERINFO` collapsed to one flag.** Apple tests a
   single global, `LINKINFO`.
3. **`SEGTABLE[SEG]` became `SEGTABLE[SEGMAP[SEG]]`.** The `IXP 4,4 / LDP`
   is the packed nibble lookup of finding 70; `SEG` no longer indexes the
   table directly.
4. **`WRITELINKERINFO` lost its argument.** II.0 passes `TRUE`; the `CXP
   16,1` pushes nothing.
5. **`RELEASE(MARKP)` and two `CLOSE`s were added** before the summary is
   printed -- the symbol table goes back to the heap, then `NEW(CODEP)`
   takes a clean buffer for the dictionary.
6. **The segment names are written with one `MOVELEFT`.** II.0 has `FOR
   LGTH := 1 TO 8 DO GENBYTE(ORD(SEGNAME[LGTH]))`; Apple moves eight bytes
   into `CODEP^[IC]` and adds 8 to `IC` itself.

### 75c. The dictionary grew, and the padding is now a loop with a check

II.0 writes the segment dictionary as a fixed 256 words and pads with a
counted loop whose length is arithmetic on `MAXSEG`:

```pascal
FOR LGTH := 1 TO 256 - 8*(MAXSEG + 1) - 40 DO GENWORD(0);
```

Apple adds a sixteen-word `SEGINFO` array (finding 74) and a four-word
`SEGSUSED`, which would overrun that arithmetic, and replaces it with a
bound and a guard:

```pascal
IF IC >= 432 THEN ERROR(407);
WHILE IC < 432 DO GENBYTE(0);
```

432 plus the 80-byte comment is 512, the block. The `ERROR(407)` is a real
check on Apple's own layout: add one more array to the dictionary and the
compiler says so rather than writing past the block.

`SEGSUSED` is written through `PROCTABLE`: `MOVELEFT(SEGSUSED,PROCTABLE,8)`
and then four `GENWORD(PROCTABLE[i])`. The copy is needed because
**`SEGSUSED` is a `SET`, not the `ARRAY [0..3] OF INTEGER` the VAR block
currently declares** -- `BODY3` compares it with `NEQ SET` against `[]`.
A set cannot be indexed, so Apple lands it in a dead array and writes the
words out of that. The declaration is left alone here because `FINISHUP`
only `MOVELEFT`s it and cannot tell the difference; `BODY3` is what will
force it.

### 75d. The harness now compiles a phase's own body

A phase's body is **procedure 1 of its segment** -- the segment procedure
itself -- and `sources()` numbers the procedures it reads from 2, because
procedure 1 is never declared in those files. So phase bodies get their own
directory, `src/pascal/<ver>/phases/`, read by `phase_body()` and diffed by
`report_phases()`. They are not beside `PASCALCO.text` because `sources()`
globs that directory and would splice them a second time at the outer
level.

Thirteen phases remain. The four under `STATEMENT` -- `CASESTAT`,
`FORSTATE`, `BODY1`, `BODY3` -- read their enclosing frames with `LOD 1,n`
and `LOD 2,n`, so none of them can be written before `BODYPART` and
`STATEMENT` have their locals. That is also what still blocks `HOLDMOST`
and `HOLDROUT`, the last two stubs in segment 1.

## 76. A size that was fitted, not explained: PUBLIC and IMPORTED are there

### 76a. `NEW` allocates by its tag list, not by the type

**VERIFIED BINARY FACT** for the seven sizes; **VERIFIED SOURCE FACT** for the
tag lists; and it **retracts finding 54b**.

Finding 22c read seven `identifier` record sizes out of `SYSTEM.COMPILER` --
**9, 10, 11, 11, 13, 18, 18** for `klass` 0..6. UCSD's declaration, laid out
as written, gives 9, 10, **12, 12**, 13, **19, 19**. Finding 54b closed the
four-word gap by deleting two fields, `PUBLIC` from the end of the
`FORMALVARS`/`ACTUALVARS` variant and `IMPORTED` from the end of the
`DECLARED`/`ACTUAL` path, and said so as STRONG INFERENCE while noting:

> What would settle it is offsets rather than sizes.

`WRITELIN` settles it, and against the deletion. Its `GLOBALSEARCH` reads
**`IND 11`** off an identifier in the `FORMALVARS`/`ACTUALVARS` arm, as a
BOOLEAN, to choose between a `PUBBLIC` and a `PRIVVATE` linker record --
exactly what II.0 uses `PUBLIC` for, at exactly the word `PUBLIC` occupies,
with `VLEV` at 9 and `VADDR` at 10 on either side of it. 1.1 does the same at
its own `$018E`. **The field is there in both releases.**

What was wrong was never the declaration. It was the assumption that a record
is allocated by its type. **UCSD allocates by the tag list the `NEW` call
supplies**, and a tag that selects an *empty* arm allocates nothing for it.
Every one of the four short `klass` values is built by a `NEW` whose last tag
selects the empty arm of a trailing `CASE BOOLEAN OF TRUE: (...)`, and II.0
writes those tags itself:

> Refined by **finding 80b**. This section first said the walk stops at the
> last tag given and that anything below it contributes nothing. It stops at
> an empty *arm*; where the tag list simply runs out, the largest remaining
> arm is allocated, exactly as for an untagged pointer. Every example below
> supplies the empty label explicitly, so none of them distinguishes the two
> readings and none of the sizes changes.

    NEW(CP,TYPES)                          9
    NEW(CP,KONST)                         10
    NEW(CP,FORMALVARS,FALSE)              11     <- PUBLIC not allocated
    NEW(UVARPTR,ACTUALVARS,FALSE)         11     <- PUBLIC not allocated
    NEW(LCP,FIELD,TRUE)                   13
    NEW(UPRCPTR,PROC,DECLARED,ACTUAL,FALSE)   18 <- IMPORTED not allocated
    NEW(UFCTPTR,FUNC,DECLARED,ACTUAL,FALSE)   18 <- IMPORTED not allocated

**9, 10, 11, 11, 13, 18, 18, with the record untouched.** The two fields exist,
are declared, and are simply not paid for by the calls that make the objects
finding 22c watched.

The trailing `FALSE` in `NEW(CP,FORMALVARS,FALSE)` is not decoration, then. It
is a word of heap, and UCSD's own initialiser is written to save it.

### 76b. Two words of Apple's `MODULE` variant

**VERIFIED BINARY FACT** for the offsets and their type; the names are
**not recovered**.

`GLOBALSEARCH`'s `MODULE` arm reads three fields, not UCSD's one: `SEGID` at
9, and two more at **10 and 11**, both BOOLEAN, both `LAND`ed into the test
that decides whether a used unit gets a `MODDULE` record at all --

    IF INMODULE AND NOT INTRINSIC AND <10> AND <11> THEN

Both releases read both. Nothing recovered so far says what they are, so they
are declared and not named -- `MODUNK10`, `MODUNK11` -- on the same principle
`SEGTABLE`'s ninth word was carried under before finding 71 identified it.
They are declared as two statements rather than one list so they allocate
forward (finding 33).

### 76c. What this costs, and what it does not

Nothing. `identifier` is only ever reached through `CTP`, so its size is not
in any global offset, and no reconstructed body allocates one: the whole of
the change is two fields back in the TYPE block. Re-running the 29 bodies
already verified against Apple's own compiler under the corrected
declarations returns 29 of 29, unchanged.

`applesrc.py` loses `DROP_FIELDS` and gains `TYPE_EDITS`, which is the same
mechanism pointed the other way -- what Apple has that UCSD does not, rather
than the reverse. `reclayout.py` gains `Layout.new_size(type, *tags)`, the
tagged rule, beside `record_variants`, the untagged one.

`probe_record_layout.py` now reads the tag lists out of II.0's own `NEW` call
sites instead of being handed them, and requires three things: that each
binary size is one some tag list in the compiler actually produces, that the
untagged rule does **not** reproduce them (or the tag path would be explaining
nothing), and that `PUBLIC` lands on word 11 where `WRITELIN` reads it.

The lesson is the one the probe's own docstring used to state and did not
apply to itself. **A size is a weak fact.** Four numbers agreed with a
deletion of two fields and also with a rule about `NEW`, and the deletion was
taken because it was the first explanation found, not because anything ruled
the other out. An offset is a strong fact: there is only one word the binary
can be reading.

## 77. WRITELINKERINFO, and a record that is written before it is wanted

Segment 16, four procedures, **427 instructions, all four identical to
Apple's** on the first emulator run. `src/pascal/1.3/phases/WRITELIN.text`.

Its origin is `unitpart.text:10-247`, where it is already a `SEGMENT
PROCEDURE` -- but the first of two in one file. Apple gave it a file and a
segment to itself, and `UNITPART` kept the other.

### 77a. Apple writes first and takes it back

II.0 decides whether a symbol interests the linker **before** writing
anything. `GLOBALSEARCH` carries a `NEEDEDBYLINKER` boolean through a
`CASE KLASS OF` whose only job in five of its arms is to clear it, tests it
twice more afterwards, and only then emits the record.

Apple deleted the flag. It saves `IC`, writes the eight-character name
immediately, and where the answer turns out to be no it **winds `IC` back**:

    SAVEIC := IC;
    ...
    MOVELEFT(NAME,CODEP^[IC],8); IC := IC + 8;
    CASE KLASS OF
      ...
      ELSE IC := SAVEIC

`IC := SAVEIC` appears seven times in the arms and is the whole of the
rejection path. `GETREFS` uses the same trick one level down -- when it
matches no references at all it does `IC := IC - 16`, discarding the entire
sixteen-byte record its caller had already written, where II.0 wrote a zero
count into it and kept it.

The `IF SAVEIC <> IC THEN` guard on the `PROC`/`FUNC` arm is the flag's last
trace: having spent the flag, Apple asks `IC` the question instead.

### 77b. Six things smaller

* The **`DECSTUFF` parameter is gone**, with the `IF DECSTUFF` around the
  tree walk and the `IF DECSTUFF THEN DLINKERINFO := FALSE` at the end.
  Finding 75b already had the call site losing its `TRUE`.
* The **NIL test moved into `GLOBALSEARCH`**. II.0 tests before all three
  calls -- `IF FCP <> NIL THEN GLOBALSEARCH(FCP)` at the top and
  `IF FCP^.LLINK <> NIL` / `RLINK` at the bottom. Apple tests once, at entry.
* `GETREFS` **lost its second parameter.** II.0 declares
  `GETREFS(ID,LENGTH: INTEGER)` and never reads `LENGTH`.
* `GETREFS` computes its own **`FIC := IC - 4`** instead of taking it from a
  variable the caller sets, so `FIC` moved from the segment procedure's
  locals into `GETREFS`'s.
* The whole **nonresident-procedure loop is gone** -- `FOR I := SEEK TO
  DECOPS`, the six `FSEEK`/`FREADREAL`/`FWRITEDEC` names and the
  `PFNUMOF` array with them. So is every `SEPPROC` branch: no `SSEPPROC`,
  `SSEPFUNC`, `SEPPREF` or `SEPFREF` record is ever written, which takes
  out the longest arm of the `CASE LITYPE` and the `FORMAT`/`BYTE` handling
  around it.
* **`LIENTRY` is gone.** Apple keeps `LITYPES` and `OPFORMAT` -- it needs the
  ordinals, and `LITYPE IN [EXTPROC,EXTFUNC]` needs the set -- but the record
  became five scalars in the segment procedure's own `VAR`, and one of them
  does for both `NWORDS` and `NPARAMS`, which were never live together.
* `IF BLOCKREAD(...) <> 1 THEN;` -- II.0's **empty statement** -- became
  `ERROR(404)`.

### 77c. Three things larger, all of them intrinsic units

Apple 1.3 has intrinsic units, and every addition here is one:

* `GENWORD(0)` in the EOF record became **`GENWORD(DATASEG)`**, so the
  end-record now carries the data segment number beside `LCMAX`.
* A variable's `VLEV` can be **negative, and then it is a data segment
  number**: `INDATASEG := VLEV < 0`, and the arm that follows compares
  `-VLEV` against `DATASEG` to decide whether the variable lives in *this*
  unit's data segment. A `PUBLICDEF` record is written only when it does
  not. That is what pins global 42 as `INTRINSIC` -- `LDO 42; LNOT` needs a
  BOOLEAN, and both its uses read as "this compilation is of an intrinsic
  unit".
* The `MODULE` arm gained the two words of finding 76b.

### 77d. What it confirmed on the way

`REFARRAY`'s element is `RECORD KEY,OFFSET: INTEGER END` and the binary reads
`SIND 1` for the key, `SIND 0` for the offset -- **finding 33 again**, a
two-name list allocated back to front. And `GETREFS`'s locals come out
`LIC` 2, `FIC` 3, `COUNT` 4, `BLOCKCOUNT` 5, `MAX` 6, `J` 7, which is II.0's
own `J,MAX,BLOCKCOUNT,COUNT: INTEGER` reversed, unchanged, with `FIC`
inserted after `LIC` as a separate declaration. The one II.0 line that
survives Apple's rewrite intact survives it in Apple's order.

### 77e. The harness diffs a phase's nested procedures now

`report_phases` checked procedure 1 only, which was enough while `FINISHUP`
was the only phase and had nothing else in it. It now diffs every procedure
of a written phase, and reports a procedure Apple has and we do not -- or the
reverse -- as a failure rather than a stub. **47 procedures declared, 33 of 33
reconstructed bodies matching Apple's p-code, 14 still stubs.**

## 78. NUMSTRING: two scanners lifted out of INSYMBOL, and a rewritten float

Segment 19, three procedures, **597 instructions, all three identical to
Apple's** on the first emulator run. `src/pascal/1.3/phases/NUMSTRIN.text`.

II.0 declares `STRING` and `NUMBER` as procedures nested inside `INSYMBOL`
(`procs.a.text:265` and `:301`) and calls them from `INSYMBOL`'s own `CASE`.
Apple lifted both into a phase and put a two-line dispatcher in front:

    BEGIN (*NUMSTRING*)
      IF FISNUM THEN NUMBER ELSE STRING
    END;

Six instructions, and the whole of segment 19's procedure 1.

### 78a. The flag is a BOOLEAN, and the parameters confirm finding 61b

`SEGDECLS` carried `NUMSTRING(FKIND: INTEGER; VAR FVP: CSP)`, which was
right about the widths and wrong about the type: the dispatcher is
`SLDL 2; FJP`, with no comparison, and only a BOOLEAN compiles to that.
`INSYMBOL`'s two call sites become `NUMSTRING(FALSE,LVP)` and
`NUMSTRING(TRUE,LVP)` -- identical p-code to the `0` and `1` they were, so
nothing there moved.

The interesting part is *which* local the flag is. It is the **first**
parameter and it lands at **local 2**; `FVP`, the second, lands at local 1.
That is finding 61b's rule -- a parameter list allocates back to front, as a
whole rather than within each group -- and here it holds across two groups of
different types, which `BUMPSEG` could not show.

The lift cost exactly one parameter. `NUMBER` does `NEW(LVP,LONG)` on
`INSYMBOL`'s own local, which is a frame away now, so `LVP` came across as
`VAR FVP` and every reference to it followed.

### 78b. `NUMBER`'s VAR block is II.0's, unchanged, and proves the rule again

    VAR EXPONENT,ENDI,ENDF,ENDE,SIGN,IPART,FPART,EPART,
        ISUM:  INTEGER;
        TIPE: (REALTIPE,INTEGERTIPE);
        RSUM: REAL;
        NOTLONG: BOOLEAN;
        K,J: INTEGER;

Reversed, that nine-name list gives `ISUM` 1, `EPART` 2, `FPART` 3, `IPART` 4,
`SIGN` 5, `ENDE` 6, `ENDF` 7, `ENDI` 8, `EXPONENT` 9, then `TIPE` 10, `RSUM`
11-12, `NOTLONG` 13, and `J` 14, `K` 15 from the second reversed list. **The
binary uses every one of those offsets and no other**, with a `FOR` limit
temp at 16. Sixteen words, and not a name of II.0's moved.

`STRING`'s block is the same story, and it settles a small oddity in II.0's:
`TP,NBLANKS,L: INTEGER` declares two variables the procedure never reads.
Reversed after the 40-word `T`, that puts `L` at 41, `NBLANKS` at 42 and `TP`
at 43 -- and 41 and 42 are exactly the two words Apple's `STRING` allocates
and never touches. **Apple kept the dead declarations**, which is why the
frame is 46 words and not 44.

### 78c. A string that is too long now says so

II.0's `STRING` writes `T[TP]` with no bound on `TP`. `T` is
`PACKED ARRAY [1..80] OF CHAR` and the loop runs to a closing quote, so a
long-enough literal walks off the end of the frame. Apple guards it:

    IF TP <= 80 THEN T[TP] := SYMBUFP^[SYMCURSOR]
    ELSE
      BEGIN
        IF NOT TOOLONG THEN ERROR(277);
        TOOLONG := TRUE
      END

The latch means one error per literal rather than one per character past 80.

`TOOLONG` is then assigned `FALSE` **at label 1**, where it is dead -- the
`GOTO 1` from the end-of-line error and the normal fall-through both land on
it and nothing reads it again. It is in the binary (`SLDC 0; STL 45` at
`$0062`, and the `UJP $0062` that is the `GOTO`), so it is in the source.

### 78d. The real conversion is Apple's, not UCSD's

This is the one place where Apple replaced an algorithm rather than trimming
one. II.0 accumulates the fraction digit by digit, dividing each by its own
power of ten:

    FOR J := ENDF DOWNTO FPART DO
      RSUM := RSUM+(ORD(SYMBUFP^[J])-ORD('0'))/PWROFTEN(J-FPART+1);

That is one `PWROFTEN` and one division per fractional digit, and it rounds
at every step. Apple runs the fraction digits through the **same** `*10`
accumulation as the integer part -- the two `FOR` loops are the same
statement twice -- and pays for it once, in the exponent:

    EXPONENT := SIGN*EXPONENT;
    IF FPART <> 9999 THEN
      EXPONENT := EXPONENT + FPART - ENDF - 1;
    IF EXPONENT < 0 THEN RSUM := RSUM/PWROFTEN(-EXPONENT)
    ELSE RSUM := RSUM*PWROFTEN(EXPONENT);

One `PWROFTEN`, one divide, and the digits enter the float exactly.

That is what the added `FPART := 9999` at the top is for. II.0 leaves `FPART`
uninitialised -- it only ever reads it inside the branch that sets it -- and
Apple needs a sentinel meaning "no fraction part" to know whether the
correction applies. It reuses `EPART`'s 9999 for it, on the next line.

The sign went the same way: II.0 branches on `IF SIGN=-1` around two whole
statements, Apple folds the sign into `EXPONENT` and branches on its sign.

Two smaller edits in the same procedure: **`e` is accepted as well as `E`**
in an exponent, and `ENDI := 0` is dropped from the initialisation (it is
assigned unconditionally a few lines later).

### 78e. Two spellings of one expression, both preserved

`NUMBER` accumulates a digit twice, and II.0 punctuates the two differently:

    ISUM := ISUM*10+(ORD(SYMBUFP^[J])-ORD('0'));      { overflow scan }
    ISUM := ISUM * 10 + ORD(SYMBUFP^[K])-ORD('0');    { long build }

The parentheses are not cosmetic. The first emits `MPI ... LDB SLDC 48 SBI
ADI`, the second `MPI ... LDB ADI SLDC 48 SBI` -- subtract-then-add against
add-then-subtract. Apple preserved both, so the binary distinguishes them and
so must the reconstruction. It is the sharpest reminder yet that what is
being recovered is a *source text*, not a meaning.

## 79. COMPOPTIONS, and the compiler calling the operating system by name

Segment 18, five procedures, **647 instructions, all five identical to
Apple's**. `src/pascal/1.3/phases/COMPOPTI.text`.

II.0's `COMMENTER` (`procs.a.text:168`) is one procedure that reads the `$`
options *and* skips the rest of the comment. Apple split it: the skipping
stayed in segment 1's `COMMENTER`, already reconstructed, and everything from
the `$` to the last option became a segment FUNCTION. The result carries
II.0's `EXIT(COMMENTER)` across the boundary -- an EXIT cannot name a
procedure it is no longer inside -- so the caller's whole use of it is

    IF NOT COMPOPTIONS(STOPPER) THEN EXIT(COMMENTER);

and the four II.0 arms that exited now call an `EXITOPTIONS` that assigns
FALSE and returns. That procedure is six instructions and the second of the
segment.

### 79a. `CXP 0,43` is not a standard procedure

Almost every `CXP 0,n` in the compiler is emitted for a standard procedure --
`RESET` is `FOPEN`, `WRITE` is `FWRITECHAR`, `BLOCKREAD` is `FBLOCKIO` -- and
needs no declaration anywhere. `CXP 0,43` is different, and `syscall.py` has
been carrying it as `OS.43` with the name withheld since finding 51.

It is not emitted by anything. Two probes compiled under Apple's own
compiler settle it: `RESET` and `REWRITE` on a file with a `STRING[40]`
variable title, a `STRING` variable, a `STRING[80]` local and a literal;
then `CONCAT`, `COPY`, `INSERT`, `DELETE`, `POS`, `LENGTH`, `STR`, string
assignment and string subscription. The string intrinsics are `CXP 0,23`
through `0,27` and the file ones `0,5` and `0,6`. **Nothing emits 43 at any
argument shape.**

So the compiler is calling it *by name*, and that means Apple's source
declares it.

### 79b. Forty-two forwards that are never defined

Under `(*$U-*)` the outer block is lex -1 and its procedures are segment 0's
-- which at run time is `SYSTEM.PASCAL`, not the compiler. A third probe
shows the mechanism exactly:

    (*$U-*)
    PROGRAM PASCALSYSTEM;
    PROCEDURE A1; FORWARD;
    PROCEDURE A2; FORWARD;
    PROCEDURE A3(VAR S: STRING; I,N: INTEGER); FORWARD;
    SEGMENT PROCEDURE PASCALCOMPILER; ...

`A1` compiles to `CXP 0,2`, `A2` to `CXP 0,3`, and `A3(T,1,40)` to

    LAO 1; SLDC 1; SLDC 40; CXP 0,4

which is the shape of every one of the compiler's `OS.43` call sites. **An
unresolved FORWARD is legal here and is how a system program names the OS.**
It takes a procedure number, compiles the call, and the body it never gets is
the operating system's.

The same probe rules out the obvious alternative. With *bodies* instead of
FORWARDs the compile stops at **error 399** on the following
`SEGMENT PROCEDURE` -- which is `CODEINSEG`, the very error
`WRITELINKERINFO` reports at its own first line. Code at lex -1 before a
segment procedure is not allowed, so the forwards cannot be defined.

The count is exact and is the whole content of the claim: procedure 1 is the
outer block, the call is procedure 43, so there are **42** of them. II.0's
`GLOBALS.TEXT` has exactly 42 forward declarations, ending at `COMMAND`.
Apple's 43rd is not `COMMAND` -- II.0's takes nothing and Apple's takes three
words -- but everything up to 42 lines up, so the skeleton emits II.0's names
in II.0's order and Apple's shape for 43 alone. The parameters of the other
41 are dropped: a forward that is never called and never defined contributes
nothing but its number.

What 43 *is* stays unrecovered. `SYSTEM.PASCAL`'s own procedure 43 forwards
straight into `FILEPROC.1`, its file-name segment, and the three call sites
pass a string, 1, and that string's declared length -- twice on a title about
to be `RESET`, once in segment 1 on an 80-character buffer whose `LENGTH` is
read immediately after. It is declared `OSPROC43` and left at that.

`ucsdpsys_compile` rejects unresolved forwards outright, so `procbuild` has a
`defang_forwards` that swaps the block for a single stub before handing the
source to the fast tier. The cost is two instructions in one procedure on a
tier that already differs at every `AND`.

### 79c. RESIDENT is a chain of MODULE identifiers

`(*$R name,name*)` is Apple's, with no UCSD equivalent: it names segments
that must stay resident. `RESSEGLIST` reads the list, and for each name --
a unit, a segment procedure, or a plain number -- calls `MARKRESIDENT`, which
is the only thing in the compiler that builds the `RESIDENT` chain. The only
other references anywhere are `BLOCK` setting it NIL and `BODY1` asking
whether it still is.

    NEW(LCP,MODULE);
    WITH LCP^ DO
      BEGIN SEGID := FSEG;
        NEXT := RESIDENT;
        MODUNK11 := (SY = IDENT) AND INMODULE AND NOT INTRINSIC
      END;
    RESIDENT := LCP

The cell is an `identifier`: the link is `NEXT` at word 7, the identifier
record's own link field, and the segment number goes to `SEGID` at 9. So
`RESIDENT` is a `CTP`, not the `^ INTEGER` placeholder it has been carrying.

And the allocation measures the variant. `NEW(...,MODULE)` asks for **13**
words, which is the 9-word fixed part plus four -- so Apple's `MODULE` is
four words where UCSD's is one. Finding 76b already had two of them from
`WRITELINKERINFO`'s reads at 10 and 11; the fourth is required by the
allocation and read by nothing. The count checks out across the whole
binary: five 13-word `NEW`s, and `decpart.a`'s two `NEW(LCP,FIELD,TRUE)`
plus `decpart.b`'s one `NEW(LCP,MODULE)` account for the three in
`DECLARAT` exactly.

`MODUNK10` gets a use here too, and a suggestive one: a named unit is marked
resident **only if** it is set. Whatever it means, it distinguishes units
that have a segment of their own.

### 79d. Six globals typed, one collision, and two orderings

Typed by this segment, each from an assignment whose right side is a
comparison: `OPT_E`, `VARSTRG`, `NOLOAD` and `LSTOPEN` are BOOLEAN, as is
`INTRINSIC` from finding 77c. `RESIDENT` is `CTP` as above.

The collision is worth recording because it is the **eight-character rule**
biting for the first time in a way that changed the source. `RESIDENTLIST`
truncates to `RESIDENT`, which is the global it assigns to, and the compiler
sees an assignment to a function result. Renamed `RESSEGLIST`.

Two orderings came out of the diff rather than out of reasoning, which is the
point of running it:

* **The case arms are in source order.** Apple's jump table sends `P` to a
  later address than `Q`, so `Q` is written first -- II.0's order, which the
  reconstruction had tidied.
* **`LVAL*10 + (ORD(LTITLE[LI])-ORD('0'))` is parenthesised** and
  `NUMSTRIN`'s other accumulation is not. Same lesson as finding 78e, in a
  different segment, found the same way.

### 79e. What Apple added to the options

`E`, `N`, `NS`, `R name`, `S` and `V` have no UCSD counterpart. `NS` is the
one finding 68 predicted: it scans up to two digits and, if the value is
above `NEXTSEG` and below 63, moves the segment counter -- which is what puts
the compiler's own phases at 7 and up. `S` takes two switches at once,
`SWAPPING` from `SW` and `SWAPMORE` from `DEL`, and steps the cursor when
`DEL` is `+` or `-`. `Q` gained `NOT CONLIST`, `L` and `U` gained the
`LSTOPEN` and `LIBNOTOPEN` guards, and `SCANSTRING` gained blank-trimming at
both ends plus the rule that a `*` inside a `(* *)` comment only terminates
it when a `)` follows.

II.0's include handling shrank in one place: it opens the file, and on
failure retries with `.TEXT` appended. Apple calls `OSPROC43` on the title
and opens once.

## 80. UNITPART, the INTRINSIC unit, and a rule the emulator corrected

Segment 17, four procedures, **906 instructions, all four identical to
Apple's on the first run**. `src/pascal/1.3/phases/UNITPART.text`.

II.0's `UNITPART` is the second of the two segment procedures in
`unitpart.text`, the file `WRITELINKERINFO` came from. Apple gave each its
own file and its own segment, and then added to this one the thing UCSD
II.0 has no notion of: the **intrinsic unit**.

### 80a. `UNIT X; INTRINSIC CODE 20 DATA 21;`

A UCSD unit is compiled into the next free segment and linked into the host
program. An Apple intrinsic unit names the two segment numbers it will own
for good -- one for its code, one for its globals -- and lives in
`SYSTEM.LIBRARY` for every program to share. `UNITDECLARATION` is where the
clause is parsed, and it is most of what Apple added to II.0's procedure:

    IF ID = 'INTRINSI' THEN
      BEGIN INTRINSIC := TRUE;
        LCODESEG := FALSE; LDATASEG := FALSE; DATASEG := 1;
        INSYMBOL;
        IF SY = IDENT THEN
          BEGIN
            IF ID = 'CODE    ' THEN ... SEGKIND := 6 ...
            IF (SY = IDENT) AND (ID = 'DATA    ') THEN ... SEGKIND := 7 ...
            IF NOT LCODESEG THEN
              BEGIN ERROR(352); LCP^.MODUNK10 := FALSE END;
            IF SY = SEMICOLON THEN INSYMBOL ELSE ERROR(14)
          END
      END
    ELSE ERROR(22)

`CODE` is required and `DATA` is not, and the two flags that say which were
seen live in **UNITPART's frame, not this one** -- `STR 1,6` and `STR 1,7`.
Everything that reads them is in the segment body: a data segment with
nothing in it is error 355, globals with no data segment to hold them is
error 350, and no code segment at all is error 352.

II.0 also has no `SEGSLOT`. Apple's `SEGMAP` decouples a segment's number
from its table slot (finding 71), so `NEWSEG` and `BUMPSEG` allocate the
slot and `SEGNUM` records the number.

### 80b. The MODULE variant's fifth word, and what NEW does when the tags run out

**VERIFIED BINARY FACT** for the two sizes and the condition between them.

`MARKRESIDENT` asks `NEW` for **13** words and `UNITDECLARATION` asks for
**14**. Both build a `MODULE` identifier. Finding 76 says a `NEW` allocates
by the tag list it is given, so the difference is a tag -- and
`DECLARATIONPART` shows the two side by side, the arms of one `IF`:

    IF LSEPPROC THEN NEW(LCP,MODULE,TRUE) ELSE NEW(LCP,MODULE,FALSE)

So the fourth of Apple's added `MODULE` words is a **BOOLEAN tag** and there
is a fifth behind its TRUE arm. The tag is written at both creation sites
(FALSE) and again in `UNITDECLARATION`'s intrinsic `DATA` arm (TRUE); the
word behind it is allocated by three call sites and read by none.

Then Apple's compiler corrected the rule. Written `NEW(LCP,MODULE)`,
`MARKRESIDENT` came back **14** where the binary has 13 -- the one
divergence in the whole run, and the only one this session. A tag list that
*runs out* does not stop: the largest remaining arm is allocated, exactly as
for an untagged pointer. Only an empty *arm* stops it. So the short sizes of
finding 76 come from supplying the empty label, never from withholding the
tag, and `MARKRESIDENT` writes `NEW(LCP,MODULE,FALSE)`.

Every example in finding 76 supplies the label explicitly, so nothing there
moves; `probe_record_layout.py` passes its 49 checks under either reading.
What settled it was a size the binary states and the fast tier cannot see.

### 80c. SEGSUSED is a set, and it is written into the interface text

**VERIFIED BINARY FACT.**

`SEGSUSED` has been carried as four unnamed words since the global map.
`UNITPART` uses `INN`, `INT` and `DIF` on all four, which will not compile
against an array, so it is `SET OF 0..63` -- and 1.1's two words are
`SET OF 0..31`.

What it is for shows up in the same place. A unit's interface text is copied
into the codefile verbatim, so that a program `USES`ing the unit can compile
against it without the source:

    IC := SYMCURSOR - TEXTSTRT + 10;
    IF IC > 1024 THEN IC := 1034;
    ...
    MOVELEFT(SYMBUFP^[TEXTSTRT],CODEP^[0],IC);
    FILLCHAR(CODEP^[IC-10],10,' ');
    CODEP^[IC-2] := 'E';

Ten blank bytes are left past the end of it. After `WRITECODE` has put the
buffer on disk the block is read back and **two of those blanks are
patched**:

    IF [30,31]*SEGSUSED <> [] THEN
      BEGIN
        IF BLOCKREAD(USERINFO.WORKCODE^,DISKBUF,1,LBLK) <> 1 THEN ERROR(402);
        IF 31 IN SEGSUSED THEN DISKBUF[LLENG+1] := 'P';
        IF 30 IN SEGSUSED THEN DISKBUF[LLENG+3] := 'L';
        ...
        SEGSUSED := SEGSUSED - [30,31]
      END;

So the unit records, in its own interface text, that its code needs the two
support segments -- and the block has to be remembered before `WRITECODE`
runs, because `CURBLK` moves past it. That is what `LBLK` and `LLENG` are,
and why the byte count is reduced modulo 512 before anything is written.

`USERINFO.WORKCODE^` is `LOD 2,8`, two lex levels up, which is the operating
system's own globals (finding 63) -- and it is `WORKCODE` at 8 rather than
`WORKSYM` because a two-name list allocates backwards (finding 33).

### 80d. The unit's initialisation body has no identifier, so one is built

II.0 compiles a unit's `BEGIN ... END` through `BLOCK` like any other body.
Apple's fourth procedure does it by hand: it pushes a lex stack entry,
fills `DFPROCP` with a procedure identifier it makes up -- named for the
unit, lex 1, procedure 1 of `SEG` -- and hands that to `BODYPART`.

    NEW(DFPROCP,PROC,DECLARED,ACTUAL,TRUE);
    WITH DFPROCP^ DO
      BEGIN NAME := MODPTR^.NAME; IDTYPE := NIL; NEXT := NIL;
        KLASS := PROC; PFDECKIND := DECLARED;
        PFLEV := 1; PFNAME := 1; PFSEG := SEG; PFKIND := ACTUAL;
        LOCALLC := 1; FORWDECL := FALSE; EXTURNAL := FALSE;
        INSCOPE := TRUE; IMPORTED := FALSE
      END;

`LLINK` and `RLINK` are the only two fields left alone: the record never
enters a symbol tree, and nothing ever looks it up by name.

This is also the first `LEXSTKREC` the reconstruction has had to lay out,
and it comes out II.0's verbatim -- eleven words, `DFPROCP` at 8,
`PREVLEXSTACKP` at 11. The pair that would have moved is `POLDPROC,SOLDPROC`,
and finding 33 puts them the right way round: the binary saves `CURPROC` to
word 4 and `NEXTPROC` to word 3, which is what a reversed two-name list
gives.

### 80e. The work disk ran out before the compiler did

Worth recording because the symptom names the wrong thing. Apple's compiler
reported **error 402 at the last line of the source**, having compiled all
2421 of them. 402 is the codefile: a Disk II volume is 280 blocks, the
source had grown to 138 of them, and the 30 that were left were not enough
to write the result into.

`write_for_emulator` now drops `SKEL13.TEXT` and `SKEL11.TEXT` from the
volume -- 82 blocks this run has no use for, since the body source carries
the declarations itself -- and prints what is left. `mkworkdisk.py` puts
them back, and `build_all.py` runs it. The ceiling is real and will be met
again: 280 blocks is the whole budget for the source and its output
together.

## 81. COMPINIT: the standard identifiers, and a version check

Segment 7, eleven procedures, **1875 instructions**, eight of them identical
on the first emulator run and all eleven on the second.
`src/pascal/1.3/phases/COMPINIT.text`.

Most of it is II.0's `compinit.text` verbatim, down to the order of the
field assignments inside each `WITH`. What Apple changed is worth the
listing.

### 81a. Forty-four names in five string literals

II.0 builds its table of special-procedure names with forty-three
assignments to an `ARRAY [1..43] OF ALPHA`. Apple packs them into
dot-separated literals, appends them into one 512-byte buffer, and cuts
them out again with `SCAN`:

    ADDNAMES('READ.READLN.WRITE.WRITELN.EOF.EOLN.PRED.SUCC.ORD.SQR.ABS.NEW.');
    ADDNAMES('UNITREAD.UNITWRIT.CONCAT.LENGTH.INSERT.DELETE.COPY.POS.');
    ...
    WHILE NPOS < NCHARS DO
      BEGIN NEXTNAME(LNAME); I := I + 1; ...

`NEXTNAME` is five statements -- blank the ALPHA, `SCAN(8,='.',...)`,
`MOVELEFT`, step the cursor -- and it replaces eighty-one lines of source
and about 700 bytes of `LDC`/`STM` pairs. The buffer and its two cursors
live in **COMPINIT's own frame**, which is why both helpers reach them with
`LOD 1,n`; that is what makes COMPINIT's `DATA SIZE` 608 bytes, the largest
frame in the compiler.

Apple's list runs to **44**: `UNITSTAT` is Apple's, and the `TINY` exclusion
set gains it and loses `SUCC`.

### 81b. BYTESTREAM and WORDSTREAM

`ENTSTDTYPES` gains three records II.0 does not have -- a `SUBRANGE` of
`0..MAXINT` and two `ARRAYS` over it:

    NEW(BYTEPTR,ARRAYS,TRUE,FALSE);    { PACKED ARRAY [0..MAXINT] OF CHAR }
    NEW(WORDPTR,ARRAYS,FALSE);         { ARRAY [0..MAXINT] OF INTEGER    }

and `ENTSTDNAMES` enters them as `BYTESTRE` and `WORDSTRE`. These are the
types a `UNITREAD` or `BLOCKREAD` buffer is checked against. Finding 64 had
`BYTEPTR` and `WORDPTR` as "compared against an STP in COMPTYPES" and no
more; this is what they are.

### 81c. The transcendentals are gone, and the CSP numbers have a hole

II.0's `ENTSTDPROCS` enters nineteen standard procedures, seven of them
`SIN`, `COS`, `LOG`, `ATAN`, `LN`, `EXP` and `SQRT`. Apple moved those into
the `TRANSCEND` unit, so thirteen are left -- and the CSP numbers they map
to are no longer contiguous:

    IF I < 5 THEN CSPNUM := I + 20 ELSE CSPNUM := I + 27

`ODD`..`ROUND` are CSP 21..24 and `MARK`..`MEMAVAIL` are 32..40, with the
transcendentals' 25..31 left empty in the interpreter's table. II.0's
single `CSPNUM := I + 20` could not survive that. Apple also keeps `XXX` at
3 -- a name that cannot be typed and whose case arm is `GOTO 1`, skipping
the entry entirely; the slot is there so that the numbering after it is
right.

### 81d. CHECKVERS, and the only way to put an address in a pointer

The first thing COMPINIT does -- before `INITSCALARS`, before anything --
is check that it is running under the right operating system:

    LPTR.LADDR := -16607;
    IF LPTR.LBYTE^[0] <> CHR(4) THEN
      BEGIN ... 'Version 1.3 of SYSTEM.COMPILER cannot run' ...
        EXIT(PASCALCOMPILER)
      END;
    LPTR.LADDR := -16606;
    HAS128K := LPTR.LBIT^[6]

$BF21 is SYSTEM.PASCAL's version byte and $BF22 carries the
machine-configuration bits. Neither is reachable through a declaration, and
Pascal has no cast, so the source must use a **variant record** with an
INTEGER arm and a pointer arm. The two reads are different widths -- a byte
for the version, a single bit for the 128K flag, which the binary takes
with `IXP 16,1` -- so the pointer arm is itself a variant of two pointer
types. That is three arms over one word, and it is forced by the code.

`^` must be followed by a type *identifier* in UCSD, so the two array types
are named; Apple's compiler reports error 2 on an inline `^ PACKED ARRAY`,
which is how that was learned.

This also settles `HAS128K`, which the global map had only as "ORed with
SWAPPING in BLOCK".

### 81e. The listing file is asked for, not declared

II.0 has no listing file at all. Apple prompts for one before reading a
line of source, and the prompt is a `REPEAT` that only ends when the file
opens or the answer is empty. Inside it: a leading `DLE` is deleted (the
editor's indent prefix), `ESC` quits the compiler, `OSPROC43` is called on
the title -- the third of its three call sites, finding 79b -- a volume
name is upper-cased in place, and `CONSOLE:` or `#1:` turns `NOISY` off and
`CONLIST` on so that the listing and the progress display do not fight over
the screen.

`I/O Error #n occured while opening ...` is Apple's spelling, not a
transcription slip.

### 81f. What INITSCALARS settles

* **`NEXTSEG := 7`** where II.0 has 10. Finding 68 inferred 7 from the
  segment numbers of the phases; here it is, written down.
* **`SEGSUSED := []`**, which is finding 80c's set being initialised.
* **`SWAPPING`, not `NOSWAP`.** II.0 sets `NOSWAP := MEMAVAIL > 9950`;
  Apple sets `SWAPPING := NOT ((MEMAVAIL < 0) OR (MEMAVAIL > 9950))`. The
  extra `< 0` guard is for a machine with more than 32K words free, where
  `MEMAVAIL` overflows.
* **`SYSTEMLIB := '*'`** -- one character, not II.0's `'*SYSTEM.LIBRARY'`
  and not the `USERINFO.STUPID` test it sat behind.
* `CODEP := NIL` rather than `NEW(CODEP)`. The buffer is allocated on first
  use, which is what `UNITPART`'s opening `IF CODEP = NIL THEN NEW(CODEP)`
  is for (finding 80).
* Six of the booleans this reconstruction typed from a single comparison
  get their initial value here too, which is a second sighting of each:
  `LINKINFO`, `INTRINSIC`, `VARSTRG`, `OPT_E`, `NOLOAD` and `SWAPMORE`.

### 81g. Three corrections, and two of them were the same mistake

The diff found exactly three things, and all three are worth naming because
none was a reasoning error about the code:

* `VAR CP1,CP: CTP` where II.0 has `VAR CP,CP1: CTP`, and `VAR PARAM,LCP`
  where II.0 has `VAR LCP,PARAM`. I had read the offsets off the binary and
  written the names in the order the offsets came out -- which is exactly
  backwards, because a list allocates in reverse (finding 33). **II.0's own
  declaration was right both times.** The rule is now stated where it
  belongs: when II.0 has a list and the offsets are consistent with it,
  copy the list.
* `RESET(LP,LTITLE)` for `REWRITE(LP,LTITLE)`. `FOPEN`'s fourth argument is
  0 for a new file and 1 for an existing one, and a listing file is
  written.

## 82. DECLARATIONPART, and what the MODULE record is for

Segment 8, twenty procedures, **4334 instructions**, all matching Apple's
p-code. `src/pascal/1.3/phases/DECLARAT.text`. Ten of the twenty were
identical on the first emulator run; six rounds settled the rest.

II.0 writes this as three files and one procedure. Apple has twenty
procedures to II.0's fifteen, and the five extra are restructuring rather
than new work:

* **CHECKSYS**, which is `IF NOT (SY IN X) THEN BEGIN ERROR(6); SKIP(X) END`
  -- ten sites in II.0, one procedure and ten calls here.
* **USEUNIT**, the ELSE arm of II.0's `USESDECLARATION` loop lifted into a
  procedure of its own. That is where II.0's `MAGIC` parameter went: it
  existed to reach Turtlegraphics behind the user's back, and Apple has no
  such thing.
* **FINDUNIT** and **FINDNAME** under GETTEXT. Apple's library search has to
  find a unit's code segment and then, separately, its data segment, so the
  search became a function and the thing that calls it twice became another.
  They are lex 5 and lex 6 -- the deepest nesting anywhere in the compiler.

### 82a. Sets hoisted out of loops

Six sets that II.0 recomputes on every pass are computed once into locals:
two in DECLARATIONPART's own frame (`FSYS+[IDENT]` for the three
declaration parsers, `FSYS+[COMMA,SEMICOLON]` for LABELDECLARATION, both
reached from below with `LDA 1,n`), one in SIMPLETYPE, one in FIELDLIST.
Not all of them -- the opening `SKIP(FSYS + [IDENT])` in CONSTDECLARATION
and TYPEDECLARATION is still computed inline, which is how the hoisting was
measured: those procedures read *both* lex-1 local 1 and lex-1 local 8.

### 82b. What Apple added to the language here

* **BYTESTREAM and WORDSTREAM are not simple types.** SIMPLETYPE rejects
  them with error 103 and PARAMETERLIST rejects them as value parameters
  with error 7. Finding 81b entered them; this is what stops them being
  used as ordinary types.
* **`(*$E+*)` relaxes the no-private-files rule.** II.0's `IF INMODULE THEN
  IF NOT ININTERFACE THEN ERROR(191)` becomes `IF NOT (ININTERFACE OR
  OPT_E)` in both places it appears. That is the first use recovered for
  `OPT_E`, which finding 79d had only as "assigned `(SW = '+')` in
  COMPOPTIONS".
* **`BUMPSEG(NEXTPROC,MAXPROCNUM,251)`** replaces II.0's `IF NEXTPROC =
  MAXPROCNUM THEN ERROR(251) ELSE NEXTPROC := NEXTPROC + 1`. MAXPROCNUM is
  254 here (finding 40), and the same helper does the segment counter.
* **An EXTERNAL procedure that is not followed by `EXTERNAL`** gives back
  its procedure number: `NEXTPROC := NEXTPROC - 1; LCP^.PFNAME := 0`. The
  test that guards it (`IF SY <> EXTERNLSY`) is dead -- nothing between it
  and the `IF SY = EXTERNLSY` that got there reads a symbol -- and the
  binary has both, so the source did.

### 82c. The MODULE record, named at last

**VERIFIED BINARY FACT.** This closes the open question findings 76b, 79c
and 80b left standing, and the four words are renamed from `MODUNK10`..13.

`GETTEXT` and `USEUNIT` write every one of them and read three, and each
use agrees with the uses already recorded elsewhere:

    MODSEG   (word 11)  the module owns a code segment
    MODLINK  (word 12)  it is not an intrinsic's own code segment
    MODDATA  (word 13)  it owns a data segment          -- the variant tag
    MODDSEG  (word 14)  that data segment's number      -- behind the tag

`USEUNIT` sets `MODSEG := LKIND IN [3,5,6]` and `MODLINK := LKIND <> 6`,
where LKIND is the used unit's SEGKIND: 3 a unit, 4 a separate procedure,
5 a linked intrinsic, 6 an intrinsic's code, 7 an intrinsic's data. So
MODSEG is "this has code of its own" and MODLINK is "and it is not an
intrinsic", which is exactly the pair `WRITELINKERINFO` ANDs together to
decide whether a used unit gets a MODDULE record (finding 76b), and exactly
what `UNITPART` guards the segment table entry with (finding 80).
`UNITDECLARATION` clears MODSEG when an INTRINSIC clause names no CODE
segment, which is the same statement from the other side.

MODDATA and MODDSEG are settled twice over. `UNITDECLARATION` sets MODDATA
in the `DATA` arm and nowhere else; `GETTEXT` reads it to decide whether to
switch DATASEG, and takes the new value from MODDSEG. And the allocation
matches: `NEW(LCP,MODULE,TRUE)` when the unit has a data segment, `FALSE`
when it does not.

### 82d. A variable's VLEV can be negative, and now it is known why

`VARDECLARATION` does not simply write `VLEV := LEVEL`:

    IF LSEPPROC OR INTRINSIC THEN
      IF LEVEL <= 1 THEN VLEV := -DATASEG
      ELSE VLEV := LEVEL
    ELSE VLEV := LEVEL;

A global of an intrinsic unit gets **minus its data segment number** in the
level field. `WRITELINKERINFO` reads it back that way -- finding 79's
`INDATASEG := VLEV < 0` and `-VLEV <> DATASEG` -- and this is where the
negative comes from.

### 82e. The library dictionary, and a third UNITFILE

`SEGDICT` is a block of `*SYSTEM.LIBRARY` read straight into a 256-word
record, and Apple's has one array II.0's does not: a packed record per
segment whose low byte is the segment number. That is finding 71's SEGINFO
word seen from the reading side -- Apple's SEGMAP decouples a slot from a
number, so the number has to be in the dictionary.

`USEFILE` gains a third value. II.0 has `UNITFILE = (WORKCODE,SYSLIBRARY)`;
Apple stores 2 as well, for the library that was already open -- the one
`(*$U name*)` gave it. GETTEXT tries a BLOCKREAD on whatever LIBRARY is
first, and only falls back to opening `*SYSTEM.LIBRARY` itself if that
fails.

### 82f. Corrections the diff found

Six rounds, and worth listing because none was a misreading of the binary
-- all six were places where II.0's text was assumed to have survived and
had not:

* SIMPLETYPE's `INSYMBOL` after `SEARCHID` is pushed down into each of the
  four arms below it, so that `LSP = STRGPTR` is tested before the symbol
  after the identifier is read rather than after.
* FIELDLIST sets `LAST := NXT` on every field, not only on the last of a
  group -- II.0's `IF NEXT = NXT1 THEN` is gone.
* `ERROR(399)`, not II.0's 398, for an array whose size comes out
  non-positive.
* PARAMETERLIST's `FSYS + [COMMA,SEMICOLON,COLON]` test gains RPARENT, so
  that the set it tests and the set it skips to are the same one.
* `IF LKIND = FORMAL THEN EXTONLY := TRUE` also does
  `LC := LC + COUNT * PTRSIZE`.
* `PROCTABLE[NEXTPROC] := 0` is unconditional where II.0 does it only
  `IF USING`, and `IMPORTED := NOT LSEPPROC AND USING` replaces II.0's
  nested IF.

### 82g. The disk ceiling, and the second drive

Finding 80e said 280 blocks would be met again, and this segment met it:
the source reached 262 blocks and left 18 for a codefile that needs about
forty. A Disk II image cannot grow, so the codefile got a volume of its
own. `mkworkdisk.py` now writes an empty `WORK2`, `runemu.py --work2`
mounts it at S5D2 in place of APPLE3 -- which a compile does not need --
and `--emu` answers the compiler's second prompt with `WORK2:BODY13.CODE`.
`--emu-check` takes the codefile from whichever volume has it.

That buys 280 blocks for output and leaves the whole of WORK for source.
The source ceiling is still real and still 274 blocks; when it arrives, the
next move is `(*$I *)` includes, and after that dropping the comments and
shortening the names for the disk copy only.

## 83. BODYPART — segment 9, the code generator and the expression parser

VERIFIED BINARY FACT unless marked otherwise. Thirty-six of the segment's
thirty-eight procedures compile, under Apple's own 1.3 compiler, to Apple's
p-code instruction for instruction. `BODY` and `BODY2` are the two still
open, and they are open together with `BODY1` and `BODY3` — see 83g.

### 83a. The shape of the file is read off the code order

II.0's `BODYPART` is five files and one procedure. Apple's is 38
procedures and three segments: II.0's `ROUTINE` became
`SEGMENT PROCEDURE ROUTINE` (segment 10) and took `LOADIDADDR`, `READ`,
`WRITE` and `CALLNONSPECIAL`'s siblings with it, and II.0's `STATEMENT`
became `SEGMENT PROCEDURE STATEMENT` (segment 11).

That forces a forward block, and the binary says where it ends. Procedure
code is emitted in declaration order, innermost first — the run of `enter`
addresses in every verified segment says so, `DECLARAT` included. In
`BODYPART`, `BODY`'s code comes **first** of all the lex-2 procedures,
ahead of `LINKERREF`'s. A procedure whose body is compiled first can only
carry number 24 if numbers 2..23 were already taken when it was parsed —
which is what a forward block does, exactly as in `PASCALCO` (finding 61).

`GENBIG` (28) and `HOLDRTN` (38) are the check on that reading. Neither is
in the forward block: each is declared where its body is, so each takes the
next free number at that point, which lands `GENBIG` above `BODY`'s nested
25, 26 and 27 rather than beside the emitters it belongs with. Nothing else
explains a `GENBIG` numbered 28 and called from `GEN1`.

The nested phases go between the forward block and `BODY`: everything
`ROUTINE` and `STATEMENT` reach with `CXP 9,n` is declared above them
(forward is enough), and `BODY` is below because it calls `STATEMENT`.

### 83b. BODY1 and BODY3 are declared inside BODY

Their procedure 1 is lex 3, so each is declared inside one of `BODYPART`'s
own procedures, and `BODY` is the only one that calls them —
`CXP 14,1` and `CXP 15,1` are its first and last instructions. A segment
procedure is in scope only where it is declared, so that settles it.
`CASESTAT` and `FORSTATE` are lex 3 for the same reason and sit inside
`STATEMENT`. The segment numbers then follow from declaration order:
`ROUTINE` 10, `STATEMENT` 11 with its two at 12 and 13, then `BODY` with
its two at 14 and 15.

`procbuild.py` grew `{SEGMENT <name>}` markers so a phase's source says
where each of its children goes.

### 83c. GEN2 takes an absolute level, and a negative one is a data segment

The one procedure of the twenty-three that did not match on the first
emulator run. II.0 passes `GEN2` a level *difference*, with `FP1 = 0`
meaning "this frame"; every caller subtracts, and `STORE`, `LOAD` and
`LOADADDRESS` each carry a `VLEVEL = 1` test for the global case.

Apple passes the **absolute** level. The three tests move into `GEN2`:

```
IF FP1 = 1 THEN GEN1(FOP-13,FP2)            { LDA->LAO, LOD->LDO, STR->SRO }
ELSE IF FP1 = LEVEL THEN GEN1(FOP+20,FP2)   { ->LLA, LDL, STL }
ELSE IF FP1 < 0 THEN ...
ELSE BEGIN GENBYTE(FOP+128); GENBYTE(LEVEL-FP1); GENBIG(FP2) END
```

and that makes room for the fourth case, which II.0 has no equivalent of. A
negative `FP1` is not a level at all: it is a **data segment**, and it is
the same negative `VLEV` that `DECLARATIONPART` writes for a global of an
intrinsic unit (findings 79, 82d). It emits `LDE` ($9D), `STE` ($D1) or
`LAE` ($A7) — Apple's load, store and load-address across a separate data
segment — followed by the segment number and the offset.

So the three callers lose their `VLEVEL = 1` arms and pass `VLEVEL`
straight through, and `ATTR.VLEVEL` holds an absolute level throughout.

### 83d. MASKBOOL, and where a boolean has to be clean

`BODYPART.15` has no II.0 ancestor. Its whole body is

```
IF GATTR.TYPTR = BOOLPTR THEN
  BEGIN GENBYTE(1(*SLDC 1*)); GENBYTE(132(*LAND*)) END
```

— two bytes that mask the loaded value to its low bit. UCSD's booleans are
only guaranteed there, and it is called in exactly three places, all of
which then use the value as a *number*: `SELECTOR` after the `LOAD` of an
array subscript, `FACTOR` after the `LOAD` of a set element, and
`EXPRESSION` after the left operand of a relational operator, but only
`IF OP = INOP`. `b IN [...]`, `a[b]` and `[b]` are the three places a
boolean becomes an index.

### 83e. GENNR, and the two library segments

II.0's `GENNR(EXTPROC: NONRESIDENT)` keeps a `PFNUMOF` table and assigns a
local procedure number to each of six runtime operations the first time it
is used. Apple's takes a segment and a procedure number directly:

```
PROCEDURE GENNR(FSEG,FPROC: INTEGER);
BEGIN SEGSUSED := SEGSUSED + [FSEG]; GEN2(77(*CXP*),FSEG,FPROC) END
```

The five call sets recovered are `DECOPS` = (30,4), `FREADDEC` = (30,2),
`FWRITEDEC` = (30,3), `FREADREAL` = (31,3) and `FWRITEREAL` = (31,4).
Segment 30 is the long-integer support and 31 the real I/O — which is what
`UNITPART` reads back out of `SEGSUSED` to stamp `L` and `P` on a unit's
interface text (finding 80).

### 83f. BYTEPTR and WORDPTR, the untyped array parameters

Apple's two pseudo-types have no index type and are compatible with
nothing, so every place they can appear had to be written out. Three were
recovered here:

* `MAKEPA` (37) is rewritten. II.0's checks a packed array's length
  against a string's and assigns. Apple's does that only when `PAFSP` is
  not `BYTEPTR`; when it is, it **manufactures** an index type — a fresh
  `SUBRANGE` of `INTPTR`, `MIN := 1`, `MAX := STRGFSP^.MAXLENG` — hangs it
  on the string's `INXTYPE`, and clears `AISSTRNG`.
* `EXPRESSION`'s `ARRAYS` arm takes the length from the other side when
  one operand is `BYTEPTR` (packed) or `WORDPTR` (unpacked), and reports
  error 129 when both are.
* `CALLNONSPECIAL` spells out what a formal of either will accept: for
  `BYTEPTR`, a packed byte array (`ELSPERWD = 2`, `ELWIDTH = 8`), a `CHAR`
  already addressed as a byte, or a `0..255` subrange; for `WORDPTR`, any
  unpacked array or any one-word type. Everything else is error 142.

`WRITEPROC`'s `PAOFCHAR(LSP)` gains `AND (LSP <> BYTEPTR)` for the same
reason: `BYTEPTR` has no bounds to get a field width from.

`CALLNONSPECIAL` also carries an optimisation II.0 has no trace of. It
precomputes `LADJ := (LSP^.SIZE <> GATTR.TYPTR^.SIZE) OR (GATTR.KIND <>
VARBL)` *before* the `LOAD` — `LOAD` overwrites `KIND` — and when it is
false the `ADJ` (or the long-integer `DAJ` triple) is not emitted at all;
`IC` is wound back over the byte `LOAD` just wrote instead, by one, or by
three when the size needed a two-byte operand.

### 83g. `(*$R name*)` holds a segment across a call

`HOLDSTMT` (27) and `HOLDRTN` (38) are nine instructions each and have the
same shape: enter, jump forward to `LOADSEGMENT(n)`, jump back to a single
`CIP`, fall through to `UNLOADSEGMENT(n)`, return. Segment 11 for the
first, segment 10 for the second, and `BODYPART.1` picks `HOLDRTN` over
`BODY` when `NOT SWAPPING OR SWAPMORE` is false.

The source that produces it is

```
PROCEDURE HOLDRTN;
BEGIN (*$R ROUTINE*)
  BODY
END ;
```

and the position of the option is forced. `BLOCK` sets `RESIDENT := NIL`
immediately before `IF SY = BEGINSY THEN INSYMBOL`, so an option written
above the `BEGIN` has already been scanned and is wiped; written after it,
`INSYMBOL` picks it up, `COMPOPTIONS`' `RESSEGLIST` chains a `MODULE`
record onto `RESIDENT` (finding 78), and `BODY1` and `BODY3` emit the
bracket. Both spellings — the name and the bare segment number — reach
`MARKRESIDENT` with the same value and are indistinguishable in the
output.

That is the mechanism `PASCALCO.28 HOLDMOST` and `.29 HOLDROUT` were still
stubs for, and it is now demonstrated rather than inferred: both wrappers
match Apple's bytes.

### 83h. The comment-stripped disk copy

Finding 82g said the source ceiling was still ahead. `BODYPART` took the
spliced source from 234 blocks to well past 274, so `--emu` now writes a
copy with everything that provably cannot change a byte removed —
comments, except `{$...}` and `(*$...*)`, which are compiler options and in
`(*$R STATEMENT*)`'s case load a segment. Each comment becomes one space,
so `50(*LDA*),0` cannot become `50,0`. Blank runs collapse. `SEARCH.TEXT`
comes off the volume for the run as well.

5415 commented lines come out as 4466 and 206 blocks. The repository keeps
the commented text; only the disk copy is stripped.

## 84. BODY, its three segments, and the last of segment 1

VERIFIED BINARY FACT unless marked otherwise. Segments 9, 14 and 15 are
complete, and so is segment 1: every procedure of `SYSTEM.COMPILER`'s
outer segment now compiles, under Apple's own 1.3 compiler, to Apple's
p-code instruction for instruction.

### 84a. One procedure, three segments, one frame

II.0's `BODY` is a single procedure. Apple's is `BODY` (BODYPART.24) with
eight instructions —

```
BODY1;
IF SWAPPING THEN HOLDSTMT ELSE BODY2;
BODY3
```

— and the work in three pieces: `BODY1` is segment 14, `BODY2` is
BODYPART.25, `BODY3` is segment 15. Splitting a procedure into segments is
what makes it swappable, and the cost is that all three read `BODY`'s frame
from outside themselves, with `LOD 1,n` and `LOD 2,n`. That is what forces
`BODY1` and `BODY3` to be declared *inside* `BODY` (finding 83b) and what
makes the frame recoverable: nineteen words, and every one of them is
written by one piece and read by another.

```
 1 EXITIC   4 LPREV   7 LOP     10 JTINX  13 LOLDIC  16 LDONELB
 2 LLC1     5 LNEXT   8 LMAIN   11 LMAX   14 LSEGIC  17 LLOADLB
 3 LRES     6 LCP     9 LLP     12 LMIN   15 LI      18 LBODYLB
                                                     19 DUMMYVAR
```

Eleven are II.0's. `LMAIN`, `LRES`, `LPREV`, `LNEXT`, `LI`, `LOLDIC`,
`LSEGIC` and the three `LBP`s are Apple's, and all ten belong to the
segment-holding machinery in 84b. The declaration order is not a choice
either: `LCP,LNEXT,LPREV,LRES: CTP` is one identifier list, because
separate declarations would allocate them the other way round (finding 33),
and the same goes for `LMIN,LMAX`, `LSEGIC,LOLDIC` and
`LBODYLB,LLOADLB,LDONELB`.

### 84b. What `(*$R*)` actually emits

`BODY1` reserves two bytes at the head of the body and puts a label on the
instruction after them:

```
LRES := RESIDENT;
IF (LRES <> NIL) OR LMAIN THEN
  BEGIN LSEGIC := IC;
    GENBYTE(215(*NOP*)); GENBYTE(215(*NOP*));
    GENLABEL(LBODYLB); PUTLABEL(LBODYLB)
  END
```

and `BODY3`, if the block turns out to want segments held, goes back and
overwrites the pair. `HOLDSEGS` — BODY3.2, and it has no II.0 ancestor at
all — writes the whole bracket:

```
	UJP  load          <- the two bytes BODY1 reserved
  body: ...
	<unload each segment>
	UJP  done
  load: <load each segment>
	UJP  body
  done:
```

so the loading runs once on entry, the unloading once on the way out, and
neither is in the path of anything else. It walks `RESIDENT` and
`USINGLIST` **reversing each chain as it goes**, which is why a segment is
unloaded in the order it was named and loaded in the reverse.

That is the shape `BODYPART.27 HOLDSTMT`, `BODYPART.38 HOLDRTN`,
`PASCALCO.30 HOLDMOST` and `PASCALCO.31 HOLDROUT` are made of, and all four
now match Apple's bytes. `HOLDMOST` is the compiler holding *itself*:

```
PROCEDURE HOLDMOST;
  PROCEDURE HOLDROUT;
  BEGIN (*$R 10*)
    COMPILE
  END ;
BEGIN (*$R 8,9,19,11,12,13,14,15*)
  IF SWAPMORE THEN COMPILE ELSE HOLDROUT
END ;
```

— DECLARATIONPART, BODYPART, NUMSTRING, STATEMENT, CASESTATEMENT,
FORSTATEMENT, BODY1 and BODY3 held across the whole compilation, and
ROUTINE as well one level in. The load order in the binary is 8, 9, 19, 11,
12, 13, 14, 15 and the unload order is its exact reverse, which is what the
chain reversal predicts and is the check on it.

The numbers are written rather than the names because eight names do not
fit in eighty columns and `RESSEGLIST` scans one line; both spellings reach
`MARKRESIDENT` with the same value, so they are indistinguishable in the
output. **SPECULATION** as to which Apple wrote.

### 84c. Segment 1's procedure 1, and what is not source

`PASCALCOMPILER`'s own statement part is three statements:

```
BEGIN
  COMPINIT;
  IF NOT SWAPPING THEN HOLDMOST ELSE COMPILE;
  FINISHUP
END;
```

The eight file operations that bracket it in the binary — a `FINIT` for
each of `LP`, `LIBRARY`, `INCLFILE` and `REFFILE` on the way in, an
`FCLOSE` for each on the way out — are not source at all. `BODY2` emits a
`FINIT` for every `FILE` in `DISPLAY[TOP].FFILE` before the first
statement, and `BODY3` emits the `FCLOSE`s after the last. The compiler
compiling itself writes its own prologue.

`procbuild.py` could not check this body before: `sources()` numbers a
file's procedures from 2, because procedure 1 of a segment is the segment
procedure itself. `PASCALCO.text` now ends with a `{PASCALCOMPILER}` marker
and the body after it goes where the skeleton's empty `BEGIN END;` was.

### 84d. The FFILE chain recovers a grouping the offsets cannot

Those eight operations are the sharpest check in the file, and they failed
first time round. Apple's order is LP, LIBRARY, INCLFILE, REFFILE. Ours was
LP, INCLFILE, LIBRARY, REFFILE.

The order is the `FFILE` chain, and `VARDECLARATION` builds it by hanging a
whole declaration group on the head at once:

```
IF NEXT = NIL THEN
  IF LSP^.FORM = FILES THEN
    BEGIN NEXT := DISPLAY[TOP].FFILE;
      DISPLAY[TOP].FFILE := IDLIST
    END
```

So separate declarations interleave in reverse, and a group stays together
and in allocation order. `VAR LIBRARY: FILE; INCLFILE: FILE;` and
`VAR INCLFILE,LIBRARY: FILE;` put the two on exactly the same words and
produce **different chains** — and only the second produces Apple's.

This is the first grouping in the global `VAR` block recovered from the
binary rather than assumed from II.0, and it is worth stating what made it
visible: a declaration group leaves no trace in the frame at all. Offsets
are blind to it. It shows up only where something walks a chain the
grouping built, which here is one procedure emitting eight instructions.
1.1's segment 1 has the same four `FINIT`s in the same order at its own
offsets, so the grouping holds there too.

`varblock.py` grew a `GROUPS` table for it, with the adjacency, the equal
size and the reversed order all checked rather than asserted.

## 85. STATEMENT, and where a segment procedure may be declared

VERIFIED BINARY FACT unless marked otherwise. Segment 11 is complete: all
eight procedures compile, under Apple's own 1.3 compiler, to Apple's p-code
instruction for instruction.

### 85a. Nine procedures, seven of them numbered

II.0's `STATEMENT` is one procedure of `BODYPART` with nine nested ones.
Apple's is a segment procedure with seven, because `CASESTATEMENT` and
`FORSTATEMENT` were made segments 12 and 13. They take no procedure number
in the parent, so the numbering is the declaration order of what is left:

```
  1 STATEMENT       5 IFSTATEMENT       (12 CASESTATEMENT)
  2 ASSIGNMENT      6 REPEATSTATEMENT
  3 GOTOSTATEMENT   7 WHILESTATEMENT    (13 FORSTATEMENT)
  4 COMPOUNDSTMT    8 WITHSTATEMENT
```

and it is not II.0's: II.0 has `WHILE` before `REPEAT`, which is also the
order of the `CASE` arms in `STATEMENT`'s own body. The `XJP` table settles
the arms independently of the procedure numbers, and the two disagree — the
`CASE` dispatches WHILE before REPEAT while the declarations run REPEAT
before WHILE, so neither can have been derived from the other.

`STATEMENT`'s own body carries a `LABEL 1` and a `GOTO 1` out of the middle
of the label search, and closes over a follow set of five symbols including
`SEPARATSY`. That last one was nearly misread: the `LDC 4w` set constant
prints as `[$0001 $0000 $0138 $0001]` for `CONSTBEGSYS`, which is what
proves our decoder prints w0..w3 and therefore that the bit is 54
(`SEPARATSY`) and not 47 (`OTHERSY`) — and `OTHERSY` would have compiled to
`SLDC 47` anyway.

### 85b. `(*$I *)` and error 399

The first run of segment 11 under Apple's compiler stopped at

```
    SEGMENT PROCEDURE <<<<
Line 2576, error 399
```

and the compiler explains itself. `PROCDECLARATION` opens with

```
IF SEGDEC THEN
  BEGIN
    IF CODEINSEG THEN
      BEGIN ERROR(399); SEGINX:=0; CURBYTE:=0 END;
```

and `CODEINSEG` goes true in `BODY3` the moment any procedure body is
written into the current segment, staying true until `FINISHSEG` clears it.
So **a segment procedure has to be declared before the first ordinary
procedure of the block that encloses it.** II.0 declares `CASESTATEMENT`
between `IFSTATEMENT` and `REPEATSTATEMENT`; Apple could not, and the two
segment declarations have to head `STATEMENT`'s declaration part — which is
exactly where `BODYPART` already keeps `ROUTINE`, `STATEMENT`, `BODY1` and
`BODY3`.

This is a placement recovered from the compiler's own rule rather than from
the offsets, and it costs nothing to check: any other placement fails to
compile at all. It also leaves the seven numbered procedures untouched,
since a segment takes no number.

### 85c. Three things in the frame that do nothing

`IFSTATEMENT` declares `LCONST,LVAL: BOOLEAN`. `LCONST` is set false once
and never set again, nothing anywhere assigns `LVAL`, and three arms of the
procedure are guarded by them:

```
IF LCONST THEN
  BEGIN IF NOT LVAL THEN IC := LOLDIC END
ELSE PUTLABEL(LCIX2)
```

The arms are unreachable, the two words are in the frame, and the code for
them is in the binary. **STRONG INFERENCE** that this is constant folding of
`IF` conditions, written and then disabled by the one assignment.

`WITHSTATEMENT` declares an `LLC: ADDRRANGE` it never touches. II.0's
`WITHSTATEMENT` saves `LC` there and restores it at the end; Apple moved the
save and restore up into `STATEMENT`, where `MARK`/`RELEASE` and `LC := LLC`
now bracket *every* statement rather than only a `WITH`, and the word stayed
behind.

`ASSIGNMENT` has an `ELSE` with nothing after it:

```
IF LSTRGCST AND (GATTR.TYPTR = CHARPTR) THEN
  GATTR.TYPTR := STRGPTR
ELSE
  ELSE
```

which is what keeps the outer `ELSE` attached to the outer `IF`. The binary
shows the branch ending in a jump over an else part that is not there, and a
plain `IF`-`THEN` does not emit one, so the empty `ELSE` is visible in the
code.

### 85d. The volume ceiling, and the split Apple used too

The spliced source reached 276 blocks, and an emptied Disk II volume has
274. `(*$I *)` is the remedy, and `write_for_emulator` now takes it: the
break goes at a top-level procedure heading nearest the halfway point, part
one keeps `WORK:BODY13.TEXT` with an `(*$I WORK2:BODY13B*)` line on the end,
and part two goes to `WORK2:` beside the codefile — 3043 lines and 2870,
with 128 and 142 blocks left over. The include is textual and would work
anywhere; the heading is chosen so the seam is readable.

With segment 11 in, the 1.3 reconstruction stands at **128 of 128 bodies
matching Apple's p-code under Apple's own compiler**, with `ROUTINE`,
`CASESTATEMENT` and `FORSTATEMENT` the three remaining stubs.

## 86. CASESTATEMENT and FORSTATEMENT, STATEMENT's two segments

VERIFIED BINARY FACT unless marked otherwise. Both now compile, under
Apple's own 1.3 compiler, to Apple's p-code instruction for instruction:
segment 12 in 303 instructions, segment 13 in 272.

### 86a. Segment 12, and one UJP too many

`CASESTATEMENT` is II.0's, with the case list still built as a sorted
chain of three-word `CASEINFO` records and reversed before the jump table
is emitted. The frame is 28 bytes — fourteen words, thirteen declared and
one the compiler takes for the `WITH`, which all three `WITH` statements
reuse. With reverse allocation inside a list (finding 33) there is exactly
one arrangement of the declarations that puts `LSP1` at 1 and `LMIN` at 12.

The sharpest correction came from a single instruction. The natural way to
write the insertion walk is

```
IF CSLAB <= LVAL.IVAL THEN
  BEGIN IF CSLAB = LVAL.IVAL THEN ERROR(156); GOTO 1 END
ELSE BEGIN LPT2 := LPT1; LPT1 := NEXT END
```

and that emits two `UJP`s: one for the `GOTO` and one jumping over the else
part. Apple's segment has exactly one. The else part is not there at all —
the `GOTO 1` **is** the branch, and the walk falls through to the step:

```
WHILE LPT1 <> NIL DO
  WITH LPT1^ DO
    BEGIN
      IF CSLAB <= LVAL.IVAL THEN
        BEGIN IF CSLAB = LVAL.IVAL THEN ERROR(156); GOTO 1 END;
      LPT2 := LPT1; LPT1 := NEXT
    END;
```

Apple's compiler always emits the jump over an else part, so an `ELSE`
here cannot be hidden: counting `UJP`s decides it. The `LABEL 1`/`GOTO 1`
pair is II.0's and is what makes the shape legal.

The `OTHERWISE` clause is Apple's addition — symbol 54, which 1.1 spells
`SEPARATE` — and it appears three times: in the follow set handed to
`STATEMENT`, in the `UNTIL` of the outer loop, and as the clause itself,
between `PUTLABEL(LCIX1)` and `PUTLABEL(LCIX)`. The generated skeletons
still name the enumerator `SEPARATSY`, so that is what the source has to
say to compile today; the rename is unresolved.

The three `LBP`s occupy 8, 9 and 10 in the order they are first used, so a
single list has to name them in the reverse of that order. A list in II.0's
order — `LADDR,LCIX,LCIX1` — allocates the same three words and compiles to
the same bytes with all three names moved one role along. **SPECULATION**
as to which Apple wrote; the offsets cannot tell them apart.

### 86b. Segment 13, and a word nothing touches

`FORSTATEMENT`'s frame is twenty bytes — ten words. Five are `LATTR`, one
each are `LSY`, `LADDR` and `LCIX`, one is the `WITH LCP^` temp, and the
word at offset 6 is never touched by any instruction in the segment.

That word is II.0's `LSP`. II.0 keeps the control variable's type there and
range-checks against `LSP^.MIN`/`LSP^.MAX`; Apple's code goes back to
`LATTR.TYPTR^` each time and never assigns it, so the declaration survives
with nothing reading it — the same leftover as `WITHSTATEMENT`'s `LLC`
(finding 85c). Its position between `LATTR` and `LSY` is fixed by the
offsets. **STRONG INFERENCE** that it is an `STP`, **SPECULATION** as to
the name. `LADDR` at 8 and `LCIX` at 9 are one list named in the reverse of
the order they are used, exactly as in 86a.

The control variable is not searched for in `FORSTATEMENT`'s own frame at
all. `SEARCHID(VARS,LCP)` writes into `LCP` at `1,5` — *`STATEMENT`'s*
fifth word — and the `WITH` copies it from there. That is an independent
check on `STATEMENT`'s declarations: `LCP` has to be its fifth word, and
`LDISX`, `LLP`, `LMARKP` and `LLC` the four after it, for this segment to
compile as Apple's does. Segment 12 does not reach out of itself this way;
segment 13 does it twice.

Two details II.0 would not predict. The loop limit is stored with
`GEN2(56(*STR*),LEVEL,LC)` and `LC` is stepped once and never given back
inside this segment. And the step is `GENLDC(1)` followed by `GEN0(2
(*ADI*))` or `GEN0(21(*SBI*))` — one increment either way, chosen by the
saved `LSY` rather than by re-reading `SY`, which is what makes the saved
symbol a local at all.

With both segments in, the 1.3 reconstruction stands at **130 of 130
bodies matching Apple's p-code under Apple's own compiler**, and `ROUTINE`
— segment 10, seventeen procedures, 2892 bytes — is the only stub left.

## 87. ROUTINE — segment 10, and the reconstruction is complete

VERIFIED BINARY FACT unless marked otherwise. Segment 10's seventeen
procedures now compile, under Apple's own 1.3 compiler, to Apple's p-code
instruction for instruction. With them in, the count is **147 of 147
bodies matching, 0 stubs**: every p-code procedure of `SYSTEM.COMPILER`
1.3, plus `IDSEARCH` and `TREESEARCH`, which the assembler tier holds
byte-identical (finding 57a).

### 87a. Apple turned ROUTINE inside out to reach CALL's own CASE

II.0 split this work in two. `ROUTINE` took the twenty-one keys that need
real argument parsing; the rest stayed inline in `CALL` as a `CASE`. Apple
moved that whole `CASE` down into the segment as **`SPECIALS`, procedure
17**, and inverted `ROUTINE`'s body to reach it:

```
IF NOT (LKEY IN [12,13,14,15,18,19,21,22,23,27,31,32,34,35,36,37,38,
                 40,41,42,43]) THEN SPECIALS
ELSE CASE LKEY OF ...
```

The `LNOT` before the `FJP` is what proves the `NOT`; the set is a
three-word constant, `$F000 $88EC $0F7D`, which is exactly those
twenty-one keys — II.0's membership test with the sense reversed. The
`XJP` arm map is II.0's arm order unchanged, and `SPECIALS`' own `XJP`
runs 5..44 with everything unlisted falling to the default.

`ROUTINE`'s frame is 24 bytes — twelve words, six of them parameters,
leaving three four-word sets assigned in the first three statements of the
body. Reverse allocation inside a list (finding 33) fixes which offset is
which: `FSYS + [COMMA]` at 15, `FSYS + [RPARENT]` at 11, their union at 7.
The names are **SPECULATION**; that they exist and are computed once is
not — II.0 rebuilt `FSYS + [COMMA,RPARENT]` at every call site.

Two small helpers are Apple's. `GETCOMMA` and `CHECKINT` are procedures 2
and 3, and they replace the twenty-odd longhand copies of
`IF SY = COMMA THEN INSYMBOL ELSE ERROR(20)` and
`IF GATTR.TYPTR <> INTPTR THEN ERROR(125)`. They have to be declared
first: every `CIP 2` and `CIP 3` in the segment depends on it, and so does
the number of every procedure after them.

### 87b. Where Apple changed II.0's behaviour, and not just its shape

* **`IDSEARCH` and `TREESEARCH` compile to `ERROR(124)`**, not to `CSP 7`
  and `CSP 8`. In 1.3 they are native 6502 and are reached as ordinary
  external procedures (finding 44), so the compiler refuses the intrinsic
  form outright. `TREESEARCH` also leaves `GATTR.TYPTR` `NIL` where II.0
  set `INTPTR`.
* **`UNITSTATUS`, key 44, is Apple's** and has no II.0 original: an
  integer unit number, a byte-addressed buffer, and a boolean direction,
  then `CSP 12 (UST)`.
* **`NEWSTMT`'s two `ERROR(116)` become `ERROR(125)`**, and so does
  `STR`'s.
* **`SEEK` with no second argument is `ERROR(20)`**, not `ERROR(125)` —
  it goes through `GETCOMMA` like everything else.
* **`ORD` rejects a type whose `SIZE` is not 1** as well as one whose
  `FORM` is at or past `POWER`.
* **`EXIT` calls `NEWPROC` when `PFNAME` is still 0**, and its
  `LINKERREF` is guarded by `NOT INTRINSIC` and points at `IC-1`, not
  `IC-2`; II.0's second `LINKERREF` for a separate procedure is gone.
* **`CONCAT` and `COPYDELETE` both drop II.0's final `LC := LLC`**, and
  `CONCAT` passes `LEVEL` to `STR` and `LDA` where II.0 passed 0.

### 87c. Two things the tooling learned

**The fast tier allocates no `WITH` temporary.** Apple's compiler takes
one word of the frame per `WITH` statement; `ucsdpsys_compile` takes none.
Comparing frame sizes across the 130 procedures that were *already*
verified against Apple's own compiler turns up 57 mismatches and every one
of them is exactly one word per `WITH` in that body. So a fast-tier frame
that is short by the `WITH` count is not evidence of a source error —
which is what let `STRGVAR` and `EXIT` through, each low by one word, with
the other fifteen exact. **VERIFIED SOURCE FACT** for Apple's side (the
frames are in the binary); the fast tier's behaviour is measured, not
documented.

**`SCAN` and `SIZEOF` are reserved words in `ucsdpsys_compile`.** They are
UCSD intrinsics with their own argument syntax and its grammar builds them
in, so no program compiled there may *declare* a procedure of either name:
*"syntax error, unexpected SCAN, expecting NAME or TYPE_NAME"*. Apple's
compiler will, and segment 10 declares both, exactly as II.0 did.
`procbuild.py` now renames them for the fast tier only, and only where
they are being declared — the regex is anchored on the `;` of the heading
or the `*)` of the closing comment, which is the one form the intrinsic
never takes. A blanket rename would be wrong: `SCAN(` is genuinely called
as an intrinsic in `PASCALCO`, `COMPINIT` and `COMPOPTI`, and both names
appear inside `ADDNAMES` string literals.

### 87d. The compiler is invoked from the menu, and it is not `{$U-}`

**VERIFIED BINARY FACT.** Three separate refusals stand between a fresh
128K boot and a running compiler, and none of them is a privilege:

| typed | answer | why |
|---|---|---|
| `X` `*SYSTEM.COMPILER` | *Illegal file name* | X appends `.CODE`; `SYSTEM.COMPILER.CODE` is 20 characters against a 15-character limit |
| `X` `*SYSTEM.COMPILER.` | *No file `*SYSTEM.COMPILER`* | the boot volume is `BOOT128:` — APPLE1 with the 128K system substituted in — and the compiler is on `APPLE2:`, in drive 2 |
| `X` `APPLE2:SYSTEM.COMPILER.` | *Line 0, error 401* | it runs, prints *"Apple Pascal Compiler [1.3]"* and asks for a listing file — then looks for its source in the system workfile, and there is none |

So **`C(ompile` from the command menu is the way in**: it prompts for the
source file and the codefile instead of reaching for a workfile, which is
what `tools/emucompile.ps1` sends —
`CWORK:BODY13.TEXT{ENTER}WORK2:BODY13.CODE{ENTER}{ENTER}`.

It would be natural to read the 401 as a `{$U-}` restriction — a system
program that may not be `X`'d. It is not. `PASCALCO.1` carries `lex 0`,
the ordinary user-program level, and finding 47 found the `$FF` lex byte
on 7 of 39 codefiles across the six disk images — both operating systems,
`128K.PASCAL`, `SETUP`, the two `GOTOXY` replacements — and never on
`SYSTEM.COMPILER`. Finding 23c already said the compiler was not built
`{$U-}`; this is the same fact seen from the console. The 401 is `NEXTBLOCK`
raising *"Unexpected end of input"* on an empty workfile (finding 27),
nothing more.

### 87e. What is left

The 1.3 reconstruction is whole. What has not been done is pushing it
through the correspondence table to 1.1 — `src/pascal/` has only `1.3`,
and `procbuild.py`'s 1.1 pass finds no sources to compile. **Superseded by
finding 88**: `src/pascal/1.1/` exists and compiles; what is left there is
the per-procedure diff, not the port.

## 88. The 1.1 port — `src/pascal/1.1` and what the two releases differ by

Finding 87e left the reconstruction whole for 1.3 and untouched for 1.1.
`src/pascal/1.1/` now exists: the 1.3 tree copied across and edited against
the 1.1 binary until it compiles, declares exactly Apple's 1.1 procedure
list in Apple's order, and produces a per-procedure diff. Everything below
is read out of `SYSTEM.COMPILER` on
`Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk`, so it is **VERIFIED BINARY
FACT** unless said otherwise.

### 88a. Five procedures 1.3 has and 1.1 does not

Declaration order is procedure numbering (finding 61), so a procedure that
1.3 added shifts every number after it. The correspondence table already
had the shifts; what it did not say is what the extra procedures *are*.

* **`IDSEARCH` and `TREESEARCH`**, the two `EXTERNAL` native declarations
  in segment 1. 1.1 has no native code (finding 44) and no forwards for
  them.
* **`CHECKVERS`** in `COMPINIT`. 1.1's `COMPINIT` ends `ENTSTDTYPES` at
  `STRGPTR` and has no version check at all; the frame is 518 bytes
  against 1.3's 608, which is `LNAMES` 256 words plus `NPOS`, `NCHARS`
  and one `WITH` temp and nothing else.
* **`INITUNIT`** in `BODYPART`. 1.1 walks `USINGLIST` inline in `BODY2`
  and emits `CXP 77` for each `MODSEG` entry. 1.3's separate procedure is
  a documented bug fix (finding 42a).
* **`MARKRESIDENT`** in `COMPOPTI`, the fifth procedure of a segment
  Apple's 1.1 gives four. 1.1's `RESSEGLIST` builds the `RESIDENT` node in
  place at all three `(*$R*)` sites — `NEW`, `SEGID`, `NEXT`, `RESIDENT` —
  and never sets `MODLINK`, which 1.3's factored version does. The local
  that holds the new node is `L1`, the slot 1.3 later gave to the unused
  `LSEG: INTEGER`. It also has no `ELSE ERROR(273)`: an unknown name in a
  `(*$R*)` list is silently ignored in 1.1.

Four globals go with them — `ISPROG`, `HAS128K`, `CONLIST`, `LSTOPEN` —
and so do the `BYTEPTR` and `WORDPTR` standard types (finding 83f).

### 88b. What the missing globals were guarding

Each of the four is one test, and the 1.1 binary shows what stands in its
place.

* **`ISPROG`** exists only to pick between two branches in `FINISHUP`.
  1.1 has neither branch: it is always `MOVELEFT(SEGSUSED,PROCTABLE,4)`
  followed by two `GENWORD`s, four bytes and two words because 1.1's
  `SEGSUSED` is a two-word set over 32 segments. `BLOCK` correspondingly
  has no `ISPROG := NOT INMODULE`.
* **`HAS128K`** is `BLOCK`'s `IF SWAPPING OR HAS128K`; 1.1 tests
  `SWAPPING` alone.
* **`CONLIST`** appears twice. `ERROR`'s early exit is
  `IF LIST AND (ERRORNUM <= 400)`, and the `Q` option is plain
  `NOISY := (SW = '-')`.
* **`LSTOPEN`** is the `L` option's guard. 1.1 rewrites the listing file
  unconditionally, and the name is `'*SYSTEM.LST.TEXT'` without 1.3's
  `[*]`.

### 88c. Three more differences in `FINISHUP`, and two in `ERROR`

`FINISHUP` is the tail of the segment dictionary and every word of it is
visible, which makes it the easiest place to see the release boundary.

* The `SEGINFO` loop is guarded in 1.1:
  `IF SEGTABLE[SEG].SEGNUM <> 0 THEN GENWORD(SEGINFO(SEG)) ELSE
  GENWORD(0)`. The field is offset 6 — `SIND 6`, the same word `SEGINFO`
  itself reads — which is `SEGNUM` under the backwards field allocation
  the skeleton already assumes (`SEGKIND, TEXTADDR, SEGNUM` declares them
  at 8, 7, 6).
* 1.1 has a trailing block 1.3 dropped: when `SEGSUSED * [30,31]` is not
  empty it emits `GENBYTE(42); GENBYTE(0)`, then `GENBYTE(seg);
  GENBYTE(6); GENBYTE(0)` for each of segments 30 and 31 that is used, and
  a final `GENBYTE(0)`.
* The comment field is copied whole: `IF COMMENT <> NIL THEN
  MOVELEFT(COMMENT^[0],CODEP^[IC],80) ELSE FILLCHAR(CODEP^[IC],80,CHR(0))`.
  1.3's `NEW(COMMENT)`/`LENGTH(COMMENT^)` version is later.

In `ERROR`, the `<sp>(continue), <esc>(terminate), E(dit` prompt is
guarded by `IF NOISY`, and the `REPEAT ... UNTIL` reads
`USERINFO.ALTMODE` — `LOD 2,15` — where 1.3 has a literal `CHR(27)`. The
`IF (ERRORNUM > 400) OR (CH = CHR(27))` two lines below is a literal in
*both*, which is finding 66c seen from the other release.

### 88d. `pairdiff.py` -- asking whether a 1.1 body's leftover is 1.3's

The fast tier can falsify a body but cannot accept one (findings 58c, 87c),
so most procedures come back DIFFERS for reasons that have nothing to do
with the source. Reading each one to decide which is a slow way to spend a
port, and there is a control the single-version comparison does not use:
the 1.3 tree is verified procedure by procedure against Apple's own
compiler (finding 87). So for a procedure that exists in both releases,

    if  diff(Apple 1.1, ours 1.1)  ==  diff(Apple 1.3, ours 1.3)

then whatever the fast tier is doing to the 1.1 body it does identically to
a 1.3 body that is known right. That is not proof -- the 1.1 body inherits
exactly the confidence 1.3's has, no more -- but it takes the procedure off
the worklist. `tools/pairdiff.py` does this, pairing bodies by name and
rewriting 1.1's global offsets and procedure numbers into 1.3's from
`correspondence-1.1-to-1.3.txt` first, so that only a difference of
substance survives. What it prints is the chunks 1.1 diverges in that 1.3
does not.

Five normalisers were added to `procbuild.py` while working the list, all
of them documented spelling differences and all applied to **both** sides:

* `drop_nops` -- alignment padding.
* `addressing` -- `SLDC e; MPI; [SLDC f; ADI;] IXA 1 [; SIND 0]` against
  `IXA e [; SIND/IND/INC f]`, and a constant index into a global array,
  `LAO n; SLDC k; IXA s` against `LAO n+ks`.
* `foldset` -- `(SLDC|LDCI) v; SLDC 1; ADJ n`, and the empty set's
  `SLDC 0; ADJ n`, against the fast tier's zero-padded push.
* `forlimit` -- a FOR statement's limit. Apple evaluates it once into a
  frame word and reloads it each pass, `<limit> STL n <var> SLDL n LEQI`;
  the fast tier keeps no temporary and re-evaluates in place. Rewritten
  only where limit and control variable are one instruction each.
* `unfold` (ours only) -- a one-character literal as CHAR rather than
  STRING[1].

`pairdiff` adds two of its own: naming the topmost frame word `WITHTMP`
where Apple's frame is larger than ours, and accepting a chunk that is a
lone `LAND`/`LOR`, a lone conditional jump, or nothing but references to
frame words -- the two compilers do not allocate the same temporaries.

The effect is a floor moving, not a score: the instruction-identical count
across both trees went 46 -> 93 as the normalisers went in, 1.3's own half
rising with 1.1's, which is the control confirming they only removed noise.

### 88e. The per-procedure deltas the diff turned up

Everything here is 1.1 behaviour read off the 1.1 binary, against what the
1.3 file said. These are the source changes the port needed beyond 88a-c.

* **`CASESTATEMENT`** has no `OTHERWISE` clause -- 1.3 added it -- and with
  it goes 1.3's third label. Without an `OTHERWISE` part the default arm of
  the `XJP` has nowhere to go but the end of the statement, so one label
  serves both the default jump and the jump out of each arm. 1.3 also
  guards the jump table with `IC + (LMAX-LMIN)*2 >= MAXCODE` / `ERROR(302)`;
  1.1 emits it unchecked. The frame is thirteen words, not fourteen.
* **`STATEMENT`** does not bracket every statement with `LLC := LC` /
  `IF LC > LCMAX THEN LCMAX := LC` / `LC := LLC`. That bookkeeping is in
  **`WITHSTATEMENT`** and **`FORSTATEMENT`** instead, each counting what it
  allocated and handing it back: `WITHSTATEMENT` keeps a second counter
  beside `LCNT` and ends `TOP := TOP - LCNT; LC := LC - LCCNT`, and
  `FORSTATEMENT` ends `LC := LC - 1` after `PUTLABEL(LCIX)` and raises
  `LCMAX` where it steps `LC`. 1.3 hoists all of it into `STATEMENT` and
  leaves `WITHSTATEMENT`'s word behind as an unused `LLC`. `STATEMENT`'s
  follow set is `[SEMICOLON,ENDSY,UNTILSY,ELSESY]` -- one word, $2608 --
  with no `SEPARATSY`.
* **`SIMPLETYPE`** calls `INSYMBOL` once, straight after
  `SEARCHID([TYPES,KONST],LCP)`, where 1.3 calls it separately in each arm;
  the `STRGPTR` test is then one condition, `(LSP = STRGPTR) AND
  (SY = LBRACK)`, and the `INTPTR` arm is a plain nested `IF`.
* **`TYP`** reports a non-positive array size as `ERROR(398)`, not 399.
* **`DECLARATIONPART`** still makes II.0's stack-and-heap display call,
  `IF NOISY THEN UNITWRITE(3,DUMMYVAR[-1600],0,35,0)`. 1.3 drops the call
  and keeps `DUMMYVAR`. This one cannot be checked in the fast tier at all:
  Apple emits the -1600 as `LDCI 1600; NGI` where `ucsdpsys_compile` folds
  it, and both compilers push a sixth word for the CSP -- Apple's last,
  `ucsdpsys_compile`'s fourth -- while six explicit arguments are a fatal
  error there. It wants the emulator tier.
* **`STRING`** has no `TOOLONG`: it stores every character without the
  `TP <= 80` test and never reports 277.
* **`HOLDSEGS`** unloads `USINGLIST` *before* `LRES` and loads it *after*,
  the reverse of 1.3, and emits no `IF LCP^.MODLINK THEN LINKERREF` for an
  `LRES` segment at either end.
* **`SPECIALS`** compiles `IDSEARCH` and `TREESEARCH` as the intrinsics
  they are, `GEN1(30,7)` and `GEN1(30,8)`, and `TREESEARCH` sets
  `GATTR.TYPTR := INTPTR`. 1.3 makes them native 6502 and refuses the
  intrinsic form with `ERROR(124)`.
* **`COMPOPTIONS`**: the quiet flag is `'O'`, not 1.3's `'Q'` -- the arm
  sits between `'N'` and `'P'` in the jump table, which fixes the letter.
  The `'S'` arm does not re-read `DEL` after stepping `SYMCURSOR`.
* **`CONSTANT`** negates only the first word of a long constant, in both
  places, where 1.3 walks all `LLENG` of them; there is no loop counter in
  the frame.
* **`BLOCK`** releases `TOS^.DMARKP` unconditionally; 1.3 guards it with
  `TOS^.DFPROCP <> OUTERBLOCK`.
* **`ERROR`** does not `CLOSE(LP,LOCK)` on the way out of a fatal error.
* **`CALLNONSPECIAL`** reports a non-`ACTUAL` `PFKIND` as `ERROR(400)`,
  not 399; keeps no copy of `GATTR.ACCESS`; and emits `GEN2(77,0,PFNAME)`
  for an imported procedure where 1.3 emits `GEN2(77,PFSEG,PFNAME)`.
* **`INITSCALARS`** clears `SEGSUSED` as a two-word set: the ceiling is 31
  in 1.1, 63 in 1.3, the same bound as `BUMPSEG`, `KINDSET`, the `$NS`
  limit and the linker's KEY offset.

### 88f. Where the tree stands

`procbuild.py` compiles both versions and reports zero stubs, zero
"Apple has it, we do not" and zero "we have it, Apple does not" in either.
93 of the 289 bodies across the two releases come out instruction-identical
under the fast tier, and `pairdiff.py` puts 89 of 1.1's still-differing
bodies at exactly 1.3's diff and no more.

The nine that remain have each been read, and none of them is a source
question:

* `PASCALCOMPILER` -- the `FINIT` calls the compiler emits for the outer
  block's four `FILE`s. Apple passes a 40-character title buffer and -2/-1;
  `ucsdpsys_compile` passes `LDCN` and -1, and in a different order.
* `ERROR` -- the `UNTIL (CH=' ') OR (CH='E') OR (CH='e') OR (CH=ALTMODE)`
  chain, `LOR` against a jump chain (finding 58c).
* `INSYMBOL` -- a `CASE` with sixty arms, laid out in source order by Apple
  and in label order by the fast tier, so the two listings do not align at
  all. Lifting both *binaries* and comparing those shows the releases
  differ in exactly one line: 1.1's `IDSEARCH` is the intrinsic, 1.3's is
  `PASCALCO.2`. Nothing else in the procedure changed.
* `CONSTANT` -- `LONGVAL[1]`, whose `(1-1)` Apple computes at run time and
  the fast tier folds.
* `FINDFORW`, `CALLNONSPECIAL`, `COMPINIT` -- the `WITH` temporary alone
  (finding 87c).
* `FACTOR` -- the two releases' binaries lift identically and the two
  source files are byte-identical; the chunks are placement.
* `DECLARATIONPART` -- the `UNITWRITE` above, which the fast tier cannot
  spell.

Comparing two *lifts* rather than two listings is the technique that broke
the last of these open, and it is worth keeping: the lift is in source
order on both sides, so a procedure whose `CASE` defeats the p-code diff
still yields a readable answer.

That is the fast tier exhausted. What is left is the emulator tier: build
1.1 under Apple's own 1.1 compiler and compare the codefile.

### 88g. The header comments, audited

The phase files' header comments came across with the copy and described
the segment as 1.3 has it. `BODYPART`'s "38 procedures", `CASESTAT`'s
`OTHERWISE` note and `ROUTINE`'s list of "where Apple changed II.0's
behaviour" were corrected with the port; `PASCALCO`'s was rewritten. The
remaining eleven were byte-identical to 1.3's, and have now been read
against the 1.1 binary. Four carried a claim that is 1.3's and not 1.1's,
and they are corrected in `src/pascal/1.1/`:

* **`COMPINIT`** claimed "four additions", two of which 1.1 does not have.
  There is no `CHECKVERS` -- the body opens `INITSCALARS; INITSETS` and
  never reads `SYSTEM.PASCAL`'s version -- and no listing-file prompt:
  no `LTITLE`, no `LSTOPEN`, no `CONLIST`, and the banner is II.0's seven
  blank lines with `'Apple Pascal Compiler [1.1]'`. What is left is the
  512-byte name buffer, which the 518-byte frame confirms. Ten procedures
  here against 1.3's eleven.
* **`FORSTATE`** claimed the loop-limit word is "stepped once and never
  given back here". That is 1.3, which hoists the bookkeeping into
  `STATEMENT` (88e). 1.1's `FORSTATEMENT` claims and releases it itself:
  `LC := LC + 1` with `IF LC > LCMAX THEN LCMAX := LC` where the limit is
  stored, and `LC := LC - 1` after the closing `PUTLABEL(LCIX)`. The rest
  of that header holds in 1.1 -- ten words, `LATTR` five, the untouched
  word at offset 6, `LADDR` at 8 and `LCIX` at 9.
* **`STATEMEN`** gave 1.3's addresses for the declaration order it reads
  off the code. In 1.1 the run is `ASSIGNMENT` at `$0000` through
  `WITHSTATEMENT` at `$03B4`, with `STATEMENT`'s own body last at `$04A8`.
  The order itself, and both segment children at lex 3, are unchanged.
* **`COMPOPTI`** said nothing about the release at all, which for this
  segment is misleading: four procedures against 1.3's five, and the quiet
  option is `'O'` (88e). Both are now in the header.

`DECLARAT`'s header was wrong in a way that has nothing to do with the
release, and is wrong in the 1.3 file too: the hoisted sets are not "one
in `DECLARATIONPART`'s frame for each of the four declaration parsers".
There are two there, `LIDSYS` and `LLABSYS`, which is what makes that
frame eleven words, plus `LCRSYS` in `SIMPLETYPE` and `LSEMSYS` in
`FIELDLIST` -- four in all. Corrected in 1.1; `src/pascal/1.3` still
carries the old wording, and being a comment it changes no byte of the
verified codefile.

The other six -- `BODY1`, `BODY3`, `FINISHUP`, `NUMSTRIN`, `UNITPART`,
`WRITELIN` -- were checked claim by claim and stand as written for 1.1.
`BODY1` is the strongest of those: the two lifts differ in nothing but
procedure numbers, so the header transfers whole, `GENBYTE(215)` reservation
included.

## 89. `OSPROC43` is the file-title normaliser, and it is `FILEPROC.8`

Finding 79b recovered the *number* -- the compiler names the operating
system by declaring 42 unresolved `FORWARD`s and calling the 43rd -- and
left what it does open, with the method written down: disassemble
`FILEPROC.8`. Done. Everything here is **VERIFIED BINARY FACT** off
`SYSTEM.PASCAL` on both three-disk sets, except where marked.

### 89a. The forwarder, and how the parameters get there

`SYSTEM.PASCAL`'s procedure 43 is seven instructions and identical in 1.1
and 1.3, byte for byte:

    SLDC 4 ; LAO 4 ; SLDO 3 ; SLDO 2 ; LDO 294 ; SLDO 1 ; CXP 6,1

`FILEPROC.1` is a four-arm dispatcher over one shared six-word signature,
and `4` is the arm that calls `FILEPROC.8`. The rest of the push is the
signature being filled: `@G4` is procedure 43's own 291-word local buffer,
which arm 4 never looks at, and `G294` the last word of it, which arm 4
never looks at either. Both are there because arms 1..3 want them.

**Why the operands are globals in a procedure that has parameters.** The
operating system is built `{$U-}`, so its outer block is lex -1 (finding
47) and its procedures are lex 0 -- which makes a procedure's *own* frame
the one `LDO`/`SLDO`/`LAO` reach, and the outer block's variables the
*intermediate* ones the lift renders `I1,n`. So `SLDO 1,2,3` are procedure
43's three parameter words and `LDO 294` a local. Read the other way round
this is nonsense, and it is worth stating because every lex-0 procedure in
`SYSTEM.PASCAL` reads this way.

Parameters are allocated backwards (finding 33), so the compiler's

    LAO 1 ; SLDC 1 ; SLDC 40 ; CXP 0,4

leaves the string at word 3, the flag at 2 and the length at 1, and arm 4
hands `FILEPROC.8` exactly those three in that order.

### 89b. What it does

`FILEPROC.8(VAR S: STRING; ISTEXT, N: INTEGER)` -- 3 parameter words, 90
words of local -- is the routine that turns what a user typed into a file
title. In order:

1. Every blank is deleted, wherever it is.
2. If `S` is empty, nothing happens.
3. If `S` ends in `'.'` the period is dropped and **nothing else is done**
   -- that, and only that, is what defeats the suffix.
4. Otherwise a trailing `[...]` size specification is split off and held
   aside.
5. If what is left ends in `':'` it is a volume name and takes no suffix.
6. Otherwise `a`..`z` are upshifted and every character below `' '` becomes
   `'?'`; then the suffix -- `'.TEXT'` if the flag is set, `'.CODE'` if not
   -- is appended, unless the last five characters already are it, or the
   result would not fit: the test is `LENGTH(S) + LENGTH(bracket) <=
   N - 5`, which is what makes the third parameter the *declared* length of
   the caller's buffer.
7. The size specification is put back on the end.

Every one of those is in the 1.3 manual, which is the confirmation this
had to have: "the suffix .TEXT is automatically supplied ... if you want to
prevent this from happening, add a period to the end of your filename"
(II-2, Compiler prompts), the same rule again for the Editor and the
Assembler, and the codefile's `.CODE[8].` example at II-2 for the
interaction with a size specification.

### 89c. The call sites, and a cross-check on finding 88a

`CXP 0,43` occurs **twice** in 1.1's `SYSTEM.COMPILER` and **three times**
in 1.3's, and the third is the one this port has just been reading about
from the other side: 1.3's `COMPINIT.1` normalises the title typed at the
listing-file prompt, in an 80-byte buffer, and 1.1 has no such prompt
(finding 88a). The other two are in `COMPOPTI.1` and are in both releases:
the `(*$I*)` include title, about to be `RESET`, and the `(*$L*)` listing
title, about to be `REWRITE`n -- both `LTITLE`, `LLA 7`, declared
`STRING[40]`.

All of them pass the flag as `SLDC 1`: **the compiler only ever asks for
`.TEXT`**. The `.CODE` half of the routine is reached from the operating
system's own Command level, which calls it with `0` on a 23-byte buffer
where it is about to `FOPEN` a codefile, and that is where a compiled
program's output title gets its suffix.

`tools/probes/probe_osproc43.py` re-derives all of this from the four
binaries -- the forwarder instruction for instruction, the dispatcher's
arm, `FILEPROC.8`'s literals and the two constants it compares against,
the five-character length guard, the clamp's presence in 1.3 and absence in
1.1, and the call-site census -- and `build_all.py` runs it.

### 89d. One release difference, in the direction 1.3 usually goes

1.1's loop upshifts and does nothing else; 1.3 adds
`IF S[I] < ' ' THEN S[I] := '?'`. Every other line of the procedure is the
same, and the forwarder and both frame sizes are identical, so a control
character in a typed title reaches the directory in 1.1 and is fenced in
1.3.

### 89e. What is still not recovered

The *name*. II.0's `GLOBALS.TEXT` has 42 forwards and stops at `COMMAND`,
Apple's 43rd has no II.0 counterpart, and nothing in the codefile names a
procedure that is not a segment's procedure 1 (finding 30). The
reconstruction keeps `OSPROC43`, which says what is actually known -- a
procedure number -- and is eight characters, so it is what Apple's compiler
sees. Naming it for its behaviour would be SPECULATION dressed as a
recovery; the behaviour is written down here instead.


## 90. The p-code diff had a blind spot, and it was hiding two real errors

Finding 87 closed the reconstruction at *147 of 147 bodies matching Apple's
p-code*, and `docs/VERIFY-1.3.md` is the runbook for reproducing it. The
claim was true as stated and weaker than it sounded. Re-running the
verification and then comparing the **bytes** rather than the disassembly
found two places where the reconstruction and Apple's binary genuinely
differ. Both are now fixed, and the check that could not see them has been
replaced.

### 90a. Why blanking a jump target costs more than it looks

`diff_proc` renders both sides and blanks every absolute address to
`$----`, because the two codefiles do not lay a segment out identically --
Apple's `PASCALCO` carries 948 bytes of native 6502 that ours has no linker
to place -- so a comparison that kept addresses would differ at every
branch and say nothing.

The cost is that **a branch that goes somewhere else reads the same**. Two
ways, and the reconstruction had one of each:

* a *short forward* branch carries its displacement in the instruction
  stream, and the disassembler resolves it to an absolute address before
  the blanking happens;
* a *backward* branch carries a negative operand, which is an index into
  the procedure's jump table, and the destination is a word in that
  table -- outside the instruction stream altogether.

In both cases a label placed one statement too far along moves nothing but
the target. And there is a Pascal edit that does exactly that and nothing
else: taking a statement that follows an `IF` and putting it inside the
`IF`. The statements are emitted in the same order either way, so every
byte of code is identical; only the false branch's destination moves.

### 90b. `NEWSEG` -- a dictionary slot that was not being allocated

`PASCALCO.13:NEWSEG` is 42 bytes and one byte of it differed: the `FJP` at
`$08CD` jumps to `$08D7` in Apple's and `$08DF` in ours. Ours read

    IF FNEWSEG THEN
      BEGIN BUMPSEG(NEXTSEG,63,354); BUMPSEG(SEGSLOT,15,354) END;
    SEGMAP[SEG] := SEGSLOT

and Apple's bumps `SEGSLOT` unconditionally:

    IF FNEWSEG THEN BUMPSEG(NEXTSEG,63,354);
    BUMPSEG(SEGSLOT,15,354);
    SEGMAP[SEG] := SEGSLOT

Only the segment *number* is conditional. This is not a stylistic
difference: `NEWSEG(FALSE)` is what an `INTRINSIC` unit's `CODE` clause
calls, with `SEG` already set to the number the source named (finding 80),
and the `WITH SEGTABLE[SEGSLOT]` on the next line of `UNITPART` has to be
addressing a slot of its own. Ours would have written the unit's segment
over its predecessor's dictionary entry. **A compiler built from the
reconstruction as it stood would have miscompiled `INTRINSIC` units.**

### 90c. `UNITPART.3` -- two statements a level too deep

One word of the jump table, `jtab-14`: Apple's `$00CC` against our `$00AD`,
so the `FJP` at `$012F` that opens `IF SY = IDENT` landed 31 bytes further
on in ours. Apple closes that `IF` after the `CODE` and `DATA` clauses:

    IF SY = IDENT THEN
      BEGIN <CODE clause>; <DATA clause> END;
    IF NOT LCODESEG THEN BEGIN ERROR(352); LCP^.MODSEG := FALSE END;
    IF SY = SEMICOLON THEN INSYMBOL ELSE ERROR(14)

Ours had the last two statements inside the `BEGIN ... END`, so an
`INTRINSIC` clause with no identifier after it raised neither *352* nor
*14* and left the semicolon unread. The second half of the same feature as
90b, found in the same run.

### 90d. What replaced the check

`procbuild.py --emu-check` now also compares **bytes**, procedure by
procedure, over `enter_ic .. jtab + 2` -- body, exit sequence, jump table,
attribute table -- and then the whole segment end to end, which takes in
the padding between procedures and the segment's tail as well. Nothing of a
procedure is left out, and no address is normalised away, because the two
codefiles put every p-code procedure at the same offset anyway.

Three things it has to say out loud rather than silently pass:

* `PASCALSY` is skipped by name. It is the skeleton's `PROGRAM
  PASCALSYSTEM` under `(*$U-*)`, the host program that stands in for the
  operating system and holds its 42 forwards (findings 63, 79b). Apple's
  `SYSTEM.COMPILER` has no segment 0 -- it is entered as a segment by an
  operating system that is already loaded -- so there is nothing to compare
  it against.
* `PASCALCO.2` and `.3` are skipped: `IDSEARCH` and `TREESEARCH` are native
  6502, they arrive in our codefile as unlinked declarations, and the
  assembler tier holds them byte-identical separately (finding 57a).
* `PASCALCO` therefore cannot match end to end. It misses exactly **948
  bytes**, which is 800 for `IDSEARCH` plus 148 for `TREESEARCH` -- the two
  numbers finding 45 assembled -- and not a byte more.

### 90e. Where the verification now stands

With both fixes in, from a fresh `mkworkdisk` and one emulator run:

```
147 procedures declared, 147 of 147 reconstructed bodies matching
Apple's p-code, 0 still stubs
0 procedure(s) differ from Apple's bytes
14 of 15 segments byte-identical end to end
```

Every p-code procedure of Apple's 1.3 `SYSTEM.COMPILER` is now reproduced
**byte for byte**, not merely instruction for instruction, and fourteen of
the fifteen segments match as whole images -- attribute tables, jump
tables, inter-procedure padding and all. The fifteenth is `PASCALCO`, short
by its two native procedures alone.

### 90e-bis. 1.1 carries one of the two

`src/pascal/1.1` was copied from 1.3 (finding 88), so it inherited both
errors. 1.1's own binary settles one of them the same way: `PASCALCO.11` is
`NEWSEG` there, and its `FJP` at `$088F` goes to `$0899`, the second
`BUMPSEG`, exactly as 1.3's does. Fixed, on 1.1's own evidence.

The `UNITPART.3` one does not transfer. 1.1's `FJP` through `jtab-14` lands
on `SLDC 22; CXP 1,2` -- `ERROR(22)` -- and not on the `LCODESEG` test, so
the two releases do not have the same statement structure there and the 1.3
correction is not a 1.1 fact. Settling 1.1's would take a jump-table
comparison, which takes a compiled 1.1 codefile, which is the emulator tier
1.1 does not reach (finding 88f). Left alone rather than guessed at.

### 90f. The lesson, in the form the working rules already have it

*"Prefer a check the binary can fail -- but check that it can fail for the
property you care about."* This is the third time that rule has been paid
for. Finding 47 was a linear sweep that re-synchronised after corruption
and still landed on the right end address; finding 28 was a probe that
verified the output and not the routine claimed to produce it; this is a
diff that verified every instruction and not where they jump to. The
question to ask of a normalisation is not "is it necessary" -- blanking the
addresses was necessary -- but **what does it make invisible, and is there
a second check that sees that**.

A practical corollary for this codebase: the two compilers place every
p-code procedure at the same offset, so the normalisation was not needed
for the emulator tier at all. It was inherited from the fast tier, where it
is unavoidable, and carried into a comparison that could have afforded the
stronger form from the start.


## 91. The shipped `SYSTEM.COMPILER` is a *linked* codefile

**VERIFIED BINARY FACT**, and it settles what finding 90d could only
describe. Every segment of Apple's shipped `SYSTEM.COMPILER` carries
`segkind = 0`, `LINKED`. The codefile our source produces carries
`segkind = 0` on fourteen of its fifteen and **`segkind = 1`, `HOSTSEG`,
on `PASCALCO`** -- the marker for a segment with an unresolved `EXTERNAL`
in it.

That is the whole of the 948-byte difference, stated in the file's own
terms. `IDSEARCH` and `TREESEARCH` are not compiled; they are assembled
separately and brought in by the **linker**, and what Apple shipped is the
linker's output. A compile alone cannot produce them and was never going to:

| | Apple's | ours, straight from the compiler |
|---|---|---|
| `PASCALCO` segkind | 0 `LINKED` | 1 `HOSTSEG` |
| `PASCALCO` length | 5606 | 4658 |
| procedures 2 and 3 | 800 + 148 bytes of 6502 | unresolved declarations |

So the reconstruction is complete in the sense that matters -- every byte
Apple's *compiler* produced, our source reproduces (finding 90e), and every
byte Apple's *assembler* produced, `src/native/SEARCH.TEXT` reproduces
(findings 45, 57a) -- and the one step never yet run is the one that joins
them: `L(ink` under the emulator, `BODY13.CODE` against the assembled
`SEARCH.CODE`. If that is right the result is `PASCALCO` at 5606 bytes,
segkind 0, and a fifteen-for-fifteen byte-identical codefile. **Nothing
else is missing.**

Two things not to assume on the way there. The library is not where those
two came from: `SYSTEM.LIBRARY` holds six units and neither routine is in
any of them (finding 92), so the linker's input was a separate assembled
codefile that Apple did not ship. And `LIBRARY.CODE` on `APPLE2:` is the
librarian *utility*, not a library.

## 92. What is in `SYSTEM.LIBRARY`, and the interfaces are Apple's own text

**VERIFIED BINARY FACT.** `tools/libmap.py` takes the library apart and
`build_all.py` runs it. Six units in seven slots, the same six in both
releases, every one of them `segkind = 6`, a **linked intrinsic** -- code
already bound, segment number fixed, so a program that `USES` one is bound
to the copy already on the boot disk rather than getting a copy of its own.

| unit | 1.1 | 1.3 | procedures (1.3) | native |
|---|---|---|---|---|
| `LONGINTIO` | 2452 | 2546 | 4 | 1 |
| `PASCALIO` | 1238 | 2070 | 9 | 0 |
| `CHAINSTUFF` | 214 | 410 | 8 | 0 |
| `TRANSCEND` | 1202 | 1268 | 9 | 0 |
| `TURTLEGRAPHICS` | 5202 | 5230 | 31 | 7 |
| `TURTLEGRAPHICS` data | 386 | 386 | -- | -- |
| `APPLESTUFF` | 678 | 652 | 8 | 6 |

`TURTLEGRAPHICS` takes two slots: a code segment and a 386-byte **data
segment** (`segkind = 7`), which is the `INTRINSIC CODE n DATA n` form
`UNITPART` parses (finding 80) seen from the other end -- the only worked
example of it in the evidence.

### 92a. The INTERFACE text is in the file

Each unit's dictionary entry carries a `TEXTADDR`, a block *inside the
library*, and what is there is the unit's `INTERFACE` section **as source
text**. The compiler puts it there so a later `USES` can compile against it
(finding 80), and it is Apple's own text -- indentation, spelling and all.
All six are extracted to `analysis/library/interface/{ver}/`.

That changes the shape of this reconstruction completely. For the compiler
every declaration had to be recovered from the code it emitted; here the
types, the constants and **every procedure heading with its exact parameter
names and types** are given. `TURTLEGRAPHICS` hands over its `SCREENCOLOR`
enumeration in Apple's own member order; `PASCALIO` and `LONGINTIO` hand
over `DECMAX` and the ten-variant `STUNT` record. What is left to recover
is the `IMPLEMENTATION` of each, against the p-code that is right there in
the same file.

### 92b. What differs between the releases

`LONGINTIO`, `TRANSCEND` and `TURTLEGRAPHICS` have the same interface in
both, to the character. Two changed:

* **`CHAINSTUFF`** gains `SWAPGPON` in 1.3, a seventh entry point beside
  `SETCHAIN`, `SETCVAL`, `GETCVAL`, `SWAPON` and `SWAPOFF`.
* **`PASCALIO`** grows from three procedures to seven. 1.1 has `FSEEK`,
  `FREADREAL` and `FWRITEREAL`; 1.3 adds `FREADDEC`, `FWRITEDEC` -- with
  the `DECMAX`/`STUNT` declarations `LONGINTIO` already carried -- and
  `SUPER_MOD` and `SUPER_DIV`. Those last two are the only identifiers
  anywhere in this evidence with an underscore in them, which under the
  eight-character rule (finding 29) fold to `SUPERMOD` and `SUPERDIV` and
  so are two distinct names by one character.

### 92c. A trap in the extraction, and a rule that generalises

The text does not end where the block does. The compiler stops copying at
`IMPLEMENTATION`, and the rest of the block is whatever the buffer held
before -- which in 1.1's `TURTLEGRAPHICS` is six procedure headings from an
*earlier* version of its own interface, in the right typeface, indented the
same way, reading exactly like the real thing. `libmap.py` cuts at the
`IMPLEMENTATION` token for that reason.

The general form is worth keeping, because this evidence is full of buffers
that are written but never cleared: **a fossil of the artifact is not the
artifact.** Take the terminator the writer used, not the one the container
provides.


## 16. Open questions

* ~~**The four unnamed words of the `MODULE` variant.**~~ **Resolved by
  finding 82c.** `DECLARATIONPART` writes all four and reads three, and
  every use agrees with the ones findings 76b, 79c and 80b had recorded:
  `MODSEG` at 11 is "owns a code segment", `MODLINK` at 12 is "and is not
  an intrinsic's own code segment" -- together, `WRITELINKERINFO`'s test --
  `MODDATA` at 13 is "owns a data segment" and is the variant tag, and
  `MODDSEG` at 14 behind it is that segment's number.
* ~~**What `OSPROC43` is.**~~ **Resolved by finding 89**, by the second of
  the two routes the question named: `FILEPROC.8` is the file-title
  normaliser -- delete the blanks, a trailing `'.'` defeats the suffix, a
  `[...]` size specification is held aside, a name ending `':'` is a volume,
  otherwise upshift and append `'.TEXT'` or `'.CODE'` if the declared length
  has room. The 1.3 manual documents every rule of it. What is still not
  recovered is Apple's *name* for it, and nothing in either binary carries
  one, so the reconstruction keeps `OSPROC43`.
* ~~**The outer block is two words wide of Apple's.**~~ **Resolved by
  finding 55c**: `SYMBUFP` and `CODEP` are the outer block's two *parameter*
  words, not `VAR` declarations, and the reconstruction was writing them as
  declarations. Both releases now compile to Apple's exact frame. Finding 46
  is confirmed. What remains open is only how Apple's source *names* those
  two words -- UCSD's program-parameter syntax is the candidate and
  `ucsdpsys_compile` will not parse it.
* ~~**`SYSTEM.PASCAL`'s segment 0 does not parse.**~~ **Resolved by finding
  50**, and the premise was wrong: slot 15 is not a segment that failed to
  parse, it is the second piece of segment 0, and the one dictionary at the
  end of slot 0 covers both. All three operating system builds now parse
  with zero inconsistent procedures, and `SYSTEM.PASCAL` lifts. The
  suggestive 6518-byte coincidence between 1.3's `SYSTEM.PASCAL` and
  `128K.PASCAL` was exactly what it looked like: the same segment 0, split
  at a different point for a different memory map.
* What the separation between the two pieces of segment 0 *is*, in absolute
  addresses. Finding 50c measures it -- 16736 bytes in both `SYSTEM.PASCAL`
  builds, 15868 in `128K.PASCAL` -- but recovers no load address, and
  nothing depends on one.
* ~~**Non-standard CSPs.**~~ Resolved by finding 17: the full table is now
  named and aritied from interpreter source, and CSP 21/22 are the compiler
  phase dispatch. TommyGoog's `LIBMAP.CODE` cross-reference is no longer
  needed for this.
* ~~**The file-variable block layout.**~~ Resolved by finding 43, and the
  premise was wrong: there is no second group. `FILESIZE = 300`, `BODY`
  emits `LDA 0,VADDR+FILESIZE` as the window argument for *every* file
  variable whether or not it has a window, and three of the four addresses
  land inside `LP` — which is a `TEXT`, 301 words, running 666..966.
  `CURBLK` at 967 confirms it.
* ~~One word of the 1222-word global area in 1.1 is unaccounted for.~~ The
  area is 1224 words, not 1222 (finding 46): a frame is PARAM SIZE plus
  DATA SIZE, and the outer block declares two words of parameters. With
  that, `DISKBUF` is exactly 256 words and runs to the last word of the
  frame, and nothing is left over.
* ~~`$D1`-`$D6` are unidentified.~~ Resolved by finding 17: `STE`, `NOP`,
  `EFJ`, `NFJ`, `BPT`, `XIT`. Still none of them occur in SYSTEM.COMPILER.
* ~~`PASCALCO.9`, `.15`, `.16`, `.17` (finding 12) are unnamed.~~ Resolved
  by finding 22.
* Two members of the `structform` enumeration, `power` at 4 and `records`
  at 6, are inferred from the gap rather than observed (finding 22b).
* ~~Word 4 of the `identifier` variant part — the 13-word `klass` — has no
  name yet. `klass` 3 and 4 both need one.~~ **Resolved by finding 54d**:
  3 is `ACTUALVARS` and 4 is `FIELD`, the 13-word class. `klass` 2 is
  `FORMALVARS`, which is why 22c saw two 11-word classes and could not tell
  them apart.
* ~~Segment 1.1 PASCALCO proc 1 has `lex=0`; the lex-level convention has
  not been pinned down.~~ Resolved by finding 23a: OS is -1, user program
  is 0, first nested procedure is 1. `PASCALCO.1` is an ordinary user
  program main, so the compiler was **not** built `{$U-}` (23c).
* ~~Four compiler option letters — `$D`, `$E`, `$F`, `$T` — are boolean
  flags in `COMPOPTI.1` with no entry in the 1.3 manual.~~ Resolved by
  finding 24a: `$D` Debug, `$F` Flip and `$T` Tiny from Parker, each
  confirmed in the binary, with the `{$T+}` omit list recovered exactly;
  `$E` identified from the binary alone as the "unit may own file
  variables" gate. Still open, narrowly: what `$E` was *called*, and the
  second `OPT_F` site in `PASCALCO.13`, which inverts a boolean rather
  than swapping bytes.
* ~~`{$U-}` producing `lex=-1` is inferred, not observed.~~ **Resolved by
  finding 47**: both three-disk sets are now in `evidence/`, and across the
  six images the lex byte is `$FF` on 7 of 39 codefiles — always the outer
  block, and always a program that had to be built that way (the operating
  system in both releases, its 128K variant, `SETUP`, and the two `GOTOXY`
  replacements). `HAZELGOTO.TEXT` is on the same disk and its first line is
  `(*$U-*)`, exactly as the manual prescribes, so the directive and the lex
  level are seen together. Nothing else has it, `SYSTEM.COMPILER` included,
  which gives finding 24e the positive control it lacked. The same addition
  brings `SYSTEM.LIBRARY` in for finding 6, which stays deferred but is no
  longer blocked, and `SYSTEM.APPLE` for finding 48.

## 93. TRANSCEND is reconstructed, byte for byte

VERIFIED BINARY FACT. `src/pascal/units/1.3/TRANSCEND.text`, compiled by
Apple's own 1.3 compiler under the emulator, produces segment 29 of
`SYSTEM.LIBRARY` exactly: nine procedures, 1268 bytes, identical as a whole
segment image and not merely procedure by procedure.

```
python tools/mkworkdisk.py
python tools/unitbuild.py --emu TRANSCEND
.\tools\emucompile.ps1 -Name TRANSCND -Release 1.3 -Compile 30 -PerKey 150
python tools/unitbuild.py --emu-check TRANSCEND
  -> 9 of 9 procedures byte-identical, and the whole segment end to end
```

Three things came out of it that the compiler work could not have reached.

### 93a. The local allocation rule, stated exactly

Finding 61 said a declaration list allocates backwards. That is half of it,
and the half that is easy to state wrongly. What the binary shows, once five
frames are matched offset by offset, is:

* **Declaration groups ascend.** Each `name : type ;` group is placed above
  the group declared before it, starting at the first free local word.
* **Identifiers inside one group descend.** In `A, B : REAL`, `B` gets the
  *lower* address and `A` the higher.

So `VAR N: INTEGER; Z, G: REAL; V: FLOAT;` lays out as `N` at 5, `G` at 6-7,
`Z` at 8-9, `V` at 10-11 -- and that is EXP's frame. This is a property
nothing but Apple's compiler can settle: `ucsdpsys_compile` allocates
identifiers *forward* inside a group, so every one of these five frames read
as DIFFERS under the fast tier while being structurally right. Getting
TRANSCEND from 8/9 to 9/9 was one group's order.

### 93b. Real constants are recoverable, digits and all

Apple's compiler converts a real literal by accumulating the digits into a
single-precision accumulator (`RSUM := RSUM*10 + digit`) and then scaling by
`PWROFTEN` -- `NUMSTRIN.NUMBER`, which is reconstructed source we can read.
That conversion is not correctly rounded: it lands a ulp or two off, and
*differently* off for different digit strings.

That is the lever. Simulating those four lines in single precision turns the
question "what did Apple type?" into a search: for each of the 22 constants
in TRANSCEND, find the decimal string whose Apple-conversion reproduces the
stored bytes. Every one of them resolves, and they resolve to the same story
-- Cody & Waite's coefficients, typed to seven or eight significant digits:

```
   $3FC90FDA  1.5707963      pi/2          $3FB8AA3B  1.442695      log2 e
   $3F317FFF  0.6933593      ln2 hi        $B95E8083 -2.1219444E-4  ln2 lo
   $40493F3A  3.140625       pi hi         $3A7DAA23  9.6765359E-4  pi lo
   $BE2AAAA4 -0.16666657     R1            $3C08873D  0.008333025   R2
   $B94FB224 -1.9807419E-4   R3            $362E9C5A  2.601903E-6   R4
```

Note that the correctly rounded conversion of the *full* published constant
disagrees with what is in the file for nine of the twenty-two. Reading those
as "Apple used a different constant" would have been wrong twice over: the
digits are short, and the conversion is sloppy. STRONG INFERENCE for the
exact digit strings -- another string could in principle land on the same
four bytes -- but VERIFIED BINARY FACT for the bytes, which is what the
check compares.

### 93c. The private procedure has to be declared first

The interface headings are what assign procedure numbers, so `SIN`..`SQRT`
are 2..8 before the implementation is parsed. `TRANSCEND`'s ninth procedure
is a sine kernel that `SIN` and `COS` both call (`CGP 9`), and 9 is the next
free number -- so it must be the *first* thing in the IMPLEMENTATION and is
still numbered last. That is a general fact about units, not about this one,
and it will decide the shape of every remaining library unit.

## 94. CHAINSTUFF is reconstructed, and it is not a free-standing unit

VERIFIED BINARY FACT. `src/pascal/units/1.3/CHAINSTUFF.text` under Apple's
1.3 compiler reproduces segment 28 of `SYSTEM.LIBRARY` exactly: eight
procedures, 410 bytes, identical as a whole segment image.

### 94a. It was compiled inside the operating system

Every procedure in it reaches a variable it does not declare -- `LDA 2,328`,
`LDA 2,340`, `STR 2,389`, `STR 2,390`, and `LOD 2,3` for OUTPUT. A lex-2
reference from a lex-1 procedure is two levels down, which under `(*$U-*)`
is the outer block (finding 87d). CHAINSTUFF cannot be compiled on its own;
it has to be nested inside a `(*$U-*)` PROGRAM whose globals are
SYSTEM.PASCAL's, and that is confirmed twice over -- it compiles, and the
bytes come out identical, which they cannot if an offset is wrong.

That a `UNIT ... INTRINSIC CODE n` may be *declared inside* a PROGRAM at all
is itself new here, and it is how Apple built the shipped library: the
library units are part of the operating system's compilation, not separate
files. TRANSCEND needs no host and takes none.

Four of SYSTEM.PASCAL's globals are therefore fixed:

| offset | size | what |
|---|---|---|
| 3 | 1 word | `GFILES[1]`, OUTPUT -- II.0's own layout, unchanged |
| 328 | 12 words | the chain title, `STRING[23]` |
| 340 | 41 words | the chain value, `STRING[80]` |
| 389 | 1 word | the graphics-swap flag |
| 390 | 1 word | the swapping flag |

The sizes are not guesses: 340 - 328 is twelve words, which is `STRING[23]`
and nothing else. What sits at 8..327 and 381..388 is *not* recovered -- the
host in the source file names it FILL and says so. II.0's `GLOBALS.TEXT` has
neither a chain title nor swap flags; both are Apple's.

### 94b. The private procedure is emitted first, again

Same rule as finding 93c, and now with a second witness. The interface
headings take 2..7; the version check is 8. Declared *last* in the
IMPLEMENTATION, every procedure was still byte-identical and the segment
image was not -- the procedures sat at the wrong addresses. Apple's
layout puts procedure 8 at $0000 and procedure 1 last, which is emission
order, which is declaration order. Moving it to the top of the
IMPLEMENTATION closed the segment.

So: **a unit's private procedures are declared first and numbered last.**
The procedure-by-procedure diff cannot see this and the whole-segment
comparison can, which is one more reason it exists (finding 90).

### 94c. Two things in it are Apple's own mistakes

Reported because both look like reconstruction errors and neither is.
`SETCHAIN` guards on `LENGTH > 24` and copies 24 characters into the
`STRING[23]` at offset 328 -- `SLDC 24; GRTI` and `SAS 23`, unambiguous in
the bytes -- so a title of exactly 24 characters is a run-time error.
`SETCVAL` guards on `LENGTH > 82` against a value parameter that is a
`STRING[80]`, so that arm is unreachable.

## 95. PASCALIO is reconstructed, byte for byte

VERIFIED BINARY FACT. `src/pascal/units/1.3/PASCALIO.text` under Apple's 1.3
compiler reproduces segment 31 of `SYSTEM.LIBRARY` exactly: nine procedures,
2070 bytes, identical as a whole segment image. It is the biggest unit in
the library that is p-code all the way down, and `FWRITEREAL` -- 350
instructions of decimal formatting -- came out identical on the first
compile.

Like CHAINSTUFF it is not free-standing (finding 94a): it reads `SYSCOM` at
lex -1 offset 1 and takes a `FIB` apart field by field, so it needs an
operating-system host. Unlike CHAINSTUFF, nearly all of what the host must
supply is recoverable, because it is UCSD II.0's and `GLOBALS.TEXT` is in
`reference_source/`. The CONST and TYPE blocks in the source file are II.0's
verbatim, and every FIB field this unit touches lands where the binary puts
it.

### 95a. The allocation rule makes II.0's records legible

Two FIB declarations only read correctly backwards, which is finding 93a
applied to record fields rather than locals:

* `FEOF,FEOLN: BOOLEAN` puts **FEOF at word 2** and FEOLN at word 1. FSEEK
  clears word 2 before word 1, which is `FEOF := FALSE` written first, and
  the "not end of file" test every read loop in this unit makes is word 2.
* `FREPTCNT,FNXTBLK,FMAXBLK: INTEGER` puts **FMAXBLK at 12**, FNXTBLK at 13,
  FREPTCNT at 14. Forwards, FSEEK would be comparing a block number against
  the number of times the window is valid without a GET; backwards it is
  `IF BLK <= FMAXBLK`, the file's high-water mark, which is what the code is
  plainly doing.

So the rule is not a quirk of the compiler's local allocator. It is how
Apple's compiler lays out any identifier list, and it decides what II.0's
own source *means*.

### 95b. `(*$U-*)` turns range checking off, and that is visible

`COMPOPTIONS`' `'U'` arm sets `RANGECHECK := NOT SYSCOMP` and
`GOTOOK := SYSCOMP`. Under `(*$U-*)`, SYSCOMP is TRUE: no `CHK` is emitted
anywhere in this unit, and `GOTO` is available without asking for it.
Both show. TRANSCEND, which is not a system compilation, emits `CHK` on
every packed-field store -- the positive control.

### 95c. The jump table distinguishes GOTO from nested IFs

`FSEEK` and `FREADREAL` each leave early from four places. Written as
`IF cond THEN (*nothing*) ELSE BEGIN rest END`, nested, the **instruction
stream is identical** to Apple's -- same opcodes, same order, same operands
once targets are blanked. The jump table is not: four `GOTO 1` share one
table entry, and four nested IFs finish at four addresses two bytes apart
and take three. Apple's table has one entry; the nested version's had
three, and the procedure was four bytes long.

There is no way to see that in a disassembly diff. It is the second time
the blanking has hidden a real structural difference (finding 90) and the
first time it has hidden one that no amount of reading the instruction
listing could have resolved.

### 95d. Two more small facts

`STR(D,S)` passes **S's declared maximum** as an operand, so the local
buffer in FWRITEDEC is `STRING[38]` and not a byte more -- the frame is one
word wider than that, and the spare word is not recovered. And a `CXP` into
another segment is rendered through the *codefile's* segment dictionary, so
a unit compiled on its own prints `CXP 35,4` where the library prints
`CXP 30,4` with the same bytes; `tools/unitbuild.py` now takes the byte
comparison as the verdict under `--emu-check` for that reason.

## 96. LONGINTIO and APPLESTUFF: every p-code procedure, byte for byte

VERIFIED BINARY FACT. Both units' p-code halves are reproduced exactly by
`src/pascal/units/1.3/{LONGINTIO,APPLESTUFF}.text` under Apple's compiler.
Neither segment can be closed end to end from here, and for the same reason
`PASCALCO` cannot (finding 91): the 6502 arrives through the linker.

| unit | segment | p-code | native | result |
|---|---|---|---|---|
| LONGINTIO | 30 | 3 of 4 | 1852 bytes | 3 of 3 byte-identical, short by the native tail |
| APPLESTUFF | 22 | 2 of 8 | 584 bytes in six | 2 of 2 byte-identical, short by the native tail |

The native figures are each procedure's whole extent, `enter_ic` through
`jtab + 2`, which is what the segment is actually short by. This table first
gave 1850 and 572, which left out the two-byte attribute word per
procedure; the corrected figures are what finding 98 reassembles.

### 96a. LONGINTIO's two procedures are PASCALIO's two procedures

`LONGINTI.2` and `PASCALIO.5` are 640 bytes each and differ in **one byte**:
the procedure number in the attribute table. `LONGINTI.3` and `PASCALIO.6`
are 32 bytes and differ in the same one byte. Apple compiled the same
`FREADDEC` and `FWRITEDEC` text into both units, and the source file here
says so by using the same text.

The 6502 procedure 4 is the long-integer engine that every `CXP 30,4` in the
library calls -- including the two calls its own `FREADDEC` makes. A unit
calling itself by segment number rather than by `CGP` is what you would
expect if the compiler treats long-integer arithmetic as a fixed intrinsic
and does not notice it is compiling the intrinsic.

### 96b. APPLESTUFF is free-standing, and the binary says which way

`KEYPRESS` emits a `CHK` on its array index. Range checking is only on when
the compilation is *not* `(*$U-*)` (finding 95b), so APPLESTUFF -- alone
among the units that touch the machine -- was compiled as an ordinary
program would be, and it needs no operating-system host. That agrees with
the other evidence: it reaches no lex -1 offset at all.

Its whole Pascal content is `UNITSTATUS(2,A[0],0)` and a test that the
console has something buffered. Everything else -- paddles, buttons,
annunciators, RANDOM, the speaker -- is 6502.

### 96c. Declaration order buys nothing for native procedures

The six 6502 procedures sit in the shipped image in the order 2, 3, 4, 8,
6, 7. That is not the order the interface declares them and it cannot be
changed from Pascal: the linker appends native code in the order it finds
it in the assembled file. Finding 94b -- declaration order is an address --
is about p-code only.

## 97. TURTLEGRAPHICS is reconstructed, and its data segment with it

VERIFIED BINARY FACT. `src/pascal/units/1.3/TURTLEGRAPHICS.text`, compiled by
Apple's own compiler, reproduces **24 of the unit's 24 p-code procedures byte
for byte** and its data segment byte for byte. Segment 20 comes out 2984
bytes against Apple's 5230; the difference is 2246 bytes, and 2246 bytes is
exactly the seven native procedures (15, 16, 20, 21, 22, 30, 31), which
belong to the assembler tier (finding 44e) the same way `PASCALCO`'s do
(finding 91). Segment 21 comes out 386 bytes, which is Apple's 386 exactly.

That closes the six library units:

| unit | segment | p-code | result |
|---|---|---|---|
| TRANSCEND | 29 | 9 of 9 | whole segment, end to end |
| CHAINSTUFF | 28 | 8 of 8 | whole segment, end to end |
| PASCALIO | 31 | 9 of 9 | whole segment, end to end |
| LONGINTIO | 30 | 3 of 4 | 3 of 3 identical, short by the native tail |
| APPLESTUFF | 22 | 2 of 8 | 2 of 2 identical, short by the native tail |
| TURTLEGRAPHICS | 20 (+ 21) | 24 of 31 | 24 of 24 identical, short by the native tail |

### 97a. The data segment can be read straight off the global references

TURTLEGRAPHICS is the only library unit with a `DATASEG`, and nothing in the
codefile describes its contents -- the dictionary carries a length and
nothing else. But every access to it is an `LDE/LAE/STE 21,n`, so the whole
layout is recoverable by collecting the offsets: eleven scalars in words 1
through 11 and a 91-element `ARRAY OF REAL` in words 12 through 193. 193
words is 386 bytes, which is the shipped length, so the reading is complete
and there is no room in it for anything unaccounted for.

Word 10 is never referenced by any instruction in the segment. It is not
slack at the end -- word 11 is the character-set pointer and words 12 up are
the table -- so the source declares a dead `SPARE: INTEGER` to hold the place.
VERIFIED BINARY FACT that the word exists and is untouched; STRONG INFERENCE
that Apple had a variable there and stopped using it.

The one thing the offsets do not give is a name, and one name mattered: the
interface declares `PROCEDURE TURN(ANGLE: INTEGER)`, so a global called
`ANGLE` would be shadowed inside `TURN` and the body would compile to the
wrong thing. Word 9 is `HEADING` here for that reason.

### 97b. The sine table is 91 decimal literals, and they can be read back

The unit ships a 91-entry sine table for whole degrees, and it is not
computed at run time: procedures 25 and 26 are 369 and 361 instructions of
nothing but `LDC` a real constant and store it. So the constants are in the
code segment as float32 and the question is what Apple *typed*.

Running finding 93b's method on all 91 -- simulate the compiler's own
decimal conversion (`RSUM := RSUM*10 + digit`, then scale by `PWROFTEN`) and
search for the shortest string that lands on the shipped bytes -- gives a
single rule for 86 of them: **six significant digits, correctly rounded**.
The remaining five, entries 28, 40, 49, 53 and 87, are each one unit low in
the last place: `0.469471`, `0.642787`, `0.754709`, `0.798635`, `0.998629`.
Those five are not a different rounding rule, because no rule produces
exactly five exceptions in a monotone table -- they are what was typed. The
table was entered by hand, and it has five typos in it that have been in
every Apple Pascal system since.

All 91 strings re-encode to the shipped bytes, so this is VERIFIED BINARY
FACT for the values; STRONG INFERENCE that six significant digits was the
intent and the five are slips.

### 97c. One CONST section, then one TYPE section

Apple's compiler takes the declaration sections of a block in order and does
not let you reopen one. A unit that declares types, then needs a constant,
then declares more types is `Line 53, error 18` -- error in declaration part,
pointing at the second `CONST`. The reconstruction therefore hoists the four
operating-system constants above the turtle types even though they belong
with the directory declarations that follow them. This is a property of the
compiler, not of the source that was compiled, so it constrains the shape of
every reconstruction but says nothing about the bytes.

Identifiers are significant to eight characters, which matters for the same
reason: `SINETABLE1` and `SINETABLE2` are the same identifier.

### 97d. TURTLEGRAPHICS is free-standing

Procedure 23 emits `CHK 0,1`. Range checking is off under `(*$U-*)` (finding
95b), so this unit -- like APPLESTUFF and unlike CHAINSTUFF, PASCALIO and
LONGINTIO -- was compiled as an ordinary program is, and needs no
operating-system host to compile. It reaches the machine through `$00BB` and
the soft switches instead of through lex -1.

## 98. The library's native half: all fourteen procedures reassemble to Apple's bytes

*Confidence: VERIFIED BINARY FACT. `tools/probes/probe_lib_native_asm.py`,
146 checks, run by `tools/build_all.py`.*

Three of the six library units are part 6502, and `src/native/` now carries
every one of those procedures as source in the Apple Pascal Assembler's
language. All fourteen assemble to the shipped bytes over the whole
procedure -- `enter_ic` through `jtab + 2`, so instructions, embedded data,
all four relocation tables, ENTER IC and the attribute word.

| file | unit | procedures | bytes |
|---|---|---|---|
| `APPLESTF.TEXT` | APPLESTUFF | 6 | 584 |
| `TURTLEGR.TEXT` | TURTLEGRAPHICS | 7 | 2246 |
| `LONGINTS.TEXT` | LONGINTIO | 1 | 1852 |

With finding 97's Pascal, that closes APPLESTUFF and TURTLEGRAPHICS and
LONGINTIO end to end: every byte of all six library units is now accounted
for by source in this repository, 55 p-code procedures and 14 native ones.

As with finding 45, the relocation tables are what make this a real test.
Nothing in the source names an entry; they are derived from which operands
mention a label, so getting them right means having written every reference
the way Apple did. The three files come to 4682 bytes and
170 relocation entries -- 144 procedure-relative, 21 segment-relative and 5
Interpreter-relative, and none base-relative -- and the probe checks each
kind separately rather than only the byte total.

### 98a. Segment-relative relocation is a `.DEF`/`.REF` pair, and it is how the natives call each other

APPLESTUFF and TURTLEGRAPHICS both have segment-relative entries -- 6 and
15 of them -- which `SYSTEM.COMPILER`'s two natives do not (finding 44e).
Every one is a
reference from one `.PROC` to a label in another `.PROC` of the same
assembly: the Linker resolves it to an offset within the segment, which is
why it cannot be procedure-relative.

They are also the evidence for structure that nothing else would show:

* **RANDOMIZE reseeds four bytes that live inside RANDOM.** RANDOM's own
  references to its seed are procedure-relative; RANDOMIZE's six references
  to the same four bytes are segment-relative. So the seed is a label in
  RANDOM, `.DEF`'d, and the two are separate procedures in one file.
* **TURTLEGRAPHICS' two private natives are a subroutine library for the
  other five.** Procedure 30 exports six entry points and procedure 31 one,
  and the fifteen segment-relative entries across the unit are calls to
  them: page select, pen colour, position, plot, step right, draw a line,
  and clip to the viewport. MOVEREL's single entry is a jump into the middle
  of MOVEABS, which is where the two become the same routine.

That is why 30 and 31 are declared last in the Pascal (finding 97's
declaration order): nothing in the Pascal calls them at all.

### 98b. RELOCSEG is determined, and it is not in the assembly

The high byte of a native procedure's attribute word is RELOCSEG, and the
manual fixes what it means (IV-36): base-relative relocation goes through
the BASE register when it is 0, and through the data segment it names when
it is not, with 1 for an Intrinsic Unit that has no data segment. The disk
agrees exactly -- `PASCALCO`'s two natives are 0, APPLESTUFF's and
LONGINTIO's are 1, and TURTLEGRAPHICS' seven are 21, which is its DATA
segment. So the byte is a Linker product derived from the Pascal host's
`INTRINSIC CODE 20 DATA 21`, and the probe checks the disk against the rule
rather than reading the byte off the disk and handing it back.

### 98c. What a linear sweep cannot tell you, and what the relocation tables can

Five of the fourteen have data inside them, and a linear sweep runs straight
through it producing plausible nonsense. Two of the five are found by the
sweep failing -- an illegal opcode -- but three are not, and one of those
matters:

`LONGINTIO`'s comparison dispatcher holds six four-byte patches, one per
relational operator, that it copies over four NOPs in its own body before
running them. Swept linearly they decode as branches, and they decode
*legally*: the sweep lands on the end of the procedure with nothing to
complain about. What gives them away is that the branches they decode to
land in the middle of other instructions, which is exactly the check that
reassembly is: a label cannot go there, so no source can produce those bytes
as code.

### 98d. What the bytes do not settle

The same limits as finding 45b. Every label name and every comment is ours;
Apple's are not in the codefile. Two of the three files are named and
commented throughout; `LONGINTS.TEXT` is not. Its eleven operations are
reached through a jump table and the source says so, but what each of them
computes has not been read out, and its interior labels are written
`L<nnnn>` -- the label's offset from the start of the procedure -- as
placeholders. Nothing about those is recovered, and nothing about them needs
to be for the bytes to be right; it is the reading that is missing, not the
reconstruction.

`tools/asmskel.py` writes that mechanical layer -- labels where something
jumps or a relocation points, symbolic operands where the binary says the
operand was symbolic, `.BYTE` for the data regions. It is deliberately not
wired into `build_all.py`: nothing in `analysis/` should look like source.

### 98e. The acceptance test is still the emulator

`tools/asm6502.py` has grown `.DEF`, `.REF`, `.INTERP`, `JMP` indirect and
the zero-page-to-absolute widening that `STA abs,Y` needs, because the
library uses all of them and `SEARCH.TEXT` used none. It is still not the
authority: **`SYSTEM.ASSMBLER`** is, and running these three files through it
under AppleWin is what would finally settle the native half, exactly as
recompiling under Apple's compiler settles the Pascal half. What the probe
rules out is the whole class of errors that would fail there too.

## 99. LINEFEED, and what the SEGINFO version stamp settles

The first APPLE3 utility is reconstructed, and getting there turned up the
field that says which of the others can be.

### 99a. LINEFEED reproduces, from Apple's own source

**VERIFIED BINARY FACT.** `LINEFEED.CODE` is one procedure and 38 bytes, and
the 1.1 and 1.3 disks ship the same 38. The 1.1 APPLE3 disk also ships
`LINEFEED.TEXT` -- Apple's source, seventeen lines -- and the 1.3 disk does
not. Compiled by Apple's own 1.3 compiler under AppleWin on the 128K system,
that source produces those 38 bytes exactly, and the segment dictionary with
them: the name, the code address and length, and every word of the tail.
The source is carried in `src/pascal/programs/1.3/LINEFEED.text` unaltered,
and `tools/mkworkdisk.py` puts it on the work volume.

That makes it the first file outside `SYSTEM.COMPILER` and `SYSTEM.LIBRARY`
closed end to end, and it is worth more than its size as calibration,
because it exercises two things nothing reconstructed so far does:

* **`CHK` is emitted.** The compiler and every library unit are `{$R-}`
  (finding 23c), so no reconstruction has yet produced a range check.
  `CHEAT.PTR^[0]:=255` emits two: the index against `0..1`, then the value
  against `0..255`, in that order, before `STB`.
* **A negative literal is not folded.** `CHEAT.INT:=-16625` compiles to
  `LDCI 16625 ; NGI`. The compiler emits the positive word and negates it
  at run time.

### 99b. SEGINFO's version field is the writing system, and it is enforced

**VERIFIED BINARY FACT.** SEGINFO is one word per dictionary slot at $100:
segnum in bits 0-7, mtype in 8-11, version in 13-15. The version is **the
release of the system that wrote the file, not of the source**. 1.1's system
writes 2 and 1.3's writes 6, and the compile above is the proof in one
direction: the code came out identical to Apple's shipped copy and the
stamp did not, because Apple's copy was written by a 1.1 system.

It is enforced, not decorative. Booted on the 128K 1.3 system with 1.1's
APPLE2 in drive 2, `C(ompile` answers

    APPLE2:SYSTEM.COMPILER is not version 1.3

and does nothing at all. So 1.1's compiler cannot be run under 1.3, and
under the 128K target there is no 1.1 system to run it on instead.

**STRONG INFERENCE.** The Linker copies a segment's SEGINFO through
unchanged. 1.3's `SYSTEM.ASSMBLER` is version 6 in six of its seven segments
and version **2** in `PASCALIO`, the unit linked into it; 1.1's is version 2
in six and version **1** in the same slot. A stamp that tracked the file
would not survive that.

### 99c. Three of the APPLE3 utilities are 1.1 binaries

**VERIFIED BINARY FACT.** `BINDER.CODE`, `LINEFEED.CODE` and
`SET40COLS.CODE` on the 1.3 APPLE3 disk are all stamped version 2. Apple
never rebuilt them. `BINDER.CODE` puts it beyond doubt: its 1.3 copy differs
from its 1.1 copy in exactly **fifteen bytes**, every one of them the high
byte of an *unused* SEGINFO slot, 1 through 15, set from 0 to $42.
`SETUP.CODE` is stamped version 0 -- older than the field -- and the two
releases' copies are byte-for-byte identical. `tools/probes/probe_stale_utils.py`
checks all of this from the bytes.

**SPECULATION, and an open question.** Nothing yet identifies what filled
those fifteen slots. A 1.1 compile writes slot 0 only; a 1.3 compile writes
all sixteen but stamps them 6. The shipped 1.3 file has all sixteen at the
1.1 version, which is neither, so some 1.3-era tool rewrote the dictionary
without touching the version. Until that is known, these three files cannot
be reproduced byte for byte by compiling anything.

### 99d. mtype says where the native code is

**VERIFIED BINARY FACT.** A segment is stamped mtype `6502` exactly when it
holds at least one native procedure, and `pcode-lsb` otherwise. Across
every segment of every codefile on all six evidence disks that is **136
segments and no exceptions** -- `tools/probes/probe_seginfo.py`. It is a
real check rather than a restatement, and it is one a reconstruction can
fail: a segment whose native procedures were missed would be stamped wrong.

`tools/diskmap.py` writes `analysis/diskset-inventory.txt`, every file on
every disk of both releases with the per-segment breakdown. The 1.1 disks
stay in evidence and stay useful even though 1.3 and the 128K system are
the target -- 1.1 ships source for utilities that 1.3 ships only as
codefiles, which is how `LINEFEED` was reconstructed at all.

## 100. The lifter, held against the whole disk set

`SYSTEM.COMPILER` lifts 145 of 145 procedures with the stack fully tracked,
and it has done for a long time. That number is worth exactly as much as the
variety of the code behind it, so the next thing after `LINEFEED` was to
point the same machinery at every other codefile on the six disks --
`tools/disasm_utils.py` and `tools/lift_utils.py`, writing
`analysis/utilities/`. **1231 procedures. The first run tracked 1120.**

The 111 failures were not spread evenly, and that is what made them useful:
the graphics demos on the APPLE3 disks were the worst of them --
`SPIRODEMO` 0 of 3, `GRAFCHARS` 0 of 5, `HILBERT` 0 of 4 -- and those are
programs Apple shipped the source for. Four causes, all now fixed, none of
them reachable from the compiler alone.

### 100a. A version-0 codefile has no segment numbers in SEGINFO

**VERIFIED BINARY FACT.** `SETUP.CODE` is version 0, older than the SEGINFO
field (finding 99), so all twelve of its segments report segment number 0.
Every name map keyed on that number therefore collapsed onto whichever
segment came last, and every call into the operating system in that file
read as a call into `TEACHSET`, whose arity is unknowable -- so the stack
model stopped. The segment's own trailing word has carried the number all
along (finding 27). `Segment.number` now falls back to it; where both exist
they agree, and `map_compiler.py` flags it if they ever stop agreeing.

### 100b. Segment 0 present is not the operating system present

**VERIFIED BINARY FACT, and the sharpest of the four.** The lifter took
`CXP 0,n` to be an operating-system call only when the codefile had no
segment 0 at all. But a separately compiled program carries a *stub*
segment 0 -- `SETUP.CODE`'s is named `PASCALSY` and holds a single 16-byte
placeholder -- so the test passed, the stub was searched for procedure 19,
and nothing was found. What settles it is not whether segment 0 exists but
whether it holds the procedure being called. That one change was worth 44
procedures.

Note what the earlier fix did here: 100a did not raise the count much on its
own (four procedures), it *renamed the failure* from `TEACHSET.19` to
`PASCALSY.19` -- and that name is what made 100b visible. A wrong name had
been hiding a wrong lookup.

### 100c. IXS does not touch the stack

**VERIFIED SOURCE FACT**, 1.3 manual IV-4: "Index string array, tos-1 is a
byte pointer to a string, tos is an index into the string. Check to see that
the index is in the range 1..current string length. If so, **continue
execution**; if not, give an execution error." It is a check and nothing
else -- both operands stay for the `LDB` or `STB` that follows. Modelling it
as an index like `IXA` would unbalance every string subscript in the system.
45 occurrences, and the manual settled it without an inference.

### 100d. A program does not carry the units it calls

**VERIFIED BINARY FACT.** A program that uses TURTLEGRAPHICS emits `CXP 20,n`
and carries nothing whatever about segment 20: the Intrinsic Unit lives in
`SYSTEM.LIBRARY` and is bound at run time. So the callee's parameter size is
not in the file being lifted, and every such call stopped the stack model.
`lift()` now takes an `extern` map built from the release's own
`SYSTEM.LIBRARY`, and the arity comes from the callee's own attribute table
rather than from a guess. `TREE`, `BALANCED` and `DISKIO` went from 2 of 6,
2 of 6 and 12 of 16 to all of them.

### 100e. Where it stands, and the one thing left

**1216 of 1231**, with `SYSTEM.COMPILER` unchanged at 145 of 145 and
`SYSTEM.PASCAL` improved to 105 of 105. Every one of the fifteen that
remain is the same thing: **a call into a native 6502 procedure**. The
codefile records a native procedure's entry point and its relocation tables
but not its parameter count -- `procnum = 0` is all the attribute word says
(finding 44) -- so the arity simply is not in the binary. It is in the
*source*, which for the library this repo now has, and supplying it from
there would close the last of them.

That accounts for `FORMATTE.2`, `LIBMAP.2`, `TURTLEGR.16` and four calls
into `APPLESTUFF`, plus `CALC.CODE`'s handful of unmodelled CSPs and one
`BPT`. It also turned up a release difference worth recording on its own:
**`APPLESTUFF.5` is native in 1.1 and p-code in 1.3.** 1.1's APPLESTUFF has
seven native procedures where 1.3's has six, because Apple rewrote that one
in Pascal.

### 100f. Sized, scoped, and complete

Two changes closed the fifteen of 100e.

**The arities.** `NATIVE_SIG` in `lift.py` now carries every native
procedure a `CXP` or `CLP` can reach, and most of it is not an inference:
those are the `.PROC` and `.FUNC` declarations in `src/native/`, which
reassemble to Apple's exact bytes. `probe_native_sig.py` reads them back and
requires the two to agree, so the table cannot go on claiming a provenance
it has lost. The convention is the caller's rather than the assembler's --
`words` counts a function's two result words as well, so `.FUNC TREESEARCH,3`
is 5 here.

Three entries have no assembly behind them and say so in place:

* **`APPLESTUFF.5` is KEYPRESS**, native in 1.1 and p-code in 1.3, so 1.3's
  own copy of the same interface procedure supplies the parameter size from
  its attribute table -- the binary, not a guess.
* **`FORMATTE.2`** is handed one word and two zero words, and its result
  goes straight into `SRO 3`, which the code then tests against
  `'Disk is write-protected'` and the rest. A function of one integer
  returning one: the unit number in, an error code out. Its own variables
  live in the last 32 bytes of its code, which is why every relocation in it
  points back into itself.
* **`LIBMAP.2`** is handed two `LLA`s and nothing consumes a result.

**LONGINTIO's engine is deliberately absent.** It is `.PROC LONGOPS,0`
because the operation number decides how many words it pops, so there is no
single arity to give it and a wrong one would be worse than none.

**The scope.** 1.3 is what is being reproduced, so `disasm_utils.targets()`
names the codefiles a 1.3 disk carries and the coverage figure is counted
over those. **1147 of 1147, everything in scope, fully tracked.** The last
three were `CALC.CODE`'s unmodelled CSPs and one `BPT`, and `CALC.CODE`
ships only on 1.1.

The scope is on the *figure*, not on the sweep. Everything on all six disks
is still disassembled and lifted into `analysis/utilities/`, because the
1.1-only files cost nothing to keep and one group of them is irreplaceable:
eleven demo programs ship as `.TEXT` on the 1.3 APPLE3 disk and as `.TEXT`
*and* `.CODE` on 1.1's, and that pair is the only corpus anywhere of Apple's
source beside Apple's own output. `probe_calibrate.py` is built on two of
them. Out of scope, they lift 81 of 84.

## 101. The global frame bound, and its one exception

Finding 46 fixed the highest valid global offset at `(param_size +
data_size) / 2` words, measured over all 287 of the compiler's procedures.
Reading FORMATTER meant reading its globals, and its outer block declares
1343 words while the code addresses `G1603`. A total that does not balance
is evidence, so this is what it turned out to be.

### 101a. The rule holds, and is usually reached exactly

**VERIFIED BINARY FACT.** Across the thirteen 1.3 codefiles with p-code, the
bound is never loose where it applies and is hit precisely: `SYSTEM.EDITOR`
1666 of 1666, `SYSTEM.FILER` 362 of 362, `LIBRARY.CODE` 767 of 767,
`LIBMAP.CODE` 757 of 757, `SET40COLS` 262 of 262, `LINEFEED` 3 of 3. The
compiler allocates to the top of the frame and the top word is generally a
temporary -- FORMATTER's `G1343` is its `FOR` limit, sitting exactly on its
own bound.

### 101b. The operating system has no outer block

**VERIFIED BINARY FACT.** `SYSTEM.PASCAL` and `128K.PASCAL` appear to exceed
the bound by 287 words, and do not. `PASCALSY` has **fifty-two** procedures
at lexical level 0, plus one in each of five other segments: the operating
system is not a Pascal program with an outer block, so "the lex-0 procedure"
does not name one and whichever the walk happens to end on is arbitrary.
`globals.collect()` takes the last it finds, which is why the figure came
out as 7. The rule is not violated there; it does not apply. This costs
nothing today -- `globalmap.py` only ever runs on `SYSTEM.COMPILER` -- but
it would silently mis-size the frame the moment the OS is a target, which
it now is.

### 101c. A file's title is allocated above the frame

**VERIFIED BINARY FACT.** Three 1.3 programs have exactly one outer block
and still address above their bound: `SYSTEM.LINKER` (91, touches `G350`),
`BINDER` (1121, touches `G1340` and `G1380`) and `FORMATTER` (1343, touches
`G1603`). In every one of them, **every single access above the bound is a
`LAO` followed by `LDCI 1 ; NGI ; CXP 0,3`** -- which is
`FINIT(file, title, -1)`, and nothing else in any of the three reaches up
there at all.

So it is the *title* argument. `BINDER` opens two files and has two such
addresses, `G1340` and `G1380`, which are **40 words apart** -- 80 bytes, the
size of a UCSD file title. FORMATTER's file variable is at `G1303` and its
title at `G1603`, 300 words above it.

**STRONG INFERENCE.** A `FILE` variable's storage is larger than what
`data_size` counts, and the title lives in the uncounted part. What decides
the layout precisely is not settled, and it does not have to be to
reconstruct these programs: declare the same variables in the same order and
Apple's compiler allocates them the same way, which is what the recompile
checks. It does have to be settled before any claim is made about *where* a
particular global lives in a program that opens a file.

## 102. FORMATTER's Pascal, and two things the manual does not say

`src/pascal/programs/1.3/FORMATTER.text`, compiled by Apple's own 1.3
compiler under the emulator on the 128K system: **three of the four p-code
procedures byte-identical**, and the fourth the right length with fifteen
bytes outstanding.

```
  proc 1  1342/1342 B   15 bytes differ
  proc 3    96/  96 B   IDENTICAL      QUITIT
  proc 4   510/ 510 B   IDENTICAL      GETVOLNAME
  proc 5   350/ 350 B   IDENTICAL      GETUNIT
```

Procedure 2 is the native 6502 function and is `EXTERNAL` here; it is not
written yet, and until it is the codefile has to be linked before it runs.

**Every `data_size` matched on the first compile** -- 2682, 0, 86, 4 -- which
is what says the global frame and all three local frames are right before a
single instruction is compared.

### 102a. What the successive differences were

Each round of the compare named one thing, and none of them was guesswork:

* **`{$I-}`.** The first compile put a `CSP 0` (IOCHECK) after every I/O
  call and Apple's has none: the program tests `IORESULT` itself. 50 bytes
  in the outer block alone.
* **The volume name is an *unpacked* array.** Apple indexes it with `IXA 1`
  and stores with `STO` -- a word at a time -- so `ARRAY[1..7] OF CHAR`
  occupies globals 12 through 18 on its own. A packed one is four words and
  leaves three unexplained, and those three were exactly the "gap" that had
  been provisionally declared as filler. There is no filler.
* **`READ(KEYBOARD, ...)`.** The Y/N prompts in the outer block read
  `LOD 1,4`, not `LOD 1,2`.
* **The buffer address is a variant record.** `TABLES` is stored as a number
  (`SRO 1301`) and passed as a pointer (`LDO 1301`, not `LAO 1301`).
* **Declaration order inside one group.** `VAR C, DIGIT: CHAR` and not
  `VAR DIGIT, C: CHAR`: identifiers within a group descend, so the *last*
  named gets the lower offset. That was the whole of `GETUNIT`'s remaining
  difference -- thirteen bytes, all of them `L1` and `L2` swapped.

### 102b. Apple Pascal 1.3 accepts OTHERWISE, and the manual never says so

**VERIFIED BINARY FACT.** The shipped `XJP` reads `XJP 39..52 else $0810`,
and `$0810` holds a real statement -- a second copy of `'Unable to format
disk'` -- which every matched arm jumps *past*. That is not a statement
following the `CASE`, which all paths would reach; it is a default arm.

`OTHERWISE` appears nowhere in the 1.3 manual or the language reference.
The compiler takes it anyway, and adding it brought procedure 1 from 1306
bytes to exactly Apple's 1342. So the reserved word exists and is
undocumented, which puts it with the undocumented compiler options of
finding 24a.

### 102c. What is left

**Fifteen bytes in procedure 1, and they are one difference.** Apple's
`FJP` for the last `IF OK THEN` jumps to the *top* of the `REPEAT` at
`$04A4`; the reconstruction jumps to the end of the body at `$08D0`. Since
the loop is `UNTIL FALSE` the two are equivalent at run time, and every one
of the other fourteen differing bytes is a consequence: the jump table
allocates a slot at first use, so one extra early entry renumbers six later
`UJP`s that are otherwise identical in target.

Nesting the third `IF OK` inside the second was tried and is wrong -- it
moves the first difference earlier and raises the count to seventeen. What
produces a false-branch straight to the loop top is not yet known.

## 103. FORMATTER's native half reassembles to Apple's bytes

`src/native/FORMATTR.TEXT` is the 6502 source for `FORMATTE.2`, the
`EXTERNAL` function the Pascal of finding 102 declares as

```pascal
FUNCTION FORMATDISK(DRIVE: INTEGER): INTEGER; EXTERNAL;
```

**VERIFIED BINARY FACT.** `tools/asm6502.py` assembles it to **354 bytes,
identical to the disk's**, with **35 procedure-relative relocation entries
and no base-, segment- or Interpreter-relative entries at all** -- the same
counts, at the same offsets, as `FORMATTER.CODE` carries. The procedure runs
`$0902`-`$0A62` in the shipped segment (`$0902`-`$09F2` code, 122
instructions; `$09F2`-`$0A12` its own storage), `PROCEDURE NUMBER` is 0,
which is what marks it native, and `RELOCSEG` is 0.

`tools/probes/probe_prog_native_asm.py` is the check, twelve assertions
covering the declaration, the two attribute bytes, every byte of the image
and each relocation kind separately. It is the fast tier only;
`SYSTEM.ASSMBLER` under the emulator remains the acceptance test (finding
44e).

### 103a. Why every relocation is procedure-relative

The procedure's variables sit *inside its own image*, past the last
instruction: the saved return address, the driver vector, the slot and unit
bytes, the error code, and 22 bytes of the driver's zero page. Nothing it
touches is a segment global or an Interpreter entry point, so there is no
kind of relocation left for the Linker to do but move it as a block. That is
the whole explanation of a 35/0/0/0 table, and it is a property the byte
compare alone would not have shown.

### 103b. RELOCSEG is 0 because a program has no data segment

The library's natives relocate through a named data segment -- 21 for
TURTLEGRAPHICS, 1 for the two Intrinsic Units that have none (finding 96).
A program does not: base-relative references go through the BASE register,
which the manual (IV-36) writes as 0. The disk agrees. The probe checks the
rule rather than reading the byte back and handing it over.

### 103c. The two paths, and where error 39 is raised

The device type byte in SYSCOM's table at `$BF27` decides:

* **type 2, a Disk II** -- the tables the Pascal half read to `$3D00` are
  `JSR`ed directly with the unit byte in A, interrupts off.
* **anything else** -- the slot's own driver is called through `$Cn00`,
  after `$CnFE` bit 3 is tested for whether it can format at all. If it
  cannot, command 0 is issued as a status call and the carry reports the
  trouble.

`39` (`LDA #$27`) is raised here, by this procedure, when the unit table has
no entry for the drive; the other four codes the Pascal prints -- 43, 47,
51, 52 -- come back from the driver.

The save/restore of the driver's zero page is asymmetric and the asymmetry is
Apple's: the save loop ends on `BNE` and copies 21 bytes, the restore loop
ends on `BPL` and copies 22, so `$3A` is restored without ever having been
saved. It is reproduced because the bytes require it.

### 103d. What this settles about NATIVE_SIG

`("FORMATTE", 2)` was the last entry in `lift.py`'s signature table read off
a *call site* rather than a declaration -- one word in, a result into
`SRO 3`. `.FUNC FORMATDISK,1` says the same thing from the other side, and
`probe_native_sig.py` now holds the two together. `("LIBMAP", 2)` is the only
inferred entry left.

### 103e. The acceptance run: Apple's own assembler, 0 errors, identical bytes

**VERIFIED BINARY FACT.** `SYSTEM.ASSMBLER` 1.3, run under AppleWin on
`src/native/FORMATTR.TEXT` (as `FMTNATIV.TEXT` on `WORK:`), reports

```
6502 Assembler [1.3]
Assembly complete:     225 lines
     0  Errors flagged on this Assembly
```

and the codefile it writes carries one segment, `FORMATDI`, holding one
native procedure of **354 bytes that are identical to `FORMATTER.CODE`'s
procedure 2**, with the same 35 procedure-relative relocation entries at the
same offsets and no entries of any other kind.

This is the acceptance tier of finding 44e, and it is the first time it has
been run for anything other than `SEARCH.TEXT`. `tools/emuassemble.ps1`
drives it, the twin of `emucompile.ps1`; the run's output and its final
screen are kept under `acceptance/`, and
`tools/probes/probe_acceptance_asm.py` re-checks them against the disk on
every build. That probe is the only one of the four native checks with none
of this project's own code on either side of the comparison.

**One thing the assembler needs that the compiler does not.** It opens
`%6502.ERRORS`, found on the volume it was itself loaded from, and
`6502.OPCODES` written with *no volume at all* -- which is looked up on the
prefix volume, and after a boot that is the boot volume. `BOOT128` does not
carry it and `APPLE2` does, so the Filer's `P(refix` has to be set to
`APPLE2:` before `A(ssem` will get past its own opcode table.

### 103f. A codefile stores native procedures unrelocated

**VERIFIED BINARY FACT**, and the reason 103e needed no adjustment on either
side. The assembler's fresh output has its procedure at offset 0; the Linker
placed the shipped copy at `$0902` inside a segment holding four p-code
procedures as well. The two are byte-identical anyway, and the words the
relocation table names are the same in both:

```
  +$002   $00F0      +$006   $00F1      +$01D   $00F4
```

Those are offsets from the start of the procedure, not addresses in the
segment. So relocation is not something the Linker performs when it places a
procedure -- it is left to the loader, and the table travels with the code
precisely so that it can be. Adding the procedure's base to each named word
before comparing, which is the obvious thing to try, makes all 35 words
differ and nothing else.

## 104. FORMATTER is reconstructed

**VERIFIED BINARY FACT.** `src/pascal/programs/1.3/FORMATTER.text` compiled
by Apple's 1.3 compiler, `src/native/FORMATTR.TEXT` assembled by Apple's 1.3
assembler, and the two joined by Apple's 1.3 Linker, produce a codefile whose
segment dictionary and whose entire 2672-byte segment `FORMATTE` are
**identical to `APPLE3:FORMATTER.CODE`**:

```
  proc 1  1342/1342 B   data 2682/2682   IDENTICAL
  proc 2   354/ 354 B   native 6502      IDENTICAL
  proc 3    96/  96 B   data    0/   0   IDENTICAL   QUITIT
  proc 4   510/ 510 B   data   86/  86   IDENTICAL   GETVOLNAME
  proc 5   350/ 350 B   data    4/   4   IDENTICAL   GETUNIT
```

The Linker's own report names what it did: `Linking FORMATTE # 1`, then
`Copying func FORMATDI`.

This is the first program on the disk set reconstructed *whole* -- the
compiler and the library were each one kind of thing, and this is both kinds
in one file, joined the way Apple joined them.

### 104a. The last fifteen bytes: an inner REPEAT that starts where the outer one does

Finding 102c left procedure 1 with fifteen bytes outstanding, all of them
consequences of one `FJP` at `$0692` that jumps to `$04A4`, the top of the
loop, where the reconstruction jumped to `$08D0`, the end of the body.

`$04A4` is the top of the loop, and a false branch that goes there is not an
`IF` -- **it is an `UNTIL`**. The two loops simply begin at the same
statement:

```pascal
  REPEAT
    REPEAT
      GETUNIT;
      ...
      IF OK THEN
        BEGIN UNITSTATUS(VOL, NBLOCKS, 1); ... END
    UNTIL OK;
    GETVOLNAME;
    ...
  UNTIL FALSE;
```

so the inner `UNTIL OK` and the outer `UNTIL FALSE` both compile to a jump
back to `$04A4`, which is why the jump table holds that address twice
(`jtab-22` and `jtab-34`). The lifter had been printing it as
`if not (G20) then goto L04A4` all along and printing `L04A4:` twice, one
above the `repeat` and one at its top; both were the reading, not an
artefact.

**This is a case where the disassembly was right and the prose around it was
wrong.** Nothing about the binary changed; what changed was reading a
backward `FJP` as a loop condition rather than as a strangely-placed `IF`.
With that one change procedure 1 went from fifteen bytes out to identical,
and the jump-table renumbering that made up the other fourteen went with it.

### 104b. 394 bytes still differ, and all of them are past the end of the file

The codefile is 3584 bytes: 512 of segment dictionary, 2672 of segment, and
**400 bytes of slack** rounding the last block up. Every difference is in
that slack, and the two are not even the same *kind* of leftover -- Apple's
holds fragments of 6502, this run's holds fragments of the Linker's own
prompts (`illegal host file`, `...up host seg`).

That is uninitialised buffer written out to fill a block, not content: the
segment dictionary gives the segment's length, and nothing reads past it. It
cannot be reproduced and does not need to be, but it is recorded here rather
than quietly excluded, and `probe_acceptance.py` requires the compared region
to be all but one block of the file so the exclusion cannot grow.

## 105. `SYSTEM.COMPILER` linked -- and two new gaps the linking uncovers

**VERIFIED BINARY FACT.** Finding 91 predicted that compiling the fifteen
segments, assembling `src/native/SEARCH.TEXT`, and `L(ink`ing the two would
leave "nothing else missing." The three steps were run for the first time
today. Two of the fifteen segments are not what that finding expected, and
both are new, not previously visible, because nothing had compared PASCALCO
as a whole image against a *linked* file before -- finding 90e's whole-segment
check ran before linking existed, and finding 91 stopped at "the linker's
output is untested."

The run itself: `procbuild.py --emu --ver=1.3` spliced `BODY13.TEXT`,
Apple's 1.3 compiler built it clean (6599 lines, 0 errors, matching finding
60d), `SYSTEM.ASSMBLER` assembled `SEARCH.TEXT` clean (519 lines, 0 errors),
and `SYSTEM.LINKER` joined them -- `Linking PASCALCO # 1`, `Copying proc
IDSEARCH`, `Copying func TREESEAR` -- with no errors. Fourteen of the
fifteen segments (`COMPINIT` through `FINISHUP`) came out **byte-identical
end to end**, same as finding 90e found pre-linking; the linker does not
touch what it does not need to.

`PASCALCO` itself is the interesting one. Its **native halves are exactly
right**: `IDSEARCH` and `TREESEARCH` sit at the same `enter_ic`/`exit_ic`/
`jtab` as Apple's shipped copy (4594/5388/5392 and 5394/5536/5540), and every
byte in that range matches. That is finding 103f confirmed a second time, at
scale, inside a real linked file rather than a standalone assembly.

Two things do not match, and both are new findings rather than corrections
of anything already on record.

### 105a. An extra, empty host segment -- 512 bytes, and what is and is not understood about it

Apple's shipped `SYSTEM.COMPILER` has **no segment 0**. The dictionary's
code addr/len word for slot 0 is `0000` and the name table holds eight
spaces -- and this is not 1.3-specific or a Linker artifact: 1.1's shipped
`SYSTEM.COMPILER`, which never goes near `SYSTEM.LINKER` at all (1.1's
`IDSEARCH`/`TREESEARCH` are p-code, no native half to link in), shows the
identical zero entry. Whatever produces this happens in the **compile**,
in both releases.

Our linked file has a real segment there, `PASCALSY` -- the `(*$U-*)
PROGRAM PASCALSYSTEM` host finding 60 established wraps `PASCALCO` as a
segment procedure. `BEGIN END.` is the entire outer block, and running the
fast tier (`ucsdpsys_compile`) on isolated model programs shaped like it
settles what its bytes actually are:

* **The zero-length code is right.** Every model program's outermost
  block, however it is nested, compiles to genuinely nothing when its body
  is `BEGIN END` -- `enter_ic = exit_ic`. That part of `PASCALSY` was never
  in question.
* **The 43-procedure attribute table is not garbage, and not a bug.**
  `NEXTPROC` is scoped per segment, saved and restored correctly across
  every level of nesting this project's own source uses -- verified
  directly: a model program nesting a `SEGMENT PROCEDURE` two and three
  levels deep, with `FORWARD` declarations, `EXTERNAL` declarations and
  multiple sibling segment procedures all present at once, restores its
  outer segment's count to exactly 1 (itself) every time. `PASCALSY`'s
  count of 43 is not that counter leaking -- it is the roughly forty-two
  operating-system routines (`FOPEN`, `FCLOSE`, `FGET`, ... `OSPROC43`)
  that the `(*$U-*)` skeleton names with a bare `FORWARD` and never
  defines, because a `(*$U-*)` program borrows the OS's own procedures by
  number rather than declaring them (finding 63, finding 79b). A `FORWARD`
  claims a procedure number the moment it is parsed, whether or not a body
  ever follows, and each of those ~42 is one more than `PASCALCOMPILER`
  itself. Removing them and substituting a single stub -- exactly what
  `procbuild.defang_forwards` does for the fast tier, since
  `ucsdpsys_compile` refuses an undefined forward the way Apple's compiler
  does not -- drops the count from 43 to 2 (the stub, plus
  `PASCALCOMPILER`), confirming the arithmetic exactly.
* **`SYSTEM.LINKER` does not drop it.** `2026-08-25-compiler-linked-v2`
  is Apple's own Linker, not a reimplementation, and it carried `PASCALSY`
  through untouched. Whatever removes it in Apple's real build happens
  before the Linker ever sees the file.

So the segment's *content*, given this source shape, is exactly what a
correct compiler produces -- the reconstruction is not miscounting
anything. What remains genuinely open is why Apple's real compile never
reaches this state at all. `BLOCK`'s own tail (`PASCALCO.text`, the
procedure of that name) calls `FINISHSEG` unconditionally once its
declaration-processing loop exhausts (`UNTIL TOS = NIL; FINISHSEG`) --
there is no guard on it, and that code is itself part of the segment
verified byte-identical against Apple's binary (finding 107), so it is
not a candidate for being wrong. The one alternative exit `BLOCK` has --
`IF (SY = UNITSY) AND NOT INMODULE THEN ... UNITPART(...); IF SY = PERIOD
THEN EXIT(BLOCK)`, skipping `FINISHSEG` entirely -- was checked and ruled
out: a real Pascal `UNIT`'s own init body is niladic (`UNITPART.text`'s
`UNITBODY`: `LOCALLC := 1`), where `PASCALCO`'s verified `PARAM SIZE` is 4;
and a unit's interface text leaves a nonzero `textaddr` in the dictionary,
where Apple's shipped file has `textaddr = 0` for every one of its sixteen
slots, PASCALCO included. Neither of those is compatible with `PASCALCO`
having come from a `UNIT`. What construct Apple's compiler actually used
to avoid calling `FINISHSEG` for the host is not established; it is the
one open question left in this file.

### 105a-i. The gap tested against Apple's own compiler, twice, and narrowed further

**VERIFIED BINARY FACT**, from two minimal programs compiled by the real
1.3 `SYSTEM.COMPILER` under the emulator, not the fast tier
(`acceptance/2026-08-25-hostseg-experiments/`):

```
(*$U-*)                            (*$U-*)
PROGRAM TESTHOST;                  VAR X: INTEGER;
VAR X: INTEGER;
                                    SEGMENT PROCEDURE INNER(A,B: INTEGER);
SEGMENT PROCEDURE INNER(A,B: INTEGER);  PROCEDURE FOO;
  PROCEDURE FOO;                   BEGIN
  BEGIN                            END;
  END;                             BEGIN
BEGIN                                FOO
  FOO                              END;
END;
                                    BEGIN
BEGIN                               END.
END.
```

Both compile clean, and both give the *exact same shape* this
reconstruction produces for `SYSTEM.COMPILER`: a real, non-empty segment 0
(16 bytes: `SEG=0`, `NEXTPROC-1=1` -- just the outer block's own attribute
record), then `INNER` as segment 1. **Apple's own compiler, given a bare
`(*$U-*) PROGRAM; VAR ...; SEGMENT PROCEDURE ...; BEGIN END.` shape,
produces a nonzero segment 0 every time.** This was checked, not assumed --
the second program drops the `PROGRAM` heading entirely (legal here,
because `COMPINIT.text`'s own code only parses one `IF SY = PROGSY`,
never requires it), and the result is identical except the segment name is
blank instead of named, which is itself one more match for what Apple's
shipped file shows at slot 0 -- just not the zero length that goes with
it.

This rules out any theory resting on some subtlety of *this* reconstruction's
`PASCALCO.text` or its splice: the mechanism that empties segment 0 in
Apple's shipped file cannot be a fast-tier-only quirk or a bug in the
verified-correct `BLOCK`/`FINISHSEG` source, because the same shape, run
through Apple's own 1.3 compiler, behaves exactly as this reconstruction's
does. Whatever Apple's real top-level source looked like, it was not this
shape.

The `UNIT`-intrinsic variant of 105a's ruled-out theory is now closed too,
on the same evidence that closed the plain one: every one of
`SYSTEM.LIBRARY`'s six real intrinsic units -- `TRANSCEND`, `CHAINSTUFF`,
`PASCALIO`, `LONGINTIO`, `TURTLEGRAPHICS`, `APPLESTUFF`, checked directly
off the shipped binary -- has `PARAM SIZE 0` for its own procedure 1, no
exception. `UNITBODY`'s niladic convention (`LOCALLC := 1`) is not
something one intrinsic unit might have escaped; it is universal across
every one Apple actually shipped. `PASCALCO`'s verified `PARAM SIZE 4`
rules out an intrinsic unit exactly as it ruled out a plain one.

What remains is narrower than before but still open: some construct
avoids `BLOCK` ever reaching its own unconditional tail `FINISHSEG` for
the host, and it is neither of `BLOCK`'s two known early exits (both
gated on `UNIT`, both ruled out) nor a difference in program-heading
syntax (tested, no effect) nor anything about `SYSTEM.LINKER` (tested
directly on this project's own linked file, finding 105a). If there is a
third path through the verified source that has not been read yet, it has
not been found by tracing the source or by testing the shape experimentally.

### 105b. `PASCALCO`'s procedure numbering is right; its physical layout is not

Every procedure's **content** was already confirmed against Apple's (finding
90e, 147 of 147, disassembly-based). Comparing the raw segment bytes for the
first time -- which only linking makes possible, since compiling alone
leaves the segment short -- shows the two files place those same procedures
at different **offsets** inside the segment. `ERROR`(4) through `ENTERID`(7)
sit at the same four offsets in both. From there they diverge:

| physical order | Apple | this reconstruction |
|---|---|---|
| 5th body | `CHECKEND` (14) | `SEARCHSECTION` (9) |
| 6th body | `HOLDMOST` (28) | `SEARCHID` (10) |
| 7th body | `INSYMBOL` (8) | `GETBOUNDS` (11) |
| ... | 9,10,11,12,13,16-21,**15**,22-25,**29**,26,27,31,30,1 | 9,10,11,12,13,14,15,16-25,27,8,26,28,... |

Every number matches finding 61's table; only the *order the bodies are
compiled in* differs. UCSD emits code in the order procedure bodies are
parsed, not in declaration order (finding 61 already established that
distinction for numbering; this is the same distinction applied to
placement). `BUMPSEG`/`NEWSEG`/`CHECKEND`/`SEGINFO`(12-15) were already
known to be **inserted by Apple** relative to the UCSD II.0 forward block;
this is evidence that Apple's source also *defines* several of them, and
`HOLDMOST`, earlier than the reconstruction currently does -- specifically,
before `INSYMBOL`'s own body, which the reconstruction places after
`COMPILE`.

3304 of `PASCALCO`'s 5606 bytes differ as a result, all of them inside
procedure bodies 9 through 30's territory (never inside procedure 1, the
outer block, or either native routine). This is a physical reordering of
`PASCALCO.text`'s procedure *definitions*, preserving every forward
declaration and every procedure number, and it is not done here -- it is
recorded as the one specific thing standing between this reconstruction and
a byte-identical `SYSTEM.COMPILER`.

### 105c. What this does and does not change

Findings 90 and 91's claims stand: every p-code procedure's *content* is
right, both native routines are right and sit at the right offset, and
fourteen of fifteen segments are exactly Apple's bytes. What finding 91's
"nothing else is missing" gets wrong is scope -- it was written before a
linked comparison was possible and described the compile-time gap
completely. The two gaps above only exist once the file is whole enough to
compare as Apple shipped it, which is what the two hard rules this finding
leans on say to expect: *"a total that does not balance is evidence"* and
*"prefer a check the binary can fail."* Both checks did.

The run's outputs are kept in `acceptance/2026-08-25-compiler-search-asm/`
and `acceptance/2026-08-25-compiler-linked/`, same as finding 104's. Neither
is wired into `probe_acceptance.py` yet -- that probe requires an exact
match, and this run does not have one.

## 106. `runemu.py` was writing to evidence, silently

**VERIFIED BINARY FACT.** During the run behind finding 105,
`evidence/disks/Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk` came back from
a `--boot128` session with a changed hash. AppleWin opens `-d1`/`-d2` for
read-write with no prompt and no error either way; a boot alone is enough
to update the volume's date stamp, and every emulator run this project has
ever made mounted `evidence/` disks the same way. `git status` catching it
is what this rule (`docs/PLAN.md`: *"nothing in evidence/ is ever
modified"*) is checked *against* -- it had not been checked *for* until now.

`git checkout` recovered the file; `evidence/` is git-tracked and every run
so far has been followed by a commit, so nothing upstream saw a modified
copy. The fix is filesystem-level, not procedural: `tools/runemu.py` now
sets the read-only attribute on every evidence disk it is about to hand
AppleWin, on every launch, rather than relying on it having been set once
by hand and staying that way (`enforce_readonly`, called right after the
existence check, before the command line is built). AppleWin mounts and
boots a read-only image exactly as before -- checked by re-running the same
`--boot128 --work2` session and confirming the hash held -- it simply
cannot write to it, which is the point.

## 107. Finding 105b closed: `PASCALCO` is byte-identical

**VERIFIED BINARY FACT.** Finding 105b's table said what was needed:
reorder `PASCALCO.text`'s procedure *bodies* to Apple's physical placement,
without touching declaration order or numbering. Done, verified against a
fresh emulator run: `PASCALCO`, all 5606 bytes, is now byte-identical to
Apple's shipped copy -- the whole segment, not just the disassembly. All 15
real segments of `SYSTEM.COMPILER` are byte-identical.

Reordering the bodies was not quite enough on its own, and the reason is
worth keeping. Three of the 31 procedures are **not** forward-declared --
`COMMENTER` (nested in `INSYMBOL`), `FINDFORW` (nested in `BLOCK`), and
`HOLDROUT` (nested in `HOLDMOST`) -- and `COMPILE`, the fourth in that
number range, was not forward-declared here either. For a procedure with no
forward declaration, UCSD assigns its number *at the same textual point* its
code is emitted: parse order, number order, and code-placement order are
one and the same thing. Moving `INSYMBOL`'s body earlier in the file (to
match Apple's physical layout) also moved *when `COMMENTER`'s header gets
parsed* -- and since `COMPILE` had no forward declaration, moving `INSYMBOL`
ahead of it let `COMMENTER` claim 27 before `COMPILE` could, cascading
`FINDFORW`, `HOLDMOST` and `HOLDROUT` down by one each. Eighteen bytes came
out wrong as a result, every one of them a procedure-number operand in the
27-31 range, in exactly the three nested bodies and nowhere else.

The fix is a single `PROCEDURE COMPILE; FORWARD;`, placed in the initial
forward block alongside the other 23 (after `BLOCK`), so `COMPILE` claims
27 at the point the forward block is parsed -- textually early -- while its
own body stays physically where it already was, after `BLOCK`, before
`HOLDMOST`. Declaration-time numbering and code-placement order are
decoupled for exactly the one procedure that needed it, which is why only
one FORWARD had to be added: every other non-forward procedure here already
has its number and its body at the same point in the file.

`acceptance/2026-08-25-compiler-linked-v2/` holds the run: `SYSTEM.COMPILER`
1.3 compiling `BODY13.TEXT` (6601 lines, 0 errors), `SYSTEM.ASSMBLER`
assembling `SEARCH.TEXT` (519 lines, 0 errors, unchanged from before), and
`SYSTEM.LINKER` joining them -- with the resulting `PASCALCO` segment
byte-identical to Apple's.

What is left is finding 105a alone: the extra, empty `PASCALSY` host
segment, 512 bytes, present in every compile of this splice and absent from
Apple's shipped file. It is not affected by anything in this finding --
segment 0's own bytes were unchanged throughout.

## 108. `runemu.py` mounted evidence for the assembler to write to -- fixed properly

**VERIFIED BINARY FACT.** Finding 106's read-only fix was necessary but
insufficient: `SYSTEM.ASSMBLER` writes a `%LINKER.INFO` scratch file to the
Filer's P(refix volume when a source references cross-segment procedures
(what `SEARCH.TEXT`'s `IDSEARCH`/`TREESEARCH` are, from the Linker's side),
and the recipe for an assemble sets that prefix to `APPLE2:` (finding 44e).
A read-only `APPLE2:` fails that write with `I/O Error #16` and stops the
assembly cold -- read-only stopped the corruption finding 106 found, and
then stopped a legitimate assemble from working at all.

The fix in `runemu.py` is `scratch_copy`: every evidence disk any drive
would have received is copied to `build/disks/emu-scratch/` fresh on every
launch and *that* copy is what AppleWin mounts, at `-d1`, `-d2` and `-s5d2`
alike. Read-only stays on the originals as defense in depth, but nothing
under `evidence/` is handed to AppleWin at all any more, so what it can or
cannot write to no longer touches the question. Reassembling `SEARCH.TEXT`
after the change gave the same clean run as before finding 106 (519 lines,
0 errors) -- the fix restores the working behavior rather than trading one
failure for another.

## 109. `LIBMAP.2` is `IDSEARCH` -- the same 800 bytes, not a similar routine

**VERIFIED BINARY FACT.** `LIBMAP.CODE`'s one native procedure and
`SYSTEM.COMPILER`'s `IDSEARCH` (`PASCALCO` procedure 2) are byte-for-byte
identical: assembling `src/native/SEARCH.TEXT`'s `IDSEARCH` and diffing the
result against `LIBMAP.2`'s own `enter_ic..jtab+2` gives **zero differences
over all 800 bytes**. Every zero-page location matches (`RTN=$7E`,
`VAL1=$86`, `VAL2=$87`, `CHARS=$88`, `NUM4CH=$90`, `ENTAD=$92`,
`PARAM1=$94`, `PNT=$96`), the case-folding and underscore-stripping scan is
identical instruction for instruction, and the entire reserved-word table
-- all thirty-some words, `AND` through `WITH`, with the same SY and OP
values, in the same per-letter order, down to the shared three-byte
empty-letter slot at the same relative offset -- is the same table.

Apple linked one routine into two codefiles rather than write a second
copy: `LIBMAP.CODE`'s job of displaying a unit's interface text needs the
same "is this identifier a reserved word" answer the compiler's own
lexer needs, so it reused the compiler's own `IDSEARCH`, whole. This also
answers `LIBMAP.9`'s otherwise-unexplained `L5 = 52` check (SY 52 is
`IMPLEMENTATION` in this table): `LIBMAP.9` is scanning the copied
interface text for the `IMPLEMENTATION` keyword to know where to stop.

This closes the native half of `LIBMAP.CODE` before it was ever written:
declaring `PROCEDURE IDSEARCH(VAR IDREC, ID); EXTERNAL;` and linking
against the existing, already-verified `src/native/SEARCH.TEXT` is the
whole of it, with no new 6502 to reconstruct. `lift.py`'s `NATIVE_SIG`
entry for `("LIBMAP", 2)` now names it `"IDSEARCH"` rather than carrying a
placeholder description, retiring the last entry in that table that was
not backed by reconstructed source (finding 100f).

## 110. `MAXUNIT`/`MAX_SEG` audit -- one real 1.1/1.3 divergence in the tree, both inert

**VERIFIED SOURCE FACT.** Prompted by a user-supplied excerpt of Dave
Tribby's `SYSTEM.PASCAL` globals (`GLOBAL1_VARS`/`GLOBAL2_VARS`,
`unit_table: ARRAY [0..20]`), checked whether anything already reconstructed
in this tree still carries 1.1/64K bounds (`MAXUNIT=12`, `MAX_SEG=31`)
where 1.3/128K needs the wider ones (`MAXUNIT=20`, `MAX_SEG=63`).

- **`SYSTEM.COMPILER`'s own global block is already right.** `KINDSET` and
  the `SEG`/`DATASEG` range checks in `src/pascal/1.3/phases/DECLARAT.text`
  and `UNITPART.text` use `0..63`, matching 1.1's `0..31` one-for-one
  (`SEGSUSED` in `analysis/reconstruction/globals-1.3.text` is `SET OF
  0..63`, 1.1's is `SET OF 0..31`) -- already tracked as a real 1.1->1.3
  drift, not missed.
- **`src/pascal/units/1.3/PASCALIO.text` and `LONGINTIO.text` still declare
  `MAXUNIT = 12` and `MAX_SEG = 31`**, verbatim from UCSD II.0's
  `GLOBALS.TEXT` (the file's own header comment says as much: "the CONST and
  TYPE blocks below are II.0's, verbatim"). This is a real discrepancy
  against Tribby's confirmed 1.3/128K values, but it is **inert**: `MAX_SEG`
  is declared and never referenced anywhere in either file, and `MAXUNIT`
  only bounds `UNITNUM`, which is the type of one scalar field (`FIB.FUNIT`)
  that this unit only ever *reads* (`UNITWRITE(FUNIT,...)`,
  `UNITREAD(FUNIT,...)`), never assigns -- so no `CHK` bound keyed to
  `MAXUNIT` is ever emitted into the compiled p-code. A subrange's *stored*
  size is one word regardless of its bound, so it can't affect the FIB
  record's byte layout either. Confirmed no compiled-output difference is
  possible; left as-is (renaming it would be re-deriving what the binary
  already doesn't care about) but flagged here so a future reader doesn't
  have to re-derive the same thing.
- `LIBMAP.text`'s own `ARRAY [0..15]` bounds (`SEGWORDS`, the segment
  dictionary) are a library file's fixed 16-segment-slot format, unrelated
  to `MAXUNIT`/`MAX_SEG` -- not a 64K/128K question at all.

No missing area found in anything currently reconstructed. `SYSTEM.PASCAL`
itself (the file that actually owns `unit_table`/`GLOBAL1_VARS`) is not
started; Tribby's disks are the reference to return to when it is -- see
`evidence/reference/tribby-6disks-catalog.md`.

**Update, same day -- source located and confirmed.** The user's pasted
excerpt is Dave Tribby's own `UNIT SysInf` ("Written by DMT beginning
2-8-87"), found as `SYSINF.TEXT` on his `psys.sdk` (a ShrinkIt-compressed
copy of the `psys` disk; the raw `.dsk`/`.do`/`.po` versions of that disk
have a disk-specific directory corruption -- see the catalog file --
`SYSINF.TEXT` from the `.sdk` decodes cleanly with
`tools/a2pascal/textfile.py`). Confirmed by reading the live text:
`max_unit := 12;` for 1.1, `max_unit := 20;` for 1.2 and 1.3
(`FUNCTION ChkPascal`), `unit_table: ARRAY [0..20] OF RECORD ...` in
`GLOBAL1_VARS`, `funit: 0..20` in `FIB_TYPE` -- exactly the values the user
quoted. But **`MAX_SEG` does not appear anywhere in this file** -- Tribby's
unit only reads `max_unit`/`unit_table`; it has no reason to touch segment
counts. So the `MAXUNIT = 12`/`MAX_SEG = 31` CONST pair with the "64K vs
128K" comments the user quoted is not from this file -- it's from a
different, still-unidentified source (almost certainly a UCSD II.0-style
`GLOBALS.TEXT` for `SYSTEM.PASCAL` itself, the same lineage `PASCALIO.text`
and `LONGINTIO.text` copied their own stale `MAXUNIT`/`MAX_SEG` CONSTs
from, above) -- not present on any of the six Tribby disks. Doesn't change
the conclusion above: still no missing area in anything this project has
reconstructed.

## 111. `LIBMAP.text` `SHOWONE`'s entry-reading loop and `GETWORD` reconstructed

**STRONG INFERENCE, instruction-traced.** Continuing `LIBMAP.CODE`
(procedure 8, `SHOWONE`, and its nested procedure 10, `GETWORD`), left as
`(*STUB*)` since finding 109/the `SHOWSEGS` session. Read the full raw
p-code for both procedures (`analysis/utilities/LIBMAP-1.3-APPLE2.pcode.txt`,
lines 593-988 and 1128-1188) rather than working from the lifted
pseudo-Pascal alone, since the lifter can't resolve `CSP`/`CXP` argument
semantics on its own.

- **The earlier stub comment's model was wrong on two counts.** It guessed
  `GETWORD` reads "a first word... double-buffered two bytes at a time."
  The actual disassembly shows exactly one `CLP 10` (call `GETWORD`) per
  loop iteration, immediately followed by a `MOVELEFT` of 16 bytes from
  `GETWORD`'s target address -- `GETWORD` copies a *whole* reference-stream
  entry in one shot, not a word. And it guessed `USINGLIB, not LISTREFS...
  LISTREFS only shows up inside SHOWREF` -- false: `LDO 601` (`LISTREFS`)
  directly gates the "external proc" case (`RKIND` 9/10), the same way
  `LDO 602` (`USINGLIB`) gates 6/7/8.
- **`GETWORD`'s real shape**: a 512-byte read buffer (`RBUF`, one disk
  block, declared `ARRAY [0..31] OF REFENTRY` -- 32 entries * 8 words =
  256 words = 512 bytes exactly), refilled via `FBLOCKIO` whenever
  `BYTEPOS` (which counts entries left unread, not bytes or "half of
  RBUF") reaches 0, then reset to 32. The read position is `IXA 8` --
  entry-indexed, an 8-word/16-byte stride -- at index `32 - BYTEPOS`, so
  the first entry read after a refill is index 0. A `FBLOCKIO <> 1` read
  error is folded into the stream itself: it forces the freshly-read
  entry's `RKIND` to 0 rather than raising anything, so `SHOWONE`'s own
  `UNTIL RKIND = 0` sees ordinary end-of-stream instead of looping on
  garbage.
- **The swap step only touches half the entry.** When `SWAPPED`, the loop
  copies the whole 16-byte entry into `SWAPBUF` and swaps *only* words
  4 through 7 of the 8-word buffer (`SWAPBYTES(SWAPBUF[I])` for `I := 4 TO
  7`) -- the four numeric fields (`RKIND`, `RVAL1`, `RVAL2`, and a spare
  word), not the 4-word name at the front. Byte order doesn't matter for a
  string; it matters for a 16-bit value, and the binary's own loop bounds
  (`SLDC 4`/`SLDC 7`, not `0`/`7`) say exactly that.
- **The RLENG/ALENG argument order in `FWRITEBYTES(VAR F, VAR A, RLENG,
  ALENG)`** (`GLOBALS.TEXT` line 293) was previously assumed
  actual-length-then-width from the body's variable names alone; two probe
  compiles through the fast tier (`WRITE` on a 12-char array with `:8`,
  then an 8-char array with `:20`) confirm the reverse: the **requested
  field width is pushed first (RLENG), the item's own static length
  second (ALENG)**. This resolves what looked like a contradiction in the
  entry-name print calls (`FWRITEBYTES(...,12,8)`): the name field itself
  is still the expected 8 characters (`SEGNAMESTR`); the call requests a
  12-column field, giving the observed 4-space left pad.
- **`REFENTRY`**, the new type this session added for the reference-stream
  entry (`RNAME: SEGNAMESTR; RKIND: 0..14; RVAL1, RVAL2: INTEGER; SPARE:
  INTEGER` -- 8 words/16 bytes, matching every `MOVELEFT` count seen), lets
  `GETWORD`, the swap block, and `VALIDNAME(ENTRY.RNAME)` all type-check
  as ordinary Pascal, compiling (per the fast tier, modulo its unrelated
  `FBLOCKIO`/`MOVELEFT` arity limits below) to the same field-offset loads
  the binary uses for `RKIND`/`RVAL1`/`RVAL2` (offsets 8, 9, 10 relative
  to the entry's own base, matching the pre-existing `KIND`/`VAL1`/`VAL2`
  local numbering this file already had).
- **Two small gaps are real and still unexplained**: one word between
  `ENTRY` (locals 4-11) and `NEEDINFO` (local 13), and roughly 276 words
  after the swap-loop counters that nothing in this procedure's body ever
  reads or writes -- previously guessed as a `SEGDICTREC`-shaped
  `SWAPTEMP`, now known to be wrong (the disassembly's only offsets
  touched anywhere in the whole procedure are 1-3, 4-13, 270-279; nothing
  in the 14-269 range is read as anything other than `RBUF`, and nothing
  past 279 is read at all). Left as an honestly-labelled `SPARE` padding
  array sized to Apple's previously-confirmed `params=2/data=556`, not
  reconfirmed with this session's real locals in place.
- **Not yet acceptance-tier verified.** `tools/xcompile.py`'s fast tier
  cannot check this procedure at all past the syntax level: its own
  builtin `moveleft`/`blockread` take three and four arguments, not the
  five and six this loop's `MOVELEFT`/`FBLOCKIO` calls need (confirmed:
  compiling the full file gets exactly the same "found five fatal errors"
  either way, all on those two calls, with everything else -- including
  the new `REFENTRY` type -- parsing clean). The AppleWin/`SYSTEM.COMPILER`
  acceptance-tier recompile that would pin the two padding gaps down
  exactly is the next step, not yet done this session.

`SHOWINFO` (procedure 9, 1042 words of locals, the largest in the file --
`docs/PLAN.md` previously said 521, which was wrong; corrected here),
`SHOWREF` (procedure 11), and `MAPLIBRARY` (procedure 12) remain
unread stubs.

**Update, same day -- acceptance-tier verified, both padding gaps
resolved differently than guessed.** `LIBMAP.text` compiles clean under
Apple's own `SYSTEM.COMPILER` (via `LIBMAPT.TEXT` on `SYSHD:`, compile
only, not linked -- `acceptance/2026-08-27-libmap-showone-getword/`),
reaching all the way to the outer program's `BEGIN` with zero errors.
Getting there took four real fixes, none of them guessable from the fast
tier or from reading the disassembly alone -- each is a fact about
*Apple's compiler*, not about the binary:

- **`@` is illegal, full stop, in every `MOVELEFT` call, not just the
  `WITH`-vs-pointer case `SHOWSEGS`'s own header comment already
  documented.** `MOVELEFT(@src, 0, @dst, 0, 16)` was this file's own
  pre-existing style (written before this session, never acceptance-tier
  checked) and fails with error 400 exactly like the `ENTRY: ^DIRENTRY`
  pointer did. Real UCSD Pascal `MOVELEFT` takes three arguments --
  `MOVELEFT(SOURCE, DESTINATION, COUNT)`, language reference "The
  MOVELEFT and MOVERIGHT Procedures" -- untyped `VAR`, no `@`, indexed
  elements allowed directly (`MOVELEFT(RBUF[IDX], W, 16)`). The compiler
  itself expands each reference argument into the two p-code words
  (address, 0) already seen in the binary's own `CSP 2` calls, so the
  five-word call shape that misled the original reading into thinking
  `MOVELEFT` took five *source* arguments was the compiler's doing, not
  the programmer's.
- **The `GLOBALS.TEXT` "reach segment 0 with a body-less `FORWARD`" idiom
  does not work for an ordinary program.** `FUNCTION FBLOCKIO(...);
  FORWARD;` with the real six-argument, `FIB`/`WINDOW`-typed signature
  (untyped `VAR` substituted for both, per the "EXTERNAL routines may
  declare an untyped VAR parameter" rule -- language reference III-3884)
  compiles the *declaration*, but the call site then fails with error
  117, unsatisfied forward reference, because nothing ever gives it a
  body. `(*$U-*)` ("compile at the system lexical level," language
  reference, the "user program" option) was tried next and made things
  worse -- error 160 on the *next* declaration down, because $U-'s side
  effects (R-/G+/I-/V- all at once) change how the compiler treats
  `EXTERNAL` too. The actual answer sidesteps the whole mechanism:
  `BLOCKREAD` is a **standard Pascal function** (language reference,
  "Untyped File I/O Operations," `BLOCKREAD(file, buffer, count,
  [blocknumber])`) that the compiler recognizes by name like `WRITE`,
  and it compiles straight to the same `CXP 0,28` -- exactly what the
  fast tier's "symbol FBLOCKIO unknown... guessing you meant the
  blockread function instead" was pointing at three fixes ago. No
  `FORWARD`, no `$U-`, no `FIB`/`WINDOW` substitute types needed at all.
- **`SHOWREF`'s parameter is a value `STRING`, not `VAR`.** The
  pre-existing guess (`VAR NAME: STRING`, reasoning that every call site
  passes a string constant's own address) fails error 154, actual
  parameter must be a variable -- a `VAR` parameter cannot bind to a
  literal like `' global'`. Changed to `NAME: STRING` (still address-passed
  under the hood, since strings are variable-size, which is almost
  certainly what produced the original mistaken reading).
- **A comment-nesting bug, not a Pascal semantics bug**: two of this
  session's own doc comments put a `{ CXP 0,28 }`-style aside inside a
  larger `{ ... }` block comment. Apple Pascal comments do not nest, so
  the inner `{` silently closed the outer one and dumped raw prose into
  the token stream (error 400 again, on a `,` inside the comment text).
  Fixed by dropping the inner braces; worth remembering for any future
  comment in this file.

With those four fixed, **both procedures' frames match Apple's binary
exactly**: `SHOWONE` `params=2/data=556`, `GETWORD` `params=2/data=2`
(read from the compiled `LIBMAPT.CODE`'s own attribute table, not
estimated). Two things about the padding gaps came out differently than
guessed:

- **`GETWORD`'s `IDX` local was wrong, not just unverified.** Apple's
  real `GETWORD` has no local for the read-position index at all --
  `32 - BYTEPOS` is computed inline in the `MOVELEFT` call. An explicit
  `IDX: INTEGER` local (needed to make the fast tier's stricter checking
  happy earlier in this same session, before the `@`/`MOVELEFT` argument
  count was corrected) gave `params=2/data=4`, two words over. Removing
  it and folding the expression inline closed the gap exactly -- this
  wasn't a "how big is the mystery padding" question at all, it was a
  real extra variable that shouldn't have been there.
- **`SHOWONE`'s trailing `SPARE` gap is one word, not 276, and the type
  matters in a way this file cannot yet explain.** Declaring it as
  `ARRAY [1..276] OF INTEGER` (this session's original guess, sized by
  matching the *previous* session's `data=556` figure against a much
  cruder local-count) overshot to `data=1106`. Bisecting empirically
  (`ARRAY [1..276]` gave `1106`, `ARRAY [1..10]` gave `574`, `ARRAY [1..1]`
  gave exactly `556`) found a clean linear relationship -- `data = 554 +
  2 * (array element count)` -- meaning **this specific array declaration
  costs two words per element here, not one.** A bare scalar `SPARE:
  INTEGER` also gives exactly `556`. Nothing in this file explains *why*
  an `ARRAY OF INTEGER` local would cost double in this position; it is
  recorded as a real, reproducible anomaly, not resolved. The practical
  fix -- declare `SPARE` as a plain `INTEGER` -- sidesteps it and matches
  Apple exactly, which is what the source now does.

Not yet done: a full instruction-for-instruction diff between this
session's compiled `SHOWONE`/`GETWORD` and Apple's binary (only the frame
sizes and the hand-traced control flow are confirmed matching; an
automated mnemonic-stream diff was attempted and abandoned when the
regex extractor proved unreliable on `LSA`/`CHK`-style variable-length
instructions -- worth a proper tool, not a quick script, if it's picked
up again).

## 112. `SET40COLS.CODE` reconstructed from scratch -- compiles clean first try, 2544/2560 bytes identical

**VERIFIED BINARY FACT.** `docs/PLAN.md` item 3 turned out to need a
correction before it could be started: checked all six evidence disks and
there is no `BINDER.TEXT` or `SET40COLS.TEXT` anywhere, so neither file is
"nearly free" the way `LINEFEED` was (finding 99a) -- both need the same
lift-and-rewrite treatment as `SYSTEM.LIBRARY`/`SYSTEM.COMPILER`/`LIBMAP`,
starting from the p-code alone. `SET40COLS.CODE` was picked over `BINDER`
because it carries no known blocker equivalent to `BINDER`'s already-
documented 15-byte SEGINFO mystery (finding 99c).

Four p-code procedures, no native half (`analysis/utilities/
SET40COLS-1.3-APPLE3.pcode.txt`/`.pas.txt`, already lifted). Read
straightforwardly off the disassembly and the language reference for two
things not otherwise obvious:

- **The directory flag byte (byte 25 of the volume's own block-2 header)
  is read/written through a small variant record** -- a whole-byte view
  to copy it in and out of the 512-byte block buffer, and an
  eight-`BOOLEAN` view to test/set bit 3 without disturbing the rest.
  `PACKED RECORD CASE INTEGER OF 0: (ASBYTE: PACKED ARRAY[0..0] OF
  0..255); 1: (BITS: PACKED ARRAY[0..7] OF BOOLEAN) END`.
- **The volume-number validation is a real `SET` membership test**, not
  arithmetic: `UNITNUM IN [4, 5, 9, 10, 11, 12]` compiles to the exact
  `LDCI 7728` bitmask the binary has (bit *N* set for volume number *N*,
  confirmed by decoding 7728 in binary against the prompt text's own
  "4, 5, 9..12").

**Compiled clean under Apple's own `SYSTEM.COMPILER` on the first attempt**
(`acceptance/2026-08-27-set40cols-compile/`) -- no iteration needed, unlike
`LIBMAP`'s `SHOWONE`/`GETWORD` (finding 111), because this file has no
`MOVELEFT`/OS-forward/untyped-parameter traps to fall into; ordinary
`WRITE`/`READ`/`UNITREAD`/`UNITWRITE` throughout. All four procedures'
`params`/`data` match Apple's shipped binary exactly (`520`/`8`/`0`/`0`
data words), and a full mnemonic-stream diff against
`SET40COLS-1.3-APPLE3.pcode.txt` is **469 of 469 instructions identical**
-- the regex-based diff tool that proved unreliable on `LIBMAP`'s
`LSA`/`CHK`-heavy code (finding 111) worked cleanly here.

**The compiled codefile is 2544 of 2560 bytes identical to Apple's
shipped `SET40COLS.CODE`.** The 16 real differences are all the same
single byte pattern, at the SEGINFO version-stamp position for each of
segment 1's 16 procedure slots: Apple's shipped file reads `$42`
(`0b010_00010`, version field `010` = 2, "1.1 writes 2" per the codefile
facts), this reconstruction's fresh 1.3 compile reads `$C2`
(`0b110_00010`, version field `110` = 6, "1.3 writes 6"). This is not a
new gap -- it is finding 99c's own "`BINDER.CODE`...stamped version 2"
fact, now directly confirmed for `SET40COLS.CODE` too, at the exact bit
level finding 99c could only describe from the outside (whole bytes
changing 0 to `$42`) before any 1.3-compiled comparison existed to read
the version field against. **Both 1.1-vintage APPLE3 utilities now agree:
whatever wrote them onto the 1.3 disk was not `SYSTEM.COMPILER`,** and
this reconstruction cannot reach byte-identical for either file until
that process is understood -- restated from finding 99c, not resolved
by it.

## 113. `LIBRARY.CODE` -- 16 procedures reconstructed to a clean compile; a checkpoint, not a finished file

**STRONG INFERENCE.** `LIBRARY.CODE` ("Apple Pascal Librarian") turned out
much bigger than `docs/PLAN.md`'s "smallest pure-Pascal target left"
suggested -- 16 procedures nested four lex levels deep, a real heap-chained
buffer for copying segments between two library files, byte-order
swapping (the same machinery as `LIBMAP.text`'s), and per-segment
link-interface relaying. Read the whole disassembly and lift
(`analysis/utilities/LIBRARY-1.3-APPLE2.pcode.txt`/`.pas.txt`) before
writing anything, then wrote all 16 procedures at once and iterated
against the acceptance tier the same way `LIBMAP`'s `SHOWONE`/`GETWORD`
did (finding 111). `src/pascal/programs/1.3/LIBRARY.text`.

**Compiles clean under Apple's own `SYSTEM.COMPILER`**
(`acceptance/2026-08-27-library-compile/`), after five real fixes, three
of them new discoveries this session did not already know from `LIBMAP`/
`SET40COLS`:

- **`INTERFACE` is a reserved word, and the compiler enforces it even
  inside a plain `PROGRAM` that never declares a `UNIT`.** A procedure
  named `INTERFACEWRITEERR` failed with a syntax error at its own
  declaration, reproducible down to its first 8 significant characters
  (`INTERFAC`) via a bisected bare fast-tier probe. Renamed to
  `IFACEWERR`.
- **`NEW(p, n)` is not a "flex array, n elements" extension -- `n`
  selects a `CASE` variant by tag value.** `NEW(BUF, 256)` against a
  plain `ARRAY[0..0] OF INTEGER` base type failed error 158, no such
  variant in this record. The binary's own repeated `NEW(@G171, 256)`
  calls all use the same literal 256, which is the variant tag, not a
  computed count -- fixed by declaring `BUF`'s base type as a one-variant
  `RECORD CASE INTEGER OF 256: (WORDS: ARRAY[0..255] OF INTEGER) END`.
- **`FILLCHAR` takes three arguments -- `(START, COUNT, BYTE)` -- not
  four.** Read off the language reference directly this time rather than
  re-deriving from the p-code's own push count, which (like `MOVELEFT`
  and `BLOCKREAD` before it, findings 111/112) includes compiler-added
  words a naive read mistakes for source-level arguments.
- **`GOTOXY`, not `FGOTOXY`, is the standard procedure name** -- `FGOTOXY`
  is segment 0's own internal implementation (`CXP 0,29`), same
  relationship as `BLOCKREAD`/`FBLOCKIO` (finding 111). The manual states
  outright that `GOTOXY` "is included as one of the built-in procedures
  in the Apple Pascal language."
- **Procedure numbers follow declaration order, which follows lex
  nesting, and getting that wrong is silent until you check.** `COPYSLOT`
  and `GETCOMMAND` were first written as top-level siblings of
  `MAINLOOP` rather than declared inside it; the file still compiled
  clean, but every procedure number from `GETCOMMAND` on was shifted
  and the `params`/`data` comparison against Apple's binary caught it
  immediately once the codefile could be inspected. Moved both inside
  `MAINLOOP`'s own declaration part, `COPYSLOT` (with its own nested
  `COPYLINK`/`READLINK`/`COPYINTERFACE`/`IFACEWERR`) before
  `GETCOMMAND`, matching the binary's lex levels (2, 3, 4, 3, 4, 2)
  exactly.

**`NEEDSSWAP`'s inherited parameter type was wrong, caught by actually
calling it.** `LIBMAP.text`'s own `NEEDSSWAP(VAR P: SEGWORDS)` (`SEGWORDS
= ARRAY[0..15] OF INTEGER`) was reused verbatim on the assumption that
its `params=6/data=10` match proved it correct -- but that procedure has
never actually been called in `LIBMAP.text`, since `MAPLIBRARY` is still a
stub; the match was frame-size coincidence, not behavioral proof. The
first real call site (`MAINLOOP`'s own `NEEDSSWAP(INDICT.ADDRLEN)`) failed
error 142, illegal actual parameter -- passing `INDICT.ADDRLEN` (`ARRAY
[0..15] OF DIRENTRY`) to a `SEGWORDS`-typed `VAR` parameter is not
type-compatible, contrary to what finding 111's own prose about LIBMAP's
`MAPLIBRARY` comment assumed. Rereading the raw disassembly (both this
file's procedure 3 *and* LIBMAP's own procedure 4) confirms it: both use
`IXA 2`, a 2-word stride, indexing `DIRENTRY` pairs and reading only the
first field (`.ADDR`) of each -- not `SEGWORDS`'s 1-word stride at all.
Fixed here with a named `ADDRLENARR = ARRAY[0..15] OF DIRENTRY` type and
`W.ASWORD := P[I].ADDR`; **`LIBMAP.text`'s own copy still has the old,
wrong type**, flagged in this file's header rather than silently
diverging, since nothing there has hit the bug yet to force the fix.

**What's confirmed exact against Apple's shipped binary** (`params`/
`data` read off the compiled `LIBRARYT.CODE`'s own attribute table):
`SWAPBYTES` (2/4), `CHECKIO` (4/2), `GETINPUT` (0/86). **Close, a few
words short, not forced**: `NEEDSSWAP` (6/8 vs Apple's 6/10), `SWAPALL`
(2/8 vs 2/10), `MSGLINE` (2/2 vs 2/4), `MSGLINEINT` (4/2 vs 4/4),
`SHOWDICT` (4/4 vs 4/8) -- the same category of gap `LIBMAP`'s
`NEEDSSWAP`/`SWAPALL` started in before finding 111 closed them, not yet
repeated here.

**`MAINLOOP`'s own gap traced to a real mechanism, not fully
characterized.** `MAINLOOP` compiled to `data=82` against Apple's `data=8`
-- 74 words over, with no candidate local variable to explain it (the
procedure declares exactly `I: INTEGER` and `ABORT: BOOLEAN`, 2 words).
Bisected empirically: replacing the long `CONCAT`-built prompt string
(`MSG := CONCAT('Slot # to copy...', 'N(ew file...')`) with a one-character
literal dropped `data` from 82 to 4 -- a 78-word swing tied to the
*length of the string literal being assigned*, not to `CONCAT` itself
(confirmed with a standalone probe: a plain `MSG := '<77-char literal>'`,
no `CONCAT` at all, on a fresh one-procedure program, gave `data=80` on
the same 77-character message; a `STRING[79]` type for the target instead
of a bare `STRING` only dropped it to `data=80` from `82` -- underlying
mechanism unaffected by the target's own declared length). The compiled
instructions for the assignment are exactly `LAO`/`LSA '<literal>'`/`SAS
<n>` -- a single store, no loop, nothing that touches a local by
offset -- yet the attribute table's `data` field scales with the
literal's length anyway, which means the compiler is reserving
evaluation-stack space for the string constant as part of the
procedure's static frame, sized to the constant, even though no named
local ever uses it. **This does not resolve the discrepancy**: Apple's own real `MAINLOOP`
assigns this *exact* message text through `G90` the same way -- the
binary's own instructions at that point are the identical `LAO 90; LSA
'Slot # to copy...'; SAS 80` sequence, inside `MAINLOOP` itself (right
before its own `CLP 16` call into `GETCOMMAND`) -- and still reports only
`data=8`. Tried and ruled out: a `CONST` declaration instead of an inline
literal makes no difference (`data=82` either way, tested standalone).
So the reservation isn't about *where* the literal comes from
syntactically, and whatever lets Apple's real source assign this same
77-character message without paying for it is still unknown. Worth
returning to with a real disassembler-level comparison of a *minimal*
Apple-compiled program doing the identical assignment, rather than more
guessing at the source side.

**Deliberately left `(*STUB*)`**: the whole copy/link/interface machinery
-- `COPYSLOT` (procedure 11), `COPYLINK` (12), `READLINK` (13),
`COPYINTERFACE` (14), the outer body's own screen-cursor-redraw detail in
`MSGLINE`/`MSGLINEINT` (a `FIB`'s own hidden window-pointer field plus a
fixed offset, read directly as screen memory -- not yet worked out how to
write in ordinary Pascal). These are read off the disassembly in the
header comments but not yet instruction-verified or acceptance-tested,
the same honest-stub practice `LIBMAP.text` uses for `SHOWINFO`/
`SHOWREF`/`MAPLIBRARY`. `docs/PLAN.md`/`docs/DISKSET.md` reflect this as
in-progress, not done.

## 114. This project's own `SYSTEM.COMPILER` compiles `LIBRARY.text` byte-identically to Apple's

**VERIFIED BINARY FACT.** Finding 113 left `MAINLOOP`'s `data=82` vs
Apple's `data=8` gap traced to a real compiler mechanism (evaluation-stack
reservation scaling with a string literal's length) but not explained --
and left open whether that mechanism might be something this project's
own reconstructed `SYSTEM.COMPILER` gets subtly wrong, separate from
Apple's real one. Settled directly: swapped `acceptance/
2026-08-25-compiler-linked-v2/COMPLINK.CODE` (this project's own compiled
`SYSTEM.COMPILER`, already known to have all 15 real segments
byte-identical to Apple's shipped file, finding 107) onto `SYSHD:` in
place of Apple's shipped one, and used it to compile `LIBRARYT.TEXT` --
the same real, 16-procedure, 574-line source finding 113 used, not a
small calibration program.

**The output is byte-identical to Apple's compiler's own output on the
same input, all 3072 bytes, 0 differences** -- every procedure's `params`/
`data` matches exactly, including `MAINLOOP`'s own `data=82`. This is the
first time this project's reconstructed `SYSTEM.COMPILER` has compiled
something substantial end to end and been checked against Apple's real
compiler doing the identical job, rather than only being checked as a
static, uncompiled codefile (finding 107) or on the small GOTOXY
calibration programs (finding 49). It passes.

**This settles what finding 113 left open**: the `MAINLOOP` anomaly is
*not* a bug in this project's compiler reconstruction -- both compilers
agree on it exactly, so both are being equally faithful to whatever real
mechanism causes it. What remains unexplained is why Apple's *shipped
binary* doesn't pay this same cost for what reads as the identical
source-level operation (`MSG := '<77-char literal>'` before a `MSGLINE`
call) -- which now has to be a difference between `LIBRARY.text`'s
reconstruction and Apple's true original source, not a compiler quirk
worth chasing further on the compiler side.

**Update, same day -- bisected further with the (now-trusted) fast
emulator loop, ruled out several candidates, and found a genuine
reversal.** Standalone probes, one change at a time, against a plain
`PROGRAM` (not `LIBRARY.text` itself, to isolate the mechanism):

- Writing the same 77-character literal directly (`WRITELN('...')`, no
  variable at all) costs **nothing** -- `data=0`. The cost is specific to
  *materializing the literal as a string value* (assignment or
  parameter), not to loading it as an `LSA` operand for immediate
  `FWRITESTRING` consumption.
- Assigning it to a **local** variable inside a nested procedure costs
  the same as assigning to a **global** one -- both `data=82`. Not a
  scope effect.
- **`{$R-}` makes no difference** -- ruled out range-check code as the
  cause.
- **Passing the literal as a value parameter to a helper procedure that
  does the assignment moves the cost to the *caller* pushing the
  argument, not the callee receiving it** -- both ended up `data=82` in
  that test, but the caller's own frame carried it independent of the
  callee's.
- **A genuine reversal**: two sibling procedures, each assigning its own
  ~77-character literal to the same global, with the *outer* program
  body only calling both and then doing a plain `WRITELN(MSG)` --
  the cost landed entirely on the **outer body** (`data=82`), and
  *both* sibling procedures containing the actual assignments came back
  `data=0`. This contradicts the earlier local-variable test, where the
  procedure containing the assignment paid the cost directly. The
  difference between the two tests: in the local-variable test, the
  procedure containing the assignment *also* did the `WRITELN` itself;
  in this one, the assigning procedures do nothing else, and the
  `WRITELN` moved to the caller.

**Working hypothesis, not confirmed**: this reservation is not a
per-procedure local count at all, but something closer to a **shared,
program-wide string-evaluation scratch requirement**, attributed to
whichever procedure the compiler happens to charge it to based on
something about call structure or statement shape -- not simply "the
procedure whose source contains the assignment." That would explain both
`LIBRARY.text`'s real anomaly (`MAINLOOP` doesn't pay for its own
77-character assignment) and this session's reversal (a sibling
procedure's assignment can get charged to its caller instead) as the same
underlying mechanism, differing only in which procedure ends up "holding"
the shared requirement in each case. Not chased further this session --
diminishing returns past this point without instrumenting the compiler's
own code generator directly, which is out of scope for now. Recorded here
so the next attempt starts from "attribution, not magnitude" rather than
re-deriving these same five negative results.

## 115. `COPYSLOT` written for real -- `params`/`data` now exact, `ABORT` is not a parameter

**VERIFIED BINARY FACT.** `LIBRARY.text`'s `COPYSLOT` (procedure 11) was
still `(*STUB*)` (finding 113) -- the actual segment-copy logic, MARK/NEW/
RELEASE heap-chained buffer and all, had only been read off the
disassembly (`analysis/utilities/LIBRARY-1.3-APPLE2.pcode.txt`), not
written or tested. Wrote it, matching the disassembly instruction by
instruction:

- The disassembly takes `@G252[FROMSLOT*2w]` (the address of
  `INDICT.ADDRLEN[FROMSLOT]`) into a local and repeatedly dereferences it,
  bare `L6^` reading the first field (`ADDR`) and `L6^.f1` the second
  (`LENG`) -- the same `SIND0`-implies-first-field pattern LIBMAP's own
  `SHOWONE`/`GETWORD` already established for a `WITH`'s hidden
  implementation (finding 111), and `@` is not legal Apple Pascal (finding
  111's own error 400). Written as `WITH INDICT.ADDRLEN[FROMSLOT] DO`
  around the whole NUMBLOCKS-computation-through-COPYLINK-call block,
  reading `ADDR`/`LENG` as plain field names inside it.
- `MARK`/`RELEASE` take a `^INTEGER`, not a pointer to the buffer's own
  type -- confirmed directly from the language reference (`MARK(HEAPPTR)
  where HEAPPTR is of type ^INTEGER... called by reference`), not
  guessed.
- `FBLOCKIO` in the lift is the disassembler's own name for whichever of
  `BLOCKREAD`/`BLOCKWRITE` the `DOREAD` argument selects -- same relationship
  established for `FGOTOXY`/`GOTOXY` (finding 113) and `FBLOCKIO`/
  `BLOCKREAD`/`BLOCKWRITE` before it (finding: LIBRARY session,
  2026-08-27, the `WRITE(OUTFILE,...)` structural fix). Written as two
  separate calls, `BLOCKREAD` for the read (`DOREAD=TRUE` in the p-code)
  and `BLOCKWRITE` for the write.
- The p-code's `if not ((193 in 1))` guarding the `COPYLINK` call decodes
  as a genuine `SET` membership test once `193 = 128+64+1`, bits 0/6/7 --
  `SEGKIND` values `{0, 6, 7}`, which `SHOWSEGS`'s own case dispatch
  (finding 111) already names "completely linked", "linked intrinsic",
  and "data segment": exactly the three kinds with no separate link-info
  block left to relay. Written as `IF NOT (INDICT.SEGKIND[FROMSLOT] IN
  [0, 6, 7]) THEN COPYLINK(...)`.
- A real, working bug caught before testing: the `NEW`-page-allocation
  loop's own counter can't reuse `MAINLOOP`'s own `I` -- `MAINLOOP`'s
  outer body calls `COPYSLOT(I, I)` *inside* a `WHILE I <= 15 DO ...  I :=
  I + 1` loop, so if `COPYSLOT` clobbered the same `I` for its own
  purposes, the caller's `I := I + 1` after return would advance from
  `COPYSLOT`'s leftover value, not the loop's own. Given a dedicated local
  (`PAGE`) instead.

Compiled clean under Apple's real `SYSTEM.COMPILER`, first attempt (0
errors, 684 lines, `acceptance/2026-08-28-library-copyslot`). Extracted
and compared against Apple's shipped binary's own `params`/`data`:

`data=10` matched immediately, but `params=6` against Apple's `4` -- two
words too many, exactly the size of a `VAR ABORT: BOOLEAN` parameter
(address = 2 words on a 6502... actually a whole extra param slot). This
is the same signal as the disassembly's own `I1,3 := 0` at the top of the
procedure: that write goes directly into `MAINLOOP`'s frame at offset 3,
not into a parameter slot at all -- meaning `ABORT` was never a `COPYSLOT`
parameter in Apple's real source. `COPYSLOT` reads and writes `MAINLOOP`'s
own `ABORT` by lexical scoping, exactly the sharing pattern LIBMAP's
`GETWORD` uses against `SHOWONE`'s locals (finding 111). Dropped the `VAR
ABORT: BOOLEAN` parameter, changed the signature to `PROCEDURE
COPYSLOT(TOSLOT, FROMSLOT: INTEGER)`, updated all three call sites.
Recompiled: still 0 errors, and **`COPYSLOT` now matches Apple's binary
exactly on both `params=4` and `data=10`**.

`COPYLINK`/`COPYINTERFACE`/`READLINK` are still stubs -- `COPYLINK`'s real
`data=534` (a whole link-info buffer's worth) and `COPYINTERFACE`'s real
`data=6` are now known targets for the next pass, not yet written.
`READLINK`'s stub already matches (`data=0` both sides) coincidentally,
same caveat as `IFACEWERR` in finding 113 -- an empty body times out at
zero locals either way, not evidence the eventual real body will also
need none.

## 116. `COPYLINK`/`READLINK`/`COPYINTERFACE` written for real -- all four exact, first attempt

**VERIFIED BINARY FACT.** The last four stubbed procedures in
`LIBRARY.text` (finding 115 left `COPYLINK`/`READLINK`/`COPYINTERFACE`
untouched): written from the disassembly the same way, and all four
matched Apple's shipped binary exactly on `params`/`data` on the first
compile.

- **`COPYLINK(BLOCKNUM: INTEGER)`** relays a segment's link-interface
  information one 8-word entry at a time via its own nested `READLINK`,
  refilling a 32-entry, 256-word `LINKBLOCK` buffer from `INFILE` (relayed
  straight to `OUTFILE`) whenever it runs dry. The loop's own exit test
  reads an entry's word `[4]`: `32767` is the normal marker (anything else
  is `'bad link info'`, zeroed so the loop still ends cleanly), `0` ends
  the loop, and `24638` marks a "long" entry whose word `[6]` holds an
  extra-entries count -- `(count+7) DIV 8` further `READLINK` calls relay
  those before the outer loop re-checks. `BLOCKNUM` is `COPYLINK`'s own
  value parameter, advanced by `READLINK` directly (`BLOCKNUM := BLOCKNUM
  + 1`) -- a nested procedure freely reassigning its enclosing procedure's
  parameter by lexical scoping, same as `MAINLOOP`'s `ABORT` in finding
  115. An I/O error inside `READLINK` sets `COPYLINK`'s own `DONE`
  directly for the same reason.
- The disassembly's own `move(@I1,5, @I1,13[(32-I1,2)*8w], 8 words)` --
  copying one whole entry out of the block buffer at a computed offset --
  is just `ENTRY := BLOCKBUF[32 - ENTRIESLEFT]` once `BLOCKBUF` is typed
  as `ARRAY [0..31] OF LINKENTRY` rather than a flat word array: Standard
  Pascal's whole-array-element assignment, no `@`, no manual offset math.
- The disassembly's `if not ((32767 in 1))` / `if (24638 in 1)` are
  single-element `SET` membership tests -- `INN` with a one-element set
  and plain integer equality compile to identical bytecode, so these are
  written as `ENTRY[4] <> 32767` / `ENTRY[4] = 24638` rather than `IN`
  literals; `COPYSLOT`'s own `SEGKIND NOT IN [0, 6, 7]` (finding 115)
  stays a real `SET` because three elements can't be a coincidental
  equality.
- **`COPYINTERFACE(IFACEBLOCK: INTEGER)`** copies one segment's own
  interface block. `IFACEBLOCK <= 0` means there is none. The normal case
  computes the block count as `INDICT.ADDRLEN[FROMSLOT].ADDR -
  IFACEBLOCK` (the next segment's own start, minus where this one's
  interface begins); when that comes out negative -- the last segment in
  the file has no "next" start to measure against -- it falls back to
  reading one block at a time through the global scratch buffer `BUF`
  until `BLOCKREAD` itself fails, then checks the number of blocks read
  landed back on the original `IFACEBLOCK` value as a consistency check
  before proceeding.
- **The `data=6` match depended on *not* declaring `COPYINTERFACE` its own
  heap-mark pointer.** The disassembly's `MARK(@I1,4)` writes into the
  *parent*'s (`COPYSLOT`'s) frame at offset 4 -- exactly where `COPYSLOT`'s
  own `MARKPTR` local already lives (finding 115's declaration order).
  `COPYINTERFACE` reuses that same variable by name, directly, for its own
  `MARK`/`NEW`/`RELEASE` cycle; it is always called before `COPYSLOT`'s
  own cycle begins, so the two never overlap in time. First attempt
  wrote it this way, matched immediately -- no data-size mismatch to
  chase.

With this, every one of `LIBRARY.text`'s 16 procedures has either an exact
or a documented-and-explained close/anomalous frame-size match; nothing
is left as an unwritten `(*STUB*)`. What remains open is finding 114's
`MAINLOOP` `data=82` vs Apple's `data=8` anomaly (confirmed not a
compiler-reconstruction bug, mechanism still not fully attributed) and
the handful of "close, a few words short" procedures documented in
finding 113 (`NEEDSSWAP`/`SWAPALL`/`MSGLINE`/`MSGLINEINT`/`SHOWDICT`).

## 117. `BINDER.text` reconstructed -- five of six procedures exact, first new file

**VERIFIED BINARY FACT.** `BINDER.CODE` (finding 99c: a 1.1-vintage
binary Apple's 1.3 disk carries unchanged, confirmed to still run under
1.3, so in scope even though never recompiled) had no shipped source on
any evidence disk. Written from scratch from `analysis/utilities/
BINDER-1.3-APPLE3.pcode.txt`/`.pas.txt`, the same lift-and-rewrite
treatment already used for `SET40COLS.text`/`LIBRARY.text`.

What it does: prompts for a codefile containing a native GOTOXY
(required to be procedure #2), extracts just that procedure's own bytes,
and patches them into a fresh copy of `SYSTEM.PASCAL`'s own segment #15
-- shifting that segment's own link information and every later
segment's file position to make room -- writing the result out as
`NEW.PASCAL`.

- **A genuinely undocumented block-size fact, found from offset
  arithmetic, not a guess.** Two globals (`G6`, the GOTOXY file's own
  segment dictionary, and `G518`, `SYSTEM.PASCAL`'s) are each populated
  by exactly one `BLOCKREAD` of one 512-byte block, and only their first
  32 words (`ADDRLEN`, an `ARRAY[0..15] OF DIRENTRY`) are ever indexed by
  this file's own six procedures. But the *offset gap* from `G6` to
  `G518`, and separately from `G518` to the next real global (`G1030`),
  is 512 words each -- not 256. Declaring each as a 512-word block
  (`ADDRLEN` plus 480 honestly-unread words) is what makes procedure 1's
  own global layout land on the right absolute offsets for every
  subsequent variable; declaring them at the 256-word size LIBRARY.text's
  own `SEGDICTREC` uses leaves a mystery 256-word gap unaccounted for
  twice over. Unlike `SEGDICTREC` (confirmed 256 words end to end by its
  own field layout in finding 113), nothing in `BINDER.text` gives
  evidence for what those extra 480 words per block actually hold --
  only that the space must be reserved.
- **`G4`/`G5` (the patch buffer and its saved starting page) are
  addressed exclusively byte-by-byte** -- `STB`/`LDB` throughout, never a
  whole-word store, including the little-endian two-byte read that
  becomes `WORDAT` and the direct procedure-kind pokes
  (`PATCH^[PATCHSIZE] := CHR(29)`). Declared `^PACKED ARRAY [0..511] OF
  CHAR`, matching the language reference's own wording for
  `MOVELEFT`/`MOVERIGHT` ("subarrays of the same PACKED ARRAY OF CHAR"),
  not the word-view `BIGBUF` pattern `LIBRARY.text` used for its own
  chained buffer.
- **`MOVELEFT`/`MOVERIGHT`'s raw p-code arguments split each reference
  parameter into an (address, offset) pair** -- five raw operands for a
  three-parameter call, the same trap already known for
  `BLOCKREAD`/`FILLCHAR` (finding 113). `MOVELEFT(PATCH^[PATCHBASE],
  PATCH^[0], PATCHSIZE + 2)` is the real three-argument source form.
- **A value `STRING` parameter costs its own 41-word copy-on-entry
  local, invisibly.** `CHECKERR(MSG: STRING; FAILED: BOOLEAN)`'s real
  `data=84` is exactly one such copy (41 words) plus one `CHAR` local for
  the space-bar wait loop. The disassembly's own `L3 := L1` is *that*
  compiler-generated copy happening, not a second, separately-declared
  local -- writing an explicit extra `TEXT: STRING` and copying `MSG`
  into it doubled `data` to 166, wrongly. A first attempt at fixing this
  by declaring `MSG` as `VAR STRING` instead failed for a more basic
  reason: every call site passes a string *literal*, and a `VAR`
  parameter cannot bind to one (error 154).
- **The same "extra explicit local" mistake, same fix, in
  `READGOTOXY`.** The disassembly's own local `L86` is used first as a
  `STRING` (the `.CODE`-appended retry filename) and, at first glance,
  looked like it might need a second declared local for that purpose.
  Declaring a separate `ALTNAME: STRING[80]` produced `data=338` against
  Apple's `256` -- 41 words over, the same one-extra-`STRING[80]`
  signature as `CHECKERR`'s bug. Fixed by reassigning `NAME` itself
  (`NAME := CONCAT(NAME, '.CODE')`) instead of introducing a second
  local; `READGOTOXY` matched exactly immediately after.
- **`WRITESEG`/`LOADSEG` each needed a `WITH DICT.ADDRLEN[N] DO`
  specifically to reproduce their own real `data`, not just for style.**
  Without it, `WRITESEG` was short exactly one word (`data=2` against
  Apple's `4`); wrapping the two field writes in `WITH` supplied the
  missing word immediately, matching `LOADSEG`'s already-`WITH`-based
  form exactly (`data=4` from the first attempt). A `WITH`'s own hidden
  address genuinely costs a real word in a *local procedure frame* --
  confirmed by this pair, not assumed.
- **That same device does not reproduce the outer body's own missing
  word.** The whole file compiles clean and five of six procedures
  (`CHECKERR`, `WORDAT`, `READGOTOXY`, `WRITESEG`, `LOADSEG`) match
  Apple's shipped binary exactly on both `params` and `data`. The outer
  program body itself (`data=2236` here, Apple's own `2238`) is short by
  exactly one word out of 1119 declared -- wrapping its own four
  `DICT.ADDRLEN[0]` references in a matching `WITH` (mirroring the
  `WRITESEG`/`LOADSEG` fix exactly) changed nothing, so whatever holds
  Apple's one extra *global* word is not the same mechanism as a local
  procedure frame's `WITH` temp. `@` is not legal Apple Pascal (finding
  111), ruling out a stray pointer variable as the explanation too. Left
  as a documented, honest gap -- one word among 1119, not forced.

Two identifier bugs caught by the fast/acceptance loop, both quick:
`PATCHENDBLK` collided with `PATCHEND` at 8 significant characters
(error 101, the exact `ONEDRIVE`/`ONEDRIV` gotcha CLAUDE.md already
documents) -- renamed to `ENDBLOCKS`. `NEW(PATCH, 256)` on a plain
`PACKED ARRAY OF CHAR` (not a `CASE` variant record) gave error 158, the
same "`n` selects a variant tag, not a size" trap finding 113 already
found for `LIBRARY.text`'s `BIGBUF` -- `BYTEBUF` here needs no variant at
all since it is already a fixed-size type, so the fix was simply `NEW
(PATCH)` with no second argument, not adding a variant.

## 118. `BINDER.text`'s SEGNUM loop -- one real `WITH`, and a dead end chased to ground on the outer body's own one-word gap

*Confidence: VERIFIED BINARY FACT for the `WITH` structure and the units
reconciliation; STRONG INFERENCE that the outer body's remaining one-word
gap has no candidate left in the file-variable-sizing rules. Acceptance
run `2026-08-28-binder-segnum-with`.*

Asked to "open the `BINDER.text` 1-word gap in the compiler disassembly" --
i.e. use `SYSTEM.COMPILER`'s own reconstructed source, not just guesswork,
to make progress on finding 117's documented `4/2236` vs Apple's `4/2238`.

### 118a. The real structural fix

`BINDER`'s own disassembly, outer body, the `SEGNUM := 1; WHILE SEGNUM <=
14 DO ...` loop:

```
LAO 518; LDO 1036; IXA 2; SRO 1121     { G1121 := @DICT.ADDRLEN[SEGNUM] }
LDO 1036; CLP 6                        { LOADSEG(SEGNUM) }
LDO 1121; SIND 1                       { push .LENG through G1121 }
LDO 1036; CLP 5                        { WRITESEG(SEGNUM, LENG) }
```

`G1121`'s address is computed **once** and reused for both calls -- Apple's
real source is `WITH DICT.ADDRLEN[SEGNUM] DO BEGIN LOADSEG(SEGNUM);
WRITESEG(SEGNUM, LENG) END`, not the inline `DICT.ADDRLEN[SEGNUM].LENG`
this file had. Fixed in `src/pascal/programs/1.3/BINDER.text`; compiled
clean, `4/2236` unchanged (the compiler was already reusing an existing
scratch global for the inline form, so this word was never the missing
one) and no other procedure regressed. Kept anyway: it is the byte-for-byte
faithful structure regardless of frame size, matching `WRITESEG`/
`LOADSEG`'s own internal `WITH` pattern one level up.

### 118b. The units confusion, and why it looked like an 1100-word gap

Manually summing `BINDER`'s declared globals (`RESERVE`..`OSFILE`) gives
~1117-1120 **words**. The codefile's own `data` field reads `2236`/`2238`
directly off the jtab with no conversion (`codefile.py`'s `_w(raw, jtab -
8)`) -- these values are already established elsewhere in this project as
matching a declared word count doubled (`COPYLINK`'s `data=534` against a
267-word `LINKBLOCK`+locals sum, `CHECKERR`'s `data=84` against a 42-word
copy-on-entry+`KEY`). Read naively as words instead of the doubled unit,
`2236`/`2238` looks like it needs ~1118 more words than anything declared
-- a false alarm from applying the wrong unit, not a real second block of
globals. Once corrected, `2238`/`2` = `1119` words lines up with the
declared total almost exactly, and the real gap is the one word finding
117 already documented, not eleven hundred.

### 118c. What was ruled out chasing it anyway

Before catching 118b, tested and killed off:

* **The FINIT "window" address (`VADDR+300`) enlarging the frame.**
  `READGOTOXY`'s own local `GTXFILE` computes `LLA 305` (its own
  `40`-word offset `5` plus `FILESIZE=300`) right at entry, yet the whole
  procedure's real frame is only `256` -- smaller than the window address
  itself. Confirms finding 43's "harmless, never dereferenced" holds at
  the *local* procedure-frame level too, not just II.0's original global
  case: the window is truly never real, full stop, regardless of scope.
* **`SYSTEM.COMPILER`'s own reconstructed `DECLARAT.text`** (already
  acceptance-verified byte-identical, finding 90/107) carries the exact
  same `FILESIZE = 300; NILFILESIZE = 40` sizing rule as II.0's
  `decpart.a.text` and `compglbls.text` -- no 1.3-specific wrinkle to the
  rule exists to explain a residual word this way.
* **A second hidden local for the `READGOTOXY` `.CODE`-retry `CONCAT`.**
  Already ruled out in finding 117 (the `NAME`-reuse fix); reconfirmed
  here by walking every `LLA`/`LDL`/`STL`/`SLDL` offset the procedure
  ever touches (`1`-`4`, `5`, `45`, `86`) -- nothing past the already-
  accounted-for `WITH`-temp at `86` is ever referenced.

No candidate for the outer body's missing word remains open. Left
documented, not forced, per finding 117.

## 119. `CODEINSEG` is global, not per-segment -- narrows finding 105a, doesn't close it

*Confidence: VERIFIED SOURCE FACT for the mechanism (all in already-verified
`PASCALCO.text`/`BODY3.text`/`COMPINIT.text`); STRONG INFERENCE for what it
predicts about the host segment; still open where it conflicts with
105a-i's own emulator test.*

Prompted by a check of whether the standard UCSD `REWRITE`/`CLOSE`/
`CLOSE(F,LOCK)` directory-space-trimming rule (a real mechanism, but for a
*volume's* `FILE` variables) could explain finding 105a's extra 512-byte
`PASCALSY` segment. It cannot: `PASCALCO.text`'s own `WRITECODE`/
`FINISHSEG` write segment code via raw `BLOCKWRITE(USERINFO.WORKCODE^,
DISKBUF, 1, CURBLK)` against a preallocated block-numbered scratch area,
never through `REWRITE`/`CLOSE` on a typed file. Wrong layer entirely --
worth ruling out explicitly since it's a plausible-sounding wrong answer.

Checking anyway turned up a real, previously uncited mechanism. `BLOCK`
calls `FINISHSEG` from two sites, not the one finding 105a's writeup
examined:

* **Line 845**, unconditional, after the lexical stack (`TOS`) is fully
  unwound -- the only one 105a discussed.
* **Line 815**, `IF CODEINSEG THEN FINISHSEG`, inside the loop, run once
  per lexical level as *each* level (including the outermost host, since
  `(*$U-*) PROGRAM` is itself `ISSEGMENT`, finding 60) finishes and pops
  off `TOS`.

`CODEINSEG` is not scoped per segment. `COMPINIT.text:334` clears it once
at the start of compilation; `BODY3.text:131-132` sets it true the moment
*any* procedure body anywhere emits its first instruction; `FINISHSEG`
itself clears it back to false as the last thing it does
(`PASCALCO.text:733`). It is a single global "has any code been generated
since the last flush" flag, not "does this segment have code."

### 119a. What this predicts for the host

The host's own `BEGIN END` is already established to compile to genuinely
zero bytes (`enter_ic = exit_ic`, finding 105a). If nothing else sets
`CODEINSEG` true between the last real segment's own `FINISHSEG` (which
resets it) and the host's own turn to pop off `TOS`, line 815 is skipped
for the host, `SEGTABLE[...].CODELENG` for slot 0 is never written, and it
stays at its initialised zero -- exactly Apple's shipped shape
(`addr=0000, len=0000`, name blank).

### 119b. Where it stops explaining things

Both `105a-i` test programs (`TESTHOST`/the headerless variant), run
through the *real* 1.3 compiler, have the identical shape -- one
`(*$U-*) PROGRAM`, one nested `SEGMENT PROCEDURE INNER` with its own
nested ordinary `PROCEDURE FOO`, outer body `BEGIN END` -- and came out
with a **non-empty** segment 0 (`NEXTPROC-1=1`), not the empty shape
119a predicts. `INNER`'s own body (`BEGIN FOO END`) is real code (a
`CXP`), so `CODEINSEG` legitimately goes true during `INNER`'s compile;
`INNER` is itself `ISSEGMENT`, so its own line-815 call should fire and
reset `CODEINSEG` back to false via its own `FINISHSEG` before the outer
level's turn -- predicting the same empty-segment-0 outcome as Apple's
real file, not the non-empty one actually observed.

Something between `INNER` finishing and the host's own pop sets
`CODEINSEG` true again, and it has not been identified -- a candidate
worth checking directly against the binary rather than guessed at
further: whether parsing the `SEGMENT PROCEDURE INNER(...)` *header*
itself (segment-table allocation, `NEWSEG`-adjacent bookkeeping) emits
anything, independent of `INNER`'s own body. Left open, narrower than
before finding 119 but not closed.

## 120. `LIBMAP.text` -- `SHOWREF`, `MAPLIBRARY`, and the outer block written for real; `NEEDSSWAP`'s wrong parameter type finally forced

*Confidence: VERIFIED BINARY FACT for the frame sizes and the outer
block's exact match; STRONG INFERENCE for `MAPLIBRARY`'s '.TEXT'-suffix
character scan, still not reproduced. Acceptance run
`2026-08-28-libmap-showref-maplibrary`.*

Picked up where the LIBMAP session (finding 111) left off: `SHOWINFO`,
`SHOWREF`, `MAPLIBRARY` and the outer block were the last stubs in the
file. `SHOWREF` and the outer block are now exact or effectively exact;
`MAPLIBRARY` closed almost the whole way; `SHOWINFO` (1042 words of
locals, the single largest procedure in the file) remains for a later
session.

### 120a. `SHOWREF` -- one word short, same shape as this file's known gaps

Straightforward once written: `IF LISTREFS THEN` prints the label,
`CASE ENTRY.RVAL1 OF` the three reference-size words, then `(N times)`/
`(once)` off `ENTRY.RVAL2`, then reads and discards `(RVAL2+7) DIV 8`
more raw entries through `GETWORD`, all off `ENTRY` -- `SHOWONE`'s own
local, read by the same nested-scoping `GETWORD` already established.
`params=2/data=102` against Apple's `2/104`, one word short -- documented,
not forced, the same flavor of small gap `NEEDSSWAP`/`SWAPALL` already
carry in this file.

### 120b. `NEEDSSWAP`'s parameter type -- flagged in finding 113, now forced by a real call site

`MAPLIBRARY`'s own disassembly calls it as `NEEDSSWAP(SEGDICT.ADDRLEN)` --
the exact call shape `LIBRARY.text` already hit and fixed (its own
`NEEDSSWAP(INDICT.ADDRLEN)`, verified exact on `params=6/data=10`).
Ported the identical fix here: `ADDRLENARR = ARRAY [0..15] OF DIRENTRY`
declared separately so a `VAR` parameter can bind to `SEGDICTREC.ADDRLEN`
directly (name equivalence, not structural -- an inline-typed field
won't bind on its own), `SEGDICTREC.ADDRLEN` itself now declared `OF
ADDRLENARR`, `NEEDSSWAP`'s body reading `P[I].ADDR` instead of `P[I]`.
Confirms finding 113's own prediction exactly. `SWAPALL` needed no
change -- its own call site here is a single `LAO 3` with no extra
pushes, matching its existing `VAR D: SEGDICTREC` signature as-is.

### 120c. `MAPLIBRARY` -- `INSERT`, not `CONCAT`, is what closes the gap

First attempt used `LIBNAME := CONCAT(LIBNAME, '.CODE')` for the
`.CODE`-retry suffix, mirroring `BINDER.text`'s own successful fix for
the identical-looking problem. It compiled clean but landed at
`data=254` against Apple's `172` -- 41 words over, and disassembling this
project's *own* compiled output (not just reading prose about Apple's)
showed exactly why: `CONCAT` here compiles through a hidden 41-word
result temp (`SCONCAT` into a scratch local, then `SAS` to assign it into
`LIBNAME`), where the real disassembly's own call is `SINSERT` --
`INSERT('.CODE', LIBNAME, LENGTH(LIBNAME)+1)`, which modifies `LIBNAME`
in place and needs no second buffer. `CONCAT`-with-hidden-temp and
`INSERT`-in-place have the same *effect* and are not the same
*instructions* -- `BINDER.text`'s own working `CONCAT` fix does not mean
`CONCAT` is free in general, only that its own call site happened to
compile that way. Fixed both the `.CODE` and `.TEXT` suffix sites to
`INSERT`; declaring `MAPNAME` before `LIBNAME` (matching the real local
offsets the disassembly showed, reversed from a first guess) and reusing
`TEMP1`/`TEMP2` for the validation loop's counters instead of fresh
locals closed the rest: `params=0/data=170` against Apple's `0/172`, one
word short, documented not forced. The disassembly's own `.TEXT`-suffix
logic also scans the name character by character for something this
rewrite doesn't reproduce (still not understood what for) -- confirmed
it isn't the source of the word, since removing the whole INSERT-based
approximation of it changes nothing about the remaining gap's size.

### 120d. The outer block -- exact, and `USINGLIB` renamed `LISTLINK`

`params=4/data=1510`, matching Apple's binary exactly on the first
attempt: `FINIT` for both file variables is automatic (no explicit call
needed, same rule finding 91 already established), a
`WHILE TEMP2<=TEMP1 DO` loop initializes `VERSTRS` to `'unknown'`
reusing the same two globals `TEMP1`/`TEMP2` the header comment already
named for exactly this, both string tables are filled in by literal
assignment, and the whole thing is one unconditional
`REPEAT MAPLIBRARY; LISTMAP:=FALSE; SHOWSEGS UNTIL FALSE` -- the
binary's own loop condition is a literal constant, and the only way out
is `MAPLIBRARY`'s own `EXIT(PROGRAM)` on an empty library name.

Along the way: `G602`, carried since finding 111 as `USINGLIB` on "no
better evidence than the fourth boolean that made sense," turns out to
be set by the prompt `'list linker info table (Y/N)? '`, not anything
library-related -- renamed `LISTLINK` throughout (`SHOWSEGS`/`SHOWONE`
included, both already-verified-exact procedures whose own instructions
did not change, only the identifier).

## 121. `SHOWINFO` written for real -- exact on the first attempt, the largest procedure in the file closes the whole one

*Confidence: VERIFIED BINARY FACT. Acceptance run
`2026-08-28-libmap-showinfo`.*

`LIBMAP.text`'s last stub, and its biggest procedure by far -- 1042 bytes
of locals against `SHOWONE`'s own 556, the next largest. `params=6/
data=1042`, matching Apple's binary exactly on the first attempt. Every
procedure in the file now has a real body; nothing left `(*STUB*)`.

### 121a. What it does

Prints a library unit's own interface text, given its starting block
(`BLK`; zero or negative means "no interface," an immediate `FALSE` via
`EXIT(SHOWINFO)`). Reads two blocks (1024 bytes) at a time through
`BLOCKREAD`, scanning each chunk byte by byte: `CHR(16)` skips two bytes
outright, a letter starts a run handed to `IDSEARCH` (finding 109's own
native routine, reused here purely to walk past one identifier -- its
result, `SY = 52`, marks some reserved word that ends the scan early,
not yet decoded further than that), and a bare `CHR(13)` immediately
followed by `CHR(0)` marks the interface's own true end. Whichever way
the inner scan stops, `NAMESTART` holds how many characters to print --
UCSD's own `WRITE(packed-array : N)` idiom -- and the outer `REPEAT`
reads another two blocks (`BLK` advanced by 2 each time) until done.

### 121b. `IDSEARCH`'s cursor is seven words, not one or two

The header comment inherited from finding 111 claimed `SHOWINFO` was
"called with `(BLK, 0, 0)`" -- wrong; `SHOWSEGS`'s own already-verified-
exact code (finding 111) calls it with a single argument, and that
settles it now that a real body exists to check the call site against.

The real find: `IDSEARCH(VAR IDREC, ID)`'s own declaration
(`PASCALCO.text`, `IDSEARCH(SYMCURSOR, SYMBUFP^)`) reads like a small
cursor, but the disassembly's own local offsets prove otherwise. The
procedure's own code only ever touches two words of whatever it passes
as `IDREC` -- one before the call (the scan position) and one after
(`SY`) -- but the next local `SHOWINFO` declares (`NAMESTART`) doesn't
land until five words later. Declaring `IDREC` as a 7-word record
(`IDX`, `SY`, and a 5-word `SPARE` this procedure never reads, the same
unread-tail shape `REFENTRY` already has, finding 111) closes the gap
exactly: `521` declared words (`IDCURSOR`'s 7 + `NAMESTART`'s 1 +
`DONE`'s 1 + `RBUF`'s 512, one 1024-byte chunk) is precisely half of
Apple's `data=1042` -- the same words-to-bytes relationship this file's
own `CHECKERR`-style value-parameter copies and `COPYLINK`'s own
256-word block already established elsewhere in this project. Matched
on the first compile, no iteration needed once the record size was
right.

### 121c. `LIBMAP.text` is now feature-complete

Every one of the file's twelve procedures (eleven p-code, one native)
now has a real, acceptance-tier-compiled body. Exact matches: the outer
block, `SWAPBYTES`, `VALIDNAME`, `SHOWSEGS`, `SHOWONE`, `GETWORD`,
`SHOWINFO`. One word short each, documented not forced: `NEEDSSWAP` (two
words), `SWAPALL`, `SHOWREF`, `MAPLIBRARY`. Nothing left unread or
stubbed -- the open threads are the small per-procedure word gaps
already documented (120a/120b) and the still-undecoded `SY=52`/
identifier-character-set specifics in `SHOWINFO` itself, not missing
structure.

## 122. `SETUP.CODE` -- reconstruction started, 54 procedures across 12 segments compile clean first attempt

*Confidence: VERIFIED BINARY FACT for the frame-size matches and the
structural discovery; STRONG INFERENCE for the field-tree's own
semantics (BST shape, sentinel node) since nothing calls into it yet.
Acceptance run `2026-08-28-setup-first-compile`.*

Started `SETUP.CODE` (`src/pascal/programs/1.3/SETUP.text`) -- the
hardware/terminal configuration utility, `docs/PLAN.md` item 5,
byte-identical between 1.1 and 1.3 with no shipped source on either
release's evidence disk. A large file: 54 procedures, 12 codefile
segments (`PASCALSY`, the main `SETUP` segment with 26 procedures,
eight trivial `NUMBERn` placeholder segments, `INITS` with 9, `TEACHSET`
with 10). This session's scope: the skeleton, the menu loop, the
field-tree/BST machinery (`SETUP2`/`SETUP3`/`SETUP4`), the two read-key
utilities (`SETUP5`/`SETUP6`), and the whole `INITS` startup segment.
`SETUP7` onward (the actual value-editing screens) and `TEACHSET`
(tutorial text) are placeholder stubs for a later session.

### 122a. What it does

Builds a binary search tree of named fields over `SYSTEM.MISCINFO` (a
96-word/192-byte terminal-profile record this program writes --
`DISKSET.md`'s own "not started" data file, and this is the way in to
it). Each field's name maps to an `(OFS, BIT, BITS)` triple describing
where its value lives in that record; `INITS` builds the whole tree
once at startup ("HAS CLOCK" at word 29 bit 0, "SCREEN HEIGHT" at word
37, and so on -- `INITS8`/`INITS9`'s own long call sequences) plus two
small linked lists of named values (`TRUE`/`FALSE`, and two more groups
for 8/16-bit prefixed-key fields) a value gets looked up against when
the user types a new one. What `OFS`/`BIT`/`BITS` actually mean as bit
offsets into `MISCINFO` is not decoded -- nothing this session wrote
needs to interpret them, only carry them.

### 122b. The real program structure: `PASCALSYSTEM` wraps `SETUP`, not the other way round

A first reading of the disassembly (`lex=0` on what looked like the
outer program body) suggested `(*$U-*) PROGRAM SETUP; ... BEGIN <menu
loop> END.` directly. That shape compiles, but `EXIT(PROGRAM)` inside a
nested `CHECKERR`-style procedure fails error 125 ("error in type of
standard procedure parameter"), and the seemingly obvious fix,
`EXIT(SETUP)`, fails error 104 (undeclared) -- the program's own name
is not usable as an `EXIT` target from within its own nested
procedures the way the language reference's `EXIT(programname)` form
implies it should be, at least not under `(*$U-*)`.

`SYSTEM.COMPILER`'s own declaration skeleton
(`analysis/reconstruction/skeleton-1.3.text`) has the real shape, and
it was sitting there the whole time: `(*$U-*) PROGRAM PASCALSYSTEM;`
wraps `SEGMENT PROCEDURE PASCALCOMPILER(CODEP, SYMBUFP)`, and it is
that *inner* segment procedure's own `EXIT(PASCALCOMPILER)` (used
inside `BLOCK`, in `PASCALCO.text`) that works -- not the outer
program. `PASCALCOMPILER`'s own two parameters are the OS's `(NIL,
NIL)` invocation convention for whatever it loads as segment 1
(finding 59); the outer `PASCALSYSTEM` itself does nothing but declare
the OS's own globals and hand off, `BEGIN END.`, trivial.

Ported the identical shape onto `SETUP.text`: `PROGRAM PASCALSYSTEM`
outermost with a trivial `BEGIN END.`; `SEGMENT PROCEDURE SETUP(P1,
P2: ANYPTR)` one level in (the same two-word `(NIL,NIL)` convention,
unused, matching the "hidden bootstrap params" already seen on
`BINDER.text`'s own outer body at `params=4`) holding everything else
and the real menu-loop body. `EXIT(SETUP)` inside `SETUP2` now resolves
exactly the way `EXIT(PASCALCOMPILER)` does.

PASCALSY's own real content here (`XIT` plus one leftover byte) against
`SYSTEM.COMPILER`'s empty/absent dictionary entry (finding 105a/119) is
an open parallel worth another look someday -- both outer `PASCALSYSTEM`
bodies are the identical trivial `BEGIN END.` shape, so whatever makes
one produce a real 16-byte segment and the other nothing at all is
still unexplained by this session's own work.

### 122c. `SETUP2`/`SETUP3` calling `SETUP4` before it's declared -- a real FORWARD, and where it goes

`SETUP3` (the BST search) calls `SETUP4` (the name-trim utility), but
`SETUP4` is Apple's own procedure 4, one *after* `SETUP3` -- meaning
naively declaring them in Apple's own numeric order gives an
undeclared-identifier error. Fixed the way `PASCALCO.text` already
relies on throughout (finding 61's rule: UCSD numbers a procedure where
its *body* is compiled, not where a `FORWARD` stub sits): `SETUP4` gets
a `FORWARD` ahead of `SETUP3`'s own declaration, with its real body
kept in Apple's own physical order after `SETUP3`'s -- so it still
becomes procedure 4, unaffected by the earlier stub.

### 122d. Declaring a `SEGMENT PROCEDURE` after a real procedure body is error 399, and the fix is declaration order, not code

Declaring `NUMBER2` right after `SETUP26`'s own real body hit error 399
-- the same `CODEINSEG` restriction finding 119 already found and named
("code before a SEGMENT PROCEDURE is error 399," `skeleton-1.3.text`'s
own comment): a value-`STRING`-copying, fully real `SETUP26` body just
having compiled leaves `CODEINSEG` true, and nothing had reset it via a
`SEGMENT PROCEDURE`'s own `FINISHSEG` yet. Since a `SEGMENT PROCEDURE`
declared inside another segment procedure does **not** consume one of
the enclosing segment's own procedure-number slots (`SETUP`'s dictionary
entry shows exactly 26 procedures, 1 outer body + `SETUP2`..`SETUP26`,
with `NUMBER2`..`NUMBER9`/`INITS`/`TEACHSET` entirely separate,
independently-numbered segments), the fix was purely about *where* to
place them textually: every `SEGMENT PROCEDURE` moved to right after
`SETUP`'s own `VAR` block, before any of `SETUP2`..`SETUP26`'s real
bodies exist to trip `CODEINSEG` -- with `SETUP2`/`SETUP3`/`SETUP4`
(the three `INITS` itself needs) `FORWARD`-declared ahead of them for
the same reason as 122c.

### 122e. `NEW(p, n)` is the same variant-tag trap again

`NEW(NEWNODE, 47)`/`NEW(NEWNODE, 43)` on plain (non-variant) `RECORD`
types hit error 158, the identical mistake finding 113 already named
for `LIBRARY.text`'s `BIGBUF`: `n` selects a `CASE` variant tag, not a
size. Neither `FIELDNODE` nor `VALNODE` is a variant record, so every
site needed plain `NEW(x)` with no second argument.

### 122f. What's confirmed exact, and what's a known, documented gap

Acceptance-tier compiled clean, 0 errors, first attempt after the fixes
above. `params`/`data` against Apple's own binary: the `SETUP` segment's
own outer body **exact** (`4/352`), `SETUP2` **exact** (`4/82`), `SETUP3`
**exact** (`6/164`), all eight of `NUMBER2`..`NUMBER9` **exact** (`0/0`).
`SETUP4` is a real, understood miss (`4/82` here against `4/2` --
`DELETE`'s own value-`STRING` parameter costs the usual ~41-word hidden
copy-on-entry the binary's byte-level `SCAN`/`MOVELEFT` approach never
pays; rewriting to match is the natural next step). `SETUP5`/`SETUP6`
were re-checked directly against Apple's own dictionary rather than
carried forward from memory and turned out already exact at `4/0` each
-- see 123 below, which corrects this paragraph. `INITS`'s own nine
procedures compile and run in shape but have not yet been checked one
by one against Apple's own per-procedure frame sizes. `SETUP7` onward
and `TEACHSET` remain placeholder stubs.

## 123. `SETUP.text` -- `SETUP4`'s real gap was `VAR` vs value on `SRC`, and `SETUP5`/`SETUP6` were already exact

122f's own claim that `SETUP5`/`SETUP6` were `4/0` against Apple's
`0/0` doesn't survive a direct check: reading `SETUP.CODE`'s own
dictionary off `evidence/disks/.../APPLE3...dsk` with `CodeFile` gives
procedure 5 (`SETUP5`) `params=4/data=0` and procedure 6 (`SETUP6`)
`params=4/data=0` -- exactly what this project's own `SETUP.text`
already compiled to. There never was a gap; 122f's summary was wrong,
not the source.

`SETUP4` (`analysis/utilities/SETUP-1.3-APPLE3.pcode.txt`, procedure 4)
opens with `SLDL 2` / `SLDL 1` / `SAS 80` -- a string-assign taking two
*addresses* off the stack, both loaded via `SLDL` (a parameter-list
load), and the rest of the procedure keeps reading/writing through
`SLDL 2` (`LDB`/`STB`, byte-level scan-and-shift) the same way. A
value-`STRING` parameter's own hidden copy is never addressed this way
-- only a `VAR` parameter's address is loaded straight off the parameter
list and dereferenced repeatedly like this. So `SRC`, not just `DEST`,
is `VAR` in Apple's real declaration:
`PROCEDURE SETUP4(VAR DEST, SRC: STRING)`. Every call site (`SETUP4(TRIMMED,
CUR^.NAME)`, `SETUP4(TRIMMED, PARENT^.NAME)`, `SETUP4(TRIMMED, NAME)`
where `NAME` is itself `INITS6`'s own value parameter) passes an lvalue,
so the change costs nothing at any call site.

Changing `SRC: STRING` to `VAR SRC: STRING` (keeping the existing
`DELETE`-loop trim, not yet rewritten to the binary's own byte-level
`SCAN`/`MOVELEFT` shape) took the frame from `4/82` to `4/0` against
Apple's `4/2` -- the ~41-word hidden-copy miss is gone entirely; what's
left is a single word, almost certainly the `SCAN` loop's own counter
local that the `DELETE`-loop rewrite has no equivalent of. Documented,
not forced. Acceptance run `2026-08-28-setup-var-src`: 0 errors,
`SETUPT.CODE` extracted and read back with `CodeFile`, `params`/`data`
confirmed directly rather than assumed from the compiler's own summary
screen.

## 124. Exec files work end to end for driving the acceptance tier -- and `emukeys.ps1` had a real bug hiding them

Apple Pascal 1.3 has a built-in scripting mechanism (manual, "Making and
Using Exec Files") that this project had never used: `m` from the Command
level records a keystroke sequence to a `.TEXT` file, running each command
live as it's typed; `x` (Execute) with `EXEC/<filename>` replays the whole
thing later with no per-keystroke waiting. Tried it against a real compile
(`SET40T.TEXT`) and it reproduces the identical, correct result --
`SET40COL`'s four procedures came back `params`/`data`-exact, matching
finding 112, from a single `X EXEC/SYSHD:COMPTEST{ENTER}` instead of the
full `C...{ENTER}...{ENTER}` sequence `emucompile.ps1` types today.

**The first two attempts silently failed, and the reason is a real bug in
`tools/emukeys.ps1`, not a misunderstanding of exec files.** An exec
file's default terminator is `%`, typed twice to close the recording. But
`emukeys.ps1` passes bare characters straight to .NET's
`System.Windows.Forms.SendKeys.SendWait`, which treats `% + ~ ( ) { }` as
modifier/grouping syntax -- `%` means "hold Alt," not "type a percent
sign." A bare `"%%"` in `-Keys` therefore sent two Alt-with-no-key events
into AppleWin, not two percent signs; the emulator never saw a
terminator, and the "exec file" that resulted was a stale, never-closed
directory entry pointing at leftover disk content from an unrelated
earlier test (confirmed by extracting it and reading the raw bytes: no
`%` anywhere in the file, just old bytes from a previously-deleted test
program). This would have silently broken any future attempt to type one
of those seven characters through this tool, exec files or otherwise.

Fixed in `tools/emukeys.ps1`: single, unbraced occurrences of
`% + ~ ( ) { }` are now auto-wrapped (`{%}`, `{+}`, etc.) before being
sent, so a bare string really is typed literally, matching the module's
own documented contract. `^x` for control-x is untouched -- that one was
already an intentional, documented exception, not a bug. Re-run with the
fix: the exec file recorded and closed correctly (2048-byte `.TEXT` file,
today's date, real `%` bytes present at the expected offsets), and
replaying it reproduced the exact compile.

**Not yet done**: wiring this into `emucompile.ps1`/`emuassemble.ps1`/
`emulink.ps1` as the default driving mechanism -- this session only
proved the mechanism works end to end and fixed the tool bug blocking it.
Also on record but explicitly not started (`docs/PLAN.md`, "carried
forward, not scheduled"): the user's own further idea of patching
`SYSTEM.COMPILER`/`SYSTEM.PASCAL` itself for interactive, space-to-page
error listings -- a real source change, not a driving-mechanism change,
and out of scope until asked for directly.

## 125. Exec files wired in as the default for all three emu*.ps1 scripts -- and a false alarm on the way

Finding 124 proved the mechanism; this wires it into `emucompile.ps1`,
`emuassemble.ps1`, and `emulink.ps1`'s hard-disk paths as the actual
default, via a new `tools/execfile.py` (`keys_to_exec_text`/
`build_exec_file`/`install_exec_file`, reusing `a2pascal.textfile.
encode_text` -- an exec file is just a plain `.TEXT` file with `%`
framing, nothing new to encode). Each script now writes its whole
compile/assemble/link keystroke sequence straight onto `HD1.hdv` as a
fixed-name exec file (`GOCOMP`/`GOASM`/`GOLINK`) before AppleWin ever
opens it, then sends only `X EXEC/SYSHD:<name>{ENTER}` -- two tokens
instead of the whole per-field sequence, and nothing left for
`SYSTEM.ASSMBLER`'s own slow load to eat characters from (the exact
failure mode `emuassemble.ps1`'s own former module note described).

Verified against real compiles/assembles/links, not just "it ran":
`SKEL13.TEXT` compiled 599 lines/0 errors; `SEARCH.TEXT` assembled 519
lines/0 errors (finding 124 already covered these two); `FORMATTR.TEXT`
compiled 263 lines/0 errors, `FMTNATIV.TEXT` assembled 225 lines/0
errors, and linking them together reproduced finding 104's own result
exactly -- `FORMATTE` segment length 2672 bytes, `Copying func
FORMATDI` in the transcript.

**A false alarm along the way, worth recording as its own lesson.** The
first attempt to verify `emulink.ps1` used `SKEL13` as the host file and
appeared to badly corrupt the Linker's first prompt (`Link what host
codefile? NK.CODE[*]`, `No file NK.CODE[*]`) -- `NK.CODE[*]` is exactly
the last 10 characters of the *output* filename (`SKEL13LNK.CODE[*]`),
which looked exactly like an exec-file replay racing SYSTEM.LINKER's own
slow load and overflowing the type-ahead buffer (plausible: unlike
SendKeys' 60ms/char pacing, exec-file replay has no throttling at all).
That diagnosis was **wrong**, caught two ways: the user pointed out
`SKEL13.CODE` didn't actually exist on the disk at the time (a prior
`mkharddisks.py` rebuild had wiped the compiler output from an earlier
session, since it isn't part of `EVIDENCE_CODEFILES` or `FILES`), and
reverting to the original, previously-"working" multi-call live-SendKeys
code reproduced the *identical* corruption -- proving it had nothing to
do with exec files at all. The real cause: `SKEL13.TEXT` is the plain
declaration skeleton with no unresolved `EXTERNAL`, so `SYSTEM.LINKER`
links after the host file alone and never asks for a library
(`emulink.ps1`'s own header comment already says this). The scripted
answers meant for prompts that never appeared landed on the `Command:`
menu instead, and `SKEL13LNK` contains an `L` that re-triggered `L(ink`
with the tail (`NK.CODE[*]`) fed in as a bogus new host-file answer --
a wrong test case, not a bug in the mechanism under test. Re-verified
clean against `FORMATTR`/`FMTNATIV`, a host that genuinely has an
unresolved `EXTERNAL` (finding 104's own pair). The working lesson: when
a `L(ink` test looks corrupted, check first whether the host file even
has an `EXTERNAL` to resolve, before chasing a timing theory.

Not touched: the `-Floppy` paths in all three scripts, still driven by
live SendKeys as before -- the hard-disk layout is the default this
project actually runs, and the floppy layout doesn't have the same
disk-load-races-SendKeys problem to begin with (system tools and output
live on separate volumes there).

## 126. `SETUP.text` -- `SETUP7` written for real, exact; discovered `SETUP13-26` are nested inside `SETUP12`, not flat siblings, and that `FORWARD` reserves a number immediately

Wrote `SETUP7` (the line-editor helper: `/` backspaces with a `<`
echoed the first time in a run, `<` zaps the buffer, RETURN or `!`
ends entry, trims via `SETUP4` before returning) for real. Hit two
real compiler errors getting there: `CONCAT(L3, LASTKEY)` (a `CHAR`
argument) is error 125 -- `CONCAT` wants a `STRING`, so appending one
typed character has to go `L3 := CONCAT(L3, ' '); L3[LENGTH(L3)] :=
LASTKEY` (append a placeholder, overwrite it), matching what the lift's
own `SCONCAT`-then-literal-`'#'` shape was actually showing all along
rather than a decompiler artifact, as first assumed. Verified exact:
`params=6/data=84`, identical to Apple's own binary.

Also attempted `SETUP12`, `13`, `14`, `15`, `25`, `26` as a flat batch
this session, with `SETUP14`/`15`/`25`/`26` `FORWARD`-declared ahead
of `SETUP12` so it could call them. That compiled with **0 errors**
but came back with **every procedure number wrong from 7 onward**
once diffed against Apple's binary -- `SETUP7`'s own real shape
(`6/84`) landed on procedure **11**, not 7, and `SETUP25`'s shape
(`0/82`) landed on **9**, not 25.

Two things this closes:

* **`FORWARD` reserves the next sequential procedure number at the
  point it's declared, not at the point it's completed.** This is
  exactly what finding 61 itself already says -- "declaration order
  is the numbering," assigned when UCSD parses the header, `FORWARD`
  or not. What broke this session was a *later paraphrase* of finding
  61, carried in this file's own `SETUP2`/`3`/`4` comment ("numbers
  assign where a body is compiled, not where a `FORWARD` stub is"),
  which is backwards. That paraphrase happened to give the right
  answer for `SETUP2`/`3`/`4` only because those three are declared
  `FORWARD` and completed in the same relative order (2, 3, 4 both
  times) -- "reserve at declaration" and the wrong paraphrase produce
  identical numbers whenever declaration order matches completion
  order, so that case was never diagnostic either way. Four forwards
  (`14`, `15`, `25`, `26`) declared as one group, out of identifier
  order relative to `SETUP12`'s own position, immediately reserved
  four consecutive numbers (7, 8, 9, 10) right where they stood, and
  `SETUP7`'s real body -- textually next, no forward of its own --
  became procedure 11. Corrected the paraphrase in `SETUP.text`'s own
  comment in place, in addition to this entry.
* **`SETUP13` through `SETUP26` are not flat siblings of `SETUP7-12`
  at all.** The lift (`analysis/utilities/SETUP-1.3-APPLE3.pas.txt`)
  gives `SETUP12` lex 1 (same level as `SETUP1`-`11`), but `SETUP13`
  lex 2, `SETUP14` lex 2, `SETUP15` lex 3, `SETUP16` lex 2, `SETUP17`
  lex 3, `SETUP18` lex 3, `SETUP19` lex 3, `SETUP20` lex 4, `SETUP21`
  lex 3, `SETUP22`-`24` lex 4, `SETUP25` lex 2, `SETUP26` lex 2 --
  every one of them is nested **inside `SETUP12`'s own declaration
  part** (with further nesting among themselves matching the deeper
  lex levels), not declared alongside it. That's the real reason
  `SETUP12` can reach `SETUP14`/`25`/`26` at all: ordinary Pascal
  nested-procedure scoping, no `FORWARD` required once they're nested
  in the right place. `SETUP7`-`11` staying flat siblings (lex 1,
  matching the binary) is correct and unaffected by this.

Reverted the flat 12/13/14/15/25/26 attempt back to plain
zero-argument stubs (matching every other not-yet-written procedure in
this file) rather than ship it with wrong numbering; only `SETUP7` is
real this session. Properly nesting `SETUP13`-`26` inside `SETUP12`,
in the right sub-hierarchy, is the natural next step -- not attempted
here. Acceptance run `2026-08-28-setup7-exact`: 0 errors, 651 lines,
`SETUPT.CODE` extracted and confirmed via `CodeFile` (not just the
compiler's own summary screen).

## 127. `SETUP.text` -- the `SETUP12` nesting hypothesis confirmed exactly: 12/13/14/15/25/26 all land on Apple's real numbers and frame sizes

Finding 126 worked out, from the lift's own lex levels and call graph,
that `SETUP13` through `SETUP26` are nested **inside `SETUP12`'s own
declaration part** (13, 14, 16, 25, 26 direct children; 15 nested in
14; 17/18/19/21 nested in 16; 20 nested in 19; 22/23/24 nested in 21),
not flat siblings the way `SETUP7`-`11` are. Rebuilt `SETUP12` that
way -- `SETUP13`, `SETUP14` (with `SETUP15` nested inside it), and
`SETUP25`/`SETUP26` written for real inside `SETUP12`'s own
declaration part, `SETUP16` (and everything nested inside it, 17-24)
left as empty stubs with their own further nesting preserved but no
real bodies yet.

**0 errors, 837 lines, first attempt at the corrected structure.**
Diffing every procedure's `params`/`data` against Apple's own binary:

| # | mine | Apple's | |
|---|------|---------|---|
| 12 | 0/0 | 0/0 | exact |
| 13 | 4/0 | 4/0 | exact |
| 14 | 0/0 | 0/0 | exact |
| 15 | 0/0 | 0/0 | exact |
| 25 | 0/82 | 0/82 | exact |
| 26 | 2/0 | 2/0 | exact |

Six for six, with no `FORWARD` needed anywhere in the whole rebuilt
block -- ordinary nested-procedure scoping was enough once the
structure matched Apple's own, confirming both finding 126's nesting
hypothesis and finding 61's real rule (declaration order is the
numbering) at the same time. `SETUP16`/`17`/`18`/`19`/`20`/`21`/`22`/
`23`/`24` differ from Apple's binary as expected -- they're still
empty stubs, not real bodies, and none of the mismatches are the kind
finding 126 was chasing (wrong procedure number); they're the ordinary
kind of gap an unwritten stub is expected to show. `SETUP16`'s own
`params` already came out right (2) purely from guessing a bare
`(L1: NODEPTR)` signature, which is a good sign for when its real body
gets written.

Acceptance run `2026-08-28-setup-nested-change`: `SETUPT.CODE`
extracted and every procedure's `params`/`data` compared directly
against Apple's `SETUP.CODE` via `CodeFile`, not just the compiler's
own summary screen.

## 128. `SETUP.text` -- `SETUP20`/`22`/`23`/`24` written for real, all four exact first attempt

Continued into `SETUP16`'s own nested subtree (finding 127's confirmed
structure). Wrote the four self-contained leaves that don't need the
bit-field pack/unpack trick or the complex numeric-entry retry loop:

* **`SETUP20`** -- `2^N` via a plain `FOR I := 1 TO N DO ANSWER :=
  ANSWER * 2` loop (the field's own bit width, used as the exclusive
  upper bound for unsigned octal/decimal/hex entry). The lift's own
  `L6 := L3` (copying the parameter into a fresh local before looping)
  is exactly what a `FOR` loop's hidden once-evaluated bound produces
  -- writing it as a `FOR` loop instead of translating that copy
  literally is what closed it.
* **`SETUP22`**/**`SETUP23`**/**`SETUP24`** -- the scalar-value
  display/list/lookup trio SETUP21 (not written) will drive. All
  three read `L1` -- SETUP16's own `NODEPTR` parameter -- by ordinary
  lexical scoping, two levels up, exactly the way finding 127
  predicted nested procedures would. `SETUP24` reuses SETUP3's own
  sentinel-search trick (finding 122's BST search): the searched-for
  name is written into `BOOLNAMES^.NAME` first, so the loop is
  guaranteed to terminate at worst back at `BOOLNAMES` itself, with no
  separate bounds check -- the same idiom, a second, independent time.

**All four exact, first attempt**, `params`/`data` against Apple's own
binary: `SETUP20` `6/6`, `SETUP22` `2/2`, `SETUP23` `0/2`, `SETUP24`
`8/84`. `SETUP16`'s own bare `(L1: NODEPTR)` guess (finding 127) still
has the right `params` (`2`) with its body still empty. `SETUP17`,
`18`, `19`, `21` (the bit-field pack/unpack and the two entry-loop
drivers) remain unwritten -- the natural next continuation, along with
`SETUP8`-`11` (the QUIT handler and the octal/decimal/hex display/
entry engine at the SETUP1-11 flat level) and `TEACHSET`.

Acceptance run `2026-08-28-setup-scalar-editor`: 0 errors, 915 lines,
`SETUPT.CODE` extracted and every procedure's `params`/`data` compared
directly against Apple's `SETUP.CODE` via `CodeFile`.

## 129. `SETUP.text` -- `SETUP17`/`SETUP18` (bit-field pack/unpack) written for real, exact

`SETUP16`'s two remaining self-contained leaves before the numeric-
entry driver itself: `SETUP17` packs a field's own bits out of
`MISCINFO` into an integer, most-significant first; `SETUP18` is the
inverse, unpacking an integer's bits back in, with a negative value
setting the field's own top bit as a sign flag first. Both need
single-bit read/write into one `MISCINFO` word (`ARRAY[0..95] OF
INTEGER`) -- redeclared `MISCREC`'s element type as a variant record
(`MISCWORD`), overlaying a whole `INTEGER` with a `PACKED ARRAY[0..15]
OF 0..1` bit view, reusing the exact idiom already established and
compiled clean in `SET40COLS.text`'s own `FLAGBYTE` (`0..1`, not
`BOOLEAN`, since `SETUP17`'s own pack does direct arithmetic on a bit
value, `RESULT+RESULT+bit`, which `BOOLEAN` can't do without an
explicit test). No other code touches `MISCINFO`'s elements directly
yet (`SETUP8` is still a stub), so the type change is safe.

First attempt landed 2 bytes short on each (`2/4` against Apple's
`2/6`) -- both procedures access `L1` (`SETUP16`'s own parameter)
directly via lexical scoping, but the lift shows an explicit `L3 :=
I1,1` step the real source apparently takes too: a local `FIELD:
NODEPTR` copy of `L1`, one extra word, used throughout instead of `L1`
itself. Adding it closed both exactly: `SETUP17` `2/6`, `SETUP18`
`2/6`.

Remaining in `SETUP16`'s own subtree: `SETUP19` and `SETUP21`, the two
entry-loop drivers that call everything written this session and last
(`SETUP7`, `9`-`11`, `13`, `17`, `18`, `20`, `22`-`24`) -- blocked on
`SETUP9`-`11` (the octal/decimal/hex display/entry engine at the flat
level) still being unwritten. Acceptance run
`2026-08-28-setup-bitfield`: 0 errors, 966 lines, `SETUPT.CODE`
extracted and every procedure's `params`/`data` compared directly
against Apple's `SETUP.CODE` via `CodeFile`.

## 130. `SETUP.text` -- `SETUP9`/`SETUP11` written for real, both exact

The last two self-contained flat (`lex 1`) leaves before `SETUP10`
itself: `SETUP9` prints one value's octal/decimal/hexadecimal (and,
when `SHOWCHAR`, ASCII/CONTROL name) read-out line; `SETUP11` prints
the entry-format help diagram, waiting on `SETUP5` until `'C'`.

`SETUP9` needed the same variant-record bit-view idiom as `SETUP17`/
`18` (finding 129) applied to a *value* parameter rather than a
`MISCINFO` word -- octal viewed 5-digits/3-bit-each, hex 4-digits/
4-bit-each. First attempt combined both views into one 3-way variant
plus a loop counter (`2` locals, `4` bytes) and landed 4 bytes short
of Apple's `4/8`; splitting into two *separate* variant locals
(`OCTVIEW`, `HEXVIEW`) plus an explicit plain-`INTEGER` copy (`L6`,
used for the decimal column) instead of writing the parameter directly
-- three named locals plus the loop counter, matching the lift's own
`L6`/`L4` shape more literally -- closed it exactly.

`SETUP11` needed an explicit `KEY: CHAR` local capturing `SETUP5`'s
own result inside the wait loop (`REPEAT KEY := SETUP5 UNTIL KEY =
'C'`) rather than calling `SETUP5` bare in the loop condition -- the
lift's own `locals 1 words` was the tell, since a bare condition call
needs no storage at all.

Both exact: `SETUP9` `4/8`, `SETUP11` `6/2`. `SETUP10` -- the actual
numeric-entry reader (locals 64 words, the largest local frame outside
`SETUP8` in the whole file: string-buffer entry via `SETUP7`, named-
key lookup against `CTRLNAMES`, octal/decimal/hex-prefixed digit
parsing with overflow checking) -- remains a stub, deliberately left
for a dedicated session rather than a rushed attempt; it's what
`SETUP19`/`21` (finding 129) are still blocked on. `SETUP8` (the QUIT
handler) and `TEACHSET` are the other remaining stubs.

Acceptance run `2026-08-28-setup-display-help`: 0 errors, 1117 lines,
`SETUPT.CODE` extracted and every procedure's `params`/`data` compared
directly against Apple's `SETUP.CODE` via `CodeFile`.

## 131. `REMIN:`/`REMOUT:` console redirect: the read/write table confirmed live and a working redirect written; the actual byte transfer over AppleWin's SSC+TCP socket hangs, root cause not found

Carried forward from the "REDIRECT" interactivity thread (`docs/PLAN.md`):
`REDIRECT` itself doesn't exist (established earlier), and a pasted,
LLM-generated "Unit Vector Table at zero-page $1A" writeup didn't either
-- it contradicts the language reference's own statement that zero-page
`0..35` decimal is explicitly scratch, reused by the system between
calls (`analysis/reference/apple-pascal-language-reference.txt:1782`),
and nothing in the UCSD II.0 OS source (`reference_source/ucsd_ii0/`)
names any such table. `$1A` is inside that scratch range -- a real
persistent OS pointer living there would be a contradiction in Apple's
own manual, not just unconfirmed.

**What's real, and independently confirmed twice over.** The user's own
`CHANGEIO` program (D.M.T., 7/22/83, pasted whole) hardcodes page-zero
location 230 decimal as a write-table base and works. Neil Parker's
*Undocumented Secrets* (a lead, not an authority, per project rules)
independently names 230 decimal (`$E6`) `WTPTR` and adds 228 (`$E4`)
`RTPTR` -- an 8-entry table of 2-byte pointers, one per unit `#1`..`#8`,
mirroring `WTPTR`'s own layout for the read side. `IOPROBE.TEXT` (a
throwaway PEEK-based probe, compiled clean, run on the real 1.3 system)
confirmed both addresses and the full 8-unit layout live:

```
RTPTR(228) = -2850   WTPTR(230) = -2866
unit 1  read=-256  write=-253   CONSOLE:
unit 2  read=-256  write=-253   SYSTERM: (identical to unit 1 -- CHANGEIO's own comment, now confirmed on the read side too)
unit 3  read=   0  write=-223   GRAPHIC:
unit 4  read=   0  write=   0   DISK1: (block device -- not in this table at all)
unit 5  read=   0  write=   0   DISK2:
unit 6  read=   0  write=-247   PRINTER: (write-only)
unit 7  read=-232  write=   0   REMIN: (read-only -- write=0 matches CHANGEIO's own comment)
unit 8  read=   0  write=-229   REMOUT: (write-only)
```

Unit 6's read slot and unit 7's write slot both read back 0 live, exactly
as needed: `CHANGEIO` already used unit 7's write slot as scratch to hold
CONSOLE:'s original write address; unit 6's read slot is the exact
mirror for the read side.

**`REDIRIO.TEXT`**, the symmetric extension of `CHANGEIO` (swaps both
CONSOLE:'s read pointer to REMIN:'s routine and its write pointer to
REMOUT:'s, using unit 6's read slot and unit 7's write slot as the two
scratch/restore locations, toggling the same way `CHANGEIO` does), also
compiled clean and **ran successfully**: after
`Redirecting console I/O to REMIN:/REMOUT:` printed (through the
original path, before the swap), the Command level's own next prompt
never appeared, and typing `HELLO<CR>` at the physical keyboard produced
*zero* change on screen (confirmed via `tools/watchscreen.py`'s idle
detection, not just eyeballing a screenshot) -- CONSOLE: read and write
are both genuinely off the keyboard/screen and pointed at REMIN:/REMOUT:.
Fully recoverable: killing the AppleWin process and rebooting reverts
everything, since only RAM was ever touched.

**The round trip over an actual endpoint does not work yet, and the
failure is earlier than expected.** `tools/runemu.py` gained an `--ssc`
flag (`-s2 ssc`, plus the `Slot 2\Serial Port Name=TCP` registry value
AppleWin's own `SerialComms.cpp` reads -- a *different* registry subkey
than the flat one `SETTINGS` already writes, confirmed by reading
`CSuperSerialCard`'s constructor directly off GitHub). With that in
place:

- `UNITSTATUS(7, result, 1)` and `UNITSTATUS(8, result, 1)` both return
  `IORESULT=0` -- Apple Pascal genuinely detects the card in slot 2.
- `UNITCLEAR(8)` also returns `IORESULT=0`.
- A plain `UNITWRITE(8, buf[0], 5, , 12)` -- the manual's own
  `TestStuff` call shape, Chapter 10 -- **hangs indefinitely** (tested
  past 60 seconds, both with and without AppleWin's `-modem` switch,
  which GH issue #311 says is needed for DTR/DCD/DSR emulation).
- Read AppleWin's own `source/SerialComms.cpp` directly (`gh api
  repos/AppleWin/AppleWin/contents/...`): `CheckComm()` -- the function
  that creates, binds, and listens the port-1977 socket -- is the first
  line of *every* register handler (`CommCommand`, `CommControl`,
  `CommReceive`, `CommTransmit`, `CommStatus`). `netstat` confirmed port
  1977 **never binds**, through a 60-second hang, either with the plain
  `UNITWRITE` or with `UNITCLEAR(8)` (which itself returns success)
  immediately followed by the same `UNITWRITE`. Since *any* register
  touch would trigger the bind, a hang with no bind at all means
  Apple Pascal's REMOUT: driver never executes a single SSC register
  access during the hang -- it's stuck in software, before ever reaching
  the hardware, for a reason not yet identified.

**Not yet tried**: single-stepping/logging inside AppleWin itself (a
debug build, or its own trace logging) to see where the 6502 PC actually
is during the hang; checking whether `UNITSTATUS`'s own successful
`IORESULT=0` implies register access already happened (in which case the
bind should already be live by the time `UNITWRITE` is called, and isn't
-- worth rechecking netstat right after `UNITSTATUS` alone); trying the
write with `(*$I-*)` and a hard timeout/retry wrapper in case it's not a
true infinite loop; the DIPSW baud-rate/interrupt defaults
(`SetDIPSWDefaults`, 9600-8-N-1, interrupts *on*) combined with
AppleWin's high `Emulation Speed` setting, in case an IRQ-driven
handshake the driver expects never arrives at the emulated speed.

Scratch programs (`IOPROBE.TEXT`, `REDIRIO.TEXT`, `SSCCHECK.TEXT`,
`SSCWRITE.TEXT`/`SSCWRITE2.TEXT`) live outside the repo for now (session
scratchpad) -- not part of the disk-set reconstruction, and not moved in
until the round trip actually works end to end.

## 132. `SETUP.text` -- `SETUP10` (the numeric-entry reader) written for real, exact

The largest remaining flat-level stub before this session, and what
`SETUP19`/`21` (finding 129) are blocked on. `FUNCTION SETUP10(HIGH, LOW:
INTEGER; NAMEDOK: BOOLEAN; VAR VALUE: INTEGER): BOOLEAN` -- reads a line
via `SETUP7`, then accepts it three ways: a single non-digit character
taken literally (`ORD`) when `NAMEDOK`; a <=3-character match against
`CTRLNAMES` or the literal `'DEL'` when `NAMEDOK` (the sentinel-search
idiom a third time -- `CTRLNAMES[33]` is written with the entry itself
first, guaranteeing the search loop terminates, same trick as `SETUP3`'s
BST search and `SETUP24`'s scalar lookup); or an optionally-signed,
optionally `D`/`H`/`O`-prefixed (default radix `G4`) run of digits,
validated digit-by-digit against a `SET OF CHAR` built from the radix
before any parsing, then accumulated with an overflow check
(`VALUE > (32767-DIGIT) DIV RADIX`) one digit at a time rather than after
the fact. Returns `TRUE` only if parsing succeeded and the result falls
in `[LOW..HIGH]`.

Parameter order (`HIGH, LOW: INTEGER; NAMEDOK: BOOLEAN`) matches
`SETUP11`'s already-exact signature exactly, both independently derived:
`SETUP10`'s own comparisons (`VALUE >= LOW`, `VALUE <= HIGH`) plus the
established rule that parameters ascend directly in declaration order
(confirmed again here, opposite of `VAR`-block locals, which descend
within a group -- `SETUP9`'s `SHOWCHAR` at local 1/`VALUE` at local 2
already showed the ascending-params half; `SETUP11`'s `HIGH` at local
1/`LOW` at local 2, printed in the source as `LOW..HIGH`, is what nails
down that a two-identifier *parameter* group ascends by listed order,
the mirror image of a `VAR` group).

First attempt landed `params=12` exact (confirming the parameter list
itself, and that a `FUNCTION`'s frame reserves a 1-word result plus a
1-word gap before its real parameters start -- already established by
`SETUP3`/`SETUP7`, both 1-argument functions whose own single parameter
landed at local 3, not 1 or 2) but `data=118` against Apple's `128` -- 10
bytes, 5 words, short. Diffing local-frame offsets directly out of the
compiled p-code (`LLA`/`STL`/`SLDL` operands) confirmed every other
local landed exactly where expected (booleans at 7/8, four working
integers at 9-12, the digit `SET OF CHAR` at 13, the entry buffer at 29)
-- the miss was entirely inside the entry buffer's own declared size.
The first attempt declared it `STRING[70]`, sized to exactly consume the
remaining budget under a (wrong) `ceil((N+1)/2)` guess; the real buffer
is a plain default `STRING` (80 characters, 41 words) -- bigger than the
tightest guess that would fit the frame, not sized to exactly fill it.
Switching to plain `STRING` closed it to `params=12/data=128` exact, and
a full 26-procedure diff against Apple's shipped `SETUP.CODE` confirmed
nothing else regressed -- only the pre-existing, already-documented gaps
remain (`SETUP4`'s one-word miss, `SETUP16`'s one-word miss, and stubs
`SETUP8`/`SETUP19`/`SETUP21`).

Acceptance run `2026-08-29-setup10-numeric-entry`: 0 errors, 1244 lines,
`SETUP.CODE` extracted and every procedure's `params`/`data` compared
directly against Apple's own binary via `CodeFile`.

## 133. `SETUP.text` -- `SETUP8` (the QUIT handler) written for real, D/H/E exact, M a documented stub

The largest procedure in the file (`data=796` bytes, 398 words -- bigger
than `SETUP10`'s 128). `PROCEDURE SETUP8` loops printing `QUIT: D(ISK)
OR M(EMORY) UPDATE, R(ETURN) H(ELP) E(XIT)` until `R` or `QUITFLAG`,
dispatching on `SETUP5`:

* **D(isk)** -- `REWRITE(F, '*NEW.MISCINFO'); F^ := MISCINFO; PUT(F);
  CLOSE(F, LOCK)`, where `F: FILE OF MISCREC`. The `*` volume prefix
  (search every online volume) is written literally into the string
  constant, matching Apple's own p-code exactly.
* **H(elp)** -- six literal `WRITE`/`WRITELN` blocks of help text, no
  new mechanism.
* **E(xit)** -- `EXIT(SETUP)`. Two other spellings were tried and both
  failed: the bare `EXIT(PROGRAM)` (valid Pascal in general, per the
  language reference's own examples) hit error 125 (type mismatch) here,
  and `EXIT(PASCALSYSTEM)` (the outer `(*$U-*) PROGRAM`'s own name) hit
  error 104 (undeclared) -- both dead ends this file's own header
  comment already recorded for `SETUP2`'s identical case, with
  `SYSTEM.COMPILER`'s own `BLOCK`/`EXIT(PASCALCOMPILER)` as the
  precedent that settled it. `EXIT(SETUP)` -- naming the enclosing
  `SEGMENT PROCEDURE`, not the outer `PROGRAM` -- is the form that
  works, and it is what `SETUP2` already uses.
* **M(emory)** -- left `(*STUB*)`, documented not forced. Apple's own
  binary pokes `MISCINFO`'s words 29..47 directly into a location the
  lift reaches via "2 levels up" from `SETUP8` -- the *same* lexical
  distance every `WRITE`/`WRITELN` in this file reaches `OUTPUT` from,
  regardless of how deeply the calling procedure is nested (confirmed
  by comparing raw p-code lex operands directly: `SETUP.1` reaches
  `OUTPUT` via `LOD 1,3`, `SETUP8` -- one level deeper -- via `LOD 2,3`,
  the encoding growing by exactly the extra static link, not a fixed
  absolute level). That places the M-branch's write target in
  `PASCALSYSTEM`'s own implicit scope, one level *above* `SETUP` itself
  -- genuinely outside what this file can declare, since `SYSTEM.PASCAL`
  (or whatever hosts `PASCALSYSTEM`'s own real globals at that level)
  is not reconstructed yet (`docs/DISKSET.md`). Writing a guessed
  identifier there would either fail to compile or silently compile
  against the wrong thing; left as an intentional no-op instead, the
  same call this file already made for `INITS5`.

`F: FILE OF MISCREC`'s own frame contribution was the other real
unknown -- a `FINIT(@L2, @L302, 96)` call implied roughly 300 words of
file-control overhead before the 96-word `MISCREC` buffer even starts,
far bigger than a typical Apple Pascal FCB. Rather than guess, a
throwaway probe program (`FSIZE.TEXT`, session scratchpad, not part of
this file) declared nothing but `F: FILE OF MISCREC` and one small
local, compiled it, and read its outer body's own `data_size` back via
`CodeFile` directly: **396 words for the file variable alone**. Together
with the M-branch's own loop counter and bound (1 word each, left
undeclared along with the stub), that accounts for the *entire* 398-word
frame -- confirming nothing else is hiding in this procedure, and that
`(1 loop var) + (396-word file var) + (1 loop bound) = 398` is the whole
story, not a coincidence.

Verified: `params=0/data=792` against Apple's `0/796` -- 2 words short,
exactly the stubbed M-branch's own loop counter and bound, documented
not forced. A full 26-procedure diff against Apple's shipped `SETUP.CODE`
confirmed nothing else regressed (the same four pre-existing gaps as
finding 132: `SETUP4`, `SETUP16`, and stubs `SETUP19`/`SETUP21`).
`SETUP19`/`21` (blocked on `SETUP8` and `SETUP10` both) are now blocked
on nothing from this file except being written; `TEACHSET`'s own ten
tutorial procedures are the last stub in `SETUP.CODE`.

Acceptance run `2026-08-29-setup8-quit-handler`: 0 errors, 1301 lines,
`SETUP.CODE` extracted and every procedure's `params`/`data` compared
directly against Apple's own binary via `CodeFile`.

## 134. `SETUP.text` -- a real parameter-ordering rule found; `SETUP19` attempted and reverted, not shipped

Attempting `SETUP19` (the numeric entry driver, nested in `SETUP16`,
blocked on nothing after finding 133) surfaced a genuine gap in this
project's own understanding of finding 93a, and then a second, deeper
mystery that stayed open. Recorded in full because the first half is a
real, reusable rule and the second half will save whoever attempts this
next from repeating the same dead ends.

### 134a. Finding 93a's rule applies to parameters too, and VAR groups behave opposite to VALUE groups

Finding 93a covers `VAR`-block locals only: "declaration groups ascend,
identifiers within one group descend." Every parameter list reconstructed
so far happened to be either single-member groups (where ascend/descend
is unobservable) or the compiler-computed offsets never got checked
closely enough to notice a conflict. Comparing two already-exact,
already-shipped signatures directly:

* `SETUP4(VAR DEST: STRING; VAR SRC: STRING)` -- `DEST` (1st-declared)
  loads its own value into `L2`, `SRC` (2nd-declared) into `L1`. `L1 <
  L2`, so the **1st-declared VAR parameter gets the *higher* offset** --
  the same "1st-listed gets the higher address" rule finding 93a already
  established for `VAR`-block locals.
* `SETUP11(HIGH, LOW: INTEGER; NAMEDOK: BOOLEAN)` -- `HIGH`
  (1st-declared) prints at `L1`, `LOW` (2nd-declared) at `L2`. `L1 < L2`,
  so the **1st-declared VALUE parameter gets the *lower* offset** -- the
  opposite of the `VAR` case, and the opposite of finding 93a's own rule.

So: a **`VAR`-parameter group descends** (matches `VAR`-block locals);
a **plain-value-parameter group ascends** (does not). Both are internally
consistent and independently confirmed by two procedures already
byte-exact against Apple's binary, so this isn't a live question -- it's
a fact about this compiler this project hadn't separated out before.
`SETUP10`'s own already-verified-exact signature
(`FUNCTION SETUP10(HIGH, LOW: INTEGER; NAMEDOK: BOOLEAN; VAR VALUE:
INTEGER): BOOLEAN`) is consistent with this rule read correctly:
`HIGH, LOW` is one ascending VALUE group (`HIGH` lower, `LOW` higher),
`NAMEDOK` its own single-member group, `VAR VALUE` its own single-member
`VAR` group -- and confirmed a second, independent way: `SETUP10`'s own
internal usage dereferences `L6` (the highest of its four param offsets)
throughout as the return-value pointer, settling which physical offset
is the `VAR` one without reference to any caller at all.

### 134b. `SETUP19`'s real frame is 44 words against 4 visible in its own body -- not resolved

Writing `SETUP19` to call `SETUP9`/`SETUP10`/`SETUP11`/`SETUP18` with the
semantically correct arguments (matching the signatures 134a settles)
compiled clean, first attempt -- but came back `params=2/data=6` against
Apple's real `2/88`. A 41-word gap this large means something structural
is missing, not a rounding/one-word miss, so it was reverted rather than
shipped. What was checked and ruled out:

* **Not a caller-argument-order artifact.** `SETUP19`'s own call to
  `SETUP.10` in the raw p-code (`enter=$0FC4`, not the simplified lift
  text) pushes `LLA 4` (the address of its own local 4) *first*, ahead of
  three plain `SLDL` value pushes -- and `SETUP10`'s sole `VAR` parameter
  is declared *last* (134a). Cross-checked against an unrelated,
  already-exact call (`SETUP21`'s own `SETUP.24(@L1, @L2)`, both `VAR`,
  in declared order) to confirm the lift's displayed call order is
  normally trustworthy; this one case still doesn't resolve cleanly
  under a simple "push order = declared order" reading, and was set
  aside rather than chased further, since it doesn't explain a 41-word
  *frame* gap either way -- argument order only affects what gets
  passed, not how many locals the *callee itself* declares.
* **Not a hidden `STRING` buffer the way `SETUP21`'s own analogous gap
  is.** `SETUP21` (`params=0/data=84` real -- also large, also
  unattempted) calls `SETUP.7(@L2)` directly, meaning it owns a local
  `STRING` (`L2`, ~41 words) to receive text before handing it to
  `SETUP24`. `SETUP19`'s own body has no `SETUP.7` call anywhere,
  visible in either the lift or the raw p-code -- it delegates all text
  entry to `SETUP10` internally, which already accounts for its own
  41-word buffer inside its *own* already-verified 128-word frame. There
  is no structural reason visible yet for `SETUP19` to need one too.
* **Not a lift-tool miscount.** The 44-word figure was confirmed
  directly from the raw p-code header (`data=88` bytes, not the lift's
  post-processed `locals 44 words` line) -- a real fact about Apple's
  compiled bytes, not a decompiler artifact.

Left as a stub (`PROCEDURE SETUP19;`, `SETUP20` still correctly nested
inside it and still exact on its own).

## 135. `SETUP.text` -- `SETUP21` (the scalar-name entry driver) written for real, exact

`SETUP21`'s own gap turned out to be exactly what finding 134b guessed
it might be: a local `STRING`. `SETUP21` calls `SETUP.7(@L2)` directly
(reading a name), unlike `SETUP19`, which delegates all text entry to
`SETUP10` and never touches `SETUP7` itself -- so `SETUP21` genuinely
needs to *own* a buffer for the name it reads, where `SETUP19` does not.
`VALUE: INTEGER` (1 word) plus `ENTRY: STRING` (default, 41 words) is
`42` words total, matching Apple's real `data=84` bytes exactly, with
no slack.

Both locals are named to avoid shadowing: `SETUP16`'s own parameter is
`L1`, and `SETUP17`'s own `VAR RESULT` parameter -- both still reached
by lexical scoping inside `SETUP22`/`23`/`24`, nested alongside `SETUP21`
inside `SETUP16` -- would have been silently shadowed by a same-named
local here, changing what those three procedures actually read without
a compiler error to catch it.

Body: shows the current value by name (`SETUP22`), then loops `SETUP7`
(read a name) against `SETUP24` (look it up, setting `VALUE`) and
`SETUP23` (re-list the allowed names on a miss) until a real match or
`QUITFLAG`, confirming (`SETUP13`) whether to keep going; the last
accepted value is packed back with `SETUP18` unless `QUITFLAG` or the
entry was left blank. `SETUP24`'s own call (`SETUP24(VALUE, ENTRY)`)
matches its already-established signature
(`VAR VALUE: INTEGER; VAR NAME2: STRING`) positionally with no
reordering needed -- unlike `SETUP19`'s own unresolved call into
`SETUP10` (finding 134b), this one args cleanly on the first attempt.

Verified: `params=0/data=84` exact, first attempt. A full 26-procedure
diff against Apple's shipped `SETUP.CODE` confirmed nothing else
regressed. `SETUP19` (finding 134b's own open 41-word mystery, still
unresolved -- this file's `SETUP7`-ownership pattern doesn't explain it,
since `SETUP19` never calls `SETUP7`) and `TEACHSET`'s ten tutorial
procedures are the only two stubs left in the entire file.

Acceptance run `2026-08-29-setup21-scalar-driver`: 0 errors, 1345 lines,
`SETUP.CODE` extracted and every procedure's `params`/`data` compared
directly against Apple's own binary via `CodeFile`.

## 136. `SYSTEM.PASCAL` started: the skeleton compiles clean, and 42 of segment 0's 43 procedures already match on `params`

First session on the operating system, target **128K.PASCAL specifically**
(not the 64K `SYSTEM.PASCAL` build, which is out of scope for this file
entirely by direct instruction -- not read, not cited, not compared
against). New source: `src/pascal/os/1.3/PASCALSYSTEM.text`.

### 136a. `WRITE`/`WRITELN` don't work here -- call the primitives directly

UCSD's own `SYSSEGS.A.TEXT` writes `FWRITELN(SYSTERM^)`, not
`WRITELN(SYSTERM^)`. Assumed this was just older style and tried the
sugar form first -- `SYSTERM: FIBP = ^FIB`, `WRITELN(SYSTERM^)` --
which hit error 125 on Apple's real compiler. Chased it three ways:

* The host compiler (`ucsdpsys_compile`, `A2_UCSDPSYS`) has the real
  `WRITE`/`WRITELN` builtins' own declared signatures baked in
  (`lib/translator/builtin.cc` in its own source tree, extracted from
  `thirdparty/ucsd-psystem-xc-0.13.tar.gz`) and reported them directly:
  `sys:fwriteln`/`sys:fwritestring`/`sys:fwritechar` all take
  `VAR F: FILE` (an untyped file, "a file of anything"), and `WRITELN`
  additionally demands "a file of char" -- neither matches `^FIB`, a
  pointer to an ordinary record. Retyping `FIBP` as `^TEXT` satisfied
  the host compiler completely.
* Apple's own compiler still refused it -- **same error 125, same
  line** -- even with `FIBP = ^TEXT`. Isolated the exact distinction
  with a two-line test program: `WRITELN(DIRECTF)`, a plain `TEXT`
  variable, compiles; `WRITELN(SYSTERM^)`, a pointer *dereference* of
  the identical type, does not. Apple's `WRITE`/`WRITELN` sugar accepts
  only a plain variable identifier as its file argument, not a general
  file-typed expression -- confirmed directly against the real compiler
  in the emulator, not inferred. The host compiler is more permissive
  here, consistent with `tools/xcompile.py`'s own header note.
  SPECULATION, not needed for anything below: this reads like the
  sugar's own argument-recognition being purely syntactic (is the
  first token a bare identifier?) rather than a type check, so a
  dereference just falls through to "no file argument given, write
  this value to `OUTPUT`" and fails there instead, on writing a whole
  record as if it were a value.
* `GLOBALS.TEXT`'s own "SYSTEM PROCEDURE FORWARD DECLARATIONS" section
  settles it completely: `PROCEDURE FWRITELN(VAR F: FIB); FORWARD;` --
  an **ordinary ****`VAR`**** parameter of type ****`FIB`****, on an
  ordinary procedure**, callable directly by name. Ordinary `VAR`
  parameters accept any file-typed expression, dereferences included --
  it is specifically `WRITE`/`WRITELN`'s own compiler sugar that is
  restrictive, and calling the real routine directly sidesteps it
  entirely. `FIBP = ^FIB` (the original type) was right all along; the
  fix was calling `FWRITELN`/`FWRITESTRING` directly, the way UCSD's
  own source already does, not retyping anything.

The raw p-code independently confirms this reading of the calling
convention, not just the syntax: `USERPROG.1` (segment 1's own body,
`analysis/utilities/128K-1.3-APPLE3.pcode.txt`) is `LOD 1,56; CXP 0,22`
-- a plain *value* load (not a dereference-then-load sequence) pushed
straight into `FWRITELN` (`OS.22`). The global at that offset is
itself the pointer; its own value already *is* the address `VAR F`
needs, which is exactly what passing a `FIBP`-typed global (not
`FIBP^`) to an ordinary `VAR FIB` parameter compiles to.

### 136b. The 41 forward declarations are 41 of segment 0's own procedure numbers

`GLOBALS.TEXT`'s forward-declaration block is not documentation, it is
41 of segment 0's own procedure declarations -- 27 "fixed" (its own
comment: "addressed directly by object code... do not move without
careful thought"), then 14 "non-fixed". Declared all 41, plus the
still-deferred outer body (`PASCALSY`, the real 451-word main loop,
`analysis/lifted/128K.PASCAL-1.3-128K.pas.txt`), for 42 total --
exactly finding 51a's own already-verified count for how far Apple's
real numbering agrees with UCSD's declared order. `FINIT` (2nd
declared) landing on procedure 3 -- one more than its declaration
position, since the enclosing block's own body always claims number 1
-- independently matches an already-recovered comment from earlier
compiler work, `OS.3 FINIT`.

Structuring the file needed the same two tricks findings 61/126/119
already established for `SETUP.text`, just at a larger scale: `FORWARD`
reserves a procedure's number immediately at declaration, not at
completion, so all 41 are `FORWARD`-declared as a block; and no
`SEGMENT PROCEDURE` may textually follow a body that is already
*complete* (error 399, `CODEINSEG`), so the six `SEGMENT PROCEDURE`s
(`USERPROGRAM` real, the other five plausible-signature stubs) sit
between the 41 `FORWARD`s and their own 41 real completions, not after
them.

### 136c. The result

**0 errors**, first attempt at the restructured file, 402 lines. Every
one of the 7 segments landed in the right disk slot with the right
name (`PASCALSY`/`USERPROG`/`FIOPRIMS`/`PRINTERR`/`INITIALI`/`GETCMD`/
`FILEPROC`, matching `analysis/diskset-inventory.txt` exactly), and
**42 of segment 0's 43 procedures already match Apple's real `params`
size exactly** -- the one mismatch is procedure 43, which finding 51c
already established is not `COMMAND` at all (Apple's own insertion,
identity withheld); nothing here forces or guesses at it. `USERPROGRAM`
itself (segment 1) matches Apple's real `args 2 words` on `params`,
straight from UCSD's own `SYSSEGS.A.TEXT`; `PRINTERROR`/`INITIALIZE`/
`GETCMD`'s own stub signatures also match Apple's real per-segment
`args` exactly (`GETCMD`'s `params=6` bytes is `1 declared arg + the
2-word function-result slot`, finding 51a's own rule, not a
mismatch). `FIOPRIMS`/`FILEPROC` have no UCSD precedent (Apple-specific,
128K-only segments) and remain unverified placeholders.

Not started yet: `PASCALSY`'s own real 451-word main-loop body (by far
the largest single procedure in the whole disk set), any of the 41
forward-declared procedures' real bodies (`FWRITELN`/`FWRITESTRING`
included -- their current bodies are empty, only `USERPROGRAM` actually
exercises them and neither is checked against Apple's binary yet), and
five of the six segments' own real content beyond procedure 1.

Acceptance run `2026-08-29-pascalsystem-skeleton`: 0 errors, 402 lines,
`PASCALSYS.CODE` extracted and its full segment/procedure structure
compared directly against Apple's real `128K.PASCAL` via `CodeFile`.

## 137. `SYSTEM.PASCAL` -- `PRINTERROR` written for real, exact, and it is not a straight UCSD port

`PRINTERROR` (segment 3, `PRINTERR` on disk) is the first real segment
body in this file besides `USERPROGRAM`. Its own real content
(`analysis/lifted/128K.PASCAL-1.3-128K.pas.txt`) diverges from UCSD's
`SYSSEGS.A.TEXT` (finding 53's own source) in several places -- Apple
reworded a handful of messages ("No procedure in segment-table" for
UCSD's "No proc in seg-table", "System I/O error" for "System IO
error", and throughout the nested `IORSLT` case), added a 16th
`XEQERR` arm ("Codespace overflow"), **dropped** `IORSLT` arm 15
("ring buffer overflow"), and added `IORSLT` arms 18-20 for the 128K
system's own ProFile hard-drive support ("illegal buffer address",
"must read a multiple of 512 bytes", "unknown ProFile error"). Written
directly from the real binary's own `CASE` arms, in Apple's own words,
not from finding 53's older UCSD text.

`S: STRING[45]`, not UCSD's `STRING[40]`: the real binary's own
`SINSERT` call passes `DESTLENG=45`, which is exactly the longest real
message ("I/O error: " + "must read a multiple of 512 bytes" = 45
characters) -- and `STRING[45]` alone is 23 words, matching Apple's
real `data=23` (`locals 23 words` in the lift) with no other local
needed at all.

Two more calling-convention restrictions surfaced, distinct from
finding 136's `WRITE`/`WRITELN` one:

* **A literal cannot bind to a `VAR` parameter through a direct call**,
  even when the real binary's own compiled code shows the literal
  reaching that exact parameter. `SINSERT(VAR SRC: STRING; ...)`
  called directly with `'I/O error: '` as `SRC` is error 154. Apple's
  own p-code (`analysis/utilities/128K-1.3-APPLE3.pcode.txt`) shows
  `SINSERT` receiving that same literal -- legal there only because the
  compiler generated the call itself while lowering ordinary `INSERT`
  sugar (which copies a literal into a temporary internally before the
  `VAR` parameter ever sees it), not because a direct call to `SINSERT`
  could do the same. Fix: use `INSERT('I/O error: ', S, 1)` sugar, not
  `SINSERT(...)` directly -- unlike `WRITE`/`WRITELN`, `INSERT`'s own
  sugar has no restriction on its own arguments' shape, so this one
  works normally once written as sugar.
* **The real global `OUTPUT`-equivalent `FWRITESTRING`/`FWRITELN` are
  called against (`I1,3`, one lexical level up -- the exact position
  `OUTPUT` itself sits at in every other file this project has
  reconstructed) still isn't identified.** Apple's own built-in
  `OUTPUT` (type `TEXT`/`INTERACTIVE`) does not type-check against
  `FWRITESTRING`'s real `VAR F: FIB` parameter (confirmed directly
  against the host compiler), so whatever is really at that position is
  not the compiler's own predeclared file -- almost certainly
  `OUTPUTFIB`, `GLOBALS.TEXT`'s own name for exactly this role, but
  unconfirmable until `PASCALSY`'s own real global `VAR` layout is
  reconstructed (still a stub). Stood in `OUTPUTFIB^` (this project's
  own declared global) for now, documented rather than guessed at
  further -- it doesn't block compiling or matching this procedure's
  own frame size, which is the check that matters until the globals
  themselves are real.

Verified: `params=4/data=46` exact, first attempt (after the
`SINSERT`->`INSERT` fix) against Apple's real `128K.PASCAL`. Segment
0's own 42-of-43 `params` match (finding 136) held unchanged --
nothing regressed.

Acceptance run `2026-08-29-pascalsystem-printerror`: 0 errors, 474
lines, `PASCALSYS.CODE` extracted and `PRINTERR`'s own procedure
compared directly against Apple's real `128K.PASCAL` via `CodeFile`.

## 138. `SYSTEM.PASCAL` -- the five string primitives (`SCONCAT`/`SINSERT`/`SCOPY`/`SDELETE`/`SPOS`) written for real, all exact, and a second parameter-order divergence found

`COPY`/`DELETE`/`POS`/`CONCAT`/`INSERT` sugar all lower to these five
(finding 52b). Writing their real bodies (`analysis/lifted/
128K.PASCAL-1.3-128K.pas.txt`, `PASCALSY.23`-`27`) surfaced a second
real calling-convention fact, independent of finding 136/137's own two:
**Apple's real declared parameter order for at least this family of
low-level primitives is not UCSD's own literal `GLOBALS.TEXT` order.**

### 138a. How the real order was recovered

Not by assuming a shortcut (a first attempt at "just reverse the
list" fit some of the five and not others -- `SPOS` needs no
reordering at all). Recovered instead by reading each real body's own
algorithm directly and asking which G-numbered word is read from,
which is written to, and which is compared as a plain `INTEGER` versus
dereferenced as a `STRING`'s own length byte -- unambiguous from the
`MOVELEFT`/`MOVERIGHT` argument roles alone (source vs. destination),
regardless of what order anything was declared in:

* **`SCONCAT`** (`PASCALSY.23`): `G1` compared as a plain `INTEGER`
  (`DESTLENG`), `G2` is `MOVELEFT`'s source (`SRC`), `G3` is the
  destination that grows (`DEST`). UCSD's own order is
  `(VAR DEST,SRC: STRING; DESTLENG: INTEGER)`; Apple's real one is
  `(DESTLENG: INTEGER; VAR DEST, SRC: STRING)` -- the value-parameter
  group moved from last to first, the `VAR` pair's own internal order
  (`DEST` before `SRC`) unchanged.
* **`SINSERT`** (`PASCALSY.24`): `G1`/`G2` both plain `INTEGER`s
  (`INSINX`, `DESTLENG` respectively -- `G1` is the shift/insert
  position, `G2` the capacity check), `G3` is `DEST` (shifted right,
  then written into), `G4` is `SRC` (read from). Apple's real order:
  `(INSINX, DESTLENG: INTEGER; VAR SRC, DEST: STRING)`.
* **`SCOPY`** (`PASCALSY.25`): `G1`/`G2` are `COPYLENG`/`SRCINX`, `G3`
  is `DEST` (cleared, then written), `G4` is `SRC` (read from). Real
  order: `(COPYLENG, SRCINX: INTEGER; VAR SRC, DEST: STRING)`.
* **`SDELETE`** (`PASCALSY.26`): `G1`/`G2` are `DELLENG`/`DELINX`,
  `G3` is `DEST` (shifted left over the deleted range). Real order:
  `(DELLENG, DELINX: INTEGER; VAR DEST: STRING)`.
* **`SPOS`** (`PASCALSY.27`) needed **no reordering at all** -- its
  real body's own `G3`/`G4` already match UCSD's own declared
  `(VAR TARGET, SRC: STRING)` order exactly, the one case out of five
  where UCSD's literal text was already right.

None of this touches `WRITE`/`INSERT`/`COPY`/etc.'s own compiler
*sugar* (`PRINTERROR`'s `INSERT('I/O error: ', S, 1)`, finding 137,
compiles independently of whatever this file declares `SINSERT` to
be -- sugar lowers straight to a fixed `CXP` target, not through this
file's own `FORWARD` declarations). It matters only for these five
procedures' own internal content matching Apple's real compiled bytes
at their own procedure numbers.

### 138b. The bodies themselves, and one real miss caught and closed

All five translate the real algorithm directly into structured Pascal
(no `GOTO`s needed for four of them; `SPOS`'s own `GOTO`-based early
exit became a `WHILE` with an explicit `I := J + 1` to end the search,
functionally identical since `I`'s own value is never read after the
loop). `SINSERT`'s real body has a `G5 := 0; IF G5 = 0 THEN ...` right
before its own `MOVELEFT` -- vestigial, since `G5` is unconditionally
reset immediately before the check it guards, so the `MOVELEFT` always
runs; written as the unconditional statement it actually is rather
than reproduced literally.

`SPOS` needed one real fix: a first attempt sized its own local
`CANDIDATE` buffer as `STRING[72]`, reasoning (wrongly) that the
lift's own "locals 44 words" already included the 2 real parameters
plus the function's own result-and-gap overhead, and so subtracted
those a second time. It does not -- confirmed directly against
`SCONCAT`'s own "locals 0 words" matching a real `data=0` -- the
lift's own figure *is* `CodeFile`'s `data` field, params/result/gap
accounted separately. Fixed by declaring `CANDIDATE` a plain default
`STRING` (80 chars, 41 words), closing 44 - 3 (`I`/`J`/`TARGETCHAR`)
exactly.

`SCAN`, `MOVELEFT`, and `MOVERIGHT` are real, documented, directly
user-callable Apple Pascal built-ins ("The SCAN Function", "The
MOVELEFT and MOVERIGHT Procedures" -- `analysis/reference/apple-
pascal-language-reference.txt`), not something this file needs to
`FORWARD`-declare itself; `SCAN(LIMIT, PEXPR, SOURCE)`'s own
`PEXPR` argument is a comparison-operator-plus-character form
(`=CHR(TARGETCHAR)`), matching the manual's own documented examples
exactly.

Verified: all five `params`/`data` exact against Apple's real
`128K.PASCAL`, first attempt for four of five (`SPOS` needed the one
`STRING[72]`->`STRING` fix above). Segment 0's own 42-of-43 `params`
match (findings 136/137) held unchanged.

Acceptance run `2026-08-29-pascalsystem-string-primitives`: 0 errors,
615 lines, `PASCALSYS.CODE` extracted and all five procedures compared
directly against Apple's real `128K.PASCAL` via `CodeFile`.

## 139. `SYSTEM.PASCAL` -- `PASCALSY`'s own global VAR section: two addressing modes told apart, and the first two globals confirmed by offset

Every remaining tractable-looking segment-0 procedure checked this
session (`FGOTOXY`, `HOMECURSOR`, `CLEARSCREEN`, `CLEARLINE`, `PROMPT`,
`SPACEWAIT`, `GETCHAR`) turned out to depend on `PASCALSY`'s own
451-word global `VAR` section, still an unreconstructed placeholder.
This is the first real progress on it, and the piece that unblocks
everything else: telling apart *how* different kinds of procedure
reach it.

### 139a. `G<n>` and `I1,n` are not the same thing, and which one a procedure uses depends on what kind of procedure it is

`analysis/lifted/128K.PASCAL-1.3-128K.pas.txt` shows **both** notations
throughout segment 0, and conflating them was the trap:

* **Flat procedures declared directly inside segment 0's own
  declaration part** (`FGOTOXY`, `SCONCAT`, `SDELETE`, ... -- every one
  of the 41 `FORWARD`-declared procedures findings 136-138 already
  cover) are lexically nested one level inside `PASCALSY`'s own body,
  same segment, no overlay boundary crossed. Their own `G<n>`
  references are **their own parameters and locals** -- confirmed
  already, every one of the five string primitives (finding 138) had
  its `G1`-`G4` match its own declared params/locals exactly, nothing
  left over. To reach `PASCALSY`'s own *globals* from one of these,
  the lift shows `I1,n` -- one static-link level up, the same
  mechanism (and the same "own level + 1" fixed distance) `OUTPUT`
  itself is reached by in every other file this project has
  reconstructed (`SETUP.text` included).
* **`SEGMENT PROCEDURE`s** (`USERPROGRAM`, `PRINTERROR`, `INITIALIZE`,
  `GETCMD`, and `FIOPRIMS`/`FILEPROC`) are each their own separately
  loaded overlay -- no static link back to `PASCALSY`'s own frame
  survives a segment boundary, so they reach shared state a different
  way. `PRINTERROR`'s own `G3` (finding 137, the error-message buffer)
  *is* a true global reference into `PASCALSY`'s own `VAR` section,
  encoded differently (closer to absolute addressing) precisely
  because `PRINTERROR` cannot use the lex-relative form at all.

Both notations name the same 451-word data area; which one a given
call site uses is determined by which side of a segment boundary the
calling code lives on, not by anything about the *variable* itself.

### 139b. `SYSCOM` and `GFILES[1]` confirmed by offset, zero reordering needed

`FGOTOXY`'s own real body (`PASCALSY.29`) clamps its two arguments
against a pointer set to `I1,1 + 37` -- and `SYSCOMREC.CRTINFO.WIDTH`
(ported from `GLOBALS.TEXT`, now declared for real in this file) sits
at exactly that offset from `SYSCOM^`, with `HEIGHT` immediately after
it clamping the other axis. That fixes `I1,1 = SYSCOM`, offset 1 --
`GLOBALS.TEXT`'s own first declared global, no reordering from UCSD's
literal text needed.

`I1,3` -- the target every segment-0 body's own `FWRITESTRING`/
`FWRITELN` call writes through, previously stood in with a placeholder
`OUTPUTFIB^` (finding 137's own documented gap) -- is `GFILES[1]^`,
not a separate variable. `SYSCOM` (1 word) at offset 1, `GFILES`
(`ARRAY [0..5] OF FIBP`, 6 words) starting at offset 2, puts
`GFILES[1]` (0-indexed) at offset 3 exactly, with UCSD's own declared
order (`SYSCOM` then `GFILES`) unchanged -- and matches
`GLOBALS.TEXT`'s own comment on `GFILES` directly ("0=INPUT, 1=OUTPUT").
`OUTPUTFIB` is a real, separate global (`GLOBALS.TEXT`'s own comment:
"GFILES are copies" of it and `INPUTFIB`) -- it is just not what this
particular call site reaches. `PRINTERROR` updated to call
`FWRITESTRING(GFILES[1]^, ...)` in place of the placeholder; still
exact on frame size (`params=4/data=46`, unchanged), and now resting on
real evidence rather than a stand-in.

Also added for real (previously a `^INTEGER` placeholder): the full
`SYSCOMREC` type -- `IORSLT`, `XEQERR`, `SYSUNIT`, `BUGSTATE`, `GDIRP`,
the `MSCWP`/`MSCW`/`TRICKARRAY` mark-stack-record chain (debugger
internals), `MEMTOP`/`SEG`/`JTAB`, `BRKPTS`, `RETRIES`, `EXPANSION`,
`MISCINFO`, `CRTTYPE`, `CRTCTRL`, `CRTINFO`, and `SEGTABLE` -- ported
directly from `GLOBALS.TEXT`, not yet independently verified field by
field beyond `CRTINFO.WIDTH`/`HEIGHT` above.

### 139c. What this does and does not unblock yet

Two offsets confirmed out of what is likely 100+ distinct globals in a
451-word frame -- real progress, not a finished reconstruction.
`FGOTOXY`'s own body can now plausibly be written (bounds-check against
`SYSCOM^.CRTINFO`, matching the pattern just confirmed), but
`HOMECURSOR`/`CLEARSCREEN`/`CLEARLINE` all call an unidentified helper
(`PASCALSY.53`, not among the 41 already-declared procedures -- likely
one of Apple's own 128K-specific additions past procedure 42, finding
51c's own territory) and reference `CRTCTRL`'s own escape-sequence
fields, plus the lift itself flags stack-depth disagreements on
`CLEARLINE`'s own constant-folded conditionals -- genuinely harder than
`FGOTOXY`, not attempted this session. `GETCHAR` references two more
still-unidentified fixed offsets (`I1,58` and thereabouts). Recovering
the rest of the 451 words -- correlating every `G<n>`/`I1,n` reference
across all seven segments' own lifts against `GLOBALS.TEXT`'s declared
order the same way this finding did for the first two -- is the real
scope of the work ahead, not something this session finishes.

Verified: `PRINTERROR` still `params=4/data=46` exact after the
`OUTPUTFIB^`->`GFILES[1]^` change; segment 0's own 42-of-43 `params`
match held unchanged; compiles clean (host and Apple's own) with the
full `SYSCOMREC` type added.

Acceptance run `2026-08-29-pascalsystem-syscomrec`: 0 errors, 686
lines, `PASCALSYS.CODE` extracted and re-verified against Apple's real
`128K.PASCAL` via `CodeFile`.

## 140. `SYSTEM.PASCAL` -- `FGOTOXY` written for real, close, one documented word

The first payoff of finding 139's own `SYSCOM`/`GFILES[1]` work:
`FGOTOXY` (`PASCALSY.29`) clamps `Y` to `SYSCOM^.CRTINFO.HEIGHT` and
`X` to `SYSCOM^.CRTINFO.WIDTH`, then writes the GOTOXY escape (ASCII
30) followed by row and column, each offset by 32, through
`GFILES[1]` -- the same target every other segment-0 body's own
console output goes through.

`params=4` exact (`X`, `Y`, matching Apple's real `args 2 words`).
`data`: mine `0` against Apple's real `2` -- one word short, and
exactly the gap predicted before compiling, not discovered after:
Apple's own real body caches `SYSCOM+37` (the address of `WIDTH`) in
its own local rather than re-reaching `SYSCOM^.CRTINFO` fresh for each
of the two comparisons. Same observable behavior, one fewer local --
documented, not forced, matching this project's own established
practice for a real, understood, immaterial gap (`SETUP4`, `SETUP16`,
several of `LIBMAP`'s procedures).

Verified: `params=4/data=0` against Apple's real `4/2`. Segment 0's own
42-of-43 `params` match held unchanged.

Acceptance run `2026-08-29-pascalsystem-fgotoxy`: 0 errors, 719 lines,
`PASCALSYS.CODE` extracted and `FGOTOXY` compared directly against
Apple's real `128K.PASCAL` via `CodeFile`.

## 141. `SYSTEM.PASCAL` -- `MAXUNIT` is 20, not UCSD II.0's own 12

`GLOBALS.TEXT` (UCSD II.0) declares `MAXUNIT = 12`, and that value had
been carried over unchanged into the reconstruction. It is 1.1's own
figure, not 1.3's. Neil Parker's *Undocumented Secrets of Apple
Pascal* documents the OS's own internal `DISKNUM` table directly:
"a table of 12 (Apple Pascal 1.1) or 20 (Apple Pascal 1.2 and 1.3)
2-byte entries, one for each device from #1: to #12: or #20:" --
raised by the user directly rather than found independently.

Changed `MAXUNIT` to `20`. `UNITABLE: ARRAY [UNITNUM] OF ...` widens
from 13 entries (`0..12`) to 21 (`0..20`), an 8-entry, 48-word (96
byte) growth -- and that is exactly what both compilers show. Host
compiler: `PASCALSY.1`'s own frame grows from 263 to 311 words.
Apple's own real compiler, independently: `data` for procedure 1 goes
from `622` (not recorded as a separate finding at the time) to `622`
-> matches the host figure exactly, `622` bytes = `311` words, against
Apple's real `902` bytes = `451` words -- confirming both the growth
amount and that the two compilers agree with each other on the new
total, still short of the full 451-word target by 140 words (unrelated
still-unrecovered globals, finding 139c's own scope).

No procedure's own `params` moved -- `UNITABLE` is a global, not a
parameter, so this could only ever affect frame *data* sizes, and
segment 0's own 42-of-43 `params` match (procedures 1-42, compared
directly against Apple's real `128K.PASCAL`) held unchanged after the
edit, confirming no regression.

Acceptance run `2026-08-29-pascalsystem-maxunit`: 0 errors, `PASCALSYS.CODE`
extracted and diffed procedure-by-procedure against Apple's real
`128K.PASCAL` via `CodeFile`; `params` match held for 1-42, `data` for
procedure 1 (`PASCALSY.1`, the outer block carrying the global `VAR`
section) now at 311 of 451 words.

## 142. `SYSTEM.PASCAL` -- `MAX_SEG` is 63, not UCSD II.0's own 31

Same pattern as finding 141, same source: Neil Parker's own document
annotates `GLOBALS.TEXT`'s `MAX_SEG = 31` directly ("31 for the 64K
system, 63 for the 128K system"), and the user caught it again before
this session found it independently.

Unlike `MAXUNIT`, this one does **not** move `PASCALSY.1`'s own frame
at all -- `SEG_RANGE = 0..MAX_SEG` only widens `SYSCOMREC.SEGTABLE`
(`ARRAY [SEG_RANGE] OF SEG_ENTRY`), and `SYSCOMREC` is a heap
structure reached through the `SYSCOM: ^SYSCOMREC` pointer, not a
field inside the outer block's own `VAR` section. `SYSCOM` itself
stays a 1-word pointer either way. Confirmed directly: the host
compiler's `PASCALSY.1` frame is unchanged at 311 words after the
edit, and so is Apple's real compiler's -- `data=622` bytes before and
after, byte for byte.

Still a real correctness fix, not a no-op: whatever eventually builds
`SYSCOMREC` at boot (not yet reconstructed) sizes its own allocation
off this constant, and any segment-table walk past index 31 would
silently miss the 128K system's own real 32 extra slots if left at
UCSD's literal value.

No procedure's own `params` moved; segment 0's 42-of-43 `params` match
held unchanged.

Acceptance run `2026-08-29-pascalsystem-maxseg`: 0 errors, 729 lines,
`PASCALSYS.CODE` extracted and diffed procedure-by-procedure against
Apple's real `128K.PASCAL` via `CodeFile` -- `params` match held for
1-42, procedure 1's `data` unchanged at 622 of the 902-byte (311-of-451
word) target, confirming the constant change is inert for this specific
frame as predicted before compiling.

## 143. `SYSTEM.PASCAL` -- the 451-word `VAR` section closed exactly

Finding 139c left 140 words genuinely unaccounted for past `FILENAME`
(UCSD II.0's `GLOBALS.TEXT` own last-declared global). Neil Parker's
document turns out to hold the rest of it: right after `FILENAME` it
transcribes, field by field with a byte offset beside each, every
global Apple itself added past UCSD II.0's own set -- reverse-engineered
and named by Dave Tribby, not read from Apple's own source (`config_char`
through `run_vol`/`what_l`, ~26 fields, ending with an explicit "End of
Apple Pascal global variables"). Two things make this usable as more
than a guess: every single gap between consecutive offsets in that list
matches this file's own already-derived word-size formula exactly, with
zero exceptions across roughly 26 fields (`VID`=8 bytes, `FULL_ID`=24,
`DIRENTRY`=26, a bare `STRING`=82, a `BOOLEAN`=2, and so on); and the
byte offset where the block starts (Parker's own "502 in 1.2 and 1.3,
restarting the count at 0" -- the same `MAXUNIT`-driven 96-byte shift
finding 141 already established) lands exactly on this file's own
already-compiled, Apple-verified total through `FILENAME` (622 bytes =
311 words) -- so Apple's real compiler and Parker's transcription agree
with each other before a line of the new block was even typed.

Added all ~26 fields, named in this file's own `UPPERCASE` convention
with Tribby's own name and function noted per field (`CONFIG_CHAR`,
`CHAIN_NAME`, `CHAIN_MSG`, `WHAT_F`, `EXEC_CH_NUM`, `WHAT_G`,
`R_EXEC_FLG`, `W_EXEC_FLG`, `SWAP_ON`, `SWAP_1_ON`, `SWAP_2_ON`,
`JUST_BOOT`, `WHAT_H`, `EXEC_IN_CH`, `EXEC_TERM`, `WHAT_I`,
`EXEC_UNIT`, `EXEC_VOL`, `EXEC_SIZE`, `WHAT_J`, `EXEC_FENTRY`,
`WHAT_K`, `DLINE_STR`, `BSPACE_STR`, `RUN_VOL`, `WHAT_L`) using the
types Parker's own listing implies from each field's declared purpose
and array bounds. Host compiler: `PASCALSY.1`'s frame lands at exactly
902 bytes (451 words) on the first attempt -- Apple's own real target,
matched exactly, not approached. Apple's own real compiler, run cold
against the same source: **`params=0/data=902`, an exact match** to
the real `128K.PASCAL`'s own procedure 1.

This is labeled STRONG INFERENCE, not VERIFIED SOURCE FACT, for the
field *names* and *individual types* -- Parker/Tribby are "a lead, not
an authority" (project rule) and neither is Apple's own source, and
several fields are honestly unidentified even in Tribby's own telling
(`WHAT_F` through `WHAT_L`, six placeholder names for blocks whose
purpose he never worked out). What the frame-size match against
Apple's real binary *does* verify, as a VERIFIED BINARY FACT: the
total byte count and the field *boundaries* (offsets) -- since a
wrong split between two adjacent fields of different total size would
have changed procedure 1's own frame total, and it did not. Individual
field identities within that boundary set remain to be confirmed the
way `SYSCOM`/`GFILES[1]` were (finding 139) -- by reading real bodies
that reference each offset -- not assumed correct because the sum
came out right.

No procedure's own `params` moved; segment 0's 42-of-43 `params` match
held unchanged. This unblocks `PASCALSY.1`'s own real 451-word main
loop body -- the single largest procedure in the whole disk set, and
the reason this whole `VAR`-section effort was undertaken -- since
every offset it might reference now has a declared field behind it.

Acceptance run `2026-08-29-pascalsystem-varsection-complete`: 0 errors,
780 lines, `PASCALSYS.CODE` extracted and diffed procedure-by-procedure
against Apple's real `128K.PASCAL` via `CodeFile` -- procedure 1
`params=0/data=902`, exact; `params` match held for 1-42 elsewhere.

## 144. `PASCALSY.1` -- the main-loop body started, three lines in, one gap identified precisely

The real p-code (`analysis/lifted/128K.PASCAL-1.3-128K.pas.txt:16-28`)
is short: `FINIT(@L396, @L696, -1)`, `EMPTYHEAP := NIL`,
`UNITCLEAR(1)`, `INITIALIZE`, a `REPEAT ... UNTIL EMPTYHEAP = NIL`
loop around `PASCALSY.48` with a conditional re-`INITIALIZE`, then
`FCLOSE(@L396, 0)` and `XIT`. Wrote the three lines that need nothing
further resolved: `EMPTYHEAP := NIL`, `UNITCLEAR(1)` (CSP 38, a plain
callable builtin -- the host compiler accepts it directly, no
declaration needed), and `INITIALIZE` (this file's own segment
procedure). Frame size held exact at `902` both before and after, as
expected -- none of these three add a local.

Two pieces left out, both genuinely unresolved rather than guessed:

* **`FINIT(@L396, @L696, -1)` / `FCLOSE(@L396, 0)`.** `LLA 696`
  exceeds this file's own confirmed 451-word frame outright -- and
  that turns out to already be explained by this project's own prior
  work, not a new problem. Findings 43a/118c already established that
  the compiler emits a file variable's `WINDOW` argument as a fixed
  `VADDR + FILESIZE` (`FILESIZE = 300`) for *every* file-typed
  variable's auto-generated `FINIT` call, "harmless: ... the pointer
  is never dereferenced" -- and `396 + 300 = 696` exactly. So `@L696`
  needs no real storage; only `@L396` does. But that call is very
  likely compiler-generated initialization for a real file-typed
  `VAR` (finding 43a's own `bodypart.e.text` excerpt: "the loop that
  initialises a block's file variables"), which means one of this
  file's currently `FIBP`-typed globals (`INPUTFIB`/`OUTPUTFIB`/
  `SYSTERM`/`SWAPFIB`, offsets 55-58) is likely mis-typed relative to
  Apple's real source -- and word 396 sits inside finding 143's own
  Tribby-derived block, around `EXEC_VOL`/`EXEC_SIZE`/`WHAT_J`, whose
  real identity there needs re-examining before this line can be
  written for real, not assumed correct because the frame total came
  out right (finding 143 already flagged this same risk for that
  region generally).
* **`PASCALSY.48()`.** Past the 41/42 forward-declared procedures
  this file has (finding 136) -- new territory. Its own small body
  (`analysis/lifted/128K.PASCAL-1.3-128K.pas.txt:1033-1042`) sets
  `STATE := HALTINIT`, clears an exec-related flag, then loops calling
  `PASCALSY.50`/`PASCALSY.58` and conditionally `USERPROG.1(NIL,
  NIL)` -- but procedures 44-58 have no source in this file at all
  yet. Writing them is the natural next step.

Compiles clean both tiers, `params=0/data=902` still exact against
Apple's real `128K.PASCAL`; segment 0's 42-of-43 `params` match held
unchanged.

Acceptance run `2026-08-29-pascalsystem-mainloop-start`: 0 errors, 839
lines, `PASCALSYS.CODE` extracted and diffed -- procedure 1
`params=0/data=902`, still exact.

## 145. `PASCALSY.1`'s `FINIT`/`FCLOSE` resolved -- `EXEC_FILE: FILE`, not seven small fields

Finding 144 left `FINIT(@L396, @L696, -1)`/`FCLOSE(@L396, 0)` open:
`LLA 696` exceeds this file's own 451-word frame, and word 396 sits
inside finding 143's own speculative Tribby-derived block, mapped at
the time to `WHAT_I` (an "unidentified 7-word block").

Ran the compiler's own real p-code, not more guessing. Adding two
temporary probe statements to `PASCALSY.1`'s own body (`WHAT_I[7] :=
WHAT_I[7]`, `EXEC_UNIT := EXEC_UNIT`, etc.) and disassembling the host
compiler's output for this file directly gave the exact offsets this
file's own declarations actually compile to: `WHAT_I` starts at word
**396** -- exactly `@L396`. Then two things closed it:

* **The silence test.** `WHAT_I` through `WHAT_K` (Tribby's seven
  guessed fields spanning that region) sum to exactly **40 words**,
  and `grep`ing the *entire* lifted disk set for `I1,397` through
  `I1,435` (every offset strictly inside that 40-word span) returns
  **nothing** -- not one reference anywhere, in any of the seven
  segments. A real set of seven separately-used named fields would be
  read or written individually somewhere; an opaque file-record blob,
  touched only through its own boilerplate `FINIT`/`FCLOSE` and
  through `GET`/`PUT`-style primitives that never emit raw `LDL n`
  for its interior, would not be.
* **The size match.** 40 words is exactly `NILFILESIZE` (finding
  43a's own constant, "a bare `FILE` is 40" words) -- the size the
  compiler gives an *untyped* `FILE` variable, independent of whatever
  it's actually used for.
* **Independent confirmation from the neighbors.** Two real
  `FWRITESTRING(I1,3, @I1,436, 0)` / `(..., @I1,440, 0)` calls in
  `PASCALSY.54` (the delete-line/backspace routine) land exactly on
  where `DLINE_STR`/`BSPACE_STR` (the very next declared fields,
  finding 143) actually compile to in this file -- confirmed directly
  against the same probe-disassembly, not assumed.

Collapsed `WHAT_I`/`EXEC_UNIT`/`EXEC_VOL`/`EXEC_SIZE`/`WHAT_J`/
`EXEC_FENTRY`/`WHAT_K` (seven fields) into one `EXEC_FILE: FILE;` --
an untyped file, still in the EXEC-file-handling region Tribby's own
comments describe throughout, matching finding 43a's own
`bodypart.e.text` pattern: the compiler auto-generates a `FINIT` call
at block entry and an `FCLOSE` at block exit for *any* file-typed
`VAR`, with no source written for either. Frame held exact (`902`
bytes, unchanged -- the seven fields summed to the same 40 words as
the one that replaced them). Host compiler confirmed the auto-
generated entry code first: `LLA 396`, `LLA 696`, `LDCI 1`, `NGI`,
`CXP 0,3` -- appearing with **zero source written for it**, purely
from declaring `EXEC_FILE`.

Apple's own real compiler, run cold against the same source, produced
the **exact same instruction sequence**, byte for byte: entry `LLA
396 / LLA 696 / LDCI 1 / NGI / CXP 0,3`, exit `LLA 396 / SLDC 0 / CXP
0,6 / XIT` -- an exact match to the original lift's own `FINIT(@L396,
@L696, -(1))` ... `FCLOSE(@L396, 0); XIT`. `params=0/data=902` held
exact throughout; segment 0's 42-of-43 `params` match held unchanged.

This closes finding 144's own remaining `FINIT`/`FCLOSE` gap entirely
-- `PASCALSY.1`'s only unwritten piece is now the `REPEAT` loop's own
`PASCALSY.48` call, which needs procedures 44-58 written first.

Acceptance run `2026-08-29-pascalsystem-execfile-finit`: 0 errors, 862
lines, `PASCALSYS.CODE` extracted -- procedure 1's compiled
instruction stream (entry through the `INITIALIZE` call) matches
Apple's real p-code byte for byte, including the auto-generated
`FINIT` call neither this file nor its author wrote a line of source
for.

## 146. `WHAT_F` was two pointers, `WHAT_H` was two booleans -- more of finding 143's own Tribby split corrected

Probing this file's own compiled offsets directly (temporary statements
referencing every finding-143 field in `PASCALSY.1`'s own body,
disassembling the host compiler's output) turned up two more spots
where Tribby's own guessed grouping was wrong in structure though
right in total size -- the same pattern finding 145 already found for
`WHAT_I`-`WHAT_K`:

* **`WHAT_F` (word 381-382, declared `ARRAY[1..2] OF INTEGER`) is
  really two pointers.** `analysis/lifted/128K.PASCAL-1.3-128K.pas.txt:
  2707`: `NEW(@I2,381, 256)` -- word 381 is a pointer, heap-allocating
  the 256-word (512-byte) EXEC read/write buffer at runtime, not a
  4-byte static array slot. Word 382 mirrors `EMPTYHEAP` exactly
  (`I2,382 := I2,54` on entry to EXEC mode, `I1,54 := I1,382` on exit,
  `PASCALSY.45`) -- a saved heap mark, same pointer type as
  `EMPTYHEAP` itself, used to `RELEASE` the buffer's own allocation
  when EXEC processing finishes. Split into `EXBUFPTR: WINDOWP`
  (typed to match `FINIT`/`FBLOCKIO`'s own parameter with no coercion,
  not a new array type of this file's own invention) and
  `EXEC_MARK: ^INTEGER`.
* **`WHAT_H` (word 392-393, declared `ARRAY[1..2] OF INTEGER`) is
  really two booleans.** `PASCALSY.57`: `not (I2,390) or I2,392` --
  used directly as an `OR` operand, which Pascal requires to be
  `BOOLEAN`, not `INTEGER`. `PASCALSY.45`: `I1,393 := (I1,54 = nil)`
  -- a plain boolean assignment. Split into `WHAT_H1`/`WHAT_H2:
  BOOLEAN` (both still Tribby-unidentified in *purpose*, unlike
  `EXBUFPTR`/`EXEC_MARK` above -- only the *type* is corrected here).

Both splits are same-word-count swaps (2 words either way), so
`PASCALSY.1`'s own frame held exact at `902` bytes throughout -- these
fixes were required to make procedures 44-47 (finding 147) *compile*
under real boolean/pointer semantics, not to close any further size
gap.

## 147. `PASCALSY.44`-`47` -- the EXEC-file buffered I/O layer, written for real

Past the 41/42 UCSD-declared set (finding 136) -- genuinely new
territory, no UCSD source and no Tribby name (his own document covers
data, not procedures). Four short bodies straight from the lift
(`analysis/lifted/128K.PASCAL-1.3-128K.pas.txt:965-1031`), named for
what they do rather than any recovered name: `EXECPUTCH(CH)` appends
one character to the write buffer (`EXBUFPTR`), auto-flushing near the
512-byte boundary and auto-closing on a doubled terminator character;
`EXECCLOSE(WASNORMAL)` closes the exec file, either read side (plain)
or write side (padding a doubled terminator + CR first when normal),
then restores `EMPTYHEAP` from `EXEC_MARK`; `EXECREADBLK`/
`EXECWRITEBLK` move one 512-byte block through `EXEC_FILE`
(finding 145).

Two real compiler-syntax lessons surfaced writing these, both
resolved by precedent already established elsewhere in this project
rather than guessed at:

* **`FCLOSE`/`FBLOCKIO` cannot be called directly on `EXEC_FILE`.**
  The host compiler rejects it outright: `EXEC_FILE` is a raw `FILE`,
  `FCLOSE`'s/`FBLOCKIO`'s own declared parameter is `VAR F: FIB` --
  different types under normal type-checking, even though the p-code
  the compiler *auto-generates* for `FINIT` (finding 145) uses exactly
  this address with no such complaint (compiler-generated code, not
  type-checked user Pascal). The fix is the standard Pascal sugar
  instead -- `CLOSE(EXEC_FILE[, LOCK])` and
  `BLOCKREAD`/`BLOCKWRITE(EXEC_FILE, buffer, nblocks, blocknum)` --
  already established, working precedent in this project's own
  verified `PASCALCO.text` (`BLOCKREAD(LIBRARY, SEGDICT, 1, 0)`,
  `CLOSE(LP, LOCK)`), confirmed directly against the language
  reference manual's own "Opening and Closing Files" / built-in
  procedures section.
* **`SCAN`'s real 3-argument form, not the lift's raw 6-operand
  dump.** The lift renders `PASCALSY.46`'s real backward buffer scan
  as `SCAN(-(511), 0, 13, I1,381, 511, 0)` -- not literal, re-typeable
  syntax (`SCAN` is a special CSP whose true form the lift's generic
  renderer doesn't reconstruct, same caveat finding 138b already
  documented for `SPOS`). The manual's own `SCAN(LIMIT, PEXPR,
  SOURCE)` -- `LIMIT` negative scans backward and returns a negative
  count, `PEXPR` a match/mismatch operator plus character (`=CH`),
  `SOURCE` the starting element -- gives `SCAN(-511, =CHR(13),
  EXBUFPTR^[511])`, matching finding 138b's own `SPOS` precedent
  exactly (`SCAN(J-I, =CHR(TARGETCHAR), SRC[I])`).

`46`/`47` both compile to Apple's real `data=0` -- no room for a local
`STRING` to hold an error message literal (and finding 137's own
literal-to-`VAR`-parameter restriction rules out passing one directly
to `FWRITESTRING`). Reused the already-declared global `PL: STRING`
("promptline string") as scratch instead of adding a local, the same
zero-extra-cost move `PRINTERROR` makes with its own local `S`
(finding 137) but via an existing global instead, since these two
procedures' own real frames have no local budget at all.

Verified: all four `params`/`data` exact against Apple's real
`128K.PASCAL` (`44: 2/0`, `45: 2/0`, `46: 0/0`, `47: 0/0`), first
attempt after the `CLOSE`/`BLOCKREAD`/`BLOCKWRITE`/`SCAN`/`PL` fixes
above. `PASCALSY.1`'s own frame held exact at `902` throughout;
segment 0's 42-of-43 `params` match held unchanged.

Acceptance run `2026-08-29-pascalsystem-exec-44-47`: 0 errors, 1000
lines, `PASCALSYS.CODE` extracted and diffed procedure-by-procedure --
44-47 all exact, procedure 1 still `902`/`902`, nothing else
regressed.
