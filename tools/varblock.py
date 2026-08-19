"""Write the compiler's `VAR` block out in Apple's own order.

The reconstruction has to declare its globals so that the compiler
allocates them at Apple's offsets: every `LDO`, `SRO` and `LAO` in the
binary carries one, so a block that allocates differently produces
different code bytes. Findings 33, 38, 39, 43 and 46 between them recovered
the name at every touched offset and the size of every object; this lays
them out as Pascal.

Three inputs, all of them already checked elsewhere:

  * **the names**, from `a2pascal/names.py` -- 129 of 1.1's 133 touched
    offsets, and the four that are not names are not objects either
    (finding 43);
  * **the frame**, `(PARAM SIZE + DATA SIZE) / 2` of the outer block, which
    is the highest valid offset (finding 46);
  * **the types**, from the UCSD II.0 `VAR` block wherever a name matched
    there, via `vardecl.py`'s own size table.

Sizes are not taken from II.0. Each object's size is the distance to the
next named offset, and the last object's is the distance to the end of the
frame -- so the block is contiguous by construction and the *only* way it
can be wrong is if an offset is missing or misnamed. The block is then
re-allocated under the compiler's own rule and every name has to land back
on the offset it came from.

That check is about *room*, and it was silent about a second thing that
matters just as much: whether the type each declaration is written with
actually allocates the room it is given. It did not, twice. `SEGTABLE` was
emitted with UCSD's eight-word entry where Apple's is nine, and `UFLDPTR`
was emitted as a two-word `CTP`, which is not a thing -- the second word is
the global Apple declared and never references (finding 39b). Either would
have shifted every declaration after it. `reconcile` now lays out every
declared type under Apple's own constants (`applesrc.py`) and requires it to
come to exactly the words the offsets allow, refusing anything it cannot
account for.

Writes analysis/reconstruction/globals-1.1.text and -1.3.text.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.globals import collect
from a2pascal.names import GLOBAL_NAMES
from vardecl import var_block, size_of, expand_inline, INLINE
import applesrc

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "analysis" / "reconstruction"
DISKS = {
    "1.1": "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk",
    "1.3": "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk",
}
# Addresses the binary computes but nothing lives at: `BODY` emits
# `LDA 0,VADDR+FILESIZE` as the FINIT window for every file variable, and
# three of the four land inside LP (finding 43).
PHANTOM = {"1.1": {835, 886, 926, 966}, "1.3": {965, 1016, 1056, 1096}}
# The one object the map splits into its fields, because the compiler
# addresses them individually as well as copying the whole thing: II.0's
# `GATTR: ATTR` (finding 22). Five consecutive one-word variables would
# allocate identically, so this is a question of which source Apple wrote
# and not of which bytes come out -- but II.0's form is the one on record.
# offset -> (name, type, words, the field names the map has)
RECORDS = {"1.1": {3: ("GATTR", "ATTR", 5)}, "1.3": {3: ("GATTR", "ATTR", 5)}}
# The outer block's two PARAMETER words, which are not `VAR` declarations and
# must not be written as any (finding 55c). A UCSD program main is given a
# two-word parameter area whatever its header says, and declared variables
# start at offset 3: of the 21 other Apple-compiled programs across the six
# disks, every single one puts its first global at 3, and `LINEFEED.CODE` --
# one variable, `VAR CHEAT: TWOFACE` -- compiles it to `SRO 3`.
#
# `SYSTEM.COMPILER` is the only one that *uses* those two words, and what it
# keeps there is not in doubt: `NEW(G1, 512)` and `NEW(G2, 650)` match
# `SYMBUFARRAY` and `CODEARRAY` to the word. Declaring them in the `VAR`
# block made the compiled frame two words too wide; leaving them out makes it
# exactly Apple's.
OUTER_PARAMS = {"1.1": (1, 2), "1.3": (1, 2)}


def ii0_types() -> dict[str, str]:
    """II.0's declared type for every name in its VAR block."""
    out = {}
    for ids, typ in var_block():
        for name in ids:
            out[name] = typ
    return out


