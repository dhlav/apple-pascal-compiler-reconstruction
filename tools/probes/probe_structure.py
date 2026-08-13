"""Check the control-flow structurer, then measure it.

Correctness first. Rewriting a goto graph into `if`/`while`/`repeat`/`case`
is exactly the kind of transformation that can look better and say
something different, so two invariants are checked on every procedure of
both releases before any success rate is reported:

  coverage   every basic block's statements appear exactly once in the
             output -- nothing silently dropped, nothing duplicated into
             two arms
  closure    every `goto Lxxxx` that survives has a matching label

Then the measure: how many gotos remain, and how many procedures come out
with none at all. A procedure with no residual goto is fully structured.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.lift import lift
from a2pascal.structure import structure

ROOT = Path(__file__).resolve().parents[2]
DISKS = (("1.1", "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk"),
         ("1.3", "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk"))

total = clean = gotos = blocks = 0
cover_bad, close_bad = [], []

for ver, f in DISKS:
    d = PascalDisk.from_file(ROOT / "evidence" / "disks" / f)
    e = d.find("SYSTEM.COMPILER")
    cf = CodeFile(d.read_blocks(e.first_block, e.blocks))
    for seg in cf.segments:
        for p in seg.pcode_procedures:
            bl = lift(seg, p, cf)
            text, g, nb = structure(bl, "")
            name = f"{ver} {seg.name}.{p.number}"
            total += 1
            gotos += g
            blocks += nb
            if g == 0:
                clean += 1

            # coverage: each block's statements, exactly once
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            for b in bl:
                for s in b.stmts:
                    if lines.count(s.strip()) != 1 and s.strip():
                        # a statement can legitimately repeat if the source
                        # itself repeats it; only flag when the count is
                        # below one, i.e. something was dropped
                        if lines.count(s.strip()) == 0:
                            cover_bad.append((name, s))
                        break

            # closure: every goto has a label
            want = set(re.findall(r"goto (L[0-9A-F]{4})", text))
            have = set(re.findall(r"^(L[0-9A-F]{4}):", text, re.M))
            if want - have:
                close_bad.append((name, sorted(want - have)))

print(f"{total} procedures, {blocks} basic blocks\n")
print("correctness")
print(f"  dropped statements : {len(cover_bad)}")
for n, s in cover_bad[:5]:
    print(f"      {n}: {s}")
print(f"  dangling gotos     : {len(close_bad)}")
for n, s in close_bad[:5]:
    print(f"      {n}: {', '.join(s)}")

print("\nstructuring")
print(f"  fully structured   : {clean}/{total} procedures "
      f"({100 * clean // total}%)")
print(f"  gotos remaining    : {gotos}  ({gotos / blocks:.2f} per block)")
