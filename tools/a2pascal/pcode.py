"""UCSD p-machine (version II.0 / Apple Pascal) instruction decoder.

Operand encodings
    UB  unsigned byte
    SB  signed byte
    DB  "don't-care" byte (used as a small unsigned count/level)
    B   "big": one byte if < 128, otherwise ((b0 & 0x7F) << 8) | b1
    W   little-endian word

Self-relative pointers (used by jump tables and XJP) are stored as the
amount to SUBTRACT from the address of the pointer word itself.

One-byte short forms. These boundaries were verified against the binaries
with tools/probes/probe_short_form_base.py, which checks that the increment
idiom `<short load X>; SLDC 1; ADI; <long store X>` names the same variable
on both sides -- the long store's operand is unambiguous, so it pins the
short load's base:

    $00-$7F  SLDC 0..127
    $D8-$E7  SLDL 1..16
    $E8-$F7  SLDO 1..16
    $F8-$FF  SIND 0..7

All three ranges are confirmed by Hyde, "P-Source: A Guide to the Apple
Pascal System" (1983), pp.160, 168 and 184 respectively.

Note that every byte in $D0-$FF is a one-byte instruction whichever way the
ranges are drawn, so a wrong split still passes a stream-synchronisation
check. It has to be tested semantically.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

# operand kind constants
NONE, UB, SB, DB, BIG, W = "none", "ub", "sb", "db", "big", "w"

# opcode -> (mnemonic, [operand kinds], comment)
OPCODES: dict[int, tuple[str, list[str]]] = {
    0x80: ("ABI", []), 0x81: ("ABR", []), 0x82: ("ADI", []), 0x83: ("ADR", []),
    0x84: ("LAND", []), 0x85: ("DIF", []), 0x86: ("DVI", []), 0x87: ("DVR", []),
    0x88: ("CHK", []), 0x89: ("FLO", []), 0x8A: ("FLT", []), 0x8B: ("INN", []),
    0x8C: ("INT", []), 0x8D: ("LOR", []), 0x8E: ("MODI", []), 0x8F: ("MPI", []),
    0x90: ("MPR", []), 0x91: ("NGI", []), 0x92: ("NGR", []), 0x93: ("LNOT", []),
    0x94: ("SRS", []), 0x95: ("SBI", []), 0x96: ("SBR", []), 0x97: ("SGS", []),
    0x98: ("SQI", []), 0x99: ("SQR", []), 0x9A: ("STO", []), 0x9B: ("IXS", []),
    0x9C: ("UNI", []), 0x9D: ("LDE", [UB, BIG]), 0x9E: ("CSP", [UB]),
    0x9F: ("LDCN", []),
    0xA0: ("ADJ", [UB]), 0xA1: ("FJP", [SB]), 0xA2: ("INC", [BIG]),
    0xA3: ("IND", [BIG]), 0xA4: ("IXA", [BIG]), 0xA5: ("LAO", [BIG]),
    0xA6: ("LSA", ["str"]), 0xA7: ("LAE", [UB, BIG]), 0xA8: ("MOV", [BIG]),
    0xA9: ("LDO", [BIG]), 0xAA: ("SAS", [UB]), 0xAB: ("SRO", [BIG]),
    0xAC: ("XJP", ["xjp"]), 0xAD: ("RNP", [DB]), 0xAE: ("CIP", [UB]),
    0xAF: ("EQU", ["cmp"]),
    0xB0: ("GEQ", ["cmp"]), 0xB1: ("GRT", ["cmp"]), 0xB2: ("LDA", [DB, BIG]),
    0xB3: ("LDC", ["ldc"]), 0xB4: ("LEQ", ["cmp"]), 0xB5: ("LES", ["cmp"]),
    0xB6: ("LOD", [DB, BIG]), 0xB7: ("NEQ", ["cmp"]), 0xB8: ("STR", [DB, BIG]),
    0xB9: ("UJP", [SB]), 0xBA: ("LDP", []), 0xBB: ("STP", []),
    0xBC: ("LDM", [UB]), 0xBD: ("STM", [UB]), 0xBE: ("LDB", []),
    0xBF: ("STB", []),
    0xC0: ("IXP", [UB, UB]), 0xC1: ("RBP", [DB]), 0xC2: ("CBP", [UB]),
    0xC3: ("EQUI", []), 0xC4: ("GEQI", []), 0xC5: ("GRTI", []),
    0xC6: ("LLA", [BIG]), 0xC7: ("LDCI", [W]), 0xC8: ("LEQI", []),
    0xC9: ("LESI", []), 0xCA: ("LDL", [BIG]), 0xCB: ("NEQI", []),
    0xCC: ("STL", [BIG]), 0xCD: ("CXP", [UB, UB]), 0xCE: ("CLP", [UB]),
    0xCF: ("CGP", [UB]),
    # $D0-$D7. Filled in from the XFRTBL dispatch table of John Brooks' Apple
    # Pascal 1.4 interpreter (Interp.s), which names every slot in $80-$FF.
    # Only $D0 and $D7 occur in SYSTEM.COMPILER; the rest are carried so that
    # an unexpected one is reported as itself rather than as an unknown byte.
    #
    # $D7 NOP was STRONG INFERENCE before (Hyde describes a word-alignment NOP
    # at p.95 but never gives its number) and is now VERIFIED SOURCE FACT: the
    # interpreter dispatches both $D2 and $D7 to IncIPC1, a bare "skip one
    # byte". $D0 LPA is confirmed too, including the detail that distinguishes
    # it from LSA -- LPA pushes a pointer *past* the length byte, LSA pushes
    # one *at* it, though both instructions are the same length.
    0xD0: ("LPA", ["str"]),
    0xD1: ("STE", [UB, BIG]),   # store extended, mirror of $9D LDE
    0xD2: ("NOP", []),
    0xD3: ("EFJ", [SB]),        # equal false jump      ) not implemented by
    0xD4: ("NFJ", [SB]),        # not-equal false jump  ) the 1.4 interpreter
    0xD5: ("BPT", [BIG]),       # breakpoint
    0xD6: ("XIT", []),          # exit the interpreter
    0xD7: ("NOP", []),
}

# comparison type codes carried by EQU/NEQ/LEQ/LES/GEQ/GRT
CMP_TYPES = {2: "REAL", 4: "STR", 6: "BOOL", 8: "SET", 10: "BYTE", 12: "WORD"}

TERMINATORS = {0xAD, 0xC1}          # RNP, RBP
UNCONDITIONAL = {0xB9, 0xAC, 0xAD, 0xC1}


@dataclass
class Insn:
    addr: int
    length: int
    opcode: int
    mnemonic: str
    operands: list
    text: str
    target: int | None = None       # branch destination, if any
    raw: bytes = b""


def _big(code: bytes, p: int) -> tuple[int, int]:
    b = code[p]
    if b < 0x80:
        return b, 1
    return ((b & 0x7F) << 8) | code[p + 1], 2


def selfrel(code: bytes, at: int) -> int:
    """Resolve the self-relative pointer word stored at offset `at`."""
    return at - struct.unpack_from("<H", code, at)[0]


def decode(code: bytes, addr: int, jtab: int | None = None) -> Insn:
    """Decode one instruction at `addr` within segment bytes `code`.

    `jtab` is the procedure's attribute-table offset. Backward branches
    (negative SB displacement) index the jump table at JTAB+d, which holds a
    self-relative pointer to the real destination; supplying jtab resolves
    those to absolute segment offsets.
    """
    op = code[addr]
    p = addr + 1

    if op < 0x80:
        return Insn(addr, 1, op, "SLDC", [op], f"SLDC {op}", raw=code[addr:addr + 1])
    if 0xD8 <= op <= 0xE7:
        n = op - 0xD7
        return Insn(addr, 1, op, "SLDL", [n], f"SLDL {n}", raw=code[addr:addr + 1])
    if 0xE8 <= op <= 0xF7:
        n = op - 0xE7
        return Insn(addr, 1, op, "SLDO", [n], f"SLDO {n}", raw=code[addr:addr + 1])
    if 0xF8 <= op <= 0xFF:
        n = op - 0xF8
        return Insn(addr, 1, op, "SIND", [n], f"SIND {n}", raw=code[addr:addr + 1])

    entry = OPCODES.get(op)
    if entry is None:
        return Insn(addr, 1, op, f"DB_{op:02X}", [], f".byte ${op:02X}",
                    raw=code[addr:addr + 1])

    mnem, kinds = entry
    vals, parts, target = [], [], None

    for kind in kinds:
        if kind in (UB, DB):
            vals.append(code[p]); parts.append(str(code[p])); p += 1
        elif kind == SB:
            d = code[p]
            d = d - 256 if d >= 128 else d
            p += 1
            vals.append(d)
            if d >= 0:
                target = p + d
                parts.append(f"${target:04X}")
            elif jtab is not None:
                target = selfrel(code, jtab + d)
                parts.append(f"${target:04X} (jtab{d})")
            else:
                parts.append(f"jtab{d}")
        elif kind == BIG:
            v, n = _big(code, p); p += n
            vals.append(v); parts.append(str(v))
        elif kind == W:
            v = struct.unpack_from("<h", code, p)[0]; p += 2
            vals.append(v); parts.append(str(v))
        elif kind == "cmp":
            t = code[p]; p += 1
            vals.append(t); parts.append(CMP_TYPES.get(t, f"type{t}"))
            if t in (10, 12):
                v, n = _big(code, p); p += n
                vals.append(v); parts.append(str(v))
        elif kind == "str":
            n = code[p]; p += 1
            s = code[p:p + n]; p += n
            vals.append(bytes(s))
            parts.append(repr(s.decode("ascii", "replace")))
        elif kind == "ldc":
            n = code[p]; p += 1
            # the word block is word-aligned relative to the segment
            if p % 2:
                p += 1
            words = [struct.unpack_from("<H", code, p + 2 * i)[0] for i in range(n)]
            p += 2 * n
            vals.append(words)
            parts.append(f"{n}w [" + " ".join(f"${x:04X}" for x in words) + "]")
        elif kind == "xjp":
            if p % 2:
                p += 1
            lo, hi = struct.unpack_from("<hh", code, p)
            p += 4
            otherwise = selfrel(code, p)
            p += 2
            table = [selfrel(code, p + 2 * i) for i in range(hi - lo + 1)]
            p += 2 * (hi - lo + 1)
            vals.extend([lo, hi, otherwise, table])
            parts.append(f"{lo}..{hi} else ${otherwise:04X} ["
                         + " ".join(f"${t:04X}" for t in table) + "]")

    text = f"{mnem} " + ",".join(parts) if parts else mnem
    return Insn(addr, p - addr, op, mnem, vals, text, target, code[addr:p])


def disassemble(code: bytes, start: int, end: int,
                jtab: int | None = None) -> tuple[list[Insn], bool]:
    """Linear sweep from `start` up to `end`. Returns (insns, ended_exactly)."""
    out, p = [], start
    while p < end:
        try:
            ins = decode(code, p, jtab)
        except (IndexError, struct.error):
            break
        out.append(ins)
        p += ins.length
    return out, p == end


def sweep_exit(code: bytes, exit_ic: int, limit: int,
               jtab: int | None = None) -> tuple[list[Insn], int | None]:
    """Decode the exit sequence from exit_ic up to the first RNP/RBP.

    Returns (instructions, offset just past the terminator) or (…, None) if
    no terminator was found before `limit`.
    """
    out, p = [], exit_ic
    while p < limit:
        ins = decode(code, p, jtab)
        out.append(ins)
        p += ins.length
        if ins.opcode in TERMINATORS:
            return out, p
    return out, None
