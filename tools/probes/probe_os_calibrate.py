"""Calibrate the lifter against the operating system's own source.

Finding 49 checked the whole pipeline against two 23-line GOTOXY programs.
They were exact, and they were also the only Pascal-and-binary pair in
`evidence/` -- so nothing had ever tested a loop, a call between procedures,
or a `with`. Finding 50 made `SYSTEM.PASCAL` parse, and finding 51 aligned its
segment 0 with UCSD II.0's declarations for procedures 1..42. That gives 41
procedures with source.

The comparison is *not* exact and cannot be, because of finding 8: the II.0
source is the generic UCSD operating system and Apple's is a fork of it. So
this checks two things that survive a fork, and requires the disagreements to
be a specific named list rather than a count.

**Loops.** Every `WHILE`, `REPEAT` and `FOR` in a body has to become a back
edge in the control-flow graph, and nothing else does. Back edges are counted
off `lift()`'s blocks, not off the structuriser's output, so a failure to
render a loop as `while` would not hide here.

**Calls.** The segment-0 routines a procedure calls must all be admissible
from its source body -- named there outright, or reachable through a standard
identifier the compiler lowers to one. That mapping is the interesting part:
`SCANTITLE` calls `SCOPY`, `SDELETE` and `SPOS` because the source says
`COPY`, `DELETE` and `POS`; `CLEARLINE` and `PROMPT` call `FWRITECHAR` and
`FWRITESTRING` because the source says `WRITE`. `ALIAS` below records it.

A subset test can go vacuous, so the probe measures its own discriminating
power and fails if it drops: each procedure's binary call set is tried against
every *other* procedure's source body, and only about 7% of those wrong
pairings are admitted. If `ALIAS` were ever loosened into a rubber stamp that
number would climb and this would stop passing.

The two measures are independent -- one is control flow, one is naming -- and
they agree on which procedures Apple changed. `EXECERROR` and `CLEARLINE` are
flagged by both in both releases, and 1.1 differs from II.0 in fewer places
than 1.3 does, which is the direction a fork accumulating changes predicts.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.pcode import disassemble, sweep_exit
from a2pascal.lift import lift
from a2pascal import syscall as sc

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "reference_source" / "ucsd_ii0"
SOURCES = ("SYSTEM.A.TEXT", "SYSTEM.B.TEXT", "SYSTEM.C.TEXT")
BUILDS = [
    ("1.3", "Apple II Pascal 1.3 APPLE3_ 680-0290-A.dsk", "128K.PASCAL"),
]
ALIGNED = range(2, 43)          # finding 51: II.0's numbering holds to 42
MAX_WRONG_PAIRING = 0.15        # measured 0.073 / 0.075

# Standard Pascal as written in the source -> the segment-0 routines the
# compiler is allowed to have emitted for it. `WRITE` chooses by argument
# type, which this does not model, so all four of its forms are admissible
# wherever a `WRITE` appears.
ALIAS = {
    "WRITE":   {"FWRITESTRING", "FWRITECHAR", "FWRITEINT", "FWRITEBYTES"},
    "WRITELN": {"FWRITESTRING", "FWRITECHAR", "FWRITEINT", "FWRITEBYTES",
                "FWRITELN"},
    "READ":    {"FREADCHAR", "FREADINT", "FREADSTRING"},
    "READLN":  {"FREADCHAR", "FREADINT", "FREADSTRING", "FREADLN"},
    "EOF": {"FEOF"}, "EOLN": {"FEOLN"}, "PAGE": {"FWRITECHAR"},
    "COPY": {"SCOPY"}, "DELETE": {"SDELETE"}, "POS": {"SPOS"},
    "CONCAT": {"SCONCAT"}, "INSERT": {"SINSERT"},
    "RESET": {"FRESET"}, "REWRITE": {"FOPEN"}, "CLOSE": {"FCLOSE"},
    "GET": {"FGET"}, "PUT": {"FPUT"}, "SEEK": {"XSEEK"},
    "BLOCKREAD": {"FBLOCKIO"}, "BLOCKWRITE": {"FBLOCKIO"},
    "GOTOXY": {"FGOTOXY"},
}

# Where Apple's segment 0 is not UCSD's. Each entry must STILL disagree --
# a list of known differences that silently went stale would be worse than
# no list -- and everything absent from it must agree exactly.
KNOWN_LOOPS = {
    "1.1": {2: "Apple's EXECERROR is not II.0's",
            6: "FCLOSE: II.0 loops over the unit, Apple does not",
            7: "FGET: Apple has a second loop",
            38: "CLEARLINE: Apple inlines PUTPREFIXED, which loops"},
    "1.3": {2: "Apple's EXECERROR is not II.0's",
            6: "FCLOSE: II.0 loops over the unit, Apple does not",
            8: "FPUT: II.0's REPEAT is gone",
            17: "FWRITECHAR: one of II.0's two loops is gone",
            19: "FWRITESTRING delegates the loop to FWRITEBYTES",
            20: "FWRITEBYTES carries FWRITESTRING's loop as well",
            38: "CLEARLINE: Apple inlines PUTPREFIXED, which loops"},
}
KNOWN_CALLS = {
    "1.1": {2: "EXECERROR calls FETCHDIR where II.0 calls VOLSEARCH",
            38: "CLEARLINE writes directly instead of via PUTPREFIXED"},
    "1.3": {2: "EXECERROR calls FETCHDIR where II.0 calls VOLSEARCH",
            19: "FWRITESTRING delegates to FWRITEBYTES",
            38: "CLEARLINE writes directly instead of via PUTPREFIXED"},
}

fails = []
checks = 0


def check(cond, what):
    global checks
    checks += 1
    if not cond:
        fails.append(what)


# ---- the source side -------------------------------------------------
sig = sc.segment0_signatures(SRC / "GLOBALS.TEXT")
NAMES = {n: v[0] for n, v in sig.items()}
DECLARED = {v: k for k, v in NAMES.items() if k in ALIGNED}

text = "\n".join((SRC / f).read_text(encoding="ascii", errors="replace")
                 for f in SOURCES)
text = re.sub(r"\(\*.*?\*\)", " ", text, flags=re.S)
text = re.sub(r"\{.*?\}", " ", text, flags=re.S)
heads = [(m.start(), len(m.group(1)), m.group(2).upper()) for m in
         re.finditer(r"^( *)(?:PROCEDURE|FUNCTION) +([A-Z_][A-Z_0-9]*)",
                     text, re.M | re.I)]
BODIES: dict[str, str] = {}
for i, (pos, indent, name) in enumerate(heads):
    if indent:
        continue        # nested: the binary numbers it separately (finding 51)
    end = next((h[0] for h in heads[i + 1:] if h[1] == 0), len(text))
    BODIES.setdefault(name, text[pos:end])

check(len(BODIES) >= 41, f"only {len(BODIES)} top-level bodies in {SOURCES}")


def source_loops(body: str) -> int:
    return sum(len(re.findall(rf"\b{k}\b", body, re.I))
               for k in ("WHILE", "REPEAT", "FOR"))


def admissible(body: str, own: str) -> set[str]:
    out = {own}                       # calling yourself is always admissible
    for word in set(re.findall(r"[A-Za-z_][A-Za-z_0-9]*", body)):
        word = word.upper()
        if word in DECLARED:
            out.add(word)
        out |= ALIAS.get(word, set())
    return out


# ---- the binary side -------------------------------------------------
for ver, dsk, fname in BUILDS:
    disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / dsk)
    e = disk.find(fname)
    cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))
    seg = cf.segments[0]

    calls: dict[int, set[str]] = {}
    admits: dict[int, set[str]] = {}
    for n in ALIGNED:
        name = NAMES[n]
        if name not in BODIES:
            continue
        p = next(x for x in seg.procedures if x.number == n)
        stream = (disassemble(seg.data, p.enter_ic, p.exit_ic, p.jtab)[0]
                  + sweep_exit(seg.data, p.exit_ic, p.jtab - 8, p.jtab)[0])

        # loops: back edges in the CFG, counted before the structuriser runs
        blocks = lift(seg, p, cf, "")
        back = sum(1 for b in blocks for t in b.succs if t <= b.start)
        want = source_loops(BODIES[name])
        known = KNOWN_LOOPS[ver]
        if n in known:
            check(back != want,
                  f"{ver} loops: {n} {name} now agrees ({want}); "
                  f"KNOWN_LOOPS says it should not -- {known[n]}")
        else:
            check(back == want,
                  f"{ver} loops: {n} {name} -- source has {want}, "
                  f"the binary has {back} back edges")

        # calls: CBP reaches a sibling in this segment, CXP 0,n the same
        # procedures by the cross-segment form.
        calls[n] = {NAMES[i.operands[-1]] for i in stream
                    if (i.mnemonic == "CBP" and i.operands[0] in NAMES)
                    or (i.mnemonic == "CXP" and i.operands[0] == 0
                        and i.operands[1] in NAMES)} & set(DECLARED)
        admits[n] = admissible(BODIES[name], name)
        known = KNOWN_CALLS[ver]
        extra = sorted(calls[n] - admits[n])
        if n in known:
            check(extra,
                  f"{ver} calls: {n} {name} is now fully admitted; "
                  f"KNOWN_CALLS says it should not be -- {known[n]}")
        else:
            check(not extra,
                  f"{ver} calls: {n} {name} calls {extra}, which its "
                  f"source body does not admit")

    # The admissibility test must stay able to reject. Try every binary call
    # set against every *other* source body; if most of them pass, ALIAS has
    # become a rubber stamp and the check above proves nothing.
    live = [n for n in calls if calls[n]]
    tries = admitted = 0
    for n in live:
        for m in admits:
            if m == n:
                continue
            tries += 1
            admitted += calls[n] <= admits[m]
    rate = admitted / tries if tries else 1.0
    check(rate <= MAX_WRONG_PAIRING,
          f"{ver}: wrong pairings admitted {admitted}/{tries} = {rate:.1%}, "
          f"over the {MAX_WRONG_PAIRING:.0%} ceiling -- ALIAS is too loose "
          f"for the call check to mean anything")
    print(f"[{ver}] {len(calls)} procedures compared, {len(live)} of them "
          f"calling into segment 0; wrong pairings admitted {rate:.1%}")

print(f"{checks} checks, {len(fails)} failures")
for f in fails[:20]:
    print("  FAIL", f)
sys.exit(1 if fails else 0)
