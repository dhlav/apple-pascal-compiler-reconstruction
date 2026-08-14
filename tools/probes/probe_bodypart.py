"""BODYPART, all of it -- and what Apple did to II.0's `BODY`.

With finding 36 every procedure in BODYPART has a name: 37 in 1.1, 37 of
1.3's 38. This probe holds the ones finding 36 adds against the binary.

The claim worth stating first is the structural one. II.0's `BODY` is a
single procedure. Apple split it into four pieces, and named two of them
in the codefile itself -- SEGMENT procedures BODY1 and BODY3 (finding
30). So the split is not an inference; only the middle piece's name is.
What the binary does fix:

  * BODYPART.24 calls **BODY1, then a local procedure, then BODY3**, in
    that order and nothing else;
  * BODYPART.24 carries **38 bytes of locals** while the piece it calls
    carries 4, which is the frame those pieces share;
  * BODY1.1, BODYPART.25 and BODY3.1 all sit at the **same lexical
    level**, one deeper than 24 -- they are siblings inside it.

Given Apple named the outer pieces BODY1 and BODY3, the sibling between
them is BODY2 and their parent is `BODY`. That last step is inference.

The rest are checked the way findings 34 and 35 check theirs -- parameter
size, lexical level, call set, and for the code generators the constants
they emit:

  * `MASKBOOL` emits bytes 1 and 132 -- `SLDC 1; LAND` -- and only when
    GATTR.TYPTR is BOOLPTR;
  * `LOADIDADDR` emits GEN2 50 (LDA) and 54 (LOD) and nothing else;
  * `HOLDSTMT` and `HOLDRTN` each wrap one call in LOADSEGMENT /
    UNLOADSEGMENT of a segment named through the codefile, so naming the
    wrong segment fails;
  * `WRITE` is one of only two procedures in BODYPART that call DECSIZE,
    which is what writing a long integer needs -- the other is FACTOR,
    for a long-integer literal, and `READ` is not among them;
  * `STRGTOPA` calls nothing at all -- it patches code already emitted.

And `LINKINFO` (global 44 in 1.1, 45 in 1.3): Apple merged II.0's
DLINKERINFO and CLINKERINFO, so the procedures that store into it must be
exactly the union of II.0's two sets.

Finding 36.
"""
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.pcode import disassemble, sweep_exit
from a2pascal.names import GLOBALS_11, GLOBALS_13, procname

ROOT = Path(__file__).resolve().parent.parent.parent
GLOBALS = {"1.1": GLOBALS_11, "1.3": GLOBALS_13}
DISKS = {
    "1.1": "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk",
    "1.3": "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk",
}

# (1.1 number, name, param bytes or None, lex, must call, must not call)
CLAIMS = [
    ("LOADIDADDR",  2,  2, [], ["ERROR", "INSYMBOL"]),
    ("MASKBOOL",    0,  2, ["GENBYTE"], ["GEN0", "GENLDC", "ERROR"]),
    ("STORE",       2,  2, ["GEN0", "GEN1", "GEN2", "ERROR"], ["INSYMBOL"]),
    ("STRGTOPA",    2,  2, [], ["GENBYTE", "GEN0", "ERROR", "INSYMBOL"]),
    ("CALL",       10,  2, ["READ", "WRITE", "CALLNONSPECIAL", "ROUTINE",
                            "LOAD", "EXPRESSION"], ["SELECTOR"]),
    ("BODY",        0,  2, ["BODY1", "BODY3"], ["STATEMENT", "ERROR"]),
    ("BODY2",       0,  3, ["STATEMENT", "INSYMBOL"], ["BODY1", "BODY3"]),
    ("HOLDSTMT",    0,  3, ["BODY2"], ["BODY1", "BODY3", "STATEMENT"]),
    ("READ",        0,  3, ["VARIABLE", "LOADIDADDR", "LOADADDRESS"],
     ["DECSIZE", "EXPRESSION"]),
    ("WRITE",       0,  3, ["LOADIDADDR", "DECSIZE", "PAOFCHAR",
                            "EXPRESSION", "LOAD"], []),
    ("CALLNONSPECIAL", 0, 3, ["LINKERREF", "NEWPROC", "STRGTOPA",
                              "EXPRESSION", "LOAD"], ["VARIABLE"]),
    ("FLOATIT",     4,  3, ["GEN0"], ["ERROR"]),
    ("STRETCHIT",   2,  3, ["GENLDC", "GENNR"], ["GEN0"]),
    ("MAKEPA",   None,  3, ["ERROR", "GETBOUNDS"], ["GEN0"]),
    ("HOLDRTN",     0,  2, ["BODY"], ["BODY2", "BODY1"]),
]

