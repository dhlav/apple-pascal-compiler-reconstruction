"""SYSTEM.LIBRARY: all six units' code, by Apple's compiler, assembler, Linker.

acceptance/2026-09-14-library-decops holds the run (findings 285, 286, 290): the six
unit sources in src/pascal/units/1.3/ compiled by SYSTEM.COMPILER as U*,
the three native sources in src/native/ assembled by SYSTEM.ASSMBLER as
N*, and the three units with native halves linked by SYSTEM.LINKER as L*.

Claims, each of which the binary can fail:

  1. **Every code segment is Apple's, byte for byte**: TRANSCEN, CHAINSTU
     and PASCALIO straight from the compile; LONGINTI, TURTLEGR and APPLESTU
     from the link. Also the SEGKIND and SEGINFO words.
  2. **The link did the work**: the same three straight from the compile are
     UNLINKED_INTRINS and shorter, so a comparison that passed them would
     be broken.
  3. **TURTLEGR's DATA segment**: slot 2 is a DATASEG of 386 bytes on no
     block, as Apple's slot 5 is.
  4. **The kept consoles report clean runs.**
  5. **Each unit's interface text is Apple's through IMPLEMENTATION**
     (finding 286): the compiler copies it still encoded, and each source's
     .layout says how Apple's editor stored those lines. The plain-text run
     before it matches none of the six, so the check can fail.
  6. **Each 10-byte trailer is Apple's but for one byte**: offset 6, where
     Apple's holds N or X and no 1.3 tool writes anything.
  7. **The kept sources and layouts are the tree's**, the three native
     sources included.
  8. **Apple's Librarian joins them** (finding 287) into NEWLIB.CODE, slots
     0-6 in Apple's order with the notice: block 0 is Apple's but for the
     block addresses, every code segment is identical, and a region-by-
     region account of Apple's 19456 bytes balances.

Not claimed: the rest of each text block, which is compiler memory, and
the block counts of LONGINTI's and TURTLEGR's text, which the shipped
compiler does not reproduce (finding 286).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from a2pascal.codefile import CodeFile
from a2pascal.disk import PascalDisk

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "acceptance" / "2026-09-14-library-decops"
# The run before finding 286: the same code, interfaces staged as plain
# text. It is the control for the interface-text check.
PLAIN = ROOT / "acceptance" / "2026-09-14-library-units"
# LONGINTS.TEXT with DECOPS's UCSD labels (finding 294), reassembled,
# relinked and rejoined; its three codefiles must be the full run's.
LABELS = ROOT / "acceptance" / "2026-09-14-decops-labels"
UNITSRC = ROOT / "src" / "pascal" / "units" / "1.3"
SOURCES = ["TRANSCEND", "CHAINSTUFF", "PASCALIO", "LONGINTIO",
           "TURTLEGRAPHICS", "APPLESTUFF"]
DISK = ROOT / "evidence" / "disks" / "Apple II Pascal 1.3 APPLE1_ 680-0283-A.dsk"
FROM = {"TRANSCEN": "UTRANS", "CHAINSTU": "UCHAIN", "PASCALIO": "UPASIO",
        "LONGINTI": "LLONG", "TURTLEGR": "LTURTLE", "APPLESTU": "LAPPLE"}
UNLINKED = {"LONGINTI": "ULONG", "TURTLEGR": "UTURTLE",
            "APPLESTU": "UAPPLE"}

fail = []


def check(ok: bool, label: str) -> None:
    print(("  ok   " if ok else "  FAIL ") + label)
    if not ok:
        fail.append(label)


def code_segment(cf: CodeFile, name: str):
    return next(s for s in cf.segments if s.name == name and s.block)


def main() -> int:
    apple = CodeFile(PascalDisk.from_file(DISK).read_file("SYSTEM.LIBRARY"))

    print("=== every code segment is Apple's ===")
    for name, run in FROM.items():
        want = code_segment(apple, name)
        got = code_segment(CodeFile((RUN / f"{run}.CODE").read_bytes()), name)
        check(got.data == want.data
              and (got.segkind_raw, got.seg_num, got.mtype, got.version)
              == (want.segkind_raw, want.seg_num, want.mtype, want.version),
              f"{name} from {run}: {len(got.data)} bytes, kind "
              f"{got.segkind_raw}, segment {got.seg_num}, {got.mtype}")

    print("=== the link did the work ===")
    for name, run in UNLINKED.items():
        want = code_segment(apple, name)
        got = code_segment(CodeFile((RUN / f"{run}.CODE").read_bytes()), name)
        check(got.segkind_raw == 5 and len(got.data) < len(want.data),
              f"{name} unlinked in {run}: kind {got.segkind_raw}, "
              f"{len(got.data)} of {len(want.data)} bytes")

    print("=== TURTLEGR's data segment ===")
    ours = CodeFile((RUN / "LTURTLE.CODE").read_bytes())
    d_ours = [s for s in ours.segments if s.segkind_raw == 7]
    d_apple = [s for s in apple.segments if s.segkind_raw == 7]
    check(len(d_ours) == len(d_apple) == 1
          and (d_ours[0].name, d_ours[0].length, d_ours[0].block,
               d_ours[0].seg_num)
          == (d_apple[0].name, d_apple[0].length, d_apple[0].block,
              d_apple[0].seg_num),
          f"one DATASEG, TURTLEGR, 386 bytes, no block, segment 21: "
          f"{[(s.name, s.length, s.block, s.seg_num) for s in d_ours]}")

    print("=== the kept consoles report clean runs ===")
    for p in sorted(RUN.glob("*-console.txt")):
        text = p.read_text(errors="replace")
        text = text.replace("0   Errors flagged on this Assembly", "")
        bad = any(w in text for w in ("rror", "undefined", "mismatch"))
        check(not bad, p.name)

    print("=== interface text, through IMPLEMENTATION ===")
    def texts(run: Path) -> dict[str, bytes]:
        out = {}
        for name, stem in FROM.items():
            data = (run / f"{stem}.CODE").read_bytes()
            for i in range(16):
                if data[0x40 + 8 * i:0x48 + 8 * i].decode("latin1").strip() \
                        != name:
                    continue
                t = int.from_bytes(data[0xE0 + 2 * i:0xE2 + 2 * i], "little")
                if t:
                    out[name] = data[t * 512:(t + 3) * 512]
        return out
    araw = PascalDisk.from_file(DISK).read_file("SYSTEM.LIBRARY")
    atext = {}
    for i in range(16):
        name = araw[0x40 + 8 * i:0x48 + 8 * i].decode("latin1").strip()
        t = int.from_bytes(araw[0xE0 + 2 * i:0xE2 + 2 * i], "little")
        if t:
            atext[name] = araw[t * 512:(t + 3) * 512]
    ours, plain = texts(RUN), texts(PLAIN)
    missed = []
    for name in FROM:
        a = atext[name]
        end = a.index(b"IMPLEMENTATION") + len(b"IMPLEMENTATION")
        check(ours[name][:end] == a[:end],
              f"{name}: {end} bytes of interface text are Apple's")
        if plain[name][:end] != a[:end]:
            missed.append(name)
        trailer_o = ours[name][end:end + 10]
        trailer_a = a[end:end + 10] if name != "TURTLEGR" else a[1024:1034]
        check(trailer_o[:6] + trailer_o[7:] == trailer_a[:6] + trailer_a[7:]
              and trailer_o[6:7] == b" " and trailer_a[6:7] in (b"N", b"X"),
              f"{name}: trailer {trailer_o!r} is Apple's {trailer_a!r} "
              f"but for offset 6")
    check(sorted(missed) == sorted(FROM),
          f"the plain-text run misses all six: {sorted(missed)}")

    print("=== the kept sources and layouts are the tree's ===")
    for stem in SOURCES:
        for ext in ("text", "layout"):
            kept = (RUN / f"{stem}.{ext}").read_bytes()
            tree = (UNITSRC / f"{stem}.{ext}").read_bytes()
            crlf, lf = b"\r\n", b"\n"
            check(kept.replace(crlf, lf) == tree.replace(crlf, lf),
                  f"{stem}.{ext}")
    for stem in ("NLONG", "LLONG", "NEWLIB"):
        check((LABELS / f"{stem}.CODE").read_bytes()
              == (RUN / f"{stem}.CODE").read_bytes(),
              f"{stem}.CODE from the relabelled DECOPS is the run's, byte "
              f"for byte")
    for name in ("LONGINTS.TEXT", "TURTLEGR.TEXT", "APPLESTF.TEXT"):
        kept = ((LABELS if name == "LONGINTS.TEXT" else RUN) / name
                ).read_bytes().replace(crlf, lf)
        tree = (ROOT / "src" / "native" / name).read_bytes()
        check(kept == tree.replace(crlf, lf), f"src/native/{name}")

    print("=== Apple's Librarian joins them (finding 287) ===")
    lib = (RUN / "NEWLIB.CODE").read_bytes()
    word = lambda b, o: int.from_bytes(b[o:o + 2], "little")
    addr_bytes = {4 * i for i in range(16)} | {0xE0 + 2 * i
                                               for i in range(16)}
    off = [i for i in range(512) if lib[i] != araw[i]]
    check(off and all(i in addr_bytes for i in off),
          f"block 0 differs only in block addresses: {off}")
    rows, total = [], 512
    same = 512 - len(off)
    for i in (0, 1, 2, 3, 4, 6):
        ta, ca, la = (word(araw, 0xE0 + 2 * i), word(araw, 4 * i),
                      word(araw, 4 * i + 2))
        to, co = word(lib, 0xE0 + 2 * i), word(lib, 4 * i)
        nb = (la + 511) // 512
        code_ok = lib[co * 512:co * 512 + la] == araw[ca * 512:ca * 512 + la]
        check(code_ok and word(lib, 4 * i + 2) == la,
              f"slot {i}: {la} code bytes identical in the joined file")
        at, ot = araw[ta * 512:ca * 512], lib[to * 512:co * 512]
        ac, oc = araw[ca * 512:(ca + nb) * 512], lib[co * 512:(co + nb) * 512]
        total += len(at) + len(ac)
        same += sum(1 for k in range(len(at)) if k < len(ot)
                    and at[k] == ot[k])
        same += sum(1 for k in range(len(ac)) if ac[k] == oc[k])
    check(total == len(araw) == 19456,
          f"text, code and slack of six slots plus block 0 tile Apple's "
          f"{len(araw)} bytes: {total}")
    # 16414 in the run of finding 287; APPLESTU's slack is the Linker's
    # memory and three more of its bytes agree in this run (finding 290).
    check(same == 16417, f"{same} of {total} bytes identical, aligned "
          f"by slot")

    print("=== the engine's name is Apple's (finding 290) ===")
    # Apple's second LONGINTI text block repeats the first from byte 129,
    # and past its trailer holds the source that followed IMPLEMENTATION.
    second = araw[2 * 512:3 * 512]
    check(second[129:422] == araw[512 + 129:512 + 422]
          and second[432:].startswith(b'EDURE DECOPS;\r\x10"EXTERNAL;'),
          f"Apple's slack declares the engine: {second[432:458]!r}")
    ulong = (RUN / "ULONG.CODE").read_bytes()
    native = (ROOT / "src" / "native" / "LONGINTS.TEXT").read_text()
    # (the name check reads the tree; LABELS' copy equals it, above)
    check(b"DECOPS  " in ulong and b"LONGOPS" not in ulong
          and ".PROC DECOPS,0" in native,
          "ULONG's link information and src/native/LONGINTS.TEXT name it "
          "DECOPS")

    print()
    if fail:
        print(f"library units: {len(fail)} check(s) failed")
        return 1
    print("library units: all six code segments Apple's")
    print("library-units-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
