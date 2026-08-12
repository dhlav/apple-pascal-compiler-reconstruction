"""Show the segment-0 signatures derived from GLOBALS.TEXT."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.syscall import segment0_signatures

ROOT = Path(__file__).resolve().parents[2]
sig = segment0_signatures(ROOT / "reference_source" / "ucsd_ii0" / "GLOBALS.TEXT")
for n in sorted(sig):
    name, words, is_fn = sig[n]
    print(f"{n:3}  {name:<15} params={words} word(s)"
          + ("   FUNCTION" if is_fn else ""))
