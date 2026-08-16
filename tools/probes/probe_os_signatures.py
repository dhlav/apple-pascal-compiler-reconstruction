"""Check the II.0 segment-0 declarations against Apple's own binary.

Until finding 50 this could only print what `GLOBALS.TEXT` declares, because
`SYSTEM.PASCAL` would not parse and there was nothing to check it against.
Now there is: Apple's segment 0 states every procedure's parameter size in
its own attribute tables, and the two lists can be laid side by side.

They agree for procedures 1 through 42 -- name order, word count and
procedure-versus-function -- in 1.1, in 1.3, and in the 128K build. That
matters twice over. It extends the *verified* segment-0 numbering from 29
(finding 18, against Miller's table) to 42, from an independent direction.
And it confirms on ten functions at once that a UCSD frame carries the
two-word result slot inside the parameter area, which is what a declared
argument count has to be adjusted by before it can be compared.

Procedure 43 is where it parts company, and the probe requires that too --
a check that only says "they agree" would pass just as well on a table
someone had quietly aligned. II.0's 43rd declaration is COMMAND and takes
nothing; Apple's 43 takes three words in every build.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.pcode import disassemble, sweep_exit
from a2pascal import syscall as sc

ROOT = Path(__file__).resolve().parents[2]
BUILDS = [
    ("1.1", "UCSD Pascal 1.1_1.dsk", "SYSTEM.PASCAL"),
    ("1.3", "Apple II Pascal 1.3 APPLE1_ 680-0283-A.dsk", "SYSTEM.PASCAL"),
    ("1.3-128K", "Apple II Pascal 1.3 APPLE3_ 680-0290-A.dsk", "128K.PASCAL"),
]
AGREE_THROUGH = 42          # and 43 must differ

# The declarations, with every adjustment this repo applies stripped back
# out, so the comparison is against UCSD's source and not against itself.
raw_overrides = dict(sc.OS_WORD_OVERRIDE)
raw_binary = dict(sc.OS_FRAME_FROM_BINARY)
sc.OS_WORD_OVERRIDE.clear()
sc.OS_FRAME_FROM_BINARY.clear()
DECL = sc.segment0_signatures(ROOT / "reference_source" / "ucsd_ii0" / "GLOBALS.TEXT")
sc.OS_WORD_OVERRIDE.update(raw_overrides)
sc.OS_FRAME_FROM_BINARY.update(raw_binary)

fails = []
checks = 0


def check(cond, what):
    global checks
    checks += 1
    if not cond:
        fails.append(what)


def frame_of(seg, p) -> tuple[int, bool]:
    """(parameter words, is a function) as the binary states them."""
    for i in reversed(disassemble(seg.data, p.enter_ic, p.exit_ic, p.jtab)[0]
                      + sweep_exit(seg.data, p.exit_ic, p.jtab - 8, p.jtab)[0]):
        if i.mnemonic in ("RNP", "RBP"):
            return p.param_size // 2, i.operands[0] != 0
    return p.param_size // 2, False


check(len(DECL) == 43, f"GLOBALS.TEXT yields {len(DECL)} declarations, want 43")
check(not raw_overrides,
      f"OS_WORD_OVERRIDE is no longer needed but holds {sorted(raw_overrides)}")

for ver, dsk, fn in BUILDS:
    disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / dsk)
    e = disk.find(fn)
    seg = CodeFile(disk.read_blocks(e.first_block, e.blocks)).segments[0]
    procs = {p.number: p for p in seg.procedures}
    nfunc = 0
    for n in sorted(DECL):
        name, decl_words, decl_fn = DECL[n]
        p = procs.get(n)
        check(p is not None, f"{ver}: segment 0 has no procedure {n} ({name})")
        if p is None:
            continue
        got_words, got_fn = frame_of(seg, p)
        # segment0_signatures already turns the declared argument count into
        # a frame by adding the result slot, so this compares frames.
        want = decl_words
        nfunc += decl_fn
        if n <= AGREE_THROUGH:
            check(got_fn == decl_fn,
                  f"{ver}: {n} {name} is a "
                  f"{'function' if decl_fn else 'procedure'} in II.0 but "
                  f"{'a function' if got_fn else 'a procedure'} in the binary")
            check(got_words == want,
                  f"{ver}: {n} {name} wants a {want}-word frame"
                  f"{' (args + result slot)' if decl_fn else ''}, "
                  f"binary has {got_words}")
        else:
            # 43. If this ever starts agreeing, the divergence claim is
            # wrong and the reader should say so rather than quietly pass.
            check(got_words != want or got_fn != decl_fn,
                  f"{ver}: {n} {name} now agrees with the binary; "
                  f"the numbering does not diverge at 43 after all")
            check(got_words == 3 and not got_fn,
                  f"{ver}: procedure 43 has {got_words}w fn={got_fn}, want 3w "
                  f"procedure")
    check(nfunc == 10,
          f"{ver}: {nfunc} functions among the declarations, want 10")

print(f"{checks} checks, {len(fails)} failures "
      f"(II.0 declarations 1..{AGREE_THROUGH} confirmed against "
      f"{len(BUILDS)} builds)")
for f in fails[:20]:
    print("  FAIL", f)
sys.exit(1 if fails else 0)
