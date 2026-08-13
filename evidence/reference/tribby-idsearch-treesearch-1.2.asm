;---------------------------------------------------
; Replacement for TREESEARCH and IDSEARCH routines,
; which were dropped from Apple Pascal in version
; 1.3.
;
; Disassembled from 1.2 version of SYSTEM.APPLE
; by Dave Tribby
;---------------------------------------------------

; Equates used by both routines...
RTN     .EQU 0          ; Holds return address

        .FUNC TreeSearch,3
        .TITLE "TREESEARCH Procedure"
;---------------------------------------------------
; Replacement for TREESEARCH function dropped from
; Pascal version 1.3. This code was disassembled
; from the Pascal 1.2 SYSTEM.APPLE, then turned into
; a callable subroutine by Dave Tribby beginning
; June 11, 1986.
;
; Functionality:
;   Search through a binary tree for an eight byte
;   token. Used by the compiler and other routines
;   for symbol table lookups.
;
; Declare in Pascal as
;   FUNCTION TreeSearch(RootPtr: WordRef;
;                       VAR NodePtr, Name): INTEGER;
;      EXTERNAL;
;   Where
;     RootPtr is a pointer to the root node of the
;       tree to be searched
;     NodePtr is a pointer variable to be updated
;       by TreeSearch
;     Name    is a PACKED ARRAY [1..8] OF CHAR
;       which contains the name to be searched for
;
; Functional return value:
;   0:  The Name passed has been found in the tree.
;       NodePtr now points to the node with the
;       specified name.
;   1:  The Name is not in the tree. If it is added
;       to the tree, it should be the right subnode
;       of the node pointed to by NodePtr.
;   -1: The Name is not in the tree. If it is added
;       to the tree, it should be the left subnode
;       of the node pointed to by NodePtr.
;---------------------------------------------------

; Page zero addresses...
RootPtr .EQU RTN+2
NodePtr .EQU RTN+4
Name    .EQU RTN+6

;---------------------------------------------------
; ---------- Start of Function TreeSearch ----------
;---------------------------------------------------
;
; Save the return address
;
        PLA
        STA RTN
        PLA
        STA RTN+1
;
; Since this is a Pascal-callable function, need
; to remove the 4 bytes of stack bias...
;
        PLA
        PLA
        PLA
        PLA
;
; Get the parameter addressess
;
        PLA
        STA Name
        PLA
        STA Name+1
        PLA
        STA NodePtr
        PLA
        STA NodePtr+1
        PLA
        STA RootPtr
        PLA
        STA RootPtr+1

;---------------------------------------------------

; Check the eight character array in the tree
; against the parameter.

ChkName LDX #8          ; Initialize char count
        LDY #255.       ;  and char pointer.

ChkChar DEX             ; Dec char number. If 0,
        BMI Return0     ;   return with "Found."
        INY             ; Inc char pointer.
        LDA @Name,Y     ; If tree value matches
        CMP @RootPtr,Y  ;  the parameter, check
        BEQ ChkChar     ;   next character.

        BMI NamLess

;---------------------------------------------------
; Name in tree is > the parameter.
;---------------------------------------------------

        LDY #8          ; If right link
        LDA @RootPtr,Y  ;  field in tree
        TAX             ;   is 0,
        INY
        LDA @RootPtr,Y
        CMP #0
        BNE ChkNxt1
        CPX #0
        BEQ Return1     ;     return "Insert on right."

; Set up to check the next node in the tree.
ChkNxt1 STX RootPtr
        STA RootPtr+1
        JMP ChkName


;---------------------------------------------------
; Name in tree is < the parameter.
;---------------------------------------------------

NamLess LDY #10.        ; If left link
        LDA @RootPtr,Y  ;  field in tree
        TAX             ;   is NIL,
        INY
        LDA @RootPtr,Y
        CMP #0
        BNE ChkNxt2
        CPX #0
        BEQ ReturnN1    ;   return "Insert on left."

