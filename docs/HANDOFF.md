# Handoff: Apple Pascal 1.3 reconstruction

For a reviewer picking this up cold. Read it in full before changing
anything. Its companions:
- `CLAUDE.md`: hard rules, tool recipes, emulator pitfalls;
- `docs/PLAN.md`: current state at the top;
- `docs/FINDINGS.md`: the evidence ledger, findings 1-294;
- `docs/DISKSET.md`: per-file scoreboard;
- `docs/PascalRecon-1.3-Reconstruction-Report.pdf`: every file, its bytes,
  its sources and its exceptions.

As of 2026-09-14 the local tree is ahead of `origin/main`
(github.com/dhlav/apple-pascal-compiler-reconstruction) by the commits
listed under **State of the tree**.

---

## 1. What the project is

**Goal.** For every file on the Apple II Pascal 1.3 disk set (the three
disks APPLE1-3, 128K system), write source such that **Apple's own tools**
turn it back into the **shipped bytes**:
- `SYSTEM.COMPILER`, `SYSTEM.ASSMBLER` and `SYSTEM.LINKER`;
- `LIBRARY.CODE` and SETUP;
- run under the AppleWin emulator.

Readable pseudocode is not the target. Byte-identical output is.

**Out of scope, by decision:**
- everything Apple Pascal 1.1;
- the 64K `SYSTEM.APPLE`/`SYSTEM.PASCAL`.

These are archived under `evidence/archive/` and `archive/`. The target
is `128K.APPLE` and `128K.PASCAL`.

**Where it stands.** `tools/mkdiskset.py` rebuilds all three disks from
this repository. **359,323 of 430,080 bytes are identical to Apple's
images**; in scope, 351,873 of 374,784. Every remaining difference has a
named cause, and `tools/probes/probe_diskset.py` requires each region's
difference count to balance against a direct image compare.

| status | files |
|---|---|
| identical, whole file | `SYSTEM.COMPILER`, `SYSTEM.ASSMBLER`*, `SYSTEM.LINKER`, `SYSTEM.EDITOR`, `SYSTEM.FILER`, `LIBRARY.CODE`, `128K.APPLE`, `SYSTEM.CHARSET`, `6502.OPCODES`, the 10 text files |
| all but a named remainder | `128K.PASCAL` (571, finishing tool's slack), `SETUP.CODE` (3,943, version word and stale pads), `LINEFEED.CODE` (467), `FORMATTER.CODE` (394, Linker slack), `LIBMAP.CODE` (311, Linker slack), `6502.ERRORS` (287), four `.MISCINFO` (556), `BINDER`/`SET40COLS` (16 each, version bits), `FORMATTER.DATA` (1) |
| accepted exception | `SYSTEM.LIBRARY`: every code byte and all interface text by Apple's tools, but the file cannot match whole (see 6.1) |
| out of scope | 64K `SYSTEM.APPLE`, `SYSTEM.PASCAL` |

\* `SYSTEM.ASSMBLER`'s `PASCALIO` segment is copied from Apple's file.
Nothing on the 1.3 disks can rebuild it (finding 235b).

---

## 2. Rules that are not negotiable

These come from `CLAUDE.md`, and the whole method depends on them.

1. **Nothing in `evidence/` is ever modified.** It is Apple's shipped
   media. AppleWin writes date stamps to any image it mounts read-write,
   so never mount an evidence image directly. Run `git status --short
   evidence/` after every emulator session.
2. **`build/`, `analysis/` and `reference_source/` are generated.** Change
   the tool and rerun `python tools/build_all.py`, which must exit 0 before
   any commit. It is about 62 steps, including 52 probes.
3. **Label every claim**: VERIFIED BINARY FACT, VERIFIED SOURCE FACT,
   STRONG INFERENCE or SPECULATION.
4. **A total that does not balance is evidence**, not slack.
5. **Prefer a check the binary can fail**, and prove it can fail for the
   property in question. Several probes carry a deliberate mutation or a
   negative control; keep that pattern.
6. **Only Apple's tools can accept a source.** The fast tier (WSL
   `ucsdpsys_compile`, `tools/asm6502.py`) can only falsify, never accept.
   The host compiler is also more permissive, and it short-circuits
   AND/OR where Apple's compiler does not.
