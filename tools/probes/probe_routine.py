"""Is ROUTINE the standard-procedure compiler, and which handler is which?

`ROUTINE(LKEY)` in bodypart.b.text is a `case` over the standard
procedures and functions, and each arm ends by emitting the p-code that
calls the run-time. Those opcodes are *literal operands* in Apple's
binary -- `GEN1(30(*CSP*), 4(*XIT*))` compiles to `SLDC 30; SLDC 4;
CXP 9,5` -- so the source's own comments name the arms, and the binary
either agrees or it does not.

That makes this the strongest kind of naming evidence available here:
not "this procedure looks like EXIT" but "this procedure is the only one
in the segment that emits CSP 4, and CSP 4 is XIT". The probe states the
ownership exactly, so two handlers cannot be swapped without a failure,
and a handler that emitted nothing distinctive could not be claimed at
all.

  * **CSP** -- `GEN1(30, n)`, a call to the run-time support procedure n.
  * **CXP 0,n** -- `GEN2(77, 0, n)`, a call to segment 0 procedure n,
    which `tools/a2pascal/syscall.py` names from the II.0 OS source.
  * **GEN0** -- a bare opcode, which is what the arithmetic arms emit.

Three of ROUTINE's seventeen are Apple's own factorings, and they are
pinned by shape and call set instead: `GETCOMMA` is fourteen bytes of
`if sy = comma then insymbol else error(20)`, `CHECKINT` is nine bytes of
`if GATTR.TYPTR <> INTPTR then error(125)`, and `SPECIALS` holds the
cases II.0's `CALL` keeps inline.

Both releases, identical procedure numbers. Finding 35.
"""
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.pcode import disassemble
from a2pascal.names import procname

ROOT = Path(__file__).resolve().parent.parent.parent
DISKS = {
    "1.1": "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk",
    "1.3": "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk",
}

# Which ROUTINE procedures emit a given CSP number, and nothing else may.
# The gloss on the right is II.0's own comment at the emitting site.
CSP_OWNER = {
    1:  ({5},  "NEW"),
    2:  ({6},  "MVL, moveleft"),
    3:  ({6},  "MVR, moveright"),
    10: ({6},  "FLC, fillchar"),
    4:  ({7},  "XIT, exit"),
    5:  ({8},  "UNITREAD"),
    6:  ({8},  "UNITWRITE"),
    11: ({14}, "SCN, scan"),
    9:  ({17}, "TIM, time"),
    23: ({17}, "TRUNC"),
}

# ...and likewise for CXP 0,n -- a call into segment 0.
CXP0_OWNER = {
    23: ({9},  "SCONCAT"),
    25: ({10}, "SCOPY"),
    26: ({10}, "SDELETE"),
    29: ({10}, "GOTOXY"),
    6:  ({12}, "FCLOSE"),
    7:  ({13}, "FGET"),
    8:  ({13}, "FPUT"),
    28: ({15}, "BLOCKIO"),
    10: ({17}, "FEOF"),
    11: ({17}, "FEOLN"),
    4:  ({17}, "FRESET"),
    5:  ({17}, "FOPEN"),
}

# (number, name, param bytes or None, lex, must call, must not call)
CLAIMS = [
    (1,  "ROUTINE",    12, 2, [], []),
    (2,  "GETCOMMA",    0, 3, ["INSYMBOL", "ERROR"], ["STRGVAR"]),
    (3,  "CHECKINT",    0, 3, ["ERROR"], ["INSYMBOL"]),
    (4,  "STRGVAR",    10, 3, ["EXPRESSION", "LOADADDRESS", "STRGTYPE"],
     ["BYTEADDRESS", "VARIABLE"]),
    (5,  "NEWSTMT",     0, 3, ["CONSTANT", "COMPTYPES"], ["BYTEADDRESS"]),
    (6,  "MOVE",        0, 3, ["VARIABLE", "BYTEADDRESS", "EXPRESSION",
                               "LOAD"], ["LOADADDRESS"]),
    (7,  "EXIT",        0, 3, ["SEARCHID", "LINKERREF"], ["EXPRESSION"]),
    (8,  "UNITIO",      0, 3, ["VARIABLE", "BYTEADDRESS", "LOAD"],
     ["LOADADDRESS"]),
    (9,  "CONCAT",      0, 3, ["STRGVAR"], ["LOAD"]),
    (10, "COPYDELETE",  0, 3, ["STRGVAR", "EXPRESSION", "LOAD"], []),
    (11, "STR",         0, 3, ["STRGVAR", "GENNR", "COMPTYPES", "STRGTYPE"],
     ["EXPRESSION"]),
    (12, "CLOSE",       0, 3, ["VARIABLE", "LOADADDRESS"], ["BYTEADDRESS"]),
    (13, "GETPUTETC",   0, 3, ["VARIABLE", "LOADADDRESS", "GENNR"],
     ["BYTEADDRESS"]),
    (14, "SCAN",        0, 3, ["VARIABLE", "BYTEADDRESS", "EXPRESSION"],
     ["LOADADDRESS"]),
    (15, "BLOCKIO",     0, 3, ["VARIABLE", "LOADADDRESS", "BYTEADDRESS",
                               "EXPRESSION", "LOAD"], []),
    (16, "SIZEOF",      0, 3, ["SEARCHID", "GENLDC"], ["EXPRESSION"]),
    (17, "SPECIALS",    0, 3, ["STRGVAR", "GEN0", "LOAD"], []),
]


