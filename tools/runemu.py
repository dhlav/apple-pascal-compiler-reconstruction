"""Launch AppleWin with the acceptance-tier drive layout.

The Apple Pascal compiler wants more than two drives (finding 15), and the
two acceptance tests need four volumes online at once:

    S6D1  APPLE1   the boot disk
    S6D2  APPLE2   SYSTEM.COMPILER and SYSTEM.ASSMBLER
    S5D1  WORK     ours -- the reconstructed source, and where output lands
    S5D2  APPLE3   utilities

`-conf` points AppleWin at an INI under `build/`, so running this does not
touch whatever configuration is already in the registry.

**This gets the machine booted and no further.** AppleWin's command line has
no switch that injects keystrokes, and `-screenshot-and-exit` is documented
for use with `-load-state`, so it fires before a cold boot has finished and
cannot even confirm one. Driving `X(ecute` is manual. What to type once it is
up:

    X  *SYSTEM.ASSMBLER     then  WORK:SEARCH      -> WORK:SEARCH.CODE
    X  *SYSTEM.COMPILER     then  WORK:SKEL13      -> WORK:SKEL13.CODE

and then bring the disk back here and diff it against the binary.

Usage: python tools/runemu.py [--release 1.3] [--dry-run]
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXE = Path(r"C:\AppleWin\AppleWin.exe")
DISKS = ROOT / "evidence" / "disks"
WORK = ROOT / "build" / "disks" / "WORK.dsk"

RELEASES = {
    "1.3": {"d1": "Apple II Pascal 1.3 APPLE1_ 680-0283-A.dsk",
            "d2": "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk",
            "s5d2": "Apple II Pascal 1.3 APPLE3_ 680-0290-A.dsk"},
    # 1.1's APPLE1 is not in evidence/; only its APPLE2 is, so 1.1 boots off
    # the UCSD disk that carries the GOTOXY pair.
    "1.1": {"d1": "UCSD Pascal 1.1_1.dsk",
            "d2": "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk",
            "s5d2": "UCSD Pascal 1.1_3.dsk"},
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", default="1.3", choices=sorted(RELEASES))
    ap.add_argument("--dry-run", action="store_true",
                    help="print the command line and stop")
    ap.add_argument("--boot128", action="store_true",
                    help="boot build/disks/BOOT128.dsk instead of APPLE1 -- "
                         "the same disk with Apple's 128K system substituted "
                         "in (mkbootdisk.py). The 64K system cannot compile "
                         "even its own sample programs.")
    args = ap.parse_args()

    if not EXE.exists():
        raise SystemExit(f"{EXE} not found")
    if not WORK.exists():
        raise SystemExit("build/disks/WORK.dsk has not been built "
                         "(python tools/mkworkdisk.py)")
    r = RELEASES[args.release]
    for key in ("d1", "d2", "s5d2"):
        if not (DISKS / r[key]).exists():
            raise SystemExit(f"missing evidence disk: {r[key]}")

    d1 = DISKS / r["d1"]
    if args.boot128:
        d1 = ROOT / "build" / "disks" / "BOOT128.dsk"
        if not d1.exists():
            raise SystemExit("BOOT128.dsk has not been built "
                             "(python tools/mkbootdisk.py)")

    conf = ROOT / "build" / f"applewin-{args.release}.ini"
    conf.parent.mkdir(parents=True, exist_ok=True)
    cmd = [str(EXE),
           "-model", "apple2e",
           "-conf", str(conf),          # keep out of the user's registry
           "-d1", str(d1),
           "-d2", str(DISKS / r["d2"]),
           "-s5", "diskii",
           "-s5d1", str(WORK),
           "-s5d2", str(DISKS / r["s5d2"]),
           "-clock-multiplier", "3.9",
           "-power-on"]

    print("S6D1", d1.name)
    print("S6D2", r["d2"])
    print("S5D1", WORK.name, "  <- ours: SEARCH.TEXT, SKEL13.TEXT, SKEL11.TEXT")
    print("S5D2", r["s5d2"])
    print()
    print(" ".join(f'"{c}"' if " " in c else c for c in cmd))
    if args.dry_run:
        return 0
    subprocess.Popen(cmd, cwd=str(ROOT))
    print("\nlaunched. Nothing here can type into it -- see the module note.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
