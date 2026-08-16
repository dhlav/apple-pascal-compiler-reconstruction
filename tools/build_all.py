"""Regenerate every derived artifact from the evidence disks, in order.

Everything under build/, analysis/ and reference_source/ is reproducible by
running this script; nothing in those trees should be hand-edited.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEPS = [
    ("reference manual text", "reference_text.py"),
    ("volume directories", "dump_dir.py"),
    ("unpack ii0src.sdk", "unpack_ii0src.py"),
    ("extract UCSD II.0 source", "extract_ii0src.py"),
    # Not an artifact: the operating system stores segment 0 in two pieces,
    # and this requires the reader's join to reproduce both exactly and to
    # refuse a damaged one (finding 50).
    ("split segment 0", "probes/probe_split_segment.py"),
    ("segment/procedure maps", "map_compiler.py"),
    ("p-code decoder self-check", "validate_pcode.py"),
    ("p-code listings", "disasm.py"),
    ("native 6502 listings", "disasm6502.py"),
    # Not an artifact: it re-assembles src/native/SEARCH.TEXT and requires the
    # bytes to equal the disk's, relocation tables included (finding 44e).
    ("native source reassembly", "probes/probe_native_asm.py"),
    ("call graph", "callgraph.py"),
    ("global data map", "globalmap.py"),
    ("1.1 -> 1.3 correspondence", "globaldiff.py"),
    ("procedure profiles", "procprofile.py"),
    ("II.0 VAR block alignment", "vardecl.py"),
    # Not an artifact: lays out UCSD's compiler records and requires them to
    # come to the sizes the binary forces (finding 54).
    ("record layout vs the binary", "probes/probe_record_layout.py"),
    ("reconstructed VAR block", "varblock.py"),
    # Not an artifact: the II.0 segment-0 declarations against Apple's own
    # attribute tables, which only became possible once SYSTEM.PASCAL parsed
    # (findings 50, 51).
    ("OS signatures vs the binary", "probes/probe_os_signatures.py"),
    ("lift to pseudo-Pascal", "liftall.py"),
    ("lift the operating system", "liftos.py"),
    # Not an artifact: lifts the two GOTOXY programs whose Pascal source is
    # on the same disk and diffs the result against it (finding 49).
    ("lifter calibration", "probes/probe_calibrate.py"),
    # Not an artifact: the same idea at scale -- 41 operating system
    # procedures against the UCSD II.0 source, checking loops and calls
    # rather than exact text, because Apple's is a fork (finding 52).
    ("lifter calibration, the OS", "probes/probe_os_calibrate.py"),
    # Not an artifact: PRINTERROR's nested case against UCSD's source for it,
    # where the arm strings are the answer key (finding 53).
    ("lifter calibration, case", "probes/probe_case_calibrate.py"),
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
