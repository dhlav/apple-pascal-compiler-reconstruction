"""Lay out UCSD Pascal types, so a declaration can be sized in words.

Everything this repo reconstructs has to *allocate* the way Apple's compiler
allocated, because the offsets are baked into every `LDO`, `SRO`, `LAO` and
field access in the binary. A type declaration is therefore a claim about
code bytes, and a claim needs checking. This sizes declarations so that the
II.0 source's records can be held against the sizes the binary forces.

The rules, all of them UCSD's rather than this repo's:

  * a word is 16 bits; `INTEGER`, `BOOLEAN`, `CHAR`, an enumeration, a
    subrange and any pointer are one word, `REAL` is two;
  * `PACKED ARRAY [a..b] OF CHAR` packs two characters to the word, so
    `ALPHA = PACKED ARRAY [1..8] OF CHAR` is four;
  * an unpacked array is its length times its element size;
  * `SET OF a..b` is the words needed to hold bits 0..b;
  * a record is its fixed fields, then -- if it has a variant part -- one
    word for the tag *if the tag is named*, and the size of the variant
    being asked about. An anonymous `CASE BOOLEAN OF` has no tag word.

That last rule is the one that matters here: a variant record has no single
size, it has one per variant, and the binary allocates the variant it is
using. `record_variants` returns all of them.

Constants are read from the same file's `CONST` block, so `PACKED ARRAY
[1..STRGLGTH] OF CHAR` sizes without STRGLGTH being written down twice.
"""
from __future__ import annotations

import re

WORD_TYPES = {"INTEGER", "BOOLEAN", "CHAR", "TEXT_UNUSED"}
DOUBLE_TYPES = {"REAL"}


class Layout:
    """Type and constant declarations from one Pascal source file."""

    def __init__(self, text: str):
        self.text = _strip_comments(text)
        self.consts = _consts(self.text)
        self.types = _types(self.text)

    # -- values -------------------------------------------------------
    def value(self, expr: str) -> int:
        """A constant expression: a literal, a named constant, or a sum."""
        expr = expr.strip()
        m = re.fullmatch(r"(.+?)\s*([-+])\s*(.+)", expr)
        if m:
            a, op, b = self.value(m.group(1)), m.group(2), self.value(m.group(3))
            return a + b if op == "+" else a - b
        if re.fullmatch(r"-?\d+", expr):
            return int(expr)
        key = expr.upper()
        if key in self.consts:
            return self.value(self.consts[key])
        raise KeyError(f"no value for {expr!r}")

    def _bounds(self, spec: str) -> tuple[int, int]:
        """`a..b`, or the ordinal range of a named enumeration or subrange."""
        spec = spec.strip()
        if ".." in spec:
            lo, hi = spec.split("..", 1)
            return self.value(lo), self.value(hi)
        body = self.types.get(spec.upper())
        if body is None:
            raise KeyError(f"no range for {spec!r}")
        if body.strip().startswith("("):
            n = len([x for x in body.strip()[1:body.rindex(")")].split(",")
                     if x.strip()])
            return 0, n - 1
        return self._bounds(body)

    # -- sizes --------------------------------------------------------
    def size(self, expr: str) -> int:
        """Size of a type expression, in words."""
        e = " ".join(expr.split()).strip().rstrip(";")
        if e.startswith("^"):
            return 1
        up = e.upper()
        if up in DOUBLE_TYPES:
            return 2
        if up in WORD_TYPES:
            return 1

        m = re.match(r"^(PACKED\s+)?ARRAY\s*\[(.+?)\]\s*OF\s+(.+)$", e, re.I)
        if m:
            packed, rng, elt = bool(m.group(1)), m.group(2), m.group(3).strip()
            lo, hi = self._bounds(rng)
            n = hi - lo + 1
            if packed and elt.upper() == "CHAR":
                return (n + 1) // 2          # two characters to the word
            return n * self.size(elt)

        m = re.match(r"^(PACKED\s+)?SET\s+OF\s+(.+)$", e, re.I)
        if m:
            _lo, hi = self._bounds(m.group(2))
            return (hi + 16) // 16

        if re.match(r"^(PACKED\s+)?RECORD\b", e, re.I):
            return max(self.record_variants(e).values())

        if e.startswith("("):                # enumeration
            return 1
        if ".." in e:                        # subrange
            return 1
        if up in self.types:
            return self.size(self.types[up])
        return 1                             # an opaque scalar is one word

    # -- records ------------------------------------------------------
    def record_variants(self, expr: str) -> dict[str, int]:
        """Every variant of a record, by the label that selects it.

        The key for a record with no variant part, and for the fixed part of
        one that has, is `""`. Nested variants are keyed by the outermost
        label, and take the largest size reachable underneath -- which is
        what the compiler allocates when it does not know the inner tag.
        """
        e = " ".join(expr.split())
        body = e[re.match(r"(PACKED\s+)?RECORD\b", e, re.I).end():]
        body = body[:_matching_end(body)]
        fixed, cases = _split_variant(body)
        base = sum(self._field_words(f) for f in _fields(fixed))
        if not cases:
            return {"": base}
        tag, arms = cases
        # A named tag occupies a word; `CASE BOOLEAN OF` does not.
        base += 1 if tag else 0
        out = {"": base}
        for labels, arm in arms:
            inner = self._arm_words(arm)
            for label in labels:
                out[label.upper()] = base + inner
        return out

    def _arm_words(self, arm: str) -> int:
        """A variant arm: its own fields, plus its own largest sub-variant."""
        fixed, cases = _split_variant(arm)
        n = sum(self._field_words(f) for f in _fields(fixed))
        if not cases:
            return n
        tag, arms = cases
        n += 1 if tag else 0
        return n + max((self._arm_words(a) for _l, a in arms), default=0)

    def _field_words(self, field: str) -> int:
        names, _, typ = field.partition(":")
        count = len([x for x in names.split(",") if x.strip()])
        return count * self.size(typ)


