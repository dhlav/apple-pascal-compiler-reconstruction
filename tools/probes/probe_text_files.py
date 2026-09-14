"""The ten text files on the 1.3 disks, byte for byte from src/text/.

A .TEXT file is its lines plus how an editor stored them: a DLE indent code
or typed spaces on each line, where each page starts, and the editor's page
zero in front (finding 288). src/text/NAME.text holds the lines and
NAME.layout the rest, in the directives `a2pascal.textfile.Layout` reads.

Claims, each of which the bytes can fail:

  1. **Every text file on the three disks has a source here**, and nothing
     here is not on a disk.
  2. **Each encodes to Apple's file exactly**: every block the directory
     gives it, header page, text pages and the zero tail of each page.
  3. **The layout is content**: the same lines through the default encoder
     (DLE only past two spaces, a zero header) match none of the ten.
  4. **The header and the lines are separately right**: with the layout's
     header directives dropped, the text pages still match and the header
     page does not.

Not claimed: that Apple's editor would write these bytes from these lines
today. The encoder is this repo's; what it is checked against is Apple's.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from a2pascal.disk import PascalDisk
from a2pascal.textfile import Layout, encode_text

ROOT = Path(__file__).resolve().parents[2]
DISKS = sorted((ROOT / "evidence" / "disks").glob("*.dsk"))
TEXT = ROOT / "src" / "text"
HEADER_DIRECTIVES = ("defined", "environment", "byte") + Layout.ENVIRONMENT

fail = []


def check(ok: bool, label: str) -> None:
    print(("  ok   " if ok else "  FAIL ") + label)
    if not ok:
        fail.append(label)


def stem(name: str) -> str:
    return name[:-5] if name.endswith(".TEXT") else name


def lines_of(path: Path) -> str:
    text = path.read_text(encoding="ascii")
    return text[:-1] if text.endswith("\n") else text


def main() -> int:
    shipped = {}
    for disk in DISKS:
        d = PascalDisk.from_file(disk)
        for e in d.directory():
            if e.kind == "textfile":
                shipped[stem(e.name)] = (d.volume().name, e.name,
                                         d.read_blocks(e.first_block,
                                                       e.blocks))

    print("=== every text file has a source ===")
    here = sorted(p.stem for p in TEXT.glob("*.text"))
    check(here == sorted(shipped),
          f"{len(shipped)} text files on the disks, {len(here)} sources: "
          f"missing {sorted(set(shipped) - set(here))}, "
          f"extra {sorted(set(here) - set(shipped))}")

    print("=== each encodes to Apple's bytes ===")
    for s, (vol, name, blob) in sorted(shipped.items()):
        src = TEXT / f"{s}.text"
        if not src.exists():
            continue
        text = lines_of(src)
        raw = (TEXT / f"{s}.layout").read_text(encoding="ascii")
        got = encode_text(text, layout=Layout(raw))
        check(got == blob, f"{vol}:{name}: {len(got)} of {len(blob)} bytes")

        plain = encode_text(text)
        same = sum(1 for i in range(min(len(plain), len(blob)))
                   if plain[i] == blob[i])
        check(plain != blob,
              f"{name} without its layout: {same} of {len(blob)} agree")

        bare = "\n".join(line for line in raw.splitlines()
                         if line.split(" ", 1)[0] not in HEADER_DIRECTIVES)
        noheader = encode_text(text, layout=Layout(bare))
        check(noheader[1024:] == blob[1024:] and noheader[:1024] != blob[:1024],
              f"{name} without its header directives: text pages match, "
              f"page zero does not")

    print()
    if fail:
        print(f"text files: {len(fail)} check(s) failed")
        return 1
    print(f"text files: all {len(shipped)} byte for byte")
    print("text-files-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
