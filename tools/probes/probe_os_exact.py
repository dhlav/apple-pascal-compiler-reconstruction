"""The OS procedures Apple's own compiler already reproduces exactly.

The kept acceptance run named by `RUN` below is what
Apple's real 1.3 `SYSTEM.COMPILER` wrote from `PASCALSYSTEM.text` under the
emulator. That run cannot be repeated inside `build_all.py` -- it is
interactive -- but its *result* can be re-checked on every build, which is
what `probe_acceptance.py` already does for the assembler and Linker runs.

The claim under test is a list, not a number: these named procedures come
out of Apple's compiler instruction-for-instruction identical to Apple's
shipped `128K.PASCAL`, on frames of exactly the same size. Naming them is
the point. A bare count can be held up by a procedure that started matching
while another stopped, and the whole reason `oscmp.py` reports gains and
losses separately is that a swap like that is the failure most worth
catching.

Three things can fail here, and each is worth catching:

  1. A procedure on the list stops matching. Both sides are frozen files,
     so that means this repository's own decoder or codefile reader changed
     what it reads out of one of them -- and every claim resting on that
     reader is then suspect.
  2. The total drops below the recorded floor.
  3. The comparison stops being able to discriminate at all. A comparison
     that returns "identical" for everything would pass checks 1 and 2
     while being worthless, so this also requires that the procedures known
     NOT to match still do not match. That is the check that keeps the
     other two honest.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from a2pascal.codefile import CodeFile
from oscmp import compare, shipped_codefile

ROOT = Path(__file__).resolve().parents[2]
RUN = (ROOT / "acceptance" / "2026-09-14-pascalsystem-intrinsic"
       / "PASCALSY.CODE")

# Verified under AppleWin on 2026-09-02, Apple's own compiler both sides.
# Grows as the reconstruction does; it must never shrink without a finding
# saying why.
EXACT = [
    "GETCMD.2", "GETCMD.4", "GETCMD.6", "GETCMD.19", "GETCMD.23",
    "GETCMD.26",
    # Finding 225's nesting pass: .8 is inside .7, .12 inside .11,
    # .21 inside .20. Half of these could not be written at all until
    # that was established, because they read their parent's frame.
    "GETCMD.5", "GETCMD.7", "GETCMD.8", "GETCMD.10", "GETCMD.12",
    "GETCMD.24",
    # Finding 226.
    "GETCMD.3", "GETCMD.9", "GETCMD.22",
    # Finding 227: GETCMD.11 and the whole of its nested family. The
    # frame was mapped from the offsets its own children reach into it
    # with (LDA 1,<n>), so all seven landed together on the first
    # compile -- .11 could not be written before the children and the
    # children could not be written before .11.
    "GETCMD.13", "GETCMD.14", "GETCMD.15", "GETCMD.16", "GETCMD.17",
    "GETCMD.18", "GETCMD.11",
    # Finding 228: GETCMD is complete, all 27 of its procedures. The
    # segment body (.1) went last on purpose -- every CLP in it is a
    # procedure number, and a wrong one would have compiled as quietly
    # as a right one until all 26 callees were real.
    "GETCMD.25", "GETCMD.27", "GETCMD.1",
    "GETCMD.20", "GETCMD.21",
    # INITIALIZE is complete: all 11 of its procedures.
    "INITIALI.1", "INITIALI.2", "INITIALI.3", "INITIALI.4", "INITIALI.5",
    "INITIALI.6", "INITIALI.7", "INITIALI.8",
    "INITIALI.9", "INITIALI.10", "INITIALI.11",
    "PASCALSY.1", "PASCALSY.9", "PASCALSY.10", "PASCALSY.11",
    "PASCALSY.14", "PASCALSY.15",
    "PASCALSY.16", "PASCALSY.17", "PASCALSY.19", "PASCALSY.20",
    "PASCALSY.21", "PASCALSY.22",
    "PASCALSY.23", "PASCALSY.24", "PASCALSY.25", "PASCALSY.26",
    "PASCALSY.29", "PASCALSY.30", "PASCALSY.31", "PASCALSY.32",
    "PASCALSY.42",
    "PASCALSY.33", "PASCALSY.34", "PASCALSY.35", "PASCALSY.39",
    "PASCALSY.36", "PASCALSY.37", "PASCALSY.38",
    "PASCALSY.44", "PASCALSY.45", "PASCALSY.46", "PASCALSY.47",
    "PASCALSY.48", "PASCALSY.49", "PASCALSY.50", "PASCALSY.53",
    "PASCALSY.54", "PASCALSY.55", "PASCALSY.56",
    "PASCALSY.51", "PASCALSY.52", "PASCALSY.57", "PASCALSY.58",
    "PASCALSY.2", "PASCALSY.3", "PASCALSY.4", "PASCALSY.5", "PASCALSY.6",
    "PASCALSY.43",
    "PASCALSY.27",
    # PASCALSY was 56 of 58 here, FGET and FPUT behind FIOPRIMS's
    # intrinsic-unit shape (findings 200, 224).
    "PASCALSY.12", "PASCALSY.13", "PASCALSY.18",
    "PASCALSY.28", "PASCALSY.40", "PASCALSY.41",
    "FILEPROC.1", "FILEPROC.3", "FILEPROC.5", "FILEPROC.6",
    "FILEPROC.7",
    # Finding 229: FPTITLE, once POS/COPY were written as sugar instead
    # of as direct SPOS/SCOPY calls -- the sugar builds its own argument
    # list, so the VAR-actual check that forced a scratch variable never
    # applied.
    "FILEPROC.8",
    "FIOPRIMS.2", "FIOPRIMS.3",
    # Finding 231. ODD and CHR are the two standard functions the
    # compiler emits no instruction for, so ODD(<integer>) is a free
    # cast to BOOLEAN -- which is what the four "unreachable"
    # procedures of finding 230 were each two instructions short of.
    # FIOPRIMS.5 (FPWINOUT, 275 instructions) was written from the
    # disassembly in the same pass and landed exact on the first
    # compile; FILEPROC is now complete, all 8.
    "FIOPRIMS.4", "FIOPRIMS.5",
    "FILEPROC.2", "FILEPROC.4",
    # Finding 232. FIOPRIMS is now the UNIT its SEGKIND says it is,
    # declared inline between USERPROGRAM's forward heading and its
    # body -- which is what puts it on segment 2 -- and FPUT USES it.
    # FIOPRIMS.1 is the unit's initialisation part, so it ends RNP 0
    # where a SEGMENT PROCEDURE ends RBP 0.
    "FIOPRIMS.1", "PASCALSY.8",
    # Finding 280: FGET, in the same compile as everything else, once
    # the USES moved to program level through an include file.
    "PASCALSY.7",
    "PRINTERR.1",
    "USERPROG.1",
]

# The discrimination control (check 3 above). With all 111 exact in RUN
# there is nothing left in it that differs, so the control is the run
# before finding 280: the same comparison must still see that run's FGET
# stub as different, and see nothing else there as different. A
# comparison that called everything identical would fail this.
CONTROL = (ROOT / "acceptance" / "2026-09-11-pascalsystem-jumps"
           / "PASCALSY.CODE")
CONTROL_DIFFERS = ["PASCALSY.7"]    # FGET: a stub in that run

# Whole segments, byte for byte against the shipped file (finding 281).
# Procedure identity says nothing about where each body sits; this does.
# Segment 0 is not here: Apple's is split across slots 0 and 15 by a
# packing step after the compile (finding 50).
WHOLE = ["USERPROG", "FIOPRIMS", "PRINTERR", "INITIALI", "GETCMD",
         "FILEPROC"]
# Its control is the run before finding 281: all 111 procedures exact,
# but GETCMD's bodies in declaration-completion order, not Apple's.
WHOLE_CONTROL = (ROOT / "acceptance" / "2026-09-13-pascalsystem-one"
                 / "PASCALSY.CODE")
WHOLE_CONTROL_DIFFERS = {"GETCMD": 4438}

# Segment 0 procedure by procedure, byte for byte, wherever Apple's split
# put each one (finding 282). Instruction identity misses a jump-table
# slot order; this does not. Its control is the run before 282, whose
# CANTSTRETCH (.49) had two slots swapped.
SEG0_CONTROL = (ROOT / "acceptance" / "2026-09-14-pascalsystem-getcmd"
                / "PASCALSY.CODE")
SEG0_CONTROL_DIFFERS = [49]

# SEGKIND for the seven real slots, the words the compiler itself writes
# (finding 282). FIOPRIMS is INTRINSIC, so it is 6 and no USES sets
# LINKINFO, so no slot is marked HOSTSEG. The same run is the control:
# before 282 FIOPRIMS was a plain unit, 3, and slot 1 came out 1.
KINDS_CONTROL = SEG0_CONTROL
KINDS_CONTROL_DIFFERS = {1: (1, 0), 2: (3, 6)}

fail = []


def proc_bytes(seg) -> dict[int, bytes]:
    """Each procedure's bytes, tiled inside the chunk that holds it.

    A procedure runs from the end of the one below it (or its chunk's
    start) through its two attribute bytes. A split segment's chunks come
    from CodeFile's join (finding 50), so Apple's two pieces tile apart.
    """
    out = {}
    for start, length, _ in seg.chunks:
        inside = sorted((p for p in seg.procedures
                         if start <= p.jtab < start + length),
                        key=lambda p: p.jtab)
        prev = start
        for p in inside:
            out[p.number] = seg.data[prev:p.jtab + 2]
            prev = p.jtab + 2
    return out


def seg0_differs(cf: CodeFile, apple_cf: CodeFile) -> list[int]:
    ours = proc_bytes(next(s for s in cf.segments if s.name == "PASCALSY"))
    apple = proc_bytes(next(s for s in apple_cf.segments
                            if s.name == "PASCALSY"))
    return sorted(n for n in apple if ours.get(n) != apple[n])


def segments(data: bytes) -> dict[str, bytes]:
    """Named segments' code bytes, straight off the dictionary."""
    out = {}
    for i in range(16):
        addr, length = int.from_bytes(data[4 * i:4 * i + 2], "little"), \
            int.from_bytes(data[4 * i + 2:4 * i + 4], "little")
        name = data[0x40 + 8 * i:0x48 + 8 * i].decode("latin1").strip()
        if length and name:
            out[name] = data[addr * 512:addr * 512 + length]
    return out


