"""The four MISCINFO profiles, written by Apple's own SETUP.

acceptance/2026-09-13-miscinfo holds four runs of the shipped SETUP.CODE
under the 1.3 system, each driven by `emuremote.py setup` from a recipe in
src/data/miscinfo/ that sets all 53 of SETUP's fields, and the
NEW.MISCINFO each one wrote, as the whole block (finding 277).

Claims, each of which the binary can fail:

  1. **Every setting is Apple's**: bytes 58-95 (words 29-47) of each run
     equal the shipped profile's, and so does the zero tail 192-511.
  2. **The recipe is what set them**: every run booted with
     SYSTEM.MISCINFO's settings, and II80's and HAZEL's differ from those,
     so a recipe SETUP ignored would fail claim 1. The recipe also
     rebuilds the 38 bytes on the host from SETUP's own field table.
  3. **Everything else is memory SETUP never wrote**: SETUP.text copies
     only words 29..47 out of SYSCOM into its 96-word BUFFER, so bytes
     0-57 and 96-191 are whatever BUFFER sat on. Ours are the same in all
     four runs (Command-level text); Apple's differ file to file.
  4. **Apple's SYSTEM.MISCINFO sat on the Filer**: its 154 such bytes are
     SYSTEM.FILER's segment code, file offsets 8206-8397, byte for byte.
  5. **Word 46 is no field**: it is 8 in all four profiles and no ENTER
     names it, so it passes through from the booted SYSTEM.MISCINFO.
  6. **The kept recipes are the recipes in the tree.**
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from a2pascal.disk import PascalDisk
from oscmp import DISKS_13

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "acceptance" / "2026-09-13-miscinfo"
RECIPES = ROOT / "src" / "data" / "miscinfo"
SETUP = ROOT / "src" / "pascal" / "programs" / "1.3" / "SETUP.text"
PROFILES = ["SYSTEM", "II40", "II80", "HAZEL"]
BOOTED = "SYSTEM"
SETTINGS = range(58, 96)
LEFTOVER = [*range(0, 58), *range(96, 192)]
FILER_AT = 8206

fail = []


def check(ok: bool, label: str) -> None:
    print(("  ok   " if ok else "  FAIL ") + label)
    if not ok:
        fail.append(label)


def shipped() -> dict[str, bytes]:
    out = {}
    for fname in DISKS_13:
        d = PascalDisk.from_file(ROOT / "evidence" / "disks" / fname)
        for e in d.directory():
            if e.name.endswith(".MISCINFO") or e.name == "SYSTEM.FILER":
                out[e.name] = bytes(d.read_blocks(e.first_block, e.blocks))
    return out


def fields(src: str) -> list[tuple[str, int, int, int]]:
    """SETUP's own ENTER table: name, word, bit, width."""
    out, width = [], 1
    for line in src.splitlines():
        m = re.search(r"PWIDTH := (\d+)", line)
        if m:
            width = int(m.group(1))
        m = re.search(r"ENTER\('(.*)',\s*(\d+),\s*(\d+)\);", line)
        if m and "PROCEDURE" not in line:
            out.append((m.group(1).replace("''", "'"), int(m.group(2)),
                        int(m.group(3)), width))
    return out


def recipe(path: Path) -> dict[str, str]:
    out = {}
    for line in path.read_text(encoding="ascii").splitlines():
        line = line.split("#")[0].strip()
        if line:
            name, _, value = line.rpartition("=")
            out[name.strip()] = value.strip()
    return out


def from_recipe(table, values: dict[str, str], word46: int) -> bytes:
    words = [0] * 48
    words[46] = word46
    for name, w, bit, width in table:
        v = values[name]
        n = {"T": 1, "F": 0}.get(v.upper(), None)
        n = int(v) if n is None else n
        assert 0 <= n < 1 << width, (name, v)
        words[w] |= n << bit
    return b"".join(x.to_bytes(2, "little") for x in words[29:48])


