"""Regenerate every derived artifact from the evidence disks, in order.

Everything under build/, analysis/ and reference_source/ is reproducible by
running this script; nothing in those trees should be hand-edited.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEPS = [
    ("volume directories", "dump_dir.py"),
    ("unpack ii0src.sdk", "unpack_ii0src.py"),
    ("extract UCSD II.0 source", "extract_ii0src.py"),
    ("segment/procedure maps", "map_compiler.py"),
    ("p-code decoder self-check", "validate_pcode.py"),
    ("p-code listings", "disasm.py"),
    ("native 6502 listings", "disasm6502.py"),
    ("call graph", "callgraph.py"),
    ("global data map", "globalmap.py"),
    ("1.1 -> 1.3 correspondence", "globaldiff.py"),
    ("procedure profiles", "procprofile.py"),
    ("lift to pseudo-Pascal", "liftall.py"),
]

for label, script in STEPS:
    print(f"\n=== {label} ({script})")
    r = subprocess.run([sys.executable, "-u", str(HERE / script)],
                       capture_output=True, text=True)
    sys.stdout.write(r.stdout[-2000:])
    if r.returncode:
        sys.stderr.write(r.stderr)
        sys.exit(f"FAILED: {script}")
print("\nall steps completed")
