"""Test the interpreter-derived CSP arities against the compiler binary.

tools/probes/probe_csp_arity.py had to *search* for CSP stack effects, and
could only reach two of them. Interp.s states all of them outright, so the
question is no longer "what are they" but "is the source we just imported
actually describing the machine this binary was compiled for" -- 1.4 is
three releases downstream of 1.1.

The test: lift every procedure on both disks and count how many balance
cleanly (no unknown opcode, no underflow, nothing left on the stack at the
end). A table that misdescribes the p-machine cannot raise that count, and
each individual entry is checked by perturbing it -- if some other arity
scores at least as well, the entry is not actually pinned down by the
binary and is reported as unconfirmed rather than verified.
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

# The table as it stood before Interp.s, for the before/after comparison.
OLD = {0: (0, 0), 1: (2, 0), 2: (3, 0), 3: (3, 0), 4: (2, 0), 7: (2, 0),
       8: (3, 0), 9: (2, 0), 10: (3, 0), 11: (4, 1), 34: (0, 1), 40: (0, 1)}

NEW = dict(lift_mod.CSP_EFFECT)

cfs = []
for f in DISKS:
    d = PascalDisk.from_file(ROOT / "evidence" / "disks" / f)
    e = d.find("SYSTEM.COMPILER")
    cfs.append(CodeFile(d.read_blocks(e.first_block, e.blocks)))

PROCS = [(seg, p, cf) for cf in cfs for seg in cf.segments
         for p in seg.pcode_procedures]


def score():
    good = 0
    for seg, p, cf in PROCS:
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


def use(table):
    lift_mod.CSP_EFFECT.clear()
    lift_mod.CSP_EFFECT.update(table)


print(f"{len(PROCS)} p-code procedures across both disks\n")

use(OLD)
old_score = score()
use(NEW)
new_score = score()

print(f"  hand-built table (12 entries):   {old_score} balance")
print(f"  Interp.s table  ({len(NEW)} entries):   {new_score} balance")
print(f"  {new_score - old_score:+d}\n")

# Per-entry: is this arity actually the best the binary allows?
from a2pascal.pcode import disassemble
from a2pascal.syscall import CSP

CANDIDATES = [(pops, pushes) for pushes in (0, 1, 2) for pops in range(0, 7)]

# Which CSPs does the compiler actually emit? Only those can be tested.
emitted = {}
for seg, p, cf in PROCS:
    for ins in disassemble(seg.data, p.enter_ic, p.exit_ic, p.jtab)[0]:
        if ins.mnemonic == "CSP":
            emitted[ins.operands[0]] = emitted.get(ins.operands[0], 0) + 1

print("per-entry verification (only CSPs the compiler emits can be tested):")
for n in sorted(emitted):
    if n not in NEW:
        print(f"  CSP {n:>2} {'':<14} emitted {emitted[n]:>3}x   NOT IN TABLE")
        continue
    truth = NEW[n]
    best_other, best_cand = -1, None
    for cand in CANDIDATES:
        if cand == truth:
            continue
        use({**NEW, n: cand})
        s = score()
        if s > best_other:
            best_other, best_cand = s, cand
    use(NEW)
    label = CSP.get(n, "?")
    margin = new_score - best_other
    if margin > 0:
        verdict = "corroborated by binary"
    elif margin == 0:
        verdict = f"tie with {best_cand} -- binary gives no signal"
    else:
        verdict = f"CONTRADICTED: {best_cand} scores {-margin} higher"
    print(f"  CSP {n:>2} {label:<14} emitted {emitted[n]:>3}x   "
          f"{truth}   margin {margin:+d}   {verdict}")
