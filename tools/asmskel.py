"""Skeleton assembly source for a native procedure, to be finished by hand.

The library's fourteen native procedures run to about 3600 bytes, and every
one of them has to come back as source that Apple's assembler turns into
exactly those bytes again. Transcribing that by eye is not the interesting
part and is where the errors would be, so this writes the mechanical part:
labels wherever something jumps or a relocation entry points, symbolic
operands wherever the binary says the operand was symbolic, and `.BYTE` for
the regions that are data.

What it does *not* write is the part that matters -- what anything is
called, and what any of it is for. The output is a starting point for
`src/native/`, not a substitute for it, and it is deliberately not wired
into build_all.py: nothing in `analysis/` should look like source.

    python tools/asmskel.py APPLESTU.6
    python tools/asmskel.py LONGINTI.4 > skel.txt
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile, RELOC_KINDS
from a2pascal.m6502 import (disassemble, IMM, ZP, ZPX, ZPY, IZX, IZY,
                            ABS, ABX, ABY, IND, REL, ACC, IMP)

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "evidence" / "disks" / \
    "Apple II Pascal 1.3 APPLE1_ 680-0283-A.dsk"

# Regions inside a procedure that are data, as (segment, procedure, lo, hi).
# Kept here rather than inferred: a linear sweep cannot tell a jump table
# from code, and guessing would put the whole disassembly out of step.
DATA = {
    ("APPLESTU", 8): [(0x0159, 0x01C2)],
    ("APPLESTU", 6): [(0x0225, 0x0229)],
    ("TURTLEGR", 16): [(0x13E7, 0x1408)],
    ("TURTLEGR", 30): [(0x0BB4, 0x0BBC), (0x0DE3, 0x0DEC)],
    ("LONGINTI", 4): [(0x02C2, 0x02D8), (0x043B, 0x0453),
                      (0x066E, 0x0675)],
}


def load(segname: str):
    d = PascalDisk.from_file(IMG)
    e = d.find("SYSTEM.LIBRARY")
    cf = CodeFile(d.read_blocks(e.first_block, e.blocks))
    for s in cf.segments:
        if s.name.strip() == segname and s.procedures:
            return s
    raise SystemExit(f"no segment named {segname}")


def exports(seg) -> dict[int, str]:
    """Every segment offset one native procedure names in another.

    A `.REF` in one procedure has to be a `.DEF` in another, and the pair is
    the only reason a segment-relative entry exists. Collecting the targets
    across the whole segment says which labels have to be exported and
    which procedure owns each.
    """
    out = {}
    for q in seg.native_procedures:
        for t in q.reloc["segment"]:
            v = int.from_bytes(seg.data[t:t + 2], "little")
            out[v] = f"S{v:04X}"
    return out


def skeleton(segname: str, number: int) -> str:
    seg = load(segname)
    p = next(q for q in seg.native_procedures if q.number == number)
    exported = exports(seg)
    base, end = p.enter_ic, p.content_end
    data = seg.data

    kind = {}                       # operand offset -> relocation kind
    for k in RELOC_KINDS:
        for t in p.reloc[k]:
            kind[t] = k

    regions, a = [], base
    for lo, hi in DATA.get((segname, number), []):
        if a < lo:
            regions.append(("code", a, lo))
        regions.append(("data", lo, hi))
        a = hi
    if a < end:
        regions.append(("code", a, end))

    insns = []
    for what, lo, hi in regions:
        if what == "code":
            insns += disassemble(data, lo, hi)[0]
    # A procedure is padded to a word boundary and the Linker puts the pad
    # back, so a lone trailing zero byte is not source -- unless something
    # relocates to it, which makes it a one-byte variable that happens to
    # sit last. FILLIT keeps two of its counters there.
    targets = {base + int.from_bytes(data[t:t + 2], "little")
               for t in p.reloc["procedure"]}
    if insns and insns[-1].raw == bytes(1) and insns[-1].addr == end - 1             and end - 1 not in targets:
        insns.pop()
        regions = [(w, lo, min(hi, end - 1)) for w, lo, hi in regions
                   if lo < end - 1]

    # Where a label may legally go: the start of an instruction, or the
    # start of a data item. Anything else is inside one, and the source
    # reached it by naming the item and adding an offset.
    item = {}                       # address -> the item start containing it
    for i in insns:
        for n in range(i.length):
            item[i.addr + n] = i.addr
    for what, lo, hi in regions:
        if what != "data":
            continue
        a = lo
        while a < hi:
            n = 2 if kind.get(a) == "procedure" else 1
            for k in range(n):
                item[a + k] = a
            a += n

    def anchor(a: int) -> int:
        return item.get(a, a)

    # Everything that has to carry a label: branch and jump targets, and
    # anything a procedure-relative relocation entry points at -- including
    # the base of an indexed operand, which is a label even though the
    # address it forms is not.
    labels = {i.target for i in insns
              if i.target is not None and i.mode is REL}
    for i in insns:
        if kind.get(i.addr + 1) == "procedure":
            labels.add(anchor(base + (i.operand or 0)))
    for what, lo, hi in regions:
        if what != "data":
            continue
        for a in range(lo, hi - 1, 2):
            if kind.get(a) == "procedure":
                labels.add(anchor(base + int.from_bytes(
                    data[a:a + 2], "little")))
    # Anything another procedure names has to be a label here, and .DEF'd.
    mine = sorted(a for a in exported if base <= a < end)
    labels |= set(mine)
    labels = {a for a in labels if a is not None}

    ordered = sorted(labels)

    def name(a: int) -> str:
        return exported.get(a) or f"L{a - base:04X}"

    def sym(a: int) -> str:
        """A label, or the label of the item containing it plus an offset.

        The high half of a table base is not its own label; neither is the
        byte before a patch site. Both were written as something named plus
        or minus a constant, and the constant is hexadecimal, which is the
        assembler's default base.
        """
        if a in labels:
            return name(a)
        at = anchor(a)
        return f"{name(at)}+0{a - at:02X}" if at in labels             else f"L{a - base:04X}?"

    def operand(i) -> str:
        """The operand as source: symbolic if the binary says it was."""
        k = kind.get(i.addr + 1)
        v = i.operand or 0
        if k == "procedure":
            return sym(base + v)
        if k == "interp":
            return ".INTERP" + (f"+{v}" if v else "")
        if k == "segment":
            return exported.get(v, f"X{v:04X}")
        if k == "base":
            return f"B{v:04X}"
        return f"0{v:04X}" if v > 0xFF or i.mode in (ABS, ABX, ABY, IND) \
            else f"0{v:02X}"

    out = []
    if mine:
        out.append("        .DEF " + ",".join(exported[a] for a in mine))
    refs = sorted({operand(i) for i in insns
                   if kind.get(i.addr + 1) == "segment"})
    if refs:
        out.append(f"        .REF {','.join(refs)}")
    by_addr = {i.addr: i for i in insns}
    for what, lo, hi in regions:
        if what == "data":
            out.append(";       ---- data")
            a = lo
            while a < hi:
                lab = name(a) if a in labels else ""
                if kind.get(a) == "procedure":
                    w = int.from_bytes(data[a:a + 2], "little")
                    out.append(f"{lab:<7} .WORD {name(base + w)}")
                    a += 2
                    continue
                row = data[a:min(a + 8, hi)]
                # Stop a row early if a later byte carries a label.
                for n in range(1, len(row)):
                    if a + n in labels:
                        row = row[:n]
                        break
                out.append(f"{lab:<7} .BYTE "
                           + ",".join(f"0{b:02X}" for b in row))
                a += len(row)
            continue
        a = lo
        while a < hi:
            i = by_addr[a]
            a += i.length
            lab = name(i.addr) if i.addr in labels else ""
            m, o = i.mode, operand(i)
            if m is IMP:
                arg = ""
            elif m is ACC:
                arg = "A"
            elif m is REL:
                arg = name(i.target)
            elif m is IMM:
                arg = f"#0{i.operand:02X}"
            elif m in (ZPX, ABX):
                arg = f"{o},X"
            elif m in (ZPY, ABY):
                arg = f"{o},Y"
            elif m is IZX:
                arg = f"@{o},X"
            elif m is IZY:
                arg = f"@{o},Y"
            elif m is IND:
                arg = f"@{o}"
            else:
                arg = o
            out.append(f"{lab:<7} {i.mnemonic:<4}{' ' + arg if arg else ''}")
    return "\n".join(out)


def main() -> None:
    for spec in sys.argv[1:]:
        segname, _, num = spec.partition(".")
        print(f";---- {spec}")
        print(skeleton(segname, int(num)))


if __name__ == "__main__":
    main()
