"""Render pages of a scanned PDF to PNG for reading.

Usage: python tools/pdfpage.py <pdf> <first> <last> [dpi]
Writes into the scratch render directory and prints the paths.
"""
import sys
from pathlib import Path

import pymupdf

OUT = Path(r"C:\Users\dhlav\AppData\Local\Temp\claude"
           r"\C--PascalRecon\73ba3658-d966-43e8-9945-ca6fe8f188e3"
           r"\scratchpad\pdf")

pdf = Path(sys.argv[1])
first, last = int(sys.argv[2]), int(sys.argv[3])
dpi = int(sys.argv[4]) if len(sys.argv) > 4 else 160

OUT.mkdir(parents=True, exist_ok=True)
doc = pymupdf.open(pdf)
print(f"{pdf.name}: {doc.page_count} pages")
for n in range(first, min(last, doc.page_count) + 1):
    pix = doc[n - 1].get_pixmap(dpi=dpi)
    path = OUT / f"p{n:04d}.png"
    pix.save(path)
    print(path)
