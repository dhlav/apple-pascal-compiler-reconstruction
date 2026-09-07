"""Emit a codefile's global data map for both Apple Pascal versions.

Written for `SYSTEM.COMPILER`, which is still the default, but nothing in
it is compiler-specific: the offsets come out of the binary and the only
names it knows are the OS entry points every program calls. Pass
`--target` for another file. `SYSTEM.ASSMBLER` needs exactly this -- its
outer block carries 2215 words of globals and there is no source anywhere
to port them from, so the map is where the VAR block has to come from.
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.globals import collect, find_files, infer_objects
from a2pascal.syscall import segment0_procedures, csp_name

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "analysis" / "global_map"
OUT.mkdir(parents=True, exist_ok=True)
SEG0 = segment0_procedures(ROOT / "reference_source" / "ucsd_ii0" / "GLOBALS.TEXT")

DISKS = {
    "1.1": "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk",
    "1.3": "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk",
}


def pretty(detail: str) -> str:
    """Expand 'CSP n' and 'CXP 0,n' inside evidence text into names."""
    if "CSP " in detail:
        n = int(detail.split("CSP ")[1].split()[0])
        detail = detail.replace(f"CSP {n}", csp_name(n))
    if "CXP 0," in detail:
        n = int(detail.split("CXP 0,")[1].split()[0])
        detail = detail.replace(f"CXP 0,{n}", f"OS.{n} {SEG0.get(n, '?')}")
    return detail


def load(fname, target):
    disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / fname)
    e = disk.find(target)
    return CodeFile(disk.read_blocks(e.first_block, e.blocks))


ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--target", default="SYSTEM.COMPILER",
                help="codefile to map (default %(default)s)")
ap.add_argument("--disk", action="append", metavar="VER=FILE",
                help="override the disk holding it, e.g. "
                     "1.3='Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk'")
args = ap.parse_args()
TARGET = args.target
for spec in args.disk or []:
    ver, _, fname = spec.partition("=")
    DISKS[ver] = fname
# One output name per file: the compiler keeps the bare name it has always
# had, so every finding that cites globals-1.3.txt still resolves.
SUFFIX = "" if TARGET == "SYSTEM.COMPILER" else f"-{TARGET.rsplit('.', 1)[-1]}"

for ver, fname in list(DISKS.items()):
    try:
        cf = load(fname, TARGET)
    except Exception:                                   # noqa: BLE001
        print(f"[{ver}] {TARGET} is not on {fname} -- skipped")
        continue
    table, accesses, area = collect(cf, ver)
    objects = infer_objects(table, area)
    files = find_files(cf)

    touched = len(table)
    covered = sum(o["words"] for o in objects if o["words"])
    L = [f"Apple Pascal {ver} {TARGET} -- global data map",
         "",
         f"Global area: offsets 1..{area} ({area * 2} bytes), from PARAM SIZE",
         f"plus DATA SIZE of the outermost block (lex level 0).",
         f"Both words count: a UCSD activation record holds the block's",
         f"parameters and its locals in one offset space starting at 1, and",
         f"DATA SIZE alone is short by the two parameter words (finding 46).",
         f"Distinct global offsets touched: {touched}",
         f"Words accounted for by inferred objects: {covered} of {area}",
         f"  (the excess is the record at offset 3, whose five words are",
         f"   counted again as the four fields addressed individually)",
         "",
         "Offsets are WORD offsets into the shared global activation record.",
         "'scalar' = address never taken, only whole-word load/store.",
         "'aggregate' = address taken with LAO, so something bigger; the word",
         "count is exact when MOV/LDM/STM pinned it, otherwise it is an upper",
         "bound set by the next touched offset.",
         "",
         "VERIFIED BINARY FACT for the access counts; the object sizes marked",
         "'bounded by next touched offset' are STRONG INFERENCE.",
         "",
         f"{'off':>5} {'kind':<10} {'words':>6} {'rd':>5} {'wr':>5} {'&':>4} "
         f"{'users':>5}  sizing / evidence"]

    for o in objects:
        ev = Counter(pretty(e.detail) for e in o["evidence"])
        top = "; ".join(f"{d} x{c}" for d, c in ev.most_common(3))
        L.append(f"{o['offset']:>5} {o['kind']:<10} "
                 f"{str(o['words'] or '?'):>6} {o['reads']:>5} {o['writes']:>5} "
                 f"{o['addr_taken']:>4} {o['users']:>5}  {o['sizing']}"
                 + (f" | {top}" if top else ""))

    if files:
        L += ["", "File variables, from FINIT(f, window, recwords) call sites:",
              "",
              "  The window is always +300: BODY emits `LDA 0,VADDR` then",
              "  `LDA 0,VADDR+FILESIZE`, and compglbls.text has FILESIZE = 300",
              "  (NILFILESIZE = 40). It emits that for every file variable,",
              "  typed or not -- so only a TEXT, INTERACTIVE or FILE OF T is",
              "  really 300+ words and actually has a window there. An",
              "  untyped FILE is NILFILESIZE words and its window address",
              "  lands inside whatever follows. Finding 43.",
              "",
              "  recwords is BODY2's own tag (VERIFIED SOURCE FACT,",
              "  BODYPART.text): -1 = untyped FILE, -2 = TEXT,",
              "  0 = INTERACTIVE, otherwise FILTYPE^.SIZE in words.", ""]
        kind = {-1: "untyped FILE", -2: "TEXT", 0: "INTERACTIVE"}
        for fib, win, rec, site in files:
            what = kind.get(rec, f"FILE OF a {rec}-word type")
            L.append(f"  FIB at word {fib:>4}, window buffer at word {win:>4} "
                     f"(+{win - fib}), recwords={rec:>3}"
                     f"  [{what}]   ({site})")

    # The hottest globals are the compiler's core state; call them out.
    L += ["", "Busiest globals (by total accesses):", ""]
    for o in sorted(objects, key=lambda x: -(x["reads"] + x["writes"] + x["addr_taken"]))[:25]:
        v = table[o["offset"]]
        users = sorted(v.touched_by)
        L.append(f"  word {o['offset']:>4}  {o['kind']:<10} "
                 f"rd={o['reads']:<4} wr={o['writes']:<4} &={o['addr_taken']:<3} "
                 f"used by {len(users)} procedures")
        L.append(f"        {', '.join(users[:12])}"
                 + (" ..." if len(users) > 12 else ""))

    # Globals passed by address to a named OS routine are the strongest
    # single-site clue we have about what a global IS.
    L += ["", "Globals whose address is passed to a named runtime routine:", ""]
    seen = set()
    for o in objects:
        for e in o["evidence"]:
            if e.kind == "arg" and "CXP 0," in e.detail:
                n = int(e.detail.split("CXP 0,")[1].split()[0])
                key = (o["offset"], n)
                if key in seen:
                    continue
                seen.add(key)
                L.append(f"  word {o['offset']:>4} -> OS.{n} {SEG0.get(n, '?')}"
                         f"   ({e.site})")

    path = OUT / f"globals{SUFFIX}-{ver}.txt"
    path.write_text("\n".join(L), encoding="ascii")
    print(f"[{ver}] area={area} words, {touched} offsets touched, "
          f"{covered} words covered -> {path.name}")
