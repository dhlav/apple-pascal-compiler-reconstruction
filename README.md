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
                   here: John Brooks' Apple Pascal 1.4 interpreter source
                   and Peter Miller's ucsd-psystem-xc. See findings 17, 18.)
  disks/           the two Apple Pascal .dsk images and ii0src.sdk
  reference/       Neil Parker; Dave Tribby's 1.2 IDSEARCH/TREESEARCH
    ucsd-ii0-compiler/  the UCSD Pascal II.0 compiler source, 15 files
    manuals/       the Apple Pascal 1.3 manual set, the 1980 language
                   reference, the 1.1 update notice, Hyde's P-Source --
                   scans plus their OCR. Copyrighted; this repo is private.
tools/             all analysis code
  a2pascal/        disk.py codefile.py pcode.py m6502.py textfile.py
                   nufx.py syscall.py lift.py structure.py globals.py
                   names.py -- recovered procedure and global names
  probes/          one-off scripts that established a format detail
  build_all.py     regenerates everything below
build/             ii0src.po, the disk image unpacked from ii0src.sdk
reference_source/  UCSD II.0 operating system source, extracted
analysis/          procedure_maps/  pcode_disassembly/  native/  callgraph/
                   global_map/      globals-*.txt, correspondence-1.1-to-1.3.txt
                   procedures/      per-procedure evidence profiles
                   reference/       the manuals' OCR, flattened for grep
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
It has since been held against Apple's own table, Part IV Ch. 4 of the 1.3
manual: **85 numbered opcodes and all four short-form ranges agree,
mnemonic and parameters**, with nothing to change (finding 25).
Calls into the runtime are named by cross-referencing the UCSD II.0 OS
source, so listings read like `CXP 0,3  ; OS.3 FINIT`; that numbering also
matches Miller's table 28 out of 28.

All 41 standard-procedure calls are named and their stack effects known,
including the `LOADSEGMENT`/`UNLOADSEGMENT` pair that drives the compiler's
phase swapping.

The compiler's global variables are mapped (sizes, shapes, access counts,
users), and **all 29 of PASCALCO's procedures are named** — the error
reporter, the scanner, the symbol-table search and entry, the code-byte
emitter, `COMPTYPES`, `BLOCK`, `GETNEXTPAGE`, `NEWSEG`, `SKIP`,
`NEXTLINE` and the rest. Two levers did most of it. One is the manual's
error list: a routine that raises "Too many segments for segment
dictionary" is doing something about segment numbers whatever else it
does. The other is that the manual documents the compiler's *output*
formats, so a routine that writes one can be named column by column —
Part II's description of the compiled listing names five globals at once,
and the codefile's procedure dictionary identifies `FINISHSEG`
(finding 28).

Naming the last of them overturned a previous conclusion. `PASCALCO.23`
writes the **segment** tail, not a procedure attribute table, so global 13
is the segment number and global 96 the procedure counter; the lexical
level is global 77, confirmed by its being the LEX operand of every
emitted `LOD`/`LDA`/`STR`. `tools/probes/probe_segtail.py` rebuilds all
30 segment tails across the two releases from the procedure lists alone
and matches them byte for byte.

Both of the scanner's enumerations are recovered **complete and gapless**
(finding 26): `SYMBOL` at 0..54 and `OPERATOR` at 0..15, from the
reserved-word table in the native `IDSEARCH`, the `case` over source
characters inside `INSYMBOL`, and the number scanner. `OPERATOR` turns out
to be the Zurich P2 / Pascal-P `operator` enumeration verbatim — all
sixteen members in the published order — which settles what this compiler
descends from. Eight globals hold a `set of symbol`, and each is pinned by
the error its guard raises against the vendor's error list, so the
listings now read

```
  until (SY in (STATBEGSYS + {endsy,unitsy,implsy}));
```

The **UCSD Pascal II.0 compiler source** is now in `evidence/` (finding
32) — the Zurich P2 descendant that Apple's compiler descends from in
turn. It is not an answer key: Apple changed things, and where the two
disagree the binary wins. But it makes everything derived from the bytes
alone checkable against a document written by the compiler's authors, and
`tools/probes/probe_ucsd_source.py` does that. **All eight numeric bounds
recovered from bare constants in the binary are named and matched** —
`MAXCODE = 1299`, `MAXJTAB = 24`, `MAXSEG = 15`, `MAXPROCNUM = 149`,
`MAXLEVEL = 8`, `MAXADDR = 28000`, `STRGLGTH = 255`, `DEFSTRGLGTH = 80`.
`OPERATOR` matches 16 of 16 members and `SYMBOL` 54 of 55, the one
difference being Apple dropping `SEPARATE` for `OTHERWISE`. `FINISHSEG`
and `PRINTLINE` reproduce line for line and column for column.

It also corrected fifty-six names. `EMIT`/`EMITWORD` are `GENBYTE`/
`GENWORD`, the emitter family is `GEN0`/`GENLDC`/`GEN1`/`GEN2`/`GENBIG`/
`GENJMP`, `FLUSHBUFFER` is `WRITECODE`, `ENDSEGMENT` is `FINISHSEG`,
`ERRORWITHTEXT` is `PRINTLINE`, and the segment `WRITELIN` is
`WRITELINKERINFO` — a name no amount of staring at the binary would have
produced. `probe_identifiers.py` now reads the II.0 source rather than a
hand-kept list, and requires every name over eight characters to appear
there; all 53 do.

