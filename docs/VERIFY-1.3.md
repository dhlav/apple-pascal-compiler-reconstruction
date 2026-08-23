# Verifying the 1.3 reconstruction against Apple's `SYSTEM.COMPILER`

The claim this repository makes is narrow and mechanical: **the
reconstructed source, compiled by Apple's own 1.3 compiler, produces
Apple's own 1.3 compiler, instruction for instruction.** This file is the
procedure for reproducing that from a clean checkout. It takes about five
minutes, most of it the emulator.

The result to expect, and the only one that counts:

```
147 procedures declared, 147 of 147 reconstructed bodies matching
Apple's p-code, 0 still stubs
```

## Why there are two tiers, and why only one of them is the authority

`ucsdpsys_compile` (the **fast tier**) runs on this machine, compiles in
seconds, and is what the reconstruction was written against day to day. It
is not the authority and cannot be. It targets UCSD II.0/II.1, and it
differs from Apple's compiler in ways that have nothing to do with the
source: it short-circuits `AND`/`OR` where Apple emits `LAND`/`LOR`
(finding 58), it folds constants Apple computes at run time, it allocates
`WITH` temporaries differently (finding 87c), and it has no `$NS`. A body
can be exactly right and still come back DIFFERS.

So the fast tier can **falsify** a body and cannot **accept** one. Only
Apple's compiler, running under Apple's operating system, settles it. That
is the **emulator tier**, and it is the whole of the procedure below.

## Prerequisites

* AppleWin at `C:\AppleWin\AppleWin.exe` (paths live at the top of
  `tools/runemu.py`).
* The three 1.3 evidence disks in `evidence/disks/`: `APPLE1_ 680-0283-A`,
  `APPLE2_ 680-0284-A`, `APPLE3_ 680-0290-A`. `evidence/` is read-only and
  nothing here writes to it.
* Python 3.11+. The fast tier additionally wants `ucsdpsys_compile` built
  under WSL, but **the verification below does not use it** -- `--emu` and
  `--emu-check` never call it.

## The four steps

```
python tools/mkbootdisk.py                      # once; build/disks/BOOT128.dsk
python tools/mkworkdisk.py                      # fresh WORK: and WORK2:
python tools/procbuild.py --emu --ver=1.3       # splice source onto WORK:
.\tools\emucompile.ps1 -Name BODY13 -Release 1.3 -Work2 -Compile 120
python tools/procbuild.py --emu-check --ver=1.3 # diff, procedure by procedure
```

### 1. `mkbootdisk.py` -- the 128K system

Only needed once; `BOOT128.dsk` is stable. It is `APPLE1` with `128K.APPLE`
and `128K.PASCAL` from `APPLE3` substituted in as `SYSTEM.APPLE` and
`SYSTEM.PASCAL`, which is the manual's own procedure.

**This is not optional.** On the 64K system the compiler dies of a runtime
stack overflow -- not on the reconstruction, which would be a result, but
on `HILBERT.TEXT`, one of Apple's own shipped samples. The 128K run
finishes with about 10,300 words of heap to spare; 64K does not have it.

### 2. `mkworkdisk.py` -- fresh volumes

Run this **before every** `--emu`. A Disk II volume is 280 blocks and that
is the entire budget: the spliced source alone is 156 blocks and the
codefile another 87. Leaving the previous run's files behind is how you get
*error 402 at the last line*, which from inside the compiler is what a full
output volume looks like and reads like a source error.

### 3. `procbuild.py --emu --ver=1.3` -- splice and write

Assembles the fifteen segment files plus `PASCALCO.text` into one program
against `analysis/reconstruction/skeleton-1.3.text`, strips the commentary
(comments provably cannot change a byte, and the volume has no room for
them), and writes it to `WORK:BODY13.TEXT`. It no longer fits on one
volume, so the tail goes to `WORK2:BODY13B.TEXT` and the head ends with
`(*$I WORK2:BODY13B*)` -- the split is put at a top-level procedure heading
so a reader recognises it (finding 82).

`--ver=1.3` is required. Without it the tool writes 1.3 and then fails to
fit 1.1 beside it. **One release per emulator run.**

