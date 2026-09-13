"""Fit generated Pascal into the columns Apple's tools actually accept.

The fast tier will compile a 266-column line with a tab in it without
complaint. Apple's will not, and it took the acceptance tier being set up to
notice:

  * **`SYSTEM.ASSMBLER` errors on an input line over 80 characters** -- it is
    error 54 in the 1.3 manual's assembler error list, so this is a stated
    limit and not an inference;
  * **the Editor's display is 79 columns.** Past that it shows `!` in the
    last visible position and the rest of the line cannot be seen, which
    makes an over-long line unmaintainable on the machine even where the
    compiler would take it;
  * **nothing Apple shipped is over 80.** The longest line in any `.TEXT` on
    the six evidence disks is 77 (`GRAFDEMO.TEXT`), and the longest in the
    UCSD II.0 source is exactly 80.

Whether `SYSTEM.COMPILER` itself enforces 80 is *not* established here -- the
error list for the compiler has no counterpart to assembler error 54, and no
line on the disks is long enough to have tested it. What is established is
that 80 is the width every surviving source was written to, so generated
source is held to it too.

Wrapping is safe because Pascal is free-form: any run of whitespace outside a
string literal or a comment can become a newline. This splits there and
nowhere else, so it cannot change what the compiler sees -- which is the
property `probe_xcompile.py` then confirms by compiling the result and
requiring Apple's own frame back.
"""

from __future__ import annotations

import re

WIDTH = 80
TAB = 8


def expand_tabs(text: str, stop: int = TAB) -> str:
    """Tabs to spaces, column by column -- except inside a string literal.

    UCSD `.TEXT` has no tab for *indentation*: the editor stores that as a
    DLE pair, and a literal 0x09 in a source file's whitespace is something
    a modern editor put there. Two of them reached the skeleton by way of
    the II.0 declarations.

    A tab **inside quotes** is a different thing and has to survive.
    INSYMBOL's whitespace case label is `'<tab>',' '` -- II.0's source has
    the character itself, and it must, because a case label has to be a
    constant and Apple's compiler rejects `CHR(9)` there with error 103.
    """
    out = []
    for line in text.split("\n"):
        col, buf, quoted = 0, [], False
        for ch in line:
            if ch == "'":
                quoted = not quoted
            if ch == "\t" and not quoted:
                n = stop - (col % stop)
                buf.append(" " * n)
                col += n
            else:
                buf.append(ch)
                col += 1
        out.append("".join(buf))
    return "\n".join(out)


def _spans(line: str) -> list[bool]:
    """For each character, whether it is inside a string or a comment.

    Pascal comments do not nest and come in two spellings; a `''` inside a
    string is an escaped quote and does not end it.
    """
    prot = [False] * len(line)
    i, state = 0, None
    while i < len(line):
        two = line[i:i + 2]
        if state is None:
            if line[i] == "'":
                state, prot[i] = "str", True
            elif line[i] == "{":
                state, prot[i] = "brace", True
            elif two == "(*":
                state = "paren"
                prot[i] = prot[i + 1] = True
                i += 2
                continue
        else:
            prot[i] = True
            if state == "str" and line[i] == "'":
                state = None
            elif state == "brace" and line[i] == "}":
                state = None
            elif state == "paren" and two == "*)":
                prot[i + 1] = True
                state = None
                i += 2
                continue
        i += 1
    return prot


def _unbreakable(line: str) -> list[bool]:
    """Where a newline must not go.

    Narrower than `_spans`: a `{ }` or `(* *)` comment may be broken across
    lines and often has to be, since an annotation can be the whole line. What
    must stay intact is a string literal -- Pascal has no continuation for one
    -- and the two-character comment brackets.

    It has to track comments even though it does not protect them, because a
    quote inside one is not a string: the `SEGTABLE` annotation reads "Apple's
    entry is 9 words", and taking that apostrophe for an opening quote
    protects the rest of the line and leaves it unbreakable.
    """
    prot = [False] * len(line)
    i, state = 0, None
    while i < len(line):
        two = line[i:i + 2]
        if state is None:
            if line[i] == "'":
                state, prot[i] = "str", True
            elif line[i] == "{":
                state = "brace"
            elif two == "(*":
                state = "paren"
                prot[i] = prot[i + 1] = True
                i += 2
                continue
        elif state == "str":
            prot[i] = True
            if line[i] == "'":
                state = None
        elif state == "brace":
            if line[i] == "}":
                state = None
        elif state == "paren":
            if two == "*)":
                prot[i] = prot[i + 1] = True
                state = None
                i += 2
                continue
        i += 1
    return prot


