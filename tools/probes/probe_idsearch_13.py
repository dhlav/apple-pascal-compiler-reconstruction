"""Test: did 1.3 replace CSP 7 (IDSEARCH) / CSP 8 (TREESEARCH) with the two
native 6502 procedures added to PASCALCO?

1.1 uses CSP 7 once and CSP 8 four times; 1.3 uses neither, and has gained
exactly two native procedures, PASCALCO.2 and PASCALCO.3. If the hypothesis
holds, the call sites should line up in the same procedures with the same
argument setup.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.pcode import disassemble, sweep_exit

ROOT = Path(__file__).resolve().parents[2]
DISKS = {
    "1.1": "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk",
    "1.3": "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk",
}


def sites(fname, pred, ctx=5):
    disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / fname)
    e = disk.find("SYSTEM.COMPILER")
    cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))
    out = []
    for s in cf.segments:
        for p in s.pcode_procedures:
            b, _ = disassemble(s.data, p.enter_ic, p.exit_ic, p.jtab)
            x, _ = sweep_exit(s.data, p.exit_ic, p.jtab - 8, p.jtab)
            st = b + x
            for k, i in enumerate(st):
                if pred(i):
                    out.append((f"{s.name}.{p.number}", i.addr,
                                [q.text for q in st[max(0, k - ctx):k + 1]]))
    return out


def show(label, rows):
    print(f"=== {label}  ({len(rows)} site(s))")
    for w, a, c in rows:
        print(f"  {w:<14} ${a:04X}:  " + "  |  ".join(c))
    print()


show("1.1 CSP 7 IDSEARCH",
     sites(DISKS["1.1"], lambda i: i.mnemonic == "CSP" and i.operands[0] == 7))
show("1.1 CSP 8 TREESEARCH",
     sites(DISKS["1.1"], lambda i: i.mnemonic == "CSP" and i.operands[0] == 8))

# Only CGP (call global procedure -- i.e. into the base segment PASCALCO)
# and an explicit CXP 1,n reference PASCALCO's procedures. A bare CLP/CIP 2
# is procedure 2 of whatever segment we are already in, which is unrelated.
is_call23 = lambda i: ((i.mnemonic == "CXP" and i.operands[0] == 1
                        and i.operands[1] in (2, 3))
                       or (i.mnemonic == "CGP" and i.operands[0] in (2, 3)))
show("1.3 calls to PASCALCO.2 / PASCALCO.3 (the native pair)",
     sites(DISKS["1.3"], is_call23))

print("""Conclusion: 1 CSP 7 site maps to 1 CGP 2 site and 4 CSP 8 sites map to
4 CGP 3 sites, each in the correspondingly renumbered procedure (1.3 adds
two procedures at slots 2-3, so 1.1 proc N is 1.3 proc N+2) and with
identical argument setup. PASCALCO.2 = IDSEARCH, PASCALCO.3 = TREESEARCH,
the latter having gained two extra parameters (pushed as SLDC 0).""")
