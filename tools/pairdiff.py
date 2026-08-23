"""Ask of every 1.1 body: is what is left of its diff the same noise 1.3 has?

`procbuild.py` compares one reconstruction against one binary. The fast
tier cannot accept a body outright (finding 58c, finding 87c), so a great
many procedures come back DIFFERS for reasons that have nothing to do with
the source -- and reading each one to decide which is a slow way to spend
the 1.1 port.

There is a control available that the single-version comparison does not
use. The 1.3 tree is verified, procedure for procedure, against Apple's
own compiler in the emulator (finding 87). So for a procedure that exists
in both releases:

    if  diff(Apple 1.1, ours 1.1)  ==  diff(Apple 1.3, ours 1.3)

then whatever the fast tier is doing to our 1.1 body it does identically to
a 1.3 body that is KNOWN right, and the 1.1 body is right in the same
places. That is not proof the 1.1 body is correct -- it inherits exactly
the confidence 1.3's has, no more -- but it is enough to take the procedure
off the worklist and put it in the emulator tier's queue instead.

Where the two diffs are NOT the same, the difference between them is the
interesting part, and it is what this prints: the chunks 1.1 diverges in
that 1.3 does not.

Procedures are paired by the name `a2pascal.names` gives them in their
segment, which is where the 1.1-to-1.3 numbering shift already lives.

Usage:
    python tools/pairdiff.py            # every paired body
    python tools/pairdiff.py DECLARAT   # one segment
"""
import difflib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a2pascal.codefile import CodeFile
from a2pascal.names import PROC_NAMES
import procbuild as pb
import xcompile

ROOT = Path(__file__).resolve().parent.parent
TABLE = (ROOT / "analysis" / "global_map"
         / "correspondence-1.1-to-1.3.txt")

GLOBAL_OPS = ("LAO", "LDO", "SRO", "SLDO")
GLOBAL_RE = re.compile(r"^(LAO|LDO|SRO|SLDO) (\d+)$")
CXP_RE = re.compile(r"^CXP (\d+),(\d+)$")


def correspondence() -> tuple[dict[int, int], dict[tuple[str, int], int]]:
    """The 1.1 -> 1.3 global and procedure maps, read off the table.

    A global's OFFSET and a procedure's NUMBER are the two things that move
    between the releases for reasons that have nothing to do with what a
    body says: 1.3 declares more globals and two more procedures. Rewriting
    them into 1.3's numbering is what lets two diffs be compared as text.
    """
    glob: dict[int, int] = {}
    proc: dict[tuple[str, int], int] = {}
    for line in TABLE.read_text(encoding="ascii",
                                errors="replace").splitlines():
        m = re.fullmatch(r"\s*(\d+)\s+(\d+)\s+[-+]\d+\s+\d+\s+[\d.]+", line)
        if m:
            glob[int(m.group(1))] = int(m.group(2))
            continue
        m = re.fullmatch(r"\s*(\w+)\.(\d+) -> (\w+)\.(\d+)\s+sim=.*", line)
        if m and m.group(1) == m.group(3):
            proc[(m.group(1), int(m.group(2)))] = int(m.group(4))
    return glob, proc


GLOBALS, PROCS = correspondence()
SEGOF = {1: "PASCALCO"} | {n: s for n, s in pb.flat_segdecls()}


def to13(seg: str, lines: list[str]) -> list[str]:
    """Put a 1.1 listing's global offsets and procedure numbers in 1.3's."""
    out = []
    for text in lines:
        m = GLOBAL_RE.match(text)
        if m and int(m.group(2)) in GLOBALS:
            out.append(f"{m.group(1)} {GLOBALS[int(m.group(2))]}")
            continue
        m = CXP_RE.match(text)
        if m:
            # `renumber` has already put phase segments at Apple's numbers,
            # so the segment half needs no correction -- only the procedure
            # half, which can shift inside a phase the same way it does
            # inside segment 1.
            target = SEGOF.get(int(m.group(1)))
            key = (target, int(m.group(2)))
            if target and key in PROCS:
                out.append(f"CXP {m.group(1)},{PROCS[key]}")
                continue
        m = re.fullmatch(r"(CLP|CGP) (\d+)", text)
        if m and (seg, int(m.group(2))) in PROCS:
            out.append(f"{m.group(1)} {PROCS[(seg, int(m.group(2)))]}")
            continue
        out.append(text)
    return out


LOCAL_RE = re.compile(r"^(STL|SLDL|LDL|LLA) (\d+|WITHTMP)$")


def withtmp(lines: list[str], words: int) -> list[str]:
    """Name the topmost frame word instead of numbering it.

    Where Apple's frame is larger than ours it is because Apple's compiler
    took a temporary ours did not. The extra word is at the top of the
    frame, so its offset is the whole frame's size in words, parameters
    included. Giving it a name rather than an offset is what lets a 1.1
    leftover be compared against 1.3's as text when the two frames differ
    in size for reasons of their own.
    """
    out = []
    for text in lines:
        m = LOCAL_RE.match(text)
        out.append(f"{m.group(1)} WITHTMP"
                   if m and m.group(2).isdigit() and int(m.group(2)) == words
                   else text)
    return out


def islocal(run) -> bool:
    """Is this run nothing but references to the frame's own words?"""
    return bool(run) and all(LOCAL_RE.match(x) for x in run)


def sameops(x, y) -> bool:
    return [LOCAL_RE.match(v).group(1) for v in x] ==            [LOCAL_RE.match(v).group(1) for v in y]


