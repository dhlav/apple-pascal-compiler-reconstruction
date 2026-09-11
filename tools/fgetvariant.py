"""Derive the FGET compilation of PASCALSYSTEM.text from the live source.

`128K.PASCAL` cannot be reached by one compile (finding 232b). `FGET` names
`FPWINADV`/`FPDLE`/`FPPEEK`, which needs `USES FIOPRIMS;`, and a `USES`
zeroes `PROCTABLE[2..5]` of the current segment -- after `EXECERROR`,
`FINIT`, `FRESET` and `FOPEN` have filled them. So the file ships with
`FGET` stubbed and its verified body parked in a comment, and a second
acceptance run trades those four procedures for it.

That second run used to be kept only as a source snapshot, which went
thousands of lines stale against the live file while still being the thing
`probe_os_exact.py` pinned. Deriving it instead means both runs come from
one source, and a fix to a procedure they share -- finding 252 corrected
`SCANTITLE` and `BLKXFER`, which both runs contain -- lands in both.

    python tools/fgetvariant.py [-o OUT]

The transformation is exactly what the comment in the source says it is:
give `FGET` the heading it wants, and swap its `BEGIN END` stub for the
body sitting above it. Every anchor is asserted, so a source edit that
moves one fails here rather than silently producing the wrong file.
"""
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "pascal" / "os" / "1.3" / "PASCALSYSTEM.text"

HEAD = "  PROCEDURE FGET;\n"
HEAD_FGET = "  PROCEDURE FGET;\n  USES FIOPRIMS;\n    LABEL 1, 2, 3;\n"
COMMENT_OPEN = "  { The body below is `FGET`'s, verified:"
BODY_OPEN = "\n      BEGIN\n      SYSCOM^.IORSLT := INOERROR;"
TAIL = "      END;\n  }\n  BEGIN\n  END;\n"


def build(text: str) -> str:
    assert text.count(HEAD) == 1, "FGET's heading moved"
    assert text.count(COMMENT_OPEN) == 1, "the parked-body comment moved"
    assert text.count(BODY_OPEN) == 1, "the parked body's first line moved"
    assert text.count(TAIL) == 1, "the parked body's end or the stub moved"

    c0 = text.index(COMMENT_OPEN)
    b0 = text.index(BODY_OPEN, c0) + 1          # keep the newline before it
    t0 = text.index(TAIL, b0)
    assert b0 < t0, "the body and its end are the wrong way round"

    body = text[b0:t0] + "      END;\n"
    out = text[:c0] + body + text[t0 + len(TAIL):]
    out = out.replace(HEAD, HEAD_FGET, 1)

    assert "USES FIOPRIMS;\n    LABEL 1, 2, 3;" in out
    assert COMMENT_OPEN not in out, "the comment survived the swap"
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-o", "--out", type=Path,
                    default=ROOT / "build" / "PASCALSY-FGET.text")
    a = ap.parse_args()
    out = build(SRC.read_text(encoding="utf-8"))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(out, encoding="utf-8", newline="\n")
    over = [n for n, l in enumerate(out.split("\n"), 1) if len(l) > 80]
    print(f"{a.out} -- {out.count(chr(10))} lines, "
          f"{len(over)} over 80 columns")
    return 1 if over else 0


if __name__ == "__main__":
    raise SystemExit(main())