# Walking back for an emitter's arguments stops at a call or a branch:
# the arguments of one call cannot cross a basic-block boundary.
CALLS = ("CXP", "CLP", "CGP", "CIP", "CBP", "CSP",
         "UJP", "FJP", "TJP", "XJP", "EFJ", "NFJ")

# name -> the segment it must hold resident while it makes its one call
HOLDS = {"HOLDSTMT": "STATEMEN", "HOLDRTN": "ROUTINE"}


def main() -> int:
    bad, checked = [], 0
    for ver, dsk in DISKS.items():
        disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / dsk)
        e = disk.find("SYSTEM.COMPILER")
        cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))
        segmap = {s.seg_num: s.name for s in cf.segments}
        segnum = {s.name: s.seg_num for s in cf.segments}
        seg = next(s for s in cf.segments if s.name == "BODYPART")
        procs = {p.number: p for p in seg.procedures}
        byname = {procname("BODYPART", n, ver): n for n in procs
                  if procname("BODYPART", n, ver)}

        # Every procedure named, except the one 1.3 inserts.
        unnamed = sorted(n for n in procs if not procname("BODYPART", n, ver))
        want = [] if ver == "1.1" else [26]
        if unnamed != want:
            bad.append(f"{ver}: BODYPART procedures without a name: "
                       f"{unnamed}, expected {want}")

        calls, emits, holds = {}, defaultdict(list), {}
        for p in seg.pcode_procedures:
            body, _ = disassemble(seg.data, p.enter_ic, p.exit_ic, p.jtab)
            ex, _ = sweep_exit(seg.data, p.exit_ic, p.jtab - 8, p.jtab)
            body = body + ex
            out = set()
            for k, ins in enumerate(body):
                if ins.mnemonic == "CXP" and ins.operands[0] != 0:
                    s, n = ins.operands
                    out.add(procname(segmap.get(s), n, ver) or f"{s}.{n}")
                elif ins.mnemonic in ("CLP", "CGP", "CIP", "CBP"):
                    out.add(procname("BODYPART", ins.operands[0], ver)
                            or f"BODYPART.{ins.operands[0]}")
                elif ins.mnemonic == "CSP" and ins.operands[0] in (21, 22):
                    prev = body[k - 1]
                    if prev.mnemonic in ("SLDC", "LDCI"):
                        holds.setdefault(p.number, set()).add(prev.operands[0])
                if ins.mnemonic not in ("CXP", "CLP", "CGP", "CIP", "CBP"):
                    continue
                if ins.mnemonic == "CXP":
                    tgt = procname(segmap.get(ins.operands[0]),
                                   ins.operands[1], ver)
                else:
                    tgt = procname("BODYPART", ins.operands[0], ver)
                if tgt not in ("GENBYTE", "GEN2"):
                    continue
                # The literals pushed since the previous call: the first
                # of them is the emitter's opcode argument.
                consts, j = [], k - 1
                while j >= 0 and body[j].mnemonic not in CALLS:
                    if body[j].mnemonic in ("SLDC", "LDCI"):
                        consts.append(body[j].operands[0])
                    j -= 1
                if consts:
                    emits[(p.number, tgt)].append(consts[-1])
            calls[p.number] = out

        for name, param, lex, must, mustnot in CLAIMS:
            checked += 1
            num = byname.get(name)
            if num is None:
                bad.append(f"{ver}: names.py has no BODYPART procedure "
                           f"called {name}")
                continue
            p = procs[num]
            if param is not None and p.param_size != param:
                bad.append(f"{ver}: {name} takes {p.param_size} bytes of "
                           f"parameters, expected {param}")
            if p.lex_level != lex:
                bad.append(f"{ver}: {name} is at lex {p.lex_level}, "
                           f"expected {lex}")
            for w in must:
                if w not in calls[num]:
                    bad.append(f"{ver}: {name} does not call {w}")
            for w in mustnot:
                if w in calls[num]:
                    bad.append(f"{ver}: {name} calls {w}, and should not")

        # BODY's three pieces are siblings one level inside it.
        body_n, body2_n = byname["BODY"], byname["BODY2"]
        checked += 1
        if procs[body_n].data_size != 38:
            bad.append(f"{ver}: BODY carries {procs[body_n].data_size} bytes "
                       f"of locals, not the 38 its pieces share")
        levels = {"BODY2": procs[body2_n].lex_level}
        for s in ("BODY1", "BODY3"):
            other = next(x for x in cf.segments if x.name == s)
            levels[s] = next(q for q in other.procedures
                             if q.number == 1).lex_level
        if len(set(levels.values())) != 1:
            bad.append(f"{ver}: BODY1, BODY2 and BODY3 are at lex "
                       f"{levels}, so they are not siblings")
        elif set(levels.values()) != {procs[body_n].lex_level + 1}:
            bad.append(f"{ver}: BODY1/BODY2/BODY3 sit at lex "
                       f"{set(levels.values())}, not one inside BODY at lex "
                       f"{procs[body_n].lex_level}")

        # The two segment-holding wrappers hold the right segment.
        for name, held in HOLDS.items():
            checked += 1
            num = byname[name]
            got = holds.get(num, set())
            if got != {segnum[held]}:
                bad.append(f"{ver}: {name} loads segment(s) "
                           f"{sorted(segmap.get(g, g) for g in got)}, "
                           f"expected just {held}")

        # MASKBOOL emits SLDC 1; LAND, and LOADIDADDR emits LDA and LOD.
        checked += 2
        if sorted(emits[(byname["MASKBOOL"], "GENBYTE")]) != [1, 132]:
            bad.append(f"{ver}: MASKBOOL emits bytes "
                       f"{sorted(emits[(byname['MASKBOOL'], 'GENBYTE')])}, "
                       f"not 1 and 132 (SLDC 1; LAND)")
        li = sorted(set(emits[(byname["LOADIDADDR"], "GEN2")]))
        if li != [50, 54]:
            bad.append(f"{ver}: LOADIDADDR emits GEN2 opcodes {li}, "
                       f"not 50 (LDA) and 54 (LOD)")

        # DECSIZE is WRITE's alone in this segment.
        checked += 1
        dec = {procname("BODYPART", n, ver) for n, c in calls.items()
               if "DECSIZE" in c}
        if dec != {"WRITE", "FACTOR"}:
            bad.append(f"{ver}: DECSIZE is called in BODYPART by "
                       f"{sorted(dec)}, expected WRITE (a long integer's "
                       f"digit count) and FACTOR (a long literal's)")

        # LINKINFO: the union of II.0's two linker-info flags.
        checked += 1
        off = next(o for o, n in GLOBALS[ver].items() if n == "LINKINFO")
        writers = set()
        for s in cf.segments:
            for p in s.pcode_procedures:
                body, _ = disassemble(s.data, p.enter_ic, p.exit_ic, p.jtab)
                if any(i.mnemonic == "SRO" and i.operands[0] == off
                       for i in body):
                    writers.add(procname(s.name, p.number, ver)
                                or f"{s.name}.{p.number}")
        expect = {"ONEUNIT", "PROCDECLARATION", "NEWPROC", "UNITPART",
                  "WRITELINKERINFO", "COMPINIT.9"}
        if writers != expect:
            bad.append(f"{ver}: LINKINFO is stored into by {sorted(writers)}, "
                       f"expected {sorted(expect)}")

        print(f"{ver}: BODYPART, {len(procs)} procedures, all named "
              f"{'' if ver == '1.1' else 'but the one 1.3 inserts at 26'}")

    if bad:
        print("\n".join(bad))
        return 1
    print(f"{checked} claims, both releases, all hold")
    print("bodypart-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
