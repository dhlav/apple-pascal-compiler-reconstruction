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
    "1.1-APPLE1": "UCSD Pascal 1.1_1.dsk",
    "1.1-APPLE2": "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk",
    "1.1-APPLE3": "UCSD Pascal 1.1_3.dsk",
}
# These have their own listings already.
SKIP = {"SYSTEM.COMPILER", "SYSTEM.LIBRARY"}
OUT = ROOT / "analysis" / "utilities"


def targets() -> set[str]:
    """Codefiles that ship on a 1.3 disk.

    1.3 is what is being reproduced, so this is the set that has to be
    reconstructed, and it is what the coverage figure is counted over.

    It is *not* a filter on what gets disassembled and lifted. Everything on
    all six disks still does, because the 1.1-only files cost nothing to
    keep and one group of them is irreplaceable: eleven demo programs ship
    as .TEXT on the 1.3 APPLE3 disk and as .TEXT *and* .CODE on 1.1's, and
    that pair is the only corpus anywhere of Apple's source beside Apple's
    own output. `probe_calibrate.py` is built on two of them.
    """
    from a2pascal.disk import PascalDisk as _D
    out = set()
    for tag, fname in DISKS.items():
        if not tag.startswith("1.3"):
            continue
        d = _D.from_file(ROOT / "evidence" / "disks" / fname)
        out |= {e.name for e in d.directory() if e.kind == "codefile"}
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    n = 0
    for tag, fname in DISKS.items():
        disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / fname)
        for e in disk.directory():
            if e.kind != "codefile" or e.name in SKIP:
                continue
            cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))
            stem = e.name.rsplit(".", 1)[0]
            path = OUT / f"{stem}-{tag}.pcode.txt"
            path.write_text(
                listing_for(cf, f"Apple Pascal {tag} {e.name}"),
                encoding="ascii")
            n += 1
    print(f"wrote {n} listings to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