def render_type(name: str, words: int, typ: str | None) -> str:
    """The declaration's type, and a comment saying where it came from."""
    if typ:
        got, _why = size_of(typ, name)
        # `INLINEREC<n>` is vardecl's bookkeeping for a record declared
        # inline in the VAR block; the declaration has to carry the record.
        typ = expand_inline(typ)
        if got == words:
            return typ, "II.0"
        return typ, f"II.0 declares {got} words, Apple has {words}"
    if words == 1:
        return "INTEGER", "ours: one word, type not recovered"
    return f"ARRAY [0..{words - 1}] OF INTEGER", \
           f"ours: {words} words, shape not recovered"


# Where II.0's declared type does not allocate the words Apple's offsets
# require. Two, and the same two in both releases. Each says what the binary
# says and nothing more.
RETYPE = {
    # Apple's segment table entry is nine words where UCSD's is eight, and
    # the binary indexes it as SEGTABLE[slot*9]. The ninth word's purpose is
    # not recovered, so it is declared and not named.
    # Apple's entry is nine words where UCSD's is eight, and the binary
    # indexes it as SEGTABLE[slot*9]. The extra word is a third name on the
    # LAST identifier list, not a field appended after it: BLOCK's
    # `SEGTABLE[SEGMAP[SEG]].SEGKIND := 1` compiles to `INC 8`, and only a
    # three-name list reversed puts SEGKIND at 8. FINISHSEG pins the other
    # end -- `CODELENG` at 0, the reversed first pair.
    #
    # The added word is SEGNUM, at offset 6, and finding 71 identifies it:
    # SEGINFO reads it into bits 0..7 of the codefile's segment-info word,
    # which is where the segment dictionary keeps a segment's number. UCSD
    # had no need of it because the slot index WAS the number; Apple's
    # SEGMAP decouples the two, so each slot has to record which segment
    # it holds.
    "SEGTABLE": ("ARRAY [SEGRANGE] OF RECORD DISKADDR,CODELENG: INTEGER; "
                 "SEGNAME: ALPHA; SEGKIND, TEXTADDR, SEGNUM: INTEGER END",
                 "Apple's entry is 9 words, indexed SEGTABLE[slot*9]; "
                 "SEGKIND at 8 (BLOCK's INC 8), SEGNUM at 6 (SEGINFO)"),
    # Nibbles, not words. Every reference to SEGMAP is an `IXP 4,4` -- four
    # entries to the word, four bits each -- so its 16 words (8 in 1.1) hold
    # 64 entries (32), and what fits in four bits is a SEGRANGE. Declaring
    # it as an array of INTEGER allocates the right number of words and
    # compiles every access wrong. NEWSEG is the body that measures it.
    "SEGMAP": ("PACKED ARRAY [0..{last}] OF SEGRANGE",
               "reached only by IXP 4,4: {entries} four-bit entries "
               "in {words} words"),
    # 1.3-only, and II.0 has no name for them, so `render_type` would call
    # them INTEGER -- which allocates the one word they occupy and will not
    # compile. COMPTYPES compares both against an `STP` (`FSP1 <> BYTEPTR`),
    # so they are structure pointers, like the CHARPTR and INTPTR beside
    # them. Finding 64.
    "BYTEPTR": ("STP", "compared against an STP in COMPTYPES"),
    # 1.3-only, and used as conditions: SWAPMORE is the test in HOLDMOST and
    # CONLIST is negated in ERROR. `FJP` and `LNOT` on an INTEGER will not
    # compile, so the binary is saying these are BOOLEAN.
    "SWAPMORE": ("BOOLEAN", "the condition in HOLDMOST"),
    "CONLIST": ("BOOLEAN", "negated in ERROR"),
    # More conditions, all from BLOCK: ISPROG is assigned NOT INMODULE,
    # SWAPPING and HAS128K are ORed together, LINKINFO is ANDed with a
    # comparison. RESIDENT is assigned NIL, so it is a pointer; nothing
    # yet dereferences it, so what it points at is not recovered.
    "ISPROG": ("BOOLEAN", "assigned NOT INMODULE in BLOCK"),
    "SWAPPING": ("BOOLEAN", "ORed with HAS128K in BLOCK"),
    "HAS128K": ("BOOLEAN", "ORed with SWAPPING in BLOCK"),
    "LINKINFO": ("BOOLEAN", "ANDed with LEVEL = 1 in BLOCK"),
    # WRITELIN.4 does `LDO 42; LNOT`, and `LNOT` takes a BOOLEAN. Its two
    # uses there both read as "this compilation is of an INTRINSIC unit":
    # it suppresses the linker record for a used unit, and it decides
    # whether a variable's data segment is this unit's own.
    "INTRINSIC": ("BOOLEAN", "LNOTed in WRITELINKERINFO"),
    "RESIDENT": ("^ INTEGER",
                 "assigned NIL in BLOCK; what it points at is not "
                 "recovered"),
    "WORDPTR": ("STP", "compared against an STP in COMPTYPES"),
}
# Offsets that hold a word Apple declared and never uses. Finding 39b: 1.1's
# 72 sits between UFLDPTR at 71 and UPRCPTR at 73, and no LDO, SRO or LAO on
# either disk touches it. Without an explicit declaration the block would
# allocate UFLDPTR's neighbour one word low.
UNUSED = {"1.1": {72: "finding 39b: declared, never referenced"},
          "1.3": {75: "finding 39b: declared, never referenced"}}


