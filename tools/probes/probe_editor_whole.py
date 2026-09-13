"""SYSTEM.EDITOR, the whole file, byte for byte.

src/pascal/programs/1.3/EDITOR.text compiled by Apple's compiler
(acceptance/2026-09-13-editor-complete), then segments 1 and 7 to 12
copied into slots 1 to 7 of a fresh codefile by Apple's LIBRARY.CODE
with the copyright notice -- the release step finding 267 found for
every system program, here with a slot remap (finding 272).

Claims, each of which the binary can fail:

  1. **EDLIB.CODE equals shipped SYSTEM.EDITOR in all 25600 bytes.**
     A copy with one byte changed must be caught, or the comparison is
     not looking.
  2. **Every slot is the reconstruction's bytes**: compile segment n and
     shipped slot m are the same bytes for each of the seven pairs, and
     each holds the procedure count Apple's does.
  3. **The Librarian did its part, and the remap was needed**: the
     compile alone is not Apple's file -- PASCALSY in slot 0, NUM2..NUM6
     in slots 2 to 6, INITIALI in slot 7 -- so copying slot for slot
     would have put a dummy segment where Apple has INITIALI.
  4. **The two over-width source lines are the ones that must be**: the
     only lines over 80 columns are lone string literals, each a
     79-character prompt -- 81 columns with its quotes alone -- that
     appears with length byte 79 in Apple's INITIALI segment.
  5. **The ancestor is the one recorded**: the UCSD II.0 editor source in
     evidence/reference/ucsd-ii0-editor still has the hashes its
     PROVENANCE.md gives, so finding 272's comparisons stay checkable.
  6. **The verified source is the source in the tree**: the EDITOR.text
     kept with the run equals src/, line endings aside.
"""
import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from a2pascal.disk import PascalDisk
from a2pascal.srcfmt import WIDTH, over_width
from oscmp import DISKS_13

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "acceptance" / "2026-09-13-editor-librarian" / "EDLIB.CODE"
COMPILE = ROOT / "acceptance" / "2026-09-13-editor-complete"
INPUT = COMPILE / "EDIT13.CODE"
KEPT_SOURCE = COMPILE / "EDITOR.text"
SOURCE = ROOT / "src" / "pascal" / "programs" / "1.3" / "EDITOR.text"
TARGET = "SYSTEM.EDITOR"
NOTICE = (b"COPYRIGHT 1979,1980,1983-1985 APPLE COMPUTER, INC. "
          b"ALL RIGHTS RESERVED")
SIZE = 25600
# compile slot -> shipped slot, segment name, procedure count
PAIRS = [(1, 1, b"EDITOR  ", 35), (7, 2, b"INITIALI", 7),
         (8, 3, b"OUT     ", 4), (9, 4, b"COPYFILE", 11),
         (10, 5, b"ENVIRONM", 5), (11, 6, b"PUTSYNTA", 2),
         (12, 7, b"EDITCORE", 65)]
REFERENCE = ROOT / "evidence" / "reference" / "ucsd-ii0-editor"
REFERENCE_SHA256 = {
    "command.text":
        "42bc8305456e1171ebe479043d2960c3b3d4ad618314f796d06b77cd8182930e",
    "copyfile.text":
        "f126cd4c88126ee3fde78aae463dd7ddf9a2074b013ecbc4539d7954fdec2c33",
    "environ.text":
        "2d3f0c6d0cfe929a702ab70b6e638f5827a74eebb8514eb5b260dfda668965ea",
    "find.text":
        "9a46ad981a0c895cc402a5512b11ba706e6c64b134f63c07f29aa75c83856f53",
    "head.text":
        "3b3e108332549fa60ca8dad215e1bc780f511a4eced423afa9560279a2e6237c",
    "init.text":
        "697f943e51edade879a5f871195415302bbae5021a3ac6e1dbfc6baa745e1a3c",
    "insertit.text":
        "f04010ba2c5e4b9b03932f02e836b254c93bdee3d2aaf0025f4f4874f264728a",
    "main.text":
        "62740389c55edee87209879460622143a16137a40e051e672e78070198dbe917",
    "misc.text":
        "012a1ee2a05bc4532d8a744c9ac76a0f08953b5122ff9a63fdcc3e70f9239bc8",
    "moveit.text":
        "32dc957248013c5e5fd583f55ea4e17b00c2c816b1c64a89b70e747a104be524",
    "out.text":
        "54881c58f102e9603045a44eb149c9c7e021f2a8679e4ad413e9a920d9058352",
    "putsyntax.text":
        "033b20d2fddec7bddd6b604358ea9c7774b9e57b0c561ff14760d69e2cf9bb43",
    "user.text":
        "884e3ff130a6ca42b00ab2e2caa656d72e957e2394f3de5d12888655f3477806",
    "util.text":
        "45195fb1697c8c90b214fc0da63f4c2cbe9f9277f7fd154c1dbb52d9eff9515e",
}

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


