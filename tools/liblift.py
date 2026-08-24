"""Lift SYSTEM.LIBRARY's units to pseudo-Pascal, and list their p-code.

The library is the next reconstruction target, and it starts from a better
place than the compiler did: every unit's INTERFACE is in the file as Apple's
own source text (finding 92a), so the declarations are given and only the
IMPLEMENTATION has to be recovered. This is the other half of the evidence --
the code those interfaces stand in front of.

Same machinery as `liftall.py`, pointed at a different codefile. Storage is
named as it is addressed and no name table is applied: `names.py` holds
SYSTEM.COMPILER's names and nothing else, so every identifier here is an
address and not a claim.

Writes analysis/lifted/SYSTEM.LIBRARY-{ver}.pas.txt and
analysis/pcode_disassembly/SYSTEM.LIBRARY-{ver}.pcode.txt.
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.pcode import disassemble, sweep_exit
from a2pascal.lift import lift
from a2pascal.structure import structure

ROOT = Path(__file__).resolve().parent.parent
LIFTED = ROOT / "analysis" / "lifted"
PCODE = ROOT / "analysis" / "pcode_disassembly"
DISKS = {
    "1.1": "UCSD Pascal 1.1_1.dsk",
    "1.3": "Apple II Pascal 1.3 APPLE1_ 680-0283-A.dsk",
}


def result_words(seg, p) -> int:
    tail = (disassemble(seg.data, p.enter_ic, p.exit_ic, p.jtab)[0]
            + sweep_exit(seg.data, p.exit_ic, p.jtab - 8, p.jtab)[0])
    for i in reversed(tail):
        if i.mnemonic in ("RNP", "RBP"):
            return i.operands[0]
    return 0


def main() -> int:
    LIFTED.mkdir(parents=True, exist_ok=True)
    PCODE.mkdir(parents=True, exist_ok=True)
    for ver, fname in DISKS.items():
        disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / fname)
        e = disk.find("SYSTEM.LIBRARY")
        cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))

        head = [f"Apple Pascal {ver} SYSTEM.LIBRARY -- lifted to pseudo-Pascal",
                "",
                "Storage is named as it is addressed, not invented: G<n> is",
                "global word n, L<n> local word n, I<lex>,<n> intermediate.",
                "No name table is applied -- the interfaces in",
                "analysis/library/interface/ are what supply real names, and",
                "matching them to these procedures is the reconstruction.",
                ""]
        lines, plines = list(head), [head[0].replace("lifted to pseudo-Pascal",
                                                    "p-code listing"), ""]
        clean = total = gotos = structured = native = 0
        reasons = Counter()
        for seg in cf.segments:
            bar = "=" * 70
            lines += [bar, f"SEGMENT {seg.seg_num} {seg.name}"
                           f"  ({len(seg.procedures)} procedures)", bar]
            plines += [bar, f"SEGMENT {seg.seg_num} {seg.name}"
                            f"  block={seg.block} len={len(seg.data)}", bar]
            for p in seg.procedures:
                if p.is_native:
                    native += 1
                    lines.append(f"\nprocedure {seg.name}.{p.number};  "
                                 f"{{ native 6502, {p.jtab - p.enter_ic} "
                                 f"bytes, not lifted }}")
                    continue
                total += 1
                ins = (disassemble(seg.data, p.enter_ic, p.exit_ic, p.jtab)[0]
                       + sweep_exit(seg.data, p.exit_ic, p.jtab - 8,
                                    p.jtab)[0])
                plines.append(f"\n--- procedure {p.number}  "
                              f"param {p.param_size} data {p.data_size} "
                              f"lex {p.lex_level}")
                plines += [f"  ${i.addr:04X}  {i.text}" for i in ins]
                rw = result_words(seg, p)
                fn = f" : <{rw} word result>" if rw else ""
                # A function's parameter area includes the caller's result
                # slot, two words (probe_funcresult.py).
                argw = p.param_size // 2 - (2 if fn else 0)
                hdr = (f"\n{'function' if fn else 'procedure'} {seg.name}."
                       f"{p.number}(args {argw} words){fn};  "
                       f"{{ locals {p.data_size // 2} words, "
                       f"lex {p.lex_level} }}")
                blocks = lift(seg, p, cf, ver)
                if any(b.incomplete for b in blocks):
                    for b in blocks:
                        for s in b.stmts:
                            if s.startswith("{ stack tracking stopped"):
                                reasons[s.split(": ", 1)[1].rstrip(" }")] += 1
                                break
                else:
                    clean += 1
                text, g, _nb = structure(blocks, hdr)
                gotos += g
                structured += g == 0
                lines.append(text)
            lines.append("")

        for path, body in ((LIFTED / f"SYSTEM.LIBRARY-{ver}.pas.txt", lines),
                           (PCODE / f"SYSTEM.LIBRARY-{ver}.pcode.txt", plines)):
            path.write_text("\n".join(body), encoding="ascii",
                            errors="replace", newline="\n")
        print(f"[{ver}] {total} p-code procedures ({native} native, not "
              f"lifted); {clean}/{total} with the stack fully tracked, "
              f"{structured}/{total} fully structured ({gotos} gotos)")
        if reasons:
            print("      blocked by:", ", ".join(f"{k} x{v}" for k, v
                                                 in reasons.most_common(8)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
