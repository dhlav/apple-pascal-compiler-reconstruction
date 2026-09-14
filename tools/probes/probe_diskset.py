"""The three 1.3 disks, rebuilt, against Apple's images: a total that balances.

tools/mkdiskset.py writes each volume out of what this repo produces and
accounts for every byte by region (finding 289). This checks that account.

Claims, each of which the bytes can fail:

  1. **The regions tile each disk**: contiguous from block 0 to the end,
     143,360 bytes, no block in two regions.
  2. **The differences balance**: the per-region counts add up to a direct
     compare of the two image files, sector order and all.
  3. **The placement is not what differs**: the same build with every region
     copied from Apple's image is Apple's image, byte for byte.
  4. **Every region differs by exactly what its finding says**, and no
     other region differs at all. A rebuilt file that regresses, a text
     layout that drifts, or a new source of difference fails here however
     the total moves.
  5. **The one boot byte is FORMATTER.DATA's**: blocks 0-1 differ from
     Apple's only where the rebuilt FORMATTER.DATA's blocks 3-4 do.
  6. **The rest is residue, and named**: directory differences lie past the
     live entries only; APPLE2's free differences lie in block 187, the
     removed LINKER.INFO entry's one block.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mkdiskset
from a2pascal.disk import PascalDisk

BLOCK = 512

# (disk, region) -> bytes that differ from Apple's, and why. Anything not
# named here must be identical.
EXPECTED = {
    # the uncleared assembler byte, via FORMATTER.DATA blocks 3-4 (275)
    ("APPLE1", "<boot>"): 1, ("APPLE2", "<boot>"): 1, ("APPLE3", "<boot>"): 1,
    ("APPLE3", "FORMATTER.DATA"): 1,
    # dead directory space: Filer text past entry 77, and on APPLE2 a
    # removed LINKER.INFO entry (289)
    ("APPLE1", "<directory>"): 14, ("APPLE2", "<directory>"): 34,
    ("APPLE3", "<directory>"): 20,
    # the LINKER.INFO file's block, left in free space (289)
    ("APPLE2", "<free>"): 44,
    # out of scope: the 64K system's nonzero bytes against zero
    ("APPLE1", "SYSTEM.APPLE"): 14057, ("APPLE3", "SYSTEM.APPLE"): 14057,
    ("APPLE1", "SYSTEM.PASCAL"): 19732,
    # memory SETUP never writes (277)
    ("APPLE1", "SYSTEM.MISCINFO"): 147, ("APPLE3", "II40.MISCINFO"): 142,
    ("APPLE3", "II80.MISCINFO"): 116, ("APPLE3", "HAZEL.MISCINFO"): 151,
    # two text blocks fewer than Apple's, so every slot after LONGINTI sits
    # a block or two early; slot by slot 16414 agree (287)
    ("APPLE1", "SYSTEM.LIBRARY"): 16156,
    # the Linker's slack past the last segment (104)
    ("APPLE2", "LIBMAP.CODE"): 311, ("APPLE3", "FORMATTER.CODE"): 394,
    # the record window's first fill (276)
    ("APPLE2", "6502.ERRORS"): 287,
    # SEGINFO version 2 against 6, and for LINEFEED the compile's slack (274,
    # 289)
    ("APPLE3", "BINDER.CODE"): 16, ("APPLE3", "SET40COLS.CODE"): 16,
    ("APPLE3", "LINEFEED.CODE"): 467,
    # version 0 and 34 stale pads (273)
    ("APPLE3", "SETUP.CODE"): 3943,
    # three slack tails of the finishing tool (284)
    ("APPLE3", "128K.PASCAL"): 571,
}
TOTAL_DIFFER = 70679
TOTAL = 3 * 143360

fail = []


def check(ok: bool, label: str) -> None:
    print(("  ok   " if ok else "  FAIL ") + label)
    if not ok:
        fail.append(label)


def main() -> int:
    result = mkdiskset.build()
    control = mkdiskset.build(carry=True)

    print("=== the regions tile each disk and the differences balance ===")
    for vol, (image, regions) in result.items():
        cursor, tiled = 0, True
        for r in regions:
            tiled &= r.first == cursor
            cursor = r.first + r.blocks
        size = sum(r.size for r in regions)
        check(tiled and cursor == 280 and size == 143360,
              f"{vol}: {len(regions)} regions, blocks 0..{cursor}, "
              f"{size} bytes")
        differ = sum(r.differ for r in regions)
        direct = mkdiskset.image_differ(vol, image)
        check(differ == direct,
              f"{vol}: regions differ by {differ}, the image files by "
              f"{direct}")

    print("=== the placement is not what differs ===")
    for vol, (image, _) in control.items():
        apple = mkdiskset.DISKS[vol].read_bytes()
        check(image == apple, f"{vol} built from Apple's own regions is "
              f"Apple's image")

    print("=== every region differs by exactly what its finding says ===")
    seen = set()
    for vol, (_, regions) in result.items():
        for r in regions:
            key = (vol, r.name)
            want = EXPECTED.get(key, 0)
            if key in EXPECTED:
                seen.add(key)
            if want or r.differ:
                check(r.differ == want,
                      f"{vol}:{r.name} ({r.category}) differs by {r.differ}, "
                      f"expected {want}")
    check(seen == set(EXPECTED),
          f"every expected region exists: missing "
          f"{sorted(set(EXPECTED) - seen)}")
    clean = [f"{v}:{r.name}" for v, (_, rs) in result.items() for r in rs
             if r.category in ("rebuilt", "text") and not r.differ]
    print(f"  ({len(clean)} rebuilt or text files identical in place)")
    total = sum(r.differ for _, rs in result.values() for r in rs)
    size = sum(r.size for _, rs in result.values() for r in rs)
    check(total == TOTAL_DIFFER and size == TOTAL,
          f"the set: {size - total} of {size} bytes identical, "
          f"{total} differ")

    print("=== the boot byte is FORMATTER.DATA's ===")
    fmt = (mkdiskset.A / mkdiskset.BOOT_FROM).read_bytes()
    apple3 = PascalDisk.from_file(mkdiskset.DISKS["APPLE3"])
    shipped_fmt = apple3.read_file("FORMATTER.DATA")
    fmt_off = [i - 3 * BLOCK for i in range(3 * BLOCK, 5 * BLOCK)
               if fmt[i] != shipped_fmt[i]]
    for vol, (image, _) in result.items():
        ours = PascalDisk(image).read_blocks(0, 2)
        theirs = PascalDisk.from_file(mkdiskset.DISKS[vol]).read_blocks(0, 2)
        off = [i for i in range(2 * BLOCK) if ours[i] != theirs[i]]
        check(off == fmt_off and theirs == shipped_fmt[3 * BLOCK:5 * BLOCK],
              f"{vol}: boot differs at {off}, FORMATTER.DATA blocks 3-4 at "
              f"{fmt_off}; Apple's boot is Apple's FORMATTER.DATA's")

    print("=== the rest is residue ===")
    for vol, (image, _) in result.items():
        apple = PascalDisk.from_file(mkdiskset.DISKS[vol])
        live = (len(apple.directory()) + 1) * 26
        ours = PascalDisk(image).read_blocks(2, 4)
        theirs = apple.read_blocks(2, 4)
        off = [i for i in range(len(ours)) if ours[i] != theirs[i]]
        check(off and min(off) >= live,
              f"{vol}: directory differs only past the live entries "
              f"(byte {live} on), first at {min(off) if off else None}")
    apple2 = PascalDisk.from_file(mkdiskset.DISKS["APPLE2"])
    raw = apple2.read_blocks(2, 4)
    dead = raw[8 * 26:9 * 26]
    check(dead[0:6] == bytes((187, 0, 188, 0, 4, 0))
          and dead[7:18] == b"LINKER.INFO",
          f"APPLE2's dead entry 8 is LINKER.INFO on block 187: {dead!r}")
    _, regions = result["APPLE2"]
    free = [r for r in regions if r.category == "free" and r.differ]
    image2 = PascalDisk(result["APPLE2"][0])
    blocks = {r.first + i for r in free for i in range(r.blocks)
              if image2.read_block(r.first + i) != apple2.read_block(r.first + i)}
    check(blocks == {187} and apple2.read_block(187).startswith(b"FORMATDI"),
          f"APPLE2's free space differs only in block 187, which holds "
          f"linker records for FORMATDI: {sorted(blocks)}")

    print()
    if fail:
        print(f"disk set: {len(fail)} check(s) failed")
        return 1
    print(f"disk set: {TOTAL - TOTAL_DIFFER} of {TOTAL} bytes identical, "
          f"every difference accounted for")
    print("diskset-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
