"""The OS procedures Apple's own compiler already reproduces exactly.

The kept acceptance run named by `RUN` below is what
Apple's real 1.3 `SYSTEM.COMPILER` wrote from `PASCALSYSTEM.text` under the
emulator. That run cannot be repeated inside `build_all.py` -- it is
interactive -- but its *result* can be re-checked on every build, which is
what `probe_acceptance.py` already does for the assembler and Linker runs.

The claim under test is a list, not a number: these named procedures come
out of Apple's compiler instruction-for-instruction identical to Apple's
shipped `128K.PASCAL`, on frames of exactly the same size. Naming them is
the point. A bare count can be held up by a procedure that started matching
while another stopped, and the whole reason `oscmp.py` reports gains and
losses separately is that a swap like that is the failure most worth
catching.

Three things can fail here, and each is worth catching:

  1. A procedure on the list stops matching. Both sides are frozen files,
     so that means this repository's own decoder or codefile reader changed
     what it reads out of one of them -- and every claim resting on that
     reader is then suspect.
  2. The total drops below the recorded floor.
  3. The comparison stops being able to discriminate at all. A comparison
     that returns "identical" for everything would pass checks 1 and 2
     while being worthless, so this also requires that the procedures known
     NOT to match still do not match. That is the check that keeps the
     other two honest.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from a2pascal.codefile import CodeFile
from oscmp import compare, shipped_codefile

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "acceptance" / "2026-09-06-pascalsystem-unit" / \
    "PASCALSY.CODE"

# Verified under AppleWin on 2026-09-02, Apple's own compiler both sides.
# Grows as the reconstruction does; it must never shrink without a finding
# saying why.
EXACT = [
    "GETCMD.2", "GETCMD.4", "GETCMD.6", "GETCMD.19", "GETCMD.23",
    "GETCMD.26",
    # Finding 225's nesting pass: .8 is inside .7, .12 inside .11,
    # .21 inside .20. Half of these could not be written at all until
    # that was established, because they read their parent's frame.
    "GETCMD.5", "GETCMD.7", "GETCMD.8", "GETCMD.10", "GETCMD.12",
    "GETCMD.24",
    # Finding 226.
    "GETCMD.3", "GETCMD.9", "GETCMD.22",
    # Finding 227: GETCMD.11 and the whole of its nested family. The
    # frame was mapped from the offsets its own children reach into it
    # with (LDA 1,<n>), so all seven landed together on the first
    # compile -- .11 could not be written before the children and the
    # children could not be written before .11.
    "GETCMD.13", "GETCMD.14", "GETCMD.15", "GETCMD.16", "GETCMD.17",
    "GETCMD.18", "GETCMD.11",
    # Finding 228: GETCMD is complete, all 27 of its procedures. The
    # segment body (.1) went last on purpose -- every CLP in it is a
    # procedure number, and a wrong one would have compiled as quietly
    # as a right one until all 26 callees were real.
    "GETCMD.25", "GETCMD.27", "GETCMD.1",
    "GETCMD.20", "GETCMD.21",
    # INITIALIZE is complete: all 11 of its procedures.
    "INITIALI.1", "INITIALI.2", "INITIALI.3", "INITIALI.4", "INITIALI.5",
    "INITIALI.6", "INITIALI.7", "INITIALI.8",
    "INITIALI.9", "INITIALI.10", "INITIALI.11",
    "PASCALSY.1",
    "PASCALSY.2", "PASCALSY.9", "PASCALSY.10", "PASCALSY.11",
    "PASCALSY.14", "PASCALSY.15",
    "PASCALSY.16", "PASCALSY.17", "PASCALSY.19", "PASCALSY.20",
    "PASCALSY.21", "PASCALSY.22",
    "PASCALSY.23", "PASCALSY.24", "PASCALSY.25", "PASCALSY.26",
    "PASCALSY.29", "PASCALSY.30", "PASCALSY.31", "PASCALSY.32",
    "PASCALSY.42",
    "PASCALSY.34", "PASCALSY.35", "PASCALSY.39",
    "PASCALSY.33",
    "PASCALSY.36", "PASCALSY.37", "PASCALSY.38",
    "PASCALSY.44", "PASCALSY.45", "PASCALSY.46", "PASCALSY.47",
    "PASCALSY.48", "PASCALSY.49", "PASCALSY.50", "PASCALSY.53",
    "PASCALSY.54", "PASCALSY.55", "PASCALSY.56",
    "PASCALSY.51", "PASCALSY.52", "PASCALSY.57", "PASCALSY.58",
    "PASCALSY.3", "PASCALSY.4", "PASCALSY.5", "PASCALSY.6",
    "PASCALSY.43",
    "PASCALSY.27",
    # PASCALSY is 56 of 58 now: only FGET and FPUT are left, and both are
    # behind FIOPRIMS's intrinsic-unit shape (findings 200, 224).
    "PASCALSY.12", "PASCALSY.13", "PASCALSY.18",
    "PASCALSY.28", "PASCALSY.40", "PASCALSY.41",
    "FILEPROC.1", "FILEPROC.3", "FILEPROC.5", "FILEPROC.6",
    "FILEPROC.7",
    # Finding 229: FPTITLE, once POS/COPY were written as sugar instead
    # of as direct SPOS/SCOPY calls -- the sugar builds its own argument
    # list, so the VAR-actual check that forced a scratch variable never
    # applied.
    "FILEPROC.8",
    "FIOPRIMS.2", "FIOPRIMS.3",
    # Finding 231. ODD and CHR are the two standard functions the
    # compiler emits no instruction for, so ODD(<integer>) is a free
    # cast to BOOLEAN -- which is what the four "unreachable"
    # procedures of finding 230 were each two instructions short of.
    # FIOPRIMS.5 (FPWINOUT, 275 instructions) was written from the
    # disassembly in the same pass and landed exact on the first
    # compile; FILEPROC is now complete, all 8.
    "FIOPRIMS.4", "FIOPRIMS.5",
    "FILEPROC.2", "FILEPROC.4",
    # Finding 232. FIOPRIMS is now the UNIT its SEGKIND says it is,
    # declared inline between USERPROGRAM's forward heading and its
    # body -- which is what puts it on segment 2 -- and FPUT USES it.
    # FIOPRIMS.1 is the unit's initialisation part, so it ends RNP 0
    # where a SEGMENT PROCEDURE ends RBP 0.
    "FIOPRIMS.1", "PASCALSY.8",
    "PRINTERR.1",
    "USERPROG.1",
]

# Procedures still known to differ, kept here as the discrimination control
# (check 3 above). These are not failures -- they are the open work, and
# what matters is that the comparison still reports them as different.
STILL_DIFFERS = [
    # One left in RUN, and finding 232b says no single compilation of
    # a single file can hold it alongside the rest. FGET needs
    # USES FIOPRIMS to name the four helpers it calls with CXP 2,n;
    # GETTEXT re-parses the interface with NEXTPROC := 2, zeroing
    # PROCTABLE[2..5] of the current segment, so the USES has to
    # precede segment 0's procedures 2-5 -- and FGET's own completion
    # cannot move there, because its nested EXECGETCH must claim
    # procedure 56 and that fixes its position after FBLOCKIO's.
    # EXECERROR (procedure 2) would have to be both before FGET, for
    # its own nested 51/52, and after it, to survive the zeroing.
    "PASCALSY.7",    # FGET: 1 against Apple's 234, a stub in RUN
]

# The other half of that trade, kept as its own run: the same file
# with FGET's real body and its USES, compiled by the same tool the
# same day. FGET comes out exact and the four procedures the zeroing
# lands on come out empty -- so the claim is not "FGET is probably
# right", it is "Apple's compiler wrote Apple's 234 instructions from
# this source", and the cost is exactly the four the finding names and
# no others. The directory keeps the source that produced it, so the
# run is reproducible rather than merely archived.
FGET_RUN = (ROOT / "acceptance" / "2026-09-06-pascalsystem-fget"
            / "PASCALSY.CODE")
FGET_EXACT = ["PASCALSY.7"]
FGET_LOST = ["PASCALSY.2", "PASCALSY.3", "PASCALSY.4", "PASCALSY.5"]

fail = []


def check(ok: bool, label: str) -> None:
    print(("  ok   " if ok else "  FAIL ") + label)
    if not ok:
        fail.append(label)


def main() -> int:
    if not RUN.exists():
        print(f"{RUN} is missing -- the acceptance run must be kept verbatim")
        return 1
    rows = compare(CodeFile(RUN.read_bytes()), shipped_codefile())

    print("=== procedures Apple's compiler reproduces exactly ===")
    for key in EXACT:
        r = rows.get(key)
        check(bool(r) and r["exact"], f"{key} instruction- and frame-identical")

    print("=== the count has not gone backwards ===")
    now = sum(1 for r in rows.values() if r["exact"])
    check(now >= len(EXACT),
          f"{now} exact, floor is {len(EXACT)} (of {len(rows)} procedures)")

    print("=== the comparison can still tell them apart ===")
    for key in STILL_DIFFERS:
        r = rows.get(key)
        check(bool(r) and not r["exact"],
              f"{key} still differs, as the reconstruction says it should")

    print("=== the FGET run, and what it costs (finding 232b) ===")
    if not FGET_RUN.exists():
        check(False, f"{FGET_RUN} is missing")
    else:
        frows = compare(CodeFile(FGET_RUN.read_bytes()), shipped_codefile())
        for key in FGET_EXACT:
            r = frows.get(key)
            check(bool(r) and r["exact"],
                  f"{key} instruction- and frame-identical in the FGET run")
        for key in FGET_LOST:
            r = frows.get(key)
            check(bool(r) and not r["exact"],
                  f"{key} emptied by that run's USES, as finding 232b says")
        ours = {k for k, r in rows.items() if r["exact"]}
        theirs = {k for k, r in frows.items() if r["exact"]}
        both = ours | theirs
        check(len(both) == len(rows),
              f"{len(both)} of {len(rows)} procedures exact across the two "
              f"runs together")

    print()
    if fail:
        print(f"OS exact: {len(fail)} check(s) failed")
        return 1
    print(f"OS exact: {len(EXACT)} named procedures verified, "
          f"{now} exact overall")
    print("os-exact-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
