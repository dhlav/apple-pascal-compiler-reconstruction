# PascalRecon

Reconstruct source for every file on the **Apple Pascal 1.3 disk set**, such
that Apple's own tools turn that source back into the shipped bytes.
Readable pseudocode is not the target — byte-identical output is.

Target is **1.3 on the 128K system only** (`128K.APPLE` + `128K.PASCAL`).
The 64K `SYSTEM.APPLE`/`SYSTEM.PASCAL` and everything 1.1 are **archived**:
the 1.1 disk images in `evidence/archive/1.1/`, the 1.1 compiler source and
the 1.1-only tools, probes and generated analysis in `archive/`. Nothing in
`build_all.py` reads them. The 64K pair cannot leave the 1.3 `APPLE1` image,
so the tools that sweep that disk skip them by name.

Reconstructed so far: `SYSTEM.COMPILER` (the whole file, finding 267e),
`SYSTEM.LINKER` (the whole file, finding 268), `SYSTEM.ASSMBLER` (whole
file with `PASCALIO` borrowed, 267f), `LIBRARY.CODE` (the whole file,
finding 269), `LIBMAP.CODE` (the whole segment, 270), `SYSTEM.FILER`
(the whole file, 271), `SYSTEM.EDITOR` (the whole file, 272),
`SETUP.CODE` (every procedure; the file predates the version word, 273),
`BINDER.CODE` and `SET40COLS.CODE` (every byte but the version field,
274),
`FORMATTER.DATA` (all but one uncleared assembler byte, 275),
`6502.OPCODES` (the whole file) and `6502.ERRORS` (all but its record
window's first fill, 276), the four `.MISCINFO` profiles (every setting,
by Apple's SETUP from recipes; the rest is memory, 277), `SYSTEM.CHARSET`
(the whole file, 278), `128K.APPLE` (the whole file, three traced
assemblies, 279),
`SYSTEM.LIBRARY`,
`LINEFEED.CODE`,
`FORMATTER.CODE`. Plan in
`docs/PLAN.md`, evidence ledger in `docs/FINDINGS.md`, per-file
scoreboard in `docs/DISKSET.md`.

## Memory

Save what you learn to memory. Update your agent memory as you discover
codepaths, patterns, library locations, and key architectural decisions.
This builds up institutional knowledge across conversations. Write concise
notes about what you found and where.

## Hard rules

1. **Nothing in `evidence/` is ever modified.** It is Apple's shipped media.
   Archived images moved to `evidence/archive/` keep their bytes exactly and
   stay read-only; a move is not a modification, an edit is.
2. **`build/`, `analysis/`, `reference_source/` are generated.** Never
   hand-edit them — change the tool and rerun `python tools/build_all.py`.
   That script is the single entry point and must exit 0 before any commit.
3. **Label every claim**: VERIFIED BINARY FACT / VERIFIED SOURCE FACT /
   STRONG INFERENCE / SPECULATION.
4. **A total that does not balance is evidence**, not slack. Require sums to
   come out exactly or say why they cannot.
5. **Prefer a check the binary can fail** — and check it can fail *for the
   property you care about*. A passing check that cannot discriminate is
   worth nothing.

## Layout

```
evidence/disks/      the three 1.3 .dsk images + ii0src.sdk, read-only
evidence/archive/    archived media (1.1), bytes unchanged, read-only
evidence/reference/  manuals, and UCSD's I.5 sources (names only)
src/native/          6502 assembly (Apple Assembler syntax)
src/pascal/1.3/      the compiler, PASCALCO.text + phases/
src/pascal/units/    SYSTEM.LIBRARY units
src/pascal/programs/ standalone utilities
tools/               generators; a2pascal/ is the library
tools/probes/        checks, not artifacts — wired into build_all.py
acceptance/          what Apple's own tools produced, kept verbatim
docs/                PLAN, FINDINGS, DISKSET
archive/             1.1 source, tools, probes, analysis -- not run
```

`tools/a2pascal/`: `disk.py` `diskwrite.py` (Pascal volumes), `codefile.py`
(segments, procedures, relocation), `pcode.py` (decoder), `m6502.py`,
`lift.py` + `structure.py` (p-code → pseudo-Pascal), `srcfmt.py`,
`globals.py`, `names.py`.

Probes print a trailing `<name>-ok` line and return non-zero on failure.
Adding one means adding it to `STEPS` in `tools/build_all.py`.

## Two validation tiers

**Fast tier** — `tools/asm6502.py` and `ucsdpsys_compile` (WSL). These are
reimplementations: *they can only falsify, never accept.* The host compiler
is also more permissive than Apple's (it accepts a trailing `;` in a field
list that Apple rejects with error 19).

