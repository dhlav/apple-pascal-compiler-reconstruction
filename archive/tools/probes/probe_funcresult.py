"""Does a function call reserve a fixed two-word result area?

PASCALCO.15 is declared with six parameter bytes -- three words -- yet its
body only ever reads the third of them, and every call site pushes the one
real argument followed by two literal zeros:

    SLDL 3 / SLDC 0 / SLDC 0 / CGP 15

The natural reading is the UCSD convention: the caller reserves room for
the function result, always two words (enough for a real), and the callee's
parameter area covers it, so the declared parameter size is
`2 + words of actual arguments` and the arguments sit at the high end.

That is a claim the binary can refute. This walks every call in both
releases whose target ends in `RNP n` with n > 0 -- i.e. every function
call -- and looks at the two instructions immediately before the call. If
the convention holds, both are pushes of the constant 0 (`SLDC 0`, or
`LDCI 0`) at every single site. One site pushing something else sinks it.

Procedure calls (`RNP 0`) are counted the same way as a control: there is
no reason for *those* to end in two zero pushes, so if the pattern shows up
just as often there, it is an artifact of the compiler and not evidence.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.pcode import disassemble, sweep_exit

ROOT = Path(__file__).resolve().parents[2]
DISKS = (("1.1", "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk"),
         ("1.3", "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk"))


def is_zero_push(i):
    return (i.mnemonic in ("SLDC", "LDCI") and i.operands[0] == 0)


for rel, fname in DISKS:
    d = PascalDisk.from_file(ROOT / "evidence" / "disks" / fname)
    e = d.find("SYSTEM.COMPILER")
    cf = CodeFile(d.read_blocks(e.first_block, e.blocks))
    segbynum = {s.seg_num: s for s in cf.segments}

    # result width of every p-code procedure, keyed (segnum, procnum)
    res: dict[tuple[int, int], int] = {}
    params: dict[tuple[int, int], int] = {}
    for s in cf.segments:
        for p in s.pcode_procedures:
            params[(s.seg_num, p.number)] = p.param_size // 2
            # RNP lives in the exit sequence, past exit_ic, not in the body.
            tail = (disassemble(s.data, p.enter_ic, p.exit_ic, p.jtab)[0]
                    + sweep_exit(s.data, p.exit_ic, p.jtab - 8, p.jtab)[0])
            for i in reversed(tail):
                if i.mnemonic in ("RNP", "RBP"):
                    res[(s.seg_num, p.number)] = i.operands[0]
                    break

    tally = {True: [0, 0], False: [0, 0]}   # isfn -> [sites, sites ending 0 0]
    odd = []
    for s in cf.segments:
        for p in s.pcode_procedures:
            body = disassemble(s.data, p.enter_ic, p.exit_ic, p.jtab)[0]
            for k, i in enumerate(body):
                if i.mnemonic == "CXP":
                    tgt = (i.operands[0], i.operands[1])
                    if i.operands[0] == 0:
                        continue
                elif i.mnemonic == "CGP":
                    tgt = (1, i.operands[0])
                elif i.mnemonic in ("CLP", "CIP"):
                    tgt = (s.seg_num, i.operands[0])
                else:
                    continue
                if tgt not in res:
                    continue           # native, or a segment we cannot see
                isfn = res[tgt] > 0
                tally[isfn][0] += 1
                if k >= 2 and is_zero_push(body[k - 1]) and \
                        is_zero_push(body[k - 2]):
                    tally[isfn][1] += 1
                elif isfn:
                    odd.append((s.name, p.number, i.address, tgt,
                                body[k - 2].text if k >= 2 else "-",
                                body[k - 1].text if k >= 1 else "-"))

    print(f"=== {rel} ===")
    for isfn, what in ((True, "function"), (False, "procedure")):
        n, z = tally[isfn]
        pct = 100.0 * z / n if n else 0.0
        print(f"  {what:<10} call sites {n:5d}   ending in two zero "
              f"pushes {z:5d}  ({pct:5.1f}%)")
    if odd:
        print(f"  {len(odd)} function call sites without the pattern:")
        for row in odd[:20]:
            print(f"    {row[0]}.{row[1]} @ ${row[2]:04X} -> seg{row[3][0]}."
                  f"{row[3][1]}   ...{row[4]} / {row[5]}")

    # If the convention holds, every function's declared parameter size is
    # at least 2 words.
    small = [(k, v) for k, v in params.items() if res.get(k, 0) > 0 and v < 2]
    print(f"  functions declaring fewer than 2 parameter words: {len(small)}")
    print()
