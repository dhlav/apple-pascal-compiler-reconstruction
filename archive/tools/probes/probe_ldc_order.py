"""Which word of an `LDC` block is word 0 of the value?

`LDC UB` is followed by UB words of inline constant. The decoder has to
decide whether the first word in the code stream is word 0 of the value or
the last one is, and for a *set* constant that decision renames every
member: word j holds members 16j..16j+15, so getting it backwards permutes
the set beyond recognition.

The compiler contains a check for this that it cannot pass by accident.
`COMPINIT` enters the standard identifiers from a run of `LSA` string
literals -- 'READ.READLN.WRITE.' and so on, 44 names, in order -- and then
loops over them with a 1-based counter, testing that counter against two
inline set constants:

    LDO <OPT_T> / FJP ...   ; if {$T+}
    SLDL 2 / LDC 3w / SLDC 3 / INN / FJP ...   ; and this one is in SET1,
                                               ; skip it: omit the built-in
    SLDL 2 / LDC 3w / SLDC 3 / INN / STL 3     ; SET2 decides ... something

So both sets are indexed by position in a list this same procedure spells
out in ASCII. That pins them:

  * every member must land in 1..44, which the wrong order violates -- it
    puts members at 0, 45 and 47;
  * SET2 must come out as exactly the value-returning built-ins, which is a
    property of the *names*, decided by Pascal and not by this decoder.

Only one of the two orders satisfies either. Finding 24d.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.pcode import disassemble

ROOT = Path(__file__).resolve().parent.parent.parent
DISKS = {
    "1.1": "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk",
    "1.3": "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk",
}

# The built-ins that return a value. This list is a fact about Pascal, not
# about the binary: it is what SET2 has to turn out to be.
FUNCTIONS = {
    "EOF", "EOLN", "PRED", "SUCC", "ORD", "SQR", "ABS", "CONCAT", "LENGTH",
    "COPY", "POS", "TREESEAR", "SCAN", "BLOCKREA", "BLOCKWRI", "TRUNC",
    "SIZEOF",
}


def members(words):
    return [16 * j + b for j, w in enumerate(words) for b in range(16)
            if w >> b & 1]


def stdident_proc(seg):
    """The COMPINIT procedure that spells out the standard identifiers."""
    for p in seg.procedures:
        if p.is_native:
            continue
        ins = disassemble(seg.data, p.enter_ic, p.exit_ic, p.jtab)[0]
        names, sets = [], []
        for i in ins:
            if i.mnemonic == "LSA":
                s = i.operands[0].decode("ascii", "replace")
                if s.endswith("."):
                    names += [n for n in s.split(".") if n]
            elif i.mnemonic == "LDC":
                sets.append(list(i.operands[0]))
        if len(names) > 30 and len(sets) == 2:
            return p, names, sets
    return None, None, None


def main():
    bad = []
    for ver, dsk in DISKS.items():
        disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / dsk)
        e = disk.find("SYSTEM.COMPILER")
        cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))
        seg = cf.segment("COMPINIT")
        proc, names, sets = stdident_proc(seg)
        if proc is None:
            bad.append(f"{ver}: no standard-identifier procedure found")
            continue

        n = len(names)
        # The decoder is expected to hand back word 0 first. Check that the
        # order it chose is the one that works, and that the other fails.
        def check(order):
            ms = [members(order(s)) for s in sets]
            in_range = all(1 <= m <= n for s in ms for m in s)
            got = {names[m - 1] for m in ms[1]} if in_range else set()
            return (in_range and got == FUNCTIONS), in_range, got

        ok, in_range, got = check(lambda w: w)
        if not ok:
            bad.append(f"{ver} COMPINIT.{proc.number}: decoded order is wrong "
                       f"-- in_range={in_range} "
                       f"SET2={sorted(got) or '<out of range>'}")
        elif check(lambda w: w[::-1])[0]:
            bad.append(f"{ver} COMPINIT.{proc.number}: BOTH orders pass, "
                       f"so this probe proves nothing")

        if not bad:
            omit = sorted(names[m - 1] for m in members(sets[0]))
            print(f"{ver} COMPINIT.{proc.number}: {n} standard identifiers; "
                  f"SET2 = the {len(FUNCTIONS)} functions exactly; "
                  f"{{$T+}} omits {len(omit)}: {' '.join(omit)}")

    if bad:
        print("\n".join(bad))
        return 1
    print("ldc-order-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
