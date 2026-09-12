"""Hold the volume writer against the volumes Apple wrote.

Being able to produce a mountable disk image proves nothing by itself -- an
image can be well-formed and still not be encoded the way Apple's FILER
encodes one. What can be proved is that this module and the reader are exact
inverses, and that the encoding agrees with six real Apple volumes:

  * **the sector map is one map.** Writing a block back where it was read
    from must leave the image bit-identical, at every block of every disk.
    A transposition in the interleave table would survive a read-only tool
    forever and destroy the first disk written with it.

  * **the directory encoder is the reader's inverse.** For each evidence
    disk, re-emit the four directory blocks from nothing but the parsed
    entries and require the original bytes back. That is the real check:
    it pins the name length byte and its padding, the file kind word, both
    date words, the volume entry's block count and file count, and the
    26-byte stride, against directories Apple built.

  * **the text encoder round-trips.** `.TEXT` has two legal spellings of the
    same line -- literal spaces or DLE compression -- so bytes cannot be
    compared. What must hold is `decode(encode(s)) == s`, over every `.TEXT`
    on every disk, in both spellings.

And the writer's own rules have to be enforceable, so the checks below also
require it to *refuse*: a file that fits in no single gap, a name already on
the volume, and a directory whose entries are out of block order.

What none of that can catch is a field the reader and the writer are both
wrong about in the same direction -- they are the same repo. So the last
section asks somebody else: `ucsd-psystem-fs`, an independent implementation
of the format by a different author, has to `fsck` the volume this repo
built, list it, and extract every file back to the source it came from. It
found the first real defect, a blank line added to the end of every file.

It is still not evidence about Apple. The acceptance tier is what settles
that: if Apple's own FILER lists the disk, the encoding is right.
"""
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import BLOCK_SIZE, PascalDisk, format_date
from a2pascal.diskwrite import (DIR_BLOCKS, DIR_START, FIRST_DATA_BLOCK,
                                MAX_FILES, PascalWriter, VolumeFull,
                                encode_date)
from a2pascal.srcfmt import expand_tabs
from a2pascal.textfile import decode_text, encode_text
import xcompile

ROOT = Path(__file__).resolve().parents[2]
DISKS = sorted((ROOT / "evidence" / "disks").glob("*.dsk"))

fails = []
checks = 0


def check(cond, what):
    global checks
    checks += 1
    if not cond:
        fails.append(what)


def refuses(fn, what, exc=Exception):
    global checks
    checks += 1
    try:
        fn()
    except exc:
        return
    fails.append(f"accepted what it must refuse: {what}")


# -- 1. the sector map is shared with the reader ------------------------

for path in DISKS:
    w = PascalWriter.from_file(path)
    r = PascalDisk.from_file(path)
    total = w.volume().total_blocks
    check(all(w.read_block(n) == r.read_block(n) for n in range(total)),
          f"{path.name}: writer and reader disagree about block contents")
    before = w.to_bytes()
    for n in range(total):
        w.write_block(n, w.read_block(n))
    check(w.to_bytes() == before,
          f"{path.name}: rewriting every block in place changed the image")

# -- 2. the directory encoder is the reader's inverse -------------------

for path in DISKS:
    w = PascalWriter.from_file(path)
    vol = w.volume()
    entries = w.entries()
    original = w.directory_bytes()
    rebuilt = w.encode_directory(vol.name, entries, vol.total_blocks,
                                 w._last_boot(), original)
    diff = [i for i in range(len(original)) if original[i] != rebuilt[i]]
    check(not diff,
          f"{path.name}: re-encoded directory differs from Apple's at "
          f"{diff[:8]} (entry {diff[0] // 26 if diff else '-'}, "
          f"byte {diff[0] % 26 if diff else '-'})")
    # The template must not be doing the work. Every live entry has to be
    # rebuilt from the parsed fields, so the same call with a blank template
    # has to reproduce all of them and differ only past the last one.
    scratch = w.encode_directory(vol.name, entries, vol.total_blocks,
                                 w._last_boot(), None)
    live = (len(entries) + 1) * 26
    # Entry 0 carries bytes this cannot account for (DLOADTIME and the last
    # four); every file entry must come back whole.
    check(scratch[26:live] == original[26:live],
          f"{path.name}: file entries are not reconstructible without the "
          f"template -- first mismatch at "
          f"{next((i for i in range(26, live) if scratch[i] != original[i]), None)}")
    check(len(entries) == vol.num_files,
          f"{path.name}: parsed {len(entries)} entries, the volume header "
          f"says {vol.num_files}")

