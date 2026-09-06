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
RUN = ROOT / "acceptance" / "2026-09-06-pascalsystem-odd" / \
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
    "PRINTERR.1",
    "USERPROG.1",
]

# Procedures still known to differ, kept here as the discrimination control
# (check 3 above). These are not failures -- they are the open work, and
# what matters is that the comparison still reports them as different.
STILL_DIFFERS = [
    # The three procedures FIOPRIMS's *shape* blocks, and nothing else
    # is left. FIOPRIMS is an intrinsic unit (SEGKIND 6 in the shipped
    # dictionary, finding 200), so its body is a UNIT initialisation
    # part at PFLEV 1 and ends RNP 0 where a SEGMENT PROCEDURE ends
    # RBP 0; and FGET/FPUT reach FPWINADV/FPDLE/FPPEEK/FPWINOUT by
    # CXP 2,n, which needs those four names visible outside the
    # segment. FPUT's body is decoded in full and kept in the source
    # as a comment (finding 224).
    "FIOPRIMS.1",    # 1 instruction, RBP 0 where Apple has RNP 0
    "PASCALSY.7",    # FGET: 1 against Apple's 234, still a stub
    "PASCALSY.8",    # FPUT: 1 against Apple's 46, blocked not unknown
]

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
