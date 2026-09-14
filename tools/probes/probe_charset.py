"""SYSTEM.CHARSET: identical, written on the 1.3 system.

acceptance/2026-09-13-charset holds the run: MAKECHRS compiled by
SYSTEM.COMPILER and run under the 1.3 system, reading CHARSET.TEXT, and
the two blocks it wrote (finding 278).

Claims, each of which the binary can fail:

  1. **All 1024 bytes are Apple's**; a flipped pixel is caught.
  2. **The text draws the glyphs upright**: read on the host with the
     layout MAKECHRS assumes (low bit left, bottom row stored first),
     CHARSET.TEXT gives Apple's file, and read the other way up it does
     not. 'A' has its apex on the top row.
  3. **The kept sources are the sources in the tree.**
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from a2pascal.disk import PascalDisk
from oscmp import DISKS_13

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "acceptance" / "2026-09-13-charset"
SOURCES = {
    "CHARSET.TEXT": ROOT / "src" / "data" / "CHARSET.TEXT",
    "MAKECHRS.text": ROOT / "src" / "pascal" / "programs" / "1.3" / "MAKECHRS.text",
}

fail = []


def check(ok: bool, label: str) -> None:
    print(("  ok   " if ok else "  FAIL ") + label)
    if not ok:
        fail.append(label)


def shipped(name: str) -> bytes:
    for fname in DISKS_13:
        d = PascalDisk.from_file(ROOT / "evidence" / "disks" / fname)
        for e in d.directory():
            if e.name == name:
                return bytes(d.read_blocks(e.first_block, e.blocks))
    raise SystemExit(f"{name} is on none of the 1.3 disks")


def lf(p: Path) -> bytes:
    return p.read_bytes().replace(b"\r\n", b"\n")


def glyphs(text: str) -> list[list[str]]:
    lines = text.splitlines()
    out = []
    for c in range(128):
        head = lines[c * 9]
        assert head.split()[:2] == ["CHR", str(c)], head
        out.append(lines[c * 9 + 1:c * 9 + 9])
    return out


def encode(rows_per_char: list[list[str]], upright: bool) -> bytes:
    out = bytearray()
    for rows in rows_per_char:
        for row in (reversed(rows) if upright else rows):
            out.append(sum(1 << i for i, ch in enumerate(row) if ch == "#"))
    return bytes(out)


def main() -> int:
    missing = [n for n in ["CHARSET.DATA", "MAKECHRS.CODE", *SOURCES]
               if not (RUN / n).exists()]
    if missing:
        print(f"missing from {RUN.name}: {missing}")
        return 1
    apple = shipped("SYSTEM.CHARSET")
    ours = (RUN / "CHARSET.DATA").read_bytes()

    print("=== SYSTEM.CHARSET against Apple's ===")
    check(len(apple) == 1024 and ours == apple, "all 1024 bytes identical")
    mutant = bytearray(ours)
    mutant[0x41 * 8 + 3] ^= 0x04
    check([i for i in range(1024) if mutant[i] != apple[i]] == [0x41 * 8 + 3],
          "a flipped pixel in 'A' is caught")

    print("=== the text draws the glyphs upright ===")
    g = glyphs(lf(SOURCES["CHARSET.TEXT"]).decode("ascii"))
    check(encode(g, upright=True) == apple,
          "CHARSET.TEXT, low bit left and bottom row first, is Apple's file")
    check(encode(g, upright=False) != apple, "the other way up it is not")
    check(g[65][0] == "..##...." and g[65][6] == "#....#.." and g[65][7] == "........",
          "'A' has its apex on the top row")

    print("=== the kept sources are the sources in the tree ===")
    for name, path in SOURCES.items():
        check(lf(RUN / name) == lf(path), f"{name} equals {path.relative_to(ROOT)}")

    print()
    if fail:
        print(f"charset: {len(fail)} check(s) failed")
        return 1
    print("SYSTEM.CHARSET: all 1024 bytes, by Apple's compiler and system")
    print("charset-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
