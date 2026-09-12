"""Which APPLE3 utilities did Apple actually rebuild for 1.3?

The version stamp says three of them were not (finding 99), and this is the
check that says so from the bytes rather than from the stamp alone: for
BINDER, LINEFEED and SET40COLS the 1.1 and 1.3 copies are compared byte for
byte, and the only differences allowed are inside the SEGINFO array at $100.
SETUP is required to be identical outright.

Everything past the end of a file's last meaningful byte is block slack --
whatever the drive happened to hold -- so the comparison stops at the end of
the last segment. That is not a loophole: the dictionary and the code are
both inside it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile

ROOT = Path(__file__).resolve().parents[2]
D11 = ROOT / "evidence" / "disks" / "UCSD Pascal 1.1_3.dsk"
D13 = ROOT / "evidence" / "disks" / \
    "Apple II Pascal 1.3 APPLE3_ 680-0290-A.dsk"

SEGINFO = range(0x100, 0x120)
# name -> whether the two releases' copies must be identical outright
FILES = {"BINDER.CODE": False, "LINEFEED.CODE": False,
         "SET40COLS.CODE": None, "SETUP.CODE": True}


def main() -> int:
    bad, checked = [], 0

    def check(cond, msg):
        nonlocal checked
        checked += 1
        if not cond:
            bad.append(msg)

    d11, d13 = PascalDisk.from_file(D11), PascalDisk.from_file(D13)
    names11 = {e.name for e in d11.directory()}
    for name, identical in FILES.items():
        if name not in names11:
            # SET40COLS is 1.3 only -- there is nothing to compare it with,
            # so all that can be said is what its own stamp says.
            cf = CodeFile(d13.read_file(name))
            check(all(s.version == 2 for s in cf.segments),
                  f"{name}: not on the 1.1 disk, and its version stamps are "
                  f"{[s.version for s in cf.segments]}, not 2")
            continue
        a, b = d11.read_file(name), d13.read_file(name)
        cf = CodeFile(b)
        end = max(s.block * 512 + s.length for s in cf.segments)
        diff = [i for i in range(end) if a[i] != b[i]]
        if identical:
            check(not diff,
                  f"{name}: {len(diff)} bytes differ between the releases, "
                  f"expected none")
            continue
        check(diff, f"{name}: the two releases' copies are identical, so "
                    f"there is nothing for this probe to distinguish")
        outside = [i for i in diff if i not in SEGINFO]
        check(not outside,
              f"{name}: differs outside SEGINFO at "
              f"{[hex(i) for i in outside[:8]]} -- 1.3 rebuilt it after all")
        # And the stamp itself is 1.1's, which is the actual claim.
        check(all(s.version == 2 for s in cf.segments),
              f"{name}: 1.3's copy is stamped "
              f"{[s.version for s in cf.segments]}, not 1.1's 2")

    if bad:
        print("\n".join(bad))
        return 1
    print(f"{checked} checks, all passed")
    print("stale-utils-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
