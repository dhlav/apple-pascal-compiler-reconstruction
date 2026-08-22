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

   ~~**Finish naming the PASCALCO service layer.**~~ **Done** (finding 22).
   `.9`, `.15`, `.16`, `.17` are `GETBOUNDS`, `ISSTRING`, `STRINGTYPE` and
   `LONGSIZE`; `.5` = `ENTERID` and `.18` = `CONSTANT` came with them.
   Fourteen routines are now named, in `tools/a2pascal/names.py`, and the
   lifter renders them.

   The phase segments are now started too: `BODYPART.3/4/5/6/27` are the
   compiler's five code emitters, and `BODYPART.25` its block-body
   generator (finding 24c). `NEXTLINE` and `SKIP` came out of finding 26,
   and `NEXTBLOCK`, `BUMPSEG`, `NEWSEGMENT`, `COMPTYPES`, `EMITWORD`,
   `BLOCK` and `COMMENT` out of finding 27. Finding 28 finished the
   segment with `SEGINFO`, `ENDSEGMENT`, `COMPILE`,
   `HOLDMOST` and `HOLDROUT` — **all 29 of PASCALCO's
   procedures are now named**, and it carried three code-generation
   routines in the phase segments with it: `BODY3.1` (which
   finding 30 then showed the codefile already names, `BODY3`),
   `BODYPART.13:NEWPROC` and `BODYPART.16:EMITJUMP`.

   The lever that worked in finding 27 is worth reusing: the manual's
   error list (II-3E) names what every `ERROR(n)` means, so a routine's
   error numbers say what it is for before its code is understood.
   `BUMPSEG` was named off error 354 alone.

   Finding 28 added a second lever, and it is the better one where it
   applies: **the manual documents the compiler's own output formats**, so
   a routine that writes one is named column by column. `ERRORWITHTEXT`
   fell to Part II's description of the compiled listing — five globals
   named at once, including Pascal-P's `dp` — and `ENDSEGMENT` to the
   codefile's procedure dictionary. Prefer these to reading control flow:
   an output format is a fixed target the binary can be held against.

   **Every name must survive Apple Pascal's 8-character rule** (finding
   29). Only the first eight significant characters count, underscores are
   ignored and case is folded, so two names alike in eight characters are
   one identifier, a name folding onto a reserved word is refused outright,
   and a name folding onto a predeclared identifier silently steals its
   meaning for the whole scope. `tools/probes/probe_identifiers.py`
   enforces all three against the registry. A name we invent is eight
   characters or fewer, so that what we write is what the compiler sees;
   longer spellings are for names the evidence forces.

   And the cautionary half of finding 28: a probe that verifies a property
   of the *output* does not verify a claim about which code produced it.
   `probe_attribtable.py` was green throughout the period finding 27b was
   wrong, because every assertion in it was about the codefile and none
   was about `PASCALCO.23`. When the claim is "routine X emits Y",
   reconstruct Y from X's own logic and diff it against the bytes —
   `probe_segtail.py` is the pattern.

   Finding 32 supersedes most of this track's guesswork: the UCSD II.0
   compiler source is now in `evidence/`, and 56 names were corrected
   against it. It is not an answer key — Apple changed the segmentation,
   the segment numbering and the option letters — but any name we invent
   should now be checked against it first, and `probe_identifiers.py`
   requires every spelling over eight characters to appear there.

   Finding 30 then added fifteen names for free, and a rule worth keeping
   ahead of all the levers above: **before inventing a name, ask whether
   the artifact already carries one.** The codefile's SEGNAME field holds
   the first eight characters of each segment procedure's identifier, so
   procedure 1 of every segment names itself — and one name invented two
   findings earlier, `BODY3.1:ENDPROC`, turned out to be `BODY3`.

   The same finding recovers the declaration skeleton from the segment
   procedures' lexical levels, which is a constraint on the reconstruction
   rather than a convenience: the level is emitted into every
   `LOD`/`LDA`/`STR` and into every attribute table, so nesting a segment
   procedure at the wrong depth changes the code bytes.