def words(b: bytes, off: int, n: int) -> list[int]:
    return [b[off + 2 * i] | b[off + 2 * i + 1] << 8 for i in range(n)]


def segment(b: bytes, slot: int) -> bytes:
    addr, leng = words(b, 4 * slot, 2)
    return b[addr * 512: addr * 512 + leng]


def name(b: bytes, slot: int) -> bytes:
    return b[0x40 + 8 * slot: 0x48 + 8 * slot]


def differing(a: bytes, b: bytes) -> list[int]:
    return ([i for i in range(min(len(a), len(b))) if a[i] != b[i]]
            + list(range(min(len(a), len(b)), max(len(a), len(b)))))


def main() -> int:
    for p in (RUN, INPUT, KEPT_SOURCE, SOURCE):
        if not p.exists():
            print(f"{p} is missing -- acceptance runs are kept verbatim")
            return 1
    apple = shipped(TARGET)
    ours = RUN.read_bytes()
    compiled = INPUT.read_bytes()

    print("=== the Librarian's output against Apple's shipped file ===")
    check(len(ours) == len(apple) == SIZE,
          f"both are {len(apple)} bytes, 50 blocks (ours {len(ours)})")
    diff = differing(ours, apple)
    check(not diff, f"every byte identical ({len(diff)} differ"
                    + (f", first at {diff[0]}" if diff else "") + ")")
    where = words(ours, 4 * 7, 1)[0] * 512 + 5000
    mutant = bytearray(ours)
    mutant[where] ^= 0x01
    check(differing(bytes(mutant), apple) == [where],
          "a copy with one EDITCORE byte flipped is caught, at that byte")
    check(ours[0:4] == b"\x00\x00\x00\x00" and name(ours, 0) == b" " * 8,
          "slot 0 is blank: no address, no length, no name")
    check(ours[432] == len(NOTICE) and ours[433:433 + len(NOTICE)] == NOTICE,
          f"the notice is a Pascal string, length byte {len(NOTICE)} first")

    print("=== every slot is the reconstruction's own bytes ===")
    for src, dst, segname, nproc in PAIRS:
        mine = segment(compiled, src)
        check(bool(mine) and name(compiled, src) == segname
              and mine == segment(ours, dst) == segment(apple, dst)
              and mine[-1] == nproc,
              f"{segname.decode().strip()}: compile slot {src} == "
              f"Librarian slot {dst} == shipped slot {dst} "
              f"({len(mine)} bytes, {mine[-1] if mine else 0} procedures)")

    print("=== the compile alone was not Apple's file ===")
    check(compiled[64:72] == b"PASCALSY" and compiled[432] == 0,
          "EDIT13.CODE has PASCALSY in slot 0 and no notice")
    dummies = [name(compiled, s) for s in range(2, 7)]
    check(dummies == [f"NUM{s}    ".encode() for s in range(2, 7)]
          and segment(compiled, 2) != segment(apple, 2),
          "slots 2 to 6 hold NUM2..NUM6, so a slot-for-slot copy would "
          "not be Apple's slot 2")

    print("=== the only over-width lines are 79-character literals ===")
    text = SOURCE.read_bytes().replace(b"\r\n", b"\n").decode("ascii")
    lines = text.split("\n")
    long = [ln for ln in lines if len(ln) > WIDTH]
    init = segment(apple, 2)
    found = [ln for ln in long
             if re.fullmatch(r"'[^']{79}';", ln)
             and bytes([79]) + ln[1:80].encode() in init]
    check(len(long) == 2 and found == long and not over_width(lines),
          f"{len(long)} lines over {WIDTH} columns, {len(found)} of them a "
          "lone literal Apple's INITIALI holds with length byte 79")

    print("=== the ancestor is the one recorded ===")
    # Hashed with LF line endings: the working copy carries CRLF.
    got = {n: hashlib.sha256((REFERENCE / n).read_bytes()
                             .replace(b"\r\n", b"\n")).hexdigest()
           for n in REFERENCE_SHA256 if (REFERENCE / n).exists()}
    check(got == REFERENCE_SHA256,
          f"UCSD II.0 editor source: {len(got)} of {len(REFERENCE_SHA256)} "
          "files present with their recorded SHA-256")

    print("=== the verified source is the source in the tree ===")
    kept = KEPT_SOURCE.read_bytes().replace(b"\r\n", b"\n")
    tree = SOURCE.read_bytes().replace(b"\r\n", b"\n")
    check(kept == tree, "acceptance EDITOR.text equals "
                        "src/pascal/programs/1.3/EDITOR.text")

    print()
    if fail:
        print(f"editor whole-file: {len(fail)} check(s) failed")
        return 1
    print("SYSTEM.EDITOR: 25600 of 25600 bytes, by Apple's compiler and "
          "Librarian")
    print("editor-whole-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
