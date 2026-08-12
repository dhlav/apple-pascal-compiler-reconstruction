# APPLE PASCAL COMPILER RECONSTRUCTION — CLAUDE HANDOFF

## User request

The user wants the actual Apple Pascal compiler source reconstructed as far
as possible. They supplied original Apple Pascal disk images and the UCSD
Pascal II.0 source disk. They specifically pointed out TommyGoog's forum work
on reverse-engineering Apple Pascal P-code back into Pascal.

The user wants this project continued by a stronger model, so preserve the
distinction between verified binary facts, source-derived facts, and inference.

## ORIGINAL INPUTS

00_ORIGINAL_INPUTS contains:

- Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk
  SHA256: 88b67683f3ac645a91e0139d987a8b8fd8725b6b4045d38eb272e4cb91341adf
- Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk
  SHA256: 873b9e41c40cef539c06b4f5e2dafe475b0fec5c52c71e241c2cf8ad0f6f05a9
- ii0src.sdk
  SHA256: 1dfab0b03dbd8b72c863bf6ce805e4493ccad70aa6dee78d493a310603ef3015
- Undocumented Secrets of Apple Pascal.html
  SHA256: 4416a361644a16cfba9eea5eb1030e5a3146f169e29a847444b25758d985184c

## WHAT HAS ACTUALLY BEEN EXTRACTED

SYSTEM.COMPILER was extracted from both Apple Pascal disk images.

Apple Pascal 1.1:
- SYSTEM.COMPILER = 75 blocks = 38,400 bytes
- extracted compiler binary is in Phase 1/3

Apple Pascal 1.3:
- SYSTEM.COMPILER = 78 blocks = 39,936 bytes

The compiler's segment organization is:

1  PASCALCO   native 6502
7  COMPINIT   P-code
8  DECLARAT   P-code
9  BODYPART   P-code
10 ROUTINE    P-code
11 STATEMEN   P-code
12 CASESTAT   P-code
13 FORSTATE   P-code
14 BODY1      P-code
15 BODY3      P-code
16 WRITELIN   P-code
17 UNITPART   P-code
18 COMPOPTI   P-code
19 NUMSTRIN   P-code
20 FINISHUP   P-code

The first segment is native 6502. The remaining compiler phases are P-code.

## IMPORTANT CORRECTION

An earlier phase incorrectly stated that COMPINIT contained 10 procedures.

The corrected JTAB walk finds 29 procedures in COMPINIT.

The corrected procedure map is in:
  02_PHASES/apple_pascal_compiler_reconstruction_phase5/
  COMPINIT-PROCEDURE-MAP-CORRECTED.txt

Treat that as the current map.

The procedure order is not the same as entry-address order. Do not sort
procedures by entry address when assigning procedure numbers.

## CURRENT COMPINIT MAP

1  entry $10E0  exit $1122  data 2444 params 4 lex 0
2  entry $0000  exit $0172  data 184  params 2 lex 1
3  entry $0184  exit $025C  data 2 params 0 lex 1
4  entry $0268  exit $0361  data 106 params 0 lex 1
5  entry $036E  exit $03C7  data 6 params 2 lex 1
6  entry $04D2  exit $0751  data 10 params 0 lex 1
7  entry $0766  exit $077F  data 0 params 4 lex 1
8  entry $078C  exit $0821  data 4 params 4 lex 1
9  entry $0830  exit $0864  data 2 params 6 lex 1
10 entry $0870  exit $0881  data 0 params 6 lex 1
11 entry $088E  exit $08AB  data 0 params 2 lex 1
12 entry $03D6  exit $046C  data 0 params 0 lex 1
13 entry $0C6A  exit $0CA9  data 4 params 6 lex 1
14 entry $08B8  exit $08C6  data 0 params 8 lex 1
15 entry $08D4  exit $08EC  data 0 params 6 lex 1
16 entry $08F8  exit $0906  data 0 params 6 lex 1
17 entry $0912  exit $091B  data 0 params 6 lex 1
18 entry $0928  exit $0AD0  data 10 params 12 lex 1
19 entry $0AE4  exit $0C4F  data 12 params 8 lex 1
20 entry $0CB6  exit $0CBF  data 0 params 2 lex 1
21 entry $0CCC  exit $0CF6  data 2 params 2 lex 1
22 entry $0D02  exit $0D73  data 6 params 2 lex 1
23 entry $0D82  exit $0DDC  data 4 params 0 lex 1
24 entry $0E48  exit $0FD3  data 4 params 8 lex 1
25 entry $0FE8  exit $1009  data 0 params 0 lex 1
26 entry $0478  exit $04BF  data 2 params 2 lex 1
27 entry $0DEA  exit $0E3C  data 2 params 2 lex 1
28 entry $1092  exit $109E  data 0 params 0 lex 1
29 entry $1076  exit $107A  data 0 params 0 lex 1

