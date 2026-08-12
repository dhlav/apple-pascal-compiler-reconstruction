# Apple Pascal Compiler Reconstruction — Phase 3

This pass uses TommyGoog's published JTAB algorithm against the supplied
binaries.

## COMPINIT procedure 1

1.1: data=518, params=0, enter=$0A46, exit=$0C71, proc=1, lex=1
1.3: data=608, params=0, enter=$0BB8, exit=$0F8D, proc=1, lex=1

The 1.1 procedure starts with CLP 9 and CLP 10, clears offsets $4D and $08,
tests compiler state at $31, and contains the literal "Apple Pascal Compiler
[1.1]". The complete raw/annotated disassemblies are included.

Important: unknown opcodes are not assigned speculative meanings.

Next: reconstruct child procedures 9 and 10, then the other COMPINIT children,
using their global-offset side effects and the 1.1/1.3 differential.
