"""Lift two programs whose Pascal source is on the same disk, and diff.

Everything in this repo reads binaries and argues backwards. Nothing had
ever been checked against source Apple compiled, because no source-and-
binary pair was in `evidence/` -- until the APPLE3 disks arrived with
`HAZELGOTO` and `SOROCGOTO`, the two GOTOXY replacements the manual tells
users to write (finding 47b). Each is 23 lines of Pascal and a 1024-byte
codefile, compiled by the compiler being reconstructed.

They are far too small to prove anything about the compiler at large. What
they do is calibrate: the decoder, the stack model, the expression
reconstruction and the structuriser all run end to end here against an
answer key, and any disagreement is a defect in this repo rather than a
question about Apple.

What is compared, all of it derived from the source text read off the disk
rather than written down here:

  * the ordered sequence of **conditions**;
  * the ordered sequence of **assignment targets**;
  * the ordered sequence of **right-hand sides**;
  * the **integer literals**, as a sequence.

Plus four things the source pins that the binary otherwise only suggests:

  * **Variable layout.** `PROCEDURE FGOTOXY(X,Y:INTEGER)` with a local
    `SEND` must put `Y` at offset 1, `X` at 2 and `SEND` at 3 -- parameters
    below locals (finding 46), each declaration allocated backwards
    (finding 33). The name map used for the diff is *predicted* from those
    two rules before the diff runs, so a wrong rule fails the whole
    comparison rather than being fitted to it.
  * **The frame.** `(PARAM + DATA)/2` must equal the highest offset the
    code touches, which is `SEND`'s second word.
  * **`UNITWRITE`'s stack effect.** The source calls
    `UNITWRITE(2,SEND,4)`; `CSP_EFFECT[6]` claims six words. So the emitted
    call must be `(2, addr, 0, 4, 0, 0)` -- the array passed as an
    address/offset pair and two defaulted arguments. That is the first CSP
    arity in the table checked against a declaration rather than fitted by
    stack balance.
  * **Structuring.** Both procedures must come out with zero gotos. They
    are nested `if/else` and nothing else, so a goto here would mean the
    structuriser cannot do the simplest case in the language.

Note `ORD('=')` in SOROCGOTO: the compiler folds it, so the comparison
resolves `ORD('c')` on the source side. That is the only rewriting done to
the source text.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.textfile import decode_text
from a2pascal.lift import lift, CSP_EFFECT
from a2pascal.structure import structure

ROOT = Path(__file__).resolve().parents[2]
IMG = ROOT / "evidence" / "disks" / "UCSD Pascal 1.1_3.dsk"
SAMPLES = ("HAZELGOTO", "SOROCGOTO")
# Predicted, not observed: parameters occupy the low offsets and locals
# follow (finding 46), and a declaration allocates its identifiers backwards
# (finding 33). PROCEDURE FGOTOXY(X,Y) with a local SEND therefore gives:
PREDICTED = {1: "Y", 2: "X", 3: "SEND"}


def norm(s: str) -> str:
    """Strip spaces, parentheses and the lifter's address-of marker."""
    s = re.sub(r"\(\*.*?\*\)", "", s, flags=re.S)
    s = s.replace("@", "").replace("^", "")
    s = re.sub(r"ORD\('(.)'\)", lambda m: str(ord(m.group(1))), s, flags=re.I)
    return re.sub(r"[\s()]", "", s).upper()


def from_source(text: str):
    """(conditions, targets, right-hand sides) in order, from the Pascal."""
    body = text[text.upper().index("OF 0..255;"):]
    body = body[body.upper().index("BEGIN") + 5:]
    body = body[:body.upper().index("END;")]
    body = re.sub(r"\(\*.*?\*\)", " ", body, flags=re.S)
    conds = [norm(m) for m in re.findall(r"\bIF\b(.*?)\bTHEN\b", body,
                                         re.I | re.S)]
    tgts, rhs = [], []
    for m in re.finditer(r"([A-Z_][A-Z0-9_]*(?:\[[^\]]*\])?)\s*:=\s*([^;]*?)"
                         r"(?=\s*(?:;|\bELSE\b|$))", body, re.I | re.S):
        tgts.append(norm(m.group(1)))
        rhs.append(norm(m.group(2)))
    return conds, tgts, rhs


def from_lifted(text: str):
    conds = [norm(m) for m in re.findall(r"\bif\s+(.*?)\s+then\b", text)]
    tgts, rhs = [], []
    for m in re.finditer(r"^\s*(\S.*?)\s*:=\s*(.*?);\s*$", text, re.M):
        tgts.append(norm(m.group(1)))
        rhs.append(norm(m.group(2)))
    return conds, tgts, rhs


