"""Launch AppleWin with the acceptance-tier drive layout.

**Default (as of finding: HD acceptance session, 2026-08-26): one 2MB Pascal
hard-disk volume on a slot-5 HDC**, built by `mkharddisks.py`:

    slot 5 HDC h1   SYSHD    boots the machine, carries every system tool
                             Apple shipped -- APPLE/PASCAL (128K), EDITOR,
                             FILER, LIBRARY, MISCINFO, CHARSET, SYNTAX,
                             ASSMBLER, COMPILER, LINKER, LIBRARY.CODE,
                             LIBMAP.CODE, 6502.OPCODES, 6502.ERRORS -- and
                             also the reconstructed source, and where
                             compiler/assembler/linker output lands.
    slots 6, 7      empty

This was two volumes (SYSHD + WORKHD, h1 and h2) briefly; see
mkharddisks.py's docstring for why a single volume needs `[*]` on every
codefile it creates and is not simply "the same thing, one disk instead of
two." `-s5h2` now carries WORKHD (`HD2.hdv`, `mkworkhd.py`) when that image
exists: not for the space, but because a Pascal volume holds 77 files and
SYSHD ran out of directory slots.

Name the volume by its Pascal volume name (`SYSHD:`), not by which .hdv
holds it. `cp2 create-disk-image ... pascal` always names a fresh volume
`NEWDISK`; two same-named volumes online at once left the Filer unable to
tell them apart back when this was still two volumes (`A(ssem` searching
`NEWDISK:` for `SYSTEM.ASSMBLER` silently found the *other*, empty, one
instead) -- not a live concern with a single HD volume, but renamed off
`NEWDISK` regardless since nothing stops a floppy or second hard disk called
`NEWDISK` from also being online. `-model apple2ee` matters too, not just
cosmetically: AppleWin only defaults the HDC to SmartPort firmware for the
*enhanced* //e -- `apple2e` boots the older v2 HDC firmware and never gets
past the `Apple //e` splash. And slot 6 needs `empty` stated explicitly, or
AppleWin's factory-default Disk][ card sits there with no media and the
autostart ROM's boot scan hangs on it before ever reaching slot 5.

**`--floppy` goes back to the older four-floppy layout** (finding 15: the
Apple Pascal compiler wants more than two drives), still available in full:

    S6D1  APPLE1   the boot disk
    S6D2  APPLE2   SYSTEM.COMPILER and SYSTEM.ASSMBLER
    S5D1  WORK     ours -- the reconstructed source, and where output lands
    S5D2  APPLE3   utilities, or WORK2 with --work2 -- a volume for the
                   codefile, which no longer fits beside the source

`--boot128`, `--release` and `--work2` apply only with `--floppy`.

`-conf` points AppleWin at an INI under `build/`, so running this does not
touch whatever configuration is already in the registry.

**This gets the machine booted and no further.** AppleWin's command line has
no switch that injects keystrokes, and `-screenshot-and-exit` is documented
for use with `-load-state`, so it fires before a cold boot has finished and
cannot even confirm one. Driving `X(ecute` is manual. What to type once it is
up (hard-disk layout; swap `SYSHD:` for `WORK:` on `--floppy`, and note the
`[*]` size specifier on the codefile -- mkharddisks.py's docstring explains
why it is not optional here):

    X  *SYSTEM.ASSMBLER     then  SYSHD:SEARCH      -> SYSHD:SEARCH.CODE[*]
    X  *SYSTEM.COMPILER     then  SYSHD:SKEL13      -> SYSHD:SKEL13.CODE[*]

and then bring the disk back here and diff it against the binary.

Usage: python tools/runemu.py [--dry-run]
       python tools/runemu.py --floppy [--release 1.3] [--dry-run]
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
HD1 = ROOT / "build" / "disks" / "HD1.hdv"     # SYSHD: boot, every tool, ours
HD2 = ROOT / "build" / "disks" / "HD2.hdv"     # WORKHD: per-run work, mkworkhd.py

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

# A Super Serial Card in slot 2, in TCP mode -- confirmed working in the
# REMIN:/REMOUT: redirect session (finding 131): `-s2 ssc` inserts the card,
# and this registry value under its own `Slot 2` subkey (not the flat
# Configuration key SETTINGS writes to) tells AppleWin to bind port 1977 as
# a TCP socket instead of a real COM port. The bind is lazy -- it happens on
# first UART access, not at launch -- so nothing is listening until the
# guest program actually touches the card (REDIRIO's own contoremote, or
# anything else that talks to unit 7/8).
SSC_REGKEY = REGKEY + r"\Slot 2"
SSC_SETTINGS = {
    "Serial Port Name": ("REG_SZ", "TCP"),
}
SSC_TCP_PORT = 1977

RELEASES = {
    "1.3": {"d1": "Apple II Pascal 1.3 APPLE1_ 680-0283-A.dsk",
            "d2": "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk",
            "s5d2": "Apple II Pascal 1.3 APPLE3_ 680-0290-A.dsk"},
}


SCRATCH = ROOT / "build" / "disks" / "emu-scratch"


def scratch_copy(path: Path) -> Path:
    """A writable copy of an evidence disk, fresh every launch.

    Read-only stops AppleWin from corrupting `evidence/` (finding 106), but
    it does not stop AppleWin from *needing* to write there: `SYSTEM.ASSMBLER`
    writes a `%LINKER.INFO` scratch file to whatever volume is the Filer's
    P(refix -- APPLE2: for an assemble (finding 44e's recipe) -- and a
    read-only APPLE2: fails that with `I/O Error #16`, not a graceful
    fallback. The fix is not to relax read-only; it is to never hand AppleWin
    the evidence file at all. Every disk this script mounts is a copy under
    `build/`, remade from evidence at the start of every launch, so nothing
    mounted is ever the file `git status` would notice.
    """
    SCRATCH.mkdir(parents=True, exist_ok=True)
    import shutil
    dest = SCRATCH / path.name
    shutil.copyfile(path, dest)
    import os
    import stat
    os.chmod(dest, os.stat(dest).st_mode | stat.S_IWRITE)
    return dest


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


def apply_settings(dry_run: bool = False, ssc: bool = False) -> None:
    """Write the configuration values AppleWin has no switch for."""
    items = list(SETTINGS.items())
    regkeys = [REGKEY] * len(SETTINGS)
    if ssc:
        items += list(SSC_SETTINGS.items())
        regkeys += [SSC_REGKEY] * len(SSC_SETTINGS)
    for regkey, (name, (regtype, value)) in zip(regkeys, items):
        cmd = ["reg", "add", regkey, "/v", name, "/t", regtype,
               "/d", value, "/f"]
        print("  " + " ".join(f'"{c}"' if " " in c else c for c in cmd))
        if dry_run:
            continue
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f"could not set {name!r}: "
                             f"{(r.stdout + r.stderr).strip()}")


def main_hd(dry_run: bool = False, ssc: bool = False) -> int:
    """The hard-disk layout: SYSHD + WORKHD on the slot-5 HDC, nothing else.

    `-model apple2ee` is not cosmetic here -- AppleWin only defaults the HDC
    to SmartPort firmware for the *enhanced* //e. `apple2e` boots the older
    v2 HDC firmware, which never gets past the `Apple //e` splash screen at
    all (findings: HD acceptance session, 2026-08-26). Slot 6 must be
    `empty` explicitly too: AppleWin's factory default puts a Disk][ card
    there with no media, and the autostart ROM's boot scan hangs waiting on
    it (spinning drive light, screen stuck on the splash) before ever
    reaching slot 5.

    `ssc` puts a Super Serial Card in slot 2 instead of leaving it at
    AppleWin's own factory default, in TCP mode on port 1977 (finding 131) --
    what a REMIN:/REMOUT: redirect (`REDIRIO.CODE`) needs a real endpoint
    behind it, rather than the silent, do-nothing I/O failures a redirect
    with nothing in slot 2 produces.
    """
    if not HD1.exists():
        raise SystemExit(f"{HD1.relative_to(ROOT)} has not been built "
                         "(python tools/mkharddisks.py)")

    cmd = [str(EXE),
           "-model", "apple2ee",
           "-s5", "hdc",
           "-s5h1", str(HD1),
           *(["-s5h2", str(HD2)] if HD2.exists() else []),
           "-s6", "empty",
           "-s7", "empty"]
    if ssc:
        cmd += ["-s2", "ssc"]
    cmd += ["-power-on"]

    print("AppleWin settings (registry; no switch exists for these):")
    apply_settings(dry_run, ssc=ssc)
    print()

    print("Slot 5 HDC h1", HD1.name, " <- SYSHD: boot, every system tool, ours")
    if HD2.exists():
        print("Slot 5 HDC h2", HD2.name, " <- WORKHD: per-run work (mkworkhd.py)")
    if ssc:
        print(f"Slot 2 SSC (TCP, port {SSC_TCP_PORT}, binds lazily on first UART access)")
    print("Slots 6, 7    empty")
    print()
    print(" ".join(f'"{c}"' if " " in c else c for c in cmd))
    if dry_run:
        return 0
    subprocess.Popen(cmd, cwd=str(ROOT))
    print("\nlaunched. Nothing here can type into it -- see the module note.")
    return 0


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
    ap.add_argument("--hd", action="store_true",
                    help="boot the hard-disk layout (SYSHD, WORKHD on the "
                         "slot-5 HDC). This is now the default -- the flag "
                         "is accepted for explicitness/scripts written "
                         "against it, but does nothing --floppy doesn't "
                         "already undo.")
    ap.add_argument("--floppy", action="store_true",
                    help="boot the old four-floppy layout (BOOT128, APPLE2, "
                         "WORK, WORK2/APPLE3) instead of the hard-disk one. "
                         "--boot128, --release and --work2 apply only here.")
    ap.add_argument("--ssc", action="store_true",
                    help="put a Super Serial Card in slot 2, TCP mode, port "
                         f"{SSC_TCP_PORT} -- the endpoint a REMIN:/REMOUT: "
                         "redirect needs. --hd only.")
    args = ap.parse_args()

    if not EXE.exists():
        raise SystemExit(f"{EXE} not found")

    if not args.floppy:
        return main_hd(args.dry_run, ssc=args.ssc)

    if not WORK.exists():
        raise SystemExit("build/disks/WORK.dsk has not been built "
                         "(python tools/mkworkdisk.py)")
    r = RELEASES[args.release]
    for key in ("d1", "d2", "s5d2"):
        if not (DISKS / r[key]).exists():
            raise SystemExit(f"missing evidence disk: {r[key]}")
    enforce_readonly(DISKS / r[key] for key in ("d1", "d2", "s5d2"))

    # Every evidence disk AppleWin will touch is mounted as a fresh scratch
    # copy, not the file under evidence/ -- see scratch_copy's note. d1 is
    # skipped when --boot128 substitutes BOOT128.dsk, and s5d2 when --work2
    # substitutes WORK2.dsk: both are already build/ artifacts.
    d1 = ROOT / "build" / "disks" / "BOOT128.dsk" if args.boot128 else \
        scratch_copy(DISKS / r["d1"])
    if args.boot128 and not d1.exists():
        raise SystemExit("BOOT128.dsk has not been built "
                         "(python tools/mkbootdisk.py)")
    d2 = scratch_copy(DISKS / r["d2"])
    s5d2 = WORK2 if args.work2 else scratch_copy(DISKS / r["s5d2"])

    # No `-conf`: it would make AppleWin read an INI instead of the registry,
    # and SETTINGS would have no effect. No `-clock-multiplier` either -- it
    # pins the speed and overrides "Emulation Speed 3".
    cmd = [str(EXE),
           "-model", "apple2e",
           "-d1", str(d1),
           "-d2", str(d2),
           "-s5", "diskii",
           "-s5d1", str(WORK),
           "-s5d2", str(s5d2),
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
