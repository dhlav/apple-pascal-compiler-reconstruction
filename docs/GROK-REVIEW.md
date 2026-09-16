# Grok Review (2026-09-15)

Branch: `Grok-Review`. Started from Claude's handoff at `docs/HANDOFF.md`
(commit `02fc9fc` and parents).

## What was re-verified

| check | result |
|---|---|
| `python tools/build_all.py` | **EXIT 0** — every STEP, including all whole-file and diskset probes |
| Disk set account | **359,323 of 430,080** identical; **70,757** differ; EXPECTED sums exactly |
| Carry control | building every region from Apple's bytes reproduces Apple's images |
| `evidence/` | clean (`git status --short evidence/` empty) after the run |
| Assembler acceptance source | `acceptance/.../ASSMBLER.text` == `src/.../ASSMBLER.text` |
| Negative control | flipping one byte of `LIBASM.CODE` / `LIBCOMP.CODE` breaks equality |

In-scope (excluding archived 64K pair): **351,873 of 374,784**, matching
PLAN / DISKSET / HANDOFF / finding 290d.

## Acceptance claim status

**Whole-file identical (probes + diskset differ 0):**
`SYSTEM.COMPILER`, `SYSTEM.ASSMBLER` (PASCALIO borrowed), `SYSTEM.LINKER`,
`LIBRARY.CODE`, `SYSTEM.FILER`, `SYSTEM.EDITOR`, `128K.APPLE`,
`SYSTEM.CHARSET`, `6502.OPCODES`, the ten text files.

**Named remainders:** each EXPECTED entry in `probe_diskset.py` matched on
this run (SETUP 3943, LIBRARY 16234, 128K.PASCAL 571, etc.).

**`SYSTEM.LIBRARY` accepted exception:** still enforced as 16,234 in place
and 16,417 slot-aligned in `probe_library_units.py`; do not reopen without
new evidence (HANDOFF §6.1).

## Changes made on this branch

1. **`tools/probes/probe_assembler_whole.py`** — require kept
   `ASSMBLER.text` to equal `src/`; add a one-byte mutant so the whole-file
   compare cannot pass on length alone.
2. **`tools/probes/probe_compiler_whole.py`** — one-byte mutant, plus a
   source lock of `PASCALCO.text` and every `phases/*.text` kept under
   `acceptance/2026-09-12-compiler-librarian/source/` against
   `src/pascal/1.3/` (BODY13 stays generated; the phase inputs are the
   lock).
3. **`docs/HANDOFF.md`** — §4 no longer overstates `probe_acceptance.py`
   (FORMATTER-only); documents which probes source-lock, and that
   FINDINGS §287/§289 headlines are superseded by 290d for live totals.

## Gaps left open (documented, not fixed)

- **Finding 290 buffer fragments** beyond LONGINTI/`DECOPS`: TURTLEGR
  `{$endc}` / path strings are FINDINGS prose, not probe assertions.
- **`mkimages.py`:** not part of `build_all.py`. SYSHD/SRCHD file-count
  logic matches HANDOFF §6.4 (35 / 73); runtime boot and UTURTLE-from-SRCHD
  compile remain as in the handoff (unverified in CI).
- **LIBMAP "311 slack"** in prose is the *difference* count; the tail past
  SEGEND is 332 bytes with 21 matching — differ ≠ length.

## Verdict

The reconstruction's acceptance requirements hold under a full
`build_all.py` re-run. The probe gaps closed on this branch are the
assembler source lock and mutant checks; remaining items are naming work
and documented exceptions, not unbalanced disk accounts.
