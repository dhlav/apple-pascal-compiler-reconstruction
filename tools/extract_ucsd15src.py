"""Extract the UCSD I.5 source listings into reference_source/ucsd_15.

`evidence/reference/ucsd-15-sources.zip` is UC San Diego's own release of
the I.5 sources (non-commercial use), mirrored at
github.com/glgorman/UCSD-Pascal-p-system; the copy here is byte-identical
to that download, sha256 41896812f4e1... It is a REFERENCE, not evidence
of what Apple shipped: see finding 263 for what it is good for and what it
is not.

The one that matters for `SYSTEM.ASSMBLER` is `UCSD I.5 Assembler.txt`,
the Adaptable Assembler this file descends from -- its own header says
"Patterned after The Waterloo Last Assembler (TLA)", which is where
Apple's segment 1 gets its name. The zip also carries a PDF of the same
listing; the .txt has no page headers or line numbers, so that is the one
this writes out.

Names only (CLAUDE.md's source rules). The release is I.5.b.1 for the
PDP-11/LSI-11, three years and a different processor away from Apple's
1.3 for the 6502, and the procedure COUNTS differ: its ASSEMBLE has
ZOP1..ZOP20 where Apple's whole segment holds 33 procedures. Every byte
still comes from the binary.
"""
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT / "evidence" / "reference" / "ucsd-15-sources.zip"
OUTDIR = ROOT / "reference_source" / "ucsd_15"

# Everything in the zip that is Pascal source text. The .MAC files are the
# PDP-11 interpreter and the .pdf copies duplicate the .txt ones, so
# neither is written out.
WANTED = (".txt",)
SKIP = {"README.txt"}


def main() -> int:
    if not ARCHIVE.exists():
        print(f"{ARCHIVE} is missing")
        return 1
    OUTDIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ARCHIVE) as z:
        names = [n for n in z.namelist()
                 if n.lower().endswith(WANTED) and n not in SKIP]
        for name in sorted(names):
            # The listings are plain ASCII with the odd high byte from the
            # original print run; latin-1 round-trips those without loss.
            text = z.read(name).decode("latin-1")
            out = OUTDIR / name.replace(" ", "_")
            out.write_text(text, encoding="utf-8")
            print(f"  {name:<44} {len(text.splitlines()):>5} lines")
    asm = OUTDIR / "UCSD_I.5_Assembler.txt"
    if not asm.exists():
        print("the assembler listing is missing from the archive")
        return 1
    head = asm.read_text(encoding="utf-8")[:2000]
    if "The Waterloo Last Assembler (TLA)" not in head:
        print("the assembler listing is not the one finding 263 describes")
        return 1
    print(f"extract-ucsd15src-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