1. ~~**Finish naming the PASCALCO service layer.**~~ **Done, and then
   some** — finding 37 closed the last five segments and finding 42 the
   three procedures 1.3 adds, so **every procedure in both binaries has a
   name**: 142 in 1.1 and 147 in 1.3, without exception. What is left of
   this track is only tightening the spellings that are still ours.

   The notes below are kept for the levers, which transfer to the global
   map and to the 1.3 delta.

   Finding 36 closes `BODYPART` — **37 of 37** — which with `PASCALCO`,
   `DECLARAT`, `ROUTINE` and `STATEMEN` leaves only `COMPINIT`,
   `UNITPART`, `COMPOPTI`, `NUMSTRIN`, `FINISHUP`, `WRITELIN` and the
   three one-procedure segments. It also corrected a name of ours:
   `BODYPART.25` was `BODY`, and `BODY` turned out to be its *parent*,
   `.24` — the fourth reminder that a name should be placed against the
   structure around it, not against its own body alone.

   Finding 35 closes `ROUTINE` as well — **seventeen of seventeen** — and
   adds the sharpest lever yet for the remaining segments: **a routine
   that emits code names itself**, because the opcode it emits is a
   literal operand in the binary and II.0's comment says what that opcode
   is. Prefer this to call sets wherever the routine is a code generator.
   It also gave five `BODYPART` names for free, and one warning worth
   carrying: `BODYPART.7` has II.0's `GENNR` *role* but not its body, so
   check the body before adopting a name, not just the call sites.

   Finding 34 closes `DECLARAT`, the first whole phase segment: **twenty of
   twenty named**, at identical numbers in both releases. The lever there
   is the one to reuse on `ROUTINE`, `UNITPART` and the rest of
   `BODYPART` — II.0 fixes each procedure's parameters, its declaration
   nesting and the calls it makes, the codefile fixes all three
   independently, and demanding that they agree *jointly* leaves no room
   to shuffle names between procedures. Where two candidates share a call
   set, look for a global one writes and the other does not:
   `TYPEDECLARATION` and `VARDECLARATION` differ only in that
   `VARDECLARATION` stores into `LC`.

   Three of `DECLARAT`'s twenty are Apple's own factorings with no
   counterpart in II.0, so expect the same elsewhere: a procedure that
   matches nothing in the source is not a failure of the method, it is
   Apple saving space, and it gets a spelling of ours of eight characters
   or fewer.

   What is left of this track is the phase segments beyond those three. The
   method that worked twice now: find code that builds a structure out of
   constants and then *names* it, and read outwards. For the emitters the
   naming lever was different and worth remembering — the *encoding* itself
   identified them, because `opcode - 128` is a claim the opcode table can
   refute.

   Do not promote any name into reconstructed source until its call sites
   agree on arity and argument kinds.

