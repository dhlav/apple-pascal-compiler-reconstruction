"""Per-procedure evidence profiles, to support naming the compiler's routines.

For every procedure this gathers, in one place, everything that constrains
what it can be: its signature, whether it is a function, who calls it, what
it calls, which globals it touches, which runtime services it uses, and any
literal strings it contains.

Function detection uses the db operand of the terminating RNP/RBP, which is
the function result size in words -- 0 for a procedure. See
tools/probes/probe_rnp_operand.py for the evidence.
"""
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.pcode import disassemble, sweep_exit
from a2pascal.syscall import segment0_procedures, csp_name

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "analysis" / "procedures"
OUT.mkdir(parents=True, exist_ok=True)
SEG0 = segment0_procedures(ROOT / "reference_source" / "ucsd_ii0" / "GLOBALS.TEXT")

DISKS = {
    "1.1": "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk",
    "1.3": "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk",
}
GLOBAL_OPS = {"LDO": "r", "SLDO": "r", "SRO": "w", "LAO": "&"}


def build(cf):
    segmap = {s.seg_num: s.name for s in cf.segments}
    streams, procs = {}, {}
    for seg in cf.segments:
        for p in seg.pcode_procedures:
            b, _ = disassemble(seg.data, p.enter_ic, p.exit_ic, p.jtab)
            x, _ = sweep_exit(seg.data, p.exit_ic, p.jtab - 8, p.jtab)
            streams[(seg.name, p.number)] = b + x
            procs[(seg.name, p.number)] = p

    def target(segname, ins):
        if ins.mnemonic == "CXP":
            s, n = ins.operands
            return ("OS", n) if s == 0 else (segmap.get(s, f"seg{s}"), n)
        if ins.mnemonic in ("CLP", "CIP"):
            return (segname, ins.operands[0])
        if ins.mnemonic == "CGP":
            return ("PASCALCO", ins.operands[0])
        return None

    callers = defaultdict(Counter)
    for key, st in streams.items():
        for ins in st:
            t = target(key[0], ins)
            if t:
                callers[t][key] += 1
    return segmap, streams, procs, callers, target


def profile(cf, ver):
    segmap, streams, procs, callers, target = build(cf)
    L = [f"Apple Pascal {ver} SYSTEM.COMPILER -- procedure profiles", "",
         "signature line: params/locals in BYTES, lex level, code size in bytes.",
         "'function(n words)' comes from the RNP/RBP db operand.",
         "globals are word offsets: r=read w=write &=address taken.", ""]

    for key in sorted(streams, key=lambda k: (k[0], k[1])):
        segname, pn = key
        p, st = procs[key], streams[key]
        fn = 0
        for i in reversed(st):
            if i.mnemonic in ("RNP", "RBP"):
                fn = i.operands[0]
                break

        g = defaultdict(set)
        csps, oss, calls, strings = Counter(), Counter(), Counter(), []
        for ins in st:
            if ins.mnemonic in GLOBAL_OPS:
                g[ins.operands[0]].add(GLOBAL_OPS[ins.mnemonic])
            elif ins.mnemonic == "CSP":
                csps[ins.operands[0]] += 1
            elif ins.mnemonic == "LSA":
                strings.append(ins.operands[0].decode("ascii", "replace"))
            t = target(segname, ins)
            if t:
                (oss if t[0] == "OS" else calls)[t] += 1

        who = callers.get(key, Counter())
        L.append("-" * 68)
        L.append(f"{segname}.{pn}   "
                 + (f"function({fn} word)" if fn else "procedure")
                 + f"   params={p.param_size} locals={p.data_size} "
                   f"lex={p.lex_level} size={p.exit_ic - p.enter_ic}")
        L.append(f"  called from {sum(who.values())} site(s) in "
                 f"{len(who)} procedure(s)"
                 + (f": {', '.join(f'{a}.{b}' for a, b in sorted(who))}"
                    if 0 < len(who) <= 14 else ""))
        if calls:
            L.append("  calls      : " + ", ".join(
                f"{a}.{b}" + (f" x{n}" if n > 1 else "")
                for (a, b), n in sorted(calls.items())))
        if oss:
            L.append("  runtime    : " + ", ".join(
                f"OS.{b} {SEG0.get(b, '?')}" + (f" x{n}" if n > 1 else "")
                for (_, b), n in sorted(oss.items())))
        if csps:
            L.append("  intrinsics : " + ", ".join(
                csp_name(k) + (f" x{n}" if n > 1 else "")
                for k, n in sorted(csps.items())))
        if g:
            L.append("  globals    : " + ", ".join(
                f"{off}{''.join(sorted(kinds))}" for off, kinds in sorted(g.items())))
        if strings:
            L.append("  strings    : " + ", ".join(repr(s) for s in strings))
    return "\n".join(L)


for ver, fname in DISKS.items():
    disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / fname)
    e = disk.find("SYSTEM.COMPILER")
    cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))
    path = OUT / f"profiles-{ver}.txt"
    path.write_text(profile(cf, ver), encoding="ascii")
    print(f"[{ver}] wrote {path.name}")