def reconcile(rows, ver: str):
    """Make every row's declared type allocate the words it occupies.

    `build` sizes an object by the distance to the next *named* offset, which
    is right about how much room it takes and silent about why. Where the
    type says something smaller, the difference is a word Apple declared
    without naming -- and emitting the short type would shift every
    declaration after it. So this splits the row, and refuses anything it has
    no evidence for.
    """
    lay = applesrc.layout(ver, INLINE)
    types = ii0_types()
    out = []
    for off, name, words, forced, note in rows:
        # A retyped object's bounds can depend on how many words Apple gave
        # it -- SEGMAP is 16 words in 1.3 and 8 in 1.1, and its element count
        # is four times either.
        fmt = dict(words=words, entries=4 * words, last=4 * words - 1)
        typ = RETYPE[name][0].format(**fmt) if name in RETYPE \
            else types.get(name)
        if forced or not typ:
            out.append((off, name, words, forced, note))
            continue
        got = lay.size(typ)
        if got == words:
            if name in RETYPE:
                out.append((off, name, words, typ,
                            RETYPE[name][1].format(**fmt)))
            else:
                out.append((off, name, words, forced, note))
            continue
        if got > words:
            raise SystemExit(
                f"[{ver}] {name}: {typ} lays out as {got} words but only "
                f"{words} are available before the next named offset")
        # Shorter than the room it has. The remainder must be accounted for.
        gap = off + got
        why = UNUSED[ver].get(gap)
        if why is None or words - got != 1:
            raise SystemExit(
                f"[{ver}] {name}: {typ} lays out as {got} words but occupies "
                f"{words}; offset {gap} is not a known unused word")
        out.append((off, name, got, None, None))
        out.append((gap, f"UNUSED{gap}", 1, "INTEGER", why))
    return out


