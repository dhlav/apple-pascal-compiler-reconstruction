"""Extract every file from the unpacked UCSD II.0 source disk."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from a2pascal.disk import PascalDisk, format_date
from a2pascal.textfile import decode_text

ROOT = Path(__file__).resolve().parent.parent
img = ROOT / "build" / "ii0src.po"
disk = PascalDisk.from_file(img, order="prodos")
vol = disk.volume()
outdir = ROOT / "reference_source" / "ucsd_ii0"
outdir.mkdir(parents=True, exist_ok=True)

print(f"volume {vol.name}: {vol.total_blocks} blocks, {vol.num_files} files")
for e in disk.directory():
    raw = disk.read_blocks(e.first_block, e.blocks)[:e.size]
    print(f"  {e.name:<16} {e.kind:<12} blocks {e.first_block:>3}..{e.next_block - 1:<3} "
          f"{e.size:>7} bytes  {format_date(e.mtime_raw)}")
    (outdir / (e.name + ".bin")).write_bytes(raw)
    if e.kind == "textfile":
        text = decode_text(raw)
        (outdir / e.name).write_text(text, encoding="ascii", errors="replace")
        print(f"      -> {e.name} ({len(text.splitlines())} lines)")
