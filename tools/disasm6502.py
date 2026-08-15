"""Disassemble the native 6502 procedures of SYSTEM.COMPILER.

Only Apple Pascal 1.3 has any: PASCALCO procedures 2 and 3, the hand-coded
IDSEARCH and TREESEARCH (findings 6a, 19). Writes
analysis/native/PASCALCO-1.3-native.asm.txt.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile, RELOC_KINDS
from a2pascal.m6502 import disassemble, ABS, ABX, ABY, IND

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "analysis" / "native"

# Established in finding 19 by matching the five 1.3 call sites against the
# five CSP 7/8 sites at the same offsets in 1.1.
NAMES = {2: "IDSEARCH", 3: "TREESEARCH"}

# Data embedded in the middle of IDSEARCH. A linear sweep through this
# produces plausible-looking nonsense, so it is carved out and rendered as
# data. Boundaries are verified in tools/probes/probe_reserved_words.py:
# the 26-entry index runs to $1313 and the word lists tile $1317..$14CE
# exactly, with no gaps or overlaps.
DATA = [
    (0x12E0, 0x1314, "letter index: 26 little-endian offsets from $11F2"),
    (0x1314, 0x14CE, "reserved-word table: per letter, a count then "
                     "10-byte entries of name[8], SY, OP"),
]
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def emit_data(data: bytes, lo: int, hi: int, note: str,
              base: int = 0, rel: dict[int, str] | None = None) -> list[str]:
    rel = rel or {}
    out = [f"  ---- data ${lo:04X}..${hi:04X}: {note}"]
    if "letter index" in note:
        for i in range(26):
            a = lo + 2 * i
            p = int.from_bytes(data[a:a + 2], "little")
            out.append(f"  {a:04X} {data[a]:02x} {data[a+1]:02x}"
                       f"     .word ${p:04X}"
                       f"   ; {LETTERS[i]} -> ${base + p:04X}"
                       f"{'  [' + rel[a] + ']' if a in rel else ''}")
        return out
    if "reserved-word" in note:
        a = 0x1317                      # first list; $1314..$1316 is the
        while a < hi:                   # shared empty-letter slot
            n = data[a]
            out.append(f"  {a:04X} {n:02x}        .byte {n}"
                       f"        ; count")
            a += 1
            for _ in range(n):
                nm = data[a:a + 8].decode("ascii", "replace")
                out.append(f"  {a:04X} {'':<9} .ascii {nm!r}"
                           f"  .byte ${data[a+8]:02X},${data[a+9]:02X}"
                           f"   ; {nm.strip()}  SY=${data[a+8]:02X} "
                           f"OP=${data[a+9]:02X}")
                a += 10
        return out
    for a in range(lo, hi, 8):
        row = data[a:min(a + 8, hi)]
        out.append(f"  {a:04X} " + " ".join(f"{b:02x}" for b in row))
    return out


def emit_reloc(data: bytes, p) -> list[str]:
    """Render the relocation area and attribute table (1.3 manual IV-35..37).

    Read from JTAB downward. The tables are dumped in that order too, so the
    listing runs backwards through memory here -- which is how the loader
    reads it.
    """
    out = ["",
           f"  ---- attribute table and relocation area "
           f"${p.content_end:04X}..${p.jtab + 2:04X}"]
    w = int.from_bytes(data[p.jtab:p.jtab + 2], "little")
    out.append(f"  {p.jtab:04X} .word ${w:04X}   ; PROCEDURE NUMBER = "
               f"{data[p.jtab]} (0 marks native), RELOCSEG = {data[p.jtab+1]}")
    v = int.from_bytes(data[p.jtab - 2:p.jtab], "little")
    out.append(f"  {p.jtab-2:04X} .word ${v:04X}   ; ENTER IC, self-relative "
               f"-> ${p.jtab - 2 - v:04X}")
    a = p.jtab - 4
    for kind in RELOC_KINDS:
        n = int.from_bytes(data[a:a + 2], "little")
        out.append(f"  {a:04X} .word ${n:04X}   ; {kind}-relative "
                   f"relocation table: {n} entr{'y' if n == 1 else 'ies'}")
        for k in range(n):
            at = a - 2 - 2 * k
            val = int.from_bytes(data[at:at + 2], "little")
            out.append(f"  {at:04X} .word ${val:04X}   ;   fix up "
                       f"${at - val:04X}")
        a -= 2 + 2 * n
    return out


def main() -> None:
    img = ROOT / "evidence" / "disks" / \
        "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk"
    d = PascalDisk.from_file(img)
    e = d.find("SYSTEM.COMPILER")
    cf = CodeFile(d.read_blocks(e.first_block, e.blocks))

    lines = ["Apple Pascal 1.3 SYSTEM.COMPILER -- native 6502 procedures",
             f"source image : {img.name}",
             "",
             "Disassembled by tools/a2pascal/m6502.py. Addresses are offsets",
             "within the PASCALCO segment, not absolute memory addresses: the",
             "segment is relocated at load time. Every word the loader has to",
             "fix up is named by the procedure's own relocation tables, and is",
             "marked [reloc: kind] below.",
             "VERIFIED BINARY FACT for the bytes; the naming is finding 19,",
             "the relocation tables are finding 44.",
             ""]

    total = clean = 0
    for seg in cf.segments:
        for p in seg.native_procedures:
            total += 1
            name = NAMES.get(p.number, f"proc {p.number}")
            end = p.content_end
            size = end - p.enter_ic
            # Word offset -> which table names it, for inline annotation.
            rel = {t: f"reloc: {kind}" for kind in RELOC_KINDS
                   for t in p.reloc[kind]}
            # Sweep code, skipping any carved-out data region.
            regions, a = [], p.enter_ic
            for lo, hi, note in DATA:
                if p.enter_ic <= lo < end:
                    if a < lo:
                        regions.append(("code", a, lo, ""))
                    regions.append(("data", lo, hi, note))
                    a = hi
            if a < end:
                regions.append(("code", a, end, ""))

            insns, exact, bad = [], True, []
            for kind, lo, hi, _n in regions:
                if kind == "code":
                    ii, ok = disassemble(seg.data, lo, hi)
                    insns += ii
                    exact = exact and ok
                    bad += [i for i in ii if i.mnemonic == "???"]
            if exact and not bad:
                clean += 1
            targets = {i.target for i in insns if i.target is not None}
            # A JMP whose operand the procedure-relative table names is a
            # jump to enter_ic + operand, not to the operand itself, so it
            # needs a label there.
            targets |= {p.enter_ic + (i.operand or 0) for i in insns
                        if i.mode in (ABS, IND) and i.addr + 1 in rel}

            lines += [
                "=" * 68,
                f"{seg.name}.{p.number}  {name}",
                f"  code + data ${p.enter_ic:04X}..${end:04X}  ({size} bytes, "
                f"{len(insns)} instructions)",
                f"  relocation area ${end:04X}..${p.jtab - 2:04X}, "
                f"attribute table ${p.jtab - 2:04X}..${p.jtab + 2:04X}",
                f"  sweep lands exactly on end: {'yes' if exact else 'NO'}"
                f"   undecodable bytes: {len(bad)}",
                "=" * 68, ""]
            by_addr = {i.addr: i for i in insns}
            for kind, lo, hi, note in regions:
                if kind == "data":
                    lines.append("")
                    lines += emit_data(seg.data, lo, hi, note,
                                       p.enter_ic, rel)
                    lines.append("")
                    continue
                a = lo
                while a < hi:
                    i = by_addr[a]
                    label = f"L{i.addr:04X}:" if i.addr in targets else ""
                    raw = " ".join(f"{b:02x}" for b in i.raw)
                    note = ""
                    if i.mode in (ABS, ABX, ABY, IND) and i.addr + 1 in rel:
                        # Only a bare absolute operand names a location on
                        # its own; an indexed one is a base, and the address
                        # it forms depends on the index register.
                        note = (f"   ; [{rel[i.addr + 1]}] -> "
                                f"${p.enter_ic + (i.operand or 0):04X}"
                                if i.mode in (ABS, IND) else
                                f"   ; [{rel[i.addr + 1]}] base = "
                                f"proc+${i.operand or 0:04X}, then indexed")
                    lines.append(
                        f"  {i.addr:04X} {raw:<9} {label:<7} {i.text}{note}")
                    a += i.length
            lines += emit_reloc(seg.data, p)
            lines.append("")

    OUT.mkdir(parents=True, exist_ok=True)
    f = OUT / "PASCALCO-1.3-native.asm.txt"
    f.write_text("\n".join(lines))
    print(f"[1.3] {clean}/{total} native procedures disassembled cleanly "
          f"-> {f.name}")


if __name__ == "__main__":
    main()