2. **Extend the global map into a declaration order.** ~~Not started.~~
   **Well advanced** (finding 33). `tools/vardecl.py` is a `build_all.py`
   step: it lays out II.0's `VAR` block under the compiler's own
   allocation rule and aligns it by name against Apple's globals, into
   `analysis/global_map/vardecl-ii0.txt`. 111 names matched, drift
   non-decreasing through the scalar region — and the alignment now
   *predicts*: finding 34c read four globals (`TEST`, `USING`,
   `USINGLIST`, `MODPTR`) off `USESDECLARATION` and all four landed on the
   offset the drift column had already named, in both releases. **The rule that makes this
   work at all: a `VAR` declaration allocates its identifiers backwards.**
   The `DISPLAY`/`PFNUMOF` question is **closed** (finding 38), and the
   count it was asked with was wrong: `vardecl.py` had been parsing the
   fields of two inline `RECORD` types as variables, which corrupted every
   offset past `DISPLAY`. With that fixed the three remaining drift steps
   all balance — `PFNUMOF` (6 words) replaced in place by a two-word
   `SEGSUSED` set; `SEGTABLE`'s ninth word (+16) plus `SEGMAP` (+8); and
   one Apple word, `TEXTSTRT`, inserted into the source-switching block.
   Twelve more globals are named, the whole tail from `REFFILE` to `LP`
   aligns word for word, and the six `PREV*`/`OLD*` save slots — placed by
   behaviour alone — came out in II.0's backwards-allocated order, which
   is an independent confirmation of finding 33's rule.

   The unnamed stretches *between* the matched runs are done too (finding
   39). **129 of 1.1's 133 touched globals now have a name**, and finding
   43 disposes of the other four: they are not objects. `FILESIZE = 300`,
   `BODY` emits `LDA 0,VADDR+FILESIZE` as the window argument for every
   file variable whether it has a window or not, and three of the four
   land inside `LP` — a `TEXT`, and therefore 301 words, not the 40 of an
   untyped `FILE`. With that corrected the drift runs flat at +27 from
   `PREVSYMBLK` to the end of the block. On the II.0 side the account is complete: 111 of 118
   variables land on an Apple name and all seven that do not are explained
   (`GATTR` split into fields, the two linker flags merged, `PFNUMOF`
   deleted, and three booleans Apple dropped).

   This task is therefore **done**. Every touched global is accounted for,
   and the sizes needed to declare them are known: II.0's own type sizes,
   plus `NILFILESIZE = 40` and `FILESIZE = 300` for the file variables.
   What remains is mechanical — writing the declarations out in the
   recovered order with those types.

   Original notes follow. The map now knows
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

   Finding 23 supplies a second block, and a different *kind* of block: the
   twenty-odd compiler-option flags, read off `COMPOPTI.1`'s case table and
   cross-checked against `COMPINIT.9`'s defaults and the manual's. Those are
   simple `BOOLEAN`s and a couple of `INTEGER`s, they cluster in the low
   twenties-to-fifties, and their defaults are known — which makes them the
   easiest run of the `VAR` block to lay out. Also the four file variables
   (23d), now identified individually.

   ~~Finding 24 adds the syntactic sets.~~ **Done, and it went further than
   planned** (finding 26). Both of the scanner's enumerations are recovered
   complete and gapless — `SYMBOL` at 0..54 and `OPERATOR` at 0..15 — which
   are two `TYPE` declarations the reconstruction can now write out
   verbatim, and the member *order* is forced, not chosen. Eight globals
   hold a `set of symbol`, each identified by the error its guard raises,
   and two of the eight are built at run time from the one below
   (`constbegsys` ⊂ `simptypebegsys` ⊂ `typebegsys`), so their declaration
   order is forced too.

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