def noise(chunk) -> bool:
    """Is this chunk one of the documented fast-tier spellings and nothing
    else?

    Two classes, both of which can appear in a 1.1 body whose 1.3
    counterpart has no matching chunk to be compared against:

      * finding 58c. Apple's compiler evaluates both halves of a boolean
        AND/OR and joins them with LAND/LOR; the fast tier short-circuits
        with a conditional jump.

      * compiler temporaries. The two compilers do not allocate the same
        anonymous frame words: Apple stashes a FOR statement's limit in one
        and takes another for a WITH (finding 87c), ucsdpsys_compile takes
        neither, or takes one where Apple takes two. What survives is a run
        of local references on one side alone, or the same run of local
        opcodes on both sides with the offsets shifted.
    """
    tag, x, y = chunk
    if tag == "delete" and x in (("LAND",), ("LOR",)):
        return True
    if tag == "insert" and y in (("FJP $----",), ("TJP $----",)):
        return True
    if tag == "delete" and islocal(x):
        return True
    if tag == "insert" and islocal(y):
        return True
    if tag == "replace" and islocal(x) and islocal(y) and sameops(x, y):
        return True
    return False


def chunks(la: list[str], lb: list[str]) -> list[tuple[str, ...]]:
    """The diff, as the runs that are not equal. Placement is already gone."""
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
            None, la, lb, autojunk=False).get_opcodes():
        if tag != "equal":
            out.append((tag, tuple(la[i1:i2]), tuple(lb[j1:j2])))
    return out


def noise(chunk) -> bool:
    """Is this chunk finding 58c and nothing else?

    Apple's compiler evaluates both halves of a boolean AND/OR and joins
    them with LAND/LOR; the fast tier short-circuits with a jump. Where a
    1.1 body has such an expression and its 1.3 counterpart does not, the
    chunk has no pair to be compared against, but it is still only the
    documented spelling difference -- a lone LAND/LOR on Apple's side, or a
    lone conditional jump on ours.
    """
    tag, x, y = chunk
    if tag == "delete" and x in (("LAND",), ("LOR",)):
        return True
    if tag == "insert" and y in (("FJP $----",), ("TJP $----",)):
        return True
    return False


def segnames(ver: str) -> list[str]:
    """Segment 1 and every phase that has a source file."""
    out = [s for s, _t, _p in pb.sources(ver)]
    out += [n for _num, n in pb.flat_segdecls()
            if pb.phase_body(ver, n) is not None]
    return out


def bodies(ver: str, cf):
    """Every (segment, number, Apple's listing, our listing) of one build."""
    for segname in segnames(ver):
        apple = pb.apple_segment(ver, segname)
        mine = cf.segment(segname)
        ours = {x.number: x for x in mine.procedures}
        for a in sorted(apple.procedures, key=lambda x: x.number):
            b = ours.get(a.number)
            if b is None:
                continue
            la = [pb.strip_targets(x) for x in pb.listing(apple, a)]
            if a.data_size > b.data_size:
                la = withtmp(la, (a.param_size + a.data_size) // 2)
            lb = pb.unfold(pb.renumber(
                [pb.strip_targets(x) for x in pb.listing(mine, b)]))
            yield (segname, a.number,
                   pb.foldset(pb.addressing(pb.forlimit(pb.drop_nops(la)))),
                   pb.foldset(pb.addressing(pb.forlimit(pb.drop_nops(lb)))), a, b)


def build(ver: str):
    segs = pb.sources(ver)
    if not segs:
        raise SystemExit(f"no sources for {ver}")
    return CodeFile(xcompile.compile_text(pb.spliced(ver, segs, fast=True)))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not xcompile.available():
        print("SKIPPED: ucsdpsys_compile is not built")
        return 0
    want = {a.upper() for a in sys.argv[1:] if not a.startswith("-")}

    byname = {}
    for seg, num, la, lb, a, b in bodies("1.3", build("1.3")):
        name = PROC_NAMES["1.3"].get((seg, num))
        if name:
            byname[(seg, name)] = (chunks(la, lb),
                                   a.data_size - b.data_size)

    same = only11 = unpaired = 0
    for seg, num, la, lb, a, b in bodies("1.1", build("1.1")):
        if want and seg not in want:
            continue
        name = PROC_NAMES["1.1"].get((seg, num))
        # Both listings are 1.1's, so both get the same rewrite: what is
        # being compared is the DIFFERENCE between them, and a difference
        # only survives the rewrite if it is one of substance.
        here = chunks(to13(seg, la), to13(seg, lb))
        gap = a.data_size - b.data_size
        if not here and gap == 0:
            continue                      # procbuild already calls it clean
        pair = byname.get((seg, name)) if name else None
        if pair is None:
            unpaired += 1
            print(f"[{seg}.{num} {name or '?'}] no 1.3 counterpart to "
                  f"compare against -- {len(here)} chunk(s), frame gap {gap}")
            continue
        there, theregap = pair
        # A subset counts: "nothing more than 1.3's diff". 1.1 can carry
        # fewer chunks than 1.3 simply by being the shorter body.
        if all(c in there or noise(c) for c in here) and gap == theregap:
            same += 1
            continue
        only11 += 1
        print(f"[{seg}.{num} {name}] diverges from 1.3's own diff"
              + (f" (frame gap {gap}, 1.3's {theregap})"
                 if gap != theregap else ""))
        for tag, x, y in here:
            if (tag, x, y) in there:
                continue
            for k in range(max(len(x), len(y))):
                print(f"    -> {x[k] if k < len(x) else '-':<24} "
                      f"{y[k] if k < len(y) else '-'}")
        print()

    print(f"{same} bodies carry exactly 1.3's diff and nothing more, "
          f"{only11} diverge, {unpaired} have no counterpart")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
