# Reconstruction plan

**Reproduce the Apple Pascal 1.3 disk set** -- for every file Apple
shipped, a source that Apple's own tools turn back into the shipped bytes.
Readable pseudocode is not the target and never was; byte-identical output
from `SYSTEM.COMPILER`, `SYSTEM.ASSMBLER` and `SYSTEM.LINKER` is.

**The target is 1.3 and the 128K system** (`128K.APPLE` + `128K.PASCAL`).
1.1 is not a goal and is not discarded: it ships *source* for utilities 1.3
ships only as codefiles, its binaries are simpler (no native code at all),
and comparing the two releases is what says which files Apple actually
rebuilt. Every 1.1 fact should be pushed through the correspondence table
of finding 11 and checked against 1.3 rather than left version-specific.

`docs/DISKSET.md` is the file-by-file scoreboard;
`analysis/diskset-inventory.txt` is its machine-readable companion,
regenerated on every build.

## Where this stands

Three files are reconstructed -- source in `src/`, and Apple's own tools
turn it back into Apple's bytes:

| file | what it took |
|---|---|
| `SYSTEM.LIBRARY` | 55 p-code and 14 native procedures (finding 98) |
| `LINEFEED.CODE` | 1.1's own source, unaltered, under the 1.3 compiler (finding 99a) |
| `FORMATTER.CODE` | the first whole program: Pascal *and* 6502, linked (finding 104) |

`SYSTEM.COMPILER` is not on that list yet, but only one thing keeps it off:
all 15 real segments -- `PASCALCO` included, body order and procedure
numbering both fixed (finding 107) -- are byte-identical to what Apple
shipped. What remains is finding 105a alone: an extra, empty `PASCALSY` host
segment, 512 bytes, that Apple's shipped file does not have at all.

Counting procedures rather than bytes, and 1.3 only: **216 done of roughly
861.** Every remaining target can be read before it is written -- the sweep
covers every codefile a 1.3 disk carries plus the 1.1 copies of those same
files, and lifts **1147 of 1147** with the stack fully tracked (finding
100). Listings are in `analysis/utilities/`, p-code and pseudo-Pascal side
by side.

The infrastructure is done and is not the constraint: readers for the
filesystem, codefiles, segments and procedure attributes; a p-code decoder
that passes a strict self-check; a 6502 disassembler and assembler; a
lifter that structures 79% of procedures with no goto at all; the global
map and the 1.1/1.3 correspondence; and the emulator tier below.

**All three of Apple's tools are now driven from here**, which is what made
`FORMATTER` possible:

* `tools/emucompile.ps1` -- `C(ompile`
* `tools/emuassemble.ps1` -- `A(ssem`
* `tools/emulink.ps1` -- `L(ink`, which is the only thing that puts an
  assembled `EXTERNAL` into a compiled host

Their output is kept under `acceptance/` and re-checked against the shipped
disks on every build by `tools/probes/probe_acceptance.py` -- the one check
in the repo with none of this project's own code on either side.

**The acceptance-tier drive layout changed since the above was written.**
`tools/mkharddisks.py` now builds a single 2MB Pascal hard-disk volume
(`SYSHD`, on a slot-5 HDC) that boots, carries every system tool, and
carries the reconstruction's own source and output all at once -- and it is
the default for `runemu.py` and all three `emu*.ps1` scripts. That retires
the `A(ssem` Filer-`P(refix` step above: `SYSHD` carries `6502.OPCODES`
itself, so the default prefix (the boot volume) resolves without help.
**Every codefile created on that merged volume needs a `[*]` size
specifier** (`SYSHD:NAME.CODE[*]`) -- a single UCSD volume claims all free
space for a new file and only shrinks it back on close, so a codefile and
`SYSTEM.ASSMBLER`'s own `%LINKER.INFO` scratch file race for it otherwise.
The old four-volume floppy layout is unchanged and still available via
`-Floppy` / `runemu.py --floppy`, where `[*]` is not needed since system
tools and output live on separate volumes there. See `CLAUDE.md` for the
full recipe.

## Next steps

The order below is by what the evidence supports, not by size. A file whose
1.1 release ships source is nearly free; a file with a native half now has
a route end to end; everything else is a straight read-and-rebuild.

