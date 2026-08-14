"""The last five segments -- and every procedure on the 1.1 disk named.

With finding 37 the registry covers **142 of 142** procedures in Apple
Pascal 1.1, and 144 of 1.3's 147; the three left out are new in 1.3 and
appended at the end of their segments, which this probe checks rather
than assumes.

COMPINIT is the clean case. `compinit.text` declares seven procedures
inside COMPINIT, and Apple's segment procedure calls **exactly seven** of
its nine -- the other two, .5 and .6, are called only from ENTSPCPROCS
and ENTSTDPROCS. So the seven are II.0's, in II.0's order, and the two
are a space optimisation of Apple's: rather than an eight-byte string
constant per standard identifier, `PUTNAMES` appends a batch of
`.`-separated names to a pool and `NEXTNAME` takes them out one at a
time, blank-padded to eight characters.

Of the two that had to be told apart, INITSCALARS and INITSETS, the
binary is unambiguous: one stores into forty-odd scalar globals with SRO,
the other writes four-word sets with STM. **This corrects finding 26c**,
which said the follow-sets were initialised in COMPINIT.9; they are
initialised in COMPINIT.10.

`PASCALCO.12` is also corrected here. It was called NEXTLINE, a name of
ours that described it. It is II.0's `CHECKEND` (procs.a.text:142), and
the probe holds it to that source line by line -- including that it is
the only reader of STARTDOTS on either disk apart from FINISHUP, which
II.0 has not got at all -- `(SCREENDOTS - STARTDOTS) mod 50 = 0` is what
needs it, and nothing else in the compiler does.

Finding 37.
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

# 1.3's three extra procedures, and the segment each is appended to. The
# claim is that they are *appended*: 1.1's numbering is untouched, which
# is why the names in names.py need no shift for these segments.
NEW_IN_13 = {("COMPINIT", 11), ("BODYPART", 26), ("COMPOPTI", 5)}

# (segment, name, param bytes or None, lex, must call, must not call)
CLAIMS = [
    ("COMPINIT", "ENTSTDTYPES",  0, 2, ["DECSIZE"], ["ENTERID"]),
    ("COMPINIT", "ENTSTDNAMES",  0, 2, ["ENTERID"], ["DECSIZE"]),
    ("COMPINIT", "ENTUNDECL",    0, 2, [], ["ENTERID", "DECSIZE"]),
    ("COMPINIT", "PUTNAMES",     2, 2, [], ["NEXTNAME"]),
    ("COMPINIT", "NEXTNAME",     2, 2, [], ["PUTNAMES"]),
    ("COMPINIT", "ENTSPCPROCS",  0, 2, ["PUTNAMES", "NEXTNAME", "ENTERID"], []),
    ("COMPINIT", "ENTSTDPROCS",  0, 2, ["PUTNAMES", "NEXTNAME", "ENTERID"], []),
    ("COMPINIT", "INITSCALARS",  0, 2, [], ["ENTERID", "PUTNAMES"]),
    ("COMPINIT", "INITSETS",     0, 2, [], ["ENTERID", "PUTNAMES"]),

    ("WRITELIN", "WRITELINKERINFO", 0, 1, ["GLOBALSEARCH", "WRITECODE"],
     ["GETREFS", "GETNEXTBLOCK"]),
    ("WRITELIN", "GETREFS",      2, 2, ["GETNEXTBLOCK", "GENWORD"], []),
    ("WRITELIN", "GETNEXTBLOCK", 0, 3, [], ["GETREFS"]),
    ("WRITELIN", "GLOBALSEARCH", 2, 2, ["GETREFS", "GLOBALSEARCH"], []),

    ("UNITPART", "UNITPART",     8, 1, ["OPENREFFILE", "UNITDECLARATION",
                                        "UNITBODY", "WRITELINKERINFO",
                                        "DECLARATIONPART"], []),
    ("UNITPART", "OPENREFFILE",  0, 2, ["ERROR"], ["INSYMBOL"]),
    ("UNITPART", "UNITDECLARATION", 10, 2, ["ENTERID", "NEWSEG", "CONSTANT"],
     []),
    ("UNITPART", "UNITBODY",     0, 2, ["BODYPART", "INSYMBOL"], ["ERROR"]),

    ("NUMSTRIN", "NUMSTRIN",     4, 1, ["STRING", "NUMBER"], []),
    ("NUMSTRIN", "STRING",       0, 2, ["ERROR", "CHECKEND"], []),
    ("NUMSTRIN", "NUMBER",       0, 2, ["ERROR"], ["CHECKEND"]),

    ("COMPOPTI", "BADOPT",       0, 2, [], ["INSYMBOL", "ERROR"]),
    ("COMPOPTI", "OPTWORD",      4, 2, [], ["INSYMBOL", "BADOPT"]),
    ("COMPOPTI", "OPTLIST",      0, 2, ["BADOPT", "INSYMBOL", "SEARCHID"], []),

    ("BODY3", "BODY3",           0, 3, ["UNITSEGS", "WRITECODE", "GENWORD",
                                        "GENBYTE", "INSYMBOL"], []),
    ("BODY3", "UNITSEGS",        0, 4, ["GENLDC", "GEN1", "GENLABEL",
                                        "PUTLABEL", "GENJMP"], ["GENWORD"]),
]


def walk(cf, ver):
    """procedure -> (call set, CSP-argument pairs, globals read/written)."""
    segmap = {s.seg_num: s.name for s in cf.segments}
    calls, gen1, reads, writes = {}, defaultdict(set), defaultdict(set), \
        defaultdict(set)
    stop = ("CXP", "CLP", "CGP", "CIP", "CBP", "CSP",
            "UJP", "FJP", "TJP", "XJP", "EFJ", "NFJ")
    for s in cf.segments:
        for p in s.pcode_procedures:
            body, _ = disassemble(s.data, p.enter_ic, p.exit_ic, p.jtab)
            ex, _ = sweep_exit(s.data, p.exit_ic, p.jtab - 8, p.jtab)
            body = body + ex
            me = (s.name, p.number)
            out = set()
            for k, ins in enumerate(body):
                if ins.mnemonic == "CXP":
                    a, n = ins.operands
                    tgt = ("OS" if a == 0 else segmap.get(a), n)
                    out.add(f"OS.{n}" if a == 0
                            else procname(segmap.get(a), n, ver) or f"{a}.{n}")
                elif ins.mnemonic in ("CLP", "CGP", "CIP", "CBP"):
                    out.add(procname(s.name, ins.operands[0], ver)
                            or f"{s.name}.{ins.operands[0]}")
                    tgt = (s.name, ins.operands[0])
                else:
                    if ins.mnemonic in ("LDO", "SLDO", "LAO"):
                        # LAO is how a multi-word global is reached: the
                        # follow-sets are written `LAO base; LDC 4w; STM 4`.
                        reads[me].add(ins.operands[0])
                    elif ins.mnemonic == "SRO":
                        writes[me].add(ins.operands[0])
                    continue
                if procname(*tgt, ver) == "GEN1":
                    cs, j = [], k - 1
                    while j >= 0 and body[j].mnemonic not in stop:
                        if body[j].mnemonic in ("SLDC", "LDCI"):
                            cs.append(body[j].operands[0])
                        j -= 1
                    if len(cs) >= 2:
                        gen1[me].add((cs[-1], cs[-2]))
            calls[me] = out
    return calls, gen1, reads, writes


def main() -> int:
    bad, checked = [], 0
    for ver, dsk in DISKS.items():
        disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / dsk)
        e = disk.find("SYSTEM.COMPILER")
        cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))
        calls, gen1, reads, writes = walk(cf, ver)
        glob = {n: o for o, n in GLOBALS[ver].items()}
        num = {}
        for s in cf.segments:
            for p in s.procedures:
                nm = procname(s.name, p.number, ver)
                if nm:
                    num[(s.name, nm)] = p

        # Nothing on the 1.1 disk is left without a name.
        checked += 1
        unnamed = {(s.name, p.number) for s in cf.segments
                   for p in s.procedures
                   if not procname(s.name, p.number, ver)}
        want = set() if ver == "1.1" else NEW_IN_13
        if unnamed != want:
            bad.append(f"{ver}: procedures without a name are "
                       f"{sorted(unnamed)}, expected {sorted(want)}")
        # ...and 1.3's extras are appended, not inserted.
        if ver == "1.3":
            checked += 1
            for sname, n in NEW_IN_13 - {("BODYPART", 26)}:
                seg = next(s for s in cf.segments if s.name == sname)
                if n != max(p.number for p in seg.procedures):
                    bad.append(f"1.3: {sname}.{n} is not the last procedure "
                               f"in its segment, so 1.1's numbering shifts")

        for sname, name, param, lex, must, mustnot in CLAIMS:
            checked += 1
            p = num.get((sname, name))
            if p is None:
                bad.append(f"{ver}: {sname} has no procedure called {name}")
                continue
            if param is not None and p.param_size != param:
                bad.append(f"{ver}: {sname}.{name} takes {p.param_size} bytes "
                           f"of parameters, expected {param}")
            if p.lex_level != lex:
                bad.append(f"{ver}: {sname}.{name} is at lex {p.lex_level}, "
                           f"expected {lex}")
            me = (sname, p.number)
            for w in must:
                if w not in calls[me]:
                    bad.append(f"{ver}: {sname}.{name} does not call {w}")
            for w in mustnot:
                if w in calls[me]:
                    bad.append(f"{ver}: {sname}.{name} calls {w}, "
                               f"and should not")

        # COMPINIT calls exactly the seven procedures II.0 declares.
        checked += 1
        seven = {"ENTSTDTYPES", "ENTSTDNAMES", "ENTUNDECL", "ENTSPCPROCS",
                 "ENTSTDPROCS", "INITSCALARS", "INITSETS"}
        got = {c for c in calls[("COMPINIT", 1)] if c in
               seven | {"PUTNAMES", "NEXTNAME"}}
        if got != seven:
            bad.append(f"{ver}: COMPINIT calls {sorted(got)} of its own "
                       f"procedures, not II.0's seven")

        # INITSCALARS stores scalars; INITSETS writes the follow-sets.
        checked += 1
        sc = num[("COMPINIT", "INITSCALARS")].number
        st = num[("COMPINIT", "INITSETS")].number
        if len(writes[("COMPINIT", sc)]) < 20:
            bad.append(f"{ver}: INITSCALARS stores into only "
                       f"{len(writes[('COMPINIT', sc)])} globals")
        sets = {glob[n] for n in ("TYPEDELS", "STATBEGSYS", "FACBEGSYS",
                                  "SELECTSYS", "BLOCKBEGSYS", "TYPEBEGSYS",
                                  "SIMPTYPEBEGSYS", "CONSTBEGSYS")}
        setwriter = {n for n in (sc, st)
                     if sets <= (writes[("COMPINIT", n)]
                                 | reads[("COMPINIT", n)])}
        if setwriter != {st}:
            bad.append(f"{ver}: the COMPINIT procedure(s) touching the "
                       f"follow-sets are {sorted(setwriter)}, expected "
                       f"only INITSETS ({st})")

        # UNITSEGS emits GETSEG and RELSEG, and only it does.
        checked += 1
        seg_emitters = {procname(s, n, ver) for (s, n), g in gen1.items()
                        if {(30, 21), (30, 22)} & g}
        if seg_emitters != {"UNITSEGS"}:
            bad.append(f"{ver}: GEN1(30, 21/22) -- GETSEG and RELSEG -- is "
                       f"emitted by {sorted(seg_emitters)}, expected only "
                       f"UNITSEGS. II.0 emits GETSEG at the head of BODY "
                       f"and RELSEG at its tail; Apple emits both here.")

        # CHECKEND is the only reader of STARTDOTS anywhere.
        checked += 1
        sd = glob["STARTDOTS"]
        readers = {procname(s, n, ver) or f"{s}.{n}"
                   for (s, n), g in reads.items() if sd in g}
        if readers != {"CHECKEND", "FINISHUP"}:
            bad.append(f"{ver}: STARTDOTS is read by {sorted(readers)}, "
                       f"expected CHECKEND -- II.0's only reader -- and "
                       f"FINISHUP, which Apple added and II.0 has not")
        checked += 1
        ce = num[("PASCALCO", "CHECKEND")]
        need = {glob[n] for n in ("SCREENDOTS", "STARTDOTS", "NOISY", "LIST",
                                  "SYMCURSOR")}
        seen = reads[("PASCALCO", ce.number)] | writes[("PASCALCO", ce.number)]
        if not need <= seen:
            bad.append(f"{ver}: CHECKEND does not touch "
                       f"{sorted(need - seen)}")
        for w in ("PRINTLINE", "GETNEXTPAGE"):
            if w not in calls[("PASCALCO", ce.number)]:
                bad.append(f"{ver}: CHECKEND does not call {w}")

        print(f"{ver}: {sum(len(s.procedures) for s in cf.segments)} "
              f"procedures, {len(unnamed)} without a name")

    if bad:
        print("\n".join(bad))
        return 1
    print(f"{checked} claims, both releases, all hold")
    print("segments-rest-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
