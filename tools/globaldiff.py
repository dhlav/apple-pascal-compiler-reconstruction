"""Derive a 1.1 -> 1.3 correspondence for globals, procedures and segments.

1.3 is a recompile of a lightly edited 1.1 source, so nearly every procedure
survives with its code almost unchanged while the global offsets shift by a
few words (globals grew from 1222 to 1355 words). Recovering the mapping
lets 1.1-derived knowledge be carried over to 1.3, which is the version we
ultimately want to reconstruct.

Method:
  1. Align each segment's procedure list across versions on the signature
     (param_size, data_size, lex_level). This absorbs the two native
     procedures 1.3 inserts at PASCALCO slots 2-3.
  2. For each matched procedure pair, align the two instruction streams on
     an operand-insensitive token per instruction, so that an instruction
     whose operand shifted still lines up.
  3. Wherever both sides of a matched position are the same kind of global
     access, cast a vote off_11 -> off_13. Aggregate and report.

Everything here is STRONG INFERENCE, not verified fact: it is only as good
as the alignment. Vote counts and conflicts are reported so the confidence
of each individual mapping is visible.
"""
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.pcode import disassemble, sweep_exit

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "analysis" / "global_map"
OUT.mkdir(parents=True, exist_ok=True)

DISKS = {
    "1.1": "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk",
    "1.3": "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk",
}
GLOBAL_READ = ("LDO", "SLDO")
GLOBAL_OPS = {"LDO": "read", "SLDO": "read", "SRO": "write", "LAO": "addr"}
# Operand-bearing instructions whose operand is expected to shift between
# versions, so the token drops it.
DROP_OPERAND = {"LDO", "SLDO", "SRO", "LAO", "LDL", "SLDL", "STL", "LLA",
                "LOD", "STR", "LDA", "FJP", "UJP", "XJP", "INC", "IXA"}


def load(fname):
    disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / fname)
    e = disk.find("SYSTEM.COMPILER")
    return CodeFile(disk.read_blocks(e.first_block, e.blocks))


def stream(seg, p):
    body, _ = disassemble(seg.data, p.enter_ic, p.exit_ic, p.jtab)
    ex, _ = sweep_exit(seg.data, p.exit_ic, p.jtab - 8, p.jtab)
    return body + ex


def token(ins):
    m = ins.mnemonic
    if m in GLOBAL_OPS:
        return f"G_{GLOBAL_OPS[m]}"
    if m in DROP_OPERAND:
        return m
    return ins.text          # calls and constants keep their operands


cf11, cf13 = load(DISKS["1.1"]), load(DISKS["1.3"])
seg13 = {s.name: s for s in cf13.segments}

votes = defaultdict(Counter)          # off11 -> Counter(off13)
proc_map = []                         # (segment, p11, p13, similarity)
unmatched = []

for s11 in cf11.segments:
    s13 = seg13.get(s11.name)
    if s13 is None:
        unmatched.append((s11.name, "segment missing in 1.3"))
        continue
    a = s11.procedures
    b = s13.procedures
    sig_a = [(p.param_size, p.data_size, p.lex_level) for p in a]
    sig_b = [(p.param_size, p.data_size, p.lex_level) for p in b]
    sm = SequenceMatcher(None, sig_a, sig_b, autojunk=False)
    for i, j, n in sm.get_matching_blocks():
        for k in range(n):
            pa, pb = a[i + k], b[j + k]
            if pa.is_native or pb.is_native:
                continue
            ta, tb = stream(s11, pa), stream(s13, pb)
            toks_a = [token(x) for x in ta]
            toks_b = [token(x) for x in tb]
            m2 = SequenceMatcher(None, toks_a, toks_b, autojunk=False)
            ratio = m2.ratio()
            proc_map.append((s11.name, pa.number, pb.number, ratio))
            if ratio < 0.5:
                continue
            for ia, ib, nn in m2.get_matching_blocks():
                for q in range(nn):
                    xa, xb = ta[ia + q], tb[ib + q]
                    if xa.mnemonic in GLOBAL_OPS and xb.mnemonic in GLOBAL_OPS:
                        if GLOBAL_OPS[xa.mnemonic] == GLOBAL_OPS[xb.mnemonic]:
                            votes[xa.operands[0]][xb.operands[0]] += 1

L = ["Apple Pascal 1.1 -> 1.3 correspondence",
     "",
     "STRONG INFERENCE throughout. See the method note in tools/globaldiff.py.",
     "",
     "== Procedure correspondence",
     "(similarity is the token-stream match ratio; 1.00 means the two",
     " procedures compile to the same instruction shapes throughout)",
     ""]
by_seg = defaultdict(list)
for segname, p11, p13, r in proc_map:
    by_seg[segname].append((p11, p13, r))
for segname in [s.name for s in cf11.segments]:
    rows = by_seg.get(segname, [])
    if not rows:
        continue
    ident = sum(1 for _, _, r in rows if r > 0.999)
    L.append(f"  {segname:<9} {len(rows):>2} matched, {ident:>2} identical")
    for p11, p13, r in rows:
        flag = "" if r > 0.999 else ("   CHANGED" if r > 0.8 else "   HEAVILY CHANGED")
        if r <= 0.999:
            L.append(f"      {segname}.{p11} -> {segname}.{p13}   sim={r:.3f}{flag}")

L += ["", "== Global offset correspondence", "",
      f"{'1.1':>6} {'1.3':>6} {'delta':>6} {'votes':>6}  confidence"]
conflicts = []
for off11 in sorted(votes):
    c = votes[off11]
    best, n = c.most_common(1)[0]
    total = sum(c.values())
    conf = n / total
    L.append(f"{off11:>6} {best:>6} {best - off11:>+6} {n:>6}  "
             f"{conf:.2f}" + ("" if conf > 0.95 else
                              f"   contested: {dict(c.most_common(4))}"))
    if conf <= 0.95:
        conflicts.append(off11)

deltas = Counter(votes[o].most_common(1)[0][0] - o for o in votes)
L += ["", "== Shift distribution", "",
      "How many globals move by each delta (a small number of distinct",
      "deltas means 1.3 inserted a few globals into an otherwise stable",
      "layout):", ""]
for d, n in sorted(deltas.items()):
    L.append(f"  delta {d:>+5}: {n:>4} globals")
L += ["", f"globals mapped: {len(votes)}", f"contested: {len(conflicts)}"]

path = OUT / "correspondence-1.1-to-1.3.txt"
path.write_text("\n".join(L), encoding="ascii")
print(f"wrote {path.name}: {len(proc_map)} procedure pairs, "
      f"{len(votes)} globals mapped, {len(conflicts)} contested")
print("shift distribution:", dict(sorted(deltas.items())))
