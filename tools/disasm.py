"""Annotated p-code listings.

Run directly, this writes SYSTEM.COMPILER's. `listing_for` is the renderer
and takes any CodeFile, which is what `disasm_utils.py` points at the rest
of the disk set.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.pcode import disassemble, sweep_exit
from a2pascal.syscall import segment0_procedures, CSP

SEG0 = segment0_procedures(ROOT_GLOBALS := Path(__file__).resolve().parent.parent
                           / "reference_source" / "ucsd_ii0" / "GLOBALS.TEXT")

ROOT = Path(__file__).resolve().parent.parent
DISKS = {
    "1.3": "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk",
}

# Segment number -> name, for annotating CXP.
def seg_names(cf):
    return {s.number: s.name for s in cf.segments}


def annotate(ins, segmap):
    if ins.mnemonic == "CXP":
        s, p = ins.operands
        if s == 0:
            return f"  ; OS.{p} {SEG0.get(p, '?')}"
        return f"  ; {segmap.get(s, f'seg{s}')}.{p}"
    if ins.mnemonic in ("CLP", "CGP", "CIP", "CBP"):
        return f"  ; local proc {ins.operands[0]}"
    if ins.mnemonic == "CSP":
        n = ins.operands[0]
        return f"  ; CSP {CSP[n]}" if n in CSP else f"  ; CSP {n}"
    return ""


def listing_for(cf, title):
    segmap = seg_names(cf)
    out = [f"{title} -- p-code listing",
           f"copyright: {cf.copyright}", ""]
    for seg in cf.segments:
        out.append("=" * 72)
        out.append(f"SEGMENT {seg.seg_num} {seg.name}  block={seg.block} "
                   f"len={seg.length} mtype={seg.mtype} nproc={len(seg.procedures)}")
        out.append("=" * 72)
        for p in seg.procedures:
            if p.is_native:
                out.append("")
                out.append(f"--- procedure {p.number}  NATIVE 6502  "
                           f"enter=${p.enter_ic:04X} jtab=${p.jtab:04X} "
                           f"data={p.data_size} (not disassembled)")
                continue
            # branch targets, for labelling
            body, _ = disassemble(seg.data, p.enter_ic, p.exit_ic, p.jtab)
            ex, end = sweep_exit(seg.data, p.exit_ic, p.jtab - 8, p.jtab)
            targets = set()
            for i in body + ex:
                if i.target is not None:
                    targets.add(i.target)
                if i.mnemonic == "XJP":
                    targets.add(i.operands[2])
                    targets.update(i.operands[3])
            out.append("")
            out.append(f"--- procedure {p.number}  lex={p.lex_level} "
                       f"params={p.param_size} data={p.data_size} "
                       f"enter=${p.enter_ic:04X} exit=${p.exit_ic:04X} jtab=${p.jtab:04X}")
            for i in body:
                lbl = f"L{i.addr:04X}:" if i.addr in targets else ""
                out.append(f"  {i.addr:04X} {i.raw.hex(' '):<20} {lbl:<8}"
                           f"{i.text}{annotate(i, segmap)}")
            out.append(f"  ---- exit code (EXIT target) ----")
            for i in ex:
                lbl = f"L{i.addr:04X}:" if i.addr in targets else ""
                out.append(f"  {i.addr:04X} {i.raw.hex(' '):<20} {lbl:<8}"
                           f"{i.text}{annotate(i, segmap)}")
            njump = (p.jtab - 8 - end) // 2 if end is not None else 0
            if njump:
                out.append(f"  ---- jump table: {njump} entr{'y' if njump == 1 else 'ies'} ----")
                for k in range(1, njump + 1):
                    at = p.jtab - 8 - 2 * k
                    import struct as _s
                    tgt = at - _s.unpack_from("<H", seg.data, at)[0]
                    out.append(f"       jtab-{p.jtab - at:<3} -> ${tgt:04X}")
        out.append("")
    return "\n".join(out)


OUT = ROOT / "analysis" / "pcode_disassembly"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for ver, fname in DISKS.items():
        disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / fname)
        e = disk.find("SYSTEM.COMPILER")
        cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))
        path = OUT / f"SYSTEM.COMPILER-{ver}.pcode.txt"
        path.write_text(listing_for(cf, f"Apple Pascal {ver} SYSTEM.COMPILER"),
                        encoding="ascii")
        print(f"wrote {path}  ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
