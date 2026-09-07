"""What Apple's own compiler made of the `SYSTEM.ASSMBLER` skeleton.

The kept run named by `RUN` is what Apple's real 1.3 `SYSTEM.COMPILER`
wrote from `src/pascal/programs/1.3/ASSMBLER.text` under the emulator --
672 lines, zero errors -- and the directory keeps that source alongside it,
so the run is reproducible rather than merely archived.

Almost every procedure in it is still a stub, so a count of exact bodies is
not what this run is evidence for. What it is evidence for is the SHAPE,
and the shape is the part that cannot be fixed later one procedure at a
time: get the segment numbering, the nesting or the declaration order wrong
and every `CGP`, `CLP` and `CXP` written afterwards is wrong with it, however
well each body reads (findings 61, 199, 235c).

So the claims under test are structural, and each can fail:

  1. **Six segments, with Apple's names, numbers, `SEGKIND` and procedure
     counts.** `TLA` on segment 1 and the five nested ones on 7-11 is what
     finding 235a's `(*$U-*)` + `(*$NS 7*)` reading predicts; an ordinary
     program would have put them somewhere else entirely.
  2. **Every shared procedure agrees on lex level and PARAM SIZE.** Lex
     level is the nesting tree of finding 235c, read back out of what the
     compiler did with the declarations; PARAM SIZE is the signature.
  3. **`TLA.1` is instruction- and frame-identical.** That one body is
     where the 2215-word `VAR` block is measured: `data 4430` only comes
     out if all 112 declarations allocate at Apple's offsets, and the three
     compiler-generated `FINIT`s and `FCLOSE`s only come out in Apple's
     order if the file variables are declared in Apple's.
  4. **The two known differences are still exactly those two, and no
     others.** Apple's `PASCALIO` is absent here because it cannot be
     rebuilt (finding 235b), and ours has a `PASCALSY` host segment Apple's
     shipped file does not, which is finding 105a's open item showing up in
     a second file. Naming them is what keeps 1-3 honest: a comparison that
     quietly tolerated a missing segment could not fail on one.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from a2pascal.codefile import CodeFile
from oscmp import compare, shipped_codefile
from procbuild import listing

ROOT = Path(__file__).resolve().parents[2]
RUN = (ROOT / "acceptance" / "2026-09-07-assembler-liwriter"
       / "ASSMBLER.CODE")
TARGET = "SYSTEM.ASSMBLER"

# (name, segment number, SEGKIND, p-code procedures) -- Apple's, and ours
# has to be the same six.
SEGMENTS = [
    ("TLA", 1, "LINKED", 38),
    ("INITIALI", 7, "LINKED", 6),
    ("SYMTBLDU", 8, "LINKED", 3),
    ("PROCEND", 9, "LINKED", 9),
    ("ASSEMBLE", 10, "LINKED", 33),
    ("PRINTERR", 11, "LINKED", 1),
]

EXACT = [
    # The segment body, written for real: 37 instructions, three FINITs in
    # and three FCLOSEs out, `params`/`data` 4/4430 (finding 235e).
    "TLA.1",
    # Finding 238's first five bodies, all exact on the first compile.
    # Each one pins a declaration as much as a statement: `TLA.21` that
    # IOCHECK is on (its two `CSP 0`s), `ASSEMBLE.16` that globals 406 and
    # 447 are `STRING[80]`, and `.19`/`.20` that global 10 is a one-word
    # variant with a byte at bits 0..7 and a three-bit field at 2..4.
    "TLA.21", "ASSEMBLE.16", "ASSEMBLE.18", "ASSEMBLE.19", "ASSEMBLE.20",
    # Finding 239: global 3's record. `ASSEMBLE.17` is the CASE that
    # dispatches on its word 5, and it is what caught the field list
    # reversing within a clause -- one instruction, `SIND 7` for `SIND 5`.
    # `TLA.31` writes its enclosing FUNCTION's result from inside a nested
    # procedure and then EXITs it.
    "ASSEMBLE.17", "ASSEMBLE.21", "ASSEMBLE.29", "ASSEMBLE.32", "TLA.31",
    # Finding 240: ASSEMBLE.17's whole nested family, all fourteen of
    # 18..31, so the segment's dispatcher and every arm under it are
    # Apple's bytes. .23 is the largest at 165 instructions.
    "ASSEMBLE.22", "ASSEMBLE.23", "ASSEMBLE.24", "ASSEMBLE.25",
    "ASSEMBLE.26", "ASSEMBLE.27", "ASSEMBLE.28", "ASSEMBLE.30",
    "ASSEMBLE.31",
    # Finding 241: the pair nested in TLA.14, which could not be written
    # before its frame was mapped from their own LOD/STR operands -- and
    # TLA.14's own frame comes out 6/10 as a result, with a stub body.
    "TLA.27", "TLA.28",
    # Finding 242: PRINTERR is complete, its one procedure. SEEK turned
    # out to be a standard procedure, so the segment needed no USES at
    # all -- which was the last open structural question about the file.
    "PRINTERR.1",
    # Finding 243: the first two of PROCEND, and they place its own
    # frame -- 652 words with a FILE at 343, read off `LDA 3,343` and
    # `LDA 2,343` in three of its children.
    "PROCEND.5", "PROCEND.6",
    # Finding 244: the eight-word linker-information record modelled as
    # the variant it is, and the packing rule that came out of it.
    "PROCEND.8",
    # Finding 245: the LIENTRY writer, 267 instructions and the largest
    # body in the file so far. Three nested CASEs on one selector, and
    # the arms are emitted in SOURCE order, not label order.
    "PROCEND.7",
]

# The six procedures that end `RNP 1` rather than `RNP 0`: they are
# FUNCTIONs, and nothing else in the file is. PARAM SIZE alone cannot see
# this -- a function's result costs two words, so `FUNCTION F: BOOLEAN` and
# `PROCEDURE P(X, Y: INTEGER)` both come to 4 and the skeleton had four of
# these declared the wrong way while matching Apple's number exactly. The
# return width is what tells them apart, so it is checked on its own.
FUNCTIONS = {"TLA.3": 1, "TLA.18": 1, "TLA.19": 1, "TLA.20": 1,
             "ASSEMBLE.3": 1, "ASSEMBLE.18": 1}

# Still stubs, kept as the discrimination control. If these came back
# "identical" the comparison would be broken, not the reconstruction.
STILL_DIFFERS = ["TLA.17", "ASSEMBLE.1", "ASSEMBLE.15", "PROCEND.1",
                 "INITIALI.1", "SYMTBLDU.1", "TLA.14"]

# Apple has these and we cannot (finding 235b); we have these and Apple
# does not (finding 105a). Both lists are exhaustive on purpose.
ONLY_APPLE = [f"PASCALIO.{n}" for n in range(1, 6)]
ONLY_OURS_SEG = "PASCALSY"

fail = []


def check(ok: bool, label: str) -> None:
    print(("  ok   " if ok else "  FAIL ") + label)
    if not ok:
        fail.append(label)


def shape(cf) -> dict:
    return {s.name.strip(): (s.number, s.segkind, len(s.pcode_procedures))
            for s in cf.segments if s.length}


def returns(cf) -> dict:
    """{procedure: words returned} for every one that returns anything.

    `BODY3` emits `RNP`/`RBP` with the result size, so a non-zero operand
    on the last instruction is what makes a procedure a FUNCTION.
    """
    # Only the six real segments: our own build also carries the $U- host
    # segment, whose 42 procedures are unresolved FORWARDs with no bodies
    # to decode at all (finding 105a).
    names = {n for n, _num, _k, _c in SEGMENTS}
    out = {}
    for s in cf.segments:
        if not s.length or s.name.strip() not in names:
            continue
        for p in s.pcode_procedures:
            last = listing(s, p)[-1].strip()
            if last.startswith(("RNP", "RBP")) and int(last.split()[1]):
                out[f"{s.name.strip()}.{p.number}"] = int(last.split()[1])
    return out


def signatures(cf) -> dict:
    out = {}
    for s in cf.segments:
        if not s.length:
            continue
        for p in s.pcode_procedures:
            out[f"{s.name.strip()}.{p.number}"] = (p.lex_level, p.param_size)
    return out


def main() -> int:
    if not RUN.exists():
        print(f"{RUN} is missing -- the acceptance run must be kept verbatim")
        return 1
    ours_cf = CodeFile(RUN.read_bytes())
    apple_cf = shipped_codefile(TARGET)

    print("=== six segments, with Apple's numbers and procedure counts ===")
    ours, apple = shape(ours_cf), shape(apple_cf)
    for name, num, kind, nproc in SEGMENTS:
        got = ours.get(name)
        check(got == (num, kind, nproc),
              f"{name}: segment {num}, {kind}, {nproc} procedures "
              f"(ours: {got})")
        check(apple.get(name) == (num, kind, nproc),
              f"{name}: and that is what Apple's shipped file has")

    print("=== lex level and PARAM SIZE, every shared procedure ===")
    o, a = signatures(ours_cf), signatures(apple_cf)
    both = sorted(set(o) & set(a))
    wrong = [k for k in both if o[k] != a[k]]
    check(len(both) == 90, f"{len(both)} procedures matched by name and "
                           f"number, expected 90")
    check(not wrong, "every one agrees on lex level and PARAM SIZE"
                     + (f" -- {[(k, o[k], a[k]) for k in wrong[:4]]}"
                        if wrong else ""))

    print("=== six FUNCTIONs, and only those six ===")
    ow, aw = returns(ours_cf), returns(apple_cf)
    check(aw == FUNCTIONS, f"Apple's shipped file returns a value from "
                           f"exactly {sorted(FUNCTIONS)}")
    check(ow == aw, f"and so does ours -- {sorted(ow)}")

    print("=== bodies Apple's compiler reproduces exactly ===")
    rows = compare(ours_cf, apple_cf)
    for key in EXACT:
        r = rows.get(key)
        check(bool(r) and r["exact"],
              f"{key} instruction- and frame-identical")

    print("=== the comparison can still tell a stub from a body ===")
    for key in STILL_DIFFERS:
        r = rows.get(key)
        check(bool(r) and not r["exact"],
              f"{key} still differs, as a stub should")

    print("=== the two known differences, and no others ===")
    only_apple = sorted(set(a) - set(o))
    check(only_apple == sorted(ONLY_APPLE),
          f"only Apple has {only_apple} -- PASCALIO, finding 235b")
    only_ours = sorted({k.rsplit(".", 1)[0] for k in set(o) - set(a)})
    check(only_ours == [ONLY_OURS_SEG],
          f"only ours has {only_ours} -- the $U- host segment, finding 105a")

    print()
    if fail:
        print(f"assembler skeleton: {len(fail)} check(s) failed")
        return 1
    print(f"assembler skeleton: 6 segments, {len(both)} signatures, "
          f"{len(EXACT)} body exact")
    print("asm-exact-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
