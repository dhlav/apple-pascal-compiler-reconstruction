"""SETUP.CODE: every procedure Apple's, and every other byte accounted for.

src/pascal/programs/1.3/SETUP.text -- UCSD's SETUP D1 with Apple's S.2
edits -- compiled by Apple's 1.3 compiler
(acceptance/2026-09-13-setup-s2). The whole file cannot be Apple's from
1.3 tools (finding 273), so this probe says exactly how close it is.

Claims, each of which the binary can fail:

  1. **All 54 procedures are instruction- and frame-identical**, and a
     copy with the cursor-up key's bit put back to D1's value is caught
     in exactly INITS.8 -- the comparison sees an operand.
  2. **The dictionary is Apple's except the version words**: every
     segment at the same block with the same length and name, and every
     differing byte of block 0 inside the SEGINFO words at $100-$11F,
     which Apple's file has as 0 and a 1.3 compile cannot.
  3. **Every differing byte inside a segment is alignment padding**, 0 in
     ours: the byte after an LDC's count, after an XJP's opcode, after a
     procedure's final RNP/RBP, or after the one-byte XIT stub. Apple's
     1979 compiler left stale bytes there; 1.3's writes GENBYTE(0).
  4. **Apple's S.2 is a small edit of D1**: the II.0 source in
     evidence/reference/ucsd-ii0-setup still has its recorded hash, and
     SETUP.text below its header comment differs from it only in the
     edits the header lists.
  5. **The verified source is the source in the tree.**
"""
import difflib
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from a2pascal.codefile import CodeFile
from a2pascal.pcode import disassemble, sweep_exit
from a2pascal.disk import PascalDisk
from oscmp import DISKS_13, compare, shipped_codefile

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "acceptance" / "2026-09-13-setup-s2"
OURS = RUN / "SETUPT.CODE"
KEPT_SOURCE = RUN / "SETUP.text"
SOURCE = ROOT / "src" / "pascal" / "programs" / "1.3" / "SETUP.text"
REFERENCE = ROOT / "evidence" / "reference" / "ucsd-ii0-setup" / "main.text"
REFERENCE_SHA256 = (
    "4a2a675efd24c27e87c8c0c70f58f813daf4ecfaa5a82dfdf77b8195fd00e8ad")
NPROC = 54
NPADS = 34
XIT, LDC, XJP = 0xD6, "LDC", "XJP"

fail = []


def check(ok: bool, label: str) -> None:
    print(("  ok   " if ok else "  FAIL ") + label)
    if not ok:
        fail.append(label)


def lf(p: Path) -> bytes:
    return p.read_bytes().replace(b"\r\n", b"\n")


def is_pad(seg, d: int) -> bool:
    """True if segment offset `d` is a byte the compiler emits only to
    word-align what follows it."""
    if d % 2 == 0:
        return False
    code = seg.data
    if seg.length == 16 and d == 1 and code[0] == XIT:
        return True
    p = next((p for p in seg.procedures if p.enter_ic <= d < p.jtab), None)
    if p is None:
        return False
    _, end = sweep_exit(code, p.exit_ic, p.jtab, p.jtab)
    if end is None:
        return False
    if d == end:
        return True
    insns, _ = disassemble(code, p.enter_ic, end, p.jtab)
    cover = [i for i in insns if i.addr <= d < i.addr + i.length]
    return bool(cover) and (
        (cover[0].mnemonic == LDC and d == cover[0].addr + 2)
        or (cover[0].mnemonic == XJP and d == cover[0].addr + 1))


