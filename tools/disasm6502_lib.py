"""Disassemble the native 6502 procedures of SYSTEM.LIBRARY.

Three of the six library units are part 6502: TURTLEGRAPHICS (seven
procedures), LONGINTIO (one) and APPLESTUFF (six). Those fourteen are all
the native code in the library, and they are what the Pascal reconstruction
cannot reach -- the linker puts them in, so they belong to the assembler
tier (finding 44e), exactly as PASCALCO's IDSEARCH and TREESEARCH do.

Writes analysis/native/LIBRARY-1.3-native.asm.txt.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile, RELOC_KINDS
from a2pascal.m6502 import disassemble, ABS, ABX, ABY, IND
from disasm6502 import emit_reloc

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "analysis" / "native"
IMG = ROOT / "evidence" / "disks" / \
    "Apple II Pascal 1.3 APPLE1_ 680-0283-A.dsk"

# The interface fixes every public name and number (finding 92a); the
# privates are numbered by declaration order and named from what they do.
NAMES = {
    "TURTLEGR": {15: "SCREENBIT", 16: "DRAWBLOCK", 20: "MOVEABS",
                 21: "MOVEREL", 22: "FILLIT", 30: "private 30",
                 31: "private 31"},
    "LONGINTI": {4: "the long-integer engine"},
    "APPLESTU": {2: "PADDLE", 3: "BUTTON", 4: "TTLOUT", 6: "RANDOM",
                 7: "RANDOMIZE", 8: "NOTE"},
}


# Data embedded in the middle of a procedure. A linear sweep through this
# decodes to nonsense, so it is carved out and dumped as bytes. Each region
# is (segment, procedure number, lo, hi, note), in segment offsets.
DATA = [
    ("APPLESTU", 8, 0x0159, 0x01C2,
     "3 bytes of scratch, then the pitch table: 2 bytes per semitone"),
    ("APPLESTU", 6, 0x0225, 0x0229, "the random seed, 4 bytes"),
    ("TURTLEGR", 30, 0x0BB4, 0x0BBC,
     "hi-res colour masks, one per SCREENCOLOR from 5 up"),
    ("TURTLEGR", 30, 0x0DE3, 0x0DEC, "bit masks and two constants"),
    ("TURTLEGR", 16, 0x13E7, 0x1408, "DRAWBLOCK's mode tables"),
    ("LONGINTI", 4, 0x043B, 0x0453,
     "six four-byte patches, one per relational operator"),
    ("LONGINTI", 4, 0x02C2, 0x02D8,
     "the entry jump table: eleven procedure-relative words"),
    ("LONGINTI", 4, 0x066E, 0x0675,
     "powers of two in BCD: 1 2 4 8 16 32 64"),
]


def emit_bytes(data: bytes, lo: int, hi: int) -> list[str]:
    out = []
    for a in range(lo, hi, 8):
        row = data[a:min(a + 8, hi)]
        out.append(f"  {a:04X} " + " ".join(f"{b:02x}" for b in row))
    return out


def main() -> None:
    d = PascalDisk.from_file(IMG)
    e = d.find("SYSTEM.LIBRARY")
    cf = CodeFile(d.read_blocks(e.first_block, e.blocks))

    lines = ["Apple Pascal 1.3 SYSTEM.LIBRARY -- native 6502 procedures",
             f"source image : {IMG.name}",
             "",
             "Disassembled by tools/a2pascal/m6502.py. Addresses are offsets",
             "within the unit's code segment, not absolute memory addresses.",
             "Every word the loader fixes up is named by the procedure's own",
             "relocation tables and marked [reloc: kind] below; reproducing",
             "those tables is the acceptance test for reassembled source",
             "(finding 44e).",
             ""]

    total = clean = 0
    for seg in cf.segments:
        nat = list(seg.native_procedures)
        if not nat:
            continue
        names = NAMES.get(seg.name.strip(), {})
        lines += ["#" * 68,
                  f"# {seg.name.strip()}  segment {seg.seg_num}: "
                  f"{len(nat)} native of {len(seg.procedures)} procedures",
                  "#" * 68, ""]
        for p in sorted(nat, key=lambda q: q.enter_ic):
            total += 1
            name = names.get(p.number, f"proc {p.number}")
            end = p.content_end
            rel = {t: f"reloc: {kind}" for kind in RELOC_KINDS
                   for t in p.reloc[kind]}
            regions, a = [], p.enter_ic
            for sname, num, lo, hi, note in sorted(DATA, key=lambda r: r[2]):
                if sname == seg.name.strip() and num == p.number:
                    if a < lo:
                        regions.append(("code", a, lo, ""))
                    regions.append(("data", lo, hi, note))
                    a = hi
            if a < end:
                regions.append(("code", a, end, ""))

            insns, exact = [], True
            for kind, lo, hi, _n in regions:
                if kind != "code":
                    continue
                ii, ok = disassemble(seg.data, lo, hi)
                insns += ii
                exact = exact and ok
            bad = [i for i in insns if i.mnemonic == "???"]
            if exact and not bad:
                clean += 1
            targets = {i.target for i in insns if i.target is not None}
            targets |= {p.enter_ic + (i.operand or 0) for i in insns
                        if i.mode in (ABS, IND) and i.addr + 1 in rel}

            counts = ", ".join(f"{k} {len(p.reloc[k])}" for k in RELOC_KINDS
                               if p.reloc[k])
            lines += [
                "=" * 68,
                f"{seg.name.strip()}.{p.number}  {name}",
                f"  code ${p.enter_ic:04X}..${end:04X}  "
                f"({end - p.enter_ic} bytes, {len(insns)} instructions)",
                f"  relocation area ${end:04X}..${p.jtab - 2:04X}"
                f"   [{counts or 'no entries'}]",
                f"  sweep lands exactly on end: {'yes' if exact else 'NO'}"
                f"   undecodable bytes: {len(bad)}",
                "=" * 68, ""]
            if not exact or bad:
                # A sweep that does not land on the end has lost sync, and
                # inventing instructions past that point is worse than
                # saying so. Dump the raw bytes instead.
                lines += ["  ---- linear sweep failed; raw bytes follow",
                          *emit_bytes(seg.data, p.enter_ic, end)]
            else:
                by_addr = {i.addr: i for i in insns}
                for kind, lo, hi, note in regions:
                    if kind == "data":
                        lines += ["",
                                  f"  ---- data ${lo:04X}..${hi:04X}: {note}",
                                  *emit_bytes(seg.data, lo, hi), ""]
                        continue
                    a = lo
                    while a < hi:
                        i = by_addr[a]
                        a += i.length
                        label = f"L{i.addr:04X}:" if i.addr in targets else ""
                        raw = " ".join(f"{b:02x}" for b in i.raw)
                        mark = ""
                        if (i.mode in (ABS, ABX, ABY, IND)
                                and i.addr + 1 in rel):
                            mark = (f"   ; [{rel[i.addr + 1]}] -> "
                                    f"${p.enter_ic + (i.operand or 0):04X}"
                                    if i.mode in (ABS, IND) else
                                    f"   ; [{rel[i.addr + 1]}] base = "
                                    f"proc+${i.operand or 0:04X}, then indexed")
                        lines.append(f"  {i.addr:04X} {raw:<9} {label:<7} "
                                     f"{i.text}{mark}")
            lines += emit_reloc(seg.data, p)
            lines.append("")

    OUT.mkdir(parents=True, exist_ok=True)
    f = OUT / "LIBRARY-1.3-native.asm.txt"
    f.write_text("\n".join(lines))
    print(f"[1.3] {clean}/{total} library native procedures disassembled "
          f"cleanly -> {f.name}")


if __name__ == "__main__":
    main()
