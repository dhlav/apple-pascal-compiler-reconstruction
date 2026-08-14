"""Is DECLARAT the declaration part of the UCSD II.0 compiler?

`decpart.a/b/c.text` declares DECLARATIONPART and, nested inside it,
seventeen procedures. Apple's DECLARAT segment has twenty. If the
seventeen really are II.0's, then three things the binary fixes -- the
parameter size, the lexical level, and who calls whom -- have to line up
with the source, all at once, and for all seventeen. Nothing about the
codefile forces that: a segment is free to declare its procedures in any
order, at any depth, with any signature.

So this is a joint claim, and each row below can break it on its own:

  * **PARAM** is the parameter size in bytes, straight out of the
    attribute table. II.0 says what the parameters are, and the type
    sizes are the ones finding 33's layout uses (SETOFSYS 8, a pointer or
    a scalar or a var parameter 2). A row with the wrong arity fails.
  * **LEX** is the lexical level, also out of the attribute table. It is
    the declaration nesting, and it is what every LOD/LDA/STR in the
    procedure is compiled against.
  * **CALLS** and **NOTCALLS** are checked against the call graph built
    from the p-code. These are the discriminating ones: PACKABLE is the
    only thing in II.0 that both recurses and calls GETBOUNDS,
    CONSTDECLARATION the only one that calls CONSTANT, PROCDECLARATION
    the only one that calls NEWSEG, GETTEXT the only one that touches a
    file. ALLOCATE calls PACKABLE and PACKABLE does not call ALLOCATE, so
    the two cannot be swapped.

Three of the twenty are Apple's own factorings, with no counterpart in
II.0 -- CHECKSYM, ONEUNIT, FINDSEG and SEGSRCH -- and they are pinned
here by shape instead: CHECKSYM calls ERROR and SKIP and *nothing else*,
which no other procedure on either disk does.

Both releases must agree, which they do at identical procedure numbers.
Finding 34.
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

# (procedure number, name, param bytes, lex, must call, must not call).
# Names in the call sets are resolved through names.py, so a rename in one
# place cannot silently pass here. `None` for PARAM means the two releases
# disagree and the number is not part of the claim.
CLAIMS = [
    (1,  "DECLARATIONPART", 8,  1,
     ["USESDECLARATION", "LABELDECLARATION", "CONSTDECLARATION",
      "TYPEDECLARATION", "VARDECLARATION", "PROCDECLARATION"],
     ["TYP"]),                      # II.0's DECLARATIONPART never calls TYP
                                    # itself -- only its declaration parsers do
    (2,  "CHECKSYM",     8,  2, ["ERROR", "SKIP"],
     ["INSYMBOL", "CHECKSYM"]),
    (3,  "TYP",          12, 2, ["SIMPLETYPE", "PACKABLE", "FIELDLIST",
                                 "POINTERTYPE", "TYP"], []),
    (4,  "SIMPLETYPE",   12, 3, ["CONSTANT"], ["TYP", "SIMPLETYPE"]),
    (5,  "PACKABLE",     6,  3, ["PACKABLE", "GETBOUNDS"],
     ["ALLOCATE", "INSYMBOL", "ERROR"]),
    (6,  "FIELDLIST",    10, 3, ["TYP", "ALLOCATE", "VARIANTLIST"], []),
    (7,  "ALLOCATE",     2,  4, ["PACKABLE"], ["INSYMBOL", "ERROR"]),
    (8,  "VARIANTLIST",  0,  4, ["FIELDLIST", "ALLOCATE", "CONSTANT"], []),
    (9,  "POINTERTYPE",  0,  3, ["SEARCHID", "ERROR"], ["TYP", "CONSTANT"]),
    (10, "USESDECLARATION", 0, 2, ["ONEUNIT"], ["GETTEXT", "DECLARATIONPART"]),
    (11, "ONEUNIT",      2,  3, ["GETTEXT", "DECLARATIONPART", "ENTERID"], []),
    (12, "GETTEXT",      2,  4, ["FINDSEG", "NEWSEG"], ["DECLARATIONPART"]),
    (13, "FINDSEG",      4,  5, ["SEGSRCH"], []),
    (14, "SEGSRCH",      None, 6, [], ["FINDSEG", "SEGSRCH"]),
    (15, "LABELDECLARATION", 0, 2, ["CHECKSYM"], ["TYP", "ENTERID"]),
    (16, "CONSTDECLARATION", 0, 2, ["CONSTANT", "ENTERID"], ["TYP"]),
    (17, "TYPEDECLARATION",  0, 2, ["TYP", "ENTERID"], ["CONSTANT"]),
    (18, "VARDECLARATION",   0, 2, ["TYP", "ENTERID"], ["CONSTANT"]),
    (19, "PROCDECLARATION",  4, 2, ["PARAMETERLIST", "NEWSEG", "BUMPSEG",
                                    "SEARCHSECTION"], ["TYP"]),
    (20, "PARAMETERLIST",   12, 3, ["SEARCHID"], ["PARAMETERLIST"]),
]


def call_sets(cf):
    """(segname, procnum) -> set of resolved callee names, per procedure."""
    segmap = {s.seg_num: s.name for s in cf.segments}
    out = defaultdict(set)
    for seg in cf.segments:
        for p in seg.pcode_procedures:
            body, _ = disassemble(seg.data, p.enter_ic, p.exit_ic, p.jtab)
            ex, _ = sweep_exit(seg.data, p.exit_ic, p.jtab - 8, p.jtab)
            for ins in body + ex:
                if ins.mnemonic == "CXP":
                    s, n = ins.operands
                    if s == 0:
                        out[(seg.name, p.number)].add(f"OS.{n}")
                        continue
                    tgt = (segmap.get(s, f"seg{s}"), n)
                elif ins.mnemonic in ("CLP", "CGP", "CIP", "CBP"):
                    tgt = (seg.name, ins.operands[0])
                else:
                    continue
                out[(seg.name, p.number)].add(tgt)
    return out


def main() -> int:
    bad, checked = [], 0
    for ver, dsk in DISKS.items():
        disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / dsk)
        e = disk.find("SYSTEM.COMPILER")
        cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))
        calls = call_sets(cf)

        seg = next(s for s in cf.segments if s.name == "DECLARAT")
        procs = {p.number: p for p in seg.procedures}
        if len(procs) != 20:
            bad.append(f"{ver}: DECLARAT has {len(procs)} procedures, not 20")

        # File I/O is GETTEXT's alone in this segment: RESET, CLOSE and
        # BLOCKREAD of LIBRARY, and nothing else here opens a file.
        fileio = {n for n in procs
                  if {"OS.5", "OS.6", "OS.28"} & calls[("DECLARAT", n)]}
        if fileio != {12}:
            bad.append(f"{ver}: the procedures doing file I/O in DECLARAT are "
                       f"{sorted(fileio)}, expected just 12 (GETTEXT)")

        # TYPEDECLARATION and VARDECLARATION have the same call set -- both
        # parse a type and enter identifiers -- so tell them apart the way
        # finding 33 does: VARDECLARATION is the one that assigns addresses,
        # and LC (global 10) is the data location counter it bumps.
        lc = next(o for o, n in GLOBALS[ver].items() if n == "LC")
        writers = set()
        for p in seg.pcode_procedures:
            body, _ = disassemble(seg.data, p.enter_ic, p.exit_ic, p.jtab)
            for ins in body:
                if ins.mnemonic == "SRO" and ins.operands[0] == lc:
                    writers.add(p.number)
        if 18 not in writers or 17 in writers:
            bad.append(f"{ver}: the DECLARAT procedures that store into LC "
                       f"are {sorted(writers)}; VARDECLARATION (18) must be "
                       f"among them and TYPEDECLARATION (17) must not")

        for num, name, param, lex, must, mustnot in CLAIMS:
            checked += 1
            got = procname("DECLARAT", num, ver)
            if got != name:
                bad.append(f"{ver}: names.py calls DECLARAT.{num} {got!r}, "
                           f"this probe claims {name!r}")
                continue
            p = procs.get(num)
            if p is None:
                bad.append(f"{ver}: DECLARAT.{num} ({name}) is missing")
                continue
            if param is not None and p.param_size != param:
                bad.append(f"{ver}: {name} takes {p.param_size} bytes of "
                           f"parameters, II.0's signature needs {param}")
            if p.lex_level != lex:
                bad.append(f"{ver}: {name} is at lex {p.lex_level}, but II.0 "
                           f"declares it at lex {lex}")

            named = {procname(t[0], t[1], ver) or f"{t[0]}.{t[1]}"
                     for t in calls[("DECLARAT", num)]
                     if not isinstance(t, str)}
            for want in must:
                if want not in named:
                    bad.append(f"{ver}: {name} does not call {want}")
            for no in mustnot:
                if no in named:
                    bad.append(f"{ver}: {name} calls {no}, which II.0's "
                               f"{name} does not")

        print(f"{ver}: DECLARAT, 20 procedures, {len(CLAIMS)} claims checked")

    if bad:
        print("\n".join(bad))
        return 1
    print(f"{checked} claims, both releases, all hold")
    print("declarat-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