; Set up to check the next node in the tree.
ChkNxt2 STX RootPtr
        STA RootPtr+1
        JMP ChkName


;---------------------------------------------------
; Parameter was found in the tree.
; Return TreeSearch functional value = 0
;---------------------------------------------------
;
Return0 LDA #0
        PHA
        PHA
        JMP GoBack


;---------------------------------------------------
; Parameter not in the tree, and should be inserted
;    on the left subnode of NodePtr.
; Return TreeSearch functional value = -1
;---------------------------------------------------
;
ReturnN1 LDA #255.
        PHA
        PHA
        JMP GoBack


;---------------------------------------------------
; Parameter not in the tree, and should be inserted
;    on the right subnode of NodePtr.
; Return TreeSearch functional value = 1
;---------------------------------------------------
;
Return1 LDA #0
        PHA
        LDA #1
        PHA


;---------------------------------------------------
; Go back to caller
;---------------------------------------------------
;
GoBack  LDY #0          ; Return value
        LDA RootPtr     ;  of last node
        STA @NodePtr,Y  ;   address in
        INY             ;    NodePtr
        LDA RootPtr+1   ;     parameter.
        STA @NodePtr,Y

        LDA RTN+1       ; Put return
        PHA             ;  address on
        LDA RTN         ;   stack, and
        PHA             ;    return.
        RTS


        .PROC IDSearch,2
        .TITLE "IDSEARCH Procedure"
;---------------------------------------------------
; Replacement for IDSEARCH procedure dropped from
; Pascal version 1.3. This code was disassembled
; from the Pascal 1.2 SYSTEM.APPLE by Dave Tribby.
;
; Declare in Pascal as
;   PROCEDURE IDSearch(VAR idrec, id);
;      EXTERNAL;
; where idrec and id have the form
;   TYPE
;      Alpha = PACKED ARRAY [1 .. 8] OF CHAR;
;   VAR
;      id: Alpha;
;      idrec: PACKED RECORD
;         offset: INTEGER;
;         val1: INTEGER;
;         val2: INTEGER;
;         name: Alpha;
;         END;   { idrec }
;---------------------------------------------------

VAL1    .EQU RTN+2
VAL2    .EQU VAL1+1
CHARS   .EQU VAL2+1     ; 8 bytes
NUM4CH  .EQU CHARS+8    ; # of entries for a starting character
ENTAD   .EQU NUM4CH+2   ; Address of table entry (2 bytes)
PARAM1  .EQU ENTAD+2    ; 1st parameter (2 bytes)
PNT     .EQU PARAM1+2   ; Pointer (2 bytes)

         PLA            ; Save
         STA RTN        ;  return
         PLA            ;   address
         STA RTN+1
         PLA
         TAY            ;     and
         PLA            ;      parameters'
         TAX            ;       addresses.
         PLA
         STA PARAM1
         PLA
         STA PARAM1+1

; Add offset (parameter 1) to address of parameter 2
; and store result in pointer.
         TYA
         LDY #0
         CLC
         ADC @PARAM1,Y
         STA PNT
         TXA
         INY
         ADC @PARAM1,Y
         STA PNT+1

         LDA #" "
         LDX #7
 $01     STA CHARS,X
         DEX
         BNE $01

         DEY
         LDA @PNT,Y     ; Get first character.
         CMP #"a"       ; If character
         BCC STCH1      ;  is between
         CMP #123.      ;   "a" and "z",
         BCS STCH1
         SEC
         SBC #32.       ;     upshift!

STCH1    STA CHARS      ; Store first char.


;   ------- Shift loop begins here -------
;       Note: Y-Reg (source pointer) = 0 at start
;             X-Reg (dest.  pointer) = 0 at start

SLOOP    INY            ; Bump character pointer.
         LDA @PNT,Y     ; Get next character.
         CMP #123.      ; If character
         BCS CHKNUM     ;  is between
         CMP #"a"       ;   "a" and "z",
         BCS UPSH       ;       upshift!

