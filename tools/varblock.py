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
can be wrong is if an offset is missing or misnamed. `probe_varblock.py`
then re-runs the compiler's allocation rule over what this writes and
requires every name to land back on the offset it came from.

Writes analysis/reconstruction/globals-1.1.text and -1.3.text.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.globals import collect
from a2pascal.names import GLOBAL_NAMES
from vardecl import var_block, size_of

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
        if got == words:
            return typ, "II.0"
        return typ, f"II.0 declares {got} words, Apple has {words}"
    if words == 1:
        return "INTEGER", "ours: one word, type not recovered"
    return f"ARRAY [0..{words - 1}] OF INTEGER", \
           f"ours: {words} words, shape not recovered"


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
    offsets = sorted(o for o in names
                     if o not in PHANTOM[ver] and o not in covered)
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

    # Round-trip: allocate the block back under the compiler's own rule --
    # start at word 1, each object at the running total -- and require every
    # name to land on the offset it came from, with the last object ending
    # exactly on the frame. Contiguity is by construction, so what this can
    # fail on is a missing or misnamed offset.
    lc = 1
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
