"""Write Apple II Pascal (UCSD) volumes, not just read them.

`disk.py` reads the evidence disks. This is the other direction, and it
exists for one reason: the acceptance tier runs Apple's own
`SYSTEM.COMPILER` and `SYSTEM.ASSMBLER` in an emulator, and nothing can be
handed to them until the reconstructed source is on a disk image they will
mount.

The filesystem is small enough to implement outright. Files are
*contiguous* -- an entry is a first block and a one-past-the-last block, and
there is no allocation map anywhere on the volume, so free space is just the
gaps between entries. The directory is four blocks starting at block 2,
holding a volume entry and up to 77 file entries of 26 bytes each, kept
sorted by first block. That is the whole format.

Being able to write it is worth little on its own; being able to show the
bytes are *Apple's* bytes is the point. Two things make that checkable, and
`probes/probe_diskwrite.py` runs both:

  * the directory encoder is the exact inverse of the reader, so every
    evidence disk's four directory blocks must come back byte for byte from
    its own parsed entries -- which tests name padding, the kind word, the
    date words and the header layout against six volumes Apple wrote;
  * the sector map is shared with the reader, so writing a block and reading
    it back has to be the identity at every block on the disk.

Neither would notice a field this module and the reader are *both* wrong
about. Nothing here can rule that out; what it rules out is drift between
the two, and any encoding Apple's own volumes contradict.
"""

from __future__ import annotations

import datetime
import struct

from .disk import (BLOCK_SIZE, DSK_SIZE, FILE_KINDS, PASCAL_TO_DOS,
                   PASCAL_TO_PRODOS, SECTOR_SIZE, SECTORS_PER_TRACK, TRACKS,
                   DirEntry, PascalDisk)

DIR_START = 2           # the volume directory always begins at block 2
DIR_BLOCKS = 4
ENTRY_SIZE = 26
# 4 x 512 = 2048 bytes / 26 = 78 entries, the first of which is the volume.
MAX_ENTRIES = (DIR_BLOCKS * BLOCK_SIZE) // ENTRY_SIZE
MAX_FILES = MAX_ENTRIES - 1
FIRST_DATA_BLOCK = DIR_START + DIR_BLOCKS     # 6
TOTAL_BLOCKS = TRACKS * SECTORS_PER_TRACK * SECTOR_SIZE // BLOCK_SIZE   # 280

KIND_CODES = {v: k for k, v in FILE_KINDS.items()}


class VolumeFull(Exception):
    """No contiguous run long enough, or the directory has no free entry."""


def encode_date(when: datetime.date | None = None) -> int:
    """The UCSD date word: bits 0-3 month, 4-8 day, 9-15 year.

    The year field is two digits. `disk._decode_date` reads a value below 70
    as 20xx, so dates from 2000 on round-trip; there is no representation for
    a year outside 1970..2069.
    """
    d = when or datetime.date.today()
    if not 1970 <= d.year <= 2069:
        raise ValueError(f"{d.year} is outside the two-digit window")
    return (d.month & 0xF) | ((d.day & 0x1F) << 4) | ((d.year % 100) << 9)


def _pack_volume(name: str, total_blocks: int, nfiles: int, last_boot: int,
                 template: bytes = b"") -> bytes:
    """The 26-byte entry 0. Its name field is seven characters, not fifteen.

    `template` is the entry as it stands on the volume, if there is one. The
    fields this understands are overwritten and everything else is left
    alone, because entry 0 has bytes nothing here can account for -- the pad
    after a short volume name, `DLOADTIME` at 18, and the last four bytes.
    """
    if not 1 <= len(name) <= 7:
        raise ValueError(f"volume name {name!r} must be 1..7 characters")
    e = bytearray(template or bytes(ENTRY_SIZE))
    if len(e) != ENTRY_SIZE:
        raise ValueError("template is not one entry")
    struct.pack_into("<HHH", e, 0, 0, FIRST_DATA_BLOCK, 0)
    e[6] = len(name)
    e[7:7 + len(name)] = name.encode("ascii")
    struct.pack_into("<HH", e, 14, total_blocks, nfiles)
    struct.pack_into("<H", e, 20, last_boot)
    return bytes(e)


def _pack_entry(en: DirEntry) -> bytes:
    """A file entry, residue and all.

    Bytes 6..21 are a Pascal `STRING[15]`: a length byte, the characters,
    and then whatever was in the buffer. `en.pad` carries that tail back out
    unchanged when the entry came off a disk, and is empty for a new file --
    so a directory this rewrites is byte-identical, and one it builds is
    zero-filled where it has nothing to say.
    """
    if not 1 <= len(en.name) <= 15:
        raise ValueError(f"file name {en.name!r} must be 1..15 characters")
    tail = 15 - len(en.name)
    if len(en.pad) not in (0, tail):
        raise ValueError(f"{en.name}: pad is {len(en.pad)} bytes, the name "
                         f"field leaves {tail}")
    e = bytearray(ENTRY_SIZE)
    struct.pack_into("<HHH", e, 0, en.first_block, en.next_block, en.kind_code)
    e[6] = len(en.name)
    e[7:7 + len(en.name)] = en.name.encode("ascii")
    e[7 + len(en.name):22] = en.pad or bytes(tail)
    struct.pack_into("<HH", e, 22, en.last_byte, en.mtime_raw)
    return bytes(e)


