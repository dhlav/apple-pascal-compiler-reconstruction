"""Score the reconstructed operating system against Apple's shipped bytes.

`procbuild.py` is the per-procedure workbench for `SYSTEM.COMPILER`, where
every body is compared as it is written. The OS needs the other view: one
scoreboard over the whole file, run after each acceptance-tier compile, that
says how many procedures now come out instruction-identical and -- the part
that actually matters -- **whether any that used to be identical stopped
being so**. A change that gains four procedures and silently loses one is
not progress, and a tally that only counts the wins cannot tell the
difference.

What is compared is the disassembled instruction text of each procedure,
`enter_ic` through the return and including the exit sweep, with absolute
jump targets blanked exactly as `procbuild.strip_targets` blanks them: an
`FJP $092A` and an `FJP $0417` are the same instruction placed differently,
and a jump to the genuinely wrong place still shows, because the
instructions after it land in the wrong order.

`params` and `data` (both byte counts, from the procedure's attribute table)
are reported alongside, because they fail *independently* of the
instructions: a body can be instruction-for-instruction right and still be
built on a frame the wrong size, which means a declaration is wrong rather
than a statement. Those two numbers are the ones that caught `GETCMD.6`'s
value-`STRING` shadow copy (finding 198) and they are why a procedure is not
called exact here until all three agree.

Procedures are matched by (segment name, procedure number). The number is
not cosmetic: UCSD assigns it at the header, so declaration order *is* the
numbering, and a body that lands under the wrong number is wrong however
well its instructions read (finding 61, finding 199).

Usage:
    python tools/oscmp.py                    # the whole scoreboard
    python tools/oscmp.py GETCMD.6           # one procedure, with a diff
    python tools/oscmp.py --baseline F.json  # compare against a saved run
    python tools/oscmp.py --save F.json      # save this run as a baseline
"""
import argparse
import difflib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.pcode import disassemble, sweep_exit

from procbuild import listing, strip_targets

APPLE3 = ROOT / "evidence" / "disks" / \
    "Apple II Pascal 1.3 APPLE3_ 680-0290-A.dsk"
SHIPPED = "128K.PASCAL"
# The default "ours" is whatever compile probe_os_exact currently pins,
# read out of the probe rather than repeated here: the two used to be
# separate constants, and oscmp's went stale against a scratch extract
# while the probe had moved on -- a bare `oscmp` then reported 15 exact
# where the probe reported 57. One place to update, so they cannot drift.
# `--ours` overrides for scoring a fresh, not-yet-kept extract.
def _pinned_run() -> Path:
    src = (ROOT / "tools" / "probes" / "probe_os_exact.py").read_text()
    ns: dict = {"ROOT": ROOT, "Path": Path}
    for stmt in re.findall(r"^RUN = .*(?:\n\s+.*)*", src, re.M):
        exec(stmt, ns)
    return ns["RUN"]


OURS = _pinned_run()


def shipped_codefile() -> CodeFile:
    """Apple's own 128K OS, read straight off the evidence disk."""
    d = PascalDisk.from_file(APPLE3)
    e = d.find(SHIPPED)
    return CodeFile(d.read_blocks(e.first_block, e.blocks))


def procedures(cf: CodeFile) -> dict[str, tuple]:
    """Every p-code procedure, keyed 'SEGMENT.number'.

    Native procedures are skipped: they are the assembler's output, not the
    compiler's, and comparing them belongs to a run of `emuassemble.ps1`.
    """
    out = {}
    for seg in cf.segments:
        if not seg.length:
            continue
        for p in seg.pcode_procedures:
            key = f"{seg.name}.{p.number}"
            out[key] = (seg, p)
    return out


def body(seg, p) -> list[str]:
    """The comparable instruction text of one procedure."""
    return [strip_targets(t) for t in listing(seg, p)]


def compare(ours_cf: CodeFile, apple_cf: CodeFile) -> dict[str, dict]:
    ours, apple = procedures(ours_cf), procedures(apple_cf)
    rows: dict[str, dict] = {}
    for key in sorted(set(ours) | set(apple), key=sortkey):
        o, a = ours.get(key), apple.get(key)
        row = {"present_ours": o is not None, "present_apple": a is not None}
        if o and a:
            ob, ab = body(*o), body(*a)
            row.update(
                insns_ours=len(ob), insns_apple=len(ab),
                params_ours=o[1].param_size, params_apple=a[1].param_size,
                data_ours=o[1].data_size, data_apple=a[1].data_size,
            )
            # Exact means all three agree. An instruction-identical body on a
            # wrong-sized frame is a declaration bug, not a win.
            row["insns_same"] = ob == ab
            row["frame_same"] = (o[1].param_size == a[1].param_size
                                 and o[1].data_size == a[1].data_size)
            row["exact"] = row["insns_same"] and row["frame_same"]
        else:
            row["exact"] = False
        rows[key] = row
    return rows