4. ~~**Write the procedure bodies.**~~ **Done for 1.3** (finding 87).
   All **147 of 147** — every p-code procedure of 1.3's `SYSTEM.COMPILER`,
   plus `IDSEARCH` and `TREESEARCH` from the assembler tier — compile under
   Apple's own compiler to Apple's p-code, instruction for instruction.
   `ROUTINE`, segment 10, was the last one in.

   `tools/procbuild.py` is the harness: it splices bodies into the verified
   skeleton, compiles, and diffs instruction for instruction against the
   binary. `python tools/procbuild.py --emu` writes the spliced source to
   `WORK:`/`WORK2:`; `tools/emucompile.ps1 -Name BODY13 -Work2 -Compile 300`
   drives Apple's compiler over it and shuts the emulator down (which is what
   flushes the image); `--emu-check` reads the codefile back and diffs.
   `build_all.py` puts the work disks back afterwards.

   **Drive the compiler from the menu, with `C(ompile`. Do not `X(ecute`
   it.** `C` prompts for the source and the codefile; X'd, the compiler
   takes its source from the system workfile and dies at *error 401, line
   0* when there isn't one. Two more traps on the way there: X appends
   `.CODE`, and `SYSTEM.COMPILER.CODE` is 20 characters against a 15-character
   limit, so it answers *"Illegal file name"*; and the compiler is not on the
   boot volume at all — `BOOT128:` is APPLE1 with the 128K system swapped in,
   and `SYSTEM.COMPILER` is on `APPLE2:` in drive 2, so `*SYSTEM.COMPILER` is
   *"No file"*. None of this is a `{$U-}` restriction: `PASCALCO.1` has
   `lex 0` and the compiler is an ordinary user program (findings 23c, 47).

   **Use `--emu-check` for anything with `AND` or `OR` in it.** The fast tier
   short-circuits where Apple emits `LAND`, so it can falsify such a body but
   never accept one (finding 58c). Everything else it settles in a second.
   It also allocates no `WITH` temporary where Apple takes one word per
   `WITH` statement, so a frame short by the `WITH` count is the tier's bias
   and not a source error (finding 87c).

   What is left is 1.1: `src/pascal/` has only `1.3`, and `procbuild.py`'s
   1.1 pass finds no sources. Carry the result across through the
   correspondence table.

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

     ~~Identify the word-data block each carries after its last `RTS`.~~
     **Done** (finding 44). They are the four relocation tables the 1.3
     manual documents at IV-35..37, read from JTAB-4 downward:
     base-relative, segment-relative, procedure-relative,
     Interpreter-relative, each a count word over that many *self-relative*
     pointers, target = `a - v`. Base, segment and interp are empty in
     both, so neither routine touches a global or calls the Interpreter;
     the procedure-relative tables hold `IDSEARCH`'s 26 letter-index words
     plus its two `LDA` bases, and `TREESEARCH`'s four `JMP` operands.
     **Every byte of both procedures is now accounted for** — the walk
     lands exactly on the end of the code in each. Along the way it
     explained why `LDA $006C,Y` is nowhere near the table it reads (the
     base is offset back by `2*ord('A')`) and gave the four `JMP`s their
     real targets, `$152E` and `$1580`.

     ~~Turn the two listings into assembly source that reassembles to the
     same bytes.~~ **Done** (finding 45). `src/native/SEARCH.TEXT` is the
     first reconstructed source in the repo — `.PROC IDSEARCH,2` and
     `.FUNC TREESEARCH,3` — and it assembles to **800 and 148 bytes
     identical to Apple's**, over the whole procedure including all four
     relocation tables and the attribute table. `tools/asm6502.py` is a
     minimal assembler for the subset used; `probe_native_asm.py` runs the
     comparison and `build_all.py` runs the probe.

     What remains here is the acceptance run: **assemble it with Apple's
     own `SYSTEM.ASSMBLER`**, which is on both evidence disks alongside
     `6500.OPCODES`/`6502.OPCODES` — it is what generated the relocation
     tables, and finding 44 makes those the test: symbolic operands in,
     correct tables out. Never hand-build a relocation table and do not
     substitute a modern assembler. That puts the last step of the native
     half in task 7's acceptance tier.
     `evidence/reference/tribby-idsearch-treesearch-1.2.asm` is a good
     structural model but is 1.2 — corroboration, not authority; it is
     where the label names in `SEARCH.TEXT` come from, which is a
     convenience and not evidence.
   * ~~Account for the ~130-word growth in globals.~~ **Done** (finding
     40). The area went 1222 → 1355, and all 133 words are accounted for:
     `ISPROG` +1, `BYTEPTR`/`WORDPTR` +2, `SEGSUSED` +2, `PROCTABLE` +105,
     `SEGMAP` +8, `JTAB` +12 (`MAXJTAB` 24 → 36, and the binary carries
     both bounds at the `ERROR(253)`/`ERROR(254)` guard), and three new
     words at startup +3. `DISPLAY` and `SEGTABLE` are unchanged. The
     probe re-derives the ledger from both binaries and fails if the total
     misses.

     One thing to carry: **1.3 renumbered at least one compiler error**
     (`JTAB` overflow moved from 253 to 254), so an error number is not a
     safe way to carry a name from 1.1 across the correspondence table.

     ~~The three procedures 1.3 adds.~~ **Done** (finding 42).
     `COMPINIT.11` is `CHECKVER`, the version gate; `COMPOPTI.5` is
     `ADDRESID`, one node of the `$R` list that 1.1 builds inline; and
     `BODYPART.26` is `INITUNIT`, which is a *documented bug fix* — 1.1's
     `BODY2` walks `USINGLIST` forward emitting each unit's initialisation
     call, and since the list is built by prepending that is reverse
     declaration order, exactly the bug the 1.1 Update pamphlet says 1.2
     fixed. 1.3 lifts the loop into a procedure that recurses on `next`
     before emitting. Note the *shape* of the fix for the reconstruction:
     1.3's `BODY2` must be a call, not a loop, or the code bytes differ.

     First two identified (finding 22b): 1.3 adds the standard types
     `BYTESTREAM` and `WORDSTREAM`, at globals 57 and 58, entered by name
     in COMPINIT alongside `INTEGER` and `STRING`. They are also the
     cleanest available proof of what word 7 of a type descriptor means,
     since `BYTESTREAM` is a packed char array that is deliberately *not*
     a `STRING`.