# ---- text handling ---------------------------------------------------
def _strip_comments(t: str) -> str:
    t = re.sub(r"\(\*.*?\*\)", " ", t, flags=re.S)
    return re.sub(r"\{.*?\}", " ", t, flags=re.S)


def _blocks(t: str, kw: str) -> list[str]:
    """Every `kw` section, each running to the next section keyword.

    A Pascal source has more than one -- `compglbls.text` opens with a
    one-line `TYPE PHYLE = FILE;` long before the real one -- so taking the
    first would find almost nothing.
    """
    stop = re.compile(r"\b(CONST|TYPE|VAR|PROCEDURE|FUNCTION|BEGIN)\b", re.I)
    out = []
    for m in re.finditer(rf"\b{kw}\b", t, re.I):
        nxt = stop.search(t, m.end())
        out.append(t[m.end():nxt.start() if nxt else len(t)])
    return out


def _consts(t: str) -> dict[str, str]:
    out = {}
    for decl in ";".join(_blocks(t, "CONST")).split(";"):
        if "=" in decl:
            name, _, val = decl.partition("=")
            if re.fullmatch(r"\s*[A-Za-z_][A-Za-z_0-9]*\s*", name):
                out[name.strip().upper()] = val.strip()
    return out


def _types(t: str) -> dict[str, str]:
    """name -> type expression, for every `name = ...;` in the TYPE block."""
    body = ";".join(_blocks(t, "TYPE"))
    out = {}
    for hit in re.finditer(r"([A-Za-z_][A-Za-z_0-9]*)\s*=\s*", body):
        name = hit.group(1).upper()
        rest = body[hit.end():]
        # The declaration runs to the semicolon that is not inside brackets,
        # parentheses or a nested RECORD.
        depth = 0
        i = 0
        while i < len(rest):
            c = rest[i]
            if c in "([":
                depth += 1
            elif c in ")]":
                depth -= 1
            elif re.match(r"RECORD\b", rest[i:], re.I):
                depth += 1
                i += 6
                continue
            elif re.match(r"END\b", rest[i:], re.I):
                depth -= 1
                i += 3
                continue
            elif c == ";" and depth <= 0:
                break
            i += 1
        out.setdefault(name, rest[:i].strip())
    return out


def _matching_end(body: str) -> int:
    """Index of the END closing the RECORD that `body` is the inside of."""
    depth = 0
    i = 0
    while i < len(body):
        if re.match(r"\bRECORD\b", body[i:], re.I) or \
           re.match(r"^RECORD\b", body[i:], re.I):
            depth += 1
            i += 6
            continue
        m = re.match(r"END\b", body[i:], re.I)
        if m:
            if depth == 0:
                return i
            depth -= 1
            i += 3
            continue
        i += 1
    return len(body)


def _split_variant(body: str) -> tuple[str, tuple[str, list] | None]:
    """(fixed part, (tag name or '', [(labels, arm text)])) of a record body."""
    m = re.search(r"\bCASE\b", body, re.I)
    if not m:
        return body, None
    fixed = body[:m.start()]
    rest = body[m.end():]
    head, _, arms_text = rest.partition(" OF ") if " OF " in rest.upper() else (rest, "", "")
    # re-split case-insensitively
    om = re.search(r"\bOF\b", rest, re.I)
    head, arms_text = rest[:om.start()], rest[om.end():]
    tag = ""
    if ":" in head:
        tag = head.split(":")[0].strip()
    # Walk the arms, skipping over each one's parenthesised body. Scanning
    # with finditer instead would resume *inside* an arm and report a nested
    # variant's labels as if they belonged to this level.
    arms = []
    pos = 0
    while True:
        am = re.compile(r"([^():;]+?)\s*:\s*\(").search(arms_text, pos)
        if not am:
            break
        labels = [x.strip() for x in am.group(1).split(",") if x.strip()]
        start = i = am.end()
        depth = 1
        while i < len(arms_text) and depth:
            depth += (arms_text[i] == "(") - (arms_text[i] == ")")
            i += 1
        arms.append((labels, arms_text[start:i - 1]))
        pos = i
    return fixed, (tag, arms)


def _fields(fixed: str) -> list[str]:
    return [f for f in (x.strip() for x in fixed.split(";")) if ":" in f]
