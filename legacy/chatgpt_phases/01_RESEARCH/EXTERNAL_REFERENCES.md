# Research and external references

The reconstruction project has used these external sources. The URLs are
included so another model can independently retrieve and verify them.

## TommyGoog / Apple II Pascal P-code reverse engineering

1. Re-engineered: Wizardry III, Legacy of Llylgamyn
https://groups.google.com/g/comp.sys.apple2/c/2oDJTbQaJWU

This is the primary methodology source. TommyGoog describes his WIZ4
Apple Pascal P-code decompiler, JTAB/procedure analysis, conversion of
P-code to Pascal, and validation by recompiling the reconstructed Pascal.

2. Wizardry re-engineering — decompiler/P-code discussion
https://groups.google.com/g/comp.sys.apple2/c/aI5ob1mLUwY/m/HhH1edM3gzkJ

3. Wizardry re-engineering — P-code examples and structural issues
https://groups.google.com/g/comp.sys.apple2/c/2oDJTbQaJWU/m/Vge7HkIcYYwJ

Important observations from TommyGoog:
- Apple Pascal code files contain segments and procedures.
- The final byte of a segment gives the procedure count.
- The JTAB/procedure pointer structure gives data size, parameter size,
  entry/exit addresses, procedure number and lexical level.
- P-code is stack based.
- VAR parameters and indirect access must be inferred from generated code.
- Different Pascal source constructs can generate identical P-code.
- His validation standard was to compile reconstructed Pascal with
  Apple Pascal 1.1 and compare the generated P-code with the historical
  binary.
- He specifically wrote a Pascal P-code disassembler/decompiler called WIZ4.

## Neil Parker / Apple Pascal reverse engineering

The supplied HTML file:
  Undocumented Secrets of Apple Pascal.html

Neil Parker's page:
https://llx.com/Neil/a2/passec.html

This documents that Apple Pascal source was not publicly released, while
UCSD Pascal II.0 source was released, and discusses Apple-specific compiler
behavior including system compilation mode.

## UCSD II.0 source

The supplied file:
  ii0src.sdk

Size:
  40,464 bytes

This is the UCSD Pascal II.0 source disk used as the source-side comparison
artifact.

## Apple Pascal disk images

The supplied originals:
  Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk
  Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk

The APPLE2 disk contains SYSTEM.COMPILER.

## Important: don't blindly trust earlier phase conclusions

Phase 1-4 contain exploratory work and some incorrect assumptions that were
later corrected. Phase 5 documents the important correction: COMPINIT contains
29 procedures, not 10. The latest corrected procedure map should be treated
as authoritative over earlier abbreviated maps.

The Phase 4/5 P9/P10 semantic analysis is also deliberately conservative.
It is not yet a source-equivalent reconstruction.

## Current project goal

Reconstruct the Apple Pascal compiler source as faithfully as possible,
preferably to the point where reconstructed Pascal can be compiled with
Apple Pascal 1.1 and produce P-code matching the historical SYSTEM.COMPILER.

The ultimate goal is preservation/reconstruction, not merely a readable
pseudocode decompilation.
