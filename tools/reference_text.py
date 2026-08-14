"""Flatten the OCR'd manuals in `evidence/reference/manuals` to plain text.

The manuals arrived as scanned PDFs plus an OCR pass exported as HTML. The
HTML is the only text layer we have, and it is wrapped in per-page markup
that makes `grep` useless. This strips the markup and writes one `.txt` per
manual into `analysis/reference/`, which is what every citation in
`docs/FINDINGS.md` was actually read from.

Nothing here interprets the text. The output is the input with the tags
removed, so a quotation checked against the `.txt` is a quotation checked
against the OCR -- and the OCR is *not* clean. It splits table columns
onto separate lines, reads `{$S-}` as `{$5 --}`, and drops the decimal
column from part of the p-code table. Anything load-bearing gets checked
against the rendered page in the PDF; `tools/pdfpage.py` does that.
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "evidence" / "reference" / "manuals"
DST = ROOT / "analysis" / "reference"

# source basename -> output name. The source names are the ones the scans
# arrived with, and they are kept exactly: each `.html` refers to a sibling
# `<basename>_files/` directory of page images, and renaming either half
# breaks the link.
MANUALS = {
    "Image071217212805.pdf.duplex_text.html": "apple-ii-pascal-1.3-manual.txt",
    "Apple Pascal Language Reference Manual.html": "apple-pascal-language-reference.txt",
    "Apple_Pascal_Update_v1.1_text.html": "apple-pascal-update-1.1.txt",
}


def flatten(markup: str) -> str:
    markup = re.sub(r"(?s)<(script|style).*?</\1>", " ", markup)
    markup = re.sub(r"(?i)</(p|div|br|tr|h[1-6])>", "\n", markup)
    markup = re.sub(r"(?s)<[^>]+>", " ", markup)
    text = html.unescape(markup)
    text = re.sub(r"[ \t\xa0]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n", text)


def main() -> int:
    DST.mkdir(parents=True, exist_ok=True)
    missing = []
    for src, out in MANUALS.items():
        path = SRC / src
        if not path.exists():
            missing.append(src)
            continue
        text = flatten(path.read_text(encoding="utf-8", errors="replace"))
        (DST / out).write_text(text, encoding="utf-8", newline="\n")
        print(f"{out}: {len(text.splitlines())} lines")
    if missing:
        print("missing from evidence/reference/manuals: " + ", ".join(missing))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
