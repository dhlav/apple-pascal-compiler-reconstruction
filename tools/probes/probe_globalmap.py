"""Apple's VAR block, where it agrees with UCSD II.0 and where it does not.

The reconstruction has to declare the compiler's globals in an order that
reproduces Apple's offsets, so every `LDO`/`SRO` in the binary is a
constraint on the source. `tools/vardecl.py` lays out II.0's VAR block
under the compiler's own backwards-allocation rule (finding 33) and prints
the drift against Apple's recovered names. The drift is flat wherever
Apple kept II.0's declaration order and steps wherever Apple edited it,
and this probe checks that every step is accounted for by an object the
binary can be made to describe -- and that the accounting can fail.

Four claims, in the order the VAR block reaches them.

  * **DISPLAY is II.0's, untouched, in both releases.** `DISPLIMIT = 12`
    gives 13 four-word entries, and the binary indexes it with `IXA 4` and
    nothing else. If the record had gained or lost a field the stride
    would say so.

  * **Apple deleted PFNUMOF and put a set of segment numbers in its
    place.** II.0's `PFNUMOF: NONRESPFLIST` is six words, and II.0's GENNR
    emits `GEN1(79 CGP, PFNUMOF[extproc])`. Apple's BODYPART.7 instead is,
    in its entirety, `SEGSUSED := SEGSUSED + [seg]` followed by
    `GEN2(77 CXP, seg, proc)` -- thirteen instructions, checked here one
    by one. The set is two words in 1.1 and four in 1.3, and every other
    reference to it in the codefile agrees, so the width is not asserted
    but measured. The drift step at PROCTABLE must then be exactly
    `-6 + width`, which for 1.1 is `+6 -> +2`.

  * **The step between SEGTABLE and COMMENT is SEGTABLE's ninth word plus
    SEGMAP, with nothing left over.** Apple's SEGTABLE entry is nine words
    where II.0's is eight (`IXA 9`, sixteen entries, = +16), and SEGMAP --
    which II.0 does not have, because II.0's segment numbers index
    SEGTABLE directly -- is a packed array of nibbles reached only by
    `IXP 4,4` (= +8). 16 + 8 = 24 = the observed step.

  * **The source-switching block 575..585 is II.0's ten names plus one
    Apple word.** The six save slots are placed here by behaviour alone:
    by which global each is copied back into, and by which routine saves
    it. II.0's GETNEXTPAGE restores PREV* when USING goes false and OLD*
    when INCLUDING does; GETTEXT saves PREV* and the `$I` arm of COMMENTER
    saves OLD*. Nothing in that reasoning uses declaration order -- yet
    laid out that way all six land at a constant drift of +27, in exactly
    the order II.0's two declarations allocate them backwards. That is the
    check that could have failed and did not.

The rest of the probe is finding 39, which fills the stretches *between*
the matched runs. Each name there was placed by the drift column -- a gap
with a verified name at each end and the same word count as II.0 has names
inside it can be filled only one way -- and what is checked here is the
behaviour instead, so the two arguments stay independent. `ENTUNDECL`'s
six `NEW`s and the record size each asks for; `BLOCK`'s lex stack;
`COMPINIT`'s `CURBLK := 1; CURBYTE := 0`; `INSYMBOL`'s opening three
instructions; the `INTRINSIC`/`DATA` literals `UNITDECLARATION` compares
against; and the `$R` arm of the option switch, which the manual says
carries both range checking and the resident-segment list.

Finding 40 then closes the loop from the other side: with both maps named,
1.3's global growth can be totalled. The correspondence table's six shift
steps say where the words went in; the objects here say what each one is;
and the sum has to equal the difference between the two global areas.
`JTAB` is the leg that leans hardest on measurement, so it is checked
twice -- the extent between `JTAB` and `REFFILE`, against the `MAXJTAB`
constant the binary compares `NEXTJTAB` with before raising the overflow
error.

Findings 38, 39 and 40.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import vardecl
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.globals import collect
from a2pascal.pcode import disassemble, sweep_exit
from a2pascal.names import GLOBALS_11, GLOBALS_13, procname

ROOT = Path(__file__).resolve().parent.parent.parent
DISKS = {
    "1.1": "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk",
    "1.3": "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk",
}
GLOBALS = {"1.1": GLOBALS_11, "1.3": GLOBALS_13}

# Only the two set widths differ between releases, and each is checked
# against every reference to the set rather than trusted.
SETW = {"1.1": 2, "1.3": 4}
SEGMAPW = {"1.1": 8, "1.3": 16}

# The whole of BODYPART.7, which is what replaced II.0's PFNUMOF lookup.
# `w` is the set width; operands of None are not constrained.
def bodypart7_shape(setg: int, w: int):
    return [("LAO", [setg]), ("LAO", [setg]), ("LDM", [w]), ("SLDC", [w]),
            ("SLDL", [2]), ("SGS", None), ("UNI", None), ("ADJ", [w]),
            ("STM", [w]),
            ("SLDC", [77]), ("SLDL", [2]), ("SLDL", [1]), ("CIP", None)]


def streams(cf):
    """(segment name, procedure number, instruction list) for every proc."""
    for seg in cf.segments:
        for p in seg.pcode_procedures:
            body, _ = disassemble(seg.data, p.enter_ic, p.exit_ic, p.jtab)
            ex, _ = sweep_exit(seg.data, p.exit_ic, p.jtab - 8, p.jtab)
            yield seg.name, p.number, body + ex


def ii0_layout():
    """II.0 name -> word offset, under the backwards-allocation rule."""
    out, off = {}, 1
    for ids, typ in vardecl.var_block():
        for name in reversed(ids):
            words, _why = vardecl.size_of(typ, name)
            out[name] = off
            off += words
    return out


def main() -> int:
    bad, checked = [], 0
    ii0 = ii0_layout()
    facts = {}

    # PFNUMOF has to be in II.0's VAR block at all, and six words of it.
    checked += 1
    if "PFNUMOF" not in ii0:
        bad.append("II.0's VAR block has no PFNUMOF, so the deletion this "
                   "probe measures is not there to measure")
    else:
        pf, _ = vardecl.size_of("NONRESPFLIST", "PFNUMOF")
        if pf != 6:
            bad.append(f"II.0's PFNUMOF is {pf} words, not the 6 that "
                       f"ARRAY [NONRESIDENT] OF INTEGER gives")
        if ii0.get("DISPLAY") is None or ii0["PFNUMOF"] != ii0["DISPLAY"] + 52:
            bad.append("II.0 does not declare PFNUMOF immediately after "
                       "DISPLAY, so Apple's set is not in its place")

    for ver, dsk in DISKS.items():
        disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / dsk)
        e = disk.find("SYSTEM.COMPILER")
        cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))
        where = {name: off for off, name in GLOBALS[ver].items()}

        missing = [n for n in ("DISPLAY", "SEGSUSED", "PROCTABLE", "SEGTABLE",
                               "SEGMAP", "SYMBLK", "SYMCURSOR", "LINESTART",
                               "USING", "INCLUDING", "REFBLK", "NREFS",
                               "REFLIST", "TEXTSTRT", "USEFILE",
                               "PREVSYMBLK", "PREVSYMCURSOR", "PREVLINESTART",
                               "OLDSYMBLK", "OLDSYMCURSOR", "OLDLINESTART")
                   if n not in where]
        if missing:
            bad.append(f"{ver}: names.py has no global called {missing}")
            continue

        table, _acc, area = collect(cf, ver)
        touched = sorted(table)
        setg, w = where["SEGSUSED"], SETW[ver]

        # --- DISPLAY: one stride, and it is 4 -----------------------------
        strides, sites = set(), 0
        for _s, _n, st in streams(cf):
            for k, ins in enumerate(st):
                if ins.mnemonic != "LAO" or ins.operands[0] != where["DISPLAY"]:
                    continue
                sites += 1
                nxt = [i for i in st[k + 1:k + 4] if i.mnemonic == "IXA"]
                if nxt:
                    strides.add(nxt[0].operands[0])
        checked += 1
        if sites == 0:
            bad.append(f"{ver}: nothing indexes DISPLAY, so its stride is "
                       f"not being checked at all")
        elif strides != {4}:
            bad.append(f"{ver}: DISPLAY is indexed with IXA {sorted(strides)}, "
                       f"not the 4 a 13 x 4 array of DISPLIMIT+1 entries needs")

        # --- SEGSUSED: a set, and every reference agrees on the width ------
        widths, setsites, ops = set(), 0, set()
        for _s, _n, st in streams(cf):
            for k, ins in enumerate(st):
                if ins.mnemonic != "LAO" or ins.operands[0] != setg:
                    continue
                setsites += 1
                for i in st[k + 1:k + 6]:
                    if i.mnemonic in ("LDM", "STM", "ADJ"):
                        widths.add(i.operands[0])
                    if i.mnemonic in ("SGS", "UNI", "INN", "INT", "DIF"):
                        ops.add(i.mnemonic)
        checked += 1
        if setsites == 0:
            bad.append(f"{ver}: global {setg} is never addressed, so the "
                       f"set claim is vacuous")
        if widths != {w}:
            bad.append(f"{ver}: SEGSUSED is loaded and stored as "
                       f"{sorted(widths)} words, not the {w} a "
                       f"SET OF 0..{w * 16 - 1} needs")
        if not {"SGS", "UNI"} <= ops or "INN" not in ops:
            bad.append(f"{ver}: SEGSUSED is used with {sorted(ops)}; without "
                       f"SGS, UNI and INN it is not a set at all")

        # --- BODYPART.7 is that replacement, instruction for instruction ---
        checked += 1
        want = bodypart7_shape(setg, w)
        got = None
        for sname, num, st in streams(cf):
            if sname == "BODYPART" and num == 7:
                got = st
        if got is None:
            bad.append(f"{ver}: no BODYPART.7 to check")
        else:
            body = [i for i in got if i.mnemonic != "RNP"]
            if len(body) != len(want):
                bad.append(f"{ver}: BODYPART.7 is {len(body)} instructions, "
                           f"not the {len(want)} of `SEGSUSED := SEGSUSED + "
                           f"[seg]; GEN2(77 CXP, seg, proc)`")
            else:
                for i, (m, o) in zip(body, want):
                    if i.mnemonic != m or (o is not None and i.operands != o):
                        bad.append(f"{ver}: BODYPART.7 has {i.mnemonic} "
                                   f"{i.operands} where the replacement for "
                                   f"PFNUMOF needs {m} {o}")
                        break

        # It is the only union into the set anywhere in the compiler.
        unions = set()
        for sname, num, st in streams(cf):
            for k, ins in enumerate(st):
                if (ins.mnemonic == "UNI"
                        and any(i.mnemonic == "LAO" and i.operands[0] == setg
                                for i in st[max(0, k - 8):k])):
                    unions.add((sname, procname(sname, num, ver) or num))
        checked += 1
        named = {n for _s, n in unions}
        if "GENNR" not in named:
            bad.append(f"{ver}: BODYPART.7 (GENNR) is not among the "
                       f"procedures that add to SEGSUSED: {sorted(named)}")

        # --- SEGMAP: nibbles, reached only by IXP 4,4, and 8/16 words -----
        packs, mapsites = set(), 0
        for _s, _n, st in streams(cf):
            for k, ins in enumerate(st):
                if ins.mnemonic != "LAO" or ins.operands[0] != where["SEGMAP"]:
                    continue
                mapsites += 1
                nxt = [i for i in st[k + 1:k + 5] if i.mnemonic == "IXP"]
                if nxt:
                    packs.add(tuple(nxt[0].operands))
        checked += 1
        if mapsites == 0:
            bad.append(f"{ver}: SEGMAP is never addressed")
        elif packs != {(4, 4)}:
            bad.append(f"{ver}: SEGMAP is indexed with IXP {sorted(packs)}, "
                       f"not the 4,4 a packed array of 0..15 needs")

        # Its extent, from the next global anybody touches.
        checked += 1
        after = [o for o in touched if o > where["SEGMAP"]]
        gap = (after[0] - where["SEGMAP"]) if after else (area - where["SEGMAP"])
        if gap != SEGMAPW[ver]:
            bad.append(f"{ver}: SEGMAP runs {gap} words before the next "
                       f"global, not the {SEGMAPW[ver]} that "
                       f"{SEGMAPW[ver] * 4} nibbles need")

        # --- SEGTABLE's entry is nine words, not II.0's eight -------------
        segstrides = set()
        for _s, _n, st in streams(cf):
            for k, ins in enumerate(st):
                if ins.mnemonic != "LAO" or ins.operands[0] != where["SEGTABLE"]:
                    continue
                nxt = [i for i in st[k + 1:k + 6] if i.mnemonic == "IXA"]
                if nxt:
                    segstrides.add(nxt[0].operands[0])
        checked += 1
        if segstrides != {9}:
            bad.append(f"{ver}: SEGTABLE is indexed with IXA "
                       f"{sorted(segstrides)}, not the 9 that makes it one "
                       f"word wider than II.0's record")

        # --- the six save slots, placed by behaviour ----------------------
        #
        # GETNEXTPAGE restores each one into the global it shadows; nobody
        # else copies them anywhere. Pair them up out of the binary and
        # compare against the names.
        restore = {}
        for _s, _n, st in streams(cf):
            for a, b in zip(st, st[1:]):
                if (a.mnemonic in ("LDO", "SLDO") and b.mnemonic == "SRO"
                        and a.operands[0] in
                        (where["PREVSYMBLK"], where["OLDSYMBLK"],
                         where["PREVSYMCURSOR"], where["OLDSYMCURSOR"],
                         where["PREVLINESTART"], where["OLDLINESTART"])):
                    restore.setdefault(a.operands[0], set()).add(b.operands[0])
        for slot, shadowed in (("SYMBLK", "SYMBLK"), ("SYMCURSOR", "SYMCURSOR"),
                               ("LINESTART", "LINESTART")):
            for pfx in ("PREV", "OLD"):
                checked += 1
                off = where[pfx + slot]
                if restore.get(off) != {where[shadowed]}:
                    bad.append(f"{ver}: {pfx}{slot} (global {off}) is copied "
                               f"into {sorted(restore.get(off, []))}, not "
                               f"into {shadowed} ({where[shadowed]}) alone")

        # ...and saved by the right routine. GETTEXT opens a unit's
        # interface text and saves PREV*; the `$I` arm of COMPOPTI's
        # segment procedure -- II.0's COMMENTER -- opens an include file
        # and saves OLD*. Neither may touch the other's set.
        saved = {}
        for sname, num, st in streams(cf):
            who = f"{sname}.{procname(sname, num, ver) or num}"
            for ins in st:
                if ins.mnemonic == "SRO":
                    saved.setdefault(ins.operands[0], set()).add(who)
        for pfx, owner in (("PREV", "DECLARAT.GETTEXT"),
                           ("OLD", "COMPOPTI.COMPOPTI")):
            for slot in ("SYMBLK", "SYMCURSOR", "LINESTART"):
                checked += 1
                off = where[pfx + slot]
                writers = saved.get(off, set())
                # GETNEXTPAGE never writes them; only the saver does.
                if writers != {owner}:
                    bad.append(f"{ver}: {pfx}{slot} is written by "
                               f"{sorted(writers)}, not by {owner} alone")

        # --- the block is contiguous, and 578 is the one insertion --------
        run = [where[n] for n in ("REFBLK", "NREFS", "REFLIST", "TEXTSTRT",
                                  "PREVSYMBLK", "OLDSYMBLK", "PREVLINESTART",
                                  "PREVSYMCURSOR", "OLDLINESTART",
                                  "OLDSYMCURSOR", "USEFILE")]
        checked += 1
        if run != list(range(run[0], run[0] + 11)):
            bad.append(f"{ver}: the source-switching block is not eleven "
                       f"consecutive words: {run}")

        # USEFILE is II.0's UNITFILE with one enumerator added: three
        # distinct constants are stored into it, and only `= WORKCODE` is
        # ever tested.
        stored = set()
        for _s, _n, st in streams(cf):
            for a, b in zip(st, st[1:]):
                if (b.mnemonic == "SRO" and b.operands[0] == where["USEFILE"]
                        and a.mnemonic in ("SLDC", "LDCI")):
                    stored.add(a.operands[0])
        checked += 1
        if stored != {0, 1, 2}:
            bad.append(f"{ver}: USEFILE is assigned {sorted(stored)}; II.0's "
                       f"UNITFILE has two enumerators and Apple's needs "
                       f"exactly three")

        # --- finding 39: the stretches between the matched runs -----------
        #
        # Each name below was placed in a gap the drift column bounds on
        # both sides. What is checked here is the behaviour instead, so the
        # two arguments stay independent.
        for n in ("ID", "DISX", "GETSTMTLEV", "PRTERR", "MARKP", "TOS",
                  "NEWBLOCK", "SCONST", "STRGCSTIC", "SMALLESTSPACE",
                  "LOWTIME", "CURBLK", "CURBYTE", "DISKBUF", "OUTERBLOCK",
                  "UTYPPTR", "UCSTPTR", "UVARPTR", "UFLDPTR", "UPRCPTR",
                  "UFCTPTR", "INTRINSIC", "DATASEG"):
            if n not in where:
                bad.append(f"{ver}: names.py has no global called {n}")
        if any(n not in where for n in ("ID", "MARKP", "UTYPPTR")):
            continue

        # ENTUNDECL NEWs the six undeclared-id pointers in one run, and the
        # size it asks for is the record variant, which names each one.
        news, csps, memavail = [], {}, set()
        for sname, num, st in streams(cf):
            for k in range(len(st) - 2):
                a, c, z = st[k:k + 3]
                if (a.mnemonic == "LAO" and c.mnemonic in ("SLDC", "LDCI")
                        and z.mnemonic == "CSP" and z.operands[0] == 1):
                    news.append((f"{sname}.{num}", a.operands[0],
                                 c.operands[0]))
            for k in range(len(st) - 1):
                a, z = st[k:k + 2]
                if a.mnemonic == "LAO" and z.mnemonic == "CSP":
                    csps.setdefault(z.operands[0], set()).add(a.operands[0])
                if (a.mnemonic == "CSP" and a.operands[0] == 40
                        and z.mnemonic == "SRO"):
                    memavail.add(z.operands[0])

        want_new = [("UTYPPTR", 9), ("UCSTPTR", 10), ("UVARPTR", 11),
                    ("UFLDPTR", 13), ("UPRCPTR", 18), ("UFCTPTR", 18)]
        undecl = {where[n] for n, _ in want_new}
        undecl_new = [(p, g, s) for p, g, s in news if g in undecl]
        checked += 1
        if len(undecl_new) != 6 or len({p for p, _g, _s in undecl_new}) != 1:
            bad.append(f"{ver}: the six undeclared-id pointers are NEWed "
                       f"{len(undecl_new)} times, from "
                       f"{sorted({p for p, _g, _s in undecl_new})} -- ENTUNDECL "
                       f"does each exactly once")
        else:
            got = [(g, s) for _p, g, s in undecl_new]
            if got != [(where[n], s) for n, s in want_new]:
                bad.append(
                    f"{ver}: ENTUNDECL NEWs "
                    + ", ".join(f"{GLOBALS[ver].get(g, g)}={s}"
                                for g, s in got)
                    + " -- II.0's order and record sizes are "
                    + ", ".join(f"{n}={s}" for n, s in want_new))

        # OUTERBLOCK is a PROC record, the largest variant, like UPRCPTR.
        checked += 1
        ob = [s for _p, g, s in news if g == where["OUTERBLOCK"]]
        if ob != [18]:
            bad.append(f"{ver}: OUTERBLOCK is NEWed as {ob} words, not the "
                       f"18 a PROC record takes")
        checked += 1
        sc = [s for _p, g, s in news if g == where["SCONST"]]
        if sc != [130]:
            bad.append(f"{ver}: SCONST is NEWed as {sc}, not 130 words")

        # MARKP is the compiler's only MARK; LOWTIME its only TIME;
        # SMALLESTSPACE its only MEMAVAIL.
        checked += 1
        if csps.get(32) != {where["MARKP"]}:
            bad.append(f"{ver}: CSP 32 MARK is given "
                       f"{sorted(csps.get(32, []))}, not MARKP "
                       f"({where['MARKP']}) alone")
        checked += 1
        if where["LOWTIME"] not in csps.get(9, set()):
            bad.append(f"{ver}: LOWTIME is not passed to CSP 9 TIME")
        checked += 1
        if memavail != {where["SMALLESTSPACE"]}:
            bad.append(f"{ver}: CSP 40 MEMAVAIL is stored into "
                       f"{sorted(memavail)}, not SMALLESTSPACE alone")

        # Fixed instruction shapes, each one a line of II.0 source.
        shapes = {
            # INSYMBOL: if GETSTMTLEV then
            #             begin BEGSTMTLEV := STMTLEV; GETSTMTLEV := false end
            "GETSTMTLEV": [("LDO", where["GETSTMTLEV"]), ("FJP", None),
                           ("LDO", where["STMTLEV"]),
                           ("SRO", where["BEGSTMTLEV"]), ("SLDC", 0),
                           ("SRO", where["GETSTMTLEV"])],
            # SEARCHID: for DISX := TOP downto 0 do LCP := DISPLAY[DISX].FNAME
            "DISX": [("SLDO", where["TOP"]), ("SRO", where["DISX"])],
            # BLOCK: RELEASE(TOS^.DMARKP); TOS := TOS^.PREVLEXSTACKP
            "TOS": [("LDO", where["TOS"]), ("IND", 10),
                    ("SRO", where["TOS"])],
            # COMPINIT: CURBLK := 1; CURBYTE := 0
            "CURBLK": [("SLDC", 1), ("SRO", where["CURBLK"]), ("SLDC", 0),
                       ("SRO", where["CURBYTE"])],
        }
        found = {k: False for k in shapes}
        for _s, _n, st in streams(cf):
            for k, _ins in enumerate(st):
                for key, want in shapes.items():
                    seq = st[k:k + len(want)]
                    if len(seq) != len(want):
                        continue
                    if all(i.mnemonic == m
                           and (o is None or i.operands[:1] == [o])
                           for i, (m, o) in zip(seq, want)):
                        found[key] = True
        for key, ok in found.items():
            checked += 1
            if not ok:
                bad.append(f"{ver}: the instruction sequence that names "
                           f"{key} is not in the binary")

        # DISPLAY[DISX] is indexed somewhere, and DISX is the only global
        # that indexes DISPLAY.
        indexers = set()
        for _s, _n, st in streams(cf):
            for k, ins in enumerate(st):
                if ins.mnemonic == "LAO" and ins.operands[0] == where["DISPLAY"]:
                    nxt = st[k + 1]
                    if nxt.mnemonic in ("LDO", "SLDO"):
                        indexers.add(nxt.operands[0])
        checked += 1
        want_idx = {where["DISX"], where["TOP"], where["GLEV"]}
        if indexers != want_idx:
            bad.append(f"{ver}: DISPLAY is indexed by globals "
                       f"{sorted(indexers)}, not by exactly TOP, DISX and "
                       f"GLEV {sorted(want_idx)}")

        # The four scanner globals are consecutive and in the order
        # compglbls.text says IDSEARCH requires, with ID four words wide.
        checked += 1
        scan = [where[n] for n in ("SYMCURSOR", "SY", "OP", "ID")]
        if scan != list(range(scan[0], scan[0] + 4)):
            bad.append(f"{ver}: SYMCURSOR, SY, OP, ID are at {scan}, not the "
                       f"four consecutive words IDSEARCH needs")
        checked += 1
        after = [o for o in touched if o > where["ID"]]
        if after and after[0] - where["ID"] != 4:
            bad.append(f"{ver}: ID runs {after[0] - where['ID']} words before "
                       f"the next global, not the 4 of an ALPHA")

        # UNITDECLARATION reads `INTRINSIC ... DATA n`, and those two words
        # are what it sets.
        up3 = None
        for sname, num, st in streams(cf):
            if sname == "UNITPART" and num == 3:
                up3 = st
        checked += 1
        if up3 is None:
            bad.append(f"{ver}: no UNITPART.3 to check")
        else:
            lits = {o for i in up3 if i.mnemonic in ("LPA", "LSA")
                    for o in i.operands if isinstance(o, bytes)}
            wrote = {i.operands[0] for i in up3 if i.mnemonic == "SRO"}
            for lit in (b"INTRINSI", b"DATA    "):
                if lit not in lits:
                    bad.append(f"{ver}: UNITPART.3 does not compare an "
                               f"identifier against {lit!r}")
            for n in ("INTRINSIC", "DATASEG"):
                if where[n] not in wrote:
                    bad.append(f"{ver}: UNITPART.3 does not write {n}")
        # DATASEG indexes SEGMAP, which is what makes it a segment number.
        checked += 1
        segidx = set()
        for _s, _n, st in streams(cf):
            for k, ins in enumerate(st):
                if ins.mnemonic == "LAO" and ins.operands[0] == where["SEGMAP"]:
                    nxt = st[k + 1]
                    if nxt.mnemonic in ("LDO", "SLDO"):
                        segidx.add(nxt.operands[0])
        if where["DATASEG"] not in segidx:
            bad.append(f"{ver}: DATASEG never indexes SEGMAP; the globals "
                       f"that do are {sorted(segidx)}")

        # RESIDENT is the manual's second `$R`. COMPOPTI's option switch
        # runs 'C'..'V', and the 'R' arm both stores RANGECHECK and, in its
        # other branch, calls the procedure that builds the list.
        checked += 1
        opt1 = None
        for sname, num, st in streams(cf):
            if sname == "COMPOPTI" and num == 1:
                opt1 = st
        optlist = next((n for s, n, _st in streams(cf) if s == "COMPOPTI"
                        and procname("COMPOPTI", n, ver) == "OPTLIST"), None)
        if opt1 is None:
            bad.append(f"{ver}: no COMPOPTI.1 to check")
        else:
            xjp = [i for i in opt1 if i.mnemonic == "XJP"]
            if len(xjp) != 1 or xjp[0].operands[:2] != [ord("C"), ord("V")]:
                bad.append(f"{ver}: COMPOPTI.1's option switch is "
                           f"{[i.operands[:2] for i in xjp]}, not one XJP over "
                           f"'C'..'V' ({ord('C')}..{ord('V')})")
            checked += 1
            arm = [k for k, i in enumerate(opt1)
                   if i.mnemonic == "SRO" and i.operands[0] == where["RANGECHECK"]]
            near = {i.operands[0] for k in arm for i in opt1[k:k + 6]
                    if i.mnemonic in ("CLP", "CGP")}
            if optlist is None or optlist not in near:
                bad.append(f"{ver}: the $R arm stores RANGECHECK but its other "
                           f"branch calls {sorted(near)}, not OPTLIST "
                           f"({optlist})")

        # Nothing outside COMPOPTI adds to the list; only the two routines
        # that start a body clear it.
        checked += 1
        writers = {f"{s}.{procname(s, n, ver) or n}"
                   for s, n, st in streams(cf)
                   if any(i.mnemonic == "SRO"
                          and i.operands[0] == where["RESIDENT"] for i in st)}
        stray = {w for w in writers if not w.startswith("COMPOPTI.")
                 and w not in ("PASCALCO.BLOCK", "UNITPART.UNITBODY")}
        if stray:
            bad.append(f"{ver}: RESIDENT is written by {sorted(stray)} as well "
                       f"as by COMPOPTI and the two routines that begin a body")

        # RESIDENT is a list head: built in COMPOPTI, cleared per body, and
        # read only where the manual says the option must appear.
        readers = {f"{s}.{procname(s, n, ver) or n}"
                   for s, n, st in streams(cf)
                   if any(i.mnemonic in ("LDO", "SLDO")
                          and i.operands[0] == where["RESIDENT"] for i in st)}
        checked += 1
        if "BODY1.BODY1" not in readers:
            bad.append(f"{ver}: RESIDENT is read by {sorted(readers)}, and "
                       f"BODY1 -- the top of a procedure body -- is not "
                       f"among them")

        # The one word Apple inserted into the undeclared-id run is never
        # referenced -- which is why it has no name.
        checked += 1
        gap = where["UVARPTR"] - where["UFLDPTR"]
        if gap != 2:
            bad.append(f"{ver}: UFLDPTR and UVARPTR are {gap} words apart, "
                       f"not the 2 that leaves exactly one unused word")
        elif (where["UFLDPTR"] + 1) in table:
            bad.append(f"{ver}: global {where['UFLDPTR'] + 1} is touched "
                       f"after all, so it is not the unused word")

        # --- finding 40: what each object measures, for the 1.3 ledger ---
        def extent(name):
            """Words from `name` to the next global anybody touches."""
            base = where[name]
            nxt = [o for o in touched if o > base]
            return (nxt[0] if nxt else area) - base

        maxjtab = {i.operands[0] for _s, _n, st in streams(cf)
                   for k, i in enumerate(st)
                   if i.mnemonic in ("SLDC", "LDCI") and 0 < k < len(st) - 1
                   and st[k - 1].mnemonic in ("LDO", "SLDO")
                   and st[k - 1].operands[0] == where["NEXTJTAB"]
                   and st[k + 1].mnemonic == "EQUI"}
        facts[ver] = {
            "area": area,
            "SEGSUSED": w,
            "SEGMAP": SEGMAPW[ver],
            "PROCTABLE": extent("PROCTABLE"),
            "JTAB": extent("JTAB"),
            "MAXJTAB": maxjtab,
            "tail": [o for o in touched if o > where["DISKBUF"]],
            "low": [o for o in touched if o < where["ININTERFACE"]],
        }

        print(f"{ver}: DISPLAY 13 x 4 at {where['DISPLAY']}; SEGSUSED "
              f"SET OF 0..{w * 16 - 1} at {setg}; SEGTABLE 16 x 9 at "
              f"{where['SEGTABLE']}; SEGMAP {SEGMAPW[ver]} words of nibbles "
              f"at {where['SEGMAP']}; 575-block at {run[0]}..{run[-1]}")

    # --- the drift ledger, in words ---------------------------------------
    #
    # Only 1.1 is aligned against II.0 by tools/vardecl.py, so the ledger
    # is checked there.
    a11 = {name: off for off, name in GLOBALS_11.items()}
    ledger = [
        # (II.0 name, II.0 name, expected change in drift, why)
        ("DISPLAY", "PROCTABLE", -6 + SETW["1.1"],
         "PFNUMOF (6 words) deleted, a SET OF 0..31 (2 words) put in its place"),
        ("SEGTABLE", "COMMENT", 16 + SEGMAPW["1.1"],
         "SEGTABLE's ninth word x 16 entries, plus SEGMAP"),
        ("REFLIST", "PREVSYMBLK", 1, "TEXTSTRT inserted"),
        ("PREVSYMBLK", "LIBRARY", 0, "nothing else inserted before LIBRARY"),
    ]
    for a, b, step, why in ledger:
        checked += 1
        if a not in ii0 or b not in ii0:
            bad.append(f"II.0's VAR block is missing {a} or {b}")
            continue
        if a not in a11 or b not in a11:
            bad.append(f"names.py has no Apple offset for {a} or {b}")
            continue
        got = (a11[b] - ii0[b]) - (a11[a] - ii0[a])
        if got != step:
            bad.append(f"the drift between {a} and {b} steps by {got:+d} "
                       f"words, but {why} accounts for {step:+d}")

    # And the ten II.0 names in the block all sit at the same drift.
    drifts = {n: a11[n] - ii0[n] for n in
              ("PREVSYMBLK", "OLDSYMBLK", "PREVLINESTART", "PREVSYMCURSOR",
               "OLDLINESTART", "OLDSYMCURSOR", "USEFILE")
              if n in ii0 and n in a11}
    checked += 1
    if len(drifts) != 7 or len(set(drifts.values())) != 1:
        bad.append(f"the seven names after TEXTSTRT do not share one drift: "
                   f"{drifts}")
    else:
        print(f"II.0's PREV*/OLD*/USEFILE all land at drift "
              f"{next(iter(drifts.values())):+d}, in reverse declaration order")

    # --- finding 40: 1.3's global growth, word for word ---------------------
    #
    # The correspondence table's shift steps say where 1.3 inserted words;
    # this says what each insertion is, and the total has to come out at the
    # difference between the two global areas.
    if "1.1" in facts and "1.3" in facts:
        f1, f3 = facts["1.1"], facts["1.3"]
        ledger = [
            ("ISPROG", 1),
            ("BYTEPTR+WORDPTR", 2),
            ("SEGSUSED", f3["SEGSUSED"] - f1["SEGSUSED"]),
            ("PROCTABLE", f3["PROCTABLE"] - f1["PROCTABLE"]),
            ("SEGMAP", f3["SEGMAP"] - f1["SEGMAP"]),
            ("JTAB", f3["JTAB"] - f1["JTAB"]),
            ("HAS128K+CONLIST+LSTOPEN", 3),
        ]
        checked += 1
        total, grew = sum(n for _w, n in ledger), f3["area"] - f1["area"]
        entries = ", ".join(f"{w} {n:+d}" for w, n in ledger)
        if total != grew:
            bad.append(f"1.3's global area grew by {grew} words, but the "
                       f"ledger accounts for {total}: {entries}")
        else:
            print(f"1.3 grows +{grew} words, all of it: {entries}")

        # The measured one the ledger leans on hardest, against a constant
        # the binary carries at the ERROR(253/254) guard.
        for ver, want in (("1.1", 24), ("1.3", 36)):
            checked += 1
            if facts[ver]["MAXJTAB"] != {want}:
                bad.append(f"{ver}: NEXTJTAB is compared against "
                           f"{sorted(facts[ver]['MAXJTAB'])}, not the "
                           f"MAXJTAB = {want} a {want + 1}-word JTAB needs")
            checked += 1
            if facts[ver]["JTAB"] != want + 1:
                bad.append(f"{ver}: JTAB spans {facts[ver]['JTAB']} words, "
                           f"not the {want + 1} MAXJTAB = {want} gives")

        # The three new tail words are 1.3's alone, and the first shift step
        # is the one word below ININTERFACE.
        checked += 1
        if f1["tail"] or len(f3["tail"]) != 3:
            bad.append(f"1.1 touches {f1['tail']} past DISKBUF and 1.3 "
                       f"touches {f3['tail']}; the ledger wants none and three")
        checked += 1
        if len(f3["low"]) - len(f1["low"]) != 1:
            bad.append(f"1.3 touches {len(f3['low'])} globals below "
                       f"ININTERFACE against 1.1's {len(f1['low'])}; the first "
                       f"shift step is one word")

    if bad:
        print("\n".join(bad))
        return 1
    print(f"{checked} checks, all passed")
    print("globalmap-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
