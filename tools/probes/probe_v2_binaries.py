"""BINDER.CODE and SET40COLS.CODE: Apple's bytes except the version field.

Both are 1.1 binaries Apple carried into 1.3 unchanged (finding 99c).
Their segments say version 2; any 1.3 compile says 6. So a whole-file
match is out of reach, and this probe pins down that it is the ONLY
thing out of reach (findings 112 and 274):

  1. **Every procedure is instruction- and frame-identical** (BINDER 6,
     SET40COLS 4).
  2. **Every differing byte is the version field**: each is a high byte
     of a SEGINFO word at $100-$11F, Apple's reads version 2 in its top
     three bits, ours 6, and the other five bits agree. Writing Apple's
     version into ours makes the WHOLE file identical, slack included.
  3. **The comparison can see a code byte**: one flipped byte in the
     segment is caught, at that byte, and costs a procedure its match.
  4. **The verified source is the source in the tree.**
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from a2pascal.codefile import CodeFile
from a2pascal.disk import PascalDisk
from oscmp import DISKS_13, compare

ROOT = Path(__file__).resolve().parents[2]
ACC = ROOT / "acceptance"
SRC = ROOT / "src" / "pascal" / "programs" / "1.3"
RUNS = [
    # (shipped name, run dir, codefile, source, procedures)
    ("BINDER.CODE", "2026-09-13-binder-exact", "BINDERT.CODE",
     "BINDER.text", 6),
    ("SET40COLS.CODE", "2026-09-13-set40cols-exact", "SET40T.CODE",
     "SET40COLS.text", 4),
]

fail = []


def check(ok: bool, label: str) -> None:
    print(("  ok   " if ok else "  FAIL ") + label)
    if not ok:
        fail.append(label)


def shipped(name: str) -> bytes:
    for fname in DISKS_13:
        d = PascalDisk.from_file(ROOT / "evidence" / "disks" / fname)
        try:
            e = d.find(name)
        except Exception:
            continue
        if e is not None:
            return bytes(d.read_blocks(e.first_block, e.blocks))
    raise SystemExit(f"{name} is on none of the 1.3 disks")


def main() -> int:
    for name, run, code, source, nproc in RUNS:
        print(f"=== {name} ===")
        paths = (ACC / run / code, ACC / run / source, SRC / source)
        missing = [p for p in paths if not p.exists()]
        if missing:
            check(False, f"missing {missing}")
            continue
        apple = shipped(name)
        ours = paths[0].read_bytes()
        acf, ocf = CodeFile(apple), CodeFile(ours)

        rows = compare(ocf, acf)
        real = {k: r for k, r in rows.items() if r["present_apple"]}
        exact = [k for k, r in real.items() if r["exact"]]
        check(len(real) == nproc and len(exact) == nproc,
              f"{len(exact)} of {len(real)} procedures instruction- and "
              "frame-identical")

        diff = [i for i in range(len(apple))
                if i >= len(ours) or apple[i] != ours[i]]
        version_only = (
            len(ours) == len(apple) and bool(diff)
            and all(0x101 <= i < 0x120 and i % 2 for i in diff)
            and all(apple[i] >> 5 == 2 and ours[i] >> 5 == 6
                    and apple[i] & 0x1F == ours[i] & 0x1F for i in diff))
        check(version_only,
              f"{len(diff)} of {len(apple)} bytes differ, every one a "
              "SEGINFO version field: 2 in Apple's, 6 in ours")
        restamped = bytearray(ours)
        for i in diff:
            restamped[i] = (restamped[i] & 0x1F) | (2 << 5)
        check(bytes(restamped) == apple,
              "with version 2 written into ours, the whole file is "
              "Apple's, slack and all")

        seg = next(s for s in ocf.segments if s.length)
        where = seg.block * 512 + seg.length // 2
        mutant = bytearray(ours)
        mutant[where] ^= 0x01
        mdiff = [i for i in range(len(apple)) if apple[i] != mutant[i]]
        lost = [k for k, r in compare(CodeFile(bytes(mutant)), acf).items()
                if r["present_apple"] and not r["exact"]]
        check(where in mdiff and len(mdiff) == len(diff) + 1 and len(lost) == 1,
              f"one flipped code byte is caught, and costs {lost}")

        check(paths[1].read_bytes().replace(b"\r\n", b"\n")
              == paths[2].read_bytes().replace(b"\r\n", b"\n"),
              f"acceptance {source} equals src/pascal/programs/1.3/{source}")

    print()
    if fail:
        print(f"v2 binaries: {len(fail)} check(s) failed")
        return 1
    print("BINDER and SET40COLS: every byte Apple's but the version field")
    print("v2-binaries-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