1. **One gap left in `SYSTEM.COMPILER`: the empty `PASCALSY` host segment
   (finding 105a), 512 bytes.** The three steps -- compile the fifteen
   segments, assemble `src/native/SEARCH.TEXT`, `L(ink` the two -- now
   produce all 15 real segments byte-identical to Apple's, `PASCALCO`
   included (finding 107 closed the body-order and numbering mismatch
   finding 105b found). What is left is a segment 0 that should not exist
   at all: Apple's shipped file has no code there -- addr and length both
   zero in the dictionary -- and every compile of `BODY13.TEXT` produces a
   real one, one `XIT` byte and an attribute table for the 15 forward-
   declared segment procedures. Two things worth trying: whether a `(*$U-*)`
   **system**-level program is supposed to have no codefile segment for its
   own outer block at all (as opposed to an ordinary program), and whether
   that is something the compiler alone decides or something `SYSTEM.LINKER`
   is meant to drop.

2. **`LIBMAP.CODE`** -- 12 procedures, one of them native. **In progress**
   (`src/pascal/programs/1.3/LIBMAP.text`). The native half is closed for
   free: finding 109 found `LIBMAP.2` is byte-for-byte Apple's own
   `IDSEARCH` from `SYSTEM.COMPILER`, linked in whole rather than
   rewritten, so `("LIBMAP", 2)` -- the last entry in `lift.py`'s
   `NATIVE_SIG` still read off a call site rather than a declaration -- is
   retired with no new 6502 at all. The VAR block compiles to Apple's exact
   757-word frame; `SWAPBYTES` and `VALIDNAME` are verified byte-for-byte
   against Apple's own p-code; `SHOWSEGS` is exact on param/data size but
   not yet checked instruction by instruction; `NEEDSSWAP` and `SWAPALL`
   are each one word of locals short (documented as a known gap, not
   forced); procedures 8-12 (`SHOWONE` and its nested `SHOWINFO`/
   `GETWORD`/`SHOWREF`, then `MAPLIBRARY`) and the outer block are still
   stubs -- `SHOWONE`'s own procedure 9 is the largest single procedure in
   the file at 521 words of locals.

3. **`BINDER.CODE` and `SET40COLS.CODE`** -- 6 and 4 procedures, and both
   are **1.1 binaries Apple never rebuilt** (finding 99c). That is what
   made `LINEFEED` nearly free: 1.1's APPLE3 ships the source, and the
   question is only whether it still compiles to the shipped bytes. Do
   these two the same way and check the answer, which may well be no --
   `BINDER` differs from its 1.1 copy in 15 bytes, all of them unused
   SEGINFO slots.

4. **`LIBRARY.CODE`** -- 16 procedures, one segment, no native. The
   smallest pure-Pascal target left, and it pairs with `LIBMAP`.

5. **`SETUP.CODE`** -- 54 procedures in 12 segments, nine of which are
   16-byte stubs, and **byte-identical between 1.1 and 1.3**. The segment
   structure is the interesting part; the stubs make it cheaper than the
   count suggests. It also writes `SYSTEM.MISCINFO`, so it is the way in to
   the three `.MISCINFO` files.

6. **`SYSTEM.LINKER`** -- 51 procedures, one segment. Now also a tool this
   project depends on, so understanding it pays twice.

7. **`SYSTEM.FILER`** -- 56 procedures, one segment.

8. **`SYSTEM.ASSMBLER`** -- 95 procedures in 7 segments, and the acceptance
   authority for everything in `src/native/`. Reconstructing the thing that
   validates the reconstruction is worth doing carefully and last of the
   utilities. Note `6502.OPCODES` and `6502.ERRORS` are its data, and
   finding 103e records how it looks for each.

9. **`SYSTEM.EDITOR`** -- 129 procedures in 12 segments, the largest single
   target on the disk set.

10. **The operating system** -- `128K.PASCAL`, 105 procedures. Four of its
    seven segments are byte-identical to 64K `SYSTEM.PASCAL`'s
    (`USERPROG`, `FIOPRIMS`, `PRINTERR`, `FILEPROC`), so the two releases
    of the OS are one target and a bit. `ii0src.sdk` is the UCSD II.0 OS
    source and is genuinely relevant here, unlike for the compiler
    (finding 8).

