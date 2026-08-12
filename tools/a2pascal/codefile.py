"""UCSD / Apple Pascal codefile (SYSTEM.COMPILER, *.CODE) structure.

Layout, all verified against the two evidence disks:

Block 0 - segment dictionary (512 bytes)
    0x000  DISKINFO[0..15]  : (codeaddr: word; codeleng: word)
                              codeaddr = block number relative to file start,
                              codeleng = length in bytes. Both zero = unused.
    0x040  SEGNAME[0..15]   : 8 chars each, space padded
    0x0C0  SEGKIND[0..15]   : word
    0x100  SEGINFO[0..15]   : word; bits 0-7 segnum, bits 8-11 mtype,
                              bits 13-15 version
    0x1A0  copyright notice : length-prefixed string

Segment - the last word of the segment is
    low byte  = segment number   (agrees with SEGINFO)
    high byte = number of procedures
Preceding it, growing downward, is the procedure dictionary: NPROC
self-relative word pointers, entry i at  seglen - 2 - 2*i.  A self-relative
pointer stored at offset p with value v designates offset p - v.

Each pointer designates that procedure's JTAB (attribute table), which sits
at the end of the procedure's code:
    JTAB+0  procedure number (byte)      -- equals the dictionary index
    JTAB+1  lexical level     (byte)
    JTAB-2  enter IC  (self-relative pointer to first instruction)
    JTAB-4  exit  IC  (self-relative pointer to the exit code)
    JTAB-6  parameter size in bytes
    JTAB-8  data (local variable) size in bytes
    JTAB-10, -12, ... jump table entries, addressed by negative offsets

Native (6502) procedures carry a procedure-number byte of 0 at JTAB+0
instead of their dictionary index, and a null (zero) exit-IC self-relative
word, since they have no EXIT target. Their enter IC is still valid. A
segment's mtype is 6502 if it contains ANY native procedure, so mtype is
not a reliable per-procedure test -- use Procedure.is_native.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field

MTYPES = {
    0: "unknown", 1: "pcode-msb", 2: "pcode-lsb", 3: "pdp-11", 4: "8080",
    5: "z80", 6: "ga440", 7: "6502", 8: "6800", 9: "ti9900",
}


def _w(b: bytes, o: int) -> int:
    return struct.unpack_from("<H", b, o)[0]


@dataclass
class Procedure:
    number: int          # dictionary index (1-based)
    jtab: int            # offset of the attribute table within the segment
    proc_num: int        # procedure number byte stored at JTAB+0
    lex_level: int
    enter_ic: int
    exit_ic: int
    param_size: int
    data_size: int
    consistent: bool = True

    @property
    def is_native(self) -> bool:
        """Native 6502 procedures store 0 where the procedure number belongs."""
        return self.proc_num == 0

    @property
    def code_start(self) -> int:
        return self.enter_ic

    @property
    def code_end(self) -> int:
        """End of this procedure's body: the exit code runs up to JTAB-8."""
        return self.jtab - 8


@dataclass
class Segment:
    index: int           # slot in the segment dictionary, 0..15
    name: str
    block: int           # block offset within the codefile
    length: int          # bytes
    seg_num: int         # from SEGINFO
    seg_num_tail: int    # from the segment's own trailing word
    mtype: str
    version: int
    data: bytes = field(repr=False, default=b"")
    procedures: list[Procedure] = field(default_factory=list)

    @property
    def is_pcode(self) -> bool:
        """True if the segment contains at least one p-code procedure.

        Not the same as mtype: a segment holding a couple of native helpers
        is stamped mtype=6502 even though the rest is p-code (Apple Pascal
        1.3's PASCALCO is exactly that -- 29 p-code, 2 native).
        """
        return any(not p.is_native for p in self.procedures)

    @property
    def pcode_procedures(self) -> list[Procedure]:
        return [p for p in self.procedures if not p.is_native]

    @property
    def native_procedures(self) -> list[Procedure]:
        return [p for p in self.procedures if p.is_native]


class CodeFile:
    def __init__(self, data: bytes):
        self.data = data
        self.segments = self._parse_dictionary()
        for seg in self.segments:
            self._parse_procedures(seg)

    @property
    def copyright(self) -> str:
        d = self.data
        n = d[0x1B0]
        return d[0x1B1:0x1B1 + n].decode("ascii", "replace")

    def _parse_dictionary(self) -> list[Segment]:
        d = self.data[:512]
        out = []
        for i in range(16):
            addr, leng = struct.unpack_from("<HH", d, i * 4)
            if leng == 0:
                continue
            name = d[0x40 + i * 8:0x48 + i * 8].decode("ascii", "replace").strip()
            info = _w(d, 0x100 + i * 2)
            raw = self.data[addr * 512: addr * 512 + leng]
            tail = _w(raw, leng - 2)
            out.append(Segment(
                index=i, name=name, block=addr, length=leng,
                seg_num=info & 0xFF, seg_num_tail=tail & 0xFF,
                mtype=MTYPES.get((info >> 8) & 0xF, f"?{(info >> 8) & 0xF}"),
                version=info >> 13, data=raw,
            ))
        return out

    @staticmethod
    def _parse_procedures(seg: Segment) -> None:
        raw, n = seg.data, seg.length
        nproc = _w(raw, n - 2) >> 8
        for i in range(1, nproc + 1):
            ptr_at = n - 2 - 2 * i
            if ptr_at < 0:
                break
            jtab = ptr_at - _w(raw, ptr_at)
            if not (8 <= jtab < n - 1):
                seg.procedures.append(Procedure(i, jtab, -1, -1, -1, -1, -1, -1, False))
                continue
            enter = (jtab - 2) - _w(raw, jtab - 2)
            exitic = (jtab - 4) - _w(raw, jtab - 4)
            p = Procedure(
                number=i, jtab=jtab, proc_num=raw[jtab], lex_level=raw[jtab + 1],
                enter_ic=enter, exit_ic=exitic,
                param_size=_w(raw, jtab - 6), data_size=_w(raw, jtab - 8),
            )
            if p.is_native:
                # No exit code, so exit_ic is a null self-relative pointer.
                p.consistent = 0 <= enter < jtab
            else:
                p.consistent = (p.proc_num == i and 0 <= enter < exitic <= jtab
                                and p.param_size % 2 == 0 and p.data_size % 2 == 0)
            seg.procedures.append(p)

    def segment(self, name: str) -> Segment:
        for s in self.segments:
            if s.name.upper() == name.upper():
                return s
        raise KeyError(name)
