"""Emit the full segment + procedure map for SYSTEM.COMPILER on both disks."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "analysis" / "procedure_maps"
OUT.mkdir(parents=True, exist_ok=True)

DISKS = {
    "1.1": "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk",
    "1.3": "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk",
}

for ver, fname in DISKS.items():
    disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / fname)
    e = disk.find("SYSTEM.COMPILER")
    cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))

    lines = [
        f"SYSTEM.COMPILER segment/procedure map -- Apple Pascal {ver}",
        f"source image : {fname}",
        f"file blocks  : {e.first_block}..{e.next_block - 1} ({e.blocks} blocks, {e.size} bytes)",
        f"copyright    : {cf.copyright}",
        "",
        "Derived directly from the binary by tools/a2pascal/codefile.py.",
        "VERIFIED BINARY FACT unless marked otherwise.",
        "",
    ]
    for seg in cf.segments:
        flag = "" if seg.seg_num == seg.seg_num_tail else "  !! SEGINFO/tail segnum disagree"
        lines.append(
            f"--- segment {seg.seg_num:2}  {seg.name:<8}  dictslot={seg.index:<2} "
            f"block={seg.block:<3} len={seg.length:<6} mtype={seg.mtype:<9} "
            f"ver={seg.version} nproc={len(seg.procedures)}{flag}")
        if seg.native_procedures:
            lines.append(f"    contains native 6502 procedures: "
                         f"{[p.number for p in seg.native_procedures]}")
        lines.append(f"    {'#':>3} {'JTAB':>6} {'enter':>6} {'exit':>6} "
                     f"{'param':>6} {'data':>6}  lex  size  ok  kind")
        for p in seg.procedures:
            size = p.exit_ic - p.enter_ic
            lines.append(
                f"    {p.number:>3} 0x{p.jtab:04X} 0x{p.enter_ic:04X} 0x{p.exit_ic:04X} "
                f"{p.param_size:>6} {p.data_size:>6}  {p.lex_level:>3} {size:>5}  "
                f"{'y' if p.consistent else 'N'}  {'6502' if p.is_native else 'pcode'}")
        lines.append("")

    text = "\n".join(lines)
    (OUT / f"SYSTEM.COMPILER-{ver}-map.txt").write_text(text, encoding="ascii")
    print(text)
