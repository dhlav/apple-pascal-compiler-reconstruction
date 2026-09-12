"""Is SLDO/SLDL 0-based or 1-based? i.e. is $E0 = SLDO 0 or SLDO 1?

The decoder currently uses n = op - $DF for SLDO ($E0 -> 1) and
n = op - $CF for SLDL ($D0 -> 1). If that is off by one, every global
offset below 17 in the global map is wrong.

Decisive test: the increment idiom
    <load X> ; SLDC 1 ; ADI ; <store X>
must load and store the SAME variable. SRO and STL have no short form, so
their operand is unambiguous; comparing it against the short-form load's
operand settles the base.
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.pcode import disassemble, sweep_exit

ROOT = Path(__file__).resolve().parents[2]

for ver, fname in (("1.1", "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk"),
                   ("1.3", "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk")):
    disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / fname)
    e = disk.find("SYSTEM.COMPILER")
    cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))
    glob, loc = Counter(), Counter()
    for seg in cf.segments:
        for p in seg.pcode_procedures:
            b, _ = disassemble(seg.data, p.enter_ic, p.exit_ic, p.jtab)
            x, _ = sweep_exit(seg.data, p.exit_ic, p.jtab - 8, p.jtab)
            st = b + x
            for k in range(len(st) - 3):
                a, c, d, f = st[k:k + 4]
                if not (c.mnemonic == "SLDC" and c.operands[0] == 1
                        and d.mnemonic == "ADI"):
                    continue
                if a.mnemonic == "SLDO" and f.mnemonic == "SRO":
                    glob[a.operands[0] - f.operands[0]] += 1
                if a.mnemonic == "SLDL" and f.mnemonic == "STL":
                    loc[a.operands[0] - f.operands[0]] += 1
    print(f"[{ver}] increment idiom, (short-load operand - store operand):")
    print(f"   SLDO vs SRO: {dict(sorted(glob.items()))}")
    print(f"   SLDL vs STL: {dict(sorted(loc.items()))}")
    print("   a spike at 0 means the current 1-based decoding is correct;")
    print("   a spike at +1 means the short forms are 0-based.\n")
