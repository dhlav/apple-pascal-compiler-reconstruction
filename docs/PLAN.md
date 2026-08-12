# Reconstruction plan

Recover Apple Pascal compiler source faithful enough that recompiling it
reproduces the historical P-code. Readable pseudocode is not the target.

**Final deliverable is 1.3.** Analysis still leads with 1.1, for two
reasons: it is the simpler artifact (no native code at all), and 1.3 is a
recompile of a lightly edited 1.1 source, so 1.1 results transfer. Finding
11 makes the transfer mechanical — 131 procedures and 128 globals are
already mapped across, with zero contested entries. Every new 1.1 fact
should be pushed through that table and checked against 1.3 rather than
left version-specific.

Two things are 1.3-only and have no 1.1 counterpart, so they need their own
track: the native `IDSEARCH` and `TREESEARCH` procedures (finding 6a), and
whatever source-level changes produced the ~130-word growth in globals.

## Status

Done, and reproducible via `python tools/build_all.py`:

* Pascal filesystem, codefile, segment and procedure-attribute readers.
* A UCSD II.0 p-code decoder that passes a strict self-check on all 287
  p-code procedures across both disks.
* Full annotated listings for every segment of both versions.
* Call graph and call-site index, with argument-setup context per site.
* UCSD II.0 OS source unpacked from `ii0src.sdk`, and the segment-0
  procedure numbering recovered from it.
* **Global data map** for both versions (finding 10): area sizes, every
  touched offset with access counts and shape evidence, the four file
  variables, the identifier buffer.
* **1.1 to 1.3 correspondence** for procedures and globals (finding 11).
* **Procedure profiles** for every routine, and first names for the
  PASCALCO service layer (finding 12).

## Next steps

1. **Finish naming the PASCALCO service layer.** Eight routines are named
   (finding 12). Still open: `PASCALCO.9`, `.15`, `.16`, `.17` — a family
   sharing a 3-word parameter list that consults global 59. Read their
   listings alongside the type-handling code in DECLARAT.

   Do not promote any name into reconstructed source until its call sites
   agree on arity and argument kinds.

2. **Extend the global map into a declaration order.** The map now knows
   sizes and shapes; the remaining step is to lay the objects out in
   declaration order and give them types, which is what a reconstructed
   `VAR` block has to reproduce. Words 3..7 (a record with addressed
   fields) and 131 (13 x 8-char entries) are the models to work from.

3. **Match phases to the published UCSD compiler structure.** Segment names
   (DECLARAT, BODYPART, ROUTINE, STATEMEN, CASESTAT, FORSTATE, BODY1,
   BODY3, UNITPART, COMPOPTI, NUMSTRIN, FINISHUP) map onto the standard
   UCSD/Zurich P2 compiler organisation. Use published UCSD compiler
   listings for structure. Note that `ii0src.sdk` cannot help here — it is
   the OS, not the compiler (finding 8).

4. **Lift p-code to structured Pascal, one procedure at a time.** Start
   with the leaves: `PASCALCO.7`, `.9`, `.13`, `.15`, `.16`, `.17` call
   nothing and are 9-63 bytes each. Build a small structuriser over the
   existing `Insn` stream (FJP/UJP/XJP into if/while/case).

5. **Resolve the non-standard CSPs**, especially `CSP 21`/`CSP 22`
   (finding 12), before reconstructing PASCALCO's phase dispatch, which
   cannot be expressed without them. Both versions need this equally.

6. **Work the 1.3 delta.** Two 1.3-only tracks:
   * A 6502 disassembler for the two native procedures, and a
     reconstruction of `IDSEARCH`/`TREESEARCH` in assembly. 1.1's
     `CSP 7`/`CSP 8` call sites give the required semantics; note
     `TREESEARCH` gained two parameters.
   * Account for the ~130-word growth in globals. The correspondence table
     localises the insertions to a few points; read off which offsets are
     new in 1.3 and classify them with the same evidence pipeline.

7. **Validation loop.** Compile reconstructed source under the target Apple
   Pascal release in an emulator and diff generated p-code against the
   original, using the same decoder on both sides. Equivalence at the
   p-code level is the acceptance test. Validate against 1.1 first — it is
   the cleaner target and the compiler that would have built 1.1's own
   source — then carry the result to 1.3 through the correspondence table.
   Start from TommyGoog's configuration (finding 15): AppleWin with **four
   disk drives**, which the Apple Pascal compiler requires. Nothing of this
   exists in the repo yet.

8. **Improve the lifter** (finding 13). Two concrete gaps: merge
   predecessor stacks at control-flow joins so argument lists that straddle
   a join resolve, and add structuring so `if not (c) then goto L` becomes
   `if`/`while`/`repeat`/`case`. Both are prerequisites for stage two —
   turning pseudo-Pascal into compilable Pascal.

## Working rules

* Label every claim: VERIFIED BINARY FACT / VERIFIED SOURCE FACT / STRONG
  INFERENCE / SPECULATION. The inherited work's biggest failure was a
  mislabelled inference promoted to a headline correction.
* Nothing in `evidence/` is ever modified.
* Everything in `build/`, `analysis/`, `reference_source/` is generated.
  Never hand-edit it; change the tool and rerun `tools/build_all.py`.
* Prefer a check the binary can fail — but check that it *can* fail for the
  property you care about. The 287/287 sync check is worthless for the
  short-form opcode ranges, because every candidate split is one byte wide
  either way; it took a separate semantic test to catch an off-by-eight
  that had been corrupting every low global offset (finding 7). Ask what a
  passing check actually rules out.
* Hyde's *P-Source* (finding 7a) settles p-machine questions directly. Use
  it before inferring.
* When a 1.1 fact is established, push it through the correspondence table
  and confirm it holds in 1.3. Divergences are findings, not noise.
