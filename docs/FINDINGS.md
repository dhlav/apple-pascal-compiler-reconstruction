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

## 16. Open questions

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
