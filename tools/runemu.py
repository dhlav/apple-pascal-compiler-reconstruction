"""Launch AppleWin with the acceptance-tier drive layout.

The Apple Pascal compiler wants more than two drives (finding 15), and the
two acceptance tests need four volumes online at once:

    S6D1  APPLE1   the boot disk
    S6D2  APPLE2   SYSTEM.COMPILER and SYSTEM.ASSMBLER
    S5D1  WORK     ours -- the reconstructed source, and where output lands
    S5D2  APPLE3   utilities, or WORK2 with --work2 -- a volume for the
                   codefile, which no longer fits beside the source

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
WORK2 = ROOT / "build" / "disks" / "WORK2.dsk"

# Applied before every launch. AppleWin reads these from the registry at
# startup and there is no command-line switch for any of them.
#
#   Emulation Speed  maximum. A compile that took 45 wall-clock seconds at
#                    3.9MHz takes a few. `-clock-multiplier` must NOT be
#                    passed as well -- it pins the speed and overrides this.
#   Video Mode       monochrome. Not cosmetic: the screen is read back from a
#                    screenshot, and colour-TV artefacts blur 40-column text
#                    into something barely legible.
#
# These go in the real registry, so `-conf` must not be passed either -- it
# tells AppleWin to use an INI file instead and all of this is ignored.
#
# **The values and the types are version-specific.** These are AppleWin
# 1.32's, read back from a UI that had been set by hand. Two traps, both hit:
# `Video Mode` 5 is monochrome in 1.30 but *Color (RGB Card/Monitor)* in
# 1.32, where monochrome is 9; and `Emulation Speed` is a **REG_SZ** here,
# not a REG_DWORD, so writing it as a DWORD replaces the value with one
# AppleWin does not read. Check both against the running build before
# trusting them -- `AppleWin.exe -model apple2e -power-on` names the video
# mode in its title bar.
REGKEY = r"HKEY_CURRENT_USER\Software\AppleWin\CurrentVersion\Configuration"
SETTINGS = {
    "Emulation Speed":  ("REG_SZ", "40"),          # maximum
    "Video Mode":       ("REG_DWORD", "9"),        # monochrome
    "Monochrome Color": ("REG_SZ", "12632256"),    # 0xC0C0C0
}

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


def enforce_readonly(paths) -> None:
    """AppleWin opens `-d1`/`-d2` for read-write and will write to them --
    a boot alone updates the volume's date stamp. That happened for real:
    `evidence/disks/Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk` came back
    from a `--boot128` run with a changed hash and no error from AppleWin at
    all (finding 105's session). The read-only bit is what stops it --
    AppleWin still mounts and boots a read-only image fine, it just cannot
    write -- so every evidence disk this script is about to hand AppleWin
    gets the bit set first, every launch, rather than trusting it was set
    by hand and stays that way.
    """
    import os
    import stat
    for p in paths:
        if p.exists() and (os.stat(p).st_mode & stat.S_IWRITE):
            os.chmod(p, os.stat(p).st_mode & ~stat.S_IWRITE)


def apply_settings(dry_run: bool = False) -> None:
    """Write the two configuration values AppleWin has no switch for."""
    for name, (regtype, value) in SETTINGS.items():
        cmd = ["reg", "add", REGKEY, "/v", name, "/t", regtype,
               "/d", value, "/f"]
        print("  " + " ".join(f'"{c}"' if " " in c else c for c in cmd))
        if dry_run:
            continue
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f"could not set {name!r}: "
                             f"{(r.stdout + r.stderr).strip()}")


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
    ap.add_argument("--work2", action="store_true",
                    help="mount build/disks/WORK2.dsk at S5D2 instead of "
                         "APPLE3, so the codefile has a volume of its own")
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
    enforce_readonly(DISKS / r[key] for key in ("d1", "d2", "s5d2"))

    d1 = DISKS / r["d1"]
    if args.boot128:
        d1 = ROOT / "build" / "disks" / "BOOT128.dsk"
        if not d1.exists():
            raise SystemExit("BOOT128.dsk has not been built "
                             "(python tools/mkbootdisk.py)")

    # No `-conf`: it would make AppleWin read an INI instead of the registry,
    # and SETTINGS would have no effect. No `-clock-multiplier` either -- it
    # pins the speed and overrides "Emulation Speed 3".
    cmd = [str(EXE),
           "-model", "apple2e",
           "-d1", str(d1),
           "-d2", str(DISKS / r["d2"]),
           "-s5", "diskii",
           "-s5d1", str(WORK),
           "-s5d2", str(WORK2 if args.work2 else DISKS / r["s5d2"]),
           "-power-on"]

    print("AppleWin settings (registry; no switch exists for these):")
    apply_settings(args.dry_run)
    print()

    print("S6D1", d1.name)
    print("S6D2", r["d2"])
    print("S5D1", WORK.name, "  <- ours: SEARCH.TEXT, SKEL13.TEXT, SKEL11.TEXT")
    print("S5D2", WORK2.name if args.work2 else r["s5d2"])
    print()
    print(" ".join(f'"{c}"' if " " in c else c for c in cmd))
    if args.dry_run:
        return 0
    subprocess.Popen(cmd, cwd=str(ROOT))
    print("\nlaunched. Nothing here can type into it -- see the module note.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
