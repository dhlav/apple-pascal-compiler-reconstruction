"""Does lift.py's native signature table say what the source says?

`NATIVE_SIG` supplies the one thing a codefile does not record: how many
words the caller pushes for a native procedure (finding 100e). Most of its
entries claim to come from the `.PROC` and `.FUNC` declarations in
`src/native/`, and a table that claims a provenance it no longer has is
worse than no table -- so this reads those declarations back and requires
them to agree, entry for entry.

The convention is the caller's, not the assembler's: `words` counts the
parameter words plus two more for a function's result space. Assembly source
declares only the parameters, so a `.FUNC` has to come out two higher here
than it reads there. That is the whole content of the check, and it fails if
either side changes without the other.

APPLESTUFF's KEYPRESS is checked differently and deliberately. It is native
in 1.1 and p-code in 1.3, so there is no assembly for it; what stands in for
the source is 1.3's own copy of the same interface procedure, whose
attribute table gives the parameter size directly.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.lift import NATIVE_SIG
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "native"
LIB13 = ROOT / "evidence" / "disks" / \
    "Apple II Pascal 1.3 APPLE1_ 680-0283-A.dsk"

# file -> segment, and the procedure number each declared name carries.
SOURCE = {
    "SEARCH.TEXT": ("PASCALCO", {"IDSEARCH": 2, "TREESEARCH": 3}),
    "APPLESTF.TEXT": ("APPLESTU", {"PADDLE": 2, "BUTTON": 3, "TTLOUT": 4,
                                   "RANDOM": 6, "RANDOMIZE": 7, "NOTE": 8}),
    "TURTLEGR.TEXT": ("TURTLEGR", {"SCREENBIT": 15, "DRAWBLOCK": 16,
                                   "MOVEABS": 20, "MOVEREL": 21,
                                   "FILLIT": 22, "HIRES": 30, "CLIP": 31}),
    "LONGINTS.TEXT": ("LONGINTI", {"DECOPS": 4}),
    "FORMATTR.TEXT": ("FORMATTE", {"FORMATDISK": 2}),
}
# Private to their own assembly, never reached by a CXP, so no entry is
# wanted; and the long-integer engine pops a variable number of words.
NO_ENTRY = {("TURTLEGR", 30), ("TURTLEGR", 31), ("LONGINTI", 4)}

DECL = re.compile(r"^\s+\.(PROC|FUNC)\s+(\w+),(\d+)", re.M)


def main() -> int:
    bad, checked = [], 0

    def check(cond, msg):
        nonlocal checked
        checked += 1
        if not cond:
            bad.append(msg)

    seen = set()
    for fname, (segname, numbers) in SOURCE.items():
        path = SRC / fname
        if not path.exists():
            bad.append(f"{fname} is missing")
            continue
        decls = {m.group(2): (m.group(1), int(m.group(3)))
                 for m in DECL.finditer(path.read_text(encoding="ascii"))}
        check(set(decls) == set(numbers),
              f"{fname} declares {sorted(decls)}, expected {sorted(numbers)}")
        for name, (kind, params) in decls.items():
            if name not in numbers:
                continue
            key = (segname, numbers[name])
            if key in NO_ENTRY:
                check(key not in NATIVE_SIG,
                      f"{key} has a NATIVE_SIG entry, but it is one of the "
                      f"procedures deliberately left unsized")
                continue
            seen.add(key)
            sig = NATIVE_SIG.get(key)
            if sig is None:
                bad.append(f"{name} ({key}) is in {fname} but not NATIVE_SIG")
                checked += 1
                continue
            words, is_fn, nm = sig
            want = params + (2 if kind == "FUNC" else 0)
            check(words == want,
                  f"{name}: NATIVE_SIG says {words} words, {fname} declares "
                  f".{kind} {name},{params} which is {want}")
            check(is_fn == (kind == "FUNC"),
                  f"{name}: NATIVE_SIG says is_function={is_fn}, {fname} "
                  f"declares .{kind}")
            check(nm == name,
                  f"{key}: NATIVE_SIG names it {nm!r}, {fname} calls it "
                  f"{name!r}")

    # KEYPRESS: 1.3's p-code copy of the same interface procedure.
    d = PascalDisk.from_file(LIB13)
    e = d.find("SYSTEM.LIBRARY")
    cf = CodeFile(d.read_blocks(e.first_block, e.blocks))
    seg = next(s for s in cf.segments if s.name.strip() == "APPLESTU")
    p5 = next(q for q in seg.procedures if q.number == 5)
    check(not p5.is_native,
          "1.3's APPLESTUFF.5 is native, so it cannot stand in as the "
          "signature for 1.1's")
    check(NATIVE_SIG[("APPLESTU", 5)][0] == p5.param_size // 2,
          f"KEYPRESS: NATIVE_SIG says "
          f"{NATIVE_SIG[('APPLESTU', 5)][0]} words, 1.3's p-code copy "
          f"declares {p5.param_size // 2}")
    seen.add(("APPLESTU", 5))

    # Anything left is an entry with no source behind it. One is expected
    # -- it was read off its call site and says so. FORMATTER's used to be
    # the second; it is now backed by FORMATTR.TEXT, and the two agree.
    rest = set(NATIVE_SIG) - seen
    check(rest == {("LIBMAP", 2)},
          f"NATIVE_SIG entries with no source behind them: {sorted(rest)}, "
          f"expected only LIBMAP's")

    if bad:
        print("\n".join(bad))
        return 1
    print(f"{checked} checks, all passed")
    print("native-sig-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
