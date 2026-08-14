"""Is the emitters' opcode argument really `opcode - 128`?

`BODYPART.5:GEN1(op, arg)` begins `GENBYTE(op + 128)`, so its first
argument names a p-code instruction in the range $80..$FF. If that reading
is right, two things follow that the binary can fail:

  * every literal `op` passed to GEN1 must be an opcode that takes
    exactly *one* operand -- GEN1 emits exactly one -- and only 37 of the
    128 candidates are;
  * the `op + 20` adjustment inside GEN2, which it applies when the
    operand it would emit is the degenerate one (lex level 0, or an integer
    comparison), must land on the short form of the *same* instruction.
    That is a claim about pairs of opcodes 20 apart, and the p-machine's
    encoding either has that structure or it does not.

Both are checked here against the decoder's own opcode table, which was
built from Hyde and Brooks without reference to any of this. Finding 24c.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.pcode import OPCODES

ROOT = Path(__file__).resolve().parent.parent.parent

# The pairs GEN2's `+20` has to produce: a two-operand addressing or
# comparison instruction, and the one-operand form it collapses to.
SHORT_FORM = {
    "LDA": "LLA", "LDC": "LDCI", "LOD": "LDL", "STR": "STL",
    "EQU": "EQUI", "GEQ": "GEQI", "GRT": "GRTI",
    "LEQ": "LEQI", "LES": "LESI", "NEQ": "NEQI",
}


def main():
    bad = []

    # (1) +20 is the short-form rule, over the whole opcode table.
    for big, short in SHORT_FORM.items():
        n = next((k for k, v in OPCODES.items() if v[0] == big), None)
        if n is None:
            bad.append(f"{big}: not in the opcode table")
            continue
        got = OPCODES.get(n + 20)
        if not got or got[0] != short:
            bad.append(f"{big} (${n:02X}) + 20 = ${n + 20:02X} is "
                       f"{got[0] if got else 'unassigned'}, expected {short}")

    # (2) every literal opcode argument to GEN1 is a one-operand opcode.
    one_operand = {k for k, v in OPCODES.items() if len(v[1]) == 1}
    for ver in ("1.1", "1.3"):
        path = ROOT / "analysis" / "lifted" / f"SYSTEM.COMPILER-{ver}.pas.txt"
        text = path.read_text()
        lits = {int(m) for m in
                re.findall(r"BODYPART\.\d+:GEN1\((\d+),", text)}
        if not lits:
            bad.append(f"{ver}: no GEN1 call sites found -- has the "
                       f"procedure been renamed, or the listing not rebuilt?")
            continue
        off = sorted(n for n in lits if n + 128 not in one_operand)
        if off:
            bad.append(f"{ver}: GEN1 arguments that are not one-operand "
                       f"opcodes: " +
                       ", ".join(f"{n} (${n + 128:02X})" for n in off))
        else:
            print(f"{ver}: {len(lits)} distinct GEN1 opcodes, all "
                  f"one-operand ({len(one_operand)} of 128 candidates are)")

    if bad:
        print("\n".join(bad))
        return 1
    print("emitters-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
