"""How big is a procedure's frame -- and therefore the global area?

The global map sized the global area from the outer block's DATA SIZE word
alone, and that was two words short. The symptom was that the map's own
objects covered more words than the area it reported, in both releases and
by the same amount: `DISKBUF` is a 512-byte disk block, 256 words, and it
would not fit; and 1.3's three tail globals sat *past* the end.

The claim under test is that a UCSD activation record holds the block's
parameters and its locals in one offset space beginning at 1, so the highest
valid offset is

    (PARAM SIZE + DATA SIZE) / 2

and not `DATA SIZE / 2`. That is a claim about every procedure, not just the
outer one, so it is measured over all 287 of them rather than argued: for
each procedure, the highest offset any `LDL`/`SLDL`/`STL`/`SRL`/`LLA`
mentions must not exceed the bound.

It is a check that can fail in both directions, and both matter:

  * **Never exceeded.** If the bound were wrong the offsets would run past
    it -- and under the old `DATA SIZE`-only reading, 14 procedures in 1.1
    and 15 in 1.3 do exactly that.
  * **Reached exactly, and often.** A bound that is merely never exceeded
    could be any large number. 105 of 1.1's 114 procedures that touch a
    local reach it precisely, which is what says it is the frame and not
    just an upper limit. The handful that fall short end in an aggregate
    whose interior words are never addressed individually -- the 256-word
    outlier is a disk buffer.

Then the two consequences for the global map, which are the reason for
caring: `DISKBUF` comes out at exactly 256 words in both releases, and 1.3's
`HAS128K`/`CONLIST`/`LSTOPEN` land on the last three words of the frame
rather than three words beyond it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.pcode import disassemble, sweep_exit
from a2pascal.globals import collect

ROOT = Path(__file__).resolve().parents[2]
DISKS = {
    "1.1": "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk",
    "1.3": "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk",
}
LOCAL = ("LDL", "SLDL", "STL", "SRL", "LLA")
# offset of DISKBUF, and the offsets of the three globals 1.3 adds at the top
DISKBUF = {"1.1": 969, "1.3": 1099}
TAIL_13 = (1355, 1356, 1357)


def load(ver):
    d = PascalDisk.from_file(ROOT / "evidence" / "disks" / DISKS[ver])
    e = d.find("SYSTEM.COMPILER")
    return CodeFile(d.read_blocks(e.first_block, e.blocks))


def main() -> int:
    bad, checked = [], 0

    def check(cond, msg):
        nonlocal checked
        checked += 1
        if not cond:
            bad.append(msg)

    for ver in DISKS:
        cf = load(ver)
        exact = over = short = counted = 0
        old_over = 0
        for seg in cf.segments:
            for p in seg.pcode_procedures:
                body, _ = disassemble(seg.data, p.enter_ic, p.exit_ic, p.jtab)
                ex, _ = sweep_exit(seg.data, p.exit_ic, p.jtab - 8, p.jtab)
                hi = max((i.operands[0] for i in body + ex
                          if i.mnemonic in LOCAL), default=0)
                if not hi:
                    continue
                counted += 1
                cap = (p.param_size + p.data_size) // 2
                if hi > cap:
                    over += 1
                    bad.append(f"[{ver}] {seg.name}.{p.number}: touches local "
                               f"{hi}, frame is {cap} "
                               f"(param {p.param_size//2} + data "
                               f"{p.data_size//2})")
                elif hi == cap:
                    exact += 1
                else:
                    short += 1
                if hi > p.data_size // 2:
                    old_over += 1

        check(over == 0,
              f"[{ver}] {over} procedures address past PARAM+DATA")
        check(exact >= counted * 0.9,
              f"[{ver}] only {exact} of {counted} procedures reach the bound "
              f"exactly; a bound that is never reached is not a frame size")
        # The control: the reading this replaces really does fail here, so
        # the fix is doing work rather than restating what was already true.
        check(old_over > 0,
              f"[{ver}] no procedure exceeds DATA SIZE alone, so this probe "
              f"cannot distinguish the two readings")
        print(f"[{ver}] {counted} procedures touch a local: {exact} reach "
              f"PARAM+DATA exactly, {short} fall short, {over} exceed it; "
              f"{old_over} would exceed DATA SIZE alone")

        # -- the two consequences for the global map ---------------------
        table, _, area = collect(cf, ver)
        outer = next(p for s in cf.segments for p in s.procedures
                     if p.lex_level == 0 and not p.is_native)
        check(area == (outer.param_size + outer.data_size) // 2,
              f"[{ver}] collect() reports area {area}, expected "
              f"{(outer.param_size + outer.data_size) // 2}")
        check(outer.param_size == 4,
              f"[{ver}] the outer block declares {outer.param_size} bytes of "
              f"parameters, expected 4; the two words are globals 1 and 2")
        for off in (1, 2):
            check(off in table,
                  f"[{ver}] global {off} is never touched, but it is inside "
                  f"the outer block's declared parameter words")

        db = DISKBUF[ver]
        # DISKBUF's extent is the distance to whatever is touched next, or to
        # the end of the frame if it is the last object -- which it is in 1.1
        # but not in 1.3, where the three added globals follow it.
        above = [o for o in table if o > db]
        extent = (min(above) if above else area + 1) - db
        check(extent == 256,
              f"[{ver}] DISKBUF at {db} spans {extent} words, not the 256 of "
              f"a 512-byte disk block")
        check(max(table) <= area,
              f"[{ver}] highest touched global is {max(table)}, past the "
              f"{area}-word frame")

    # -- 1.3's three added globals sit on the last three words ------------
    cf13 = load("1.3")
    t13, _, a13 = collect(cf13, "1.3")
    check(a13 == TAIL_13[-1],
          f"1.3's frame is {a13} words; LSTOPEN is at {TAIL_13[-1]}, which "
          f"must be the last word")
    for off in TAIL_13:
        check(off in t13, f"1.3 global {off} is not touched")

    if bad:
        print("\n".join(bad))
        return 1
    print(f"{checked} checks, all passed")
    print("frame-size-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
