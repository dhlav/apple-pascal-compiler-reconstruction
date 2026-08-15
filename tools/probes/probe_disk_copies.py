"""Are the evidence disks' codefiles sound, and do the duplicates agree?

Two boot disks joined `evidence/` after the two program disks, and between
them the four images carry `SYSTEM.COMPILER` twice per release. That is an
opportunity and a hazard: a second copy corroborates the artifact everything
here is built on, or it disagrees with it, and either way the answer should
not be assumed.

Two tests, over every codefile on every disk.

  * **Duplicate files must be byte-identical.** Where they are not, the
    difference is reported rather than averaged away.
  * **Every branch must land on an instruction boundary inside its own
    procedure.** This is a much sharper check than the linear-sweep test in
    `validate_pcode.py`: a sweep re-synchronises after a few bad bytes and
    still lands on the end address, so it passes on corrupted code. A jump
    target does not re-synchronise. Across roughly 1400 procedures on the
    four disks, exactly one fails.

What it found: 1.1's `SYSTEM.COMPILER` is byte-identical on both its disks,
and 1.3's is **not** -- the copy on the APPLE0 boot image differs from the
APPLE2 one in seven bytes inside `BODY3`, and it is the boot copy that is
wrong (finding 47). Every other codefile on that same disk is clean, so it
is a damaged sector in that image and not a fault in the reader.
"""
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.pcode import disassemble, sweep_exit

ROOT = Path(__file__).resolve().parents[2]
DISKS = ROOT / "evidence" / "disks"

# The one known bad site, so a *new* one is a failure rather than noise.
KNOWN_BAD = {
    ("Apple II Pascal 1.3 APPLE0_ 680-0282-A.dsk", "SYSTEM.COMPILER",
     "BODY3", 1, 0x0339),
}
# Which release each image belongs to. Copies of a file must agree within a
# release; across releases they are different programs and are expected to
# differ.
RELEASE = {
    "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk": "1.1",
    "UCSD Pascal 1.1_0.dsk": "1.1",
    "Apple II Pascal 1.3 APPLE0_ 680-0282-A.dsk": "1.3",
    "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk": "1.3",
}


def codefiles(img: Path):
    d = PascalDisk.from_file(img)
    for e in d.directory():
        raw = d.read_blocks(e.first_block, e.blocks)
        try:
            cf = CodeFile(raw)
        except Exception:
            continue
        if cf.segments:
            yield e, raw[:e.size], cf


def main() -> int:
    bad, checked = [], 0

    def check(cond, msg):
        nonlocal checked
        checked += 1
        if not cond:
            bad.append(msg)

    seen: dict[str, list[tuple[str, str]]] = {}
    found_bad = set()
    total_procs = 0

    imgs = sorted(DISKS.glob("*.dsk"))
    check(len(imgs) == 4, f"{len(imgs)} disk images in evidence, expected 4")

    for img in imgs:
        for e, raw, cf in codefiles(img):
            seen.setdefault(e.name, []).append(
                (img.name, hashlib.sha256(raw).hexdigest()))
            for seg in cf.segments:
                for p in seg.pcode_procedures:
                    if not p.consistent:
                        continue
                    try:
                        body, ok = disassemble(seg.data, p.enter_ic,
                                               p.exit_ic, p.jtab)
                        ex, _ = sweep_exit(seg.data, p.exit_ic,
                                           p.jtab - 8, p.jtab)
                    except Exception:
                        bad.append(f"{img.name}/{e.name} {seg.name}.{p.number}"
                                   f": does not disassemble")
                        continue
                    total_procs += 1
                    check(ok, f"{img.name}/{e.name} {seg.name}.{p.number}: "
                              f"sweep does not land on the end")
                    starts = {i.addr for i in body + ex}
                    for i in body + ex:
                        t = i.target
                        if t is None:
                            continue
                        if p.enter_ic <= t <= p.jtab - 8 and t in starts:
                            continue
                        site = (img.name, e.name, seg.name, p.number, i.addr)
                        found_bad.add(site)
                        if site not in KNOWN_BAD:
                            bad.append(f"{img.name}/{e.name} {seg.name}."
                                       f"{p.number}@${i.addr:04X}: {i.text} "
                                       f"does not land on an instruction")

    print(f"{len(imgs)} disks, {len(seen)} distinct codefile names, "
          f"{total_procs} procedures checked")

    check(found_bad == KNOWN_BAD,
          f"bad branch targets are {sorted(found_bad)}, expected exactly "
          f"{sorted(KNOWN_BAD)}")
    pairs = 0
    for name, copies in sorted(seen.items()):
        for rel in ("1.1", "1.3"):
            here = [(d, h) for d, h in copies if RELEASE[d] == rel]
            if len(here) < 2:
                continue
            pairs += 1
            digests = {h for _, h in here}
            where = " and ".join(d for d, _ in here)
            if (name, rel) == ("SYSTEM.COMPILER", "1.3"):
                # The one known disagreement, and it is a finding, not noise.
                check(len(digests) == 2,
                      f"1.3's two SYSTEM.COMPILER copies now agree; finding 47 "
                      f"says they differ in seven bytes inside BODY3")
                continue
            check(len(digests) == 1, f"{rel} {name} differs between {where}")
    # SYSTEM.COMPILER is the only file each release ships on both of its
    # disks; everything else appears once. So there are exactly two pairs,
    # and if that stops being true the grouping above is wrong.
    check(pairs == 2,
          f"{pairs} same-release duplicate pairs found, expected 2 "
          f"(SYSTEM.COMPILER in each release)")

    if bad:
        print("\n".join(x for x in bad if x))
        return 1
    print(f"{checked} checks, all passed")
    print("disk-copies-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