It also settled the rule the reconstruction's `VAR` block has to obey
(finding 33). `VARDECLARATION` collects a declaration's identifiers by
*prepending* them to a list, then walks that list assigning addresses — so
**a `VAR` declaration allocates backwards**: `VAR LC,IC: ADDRRANGE` puts
`IC` at the lower offset. That is a prediction about Apple's binary, and
it holds **18 declaration groups, 86 names, across both releases**
(`probe_vardecl.py`). None of those names came from declaration order;
the eight symbol-set globals were each assigned by the error its guard
raises (finding 26c) and come out in exactly reverse order, all eight.

`tools/vardecl.py` lays II.0's `VAR` block out under that rule and aligns
it against Apple's globals: 67 matched names, differing only by a drift
that never decreases through the scalar region. The first sixteen words of
Apple's global area are II.0's, in order.

Inside the phase segments, the statement grammar and the expression chain
are recovered (finding 31). Each of `STATEMEN`'s seven statement parsers
is pinned twice over — by the reserved word it demands, through a symbol
code recovered separately, and by the error number it raises when that
word is missing, which Apple's error list glosses in English. `while`
demands `dosy` and raises 54, "'DO' expected"; `with` raises 250, "Too
many scopes of nested identifiers", which only a construct that opens a
scope can. `BODYPART.11` → `.33` → `.34` → `.35` sit at lexical levels 2,
3, 4 and 5, each declared inside the one before, which is Pascal-P's
`expression → simpleexpression → term → factor` exactly.

That also recovers the compiler's busiest data structure. Globals 3–7 are
Pascal-P's `gattr`, field for field: the global map had already sized word
3 as a five-word record whose words 4–7 are addressed individually, at 202
accesses, and `BODYPART.8:LOAD` shows it emitting `LOD <word 6>, <word 7>`
— which only a lexical level and an offset can be.

Fifteen more names needed no inference: the manual says the codefile's
SEGNAME field holds *"the first eight characters of the … SEGMENT
procedure … name that was translated into the corresponding segment"*, so
the segment dictionary has been carrying identifiers out of Apple's source
all along. Procedure 1 of each segment is that segment procedure, and its
lexical level is the depth at which Apple declared it — which recovers the
compiler's declaration skeleton, identical in both releases (finding 30):

```
  PASCALCO                                    lex 0   the program
    COMPINIT  DECLARAT  BODYPART  WRITELIN    lex 1
    UNITPART  COMPOPTI  NUMSTRIN  FINISHUP
      ROUTINE   STATEMEN                      lex 2
        BODY1  BODY3  CASESTAT  FORSTATE      lex 3
```

Every recovered name has to survive a constraint the reconstruction cannot
ignore: **Apple Pascal keeps only the first eight significant characters**
of an identifier, ignoring underscores and folding case — implemented
literally in 1.3's native `IDSEARCH`, which fills an eight-byte buffer and
discards the ninth character onward. Two names alike in eight characters
are one identifier. That killed four of finding 26's spellings: Pascal-P's
convention would give `interfacesy`, `implementationsy`, `externalsy` and
`otherwisesy`, each of which folds onto the reserved word it names and so
scans as that reserved word. It also renamed `PASCALCO.15` off `STRING`,
which is predeclared and whose type the compiler itself needs.
`tools/probes/probe_identifiers.py` now enforces the rule against every
name in the registry, including the 42 reserved words and 66 predeclared
identifiers (finding 29).

Its two central data structures are recovered field by field from the code
that initialises them: the type descriptor and the symbol-table entry,
with the `structform` and `klass` enumerations, and the standard types
`INTEGER`, `REAL`, `CHAR`, `BOOLEAN`, `STRING`, `TEXT` and `INTERACTIVE`
named by the compiler itself (finding 22). 1.3 adds two more, `BYTESTREAM`
and `WORDSTREAM`.

Every compiler option is accounted for, including the four letters no
manual documents: `$D` emits a `BPT` before each statement, `$F`
byte-swaps the code it generates, `$T` drops fifteen named built-ins to
save symbol-table space, and `$E` — undocumented anywhere, recovered from
the binary alone — lets a unit's implementation part own file variables
(finding 24).

The Apple Pascal 1.3 manual (finding 23) settles the lex-level convention,
confirms that a function's parameter area includes its result slot, and
corrects the lifter's reading of `CGP`. Cross-reading it against
`COMPOPTI.1` names the whole compiler-option block — `{$R-}`, `{$G+}` and
the rest — and shows that `SYSTEM.COMPILER` itself was compiled with range
checking off but *not* at the system lexical level.

**All 287 procedures across the two releases lift to structured
pseudo-Pascal** with the evaluation stack fully tracked, and **201 of them
come out with no `goto` at all** — real `if`/`while`/`repeat`/`case`
(`analysis/lifted/`). `tools/show.py SEGMENT.N` prints a procedure's
p-code listing; `tools/liftproc.py SEGMENT.N` prints its lifted form:

```
  L5 := G1^[G14];
  L4 := 0;  L3 := 0;
  while ((L5 in {48,49,50,51,52,53,54,55,56,57}) and (L4 < 4)) do begin
    L3 := ((L3*10)+(L5-48));       { 48 is '0' -- the number scanner }
    L4 := (L4+1);
    L5 := G1^[(G14+L4)];
  end;
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
