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
RUN = (ROOT / "acceptance" / "2026-09-12-assembler-i5-names"
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
    # Finding 246. PROCEND is 6 of 9 now; only .1, .3 and .4 are left.
    "PROCEND.2", "PROCEND.9",
    # Finding 247. PROCEND is 7 of 9; only .1 and .3 are left.
    "PROCEND.4",
    # Finding 248. PROCEND is 8 of 9 -- only its own 520-instruction
    # body is left.
    "PROCEND.3",
    # Finding 249. PROCEND is complete: its own body, the second-largest
    # in the file, and the first whole segment of the assembler to come
    # out Apple's bytes. It is also what measured the frame -- 651
    # declared words and one FOR limit temp, not 652 declared.
    "PROCEND.1",
    # Finding 250: seven of the data-generating pseudo-op handlers, six of
    # them exact on the first compile. `.5` is what turned the invented
    # five-word record into the FIVEREC that was already declared.
    "ASSEMBLE.5", "ASSEMBLE.7", "ASSEMBLE.8", "ASSEMBLE.11",
    "ASSEMBLE.12", "ASSEMBLE.13", "ASSEMBLE.14",
    # Finding 251: ASMREC's variant, which findings 239 and 250d left
    # open. `INITIALI.3` is the runtime endian test behind global 57;
    # `TLA.24` seeds the FIVEREC at global 13; `ASSEMBLE.9` is the
    # .DEF/.REF helper that needed word 7 to be a FIVEP; `ASSEMBLE.33`
    # scans the macro buffers.
    "INITIALI.3", "TLA.24", "ASSEMBLE.9", "ASSEMBLE.33",
    # Finding 254: ASSEMBLE is complete, all 33. `.1` went last because
    # every CLP in it is a procedure number -- and it still cost one,
    # `CXP 1,7` where this had `CLP 7`, two procedures named 7 one line
    # apart. Word 6 of ASMREC moved into the variant on the way, which
    # finding 251e had predicted.
    "ASSEMBLE.1", "ASSEMBLE.2", "ASSEMBLE.3", "ASSEMBLE.4",
    "ASSEMBLE.6", "ASSEMBLE.10", "ASSEMBLE.15",
    # Finding 255: SYMTBLDUMP is complete, all three, first compile. The
    # sort tree, the in-order walk, and WRITE of a PACKED ARRAY OF CHAR
    # taking a one-word LOADADDRESS rather than a two-word BYTEADDRESS.
    "SYMTBLDU.1", "SYMTBLDU.2", "SYMTBLDU.3",
    # Finding 256: INITIALIZE is complete, and with it five of the six
    # segments. The directive table in .2 names every token code the rest
    # of the file compares against; .4's hash is bitwise arithmetic on a
    # BOOLEAN-declared word; .6 casts an integer to a pointer through a
    # one-word variant record.
    "INITIALI.1", "INITIALI.2", "INITIALI.4", "INITIALI.5", "INITIALI.6",
    # Finding 257: the first six of TLA's 38, all exact on the first
    # compile. `.3` swaps the two bytes of a word through BYTEPAIR; `.5`
    # is the I/O error reporter, and its `X1: BOOLEAN` is visible only in
    # the body (PARAM SIZE is 2 either way); `.8` writes the
    # MEMAVAIL/line banner; `.19` validates a parsed operand and has five
    # parameters and no locals at all; `.20` is MOD with the correction a
    # negative dividend needs; `.25` accumulates cross-reference words
    # seven to a record and PUTs when the seventh lands.
    "TLA.3", "TLA.5", "TLA.8", "TLA.19", "TLA.20", "TLA.25",
    # Finding 258: the byte emitter and its listing line, the
    # undefined-local sweep, and the line copier. `.4` and `.23`
    # close together -- `.23` reads `.4`'s locals 4 and 5 with
    # `LOD 1,n` and has no frame of its own at all.
    "TLA.4", "TLA.6", "TLA.7", "TLA.23",
    # Finding 259: the listing writers and the two files. A number is
    # TWO words wide, which is what the declared-and-never-touched
    # words in TLA.3 and TLA.14 were -- those two frames and TLA.4's
    # stay exact with the placeholders gone, and would not if the
    # type were one word and a pad.
    "TLA.9", "TLA.11", "TLA.12", "TLA.22", "TLA.26", "TLA.29",
    # Finding 260: the error reporter and the two reference
    # dispatchers, which are the same CASE on the same word with
    # different handlers under it -- and both end by handing a
    # two-word number to TLA.13, the third and fourth frame to need
    # NUMREC. `.30` opens an INCLUDE level.
    "TLA.2", "TLA.14", "TLA.15", "TLA.30",
    # Finding 261: the line writer and the word writer. `TLA.13`
    # takes the two-word number by VAR and copies it with MOV 2,
    # which retyped a sixth frame -- `ASSEMBLE.9`'s, whose own
    # placeholder was the second word -- without moving a byte.
    "TLA.10", "TLA.13",
    # Finding 262: the scanner. `.16` reads the next character out of
    # one of three sources and `.17` classifies it into one of 30
    # token codes; 407 and 160 instructions, both exact on the first
    # compile, and between them they pin five more BOOLEAN globals.
    "TLA.16", "TLA.17",
    # Finding 263: EXPREND, written from UCSD's own I.5 listing --
    # the same procedure, the same error number 27, the same three
    # cases. The run that carries it also carries the whole naming
    # pass, and every name in it is byte-neutral: these 82 were
    # exact before it and are exact after.
    "TLA.32",
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
STILL_DIFFERS = ["TLA.34", "TLA.35", "TLA.33",
                 "TLA.18", "TLA.36", "TLA.37", "TLA.38"]

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
