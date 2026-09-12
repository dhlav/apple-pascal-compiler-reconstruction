"""Lift procedures to pseudo-Pascal: liftproc.py [ver] SEGMENT.N ..."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.lift import lift, render
from a2pascal.names import procname

ROOT = Path(__file__).resolve().parent.parent
DISKS = {
    "1.3": "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk",
}

args = sys.argv[1:]
ver = "1.3"
if args and re.fullmatch(r"1\.3", args[0]):
    ver, args = args[0], args[1:]

disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / DISKS[ver])
e = disk.find("SYSTEM.COMPILER")
cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))

for spec in args:
    segname, num = spec.upper().rsplit(".", 1)
    seg = cf.segment(segname)
    p = next(x for x in seg.procedures if x.number == int(num))
    fn = ""
    from a2pascal.pcode import disassemble, sweep_exit
    for i in reversed(disassemble(seg.data, p.enter_ic, p.exit_ic, p.jtab)[0]
                      + sweep_exit(seg.data, p.exit_ic, p.jtab - 8, p.jtab)[0]):
        if i.mnemonic in ("RNP", "RBP"):
            fn = f" : <{i.operands[0]} word result>" if i.operands[0] else ""
            break
    nm = procname(segname, int(num), ver)
    argw = p.param_size // 2 - (2 if fn else 0)
    hdr = (f"{'function' if fn else 'procedure'} {segname}.{num}"
           f"{':' + nm if nm else ''}"
           f"(args {argw} words){fn};  "
           f"{{ locals {p.data_size // 2} words, lex {p.lex_level} }}")
    print(render(lift(seg, p, cf, ver), hdr))
    print()
