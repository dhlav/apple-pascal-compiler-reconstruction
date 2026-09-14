"""SYSTEM.LIBRARY: all six units' code, by Apple's compiler, assembler, Linker.

acceptance/2026-09-14-library-units holds the run (finding 285): the six
unit sources in src/pascal/units/1.3/ compiled by SYSTEM.COMPILER as U*,
the three native sources in src/native/ assembled by SYSTEM.ASSMBLER as
N*, and the three units with native halves linked by SYSTEM.LINKER as L*.

Claims, each of which the binary can fail:

  1. **Every code segment is Apple's, byte for byte**: TRANSCEN, CHAINSTU
     and PASCALIO straight from the compile; LONGINTI, TURTLEGR and APPLESTU
     from the link. Also the SEGKIND and SEGINFO words.
  2. **The link did the work**: the same three straight from the compile are
     UNLINKED_INTRINS and shorter, so a comparison that passed them would
     be broken.
  3. **TURTLEGR's DATA segment**: slot 2 is a DATASEG of 386 bytes on no
     block, as Apple's slot 5 is.
  4. **The kept consoles report clean runs.**

Not claimed: the interface text the compiler copies ahead of each segment.
It is copied from the source file's own bytes, DLE indentation and page
position included, and those are not what the plain sources here encode
(finding 285).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from a2pascal.codefile import CodeFile
from a2pascal.disk import PascalDisk

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "acceptance" / "2026-09-14-library-units"
DISK = ROOT / "evidence" / "disks" / "Apple II Pascal 1.3 APPLE1_ 680-0283-A.dsk"
FROM = {"TRANSCEN": "UTRANS", "CHAINSTU": "UCHAIN", "PASCALIO": "UPASIO",
        "LONGINTI": "LLONG", "TURTLEGR": "LTURTLE", "APPLESTU": "LAPPLE"}
UNLINKED = {"LONGINTI": "ULONG", "TURTLEGR": "UTURTLE",
            "APPLESTU": "UAPPLE"}

fail = []


def check(ok: bool, label: str) -> None:
    print(("  ok   " if ok else "  FAIL ") + label)
    if not ok:
        fail.append(label)


def code_segment(cf: CodeFile, name: str):
    return next(s for s in cf.segments if s.name == name and s.block)


def main() -> int:
    apple = CodeFile(PascalDisk.from_file(DISK).read_file("SYSTEM.LIBRARY"))

    print("=== every code segment is Apple's ===")
    for name, run in FROM.items():
        want = code_segment(apple, name)
        got = code_segment(CodeFile((RUN / f"{run}.CODE").read_bytes()), name)
        check(got.data == want.data
              and (got.segkind_raw, got.seg_num, got.mtype, got.version)
              == (want.segkind_raw, want.seg_num, want.mtype, want.version),
              f"{name} from {run}: {len(got.data)} bytes, kind "
              f"{got.segkind_raw}, segment {got.seg_num}, {got.mtype}")

    print("=== the link did the work ===")
    for name, run in UNLINKED.items():
        want = code_segment(apple, name)
        got = code_segment(CodeFile((RUN / f"{run}.CODE").read_bytes()), name)
        check(got.segkind_raw == 5 and len(got.data) < len(want.data),
              f"{name} unlinked in {run}: kind {got.segkind_raw}, "
              f"{len(got.data)} of {len(want.data)} bytes")

    print("=== TURTLEGR's data segment ===")
    ours = CodeFile((RUN / "LTURTLE.CODE").read_bytes())
    d_ours = [s for s in ours.segments if s.segkind_raw == 7]
    d_apple = [s for s in apple.segments if s.segkind_raw == 7]
    check(len(d_ours) == len(d_apple) == 1
          and (d_ours[0].name, d_ours[0].length, d_ours[0].block,
               d_ours[0].seg_num)
          == (d_apple[0].name, d_apple[0].length, d_apple[0].block,
              d_apple[0].seg_num),
          f"one DATASEG, TURTLEGR, 386 bytes, no block, segment 21: "
          f"{[(s.name, s.length, s.block, s.seg_num) for s in d_ours]}")

    print("=== the kept consoles report clean runs ===")
    for p in sorted(RUN.glob("*-console.txt")):
        text = p.read_text(errors="replace")
        text = text.replace("0   Errors flagged on this Assembly", "")
        bad = any(w in text for w in ("rror", "undefined", "mismatch"))
        check(not bad, p.name)

    print()
    if fail:
        print(f"library units: {len(fail)} check(s) failed")
        return 1
    print("library units: all six code segments Apple's")
    print("library-units-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
