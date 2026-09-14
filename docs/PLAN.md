# Reconstruction plan

**Reproduce the Apple Pascal 1.3 disk set** -- for every file Apple
shipped, a source that Apple's own tools turn back into the shipped bytes.
Readable pseudocode is not the target and never was; byte-identical output
from `SYSTEM.COMPILER`, `SYSTEM.ASSMBLER` and `SYSTEM.LINKER` is.

**The target is 1.3 and the 128K system only** (`128K.APPLE` +
`128K.PASCAL`). As of 2026-09-12 the 64K `SYSTEM.APPLE`/`SYSTEM.PASCAL` and
all of 1.1 are archived and out of the build (`archive/README.md`). The
history below still cites 1.1 where 1.1 is how a fact was first found;
treat those as leads to confirm against the 1.3 binaries, not as live
checks.

**Current state** (the sections below are older): `SYSTEM.COMPILER` and
`SYSTEM.ASSMBLER` are reproduced as whole files by Apple's own compiler,
assembler, Linker and Librarian (findings 267e and 267f; `PASCALIO` in the
assembler is borrowed, finding 235b); `128K.PASCAL` is 111 of 111 in one
compile (finding 280), and the whole file but 571 bytes of another tool's slack once `MAKEOS` finishes it on the 1.3 system (findings 281-284). `SYSTEM.LINKER` is identical as a whole
file too (finding 268), from I.5's linker and the binary, and so is
`LIBRARY.CODE` (finding 269), from I.5's Librarian, and `LIBMAP.CODE`
through the end of its segment (finding 270), from I.5's LibMap, and
`SYSTEM.FILER` (finding 271), from UCSD's II.0 Filer, and `SYSTEM.EDITOR`
(finding 272), from UCSD's II.0 screen editor. `SETUP.CODE` is 54 of 54
procedures from UCSD's SETUP D1 (finding 273) -- as far as 1.3 tools
reach, since it predates the version word. `BINDER.CODE` (finding
274) and `SET40COLS.CODE` (112) are every byte but the version field:
they are 1.1 binaries, version 2, and a 1.3 compile writes 6.
`FORMATTER.DATA` is 3583 of 3584 bytes, assembled and joined on the 1.3
system (finding 275); `6502.OPCODES` is identical and `6502.ERRORS` is
all but the 287 bytes its record window started with (finding 276). The
four MISCINFO profiles have every setting from Apple's SETUP, run from
recipes; their other bytes are memory SETUP never writes (finding 277).
`SYSTEM.CHARSET` is identical (finding 278), and so is `128K.APPLE`, the
interpreter, from three traced assemblies (finding 279).
`SYSTEM.LIBRARY` has every code byte and all interface text by Apple's
tools (findings 285-287). The ten text files are identical from
`src/text/` (finding 288). **The disks are written** (step 12, finding
289, 290): 359,323 of 430,080 bytes, every difference accounted for by
`probe_diskset.py`.
Check `github.com/dhlav/ucsd-psystem-os` for an ancestor first; it
carries more of UCSD's II.0 tools than `ii0src.sdk` does.

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
segment, 512 bytes, that Apple's shipped file does not have at all. It also
now has a real self-hosting check behind it, not just a static byte
comparison: swapped onto `SYSHD:` in place of Apple's shipped compiler, it
compiled `LIBRARY.text` (finding 113's real 574-line, 16-procedure source)
**byte-identically** to what Apple's own compiler produces from the same
input, 3072 bytes, 0 differences (finding 114).

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

1. **CLOSED (finding 267e): `SYSTEM.COMPILER` is identical as a whole
   file.** The `PASCALSY` host segment was never a source gap: Apple's
   release step copied segments 1-15 into a fresh file with `LIBRARY.CODE`.
   What follows is the history of the gap.

   *Was:* **One gap left in `SYSTEM.COMPILER`: the empty `PASCALSY` host segment
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
   forced); `SHOWONE` (procedure 8)'s own entry-reading loop and its
   nested `GETWORD` are now reconstructed instruction for instruction and
   **acceptance-tier verified** -- `params=2/data=556` and `params=2/data=2`
   respectively, both exact matches to Apple's compiled binary (finding
   111 update; `acceptance/2026-08-27-libmap-showone-getword/`). The fast
   tier can't check either one (its builtin `moveleft`/`blockread` take
   the wrong number of arguments for the real UCSD calls this loop
   needs), so this had to go through AppleWin directly. `SHOWINFO`
   (procedure 9, the largest single procedure in the file at 1042 words of
   locals), `SHOWREF` (procedure 11), and `MAPLIBRARY` (procedure 12) plus
   the outer block are still stubs.

