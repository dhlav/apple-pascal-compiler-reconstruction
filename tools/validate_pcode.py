"""Objective quality metric for the p-code opcode table.

For every procedure in every p-code segment of SYSTEM.COMPILER:
  * linear-sweep enter_ic .. exit_ic and require the sweep to land exactly
    on exit_ic (a bad operand length desynchronises the stream immediately);
  * require the instruction at exit_ic to be RNP or RBP.

Any procedure failing either check, or containing an unknown opcode, is
reported. A clean run is strong evidence the table and operand lengths
are correct.
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.pcode import disassemble, sweep_exit

ROOT = Path(__file__).resolve().parent.parent
DISKS = {
    "1.1": "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk",
    "1.3": "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk",
}

total = ok = 0
bad = []
opcount = Counter()

for ver, fname in DISKS.items():
    disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / fname)
    e = disk.find("SYSTEM.COMPILER")
    cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))
    for seg in cf.segments:
        if seg.native_procedures:
            print(f"[{ver}] {seg.name}: skipping native procedures "
                  f"{[p.number for p in seg.native_procedures]}")
        for p in seg.pcode_procedures:
            total += 1
            insns, exact = disassemble(seg.data, p.enter_ic, p.exit_ic, p.jtab)
            try:
                ex_insns, end = sweep_exit(seg.data, p.exit_ic, p.jtab - 8, p.jtab)
            except Exception:
                ex_insns, end = [], None
            for i in insns + ex_insns:
                opcount[i.mnemonic] += 1
            unknown = [i for i in insns + ex_insns if i.mnemonic.startswith("DB_")]
            # Slack between the end of the exit code and the attribute table
            # holds the procedure's jump table (plus up to one alignment byte,
            # since p-code is not word-aligned).
            slack = None if end is None else p.jtab - 8 - end
            good = exact and not unknown and end is not None and slack >= 0
            if good:
                ok += 1
            else:
                bad.append((ver, seg.name, p.number, exact, slack,
                            [f"{i.addr:04X}:{i.opcode:02X}" for i in unknown][:4]))

print(f"\nprocedures: {ok}/{total} decode cleanly")
if bad:
    print("\nfailures:")
    for ver, seg, n, exact, slack, unk in bad:
        print(f"  [{ver}] {seg} proc {n}: in_sync={exact} jumptable_slack={slack} unknown={unk}")
print("\nopcode frequency:")
for m, c in opcount.most_common():
    print(f"  {m:<6} {c}")
