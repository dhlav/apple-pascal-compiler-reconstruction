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


def encode_text(text: str, header: bytes | None = None,
                compress: bool = True) -> bytes:
    """Build a .TEXT file: a header page, then packed 1024-byte text pages.

    The one rule that is not optional is that **a line may not straddle a
    page boundary** -- the editor seeks by page and the compiler reads a page
    at a time, so a line split across two of them is lost, not merely
    reflowed. Each page is filled with whole lines and padded with NULs.

    The padding is not slack: **at least one NUL is required**, so a page
    holds at most PAGE-1 bytes of line data. The compiler finds the end of a
    page only by looking for a NUL where the next line should start --

        IF SYMBUFP^[SYMCURSOR]=CHR(0) THEN GETNEXTPAGE
        ELSE LINESTART := SYMCURSOR;                  { procs.a.text CHECKEND }

    -- so a page filled to exactly PAGE bytes never triggers the fetch. The
    scanner reads past the end of the buffer, the byte there is not a symbol,
    and the compiler reports `error 400` against the last line that fitted.
    That is a real failure we hit: the 1.3 skeleton's page 11 came out exactly
    full and Apple's compiler died on it. Apple's own editor keeps the same
    invariant -- of the 159 text pages in the 21 `.TEXT` files on the evidence
    disks, the least padded has one NUL.

    DLE indentation compression is what Apple's own editor emits, so it is
    the default here; it is a pure size optimisation and `compress=False`
    writes the same lines as literal spaces. Neither form is "the" encoding
    of a given text -- `decode_text` accepts both and maps them onto the same
    string, which is why the round-trip that can be checked is
    `decode_text(encode_text(s)) == s` and not equality of bytes.

    `header` is the 1024-byte editor environment block. Zeros are fine for a
    file the compiler will read; the editor rewrites it on first save.
    """
    if header is None:
        header = bytes(HEADER_BYTES)
    if len(header) != HEADER_BYTES:
        raise ValueError(f"header is {len(header)} bytes, need {HEADER_BYTES}")

    def render(line: str) -> bytes:
        body = line.rstrip("\n")
        if any(ord(c) > 0x7E or ord(c) < 0x20 for c in body):
            bad = next(c for c in body if ord(c) > 0x7E or ord(c) < 0x20)
            raise ValueError(f"line contains non-printable {ord(bad):#04x}: "
                             f"{body!r}")
        if compress:
            ind = len(body) - len(body.lstrip(" "))
            # The indent byte is `ind + 32` and is one byte, so runs past 223
            # cannot be expressed; and two bytes only pay for themselves past
            # two spaces.
            if 2 < ind <= 0xDF:
                return bytes((DLE, ind + 32)) + body[ind:].encode("ascii") \
                    + bytes((CR,))
        return body.encode("ascii") + bytes((CR,))

    # No trailing-newline normalisation here, deliberately. It is tempting:
    # in UCSD every line ends with CR including the last, so a host file's
    # final newline is a terminator and swallowing it stops a converted file
    # gaining a blank line. But ten of the 21 `.TEXT` files on the evidence
    # disks really do end with a blank line, and `decode_text` reports it, so
    # swallowing it here would stop this being the reader's inverse. The
    # caller knows which convention its input follows; this does not.
    body = text.replace("\r\n", "\n").replace("\r", "\n")

    out = bytearray(header)
    page = bytearray()
    for line in body.split("\n"):
        enc = render(line)
        if len(enc) >= PAGE:
            raise ValueError(f"line of {len(enc)} bytes will not fit in a "
                             f"{PAGE}-byte page: {line[:60]!r}...")
        if len(page) + len(enc) >= PAGE:
            out += page + bytes(PAGE - len(page))
            page = bytearray()
        page += enc
    if page:
        out += page + bytes(PAGE - len(page))
    return bytes(out)