**Acceptance tier** — Apple's own tools under AppleWin. This is the only
authority. Interactive by nature, so it cannot be a probe; instead its
output is kept in `acceptance/` and `probe_acceptance.py` re-checks it on
every build.

```
python tools/mkharddisks.py                     # ALWAYS first — stale disks lie
powershell -File tools/emucompile.ps1 -Name REDIRIO   # bootstrap, once per rebuild
python tools/emuremote.py compile  X
python tools/emuremote.py assemble X
python tools/emuremote.py link --host X --lib Y --out Z
python tools/emuremote.py observe "L" --seconds 40    # capture a tool's prompts
python tools/emuremote.py librarian --input X --out Y --slots 1-15 --notice "..."
python tools/emuremote.py run X                       # X(ecute a program
python tools/emuremote.py setup --recipe R            # SETUP -> NEW.MISCINFO
python tools/mkworkhd.py                              # WORKHD, drive 2, once
python tools/emuremote.py --vol WORKHD compile X      # a run's files on WORKHD
```

**`emuremote.py` is the path to prefer for all three tools** (findings
210–213). The system's console is redirected to a TCP socket, so it needs no
foreground window, types nothing, waits for each tool's own completion text
instead of a fixed sleep (`PASCALSY`: 57s against 340s), returns output as
**text** — error and line numbers read, not eyeballed off a PNG — and exits
non-zero on failure. It produces byte-identical segments to the SendKeys
path; only the inter-segment slack differs, which is why a whole-file `cmp`
is the wrong test (finding 212a).

`emulink.ps1`'s own module note ends "that race is not fully solved" — it
is, here, by not racing: the Linker's prompt sequence *depends on the data*
(a host with no unresolved `EXTERNAL` skips the library list entirely), so
answers must wait for the prompt they answer. A link is verified by parsing
the output's segment dictionary: **a segment still marked `HOSTSEG` means
the link did not do its job**, and a failed link writes an output file
anyway, so its existence proves nothing (finding 91).

It arms the channel by installing `REDIRIO.CODE` as `SYSTEM.STARTUP` and
removes it in a `finally`. **A SYSHD left armed with nobody listening looks
exactly like a disk that will not boot** — blank screen, dead keyboard, no
error — so if a volume ever behaves that way, check for a stray
`SYSTEM.STARTUP` before suspecting the image. The `emu*.ps1` scripts still
work and are the fallback; `emucompile.ps1` is also what compiles `REDIRIO`
itself, which has to exist on the volume before any of this runs.

One 2MB Pascal hard-disk volume on a slot-5 HDC (`SYSHD` — boots, carries
every system tool, and carries ours too) is the **default** for all four
`emu*`/`runemu.py` scripts — `mkharddisks.py` builds it, and `cp2.exe`
(CiderPress II, `C:\CiderPress2\cp2.exe`) is required since a2pascal's
disk/diskwrite only read/write 5.25" floppy geometry. Name files by Pascal
volume name (`SYSHD:`), not by which `.hdv` holds them.

