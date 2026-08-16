"""Check `case` against source, using the one table that has both.

Finding 52 calibrated loops and calls across 41 procedures and could not
reach a `case`: segment 0 does not contain one. `PRINTERROR` does. It is slot
3 of the same file, it is a 15-arm `CASE` with a second 19-arm `CASE` nested
inside one of its arms, every arm assigns a string literal, and UCSD's source
for it is in `SYSSEGS.A.TEXT`.

That makes it an unusually good test, because the strings are the answer key.
A jump table mis-read by one, an arm attributed to the wrong label, or an
`LSA` mis-sized would all show up as a message landing on the wrong number --
and the numbers are error codes, so they are not interchangeable.

What comes out: **31 arms in 1.1 and 21 in 1.3 carry a message identical to
UCSD's, character for character**, and almost all of the rest are Apple
rewording the same message (`'No proc in seg-table'` becomes `'No procedure
in segment-table'`, `'dup dir entry'` becomes `'duplicate directory entry'`).
The structure matches exactly -- the default assignment before the case, all
fifteen outer labels, the nesting of the second table inside arm 10. 1.1 is
again the nearer of the two to II.0, as in finding 52d.

Apple's departures are held as a named list per release, the same discipline
finding 52 uses: the I/O errors it redefined outright, the labels it dropped,
the ones it added. If any of those stops being a departure the probe fails,
so the list cannot quietly go stale. A reworded arm must still share a word
with UCSD's, so a message landing on the wrong error number is caught.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.lift import lift
from a2pascal.structure import structure

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "reference_source" / "ucsd_ii0" / "SYSSEGS.A.TEXT"
BUILDS = [
    ("1.1", "UCSD Pascal 1.1_1.dsk", "SYSTEM.PASCAL"),
    ("1.3", "Apple II Pascal 1.3 APPLE1_ 680-0283-A.dsk", "SYSTEM.PASCAL"),
]
# Apple's departures from II.0, per release. Each must STILL be a departure.
DROPPED = {"1.1": {15, 19}, "1.3": {15}}          # inner labels II.0 has, Apple lacks
ADDED_OUTER = {"1.1": set(), "1.3": {16}}
ADDED_INNER = {"1.1": set(), "1.3": {20}}
REDEFINED = {                                  # inner labels Apple reused
    "1.1": {18: "bad byte count"},
    "1.3": {18: "bad byte count", 19: "bad init record"},
}
MIN_IDENTICAL = {"1.1": 31, "1.3": 21}   # 1.1 is the nearer to II.0

fails = []
checks = 0


def check(cond, what):
    global checks
    checks += 1
    if not cond:
        fails.append(what)


# ---- II.0's arms -----------------------------------------------------
text = SRC.read_text(encoding="ascii", errors="replace")
body = text[text.index("SEGMENT PROCEDURE PRINTERROR"):]
body = body[:body.index("END (*PRINTERROR*)")]
i0, i1 = body.index("CASE IORSLT OF"), body.index("END (*IO ERRORS*)")


def arms(t):
    return {int(m.group(1)): m.group(2) for m in
            re.finditer(r"^\s*(\d+):\s*(?:BEGIN\s*)?S := '([^']*)'", t, re.M)}


SRC_OUTER = arms(body[:i0] + body[i1:])
SRC_INNER = arms(body[i0:i1])
check(len(SRC_OUTER) == 15, f"II.0's outer case has {len(SRC_OUTER)} arms, want 15")
check(len(SRC_INNER) == 19, f"II.0's inner case has {len(SRC_INNER)} arms, want 19")

ARM = re.compile(r"^(\s*)(\d+): begin\s*\n\s*@?G\d+\^? := '([^']*)'", re.M)

for ver, dsk, fname in BUILDS:
    disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / dsk)
    e = disk.find(fname)
    cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))
    seg = cf.segment("PRINTERR")
    p = next(x for x in seg.procedures if x.number == 1)
    rendered, gotos, _ = structure(lift(seg, p, cf, ""), "procedure PRINTERR.1;")

    check(gotos == 0, f"{ver}: PRINTERROR structures with {gotos} gotos, want 0")
    check(rendered.count("case ") == 2,
          f"{ver}: {rendered.count('case ')} case statements, want 2")

    # The nested table must sit inside the outer arm labelled 10, exactly
    # where II.0 puts it. Split there and read the arms of each.
    inner_at = rendered.index("case ", rendered.index("case ") + 1)
    check(rendered[:inner_at].rfind("\n    10: begin") != -1,
          f"{ver}: the nested case is not inside outer arm 10, "
          f"where II.0 puts it")

    indent = ARM.search(rendered[inner_at:]).group(1)
    inner_txt = rendered[inner_at:]
    end = inner_txt.index("\n" + indent[:-2] + "end;")
    got_inner = {int(m.group(2)): m.group(3) for m in ARM.finditer(inner_txt[:end])}
    got_outer = {int(m.group(2)): m.group(3)
                 for m in ARM.finditer(rendered[:inner_at] + inner_txt[end:])}

    identical = 0
    for label, (S, A, dropped, added) in (
            ("outer", (SRC_OUTER, got_outer, set(), ADDED_OUTER[ver])),
            ("inner", (SRC_INNER, got_inner, DROPPED[ver], ADDED_INNER[ver]))):
        check(set(S) - set(A) == dropped,
              f"{ver} {label}: II.0 labels Apple lacks are "
              f"{sorted(set(S) - set(A))}, expected {sorted(dropped)}")
        check(set(A) - set(S) == added,
              f"{ver} {label}: Apple-only labels are "
              f"{sorted(set(A) - set(S))}, expected {sorted(added)}")
        for k in sorted(set(S) & set(A)):
            redef = REDEFINED[ver] if label == "inner" else {}
            if k in redef:
                check(S[k] != A[k],
                      f"{ver} {label} {k}: now matches II.0 ({S[k]!r}); "
                      f"REDEFINED says Apple changed it")
                check(S[k] == redef[k],
                      f"{ver} {label} {k}: II.0 says {S[k]!r}, "
                      f"REDEFINED expects {redef[k]!r}")
                continue
            if S[k] == A[k]:
                identical += 1
                continue
            # Reworded: it must still be the same message, not a different
            # error that happened to land on this number.
            tok = lambda s: set(re.findall(r"[a-z0-9#]+", s.lower()))
            check(bool(tok(S[k]) & tok(A[k])),
                  f"{ver} {label} {k}: II.0 says {S[k]!r} but the binary "
                  f"says {A[k]!r}, with no word in common")

    check(identical >= MIN_IDENTICAL[ver],
          f"{ver}: {identical} arms identical to II.0, want at least "
          f"{MIN_IDENTICAL[ver]}")
    print(f"[{ver}] PRINTERROR: {len(got_outer)} + {len(got_inner)} arms, "
          f"{identical} of them carrying UCSD's message unchanged")

print(f"{checks} checks, {len(fails)} failures")
for f in fails[:20]:
    print("  FAIL", f)
sys.exit(1 if fails else 0)
