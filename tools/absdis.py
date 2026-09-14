"""Turn an absolute 6502 image into Apple Assembler source, by tracing.

    python tools/absdis.py HINTS [--report] [--out-dir DIR]

For the files Apple built with SYSTEM.ASSMBLER in `.ABSOLUTE` mode and then
copied block for block into a data file -- FORMATTER.DATA's three pieces
(finding 275) and 128K.APPLE (finding 279). An absolute codefile carries no
relocation, so the byte compare cannot tell a label from a constant or code
from `.BYTE`: what it can check is that the source assembles to Apple's
bytes. Everything the trace decides beyond that is reading, not evidence.

The hints file, one directive to a line, `;` comments:

    image    PATH                      the shipped file, relative to the repo
    image    DISK FILE                 or FILE on the evidence disk DISK
                                       (APPLE1, APPLE2, APPLE3)
    piece    NAME                      starts a piece: one .PROC, one codefile
    region   OFFSET LENGTH ORG         file bytes that load at ORG (hex)
    entry    ADDR [ADDR...]            code starts inside the current piece
    calls    PIECE [LO HI [FLO FHI]]   every JSR/JMP in PIECE's trace, from
                                       FLO-FHI, that lands in LO-HI of the
                                       current piece is an entry
    foreign  FLO FHI LO HI             a reference from FLO-FHI to LO-HI is
                                       not this piece's (the other bank)
    words    PIECE ADDR COUNT [LO HI]  COUNT words at ADDR in PIECE; each in
                                       LO-HI is a code address here
    wordsm1  PIECE ADDR COUNT          the same, each the address minus one
                                       (pushed for an RTS)
    data     ADDR COUNT                bytes never to be traced as code
    out      FILENAME                  where the current piece's source goes
    header   TEXT                      a comment line for the source's head

A piece's regions are assembled in order into one `.PROC`, a `.ORG` at each.
An operand that lands in a region of its own piece becomes a label
(`L<addr>`, or `L<head>+k` inside an instruction); anything else stays a
hex constant, since another piece's labels are another assembly's.

Things Apple's assembler forces, each learnt on FORMATTER.DATA:

  * an absolute-mode operand below $100 whose opcode has a zero-page twin
    cannot be written as a mnemonic (the assembler would pick zero page), so
    that one instruction is emitted as `.BYTE`;
  * hex constants begin with a digit (`0D000`), `@` is indirect;
  * a line stays within 80 columns (error 54).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a2pascal.m6502 import (decode, IMP, ACC, IMM, ZP, ZPX, ZPY, IZX, IZY,
                            ABS, ABX, ABY, IND, REL)

ROOT = Path(__file__).resolve().parent.parent
ZP_TWIN_ABX = {"JSR", "JMP"}          # ABS/ABX mnemonics with no zero page
STOPS = set()     # (piece, addr): a trace ran into a bad opcode or a region end


class Piece:
    def __init__(self, name):
        self.name = name
        self.regions = []             # (offset, length, org)
        self.entries = []
        self.tables = []              # (kind, piece, addr, count)
        self.data = []                # (addr, count)
        self.calls = []               # (piece, to lo, to hi, from lo, from hi)
        self.foreign = []             # (from lo, from hi, to lo, to hi)
        self.out = None
        self.header = []

    def region_of(self, addr):
        for r in self.regions:
            if r[2] <= addr < r[2] + r[1]:
                return r
        return None


def parse(path):
    pieces, image, cur = {}, None, None
    for n, line in enumerate(Path(path).read_text().splitlines(), 1):
        line = line.split(";")[0].strip()
        if not line:
            continue
        word, *args = line.split(None, 1)
        rest = args[0] if args else ""
        f = rest.split()
        if word == "image" and len(f) == 2:
            from a2pascal.disk import PascalDisk
            disk, = [p for p in (ROOT / "evidence" / "disks").glob("*.dsk")
                     if f"{f[0]}_" in p.name]
            e = PascalDisk.from_file(disk).find(f[1])
            image = bytes(PascalDisk.from_file(disk).read_blocks(
                e.first_block, e.blocks))
        elif word == "image":
            image = (ROOT / rest).read_bytes()
        elif word == "piece":
            cur = pieces[f[0]] = Piece(f[0])
        elif word == "region":
            cur.regions.append((int(f[0], 16), int(f[1], 16), int(f[2], 16)))
        elif word == "entry":
            cur.entries += [int(x, 16) for x in f]
        elif word in ("words", "wordsm1"):
            lo, hi = (int(f[3], 16), int(f[4], 16)) if len(f) > 3 else (0, 0xFFFF)
            cur.tables.append((word, f[0], int(f[1], 16), int(f[2]), lo, hi))
        elif word == "calls":
            g = [int(x, 16) for x in f[1:]] + [0, 0xFFFF, 0, 0xFFFF][len(f) - 1:]
            cur.calls.append((f[0], *g[:4]))
        elif word == "foreign":
            cur.foreign.append(tuple(int(x, 16) for x in f))
        elif word == "data":
            cur.data.append((int(f[0], 16), int(f[1], 16)))
        elif word == "out":
            cur.out = f[0]
        elif word == "header":
            cur.header.append(rest)
        else:
            raise SystemExit(f"{path}:{n}: unknown directive {word!r}")
    return image, pieces


def byte_at(image, piece, addr):
    r = piece.region_of(addr)
    if r is None:
        raise SystemExit(f"${addr:04X} is not in piece {piece.name}")
    return image[r[0] + addr - r[2]]


def owns(piece, frm, target):
    """Is a reference from `frm` to `target` one of this piece's labels?"""
    if not piece.region_of(target):
        return False
    return not any(fl <= frm <= fh and tl <= target <= th
                   for fl, fh, tl, th in piece.foreign)


