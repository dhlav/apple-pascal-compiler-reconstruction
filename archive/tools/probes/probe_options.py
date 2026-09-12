"""Check the compiler-option globals against COMPOPTI.1's own case table.

Finding 23c reads the option letter -> global mapping off the `XJP` in
`COMPOPTI.1`: each arm of that case sets one global from the option's `+`
or `-` argument. This re-derives the mapping from the binary and compares
it with `names.py`, in both releases, so that renaming a global wrongly --
or a decoder change that shifts the jump table -- fails here rather than
quietly mislabelling every listing.

It also re-checks the one claim the manual makes about the arms rather than
about a single option: that `{$U-}` sets R-, G+, I-, V- (II-155).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.pcode import disassemble
from a2pascal.names import GLOBAL_NAMES

ROOT = Path(__file__).resolve().parent.parent.parent
DISKS = {
    "1.1": "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk",
    "1.3": "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk",
}

# What each letter's arm is expected to write, by the name in names.py.
# Letters whose arm does something other than set one flag from the
# argument (C, I, L, N, P, R, S, U) are checked separately or not at all.
SIMPLE = {
    "D": "DEBUGGING", "E": "OPT_E", "F": "FLIPBYTES", "G": "GOTOOK",
    "Q": "NOISY", "T": "TINY", "V": "VARSTRG",
}
# The globals {$U-} must write, per the manual.
U_ARM = {"SYSCOMP", "RANGECHECK", "IOCHECK", "VARSTRG", "GOTOOK"}


def arms(seg, proc):
    """Case value -> instructions of that arm, up to the arm's exit jump."""
    ins = disassemble(seg.data, proc.enter_ic, proc.exit_ic, proc.jtab)[0]
    xjp = next(i for i in ins if i.mnemonic == "XJP")
    lo, _hi, dflt, table = xjp.operands
    by_addr = {i.addr: k for k, i in enumerate(ins)}
    out = {}
    for n, addr in enumerate(table):
        if addr == dflt:
            continue
        k = by_addr[addr]
        body = []
        while k < len(ins) and ins[k].mnemonic != "UJP":
            body.append(ins[k])
            k += 1
        out[chr(lo + n)] = body
    return out


def first_store(body, names):
    for i in body:
        if i.mnemonic in ("SRO", "STO"):
            return names.get(i.operands[0]) if i.operands else None
    return None


def main():
    bad = []
    for ver, dsk in DISKS.items():
        disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / dsk)
        e = disk.find("SYSTEM.COMPILER")
        cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))
        seg = cf.segment("COMPOPTI")
        proc = next(p for p in seg.procedures if p.number == 1)
        names = GLOBAL_NAMES[ver]
        table = arms(seg, proc)

        for letter, want in SIMPLE.items():
            got = first_store(table.get(letter, []), names)
            if got != want:
                bad.append(f"{ver} ${letter}: expected {want}, arm writes {got}")

        wrote = {names[i.operands[0]] for i in table.get("U", [])
                 if i.mnemonic == "SRO" and i.operands[0] in names}
        if wrote != U_ARM:
            bad.append(f"{ver} $U- arm writes {sorted(wrote)}, "
                       f"expected {sorted(U_ARM)}")

    print("\n".join(bad) if bad else "options-ok")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
