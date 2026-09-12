"""Decide which VAR parameter types occupy two stack words.

OUTCOME: no type-based rule works, and this hypothesis was rejected. Kept
as the record of that. The best scoring rule here, {FIB, WINDOW}, fixes
FBLOCKIO and immediately breaks FCLOSE, which is declared with the same
`VAR F: FIB` and whose call sites supply one word for it. A rule cannot be
right and wrong about the same declaration.

The real explanation is finding 8: GLOBALS.TEXT is the *generic* UCSD II.0
operating system, not Apple's, so its declarations are a default rather
than evidence. Individual routines are overridden from call-site evidence
instead, by tools/probes/probe_os_arity.py. Use that one.


UCSD passes a reference into a packed object as a (base, index) pair rather
than one address. The segment-0 declarations in GLOBALS.TEXT do not say
which types that applies to -- FBLOCKIO is declared with six parameters and
its call sites push eight words -- so the rule has to come from the binary.

Scored on the whole compiler, both releases. Two numbers, both of which a
wrong rule inflates:

  residue   values still on the evaluation stack where nothing can consume
            them, i.e. arguments that were never attributed to a call
  conflict  joins where two paths disagree about how deep the stack is,
            which is what an undercounted callee produces downstream

The right rule should minimise both at once. A rule that trades one for the
other is not obviously right and is reported as such.
"""
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import a2pascal.syscall as sc
import a2pascal.lift as lift_mod
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile

ROOT = Path(__file__).resolve().parents[2]
DISKS = ("Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk",
         "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk")

# Every type that appears as a VAR parameter in the segment-0 forward
# declarations. CHAR and INTEGER are scalars and cannot be two words; they
# are included so the search can confirm that rather than assume it.
CANDIDATES = ["FIB", "WINDOW", "STRING", "DIRENTRY", "DIRP", "TID", "VID",
              "FILEKIND", "INTEGER", "CHAR"]

PROCS = []
for f in DISKS:
    d = PascalDisk.from_file(ROOT / "evidence" / "disks" / f)
    e = d.find("SYSTEM.COMPILER")
    cf = CodeFile(d.read_blocks(e.first_block, e.blocks))
    PROCS += [(s, p, cf) for s in cf.segments for p in s.pcode_procedures]

GLOBALS = ROOT / "reference_source" / "ucsd_ii0" / "GLOBALS.TEXT"


def score(two_word):
    sc.VAR_TWO_WORD = set(two_word)
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
    return residue, conflict


print(f"{len(PROCS)} procedures, both releases\n")
print(f"{'VAR types passed as 2 words':<40} {'residue':>8} {'conflict':>9}"
      f" {'total':>7}")
print("-" * 68)

results = []
# Search single types and pairs; the true rule is unlikely to be larger,
# and an exhaustive subset search over 10 candidates is not worth the time.
subsets = [()] + [(c,) for c in CANDIDATES] + \
    list(itertools.combinations(CANDIDATES, 2))
for sub in subsets:
    r, c = score(sub)
    results.append((r + c, r, c, sub))

results.sort()
for tot, r, c, sub in results[:12]:
    label = ", ".join(sub) if sub else "(none -- every VAR is 1 word)"
    print(f"{label:<40} {r:>8} {c:>9} {tot:>7}")

best = results[0]
print(f"\nbest: {', '.join(best[3]) or 'none'}")
ties = [x for x in results if x[0] == best[0]]
if len(ties) > 1:
    print(f"  TIED with {len(ties) - 1} other rule(s): "
          + "; ".join(", ".join(t[3]) or "none" for t in ties[1:]))