Expect: `wrote WORK:BODY13.TEXT (6598 lines, 30 procedures)`.

### 4. `emucompile.ps1` -- Apple's compiler does the work

Launches AppleWin on BOOT128 with `APPLE2` in drive 2, waits for the boot,
sends `C` and the two filenames, waits, screenshots, and closes the
emulator -- **the close is what flushes the disk images**, because AppleWin
holds them open until it exits. Do not skip it or read the image early.

Three things about driving it, each of which cost a run to learn:

* **`C(ompile` from the command menu is the way in**, not `X(ecute`.
  `X` appends `.CODE` and `SYSTEM.COMPILER.CODE` is over the 15-character
  limit; and `X`-ing it directly gets *Line 0, error 401*, which is the
  compiler looking for a workfile that is not there. Not a privilege
  problem -- the compiler is not `{$U-}` (finding 87d).
* **Send the whole command in one call.** Apple Pascal has a type-ahead
  buffer, so there is no need to wait for each prompt -- but keep 60ms
  between characters or the system drops them.
* **Do not touch the keyboard or click anything while it runs.**
  `emukeys.ps1` throws rather than type into the wrong window, and a
  stolen focus aborts the run. Both failure modes are real and both were
  hit while writing this.

Read the screenshot. A clean run ends `6597 lines`, `Smallest available
space = 9239 words`, and the Command prompt. Anything else -- a line number
followed by an error, `Stack overflow`, the editor -- means stop and read
before going on.

### 5. `procbuild.py --emu-check --ver=1.3` -- the diff

Finds `BODY13.CODE` on whichever volume has it, disassembles it and Apple's
shipped `SYSTEM.COMPILER` **with the same decoder**, and compares the
instruction text of every procedure from `enter_ic` through the return,
including the exit sweep, because UCSD puts case jump tables past the
return and they are part of the procedure.

Absolute jump targets are blanked to `$----`: `FJP $092A` and `FJP $0417`
are the same instruction in two codefiles, and a jump to the *wrong* place
still shows, because the instructions after it land in the wrong order.
Identifiers are not compared -- they are not recoverable from the binary
and change no byte. Procedure *numbers* are compared and must match:
declaration order is the numbering (finding 61).

## What the result does and does not establish

**Does:** every p-code procedure of 1.3's `SYSTEM.COMPILER` is reproduced
exactly by this source under Apple's compiler. Plus `IDSEARCH` and
`TREESEARCH`, the two native 6502 routines, which the assembler tier holds
byte-identical (finding 57a) -- reassemble those with `SYSTEM.ASSMBLER`,
not a host assembler, because Apple's assembler is what emits the
relocation tables.

**Does not:** recover Apple's identifiers, comments, or formatting. Those
are not in the binary. Where a name here is a guess it is marked
SPECULATION in `docs/FINDINGS.md`.

## If it fails

| symptom | cause |
|---|---|
| *error 402* at the last line | output volume full -- rerun `mkworkdisk.py` |
| *Stack overflow* | booted 64K by mistake; check `BOOT128.dsk` is in S6D1 |
| *is not version 1.3* | a non-1.3 compiler in drive 2 |
| lands in the editor | a prompt was refused and type-ahead fell through to `E` |
| `BODY13.CODE` on neither volume | the compile never finished; read the screenshot |
| a codefile exactly as big as the free space | preallocation left by a **failed** compile, not a result |

That last row is worth its own line. The compiler grabs the whole free
extent for its output and shrinks it on success, so a codefile whose size
equals the volume's free blocks is a failed run, not a finished one.

## 1.1

`src/pascal/1.1/` is a separate matter and is **not** verified to this
standard. Its state is finding 88: 93 of 289 bodies across the two releases
instruction-identical under the fast tier, 89 more carrying exactly the
diff their verified 1.3 counterpart carries, and 9 read by hand. The
emulator tier does not reach it -- 1.1's compiler runs only under 1.1's
operating system, which is 64K, and the reconstruction needs about one
64K bank more heap than that leaves. No compiler option closes the gap:
`(*$S++*)` and `(*$T+*)` together move the failure from line 637 to line
994 of 9,473 and stop.