**Every codefile created on `SYSHD:` needs a `[*]` size specifier** —
`SYSHD:NAME.CODE[*]`, not `SYSHD:NAME.CODE`. A single UCSD volume claims
*all* currently-free contiguous space for a new file and only shrinks it
back on a clean close; `SYSTEM.ASSMBLER`'s own `%LINKER.INFO` scratch file
and an output codefile both being created on the one merged volume raced
for that space, and the codefile got `I/O error: no room on volume` even
with thousands of blocks free. This isn't a bug in this repo's tooling —
it's the exact situation, and the exact fix, the manual documents for a
one-drive system (ch. 3 "File Size Specification", ch. 5 "Allocating File
Space"): `[*]` reserves the second-largest contiguous area (or half the
largest, whichever is more) instead of grabbing the whole thing. All three
`emu*.ps1` scripts already append it. **A Pascal volume also holds at most
77 files regardless of size** — `mkharddisks.py` checks this after every
build and fails loudly rather than let it be a surprise; give any new
volume a distinct name too, in case a second one is ever online at once —
two disks both named `NEWDISK` (cp2's default) left the Filer unable to
tell them apart.

**Per-run work goes on `WORKHD`, drive 2 of the same HDC** (`HD2.hdv`,
`python tools/mkworkhd.py`, `--reset` to empty it). SYSHD hit 77 files
twice in one session. `runemu.py` mounts HD2 on `-s5h2` whenever it
exists; `stagefile.py --vol WORKHD` and `emuremote.py --vol WORKHD` put a
run's sources and outputs there. System tools (the Librarian and SETUP
included) and REDIRIO stay on SYSHD. A program's `*NAME` still means the
boot volume, so write `WORKHD:NAME` in a program that should write there.
Keep new per-run files off SYSHD.

**The old four-floppy layout is still there behind `-Floppy`** (`runemu.py
--floppy`), unchanged, and does not need `[*]` — system tools and output
live on separate volumes there, so nothing races for space:

```
python tools/mkworkdisk.py                      # ALWAYS first — stale disks lie
powershell -File tools/emucompile.ps1  -Name X -Floppy -Work2 -Compile 40
powershell -File tools/emuassemble.ps1 -Name X -Floppy
powershell -File tools/emulink.ps1 -HostFile X -Lib Y -Out Z -Floppy
```

