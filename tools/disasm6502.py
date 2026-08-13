"""Disassemble the native 6502 procedures of SYSTEM.COMPILER.

Only Apple Pascal 1.3 has any: PASCALCO procedures 2 and 3, the hand-coded
IDSEARCH and TREESEARCH (findings 6a, 19). Writes
analysis/native/PASCALCO-1.3-native.asm.txt.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.m6502 import disassemble

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
    # Both procedures carry a block of word-sized data between their last
    # RTS and their attribute table. Not identified. UCSD stores relocation
    # lists for assembled procedures, which is the obvious guess, but the
    # values have not been made to fit that and are left as bytes rather
    # than described as something they may not be.
    (0x14CE, 0x150C, "unidentified trailing data, after the last RTS"),
    (0x1592, 0x15A0, "unidentified trailing data, after the last RTS"),
]
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def emit_data(data: bytes, lo: int, hi: int, note: str) -> list[str]:
    out = [f"  ---- data ${lo:04X}..${hi:04X}: {note}"]
    if "letter index" in note:
        for i in range(26):
            p = int.from_bytes(data[lo + 2 * i:lo + 2 * i + 2], "little")
            out.append(f"  {lo + 2 * i:04X} {data[lo + 2 * i]:02x} "
                       f"{data[lo + 2 * i + 1]:02x}     .word ${p:04X}"
                       f"   ; {LETTERS[i]} -> ${0x11F2 + p:04X}")
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
             "segment is relocated at load time, so any absolute operand below",
             "is a segment-relative reference that the loader fixes up.",
             "VERIFIED BINARY FACT for the bytes; the naming is finding 19.",
             ""]

    total = clean = 0
    for seg in cf.segments:
        for p in seg.native_procedures:
            total += 1
            name = NAMES.get(p.number, f"proc {p.number}")
            size = p.exit_ic - p.enter_ic
            # Sweep code, skipping any carved-out data region.
            regions, a = [], p.enter_ic
            for lo, hi, note in DATA:
                if p.enter_ic <= lo < p.exit_ic:
                    if a < lo:
                        regions.append(("code", a, lo, ""))
                    regions.append(("data", lo, hi, note))
                    a = hi
            if a < p.exit_ic:
                regions.append(("code", a, p.exit_ic, ""))

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

            lines += [
                "=" * 68,
                f"{seg.name}.{p.number}  {name}",
                f"  bytes ${p.enter_ic:04X}..${p.exit_ic:04X}  ({size} bytes, "
                f"{len(insns)} instructions)",
                f"  sweep lands exactly on end: {'yes' if exact else 'NO'}"
                f"   undecodable bytes: {len(bad)}",
                "=" * 68, ""]
            by_addr = {i.addr: i for i in insns}
            for kind, lo, hi, note in regions:
                if kind == "data":
                    lines.append("")
                    lines += emit_data(seg.data, lo, hi, note)
                    lines.append("")
                    continue
                a = lo
                while a < hi:
                    i = by_addr[a]
                    label = f"L{i.addr:04X}:" if i.addr in targets else ""
                    raw = " ".join(f"{b:02x}" for b in i.raw)
                    lines.append(
                        f"  {i.addr:04X} {raw:<9} {label:<7} {i.text}")
                    a += i.length
            lines.append("")

    OUT.mkdir(parents=True, exist_ok=True)
    f = OUT / "PASCALCO-1.3-native.asm.txt"
    f.write_text("\n".join(lines))
    print(f"[1.3] {clean}/{total} native procedures disassembled cleanly "
          f"-> {f.name}")


if __name__ == "__main__":
    main()
