"""Pseudo-Pascal for the rest of the disk set.

The companion to `disasm_utils.py`: every codefile on the six evidence
disks other than `SYSTEM.COMPILER` and `SYSTEM.LIBRARY`, lifted and
structured the same way, into `analysis/utilities/`.

The per-file coverage line is the useful output. The lifter and structurer
were built against the compiler and the library, and a utility they cannot
follow is either a construct those two never used or a bug -- either way it
is worth knowing before the source is written rather than after.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from liftall import lift_codefile
from disasm_utils import DISKS, SKIP, OUT, targets

# The boot disk of each release, for the Intrinsic Units a program calls but
# does not contain.
LIBDISK = {"1.3": "Apple II Pascal 1.3 APPLE1_ 680-0283-A.dsk",
           "1.1": "UCSD Pascal 1.1_1.dsk"}


def library(ver):
    """{segment number: Segment} for every unit in that release's library."""
    path = ROOT / "evidence" / "disks" / LIBDISK[ver]
    disk = PascalDisk.from_file(path)
    try:
        e = disk.find("SYSTEM.LIBRARY")
    except Exception:                                   # noqa: BLE001
        return {}
    cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))
    return {s.number: s for s in cf.segments if s.procedures}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    tot_c = tot_n = tot_s = tot_g = 0
    libs = {}
    want = targets()
    for tag, fname in DISKS.items():
        disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / fname)
        for e in disk.directory():
            if e.kind != "codefile" or e.name in SKIP or e.name not in want:
                continue
            cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))
            ver = tag.split("-")[0]
            text, clean, total, structured, gotos, _ = lift_codefile(
                cf, ver, f"Apple Pascal {tag} {e.name}", libs.setdefault(
                    ver, library(ver)))
            stem = e.name.rsplit(".", 1)[0]
            (OUT / f"{stem}-{tag}.pas.txt").write_text(
                text, encoding="ascii", errors="replace")
            tot_c += clean
            tot_n += total
            tot_s += structured
            tot_g += gotos
            print(f"  {tag} {e.name:16s} {clean:3d}/{total:3d} tracked  "
                  f"{structured:3d}/{total:3d} structured  {gotos:3d} gotos")
    print(f"total {tot_c}/{tot_n} lifted with the stack fully tracked; "
          f"{tot_s}/{tot_n} fully structured ({tot_g} gotos left)")
    return 0


ROOT = Path(__file__).resolve().parent.parent

if __name__ == "__main__":
    sys.exit(main())
