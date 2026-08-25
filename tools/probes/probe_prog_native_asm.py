"""Do the programs' reconstructed native sources assemble back to Apple's bytes?

The companion to `probe_lib_native_asm.py`, which does the same for
`SYSTEM.LIBRARY`, and to `probe_native_asm.py`, which does it for
`SYSTEM.COMPILER`. This one covers the native halves of the utilities on
the 1.3 disks.

A utility differs from the library in one way that matters here: its native
procedure is `EXTERNAL` in the Pascal and the Linker joins the two, so the
procedure sits in the same segment as the p-code rather than in a segment of
its own. Nothing about the layout changes -- code, four relocation tables,
ENTER IC and the attribute word -- and the comparison is the same one, over
the whole procedure from `enter_ic` to `jtab + 2`.

The acceptance test is `SYSTEM.ASSMBLER` under the emulator (finding 44e).
This is the fast tier of it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from asm6502 import assemble_file, AsmError
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile, RELOC_KINDS

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "native"
DISKS = ROOT / "evidence" / "disks"

# (disk, codefile, source, segment, procedure, name, kind, parameter words)
UNITS = [
    ("Apple II Pascal 1.3 APPLE3_ 680-0290-A.dsk", "FORMATTER.CODE",
     "FORMATTR.TEXT", "FORMATTE", 2, "FORMATDISK", "FUNC", 1),
]


def main() -> int:
    bad, checked = [], 0

    def check(cond, msg):
        nonlocal checked
        checked += 1
        if not cond:
            bad.append(msg)

    for dsk, code, fname, segname, num, name, kind, words in UNITS:
        d = PascalDisk.from_file(DISKS / dsk)
        cf = CodeFile(d.read_file(code))
        seg = next((s for s in cf.segments
                    if s.name.strip() == segname), None)
        if seg is None:
            bad.append(f"{code}: no segment {segname}")
            continue
        p = next((q for q in seg.native_procedures if q.number == num), None)
        if p is None:
            bad.append(f"{code} {segname}.{num} is not native on the disk")
            continue

        try:
            procs = assemble_file(SRC / fname, bases={name: p.enter_ic})
        except AsmError as ex:
            bad.append(f"{fname} does not assemble:\n{ex}")
            continue
        check(len(procs) == 1,
              f"{fname} declares {[q.name for q in procs]}, expected just "
              f"{name}")
        a = procs[0]
        check(a.name == name, f"{fname} declares {a.name}, expected {name}")
        check(a.kind == kind,
              f"{name} is declared .{a.kind}, expected .{kind}")
        check(a.words == words,
              f"{name} declares {a.words} parameter words, expected {words}")
        check(seg.data[p.jtab] == 0,
              f"{name}: PROCEDURE NUMBER is {seg.data[p.jtab]}, and 0 is "
              f"what marks a procedure native")

        # RELOCSEG. A program has no data segment of its own, so
        # base-relative relocation goes through the BASE register and the
        # manual's rule (IV-36) gives 0. It is checked, not read back.
        check(seg.data[p.jtab + 1] == 0,
              f"{name}: RELOCSEG on the disk is {seg.data[p.jtab + 1]}, and "
              f"a program relocates through BASE, which is 0")

        disk = seg.data[p.enter_ic:p.jtab + 2]
        got = a.image(relocseg=seg.data[p.jtab + 1])
        check(len(got) == len(disk),
              f"{name}: assembled {len(got)} bytes, disk has {len(disk)}")
        if len(got) == len(disk):
            diffs = [i for i, (x, y) in enumerate(zip(disk, got)) if x != y]
            check(not diffs,
                  f"{name}: {len(diffs)} byte(s) differ, first at "
                  f"+${diffs[0]:04X}: disk {disk[diffs[0]]:02x}, assembled "
                  f"{got[diffs[0]]:02x}" if diffs else "")

        # Not implied by the byte compare: that the entries the assembler
        # generated are the ones the disk names, kind by kind.
        mine = {"procedure": a.reloc, "segment": a.segreloc,
                "interp": a.interpreloc, "base": []}
        for k in RELOC_KINDS:
            check(sorted(mine[k]) == sorted(t - p.enter_ic
                                            for t in p.reloc[k]),
                  f"{name}: {k}-relative -- assembler relocates "
                  f"{sorted(mine[k])}, disk relocates "
                  f"{sorted(t - p.enter_ic for t in p.reloc[k])}")

    if bad:
        print("\n".join(bad))
        return 1
    print(f"{checked} checks, all passed")
    print("prog-native-asm-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
