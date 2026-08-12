"""UCSD Pascal .TEXT file decoding.

A .TEXT file begins with a 1024-byte header page (the editor's environment
block) followed by 1024-byte text pages. Within a page:
  * lines end with CR (0x0D);
  * a DLE (0x10) is followed by one byte giving indentation + 32, i.e. the
    line is prefixed with (byte - 32) spaces;
  * NULs pad out the tail of a page.
"""

DLE = 0x10
CR = 0x0D
HEADER_BYTES = 1024
PAGE = 1024


def decode_text(data: bytes, has_header: bool = True) -> str:
    body = data[HEADER_BYTES:] if has_header else data
    out = []
    for base in range(0, len(body), PAGE):
        page = body[base:base + PAGE]
        i, line = 0, []
        while i < len(page):
            b = page[i]
            if b == 0:
                i += 1
                continue
            if b == DLE and i + 1 < len(page):
                line.append(" " * max(0, page[i + 1] - 32))
                i += 2
                continue
            if b == CR:
                out.append("".join(line))
                line = []
                i += 1
                continue
            line.append(chr(b & 0x7F))
            i += 1
        if line:
            out.append("".join(line))
    return "\n".join(out)