7. **Validation loop**, now in two tiers (finding 18).

   * ~~*Start here:* `HAZELGOTO.TEXT` and `HAZELGOTO.CODE`.~~ **Done for
     the lifting direction** (finding 49). Both GOTOXY samples lift and
     structure to their own source, statement for statement, with zero
     gotos; `probe_calibrate.py` extracts conditions, assignment targets,
     right-hand sides and literals from each side by the same rules and
     requires all four to match, and `build_all.py` runs it. It confirmed
     finding 33's backwards allocation on *parameters* and finding 46's
     frame model against a declaration, and checked `UNITWRITE`'s six-word
     stack effect against a call written in Pascal. It found two tooling
     defects, both fixed.

     What it did not cover: loops, `case`, sets, inter-procedure calls,
     records, `with` -- the samples use none of them.

   * ~~*Then:* `SYSTEM.PASCAL`.~~ **Done** (findings 50, 51, 52). The reader
     problem that blocked it is solved -- slot 15 was never a broken
     segment, it is the second piece of segment 0 -- and all three OS builds
     now parse and lift. Segment 0's numbering aligns with UCSD II.0's
     declarations through procedure 42, so 41 procedures have source.
     `probe_os_calibrate.py` checks loops (back edges in the CFG, counted
     before the structuriser runs) and calls (every segment-0 routine called
     must be admissible from the source body), and it measures its own
     discriminating power so the second check cannot go vacuous. It also
     recovered the compiler's built-in mapping -- `COPY`/`DELETE`/`POS` to
     `SCOPY`/`SDELETE`/`SPOS`, `WRITE` to one of four `FWRITE*` by argument
     type -- which finding 52b tabulates.

     **What is still unchecked against source, in priority order:**

     1. **`with`, and record field *offsets*.** Record *sizes* are now
        checked -- finding 54 lays UCSD's declarations out and reproduces
        `ATTR` at 5 words, `STRUCTURE` at 9, and all seven `identifier`
        `klass` sizes, plus the seventeen VAR-block sizes `vardecl.py` used
        to tabulate. What is still unchecked is offsets: a `WITH SYSCOM^ DO`
        followed by a named field has to become one particular displacement,
        and `reclayout.py` can now compute that displacement from the
        declaration. Doing so would also settle finding 54b, where sizes
        alone cannot say *which* two fields Apple's `identifier` lacks --
        offsets can, because dropping a different word would shift
        everything after it.

     2. ~~**`case`.**~~ **Done** (finding 53). `PRINTERROR`'s nested case
        against UCSD's source for it: 31 error messages in 1.1 and 21 in 1.3
        come out identical to II.0 character for character, with the arm
        labels, the nesting inside arm 10 and the default assignment all
        matching. `probe_case_calibrate.py` gates it.

     3. **Sets.** Present in the lifted output (`G3 in @I1,122^<4w>`) and
        never checked against a declaration.
     4. **The other OS segments.** `USERPROGRAM`, `DEBUGGER`, `PRINTERROR`,
        `INITIALIZE`, `GETCMD` and `FILEPROC` all have source in
        `SYSSEGS.A/B.TEXT` and match Apple's slot names exactly. Aligning
        their procedure numbering would roughly triple the calibration set.
        Harder than segment 0 was, because there is no forward-declaration
        block to fix the numbering -- it would have to be established from
        signatures and call structure first.

     The other direction � source *in*, codefile out � is still the
     emulator's job.
   * ~~*Fast tier, new:*~~ **Built and calibrated** (finding 55).
     `thirdparty/ucsd-psystem-xc/build.sh` builds Peter Miller's
     `ucsdpsys_compile` and `ucsdpsys_disassemble` reproducibly under WSL;
     `tools/xcompile.py` drives it from Windows and `probe_xcompile.py`
     gates it.

     It is better than this entry expected. On both GOTOXY programs -- the
     only source-and-binary pairs in `evidence/` -- it reproduces Apple's
     p-code **byte for byte**, apart from one alignment byte per procedure
     that Apple writes as 0 and it writes as `NOP`. So it is not merely a
     syntax check; for the constructs those programs use it is a reference.
     It is still a different compiler by a different author, and where it
     disagrees with the binary the binary wins.

     Use it on everything. It compiled the declaration skeleton on its first
     run and found a two-word error in the global frame that thirty findings
     of reading the binary had not (finding 55c) -- which is now the top
     open question, because every offset depends on it.
   * *Acceptance tier — **run, and both tests passed*** (finding 57).
     Apple II Pascal 1.3 under AppleWin, on the reconstruction:

     1. **`SYSTEM.ASSMBLER` on `SEARCH.TEXT`** — 519 lines, 0 errors, and
        `IDSEARCH` (800 bytes) and `TREESEARCH` (148 bytes) come back
        **identical to Apple's, every byte**, relocation tables included.
        Finding 44e is closed.
     2. **`SYSTEM.COMPILER` on `SKEL13.TEXT`** — 465 lines, no errors,
        segment `PASCALCO`, outer block `param 4 / data 2710 / lex 0`,
        **exactly Apple's**. All 130 declarations are confirmed by the only
        authority that counts.

     **Run it on 128K.** The 64K system cannot compile even Apple's own
     `HILBERT.TEXT` — it dies with a runtime stack overflow. `mkbootdisk.py`
     builds `BOOT128.dsk` (APPLE1 with `128K.APPLE`/`128K.PASCAL`
     substituted); `runemu.py --boot128` boots it.

     The tooling: `tools/runemu.py` mounts the four drives, asserts the two
     registry settings that have no command-line switch (maximum speed, and
     a monochrome video mode so screenshots are legible), and boots;
     `tools/emukeys.ps1` sends keystrokes and captures the screen. Those
     registry values and their *types* are AppleWin-version-specific — see
     finding 57d before changing builds. Neither is
     part of `build_all.py` — the acceptance tier is interactive by nature
     and cannot be a probe. Two operational traps, both learned the hard way:
     **SendKeys goes to whatever holds focus** (emukeys.ps1 now refuses to
     type unless AppleWin is foreground), and **AppleWin does not flush a
     written image until eject or exit** (close it before reading the disk).

     Carry forward: **the fast tier is more permissive than Apple's
     compiler.** It accepted a trailing `;` before `)` in a field list that
     Apple's rejects with error 19. "It compiles" from `ucsdpsys_compile` is
     the weaker claim.

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
   * *Control-flow structuring — done, 79%* (findings 21 and 41).
     `tools/a2pascal/structure.py`. **229 of 287 procedures come out with
     no goto at all**; 156 gotos remain over 6252 blocks, 0.02 per block.
     Both correctness invariants — no dropped statements, no dangling
     gotos — hold at zero, and `tools/probes/probe_structure.py` re-checks
     them, so a regression here is visible rather than silent.

     The step from 70% came from `case`, which finding 41 found the
     recogniser had never matched even once: UCSD puts the jump table
     *after* the arms, so the construct has to be keyed on the `UJP` that
     reaches the table. 50 of 54 now come out as `case` statements, worth
     840 of the 1390 gotos.

     **The earlier guess here was wrong and is worth recording as such:**
     short-circuit boolean evaluation is not what was left, because the
     compiler does not short-circuit at all — `and` and `or` compile to
     `LAND` and `LOR` on values, and the `FJP` chains that look like
     short-circuiting are nested `if`s in the source. Measure the refusals
     before guessing at them; the instrumentation is four lines of
     subclass over `_Structurer`.

     What remains is thin: 224 of 246 loop headers are recovered, and the
     22 that are not are multi-exit loops, which Pascal itself writes with
     a `goto` or an `EXIT`. The 156 residual gotos spread over 58
     procedures with at most 9 in any one, so there is no further single
     win of this size.

   Also open, and harder: 89 joins where the two paths disagree on stack
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
  passing check actually rules out. Finding 47 is the sharpest case: a
  linear sweep re-synchronises a few bytes after corruption and still lands
  on the procedure's end address, so 287/287 said nothing at all about
  seven bad bytes in `BODY3`; a branch-target check found them at once.
