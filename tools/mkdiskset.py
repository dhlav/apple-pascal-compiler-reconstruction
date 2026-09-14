"""Write the three 1.3 disks out of reconstructed files, and account for them.

    python tools/mkdiskset.py

Each evidence volume is rebuilt block for block from what this repo can
produce, into build/diskset/APPLE1.dsk .. APPLE3.dsk, and compared with the
evidence image as a whole. The account goes to analysis/diskset-account.txt:
every byte of every disk falls in exactly one region, and the regions have
to add up to the disk -- both the byte count and the count of bytes that
differ, which is also measured directly between the two image files.

Where each region's bytes come from:

  boot        blocks 0-1: blocks 3-4 of the rebuilt FORMATTER.DATA, which
              holds the Disk II boot that every 1.3 disk carries (275)
  directory   blocks 2-5: Apple's entries re-encoded -- names, placement,
              dates and the Filer's name residue are the master's history,
              not content any tool here produces. The dead space past the
              last entry is written as zero
  rebuilt     a file Apple's own tools produced from this repo's source,
              kept in acceptance/ as it came off the emulator
  text        a text file encoded from src/text/ and its .layout (288)
  archived    the 64K SYSTEM.APPLE and SYSTEM.PASCAL, out of scope: zero
  free        unallocated blocks: zero

A file's region is the blocks Apple's directory gives it. A rebuilt file
shorter than that is padded with zero; longer is an error, because it would
not fit where Apple put it.

`build()` is what probe_diskset.py checks; this script writes its result.
"""
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from a2pascal.disk import PascalDisk
from a2pascal.diskwrite import PascalWriter
from a2pascal.textfile import Layout, encode_text

EVIDENCE = ROOT / "evidence" / "disks"
DISKS = {"APPLE1": EVIDENCE / "Apple II Pascal 1.3 APPLE1_ 680-0283-A.dsk",
         "APPLE2": EVIDENCE / "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk",
         "APPLE3": EVIDENCE / "Apple II Pascal 1.3 APPLE3_ 680-0290-A.dsk"}
A = ROOT / "acceptance"
TEXT = ROOT / "src" / "text"
OUT = ROOT / "build" / "diskset"
ACCOUNT = ROOT / "analysis" / "diskset-account.txt"
BLOCK = 512

# Each non-text file: the kept output of Apple's tools, and the finding
# that says what it is.
REBUILT = {
    "SYSTEM.EDITOR": ("2026-09-13-editor-librarian/EDLIB.CODE", 272),
    "SYSTEM.FILER": ("2026-09-12-filer-librarian/LIBFILER.CODE", 271),
    "SYSTEM.LIBRARY": ("2026-09-14-library-decops/NEWLIB.CODE", 290),
    "SYSTEM.MISCINFO": ("2026-09-13-miscinfo/SYSTEM-NEW.MISCINFO", 277),
    "SYSTEM.CHARSET": ("2026-09-13-charset/CHARSET.DATA", 278),
    "SYSTEM.ASSMBLER": ("2026-09-12-assembler-librarian/LIBASM.CODE", 267),
    "SYSTEM.COMPILER": ("2026-09-12-compiler-librarian/LIBCOMP.CODE", 267),
    "SYSTEM.LINKER": ("2026-09-14-linker-names/LIBLINK.CODE", 291),
    "LIBRARY.CODE": ("2026-09-12-library-librarian/LIBLIB.CODE", 269),
    "LIBMAP.CODE": ("2026-09-12-libmap-linked/LIBMAPL.CODE", 270),
    "6502.OPCODES": ("2026-09-13-asm-data/OPCODES.DATA", 276),
    "6502.ERRORS": ("2026-09-13-asm-data/ERRORS.DATA", 276),
    "FORMATTER.CODE": ("2026-08-24-formatter-linked/LINKED.CODE", 104),
    "FORMATTER.DATA": ("2026-09-13-formatter-data/FORMATTER.DATA", 275),
    "BINDER.CODE": ("2026-09-13-binder-exact/BINDERT.CODE", 274),
    "LINEFEED.CODE": ("2026-09-14-linefeed/LINEFEED.CODE", 288),
    "SET40COLS.CODE": ("2026-09-13-set40cols-exact/SET40T.CODE", 274),
    "II40.MISCINFO": ("2026-09-13-miscinfo/II40-NEW.MISCINFO", 277),
    "II80.MISCINFO": ("2026-09-13-miscinfo/II80-NEW.MISCINFO", 277),
    "HAZEL.MISCINFO": ("2026-09-13-miscinfo/HAZEL-NEW.MISCINFO", 277),
    "SETUP.CODE": ("2026-09-13-setup-s2/SETUPT.CODE", 273),
    "128K.APPLE": ("2026-09-13-128k-apple/INTERP.DATA", 279),
    "128K.PASCAL": ("2026-09-14-128k-pascal/128K.PASCAL", 284),
}
ARCHIVED = {"SYSTEM.APPLE", "SYSTEM.PASCAL"}
BOOT_FROM = "2026-09-13-formatter-data/FORMATTER.DATA"


@dataclass
class Region:
    disk: str
    name: str          # a file name, or <boot>, <directory>, <free>
    category: str      # boot directory rebuilt text archived free
    first: int         # block
    blocks: int
    differ: int = 0
    source: str = ""

    @property
    def size(self) -> int:
        return self.blocks * BLOCK


def text_stem(name: str) -> str:
    return name[:-5] if name.endswith(".TEXT") else name


