"""Compile the GOTOXY programs on the host and diff against Apple's own output.

`evidence/` holds exactly two programs where Apple's compiler's *input* and
*output* are both on the disk: `HAZELGOTO` and `SOROCGOTO`, the two GOTOXY
replacements the manual tells users to write. Finding 49 used them to
calibrate the lifter. This uses them for the other direction -- source in,
codefile out -- which nothing in this repo could do before.

What it requires, for each program:

  * the compiled segment is the same length as Apple's, to the byte;
  * the p-code disassembles identically, instruction for instruction and
    operand for operand, read by this repo's own decoder on both sides;
  * the reconstructed declaration skeletons compile to Apple's own global
    frame, to the byte, in both releases;
  * the segment bytes differ *only* at the known padding positions -- one
    byte per procedure, past the `RBP` or `XIT` that ends it, where Apple
    writes 0 and `ucsdpsys_compile` writes `NOP`. Nothing reaches them.

The last of those is the one that can rot, so it is pinned by position and
by value rather than counted: a new difference anywhere else fails, and so
does a padding byte that stops differing.

If the toolchain is not built this reports that and exits 0. That is a
deliberate hole -- the check is worth having and the toolchain is not part of
the repo -- but it means a green run is not proof this ran. The printed line
says which happened.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.textfile import decode_text
from a2pascal.pcode import disassemble, sweep_exit
import xcompile

ROOT = Path(__file__).resolve().parents[2]
DISK = ROOT / "evidence" / "disks" / "UCSD Pascal 1.1_3.dsk"
SAMPLES = ("HAZELGOTO", "SOROCGOTO")

# Apple writes 0 where ucsdpsys_compile writes NOP, to word-align after a
# procedure's exit code. Segment offsets, per program.
PADDING = {"HAZELGOTO": (83, 95), "SOROCGOTO": (71, 83)}
APPLE_PAD, XC_PAD = 0x00, 0xD7          # 0xD7 is NOP

fails = []
checks = 0


def check(cond, what):
    global checks
    checks += 1
    if not cond:
        fails.append(what)


def listing(seg, p):
    """Every instruction up to and including the return.

    A procedure returns with RNP or RBP; the program's outer block ends
    with XIT. The sweep past either would decode the alignment byte, the
    one thing the two compilers do differ on -- Apple's 0 reads as `SLDC 0`
    and `ucsdpsys_compile`'s as `NOP`. That byte is checked below, by value
    and position; including it here would just report the same difference
    twice and hide anything real behind it.
    """
    ins = (disassemble(seg.data, p.enter_ic, p.exit_ic, p.jtab)[0]
           + sweep_exit(seg.data, p.exit_ic, p.jtab - 8, p.jtab)[0])
    out = []
    for i in ins:
        out.append(i.text)
        if i.mnemonic in ("RNP", "RBP", "XIT"):
            break
    return out


if not xcompile.available():
    print("SKIPPED: ucsdpsys_compile is not built "
          "(thirdparty/ucsd-psystem-xc/build.sh)")
    sys.exit(0)

disk = PascalDisk.from_file(DISK)
for name in SAMPLES:
    e = disk.find(name + ".TEXT")
    source = decode_text(disk.read_blocks(e.first_block, e.blocks))
    e = disk.find(name + ".CODE")
    apple = CodeFile(disk.read_blocks(e.first_block, e.blocks))

    try:
        mine = CodeFile(xcompile.compile_text(source))
    except xcompile.CompileError as exc:
        fails.append(f"{name}: did not compile -- {exc}")
        continue

    check(len(mine.segments) == len(apple.segments),
          f"{name}: {len(mine.segments)} segments, Apple has "
          f"{len(apple.segments)}")
    for a, b in zip(apple.segments, mine.segments):
        check(a.name == b.name, f"{name}: segment {b.name!r}, Apple {a.name!r}")
        check(a.seg_num == b.seg_num,
              f"{name}: segment number {b.seg_num}, Apple {a.seg_num}")
        check(a.length == b.length,
              f"{name}: segment is {b.length} bytes, Apple's is {a.length}")
        check(len(a.procedures) == len(b.procedures),
              f"{name}: {len(b.procedures)} procedures, Apple has "
              f"{len(a.procedures)}")
        for pa, pb in zip(a.procedures, b.procedures):
            check(pa.param_size == pb.param_size and pa.data_size == pb.data_size,
                  f"{name}.{pb.number}: frame is param {pb.param_size} / data "
                  f"{pb.data_size}, Apple's is {pa.param_size} / {pa.data_size}")
            check(pa.lex_level == pb.lex_level,
                  f"{name}.{pb.number}: lex {pb.lex_level}, Apple {pa.lex_level}")
            check(listing(a, pa) == listing(b, pb),
                  f"{name}.{pb.number}: the p-code differs from Apple's")

        if a.length == b.length:
            diff = [i for i in range(a.length) if a.data[i] != b.data[i]]
            check(tuple(diff) == PADDING[name],
                  f"{name}: segment bytes differ at {diff}, "
                  f"expected only the padding at {list(PADDING[name])}")
            for i in diff:
                check(a.data[i] == APPLE_PAD and b.data[i] == XC_PAD,
                      f"{name}: offset {i} is Apple 0x{a.data[i]:02X} / "
                      f"ours 0x{b.data[i]:02X}, not the known 0x00 / 0xD7")

# The reconstructed declarations, compiled, must give Apple's own global
# frame. This is the check that caught SYMBUFP and CODEP being written as
# VAR declarations when they are the outer block's parameter words: it was
# two words wide in both releases (finding 55c).
REC = ROOT / "analysis" / "reconstruction"
COMPILER = {"1.1": "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk",
            "1.3": "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk"}
for ver, dname in COMPILER.items():
    skel = REC / f"skeleton-{ver}.text"
    if not skel.exists():
        fails.append(f"{skel.name} has not been generated (tools/srcskel.py)")
        continue
    try:
        mine = CodeFile(xcompile.compile_text(
            skel.read_text(encoding="ascii", errors="replace")))
    except xcompile.CompileError as exc:
        fails.append(f"skeleton-{ver}: did not compile -- {exc}")
        continue
    # The compiler is a SEGMENT PROCEDURE inside a (*$U-*) host program
    # (finding 60), so segment 0 is the host and segment 1 is PASCALCO.
    mseg = next(x for x in mine.segments if x.name == "PASCALCO")
    mp = next(x for x in mseg.procedures if x.number == 1)
    ad = PascalDisk.from_file(ROOT / "evidence" / "disks" / dname)
    ae = ad.find("SYSTEM.COMPILER")
    ap = CodeFile(ad.read_blocks(ae.first_block, ae.blocks))         .segment("PASCALCO").procedures[0]
    check((mseg.seg_num, mp.lex_level) == (1, 0),
          f"skeleton-{ver}: PASCALCO comes out as segment {mseg.seg_num} at "
          f"lex {mp.lex_level}, Apple's is segment 1 at lex 0")
    check((mp.param_size, mp.data_size) == (ap.param_size, ap.data_size),
          f"skeleton-{ver}: the declarations compile to param {mp.param_size} / "
          f"data {mp.data_size}, but Apple's outer block is param "
          f"{ap.param_size} / data {ap.data_size}")

print(f"{checks} checks, {len(fails)} failures "
      f"({len(SAMPLES)} programs diffed against Apple's own output, "
      f"{len(COMPILER)} reconstructed VAR blocks checked against its frame)")
for f in fails[:20]:
    print("  FAIL", f)
sys.exit(1 if fails else 0)
