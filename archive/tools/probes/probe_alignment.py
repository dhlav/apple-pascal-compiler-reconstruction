"""Do the LDC and XJP inline operand blocks self-align to a word boundary?

The decoder currently pads to an even offset before reading LDC's word
block and XJP's table. If that is wrong the stream desynchronises, so
flipping the assumption and re-running the whole-corpus sync check settles
it. (Hyde p.95 shows the compiler emitting a NOP to align string constants,
which raises the question of whether these blocks self-align at all.)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import a2pascal.pcode as pcode
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile

ROOT = Path(__file__).resolve().parents[2]
DISKS = ("Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk",
         "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk")

cfs = []
for f in DISKS:
    d = PascalDisk.from_file(ROOT / "evidence" / "disks" / f)
    e = d.find("SYSTEM.COMPILER")
    cfs.append(CodeFile(d.read_blocks(e.first_block, e.blocks)))


def run():
    ok = bad = 0
    for cf in cfs:
        for seg in cf.segments:
            for p in seg.pcode_procedures:
                try:
                    _, exact = pcode.disassemble(seg.data, p.enter_ic,
                                                 p.exit_ic, p.jtab)
                    _, end = pcode.sweep_exit(seg.data, p.exit_ic,
                                              p.jtab - 8, p.jtab)
                except Exception:
                    exact, end = False, None
                if exact and end is not None:
                    ok += 1
                else:
                    bad += 1
    return ok, bad


print("with word alignment of LDC/XJP blocks   :", run())

src = Path(pcode.__file__).read_text()
patched = src.replace("            if p % 2:\n                p += 1\n", "")
ns = {}
exec(compile(patched, "pcode_noalign", "exec"), ns)
pcode.disassemble, pcode.sweep_exit = ns["disassemble"], ns["sweep_exit"]
print("without word alignment                  :", run())
