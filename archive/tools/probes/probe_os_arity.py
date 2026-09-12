"""Check each segment-0 routine's parameter count against the call sites.

`syscall.py` reads segment-0 signatures out of GLOBALS.TEXT, the UCSD II.0
operating system source. But that is *generic* UCSD, not Apple's (finding
8), so a declaration there is a good default and not evidence about the
binary on the evidence disks.

This tests every routine the compiler actually calls. For each, it varies
only that routine's word count and scores the whole compiler:

  residue   values left on the evaluation stack with nothing to consume
            them -- an undercounted callee leaves its own arguments behind
  conflict  joins where two paths disagree on stack depth, which is what
            that residue turns into once it reaches a merge

Both are things a wrong count inflates, so the declared value should win.
Where the binary prefers a different count by a clear margin, that is
Apple's segment 0 differing from UCSD's, and the override goes in
syscall.OS_WORD_OVERRIDE. Where the declared value wins or ties, nothing
changes -- a tie is not evidence.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import a2pascal.syscall as sc
import a2pascal.lift as lift_mod
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.pcode import disassemble

ROOT = Path(__file__).resolve().parents[2]
DISKS = ("Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk",
         "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk")
GLOBALS = ROOT / "reference_source" / "ucsd_ii0" / "GLOBALS.TEXT"

PROCS = []
for f in DISKS:
    d = PascalDisk.from_file(ROOT / "evidence" / "disks" / f)
    e = d.find("SYSTEM.COMPILER")
    cf = CodeFile(d.read_blocks(e.first_block, e.blocks))
    PROCS += [(s, p, cf) for s in cf.segments for p in s.pcode_procedures]

BASE_SIG = sc.segment0_signatures(GLOBALS)

# Which segment-0 routines does the compiler call, and how often?
called: dict[int, int] = {}
for s, p, cf in PROCS:
    for i in disassemble(s.data, p.enter_ic, p.exit_ic, p.jtab)[0]:
        if i.mnemonic == "CXP" and i.operands[0] == 0:
            called[i.operands[1]] = called.get(i.operands[1], 0) + 1


def score(overrides):
    sc.OS_WORD_OVERRIDE = dict(overrides)
    lift_mod.OS_SIG = sc.segment0_signatures(GLOBALS)
    residue = conflict = 0
    for s, p, cf in PROCS:
        try:
            blocks = lift_mod.lift(s, p, cf)
        except Exception:
            continue
        for b in blocks:
            for t in b.stmts:
                if t.startswith("{ left on stack"):
                    residue += 1
                elif t.startswith("{ paths disagree"):
                    conflict += 1
    return residue + conflict


base = score({})
print(f"{len(PROCS)} procedures, both releases")
print(f"baseline (GLOBALS.TEXT as declared): {base}\n")
print(f"{'routine':<16}{'calls':>6}{'declared':>9}{'best':>6}{'score':>7}"
      f"{'margin':>8}  verdict")
print("-" * 74)

overrides = {}
for num in sorted(called):
    if num not in BASE_SIG:
        continue
    name, declared, _ = BASE_SIG[num]
    scores = {}
    for w in range(0, 11):
        scores[w] = score({**overrides, name: w})
    best_w = min(scores, key=lambda w: (scores[w], abs(w - declared)))
    margin = scores[declared] - scores[best_w]
    if best_w != declared and margin > 0:
        overrides[name] = best_w
        verdict = f"OVERRIDE {declared} -> {best_w}"
    elif best_w != declared:
        verdict = "tie -- declared kept"
        best_w = declared
    else:
        verdict = "declared confirmed"
    print(f"{name:<16}{called[num]:>6}{declared:>9}{best_w:>6}"
          f"{scores[best_w]:>7}{margin:>8}  {verdict}")

print(f"\nfinal: {score(overrides)}  (from {base})")
print("OS_WORD_OVERRIDE =", overrides)
