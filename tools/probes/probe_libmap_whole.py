"""LIBMAP.CODE, the whole segment, and Apple's own names for its globals.

src/pascal/programs/1.3/LIBMAP.text compiled by Apple's compiler
(acceptance/2026-09-12-libmap-complete), src/native/SEARCH.TEXT assembled
by Apple's assembler, and the two linked by Apple's Linker
(acceptance/2026-09-12-libmap-linked). LIBMAP is an ordinary PROGRAM: the
shipped file is the Linker's output, slot 0, no notice, no Librarian.

Claims, each of which the binary can fail:

  1. **The Linker's output equals shipped LIBMAP.CODE through the end of
     the segment**: block 0 and all 4788 segment bytes, native IDSEARCH
     included. The last block's tail is slack (CLAUDE.md), and the check
     is shown to cover exactly the bytes before it and none after.
  2. **The link did its job**: the compile alone is HOSTSEG with p-code
     machine type, and the output is LINKED 6502, as shipped.
  3. **Apple's slack names the globals** (finding 270c). Apple's tail
     holds compiler identifier-table nodes, each an 8-character name then
     seven words, the last being the variable's offset. Every node there
     must match a PUBLDEF in our compile's own link info, same name and
     same offset. FLIPPED, VERSION and MACHKIND are Apple's additions and
     were placeholders until this was read.
  4. **The verified source is the source in the tree.**
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from a2pascal.disk import PascalDisk
from oscmp import DISKS_13

ROOT = Path(__file__).resolve().parents[2]
COMPILE = ROOT / "acceptance" / "2026-09-12-libmap-complete"
LINKED = ROOT / "acceptance" / "2026-09-12-libmap-linked"
INPUT = COMPILE / "LIBMAPT.CODE"
RUN = LINKED / "LIBMAPL.CODE"
KEPT_SOURCE = COMPILE / "LIBMAP.text"
SOURCE = ROOT / "src" / "pascal" / "programs" / "1.3" / "LIBMAP.text"
TARGET = "LIBMAP.CODE"
SEGLEN = 4788
SEGEND = 512 + SEGLEN
NPROC = 12
PUBLDEF = 7
EXPECTED_NODES = {"SEGTBL": 3, "FP": 259, "MAPFILE": 299, "FIRSTTIM": 600,
                  "LISTREFS": 601, "LISTMAP": 602, "FLIPPED": 603,
                  "VERSION": 604, "MACHKIND": 636}

fail = []


def check(ok: bool, label: str) -> None:
    print(("  ok   " if ok else "  FAIL ") + label)
    if not ok:
        fail.append(label)


def shipped(name: str) -> bytes:
    for fname in DISKS_13:
        d = PascalDisk.from_file(ROOT / "evidence" / "disks" / fname)
        try:
            e = d.find(name)
        except Exception:
            continue
        if e is not None:
            return bytes(d.read_blocks(e.first_block, e.blocks))
    raise SystemExit(f"{name} is on none of the 1.3 disks")


def word(b: bytes, off: int) -> int:
    return b[off] | b[off + 1] << 8


def differing(a: bytes, b: bytes) -> list[int]:
    return ([i for i in range(min(len(a), len(b))) if a[i] != b[i]]
            + list(range(min(len(a), len(b)), max(len(a), len(b)))))


def is_name(b: bytes) -> bool:
    s = b.rstrip(b" ")
    return (len(b) == 8 and 0 < len(s) and chr(s[0]).isupper()
            and all(chr(c).isupper() or chr(c).isdigit() or c == 0x5F
                    for c in s))


def slack_nodes(b: bytes) -> dict[str, int]:
    """Identifier nodes for level-1 variables in the tail: name, then
    LLINK, RLINK, IDTYPE, NEXT, KLASS=3, VLEV=1, VADDR."""
    out = {}
    for o in range(SEGEND, len(b) - 22 + 1):
        if is_name(b[o:o + 8]) and word(b, o + 16) == 3 \
                and word(b, o + 18) == 1:
            out[b[o:o + 8].decode().rstrip()] = word(b, o + 20)
    return out


def publdefs(b: bytes) -> dict[str, int]:
    """PUBLDEF records in the compile's link info, which follows the
    segment on the next block boundary and ends at an EOFMARK."""
    addr, leng = word(b, 0), word(b, 2)
    o = (addr * 512 + leng + 511) // 512 * 512
    out = {}
    while o + 16 <= len(b):
        name, litype = b[o:o + 8], word(b, o + 8)
        if litype == 0:
            break
        if litype == PUBLDEF:
            out[name.decode().rstrip()] = word(b, o + 10)
        o += 16
    return out


def main() -> int:
    for p in (RUN, INPUT, KEPT_SOURCE, SOURCE):
        if not p.exists():
            print(f"{p} is missing -- acceptance runs are kept verbatim")
            return 1
    apple = shipped(TARGET)
    ours = RUN.read_bytes()
    compiled = INPUT.read_bytes()

    print("=== the Linker's output against Apple's shipped file ===")
    check(len(ours) == len(apple) == 5632,
          f"both are {len(apple)} bytes, 11 blocks (ours {len(ours)})")
    check(word(apple, 0) == 1 and word(apple, 2) == SEGLEN
          and word(ours, 2) == SEGLEN,
          f"slot 0 holds the segment at block 1, {SEGLEN} bytes, "
          f"ending at byte {SEGEND}")
    diff = differing(ours, apple)
    before = [i for i in diff if i < SEGEND]
    check(not before, f"block 0 and every segment byte identical "
                      f"({len(before)} differ before {SEGEND})")
    check(all(i >= SEGEND for i in diff),
          f"the {len(diff)} differing bytes are all tail slack")
    mutant = bytearray(ours)
    mutant[SEGEND - 1] ^= 0x01
    check(SEGEND - 1 in differing(bytes(mutant), apple),
          "a flip in the segment's last byte is caught")
    check(apple[SEGLEN - 16 + 512] == ours[SEGLEN - 16 + 512]
          and ours[SEGEND - 1] == NPROC,
          f"the segment ends with its dictionary: {NPROC} procedures")
    check(apple[64:72] == ours[64:72] == b"LIBMAP  "
          and apple[432] == ours[432] == 0,
          "named LIBMAP in slot 0, no notice: not the Librarian's file")

    print("=== the link did its job ===")
    check(word(compiled, 192) == 1 and (word(compiled, 256) >> 8) & 15 == 2,
          "the compile alone is HOSTSEG, machine type 2 (p-code)")
    check(word(ours, 192) == word(apple, 192) == 0
          and (word(ours, 256) >> 8) & 15 == 7,
          "the output is LINKED, machine type 7 (6502), as shipped")

    print("=== Apple's slack names the globals ===")
    nodes = slack_nodes(apple)
    check(nodes == EXPECTED_NODES,
          f"Apple's tail holds {len(nodes)} variable nodes: "
          + ", ".join(f"{k} {v}" for k, v in sorted(nodes.items(),
                                                     key=lambda x: x[1])))
    ours_defs = publdefs(compiled)
    wrong = {k: (v, ours_defs.get(k)) for k, v in nodes.items()
             if ours_defs.get(k) != v}
    check(bool(nodes) and not wrong,
          "each is a global of our compile at the same offset"
          + (f" (mismatch: {wrong})" if wrong else ""))
    check(ours_defs.get("I") == 756 and b"I       " in apple[SEGEND:],
          "I, whose offset runs past the file's end, is our word 756")
    renamed = dict(ours_defs, FLIPPED=999)
    check(any(renamed.get(k) != v for k, v in nodes.items()),
          "a global at the wrong offset would be caught")
    check(not slack_nodes(ours),
          "our own tail holds no such nodes: the names are Apple's")

    print("=== the verified source is the source in the tree ===")
    kept = KEPT_SOURCE.read_bytes().replace(b"\r\n", b"\n")
    tree = SOURCE.read_bytes().replace(b"\r\n", b"\n")
    check(kept == tree, "acceptance LIBMAP.text equals "
                        "src/pascal/programs/1.3/LIBMAP.text")

    print()
    if fail:
        print(f"libmap whole-file: {len(fail)} check(s) failed")
        return 1
    print(f"LIBMAP.CODE: {SEGEND} of {SEGEND} bytes before the slack, by "
          "Apple's compiler, assembler and Linker")
    print("libmap-whole-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
