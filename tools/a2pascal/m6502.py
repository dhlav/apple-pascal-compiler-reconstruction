"""A plain NMOS 6502 disassembler.

Needed because Apple Pascal 1.3 hand-coded IDSEARCH and TREESEARCH in
assembly and the UCSD Linker merged them into SYSTEM.COMPILER's PASCALCO
segment, where they sit as native procedures 2 and 3 (finding 6a). Nothing
else in either compiler is native.

Undocumented opcodes are not decoded: this code was produced by Apple's
6502 assembler from source, so any byte outside the legal set means the
disassembly has lost sync, and saying so is more useful than inventing an
instruction. That is the same discipline the p-code decoder uses.
"""

from __future__ import annotations

from dataclasses import dataclass

# addressing modes, with the total instruction length in bytes
IMP, ACC, IMM, ZP, ZPX, ZPY, IZX, IZY, ABS, ABX, ABY, IND, REL = range(13)

LENGTH = {IMP: 1, ACC: 1, IMM: 2, ZP: 2, ZPX: 2, ZPY: 2, IZX: 2, IZY: 2,
          ABS: 3, ABX: 3, ABY: 3, IND: 3, REL: 2}

_ = None
# opcode table, 16 per row, indexed by opcode
TABLE: list[tuple[str, int] | None] = [
    # 0x
    ("BRK", IMP), ("ORA", IZX), _, _, _, ("ORA", ZP), ("ASL", ZP), _,
    ("PHP", IMP), ("ORA", IMM), ("ASL", ACC), _, _, ("ORA", ABS), ("ASL", ABS), _,
    # 1x
    ("BPL", REL), ("ORA", IZY), _, _, _, ("ORA", ZPX), ("ASL", ZPX), _,
    ("CLC", IMP), ("ORA", ABY), _, _, _, ("ORA", ABX), ("ASL", ABX), _,
    # 2x
    ("JSR", ABS), ("AND", IZX), _, _, ("BIT", ZP), ("AND", ZP), ("ROL", ZP), _,
    ("PLP", IMP), ("AND", IMM), ("ROL", ACC), _, ("BIT", ABS), ("AND", ABS), ("ROL", ABS), _,
    # 3x
    ("BMI", REL), ("AND", IZY), _, _, _, ("AND", ZPX), ("ROL", ZPX), _,
    ("SEC", IMP), ("AND", ABY), _, _, _, ("AND", ABX), ("ROL", ABX), _,
    # 4x
    ("RTI", IMP), ("EOR", IZX), _, _, _, ("EOR", ZP), ("LSR", ZP), _,
    ("PHA", IMP), ("EOR", IMM), ("LSR", ACC), _, ("JMP", ABS), ("EOR", ABS), ("LSR", ABS), _,
    # 5x
    ("BVC", REL), ("EOR", IZY), _, _, _, ("EOR", ZPX), ("LSR", ZPX), _,
    ("CLI", IMP), ("EOR", ABY), _, _, _, ("EOR", ABX), ("LSR", ABX), _,
    # 6x
    ("RTS", IMP), ("ADC", IZX), _, _, _, ("ADC", ZP), ("ROR", ZP), _,
    ("PLA", IMP), ("ADC", IMM), ("ROR", ACC), _, ("JMP", IND), ("ADC", ABS), ("ROR", ABS), _,
    # 7x
    ("BVS", REL), ("ADC", IZY), _, _, _, ("ADC", ZPX), ("ROR", ZPX), _,
    ("SEI", IMP), ("ADC", ABY), _, _, _, ("ADC", ABX), ("ROR", ABX), _,
    # 8x
    _, ("STA", IZX), _, _, ("STY", ZP), ("STA", ZP), ("STX", ZP), _,
    ("DEY", IMP), _, ("TXA", IMP), _, ("STY", ABS), ("STA", ABS), ("STX", ABS), _,
    # 9x
    ("BCC", REL), ("STA", IZY), _, _, ("STY", ZPX), ("STA", ZPX), ("STX", ZPY), _,
    ("TYA", IMP), ("STA", ABY), ("TXS", IMP), _, _, ("STA", ABX), _, _,
    # Ax
    ("LDY", IMM), ("LDA", IZX), ("LDX", IMM), _, ("LDY", ZP), ("LDA", ZP), ("LDX", ZP), _,
    ("TAY", IMP), ("LDA", IMM), ("TAX", IMP), _, ("LDY", ABS), ("LDA", ABS), ("LDX", ABS), _,
    # Bx
    ("BCS", REL), ("LDA", IZY), _, _, ("LDY", ZPX), ("LDA", ZPX), ("LDX", ZPY), _,
    ("CLV", IMP), ("LDA", ABY), ("TSX", IMP), _, ("LDY", ABX), ("LDA", ABX), ("LDX", ABY), _,
    # Cx
    ("CPY", IMM), ("CMP", IZX), _, _, ("CPY", ZP), ("CMP", ZP), ("DEC", ZP), _,
    ("INY", IMP), ("CMP", IMM), ("DEX", IMP), _, ("CPY", ABS), ("CMP", ABS), ("DEC", ABS), _,
    # Dx
    ("BNE", REL), ("CMP", IZY), _, _, _, ("CMP", ZPX), ("DEC", ZPX), _,
    ("CLD", IMP), ("CMP", ABY), _, _, _, ("CMP", ABX), ("DEC", ABX), _,
    # Ex
    ("CPX", IMM), ("SBC", IZX), _, _, ("CPX", ZP), ("SBC", ZP), ("INC", ZP), _,
    ("INX", IMP), ("SBC", IMM), ("NOP", IMP), _, ("CPX", ABS), ("SBC", ABS), ("INC", ABS), _,
    # Fx
    ("BEQ", REL), ("SBC", IZY), _, _, _, ("SBC", ZPX), ("INC", ZPX), _,
    ("SED", IMP), ("SBC", ABY), _, _, _, ("SBC", ABX), ("INC", ABX), _,
]
assert len(TABLE) == 256