def build(ver: str) -> list[str]:
    disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / DISKS[ver])
    e = disk.find("SYSTEM.COMPILER")
    cf = CodeFile(disk.read_blocks(e.first_block, e.blocks))
    table, _acc, frame = collect(cf, ver)
    names = GLOBAL_NAMES[ver]
    types = ii0_types()

    # Objects are the named offsets, in order. Everything else the binary
    # touches is inside one of them.
    recs = RECORDS[ver]
    covered = {o + k for o, (_n, _t, w) in recs.items() for k in range(1, w)}
    params = OUTER_PARAMS[ver]
    offsets = sorted(o for o in names
                     if o not in PHANTOM[ver] and o not in covered
                     and o not in params)
    rows = []
    for i, off in enumerate(offsets):
        nxt = offsets[i + 1] if i + 1 < len(offsets) else frame + 1
        if off in recs:
            nm, typ, w = recs[off]
            fields = [names[off + k] for k in range(w) if off + k in names]
            rows.append((off, nm, w, typ,
                         f"II.0 record; the map splits it into "
                         f"{', '.join(fields)}"))
            continue
        rows.append((off, names[off], nxt - off, None, None))

    rows = reconcile(rows, ver)

    # Round-trip: allocate the block back under the compiler's own rule --
    # start at word 1, each object at the running total -- and require every
    # name to land on the offset it came from, with the last object ending
    # exactly on the frame. Contiguity is by construction, so what this can
    # fail on is a missing or misnamed offset.
    lc = max(OUTER_PARAMS[ver]) + 1     # declared variables start past them
    for off, name, words, *_ in rows:
        if lc != off:
            raise SystemExit(f"[{ver}] {name} allocates at {lc}, "
                             f"but the binary has it at {off}")
        lc += words
    if lc != frame + 1:
        raise SystemExit(f"[{ver}] the block ends at {lc - 1}, "
                         f"but the frame runs to {frame}")

    touched = sorted(table)
    unnamed = [o for o in touched if o not in names]

    L = [f"Apple Pascal {ver} SYSTEM.COMPILER -- the global VAR block,",
         "reconstructed in Apple's allocation order.",
         "",
         f"Frame: offsets 1..{frame}, from PARAM SIZE + DATA SIZE of the",
         f"outer block (finding 46). {len(rows)} objects, "
         f"{sum(r[2] for r in rows)} words, no gaps.",
         "",
         "Generated by tools/varblock.py; do not edit. Each object's size is",
         "the distance to the next named offset, so the block is contiguous",
         "by construction. The TYPE column is II.0's declaration where the",
         "name matched there and ours otherwise -- a one-word object whose",
         "type was never recovered is written INTEGER, which is a",
         "placeholder and not a claim.",
         "",
         "Declaration order is NOT recovered: the binary fixes the offsets",
         "and nothing else, so this writes one identifier per declaration.",
         "Grouping several into one `VAR a,b,c: T` would reverse them",
         "(finding 33) and is only safe where II.0's own grouping is known",
         "to have survived -- see the drift runs in vardecl-ii0.txt.",
         "",
         f"{{ Offsets {params[0]} and {params[1]} are the outer block's two",
         "  PARAMETER words, not declarations -- see finding 55c. Apple keeps",
         f"  {names[params[0]]} and {names[params[1]]} there; every other Apple-compiled",
         "  program on the six disks leaves them unused and starts its",
         "  variables at offset 3. Writing them below would make the",
         "  compiled frame two words too wide. }",
         "",
         "VAR",
         ]
    for off, name, words, forced, note in rows:
        typ, why = ((forced, note) if forced
                    else render_type(name, words, types.get(name)))
        L.append(f"  {name:<16}: {typ};"
                 f"{'':<{max(1, 34 - len(typ))}}"
                 f"{{ {off:>4}, {words:>4} word{'s' if words != 1 else ' '}"
                 f"  {why} }}")
    L += ["", f"{{ {len(unnamed)} touched offsets are not objects: "
              f"{unnamed} -- finding 43 }}", ""]
    return L


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for ver in DISKS:
        lines = build(ver)
        f = OUT / f"globals-{ver}.text"
        f.write_text("\n".join(lines), encoding="ascii", errors="replace")
        nobj = sum(1 for x in lines if x.startswith("  ") and ":" in x)
        print(f"[{ver}] wrote {f.name}: {nobj} declarations")
    return 0


if __name__ == "__main__":
    sys.exit(main())
