"""Build the SYSTEM.COMPILER call graph and per-procedure call-site index.

Emits, for each version:
  analysis/callgraph/callgraph-<ver>.txt   callers/callees per procedure
  analysis/callgraph/callsites-<ver>.txt   every call site with the p-code
                                           that pushes its arguments
"""
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.pcode import disassemble, sweep_exit
from a2pascal.syscall import segment0_procedures

ROOT = Path(__file__).resolve().parent.parent
SEG0 = segment0_procedures(ROOT / "reference_source" / "ucsd_ii0" / "GLOBALS.TEXT")
DISKS = {
    "1.1": "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk",
    "1.3": "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk",
}
CONTEXT = 6      # instructions of argument setup to show before each call


def analyse(cf):
    segmap = {s.seg_num: s.name for s in cf.segments}
    # (segname, procnum) -> list of (caller_segname, caller_proc, addr, context)
    callers = defaultdict(list)
    callees = defaultdict(list)

    for seg in cf.segments:
        for p in seg.pcode_procedures:
            body, _ = disassemble(seg.data, p.enter_ic, p.exit_ic, p.jtab)
            ex, _ = sweep_exit(seg.data, p.exit_ic, p.jtab - 8, p.jtab)
            stream = body + ex
            me = (seg.name, p.number)
            for k, ins in enumerate(stream):
                if ins.mnemonic == "CXP":
                    s, n = ins.operands
                    if s == 0:
                        tgt = ("OS", f"{n} {SEG0.get(n, '?')}")
                    else:
                        tgt = (segmap.get(s, f"seg{s}"), n)
                elif ins.mnemonic in ("CLP", "CGP", "CIP", "CBP"):
                    tgt = (seg.name, ins.operands[0])
                else:
                    continue
                ctx = stream[max(0, k - CONTEXT):k]
                callers[tgt].append((me, ins.addr, ins.mnemonic, ctx))
                callees[me].append((tgt, ins.addr, ins.mnemonic))
    return segmap, callers, callees


for ver, fname in DISKS.items():
    disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / fname)
    e = disk.find("SYSTEM.COMPILER")
    cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))
    segmap, callers, callees = analyse(cf)

    out = ROOT / "analysis" / "callgraph"
    out.mkdir(parents=True, exist_ok=True)

    lines = [f"Apple Pascal {ver} SYSTEM.COMPILER call graph", ""]
    for seg in cf.segments:
        for p in seg.pcode_procedures:
            me = (seg.name, p.number)
            ins = sorted({(c[0][0], c[0][1]) for c in callers.get(me, [])})
            outs = sorted({t for t, _, _ in callees.get(me, [])})
            lines.append(f"{seg.name}.{p.number}  (params={p.param_size} "
                         f"data={p.data_size} lex={p.lex_level} "
                         f"size={p.exit_ic - p.enter_ic})")
            lines.append("    called by: " + (", ".join(f"{a}.{b}" for a, b in ins) or "<none found>"))
            lines.append("    calls    : " + (", ".join(f"{a}.{b}" for a, b in outs) or "<none>"))
    (out / f"callgraph-{ver}.txt").write_text("\n".join(lines), encoding="ascii")

    lines = [f"Apple Pascal {ver} SYSTEM.COMPILER call sites",
             f"(up to {CONTEXT} instructions of argument setup shown per site)", ""]
    for tgt in sorted(callers, key=lambda t: (t[0], t[1])):
        lines.append(f"=== {tgt[0]}.{tgt[1]}  -- {len(callers[tgt])} call site(s)")
        for me, addr, mnem, ctx in callers[tgt]:
            lines.append(f"  from {me[0]}.{me[1]} at ${addr:04X} via {mnem}")
            for i in ctx:
                lines.append(f"      {i.addr:04X}  {i.text}")
        lines.append("")
    (out / f"callsites-{ver}.txt").write_text("\n".join(lines), encoding="ascii")
    print(f"[{ver}] wrote callgraph-{ver}.txt, callsites-{ver}.txt")