# -- 3. the date word ---------------------------------------------------

# Nothing above touches `encode_date`: a file this writes is never read back
# for its date, so month and day could be transposed and every other check
# would still pass. Held against the dates Apple stamped instead -- decode
# each one, re-encode it, and require the word back.
ndates = nentries = 0
for path in DISKS:
    for e in PascalDisk.from_file(path).directory():
        nentries += 1
        shown = format_date(e.mtime_raw)
        if shown.startswith("<raw"):
            continue        # day 0 or an out-of-range month; not a date
        day, month, year = (int(x) for x in shown.split("-"))
        ndates += 1
        check(encode_date(datetime.date(year, month, day)) == e.mtime_raw,
              f"{path.name}:{e.name}: {shown} re-encodes to "
              f"{encode_date(datetime.date(year, month, day)):#06x}, "
              f"Apple wrote {e.mtime_raw:#06x}")
# Every entry on all six disks carries a decodable date, so the loop above
# must not be skipping any -- otherwise a decoder that rejected everything
# would leave this section vacuously green.
check(ndates == nentries,
      f"{nentries - ndates} of {nentries} entries decoded to no date at all")
# and the ends of the representable window
for d in (datetime.date(1970, 1, 1), datetime.date(2069, 12, 31),
          datetime.date(2026, 8, 16)):
    check(format_date(encode_date(d)) == d.strftime("%d-%m-%Y"),
          f"{d} does not survive encode/decode "
          f"(got {format_date(encode_date(d))})")

# -- 4. .TEXT round-trips, in both spellings ----------------------------

ntext = 0
for path in DISKS:
    d = PascalDisk.from_file(path)
    for e in d.directory():
        if e.kind != "textfile":
            continue
        ntext += 1
        want = decode_text(d.read_blocks(e.first_block, e.blocks))
        for compress in (True, False):
            try:
                got = decode_text(encode_text(want, compress=compress))
            except ValueError as exc:
                fails.append(f"{path.name}:{e.name} would not encode "
                             f"(compress={compress}): {exc}")
                checks += 1
                continue
            check(got == want,
                  f"{path.name}:{e.name} does not survive encode/decode "
                  f"(compress={compress})")
        # Every page must hold whole lines: no page may end mid-line, which
        # is the one .TEXT rule a naive writer breaks.
        enc = encode_text(want)
        body = enc[1024:]
        check(len(body) % 1024 == 0, f"{path.name}:{e.name}: ragged final page")
        for base in range(0, len(body), 1024):
            page = body[base:base + 1024].rstrip(b"\x00")
            check(not page or page[-1] == 0x0D,
                  f"{path.name}:{e.name}: page at {base} ends mid-line")
            # ...and no page may be full to the brim. The compiler moves to
            # the next page only on seeing a NUL where the next line would
            # start (CHECKEND in procs.a.text), so a page of exactly 1024
            # content bytes makes it scan off the end of its buffer and
            # report error 400 against the last line that fitted. That is not
            # theoretical: it is what killed the 1.3 skeleton under Apple's
            # own compiler. Apple's editor keeps the same invariant -- the
            # least-padded page in this whole corpus has one NUL.
            check(len(page) < 1024,
                  f"{path.name}:{e.name}: page at {base} is full to 1024 "
                  f"bytes with no NUL; the compiler cannot find its end")