7. **Names need evidence.** A placeholder (`LK<n>`, `G<n>`, `L<n>`, `M<n>`)
   is renamed only when an ancestor source matches the body statement for
   statement in the same slot. Otherwise it stays a placeholder.
   Descriptive invented names are not used.

---

## 3. Environment

- **OS and runtime:** Windows 11. Python 3.14. Bash via Git Bash, and
  PowerShell.
- **Emulator:** AppleWin at `C:\AppleWin\AppleWin.exe`. Model `apple2ee`
  (enhanced //e). HDC in slot 5, slot 6 empty. SSC in slot 2 in TCP mode,
  port 1977.
- **Port 1977:** Windows' dynamic range can reserve 1977 away from
  AppleWin (finding 236). An administered reservation must exist; check
  with `netsh int ipv4 show excludedportrange protocol=tcp`.
- **CiderPress II** at `C:\CiderPress2\cp2.exe`. `tools/a2pascal` only
  reads and writes 140K floppy images; hard-disk images go through cp2.
- **Fast tier:** `thirdparty/ucsd-psystem-xc` under WSL (Ubuntu).
- **PDF tooling:** `reportlab` and `pymupdf`.

---

## 4. How the acceptance tier works

Apple's tools run inside AppleWin, driven with no keystrokes:
- `tools/remote/REDIRIO.text` is installed as `SYSTEM.STARTUP`. It
  redirects the console to the serial card.
- `tools/emuremote.py` talks to it over TCP 1977 and waits for each tool's
  own completion text.

Two 2MB Pascal hard-disk volumes:
- `build/disks/HD1.hdv` = `SYSHD`: boots, and holds the system tools and
  `REDIRIO.CODE`. Built by `tools/mkharddisks.py`. **Rebuilding it forces
  a manual REDIRIO bootstrap compile, so do not rebuild it casually.**
- `build/disks/HD2.hdv` = `WORKHD`: per-run files, built by
  `tools/mkworkhd.py`. **Put new work here.**

```
python tools/stagefile.py --vol WORKHD src/.../X.text X.TEXT   # applies a .layout if one is beside the source
python tools/emuremote.py --quiet --vol WORKHD --timeout 600 compile X
python tools/emuremote.py --quiet --vol WORKHD --timeout 600 assemble N
python tools/emuremote.py --quiet --vol WORKHD --timeout 600 link --host X --lib N --out L
python tools/emuremote.py --quiet --vol WORKHD --timeout 600 librarian --input L --slots 1:1 --out OUT --notice "COPYRIGHT 1979,1980,1983-1985 APPLE COMPUTER, INC. ALL RIGHTS RESERVED"
python tools/emuremote.py --quiet --vol WORKHD --timeout 600 run MAKEOS        # X(ecute a program
cd <dest dir> && cp2 extract --raw --strip-paths build/disks/HD2.hdv X.CODE     # delete the destination first
```

**Results are kept verbatim** in `acceptance/<date>-<name>/`: codefiles,
consoles and the source that was compiled. There are 130 run directories.
The probes compare them with Apple's disks, and most also compare the kept
source with `src/`. So **any source edit, a rename included, needs a fresh
acceptance run**, or the probe fails.

**The release step.** System programs come out of the compiler and are
then copied into a fresh codefile by Apple's `LIBRARY.CODE` with the
copyright notice. That is why slot 0 is blank in the shipped files
(finding 267).

---

## 5. Pitfalls that actually happened

- **cp2 `add` and `extract` never overwrite.** Delete the destination
  first, or you score the previous run. Two runs agreeing too well is the
  signature.
- **A failed compile or link still writes an output file.** Check the
  console and the segment dictionary, not the file's existence. A segment
  still marked `HOSTSEG` means the link did not happen.
- **Codefiles created on a hard-disk volume need `[*]`**
  (`NAME.CODE[*]`). A Pascal volume holds **77 files** at any size.
- **Names:**
  - a volume filename is at most 15 characters, and Pascal identifiers
    are significant to 8;
  - Apple's compiler reports **"String overflow" for a 15-character
    codefile name** (`TURTLEUNIT.CODE`), while `SET40COLS.CODE` is
    accepted. Keep compiled stems to 9 characters;
  - stage `LIBRARY.text` as `LIBR13`, or it overwrites the Librarian.
- **`stagefile.py` refuses a unit source whose `.layout` `expect` lines
  moved.** In a batch the refusal scrolls past, and the **old** staged file
  compiles silently. This happened in finding 290; check every stage line.
- **Emulator:**
  - `emuremote`'s shutdown runs `taskkill /IM AppleWin.exe`, which closes
    every AppleWin, a user's included;
  - AppleWin does not flush an image until it exits.
- **AppleWin's toolbar drive buttons are floppy drives.** An 8MB `.hdv` put
  there reports "Unable to open the image"; hard disks go on the slot-5
  controller.
- **Session scratch directories can vanish.** Keep anything worth having
  in the repo.
- **Reading the binary:**
  - a backward branch is a loop condition first;
  - the compiler does not short-circuit;
  - a `CASE` jump table comes after the arms;
  - allocation order: declaration groups ascend, identifiers within one
    group descend;
  - a record's field list reverses within a clause.

  Read the verified compiler source (`src/pascal/1.3/`) to settle "can
  the compiler do X" instead of running experiments.

---

## 6. Open items and where the evidence stops

### 6.1 `SYSTEM.LIBRARY`: accepted exception, do not reopen without new evidence

All six code segments and TURTLEGR's data segment are byte-identical, and
each unit's interface text matches through `IMPLEMENTATION`. The file
cannot match whole. Apple's text blocks came from a compiler **other than**
the shipped one:
- the block counts differ: LONGINTI 2 and TURTLEGR 3, against the shipped
  compiler's 1 and 2;
- each 10-byte trailer holds `N` or `X` at offset 6;
- the extra blocks hold buffer copies.

Unit by unit 16,417 of 19,456 bytes agree. In place on the disk 16,234
differ, because the file is two blocks short. Findings 285-287 and 290.

The buffer copies preserve fragments of Apple's own source (290):
- `PROCEDURE DECOPS; EXTERNAL;`;
- `{$endc}` and `{$SETC SHORT := FALSE}` in TURTLEGRAPHICS;
- `/P/NEWC/C.CODE`.

**Worth a reviewer's time:** the exact rule in `UNITPART`
(`src/pascal/1.3/phases/UNITPART.text`, from `IC := SYMCURSOR - TEXTSTRT +
10`). TURTLEGR's block shape matches the `IC > 1024` branch (CR and NUL at
the text's end, trailer at 1024). The shipped compiler can only take that
branch when `SYMCURSOR - TEXTSTRT > 1014`, which an 826-byte interface
cannot reach. If a different condition explains all three units at once
(including why TRANSCEN and APPLESTU carry `N` without `L`), that is new
evidence.

### 6.2 Remainders believed unclosable

These are all leftover memory from Apple's sessions or version stamps:
Linker slack, SETUP's pads, `6502.ERRORS`' first record fill, the
`.MISCINFO` memory, `128K.PASCAL`'s finishing-tool slack. Each finding
says why. Challenge any of them with a mechanism, not a guess.

### 6.3 Placeholder names (the active work)

Done, and verified byte-identical on the acceptance tier:

| finding | file | what was named |
|---|---|---|
| 291 | Linker | byte-flip and small-memory names |
| 292 | Librarian | byte-flip names |
| 293 | LibMap | byte-flip names |
| 294 | `DECOPS` | eleven operation names |

The names came from UCSD's II.0 sources in
**github.com/dhlav/ucsd-psystem-os**: `linker/`, `librarian/`, `libmap/`,
`long_integer/` (fetch with `gh api`). That tree is Peter Miller's
packaging. It is faithful to UCSD's text except occasional renames, such as
`NORMAL` → `UK_NORMAL` in `globals.text`, so names taken from it are
STRONG INFERENCE.

Remaining, roughly in order of available evidence:
1. **`src/native/TURTLEGR.TEXT`**: about 121 `L<nnnn>` labels. The mirror
   has `turtle_graphics/`.
2. **The mirror's `pascalio/` and `transcendental/`** against those units.
3. **Placeholders with no ancestor found yet:**
   - Linker: `G29`, `G91`, `LK2`, `LK3`, `LK17`, `LK51`;
   - Librarian: `G131`, `LB6`, `LB15`, `M2`, `M3`;
   - LibMap: `L85`;
   - smaller sets in `FILER.text` (~12), `EDITOR.text` (~24) and
     `PASCALSYSTEM.text` (~14).
4. **`SYSTEM.ASSMBLER`**: about 204 placeholders. The ancestor is UCSD's
   I.5 assembler (`reference_source/ucsd_15`); no II.0 assembler has been
   found.
5. **`128K.APPLE`'s interpreter**: about 800 `L<nnnn>` labels in
   `src/native/interp/`. These files are generated by `tools/absdis.py` from
   `128K.hints`, so **edit the hints, not the .TEXT**. The candidate name
   source is John Brooks' Apple Pascal 1.4 interpreter (external; see
   findings 17-18).

