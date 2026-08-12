"""Recover the stack effect of the undocumented CSPs by balance testing.

A procedure lifts "cleanly" only if every instruction's stack effect is
known AND the evaluation stack is empty at the end. So for an unknown CSP,
the (pops, pushes) pair that is actually correct should be the one that
makes the most procedures balance; wrong pairs leave residue or underflow.

Solved greedily: try every candidate for every still-unknown CSP, adopt the
single best improvement, repeat. The margin over the runner-up is printed
so a weakly-determined answer is visible as such.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import a2pascal.lift as lift_mod
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.lift import lift

ROOT = Path(__file__).resolve().parents[2]
DISKS = ("Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk",
         "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk")

cfs = []
for f in DISKS:
    d = PascalDisk.from_file(ROOT / "evidence" / "disks" / f)
    e = d.find("SYSTEM.COMPILER")
    cfs.append(CodeFile(d.read_blocks(e.first_block, e.blocks)))


def score():
    good = 0
    for cf in cfs:
        for seg in cf.segments:
            for p in seg.pcode_procedures:
                try:
                    blocks = lift(seg, p, cf)
                except Exception:
                    continue
                if any(b.incomplete or b.underflow for b in blocks):
                    continue
                if any(s.startswith("{ left on stack") for b in blocks
                       for s in b.stmts):
                    continue
                good += 1
    return good


UNKNOWN = [6, 21, 22, 23, 24, 32, 33, 34, 36, 40]
CANDIDATES = [(pops, pushes) for pushes in (0, 1) for pops in range(0, 6)]

base = score()
print(f"baseline: {base} procedures balance\n")

remaining = list(UNKNOWN)
while remaining:
    results = []
    for n in remaining:
        for cand in CANDIDATES:
            lift_mod.CSP_EFFECT[n] = cand
            results.append((score(), n, cand))
            del lift_mod.CSP_EFFECT[n]
    results.sort(reverse=True)
    best, n, cand = results[0]
    if best <= base:
        print("no further improvement; unresolved:", remaining)
        break
    runner = next((s for s, nn, cc in results if nn == n and cc != cand), best)
    lift_mod.CSP_EFFECT[n] = cand
    remaining.remove(n)
    print(f"CSP {n:>2}: pops={cand[0]} pushes={cand[1]}   "
          f"{base} -> {best} balanced   (next best for this CSP: {runner})")
    base = best

print("\nresolved table:", {k: v for k, v in sorted(lift_mod.CSP_EFFECT.items())})
