"""What the SEGINFO word says, and whether the disks agree with it.

SEGINFO is one word per dictionary slot at offset $100 of a codefile:
segnum in bits 0-7, mtype in 8-11, version in 13-15. Two of those three are
worth checking rather than merely reading, because a reconstruction has to
reproduce them and neither is written down in any source file.

  * mtype is 6502 exactly when the segment holds at least one native
    procedure, and pcode-lsb otherwise. This is checked across every
    segment of every codefile on all six evidence disks. It can fail: a
    segment whose native procedures were missed, or a stamp that tracked
    something else entirely, would show up here at once.

  * version is the release of the *system that wrote the file*, not of the
    source. 1.1 writes 2 and 1.3 writes 6, and it is enforced -- booted on
    1.3, C(ompile with 1.1's APPLE2 in drive 2 answers "APPLE2:
    SYSTEM.COMPILER is not version 1.3" and does nothing. So every codefile
    on a 1.3 disk should be version 6, and the ones that are not are files
    Apple shipped without rebuilding. Those are listed rather than failed:
    the point of the check is that the list stays the one finding 99 names.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile

ROOT = Path(__file__).resolve().parents[2]
DISKS = ROOT / "evidence" / "disks"

# Codefiles on the 1.3 disks that are not stamped version 6, and why
# (finding 99). BINDER, LINEFEED and SET40COLS are the 1.1 binaries; the
# assembler's PASCALIO is a linked-in unit whose stamp the Linker copied
# through; SETUP predates the field.
STALE_13 = {
    ("BINDER.CODE", "APPLEBIN"): 2,
    ("LINEFEED.CODE", "LINEFEED"): 2,
    ("SET40COLS.CODE", "SET40COL"): 2,
    ("SYSTEM.ASSMBLER", "PASCALIO"): 2,
    ("SETUP.CODE", "PASCALSY"): 0, ("SETUP.CODE", "SETUP"): 0,
    ("SETUP.CODE", "NUMBER2"): 0, ("SETUP.CODE", "NUMBER3"): 0,
    ("SETUP.CODE", "NUMBER4"): 0, ("SETUP.CODE", "NUMBER5"): 0,
    ("SETUP.CODE", "NUMBER6"): 0, ("SETUP.CODE", "NUMBER7"): 0,
    ("SETUP.CODE", "NUMBER8"): 0, ("SETUP.CODE", "NUMBER9"): 0,
    ("SETUP.CODE", "INITS"): 0, ("SETUP.CODE", "TEACHSET"): 0,
}


def main() -> int:
    bad, checked = [], 0

    def check(cond, msg):
        nonlocal checked
        checked += 1
        if not cond:
            bad.append(msg)

    for path in sorted(DISKS.glob("*.dsk")):
        is13 = "1.3" in path.name
        d = PascalDisk.from_file(path)
        for e in d.directory():
            if e.kind != "codefile":
                continue
            cf = CodeFile(d.read_blocks(e.first_block, e.blocks))
            for s in cf.segments:
                native = bool(s.native_procedures)
                check((s.mtype == "6502") == native,
                      f"{path.name} {e.name} {s.name}: mtype is {s.mtype} "
                      f"but the segment has {len(s.native_procedures)} "
                      f"native procedures")
                if not is13:
                    continue
                want = STALE_13.get((e.name, s.name), 6)
                check(s.version == want,
                      f"{path.name} {e.name} {s.name}: version {s.version}, "
                      f"expected {want} -- a 1.3 disk is version 6 unless "
                      f"finding 99 says why not")

    if bad:
        print("\n".join(bad))
        return 1
    print(f"{checked} checks, all passed")
    print("seginfo-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
