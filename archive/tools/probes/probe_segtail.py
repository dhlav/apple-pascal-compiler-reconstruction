"""What does `PASCALCO.23` write, and therefore what is global 13?

`PASCALCO.23` is the last thing that runs for each segment. It emits

    for i := G96-1 downto 1:
        EMITWORD(0)  or  EMITWORD((LCBASE + CODEINX) - G185[i])
    EMIT(G13)
    EMIT(G96 - 1)

then records the segment's end address and resets `LCBASE`.

Finding 27 read those two `EMIT`s as `JTAB+0` and `JTAB+1` of a procedure
attribute table, and concluded from the second that global 96 is the
lexical level. That was wrong, and this probe is what shows it: the bytes
`PASCALCO.23` writes are the **segment tail**, not an attribute table.

The check reconstructs each segment's last `2*nproc + 2` bytes from the
procedure list alone, exactly as the routine would emit them --

  * `nproc` self-relative pointers, procedure `nproc` first (lowest
    address) down to procedure 1, each holding `its_own_address - jtab`;
  * then one byte of segment number, then one byte of procedure count.

-- and compares that reconstruction with the bytes actually on the disk.
Nothing here is read out of `Segment.seg_num_tail`; the segment number
comes from the *dictionary* at block 0, which `PASCALCO.23` never touches,
so the low byte agreeing is a real coincidence to explain.

If it matches, `EMIT(G13)` is writing a segment number and `EMIT(G96-1)` a
procedure count, and neither global is a lexical level. Finding 28.
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile

ROOT = Path(__file__).resolve().parent.parent.parent
DISKS = {
    "1.1": "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk",
    "1.3": "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk",
}


def rebuild_tail(seg) -> bytes:
    """The tail PASCALCO.23 would emit for this segment."""
    n, out = seg.length, bytearray()
    for p in sorted(seg.procedures, key=lambda p: p.number, reverse=True):
        at = n - 2 - 2 * p.number          # where this pointer will land
        out += struct.pack("<H", at - p.jtab)
    out += bytes([seg.seg_num, len(seg.procedures)])
    return bytes(out)


def main() -> int:
    bad, checked = [], 0
    for ver, dsk in DISKS.items():
        disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / dsk)
        e = disk.find("SYSTEM.COMPILER")
        cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))

        for seg in cf.segments:
            want = rebuild_tail(seg)
            got = seg.data[seg.length - len(want):seg.length]
            checked += 1
            if got != want:
                # Report the first word that differs, so a wrong ordering
                # reads differently from a wrong segment number.
                where = next(i for i in range(len(want)) if want[i] != got[i])
                bad.append(f"{ver} {seg.name}: tail differs at byte "
                           f"{where - len(want)} of the segment -- "
                           f"emitted {want[where]:02X}, disk has {got[where]:02X}")
        print(f"{ver}: {len(cf.segments)} segment tails rebuilt from the "
              f"procedure list and matched byte for byte")

    if bad:
        print("\n".join(bad))
        return 1
    print(f"{checked} tails; EMIT(G13) is a segment number and EMIT(G96-1) "
          f"a procedure count")
    print("segtail-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