def seg_differs(ours: bytes, apple: bytes) -> int:
    return (sum(a != b for a, b in zip(ours, apple))
            + abs(len(ours) - len(apple)))


def check(ok: bool, label: str) -> None:
    print(("  ok   " if ok else "  FAIL ") + label)
    if not ok:
        fail.append(label)


def main() -> int:
    if not RUN.exists():
        print(f"{RUN} is missing -- the acceptance run must be kept verbatim")
        return 1
    rows = compare(CodeFile(RUN.read_bytes()), shipped_codefile())

    print("=== procedures Apple's compiler reproduces exactly ===")
    for key in EXACT:
        r = rows.get(key)
        check(bool(r) and r["exact"], f"{key} instruction- and frame-identical")

    print("=== the count has not gone backwards ===")
    now = sum(1 for r in rows.values() if r["exact"])
    check(now >= len(EXACT),
          f"{now} exact, floor is {len(EXACT)} (of {len(rows)} procedures)")

    print("=== every procedure, in one compile (finding 280) ===")
    check(now == len(rows) == 111,
          f"{now} of {len(rows)} procedures exact in the one run")

    print("=== the comparison can still tell them apart ===")
    if not CONTROL.exists():
        check(False, f"{CONTROL} is missing")
    else:
        crows = compare(CodeFile(CONTROL.read_bytes()), shipped_codefile())
        differ = sorted(k for k, r in crows.items() if not r["exact"])
        check(differ == CONTROL_DIFFERS,
              f"the pre-280 run still differs in exactly {CONTROL_DIFFERS}: "
              f"{differ}")

    print("=== whole segments, byte for byte (finding 281) ===")
    apple = segments(shipped_codefile().data)
    ours = segments(RUN.read_bytes())
    for name in WHOLE:
        n = seg_differs(ours.get(name, b""), apple[name])
        check(n == 0, f"{name}: {len(apple[name])} bytes, {n} differ")
    if not WHOLE_CONTROL.exists():
        check(False, f"{WHOLE_CONTROL} is missing")
    else:
        ctl = segments(WHOLE_CONTROL.read_bytes())
        got = {name: seg_differs(ctl.get(name, b""), apple[name])
               for name in WHOLE}
        got = {k: v for k, v in got.items() if v}
        check(got == WHOLE_CONTROL_DIFFERS,
              f"the pre-281 run differs in exactly "
              f"{WHOLE_CONTROL_DIFFERS}: {got}")

    print("=== segment 0, every procedure byte for byte (finding 282) ===")
    shipped = shipped_codefile()
    apple0 = next(s for s in shipped.segments if s.name == "PASCALSY")
    check(len(apple0.chunks) == 2, f"Apple's segment 0 joined from two "
          f"pieces: {[(c[2], c[1]) for c in apple0.chunks]}")
    check(len(proc_bytes(apple0)) == 58, "all 58 procedures tile a piece")
    # How the pieces were filled. Both hold their procedures in number
    # order, whatever order the compile wrote them in, and slot 0's set is
    # exactly what first-fit in number order gives for some capacity:
    # every procedure that went in kept the running total under it, every
    # one that did not would have gone over.
    pieces = {}
    for start, length, slot in apple0.chunks:
        pieces[slot] = [p.number for p in sorted(
            (p for p in apple0.procedures
             if start <= p.jtab < start + length), key=lambda p: p.jtab)]
    check(all(v == sorted(v) for v in pieces.values()),
          f"each piece in procedure-number order: {pieces}")
    sizes = {n: len(b) for n, b in proc_bytes(apple0).items()}
    dict_bytes = 2 + 2 * len(sizes)
    lo, hi, total = 0, 1 << 16, dict_bytes
    for n in sorted(sizes):
        if n in pieces[0]:
            total += sizes[n]
            lo = max(lo, total)
        else:
            hi = min(hi, total + sizes[n] - 1)
    slot0_len = next(n for _, n, slot in apple0.chunks if slot == 0)
    check(lo <= hi and lo == slot0_len,
          f"slot 0 is first-fit in number order: any capacity {lo}..{hi} "
          f"bytes gives its set")
    got = seg0_differs(CodeFile(RUN.read_bytes()), shipped)
    check(got == [], f"no procedure's bytes differ: {got}")
    if not SEG0_CONTROL.exists():
        check(False, f"{SEG0_CONTROL} is missing")
    else:
        got = seg0_differs(CodeFile(SEG0_CONTROL.read_bytes()), shipped)
        check(got == SEG0_CONTROL_DIFFERS,
              f"the pre-282 run differs in exactly procedures "
              f"{SEG0_CONTROL_DIFFERS}: {got}")

    print("=== slack after each segment (finding 282) ===")
    # The tail of a segment's last block. For slots 2-6 Apple's holds the
    # same bytes as this compile's, so whatever finished the file copied
    # those blocks whole. Slot 1's does not: its tail holds unit names
    # and a file title, memory of whatever tool wrote that block.
    def tails(data: bytes) -> dict[int, bytes]:
        out = {}
        for i in range(1, 7):
            addr = int.from_bytes(data[4 * i:4 * i + 2], "little")
            length = int.from_bytes(data[4 * i + 2:4 * i + 4], "little")
            end = addr * 512 + length
            out[i] = data[end:(addr + (length + 511) // 512) * 512]
        return out
    at, ot = tails(shipped.data), tails(RUN.read_bytes())
    same = [i for i in at if at[i] == ot[i]]
    check(same == [2, 3, 4, 5, 6],
          f"slots whose slack is the compiler's own: {same}")
    check(b"SYSTERM" in at[1] and b"SYSTERM" not in ot[1],
          "slot 1's slack is another tool's memory (unit names)")

    print("=== SEGKIND, slots 0-6 (finding 282) ===")
    def kinds(data: bytes) -> list[int]:
        return [int.from_bytes(data[0xC0 + 2 * i:0xC2 + 2 * i], "little")
                for i in range(7)]
    want = kinds(shipped.data)
    check(kinds(RUN.read_bytes()) == want,
          f"the compile's SEGKINDs are Apple's: {want}")
    if not KINDS_CONTROL.exists():
        check(False, f"{KINDS_CONTROL} is missing")
    else:
        ctl = kinds(KINDS_CONTROL.read_bytes())
        got = {i: (ctl[i], want[i]) for i in range(7) if ctl[i] != want[i]}
        check(got == KINDS_CONTROL_DIFFERS,
              f"the pre-282 run differs in exactly {KINDS_CONTROL_DIFFERS} "
              f"(ours, Apple's): {got}")

    print()
    if fail:
        print(f"OS exact: {len(fail)} check(s) failed")
        return 1
    print(f"OS exact: {len(EXACT)} named procedures verified, "
          f"{now} exact overall")
    print("os-exact-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
