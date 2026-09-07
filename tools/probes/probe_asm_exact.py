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

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "acceptance" / "2026-09-07-assembler-skeleton" / "ASSMBLER.CODE"
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
]

# Still stubs, kept as the discrimination control. If these came back
# "identical" the comparison would be broken, not the reconstruction.
STILL_DIFFERS = ["TLA.17", "ASSEMBLE.1", "PROCEND.1", "INITIALI.1",
                 "SYMTBLDU.1", "PRINTERR.1"]

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
