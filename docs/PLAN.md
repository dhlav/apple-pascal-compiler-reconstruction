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

1. ~~**Finish naming the PASCALCO service layer.**~~ **Done** (finding 22).
   `.9`, `.15`, `.16`, `.17` are `GETBOUNDS`, `STRING`, `STRINGTYPE` and
   `LONGSIZE`; `.5` = `ENTERID` and `.18` = `CONSTANT` came with them.
   Fourteen routines are now named, in `tools/a2pascal/names.py`, and the
   lifter renders them.

   What is left of this track is the rest of PASCALCO — 15 of its 29
   procedures still have no name — and the phase segments, none of which
   have been touched. The method that worked: find code that builds a
   structure out of constants and then *names* it, and read outwards.

   Do not promote any name into reconstructed source until its call sites
   agree on arity and argument kinds.

2. **Extend the global map into a declaration order.** The map now knows
   sizes and shapes; the remaining step is to lay the objects out in
   declaration order and give them types, which is what a reconstructed
   `VAR` block has to reproduce. Words 3..7 (a record with addressed
   fields) and 131 (13 x 8-char entries) are the models to work from.

   Two anchors from finding 17: `LDO n` addresses `BASE + 2n + 10`, and word
   0 is never referenced on either disk, so the first declared global is at
   operand 1. Also fold in the `RNP` result-width census — 19 of the 287
   procedures are functions, all returning one word — since every one of
   those needs a `function`, not a `procedure`, header with a matching
   result type.

   Finding 22 supplies the first real block of it: twelve named globals in
   each release, and — more useful — the two record types nearly all of
   them point at, `structure` and `identifier`, with field offsets and two
   enumerations (`structform`, `klass`). Those are `TYPE` declarations the
   reconstruction needs verbatim, and they come with a constraint: get the
   member order of `structform` wrong and every `form` comparison in the
   compiler shifts. Two of its members are still inferred from the gap.

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

5. ~~**Resolve the non-standard CSPs.**~~ **Done** (finding 17). The whole
   table is named and aritied from interpreter source and confirmed against
   the binary; `CSP 21`/`22` are `LOADSEGMENT`/`UNLOADSEGMENT`, and
   PASCALCO's phase dispatch is now readable. What is left is downstream:
   write the dispatch back out as Pascal, and note that it lives in the
   procedure *exit* sequences, which `disassemble(enter_ic, exit_ic)` does
   not cover — anything that walks only procedure bodies will miss it.

6. **Work the 1.3 delta.** Two 1.3-only tracks:
   * *Native procedures — disassembly done* (finding 19). Both are
     disassembled cleanly in `analysis/native/`, identified as `IDSEARCH`
     (PASCALCO.2) and `TREESEARCH` (PASCALCO.3), and their signatures are
     known, so all 287 procedures now lift. The reserved-word table
     embedded in IDSEARCH is decoded, including the compiler's `SY`/`OP`
     symbol codes for all 42 reserved words — feed those into step 2, since
     a reconstruction has to declare that enumeration.

     What remains: turn the two listings into assembly source that
     reassembles to the same bytes, and identify the word-data block each
     carries after its last `RTS` (probably linker relocation lists).
     `evidence/reference/tribby-idsearch-treesearch-1.2.asm` is a good
     structural model but is 1.2 — corroboration, not authority.
   * Account for the ~130-word growth in globals. The correspondence table
     localises the insertions to a few points; read off which offsets are
     new in 1.3 and classify them with the same evidence pipeline.

     First two identified (finding 22b): 1.3 adds the standard types
     `BYTESTREAM` and `WORDSTREAM`, at globals 57 and 58, entered by name
     in COMPINIT alongside `INTEGER` and `STRING`. They are also the
     cleanest available proof of what word 7 of a type descriptor means,
     since `BYTESTREAM` is a packed char array that is deliberately *not*
     a `STRING`.

7. **Validation loop**, now in two tiers (finding 18).

   * *Fast tier, new:* build `ucsdpsys_compile` / `ucsdpsys_disassemble`
     from Peter Miller's `ucsd-psystem-xc` and run reconstructed source
     through them on the host. This catches source that does not compile or
     that compiles to visibly wrong structure, in seconds and with no
     emulator. Neither tool has been built yet.
   * *Acceptance tier, unchanged:* recompile under the target Apple Pascal
     release in an emulator and diff generated p-code against the original,
     using the same decoder on both sides. Start from TommyGoog's
     configuration (finding 15): AppleWin with **four disk drives**, which
     the Apple Pascal compiler requires.

   Keep the tiers distinct. `ucsdpsys_compile` is a modern reimplementation
   and will not emit byte-identical p-code for equivalent source, so it can
   only ever falsify, never accept. Validate against 1.1 first — it is the
   cleaner target and the compiler that would have built 1.1's own source —
   then carry the result to 1.3 through the correspondence table.

8. **Improve the lifter** (findings 13, 20, 21). Both halves done.

   * *Stack merging at joins — done.* Entry stacks are the fixed-point
     merge of predecessors', with `phi` for equal-depth disagreement and an
     explicit report for unequal depth. Unattributed stack values across
     both releases: 542 → 22.
   * *Control-flow structuring — done, 70%* (finding 21).
     `tools/a2pascal/structure.py`. **201 of 287 procedures come out with
     no goto at all**; 1390 gotos remain over 6252 blocks. Both correctness
     invariants — no dropped statements, no dangling gotos — hold at zero,
     and `tools/probes/probe_structure.py` re-checks them, so a regression
     here is visible rather than silent.

     To push past 69%, look at what the structurer refuses: it rejects any
     construct whose blocks jump outside it. That is the honest answer for
     short-circuit boolean evaluation and for `exit`, and those are most of
     what is left. Handling short-circuit `and`/`or` as expression-level
     constructs rather than control flow is probably the single biggest
     remaining win.

   Also open, and harder: 91 joins where the two paths disagree on stack
   depth. Mostly UCSD sets, which are variable-length at runtime, so a
   static word-count model cannot always size them. Do not "fix" these by
   loosening the merge — the report is what makes a wrong callee arity
   findable, which is how finding 20a was found.

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
