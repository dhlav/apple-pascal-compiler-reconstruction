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
RUN = ROOT / "acceptance" / "2026-09-02-pascalsystem-execblk" / \
    "PASCALSY.CODE"

# Verified under AppleWin on 2026-09-02, Apple's own compiler both sides.
# Grows as the reconstruction does; it must never shrink without a finding
# saying why.
EXACT = [
    "GETCMD.4", "GETCMD.6", "GETCMD.23",
    "INITIALI.7",
    "PASCALSY.2", "PASCALSY.9", "PASCALSY.10", "PASCALSY.11",
    "PASCALSY.14", "PASCALSY.15", "PASCALSY.21", "PASCALSY.22",
    "PASCALSY.23", "PASCALSY.24", "PASCALSY.25", "PASCALSY.26",
    "PASCALSY.44", "PASCALSY.45", "PASCALSY.46", "PASCALSY.47",
    "PASCALSY.51", "PASCALSY.52",
    "PRINTERR.1",
    "USERPROG.1",
]

# Procedures still known to differ, kept here as the discrimination control
# (check 3 above). These are not failures -- they are the open work, and
# what matters is that the comparison still reports them as different.
STILL_DIFFERS = [
    "PASCALSY.1",    # the outer block: 14 instructions against Apple's 24
    "PASCALSY.33",   # SCANTITLE: data 254 against Apple's 172
    "INITIALI.1",    # data 66 against Apple's 118, two banners missing
    "GETCMD.2",      # RUNWORKFILE: one arg is a global, not a local
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
