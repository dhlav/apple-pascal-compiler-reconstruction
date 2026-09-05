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
RUN = ROOT / "acceptance" / "2026-09-04-pascalsystem-sysassoc" / \
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
    "FIOPRIMS.2", "FIOPRIMS.3",
    "PRINTERR.1",
    "USERPROG.1",
]

# Procedures still known to differ, kept here as the discrimination control
# (check 3 above). These are not failures -- they are the open work, and
# what matters is that the comparison still reports them as different.
STILL_DIFFERS = [
    "GETCMD.20",     # STARTCOMPILE: still a stub, 342 instructions
    "FIOPRIMS.5",    # 3 instructions against Apple's 275, still a stub
    "FILEPROC.4",    # FPOPEN: 563 against Apple's 473; see finding 220
    # The two procedures FIOPRIMS's shape blocks. FPUT's body is decoded
    # in full and written out in the source as a comment; it needs the
    # CXP 2,5 only an intrinsic unit can give it (finding 224).
    "PASCALSY.7",    # FGET: 1 against Apple's 234, still a stub
    "PASCALSY.8",    # FPUT: 1 against Apple's 46, blocked not unknown
    # Frame-identical, and every instruction matches but the two the
    # finding-218b stand-in costs. These two are the control for that
    # gap: if either ever reports exact, `IF FNXTBLK THEN` started
    # compiling and 218b has been answered.
    "FIOPRIMS.4",    # FPPEEK: 45 instructions against Apple's 43
    "FILEPROC.2",    # FPNEWBLK: 163 against Apple's 161
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