# zero page as the p-machine uses it, from Common.s of John Brooks' 1.4
# interpreter (finding 17). A native procedure runs inside the interpreter,
# so these are the names its author was writing against.
ZP_NAMES = {
    0x50: "BASE", 0x51: "BASE+1", 0x52: "MP", 0x53: "MP+1",
    0x54: "JTAB", 0x55: "JTAB+1", 0x56: "SEG", 0x57: "SEG+1",
    0x58: "IPC", 0x59: "IPC+1", 0x5A: "NP", 0x5B: "NP+1",
    0x5C: "KP", 0x5D: "KP+1", 0x5E: "StrP", 0x5F: "StrP+1",
    0x60: "CodeP", 0x61: "CodeP+1", 0x62: "CodeLow", 0x63: "CodeLow+1",
    0x68: "BigParam", 0x69: "BigParam+1",
    0x6C: "PrevMP", 0x6D: "PrevMP+1", 0x6E: "VarPtr", 0x6F: "VarPtr+1",
    0x70: "SPTemp", 0x71: "SPTemp+1", 0x72: "SrcPtr", 0x73: "SrcPtr+1",
    0x74: "DstPtr", 0x75: "DstPtr+1", 0x76: "CmpType",
}


@dataclass
class Insn6502:
    addr: int
    length: int
    opcode: int
    mnemonic: str
    mode: int
    operand: int | None
    text: str
    target: int | None = None       # branch/jump destination
    raw: bytes = b""


def _zp(a: int) -> str:
    n = ZP_NAMES.get(a)
    return f"${a:02X}" + (f" [{n}]" if n else "")


def decode(code: bytes, addr: int, base: int = 0) -> Insn6502:
    """Decode one instruction. `base` is the address the segment loads at,
    used only to render absolute operands; pass 0 to keep them raw."""
    op = code[addr]
    ent = TABLE[op]
    if ent is None:
        return Insn6502(addr, 1, op, "???", IMP, None,
                        f".byte ${op:02X}", raw=code[addr:addr + 1])
    mnem, mode = ent
    n = LENGTH[mode]
    if addr + n > len(code):
        return Insn6502(addr, 1, op, "???", IMP, None,
                        f".byte ${op:02X}", raw=code[addr:addr + 1])

    val = target = None
    if mode in (IMM, ZP, ZPX, ZPY, IZX, IZY):
        val = code[addr + 1]
    elif mode in (ABS, ABX, ABY, IND):
        val = code[addr + 1] | (code[addr + 2] << 8)
    elif mode == REL:
        d = code[addr + 1]
        val = d - 256 if d > 127 else d
        target = addr + 2 + val

    arg = {
        IMP: "", ACC: "A",
        IMM: f"#${val:02X}" if val is not None else "",
        ZP: _zp(val) if val is not None else "",
        ZPX: f"{_zp(val)},X" if val is not None else "",
        ZPY: f"{_zp(val)},Y" if val is not None else "",
        IZX: f"({_zp(val)},X)" if val is not None else "",
        IZY: f"({_zp(val)}),Y" if val is not None else "",
        ABS: f"${val:04X}" if val is not None else "",
        ABX: f"${val:04X},X" if val is not None else "",
        ABY: f"${val:04X},Y" if val is not None else "",
        IND: f"(${val:04X})" if val is not None else "",
        REL: f"${target:04X}" if target is not None else "",
    }[mode]

    if mode in (ABS, IND) and mnem in ("JMP", "JSR"):
        target = val

    text = f"{mnem} {arg}".rstrip()
    return Insn6502(addr, n, op, mnem, mode, val, text, target,
                    code[addr:addr + n])


def disassemble(code: bytes, start: int, end: int) -> tuple[list[Insn6502], bool]:
    """Linear sweep. Returns (instructions, landed_exactly_on_end)."""
    out, p = [], start
    while p < end:
        ins = decode(code, p)
        out.append(ins)
        p += ins.length
    return out, p == end