def trace_one(image, piece, extra):
    todo = list(piece.entries) + list(extra)
    for kind, pname, addr, count, lo, hi in piece.tables:
        src = pieces_g[pname]
        for k in range(count):
            v = (byte_at(image, src, addr + 2 * k)
                 | byte_at(image, src, addr + 2 * k + 1) << 8)
            v += 1 if kind == "wordsm1" else 0
            if lo <= v <= hi:
                todo.append(v)
    nocode = set()
    for a, c in piece.data:
        nocode.update(range(a, a + c))
    code, refs = {}, set()
    while todo:
        a = todo.pop()
        while piece.region_of(a) and a not in code and a not in nocode:
            r = piece.region_of(a)
            buf = image[r[0]:r[0] + r[1]]
            ins = decode(buf, a - r[2])
            if ins.mnemonic == "???" or a + ins.length > r[2] + r[1]:
                STOPS.add((piece.name, a))
                break
            ins.addr = a
            code[a] = ins
            if ins.mode == REL:
                ins.target = a + 2 + ins.operand
                if piece.region_of(ins.target):
                    refs.add(ins.target)
                    todo.append(ins.target)
            elif ins.mode in (ABS, ABX, ABY, IND):
                if owns(piece, a, ins.operand):
                    refs.add(ins.operand)
                    if ins.mnemonic in ("JSR", "JMP") and ins.mode == ABS:
                        todo.append(ins.operand)
            if ins.mnemonic in ("RTS", "RTI", "BRK", "JMP"):
                break
            a += ins.length
    for kind, pname, addr, count, lo, hi in piece.tables:
        if pname == piece.name:
            refs.add(addr)
    return code, refs


def trace_all(image, pieces):
    """Trace every piece, feeding each the calls other pieces make into it,
    until nothing new turns up."""
    global pieces_g
    pieces_g = pieces
    extra = {n: set() for n in pieces}
    while True:
        result = {n: trace_one(image, p, extra[n]) for n, p in pieces.items()}
        grew = False
        for n, p in pieces.items():
            for pname, tl, th, fl, fh in p.calls:
                for i in result[pname][0].values():
                    if (i.mnemonic in ("JSR", "JMP") and i.mode == ABS
                            and tl <= i.operand <= th and fl <= i.addr <= fh
                            and p.region_of(i.operand)
                            and i.operand not in extra[n]):
                        extra[n].add(i.operand)
                        grew = True
        if not grew:
            return result


def hx(v, w):
    s = f"{v:0{w}X}"
    return s if s[0].isdigit() else "0" + s


