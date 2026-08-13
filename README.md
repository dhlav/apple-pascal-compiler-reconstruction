# Apple Pascal compiler reconstruction

Recovering the source of Apple Pascal's `SYSTEM.COMPILER` from the shipped
binaries, to the point where recompiling the reconstruction under Apple
Pascal 1.1 reproduces the original P-code.

Start with **[docs/FINDINGS.md](docs/FINDINGS.md)** — what is established,
and where the inherited ChatGPT handoff was wrong. Then
**[docs/PLAN.md](docs/PLAN.md)** for what happens next.

## Layout

```
evidence/          original inputs, never modified
                   (two external sources are read in place and NOT copied
                   here: John Brooks' Apple Pascal 1.4 interpreter source,
                   and Peter Miller's ucsd-psystem-xc. See findings 17, 18.)
  disks/           the two Apple Pascal .dsk images and ii0src.sdk
  reference/       Neil Parker; Dave Tribby's 1.2 IDSEARCH/TREESEARCH
tools/             all analysis code
  a2pascal/        disk.py codefile.py pcode.py m6502.py textfile.py
                   nufx.py syscall.py lift.py globals.py
  probes/          one-off scripts that established a format detail
  build_all.py     regenerates everything below
build/             ii0src.po, the disk image unpacked from ii0src.sdk
reference_source/  UCSD II.0 operating system source, extracted
analysis/          procedure_maps/  pcode_disassembly/  native/  callgraph/
                   global_map/      globals-*.txt, correspondence-1.1-to-1.3.txt
                   procedures/      per-procedure evidence profiles
legacy/            the inherited ChatGPT phase archive, unaltered
docs/              FINDINGS.md, PLAN.md
```

`build/`, `reference_source/` and `analysis/` are entirely generated:

```
python tools/build_all.py
```

## The short version

`SYSTEM.COMPILER` is a UCSD codefile of 15 segments: `PASCALCO` (the main
program and its service routines) plus 14 phase segments — `COMPINIT`,
`DECLARAT`, `BODYPART`, `ROUTINE`, `STATEMEN`, `CASESTAT`, `FORSTATE`,
`BODY1`, `BODY3`, `WRITELIN`, `UNITPART`, `COMPOPTI`, `NUMSTRIN`,
`FINISHUP`. Almost all of it is UCSD II.0 P-code in both releases: across
the two disks there are 287 p-code procedures and exactly **2** native 6502
ones, both added in 1.3.

The decoder in `tools/a2pascal/pcode.py` disassembles all 287 with the
instruction stream landing exactly on every procedure boundary and no
unknown opcodes. Its opcode table is cross-checked against three
independent sources — Hyde's *P-Source* (1983), John Brooks' Apple Pascal
1.4 interpreter, and Peter Miller's `ucsd-psystem-xc` — which agree with it
and, on the one point where they disagree with each other, against Hyde.
Calls into the runtime are named by cross-referencing the UCSD II.0 OS
source, so listings read like `CXP 0,3  ; OS.3 FINIT`; that numbering also
matches Miller's table 28 out of 28.

All 41 standard-procedure calls are named and their stack effects known,
including the `LOADSEGMENT`/`UNLOADSEGMENT` pair that drives the compiler's
phase swapping.

The compiler's global variables are mapped (sizes, shapes, access counts,
users), and several service routines are identified — the error reporter,
the scanner, the symbol-table search, the code-byte emitter.

**All 287 procedures across the two releases lift to expression-level
pseudo-Pascal** with the evaluation stack fully tracked
(`analysis/lifted/`). `tools/show.py SEGMENT.N` prints a procedure's
p-code listing; `tools/liftproc.py SEGMENT.N` prints its lifted form:

```
procedure PASCALCO.20(params 1 words);  { locals 0 words, lex 1 }
  G2^[G9] := L1;
  G9 := (G9+1);
```

The eventual target is **1.3**, but analysis leads with 1.1 and transfers:
`tools/globaldiff.py` matches 131 procedures and 128 globals across the two
releases with zero contested entries, so 1.1 results carry over
mechanically.

Three corrections to the inherited handoff matter most: `COMPINIT` has
**10** procedures, not 29 — the "29-procedure COMPINIT map" is actually
PASCALCO's map; `ii0src.sdk` is the UCSD **operating system** source, not
compiler source; and PASCALCO was never "rewritten in native 6502" — 1.3
hand-coded just two routines, `IDSEARCH` and `TREESEARCH`.
