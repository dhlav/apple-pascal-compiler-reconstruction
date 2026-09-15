"""Two 8MB AppleWin hard-disk images: Apple's system, and this repo's source.

    python tools/mkimages.py          # writes build/images/SYSHD.hdv, SRCHD.hdv

**SYSHD** is a turnkey Apple Pascal 1.3 system for a 128K machine, made
only of files Apple shipped, byte for byte:

  * every file on APPLE1, APPLE2 and APPLE3;
  * except the 64K SYSTEM.APPLE and SYSTEM.PASCAL, which are replaced by
    128K.APPLE and 128K.PASCAL copied to those names -- the manual's own
    procedure for a 128K system (tools/mkbootdisk.py);
  * 128K.APPLE and 128K.PASCAL are also kept under their own names.

**SRCHD** holds the Pascal and 6502 assembly source this reconstruction
wrote and used, as Pascal text files, plus the data files and SETUP recipes
those programs read. No Python. Names are cut to fit a Pascal volume's 15
characters, and a source that is compiled keeps its name to nine before
.TEXT: Apple's compiler reports "String overflow" for a 15-character
codefile name such as TURTLEUNIT.CODE, while SET40COLS.CODE compiles. The
units carry the names they were staged under for the acceptance runs
(UTRANS, UCHAIN, UPASIO, ULONG, UTURTLE, UAPPLE). README.TEXT on the volume
maps each file to what it builds.
Unit sources and the ten text files are encoded with their .layout (the
editor's DLE codes, page breaks and page zero), exactly as they were staged
for Apple's tools; the compiler is here both as its parts (PASCALCO and its
phases) and as BODY13.TEXT, procbuild.py's splice of them.

Both are single Pascal volumes on an 8MB image, so each holds at most 77
files; this checks both counts. Boot SYSHD on AppleWin's enhanced //e
(`-model apple2ee`) with a hard disk controller in slot 5 and slot 6 empty
(tools/runemu.py explains both). Requires CiderPress II's cp2.exe.

These are separate from build/disks/HD1.hdv and HD2.hdv, the acceptance
tier's working volumes, which carry REDIRIO and per-run files.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from a2pascal.disk import PascalDisk
from a2pascal.srcfmt import WIDTH, expand_tabs, over_width
from a2pascal.textfile import Layout, encode_text

CP2 = Path(r"C:\CiderPress2\cp2.exe")
OUT = ROOT / "build" / "images"
SIZE = "8M"
MAX_FILES = 77
EVIDENCE = ROOT / "evidence" / "disks"
DISKS = {"APPLE1": EVIDENCE / "Apple II Pascal 1.3 APPLE1_ 680-0283-A.dsk",
         "APPLE2": EVIDENCE / "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk",
         "APPLE3": EVIDENCE / "Apple II Pascal 1.3 APPLE3_ 680-0290-A.dsk"}
SYSTEM_64K = {"SYSTEM.APPLE", "SYSTEM.PASCAL"}
AS_SYSTEM = {"SYSTEM.APPLE": "128K.APPLE", "SYSTEM.PASCAL": "128K.PASCAL"}

PR = ROOT / "src" / "pascal" / "programs" / "1.3"
UN = ROOT / "src" / "pascal" / "units" / "1.3"
OS = ROOT / "src" / "pascal" / "os" / "1.3"
CO = ROOT / "src" / "pascal" / "1.3"
NA = ROOT / "src" / "native"
DA = ROOT / "src" / "data"
TX = ROOT / "src" / "text"
PHASES = ["COMPINIT", "COMPOPTI", "DECLARAT", "BODYPART", "ROUTINE",
          "STATEMEN", "CASESTAT", "FORSTATE", "NUMSTRIN", "BODY1", "BODY3",
          "UNITPART", "FINISHUP", "WRITELIN"]

# name on SRCHD, repository path (None: generated here), what it builds
SOURCES = [
    ("BODY13.TEXT", None, "SYSTEM.COMPILER: PASCALCO and the 14 phases, spliced as compiled"),
    ("PASCALCO.TEXT", CO / "PASCALCO.text", "SYSTEM.COMPILER: declarations and outer block"),
    *[(f"{p}.TEXT", CO / "phases" / f"{p}.text", f"SYSTEM.COMPILER: phase {p}")
      for p in PHASES],
    ("SEARCH.TEXT", NA / "SEARCH.TEXT", "IDSEARCH/TREESEARCH (6502): SYSTEM.COMPILER, LIBMAP.CODE"),
    ("ASSMBLER.TEXT", PR / "ASSMBLER.text", "SYSTEM.ASSMBLER"),
    ("LINKER.TEXT", PR / "LINKER.text", "SYSTEM.LINKER"),
    ("EDITOR.TEXT", PR / "EDITOR.text", "SYSTEM.EDITOR"),
    ("FILER.TEXT", PR / "FILER.text", "SYSTEM.FILER"),
    ("LIBRARY.TEXT", PR / "LIBRARY.text", "LIBRARY.CODE"),
    ("LIBMAP.TEXT", PR / "LIBMAP.text", "LIBMAP.CODE (links SEARCH)"),
    ("SETUP.TEXT", PR / "SETUP.text", "SETUP.CODE"),
    ("BINDER.TEXT", PR / "BINDER.text", "BINDER.CODE"),
    ("SET40COLS.TEXT", PR / "SET40COLS.text", "SET40COLS.CODE"),
    ("LINEFEED.TEXT", PR / "LINEFEED.text", "LINEFEED.CODE"),
    ("FORMATTER.TEXT", PR / "FORMATTER.text", "FORMATTER.CODE (links FORMATTR)"),
    ("FORMATTR.TEXT", NA / "FORMATTR.TEXT", "FORMATDISK (6502): FORMATTER.CODE"),
    ("ASMFORMAT.TEXT", NA / "ASMFORMAT.TEXT", "Disk II formatter (6502): FORMATTER.DATA"),
    ("BOOTII.TEXT", NA / "BOOTII.TEXT", "Disk II boot (6502): FORMATTER.DATA"),
    ("BOOTPD.TEXT", NA / "BOOTPD.TEXT", "ProDOS boot (6502): FORMATTER.DATA"),
    ("MAKEBOOT.TEXT", PR / "MAKEBOOT.text", "BOOTTRACKS.DATA, for FORMATTER.DATA"),
    ("MAKEFMT.TEXT", PR / "MAKEFMT.text", "FORMATTER.DATA"),
    ("PASCALSY.TEXT", OS / "PASCALSYSTEM.text", "128K.PASCAL (with MAKEOS)"),
    ("USESFIO.TEXT", OS / "USESFIO.text", "include file for PASCALSY"),
    ("MAKEOS.TEXT", PR / "MAKEOS.text", "128K.PASCAL, finished from PASCALSY.CODE"),
    ("INTERP.TEXT", NA / "interp" / "INTERP.TEXT", "128K.APPLE, bank 2 (6502, .ABSOLUTE)"),
    ("TOP.TEXT", NA / "interp" / "TOP.TEXT", "128K.APPLE, top pages (6502, .ABSOLUTE)"),
    ("BANK1.TEXT", NA / "interp" / "BANK1.TEXT", "128K.APPLE, bank 1 (6502, .ABSOLUTE)"),
    ("MAKEINTP.TEXT", PR / "MAKEINTP.text", "128K.APPLE, joined from the three"),
    ("ULONG.TEXT", UN / "LONGINTIO.text", "SYSTEM.LIBRARY unit LONGINTIO"),
    ("LONGINTS.TEXT", NA / "LONGINTS.TEXT", "DECOPS (6502): LONGINTIO"),
    ("UPASIO.TEXT", UN / "PASCALIO.text", "SYSTEM.LIBRARY unit PASCALIO"),
    ("UCHAIN.TEXT", UN / "CHAINSTUFF.text", "SYSTEM.LIBRARY unit CHAINSTUFF"),
    ("UTRANS.TEXT", UN / "TRANSCEND.text", "SYSTEM.LIBRARY unit TRANSCEND"),
    ("UTURTLE.TEXT", UN / "TURTLEGRAPHICS.text", "SYSTEM.LIBRARY unit TURTLEGRAPHICS"),
    ("TURTLEGR.TEXT", NA / "TURTLEGR.TEXT", "TURTLEGRAPHICS native procedures (6502)"),
    ("UAPPLE.TEXT", UN / "APPLESTUFF.text", "SYSTEM.LIBRARY unit APPLESTUFF"),
    ("APPLESTF.TEXT", NA / "APPLESTF.TEXT", "APPLESTUFF native procedures (6502)"),
    ("CHARSET.TEXT", DA / "CHARSET.TEXT", "data read by MAKECHRS"),
    ("MAKECHRS.TEXT", PR / "MAKECHRS.text", "SYSTEM.CHARSET"),
    ("OPS6502.TEXT", DA / "OPS6502.TEXT", "data read by MAKEOPS"),
    ("MAKEOPS.TEXT", PR / "MAKEOPS.text", "6502.OPCODES"),
    ("ERRS6502.TEXT", DA / "ERRS6502.TEXT", "data read by MAKEERRS"),
    ("MAKEERRS.TEXT", PR / "MAKEERRS.text", "6502.ERRORS"),
    ("SYSMISC.TEXT", DA / "miscinfo" / "SYSTEM.recipe", "SETUP settings for SYSTEM.MISCINFO"),
    ("II40MISC.TEXT", DA / "miscinfo" / "II40.recipe", "SETUP settings for II40.MISCINFO"),
    ("II80MISC.TEXT", DA / "miscinfo" / "II80.recipe", "SETUP settings for II80.MISCINFO"),
    ("HAZELMIS.TEXT", DA / "miscinfo" / "HAZEL.recipe", "SETUP settings for HAZEL.MISCINFO"),
    *[(n, TX / f"{n[:-5] if n.endswith('.TEXT') else n}.text",
       f"{n} itself (with its layout)")
      for n in ("SYSTEM.SYNTAX", "BALANCED.TEXT", "CROSSREF.TEXT", "DISKIO.TEXT",
                "GRAFCHARS.TEXT", "GRAFDEMO.TEXT", "HAZELGOTO.TEXT",
                "HILBERT.TEXT", "SPIRODEMO.TEXT", "TREE.TEXT")],
    ("REDIRIO.TEXT", ROOT / "tools" / "remote" / "REDIRIO.text", "remote console used to drive Apple's tools (not on Apple's disks)"),
    ("REMTEST.TEXT", ROOT / "tools" / "remote" / "REMTEST.text", "remote console transport test (not on Apple's disks)"),
]


def cp2(*args: str, cwd: Path | None = None) -> str:
    r = subprocess.run([str(CP2), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace",
                       cwd=None if cwd is None else str(cwd))
    if r.returncode:
        raise SystemExit(f"cp2 {' '.join(args)} failed:\n{r.stdout}{r.stderr}")
    return r.stdout


def catalog_names(image: Path) -> list[str]:
    out = cp2("catalog", str(image))
    names = []
    for line in out.splitlines()[2:]:
        parts = line.split()
        if len(parts) >= 6 and parts[0] in ("PTX", "PCD", "PDA", "PTX+", "PSD", "PBD", "PFT", "PIF", "PBA", "PSC", "PGR"):
            names.append(parts[-1])
    return names


def new_volume(path: Path, name: str) -> None:
    path.unlink(missing_ok=True)
    cp2("create-disk-image", str(path), SIZE, "pascal")
    cp2("move", str(path), ":", name)


def build_syshd(scratch: Path) -> Path:
    img = OUT / "SYSHD.hdv"
    new_volume(img, "SYSHD")
    expected = {}
    for vol, dsk in DISKS.items():
        d = PascalDisk.from_file(dsk)
        names = [e.name for e in d.directory()
                 if e.name not in SYSTEM_64K and e.name not in expected]
        for n in names:
            expected[n] = (vol, n)
        if names:
            cp2("copy", str(dsk), *names, str(img))
    # The 128K pair under the names the boot looks for: extracted from
    # APPLE3 and added back renamed, with the codefile/datafile types cp2
    # copies from the originals.
    a3 = DISKS["APPLE3"]
    kinds = {e.name: e.kind for e in PascalDisk.from_file(a3).directory()}
    for sysname, name in AS_SYSTEM.items():
        work = scratch / "sys"
        shutil.rmtree(work, ignore_errors=True)
        work.mkdir(parents=True)
        cp2("extract", "--raw", "--strip-paths", str(a3), name, cwd=work)
        (work / name).rename(work / sysname)
        cp2("add", "--raw", "--no-strip-ext", "--strip-paths", str(img),
            str(work / sysname))
        cp2("set-attr", str(img),
            "type=" + ("PCD" if kinds[name] == "codefile" else "PDA"), sysname)
        expected[sysname] = ("APPLE3", name)

    # Every file reads back as Apple's bytes.
    got = scratch / "check"
    shutil.rmtree(got, ignore_errors=True)
    got.mkdir()
    names = catalog_names(img)
    if sorted(names) != sorted(expected):
        raise SystemExit(f"SYSHD holds {sorted(set(names) ^ set(expected))} "
                         "unexpectedly")
    cp2("extract", "--raw", "--strip-paths", str(img), *names, cwd=got)
    for n, (vol, src) in expected.items():
        want = PascalDisk.from_file(DISKS[vol]).read_file(src)
        have = (got / n).read_bytes()
        if have[:len(want)] != want or len(have) - len(want) >= 512:
            raise SystemExit(f"SYSHD:{n} is not {vol}:{src} byte for byte")
    return img


def encode(name: str, path: Path | None) -> bytes:
    if path is None:
        sys.path.insert(0, str(ROOT / "tools"))
        import procbuild
        procbuild.USE_NS = True      # as write_for_emulator compiles it
        text = procbuild.spliced("1.3", procbuild.sources("1.3"))
        layout = None
    else:
        text = path.read_text(encoding="ascii", errors="replace")
        layout = Layout.beside(path)
    text = expand_tabs(text)
    text = text[:-1] if text.endswith("\n") else text
    if path is not None and path.suffix.upper() == ".TEXT" and \
            path.parent.name in ("native", "interp"):
        long = over_width(text.split("\n"))
        if long:
            raise SystemExit(f"{name}: {len(long)} lines over {WIDTH} columns")
    return encode_text(text, layout=layout)


def build_srchd(scratch: Path) -> Path:
    img = OUT / "SRCHD.hdv"
    new_volume(img, "SRCHD")
    names = [n for n, _p, _w in SOURCES] + ["README.TEXT"]
    # 15 characters is the volume's limit; a compiled source's codefile name
    # has to stay under it, so a .TEXT stem is held to nine.
    long = [n for n in names if len(n) > 15
            or (n.endswith(".TEXT") and len(n) - 5 > 9)]
    dup = {n for n in names if names.count(n) > 1}
    if long or dup:
        raise SystemExit(f"bad names: too long {long}, duplicated {sorted(dup)}")
    work = scratch / "src"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)

    readme = ["SRCHD: the source of the Apple Pascal 1.3 reconstruction",
              "",
              "Pascal and 6502 assembly (Apple Assembler) written and used",
              "to rebuild the 1.3 disk set with Apple's own tools, plus the",
              "data files and SETUP settings those programs read. Names are",
              "cut to 15 characters. Unit sources and the text files carry",
              "the line encoding Apple's editor used (their .layout files).",
              "Sources that open other files name the volume they were run",
              "from (SYSHD: or WORKHD:); change it to SRCHD: to run them",
              "here. The repository keeps the originals under src/ and",
              "the account of every byte in docs/.",
              "",
              "FILE             BUILDS / USED FOR"]
    for n, path, what in SOURCES:
        if path is not None and not path.exists():
            raise SystemExit(f"{path} does not exist")
        (work / n).write_bytes(encode(n, path))
        readme.append(f"{n:<16} {what}")
    (work / "README.TEXT").write_bytes(encode_text("\n".join(readme)))

    for n in names:
        cp2("add", "--raw", "--no-strip-ext", "--strip-paths", str(img),
            str(work / n))
        cp2("set-attr", str(img), "type=PTX", n)

    got = scratch / "srccheck"
    shutil.rmtree(got, ignore_errors=True)
    got.mkdir()
    listed = catalog_names(img)
    if sorted(listed) != sorted(names):
        raise SystemExit(f"SRCHD catalog differs: {sorted(set(listed) ^ set(names))}")
    cp2("extract", "--raw", "--strip-paths", str(img), *names, cwd=got)
    for n in names:
        want = (work / n).read_bytes()
        have = (got / n).read_bytes()
        if have[:len(want)] != want:
            raise SystemExit(f"SRCHD:{n} does not read back as written")
    return img


def main() -> int:
    if not CP2.exists():
        raise SystemExit(f"{CP2} not found (CiderPress II is required)")
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp)
        for img in (build_syshd(scratch), build_srchd(scratch)):
            names = catalog_names(img)
            if len(names) > MAX_FILES:
                raise SystemExit(f"{img.name}: {len(names)} files, over "
                                 f"{MAX_FILES}")
            size = img.stat().st_size
            print(f"{img.relative_to(ROOT)}: {size:,} bytes, "
                  f"{len(names)}/{MAX_FILES} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
