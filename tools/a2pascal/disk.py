"""Apple II Pascal (UCSD) filesystem reader for 5.25" .dsk images.

A 143,360-byte .dsk is 35 tracks x 16 sectors x 256 bytes. Two sector
orderings are in circulation for the same physical media:

  "dos"    - sectors stored in DOS 3.3 physical order (the usual .dsk)
  "prodos" - sectors stored in ProDOS/block order (the usual .po)

UCSD Pascal addresses the disk in 512-byte blocks. Each block is two
256-byte logical sectors, and the Pascal logical -> DOS physical sector
map is the standard 16-entry table below.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

SECTOR_SIZE = 256
BLOCK_SIZE = 512
SECTORS_PER_TRACK = 16
TRACKS = 35
DSK_SIZE = TRACKS * SECTORS_PER_TRACK * SECTOR_SIZE

# Pascal/ProDOS logical sector -> DOS 3.3 physical sector.
# Verified against both evidence disks: the volume directory (Pascal block 2)
# lands on physical sectors 11,10 of track 0, which is where it actually is.
PASCAL_TO_DOS = [0, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 15]
# ProDOS-order images already store sectors in block order.
PASCAL_TO_PRODOS = list(range(16))

FILE_KINDS = {
    0: "untypedfile",
    1: "xdskfile",
    2: "codefile",
    3: "textfile",
    4: "infofile",
    5: "datafile",
    6: "graffile",
    7: "fotofile",
    8: "securedir",
}


@dataclass(frozen=True)
class DirEntry:
    index: int
    first_block: int
    next_block: int      # first block *after* the file
    kind: str
    kind_code: int
    name: str
    last_byte: int       # bytes used in the final block
    mtime_raw: int
    # The unused tail of the 16-byte name field, from the end of the name to
    # byte 22. It is not a field and it is not zero: the FILER assigns a
    # Pascal `STRING[15]`, which copies the length byte and the characters
    # and leaves the rest of the buffer holding whatever the last assignment
    # put there. On the six evidence disks every entry ends `24 67`,
    # right-aligned at bytes 20-21, whatever the name's length. Carried here
    # so a rewritten directory can put it back verbatim -- scrubbing bytes we
    # cannot explain is not the same as reproducing the volume.
    pad: bytes = b""

    @property
    def blocks(self) -> int:
        return self.next_block - self.first_block

    @property
    def size(self) -> int:
        return (self.blocks - 1) * BLOCK_SIZE + self.last_byte if self.blocks else 0


@dataclass(frozen=True)
class VolumeInfo:
    name: str
    total_blocks: int
    num_files: int


def _decode_date(word: int) -> str:
    """UCSD date word: bits 0-3 month, 4-8 day, 9-15 year."""
    month = word & 0xF
    day = (word >> 4) & 0x1F
    year = (word >> 9) & 0x7F
    if not (1 <= month <= 12):
        return f"<raw {word:04X}>"
    return f"{day:02d}-{month:02d}-{1900 + year if year >= 70 else 2000 + year}"


class PascalDisk:
    def __init__(self, data: bytes, order: str = "auto"):
        if len(data) != DSK_SIZE:
            raise ValueError(f"expected {DSK_SIZE} bytes, got {len(data)}")
        self.data = data
        self.order = self._detect_order() if order == "auto" else order
        self._map = PASCAL_TO_DOS if self.order == "dos" else PASCAL_TO_PRODOS

    @classmethod
    def from_file(cls, path, order: str = "auto") -> "PascalDisk":
        with open(path, "rb") as fh:
            return cls(fh.read(), order)

    def _detect_order(self) -> str:
        """Pick the ordering whose block 2 parses as a Pascal volume directory."""
        for order in ("dos", "prodos"):
            self._map = PASCAL_TO_DOS if order == "dos" else PASCAL_TO_PRODOS
            try:
                blk = self.read_block(2)
            except Exception:
                continue
            first, last, kind, namelen = struct.unpack_from("<HHHB", blk, 0)
            if first == 0 and last == 6 and kind == 0 and 1 <= namelen <= 7:
                return order
        raise ValueError("no sector ordering yields a valid Pascal volume directory")

    def read_block(self, n: int) -> bytes:
        track, half = divmod(n, 8)
        if not 0 <= track < TRACKS:
            raise ValueError(f"block {n} out of range")
        out = bytearray()
        for logical in (half * 2, half * 2 + 1):
            phys = self._map[logical]
            off = (track * SECTORS_PER_TRACK + phys) * SECTOR_SIZE
            out += self.data[off:off + SECTOR_SIZE]
        return bytes(out)

    def read_blocks(self, start: int, count: int) -> bytes:
        return b"".join(self.read_block(start + i) for i in range(count))

    def volume(self) -> VolumeInfo:
        blk = self.read_block(2)
        namelen = blk[6]
        name = blk[7:7 + namelen].decode("ascii", "replace")
        total, nfiles = struct.unpack_from("<HH", blk, 14)
        return VolumeInfo(name, total, nfiles)

    def directory(self) -> list[DirEntry]:
        raw = self.read_blocks(2, 4)
        nfiles = struct.unpack_from("<H", raw, 16)[0]
        entries = []
        for i in range(1, nfiles + 1):
            off = i * 26
            first, nxt, kindw = struct.unpack_from("<HHH", raw, off)
            namelen = raw[off + 6]
            if namelen > 15:
                continue
            name = raw[off + 7:off + 7 + namelen].decode("ascii", "replace")
            last_byte, mtime = struct.unpack_from("<HH", raw, off + 22)
            kind_code = kindw & 0xF
            entries.append(DirEntry(i, first, nxt, FILE_KINDS.get(kind_code, f"kind{kind_code}"),
                                    kind_code, name, last_byte, mtime,
                                    bytes(raw[off + 7 + namelen:off + 22])))
        return entries

    def read_file(self, name: str) -> bytes:
        for e in self.directory():
            if e.name.upper() == name.upper():
                return self.read_blocks(e.first_block, e.blocks)[:e.size]
        raise KeyError(name)

    def find(self, name: str) -> DirEntry:
        for e in self.directory():
            if e.name.upper() == name.upper():
                return e
        raise KeyError(name)


def format_date(word: int) -> str:
    return _decode_date(word)
