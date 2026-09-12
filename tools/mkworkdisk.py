"""Build the work disk the acceptance tier mounts.

The acceptance test is Apple's own `SYSTEM.COMPILER` and `SYSTEM.ASSMBLER`,
running under AppleWin, compiling and assembling the reconstruction. Nothing
can be handed to them until the source is on a volume they will mount, which
is what this produces: a blank Pascal volume named WORK carrying

  * `SEARCH.TEXT`  -- the reconstructed 6502 source for 1.3's `IDSEARCH` and
    `TREESEARCH`, which `probe_native_asm.py` already assembles to Apple's
    exact bytes with this repo's own assembler. Apple's assembler is the one
    that emits the four relocation tables, so it is the only thing that can
    settle finding 44e.
  * `SKEL13.TEXT` and `SKEL11.TEXT` -- the declaration skeletons. The fast
    tier compiles both to Apple's exact global frame; the question here is
    whether Apple's compiler agrees, which is the only opinion that counts.

The volume is not bootable. It goes in a drive alongside APPLE1 and APPLE2,
and it is left mostly empty on purpose -- the compiler and the assembler both
write their output next to their input, and `SYSTEM.WRK.TEXT` will land here
too if the editor is used.

Writes build/disks/WORK.dsk.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a2pascal.disk import PascalDisk, format_date
from a2pascal.diskwrite import PascalWriter
from a2pascal.srcfmt import WIDTH, expand_tabs, over_width
from a2pascal.textfile import decode_text, encode_text

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "disks"
VOLUME = "WORK"
VOLUME2 = "WORK2"

# (name on the volume, source file). Names are upper case and at most 15
# characters, and inside Apple Pascal's eight significant characters as well.
# The 1.1 skeleton (`SKEL11`) went to archive/ with the rest of 1.1.
FILES = [
    ("SEARCH.TEXT", ROOT / "src" / "native" / "SEARCH.TEXT"),
    ("SKEL13.TEXT", ROOT / "analysis" / "reconstruction" / "skeleton-1.3.text"),
    # The APPLE3 utilities, smallest first. LINEFEED is Apple's own source,
    # off the 1.1 APPLE3 disk, carried over unaltered as the hypothesis for
    # 1.3 -- the two releases ship byte-identical codefiles for it.
    ("LINEFEED.TEXT", ROOT / "src" / "pascal" / "programs" / "1.3" /
     "LINEFEED.text"),
    # FORMATTR, not FORMATTER: eight significant characters (finding 97c),
    # and the compiler writes its output beside the source, so a name that
    # collided would overwrite the evidence copy's name on the volume.
    ("FORMATTR.TEXT", ROOT / "src" / "pascal" / "programs" / "1.3" /
     "FORMATTER.text"),
    # Its native half, which the Assembler takes and the Linker joins to the
    # compiled Pascal. It cannot go on as FORMATTR too, so it is FMTNATIV --
    # the repo file is `src/native/FORMATTR.TEXT`, named for the segment it
    # belongs to, and only the volume name differs.
    ("FMTNATIV.TEXT", ROOT / "src" / "native" / "FORMATTR.TEXT"),
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    # DOS sector order, because that is what a `.dsk` means to AppleWin and
    # what all six evidence disks are.
    w = PascalWriter.blank(VOLUME, order="dos")

    for name, path in FILES:
        if not path.exists():
            raise SystemExit(f"{path} has not been generated")
        text = expand_tabs(path.read_text(encoding="ascii", errors="replace"))
        # A host file's final newline terminates its last line; UCSD writes a
        # CR after every line including the last, so passing the newline
        # through would put a blank line on the end of every file. That is
        # this side's convention and not `encode_text`'s -- Apple's own
        # `.TEXT` files often do end with a blank line.
        text = text[:-1] if text.endswith("\n") else text
        # 80 columns is a hard limit for the assembler (error 54) and the
        # width every surviving Apple source was written to. Refuse rather
        # than ship a disk whose files the machine cannot open properly.
        long = over_width(text.split("\n"))
        if long:
            raise SystemExit(
                f"{name}: {len(long)} lines exceed {WIDTH} columns "
                f"{long[:5]} -- fix the generator, not the disk")
        w.add_file(name, encode_text(text), "textfile")

    dsk = OUT / f"{VOLUME}.dsk"
    w.save(dsk)

    # A second, empty volume. A Disk II is 280 blocks and that is the whole
    # budget for the source and the codefile Apple's compiler writes beside
    # it; once the source passed 260 blocks there was no longer room for
    # both. WORK2 goes in S5D2 in place of APPLE3, which a compile does not
    # need, and `--emu` answers the compiler's second prompt with
    # `WORK2:...CODE`. See finding 82.
    PascalWriter.blank(VOLUME2, order="dos").save(OUT / f"{VOLUME2}.dsk")
    print(f"wrote {(OUT / (VOLUME2 + '.dsk')).relative_to(ROOT)}: "
          f"{VOLUME2}:, empty, for the codefile")

    # Read it back with the reader, not the writer's own accessors, and
    # require the text out to equal the text in.
    d = PascalDisk.from_file(dsk)
    for name, path in FILES:
        want = expand_tabs(path.read_text(encoding="ascii", errors="replace"))
        want = want[:-1] if want.endswith("\n") else want
        got = decode_text(d.read_file(name))
        if got != want:
            raise SystemExit(f"{name} does not read back as it was written")

    vol = d.volume()
    print(f"wrote {dsk.relative_to(ROOT)}: {vol.name}: at {vol.total_blocks} "
          f"blocks, {vol.num_files} files, {w.free_blocks()} blocks free")
    for e in d.directory():
        print(f"  {e.name:<16} {e.blocks:>4} blocks  {e.size:>6} bytes  "
              f"{e.kind:<10} {format_date(e.mtime_raw)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
