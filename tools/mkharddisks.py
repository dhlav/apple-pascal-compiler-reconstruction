"""Build the two hard-disk images the HD acceptance tier mounts.

The floppy tier's four volumes (BOOT128, APPLE2, WORK, WORK2) fold onto two
2MB Pascal hard-disk volumes here, both living on the Hard Disk Controller
card in slot 5 (`-s5 hdc`):

  SYSHD   (`build/disks/HD1.hdv`)  boots the machine and carries every system
          tool Apple shipped -- SYSTEM.APPLE/PASCAL (128K), EDITOR, FILER,
          LIBRARY, MISCINFO, CHARSET, SYNTAX, ASSMBLER, COMPILER, LINKER,
          LIBRARY.CODE, LIBMAP.CODE, 6502.OPCODES, 6502.ERRORS. Stable --
          rebuilding it is cheap, but nothing here changes between runs.
  WORKHD  (`build/disks/HD2.hdv`)  ours: the same reconstructed source
          mkworkdisk.py puts on WORK.dsk, and where compiler/assembler/linker
          output lands.

Two things a 5.25" floppy volume never has to worry about, and a hard disk
always does:

  * **a2pascal/disk.py and diskwrite.py do not reach this size.** They assume
    the 35-track/16-sector DOS-order geometry of a 143,360-byte volume; a 2MB
    hard-disk image is a flat run of 512-byte blocks with no track/sector
    skew at all, a different (simpler) format this repo has no reader for.
    So this shells out to CiderPress II's `cp2.exe`, which understands the
    Pascal directory format at any size, instead.
  * **volume names must be distinct.** `cp2 create-disk-image ... pascal`
    always names a fresh volume `NEWDISK`; two same-named volumes online at
    once left the Filer unable to tell them apart -- `A(ssem` searched
    `NEWDISK:` for `SYSTEM.ASSMBLER` and silently found the *other* one,
    empty, volume (finding: HD acceptance session, 2026-08-26). Renamed here
    before anything is copied on.

Requires `C:\\CiderPress2\\cp2.exe` (CiderPress II) and boots via SmartPort
firmware, which AppleWin only defaults to for `-model apple2ee` (the
*enhanced* //e) -- `apple2e` still uses the older v2 HDC firmware and never
gets past the `Apple //e` splash. See `runemu.py --hd`.

Writes build/disks/HD1.hdv and build/disks/HD2.hdv.
"""
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a2pascal.srcfmt import WIDTH, expand_tabs, over_width
from a2pascal.textfile import encode_text

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "disks"
CP2 = Path(r"C:\CiderPress2\cp2.exe")
BOOT128 = OUT / "BOOT128.dsk"
APPLE2 = ROOT / "evidence" / "disks" / "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk"

HD1 = OUT / "HD1.hdv"
HD2 = OUT / "HD2.hdv"

# Same list mkworkdisk.py puts on WORK.dsk -- see that module for why each
# one is here and why the names are what they are.
FILES = [
    ("SEARCH.TEXT", ROOT / "src" / "native" / "SEARCH.TEXT"),
    ("SKEL13.TEXT", ROOT / "analysis" / "reconstruction" / "skeleton-1.3.text"),
    ("SKEL11.TEXT", ROOT / "analysis" / "reconstruction" / "skeleton-1.1.text"),
    ("LINEFEED.TEXT", ROOT / "src" / "pascal" / "programs" / "1.3" /
     "LINEFEED.text"),
    ("FORMATTR.TEXT", ROOT / "src" / "pascal" / "programs" / "1.3" /
     "FORMATTER.text"),
    ("FMTNATIV.TEXT", ROOT / "src" / "native" / "FORMATTR.TEXT"),
]


def cp2(*args: str) -> str:
    r = subprocess.run([str(CP2), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode:
        raise SystemExit(f"cp2 {' '.join(args)} failed:\n{r.stdout}{r.stderr}")
    return r.stdout


def main() -> int:
    if not CP2.exists():
        raise SystemExit(f"{CP2} not found -- CiderPress II is required "
                         "for hard-disk images (a2pascal only reads/writes "
                         "5.25\" floppy geometry)")
    if not BOOT128.exists():
        raise SystemExit("build/disks/BOOT128.dsk has not been built "
                         "(python tools/mkbootdisk.py)")
    OUT.mkdir(parents=True, exist_ok=True)

    # -- SYSHD: boot + every system tool, rebuilt fresh every run ----------
    HD1.unlink(missing_ok=True)
    cp2("create-disk-image", str(HD1), "2M", "pascal")
    cp2("move", str(HD1), ":", "SYSHD")
    cp2("copy", str(BOOT128), str(HD1))
    cp2("copy", str(APPLE2), str(HD1))

    # -- WORKHD: ours, rebuilt fresh every run ------------------------------
    HD2.unlink(missing_ok=True)
    cp2("create-disk-image", str(HD2), "2M", "pascal")
    cp2("move", str(HD2), ":", "WORKHD")

    scratch = OUT / "hd-scratch"
    scratch.mkdir(exist_ok=True)
    for name, path in FILES:
        if not path.exists():
            raise SystemExit(f"{path} has not been generated")
        text = expand_tabs(path.read_text(encoding="ascii", errors="replace"))
        text = text[:-1] if text.endswith("\n") else text
        long = over_width(text.split("\n"))
        if long:
            raise SystemExit(
                f"{name}: {len(long)} lines exceed {WIDTH} columns "
                f"{long[:5]} -- fix the generator, not the disk")
        tmp = scratch / name
        tmp.write_bytes(encode_text(text))
        cp2("add", "--raw", "--no-strip-ext", "--strip-paths", str(HD2),
            str(tmp))
        cp2("set-attr", str(HD2), name, "type=PTX")
    shutil.rmtree(scratch)

    for img, label in ((HD1, "SYSHD"), (HD2, "WORKHD")):
        out = cp2("catalog", str(img))
        if f'"{label}"' not in out:
            raise SystemExit(f"{img.name} did not come up named {label}:\n{out}")
        print(out, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
