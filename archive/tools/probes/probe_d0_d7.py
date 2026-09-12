"""Identify opcodes $D0 and $D7, the only bytes in $D0-$D7 that occur."""
import sys
from collections import Counter
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

hits = {0xD0: [], 0xD7: []}
before, after = Counter(), Counter()
for seg in cf.segments:
    for p in seg.pcode_procedures:
        b, _ = disassemble(seg.data, p.enter_ic, p.exit_ic, p.jtab)
        x, _ = sweep_exit(seg.data, p.exit_ic, p.jtab - 8, p.jtab)
        st = b + x
        for k, i in enumerate(st):
            if i.opcode in hits:
                ctx = ([q.text for q in st[max(0, k - 3):k]],
                       [q.text for q in st[k + 1:k + 4]])
                hits[i.opcode].append((f"{seg.name}.{p.number}", i.addr, ctx))
                if k:
                    before[(i.opcode, st[k - 1].mnemonic)] += 1
                if k + 1 < len(st):
                    after[(i.opcode, st[k + 1].mnemonic)] += 1

for op in (0xD0, 0xD7):
    print(f"=== ${op:02X}: {len(hits[op])} occurrences")
    print("  preceded by:", ", ".join(
        f"{m} x{n}" for (o, m), n in before.most_common() if o == op)[:200])
    print("  followed by:", ", ".join(
        f"{m} x{n}" for (o, m), n in after.most_common() if o == op)[:200])
    for w, a, (pre, post) in hits[op][:8]:
        print(f"  {w:<13} ${a:04X}:  " + " ; ".join(pre)
              + f"   >>${op:02X}<<   " + " ; ".join(post))
    print()