def generate(image, piece, traced):
    code, refs = traced[piece.name]
    refs = {r for r in refs if piece.region_of(r)}
    wordtab = {}
    for kind, pname, addr, count, lo, hi in piece.tables:
        if pname == piece.name:
            for k in range(count):
                wordtab[addr + 2 * k] = kind

    # Pass 1: the linear walk the source will make. An instruction the trace
    # found is taken where the walk meets it, so where Apple's code jumps
    # into the middle of another instruction (the BIT-skip trick) the walk
    # keeps the outer one and the inner address becomes L<head>+k.
    items = []                        # (start, length, kind)
    for off, length, org in piece.regions:
        a, hi = org, org + length
        items.append((org, 0, "org"))
        while a < hi:
            if a in code:
                items.append((a, code[a].length, "code"))
                a += code[a].length
            elif a in wordtab and a + 1 < hi:
                items.append((a, 2, "word"))
                a += 2
            else:
                b = a + 1
                while (b < hi and b not in code and b not in refs
                       and b not in wordtab and b - a < 8):
                    b += 1
                items.append((a, b - a, "bytes"))
                a = b
    starts = {st: ln for st, ln, kind in items if kind != "org"}
    inner, labels = {}, set()
    heads = sorted(starts)
    import bisect
    for r in refs:
        if r in starts:
            labels.add(r)
        else:
            h = heads[bisect.bisect_right(heads, r) - 1]
            inner[r] = (h, r - h)
            labels.add(h)

    def name(v, frm=None):
        if frm is not None and not owns(piece, frm, v):
            return None
        if v in inner:
            h, k = inner[v]
            return f"L{h:04X}+{k}"
        return f"L{v:04X}" if v in labels else None

    def operand(i):
        m, v = i.mode, i.operand
        if m == IMP:
            return ""
        if m == ACC:
            return "A"
        if m == IMM:
            return "#" + hx(v, 2)
        if m == REL:
            return name(i.target) or hx(i.target, 4)
        if m in (ZP, ZPX, ZPY, IZX, IZY):
            s = hx(v, 2)
            return {ZP: s, ZPX: s + ",X", ZPY: s + ",Y",
                    IZX: "@" + s + ",X", IZY: "@" + s + ",Y"}[m]
        s = name(v, i.addr) or hx(v, 4)
        return {ABS: s, ABX: s + ",X", ABY: s + ",Y", IND: "@" + s}[m]

    def forced_byte(i):
        """Absolute mode, operand below $100, and a zero-page twin exists;
        or a branch out of the piece, which the assembler calls too far."""
        if i.mode == REL:
            return not piece.region_of(i.target)
        if i.mode not in (ABS, ABX, ABY) or i.operand >= 0x100:
            return False
        if i.mode == ABY:
            return i.mnemonic in ("LDX", "STX")
        return i.mnemonic not in ZP_TWIN_ABX

    lines = [f"; {h}" if h else ";" for h in piece.header]
    lines += ["        .ABSOLUTE", f"        .PROC   {piece.name}"]
    stats = {"code": 0, "bytes": 0, "forced": 0}
    for a, length, kind in items:
        if kind == "org":
            lines.append(f"        .ORG    {hx(a, 4)}")
            off = piece.region_of(a)
            base = off[0] - off[2]
            continue
        lab = f"L{a:04X}" if a in labels else ""
        if kind == "code":
            i = code[a]
            if forced_byte(i):
                vals = ",".join(hx(x, 2) for x in i.raw)
                what = (f"{hx(i.target, 4)}, out of the piece"
                        if i.mode == REL else f"{hx(i.operand, 4)}, absolute")
                lines.append(f"{lab:<8}.BYTE {vals:<20}; {i.mnemonic} {what}")
                stats["forced"] += 1
            else:
                lines.append(f"{lab:<8}{i.mnemonic:<4} {operand(i)}".rstrip())
            stats["code"] += length
        elif kind == "word":
            v = image[base + a] | image[base + a + 1] << 8
            target = v + (1 if wordtab[a] == "wordsm1" else 0)
            s = name(target) or hx(target, 4)
            if wordtab[a] == "wordsm1":
                s += "-1"
            lines.append(f"{lab:<8}.WORD {s}")
        else:
            vals = ",".join(hx(x, 2) for x in image[base + a:base + a + length])
            lines.append(f"{lab:<8}.BYTE {vals}")
            stats["bytes"] += length
    lines.append("        .END")
    long = [n for n, l in enumerate(lines, 1) if len(l) > 80]
    if long:
        raise SystemExit(f"{piece.name}: lines over 80 columns: {long[:5]}")
    return lines, code, stats


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("hints")
    ap.add_argument("--report", action="store_true",
                    help="list the untraced runs instead of writing source")
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args()
    image, pieces = parse(args.hints)
    traced = trace_all(image, pieces)
    for piece in pieces.values():
        lines, code, st = generate(image, piece, traced)
        total = sum(r[1] for r in piece.regions)
        print(f"{piece.name}: {total} bytes, {st['code']} traced as code, "
              f"{st['bytes']} as .BYTE, {st['forced']} forced absolute, "
              f"{len(lines)} lines")
        if args.report:
            for pn, at in sorted(STOPS):
                if pn == piece.name:
                    print(f"   trace stopped at ${at:04X} (bad opcode or region end)")
            covered = set()
            for a, i in traced[piece.name][0].items():
                covered.update(range(a, a + i.length))
            for off, length, org in piece.regions:
                a = org
                while a < org + length:
                    if a in covered:
                        a += 1
                        continue
                    b = a
                    while b < org + length and b not in covered:
                        b += 1
                    if b - a >= 16:
                        print(f"   untraced ${a:04X}-${b - 1:04X} ({b - a})")
                    a = b
        elif piece.out:
            out = Path(args.out_dir or ROOT) / piece.out
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text("\n".join(lines) + "\n", newline="\n")
            print(f"   -> {out}")


if __name__ == "__main__":
    main()
