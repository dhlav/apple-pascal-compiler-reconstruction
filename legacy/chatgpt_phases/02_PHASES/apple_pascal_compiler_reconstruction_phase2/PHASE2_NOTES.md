# Apple Pascal Compiler Reconstruction — Phase 2

Target: Apple Pascal 1.1 SYSTEM.COMPILER / COMPINIT procedure 1.

Recovered metadata:
- Segment 7: COMPINIT
- Procedure 1
- Entry $0A46
- Exit $0C71
- Data size 518 bytes
- Parameter size 0
- Lexical level 1

Initial P-code was decoded and anchored with the compiler identification
string.  The Pascal reconstruction is deliberately conservative; unknown
compiler-global variables are not given invented semantic names.

Next work:
1. Complete opcode decoding for COMPINIT.
2. Recover all branch targets and basic blocks.
3. Map data references against the compiler's global data area.
4. Compare COMPINIT 1.1 against 1.3.
5. Cross-reference matching structures against UCSD Pascal II.0 source.
6. Produce source reconstruction only where semantics are supported.
