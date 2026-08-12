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

## 16. Open questions

* **Non-standard CSPs.** See findings 14 and 15. Still unnamed and
  un-aritied: CSP 6, 22, 23, 24, 32, 33, 36. The most valuable next move is
  probably TommyGoog's: cross-reference `LIBMAP.CODE` / `LIBRARY.CODE`,
  both of which are on the 1.3 disk already in `evidence/`.
* **The file-variable block layout.** The four FIBs sit at words 535, 586,
  626, 666 — spacings of 51, 40, 40 — and their window buffers at 835, 886,
  926, 966, with *identical* internal spacing and a constant +300 offset
  between the two groups. A UCSD `FIB` is a large variant record whose
  size depends on the `FSOFTBUF` variant, so the non-uniform spacing is
  plausible, but the exact layout has not been resolved and the parallel
  structure of the two groups is unexplained. Do not assume these are two
  arrays.
* One word of the 1222-word global area in 1.1 is unaccounted for.
* `$D1`-`$D6` are unidentified. They do not occur in SYSTEM.COMPILER, so
  they cost nothing here, but a complete decoder would want them. Hyde ch.5
  documents them somewhere in pp. 151-306.
* `PASCALCO.9`, `.15`, `.16`, `.17` (finding 12) are unnamed.
* Segment 1.1 PASCALCO proc 1 has `lex=0`; every other procedure in the
  compiler has lex 1 or greater. Consistent with it being the outermost
  program block, but the lex-level convention has not been pinned down.