CHKNUM   CMP #"0"       ; Check for number.
         BCC CKALPH
         CMP #":"
         BCC ENDSL

CKALPH   CMP #"A"       ; Check for alpha/"_"
         BCC BUMPPTR    ; If not in range,
         CMP #"["       ;  end of token.
         BCC ENDSL
         CMP #"_"
         BNE BUMPPTR
         BEQ SLOOP      ; (Skip over "_")

UPSH     SBC #32.       ; Upshift

; End of shift loop. Store character.
ENDSL    INX            ; Increment dest pointer.
         CPX #8         ; If not beyond end,
         BCS SLOOP
         STA CHARS,X    ;  store in char array.
         BCC SLOOP

; Token has been parsed and upshifted. Add number
; of characters (in Y-reg) to parameter 1 and store.
BUMPPTR  DEY
         TYA
         LDY #0
         CLC
         ADC @PARAM1,Y
         STA @PARAM1,Y
         INY
         LDA @PARAM1,Y
         ADC #0
         STA @PARAM1,Y

; Use first character to access address table
         LDA CHARS
         ASL A
         TAY
         LDA ADRTBL-082,Y
         STA ENTAD        ; Get address from
         LDA ADRTBL-081,Y ;  table entry.
         STA ENTAD+1

         LDY #0         ; First value in table is
         LDA @ENTAD,Y   ;  # of symbols beginning
         STA NUM4CH     ;   with given character.

; See if upshifted symbol matches anything in the table.
LOADREG  LDX #0
         LDY #1
CMPSYM   INX
         INY
         LDA @ENTAD,Y
         CMP CHARS,X
         BEQ CHKEND

; Symbol does not match this table entry.
         DEC NUM4CH     ; Decrease alpha counter.
         BEQ NOTIN      ; If no more, no match in table.

         LDA ENTAD      ;  Point
         CLC            ;   to next
         ADC #10.       ;    table entry.
         STA ENTAD
         BCC ROLL
         INC ENTAD+1
ROLL     BNE LOADREG    ; Check next table entry.

CHKEND   CPX #7.        ; If not at end,
         BNE CMPSYM     ;  keep comparing.

; The symbol was found in the table.
         INY
         LDA @ENTAD,Y
         STA VAL1
         INY
         LDA @ENTAD,Y
         STA VAL2
         LDY #2
         LDA VAL1
         STA @PARAM1,Y
         INY
         LDA #0
         STA @PARAM1,Y
         INY
         LDA VAL2
         STA @PARAM1,Y
         INY
         LDA #0
         STA @PARAM1,Y
         BEQ ALLDONE


; The symbol is not in the table.
NOTIN    LDA #0
         LDY #2
         STA @PARAM1,Y
         INY
         STA @PARAM1,Y
         INY
         INY
         STA @PARAM1,Y
         DEY
         LDA #21.
         STA @PARAM1,Y

         LDY #14.
         LDX #7
$02      DEY
         LDA CHARS,X
         STA @PARAM1,Y
         DEX
         BPL $02

ALLDONE  LDA RTN+1
         PHA
         LDA RTN
         PHA
         RTS

ADRTBL  .WORD NUMA      ; Entries beginning with "A"
        .WORD NUMB      ; Entries beginning with "B"
        .WORD NUMC      ; Entries beginning with "C"
        .WORD NUMD      ; Entries beginning with "D"
        .WORD NUME      ; Entries beginning with "E"
        .WORD NUMF      ; Entries beginning with "F"
        .WORD NUMG      ; Entries beginning with "G"
        .WORD NUM0      ; NO Entries beginning with "H"
        .WORD NUMI      ; Entries beginning with "I"
        .WORD NUM0      ; NO Entries beginning with "J"
        .WORD NUM0      ; NO Entries beginning with "K"
        .WORD NUML      ; Entries beginning with "L"
        .WORD NUMM      ; Entries beginning with "M"
        .WORD NUMN      ; Entries beginning with "N"
        .WORD NUMO      ; Entries beginning with "O"
        .WORD NUMP      ; Entries beginning with "P"
        .WORD NUM0      ; NO Entries beginning with "Q"
        .WORD NUMR      ; Entries beginning with "R"
        .WORD NUMS      ; Entries beginning with "S"
        .WORD NUMT      ; Entries beginning with "T"
        .WORD NUMU      ; Entries beginning with "U"
        .WORD NUMV      ; Entries beginning with "V"
        .WORD NUMW      ; Entries beginning with "W"
        .WORD NUM0      ; NO Entries beginning with "X"
        .WORD NUM0      ; NO Entries beginning with "Y"
        .WORD NUM0      ; NO Entries beginning with "Z"

