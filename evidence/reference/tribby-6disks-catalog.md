# Dave Tribby's six disks -- all six now fully readable

**Update, later the same day:** the user supplied `.sdk` (ShrinkIt-compressed)
versions of all six disks at `C:\dl\trib\*.sdk`. `cp2` (v1.2.0, see below)
opens every one of them directly -- including `psys.sdk`, which is the one
the raw `.dsk`/`.do`/`.po` images could never get past "contents not
recognized" for. Whatever was wrong with the raw `psys` image (the 236-byte
directory misalignment documented below) is **not present in the ShrinkIt
copy** -- it reads clean, 38 files, full listing below. This closes out the
open item this file used to end on.

**Found the file the user's `GLOBAL1_VARS`/`GLOBAL2_VARS` excerpt came
from: `psys.sdk`'s `SYSINF.TEXT`.** Extracted and decoded with this
project's own `tools/a2pascal/textfile.py` -- clean round trip. It's Dave
Tribby's own `UNIT SysInf` ("Written by DMT beginning 2-8-87"), a
system-information utility unit, not part of Apple's own `SYSTEM.PASCAL`
source (which this project doesn't have and isn't started). Confirmed
**VERIFIED SOURCE FACT** against the live text: `max_unit := 12;` for
version 1.1, `max_unit := 20;` for 1.2 and 1.3 (`FUNCTION ChkPascal`), and
`unit_table: ARRAY [0 .. 20] OF RECORD ...` in `GLOBAL1_VARS` -- exactly
matching what the user pasted. **No `MAX_SEG` constant appears anywhere in
this file** -- Tribby's unit only cares about `max_unit`/`unit_table`; the
`MAXUNIT`/`MAX_SEG` CONST pair with the "64K vs 128K" comments the user
quoted must be from a different source (most likely a UCSD II.0-style
`GLOBALS.TEXT` for `SYSTEM.PASCAL` itself, the same lineage as the
`PASCALIO.text`/`LONGINTIO.text` CONST block flagged in finding 110 --
still not present on any of these six disks). The decoded text isn't
checked into this repo; re-extract `SYSINF.TEXT` from `C:\dl\trib\psys.sdk`
with `cp2` if it's needed again.

---

*(Everything below reflects the investigation before the `.sdk` files
arrived -- kept for the record of what was tried and ruled out on the raw
`.dsk`/`.do`/`.po` images.)*

Source: `C:\dl\trib\*.dsk` (user-supplied, 2026-08-27). Not copied into this
repo -- these are 800K (`futil1`, `io`, `prdev`, `psys`) and 143,360-byte
(`diskmap`, `tools0`) raw images. `diskmap.dsk` and `tools0.dsk` are
ordinary 5.25" Pascal floppies and read cleanly with this project's own
`tools/a2pascal/disk.py` / CiderPress II.

**Update, same day:** the installed `C:\CiderPress2\cp2.exe` was v1.0.1
(2024). CiderPress II v1.2.0 (GitHub, 2026-03-21) added MOOF disk-image
support -- MOOF is the 3.5" format, which is what these four images
actually are. Downloaded `cp2_1.2.0_win-x64_sc.zip` from
`github.com/fadden/CiderPress2` to a scratch dir and re-tested: **v1.2.0
reads `futil1.dsk`, `io.dsk`, and `prdev.dsk` cleanly** -- `cp2 list` gives
full, correct file listings directly, no workaround needed, superseding the
regex-guessed filename lists below (kept struck through for the record).
`extract` pulls files out cleanly too (tested on `io.dsk`'s `U128DR.TEXT`,
see below).

