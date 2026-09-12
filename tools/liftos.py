"""Lift the operating system to pseudo-Pascal.

`SYSTEM.PASCAL` is not the deliverable -- `SYSTEM.COMPILER` is. It is here
because it is the only large Apple Pascal binary whose source is available
(`reference_source/ucsd_ii0/`), which makes it the calibration target finding
49e asked for: the GOTOXY samples proved the pipeline on two tiny procedures
using assignments and conditionals and nothing else, and the operating system
exercises loops, `case`, sets, records, `with` and calls between segments.

Finding 8 sets the limit on what that comparison can prove. The source is the
*generic* UCSD II.0 operating system; Apple's is a fork of it. Routines that
match are evidence about the compiler; routines that differ are evidence
about Apple, not about the lifter. So this writes the listing and counts what
lifted, and leaves the alignment to `probes/probe_os_calibrate.py`.

Segment 0 is stored in two pieces (finding 50), which is why the header says
which piece each procedure came out of -- a procedure whose JTAB is in the
continuation is no different in kind, and if the join were wrong that is
where it would show first.

Writes analysis/lifted/SYSTEM.PASCAL-{1.1,1.3}.pas.txt.
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
OUT = ROOT / "analysis" / "lifted"
DISKS = {
    "1.3-128K": ("Apple II Pascal 1.3 APPLE3_ 680-0290-A.dsk", "128K.PASCAL"),
}


def result_words(seg, p) -> int:
    """A function returns through RNP/RBP's operand; 0 means a procedure."""
    tail = (disassemble(seg.data, p.enter_ic, p.exit_ic, p.jtab)[0]
            + sweep_exit(seg.data, p.exit_ic, p.jtab - 8, p.jtab)[0])
    for i in reversed(tail):
        if i.mnemonic in ("RNP", "RBP"):
            return i.operands[0]
    return 0


def piece(seg, p) -> str:
    """Which stored piece of a split segment this procedure came out of."""
    if not seg.is_split:
        return ""
    for at, n, slot in seg.chunks:
        if at <= p.jtab < at + n:
            return f", slot {slot}"
    return ", PADDING"          # cannot happen; the probe requires it cannot


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for ver, (fname, member) in DISKS.items():
        disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / fname)
        e = disk.find(member)
        cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))

        lines = [f"Apple Pascal {ver} {member} -- lifted to pseudo-Pascal",
                 "",
                 "Storage is named as it is addressed, not invented: G<n> is",
                 "global word n, L<n> local word n, I<lex>,<n> intermediate.",
                 "No name table is applied -- names.py holds SYSTEM.COMPILER's",
                 "names and nothing else, so every identifier here is an",
                 "address and not a claim.",
                 "",
                 "Segment 0 is stored in two pieces (finding 50); each",
                 "procedure header says which one it came out of.",
                 ""]
        clean = total = gotos = structured = 0
        reasons = Counter()
        for seg in cf.segments:
            lines += ["=" * 70,
                      f"SEGMENT {seg.seg_num} {seg.name}"
                      + (f"  [split: {len(seg.chunks)} pieces]"
                         if seg.is_split else ""),
                      "=" * 70]
            for p in seg.procedures:
                if p.is_native:
                    lines.append(f"\nprocedure {seg.name}.{p.number};  "
                                 f"{{ native 6502, not lifted }}")
                    continue
                total += 1
                rw = result_words(seg, p)
                fn = f" : <{rw} word result>" if rw else ""
                # A function's parameter area includes the result slot the
                # caller reserves (probe_funcresult.py).
                argw = p.param_size // 2 - (2 if rw else 0)
                hdr = (f"\n{'function' if rw else 'procedure'} {seg.name}."
                       f"{p.number}(args {argw} words){fn};  "
                       f"{{ locals {p.data_size // 2} words, "
                       f"lex {p.lex_level}{piece(seg, p)} }}")
                blocks = lift(seg, p, cf, "")
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
                structured += (g == 0)
                lines.append(text)
            lines.append("")

        path = OUT / f"{member}-{ver}.pas.txt"
        path.write_text("\n".join(lines), encoding="ascii", errors="replace")
        print(f"[{ver}] {clean}/{total} lifted with the stack fully tracked; "
              f"{structured}/{total} fully structured "
              f"({gotos} gotos left) -> {path.name}")
        if reasons:
            print("      blocked by:", ", ".join(f"{k} x{v}"
                                                 for k, v in reasons.most_common(8)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
