"""Take SYSTEM.LIBRARY apart: what units are in it, and their INTERFACE text.

Apple ships six units in one library file, every one of them a *linked
intrinsic* (segkind 6): a unit whose code segment is already bound and whose
segment number is fixed, so a program that `USES` it is linked against the
copy that is already on the boot disk.

The find that makes reconstruction tractable is in the segment dictionary.
Each unit's dictionary entry carries a TEXTADDR -- a block, inside the
library itself, holding **the unit's INTERFACE section as source text**.
That is Apple's own source, not a reconstruction: the compiler copies the
interface into the codefile so a later `USES` can compile against it
(finding 80), and nobody ever took it out again. So for each unit the
declarations, the types and every procedure heading are recovered exactly,
and only the IMPLEMENTATION has to be worked out from the p-code.

Writes analysis/library/SYSTEM.LIBRARY-{ver}-map.txt and, beside it,
interface/{ver}/{UNIT}.text -- one file per unit, decoded.
"""
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "analysis" / "library"
DISKS = {
    "1.1": ("UCSD Pascal 1.1_1.dsk", "SYSTEM.LIBRARY"),
    "1.3": ("Apple II Pascal 1.3 APPLE1_ 680-0283-A.dsk", "SYSTEM.LIBRARY"),
}
# The segment dictionary, 512 bytes at the head of every codefile. Offsets
# are the ones the 1.3 manual gives at IV-32 and FINISHUP writes (finding 75).
DISKINFO, SEGNAME, SEGKIND, TEXTADDR, SEGINFO = 0x00, 0x40, 0xC0, 0xE0, 0x100
KIND = {0: "LINKED", 1: "HOSTSEG", 2: "SEGPROC", 3: "UNITSEG",
        4: "SEPRTSEG", 5: "UNLINKED-INTRINS", 6: "LINKED-INTRINS",
        7: "DATASEG"}


def word(raw: bytes, off: int) -> int:
    return struct.unpack_from("<H", raw, off)[0]


def decode_text(raw: bytes, first: int, last: int) -> str:
    """The interface text, from block `first` up to the code at `last`.

    A UCSD textfile compresses leading blanks: DLE (16) then a byte, and the
    indent is that byte less 32. Lines end in CR, and a block is padded with
    NULs from the last complete line, so a NUL ends the block and not the
    file.
    """
    out = []
    for blk in range(first, last):
        page, i = raw[blk * 512:(blk + 1) * 512], 0
        while i < len(page):
            c = page[i]
            if c == 0:
                break
            if c == 16 and i + 1 < len(page):
                out.append(" " * max(0, page[i + 1] - 32))
                i += 2
                continue
            out.append("\n" if c == 13 else chr(c) if 32 <= c < 127 else " ")
            i += 1
    # The interface ends at IMPLEMENTATION -- that is where the compiler
    # stops copying. What follows in the block is whatever was in the
    # buffer before, and it looks like source: 1.1's TURTLEGRAPHICS is
    # followed by six procedure headings from an earlier version of its
    # own interface. Cut it, or a stale copy reads as evidence.
    text = "".join(out)
    m = re.search(r"^\s*IMPLEMENTATION", text, re.M)
    return (text[:m.end()] + "\n") if m else text


def main() -> int:
    for ver, (fname, member) in DISKS.items():
        disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / fname)
        e = disk.find(member)
        raw = disk.read_blocks(e.first_block, e.blocks)
        cf = CodeFile(raw)
        segs = {s.index: s for s in cf.segments}

        lines = [f"{member} unit map -- Apple Pascal {ver}",
                 f"source image : {fname}",
                 f"file blocks  : {e.first_block}..{e.first_block + e.blocks}"
                 f" ({e.blocks} blocks, {len(raw)} bytes)",
                 "",
                 "Derived directly from the binary by tools/libmap.py.",
                 "VERIFIED BINARY FACT unless marked otherwise.",
                 ""]
        for i in range(16):
            blk, leng = word(raw, i * 4), word(raw, i * 4 + 2)
            if not leng:
                continue
            name = raw[SEGNAME + i * 8:SEGNAME + i * 8 + 8].decode(
                "ascii", "replace")
            kind, ta = word(raw, SEGKIND + i * 2), word(raw, TEXTADDR + i * 2)
            seg = segs.get(i)
            native = sum(1 for p in seg.procedures if p.is_native) if seg else 0
            lines += ["", f"--- slot {i}  {name}  block={blk} len={leng} "
                          f"segkind={kind} ({KIND.get(kind, '?')}) "
                          f"textaddr={ta}"]
            if seg:
                lines.append("      #  param   data  lex  size  kind")
                for p in seg.procedures:
                    lines.append(
                        f"    {p.number:3} {p.param_size:6} {p.data_size:6} "
                        f"{p.lex_level:4} {p.jtab - p.enter_ic:5}  "
                        f"{'6502' if p.is_native else 'pcode'}")
                lines.append(f"    {len(seg.procedures)} procedures, "
                             f"{native} native")
            if ta and blk > ta:
                text = decode_text(raw, ta, blk)
                d = OUT / "interface" / ver
                d.mkdir(parents=True, exist_ok=True)
                (d / f"{name.strip()}.text").write_text(text, newline="\n")
                lines.append(f"    INTERFACE text: blocks {ta}..{blk}, "
                             f"{len(text)} characters, written to "
                             f"analysis/library/interface/{ver}/"
                             f"{name.strip()}.text")

        OUT.mkdir(parents=True, exist_ok=True)
        path = OUT / f"{member}-{ver}-map.txt"
        path.write_text("\n".join(lines) + "\n", newline="\n")
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
