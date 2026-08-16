"""Build a 128K Apple Pascal 1.3 boot disk.

The acceptance run hit a wall the 64K system cannot get past. Booting
`APPLE1` announces *"Pascal system size is 64K"*, and on that system the
compiler dies with a runtime **stack overflow** -- not on the reconstruction,
which would be a result, but on `HILBERT.TEXT`, one of Apple's own shipped
samples. A compiler that cannot compile the sample programs on the disk next
to it is not the configuration Apple used.

Apple shipped the answer on `APPLE3`: `128K.APPLE` and `128K.PASCAL`, the
interpreter and operating system for a 128K machine. The manual's procedure
is to transfer them onto the boot disk under the names `SYSTEM.APPLE` and
`SYSTEM.PASCAL`. `evidence/` is never modified, so this builds a *new* disk
that is `APPLE1` with those two files substituted.

Nothing is edited by hand: the writer removes the two 64K files and places
the two 128K ones, which is the first real use of the volume writer for
something other than a work disk. The 45-block `SYSTEM.PASCAL` does not fit
in the 44-block hole its predecessor left, so it lands in the free run at
the end of the volume. That is fine -- UCSD files are found through the
directory, not by position -- and it is exactly the kind of thing this
would get wrong silently if the writer's free-space accounting were off.

Writes build/disks/BOOT128.dsk.
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a2pascal.disk import PascalDisk, format_date
from a2pascal.diskwrite import PascalWriter

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "disks"
BASE = ROOT / "evidence" / "disks" / "Apple II Pascal 1.3 APPLE1_ 680-0283-A.dsk"
SRC = ROOT / "evidence" / "disks" / "Apple II Pascal 1.3 APPLE3_ 680-0290-A.dsk"

# name on the new disk <- name on APPLE3
SUBSTITUTE = {"SYSTEM.APPLE": "128K.APPLE", "SYSTEM.PASCAL": "128K.PASCAL"}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    dst = OUT / "BOOT128.dsk"
    shutil.copyfile(BASE, dst)

    src = PascalDisk.from_file(SRC)
    w = PascalWriter.from_file(dst)

    # Remove both first: freeing the old system's blocks is what makes room.
    for name in SUBSTITUTE:
        w.remove_file(name)
    for name, srcname in SUBSTITUTE.items():
        e = src.find(srcname)
        payload = src.read_blocks(e.first_block, e.blocks)[:e.size]
        w.add_file(name, payload, e.kind, mtime_raw=e.mtime_raw)

    w.save(dst)

    # The substituted files have to read back byte for byte, and the volume
    # has to still hold everything else it started with.
    out = PascalDisk.from_file(dst)
    before = {e.name: e for e in PascalDisk.from_file(BASE).directory()}
    after = {e.name: e for e in out.directory()}
    if set(before) != set(after):
        raise SystemExit(f"file set changed: "
                         f"{set(before) ^ set(after)}")
    for name, srcname in SUBSTITUTE.items():
        e = src.find(srcname)
        if out.read_file(name) != src.read_blocks(e.first_block, e.blocks)[:e.size]:
            raise SystemExit(f"{name} does not read back as {srcname}")
    for name in before:
        if name in SUBSTITUTE:
            continue
        if out.read_file(name) != PascalDisk.from_file(BASE).read_file(name):
            raise SystemExit(f"{name} changed, and nothing asked it to")

    vol = out.volume()
    print(f"wrote {dst.relative_to(ROOT)}: {vol.name}: {vol.num_files} files, "
          f"{PascalWriter.from_file(dst).free_blocks()} blocks free")
    for e in out.directory():
        mark = "  <- 128K" if e.name in SUBSTITUTE else ""
        print(f"  {e.name:<18}{e.blocks:>4} blk  {e.first_block:>3}.."
              f"{e.next_block:<3} {format_date(e.mtime_raw)}{mark}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
