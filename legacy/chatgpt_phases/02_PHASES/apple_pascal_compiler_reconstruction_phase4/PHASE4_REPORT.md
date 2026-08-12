# Apple Pascal Compiler Reconstruction — Phase 4

## Focus: COMPINIT child procedures 9 and 10

The prior pass identified these as small routines. This pass deliberately
keeps them byte-exact and avoids assigning Pascal names without sufficient
evidence.

The procedure metadata is recovered from the JTAB/procedure pointer structure,
following TommyGoog's documented method. Tommy describes reading the procedure
count from the end of a segment, locating the JTAB for a selected procedure,
then using the JTAB to find entry/exit addresses and walk P-code. This is the
same architecture used here.

### Why P9/P10 matter

COMPINIT procedure 1 begins by invoking procedures 9 and 10. Their small
bodies make them useful candidates for identifying compiler-state operations,
but their parameter areas mean they should not automatically be classified as
simple initialization procedures.

The correct next step is caller/callee correlation:
- identify every call to P9/P10;
- identify the stack values immediately preceding each call;
- determine whether those values are addresses, scalar values, or records;
- compare P9/P10 in Apple Pascal 1.1 and 1.3;
- then map the referenced compiler-global offsets.

### Reconstruction rule

No semantic variable name is promoted to a source-level name until supported
by either:
1. a matching UCSD source construct,
2. repeated consistent use in Apple compiler code, or
3. a compile-and-P-code equivalence test.

This avoids the common reverse-engineering failure mode of producing plausible
but unverifiable Pascal.

### Important external validation

TommyGoog's Wizardry re-engineering work explicitly describes the DeCompiler
workflow: load the selected segment, locate the procedure, display its JTAB,
then walk the P-code with a large opcode dispatch. His later work uses
reconstructed Pascal and compares newly generated P-code with the historical
code. citeturn0search1turn0search2

The supplied Apple Pascal documentation independently establishes that
{$U-} is system mode and that it was used to compile SYSTEM.COMPILER itself.

## Deliverable

This package contains:
- complete COMPINIT procedure metadata for Apple Pascal 1.1;
- exact raw bodies for P9 and P10;
- a procedure map;
- this reconstruction report.

Next target: build a fully validated P-code decoder for P9/P10, then trace their
call sites in P1/P2/P3/etc. before assigning source-level semantics.