Then read `build/disks/WORK2.dsk` (or `HD1.hdv` with `cp2.exe`, since
a2pascal can't) and diff.

### Emulator pitfalls (all hit for real)

- **Windows reserves port 1977 out from under AppleWin.** The
  remote console dies silently: REDIRIO boots and prints
  `console -> REMIN:/REMOUT: now`, then nothing, and the client
  only ever reaches `SYN_SENT` because AppleWin's bind failed and
  it does not say so. 1977 is inside the TCP dynamic range
  (`netsh int ipv4 show dynamicport tcp` -- 1025 up), so WinNAT and
  Hyper-V take blocks out of it. Check with `netsh int ipv4 show
  excludedportrange protocol=tcp`: an administered reservation for
  1977 must be there (finding 236). Note also that a **closed**
  loopback port on this machine times out rather than refusing, so
  a connect timeout is not evidence of anything.
- **AppleWin does not flush a written image until eject or exit.** The
  scripts close it before you read the disk. Do not read `WORK2.dsk` while
  it is running.
- **SendKeys goes to whatever holds focus.** `emukeys.ps1` refuses to type
  unless AppleWin is foreground, and that guard is correct — do not defeat
  it.
- **60ms between characters.** Batch the whole command in one SendKeys call
  (Pascal has type-ahead), but slower per-key or characters are dropped.
- **The assembler needs `P(refix` set to `APPLE2:` first.** It opens
  `%6502.ERRORS` on its own volume but `6502.OPCODES` with *no* volume, so
  that one resolves against the prefix volume, which after boot is the boot
  disk — and `BOOT128` does not carry it.
- **Run on 128K.** The 64K system cannot compile Apple's own `HILBERT.TEXT`
  (runtime stack overflow). `mkbootdisk.py` builds `BOOT128.dsk`.
- **Check the version banner** if a compile behaves oddly: a compiler from
  another release gives `SYSTEM.COMPILER is not version 1.3` and drops you
  in the Editor.
- AppleWin registry settings are **version-specific in value and type**
  (`Emulation Speed` is REG_SZ). See finding 57d.
- **AppleWin opens `-d1`/`-d2` read-write and will write to evidence.** A
  boot alone updates a volume's date stamp; no error, no prompt. `git
  status` after every session, and `runemu.py` now sets the read-only
  attribute on every evidence disk before each launch (finding 106) — but
  that is a second check, not a reason to skip the first.
- **A Disk II volume's free space is a shared, shrinking budget.** Adding a
  file to `mkworkdisk.py`'s `FILES` list eats into what `procbuild.py
  --emu`'s splice needs, and re-running `mkworkdisk.py` wipes `WORK2.dsk`
  along with `WORK.dsk` — including a codefile an earlier step in the same
  session just produced. Add files to an existing disk with
  `PascalWriter.from_file(...).add_file(...)` instead when something else
  on it must survive, and back up a `.dsk` before touching it if it holds a
  result nothing has verified yet.
- **A failed `L(ink` still writes an output file** — sized to whatever was
  free, same as a failed compile (findings 91's table). `remove_file` it
  before retrying, not just the source of the failure.

## Apple Pascal 1.3, things that bite

- **Identifiers are significant to 8 characters.** `ONEDRIVE`/`ONEDRIV`
  collide. Volume filenames are 15 chars but the compiler writes output
  beside the source, so pick names that do not collide at 8 either.
- **`UNIT` is a reserved word.** So are the usual ones; a parameter named
  `UNIT` gives error 7.
- **`(*$I-*)` if the program tests `IORESULT` itself** — otherwise every I/O
  statement carries a `CSP 0` the shipped codefile does not have.
- **Allocation order: declaration groups ascend, identifiers within one
  group descend.** `VAR C, DIGIT: CHAR` and `VAR DIGIT, C: CHAR` give
  different offsets (finding 93a).
- **`OTHERWISE` in `CASE` is accepted and undocumented** — the manual never
  mentions it (finding 102b).
- An array indexed with `IXA 1` and stored with `STO` is **unpacked**; a
  packed one uses different code and a different size.
- `{$R-}` (no `CHK`) is established; `{$G+}` all but certain; `{$U-}` ruled
  out.
- Global frame bound is `(param_size + data_size) / 2` **words** — parameters
  and locals share one offset space (finding 46).
- Source files: **LF line endings**, plain ASCII. **Assembler source ≤80
  columns** (error 54); `srcfmt.over_width` enforces it for any file with
  a `.PROC`/`.FUNC`. **Pascal source has no width limit here**: Apple's
  compiler read `SYSTEM.EDITOR`'s 81-column lines (finding 272e). Nothing
  longer has been tried, so keep Pascal near 80 unless a line cannot be.

## Codefile facts

- Segment dictionary at offset 0: code addr/len `$00`, names `$40`,
  **SEGINFO `$100`**, textaddr `$120`, seginfo `$140`.
- **SEGINFO version** = the release that *wrote* the file (1.1 writes 2, 1.3
  writes 6), enforced by the OS. It is how you tell a rebuilt file from a
  binary carried over unchanged.
- `mtype == 6502` exactly when a segment holds native procedures.
- Native procedure: `enter_ic` → `jtab+2`; four relocation tables (base,
  segment, procedure, interp) read from `jtab-4` downward; `PROCEDURE NUMBER
  == 0` marks it native. **Parameter count is not recorded** — hence
  `NATIVE_SIG` in `lift.py`, guarded by `probe_native_sig.py`.
- **Native procedures are stored UNRELOCATED.** Address words hold offsets
  from the procedure's own start; relocation is the loader's work. Do not
  add a base before comparing (finding 103f).
- `RELOCSEG` (high byte of the attribute word): 0 = through the BASE
  register, which is what a program uses; non-zero names a data segment; 1
  for an Intrinsic Unit with none.
- **A compile alone leaves a segment with an `EXTERNAL` marked `HOSTSEG`.**
  Only `SYSTEM.LINKER` resolves it and produces the `LINKED` segkind Apple
  shipped (finding 91). A file with a native half needs all three tools.
- The tail of the last block is **uninitialised slack**, not content. Apple's
  holds leftover 6502; yours will hold whatever the tool had in memory.
  Compare up to the end of the segment and say so.

## 6502 source

Apple Assembler syntax: default **hex** (constants must start with a digit —
`0FEAE`, not `$FEAE`), `.PROC`/`.FUNC name,words`, `.BYTE`, `.EQU`,
`.DEF`/`.REF`, `.INTERP`, `@` for indirect, `.END`.

Write **symbolic operands and let the assembler emit the relocation tables**
— never hand-build one, never substitute a modern assembler. A reference
written as a constant where Apple wrote a label assembles fine and fails the
byte compare, which is the point.

`.FUNC` declares only its parameters; `NATIVE_SIG`'s `words` counts
parameters **plus two** for the function result.

## Reading the binary

- **A backward branch is a loop condition before it is anything else.** An
  `FJP` to the top of a `REPEAT` is an `UNTIL`, not a misplaced `IF`. Two
  loops can start at the same statement, so the jump table holds one address
  twice (finding 104a).
- The lifter's output is usually right when the prose around it is wrong —
  it had been printing `goto <loop top>` correctly for a round while the
  reconstruction chased a different shape.
- The compiler **does not short-circuit**: `and`/`or` compile to `LAND`/`LOR`
  on values, and `FJP` chains that look like short-circuiting are nested
  `if`s in the source.
- UCSD puts a `CASE` jump table **after** the arms.
- Error numbers name a routine's purpose (manual II-3E) — but **1.3
  renumbered at least one** (`JTAB` overflow 253 → 254), so do not carry a
  name across releases by error number.

## Sources of truth, in order

1. The binary.
2. The Apple Pascal 1.3 manual and language reference —
   `evidence/reference/manuals/`, OCR flattened to `analysis/reference/*.txt`
   by `reference_text.py`. **OCR is unreliable for dense pages**; re-read as
   an image with `tools/pdfpage.py` before quoting.
3. Hyde's *P-Source* for p-machine questions.
4. Published Pascal-P / UCSD source — legitimate for **names only**. The
   compiler is a direct P2 descendant (its `operator` enum survives
   verbatim), but re-derive every structure from the binary.
5. Neil Parker's *Undocumented Secrets of Apple Pascal* — a lead, not an
   authority. It got `SYSTEM.COMPILER`'s own `{$U-}` status wrong.
6. `evidence/reference/tribby-idsearch-treesearch-1.2.asm` is **1.2** —
   corroboration and a source of label names, not evidence.

`ii0src.sdk` is the UCSD II.0 **operating system**, not the compiler — it is
relevant to `SYSTEM.PASCAL` and useless for `SYSTEM.COMPILER` (finding 8).

## Naming and correspondence

A recovered name can be wrong, and it shows up as a *second* routine
behaving more like the name than the one holding it. Write the evidence down
and leave the name alone until the answer is known — renaming twice is worse
than renaming late.

The 1.1 -> 1.3 correspondence table (finding 11) and its tools are archived
with 1.1. Findings that cite 1.1 are history; confirm anything they claim
against the 1.3 binaries before relying on it.

## Git

Commit messages explain *why* and record what was wrong, not just what
changed. Push only when asked. Files carry CRLF in the working copy and LF
in the repo — the `warning: LF will be replaced by CRLF` noise on every
`git add` is expected.