class PascalWriter:
    """A mutable Pascal volume image.

    Block addressing and the sector map are the reader's; this only adds the
    write half, so the two cannot disagree about where a block lives.
    """

    def __init__(self, data: bytes, order: str = "auto"):
        if len(data) != DSK_SIZE:
            raise ValueError(f"expected {DSK_SIZE} bytes, got {len(data)}")
        self.data = bytearray(data)
        # Detection needs a parsed directory, so borrow the reader's.
        self.order = PascalDisk(bytes(data), order).order if order == "auto" \
            else order
        self._map = PASCAL_TO_DOS if self.order == "dos" else PASCAL_TO_PRODOS

    # -- construction ---------------------------------------------------

    @classmethod
    def from_file(cls, path, order: str = "auto") -> "PascalWriter":
        with open(path, "rb") as fh:
            return cls(fh.read(), order)

    @classmethod
    def blank(cls, name: str, order: str = "dos",
              boot: bytes | None = None) -> "PascalWriter":
        """An empty volume.

        Blocks 0 and 1 are the boot area. Leaving them zero gives a volume
        the Filer will mount and read but the machine will not boot from,
        which is what a work disk in drive 2 wants; pass `boot` (1024 bytes,
        lifted from a real boot disk) if it has to boot.
        """
        w = cls.__new__(cls)
        w.data = bytearray(DSK_SIZE)
        w.order = order
        w._map = PASCAL_TO_DOS if order == "dos" else PASCAL_TO_PRODOS
        if boot is not None:
            if len(boot) != 2 * BLOCK_SIZE:
                raise ValueError("boot area is two blocks")
            w.write_block(0, boot[:BLOCK_SIZE])
            w.write_block(1, boot[BLOCK_SIZE:])
        w._commit(name, [], encode_date())
        return w

    # -- blocks ---------------------------------------------------------

    def _offsets(self, n: int) -> tuple[int, int]:
        track, half = divmod(n, 8)
        if not 0 <= track < TRACKS:
            raise ValueError(f"block {n} out of range")
        return tuple((track * SECTORS_PER_TRACK + self._map[s]) * SECTOR_SIZE
                     for s in (half * 2, half * 2 + 1))

    def read_block(self, n: int) -> bytes:
        a, b = self._offsets(n)
        return bytes(self.data[a:a + SECTOR_SIZE] + self.data[b:b + SECTOR_SIZE])

    def write_block(self, n: int, payload: bytes) -> None:
        if len(payload) != BLOCK_SIZE:
            raise ValueError(f"block {n}: {len(payload)} bytes, need {BLOCK_SIZE}")
        a, b = self._offsets(n)
        self.data[a:a + SECTOR_SIZE] = payload[:SECTOR_SIZE]
        self.data[b:b + SECTOR_SIZE] = payload[SECTOR_SIZE:]

    def read_blocks(self, start: int, count: int) -> bytes:
        return b"".join(self.read_block(start + i) for i in range(count))

    def write_blocks(self, start: int, payload: bytes) -> None:
        if len(payload) % BLOCK_SIZE:
            raise ValueError("payload is not a whole number of blocks")
        for i in range(len(payload) // BLOCK_SIZE):
            self.write_block(start + i, payload[i * BLOCK_SIZE:(i + 1) * BLOCK_SIZE])

    # -- directory ------------------------------------------------------

    def _reader(self) -> PascalDisk:
        return PascalDisk(bytes(self.data), self.order)

    def volume(self):
        return self._reader().volume()

    def entries(self) -> list[DirEntry]:
        return self._reader().directory()

    def directory_bytes(self) -> bytes:
        """The four directory blocks as they currently stand on the image."""
        return self.read_blocks(DIR_START, DIR_BLOCKS)

    def encode_directory(self, name: str, entries: list[DirEntry],
                         total_blocks: int, last_boot: int,
                         template: bytes | None = None) -> bytes:
        """Lay out the four directory blocks. The inverse of `directory()`.

        Entries are written in the order given and must already be sorted by
        first block -- the Filer walks the directory linearly and a run out of
        order is a corrupt volume, not a slow one.

        `template` is the directory as it currently stands. Everything past
        the live entries is copied from it rather than zeroed: the FILER
        unlinks a file by decrementing the count and shuffling the entries
        down, so the tail holds the remains of deleted entries, and blanking
        them would be a change to the volume that nothing here asked for.
        Pass `None` to build a directory from nothing.
        """
        if len(entries) > MAX_FILES:
            raise VolumeFull(f"{len(entries)} files, the directory holds {MAX_FILES}")
        prev = FIRST_DATA_BLOCK
        for en in entries:
            if en.first_block < prev:
                raise ValueError(f"{en.name} starts at {en.first_block}, "
                                 f"behind the previous file's end {prev}")
            if en.next_block <= en.first_block:
                raise ValueError(f"{en.name} is empty ({en.first_block}"
                                 f"..{en.next_block})")
            if en.next_block > total_blocks:
                raise ValueError(f"{en.name} runs past the end of the volume")
            prev = en.next_block
        if template is not None and len(template) != DIR_BLOCKS * BLOCK_SIZE:
            raise ValueError("template is not the four directory blocks")
        raw = bytearray(template if template is not None
                        else bytes(DIR_BLOCKS * BLOCK_SIZE))
        raw[0:ENTRY_SIZE] = _pack_volume(name, total_blocks, len(entries),
                                         last_boot,
                                         bytes(raw[0:ENTRY_SIZE]) if template
                                         else b"")
        for i, en in enumerate(entries, start=1):
            raw[i * ENTRY_SIZE:(i + 1) * ENTRY_SIZE] = _pack_entry(en)
        return bytes(raw)

    def _commit(self, name: str, entries: list[DirEntry],
                last_boot: int, total_blocks: int = TOTAL_BLOCKS,
                template: bytes | None = None) -> None:
        self.write_blocks(DIR_START,
                          self.encode_directory(name, entries, total_blocks,
                                                last_boot, template))

    # -- free space -----------------------------------------------------

    def gaps(self) -> list[tuple[int, int]]:
        """(start, length) of every unallocated run, in block order."""
        vol = self.volume()
        out, cursor = [], FIRST_DATA_BLOCK
        for en in self.entries():
            if en.first_block > cursor:
                out.append((cursor, en.first_block - cursor))
            cursor = max(cursor, en.next_block)
        if vol.total_blocks > cursor:
            out.append((cursor, vol.total_blocks - cursor))
        return out

    def free_blocks(self) -> int:
        return sum(n for _, n in self.gaps())

    # -- files ----------------------------------------------------------

    def add_file(self, name: str, payload: bytes, kind: str = "textfile",
                 when: datetime.date | None = None,
                 mtime_raw: int | None = None) -> DirEntry:
        """Place a file in the first gap long enough to hold it.

        First fit, not best fit: the Filer's own `K(runch` exists because
        UCSD volumes fragment, and reproducing a smarter policy would only
        make the layout harder to predict. If the file does not fit in any
        single gap it does not fit -- there is no way to split it.
        """
        name = name.upper()
        if any(e.name.upper() == name for e in self.entries()):
            raise ValueError(f"{name} is already on the volume")
        if kind not in KIND_CODES:
            raise ValueError(f"unknown file kind {kind!r}")
        nblocks = max(1, -(-len(payload) // BLOCK_SIZE))
        last_byte = len(payload) - (nblocks - 1) * BLOCK_SIZE if payload else 0

        start = next((s for s, n in self.gaps() if n >= nblocks), None)
        if start is None:
            raise VolumeFull(
                f"{name} needs {nblocks} contiguous blocks; the largest free "
                f"run is {max((n for _, n in self.gaps()), default=0)} "
                f"({self.free_blocks()} free in total)")

        template = self.directory_bytes()
        padded = payload + bytes(nblocks * BLOCK_SIZE - len(payload))
        self.write_blocks(start, padded)

        # `mtime_raw` carries a date word straight through, for copying a
        # file from one volume to another with the stamp it already had.
        en = DirEntry(0, start, start + nblocks, kind, KIND_CODES[kind],
                      name, last_byte,
                      encode_date(when) if mtime_raw is None else mtime_raw)
        entries = sorted(self.entries() + [en], key=lambda e: e.first_block)
        vol = self.volume()
        self._commit(vol.name, entries, self._last_boot(), vol.total_blocks,
                     template)
        return en

    def remove_file(self, name: str) -> None:
        """Drop the directory entry. The blocks are not scrubbed.

        That is what the Filer does too: `R(emove` unlinks and the data stays
        until something is written over it.
        """
        entries = self.entries()
        keep = [e for e in entries if e.name.upper() != name.upper()]
        if len(keep) == len(entries):
            raise KeyError(name)
        vol = self.volume()
        self._commit(vol.name, keep, self._last_boot(), vol.total_blocks,
                     self.directory_bytes())

    def _last_boot(self) -> int:
        return struct.unpack_from("<H", self.read_block(DIR_START), 20)[0]

    # -- output ---------------------------------------------------------

    def to_bytes(self) -> bytes:
        return bytes(self.data)

    def save(self, path) -> None:
        with open(path, "wb") as fh:
            fh.write(self.data)
