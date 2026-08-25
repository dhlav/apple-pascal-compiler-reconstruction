"""Every file on every evidence disk, and what is inside the codefiles.

The reconstruction targets one release and one machine at a time -- 1.3, and
the 128K system -- but the other disks stay in evidence and stay useful:
1.1 ships source for utilities 1.3 ships only as codefiles, and comparing
the two releases is what says which files Apple actually rebuilt. So this
writes the whole set out, both releases, rather than just the target.

Per codefile it lists each segment with its dictionary slot, segment number,
SEGINFO version and mtype, size, and how many of its procedures are p-code
and how many are native 6502.

Writes analysis/diskset-inventory.txt.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile

ROOT = Path(__file__).resolve().parent.parent
DISKS = ROOT / "evidence" / "disks"
OUT = ROOT / "analysis" / "diskset-inventory.txt"


def main() -> int:
    lines = [
        "Every file on every evidence disk.",
        "",
        "v = SEGINFO version: 1.1's system writes 2, 1.3's writes 6, and a 0",
        "is a codefile older than the field. The system enforces it -- 1.3",
        "refuses a version-2 SYSTEM.COMPILER outright (finding 99).",
        "mtype is 6502 exactly when the segment holds native procedures.",
        "",
    ]
    for path in sorted(DISKS.glob("*.dsk")):
        d = PascalDisk.from_file(path)
        lines.append(f"=== {path.name}   volume {d.volume().name}")
        for e in d.directory():
            lines.append(f"  {e.name:16s} {e.blocks:4d} blk {e.size:7d} B  "
                         f"{e.kind}")
            if e.kind != "codefile":
                continue
            try:
                cf = CodeFile(d.read_blocks(e.first_block, e.blocks))
            except Exception as ex:                     # noqa: BLE001
                lines.append(f"      unreadable: {ex}")
                continue
            for s in cf.segments:
                p = len(s.pcode_procedures)
                n = len(s.native_procedures)
                lines.append(
                    f"      slot{s.index:2d} seg{s.seg_num:<3d} {s.name:9s} "
                    f"v{s.version} {s.mtype:10s} {s.length:6d} B  "
                    f"{p:3d} p-code  {n:2d} native")
        lines.append("")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="ascii")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(lines)} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
