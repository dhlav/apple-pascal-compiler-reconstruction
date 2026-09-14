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
                compress: bool = True, layout: "Layout | None" = None) -> bytes:
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

    `layout` is for the one case where the bytes do matter: a unit's
    interface, which the compiler copies into the codefile still encoded
    (finding 285). See `Layout`.
    """
    if header is None:
        header = bytes(HEADER_BYTES)
    if len(header) != HEADER_BYTES:
        raise ValueError(f"header is {len(header)} bytes, need {HEADER_BYTES}")

    def render(number: int, line: str) -> bytes:
        body = line.rstrip("\n")
        # TAB is the one control character a source line may carry: it is a
        # legal `.TEXT` byte, `decode_text` passes it through, and INSYMBOL's
        # whitespace case label is a literal one (see `expand_tabs`).
        def bad_char(c: str) -> bool:
            return ord(c) > 0x7E or (ord(c) < 0x20 and c != "	")

        if any(bad_char(c) for c in body):
            bad = next(c for c in body if bad_char(c))
            raise ValueError(f"line contains non-printable {ord(bad):#04x}: "
                             f"{body!r}")
        if layout is not None:
            return layout.render(number, body)
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

    lines = body.split("\n")
    if layout is not None:
        layout.check(lines)
    out = bytearray(header)
    page = bytearray()
    for number, line in enumerate(lines, 1):
        enc = render(number, line)
        if len(enc) >= PAGE:
            raise ValueError(f"line of {len(enc)} bytes will not fit in a "
                             f"{PAGE}-byte page: {line[:60]!r}...")
        if page and layout is not None and number in layout.pages:
            out += page + bytes(PAGE - len(page))
            page = bytearray()
        if len(page) + len(enc) >= PAGE:
            out += page + bytes(PAGE - len(page))
            page = bytearray()
        page += enc
    if page:
        out += page + bytes(PAGE - len(page))
    return bytes(out)


class Layout:
    """How an editor stored a file's lines, where plain text cannot say.

    A unit's interface is copied into its codefile still encoded (finding
    285), so for a unit the encoding is content. Apple's editor wrote a DLE
    indent code on nearly every line; a few lines kept typed spaces, which
    is editing history. A `.layout` file beside the source records it, one
    directive per line, `#` comments:

        dle              every line gets a DLE indent code, indent 0 and
                         blank lines included
        literal N        line N keeps its indentation as typed spaces
        split N K        line N: a DLE for K spaces, then the rest as typed
        page N           line N starts a new page
        expect N TEXT    line N must read TEXT (after one space), so an
                         edit that moves a line fails instead of misencoding

    Line numbers are 1-based, as an editor shows them.
    """

    def __init__(self, text: str):
        self.dle = False
        self.literal: dict[int, int] = {}      # line -> spaces in its DLE
        self.pages: set[int] = set()
        self.expect: dict[int, str] = {}
        for raw in text.splitlines():
            if raw.startswith("expect "):
                n, _, want = raw[len("expect "):].partition(" ")
                self.expect[int(n)] = want
                continue
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            word, _, rest = line.partition(" ")
            if word == "dle":
                self.dle = True
            elif word == "literal":
                self.literal[int(rest)] = 0
            elif word == "split":
                n, k = rest.split()
                self.literal[int(n)] = int(k)
            elif word == "page":
                self.pages.add(int(rest))
            else:
                raise ValueError(f"unknown layout directive: {raw!r}")
        if not self.dle:
            raise ValueError("a layout must say `dle`")

    @classmethod
    def beside(cls, source) -> "Layout | None":
        """The layout for `source`, if a `.layout` of the same stem exists."""
        from pathlib import Path
        path = Path(source).with_suffix(".layout")
        return cls(path.read_text(encoding="ascii")) if path.exists() else None

    def check(self, lines: list[str]) -> None:
        for n, want in sorted(self.expect.items()):
            got = lines[n - 1] if n <= len(lines) else None
            if got != want:
                raise ValueError(f"layout expects line {n} to be {want!r}, "
                                 f"it is {got!r}")

    def render(self, number: int, body: str) -> bytes:
        ind = len(body) - len(body.lstrip(" "))
        if number in self.literal:
            k = self.literal[number]
            if k > ind:
                raise ValueError(f"line {number}: a DLE for {k} spaces, but "
                                 f"it is indented {ind}")
            head = bytes((DLE, k + 32)) if k else b""
            return head + body[k:].encode("ascii") + bytes((CR,))
        return (bytes((DLE, ind + 32)) + body[ind:].encode("ascii")
                + bytes((CR,)))
