"""Examine the two anomalous procedures in Apple Pascal 1.3's PASCALCO.

The segment is flagged mtype=6502, but 29 of its 31 procedures parse as
ordinary p-code attribute tables. This looks at procedures 2 and 3, which
do not, and tries a p-code sweep on the rest.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.pcode import disassemble, sweep_exit

ROOT = Path(__file__).resolve().parents[2]
disk = PascalDisk.from_file(ROOT / "evidence" / "disks" /
                            "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk")
e = disk.find("SYSTEM.COMPILER")
cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))
seg = cf.segment("PASCALCO")
print(f"PASCALCO 1.3: len={seg.length} mtype={seg.mtype} nproc={len(seg.procedures)}\n")

for p in seg.procedures:
    if p.number > 4:
        continue
    print(f"proc {p.number}: JTAB=0x{p.jtab:04X} pn={p.proc_num} lex={p.lex_level} "
          f"enter=0x{p.enter_ic:04X} exit=0x{p.exit_ic:04X} "
          f"param={p.param_size} data={p.data_size} ok={p.consistent}")
    print(f"   attr bytes JTAB-10..JTAB+2: {seg.data[p.jtab - 10:p.jtab + 2].hex(' ')}")
    print(f"   first 24 bytes at enter   : {seg.data[p.enter_ic:p.enter_ic + 24].hex(' ')}")
print()

ok = bad = 0
for p in seg.procedures:
    try:
        insns, exact = disassemble(seg.data, p.enter_ic, p.exit_ic, p.jtab)
        ex, end = sweep_exit(seg.data, p.exit_ic, p.jtab - 8, p.jtab)
        unknown = [i for i in insns + ex if i.mnemonic.startswith("DB_")]
        good = exact and not unknown and end is not None and p.jtab - 8 - end >= 0
    except Exception:
        good = False
    if good:
        ok += 1
    else:
        bad += 1
        print(f"  proc {p.number} does NOT sweep as p-code")
print(f"\n{ok}/{len(seg.procedures)} procedures sweep cleanly as p-code")