* **A total that does not balance is evidence.** The global map printed
  "1225 of 1222" at the top of every run for thirty findings, and it was
  read as slack in the object inference each time — because the inference
  really does over-count elsewhere, so there were two explanations and the
  wrong one was never separated out. It was a two-word error in the area
  (finding 46). Require the sum to come out exactly, or say why it cannot.
* Hyde's *P-Source* (finding 7a) settles p-machine questions directly. Use
  it before inferring.
* **Native 6502 code is finalised with Apple's own `SYSTEM.ASSMBLER`**, on
  both evidence disks. It handles relocation; a hand-written relocation
  table or a modern assembler will not reproduce the bytes. Write `.PROC`
  source with symbolic operands and let the assembler emit the tables
  (finding 44e).
* The Apple Pascal 1.3 manual (finding 23) is the vendor's own account of
  the p-machine, the codefile format and every compiler option. Use it
  before inferring too — it caught a `CGP` bug the binary had been hiding,
  and its Part IV Ch. 4 validated the whole opcode table at once
  (finding 25). All the manuals now live in
  `evidence/reference/manuals/`, with their OCR flattened into
  `analysis/reference/*.txt` by `tools/reference_text.py` — grep that.
  The OCR is unreliable for anything dense; re-read the page as an image
  with `tools/pdfpage.py` before quoting it.
