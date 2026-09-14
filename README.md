# Apple Pascal 1.3, reconstructed

Source for the files on the Apple Pascal 1.3 disk set (128K system),
written so that **Apple's own tools**, run under AppleWin, turn it back
into the bytes Apple shipped. The target is byte-identical output, not
readable pseudocode.

**Where it stands.** `tools/mkdiskset.py` writes the three 1.3 disks,
`APPLE1`-`APPLE3`, from what this repository rebuilds. **359,323 of their
430,080 bytes are identical to Apple's images.** Without the archived 64K
system it is 351,873 of 374,784. Every remaining difference has a named
cause, and `tools/probes/probe_diskset.py` requires the account to
balance region by region against a direct image compare.

## The files

Each file is rebuilt by Apple's compiler, assembler, Linker, Librarian or
SETUP on the 1.3 system unless marked otherwise. "Identical" means every
byte of the file as it sits on the disk.

| file | result | source | finding |
|---|---|---|---|
| `SYSTEM.COMPILER` | identical | `src/pascal/1.3/`, `src/native/SEARCH.TEXT` | 267e |
| `SYSTEM.ASSMBLER` | identical; its `PASCALIO` segment is copied from Apple's file, nothing on the disks rebuilds it | `src/pascal/programs/1.3/ASSMBLER.text` | 267f, 235b |
| `SYSTEM.LINKER` | identical | `programs/1.3/LINKER.text` | 268 |
| `SYSTEM.EDITOR` | identical | `programs/1.3/EDITOR.text` | 272 |
| `SYSTEM.FILER` | identical | `programs/1.3/FILER.text` | 271 |
| `LIBRARY.CODE` | identical | `programs/1.3/LIBRARY.text` | 269 |
| `128K.APPLE` | identical | `src/native/interp/`, `MAKEINTP` | 279 |
| `SYSTEM.CHARSET` | identical | `src/data/CHARSET.TEXT`, `MAKECHRS` | 278 |
| `6502.OPCODES` | identical | `src/data/OPS6502.TEXT`, `MAKEOPS` | 276 |
| ten text files | identical, by this repository's encoder | `src/text/` and `.layout` | 288 |
| `FORMATTER.DATA` | all but 1 byte | `src/native/ASMFORMAT`, `BOOTII`, `BOOTPD`; `MAKEBOOT`, `MAKEFMT` | 275 |
| `BINDER.CODE`, `SET40COLS.CODE` | all but 16 version bytes each | `programs/1.3/` | 274 |
| `6502.ERRORS` | all but 287 bytes | `src/data/ERRS6502.TEXT`, `MAKEERRS` | 276 |
| `LIBMAP.CODE` | all but 311 bytes of Linker slack | `programs/1.3/LIBMAP.text` | 270 |
| `FORMATTER.CODE` | all but 394 bytes of Linker slack | `programs/1.3/FORMATTER.text`, `src/native/FORMATTR.TEXT` | 104 |
| `LINEFEED.CODE` | all but version bytes and slack (467) | `programs/1.3/LINEFEED.text` | 99a, 288c |
| `128K.PASCAL` | all but 571 bytes of a finishing tool's slack | `src/pascal/os/1.3/PASCALSYSTEM.text`, `MAKEOS` | 284 |
| four `.MISCINFO` | every setting; 556 bytes of memory SETUP never writes | `src/data/miscinfo/` recipes | 277 |
| `SETUP.CODE` | all 54 procedures; 3,943 bytes of version word and stale pads no 1.3 compiler writes | `programs/1.3/SETUP.text` | 273 |
| `SYSTEM.LIBRARY` | **accepted exception**: every code byte and all interface text, 16,417 of 19,456 aligned by unit | `src/pascal/units/1.3/`, `src/native/` | 285-287, 290 |
| `SYSTEM.APPLE`, `SYSTEM.PASCAL` | out of scope: the 64K system, archived | -- | -- |

`SYSTEM.LIBRARY`'s text blocks were written by a compiler other than the
one Apple shipped: their block counts, a trailer flag byte and buffer copies
in the extra blocks. No source can reproduce those, so the file is two
blocks short and its units sit early on the disk. `docs/PLAN.md` records
the decision.

The boot blocks come from the rebuilt `FORMATTER.DATA`. The directory
entries (names, placement, dates) are Apple's, re-encoded. What is left on
the disks beyond the table is Apple's mastering residue: dead directory
space and one block of old linker records on `APPLE2` (289b).

## Checking it

```
python tools/build_all.py
```

This regenerates `build/`, `analysis/` and `reference_source/` from the
evidence and runs every probe; it must exit 0. The emulator runs themselves
are interactive, so their output is kept verbatim in `acceptance/`, and the
probes compare that with Apple's disks on every build. How to drive Apple's
tools (`tools/emuremote.py`) is in `CLAUDE.md`.

## Reading further

* **`docs/DISKSET.md`** -- the per-file scoreboard.
* **`docs/FINDINGS.md`** -- the evidence ledger, 290 findings, each claim
  labelled VERIFIED BINARY FACT, VERIFIED SOURCE FACT, STRONG INFERENCE or
  SPECULATION.
* **`docs/PLAN.md`** -- current state, the plan as it ran, working rules.
* **`analysis/diskset-account.txt`** -- every byte of every disk, by region.

## Layout

```
evidence/disks/      the three 1.3 disk images and ii0src.sdk, never modified
evidence/reference/  manuals, Parker, Tribby, UCSD II.0 and I.5 sources
src/pascal/1.3/      SYSTEM.COMPILER
src/pascal/os/1.3/   128K.PASCAL
src/pascal/units/    SYSTEM.LIBRARY's units, with .layout files
src/pascal/programs/ the utilities and the MAKE* finishing programs
src/native/          6502 assembly, Apple Assembler syntax
src/data/            data file sources and SETUP recipes
src/text/            the ten text files, with .layout files
tools/               generators and emulator drivers; a2pascal/ is the library
tools/probes/        checks, run by build_all.py
acceptance/          what Apple's tools produced, kept verbatim
docs/                PLAN, FINDINGS, DISKSET
archive/             Apple Pascal 1.1 and the 64K system, not built
legacy/              the inherited ChatGPT-era handoff, not used
```
