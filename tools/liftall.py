"""Lift every procedure to pseudo-Pascal and report coverage."""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.pcode import disassemble, sweep_exit
from a2pascal.lift import lift, render

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "analysis" / "lifted"
OUT.mkdir(parents=True, exist_ok=True)
DISKS = {
    "1.1": "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk",
    "1.3": "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk",
}

for ver, fname in DISKS.items():
    disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / fname)
    e = disk.find("SYSTEM.COMPILER")
    cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))

    lines = [f"Apple Pascal {ver} SYSTEM.COMPILER -- lifted to pseudo-Pascal",
             "",
             "Storage is named as it is addressed, not invented: G<n> is global",
             "word n, L<n> local word n, I<lex>,<n> intermediate. See",
             "docs/FINDINGS.md for what the numbered storage actually is.",
             "A '{ stack tracking stopped }' marker means an instruction of",
             "unknown stack effect was reached; the rest of that block is",
             "listed verbatim.",
             ""]
    clean = total = 0
    reasons = Counter()
    for seg in cf.segments:
        lines.append("=" * 70)
        lines.append(f"SEGMENT {seg.seg_num} {seg.name}")
        lines.append("=" * 70)
        for p in seg.procedures:
            if p.is_native:
                lines.append(f"\nprocedure {seg.name}.{p.number};  "
                             f"{{ native 6502, not lifted }}")
                continue
            total += 1
            fn = ""
            for i in reversed(disassemble(seg.data, p.enter_ic, p.exit_ic, p.jtab)[0]
                              + sweep_exit(seg.data, p.exit_ic, p.jtab - 8, p.jtab)[0]):
                if i.mnemonic in ("RNP", "RBP"):
                    fn = f" : <{i.operands[0]} word result>" if i.operands[0] else ""
                    break
            hdr = (f"\n{'function' if fn else 'procedure'} {seg.name}.{p.number}"
                   f"(params {p.param_size // 2} words){fn};  "
                   f"{{ locals {p.data_size // 2} words, lex {p.lex_level} }}")
            blocks = lift(seg, p, cf)
            if any(b.incomplete for b in blocks):
                for b in blocks:
                    for s in b.stmts:
                        if s.startswith("{ stack tracking stopped"):
                            reasons[s.split(": ", 1)[1].rstrip(" }")] += 1
                            break
            else:
                clean += 1
            lines.append(render(blocks, hdr))
        lines.append("")

    path = OUT / f"SYSTEM.COMPILER-{ver}.pas.txt"
    path.write_text("\n".join(lines), encoding="ascii", errors="replace")
    print(f"[{ver}] {clean}/{total} procedures lifted with the stack fully "
          f"tracked -> {path.name}")
    if reasons:
        print("      blocked by:", ", ".join(f"{k} x{v}"
                                             for k, v in reasons.most_common(12)))