# `encode_text` must not normalise a trailing newline away. Ten of the 21
# `.TEXT` files above genuinely end with a blank line and `decode_text`
# reports it, so swallowing one would stop the two being inverses -- which is
# exactly what happened on the first attempt. The host-side convention, where
# a final newline terminates the last line rather than starting an empty one,
# is the caller's business; `mkworkdisk.py` applies it.
for src in ("A\nB\n", "A\nB", "A\nB\n\n", "", "\n", "  indented\n"):
    check(decode_text(encode_text(src)) == src.replace("\r\n", "\n"),
          f"encode/decode of {src!r} gives "
          f"{decode_text(encode_text(src))!r}, which is not the identity")

# The page-full case, constructed rather than hoped for. None of Apple's own
# files happens to pack to exactly 1024, so the sweep above would stay green
# on a writer that allowed it; this builds the case on purpose. `n` lines of
# `w` characters plus a CR each, chosen to total exactly 1024 -- with
# compression off, so the encoded length is the obvious one.
for w in (7, 15, 31, 127):
    n = 1024 // (w + 1)
    src = "\n".join("X" * w for _ in range(n))
    enc = encode_text(src, compress=False)
    body = enc[1024:]
    check(len(body) == 2048,
          f"{n} lines of {w} chars packed into {len(body) // 1024} page(s); "
          f"they total exactly 1024 bytes and must not share one")
    check(body[1023] == 0,
          f"{n} lines of {w} chars leave page 0 with no terminating NUL")
    check(decode_text(enc) == src,
          f"{n} lines of {w} chars do not survive the page split")

# -- 5. a volume built from nothing -------------------------------------

w = PascalWriter.blank("WORK", order="dos")
vol = w.volume()
check(vol.name == "WORK", f"blank volume is named {vol.name!r}")
check(vol.num_files == 0, f"blank volume has {vol.num_files} files")
check(vol.total_blocks == 280, f"blank volume claims {vol.total_blocks} blocks")
check(w.free_blocks() == 280 - FIRST_DATA_BLOCK,
      f"blank volume has {w.free_blocks()} free, expected {280 - FIRST_DATA_BLOCK}")
check(w.gaps() == [(FIRST_DATA_BLOCK, 274)],
      f"blank volume's free list is {w.gaps()}")
# It has to survive a trip through the *reader*, not just its own accessors.
check(PascalDisk(w.to_bytes()).directory() == [],
      "the reader finds files on a blank volume")
check(PascalDisk(w.to_bytes()).order == "dos",
      "a blank DOS-order volume does not detect as DOS-order")

# -- 6. files go on and come back off -----------------------------------

SAMPLES = [
    ("SHORT.TEXT", "PROGRAM T;\nBEGIN\nEND.\n", "textfile"),
    ("BIG.DATA", bytes(range(256)) * 9, "datafile"),          # 2304 b, 5 blocks
    ("EXACT.DATA", b"Z" * BLOCK_SIZE, "datafile"),            # exactly 1 block
    ("TINY.DATA", b"!", "datafile"),
]
placed = []
for name, payload, kind in SAMPLES:
    data = encode_text(payload) if isinstance(payload, str) else payload
    en = w.add_file(name, data, kind)
    placed.append((name, data, kind, en))

d = PascalDisk(w.to_bytes())
check([e.name for e in d.directory()] == [n for n, *_ in SAMPLES],
      f"directory reads back as {[e.name for e in d.directory()]}")
for name, data, kind, en in placed:
    e = d.find(name)
    check(e.kind == kind, f"{name}: kind reads back as {e.kind!r}, wrote {kind!r}")
    check(e.size == len(data),
          f"{name}: size reads back as {e.size}, wrote {len(data)}")
    check(d.read_file(name) == data, f"{name}: contents changed on the way")
    check(e.first_block == en.first_block and e.next_block == en.next_block,
          f"{name}: placed at {en.first_block}..{en.next_block}, reads back "
          f"at {e.first_block}..{e.next_block}")
