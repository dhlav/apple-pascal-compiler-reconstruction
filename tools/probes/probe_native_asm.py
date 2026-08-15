"""Does the reconstructed native source assemble back to Apple's bytes?

`src/native/SEARCH.TEXT` is the reconstruction of 1.3's `IDSEARCH` and
`TREESEARCH` in the Apple Pascal Assembler's language. The acceptance test
is `SYSTEM.ASSMBLER` itself, under an emulator (finding 44e). This probe is
the fast tier of the same test: `tools/asm6502.py` implements the subset of
the language the two routines use and emits the procedure exactly as the
Linker would lay it out -- code, four relocation tables, ENTER IC and the
procedure-number word -- and the result is compared byte for byte against
`SYSTEM.COMPILER`.

The comparison covers the whole procedure, `enter_ic` through `jtab+2`, so
it is not only the instructions that have to match: the relocation tables
have to come out with the right counts, in the right order, with the right
self-relative values. Those are generated from the source's symbolic
operands, not written down, so they fail if a single reference is written as
a constant where the original used a label -- which is the mistake this is
here to catch.

A byte comparison is a hard check, but it is not a check of *everything*.
What it does not settle: the identifiers (Apple's own names for these
labels are not recoverable), the comments, the layout, and whether Apple's
source spelled a constant `#" "` or `#20`. Those are unconstrained by the
bytes and are ours.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from asm6502 import assemble_file, AsmError
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "native" / "SEARCH.TEXT"
IMG = ROOT / "evidence" / "disks" / \
    "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk"
# procedure number in PASCALCO -> (name, kind, declared parameter words)
WANT = {2: ("IDSEARCH", "PROC", 2), 3: ("TREESEARCH", "FUNC", 3)}


def main() -> int:
    bad, checked = [], 0

    def check(cond, msg):
        nonlocal checked
        checked += 1
        if not cond:
            bad.append(msg)

    d = PascalDisk.from_file(IMG)
    e = d.find("SYSTEM.COMPILER")
    seg = CodeFile(d.read_blocks(e.first_block, e.blocks)).segment("PASCALCO")

    try:
        procs = assemble_file(SRC)
    except AsmError as e:
        print(f"{SRC.name} does not assemble:\n{e}")
        return 1
    check(len(procs) == 2,
          f"{SRC.name} declares {len(procs)} routines, expected 2")
    by_name = {p.name: p for p in procs}
    check([p.name for p in procs] == ["IDSEARCH", "TREESEARCH"],
          f"source order is {[p.name for p in procs]}; the two are linked "
          f"into PASCALCO as procedures 2 and 3 in that order")

    for num, (name, kind, words) in WANT.items():
        p = next((x for x in seg.native_procedures if x.number == num), None)
        if p is None or name not in by_name:
            bad.append(f"PASCALCO.{num} {name}: missing from disk or source")
            continue
        a = by_name[name]
        check(a.kind == kind,
              f"{name} is declared .{a.kind}, expected .{kind}")
        check(a.words == words,
              f"{name} declares {a.words} parameter words, expected {words}")

        want = seg.data[p.enter_ic:p.jtab + 2]
        got = a.image()
        check(len(got) == len(want),
              f"{name}: assembled {len(got)} bytes, disk has {len(want)}")
        if len(got) == len(want):
            diffs = [i for i, (x, y) in enumerate(zip(want, got)) if x != y]
            check(not diffs,
                  f"{name}: {len(diffs)} byte(s) differ, first at "
                  f"+${diffs[0]:04X} (${p.enter_ic + diffs[0]:04X}): disk "
                  f"{want[diffs[0]]:02x}, assembled {got[diffs[0]]:02x}"
                  if diffs else "")

        # Not implied by the byte compare on its own: that the relocation
        # entries the assembler *generated* are the ones the disk names, so a
        # coincidence of lengths cannot pass this.
        check(sorted(a.reloc) == sorted(t - p.enter_ic
                                        for t in p.reloc["procedure"]),
              f"{name}: assembler relocates {sorted(a.reloc)}, disk relocates "
              f"{sorted(t - p.enter_ic for t in p.reloc['procedure'])}")
        for kindname in ("base", "segment", "interp"):
            check(not p.reloc[kindname],
                  f"{name}: disk has {kindname}-relative entries, which the "
                  f"source has no directive to produce")

    if bad:
        print("\n".join(bad))
        return 1
    print(f"{checked} checks, all passed")
    print("native-asm-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