NUM0     .BYTE 001,040,023
NUMA     .BYTE 2
         .ASCII  "AND     "
         .BYTE 027,2
         .ASCII  "ARRAY   "
         .BYTE 02C,0
NUMB     .BYTE 1
         .ASCII  "BEGIN   "
         .BYTE 013,0
NUMC     .BYTE 2
         .ASCII  "CASE    "
         .BYTE 015,0
         .ASCII  "CONST   "
         .BYTE 01C,0
NUMD     .BYTE 3
         .ASCII  "DO      "
         .BYTE 006,0
         .ASCII  "DIV     "
         .BYTE 027,3
         .ASCII  "DOWNTO  "
         .BYTE 008,0
NUME     .BYTE 3
         .ASCII  "END     "
         .BYTE 009,0
         .ASCII  "ELSE    "
         .BYTE 00D,0
         .ASCII  "EXTERNAL"
         .BYTE 035,0
NUMF     .BYTE 4
         .ASCII  "FOR     "
         .BYTE 018,0
         .ASCII  "FUNCTION"
         .BYTE 020,0
         .ASCII  "FILE    "
         .BYTE 02E,0
         .ASCII  "FORWARD "
         .BYTE 022,0
NUMG     .BYTE 1
         .ASCII  "GOTO    "
         .BYTE 01A,0
NUMI     .BYTE 4
         .ASCII  "IF      "
         .BYTE 014,0
         .ASCII  "IN      "
         .BYTE 029,0E
         .ASCII  "IMPLEMEN"
         .BYTE 034,0
         .ASCII  "INTERFAC"
         .BYTE 033,0
NUML     .BYTE 1
         .ASCII  "LABEL   "
         .BYTE 01B,0
NUMM     .BYTE 1
         .ASCII  "MOD     "
         .BYTE 027,4
NUMN     .BYTE 1
         .ASCII  "NOT     "
         .BYTE 026,0
NUMO     .BYTE 2
         .ASCII  "OF      "
         .BYTE 00B,0
         .ASCII  "OR      "
         .BYTE 028,7
NUMP     .BYTE 3
         .ASCII  "PROCEDUR"
         .BYTE 01F,0
         .ASCII  "PACKED  "
         .BYTE 02B,0
         .ASCII  "PROGRAM "
         .BYTE 021,0
NUMR     .BYTE 2
         .ASCII  "REPEAT  "
         .BYTE 016,0
         .ASCII  "RECORD  "
         .BYTE 02D,0
NUMS     .BYTE 2
         .ASCII  "SET     "
         .BYTE 02A,0
         .ASCII  "SEGMENT "
         .BYTE 021,0
NUMT     .BYTE 3
         .ASCII  "THEN    "
         .BYTE 00C,0
         .ASCII  "TO      "
         .BYTE 007,0
         .ASCII  "TYPE    "
         .BYTE 01D,0
NUMU     .BYTE 3
         .ASCII  "UNTIL   "
         .BYTE 00A,0
         .ASCII  "USES    "
         .BYTE 031,0
         .ASCII  "UNIT    "
         .BYTE 032,0
NUMV     .BYTE 1
         .ASCII  "VAR     "
         .BYTE 01E,0
NUMW     .BYTE 2
         .ASCII  "WHILE   "
         .BYTE 017,0
         .ASCII  "WITH    "
         .BYTE 019,0

        .END