check(d.read_file("SHORT.TEXT")[:1024] == bytes(1024),
      "SHORT.TEXT lost its header page")
check(decode_text(d.read_file("SHORT.TEXT")) == "PROGRAM T;\nBEGIN\nEND.\n",
      "SHORT.TEXT does not decode back to its source")

# Files are contiguous and packed from block 6 with no gap.
ents = d.directory()
check(ents[0].first_block == FIRST_DATA_BLOCK,
      f"the first file starts at {ents[0].first_block}, not {FIRST_DATA_BLOCK}")
check(all(a.next_block == b.first_block for a, b in zip(ents, ents[1:])),
      "the files are not packed contiguously")

# -- 7. first fit reuses a hole -----------------------------------------

hole = d.find("BIG.DATA")
w.remove_file("BIG.DATA")
check(w.volume().num_files == 3, f"{w.volume().num_files} files after removing one")
check((hole.first_block, hole.blocks) in w.gaps(),
      f"removing BIG.DATA left free list {w.gaps()}, expected a "
      f"{hole.blocks}-block hole at {hole.first_block}")
en = w.add_file("FILLER.DATA", b"x" * (hole.blocks * BLOCK_SIZE), "datafile")
check(en.first_block == hole.first_block,
      f"FILLER.DATA went to block {en.first_block}, not into the hole at "
      f"{hole.first_block}")
ents = PascalDisk(w.to_bytes()).directory()
check([e.first_block for e in ents] == sorted(e.first_block for e in ents),
      "the directory came back out of block order")

# -- 8. it has to refuse ------------------------------------------------

refuses(lambda: w.add_file("SHORT.TEXT", b"x", "datafile"),
        "a name already on the volume")
refuses(lambda: w.add_file("HUGE.DATA", b"x" * (300 * BLOCK_SIZE), "datafile"),
        "a file larger than the volume", VolumeFull)
refuses(lambda: w.add_file("NOSUCH.DATA", b"x", "sausagefile"),
        "an unknown file kind")
refuses(lambda: w.add_file("A" * 16, b"x", "datafile"),
        "a 16-character file name")
refuses(lambda: PascalWriter.blank("TOOLONGNAME"), "an 8-character volume name")
refuses(lambda: w.write_block(0, b"short"), "a block that is not 512 bytes")
refuses(lambda: w.remove_file("NOTHERE.DATA"), "removing a file that is absent",
        KeyError)
refuses(lambda: encode_text("x" * 2000), "a line too long for a page")
refuses(lambda: encode_text("bell\ahere"), "a control character in a line")
# ...but not TAB, which is a legal `.TEXT` byte and the one control character
# a source line may carry. INSYMBOL's whitespace case label is a literal tab,
# because a case label must be a constant and Apple's compiler rejects
# `CHR(9)` there with error 103.
check(decode_text(encode_text("a\tb")) == "a\tb",
      "a TAB does not survive encode/decode")
refuses(lambda: encode_date.__call__(__import__("datetime").date(2100, 1, 1)),
        "a year outside the two-digit window")

# The ordering rule, which is the one a caller can break without noticing.
good = w.entries()
swapped = [good[1], good[0]] + good[2:]
refuses(lambda: w.encode_directory("WORK", swapped, 280, 0),
        "a directory whose entries are out of block order")
refuses(lambda: w.encode_directory("WORK", good * 30, 280, 0),
        f"more than {MAX_FILES} files", VolumeFull)

# -- 9. a real Apple disk survives being rewritten wholesale ------------

