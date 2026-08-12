"""What does the db operand of RNP/RBP mean?

Hypothesis: it is the size in words of the function result, so 0 for a
procedure and non-zero for a function. Test it against an independent
signal -- whether the value left by a call is consumed at the call site --
by checking the instruction immediately after each call.
"""
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.pcode import disassemble, sweep_exit

ROOT = Path(__file__).resolve().parents[2]
disk = PascalDisk.from_file(ROOT / "evidence" / "disks" /
                            "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk")
e = disk.find("SYSTEM.COMPILER")
cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))
segmap = {s.seg_num: s.name for s in cf.segments}

# 1. terminator operand per procedure
term = {}
streams = {}
for seg in cf.segments:
    for p in seg.pcode_procedures:
        b, _ = disassemble(seg.data, p.enter_ic, p.exit_ic, p.jtab)
        x, _ = sweep_exit(seg.data, p.exit_ic, p.jtab - 8, p.jtab)
        streams[(seg.name, p.number)] = b + x
        for i in reversed(b + x):
            if i.mnemonic in ("RNP", "RBP"):
                term[(seg.name, p.number)] = (i.mnemonic, i.operands[0])
                break

print("terminator operand distribution:",
      Counter(v[1] for v in term.values()))
print()

# 2. is the result consumed? look at the instruction right after each call
CONSUMES = {"STL", "SRO", "STR", "STO", "STB", "STM", "STP", "ADI", "SBI",
            "MPI", "DVI", "MODI", "EQUI", "NEQI", "LESI", "LEQI", "GRTI",
            "GEQI", "EQU", "NEQ", "LES", "LEQ", "GRT", "GEQ", "FJP", "LNOT",
            "LAND", "LOR", "SIND", "IND", "IXA", "ADJ", "NGI", "INC", "IXP",
            "UNI", "INT", "DIF", "INN", "SGS", "ABI", "SQI", "CHK", "XJP",
            "LDB", "MOV", "LDM", "SAS", "IXS", "FLT", "SRS"}
after = defaultdict(Counter)
for (segname, pn), st in streams.items():
    for k, ins in enumerate(st[:-1]):
        if ins.mnemonic == "CXP":
            tgt = (segmap.get(ins.operands[0]), ins.operands[1])
        elif ins.mnemonic in ("CLP", "CIP"):
            tgt = (segname, ins.operands[0])
        elif ins.mnemonic == "CGP":
            tgt = ("PASCALCO", ins.operands[0])
        else:
            continue
        if tgt not in term:
            continue
        after[tgt]["consumed" if st[k + 1].mnemonic in CONSUMES else "dropped"] += 1

print(f"{'procedure':<16} {'term':>8} {'db':>3}  consumed/dropped at call sites")
agree = disagree = 0
for tgt in sorted(after, key=lambda t: (t[0] or "", t[1])):
    if tgt not in term:
        continue
    mn, db = term[tgt]
    c, d = after[tgt]["consumed"], after[tgt]["dropped"]
    looks_fn = c > d
    says_fn = db != 0
    ok = looks_fn == says_fn
    agree += ok
    disagree += not ok
    if not ok or db:
        print(f"{tgt[0]}.{tgt[1]:<12} {mn:>8} {db:>3}  "
              f"consumed={c:<4} dropped={d:<4} {'' if ok else '<-- DISAGREES'}")
print(f"\nagree={agree} disagree={disagree}")
