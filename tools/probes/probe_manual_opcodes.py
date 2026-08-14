"""Does the decoder's opcode table agree with Apple's own?

`tools/a2pascal/pcode.py` was built from Hyde's *P-Source* and John Brooks'
1.4 interpreter, corrected twice by semantic probes against the binaries
(finding 7). None of that was vendor documentation.

Part IV, Chapter 4 of the Apple II Pascal 1.3 manual *is* vendor
documentation: "The P-Machine Instruction Set", IV-57..IV-76, which gives
every opcode by decimal number with its parameter list, and then repeats
the whole thing as "Table 4-1. P-Codes in Numerical Order". The table below
is transcribed from those pages -- it is Apple's table, not ours -- and
this probe holds the decoder against it.

Two things make the check worth running rather than assuming:

  * the decoder's numbers came from a third-party book and an unofficial
    reinterpretation of a later interpreter, and two of them were wrong
    when they were first written down;
  * a mnemonic can agree while the *parameter list* does not, and the
    parameter list is what decides where the next instruction starts.

Finding 25.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.pcode import OPCODES, decode

# --- Apple II Pascal 1.3 manual, IV-62..IV-76 ------------------------------
#
# decimal opcode -> (mnemonic, parameters as the manual writes them).
# `<data>` and `<chars>` are the manual's own notation for an inline block.
MANUAL: dict[int, tuple[str, tuple[str, ...]]] = {
    128: ("ABI", ()),      129: ("ABR", ()),      130: ("ADI", ()),
    131: ("ADR", ()),      132: ("LAND", ()),     133: ("DIF", ()),
    134: ("DVI", ()),      135: ("DVR", ()),      136: ("CHK", ()),
    137: ("FLO", ()),      138: ("FLT", ()),      139: ("INN", ()),
    140: ("INT", ()),      141: ("LOR", ()),      142: ("MODI", ()),
    143: ("MPI", ()),      144: ("MPR", ()),      145: ("NGI", ()),
    146: ("NGR", ()),      147: ("LNOT", ()),     148: ("SRS", ()),
    149: ("SBI", ()),      150: ("SBR", ()),      151: ("SGS", ()),
    152: ("SQI", ()),      153: ("SQR", ()),      154: ("STO", ()),
    155: ("IXS", ()),      156: ("UNI", ()),      157: ("LDE", ("UB", "B")),
    158: ("CSP", ("UB",)), 159: ("LDCN", ()),     160: ("ADJ", ("UB",)),
    161: ("FJP", ("SB",)), 162: ("INC", ("B",)),  163: ("IND", ("B",)),
    164: ("IXA", ("B",)),  165: ("LAO", ("B",)),
    166: ("LSA", ("UB", "<chars>")),
    167: ("LAE", ("UB", "B")),
    168: ("MOV", ("B",)),  169: ("LDO", ("B",)),  170: ("SAS", ("UB",)),
    171: ("SRO", ("B",)),
    # "W1,W2,<case table>,W3" -- the decoder folds the whole block into one
    # composite operand, so it is compared by name only.
    172: ("XJP", ("<case>",)),
    173: ("RNP", ("DB",)), 174: ("CIP", ("UB",)), 175: ("EQU", ("UB",)),
    176: ("GEQ", ("UB",)), 177: ("GRT", ("UB",)),
    178: ("LDA", ("DB", "B")),
    179: ("LDC", ("UB", "<data>")),
    180: ("LEQ", ("UB",)), 181: ("LES", ("UB",)),
    182: ("LOD", ("DB", "B")),
    183: ("NEQ", ("UB",)),
    184: ("STR", ("DB", "B")),
    185: ("UJP", ("SB",)), 186: ("LDP", ()),      187: ("STP", ()),
    188: ("LDM", ("UB",)), 189: ("STM", ("UB",)), 190: ("LDB", ()),
    191: ("STB", ()),
    192: ("IXP", ("UB", "UB")),
    193: ("RBP", ("DB",)), 194: ("CBP", ("UB",)), 195: ("EQUI", ()),
    196: ("GEQI", ()),     197: ("GRTI", ()),     198: ("LLA", ("B",)),
    199: ("LDCI", ("W",)), 200: ("LEQI", ()),     201: ("LESI", ()),
    202: ("LDL", ("B",)),  203: ("NEQI", ()),     204: ("STL", ("B",)),
    205: ("CXP", ("UB", "UB")),
    206: ("CLP", ("UB",)), 207: ("CGP", ("UB",)),
    208: ("LPA", ("UB", "<chars>")),
    209: ("STE", ("UB", "B")),
    213: ("BPT", ("B",)),  214: ("XIT", ()),      215: ("NOP", ()),
}

# The manual's parameter names against the decoder's operand-kind constants.
KIND = {
    "UB": "ub", "SB": "sb", "DB": "db", "B": "big", "W": "w",
    "<chars>": None,      # folded into the decoder's "str" operand
    "<data>": None,       # folded into the decoder's "ldc" operand
}

# Where the decoder deliberately folds a manual parameter list into one
# composite operand, because the block is variable-length and has to be
# consumed as a unit.
COMPOSITE = {
    "LSA": ("str",), "LPA": ("str",), "LDC": ("ldc",), "XJP": ("xjp",),
    # EQU and friends carry the type code as UB, and the manual gives the
    # byte-array and word forms (UB = 10, 12) an extra B. The decoder reads
    # the type code and then conditionally the B, which is one operand kind.
    "EQU": ("cmp",), "NEQ": ("cmp",), "LEQ": ("cmp",),
    "LES": ("cmp",), "GEQ": ("cmp",), "GRT": ("cmp",),
}

# The manual's short-form ranges, IV-62..IV-67 and Table 4-1.
SHORT = [
    (0, 127, "SLDC", 0),      # SLDC_0 .. SLDC_127, value = opcode
    (216, 231, "SLDL", 1),    # SLDL_1 .. SLDL_16
    (232, 247, "SLDO", 1),    # SLDO_1 .. SLDO_16
    (248, 255, "SIND", 0),    # SIND_0 .. SIND_7
]


def expected_kinds(mnem: str, params: tuple[str, ...]) -> tuple[str, ...]:
    if mnem in COMPOSITE:
        return COMPOSITE[mnem]
    return tuple(k for k in (KIND[p] for p in params) if k is not None)


def main() -> int:
    bad, notes = [], []

    for op, (mnem, params) in sorted(MANUAL.items()):
        entry = OPCODES.get(op)
        if entry is None:
            bad.append(f"${op:02X} ({op}): manual says {mnem}, "
                       f"decoder has no entry")
            continue
        got_mnem, got_kinds = entry[0], tuple(entry[1])
        if got_mnem != mnem:
            bad.append(f"${op:02X} ({op}): manual says {mnem}, "
                       f"decoder says {got_mnem}")
            continue
        want = expected_kinds(mnem, params)
        if got_kinds != want:
            bad.append(f"${op:02X} {mnem}: manual parameters "
                       f"{','.join(params) or '-'} -> {want}, "
                       f"decoder has {got_kinds}")

    # The one-byte forms are not in OPCODES; the decoder special-cases them
    # before the table lookup, so drive it through `decode`.
    for lo, hi, mnem, base in SHORT:
        for op in (lo, hi):
            ins = decode(bytes([op]), 0)
            want_val = base + (op - lo)
            if ins.mnemonic != mnem or ins.operands != [want_val]:
                bad.append(f"${op:02X} ({op}): manual says {mnem}_{want_val}, "
                           f"decoder says {ins.text}")

    extra = sorted(set(OPCODES) - set(MANUAL))
    if extra:
        notes.append("in the decoder, not in the manual's table: " +
                     ", ".join(f"${op:02X} {OPCODES[op][0]}" for op in extra))

    if bad:
        print("\n".join(bad))
        return 1
    print(f"{len(MANUAL)} numbered opcodes + 4 short-form ranges agree with "
          f"the manual, mnemonic and parameters")
    for n in notes:
        print("  note: " + n)
    print("manual-opcodes-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