11. **The files that are not codefiles.** They still have to come from
    somewhere before a disk can be written:
    * `SYSTEM.APPLE` / `128K.APPLE` -- raw 6502, the interpreter. Not a
      codefile, so none of the codefile tooling applies; this is a
      disassembly project of its own.
    * `SYSTEM.CHARSET` (1024 B), `FORMATTER.DATA` (3584 B, the format
      tables `FORMATDISK` calls at `$3D00`), `6502.OPCODES` (720 B),
      `6502.ERRORS` (3570 B), the three `.MISCINFO` profiles. Each needs a
      generator whose output is checked byte for byte, the way a source is.
    * `SYSTEM.SYNTAX` and the eleven sample `.TEXT` programs are *already
      text on the disk*, so they are reproduced by writing the volume and
      nothing else.

12. **Write the disks.** The end of the project: the volume writer already
    re-encodes every evidence volume byte for byte from its own parsed
    entries, so the writer is not the risk. What is missing is a build step
    that assembles a full 1.3 volume out of reconstructed files and diffs
    it against the evidence image -- one number for the whole project, and
    a total that has to balance.

### Carried forward, not scheduled

* **`src/pascal/units/1.1/` is empty.** The 1.1 library has no
  reconstruction at all yet.
* **`LONGINTS.TEXT`'s eleven operations are not read out** (finding 98d).
  The engine reassembles to Apple's bytes, but what each operation number
  does is still unread, and it is the one native procedure deliberately
  left out of `NATIVE_SIG` because its arity is variable.
* **89 joins where the two paths disagree on stack depth**, mostly UCSD
  sets. Do not "fix" these by loosening the merge -- the report is what
  makes a wrong callee arity findable.
* **The 1.1 side of the disk set.** `CALC.CODE` and the demo programs'
  codefiles ship only on 1.1, so they are out of scope but still swept and
  still listed. The demos' 1.1 `.CODE` beside their `.TEXT` is the only
  source-and-output pair Apple left behind, and it is a calibration corpus
  worth using before guessing at a construct.

## The compiler phase, kept as the record

Steps 1-8 below are the plan that produced `SYSTEM.COMPILER` and the
library. They are left as they were written, including the guesses that
turned out wrong and are marked as such -- the working rules at the end are
mostly lessons from them.

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

4. ~~**Write the procedure bodies.**~~ **Done for 1.3** (findings 87, 90).
   All **147 of 147** — every p-code procedure of 1.3's `SYSTEM.COMPILER`,
   plus `IDSEARCH` and `TREESEARCH` from the assembler tier — compile under
   Apple's own compiler to Apple's p-code. `ROUTINE`, segment 10, was the
   last one in.

   Finding 90 raised that from *instruction for instruction* to **byte for
   byte**, and found two real errors on the way: `--emu-check` blanked
   absolute jump targets, so a label placed one statement too far along was
   invisible to it. `NEWSEG` was not allocating a dictionary slot for an
   `INTRINSIC` unit and `UNITPART.3` had two error checks a level too deep.
   The check now compares bytes — jump tables and attribute tables included
   — and each segment as a whole image: **14 of 15 segments byte-identical
   end to end**, `PASCALCO` short by exactly the 948 bytes of its two native
   procedures. `docs/VERIFY-1.3.md` is the runbook.

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
* **A file is not reconstructed until Apple's own tools rebuild it.** All
  three are driven from here now -- `emucompile.ps1`, `emuassemble.ps1`,
  `emulink.ps1` -- and a program with an `EXTERNAL` in it needs all three:
  the compiler leaves the segment marked `HOSTSEG` and only the Linker
  resolves it (findings 91, 104). Keep each run's output under
  `acceptance/`, because the emulator tier is interactive and would
  otherwise be a claim rather than a check.
* **A backward branch is a loop condition before it is anything else.**
  Fifteen bytes of `FORMATTER` stayed open for a round because an `FJP` to
  the top of a `REPEAT` was read as a strangely-placed `IF` instead of as
  the `UNTIL` it was -- an inner loop starting at the same statement as the
  outer one (finding 104a). The lifter had been printing it correctly the
  whole time. When the listing and the prose disagree, re-read the listing.
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