# The sharpest end-to-end form of check 2: take Apple's own volume, re-commit
# its directory through the writer, and require the whole 143,360-byte image
# back unchanged.
for path in DISKS:
    w2 = PascalWriter.from_file(path)
    before = w2.to_bytes()
    v = w2.volume()
    w2._commit(v.name, w2.entries(), w2._last_boot(), v.total_blocks,
               w2.directory_bytes())
    after = w2.to_bytes()
    diff = [i for i in range(len(before)) if before[i] != after[i]]
    check(not diff,
          f"{path.name}: re-committing Apple's own directory changed "
          f"{len(diff)} bytes, first at {diff[0] if diff else '-'}")

# -- 10. someone else's implementation, on a disk we wrote ---------------

# Everything above is this repo checking itself: the writer against the
# reader, both of them ours. `ucsd-psystem-fs` is a separate implementation of
# the same format by a different author, so it can answer the one question
# our own tools cannot -- whether a volume we produced is well formed by
# anybody's reckoning but our own. It is not evidence about Apple; it is the
# nearest thing available to a second opinion before the emulator gives the
# real one.
WORK = ROOT / "build" / "disks" / "WORK.dsk"
if not xcompile.fs_available():
    print("SKIPPED the independent cross-check: ucsdpsys_disk is not "
          "installed (thirdparty/ucsd-psystem-xc/build.sh builds its sibling)")
elif not WORK.exists():
    fails.append("build/disks/WORK.dsk has not been generated (mkworkdisk.py)")
    checks += 1
else:
    wp = xcompile.wslpath(WORK)
    r = xcompile.fs(f'ucsdpsys_fsck -f "{wp}"')
    check(r.returncode == 0,
          f"ucsdpsys_fsck rejects our volume: {(r.stdout + r.stderr).strip()[:300]}")
    r = xcompile.fs(f'ucsdpsys_disk -f "{wp}" --list')
    listed = r.stdout
    check(r.returncode == 0, f"ucsdpsys_disk cannot list our volume: "
                             f"{(r.stdout + r.stderr).strip()[:300]}")
    for e in PascalDisk.from_file(WORK).directory():
        check(e.name in listed,
              f"ucsdpsys_disk does not list {e.name}, which is on the volume")
    check("WORK:" in listed, f"the volume name is not WORK: {listed[:80]!r}")
    # And the contents have to come back out. Its `-g` decodes `.TEXT` and
    # renders DLE indentation as tabs, so compare with tabs expanded.
    src = {"SEARCH.TEXT": ROOT / "src/native/SEARCH.TEXT",
           "SKEL13.TEXT": ROOT / "analysis/reconstruction/skeleton-1.3.text"}
    got = xcompile.fs(
        f'd=$(mktemp -d) && cd "$d" && ucsdpsys_disk -f "{wp}" '
        + " ".join(f"-g {n}" for n in src)
        + ' && for f in *; do echo "@@@$f"; expand -t8 "$f"; done')
    check(got.returncode == 0,
          f"ucsdpsys_disk cannot extract from our volume: "
          f"{(got.stdout + got.stderr).strip()[:300]}")
    blobs = {}
    for chunk in got.stdout.split("@@@")[1:]:
        head, _, rest = chunk.partition("\n")
        blobs[head.strip()] = rest
    for name, path in src.items():
        want = expand_tabs(path.read_text(encoding="ascii", errors="replace"))
        want = want[:-1] if want.endswith("\n") else want
        mine = [ln.rstrip() for ln in want.split("\n")]
        theirs = [ln.rstrip() for ln in blobs.get(name, "").rstrip("\n").split("\n")]
        check(mine == theirs,
              f"{name}: ucsdpsys_disk extracts {len(theirs)} lines, the source "
              f"has {len(mine)}; first difference at line "
              f"{next((i for i, (a, b) in enumerate(zip(mine, theirs), 1) if a != b), 'end')}")

print(f"{checks} checks, {len(fails)} failures "
      f"({len(DISKS)} Apple volumes re-encoded, {ntext} .TEXT files "
      f"round-tripped, {ndates} dates re-encoded, one volume built from nothing)")
for f in fails[:20]:
    print("  FAIL", f)
sys.exit(1 if fails else 0)