The slack of shipped codefiles sometimes holds compiler symbol nodes or
source text (270c, 290). Look there before anywhere else.

### 6.4 AppleWin images (uncommitted until this handoff's commit)

`tools/mkimages.py` builds `build/images/SYSHD.hdv` and `SRCHD.hdv`, both
8MB.
- **SYSHD** is Apple's shipped files, byte for byte, with the 128K pair
  also copied to `SYSTEM.APPLE`/`SYSTEM.PASCAL`. 35 files. **Verified**:
  it boots turnkey to "Welcome SYSHD, to Apple II Pascal 1.3 ... Pascal
  system size is 128K".
- **SRCHD** is the Pascal and 6502 source, the data files, the SETUP
  recipes and a README. 73 of 77 files. **Verified**: the Filer lists all
  files, and `SET40COLS.TEXT` compiled clean from it (an earlier naming of
  the same build).

**Not yet verified:**
- **The unit rename:** after the units were renamed `UTRANS` to `UAPPLE`,
  `UTURTLE.TEXT` has not been compiled from SRCHD and compared with
  `acceptance/2026-09-14-library-decops/UTURTLE.CODE`. The test script was
  lost with a session scratch directory; rewrite it:
  1. copy both images;
  2. add `REDIRIO.CODE` from HD1 as `SYSTEM.STARTUP` on the copy;
  3. launch AppleWin with the copies;
  4. drive `C(ompile` over the socket;
  5. extract and compare the code segments.