def main() -> int:
    missing = [n for p in PROFILES for n in
               (f"{p}-NEW.MISCINFO", f"{p}.recipe", f"{p}-setup-console.txt")
               if not (RUN / n).exists()]
    if missing:
        print(f"missing from {RUN.name}: {missing}")
        return 1
    apple = shipped()
    ours = {p: (RUN / f"{p}-NEW.MISCINFO").read_bytes() for p in PROFILES}
    src = SETUP.read_text(encoding="ascii")
    table = fields(src)

    print("=== every setting is Apple's ===")
    for p in PROFILES:
        a, o = apple[f"{p}.MISCINFO"], ours[p]
        diff = [i for i in range(512) if a[i] != o[i]]
        check(len(a) == len(o) == 512 and a[58:96] == o[58:96]
              and a[192:] == o[192:] == bytes(320),
              f"{p}: bytes 58-95 and the zero tail identical")
        check(all(i in LEFTOVER for i in diff),
              f"{p}: the {len(diff)} bytes that differ are all in 0-57 "
              "and 96-191")

    print("=== the recipe is what set them ===")
    boot = apple[f"{BOOTED}.MISCINFO"]
    for p in PROFILES:
        if p == BOOTED:
            continue
        moved = [i for i in SETTINGS if apple[f"{p}.MISCINFO"][i] != boot[i]]
        print(f"       {p}: {len(moved)} settings bytes differ from the "
              "booted SYSTEM.MISCINFO")
    check(any(apple[f"{p}.MISCINFO"][58:96] != boot[58:96]
              for p in ("II80", "HAZEL")),
          "at least one run had to change settings the boot supplied")
    check(len(table) == 53 and len({t[0] for t in table}) == 53,
          "SETUP's ENTER table has 53 distinct fields")
    for p in PROFILES:
        values = recipe(RECIPES / f"{p}.recipe")
        a = apple[f"{p}.MISCINFO"]
        check(set(values) == {t[0] for t in table}
              and from_recipe(table, values, 8) == a[58:96],
              f"{p}.recipe names every field and rebuilds bytes 58-95 on "
              "the host")
    mutated = recipe(RECIPES / "HAZEL.recipe")
    mutated["SCREEN WIDTH"] = "40"
    check(from_recipe(table, mutated, 8) != apple["HAZEL.MISCINFO"][58:96],
          "a changed recipe value is caught")

    print("=== everything else is memory SETUP never wrote ===")
    check("STARTINDEX = 29;" in src and "ENDINDEX   = 47;" in src
          and "WRDINDMAX  = 95;" in src
          and "BUFFER[INDEX] := PSYSCOM^[INDEX];" in src
          and "OUTFILE^ := BUFFER;" in src,
          "SETUP copies words 29..47 into BUFFER and writes all 96 words")
    left = {p: bytes(ours[p][i] for i in LEFTOVER) for p in PROFILES}
    check(len(set(left.values())) == 1,
          "our four runs left the same 154 bytes")
    theirs = {p: bytes(apple[f"{p}.MISCINFO"][i] for i in LEFTOVER)
              for p in PROFILES}
    check(len(set(theirs.values())) == 4 and theirs["II80"] == bytes(154),
          "Apple's four differ from each other; II80's are all zero")

    print("=== Apple's SYSTEM.MISCINFO sat on the Filer ===")
    filer = apple["SYSTEM.FILER"]
    sysm = apple["SYSTEM.MISCINFO"]
    check(all(sysm[i] == filer[FILER_AT + i] for i in LEFTOVER),
          f"bytes 0-57 and 96-191 are SYSTEM.FILER's {FILER_AT}-"
          f"{FILER_AT + 191}")
    check(not all(sysm[i] == filer[FILER_AT + 2 + i] for i in LEFTOVER),
          "two bytes off, they are not")

    print("=== word 46 is no field ===")
    check(all(t[1] != 46 for t in table)
          and all(apple[f"{p}.MISCINFO"][92:94] == b"\x08\x00"
                  and ours[p][92:94] == b"\x08\x00" for p in PROFILES),
          "no ENTER names word 46, and it is 8 in all eight files")

    print("=== the kept recipes are the recipes in the tree ===")
    for p in PROFILES:
        check((RUN / f"{p}.recipe").read_bytes().replace(b"\r\n", b"\n")
              == (RECIPES / f"{p}.recipe").read_bytes().replace(b"\r\n", b"\n"),
              f"{p}.recipe equals src/data/miscinfo/{p}.recipe")

    print()
    if fail:
        print(f"miscinfo: {len(fail)} check(s) failed")
        return 1
    print("MISCINFO: all four profiles' settings and tails by Apple's SETUP; "
          "the rest is memory")
    print("miscinfo-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
