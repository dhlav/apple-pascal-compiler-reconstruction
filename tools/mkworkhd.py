"""Build WORKHD, the second hard-disk volume, on the slot-5 HDC's drive 2.

    python tools/mkworkhd.py            # create build/disks/HD2.hdv if absent
    python tools/mkworkhd.py --reset    # wipe it and start empty

SYSHD (`HD1.hdv`, `mkharddisks.py`) carries every system tool, the
reconstruction's standing sources and `REDIRIO.CODE`, and a Pascal volume
holds at most 77 files however large it is. Every acceptance run adds a
source, a codefile and often a data file on top, so SYSHD filled twice in
one session (findings 276, 278). WORKHD is where that per-run work goes
instead: stage with `stagefile.py --vol WORKHD`, drive with
`emuremote.py --vol WORKHD`. The system tools still come from SYSHD, the
boot volume, and REDIRIO is still installed there.

This is a separate script, not a step of `mkharddisks.py`, on purpose:
rebuilding SYSHD is what forces the REDIRIO bootstrap, and emptying the work
volume should never cost that. Nor is it a `build_all.py` step -- the volume
holds emulator output that has not always been kept yet.

It is a distinct volume name for the reason `mkharddisks.py` gives: two
volumes both called `NEWDISK` online at once left the Filer unable to tell
them apart. The one-volume `[*]` race (same docstring) does not arise
between the two, but `emuremote.py` keeps the `[*]` anyway.
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CP2 = Path(r"C:\CiderPress2\cp2.exe")
HD2 = ROOT / "build" / "disks" / "HD2.hdv"
NAME = "WORKHD"


def cp2(*args: str) -> str:
    r = subprocess.run([str(CP2), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode:
        raise SystemExit(f"cp2 {' '.join(args)} failed:\n{r.stdout}{r.stderr}")
    return r.stdout


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--reset", action="store_true",
                    help="delete the existing volume and create it empty")
    args = ap.parse_args()
    if not CP2.exists():
        raise SystemExit(f"{CP2} not found -- CiderPress II is required")
    if HD2.exists() and not args.reset:
        print(f"{HD2.relative_to(ROOT)} already exists; --reset to empty it")
        print(cp2("catalog", str(HD2)), end="")
        return 0
    HD2.parent.mkdir(parents=True, exist_ok=True)
    HD2.unlink(missing_ok=True)
    cp2("create-disk-image", str(HD2), "2M", "pascal")
    cp2("move", str(HD2), ":", NAME)
    out = cp2("catalog", str(HD2))
    if f'"{NAME}"' not in out:
        raise SystemExit(f"{HD2.name} did not come up named {NAME}:\n{out}")
    print(out, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
