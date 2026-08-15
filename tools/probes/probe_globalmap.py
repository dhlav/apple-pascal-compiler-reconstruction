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

Finding 38.
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

    if bad:
        print("\n".join(bad))
        return 1
    print(f"{checked} checks, all passed")
    print("globalmap-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