- **`BODY13.TEXT` on SRCHD** is the *commented* splice. Apple's compiler
  was fed the comment-stripped variant (`procbuild.uncomment`) for space.
  Comments cannot change code bytes, but slack could differ, and that has
  not been tried.

---

## 7. What a review should look at hardest

- **Probes that could pass without discriminating.** Mutate a byte in a
  kept acceptance file and confirm the right probe fails for the right
  reason. `probe_diskset.py`'s `EXPECTED` table and the carry control are
  the backbone.
- **STRONG INFERENCE claims** in findings 283-294, especially:
  - 286c and 290 (the other compiler, the buffer-copy reading);
  - 284 (what Apple's finishing tool did);
  - 291-294 (II.0 provenance through the mirror).
- **`src/text/*.layout` header fields** (288): named from `SYSTEM.EDITOR`'s
  `HEADER` record. HAZELGOTO's page zero does not fit that record and is
  recorded as raw bytes.
- **The report** (`tools/mkreport.py`): byte counts are parsed from
  `analysis/diskset-account.txt`, but the per-file notes are hand-written.
  Check them against FINDINGS.

---

## 8. State of the tree

Pushed through `b292a2e`. Local and not yet pushed, oldest first:

```
d1485b9  SYSTEM.LINKER: II.0 names for the byte-flip and small-memory placeholders
3b04add  LIBRARY.CODE: II.0 names for the Librarian's byte-flip placeholders
639b4a7  LIBMAP.CODE: II.0 names for the byte-flip placeholders
c1ee3d0  DECOPS: UCSD's names for the eleven long-integer operations
d032f15  docs: the per-file reconstruction report as a PDF
3d02407  Report: the source files behind every destination file
(this commit) tools/mkimages.py and this handoff
```

`python tools/build_all.py` exits 0 with this commit. `evidence/` is clean.

**Conventions:**
- commit messages explain *why* and record what was wrong;
- working copies are CRLF and the repo stores LF, so git's LF-to-CRLF
  warnings are expected;
- `*.pdf` is marked binary.
