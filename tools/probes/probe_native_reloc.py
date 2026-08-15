"""The relocation tables of 1.3's two native procedures (finding 44).

Both `IDSEARCH` and `TREESEARCH` carry a block of word data between their
last `RTS` and their attribute table which had been left unidentified. The
1.3 manual, Part IV chapter 4, describes exactly what it is:

  * the highest word of an assembly procedure's attribute table has 0 in
    its PROCEDURE NUMBER field -- that is the marker the Interpreter uses --
    and the RELOCSEG number in the other byte;
  * the second highest is ENTER IC, as for a p-code procedure;
  * then four relocation tables, "from high address to low ... base-relative,
    segment-relative, procedure-relative, and Interpreter-relative";
  * each table is a count word followed by that many *self-relative*
    one-word pointers at lower addresses, naming the words the loader must
    fix up.

That is a strong claim, because it says where every remaining byte of both
procedures goes and what each one points at, and the pointers have to land
on something. This probe holds it against the bytes.

The checks that can fail, in the order the loader reads them:

  * the four tables tile the gap exactly -- the walk from JTAB-4 downward
    must stop on the byte after the last code or data byte, with no word
    left over and none borrowed from the code;
  * every self-relative pointer must decode *downward* (target = a - v).
    The probe also checks that a + v lands outside the procedure for every
    entry, so the sign is established rather than assumed;
  * the procedure-relative target set must be exactly the set of absolute
    operands in the code plus, for IDSEARCH, the 26 words of the letter
    index. Anything the loader would not fix up must not be listed, and
    anything absolute that it would must be;
  * the two absolute operands IDSEARCH does have are the low and high byte
    of a *base*: proc+$006C indexed by twice the first character. With the
    character uppercased that reaches the letter index at proc+$00EE, which
    is where the index actually is. That is the arithmetic that explains
    why $006C is nowhere near the table it reads;
  * TREESEARCH's four are `JMP` operands, and proc+operand must land on the
    first byte of a decoded instruction, not into the middle of one;
  * base-, segment- and Interpreter-relative are all empty in both. Which
    is the interesting negative: neither routine touches a global or calls
    the Interpreter, so `.PUBLIC`/`.PRIVATE`, `.REF`/`.DEF` and `.INTERP`
    were all unused, and the two procedures are self-contained.

Controls, so a green here is not vacuous: 1.1 has no native procedures at
all, and no p-code procedure in either release parses as one.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile, RELOC_KINDS
from a2pascal.m6502 import disassemble, ABS, ABX, ABY, IND

ROOT = Path(__file__).resolve().parents[2]
DISKS = {
    "1.1": "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk",
    "1.3": "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk",
}
# Verified independently by probe_reserved_words.py: the letter index is 26
# words at proc+$00EE and the word lists tile $1314..$14CE.
IDX_LO, IDX_HI = 0x12E0, 0x1314
RW_LO, RW_HI = 0x1314, 0x14CE
# Code, i.e. everything that is not one of the two data blocks above.
CODE = {2: [(0x11F2, 0x12E0)], 3: [(0x1512, 0x1592)]}
EXPECT = {2: ("IDSEARCH", 28), 3: ("TREESEARCH", 4)}


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

    cf = load("1.3")
    seg = cf.segment("PASCALCO")
    natives = seg.native_procedures
    check(len(natives) == 2,
          f"1.3 PASCALCO has {len(natives)} native procedures, expected 2")

    for p in natives:
        name, want_n = EXPECT[p.number]
        tag = f"PASCALCO.{p.number} {name}"
        raw = seg.data

        # -- the attribute table itself ----------------------------------
        check(raw[p.jtab] == 0,
              f"{tag}: PROCEDURE NUMBER is {raw[p.jtab]}, not the native 0")
        check(raw[p.jtab + 1] == 0,
              f"{tag}: RELOCSEG is {raw[p.jtab+1]}, expected 0 "
              f"(no intrinsic-unit data segment)")
        v = int.from_bytes(raw[p.jtab - 2:p.jtab], "little")
        check(p.jtab - 2 - v == p.enter_ic,
              f"{tag}: ENTER IC ${v:04X} at ${p.jtab-2:04X} decodes to "
              f"${p.jtab-2-v:04X}, not ${p.enter_ic:04X}")

        # -- the four tables tile the gap exactly ------------------------
        a = p.jtab - 4
        for kind in RELOC_KINDS:
            a -= 2 + 2 * len(p.reloc[kind])
        check(a + 2 == p.content_end,
              f"{tag}: relocation walk ends at ${a+2:04X}, "
              f"content_end is ${p.content_end:04X}")

        code_hi = CODE[p.number][-1][1]
        data_hi = RW_HI if p.number == 2 else code_hi
        check(p.content_end == data_hi,
              f"{tag}: content ends ${p.content_end:04X}, "
              f"but the last code or data byte is at ${data_hi-1:04X}")
        check(p.enter_ic == CODE[p.number][0][0],
              f"{tag}: enters at ${p.enter_ic:04X}, expected "
              f"${CODE[p.number][0][0]:04X}")

        # -- which tables are populated ----------------------------------
        for kind in ("base", "segment", "interp"):
            check(not p.reloc[kind],
                  f"{tag}: {kind}-relative table has "
                  f"{len(p.reloc[kind])} entries, expected none")
        check(len(p.reloc["procedure"]) == want_n,
              f"{tag}: procedure-relative table has "
              f"{len(p.reloc['procedure'])} entries, expected {want_n}")

        # -- the pointers decode downward, and only downward -------------
        for t in p.reloc["procedure"]:
            at = p.reloc_at[t]
            w = int.from_bytes(raw[at:at + 2], "little")
            check(p.enter_ic <= t < p.content_end,
                  f"{tag}: pointer at ${at:04X} designates ${t:04X}, "
                  f"outside ${p.enter_ic:04X}..${p.content_end:04X}")
            check(not (p.enter_ic <= at + w < p.content_end),
                  f"{tag}: pointer at ${at:04X} would also land inside the "
                  f"procedure if read upward (${at+w:04X}); the sign of the "
                  f"self-relative encoding is not pinned by this entry")

        # -- the target set is exactly what needs fixing up --------------
        insns = []
        for lo, hi in CODE[p.number]:
            ii, exact = disassemble(raw, lo, hi)
            check(exact, f"{tag}: code sweep ${lo:04X}..${hi:04X} "
                         f"does not land on the end")
            insns += ii
        abs_ops = {i.addr + 1 for i in insns
                   if i.mode in (ABS, ABX, ABY, IND)}
        want = set(abs_ops)
        if p.number == 2:
            want |= set(range(IDX_LO, IDX_HI, 2))
        got = set(p.reloc["procedure"])
        check(got == want,
              f"{tag}: procedure-relative targets differ from the words that "
              f"need fixing up: listed but not absolute "
              f"{sorted(hex(x) for x in got - want)}, absolute but not "
              f"listed {sorted(hex(x) for x in want - got)}")

        # -- what each target actually points at -------------------------
        starts = {i.addr for i in insns}
        for i in insns:
            if i.mode in (ABS, IND) and i.addr + 1 in got:
                dest = p.enter_ic + (i.operand or 0)
                check(i.mnemonic == "JMP",
                      f"{tag}: relocated absolute {i.mnemonic} at "
                      f"${i.addr:04X}, expected a JMP")
                check(dest in starts,
                      f"{tag}: {i.text} at ${i.addr:04X} relocates to "
                      f"${dest:04X}, which is not an instruction boundary")

    # -- IDSEARCH's letter index -----------------------------------------
    p2 = next(p for p in natives if p.number == 2)
    raw = seg.data
    ins2, _ = disassemble(raw, *CODE[2][0])
    based = [i for i in ins2 if i.mode in (ABX, ABY)]
    check(len(based) == 2,
          f"IDSEARCH has {len(based)} indexed absolute operands, expected 2 "
          f"(the low and high byte of the letter-index base)")
    if len(based) == 2:
        lo_i, hi_i = based
        check(hi_i.operand == lo_i.operand + 1,
              f"IDSEARCH's two indexed bases are ${lo_i.operand:04X} and "
              f"${hi_i.operand:04X}, not consecutive bytes")
        # $88 holds the identifier's first character, uppercased, and the
        # code does ASL A before TAY, so the index is 2*ord(c).
        reach = p2.enter_ic + lo_i.operand + 2 * ord("A")
        check(reach == IDX_LO,
              f"IDSEARCH's base proc+${lo_i.operand:04X} indexed by 2*'A' "
              f"reaches ${reach:04X}, not the letter index at ${IDX_LO:04X}")
        reach_z = p2.enter_ic + lo_i.operand + 2 * ord("Z")
        check(reach_z == IDX_HI - 2,
              f"...and by 2*'Z' reaches ${reach_z:04X}, not the last index "
              f"slot at ${IDX_HI-2:04X}")

    # every letter-index word must point into the reserved-word table
    for a in range(IDX_LO, IDX_HI, 2):
        w = int.from_bytes(raw[a:a + 2], "little")
        t = p2.enter_ic + w
        check(RW_LO <= t < RW_HI,
              f"letter index at ${a:04X} points to ${t:04X}, outside the "
              f"reserved-word table ${RW_LO:04X}..${RW_HI:04X}")

    # -- controls ---------------------------------------------------------
    cf11 = load("1.1")
    n11 = sum(len(s.native_procedures) for s in cf11.segments)
    check(n11 == 0, f"1.1 has {n11} native procedures, expected none")
    for ver, c in (("1.1", cf11), ("1.3", cf)):
        stray = [f"{s.name}.{p.number}" for s in c.segments
                 for p in s.pcode_procedures if p.reloc]
        check(not stray,
              f"{ver}: p-code procedures parsed as native: {stray}")
    n13 = sum(len(s.native_procedures) for s in cf.segments)
    check(n13 == 2, f"1.3 has {n13} native procedures in total, expected 2")

    if bad:
        print("\n".join(bad))
        return 1
    print(f"{checked} checks, all passed")
    print("native-reloc-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
