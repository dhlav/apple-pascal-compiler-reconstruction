"""Print the listing of one procedure: show.py [ver] SEGMENT.N [SEGMENT.N ...]"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
args = sys.argv[1:]
ver = "1.1"
if args and re.fullmatch(r"1\.[13]", args[0]):
    ver, args = args[0], args[1:]

text = (ROOT / "analysis" / "pcode_disassembly"
        / f"SYSTEM.COMPILER-{ver}.pcode.txt").read_text()
blocks = text.split("\n--- procedure ")
seg = None
index = {}
for b in blocks:
    # The SEGMENT header for the *next* segment sits at the end of the
    # previous procedure's block, so this block still belongs to the
    # segment named before it. Index first, then move on.
    n = re.match(r"(\d+)", b)
    if n and seg:
        index[f"{seg}.{n.group(1)}"] = "--- procedure " + b.split("\n====")[0]
    m = re.search(r"^SEGMENT \d+ (\w+)", b, re.M)
    if m:
        seg = m.group(1)

for key in args:
    print(index.get(key.upper(), f"<{key} not found>").rstrip())
    print()