**`psys.dsk` still fails even under v1.2.0**, and the failure mode narrows
down the cause. `cp2 read-block 2` on the three working disks (e.g.
`futil1`) returns the volume header (`first=0,last=6,kind=0,namelen=6,
"FUTIL1"`) starting at byte 0 of the block, exactly per spec. On `psys` the
same call returns 236 bytes of zero padding *before* the header bytes begin
(header lands at raw file offset 1260, not the expected 1024 = block 2 *
512). Shifting the whole 819,200-byte file left by exactly 236 bytes makes
`cp2 list` recognize it as a Pascal volume (no more "contents not
recognized") -- but every file then reports `<DAMAGED>`, because a uniform
byte-shift by a non-block-multiple fixes the directory header's alignment
by coincidence while leaving every block-number pointer in the directory
referring to the wrong bytes. That rules out "simple missing header bytes"
as the explanation. Whatever is wrong with `psys.dsk` specifically is a
real, disk-specific issue (a non-linear block order unique to this image,
or genuine corruption in the source media/imaging), not just a format
version gap `cp2` needed to catch up on -- the other three 800K images from
the same batch, same nominal format, don't have it.

## What's confirmed on each disk (filenames only, via directory reads)

**`psys.dsk`** ("PSYS.3", 1600 blocks) -- `SYSTEM.PASCAL`-adjacent tools and,
notably, **`LOSYS128K.TEXT`** (128K-system-relevant; worth chasing once this
disk decodes, given [[PLAN.md item 13]] on `SYSTEM.APPLE`/`128K.APPLE`).
Also: `SEGINFO.TEXT`/`.CODE`, `PTABLES.TEXT`/`.CODE`, `SETCSTRING.TEXT`,
`SYSREP`/`NEWSYSREP`/`SYSINF`/`MSINF`, `TREESEARCH.TEXT`/`.CODE` (a 1.2
source counterpart to `evidence/reference/tribby-idsearch-treesearch-1.2.asm`,
worth comparing once readable), `MAKE1.2SYS.CODE`/`.TEXT`, `CHANGEIO`,
`DISKDATE`, `SELECT`, `IDTEST`, `MENU`, `INSTALBOOT`, `CODEINFO`, `PRGADDR`,
`COPYBOOT`, `TSPNUM`, `SPNUM`, `PAM`/`PAMINFO`, `CHKSTAT`, `STARTUP`,
`SYSINFDOC`, `YBOOT.CODE`, `NEWBOOT`, `NEWNEW`, `COPYPROG`, `CHECKFILE`,
`CHECKMEM`. This is also where Tribby's `SYSTEM.PASCAL` globals declaration
(`GLOBAL1_VARS`/`GLOBAL2_VARS`, `MAXUNIT`, `MAX_SEG`, `unit_table`) lives,
embedded in one of these files rather than a standalone `GLOBALS.TEXT` --
which file has it is not yet pinned down, since it only turned up via the
unreliable linear scan above.

~~**`futil1.dsk`** -- file utilities: `BACKUP`, `CATALOG`/`CATINFO`,
`COMPFILES` (+`ACOMPFILES`), `COPYFILE`, `FASTIO`, `FILEINFO`,
`PAGER`/`PAGERINFO`/`DOPAGER`, `PROSE.CODE`, `SORTFILE`/`SORTTEST`, `SPLIT`,
`SVMGR`, `SYSINF`, `TESTFILEIN`, `TIMER`.~~ (superseded below)

~~**`io.dsk`** -- device drivers and comms: ... `U128DR.TEXT` ...~~
(superseded below)

~~**`prdev.dsk`** -- assembler/disassembler tooling: ...~~ (superseded below)

## Confirmed file listings, `cp2` v1.2.0 (`cp2 list`, exact and complete)

**`futil1.dsk`** (21 files): `PAGERINFO.TEXT`, `PAGER.TEXT`, `PTEST.TEXT`,
`DOPAGER.TEXT`, `COPYFILE.TEXT`, `COMPFILES.TEXT`, `SORTFILE.TEXT`,
`ACOMPFILES.TEXT`, `SORTTEST.TEXT`, `FILEINFO.TEXT`, `TESTFILEIN.TEXT`,
`FASTIO.TEXT`, `FASTIO.CODE`, `PROSE.CODE`, `BACKUP.TEXT`, `BACKUP.CODE`,
`SEE.TEXT`, `CATINFO.TEXT`, `CATINCL.TEXT`, `CATALOG.TEXT`, `CATALOG.CODE`.

**`io.dsk`** (47 files): `DVRTEST.TEXT`, `TERMINAL.TEXT`, `TERMINAL.CODE`,
`TESTCLOCK.TEXT`, `TESTCLOCK.CODE`, `CLOCKGS.TEXT`, `CLOCKGS.CODE`,
`OKIDATA.TEXT`, `TIMER.TEXT`, `TRACDVR.CODE`, `TRACDVR.TEXT`,
`MEMBFDVR.CODE`, `MEMBFDVR.TEXT`, `REMOTE.TEXT`, `SCREENTEST.TEXT`,
`SCREENTEST.CODE`, `CLEARAUX.TEXT`, `CLEARAUX.CODE`, `AUXGET.TEXT`,
`AUXGET.CODE`, `DISKSTUFF.TEXT`, `PASCALDISK.TEXT`, `DISKSTUFF`,
`SIDERDISK.TEXT`, `SIDERIO.CODE`, `SIDERIO.TEXT`, `HEXEDIT.TEXT`,
`HEXEDIT.CODE`, `RECOVER.TEXT`, `RECOVER.CODE`, `REMSTATUS.CODE`,
`REMSTATUS.TEXT`, `MODTEST.TEXT`, `HELPFILE.TEXT`, `LINK.TEXT`,
`MODTEST.CODE`, `REMTEST.TEXT`, **`U128DR.TEXT`**, `CONNECT.CODE`,
`MACROKEYS.TEXT`, `AXMODEM.CODE`, `SPECIALS.TEXT`, `XMSTUFF.TEXT`,
`READREM.TEXT`, `READREM.CODE`, `CONNECT.TEXT`, `AXMODEM.TEXT`,
`XMSTUFF.CODE`, `RUN.CODE`.

**`prdev.dsk`** (17 files): `CROSSREF.TEXT`, `CROSSREFA.TEXT`,
`ABSDIS.TEXT`, `6500.INSTRS`, `PCODE.INSTRS`, `POPORDER.TEXT`,
`CODETEST.TEXT`, `BUILDOPS.TEXT`, `DINCLUDE.TEXT`, `DISASSM.TEXT`,
`DISASSM.CODE`, `POPCODES.TEXT`, `FIXDIS.CODE`, `FIXDIS.TEXT`,
`PROCNUM.CODE`, `PROCNUM.TEXT`, `ABSDIS.CODE`.

### `U128DR.TEXT` -- extracted and read, confirmed relevant to plan item 13

Extracted with `cp2 x io.dsk U128DR.TEXT` and decoded with this project's
own `tools/a2pascal/textfile.py` `decode_text` -- clean round trip, no
garbling. It's a dated 1983 6502 driver source, `.PROC U128DR`, handling
the p-system's driver call protocol (init/status/read/write dispatch on the
X register, block/byte-count/buffer/unit params popped off the stack) for
what reads like a RAM-disk-style block device sized to the 128K system.
Worth a real read when `SYSTEM.APPLE`/`128K.APPLE` (plan item 13) gets
picked up -- this is a working driver skeleton for that memory config, not
just a name match.

