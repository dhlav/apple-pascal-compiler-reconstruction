"""P-code listings for the rest of the disk set.

`SYSTEM.COMPILER` and `SYSTEM.LIBRARY` have listings of their own. Every
other codefile on the 1.3 disks is a reconstruction target too, and this
writes the same annotated listing for each of them into
`analysis/utilities/`.

The 1.1 disks are included where a file exists in both releases, because a
1.3 utility Apple did not rebuild (finding 99c) has to be read against the
compiler that actually produced it -- and because 1.1 sometimes ships the
source, which is how LINEFEED was reconstructed.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from disasm import listing_for

ROOT = Path(__file__).resolve().parent.parent
DISKS = {
    "1.3-APPLE1": "Apple II Pascal 1.3 APPLE1_ 680-0283-A.dsk",
    "1.3-APPLE2": "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk",
    "1.3-APPLE3": "Apple II Pascal 1.3 APPLE3_ 680-0290-A.dsk",
}
# These have their own listings already -- and SYSTEM.PASCAL is the 64K
# operating system, archived: only 128K.PASCAL is a target, and the 64K
# build stays inside the APPLE1 image only because evidence cannot change.
SKIP = {"SYSTEM.COMPILER", "SYSTEM.LIBRARY", "SYSTEM.PASCAL"}
OUT = ROOT / "analysis" / "utilities"


def targets() -> set[str]:
    """Codefiles that ship on a 1.3 disk.

    1.3 is what is being reproduced, so this is the set that has to be
    reconstructed, and it is what the coverage figure is counted over.

    Only the three 1.3 disks are swept. The 1.1 disks, and with them the
    demo programs that shipped as .TEXT and .CODE together and calibrated
    the lifter (archive/tools/probes/probe_calibrate.py), are in
    evidence/archive/1.1. The archived 64K SYSTEM.PASCAL is left out.
    """
    from a2pascal.disk import PascalDisk as _D
    out = set()
    for tag, fname in DISKS.items():
        if not tag.startswith("1.3"):
            continue
        d = _D.from_file(ROOT / "evidence" / "disks" / fname)
        out |= {e.name for e in d.directory()
                if e.kind == "codefile" and e.name != "SYSTEM.PASCAL"}
    return out


def stems(names) -> dict:
    """{filename: the part of it that names the output file}.

    The extension comes off -- `FORMATTER.CODE` reads better as
    `FORMATTER` -- but only where that leaves the file distinguishable.
    Six of the files on these disks are `SYSTEM.something`, and stripping
    blindly gave all of them the same name: on 1.3's APPLE1 the listings
    for `SYSTEM.PASCAL` and `SYSTEM.EDITOR` were written and then
    overwritten by `SYSTEM.FILER`'s, and on APPLE2 `SYSTEM.ASSMBLER`'s was
    overwritten by `SYSTEM.LINKER`'s. No error, no gap in the count -- the
    files were simply not there, and the assembler had no listing at all
    for the length of the project. Collisions keep their full names.
    """
    out, seen = {}, {}
    for name in names:
        seen.setdefault(name.rsplit(".", 1)[0], []).append(name)
    for stem, group in seen.items():
        for name in group:
            out[name] = stem if len(group) == 1 else name
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    n = 0
    for tag, fname in DISKS.items():
        disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / fname)
        wanted = [e for e in disk.directory()
                  if e.kind == "codefile" and e.name not in SKIP]
        stem_of = stems(e.name for e in wanted)
        for e in wanted:
            cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))
            stem = stem_of[e.name]
            path = OUT / f"{stem}-{tag}.pcode.txt"
            path.write_text(
                listing_for(cf, f"Apple Pascal {tag} {e.name}"),
                encoding="ascii")
            n += 1
    print(f"wrote {n} listings to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