def sortkey(key: str):
    seg, num = key.rsplit(".", 1)
    return (seg, int(num))


def render(rows: dict[str, dict], verbose: bool) -> None:
    exact = [k for k, r in rows.items() if r["exact"]]
    by_seg: dict[str, list[str]] = {}
    for k in exact:
        by_seg.setdefault(k.rsplit(".", 1)[0], []).append(k)

    print(f"{'procedure':<16} {'insns (ours/Apple)':>20} "
          f"{'params':>12} {'data':>12}   verdict")
    for key, r in rows.items():
        if not r["present_ours"]:
            print(f"{key:<16} {'-- not in ours --':>20}")
            continue
        if not r["present_apple"]:
            print(f"{key:<16} {'-- not in Apple --':>20}")
            continue
        if r["exact"]:
            verdict = "EXACT"
        elif r["insns_same"]:
            verdict = "insns match, FRAME DIFFERS"
        elif r["frame_same"]:
            verdict = "frame match, insns differ"
        else:
            verdict = "differs"
        if r["exact"] and not verbose:
            continue
        print(f"{key:<16} "
              f"{r['insns_ours']:>9}/{r['insns_apple']:<10} "
              f"{r['params_ours']:>5}/{r['params_apple']:<6} "
              f"{r['data_ours']:>5}/{r['data_apple']:<6}   {verdict}")

    print()
    print(f"instruction-and-frame identical: {len(exact)} of {len(rows)}")
    for seg in sorted(by_seg):
        nums = sorted(int(k.rsplit('.', 1)[1]) for k in by_seg[seg])
        print(f"  {seg}: {len(nums)} -- {nums}")


def diff_one(key: str, ours_cf: CodeFile, apple_cf: CodeFile) -> int:
    ours, apple = procedures(ours_cf), procedures(apple_cf)
    if key not in apple:
        print(f"{key} is not in Apple's {SHIPPED}")
        return 1
    if key not in ours:
        print(f"{key} is not in our build")
        return 1
    o, a = ours[key], apple[key]
    print(f"{key}: params {o[1].param_size}/{a[1].param_size}  "
          f"data {o[1].data_size}/{a[1].data_size}")
    ob, ab = body(*o), body(*a)
    if ob == ab:
        print(f"instructions identical ({len(ob)})")
    else:
        for line in difflib.unified_diff(ab, ob, "Apple", "ours",
                                         lineterm="", n=3):
            print(line)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("procedure", nargs="?",
                    help="one 'SEGMENT.number' to diff in full")
    ap.add_argument("--ours", type=Path, default=OURS,
                    help="the compiled codefile to score (default %(default)s)")
    ap.add_argument("--verbose", action="store_true",
                    help="list the exact procedures too, not just the rest")
    ap.add_argument("--save", type=Path,
                    help="write this run's verdicts as a baseline")
    ap.add_argument("--baseline", type=Path,
                    help="compare against a saved baseline and name what "
                         "was gained and, more importantly, lost")
    args = ap.parse_args()

    if not args.ours.exists():
        raise SystemExit(
            f"{args.ours} does not exist -- compile it in the emulator first "
            "(powershell -File tools/emucompile.ps1 -Name PASCALSY) and "
            "extract it with cp2 from build/disks/HD1.hdv")
    ours_cf = CodeFile(args.ours.read_bytes())
    apple_cf = shipped_codefile()

    if args.procedure:
        return diff_one(args.procedure, ours_cf, apple_cf)

    rows = compare(ours_cf, apple_cf)
    render(rows, args.verbose)

    if args.baseline:
        old = json.loads(args.baseline.read_text())
        was = {k for k, r in old.items() if r.get("exact")}
        now = {k for k, r in rows.items() if r["exact"]}
        gained, lost = sorted(now - was, key=sortkey), sorted(was - now,
                                                             key=sortkey)
        print(f"\nagainst {args.baseline.name}: "
              f"{len(was)} -> {len(now)}")
        print(f"  gained: {gained}")
        print(f"  lost:   {lost}")
        if lost:
            print("  a procedure that was exact and is no longer is a "
                  "REGRESSION, not noise -- find it before going on")
            return 1
    if args.save:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        args.save.write_text(json.dumps(rows, indent=1))
        print(f"\nsaved baseline {args.save}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