def main() -> int:
    bad, checked = [], 0

    def check(cond, msg):
        nonlocal checked
        checked += 1
        if not cond:
            bad.append(msg)

    disk = PascalDisk.from_file(IMG)

    def read(name):
        e = disk.find(name)
        return disk.read_blocks(e.first_block, e.blocks)[:e.size]

    for base in SAMPLES:
        src = decode_text(read(base + ".TEXT"))
        e = disk.find(base + ".CODE")
        cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))

        check(len(cf.segments) == 1 and cf.segments[0].name == "GOXY",
              f"{base}: segments are "
              f"{[s.name for s in cf.segments]}, expected one named GOXY")
        seg = cf.segments[0]
        outer = next(p for p in seg.procedures if p.number == 1)
        proc = next(p for p in seg.procedures if p.number == 2)

        check(outer.lex_level == 255,
              f"{base}: the outer block's lex is {outer.lex_level}, not -1, "
              f"though the source begins (*$U-*)")
        check(outer.enter_ic == outer.exit_ic,
              f"{base}: the dummy main has a body; the source is BEGIN END")
        check(proc.lex_level == 0,
              f"{base}: FGOTOXY is at lex {proc.lex_level}, expected 0")

        # -- the frame, and the layout it implies -------------------------
        check(proc.param_size == 4,
              f"{base}: {proc.param_size} bytes of parameters for "
              f"(X,Y:INTEGER), expected 4")
        check(proc.data_size == 4,
              f"{base}: {proc.data_size} bytes of locals for a "
              f"PACKED ARRAY[0..3] OF 0..255, expected 4")
        frame = (proc.param_size + proc.data_size) // 2
        check(frame == 4, f"{base}: frame is {frame} words, expected 4")

        blocks = lift(seg, proc, cf, "")      # "" = no compiler name tables
        text, gotos, _ = structure(blocks, "")
        check(gotos == 0,
              f"{base}: {gotos} gotos left in a procedure that is nested "
              f"if/else and nothing else")

        # SEND is the only variable whose address is taken, and it must be
        # the one PREDICTED says.
        addressed = sorted({int(m) for m in re.findall(r"@G(\d+)", text)})
        check(addressed == [3],
              f"{base}: addresses are taken of G{addressed}, but the local "
              f"SEND is predicted at offset 3")
        used = sorted({int(m) for m in re.findall(r"G(\d+)", text)})
        check(used == [1, 2, 3],
              f"{base}: touches G{used}, expected G1..G3")

        named = text
        for off, nm in PREDICTED.items():
            named = re.sub(rf"\bG{off}\b", nm, named)

        sc, st, sr = from_source(src)
        lc, lt, lr = from_lifted(named)
        check(sc == lc, f"{base}: conditions differ\n    source {sc}\n"
                        f"    lifted {lc}")
        check(st == lt, f"{base}: assignment targets differ\n    source {st}\n"
                        f"    lifted {lt}")
        check(sr == lr, f"{base}: right-hand sides differ\n    source {sr}\n"
                        f"    lifted {lr}")
        check(len(st) > 4,
              f"{base}: only {len(st)} assignments matched; the comparison "
              f"is too thin to mean anything")

        nums_s = re.findall(r"\d+", "".join(sr) + "".join(sc))
        nums_l = re.findall(r"\d+", "".join(lr) + "".join(lc))
        check(nums_s == nums_l,
              f"{base}: integer literals differ {nums_s} vs {nums_l}")

        # -- UNITWRITE ----------------------------------------------------
        call = re.search(r"UNITWRITE\((.*?)\);", named)
        check(call is not None,
              f"{base}: no UNITWRITE call in the lifted body, though the "
              f"source ends with one")
        if call:
            args = [a.strip() for a in call.group(1).split(",")]
            check(CSP_EFFECT[6] == (6, 0),
                  f"CSP_EFFECT[6] is {CSP_EFFECT[6]}, not (6, 0)")
            check(len(args) == 6,
                  f"{base}: UNITWRITE emitted {len(args)} words, and "
                  f"CSP_EFFECT[6] claims 6")
            args += [""] * (6 - len(args))      # so a short call reports
            check(args[0] == "2" and args[1] == "@SEND" and args[2] == "0",
                  f"{base}: UNITWRITE's first three words are {args[:3]}, "
                  f"expected the unit number and SEND as an address/offset "
                  f"pair")
            check(args[3] == "4",
                  f"{base}: UNITWRITE's length word is {args[3]}, and the "
                  f"source passes 4")
            check(args[4] == "0" and args[5] == "0",
                  f"{base}: UNITWRITE's defaulted block and mode words are "
                  f"{args[4:]}, expected 0 and 0")

        print(f"{base}: {len(st)} assignments, {len(sc)} conditions, "
              f"{gotos} gotos -- matches source")

    if bad:
        print("\n".join(bad))
        return 1
    print(f"{checked} checks, all passed")
    print("calibrate-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
