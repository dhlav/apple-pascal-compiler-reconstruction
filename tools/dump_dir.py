"""List the Pascal volume directory of each evidence disk image."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from a2pascal.disk import PascalDisk, format_date

ROOT = Path(__file__).resolve().parent.parent

for img in sorted((ROOT / "evidence" / "disks").glob("*.dsk")):
    disk = PascalDisk.from_file(img)
    vol = disk.volume()
    print(f"== {img.name}")
    print(f"   order={disk.order}  volume={vol.name}:  blocks={vol.total_blocks}  files={vol.num_files}")
    print(f"   {'#':>2} {'name':<16} {'blk':>4} {'..':>4} {'nblk':>4} {'bytes':>7}  {'kind':<12} mod")
    for e in disk.directory():
        print(f"   {e.index:>2} {e.name:<16} {e.first_block:>4} {e.next_block:>4} "
              f"{e.blocks:>4} {e.size:>7}  {e.kind:<12} {format_date(e.mtime_raw)}")
    print()