* The compiler is a direct descendant of the Zurich P2 / Pascal-P
  compiler, and finding 26b puts that beyond doubt: its `operator`
  enumeration survives verbatim, all sixteen members in the published
  order. Published Pascal-P source is therefore a legitimate source of
  *names* — but only names. Every structure taken from it has to be
  re-derived from the binary before it is written down, and where Apple
  diverged (`longconst`, `PROGRAM` and `SEGMENT` sharing a code) the
  binary is what says so.
* Neil Parker's *Undocumented Secrets of Apple Pascal* covers what the
  manuals do not — the undocumented compiler options, the `{$U-}`
  convention, on-disk structures. Treat it as a lead, not an authority: it
  resolved three option letters (finding 24a) and got `SYSTEM.COMPILER`'s
  own `{$U-}` status wrong (24e).
* The reconstructed source has to carry the directives the original had.
  `{$R-}` is established (no `CHK` anywhere) and `{$G+}` is all but certain;
  `{$U-}` is ruled out. See finding 23c.
* When a 1.1 fact is established, push it through the correspondence table
  and confirm it holds in 1.3. Divergences are findings, not noise — the
  segment limit moving from 31 to 63 (finding 27a) was found that way, and
  it corrected a version confusion in finding 23c.
* A recovered name can be wrong, and the way that shows up is a second
  routine behaving more like the name than the one holding it. Finding 27b
  is the worked example: global 96 does everything global 13 was named
  for. When that happens, write the evidence down and leave the name
  alone until the answer is actually known — renaming twice is worse than
  renaming late.
