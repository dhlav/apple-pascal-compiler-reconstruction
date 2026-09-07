"""Lay out `SYSTEM.ASSMBLER`'s global VAR block from the binary alone.

`varblock.py` does this for `SYSTEM.COMPILER`, and it can lean on names:
UCSD II.0's own source declares most of that block, so each object arrives
with a name and a type and the job is to check that they allocate where
Apple put them. The assembler has no such source anywhere -- finding 235 --
so every one of its 2215 words has to come out of the p-code that touches
it, and the only thing holding the block together is that the sizes sum.

That makes the sum the whole test, and it is one the binary can fail. The
outer block's frame is `(PARAM SIZE + DATA SIZE) / 2` words (finding 46).
Words 1 and 2 are `COMPINIT`'s `LC := LC+2` and are not declarations. Every
object the map infers is laid end to end from word 3, gaps are declared
explicitly rather than skipped, and the last declaration has to end exactly
on the frame. A missing object, a mis-sized one, or a gap swallowed by its
neighbour all show up here as an arithmetic failure and not as a compile
that quietly puts every later global one word out.

Three of the objects are file variables and they are the reason a size
model is needed rather than a word count. `BODY2` emits
`LDA 0,VADDR; LDA 0,VADDR+FILESIZE; <recwords>; CXP 0,3` for each
(BODYPART.text), so the FINIT sites in `TLA.1` say what each one is:

  * recwords 0 -- `INTERACTIVE`, FILESIZE + a one-word window;
  * recwords -1 -- an untyped `FILE`, NILFILESIZE words and no window at
    all, its +300 address landing inside the variable that follows;
  * recwords 8 -- `FILE OF` an eight-word type, FILESIZE + eight.

Get any of those three wrong and the block still *looks* contiguous while
being 260 words adrift, which is precisely the failure the round trip is
here to catch.

Names are `G<offset>`: not recovered, and writing a guess would be worse
than writing none. Types are placeholders with the right size, which is
all the compiler needs to allocate Apple's offsets.

Writes analysis/reconstruction/asm-globals-1.1.text and -1.3.text.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a2pascal.codefile import CodeFile
from a2pascal.disk import PascalDisk
from a2pascal.globals import collect, find_files, infer_objects

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "analysis" / "reconstruction"
TARGET = "SYSTEM.ASSMBLER"
DISKS = {
    "1.1": "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk",
    "1.3": "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk",
}
FILESIZE, NILFILESIZE = 300, 40


def file_type(recwords: int) -> tuple[str, int, str]:
    """(declared type, words allocated, why) for one FINIT tag."""
    if recwords == 0:
        return "INTERACTIVE", FILESIZE + 1, "recwords 0"
    if recwords == -1:
        return "FILE", NILFILESIZE, "recwords -1, no window allocated"
    if recwords == -2:
        return "TEXT", FILESIZE + 1, "recwords -2"
    return (f"FILE OF PACKED ARRAY [0..{recwords * 2 - 1}] OF CHAR",
            FILESIZE + recwords, f"recwords {recwords}")


def declare(words: int) -> str:
    if words == 1:
        return "INTEGER"
    return f"ARRAY [0..{words - 1}] OF INTEGER"


# The block is meant to be pasted into Pascal source, which is 80 columns
# (mkworkdisk.py enforces it), so the inline comment carries the offset, the
# size and a one-word tag for how the size was arrived at. The evidence
# behind each tag is in analysis/global_map/globals-ASSMBLER-<ver>.txt in
# full; abbreviating it here does not lose it.
TAGS = [("gap", "gap"), ("sized by", "measured"),
        ("bounded by", "bounded"), ("file variable", "file")]


def tag(why: str) -> str:
    for prefix, short in TAGS:
        if why.startswith(prefix):
            return short
    return "touched"


def build(ver: str, fname: str) -> list[str]:
    disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / fname)
    e = disk.find(TARGET)
    cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))
    table, _acc, frame = collect(cf, ver)
    # The words before the first declaration, read off the block rather than
    # assumed. TLA is a SEGMENT PROCEDURE under (*$U-*) (finding 235a), so
    # these two are its own parameters -- the pair SYSTEM.PASCAL enters
    # segment 1 with, and which the assembler never reads -- not the
    # LC := LC+2 an ordinary program main gets. Either way PARAM SIZE is
    # where the codefile records the count, and hard-coding 2 would make the
    # one thing separating a parameter word from a declared word
    # unfalsifiable (findings 55c, 59).
    outer = next(p for s_ in cf.segments if s_.length
                 for p in s_.pcode_procedures if p.number == 1
                 and s_.number == 1)
    param_words = outer.param_size // 2
    objects = sorted(infer_objects(table, frame), key=lambda o: o["offset"])
    at = {o["offset"]: o for o in objects}
    files = {fib: rec for fib, _win, rec, _site in find_files(cf)}
    # Every address a FINIT computes that is not the FIB itself: the real
    # window of a typed file, and the fiction BODY2 emits for an untyped one.
    # An object at one of these is not a declaration of its own -- but which
    # ones a file actually covers is what the round trip below has to decide,
    # so this is only the set of addresses allowed to disappear, not a
    # decision about any of them.
    computed = {win for _fib, win, _rec, _site in find_files(cf)}

    rows, cursor, cover = [], param_words + 1, None
    for o in objects:
        off = o["offset"]
        if off < cursor:
            # Swallowed by the declaration before it. Two things may be: a
            # FINIT-computed address, and a field of an object the map itself
            # calls a record -- it says so, naming the field offsets. Anything
            # else means a size model quietly eating a variable.
            if off not in computed and (cover is None
                                        or cover["kind"] != "record"):
                raise SystemExit(
                    f"[{ver}] the declaration at {rows[-1][0]} covers word "
                    f"{off}, which the binary addresses in its own right")
            continue
        cover = o
        if off > cursor:
            # A gap is only ever evidence about the object BEFORE it -- that
            # it was measured (MOV/LDM pinned its width) and Apple declared
            # something after it nothing reads. A file variable's width is
            # not measured, it is modelled, so a gap after one is not a gap:
            # it is the model coming up short and papering over the
            # difference. Refuse rather than absorb it.
            if rows and rows[-1][3].startswith("file variable"):
                raise SystemExit(
                    f"[{ver}] the file at {rows[-1][0]} is modelled as "
                    f"{rows[-1][1]} words and leaves {off - cursor} before "
                    f"word {off}; a file's size is not sized by distance, so "
                    f"this is the model being wrong")
            rows.append((cursor, off - cursor, declare(off - cursor),
                         "gap: no instruction touches these words"))
        if off in files:
            typ, words, why = file_type(files[off])
            rows.append((off, words, typ, f"file variable, {why}"))
        else:
            words = o["words"] or 1
            rows.append((off, words, declare(words), o["sizing"]))
        cursor = off + words

    # The round trip, and the only check this block has. Sizes come from two
    # independent places: an ordinary object is as wide as the distance to
    # the next offset the binary touches, which is true by construction and
    # proves nothing on its own, but a FILE is sized from FILESIZE,
    # NILFILESIZE and BODY2's recwords tag -- numbers that know nothing about
    # where the next variable is. So a wrong file model shows up here as a
    # declaration landing off a touched offset, and the three files between
    # them account for 649 of the 2215 words.
    lc = param_words + 1
    for off, words, _typ, _why in rows:
        if lc != off:
            raise SystemExit(f"[{ver}] the declaration for word {off} "
                             f"allocates at {lc}")
        if off in at and at[off]["words"] and off not in files                 and at[off]["words"] != words:
            raise SystemExit(f"[{ver}] word {off} is {words} words here and "
                             f"{at[off]['words']} in the map")
        lc += words
    if lc != frame + 1:
        raise SystemExit(f"[{ver}] the block ends at {lc - 1}, "
                         f"but the frame runs to {frame}")
    # And every offset the binary touches has to be inside some declaration.
    for off in table:
        if off > frame or (off <= param_words and off not in files):
            continue
        prev = max(r[0] for r in rows if r[0] <= off)
        span = next(r[1] for r in rows if r[0] == prev)
        if off >= prev + span:
            raise SystemExit(f"[{ver}] word {off} is touched but falls in no "
                             f"declaration")

    ngap = sum(1 for r in rows if r[3].startswith("gap"))
    L = [f"Apple Pascal {ver} {TARGET} -- the global VAR block,",
         "laid out in Apple's allocation order.",
         "",
         f"Frame: offsets 1..{frame}, from PARAM SIZE + DATA SIZE of the",
         f"outer block (finding 46). {len(rows)} declarations, "
         f"{sum(r[1] for r in rows)} words, no gaps and no overlaps.",
         f"{ngap} of them cover words no instruction touches.",
         "",
         "Generated by tools/asmvars.py; do not edit. NAMES ARE NOT",
         "RECOVERED -- G<offset> is the offset, not a claim about what",
         "Apple called it -- and neither are the types: every placeholder",
         "here allocates the right number of words and says nothing else.",
         "What IS verified is the arithmetic, which the tool refuses to",
         "write out unless every declaration lands on the offset the binary",
         "uses and the last one ends exactly on the frame.",
         "",
         f"{{ Offsets 1..{param_words} are TLA's own parameter words, the pair",
         "  SYSTEM.PASCAL enters segment 1 with and the assembler never",
         "  reads (findings 59, 235a). They are not declarations: writing",
         "  them below would make the compiled frame two words too wide. }",
         "",
         "VAR",
         ]
    for off, words, typ, why in rows:
        name = f"G{off}"
        L.append(f"  {name:<9}: {typ};"
                 f"{'':<{max(1, 42 - len(typ))}}"
                 f"{{ {off:>4} {words:>4}w {tag(why)} }}")
    return L + [""]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for ver, fname in DISKS.items():
        lines = build(ver, fname)
        f = OUT / f"asm-globals-{ver}.text"
        f.write_text("\n".join(lines), encoding="ascii", errors="replace")
        n = sum(1 for x in lines if x.startswith("  G"))
        print(f"[{ver}] wrote {f.name}: {n} declarations")
    return 0


if __name__ == "__main__":
    sys.exit(main())