def main() -> int:
    for p in (OURS, KEPT_SOURCE, SOURCE, REFERENCE):
        if not p.exists():
            print(f"{p} is missing")
            return 1
    raw_ours = OURS.read_bytes()
    ours = CodeFile(raw_ours)
    apple = shipped_codefile("SETUP.CODE")

    print("=== every procedure is Apple's ===")
    rows = compare(ours, apple)
    real = {k: r for k, r in rows.items() if r["present_apple"]}
    exact = [k for k, r in real.items() if r["exact"]]
    check(len(real) == NPROC and len(exact) == NPROC,
          f"{len(exact)} of {len(real)} instruction- and frame-identical")
    # D1 had the prefixed cursor-up key at bit 3 of word 47; S.2 has 2.
    seg = next(s for s in ours.segments if s.name == "INITS")
    needle = b"PREFIXED[KEY FOR MOVING CURSOR UP]"
    at = seg.data.find(needle) + len(needle)
    where = seg.data.find(bytes([47, 2]), at)
    mutant = bytearray(raw_ours)
    mutant[seg.block * 512 + where + 1] = 3
    bad = [k for k, r in compare(CodeFile(bytes(mutant)), apple).items()
           if r["present_apple"] and not r["exact"]]
    check(where > at and bad == ["INITS.8"],
          f"D1's cursor-up bit put back is caught in exactly {bad}")

    print("=== the dictionary is Apple's but for the version words ===")
    a_segs = {s.name: s for s in apple.segments if s.length}
    o_segs = {s.name: s for s in ours.segments if s.length}
    check(a_segs.keys() == o_segs.keys() and all(
              (a_segs[n].index, a_segs[n].block, a_segs[n].length)
              == (o_segs[n].index, o_segs[n].block, o_segs[n].length)
              for n in a_segs),
          f"all {len(a_segs)} segments in the same slot, block and length")
    disk_apple = b""
    for fname in DISKS_13:
        d = PascalDisk.from_file(ROOT / "evidence" / "disks" / fname)
        try:
            e = d.find("SETUP.CODE")
        except Exception:
            continue
        if e is not None:
            disk_apple = bytes(d.read_blocks(e.first_block, e.blocks))
            break
    b0 = [i for i in range(512) if disk_apple[i] != raw_ours[i]]
    check(bool(b0) and all(0x100 <= i < 0x120 for i in b0)
          and disk_apple[0x100:0x120] == bytes(32),
          f"block 0: {len(b0)} bytes differ, all in SEGINFO, which Apple "
          "has as 0")

    print("=== every other differing segment byte is padding ===")
    pads, other = 0, []
    for n, sa in a_segs.items():
        so = o_segs[n]
        for d in range(sa.length):
            if sa.data[d] != so.data[d]:
                if is_pad(sa, d) and so.data[d] == 0:
                    pads += 1
                else:
                    other.append(f"{n}+{d:#x}")
    check(pads == NPADS and not other,
          f"{pads} differing bytes, all alignment pads that are 0 in ours "
          f"({len(other)} not: {other[:5]})")
    seg1 = a_segs["SETUP"]
    code_byte = next(i for i in range(1, seg1.length, 2)
                     if not is_pad(seg1, i))
    check(not is_pad(seg1, 0) and not is_pad(seg1, code_byte),
          "and the pad test rejects an ordinary code byte")

    print("=== S.2 is a small edit of UCSD's D1 ===")
    check(hashlib.sha256(lf(REFERENCE)).hexdigest() == REFERENCE_SHA256,
          "UCSD II.0 SETUP source has its recorded SHA-256")
    tree = lf(SOURCE).decode("ascii").split("\n")
    body = tree[next(i for i, ln in enumerate(tree)
                     if ln.startswith("(*")):]
    d1 = lf(REFERENCE).decode("ascii").split("\n")
    changed = [ln for ln in difflib.unified_diff(d1, body, lineterm="", n=0)
               if ln[:1] in "+-" and ln[:3] not in ("+++", "---")]
    # Measured on the first S.2 compile: the six edits the header lists.
    # Any further edit to the UCSD text moves this number.
    check(len(changed) == 39,
          f"{len(changed)} lines added or removed below the header, the "
          "39 the listed edits account for")

    print("=== the verified source is the source in the tree ===")
    check(lf(KEPT_SOURCE) == lf(SOURCE),
          "acceptance SETUP.text equals src/pascal/programs/1.3/SETUP.text")

    print()
    if fail:
        print(f"setup exact: {len(fail)} check(s) failed")
        return 1
    print("SETUP.CODE: 54 of 54 procedures; every other difference is a "
          "version word or a pad")
    print("setup-exact-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