def emitted(seg, p, segmap):
    """(csp numbers, cxp0 numbers) this procedure emits as literals."""
    body, _ = disassemble(seg.data, p.enter_ic, p.exit_ic, p.jtab)
    csp, cxp0 = set(), set()
    for k, ins in enumerate(body):
        if ins.mnemonic != "CXP":
            continue
        s, n = ins.operands
        tgt = f"{segmap.get(s, s)}.{n}"
        window = body[max(0, k - 6):k]
        consts = [x.operands[0] for x in window
                  if x.mnemonic in ("SLDC", "LDCI")]
        if tgt == "BODYPART.5" and len(consts) >= 2 and consts[-2] == 30:
            csp.add(consts[-1])            # GEN1(30 CSP, n)
        elif tgt == "BODYPART.6" and len(consts) >= 3 \
                and consts[-3] == 77 and consts[-2] == 0:
            cxp0.add(consts[-1])           # GEN2(77 CXP, 0 SYS, n)
    return csp, cxp0


def main() -> int:
    bad, checked = [], 0
    for ver, dsk in DISKS.items():
        disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / dsk)
        e = disk.find("SYSTEM.COMPILER")
        cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))
        segmap = {s.seg_num: s.name for s in cf.segments}
        seg = next(s for s in cf.segments if s.name == "ROUTINE")
        procs = {p.number: p for p in seg.procedures}
        if len(procs) != 17:
            bad.append(f"{ver}: ROUTINE has {len(procs)} procedures, not 17")

        csp_by, cxp_by = defaultdict(set), defaultdict(set)
        calls = {}
        for p in seg.pcode_procedures:
            csp, cxp0 = emitted(seg, p, segmap)
            for n in csp:
                csp_by[n].add(p.number)
            for n in cxp0:
                cxp_by[n].add(p.number)
            body, _ = disassemble(seg.data, p.enter_ic, p.exit_ic, p.jtab)
            out = set()
            for ins in body:
                if ins.mnemonic == "CXP" and ins.operands[0] != 0:
                    out.add((segmap.get(ins.operands[0]), ins.operands[1]))
                elif ins.mnemonic in ("CLP", "CGP", "CIP", "CBP"):
                    out.add((seg.name, ins.operands[0]))
            calls[p.number] = {procname(s, n, ver) or f"{s}.{n}"
                               for s, n in out}

        for table, by, what in ((CSP_OWNER, csp_by, "CSP"),
                                (CXP0_OWNER, cxp_by, "CXP 0,")):
            for n, (owners, gloss) in table.items():
                checked += 1
                got = by.get(n, set())
                if got != owners:
                    bad.append(
                        f"{ver}: {what}{n} ({gloss}) is emitted by ROUTINE "
                        f"{sorted(got)}, but the source puts it in "
                        + ", ".join(f"{o}:{procname('ROUTINE', o, ver)}"
                                    for o in sorted(owners)))

        for num, name, param, lex, must, mustnot in CLAIMS:
            checked += 1
            got = procname("ROUTINE", num, ver)
            if got != name:
                bad.append(f"{ver}: names.py calls ROUTINE.{num} {got!r}, "
                           f"this probe claims {name!r}")
                continue
            p = procs.get(num)
            if p is None:
                bad.append(f"{ver}: ROUTINE.{num} ({name}) is missing")
                continue
            if param is not None and p.param_size != param:
                bad.append(f"{ver}: {name} takes {p.param_size} bytes of "
                           f"parameters, II.0's signature needs {param}")
            if p.lex_level != lex:
                bad.append(f"{ver}: {name} is at lex {p.lex_level}, "
                           f"expected {lex}")
            for want in must:
                if want not in calls[num]:
                    bad.append(f"{ver}: {name} does not call {want}")
            for no in mustnot:
                if no in calls[num]:
                    bad.append(f"{ver}: {name} calls {no}, which II.0's "
                               f"{name} does not")

        print(f"{ver}: ROUTINE, 17 procedures, "
              f"{len(CSP_OWNER)} CSP and {len(CXP0_OWNER)} CXP 0 numbers "
              f"each owned by exactly one handler")

    if bad:
        print("\n".join(bad))
        return 1
    print(f"{checked} claims, both releases, all hold")
    print("routine-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
