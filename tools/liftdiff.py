"""Diff a 1.1 body against its 1.3 counterpart as lifted source.

The p-code diff aligns badly where a CASE statement's arms are laid out
differently -- Apple's compiler emits them in source order and the fast
tier in label order -- so a procedure like INSYMBOL looks wholly changed
for no reason at all. The lift is in source order on both sides, so
comparing two lifts shows what the two releases actually say. Addresses
and procedure numbers are blanked, since both move for reasons of their
own.

What this compares is Apple's 1.3 binary against Apple's 1.1 binary. It
does not check the reconstruction; it says what the port has to account
for, which is the question the p-code diff could not answer.

Usage:
    python tools/liftdiff.py PASCALCO.6
"""
import difflib
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a2pascal.names import PROC_NAMES

ROOT = Path(__file__).resolve().parent.parent


def lift(ver: str, name: str) -> list[str]:
    out = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "liftproc.py"), ver, name],
        capture_output=True, text=True).stdout
    out = re.sub(r"L[0-9A-F]{4}", "L", out)
    return re.sub(r"\b([A-Z0-9]+)\.\d+:", r"\1:",
                  out).splitlines(keepends=True)


def main() -> int:
    if len(sys.argv) != 2 or "." not in sys.argv[1]:
        raise SystemExit("usage: liftdiff.py SEGMENT.NUMBER   (1.1's number)")
    seg, num = sys.argv[1].split(".")
    name = PROC_NAMES["1.1"].get((seg, int(num)))
    if name is None:
        raise SystemExit(f"no 1.1 procedure {seg}.{num}")
    # Paired by name, not by the correspondence table: a procedure that
    # changed enough to defeat the table's similarity match -- FINDFORW,
    # which went from PROCEDURE to FUNCTION -- is exactly the one worth
    # looking at.
    pair = [k[1] for k, v in PROC_NAMES["1.3"].items()
            if k[0] == seg and v == name]
    if not pair:
        raise SystemExit(f"{seg}.{num} {name} has no 1.3 counterpart")
    sys.stdout.writelines(difflib.unified_diff(
        lift("1.3", f"{seg}.{pair[0]}"), lift("1.1", f"{seg}.{num}"),
        "1.3", "1.1"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
