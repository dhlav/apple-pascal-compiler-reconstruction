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
value only `if (n > NEXTSEG) and (n < 31)` — the 64K bound, on the nose,
with the default sitting at the bottom of the documented range.

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

    until (SY in (STATBEGSYS + {endsy,unitsy,implementationsy}));

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
  arrays. (Which file is which *is* now known — finding 23d.)
* One word of the 1222-word global area in 1.1 is unaccounted for.
* ~~`$D1`-`$D6` are unidentified.~~ Resolved by finding 17: `STE`, `NOP`,
  `EFJ`, `NFJ`, `BPT`, `XIT`. Still none of them occur in SYSTEM.COMPILER.
* ~~`PASCALCO.9`, `.15`, `.16`, `.17` (finding 12) are unnamed.~~ Resolved
  by finding 22.
* Two members of the `structform` enumeration, `power` at 4 and `records`
  at 6, are inferred from the gap rather than observed (finding 22b).
* Word 4 of the `identifier` variant part — the 13-word `klass` — has no
  name yet. `klass` 3 and 4 both need one.
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
* `{$U-}` producing `lex=-1` is inferred, not observed: neither disk in
  `evidence/` carries `SYSTEM.PASCAL`, the one artifact on hand known to
  have been built that way. Adding a boot disk would settle it — the same
  addition finding 6's `SYSTEM.LIBRARY` question is waiting on.
