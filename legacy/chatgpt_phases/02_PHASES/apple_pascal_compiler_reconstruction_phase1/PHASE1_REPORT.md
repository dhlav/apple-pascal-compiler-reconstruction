# Apple Pascal Compiler Reconstruction — Phase 1

We have now extracted and structurally decoded SYSTEM.COMPILER from Apple Pascal 1.1 and 1.3.

## 1.1
SYSTEM.COMPILER = blocks 6..80, 75 blocks = 38,400 bytes.
COMPINIT has 10 procedures. Procedure 1: entry $0A46, exit $0C71, data size 518, params 0, lexical level 1.

## 1.3
SYSTEM.COMPILER = blocks 56..133, 78 blocks = 39,936 bytes.

## Segment architecture
1 PASCALCO (6502 native)
7 COMPINIT
8 DECLARAT
9 BODYPART
10 ROUTINE
11 STATEMEN
12 CASESTAT
13 FORSTATE
14 BODY1
15 BODY3
16 WRITELIN
17 UNITPART
18 COMPOPTI
19 NUMSTRIN
20 FINISHUP

The P-code procedure tables have been recovered for every P-code segment.

## Reconstruction strategy
The next step is to annotate COMPINIT procedure 1 instruction-by-instruction, then compare the 1.1 and 1.3 versions and correlate the resulting compiler phases with UCSD Pascal II.0 source. TommyGoog's method is our validation model: reconstruct source, compile it with Apple Pascal 1.1, and compare generated P-code against the historical code.

The supplied Neil Parker document confirms Apple Pascal source was not publicly released, while UCSD Pascal II.0 source was released; it also confirms Apple used {$U-} system mode to compile SYSTEM.COMPILER itself.