## `psys.sdk` -- confirmed listing (38 files, `cp2` v1.2.0, ShrinkIt copy)

`MAKE1.2SYS.TEXT`, `PTABLES.TEXT`, `SETCSTRING.TEXT`, `COPYPROG.TEXT`,
`CHECKFILE.TEXT`, `CHECKMEM.TEXT`, `MSINF.TEXT`, `SEGINFO.TEXT`,
`SYSINF.TEXT` (Tribby's `GLOBAL1_VARS`/`GLOBAL2_VARS` source -- see top of
file), `SYSREP.TEXT`, `NEWBOOT.TEXT`, `NEWSYSREP.TEXT`, `NEWNEW.TEXT`,
`CODEINFO.TEXT`, `PRGADDR.TEXT`, `TSPNUM.TEXT`, `SPNUM.TEXT`, `PAM.TEXT`,
`PAMINFO.TEXT`, `CHKSTAT.TEXT`, `STARTUP.TEXT`, `SYSINFDOC.TEXT`,
`CHANGEIO.TEXT`, `DISKDATE.TEXT`, `SELECT.TEXT`, `IDTEST.TEXT`,
`INSTALBOOT.TEXT`, `TREESEARCH.CODE`, `TREESEARCH.TEXT`,
`MAKE1.2SYS.CODE`, `MSINF.CODE`, `PTABLES.CODE`, `SETCSTRING.CODE`,
`SEGINFO.CODE`, `PAM.CODE`, `MENU.TEXT`, `MENU.CODE`, `COPYBOOT.TEXT`,
`COPYBOOT.CODE`.

Neither `LOSYS128K.TEXT` nor `YBOOT.CODE` -- both named in the earlier
regex-guessed scan above -- are actually on this disk; those names were
artifacts of reading garbled/misaligned data and should be disregarded.

`TREESEARCH.TEXT`/`.CODE` is the 1.2 source counterpart to
`evidence/reference/tribby-idsearch-treesearch-1.2.asm` and is now
extractable cleanly if it's ever worth comparing against that listing.

## If this is picked back up

All six disks are readable now (five raw, `psys` via its `.sdk`). Nothing
here blocks further work; extract from the `.sdk` files with `cp2` v1.2.0
as needed. `SYSTEM.PASCAL` itself is still not started in this repo --
these disks remain corroboration, not a source to copy from directly (see
`evidence/reference/README.md`'s standing rule).