def payload_for(entry) -> tuple[str, bytes, str]:
    """(category, bytes, where from) for one directory entry."""
    if entry.name in ARCHIVED:
        return "archived", b"", "not rebuilt, 64K system"
    if entry.name in REBUILT:
        rel, finding = REBUILT[entry.name]
        return "rebuilt", (A / rel).read_bytes(), f"{rel} ({finding})"
    if entry.kind == "textfile":
        stem = text_stem(entry.name)
        src = TEXT / f"{stem}.text"
        text = src.read_text(encoding="ascii")
        text = text[:-1] if text.endswith("\n") else text
        layout = Layout((TEXT / f"{stem}.layout").read_text(encoding="ascii"))
        return "text", encode_text(text, layout=layout), \
            f"src/text/{stem}.text (288)"
    raise KeyError(f"nothing produces {entry.name}")


def build_disk(vol: str, carry: bool = False):
    """The rebuilt image and its regions.

    `carry` builds the control instead: every region copied from the
    evidence image through the same placement. It must equal the evidence
    exactly, or the placement -- not the reconstruction -- is what differs.
    """
    apple = PascalDisk.from_file(DISKS[vol])
    info = apple.volume()
    total = info.total_blocks
    w = PascalWriter.blank(vol, order=apple.order)
    regions: list[Region] = []

    boot = (A / BOOT_FROM).read_bytes()[3 * BLOCK:5 * BLOCK]
    if carry:
        boot = apple.read_blocks(0, 2)
    w.write_blocks(0, boot)
    regions.append(Region(vol, "<boot>", "boot", 0, 2,
                          source=f"{BOOT_FROM} blocks 3-4"))

    entries = apple.directory()
    raw_dir = apple.read_blocks(2, 4)
    last_boot = int.from_bytes(raw_dir[20:22], "little")
    directory = w.encode_directory(info.name, entries, total, last_boot,
                                   template=raw_dir if carry else None)
    w.write_blocks(2, directory)
    regions.append(Region(vol, "<directory>", "directory", 2, 4,
                          source="Apple's entries, dead space zero"))

    cursor = 6
    for e in entries:
        if e.first_block > cursor:
            regions.append(Region(vol, "<free>", "free", cursor,
                                  e.first_block - cursor, source="zero"))
        category, data, source = payload_for(e)
        if carry:
            data = apple.read_blocks(e.first_block, e.blocks)
        if len(data) > e.blocks * BLOCK:
            raise ValueError(f"{vol}:{e.name} is {len(data)} bytes, Apple's "
                             f"directory gives it {e.blocks} blocks")
        data = data + bytes(e.blocks * BLOCK - len(data))
        w.write_blocks(e.first_block, data)
        regions.append(Region(vol, e.name, category, e.first_block, e.blocks,
                              source=source))
        cursor = e.next_block
    if cursor < total:
        regions.append(Region(vol, "<free>", "free", cursor, total - cursor,
                              source="zero"))
    if carry:
        for r in regions:
            if r.category == "free":
                w.write_blocks(r.first, apple.read_blocks(r.first, r.blocks))

    for r in regions:
        ours = w.read_blocks(r.first, r.blocks)
        theirs = apple.read_blocks(r.first, r.blocks)
        r.differ = sum(1 for a, b in zip(ours, theirs) if a != b)
    return w.to_bytes(), regions


def build(carry: bool = False) -> dict[str, tuple[bytes, list[Region]]]:
    return {vol: build_disk(vol, carry) for vol in DISKS}


def image_differ(vol: str, image: bytes) -> int:
    apple = DISKS[vol].read_bytes()
    return sum(1 for a, b in zip(image, apple) if a != b)


def render(result) -> str:
    out = ["# The 1.3 disk set, rebuilt -- generated by tools/mkdiskset.py",
           "#",
           "# Every byte of each disk is in exactly one region. `differ` is",
           "# bytes unlike Apple's image. Text is src/text/ through its",
           "# .layout; rebuilt is Apple's tools on this repo's source.",
           ""]
    grand: dict[str, list[int]] = {}
    for vol, (image, regions) in result.items():
        size = sum(r.size for r in regions)
        differ = sum(r.differ for r in regions)
        out.append(f"{vol}  {size} bytes, {size - differ} identical, "
                   f"{differ} differ (image compare: "
                   f"{image_differ(vol, image)})")
        out.append(f"  {'blocks':>9}  {'region':16} {'category':9} "
                   f"{'bytes':>6} {'differ':>6}  source")
        for r in regions:
            out.append(f"  {r.first:4}+{r.blocks:<4}  {r.name:16} "
                       f"{r.category:9} {r.size:6} {r.differ:6}  {r.source}")
            g = grand.setdefault(r.category, [0, 0])
            g[0] += r.size
            g[1] += r.differ
        out.append("")
    out.append("The set, by category")
    for cat in ("rebuilt", "text", "boot", "directory", "free", "archived"):
        size, differ = grand.get(cat, [0, 0])
        out.append(f"  {cat:9} {size:7} bytes {size - differ:7} identical "
                   f"{differ:6} differ")
    size = sum(g[0] for g in grand.values())
    differ = sum(g[1] for g in grand.values())
    out.append(f"  {'all':9} {size:7} bytes {size - differ:7} identical "
               f"{differ:6} differ")
    return "\n".join(out) + "\n"


def main() -> int:
    result = build()
    OUT.mkdir(parents=True, exist_ok=True)
    for vol, (image, _) in result.items():
        (OUT / f"{vol}.dsk").write_bytes(image)
    ACCOUNT.parent.mkdir(parents=True, exist_ok=True)
    text = render(result)
    ACCOUNT.write_text(text, newline="\n")
    print(text, end="")
    print(f"wrote build/diskset/ and {ACCOUNT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
