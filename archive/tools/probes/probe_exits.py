"""Inspect the exit-code region of the procedures that failed the RNP/RBP check."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.pcode import decode

ROOT = Path(__file__).resolve().parents[2]
CASES = [
    ("1.1", "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk", "PASCALCO", 1),
    ("1.1", "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk", "PASCALCO", 28),
    ("1.1", "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk", "PASCALCO", 29),
    ("1.1", "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk", "BODYPART", 26),
    ("1.1", "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk", "BODYPART", 37),
]
cache = {}
for ver, fname, segname, pn in CASES:
    if fname not in cache:
        d = PascalDisk.from_file(ROOT / "evidence" / "disks" / fname)
        e = d.find("SYSTEM.COMPILER")
        cache[fname] = CodeFile(d.read_blocks(e.first_block, e.blocks))
    seg = cache[fname].segment(segname)
    p = [x for x in seg.procedures if x.number == pn][0]
    print(f"== [{ver}] {segname} proc {pn}: enter=0x{p.enter_ic:04X} exit=0x{p.exit_ic:04X} "
          f"jtab=0x{p.jtab:04X} param={p.param_size} data={p.data_size} lex={p.lex_level}")
    print(f"   body bytes : {seg.data[p.enter_ic:p.exit_ic].hex(' ')}")
    print(f"   exit..jtab : {seg.data[p.exit_ic:p.jtab + 2].hex(' ')}")
    q = p.exit_ic
    while q < p.jtab - 8:
        ins = decode(seg.data, q)
        print(f"     {q:04X}  {ins.raw.hex(' '):<14} {ins.text}")
        q += ins.length
        if ins.mnemonic in ("RNP", "RBP"):
            print(f"     -> terminates at 0x{q:04X}; jtab-8=0x{p.jtab - 8:04X}; "
                  f"slack={p.jtab - 8 - q} bytes ({(p.jtab - 8 - q) // 2} jumptable words)")
            break
    print()
