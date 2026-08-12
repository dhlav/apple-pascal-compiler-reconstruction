"""Minimal NuFX (ShrinkIt) reader: enough to extract an LZW/1 disk image.

ShrinkIt compresses a thread in 4096-byte chunks. Each chunk is first
RLE-encoded (escape byte, value, count-1) and then optionally LZW-encoded,
so decompression is LZW-expand then RLE-expand.

Chunk header: word = length of the LZW-expanded (still RLE-encoded) data,
byte = LZW-used flag. When the chunk was stored without RLE, that length
is 4096 and the RLE pass is skipped.

Two details below were determined empirically against ii0src.sdk rather
than taken from documentation, and are asserted by tools/unpack_ii0src.py:
the first assignable LZW code is 0x101 with an "early" width change, and
the string table is reset at the start of every chunk.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

CHUNK = 4096

THREAD_CLASS = {0: "message", 1: "control", 2: "data", 3: "filename"}
FORMATS = {0: "uncompressed", 1: "squeeze", 2: "lzw1", 3: "lzw2",
           4: "lzc12", 5: "lzc16"}


@dataclass
class Thread:
    cls: str
    kind: int
    fmt: str
    eof: int
    comp_len: int
    offset: int


@dataclass
class Record:
    name: str
    storage_type: int
    extra_type: int
    threads: list[Thread]


class NuFX:
    def __init__(self, data: bytes):
        if data[:6] != b"N\xf5F\xe9l\xe5":
            raise ValueError("not a NuFX archive")
        self.data = data
        self.total_records = struct.unpack_from("<I", data, 8)[0]
        self.master_eof = struct.unpack_from("<I", data, 38)[0]
        self.records = self._parse_records()

    def _parse_records(self) -> list[Record]:
        d, p, out = self.data, 48, []
        for _ in range(self.total_records):
            if d[p:p + 4] != b"N\xf5F\xd8":
                raise ValueError(f"bad record header at 0x{p:X}")
            attrib_count, _ver, nthreads = struct.unpack_from("<HHI", d, p + 6)
            extra_type, storage_type = struct.unpack_from("<IH", d, p + 26)
            namelen = struct.unpack_from("<H", d, p + attrib_count - 2)[0]
            q = p + attrib_count
            hdr_name = d[q:q + namelen].decode("ascii", "replace")
            q += namelen
            threads = []
            for _t in range(nthreads):
                tcls, tfmt, tkind, _crc, teof, tcomp = struct.unpack_from("<HHHHII", d, q)
                threads.append(Thread(THREAD_CLASS.get(tcls, str(tcls)), tkind,
                                      FORMATS.get(tfmt, str(tfmt)), teof, tcomp, 0))
                q += 16
            for t in threads:
                t.offset = q
                q += t.comp_len
            name = hdr_name
            for t in threads:
                if t.cls == "filename":
                    name = d[t.offset:t.offset + t.eof].decode("ascii", "replace")
            out.append(Record(name, storage_type, extra_type, threads))
            p = q
        return out

    def thread_bytes(self, t: Thread) -> bytes:
        return self.data[t.offset:t.offset + t.comp_len]


class _BitReader:
    """LSB-first bit reader, as used by ShrinkIt LZW."""

    def __init__(self, data: bytes):
        self.data, self.pos, self.bits, self.nbits = data, 0, 0, 0

    def read(self, n: int) -> int | None:
        while self.nbits < n:
            if self.pos >= len(self.data):
                return None
            self.bits |= self.data[self.pos] << self.nbits
            self.pos += 1
            self.nbits += 8
        v = self.bits & ((1 << n) - 1)
        self.bits >>= n
        self.nbits -= n
        return v

    def align(self) -> None:
        self.bits, self.nbits = 0, 0


class _LZW1:
    """ShrinkIt LZW decoder; in LZW/1 the table persists across chunks.

    Variant determined empirically against ii0src.sdk (whose expanded block 2
    must be a valid UCSD volume directory): the first assignable code is
    0x101, and the code width increases "early" -- as soon as the next free
    code reaches (1 << width) - 1. Callers reset() per chunk.
    """

    def __init__(self):
        self.reset()

    def reset(self) -> None:
        self.prefix = [0] * 0x1000
        self.suffix = [0] * 0x1000
        self.next_code = 0x101
        self.width = 9

    def _expand(self, code: int) -> bytes:
        out = bytearray()
        guard = 0
        while code >= 0x100:
            if guard > 0x1000:
                raise ValueError("cyclic LZW prefix chain -- decoder desynchronised")
            out.append(self.suffix[code])
            code = self.prefix[code]
            guard += 1
        out.append(code)
        out.reverse()
        return bytes(out)

    def decode_chunk(self, br: _BitReader, want: int) -> bytes:
        out = bytearray()
        old = None
        first = 0
        while len(out) < want:
            code = br.read(self.width)
            if code is None:
                break
            if code == 0x100:            # table clear (LZW/2 style, tolerated)
                self.reset()
                old = None
                continue
            if old is None:
                s = self._expand(code)
            elif code < self.next_code:
                s = self._expand(code)
            else:
                s = self._expand(old) + bytes([first])
            first = s[0]
            out += s
            if old is not None and self.next_code < 0x1000:
                self.prefix[self.next_code] = old
                self.suffix[self.next_code] = first
                self.next_code += 1
                if self.next_code >= (1 << self.width) - 1 and self.width < 12:
                    self.width += 1
            old = code
        return bytes(out[:want])


def _rle_expand(data: bytes, esc: int, want: int) -> bytes:
    out = bytearray()
    i = 0
    while i < len(data) and len(out) < want:
        b = data[i]
        if b == esc:
            out += bytes([data[i + 1]]) * (data[i + 2] + 1)
            i += 3
        else:
            out.append(b)
            i += 1
    return bytes(out)


def expand_lzw1(thread: bytes, total_out: int) -> bytes:
    """Expand an LZW/1 thread. `total_out` is the uncompressed byte count."""
    crc, volume, esc = struct.unpack_from("<HBB", thread, 0)
    p = 4
    lzw = _LZW1()
    out = bytearray()
    while len(out) < total_out:
        if p + 3 > len(thread):
            break
        rle_len, lzw_flag = struct.unpack_from("<HB", thread, p)
        p += 3
        want_out = min(CHUNK, total_out - len(out))
        lzw.reset()
        if lzw_flag:
            br = _BitReader(thread[p:])
            rle_data = lzw.decode_chunk(br, rle_len)
            p += br.pos
        else:
            rle_data = thread[p:p + rle_len]
            p += rle_len
        if rle_len == want_out:
            out += rle_data[:want_out]          # chunk was not RLE'd
        else:
            out += _rle_expand(rle_data, esc, want_out)
    return bytes(out[:total_out]), crc, volume, esc, p
