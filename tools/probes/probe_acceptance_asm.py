"""What Apple's own assembler produced, against what Apple shipped.

`probe_prog_native_asm.py` and its two siblings run `tools/asm6502.py`, which
is this project's reimplementation and can only ever falsify a source. The
authority is `SYSTEM.ASSMBLER` itself, run under AppleWin (finding 44e), and
that run is interactive -- it cannot be part of `build_all.py`.

What can be part of it is the *result*. `acceptance/` keeps the codefile each
run produced exactly as it came off the emulator, and this compares it
against the binary Apple shipped. The reimplementation is not involved at
any point here: both sides are Apple's.

The comparison needs no relocation applied to either side. A native procedure
is stored in a codefile with its address words still holding offsets from the
start of the procedure -- relocation is the loader's work, not the Linker's --
so the assembler's fresh output and a procedure the Linker placed at $0902
inside a larger segment hold the same 354 bytes (finding 103f).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile, RELOC_KINDS

ROOT = Path(__file__).resolve().parents[2]
ACC = ROOT / "acceptance"
DISKS = ROOT / "evidence" / "disks"

# (run directory, the codefile it produced, the segment and procedure in it,
#  then the shipped disk, codefile, segment and procedure to match)
RUNS = [
    ("2026-08-24-formatter-native", "FMTNATIV.CODE", "FORMATDI", 1,
     "Apple II Pascal 1.3 APPLE3_ 680-0290-A.dsk", "FORMATTER.CODE",
     "FORMATTE", 2),
]


def native(cf, segname, num, where, bad):
    seg = next((s for s in cf.segments if s.name.strip() == segname), None)
    if seg is None:
        bad.append(f"{where}: no segment {segname}")
        return None, None
    p = next((q for q in seg.native_procedures if q.number == num), None)
    if p is None:
        bad.append(f"{where}: {segname}.{num} is not a native procedure")
    return seg, p


def main() -> int:
    bad, checked = [], 0

    def check(cond, msg):
        nonlocal checked
        checked += 1
        if not cond:
            bad.append(msg)

    for run, out, oseg, onum, dsk, code, dseg, dnum in RUNS:
        d = ACC / run
        check(d.is_dir(), f"{run}: the run directory is gone")
        if not d.is_dir():
            continue
        check((d / "screen.png").exists(),
              f"{run}: the screen at the end of the run is not kept")

        a = CodeFile((d / out).read_bytes())
        b = CodeFile(PascalDisk.from_file(DISKS / dsk).read_file(code))
        aseg, ap = native(a, oseg, onum, f"{run}/{out}", bad)
        bseg, bp = native(b, dseg, dnum, code, bad)
        if ap is None or bp is None:
            continue

        mine = aseg.data[ap.enter_ic:ap.jtab + 2]
        disk = bseg.data[bp.enter_ic:bp.jtab + 2]
        check(len(mine) == len(disk),
              f"{run}: the assembler wrote {len(mine)} bytes, "
              f"{code} carries {len(disk)}")
        if len(mine) == len(disk):
            diffs = [i for i, (x, y) in enumerate(zip(mine, disk)) if x != y]
            check(not diffs,
                  f"{run}: {len(diffs)} byte(s) differ, first at "
                  f"+${diffs[0]:04X}: assembler {mine[diffs[0]]:02x}, "
                  f"{code} {disk[diffs[0]]:02x}" if diffs else "")

        for k in RELOC_KINDS:
            check(sorted(t - ap.enter_ic for t in ap.reloc[k])
                  == sorted(t - bp.enter_ic for t in bp.reloc[k]),
                  f"{run}: {k}-relative -- the assembler wrote "
                  f"{sorted(t - ap.enter_ic for t in ap.reloc[k])}, "
                  f"{code} carries "
                  f"{sorted(t - bp.enter_ic for t in bp.reloc[k])}")

    if bad:
        print("\n".join(bad))
        return 1
    print(f"{checked} checks, all passed")
    print("acceptance-asm-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