## TOMMYGOOG METHODOLOGY

Use TommyGoog's work as the methodological reference, especially:
https://groups.google.com/g/comp.sys.apple2/c/2oDJTbQaJWU

His process:
1. Locate segment.
2. Read procedure count from end.
3. Recover JTAB/procedure metadata.
4. Walk P-code.
5. Infer Pascal control structures and declarations.
6. Compile reconstructed Pascal with Apple Pascal 1.1.
7. Compare generated P-code with original.
8. Iterate until equivalent.

Do not declare source reconstruction successful just because the output is
readable. The desired endpoint is code-equivalence or very close binary/P-code
equivalence.

## P9/P10 CURRENT STATUS

COMPINIT P9:
- entry $0830
- exit $0864
- data 2
- params 6
- lex 1

COMPINIT P10:
- entry $0870
- exit $0881
- data 0
- params 6
- lex 1

Exact raw P9/P10 bodies are in Phase 4/5.

The current interpretation is intentionally conservative:
- both have 6-byte parameter areas;
- P9 performs indirect/reference/field operations;
- P10 performs a comparison/update pattern and invokes an external/global
  procedure;
- exact Pascal types and semantic names are NOT yet established.

Do not promote guessed names to source-level declarations until call-site
analysis supports them.

## NEXT TECHNICAL TASK

1. Find every call to procedure 9 and procedure 10 in COMPINIT.
2. Decode the P-code immediately preceding each call.
3. Determine whether each argument is a value or address.
4. Infer parameter types from the operations performed.
5. Reconstruct P9/P10.
6. Verify their callers.
7. Then move through COMPINIT procedures 2-8 and 11-29.
8. Build a compiler-global data map.
9. Cross-reference the UCSD II.0 source.
10. Compare Apple Pascal 1.1 vs 1.3 to isolate Apple-specific changes.
11. Only then begin a source-level compiler module reconstruction.
12. Eventually compile under Apple Pascal 1.1 and compare generated P-code.

## FILES TO READ FIRST

1. 01_RESEARCH/EXTERNAL_REFERENCES.md
2. 00_ORIGINAL_INPUTS/Undocumented Secrets of Apple Pascal.html
3. 00_ORIGINAL_INPUTS/ii0src.sdk
4. 02_PHASES/apple_pascal_compiler_reconstruction_phase5/
   COMPINIT-PROCEDURE-MAP-CORRECTED.txt
5. 02_PHASES/apple_pascal_compiler_reconstruction_phase5/
   COMPINIT-P09-P10-structural-analysis.txt
6. 03_WORKING_ARTIFACTS/compinit_p1_listing_correct.txt
7. 03_WORKING_ARTIFACTS/decode_compinit.py

Then inspect the original .dsk images directly if needed.

## IMPORTANT CAUTIONS

- Earlier phase reports contain exploratory errors. Phase 5 corrects the
  biggest one: COMPINIT has 29 procedures.
- Some opcode names/lengths in early scripts are provisional. Prefer TommyGoog's
  published opcode/decompiler descriptions and the Apple Pascal technical
  reference over an old heuristic table.
- Do not assume UCSD II.0 source is identical to Apple Pascal source.
- Do not assume segment numbers equal directory-entry numbers.
- Do not infer source-level names merely from byte offsets.
- Preserve exact raw binary artifacts; they are the evidence.
- Keep a distinction between:
    VERIFIED BINARY FACT
    VERIFIED SOURCE FACT
    STRONG INFERENCE
    SPECULATION
- Record every newly established mapping so later work can be audited.

## PROJECT END STATE

Ideally produce:

apple_pascal_reconstructed/
  source/
    COMPINIT.TEXT
    DECLARAT.TEXT
    BODYPART.TEXT
    ROUTINE.TEXT
    STATEMEN.TEXT
    CASESTAT.TEXT
    FORSTATE.TEXT
    BODY1.TEXT
    BODY3.TEXT
    WRITELIN.TEXT
    UNITPART.TEXT
    COMPOPTI.TEXT
    NUMSTRIN.TEXT
    FINISHUP.TEXT
    PASCALCO.IAS

  analysis/
    compiler_global_map.md
    procedure_maps/
    pcode_disassembly/
    1.1_vs_1.3_diff/

  validation/
    reconstructed_system_compiler/
    generated_pcode/
    original_vs_generated/

A functionally equivalent source reconstruction is more valuable than a
cosmetic decompilation.
