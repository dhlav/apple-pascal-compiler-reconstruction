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
    ("disk set inventory", "diskmap.py"),
    # Not an artifact: mtype has to agree with where the native code
    # actually is, and a 1.3 disk has to be stamped version 6 except where
    # finding 99 says otherwise.
    ("SEGINFO version and mtype", "probes/probe_seginfo.py"),
    # Not an artifact: SEGKIND is the one field that tells a unit from a
    # segment procedure, and it is what says FIOPRIMS is an intrinsic unit
    # rather than the SEGMENT PROCEDURE findings 190/194 kept failing to
    # compile (finding 200).
    ("SEGKIND: FIOPRIMS is a unit", "probes/probe_segkind.py"),
    # Not an artifact: the three APPLE3 utilities 1.3 shipped without
    # rebuilding differ from their 1.1 copies only inside SEGINFO.
    ("utilities 1.3 did not rebuild", "probes/probe_stale_utils.py"),
    ("segment/procedure maps", "map_compiler.py"),
    ("SYSTEM.LIBRARY unit map and interfaces", "libmap.py"),
    ("p-code decoder self-check", "validate_pcode.py"),
    ("p-code listings", "disasm.py"),
    # Not an artifact: the native signatures lift.py has to be told have to
    # keep matching the .PROC/.FUNC declarations they claim to come from.
    ("native signatures vs src/native", "probes/probe_native_sig.py"),
    ("disk set p-code listings", "disasm_utils.py"),
    ("disk set lifted to pseudo-Pascal", "lift_utils.py"),
    ("native 6502 listings", "disasm6502.py"),
    ("SYSTEM.LIBRARY native 6502 listings", "disasm6502_lib.py"),
    # Not an artifact: it re-assembles src/native/SEARCH.TEXT and requires the
    # bytes to equal the disk's, relocation tables included (finding 44e).
    ("native source reassembly", "probes/probe_native_asm.py"),
    # Same test for the library's fourteen native procedures.
    ("library native source reassembly",
     "probes/probe_lib_native_asm.py"),
    # And for the native halves of the utilities on the 1.3 disks.
    ("program native source reassembly",
     "probes/probe_prog_native_asm.py"),
    # Not an artifact, and the only one of the four with no reimplementation
    # in it: what SYSTEM.ASSMBLER itself wrote under the emulator, against
    # what Apple shipped.
    ("acceptance runs vs the shipped binaries",
     "probes/probe_acceptance.py"),
    # Same idea for the operating system, which is mid-reconstruction and so
    # has no whole-file compare to make yet: the procedures Apple's own
    # compiler already reproduces exactly are named, and a named one going
    # missing is a regression however the total moves (finding 201).
    ("OS procedures already exact", "probes/probe_os_exact.py"),
    ("call graph", "callgraph.py"),
    ("global data map", "globalmap.py"),
    ("1.1 -> 1.3 correspondence", "globaldiff.py"),
    ("procedure profiles", "procprofile.py"),
    ("II.0 VAR block alignment", "vardecl.py"),
    # Not an artifact: lays out UCSD's compiler records and requires them to
    # come to the sizes the binary forces (finding 54).
    ("record layout vs the binary", "probes/probe_record_layout.py"),
    ("reconstructed VAR block", "varblock.py"),
    ("reconstructed declaration skeleton", "srcskel.py"),
    # The disk the acceptance tier mounts: the reconstructed sources on a
    # Pascal volume Apple's own FILER can list.
    ("acceptance work disk", "mkworkdisk.py"),
    # Not an artifact: the volume writer against the volumes Apple wrote --
    # every evidence directory re-encoded byte for byte from its own parsed
    # entries, every block written back where it was read from, and the disk
    # just built handed to an independent implementation to check. Runs after
    # mkworkdisk.py because that last part needs the disk.
    ("volume writer vs Apple's volumes", "probes/probe_diskwrite.py"),
    # Not an artifact: the II.0 segment-0 declarations against Apple's own
    # attribute tables, which only became possible once SYSTEM.PASCAL parsed
    # (findings 50, 51).
    ("OS signatures vs the binary", "probes/probe_os_signatures.py"),
    ("lift to pseudo-Pascal", "liftall.py"),
    ("lift the operating system", "liftos.py"),
    ("lift SYSTEM.LIBRARY", "liblift.py"),
    # Not an artifact: lifts the two GOTOXY programs whose Pascal source is
    # on the same disk and diffs the result against it (finding 49).
    ("lifter calibration", "probes/probe_calibrate.py"),
    # Not an artifact: compiles the two GOTOXY programs on the host and
    # diffs the result against Apple's own compiled output (finding 55).
    # Skips, loudly, if the toolchain is not built.
    ("host compile vs Apple's output", "probes/probe_xcompile.py"),
    # Not an artifact: the same idea at scale -- 41 operating system
    # procedures against the UCSD II.0 source, checking loops and calls
    # rather than exact text, because Apple's is a fork (finding 52).
    ("lifter calibration, the OS", "probes/probe_os_calibrate.py"),
    # Not an artifact: PRINTERROR's nested case against UCSD's source for it,
    # where the arm strings are the answer key (finding 53).
    ("lifter calibration, case", "probes/probe_case_calibrate.py"),
    # Not an artifact: the operating system routine the compiler calls by
    # number, re-derived from all four binaries (finding 89).
    ("OSPROC43 vs the binaries", "probes/probe_osproc43.py"),
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
