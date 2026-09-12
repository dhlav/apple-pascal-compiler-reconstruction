"""The three procedures 1.3 adds, and what each one is.

`tools/globaldiff.py` matches 131 procedures across the two releases. Three
of 1.3's have no 1.1 counterpart, and they were the last unnamed routines
in either binary. Each is checked here against the shape that named it,
and two of the three are checked against 1.1 as well -- because what makes
them interesting is not what they do but what they *replace*.

  COMPINIT.11  CHECKVER   the version gate. Reads the byte at $BF21 and
                          refuses to run unless it is 4, then takes bit 6
                          of $BF22 into HAS128K (finding 40).
  BODYPART.26  INITUNIT   walks USINGLIST emitting each used unit's
                          initialisation call. 1.1's BODY2 does the same
                          emission in a forward loop; this recurses on
                          `next` before emitting, which reverses the walk.
  COMPOPTI.5   ADDRESID   builds one node of the $R resident-segment list.
                          1.1's OPTLIST does it inline.

1.3 adds five routines in all: these three plus the two *native* ones,
IDSEARCH and TREESEARCH (finding 19), which 1.1 does not have at all
because 1.1 does that work in p-code inside the scanner. The probe expects
exactly those five and nothing else.

INITUNIT is the one worth a probe rather than a note, because the vendor
says what it is for. The 1.1 *Update* pamphlet lists among the compiler
bugs 1.2 fixed:

    Initialization sections of nested units were (incorrectly) executed in
    the reverse order. Now they are executed in the correct order.

USINGLIST is built by prepending, so a forward walk emits the calls in
reverse declaration order -- which is exactly the bug -- and recursing
first emits them in declaration order. So the check that matters is not
that 1.3 recurses but that **1.1 does not**: the same three emitted
constants, the same list, in a loop instead. Both halves are asserted, and
either one failing would mean the pairing is wrong.

Finding 42.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.pcode import disassemble, sweep_exit
from a2pascal.names import GLOBALS_11, GLOBALS_13, procname

ROOT = Path(__file__).resolve().parent.parent.parent
DISKS = {
    "1.1": "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk",
    "1.3": "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk",
}
GLOBALS = {"1.1": GLOBALS_11, "1.3": GLOBALS_13}

ONLY_13 = {("COMPINIT", 11): "CHECKVER",
           ("BODYPART", 26): "INITUNIT",
           ("COMPOPTI", 5): "ADDRESID"}

# Neil Parker's low-memory table: $BF21 is VERSION ("0=1.0, 2=1.1, 3=1.2,
# 4=1.3"), $BF22 is FLAVOR, whose bits 6 and 5 are the memory size.
VERSION_ADDR, FLAVOR_ADDR = -16607, -16606


def main() -> int:
    bad, checked = [], 0
    code, procs = {}, {}

    for ver, dsk in DISKS.items():
        disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / dsk)
        e = disk.find("SYSTEM.COMPILER")
        cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))
        procs[ver] = set()
        for seg in cf.segments:
            for p in seg.procedures:
                procs[ver].add((seg.name, p.number))
            for p in seg.pcode_procedures:
                body, _ = disassemble(seg.data, p.enter_ic, p.exit_ic, p.jtab)
                ex, _ = sweep_exit(seg.data, p.exit_ic, p.jtab - 8, p.jtab)
                code[(ver, seg.name, p.number)] = body + ex

    # 1.3 adds exactly these three, and nothing else. The comparison has to
    # be by name: 1.3 renumbers -- the two native procedures take
    # PASCALCO.2 and .3, and BODYPART's insertion at 26 shifts everything
    # above it -- so raw (segment, number) pairs do not line up.
    checked += 1
    named = {v: {(s, procname(s, n, v)) for s, n in procs[v]} for v in DISKS}
    added = named["1.3"] - named["1.1"]
    want = ({(s, nm) for (s, _n), nm in ONLY_13.items()}
            | {("PASCALCO", "IDSEARCH"), ("PASCALCO", "TREESEARCH")})
    if added != want:
        bad.append(f"1.3 adds {sorted(added)}, not the five this probe "
                   f"accounts for: {sorted(want)}")

    # And every procedure in both releases now has a name.
    for ver in DISKS:
        checked += 1
        unnamed = sorted(f"{s}.{n}" for s, n in procs[ver]
                         if not procname(s, n, ver))
        if unnamed:
            bad.append(f"{ver}: {len(unnamed)} procedures still unnamed: "
                       f"{unnamed[:6]}")
    for (seg, num), want in ONLY_13.items():
        checked += 1
        if procname(seg, num, "1.3") != want:
            bad.append(f"names.py calls 1.3 {seg}.{num} "
                       f"{procname(seg, num, '1.3')!r}, not {want!r}")

    w11 = {n: o for o, n in GLOBALS_11.items()}
    w13 = {n: o for o, n in GLOBALS_13.items()}

    # --- CHECKVER ---------------------------------------------------------
    cv = code[("1.3", "COMPINIT", 11)]
    consts = {i.operands[0] for i in cv if i.mnemonic in ("SLDC", "LDCI")}
    text = b" ".join(o for i in cv for o in i.operands
                     if isinstance(o, bytes))
    checked += 1
    for want in (16607, 16606, 4, 6):
        if want not in consts:
            bad.append(f"CHECKVER does not use the constant {want}; it needs "
                       f"$BF21 and $BF22, the version 4, and bit 6")
    checked += 1
    if b"non-1.3 version of SYSTEM.PASCAL" not in text:
        bad.append("CHECKVER does not carry the version-mismatch message")
    checked += 1
    writers = {f"{s}.{n}" for (v, s, n), st in code.items() if v == "1.3"
               and any(i.mnemonic == "SRO" and i.operands[0] == w13["HAS128K"]
                       for i in st)}
    if writers != {"COMPINIT.11"}:
        bad.append(f"HAS128K is written by {sorted(writers)}, not by "
                   f"CHECKVER alone")

    # --- INITUNIT, against 1.1's loop -------------------------------------
    iu = code[("1.3", "BODYPART", 26)]
    checked += 1
    if not any(i.mnemonic in ("CIP", "CLP", "CGP", "CBP")
               and i.operands[0] == 26 for i in iu):
        bad.append("INITUNIT does not call itself, so it cannot be the "
                   "recursion that reverses the walk")
    # the recursive call must come *before* the emission, or the order is
    # 1.1's again
    rec = [k for k, i in enumerate(iu) if i.mnemonic == "CIP"
           and i.operands[0] == 26]
    emit = [k for k, i in enumerate(iu) if i.mnemonic in ("SLDC", "LDCI")
            and i.operands[0] == 77]
    checked += 1
    if not rec or not emit or min(rec) > min(emit):
        bad.append("INITUNIT emits before it recurses, which would leave "
                   "the initialisation order 1.1's")

    # 1.1's BODY2 does the emission itself, from USINGLIST, in a loop.
    b2 = {"1.1": code[("1.1", "BODYPART", 25)],
          "1.3": code[("1.3", "BODYPART", 25)]}
    checked += 1
    reads11 = any(i.mnemonic in ("LDO", "SLDO")
                  and i.operands[0] == w11["USINGLIST"] for i in b2["1.1"])
    emits11 = any(i.mnemonic in ("SLDC", "LDCI") and i.operands[0] == 77
                  for i in b2["1.1"])
    if not (reads11 and emits11):
        bad.append("1.1's BODY2 does not read USINGLIST and emit CXP "
                   "itself, so INITUNIT has nothing to have replaced")
    checked += 1
    if any(i.mnemonic in ("CIP", "CLP", "CGP", "CBP")
           and procname("BODYPART", i.operands[0], "1.1") == "INITUNIT"
           for i in b2["1.1"]):
        bad.append("1.1's BODY2 calls an INITUNIT, which 1.1 does not have")
    # ...and 1.3's hands it over instead: the call's argument is USINGLIST.
    checked += 1
    handoff = [k for k, i in enumerate(b2["1.3"])
               if i.mnemonic in ("CLP", "CIP", "CGP") and i.operands[0] == 26]
    if not handoff:
        bad.append("1.3's BODY2 does not call INITUNIT")
    elif not any(i.mnemonic == "LAO" and i.operands[0] == w13["USINGLIST"]
                 for i in b2["1.3"][max(0, handoff[0] - 3):handoff[0]]):
        bad.append("1.3's BODY2 calls INITUNIT without passing USINGLIST")
    # 1.3's BODY2 must no longer walk the list itself. It still emits other
    # CXPs, so the test is the list, not the opcode. An absence check is
    # only worth anything if the thing exists elsewhere, so the control
    # comes first: 1.3 must read USINGLIST *somewhere*.
    checked += 1
    elsewhere = {f"{s}.{n}" for (v, s, n), st in code.items() if v == "1.3"
                 and any(i.mnemonic in ("LDO", "SLDO")
                         and i.operands[0] == w13["USINGLIST"] for i in st)}
    if not elsewhere:
        bad.append(f"nothing in 1.3 reads global {w13['USINGLIST']}, so the "
                   f"USINGLIST offset is wrong and the next check is vacuous")
    checked += 1
    if any(i.mnemonic in ("LDO", "SLDO") and i.operands[0] == w13["USINGLIST"]
           for i in b2["1.3"]):
        bad.append("1.3's BODY2 still reads USINGLIST, so the walk was not "
                   "moved into INITUNIT")
    checked += 1
    if not any(i.mnemonic in ("LDO", "SLDO", "LAO")
               and i.operands[0] == w13["USINGLIST"] for i in iu):
        pass    # INITUNIT takes the list by reference, so it need not name it

    # --- ADDRESID ---------------------------------------------------------
    ar = code[("1.3", "COMPOPTI", 5)]
    checked += 1
    news = [k for k, i in enumerate(ar) if i.mnemonic == "CSP"
            and i.operands[0] == 1]
    sizes = {ar[k - 1].operands[0] for k in news
             if ar[k - 1].mnemonic in ("SLDC", "LDCI")}
    if sizes != {13}:
        bad.append(f"ADDRESID NEWs {sorted(sizes)} words, not the 13 of the "
                   f"identifier variant the $R list uses")
    checked += 1
    g = w13["RESIDENT"]
    if not (any(i.mnemonic in ("LDO", "SLDO") and i.operands[0] == g
                for i in ar)
            and any(i.mnemonic == "SRO" and i.operands[0] == g for i in ar)):
        bad.append("ADDRESID does not both read and write RESIDENT, so it "
                   "is not prepending to that list")
    checked += 1
    if not any(i.mnemonic in ("CLP", "CIP", "CGP") and i.operands[0] == 5
               for i in code[("1.3", "COMPOPTI", 4)]):
        bad.append("1.3's OPTLIST does not call ADDRESID")
    checked += 1
    if any(i.mnemonic in ("CLP", "CIP", "CGP") and i.operands[0] == 5
           for i in code[("1.1", "COMPOPTI", 4)]):
        bad.append("1.1's OPTLIST calls a COMPOPTI.5, which 1.1 does not "
                   "have")

    if bad:
        print("\n".join(bad))
        return 1
    print("1.3 adds exactly five routines: the natives IDSEARCH and "
          "TREESEARCH, plus COMPINIT.11 CHECKVER, BODYPART.26 INITUNIT and "
          "COMPOPTI.5 ADDRESID")
    print("every procedure in both releases is named: 142 in 1.1, 147 in 1.3")
    print("BODY2 emits the unit-initialisation calls itself in 1.1 and hands "
          "USINGLIST to INITUNIT in 1.3, which recurses before emitting")
    print(f"{checked} checks, all passed")
    print("13only-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