3. **`BINDER.CODE` and `SET40COLS.CODE`** -- 6 and 4 procedures, and both
   are **1.1 binaries Apple never rebuilt** (finding 99c). Both run under
   1.3 -- confirmed by hand in AppleWin off `SYSHD:` (they're on the disk
   now, `tools/mkharddisks.py`'s `EVIDENCE_CODEFILES`) -- so **they're in
   scope, not a maybe**. **Correction, 2026-08-27: neither is "nearly free"
   like `LINEFEED` -- checked all six evidence disks and there is no
   `BINDER.TEXT` or `SET40COLS.TEXT` anywhere.** 1.1's APPLE3
   (`UCSD Pascal 1.1_3.dsk`, volume `APPLE3`) ships `BINDER.CODE` as a
   binary only, and doesn't carry `SET40COLS` at all in any form. Both
   need the full lift-and-rewrite treatment this project used for
   `SYSTEM.LIBRARY`/`SYSTEM.COMPILER`/`LIBMAP`, not a recompile of shipped
   source. `BINDER` also has a known dead end even after that: its 1.3
   copy differs from its 1.1 copy in exactly 15 bytes, all unused SEGINFO
   slots that neither a 1.1 nor a 1.3 compile produces (finding 99c) --
   so byte-identical is not reachable for `BINDER` until that's explained,
   independent of how good the reconstructed source is. `SET40COLS` carries
   no such known blocker; it's the more promising of the two to start with.
   **`SET40COLS` done to the same wall `BINDER` was already known to have**
   (finding 112, `src/pascal/programs/1.3/SET40COLS.text`): compiled clean
   under Apple's own `SYSTEM.COMPILER` on the first attempt, all four
   procedures' frames exact, a full instruction diff 469/469 identical,
   and the compiled codefile 2544/2560 bytes identical to Apple's shipped
   copy -- the remaining 16 bytes are the *same* SEGINFO version-stamp
   anomaly finding 99c found in `BINDER` (`$42` vs a fresh compile's
   `$C2`), now confirmed to be the same mechanism in both files rather
   than two unrelated oddities. `SET40COLS` will not reach byte-identical
   until that's understood, same as `BINDER` -- but everything this
   project's own tools can check, checks out. **`BINDER` itself is now
   also reconstructed** (finding 117, `src/pascal/programs/1.3/
   BINDER.text`): compiled clean under Apple's own `SYSTEM.COMPILER`
   after a handful of real fixes (a value `STRING` parameter's own
   41-word copy-on-entry local, `NEW` without a variant tag on a plain
   array, an 8-character identifier collision), and five of its six
   procedures match Apple's shipped binary exactly on both `params` and
   `data` -- the sixth (the outer program body) is short by exactly one
   word out of 1119, documented not forced. Byte-identical is still not
   reachable, same known wall as `SET40COLS`.

4. **`LIBRARY.CODE`** -- 16 procedures, one segment, no native.
   **Correction: not the smallest target left** -- procedure *count* is
   small but it nests four lex levels deep with a real heap-chained
   buffer, byte-order swapping, and per-segment link-interface copying;
   comparable in scope to `LIBMAP`, not smaller. **In progress**
   (`src/pascal/programs/1.3/LIBRARY.text`, finding 113): all 16
   procedures declared with the right structure and compile clean under
   Apple's own `SYSTEM.COMPILER`; `SWAPBYTES`/`CHECKIO`/`GETINPUT` frames
   exact, several more (`NEEDSSWAP`, `SWAPALL`, `MSGLINE`, `MSGLINEINT`,
   `SHOWDICT`) close within a few words (documented, not forced);
   `MAINLOOP` itself has a real unexplained 74-word frame gap. The
   copy/link/interface logic (`COPYSLOT`/`COPYLINK`/`READLINK`/
   `COPYINTERFACE`) and one cosmetic screen-cursor detail in
   `MSGLINE`/`MSGLINEINT` are still `(*STUB*)`.

5. **`SETUP.CODE`** -- **Superseded by finding 273**: UCSD's own SETUP D1
   source plus six edits gives all 54 procedures; the history below is the
   hand reconstruction it replaced. 54 procedures in 12 segments, nine of which are
   16-byte stubs, and **byte-identical between 1.1 and 1.3**. The segment
   structure is the interesting part; the stubs make it cheaper than the
   count suggests. It also writes `SYSTEM.MISCINFO`, so it is the way in to
   the three `.MISCINFO` files. **Started** (finding 122,
   `src/pascal/programs/1.3/SETUP.text`): all 54 procedures compile clean
   under Apple's own `SYSTEM.COMPILER`, first attempt, after finding the
   real `(*$U-*) PROGRAM PASCALSYSTEM` / `SEGMENT PROCEDURE
   SETUP(P1,P2)` wrapping shape (`SYSTEM.COMPILER`'s own skeleton has
   the precedent -- a naive single-`PROGRAM` shape fails `EXIT`). The
   outer body, `SETUP2`, `SETUP3`, `SETUP5`, `SETUP6`, `SETUP7`, and
   all eight `NUMBERn` stubs are frame-exact (finding 123 corrected an
   earlier wrong claim that `SETUP5`/`SETUP6` didn't match -- they
   always did). `SETUP4` went from an 82-word miss to a one-word miss
   once `SRC` was made `VAR` instead of value, matching what the
   binary's own procedure 4 actually loads (finding 123); the one
   remaining word is documented not forced. **`SETUP13`-`26` are
   nested inside `SETUP12`, not flat siblings of it** (finding 126,
   from the lift's own lex levels) -- a first attempt declaring them
   flat, with `FORWARD` used to let `SETUP12` reach the later ones,
   compiled clean but numbered every procedure wrong from 7 onward,
   since `FORWARD` reserves a number immediately at declaration --
   which finding 61 already said, but a later paraphrase of it in
   `SETUP.text`'s own comments had backwards, corrected in place.
   Rebuilt with the real nesting (finding 127) and it landed exactly:
   `SETUP12`, `13`, `14`, `15`, `25`, `26` all frame-exact against
   Apple's binary, no `FORWARD` needed anywhere. Filled in the
   scalar-value trio `SETUP22`/`23`/`24` (finding 128) plus `SETUP20`
   (`2^N`), all four exact first attempt -- `24` reuses SETUP3's own
   sentinel-search trick, a second independent confirmation of that
   idiom. Filled in `SETUP17`/`18` too (finding 129, the bit-field
   pack/unpack), reusing `SET40COLS.text`'s own variant-record bit-view
   idiom to read/write single bits of a `MISCINFO` word -- both exact
   once a local copy of `SETUP16`'s own parameter (`FIELD := L1`,
   matching the lift's explicit `L3 := I1,1`) was added rather than
   relying on lexical scoping alone. Filled in `SETUP9`/`11` too
   (finding 130) -- the octal/decimal/hex read-out line (a second,
   independent variant-record bit-view use, split into two separate
   `OCTVIEW`/`HEXVIEW` locals rather than one combined type once a
   combined attempt landed 4 bytes short) and the entry-format help
   screen (needed an explicit `KEY: CHAR` local capturing `SETUP5`'s
   own result, not a bare call in the loop condition) -- both exact.
   Filled in `SETUP10` too (finding 132) -- the numeric-entry reader,
   `locals 64 words`, the largest local frame in the file outside
   `SETUP8`: string-buffer entry via `SETUP7`, the sentinel-search
   idiom a third time for named-key lookup, radix-prefixed digit
   parsing with a per-digit overflow check. Exact (`params=12/data=128`)
   once the entry buffer was declared a plain default `STRING` (80
   chars) rather than a `STRING[70]` sized to exactly fit the remaining
   frame budget -- a first attempt at the tighter guess landed 5 words
   short; Apple's real buffer is bigger than the tightest fit, not
   sized to consume it exactly. A full 26-procedure diff against
   Apple's shipped binary confirmed nothing else regressed. Filled in
   `SETUP8` too (finding 133) -- the QUIT handler, the largest
   procedure in the file at 398 words: D(isk) writes `NEW.MISCINFO` via
   `REWRITE`/`PUT`/`CLOSE(F,LOCK)`, H(elp) is six literal `WRITE`
   blocks, E(xit) is `EXIT(SETUP)` (this file's own established form --
   `EXIT(PROGRAM)` and `EXIT(PASCALSYSTEM)` both fail, errors 125 and
   104, same as `SETUP2`'s own precedent). M(emory)-update is left an
   intentional stub: Apple's binary pokes `MISCINFO` directly into a
   location reached via the *same* lexical distance every `WRITE` in
   this file reaches `OUTPUT` from -- `PASCALSYSTEM`'s own implicit
   scope, one level above `SETUP` itself, genuinely outside what this
   file can declare until `SYSTEM.PASCAL` is reconstructed. A throwaway
   probe (not part of this file) empirically measured `FILE OF MISCREC`
   alone at 396 words, confirming the rest of the frame is accounted
   for. `params=0/data=792` against Apple's `0/796` -- 2 words short
   (the stubbed M-branch's own loop counter/bound), documented not
   forced; nothing else regressed. Attempted `SETUP19` next (finding
   134) -- compiled clean but landed `data=6` against Apple's real `88`,
   a 41-word gap too large to force, so reverted to a stub rather than
   shipped. Caught a real, reusable rule along the way: a
   `VAR`-parameter group descends like a `VAR`-block local (finding
   93a), but a plain-value-parameter group *ascends* -- the opposite,
   confirmed by comparing `SETUP4`'s and `SETUP11`'s own already-exact
   signatures directly. Filled in `SETUP21` instead (finding 135,
   `params=0/data=84` exact) -- it owns a local `VALUE`/`ENTRY: STRING`
   (41 words) because it calls `SETUP7` directly to read a name;
   `SETUP19` never calls `SETUP7` (it delegates all text entry to
   `SETUP10`), so that pattern doesn't explain its own gap, which stays
   open. `SETUP19` and `TEACHSET`'s own ten tutorial procedures are now
   the only two stubs left in `SETUP.CODE`, the natural next session.

6. **`SYSTEM.LINKER`** -- 51 procedures, one segment. Now also a tool this
   project depends on, so understanding it pays twice.

7. **`SYSTEM.FILER`** -- 56 procedures, one segment.

8. **`SYSTEM.ASSMBLER`** -- 95 procedures in 7 segments, and the acceptance
   authority for everything in `src/native/`. Reconstructing the thing that
   validates the reconstruction is worth doing carefully and last of the
   utilities. Note `6502.OPCODES` and `6502.ERRORS` are its data, and
   finding 103e records how it looks for each.

9. **`SYSTEM.EDITOR`** -- 129 procedures in 7 segments (numbered 1 and
   7-12), the largest single target on the disk set. **Done**: the whole
   file, finding 272.

10. **The operating system** -- `128K.PASCAL` specifically, the only build
    this file targets, reads, or cites; the 64K `SYSTEM.PASCAL` build is
    out of scope entirely, by direct instruction. 7 segments, ~105
    procedures. `ii0src.sdk` is the UCSD II.0 OS source and is genuinely
    relevant here, unlike for the compiler (finding 8).

    **Started** (finding 136, `src/pascal/os/1.3/PASCALSYSTEM.text`): the
    skeleton compiles clean under Apple's own `SYSTEM.COMPILER`, first
    attempt at the restructured file. `CONST`/`TYPE`/`VAR` ported from
    `GLOBALS.TEXT`; its own 41 forward-declared segment-0 procedures (27
    "fixed", 14 "non-fixed") declared in order, giving 42 of segment 0's
    43 procedures a `params` size that already matches Apple's real
    binary exactly (the one mismatch, procedure 43, is already known not
    to be `COMMAND` -- finding 51c). All 7 segments land in their real
    disk slots with their real names; `USERPROGRAM` (segment 1) is a
    real, working body straight from UCSD's own `SYSSEGS.A.TEXT`, and
    matches Apple's real `args 2 words` exactly. Getting there required
    chasing down a real Apple-compiler quirk: `WRITE`/`WRITELN`'s own
    sugar only accepts a plain variable identifier as its file argument,
    not a pointer dereference (`WRITELN(SYSTERM^)` fails on Apple's real
    compiler even though the host compiler accepts it) -- UCSD's own
    source already avoids this, calling `FWRITELN`/`FWRITESTRING`
    directly as ordinary forward-declared procedures, which is what this
    file now does too. Filled in `PRINTERROR` too (finding 137,
    `params=4/data=46` exact) -- not a straight UCSD port, Apple's real
    `CASE` arms rework several messages and add 128K ProFile-specific
    error codes, written directly from the binary's own text. Caught a
    second calling-convention restriction along the way: a literal
    can't bind to a `VAR` parameter through a *direct* call (`SINSERT`
    itself is error 154 on a literal `SRC`), even though Apple's own
    compiled code shows that same literal reaching that same parameter
    -- legal there only as part of the compiler's own lowering of
    ordinary `INSERT` sugar, which has no such restriction of its own.
    Filled in `SCONCAT`/`SINSERT`/`SCOPY`/`SDELETE`/`SPOS` too (finding
    138, what `CONCAT`/`INSERT`/`COPY`/`DELETE`/`POS` sugar lowers to)
    -- all five exact. Found a third real fact along the way: Apple's
    actual parameter *order* for these five is not UCSD's own literal
    text, recovered by reading each real body's own algorithm directly
    (which word is read from, written to, or compared as a plain
    `INTEGER`) rather than assuming a "reverse the list" shortcut,
    which fit some of the five and not others (`SPOS` needed no
    reordering at all).

    Started on `PASCALSY`'s own 451-word global `VAR` section too
    (finding 139) -- what nearly every remaining procedure turned out
    to depend on once checked (`FGOTOXY`, `HOMECURSOR`, `CLEARSCREEN`,
    `CLEARLINE`, `PROMPT`, `SPACEWAIT`, `GETCHAR` all do). Told apart
    two distinct addressing modes the lift shows (`G<n>` = a flat
    segment-0 procedure's own params/locals, *or* a `SEGMENT
    PROCEDURE`'s own absolute reach into the globals, depending which
    kind of procedure it is; `I1,n` = a flat procedure's lex-relative
    reach into the same globals), then confirmed the first two offsets
    by reading `FGOTOXY`'s own real body directly: `SYSCOM` (offset 1)
    and `GFILES[1]` (offset 3 -- the real target of every segment-0
    body's own console-output call, not a separate `OUTPUTFIB`,
    zero reordering from UCSD's own declared order needed). The real
    `SYSCOMREC` type is now declared for real (`CRTINFO`/`CRTCTRL`/
    `MISCINFO`/`SEGTABLE`/the debugger's own mark-stack chain), not yet
    verified field by field beyond `CRTINFO.WIDTH`/`HEIGHT`.
    2 offsets confirmed of a likely 100+ in the full frame -- real
    progress, not a finished reconstruction. Put it to immediate use:
    `FGOTOXY` written for real (finding 140), `params=4/data=0` against
    Apple's real `4/2` -- one documented word (Apple's own body caches
    `SYSCOM+37` in a local this version re-derives instead, same
    behavior). A quick check of `DIGITS`/`UNITABLE` alone (82 words,
    isolated compile) confirmed those two fields' own sizes are right;
    `MAXUNIT` itself was then corrected from UCSD II.0's own `12`
    (1.1's value) to `20` (1.2/1.3's, per Neil Parker's documented
    `DISKNUM` table, finding 141), widening `UNITABLE` by 48 words, and
    `MAX_SEG` from `31` to `63` (same source, finding 142, confirmed
    inert for this frame -- it only widens a heap structure reached
    through the `SYSCOM` pointer). **The 451-word `VAR` section is now
    closed exactly** (finding 143): Parker's own document transcribes
    every field Apple added past UCSD II.0's own `GLOBALS.TEXT` (Dave
    Tribby's reverse-engineered names -- `CONFIG_CHAR` through
    `WHAT_L`, ~26 fields), and it checks out two independent ways
    before typing a line of it: every offset gap in Parker's own list
    matches this file's already-derived word-size formulas exactly,
    and the block's own starting offset landed exactly on this file's
    already-Apple-verified total through `FILENAME`. Procedure 1 now
    compiles to `params=0/data=902` against Apple's real `128K.PASCAL`
    -- an **exact match**, both compilers agreeing, first attempt.
    Field *names* and *individual* types stay STRONG INFERENCE, not
    verified fact (six of them are Tribby's own unidentified
    placeholders, `WHAT_F` through `WHAT_L`) -- what the frame-size
    match verifies is the field *boundaries*, not each identity.
    `HOMECURSOR`/`CLEARSCREEN`/`CLEARLINE` call an unidentified helper
    (`PASCALSY.53`, past procedure 42, likely one of Apple's own
    128K-specific additions) and are genuinely harder than `FGOTOXY`;
    not attempted yet. `PASCALSY.1`'s own real main-loop body is
    started (finding 144): `EMPTYHEAP := NIL`, `UNITCLEAR(1)`,
    `INITIALIZE` all written and verified exact (`params=0/data=902`
    held). The `FINIT`/`FCLOSE` gap closed too (finding 145): the
    "still-misidentified" file variable turned out to be seven of
    finding 143's own Tribby-guessed fields (`WHAT_I`-`WHAT_K`)
    collapsing into one real, opaque, untyped `EXEC_FILE: FILE` (40
    words = `NILFILESIZE` exactly -- nothing in the whole disk set
    references any offset strictly inside that span). Apple's own
    compiler auto-generates the entire `FINIT`/`FCLOSE` sequence from
    that one `VAR` declaration, confirmed byte-for-byte against
    Apple's real compile with zero source written for either call.
    Procedures 44-47 (findings 146/147) -- the EXEC-file buffered I/O
    layer (`EXECPUTCH`/`EXECCLOSE`/`EXECREADBLK`/`EXECWRITEBLK`,
    this project's own names, no UCSD/Tribby precedent for procedures
    past 43) -- are now written and verified exact too, surfacing two
    more of finding 143's own Tribby fields that were mis-split
    (`WHAT_F` -> two pointers, `WHAT_H` -> two booleans, same pattern
    as `WHAT_I`-`WHAT_K`) and establishing the working idiom for
    calling `CLOSE`/`BLOCKREAD`/`BLOCKWRITE` sugar on `EXEC_FILE`
    rather than `FCLOSE`/`FBLOCKIO` directly (type-checking rejects
    the latter). Procedure 50 (`WAITSYSVOL`, finding 148) is now
    written too -- `params` exact, `data` documented one word short,
    a likely-related open question about how `GFILES[1]^` is really
    reached at that point in Apple's own source. `48`/`49` are
    declared only as number-preserving stubs, needed to reach
    `PASCALSY.58` by number from `48`'s own real `REPEAT` loop.
    **The `lex 1` nested group is no longer one undifferentiated
    blob** (finding 149): a full caller-graph read resolved it into
    four small, independent pairs, each nested inside an
    already-identified `lex 0` parent -- `51`/`52` inside `EXECERROR`
    (proc 2), `56` inside `FGET` (proc 7), `55` inside `FBLOCKIO`
    (proc 28), and `57`/`58` inside `48` itself (the one piece with no
    UCSD precedent at all, involving `LOADSEGMENT`/`UNLOADSEGMENT`, a
    `GETCMD.1` dispatch, and a non-local `EXIT`). None of the four
    parents are written for real yet. Starting on that work surfaced
    a labeling trap (finding 150): `G<n>` inside one of these `lex 0`
    procedures' own bodies is *that procedure's own frame* (its own
    params/locals, `SLDO`/`LDO` opcodes), not `PASCALSY.1`'s globals
    -- confirmed by two independent probes -- so `FGET`'s own
    `G12 := G1; ... G12^.f5 ...` is a local pointer copy plus real
    `FIB`-field access, not a read of global word 12. The `FIB`
    record's own real word layout came out of the same probe
    (`FWINDOW`=1 through `FBUFFER`=34 onward, 290 words total) and is
    now corroborated against `SYSTEM.LIBRARY`'s own already-verified
    `PASCALIO.text` (finding 151) -- same field order, confirmed
    independently. **The four pairs are scope-independent but NOT
    order-independent** (finding 152, caught by testing before
    commit): a nested helper's own procedure number is whatever is
    next available when its *enclosing body* is textually written, not
    tied to the parent's own already-fixed `FORWARD` number. The
    required order to keep every number matching Apple's real one:
    `EXECERROR`'s real body (claims 51, 52 for its own two children)
    -> stub or real slots for 53/54 (still unidentified) ->
    `FBLOCKIO`'s real body (claims 55) -> only then `FGET`'s real body
    (claims 56). `48`+57/58 can go anywhere after all of that, since
    its own children are the last two numbers in the group. Start the
    next session on `EXECERROR` -- it is first in this order regardless
    of which pair looks easiest.
    **`51`/`52` are now written for real and VERIFIED BINARY FACT**
    (finding 153): read from `128K.PASCAL`'s own raw p-code directly,
    not the lift's abstracted `.fN` rendering, which had led two
    earlier probes this session into a dead end (guessing `L1` needed
    a `TRICKARRAY` cast built via pointer-type coercion -- both
    rejected by the host compiler). The premise was wrong: `L1 :=
    I2,1` is two lex levels up from a proc nested one level inside
    `EXECERROR`, which reaches the *block itself*, i.e. true global
    word 1 = `SYSCOM` directly -- an ordinary `^SYSCOMREC := ^SYSCOMREC`
    assignment, no cast needed at all. `IND`/`SIND n` is a plain
    zero-based word offset from `SYSCOM`; `SEG`/`JTAB`/`BOMBIPC` only
    fit their printed labels (`"S#"`/`"P#"`/`"I#"`) once finding 93a's
    identifier-group reversal is applied to `SYSCOMREC`'s own two
    3-identifier groups exactly as already declared (no source change
    needed), and the `"I/O error #"` value is `USERINFO.ERRNUM` --
    confirmed structurally via a probe self-assignment inside this
    file's own real, already-verified `VAR` section. The reconstructed
    bodies disassemble instruction-for-instruction identical to the
    real binary (same string literals, same `IND`/`SIND` operands,
    same call sequence) except `CBP` where the real binary has `CXP`
    (expected -- compiled standalone, not through the real split
    segment 0).

    **`EXECERROR` itself is now written for real too** (finding 154),
    whole body, same session. The "`TRICKARRAY` memory-diddle" that
    justified the earlier detour into Hyde's *P-Source* turned out not
    to apply to this procedure at all -- the lift's opaque
    `(G2^.f4[0*13w]+3) <> @I1,63` is nothing but `G2^.GDIRP^[0].DVID <>
    SYVID`, an ordinary `DIRP` dereference through a type already
    declared in this file, no cast needed. `GFILES[0]`/`[1] :=
    INPUTFIB`/`OUTPUTFIB`, `USERINFO.ERRNUM := IORESULT()`,
    `FWRITELN(SYSTERM^)` (a fourth global identified via the same
    probe-and-disassemble method, `SYSTERM`=56), the `MEMAVAIL`
    threshold check, `FETCHDIR`/volume-id/`PRINTERROR` chain, the
    `R_EXEC_FLG`/`W_EXEC_FLG`-gated `EXECCLOSE(TRUE)`, and the
    reboot/hang decision (exact `SET` literals decoded by hand from
    the raw bitmask constants -- `XEQERR IN [1,5,6,8,11,13,14]`, and
    `[1..20]` for the I/O-error sub-case) are all VERIFIED BINARY FACT,
    disassembling instruction-for-instruction identical to the real
    binary apart from two flagged, expected fast-tier compiler-codegen
    differences (constant folding on `2028+50`; short-circuit vs. `LOR`
    codegen for one `OR`).

    **Scope check (finding 155)**: "the rest of the stubs" is 28
    trivial `BEGIN END;` bodies in segment 0 alone, plus four *entire
    other segments* (`FIOPRIMS`, `INITIALIZE`, `GETCMD`, `FILEPROC`)
    that are `BEGIN END` in full and will each decompose into several
    procedures once opened -- `EXECERROR` alone took a full session.
    User direction: work in **dependency order**, not file order, so
    partial progress stays maximally useful.

    `FINIT` (finding 155, `PASCALSY.3`) and the trivial accessors
    `FEOF`/`FEOLN` (`PASCALSY.10`/`11`) are now written and verified.
    `EXECCLOSE` turned out to already be correct from earlier in the
    session (rediscovered, not redone).

    **`FILEPROC`'s real dispatch is now fully mapped** (finding 156),
    read directly from `SYSTEM.PASCAL` 1.3's own `FILEPROC` segment --
    `FILEPROC.1` dispatches on word 6 (`OP`, the first-declared
    parameter, per a new confirmed rule: 156a, separately-declared
    parameter clauses reverse across the whole list, not just within
    one `VAR`/value group as findings 93a/134a covered). All three of
    `FRESET`/`FOPEN`/`FCLOSE`'s own arms are pinned exactly: arm 1
    calls a 1-arg helper with `F`; arm 2 calls a 4-arg helper with
    `F, FTITLE, FOPENOLD, JUNK` (their own original declared order);
    arm 3 runs an inner 0..3 dispatch on `FTYPE: CLOSETYPE` (which only
    resolving `FCLOSE`'s own parameter order under 156a reveals -- word
    1 is `FTYPE`, not `F`) before calling a 2-arg helper with `F,
    ORD(FTYPE)`.

    **`FILEPROC` written for real, `FRESET`/`FOPEN`/`FCLOSE` unblocked**
    (finding 157) -- the predicted variant-record parameter turned out
    unnecessary: `ORD(FTYPE)` at `FCLOSE`'s own call site satisfies the
    shared `ARGINT` slot directly, since a `CLOSETYPE`'s ordinal
    representation already *is* a plain integer. `FILEPROC`'s real
    signature (`OP: INTEGER; VAR F: FIB; VAR ARGSTR: STRING; ARGBOOL:
    BOOLEAN; ARGPTR: FIBP; ARGINT: INTEGER`) is written and compiling
    clean, and all three forwarders now route through it with an
    almost instruction-for-instruction match against the real binary's
    own call sites (`FOPEN`'s call matches literally on every real-
    valued slot). Three small, documented frame-size gaps remain
    (`FRESET` 5 words, `FOPEN` 1 word, `FCLOSE` 4 words) -- all from
    Apple's real binary reading uninitialized don't-care locals where
    this reconstruction passes explicit `FALSE`/`NIL`/`0` instead, a
    deliberate, defensible choice not chased to exact match. Also
    surfaced, still open: this project's own procedure-number count
    puts `COMMAND` at 43, but the real `PASCALSY.43` needs three words
    of params where `COMMAND`'s current forward declaration (matching
    UCSD's own plain, argument-less `COMMAND`) takes none --
    unresolved, flagged for whoever writes `COMMAND` for real (arm 4
    of `FILEPROC`, the file-title normalizer, is not yet exercised by
    any written caller in this file for the same reason).

    **`FILEPROC`'s own arm bodies are still `BEGIN END`** -- the
    dispatcher (`FILEPROC.1`) routes correctly now, but `FRESET`/
    `FOPEN`/`FCLOSE` don't yet *do* anything until `FILEPROC`-segment-
    local procedures 2/3/4/7 (arm 1/2/3/3's-inner-helper) are written
    for real. `FILEPROC.8` (arm 4, the title normalizer) is already
    independently probe-verified by `probe_osproc43.py` and doesn't
    need rework.

    **The `FBLOCKIO` chain remains the other high-value target and the
    harder one**: `FGET`/`FPUT`/`FREADCHAR`/`FWRITECHAR`/etc. all build
    on `FBLOCKIO` (`PASCALSY.28`), a ~110-instruction buffered-disk-I/O
    routine with retry logic that also needs `STUB49` (currently a
    stub) written for real and nests its own `PASCALSY.55`.
    `FREADINT`/`FWRITEINT` are each full parsing/formatting state
    machines (~50-70 instructions), not short wrappers -- confirmed by
    reading their raw p-code directly, not assumed from the header
    comment's word counts.

    **Neither remaining path turned out self-contained on closer
    inspection.** `FILEPROC`'s arm 1 (`FILEPROC`-segment-local
    `PASCALSY`-unrelated proc 3, `FRESET`'s real target) itself calls
    a cross-segment `FIOPRIMS.2` (that whole segment is still `BEGIN
    END`) and `PASCALSY.7`/`FGET` (also still a stub) -- so even
    "finish `FILEPROC`'s arm bodies" transitively needs most of the
    `FIB` layer written first, not just `FILEPROC` itself.
    `PASCALSY.55` (findings 158/159) is now written for real as
    `BLKXFER` and matches the binary's disassembly instruction-for-
    instruction -- all six parameters turned out to be plain values,
    not `VAR` (a correction to 159's own first draft), and the
    `BUFADDR^[BYTEOFS]` indexing that looked ruled out was actually
    right once tested against the real `WINDOWP` type with this file's
    established no-range-check status instead of a placeholder array.
    Still open: `BLKXFER` currently lands on procedure number 53, not
    55 -- the host compiler has never assigned `FBLOCKIO`'s own stub a
    number at all (confirmed pre-existing, not caused by this change),
    so whatever occupies real procedures 53/54 is still unplaced.
    `FBLOCKIO`'s own body is now written whole (finding 161) and
    compiles clean, but is labelled STRONG INFERENCE rather than
    verified: unlike `BLKXFER`, its shape could not be cross-checked
    instruction-for-instruction because `tools/xcompile.py` silently
    omits `FBLOCKIO` from its own compiled procedure table for reasons
    not tracked down (confirmed not dead-code elimination, not a
    `SEGMENT PROCEDURE` in between -- see finding 161's own note). The
    acceptance tier is what would actually confirm this one. `STUB49`'s
    real 3-argument signature is now known (`VAR F: FIB; B, C:
    INTEGER`) even though its body is still a stub. `FILEPROC`'s own
    arm bodies (2/3/4/7 -- makes `FRESET`/`FOPEN`/`FCLOSE` actually
    functional, not just correctly-routed) are the next natural target,
    once `FGET`/`FIOPRIMS.2` are within reach. `STUB49` (the write-time
    file-extension logic `FBLOCKIO` calls into) is now written whole
    (finding 165), after a chain of corrections along the way: its
    real signature is one `VAR F: FIB` parameter, `BOOLEAN` result
    (finding 162, not the three-argument reading finding 161 first
    assumed); its body calls `VOLSEARCH` (verify the file's volume is
    still on the same unit) and `WRITEDIR` (finding 163), both
    identified by frame-size match against signatures already declared
    in this file; `DIRENTRY`'s own real field offsets (finding 164,
    probe-verified after a hand-counted guess got them wrong the same
    way `FIB`'s did) resolve the guard clause and directory-scan loop;
    and the body's full logic (compute an extension boundary, skip the
    write if there's already room, otherwise extend the matched entry
    and write it back, then update `F`'s own cached fields -- including
    the `STP 7, 9, 100` mystery, resolved as `DATEREC.YEAR := 100`,
    this file's own documented "temp-disk flag") is finding 165 itself.
    Compiles clean; close but not exact frame-size match, the same
    situation as `FBLOCKIO` (not the higher-confidence verified match
    `BLKXFER` got). `FILEPROC.1`'s own dispatch body is now written too
    (finding 166) -- three of its four arms (`OP=1,2,4`) match the real
    binary's instruction shape exactly (proc-number gap aside, the same
    kind of gap already seen for `BLKXFER`); arm 3 is a deliberate,
    documented simplification. `FPTITLE` (`FILEPROC.8`, arm 4) is now
    written for real too (finding 167) -- `params` exact, `locals` five
    words short, documented not forced; identified all four of its
    `CXP` calls (`SCONCAT`/`SINSERT`/`SCOPY`/`SDELETE`/`SPOS`, segment
    0's own string-sugar helpers) and cross-checked against
    `probe_osproc43.py`'s own independent facts about the real binary.
`FPRESET` (arm 1, `FILEPROC.3`) and its own block-advance
    helper `FPNEWBLK` (`FILEPROC.2`) are now written for real too
    (finding 168) -- turned out to need no `FIOPRIMS` dependency at
    all, contrary to an earlier assumption made before either was
    actually disassembled; the only remaining stub in that path is
    `FGET` itself. `FPOPEN`/`FPCLOSE` (arms 2/3, `FILEPROC.4`/`.7`)
    remain `BEGIN END` -- `FPCLOSE`'s target is large (~140
    instructions, several still-unidentified `CXP` calls) and
    `FPOPEN`'s has its own nested helpers (`FILEPROC.5`/`.6`) neither
    attempted yet. `FGET`'s own real shape is now mapped (finding
    169), but it turned out **not** to be the clean next target
    finding 168 expected: three separate branches of its main loop
    call directly into `FIOPRIMS` (segment 2, still entirely
    unwritten, no internal procedure numbering at all) for soft-buffer
    window advance, `DLE`-indentation handling, and `TEXTFILE` byte
    expansion -- load-bearing control flow, not a prerequisite that
    can be stubbed around. `PASCALSY.56` is also now confirmed nested
    *inside* `FGET` itself (the lex-1 nested group finding 149 first
    surfaced), for the `EXEC`-redirect read-mirror path. `FIOPRIMS`
    itself -- specifically its own procedures 2/3/4 -- is the actual
    highest-leverage target now, not `FGET` directly. `FIOPRIMS`'s own
    five-procedure layout is now mapped and three signatures confirmed
    by argument-count match (finding 170): `.2`/`.3` are `FUNCTION
    (VAR F: FIB): BOOLEAN`, `.4` is a plain `PROCEDURE (VAR F: FIB)`.
    `.2`'s own body was read in full (soft-buffer window advance via
    `MOVELEFT`/`UNITREAD`/`UNITWRITE`) but its exact byte-count
    arithmetic isn't confidently resolved -- left undone rather than
    guessed. `.3`/`.4` are now written for real (finding 171): `.3`
    (`FPDLE`) is DLE-blank expansion, priming `F.FREPTCNT` so `FGET`'s
    own early-return guard replays a cached space with no further I/O;
    `.4` (`FPPEEK`) is a speculative lookahead `GET` with rollback for
    `TEXTFILE` `EOLN` detection, snapshotting the whole `FIB` via a
    plain record assignment. Both compile clean, close-not-exact on
    `locals`. `FIOPRIMS.2` (soft-buffer window advance) remains the one
    real gap in this segment -- the harder routine, not chased further
    this session. `FPOPEN`'s own real target (`FILEPROC.4`) is mapped
    but not attempted as a body (finding 172): ~340 instructions, an
    order of magnitude larger than anything else in this file so far,
    with its own nested helper (`FILEPROC.5`, itself nesting `.6`) --
    genuinely multi-session-scale, not something to force. Confirmed
    three more segment-0 identities along the way by exact frame-size
    match: `32=DIRSEARCH`, `33=SCANTITLE`, `34=DELENTRY`, placing five
    of the file's six "non-fixed forward declarations" against real
    procedure numbers (only `INSENTRY` still unplaced). `FPCLOSE`
    (`FILEPROC.7`) is now written whole too (finding 173) -- turned out
    tractable where `FPOPEN`'s target wasn't, since the vocabulary
    findings 161-172 built up (`STUB49`'s scan-loop idiom, `DIRENTRY`'s
    real offsets, `VOLSEARCH`/`DIRSEARCH`/`DELENTRY`/`WRITEDIR`) all
    recur directly in it: all four `CLOSE` modes (`CNORMAL`/`CLOCK`/
    `CPURGE`/`CCRUNCH`), directory-entry deletion/replacement, and
    `DACCESS` date-stamping logic. `params` exact, `locals` two words
    short. `FILEPROC` now has only `FPOPEN` (arm 2, `FILEPROC.4`, ~340
    instructions with its own nested helper chain) left unwritten as a
    body -- everything else in this segment is real. `FPWINADV`
    (`FIOPRIMS.2`, soft-buffer window advance) is now written too
    (finding 174), closing out `FIOPRIMS` entirely -- `params` exact,
    `locals` two words short, from two identified, host-compiler-only
    gaps (a redundant `WITH F DO` address cache the host tool always
    collapses away, and `DIRENTRY.DLASTBYTE` compiling packed under
    this host tool where the real binary's own access is a plain word).
    That second gap is latent in every already-written `DLASTBYTE`
    reference in this file (`STUB49`, `FPCLOSE`) too, previously
    undetected. `FPOPEN`'s own two nested helpers are now written for
    real too (`FPALLOC`/`FPGAP` = `FILEPROC.5`/`.6`, findings 175-176):
    a free-space-for-a-new-file search tracking the largest and
    second-largest gaps between directory entries, matching this
    project's own documented UCSD `[*]` allocation algorithm -- `params`
    exact, instruction count exact (`177`/`25`) against the real binary
    for both, the tightest match anywhere in this file's whole
    forward-declared-far-from-body class. Along the way `PASCALSY.35 =
    INSENTRY` was confirmed, placing the last of this file's six
    non-fixed forward declarations, and `FTID` had to become a `VAR`
    parameter (a value `STRING` costs the callee an 8-word local shadow
    copy this file's own routines never carry). `.4` (`FPOPEN` itself,
    472 instructions, the one procedure that actually calls `FPALLOC`)
    is now the only body left unwritten anywhere in
    `FILEPROC`/`FIOPRIMS`. Its full disassembly is now read in
    structural outline (finding 177): every real branch identified by
    known call sites (`SCANTITLE`/`VOLSEARCH`/`DIRSEARCH`/`FPALLOC`/
    `WRITEDIR`/`FPRESET`/`FPNEWBLK`) and cross-checked against the
    `IORSLTWD` enum's own error names, which line up with what each
    branch is actually doing -- a `RESET`-vs-`REWRITE` split on
    `DIRSEARCH`'s result, directory-entry population, and a soft-buffer
    setup tail. **One open blocker**: the stub's guessed third
    parameter (`OLDOK: BOOLEAN`) is contradicted by the real bytecode
    (`SLDL 2; SLDC 1; GRTI`, then compared against `2`/`4` -- no
    two-valued `BOOLEAN` produces that), so the real type needs settling
    -- possibly also implicating `FILEPROC.1`'s own dispatcher call
    site (finding 166) -- before a candidate body can even declare the
    right signature. Several stretches (a `MARK`/`RELEASE` heap-scratch
    block, the exact `FHEADER` population order) still need a closer
    read too. Genuinely multi-session scale, as finding 172 already
    said -- this pass narrows what's left rather than closing it.

    **The `OLDOK` blocker is now resolved as far as static analysis can
    take it (finding 178)**: an exhaustive search of every call site in
    all six of `128K.PASCAL`'s segments confirms `FILEPROC`'s
    dispatcher has exactly three callers (`FRESET`/`FOPEN`/`FCLOSE`,
    matching `PASCALSY.4`/`.5`/`.6`) and no undiscovered fourth one --
    the real value really is a plain `0`/`1` boolean from every known
    caller. Loose `BOOLEAN`/`INTEGER` typing is also ruled out (this
    host compiler rejects it outright) and a plain `ORD()` cast gets
    constant-folded away by the compiler's own static boolean-range
    analysis. What *does* work: `TRICKARRAY` (this file's own existing
    "memory diddling" union type) reinterprets `OLDOK`'s raw bits in a
    way the compiler can't statically bound, reproducing the real
    binary's own `GRTI`/`EQUI` comparisons exactly. One gap remains
    before writing the body: the real binary's `(P2=2) OR (P2=4)`
    compiles to a literal `LOR`, but every source variant tried this
    session compiles through this host tool to a short-circuit `FJP`
    chain instead -- not yet resolved, plausibly another host-compiler
    divergence (findings 174/176's own class) rather than a wrong
    reading. A small unrelated gap was also caught in the process:
    `FOPEN`'s own already-written forwarder passes a literal `0` for
    `FILEPROC`'s `ARGINT` slot where the real binary reads a genuine
    global (`SLDO 5`) instead -- not fixed this session.

    **The `LOR` gap turned out general, not FPOPEN-specific (finding
    178's own follow-up)**: the already-committed `FPCLOSE` body, which
    itself uses `AND`/`OR` several times, also never emits `LAND`/`LOR`
    under this host compiler -- it always short-circuits. New memory:
    `host-compiler-always-shortcircuits`. This affects every `AND`/`OR`
    in this file's reconstructed source, not just this one comparison.

    **The preamble itself is now drafted and test-compiled (finding
    179)**, though not committed to source: `LOD 2,55` is `SWAPFIB`
    (confirmed by probe), `LDA 2,126` is `UNITABLE`'s own base. Real
    control flow: guard `F^.FISOPEN`, call `SCANTITLE` (success is the
    `THEN` branch, not `NOT`-wrapped), compute the `TRICKARRAY`-derived
    `OLDOK` flag, then gate a `MARK`/`RELEASE`/`UNITABLE`-search
    bootstrap fallback on `SWAPFIB^.FISOPEN AND (SYSCOM^.GDIRP = NIL)`.
    That whole fallback block, the directory-search/`FPALLOC`/
    `INSENTRY` path, and the soft-buffer setup tail remain undecoded --
    this covers roughly the first 15% of the routine. Not committed:
    this file's own convention is a complete, compiling procedure
    before landing it, not a partial one.

    **Extended past `VOLSEARCH` (finding 180)**: every `F^`-field write
    once a volume is found (`FISOPEN`, `FMODIFIED`, `FUNIT`, `FVID`,
    `FNXTBLK`, `FISBLKD`, `FSOFTBUF`) matches its already-established
    offset exactly, field-by-field against the real instructions, and
    `OLDOK`'s own storage gets overwritten with the `TRICKARRAY`-derived
    flag matching the `STL 2` writeback finding 178 first flagged. The
    `DIR<>NIL AND LENGTH(TID)>0` branch gating `DIRSEARCH` also matches
    exactly. The **one remaining blocker** before this whole section can
    compile as a real, testable candidate is the bootstrap fallback
    block itself (`MARK`/`RELEASE`/`UNITABLE`-linear-search, magic
    constants `2028`/`400`) -- a *structural* gap (a whole missing
    branch), not the usual small "word or two short" class this file
    otherwise tolerates, so not committed until that block is decoded
    too.

    **That blocker is now cleared (finding 181)**: the bootstrap block
    is an emergency swap-out, gated three levels deep (`SWAPFIB^
    .FISOPEN AND GDIRP=NIL`, then two heap-growth-bound checks via
    `MARK`/`ORD()`-on-pointers, then a `UNITABLE`-vs-`SWAPFIB^.FVID`
    consistency check) before it `UNITWRITE`s the free-heap area out to
    the swap file and releases back to `EMPTYHEAP`. Compiles clean as a
    standalone candidate covering the full preamble through `VOLSEARCH`
    (addr 608-786). One new host-compiler quirk found doing this: `2028
    + 400` gets constant-folded to `LDCI 2428` here, where the real
    binary keeps it as two separate pushes plus a runtime `ADI` --
    another instance of the already-accepted "compiler decides
    differently than Apple's did" class (findings 174/176/178). Still
    not committed -- the `DIRSEARCH`/`FPALLOC`/`INSENTRY` path and the
    soft-buffer setup tail (roughly addr 787-1358) are the only piece
    of `FPOPEN` left entirely undrafted now.

    **`DIRSEARCH`/`FPALLOC`/`DELENTRY` decoded and compiled (finding
    182)**: found-vs-not-found on `DIRSEARCH`, crossed with `OLDOK`,
    branches to `RESET`-style-found/`REWRITE`-style-create-new; a new
    file's `KIND` defaults to `DATAFILE` when `SCANTITLE` left it
    `UNTYPEDFILE`; `SEGS` (`SCANTITLE`'s own segment-count output)
    doubles as `FPALLOC`'s requested size; a non-`TEXTFILE` entry gets
    its `DLASTBLK` shrunk by one block, and `DELENTRY`'d back out if
    that leaves it `<= 4` blocks. Caught a real, generally-useful bug
    along the way: a local var named identically to its own type
    (`VID: VID`, `TID: TID` -- this file's own established style)
    shadows that type for every *nested* scope, breaking `FPALLOC`'s
    own `VAR FTID: TID` parameter with a confusing "unknown symbol" at
    the nested site, not the shadowing declaration. New memory:
    `var-type-name-collision`. Compiles clean as a complete standalone
    procedure (`params` exact) covering the whole preamble through this
    section. Only the soft-buffer setup tail (addr 1050-1358, ~290
    instructions) remains before `FPOPEN` can be assembled and
    committed whole.

    **Soft-buffer setup tail decoded, full candidate compiles (finding
    183)**: the last piece. `FHEADER.DFIRSTBLK/DLASTBLK/DFKIND/DTID/
    DLASTBYTE/DACCESS` synthesized from scratch for the "open with no
    title" arm (a sibling of finding 182's `DIRSEARCH` arm, not a
    continuation of it -- both converge at addr 1130); `FMAXBLK`, the
    `FSOFTBUF`-gated `FNXTBYTE`/`FMAXBYTE`/`FBUFCHNGD` setup, a new
    `TEXTFILE`'s two zero-filled header blocks, the `FPRESET`/
    `FPNEWBLK` dispatch on `OLDOK`, and finding 181's emergency
    swap-*out* finally mirrored by a swap-back-*in* (`UNITREAD`)
    gated on `FLAG`. Confirmed every mid-body error return in the
    whole routine is an explicit `GOTO` to a shared exit label, not
    implicit control flow -- `LABEL 999; ... GOTO 999 ... 999: END`
    reproduces it. Full candidate compiles clean, `params` exact
    (`8` bytes), `locals` `42`/`50` bytes (`21`/`25` words).

    **Locals gap explained, `FPOPEN` committed (finding 184)**: the
    4-word gap isn't unique to `FPOPEN` -- checking every
    already-committed procedure in this same segment the same way
    turns up the identical pattern everywhere (the dispatcher,
    `FPNEWBLK`, `FPRESET`, `FPALLOC`, `FPCLOSE` short 1-2 words each,
    `FPTITLE` short 5), the same already-documented "missing `F`-cache"
    host-compiler gap (findings 174/179/180) simply accumulating more
    on `FPOPEN` because it's the largest routine in the file and
    dereferences `F^`/`F^.FHEADER`/`UNITABLE[UNITNO]` more times than
    anywhere else. **`FPOPEN` is now committed** to
    `PASCALSYSTEM.text` -- the last undrafted routine in
    `FILEPROC`/`FIOPRIMS` is closed.

    **`DIRSEARCH`/`DELENTRY`/`INSENTRY` written for real (finding
    185)**: `FPOPEN`'s remaining segment-0 dependencies were still six
    stubs (`VOLSEARCH`, `WRITEDIR`, `DIRSEARCH`, `SCANTITLE`,
    `DELENTRY`, `INSENTRY`). Sized all six by real instruction count
    first: `INSENTRY` 39, `DELENTRY`/`DIRSEARCH` 44 each -- tractable
    in one pass -- versus `WRITEDIR` 128, `VOLSEARCH` 244, `SCANTITLE`
    353, each its own undertaking. `DIRSEARCH` scans for an entry
    matching both `DTID` and a permanent-vs-temp status test against
    `DACCESS.YEAR <> 100` (this file's own temp-file sentinel, finding
    173); `DELENTRY`/`INSENTRY` are a shift-down/shift-up pair around
    the directory array. A second, independent instance of the
    `DLASTBYTE`-class packing divergence (finding 174) turned up on
    `DNUMFILES` (also a subrange alone in its own word, also read
    unpacked by Apple's real compiler where this host tool always
    packs it). All three compile clean, `params` exact, `locals`
    short by 1-2 words each -- inside finding 184's own established
    range -- and are now committed. `VOLSEARCH`, `WRITEDIR`, and
    `SCANTITLE` remain stubs, the natural next targets in that
    ascending-size order.

    **`WRITEDIR` written for real (finding 186)**: a single boolean
    local reused across a three-tier guard chain -- volume-ID/tag
    consistency, then either a "written very recently with interrupts
    off" fast path or a re-read-and-compare-`DVID` paranoid check,
    then the real `UNITWRITE` of `(DNUMFILES + 1) * 26` bytes to block
    `2`. `DIR[0].DLASTBLK = 10` (an otherwise-unused field on this
    variant, repurposed as a flag) triggers a second redundant copy to
    block `6` -- a 128K-ProFile-specific feature, the same theme as
    `PRINTERROR`'s own 128K-specific codes (finding 137). Any failure
    anywhere in the chain invalidates `UNITABLE[FUNIT]`'s own cached
    `UVID`/`UEOVBLK` at the end, forcing a fresh `VOLSEARCH` next time.
    Compiles clean, `params` exact, `locals` short by 2 words (same
    accepted class). Committed. `VOLSEARCH` and `SCANTITLE` -- the two
    largest of `FPOPEN`'s remaining dependencies -- are what's left.

    **`VOLSEARCH` written for real (finding 187)**: found a bigger
    dependency this project hadn't identified -- `CBP 42`, matching
    `FETCHDIR(FUNIT): BOOLEAN`'s already-declared signature by frame
    size, and itself a ~234-instruction routine (comparable to
    `VOLSEARCH`'s own size). Written around it as an opaque call, the
    same way `FPOPEN` was written around `FPRESET`/`FPNEWBLK` before
    those existed. `VOLSEARCH`'s own logic: parse a `"#nn"` unit-number
    reference (confirming a new fact, `MAXUNIT = 20`) or fall back to a
    named search of `UNITABLE`; verify/fetch the found unit's directory
    (trusting a fresh `SYSCOM^.GDIRP` cache via the same `WRITEDIR`-
    established freshness idiom, or calling `FETCHDIR`); and, if
    `LOOKHARD` is set and nothing panned out, one more unconditional
    `FETCHDIR`-every-unit pass. `FDIR` comes back `NIL` for a
    non-block unit -- confirmed as `VOLSEARCH`'s own real contract, not
    just an assumption `FPOPEN` was already relying on (findings
    182/183). Compiles clean, `params` exact; `locals` are *longer*
    than real here (`16` vs `12`) -- named per-phase booleans instead
    of the real binary's single reused scratch word, a deliberate
    readability choice. Committed. `SCANTITLE` (353 instructions, the
    largest of the original six) and `FETCHDIR` (~234, newly
    surfaced) are what remain before `FPOPEN`'s whole dependency chain
    is closed.

    **`FETCHDIR` written for real (finding 188)**: reads a unit's
    directory into `SYSCOM^.GDIRP` (lazily `NEW`'d), validates it, and
    caches the result -- closing `VOLSEARCH`'s own last dependency. A
    real access-control check turned up new to this project:
    `DFKIND` must match the variant appropriate to the current
    `SYSCOM^.MISCINFO.USERKIND` (`BOOKER` accepts anything; the
    `AQUIZ`/`PQUIZ` "quiz mode" pair requires `SECUREDIR`; `NORMAL`
    requires `UNTYPEDFILE`) -- Apple Pascal's own documented
    restricted-access feature, enforced for the first time in this
    reconstruction. Self-healing on read: only when the directory's
    name actually changed does it walk every entry, `DELENTRY`ing
    (finding 185) anything structurally invalid and `UNITWRITE`ing the
    cleaned result back (`WRITEDIR`'s own shape, finding 186). A real,
    documented `NEW`-argument divergence: the real binary passes an
    explicit `1014`-word size, this host compiler refuses any extra
    argument to `NEW` on a variant-record array, so the candidate
    calls plain `NEW(SYSCOM^.GDIRP)` -- behaviourally equivalent since
    the element count is fixed at compile time either way. Compiles
    clean, `params` exact; `locals` short by `8` bytes (`4` words),
    the biggest gap yet but still the same accepted "missing
    address-cache" class (this routine dereferences `SYSCOM^`/
    `UNITABLE[FUNIT]`/`SYSCOM^.GDIRP^[...]` more than almost anything
    else in the file). Committed. `SCANTITLE` (353 instructions) is
    now the only remaining stub in `FPOPEN`'s whole dependency chain.

    **`SCANTITLE` written for real -- `FPOPEN`'s whole chain closed
    (finding 189)**: the largest of the six (353 instructions).
    Parses `VOLNAME:FILENAME.EXT[size]` into `FVID`/`FTID`/`FSEGS`/
    `FKIND`: normalize (strip blanks/controls, upshift letters);
    `'*'`/`'%'` volume-prefix shorthands (`SYVID`/a second,
    unidentified global -- see below); a `:`-delimited volume name
    (over 7 characters is left alone entirely); a `<=15`-character
    file ID before an optional `[...]` size spec, where a lone `'*'`
    inside the brackets is `CLAUDE.md`'s own already-documented `[*]`
    sentinel (`FSEGS := -1`); and a suffix-driven `FKIND`
    (`.TEXT`/`.CODE`/`.BACK`/`.INFO`/`.GRAF`/`.FOTO`, with `.BACK`
    mapping to the same `TEXTFILE` kind as `.TEXT` -- a real,
    previously-undocumented fact). Written using `COPY`/`DELETE`/
    `POS` sugar rather than direct `SCOPY`/`SDELETE`/`SPOS` calls,
    since the real disassembly's own push shapes at those call sites
    don't match a direct call's established order (finding 138
    already established the sugar as what these routines exist for).
    One open detail: `'%'`'s own target global (real word offset
    `444`) wasn't identified by name; the candidate uses `DKVID` as a
    documented placeholder. Compiles clean, `params` exact; `locals`
    longer than real by 41 words (named working variables instead of
    the real binary's tighter scratch reuse, same direction as
    `VOLSEARCH`'s own gap). Committed -- **this closes `FPOPEN`'s
    entire dependency chain**: every routine it calls, transitively,
    is now written for real.

    **`FGET` decoded in full, but blocked by a real host-compiler
    limitation (finding 190)**: a `FORWARD` declaration cannot be
    completed by a nested declaration across a `SEGMENT PROCEDURE`
    scope boundary under this host compiler -- confirmed with an
    isolated four-line repro, not a mistake in how the declarations
    were written. `FGET`'s dependencies (`FPWINADV`/`FPDLE`/`FPPEEK`,
    `FIOPRIMS.2`/`.3`/`.4`) are correctly nested inside `SEGMENT
    PROCEDURE FIOPRIMS` (required for their real procedure numbers,
    already verified in findings 170/171/174), which makes them
    invisible to `FGET`'s own sibling scope by ordinary Pascal rules;
    adding matching outer `FORWARD`s and completing them with the
    short form inside `FIOPRIMS` (mirroring how `FGET` itself is
    completed at the outer level) does not work. `FGET`'s own full
    body is decoded regardless (closes finding 169's open question:
    `SYSCOM^.CRTINFO.EOF`, word 41 offset 0, is the terminal's
    configured EOF character; `CBP 44` confirmed = `EXECPUTCH`;
    `FPPEEK` confirmed a plain `PROCEDURE`, not a `FUNCTION`, and
    calls `FGET` back -- genuine mutual recursion). Nothing committed;
    left open as a structural blocker, not the usual close-but-
    inexact class, worth flagging since it will recur for any other
    cross-`SEGMENT PROCEDURE` call this file still needs.

    **`HOMECURSOR`/`CLEARSCREEN`/`CLEARLINE`/`PROMPT` written for real
    (finding 191)**: four `CRTCTRL`-escape-sequence routines
    (`PASCALSY.36`-`.39`), flagged since finding 139c as depending on
    a then-unidentified shared helper (`PASCALSY.53`), decoded and
    written once that helper's own body was read directly. Shared
    shape: write `CRTCTRL.ESCAPE` unless `CRTCTRL.PREFIXED[idx]` says
    this control function doesn't need it, write the control
    character, then `FILLER`'s padding nulls if `FILL_LEN > 0`.
    `CLEARSCREEN` calls `UNITCLEAR(3)` (Apple's own console driver
    apparently treats the CRT as unit `3`) before its `ERASEEOS`/
    `CLEARSCREEN` fallback; `CLEARLINE` has a real third tier for
    terminals with neither `ERASEEOL` nor `CLEARLINE`: blank the line
    with literal spaces and an `RLF`. Along the way, a live
    demonstration of this file's own "declaration order is the
    numbering, no gaps" rule: factoring the shared helper into its own
    top-level `FORWARD` shifted every later procedure number by one
    (`HOMECURSOR` itself landed on `37` instead of `36`, caught by
    recompiling and comparing against the real binary) -- reverted,
    inlined at each of the three call sites instead, leaving
    `PASCALSY.53`'s own real declaration position unresolved. All four
    compile clean, `params=0` exact, numbers unchanged. Committed.

    **`STUB48` written for real, with two nested helpers (finding
    192)**: `PASCALSY`'s own top-level "wait for the system volume,
    read commands, launch the user program" loop, called directly
    from the program's own outer `BEGIN...END` (not from `COMMAND`).
    Nests `GETNEXTCMD` (real `.57`) and `CMDDISPATCH` (real `.58`).
    Every global it touches -- `STATE`, `SWAP_ON`/`SWAP_1_ON`/
    `SWAP_2_ON`, `WHAT_H1`, `CHAIN_NAME`, `USERINFO.ERRNUM`/
    `.CODEFIBP` -- turned out already declared; `WHAT_H1`'s own
    pre-existing comment ("tested/cleared around user-program
    dispatch, `PASCALSY.57`") independently confirmed this session's
    read of `.57` before it was even written. `GETNEXTCMD` reads
    commands via `GETCMD` and either launches `USERPROGRAM` or
    re-arms the swap flag, with post-command cleanup (`FETCHDIR`
    re-verify, `FCLOSE`-and-lock the scratch code file after a
    compile-only command, lock both console files after a
    program-load command, clear a busy console unit). `CMDDISPATCH`
    and `STUB48` itself are two more layers of the same "wait, read,
    maybe launch" shape. Compiles clean, `params=0` exact throughout;
    `CMDDISPATCH` also matches the real binary's own instruction count
    exactly (`19`). Lands on this candidate's own numbers `54`/`55`,
    not real `57`/`58` -- the same pre-existing `BLKXFER`-class
    numbering drift, not new. Committed.

    **Five more small stubs written for real (finding 193)**:
    `XSEEK`/`XREADREAL`/`XWRITEREAL` (`.9`/`.14`/`.15`, UCSD's own
    never-implemented `SEEK`/real-number I/O -- `SYSCOM^.XEQERR := 11;
    EXECERROR`, all three byte-identical) and `FREADLN`/`FWRITELN`
    (`.21`/`.22`, small wrappers around the still-blocked `FGET`/
    `FPUT` that will start doing real work once those are written).
    All five compile clean with **exact instruction counts against the
    real binary**. Committed.

    **Five real-hardware experiments ruled out five plausible fixes for
    the `FGET`/`FIOPRIMS` cross-segment call (finding 194)**: tested
    directly against Apple's own 1.3 `SYSTEM.COMPILER` under AppleWin,
    not just the fast tier. A plain outer `FORWARD` completed one level
    inside a `SEGMENT PROCEDURE` fails identically on real hardware
    (error 123, matching finding 190's host-tool read); marking the
    `FORWARD` itself `SEGMENT` doesn't change that; declaring each
    helper as its own independent top-level `SEGMENT` compiles but
    produces three separate segments, not one shared `FIOPRIMS`;
    repeating the full header at the nested completion site compiles
    but silently shadows instead of binding; an inline Regular `UNIT`
    compiles its own block but fails `USES` with "Unit not in library."
    `FGET`/`FPUT` and their dependents stay stubs; two angles (an actual
    library round trip for a `UNIT`-based `FIOPRIMS`, re-reading
    `PASCALIO.text`'s own `CXP 0,7` comment) are untried.

    **`INITIALIZE` written for real from UCSD's own `SYSSEGS.A.TEXT`,
    and the whole file compiles clean under Apple's real 1.3 compiler
    for the first time (finding 195)**. All 11 real procedures mapped
    with high confidence against UCSD's own source (`INITSYSCOM`/
    `INIT_FILLER`/`INITUNITABLE`/`INIT_ENTRY`/`INITHEAP`/
    `INITWORKFILE`/`TRY_OPEN`/`INITFILES`, plus two Apple-only nested
    helpers UCSD has no equivalent for); `.7`/`.8` match the real
    binary exactly on params/data/instructions, most of the rest close
    or exact on at least one axis. Two real `CSP 21`/`22` calls
    (`LoadSegment`/`UnloadSegment`) bracket the whole body in the real
    binary but aren't implemented as callable identifiers in either
    compiler -- left out, open question. Getting this to compile
    surfaced and fixed **four real Apple-compiler divergences the fast
    tier had been silently letting through in already-committed code**:
    a string literal can't bind to a `VAR STRING` parameter (`FPTITLE`/
    `PRINTSPI`/`PRTXEQER`/`EXECERROR`, all pre-existing); a block's
    `VAR` section can't follow its own nested procedure declarations
    (`EXECERROR`); a niladic CSP called with `()` is a hard parameter-
    count error on real Apple, not just a style warning (`IORESULT()`/
    `MEMAVAIL()` in `EXECERROR`); `@` doesn't bind to a `VAR` formal
    parameter (`FBLOCKIO`'s own call into `BLKXFER`, fixed by making
    `BLKXFER`'s own `BUFADDR` a `VAR WINDOW` instead of a `WINDOWP`).
    All four fixed; the full 3746-line file now compiles start to
    finish under AppleWin with zero fatal errors -- the first time the
    whole file has been run through the acceptance tier at once.

    **`GETCMD` scaffolded -- 26 number-preserving stubs, real
    procedure sizes catalogued (finding 196)**. Real `GETCMD` has 27
    procedures against UCSD's own `SYSSEGS.B.TEXT` (`github.com/dhlav/
    ucsd-psystem-os`) 7 -- the menu loop, `ASSOCIATE`/`SYS_ASSOCIATE`/
    `STARTCOMPILE`/`FINISHCOMPILE`/`EXECUTE`/`RUNWORKFILE` chain all
    recognizably survive, but real `.11`-`.18` are a whole
    INTRINSIC-unit-availability checker with no UCSD precedent at all
    (reads `SYSTEM.LIBRARY`'s own segment table, reports missing units
    by number). Every real procedure's `params`/`data`/instruction
    count read off the binary and recorded in the file's own header
    comment for the next session. All 27 compile clean, verified on
    real Apple 1.3 hardware. Next: `.2`/`.3`/`.19`/`.20` have real UCSD
    source to work from directly; `.11`-`.18` need a from-scratch
    decode; `GETCMD.1`'s own menu-loop body needs every other procedure
    written first and its own careful arm-by-arm decode.

    **`.4`/`.23`/`.26` written for real (finding 197)** -- `GETYESNO`,
    `EXECOPNERR`, `SWAPMENU`, all with no UCSD precedent. Caught the
    literal-into-`VAR STRING` divergence (finding 195) recurring live,
    mid-session, in two of the three: both first compiled to within
    one instruction of the real binary using a literal bound directly
    to `FWRITESTRING`'s own `VAR` parameter, which fails on real Apple
    hardware -- fixed with a scratch `MSG` var, same as finding 195,
    at a real and now-documented word/instruction cost against the
    otherwise-near-exact match. All three verified compiling clean on
    real Apple 1.3 hardware, whole file.

    **`PASCALSY.43` finally named and written for real -- `TITLENORM`
    -- and `GETCMD.6` (`BADTITLE`) with it (finding 198)**. `PASCALSY.
    43` sat under the wrong name (`COMMAND`, ruled out by finding 51c
    long ago but never fixed) and the wrong signature; now it's the
    real seven-instruction forwarder into `FILEPROC` arm 4 (`FPTITLE`),
    exact on params and instructions against the real binary.
    `BADTITLE` (`SCANTITLE` plus an "Illegal filename" report) is
    exact on params/data, close on instructions. `GETCMD.27`
    attempted and reverted: its own real body calls `FOPEN` directly
    on `EXEC_FILE`, which is declared `FILE` (finding 145) not `FIB`
    -- a real type mismatch `ucsdpsys_compile` rejects outright, not
    resolved this session. Left open rather than forced. Two follow-up
    experiments on real Apple hardware ruled out the two obvious
    fixes: an untyped `VAR F` parameter for `FOPEN` doesn't even parse
    (error 7), and a plain `FILE`-typed actual against `FOPEN`'s own
    `VAR F: FIB` fails with "Illegal actual parameter" (error 142) --
    yet the real binary's own disassembly (`LDA 2,396` into `CXP 0,5`)
    is unambiguous that this exact call really does happen. Still
    open.

    **`FIOPRIMS` is an INTRINSIC UNIT, and that is why `FGET` would
    never compile (finding 200)** -- the single most important result
    in this file so far. The segment dictionary's `SEGKIND` word
    (`0x0C0 + 2*slot`), which `codefile.py` documented from the day it
    was written and never parsed, reads `LINKED_INTRINS` for
    `FIOPRIMS` and `LINKED` for every other segment of both 1.3
    operating systems. Every code segment of `SYSTEM.LIBRARY` -- units
    this project has already reconstructed -- reads back the same way,
    and 1.1 has no `FIOPRIMS` at all (segment 2 there is `DEBUGGER`).
    So findings 190 and 194 spent five real-hardware experiments on
    `SEGMENT PROCEDURE` shapes testing a premise one unread word
    contradicts. The unit reading explains everything they could not:
    one shared segment (one `IMPLEMENTATION`), `FIOPRIMS.1` with zero
    instructions (an empty initialization part), and `FGET` naming
    `FPWINADV`/`FPDLE`/`FPPEEK` at all (they are in the `INTERFACE`).
    Now a probe (`probe_segkind.py`, in `build_all.py`) and a column
    in `analysis/diskset-inventory.txt`. The real shape --
    `(*$U-*)`/`UNIT FIOPRIMS; INTRINSIC CODE 2;`/`INTERFACE`/
    `IMPLEMENTATION`/`BEGIN END;` -- is confirmed compiling on real
    hardware, and `src/pascal/units/1.3/PASCALIO.text` is already
    exactly that shape and already verified, so the template is in
    hand. What remains is build wiring, not language: the host needs a
    real `USES`, which needs the unit compiled to a library first.

    **`GETCMD.2` (`RUNWORKFILE`) written for real -- and a real
    numbering-mechanism correction along the way (finding 199)**.
    Discovered by accident while giving `RUNWORKFILE` forward access to
    still-stub `.19`/`.20`: a `FORWARD` claims its procedure number the
    instant it is *written*, not at completion, inside a `SEGMENT`'s
    own nested scope exactly as it already does at `PASCALSY`'s own
    outer one -- this project had just never added a *new* forward
    mid-segment before. Every one of `GETCMD`'s `.2`-`.27` is now
    forward-declared once, in one block, in real procedure order,
    right after the segment's own heading (mirroring `PASCALSY`'s own
    convention); completions may appear in any order after that.
    `RUNWORKFILE` itself: `params` exact (`2`), `data` not (the usual
    literal-into-`VAR-STRING` `MSG` cost). Verified compiling clean on
    real Apple 1.3 hardware, whole file.

    **Console output is bare `WRITE`/`WRITELN` with no file argument, and
    the scratch-`STRING` workaround was never needed (finding 201).** The
    paragraph above about `WRITE`'s file argument stays true as far as it
    goes -- a *dereference* really is rejected there, which is why
    `USERPROGRAM` keeps its direct `FWRITELN(SYSTERM^)` -- but the
    conclusion drawn from it was wrong. Apple's own source does not call
    `FWRITESTRING` for console output at all; it writes `WRITE('literal')`
    and `WRITELN` with **no file argument**, and the compiler's sugar for
    the defaulted output file lowers to `LOD 1,3 | LSA | SLDC 0 |
    CXP 0,19`. Error 154 never fires because the sugar builds the argument
    list itself. Proved from this project's own byte-identical
    `FORMATTER.text`/`FORMATTER.CODE` pair, which holds that exact
    construct and those exact bytes, then confirmed on hardware. This also
    retires the `LOD 1,3` note that had stood open for two sessions: it is
    the compiler's own default-output reference, not an identifier this
    project failed to recover. 103 call sites converted, 28 scratch pairs
    and 7 dead declarations removed; `BADTITLE`'s parameter corrected to a
    value `STRING` (its `LLA 4 | SLDL 3 | SAS 80` prologue is the shadow
    copy) and its empty-test to `FTID`. **10 -> 15 procedures
    instruction- and frame-identical, none lost.**

    Two pieces of tooling came out of it and are now the standing
    scoreboard for the rest of this item: `tools/oscmp.py` scores the
    whole compiled codefile against shipped `128K.PASCAL` procedure by
    procedure -- instruction text *and* `params`/`data`, because a right
    body on a wrong frame is a declaration bug -- and names what a change
    gained and lost; `tools/probes/probe_os_exact.py` (in `build_all.py`)
    pins the fifteen by name against the kept acceptance run, with four
    known-differing procedures as a discrimination control.
    `PASCALSYSTEM.text` is also in `mkharddisks.py`'s own `FILES` list now
    as `PASCALSY.TEXT`, so the acceptance disk is built from the working
    tree by the one documented entry point.

    **The four string primitives' parameter lists were reversed, and
    UCSD's own declarations were right all along (finding 202).** Finding
    138 read each real frame correctly and then wrote that frame out as
    the declaration, which is the wrong direction -- a declaration
    reverses into its frame (finding 175). Reversing all four real frames
    gives UCSD's `GLOBALS.TEXT` declarations back character for
    character, and `SPOS` was never the exception it was written up as,
    only the one the error happened not to disturb. Every one of the four
    bodies had the right instructions reading the wrong parameters, and
    every call site pushed in the wrong order to match; both were
    invisible while the comparison looked at frame *sizes* alone, which
    were right throughout. **15 -> 20 exact, none lost.** With it:
    `SINSERT`'s `ONRIGHT := 0` is a real bounds guard, not the dead code
    it had been simplified away as; `RUNWORKFILE` is UCSD's own
    `ASSOCIATE(CONCAT(CODEVID,':',CODETID), ...)` expression rather than
    a locally built title (the binary's `SLDC 0 | STL 2`, its running
    `7`/`8`/`23` maxima and its twelve-word `data` all say so); and
    `READ` has a defaulted file exactly as `WRITE` does, one offset lower
    -- `GFILES[0]` at 2 against `GFILES[1]` at 3.

    **The EXEC-file I/O layer closed on a type nobody would have guessed
    (finding 202d).** Tribby's `what_g` is not an array -- the binary
    reaches globals 384 and 385 with a plain `LOD` in all eleven places
    and never with `LDA`+`IXA` -- and `EXEC_BLK`, the second of the two,
    is a **`BOOLEAN`** that is stepped with `SUCC` and read as a block
    number through `ORD`. The same word is an `AND` operand, an `IF`
    condition, an addend and `FBLOCKIO`'s `RBLOCK`, which no one
    ordinary type covers; `SUCC` and `ORD` are the two conversions that
    emit no instruction at all, so they are invisible in a diff and are
    the only way all four uses reconcile. The direction was settled by a
    *failed* compile: `INTEGER` plus `AND EXEC_BLK` is error 134 on
    Apple's own compiler. **20 -> 24 exact**, `PASCALSY.44`-`.47` in one
    step.

    **`KEYBOARD` is a third predeclared file, at global 4 (finding
    202e).** `WAITSYSVOL` and `SWAPMENU` read the console through a bare
    `LOD 1,4`/`LOD 2,4` that `GFILES[2]^` cannot produce. `GFILES` is
    still genuinely an array, unlike `WHAT_G` -- inside `PASCALSY` it is
    indexed in exactly one procedure with exactly the constants 0 and 1 --
    so global 4 is the compiler's own hardwired third file, one slot past
    `READ`'s INPUT at 2 and `WRITE`'s OUTPUT at 3. `INSERT` and `EOLN` are
    sugar too, and emit `CXP 0,24`/`CXP 0,11` where a hand-written
    `SINSERT`/`FEOLN` call emits `CBP`: that opcode difference is what
    tells sugar from an ordinary call at the p-code level. With two
    local-frame corrections read off *offsets* rather than sizes, **24 ->
    26 exact**.

    **`PASCALSY.53`-`.58`'s numbering came out of the call graph (finding
    202f).** A `CLP` names a procedure nested inside its caller, so `.55`
    is `FBLOCKIO`'s, `.56` is `FGET`'s and `.58` is `STUB48`'s -- which
    is why `GETNEXTCMD`/`CMDDISPATCH` belong on `57`/`58`, not the
    `54`/`55` this file had them on, and why `BLKXFER` had been sitting at
    top level on `53` where Apple has a shared CRT control-character
    writer. Fixing it needed no renumbering machinery, only moving bodies:
    a completion may sit anywhere, since only the `FORWARD` block's order
    fixes numbers (finding 199). The note claiming a shared helper could
    not be factored out without shifting later numbers was answerable all
    along. `PUTCRT` is written for real, `CLEARSCREEN`/`CLEARLINE` with
    it -- and the old inlined versions had the `PREFIXED` test backwards.
    **26 -> 31 exact.**

    **`NEW`'s variant tags, two `REPEAT`s, and the `FIOPRIMS` blocker
    localised (finding 202g).** `INITHEAP`'s six FIB allocations are
    `NEW(p, TRUE, FALSE)`, not plain `NEW(p)`: a plain one takes `FIB`'s
    largest variant, 290 words because of the 512-byte soft buffer, where
    the tagged one stops at `FISOPEN=TRUE, FSOFTBUF=FALSE` and comes to
    Apple's `SLDC 30` field for field. `STUB48` and `CMDDISPATCH` both
    test at the bottom -- `REPEAT ... UNTIL STATE = HALTINIT`, not the
    `WHILE` this file had -- and `CMDDISPATCH`'s `ELSE` is a plain
    `EXIT`. **31 -> 33 exact.** That leaves `PASCALSY.58` identical apart
    from six compiler-emitted instructions: a `LOADSEGMENT(2)` /
    `UNLOADSEGMENT(2)` residency wrapper on `FIOPRIMS`'s own segment. The
    `FIOPRIMS` wiring open since finding 200 now has a measurable handle
    -- whatever makes it a real `USES` will show up there first.

    **The `$R` "resident" option is what emits `LOADSEGMENT` /
    `UNLOADSEGMENT`, and the answer was already in this repository
    (finding 203).** Three procedures of `128K.PASCAL` carry a
    compiler-generated wrapper whose segment number is not derived from
    anything the body calls -- `PASCALSY.58` loads segment 2 while
    calling only segment 1 -- and it is not automatic either. The
    construct is `(*$R <unit-or-segment>*)`, placed right after `BEGIN`,
    and `SYSTEM.COMPILER`'s own byte-identical `BODYPART` had been using
    it in `HOLDRTN` and `HOLDSTMT` for months. The manual documents both
    an identifier and a number form; `INITIALIZE` must use the number,
    since naming `FILEPROC` -- declared later, because segment numbers
    follow declaration order -- is error 273. **33 -> 34 exact**, closing
    the last non-stub procedure in the segment-0 command loop.

    **`CMDSTATE` has eleven members, not UCSD's ten (finding 204), and
    the whole segment-0 command loop is now byte-exact.** `GETNEXTCMD`
    dispatches with `XJP 2..10` and tests membership against the set
    constant `2044` -- bits 2 through 10 -- and neither can come from a
    type ending at ordinal 9. The extra member is appended, which the
    binary's other set constants confirm independently (`224` is bits 5-7,
    `12` is bits 2-3, both exactly right on the existing ordinals). Its
    name is not recoverable; UCSD's own `CONST ASSEMONLY = LINKANDGO`
    and 1.3 putting `A(ssem` on the command line make an assemble state
    the obvious guess, but a guess is not a name. With it, `GETNEXTCMD`
    came out exact -- **34 -> 35** -- and `PASCALSY.48`, `.50`, `.53`,
    `.55`, `.57`, `.58` are all identical: the outer command loop, its two
    nested helpers, the volume wait, the CRT control writer and the
    block-transfer routine.

    **`GETCMD.19` (`ASSOCIATE`) written for real (finding 205), 259
    instructions -- the largest procedure decoded for this file, and
    `GETCMD.2` closed alongside it. 35 -> 37 exact.** The sixth
    parameter is the BOOLEAN that gates the version check, not the
    `INTEGER` this file had guessed; reversal then places all six, and
    `ERROROK` on word `5` -- third of three BOOLEANs in one group -- is
    what fixed the order. Global word `444` turned out to be `RUN_VOL`,
    the `%` volume, **declared in this file all along at the right
    offset with its own comment beside it** while both routines that
    read it wrote `DKVID`; `ASSOCIATE` saves it, sets it to the volume
    of the code file it just opened, and restores it only on the
    failure path, which is exactly what makes `%` mean "wherever the
    code file came from". That one wrong offset encodes a byte shorter,
    and an odd number of bytes flips the parity of every alignment
    `NOP` after it, so a single error read as thirteen differences.

    The four-word set at `0x120` of the segment dictionary is now
    parsed: it is the **intrinsic units a codefile requires**.
    `128K.PASCAL`'s own is `0004`, bit 2, and segment 2 is `FIOPRIMS`,
    the one segment of the OS whose `SEGKIND` is `LINKED_INTRINS`
    (finding 200); `SYSTEM.LIBRARY`'s is zero, since it provides
    intrinsics rather than requiring them. `ASSOCIATE` intersects it
    with the set `.10` builds from the file's own segments and reports
    "Conflict between intrinsic and user segment(s)". `SEGDICT` as
    declared now places every part of the block by an offset the binary
    carries, and the seven parts sum to exactly 256 words.

    Two smaller facts came out of the same run. `GETCMD.1`'s three
    words of `data` are UCSD's `CH`/`BADCMD`/`DONT_CARE`, and
    `DONT_CARE` on word `6` is the `LAO 6` that had been `GETCMD.2`'s
    last divergence -- inside a segment's nested procedure
    `LAO`/`SRO`/`SLDO` address the *segment's* frame, which is the same
    fact that makes `GETCMD := LINKANDGO` compile to `SRO 1`. And the
    fast tier drops an unused `WITH` pointer where Apple's compiler
    keeps it: `WITH SYSCOM^, ...` costs a word that nothing reads, and
    it is the difference between `data` 728 and 726.

    **`SCANTITLE` normalizes the parameter itself (finding 206). 37 ->
    38 exact.** The 82-byte gap that had stood for four sessions was a
    local `T` that should never have existed: `FTITLE` is a value
    `STRING`, the compiler has already made a private copy at word 8,
    and Apple's body strips, upshifts and `DELETE`s *that* in place --
    `LAO 8` is every reference to the working string in all 354
    instructions. A value `STRING` parameter is not only a cost
    (finding 176); it is a scratch buffer the caller already paid for.
    Three smaller things came with it: the character is cached in a
    `CHAR` rather than re-read from the string three times, the upshift
    is `ORD(CH) - ORD('a') + ORD('A')` and not `- 32`, and two integers
    do the work of the three this file declared -- `I` is reused five
    times over and `P` holds only `POS(']')`, which is the only reason
    the two can be told apart. The digit scan is a `REPEAT`, the fourth
    loop in this reconstruction written as a `WHILE` that the binary
    tests at the bottom.

    **The file primitives and what `BASE` addresses (findings 207-209).
    38 -> 44 exact.** `SRO 11` inside `PASCALSY.56` had been recorded as
    an open question rather than guessed at, and it is now settled:
    `BASE` is the activation record of the currently active *lex-0*
    procedure, not the globals. From lex 0, `SRO`/`SLDO`/`LAO` name the
    procedure's own frame; from a lex-1 procedure nested inside one, the
    globals move to `LOD 2,n` and `SRO`/`SLDO` still name the parent's
    frame. Checked so it could have failed: 1123 BASE-relative
    references from lex-0 procedures across the whole file, not one of
    them outside the referencing procedure's own frame, and all eight
    lex-1 procedures that use BASE at all inside their parent's.

    That let `.56` (`EXECGETCH`, the read-side twin of `EXECPUTCH`) be
    written, along with `FGET`'s own frame, which had to be right for
    `.56`'s two offsets to mean anything even though `FGET`'s body still
    waits on `FIOPRIMS`. `PASCALSY.1` was four lines short of Apple's:
    the `REPEAT STUB48; IF EMPTYHEAP <> NIL THEN INITIALIZE UNTIL
    EMPTYHEAP = NIL` that drives the whole system. `PASCALSY.54` turned
    out to be UCSD's own `CHECKDEL` and placed three packed-field
    offsets straight out of finding 93a's reversal rule, with nothing
    left over. `FREADCHAR`, `FWRITECHAR` and `FWRITEBYTES` are Apple's
    restructured versions of UCSD's write path, which moved everything
    out of `FWRITESTRING` and into `FWRITEBYTES`.

    `FWRITESTRING` (`.19`) closed after that, and it took a type rather
    than an expression (finding 214). Its `FWRITEBYTES` argument is the
    string parameter's address plus one byte, which is `S[1]` -- a
    component of a *packed* variable, and so illegal as a `VAR` actual
    (error 103) for every formal but one. `BYTESTREAM`, new in 1.3, is
    the exception: Apple's compiler folds base and index into one
    address with the `ADI` that had been the open instruction. That was
    read out of `src/pascal/1.3/phases/BODYPART.text`, this project's
    own reconstruction of the 1.3 compiler, after six acceptance runs
    had failed to guess it -- `SYSTEM.COMPILER` is a reference for what
    1.3 accepts, not only a deliverable. **45 of 111.**

    `VOLSEARCH` (`.30`), the file-extension routine (`.49`) and
    `FPWINADV` (`FIOPRIMS.2`) followed it the same day (finding 215),
    and all three were *shapes* rather than offsets: a frame four words
    too long because two of Apple's locals do double duty, an `IF`/
    `ELSE` written as a `BEGIN ... END`, and a `GOTO` that jumps out of
    two levels and past the statement after them. **48 of 111.**

    `INITIALI.1` closed next (finding 216) -- 361 instructions and a
    59-word frame, the largest procedure in the file to match. Its
    *frame* named four of the five missing pieces before any code was
    read: a `STRING[40]` at offsets 1-21 that the body never touches
    (the nested procedures use it through `LAO 1`), a `FOR` index at
    22, and a free union at 57 that fabricates a pointer from a
    literal address, since 1.3 has no `@`. **49 of 111.**

    Eight more followed immediately (finding 217), all of them the same
    shape: a `data` count one or two words short is evidence about a
    `WITH` (or a `FOR` loop's limit temp), not about a declaration.
    `PASCALSY.39` closed too -- not by writing a statement but by
    declaring the one word its body never touches, every other reading
    of that word having been excluded. **57 of 111.**

    Nine more in one pass (findings 218-219), from three separate
    causes. `FNXTBYTE` and `FMAXBYTE` were swapped at five soft-buffer
    sites -- a swap invisible in a frame comparison *and* in an
    instruction count, since both readings emit the same five opcodes
    and only the `INC` operand separates them. Four `FILEPROC`
    forwarders passed literals where Apple passes an uninitialised
    local it never assigns; the frame gap and the instruction gap
    there were the same fact seen twice. And `FILEPROC.7` (`FPCLOSE`,
    292 instructions) came out whole once its *jump targets* were read
    rather than its instruction text -- the `FISOPEN` guard jumps to
    the `RNP`, two failure arms are a `GOTO` and not an `ELSE`, and
    `WRITEDIR` is a sibling of the `IF` rather than the tail of its
    `ELSE`. `FIOPRIMS.3` and `FILEPROC.3` simply had their `THEN` and
    `ELSE` exchanged. **66 of 111.**

    Four more followed (finding 220), all in `FILEPROC`, and three of
    them were locked together: `FILEPROC.6` had been frame-exact at
    26/26 for some time while reading its *parent's* frame at three
    wrong offsets, so it could only move when `FILEPROC.5` did, and
    `.5`'s declaration order could only be fixed from `.6`'s operands.
    A nested procedure is a second, independent measurement of its
    parent's `VAR` block. `FILEPROC.1`'s missing word turned out to be
    forced by a type: `FPCLOSE` takes a `CLOSETYPE`, Pascal cannot
    turn an integer back into an enumeration, so the conversion is
    written out as a four-arm `CASE` whose every arm is the identity.
    `PASCALSY.27` (`SPOS`) exits with a `GOTO` to a label at the end
    of its body rather than by setting its index past the limit.
    **70 of 111.**

    **And the shipped compiler will not compile the shipped OS**
    (finding 220). Two unrelated constructs now, in two different
    segments: an `INTEGER` FIB field used directly as a Boolean
    (error 135) and a string constant passed to a `VAR STRING` formal
    (error 154), both confirmed rejected on real hardware, both
    present in `128K.PASCAL`'s own bytes. The economical reading is
    that Apple built the OS with a different, looser compiler than
    the one on the disk -- and it is testable, since every further
    case should also be a relaxation. Three procedures are pinned
    short by it: `FIOPRIMS.4` (45/43) and `FILEPROC.2` (163/161) are
    frame-identical and differ only by the `SLDC 0 | NEQI` the
    stand-in adds, and `FILEPROC.8` needs a scratch `STRING` per
    separator, which is its whole `data` overshoot. The first two are
    in `probe_os_exact`'s `STILL_DIFFERS` list as the control: if
    either ever reports exact, 218b has been answered.

    Then `WRITEDIR` and `FETCHDIR` (finding 221), the file's two
    directory routines, both held open by one misreading. Their
    `data` gaps had been written up as a "missing address-cache"
    class of their own -- the real binary caches `SYSCOM^`,
    `UNITABLE[FUNIT]` and `GDIRP^[...]` into scratch locals where the
    reconstruction recomputed each one fresh, and that was taken as a
    compiler difference nothing in the source could reach. It is
    reachable, and it is `WITH`: six pointers across the two
    routines, one per open `WITH`. The note was right about what the
    binary does and wrong about why it was out of reach. Also from
    the offsets: `WRITEDIR`'s freshness test reads `HASCLOCK`, not
    `NOBREAK` -- bit 0, the *last* name of the seven-boolean group,
    and the only reading that makes sense, since a "written in the
    last 300 ticks" test says nothing on a machine with no clock.
    **72 of 111.**

    Then three in `INITIALIZE` (finding 222), taking that segment to
    10 of its 11. `INITIALI.4`/`.5` are seventeen instructions each,
    identical but for `INC 36` against `INC 47` -- `CRTCTRL.PREFIXED`
    and `CRTINFO.PREFIXED`, both landing exactly where `SYSCOMREC`'s
    packed-field count puts them -- and they add a character to
    `CONFIG_CHAR` when the flag is clear. `LDA 3,312` with `ADJ 16`
    also gives the first independent check of the Parker/Tribby global
    offsets past `FILENAME` against Apple's own bytes: they are right.
    `INITIALI.6`'s 61 missing words are a private 60-word copy of the
    title table -- needed, because `FILENAME[F]` is overwritten the
    moment a tool is found -- plus one `WITH`. **75 of 111.**

    `FILEPROC.4` (`FPOPEN`) then settled finding 220's status. Its
    third parameter is compared `> 1`, `= 2`, `= 4` *and* driven
    straight into `FJP` five times, in the same procedure; error 129
    and error 135 respectively under the shipped compiler, both
    confirmed on hardware. Together with 218b's `FNXTBLK` that is the
    same variable used as integer and Boolean inside one procedure,
    twice, in unrelated segments -- a systematic relaxation of
    BOOLEAN/INTEGER typing in whatever compiler built the OS, not a
    scattering of odd constructs. `FILEPROC.4` cannot be made exact.

    `INITSYSCOM` closed last (finding 223) and with it **every one of
    `INITIALIZE`'s eleven procedures** -- the first whole
    multi-procedure segment of the OS. It reads `*SYSTEM.MISCINFO`
    into a 240-word local `SYSCOMREC` and copies four spans out; the
    reconstruction had read straight into `SYSCOM^` because
    whole-record assignment looked impossible without redeclaring the
    anonymous record types, and with a local of the *real* type it is
    both legal and what Apple wrote. **76 of 111.**

    The first attempt at its sixteen `MERGEA`/`MERGEB` calls got the
    structure exactly right and every character name wrong -- 318
    instructions against 317, only the packed-field operands
    differing. The mistake was deriving the record layout and the
    argument names from each other. Deriving the layout only from our
    own output, where the names are known because we wrote them, and
    reading Apple's operands against *that*, fixed it in one pass and
    produced two independent cross-checks (`PREFIXED[5]` and
    `MERGEA(5, BACKSPACE)` agreeing on backspace's index).

    Six more followed (finding 224), taking it to **82 of 111** and
    `PASCALSY` itself to **56 of 58**: `FBLOCKIO`, `FREADINT`,
    `FWRITEINT`, `FREADSTRING`, `SPACEWAIT`, `GETCHAR`. Five of the
    six are UCSD II.0's own procedures with visible 1.3 edits, and
    what closed them was taking UCSD's `VAR` lines *verbatim* --
    three frames agreed on the first compile with no reordering at
    all. `reference_source/ucsd_ii0/` had been read for structure
    since finding 195; its declarations were the part going unused.

    **Open, in rough order of value.**
    **`FIOPRIMS`'s intrinsic-unit build wiring is now the single
    largest blocked item** (finding 224c). Four procedures sit behind
    it and nothing else: `FGET` (`PASCALSY.7`, 234 instructions,
    decoded since finding 190), `FPUT` (`PASCALSY.8`, 46, decoded in
    full and written out in the source as a comment), `FIOPRIMS.5`
    (275, `FPUT`'s own callee) and `FIOPRIMS.1`, whose only difference
    from ours is `RNP 0` against `RBP 0`. That last one is the
    cheapest confirmation finding 200 could have asked for: one
    opcode, and it says the shape is wrong rather than the body.
    Finding 205c gives the wiring an acceptance test of its own, since
    our codefile's `0x120` must come out `0004` too.
    `GETCMD` had that structural pass (finding 225) and went 6 of 27
    to **27 of 27 -- complete** (finding 226 added `SYSASSOC`, `.9`
    and `.22`; finding 227 `.11` and the whole of `.13`-`.18` in one
    compile; finding 228 the EXEC pair `.25`/`.27`, the command loop
    `.1`, and `STARTCOMPILE` `.20`/`.21`): seven of its procedures
    are two or three levels
    inside the segment rather than one, which `RBP`/`RNP`, the `lex`
    of a global reference, and the call opcode all agree on. `.8`,
    `.17` and `.21` have no frame of their own and read only their
    parent's locals, so nesting them is what makes their operands mean
    anything -- `.17` and `.21` are now waiting on `.16`'s and `.20`'s
    `VAR` blocks specifically, not on decoding.
    Nothing is left in `GETCMD`, and `FILEPROC` closed too (finding
    229): `FPTITLE` exact, `FPOPEN` frame-exact and two instructions
    out. What the whole file still owes is exactly two things --
    `FIOPRIMS`'s intrinsic-unit shape (`PASCALSY.7`/`.8`,
    `FIOPRIMS.5`, `FIOPRIMS.1`) and finding 218b, which is now worth
    three procedures rather than two (`FIOPRIMS.4`, `FILEPROC.2`,
    `FILEPROC.4`) and is *not* a `FIB` declaration question --
    finding 229c rules that out.
    `FILEPROC.4` (`FPOPEN`) at 563/473 and `FILEPROC.8` (`FPTITLE`)
    at 168/203 -- real bodies, close, diffs to read rather than
    routines to decode; `.8` also carries finding 220's error-154
    gap, so it can get closer but probably not exact.

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
    **Done** (finding 289): `tools/mkdiskset.py`, `probe_diskset.py`,
    `analysis/diskset-account.txt`.

13. **`SYSTEM.APPLE`/`128K.APPLE` itself** -- item 11's "disassembly project
    of its own," scoped into steps:
    * Analyze John Brooks' `SYSTEM.APPLE` source and pull out whatever in it
      is not specific to the 128K configuration -- the interpreter core
      this project actually needs, separated from the parts that only
      apply to a different memory size.
    * Convert what's pulled out to Apple's own assembler dialect (Apple
      Assembler syntax, symbolic operands, `.PROC`/`.FUNC` -- the same
      conventions `src/native/` already follows), so it is a source this
      repo can assemble rather than a reference to read past.
    * Build a turnkey pipeline to recompile/reassemble the whole thing in
      AppleWin, the same shape as the `emu*.ps1` scripts already give
      `SYSTEM.COMPILER`/`SYSTEM.ASSMBLER`/`SYSTEM.LINKER`.
    * Once that stands on its own, adjust it to use the Peter Miller
      (`ucsdpsys`) tools where that helps -- the fast tier this project
      already relies on for the p-code side.

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
* **Interactive acceptance-tier driving (the "REDIRECT" thread).** The
  user asked whether AppleWin's Super Serial Card (slot 2, TCP port 1977 --
  confirmed real and working, see below) could replace the current
  screenshot-and-SendKeys loop with a live, read-as-text session against
  the running system -- hitting space to page through more compiler
  errors in one shot instead of one screenshot per keystroke. Checked
  directly, twice: `REDIRECT` is not a real Apple Pascal 1.3 procedure
  (compiled a test program against it -- error 104, undeclared -- and it
  is absent from the full UCSD II.0 source tree in `evidence/`, all six
  files, zero hits), and `CONSOLE:` is hardwired to the Apple's own
  screen/keyboard firmware (manual, confirmed), so nothing in Apple
  Pascal 1.3 itself can redirect the system command level's own I/O to
  `REMIN:`/`REMOUT:` (slot 2, units 7/8 -- that part of the claim was
  real). The user's own next idea, not yet tried: **patch the compiler
  and/or the OS itself** so error reporting (or the console generally)
  pages interactively rather than stopping the whole compile/list -- a
  real code change to `SYSTEM.COMPILER`/`SYSTEM.PASCAL`, not a
  configuration trick, and "system wide" per the user (affecting more
  than just error listings). Not started; the user asked to hang tight
  on it. **Tried in the meantime, and it works**: Apple Pascal's own
  built-in exec files (finding 124) -- `M(ake` records a keystroke
  sequence to a `.TEXT` file, `X EXEC/<file>` replays the whole thing
  later without per-keystroke waiting. Proved end to end against a real
  compile (`SET40T.TEXT`, exact frame-size match to finding 112) and
  fixed a real bug in `tools/emukeys.ps1` along the way -- it was
  passing bare `% + ~ ( ) { }` straight to .NET's `SendKeys`, which
  treats them as modifier/grouping syntax, so an exec file's own `%`
  terminator was silently never reaching the emulator at all. **Now
  wired in as the default** for all three `emu*.ps1` scripts' hard-disk
  paths (finding 125, `tools/execfile.py`), verified against real
  compiles/assembles/links including a full `FORMATTR`/`FMTNATIV` link
  reproducing finding 104's own byte-identical result -- the `-Floppy`
  paths are untouched, still live SendKeys. AppleWin's SSC/TCP mode
  itself is confirmed live and usable
  (`HKCU\Software\AppleWin\CurrentVersion\Configuration\Slot 2\Serial
  Port Name = TCP`, lazily binds port 1977 on first UART access) for
  anything that talks to `REMIN:`/`REMOUT:` from inside a running
  program, if that ends up being part of the eventual approach.
* **The low-level `CHANGEIO`-style redirect (finding 131): mechanism
  proven, round trip still blocked.** A pasted, LLM-generated "Unit
  Vector Table at zero-page $1A" writeup turned out fabricated too --
  contradicts the language reference's own statement that zero-page
  `0..35` decimal is scratch space, and matches nothing in the UCSD OS
  source. The user's own `CHANGEIO` program (page-zero 230 decimal, a
  write-pointer table, `CONSOLE:`<->`PRINTER:`) is real and independently
  confirmed by Neil Parker's document (`RTPTR`=228/`WTPTR`=230, 8 entries
  of 2 bytes, one per unit `#1`..`#8`) *and* by a live PEEK probe against
  the real 1.3 system -- table contents, all 8 units, matched exactly,
  including unit 6's read slot and unit 7's write slot both reading back
  0 live, the two scratch slots a symmetric read+write redirect needs.
  `REDIRIO.TEXT`, the read+write extension of `CHANGEIO`, compiled clean
  and **works**: after running it, the physical keyboard stopped
  affecting the screen at all (confirmed via `tools/watchscreen.py`'s
  idle detection) -- Command-level I/O is genuinely off CONSOLE: and
  pointed at REMIN:/REMOUT:. Fully recoverable (RAM-only, a reboot
  reverts it).
  **No longer blocked (finding 210).** The byte transfer over AppleWin's
  SSC+TCP socket works, both directions, and the old diagnosis was wrong:
  the driver *was* reaching the hardware. `CheckComm()` binding port 1977
  does not make the card report carrier -- only an accepted connection
  does -- so with nothing connected, DSR and DCD read inactive and Apple's
  `REMOUT:` driver waits for it forever. Since AppleWin creates the socket
  only on the guest's first register access, the host client has to
  poll-connect rather than connect once; that is the entire fix. The
  status register reads `$70` unconnected and `$10` connected, measured
  both ways.
  Proven end to end through Apple's own code: the Filer's `L(dir` with
  `SYSHD:,REMOUT:` delivered a whole directory listing as clean text, and
  `tools/remote/REMTEST.text` (`UNITWRITE` to unit 8, blocking `UNITREAD`
  from unit 7, echo back) round-tripped `PING4321` unchanged. The pieces
  and the four things that make or break it are in `tools/remote/`.
  **And the console redirect itself now works (finding 211).** `REDIRIO`
  rewritten from finding 131's page-zero facts and run: the Command level,
  the Filer, its prompts, its echo and a full directory listing all came
  out of the socket, and the host's keystrokes all went in, with the
  screen blank and the physical keyboard dead. It is a toggle, and the
  second run was sent over the socket through the redirect it was undoing.
  Units 1 *and* 2 have to be swapped -- `CONSOLE:` and `SYSTERM:` share
  the same routines but are separate entries, and the system reads through
  `SYSTERM:` when it wants no echo, so changing only unit 1 leaves a live
  keyboard behind and makes "the keyboard is dead" unfalsifiable, which is
  the hole in finding 131's own test.
  **And it is wired in (finding 212).** `tools/emuremote.py` compiles with
  no keystrokes at all: `REDIRIO.CODE` is installed as `SYSTEM.STARTUP` so
  the boot arms the channel, the `C(ompile` sequence goes over the socket,
  and the driver waits for the compiler's own last line instead of a fixed
  sleep. `PASCALSY` takes **57s against the SendKeys path's 340s** of
  padding, comes back as text, and exits non-zero on a compile error with
  the line and error number extracted. Two builds from identical source,
  one each way, differ in 555 bytes and **none of them is inside a
  segment** -- every segment byte-identical, `oscmp` 44 of 111 both ways
  (110 as of finding 232, and 111 across two runs, finding 233).
  The slack differs because the SendKeys path leaves its own exec-file text
  in the compiler's memory, which is a good illustration of why a
  whole-file `cmp` is the wrong acceptance test for a codefile.
  `emucompile.ps1` is untouched and is both the fallback and the way
  `REDIRIO` itself gets compiled. **The assembler and linker followed
  (finding 213)**: `emuremote.py compile|assemble|link`, proved end to
  end by compiling `FORMATTR`, assembling `FMTNATIV` and linking them
  entirely over the socket to a codefile byte-identical to Apple's
  shipped `FORMATTER.CODE`. `emulink.ps1`'s own "that race is not fully
  solved" is solved by not racing -- the Linker's prompt sequence
  depends on the data, so answers wait for the prompt they answer -- and
  a link is verified by segment dictionary (`HOSTSEG` means it did not
  work) rather than by the output file existing, which proves nothing.

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
