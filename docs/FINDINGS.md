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

`tools/pdfpage.py` renders pages to PNG for reading. The book is not
redistributed in this repo; point the tool at your own copy.

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

Not yet resolved: `PASCALCO.9`, `.15`, `.16`, `.17` are a family of small
routines sharing a 3-word parameter list, three of them functions, that
consult word 59 and each other. They look like the type-comparison helpers
of a Pascal compiler, but nothing yet pins them down.

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

**Still open.** Both procedures carry a block of word data between their
last `RTS` and their attribute table — `$14CE`-`$150C` in IDSEARCH,
`$1592`-`$15A0` in TREESEARCH. Linker relocation lists are the obvious
guess, since the 26 index words are absolute references needing fixup, but
the values have not been made to fit and are emitted as raw bytes rather
than described as something they may not be.

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

## 16. Open questions

* ~~**Non-standard CSPs.**~~ Resolved by finding 17: the full table is now
  named and aritied from interpreter source, and CSP 21/22 are the compiler
  phase dispatch. TommyGoog's `LIBMAP.CODE` cross-reference is no longer
  needed for this.
* **The file-variable block layout.** The four FIBs sit at words 535, 586,
  626, 666 — spacings of 51, 40, 40 — and their window buffers at 835, 886,
  926, 966, with *identical* internal spacing and a constant +300 offset
  between the two groups. A UCSD `FIB` is a large variant record whose
  size depends on the `FSOFTBUF` variant, so the non-uniform spacing is
  plausible, but the exact layout has not been resolved and the parallel
  structure of the two groups is unexplained. Do not assume these are two
  arrays.
* One word of the 1222-word global area in 1.1 is unaccounted for.
* ~~`$D1`-`$D6` are unidentified.~~ Resolved by finding 17: `STE`, `NOP`,
  `EFJ`, `NFJ`, `BPT`, `XIT`. Still none of them occur in SYSTEM.COMPILER.
* `PASCALCO.9`, `.15`, `.16`, `.17` (finding 12) are unnamed.
* Segment 1.1 PASCALCO proc 1 has `lex=0`; every other procedure in the
  compiler has lex 1 or greater. Consistent with it being the outermost
  program block, but the lex-level convention has not been pinned down.