def split_comment(line: str) -> tuple[str, str]:
    """Separate a trailing `{ ... }` annotation from the code before it.

    `varblock.py` writes the offset and word count of every global as a
    comment after the declaration, which is most of what pushes these lines
    past 80. The comment is worth keeping and does not have to be there.
    """
    prot = _spans(line)
    start = None
    for i, ch in enumerate(line):
        if ch == "{" and prot[i] and (i == 0 or not prot[i - 1]):
            start = i
    if start is None or not line.rstrip().endswith("}"):
        return line, ""
    return line[:start].rstrip(), line[start:].rstrip()


def wrap(line: str, width: int = WIDTH, indent: int | None = None) -> list[str]:
    """Break one line at whitespace so that no piece exceeds `width`.

    Continuations are indented past the original's leading whitespace so the
    declaration still reads as one item. A single token longer than the width
    is emitted over-long rather than corrupted -- the caller is told by the
    line still being too long, which is better than a silent split inside an
    identifier.
    """
    if len(line) <= width:
        return [line]
    lead = len(line) - len(line.lstrip())
    cont = " " * (lead + 4 if indent is None else indent)
    if len(cont) >= width:
        return [line]                         # no room to continue into
    # Computed once over the whole line: comment and string state cannot be
    # recovered from a fragment, and the second half of a wrapped annotation
    # starts in the middle of a comment.
    prot = _unbreakable(line)
    out, start = [], 0

    def breakable(i, frm):
        return line[i] == " " and not prot[i] and not prot[i - 1] \
            and line[frm:i].strip()

    while True:
        pre = "" if not out else cont
        if len(pre) + len(line) - start <= width:
            break
        room = width - len(pre)
        cut = max((i for i in range(start + 1, min(start + room + 1, len(line)))
                   if breakable(i, start)), default=None)
        if cut is None:
            # Nothing breakable within the width; take the first break past
            # it and let this piece run over rather than split a token.
            cut = next((i for i in range(min(start + room, len(line)), len(line))
                        if breakable(i, start)), None)
        if cut is None:
            break
        out.append(pre + line[start:cut].rstrip())
        start = cut
        while start < len(line) and line[start] == " ":
            start += 1
    tail = line[start:].rstrip()
    if tail:
        out.append(("" if not out else cont) + tail)
    return out


def format_lines(lines: list[str], width: int = WIDTH) -> list[str]:
    """Fit a block of generated Pascal into `width` columns.

    A trailing annotation comment is lifted onto its own line above the
    declaration, which is enough on its own for most of them; anything still
    too long is then wrapped at whitespace.
    """
    out: list[str] = []
    for raw in expand_tabs("\n".join(lines)).split("\n"):
        if len(raw) <= width:
            out.append(raw)
            continue
        code, comment = split_comment(raw)
        lead = " " * (len(raw) - len(raw.lstrip()))
        if comment:
            out += wrap(lead + comment, width, len(lead))
        out += wrap(code, width)
    return out


_LONE_LITERAL = re.compile(r"'(?:[^']|'')*'[;,)]*")


def over_width(lines: list[str], width: int = WIDTH) -> list[tuple[int, int]]:
    """(line number, length) for every line that is still too long.

    One exception: a line that is nothing but a single Pascal string
    literal, starting in column 1, with at most closing punctuation after
    it. Pascal cannot continue a literal onto the next line, so an
    80-character prompt (SYSTEM.EDITOR's COMPROMPT) is 82 columns however
    it is written. Apple's compiler reads a line of any length; the limit
    is the assembler's (error 54), and no assembler source is shaped like
    this. Indentation disqualifies a line -- that can always be removed.
    """
    return [(i, len(ln)) for i, ln in enumerate(lines, 1)
            if len(ln) > width and not _LONE_LITERAL.fullmatch(ln)]
