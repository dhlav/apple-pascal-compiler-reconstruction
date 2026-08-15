"""The evidence disk set: is it sound, and what does `{$U-}` look like?

`evidence/disks/` holds the two three-disk sets Apple shipped, minus the
APPLE0 variants:

    APPLE1  the boot volume -- SYSTEM.APPLE (the 6502 interpreter),
            SYSTEM.PASCAL, EDITOR, FILER, LIBRARY
    APPLE2  the second drive -- SYSTEM.COMPILER, LINKER, ASSMBLER
    APPLE3  utilities, examples, and a second copy of SYSTEM.APPLE

An APPLE0 image exists for each release, carrying a merged subset. Neither
is used here, and 1.3's is a good reason why: its `SYSTEM.COMPILER` differs
from the APPLE2 one in seven bytes inside `BODY3`, and those seven bytes are
damaged -- they decode to a `UJP` past the procedure's own attribute table.
See finding 47.

Three tests over every codefile on every disk.

  * **Every branch must land on an instruction boundary inside its own
    procedure.** This is much sharper than the linear-sweep test in
    `validate_pcode.py`: a sweep re-synchronises a few bytes after damage
    and still lands on the end address, so it passes on corrupted code. A
    jump target does not re-synchronise. Over the 1490 procedures on the
    six disks that parse, it fails nowhere.
  * **Files that appear on more than one disk of the same release must be
    byte-identical.** `SYSTEM.APPLE` is on APPLE1 and APPLE3 in both
    releases, and is the same file in each.
  * **`lex = -1` marks a `{$U-}` compilation, and only that.** The manual
    (1.3, Part I ch. 12) says `(*$U-*)` "should be the first thing in the
    GOTOXY file", and `HAZELGOTO.TEXT` on APPLE3 begins with exactly that.
    So the programs whose outer block carries `$FF` are checked against the
    ones that should: the operating system in both releases, its 128K
    variant, `SETUP`, and the two GOTOXY replacements. Everything else --
    including every `SYSTEM.COMPILER` -- must not have it.

The last is what turns finding 24e from an argument out of absence into one
with a positive control: `SYSTEM.COMPILER` is not `{$U-}`, and here is what
a program that *is* looks like.
"""
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.pcode import disassemble, sweep_exit
from a2pascal.textfile import decode_text

ROOT = Path(__file__).resolve().parents[2]
DISKS = ROOT / "evidence" / "disks"

# image -> (release, volume). APPLE0 is deliberately absent from both sets.
SET = {
    "UCSD Pascal 1.1_1.dsk": ("1.1", "APPLE1"),
    "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk": ("1.1", "APPLE2"),
    "UCSD Pascal 1.1_3.dsk": ("1.1", "APPLE3"),
    "Apple II Pascal 1.3 APPLE1_ 680-0283-A.dsk": ("1.3", "APPLE1"),
    "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk": ("1.3", "APPLE2"),
    "Apple II Pascal 1.3 APPLE3_ 680-0290-A.dsk": ("1.3", "APPLE3"),
}
# Every codefile whose outer block should carry lex = -1, i.e. every program
# on these disks compiled {$U-}.
EXPECT_U_MINUS = {
    ("1.1", "SYSTEM.PASCAL"), ("1.3", "SYSTEM.PASCAL"),
    ("1.1", "SETUP.CODE"), ("1.3", "SETUP.CODE"),
    ("1.3", "128K.PASCAL"),
    ("1.1", "SOROCGOTO.CODE"), ("1.1", "HAZELGOTO.CODE"),
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

    imgs = sorted(DISKS.glob("*.dsk"))
    check({i.name for i in imgs} == set(SET),
          f"evidence/disks holds {sorted(i.name for i in imgs)}, expected "
          f"{sorted(SET)}")
    imgs = [i for i in imgs if i.name in SET]

    seen: dict[tuple[str, str], set[str]] = {}
    u_minus: set[tuple[str, str]] = set()
    total_procs = nfiles = 0

    for img in imgs:
        rel, _vol = SET[img.name]
        # SYSTEM.APPLE is a datafile -- the raw 6502 interpreter -- so it is
        # hashed from the directory rather than through CodeFile.
        disk = PascalDisk.from_file(img)
        for e in disk.directory():
            raw = disk.read_blocks(e.first_block, e.blocks)[:e.size]
            seen.setdefault((rel, e.name), set()).add(
                hashlib.sha256(raw).hexdigest())
        for e, raw, cf in codefiles(img):
            nfiles += 1
            for seg in cf.segments:
                for p in seg.procedures:
                    if p.lex_level == 255:
                        u_minus.add((rel, e.name))
                        check(p.number == 1,
                              f"{img.name}/{e.name}: lex -1 on "
                              f"{seg.name}.{p.number}, not the outer block")
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
                        check(p.enter_ic <= t <= p.jtab - 8 and t in starts,
                              f"{img.name}/{e.name} {seg.name}.{p.number}"
                              f"@${i.addr:04X}: {i.text} does not land on an "
                              f"instruction")

    print(f"{len(imgs)} disks, {nfiles} codefiles, {total_procs} procedures")

    # -- duplicates within a release --------------------------------------
    dups = {k: v for k, v in seen.items() if len(v) > 1}
    check(not dups,
          f"same-release copies differ: {sorted(k for k in dups)}")
    shared = [k for k in seen if k[1] == "SYSTEM.APPLE"]
    check(len(shared) == 2,
          f"SYSTEM.APPLE appears for {len(shared)} releases, expected 2")

    # -- {$U-} -------------------------------------------------------------
    check(u_minus == EXPECT_U_MINUS,
          f"lex -1 on {sorted(u_minus)}, expected {sorted(EXPECT_U_MINUS)}")
    for rel in ("1.1", "1.3"):
        check((rel, "SYSTEM.COMPILER") not in u_minus,
              f"{rel} SYSTEM.COMPILER is compiled with $U-, contradicting "
              f"finding 24e")
    print(f"lex = -1 on {len(u_minus)} of {nfiles} codefiles: "
          f"{sorted(n for _, n in u_minus)}")

    # The source side of the same claim: the one {$U-} program whose text is
    # on the disks says so in its first line.
    d = PascalDisk.from_file(DISKS / "UCSD Pascal 1.1_3.dsk")
    e = d.find("HAZELGOTO.TEXT")
    txt = decode_text(d.read_blocks(e.first_block, e.blocks)[:e.size])
    first = txt.strip().splitlines()[0].strip()
    check(first.upper() == "(*$U-*)",
          f"HAZELGOTO.TEXT begins {first!r}, not the (*$U-*) the manual "
          f"prescribes")
    check("PROGRAM GOXY" in txt.upper(),
          "HAZELGOTO.TEXT does not declare PROGRAM GOXY, so it is not the "
          "source of HAZELGOTO.CODE's outer block")

    if bad:
        print("\n".join(x for x in bad if x))
        return 1
    print(f"{checked} checks, all passed")
    print("disk-copies-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
