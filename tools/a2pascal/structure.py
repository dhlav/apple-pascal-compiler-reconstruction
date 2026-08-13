"""Recover Pascal control flow from the lifted basic-block graph.

The lifter produces statements plus a CFG; this turns the CFG back into
`if`/`while`/`repeat`/`case`. It is the second half of plan step 8 and the
last thing between the lifted output and source a compiler would accept.

Method: recursive descent over the blocks *in address order*, which works
because a Pascal compiler emits structured source as linear code with
forward branches out of each construct. Each construct is recognised by the
shape it leaves behind:

    if c then          <cond>; FJP past-the-then
    if/else            ... then-part ends UJP past-the-else
    while c do         loop header whose FJP leaves the loop, latch UJPs back
    repeat until c     no header test; latch FJPs back to the head
    case               XJP, whose jump table the decoder already carries

Nothing is forced. A region that does not match a pattern exactly is
emitted as the plain blocks and gotos it always was, so the output stays
faithful and the unstructured remainder stays visible and countable. That
count is the measure of this module: `structured_fraction` reports it, and
liftall prints it.
"""

from __future__ import annotations

INDENT = "  "


def _succs(b) -> list[int]:
    return list(b.succs)


def _is_goto_only(b) -> bool:
    """Block that does nothing but jump."""
    return not b.stmts and b.cond is None and b.branch is not None


class _Structurer:
    def __init__(self, blocks):
        self.blocks = blocks
        self.by = {b.start: b for b in blocks}
        self.order = [b.start for b in blocks]
        self.idx = {a: i for i, a in enumerate(self.order)}
        self.gotos = 0          # gotos that survived structuring
        self.labels: set[int] = set()
        # Blocks whose *terminal jump* a construct has absorbed. The block
        # is still emitted -- a latch or an else-skipping block usually
        # carries real statements ahead of its jump, and dropping the whole
        # block to get rid of the jump silently loses them.
        self.absorbed: set[int] = set()
        # Loop headers currently being emitted. `repeat` re-enters emit()
        # at its own header, so without this it would rediscover the same
        # back edge and recurse forever.
        self.open_loops: set[int] = set()

    # -- helpers ---------------------------------------------------------
    def _at(self, i):
        return self.by[self.order[i]]

    def _index_of(self, addr):
        return self.idx.get(addr)

    def _backedge_latch(self, i, hi):
        """Largest j in (i, hi) with an edge back to block i, or None."""
        head = self.order[i]
        cands = [j for j in range(i + 1, hi)
                 if head in _succs(self._at(j))]
        return max(cands) if cands else None

    def _escapes(self, lo, hi, allowed):
        """True if any block in [lo,hi) jumps somewhere outside the region.

        `allowed` is the set of addresses a construct may legitimately exit
        to. Anything else means the region is not self-contained and must
        not be wrapped in a Pascal construct.
        """
        span = {self.order[k] for k in range(lo, hi)}
        for k in range(lo, hi):
            for s in _succs(self._at(k)):
                if s not in span and s not in allowed:
                    return True
        return False

    # -- emit ------------------------------------------------------------
    def emit(self, lo, hi, depth) -> list[str]:
        out: list[str] = []
        i = lo
        while i < hi:
            b = self._at(i)
            step = self._one(b, i, hi, depth, out)
            i = step
        return out

    def _one(self, b, i, hi, depth, out) -> int:
        pad = INDENT * depth
        last = b.insns[-1]

        # ---- loops, before anything else: a back edge into this block
        latch = self._backedge_latch(i, hi)
        if latch is not None and b.start not in self.open_loops:
            n = self._loop(b, i, latch, hi, depth, out)
            if n is not None:
                return n

        # ---- case
        if last.mnemonic == "XJP":
            n = self._case(b, i, hi, depth, out)
            if n is not None:
                return n

        # ---- if
        if b.cond is not None and b.branch is not None:
            n = self._if(b, i, hi, depth, out)
            if n is not None:
                return n

        # ---- plain block, with whatever jump it carries
        self._plain(b, depth, out)
        return i + 1

    def _plain(self, b, depth, out):
        pad = INDENT * depth
        for s in b.stmts:
            out.append(pad + s)
        if b.start in self.absorbed:
            return
        if b.cond is not None and b.branch is not None:
            out.append(f"{pad}if not ({b.cond}) then goto L{b.branch:04X};")
            self.gotos += 1
            self.labels.add(b.branch)
        elif b.branch is not None:
            out.append(f"{pad}goto L{b.branch:04X};")
            self.gotos += 1
            self.labels.add(b.branch)
        elif b.insns[-1].mnemonic == "XJP":
            o = b.insns[-1].operands
            out.append(f"{pad}case <selector> of  {{ {o[0]}..{o[1]} }}")
            for v, t in zip(range(o[0], o[1] + 1), o[3]):
                out.append(f"{pad}{INDENT}{v}: goto L{t:04X};")
                self.labels.add(t)
                self.gotos += 1
            out.append(f"{pad}{INDENT}otherwise goto L{o[2]:04X};")
            self.labels.add(o[2])
            self.gotos += 1
            out.append(f"{pad}end;")

    # -- constructs ------------------------------------------------------
    def _loop(self, b, i, latch, hi, depth, out):
        pad = INDENT * depth
        lat = self._at(latch)
        after = latch + 1
        after_addr = self.order[after] if after < len(self.order) else None

        # while: the header tests and its false branch leaves the loop; the
        # header must carry no statements of its own, or they would belong
        # inside the loop before the test and Pascal cannot say that.
        if (not b.stmts and b.cond is not None and b.branch == after_addr
                and lat.branch == b.start and lat.cond is None):
            if self._escapes(i, after, {b.start, after_addr}):
                return None
            self.absorbed.add(lat.start)     # its UJP is the loop's back edge
            out.append(f"{pad}while {b.cond} do begin")
            out += self.emit(i + 1, after, depth + 1)
            out.append(f"{pad}end;")
            return after

        # repeat/until: no test at the head, the latch tests and its false
        # branch goes back. FJP jumps when false, so "jump back if false"
        # is exactly "until <cond>".
        if lat.cond is not None and lat.branch == b.start:
            if self._escapes(i, after, {b.start, after_addr}):
                return None
            self.absorbed.add(lat.start)     # its FJP is the until test
            out.append(f"{pad}repeat")
            self.open_loops.add(b.start)
            out += self.emit(i, after, depth + 1)
            self.open_loops.discard(b.start)
            out.append(f"{pad}until {lat.cond};")
            return after

        return None

    def _if(self, b, i, hi, depth, out):
        pad = INDENT * depth
        t = self._index_of(b.branch)
        if t is None or t <= i or t > hi:
            return None

        # else-part: the block before the target ends in a forward jump
        # over a second region.
        prev = self._at(t - 1)
        e = self._index_of(prev.branch) if prev.branch is not None else None
        has_else = (prev.cond is None and e is not None and t < e <= hi
                    and t - 1 > i)

        end = e if has_else else t
        if self._escapes(i + 1, end, {self.order[end]} if end < len(self.order)
                         else set()):
            return None

        for s in b.stmts:
            out.append(pad + s)
        out.append(f"{pad}if {b.cond} then begin")
        if has_else:
            # block t-1 carries the jump over the else. Absorb the jump but
            # still emit the block: it usually has real statements first.
            self.absorbed.add(prev.start)
        out += self.emit(i + 1, t, depth + 1)
        if has_else:
            out.append(f"{pad}end else begin")
            out += self.emit(t, e, depth + 1)
        out.append(f"{pad}end;")
        return end

    def _case(self, b, i, hi, depth, out):
        pad = INDENT * depth
        o = b.insns[-1].operands
        lo_v, hi_v, other, table = o[0], o[1], o[2], o[3]
        arms = list(zip(range(lo_v, hi_v + 1), table))
        # Every arm must land inside the region and after this block, and
        # the arms must partition a contiguous stretch of blocks.
        raw = {self._index_of(t) for _, t in arms}
        if any(x is None or x <= i or x > hi for x in raw):
            return None
        tgts = sorted(raw)
        # the case ends where the last arm ends
        end = self._index_of(other)
        if end is None or end < max(tgts):
            return None
        if self._escapes(i + 1, end, {other}):
            return None

        for s in b.stmts:
            out.append(pad + s)
        out.append(f"{pad}case <selector> of")
        bounds = tgts + [end]
        for k, start in enumerate(tgts):
            vals = [str(v) for v, t in arms if self._index_of(t) == start]
            # an arm normally ends by jumping past the case; absorb that
            tail = self._at(bounds[k + 1] - 1)
            if tail.cond is None and tail.branch == other:
                self.absorbed.add(tail.start)
            out.append(f"{pad}{INDENT}{', '.join(vals)}: begin")
            out += self.emit(start, bounds[k + 1], depth + 2)
            out.append(f"{pad}{INDENT}end;")
        out.append(f"{pad}end;")
        return end


class _LabelStructurer(_Structurer):
    """Second pass: same walk, but emits a label before any block that the
    first pass found something still jumping to."""

    def __init__(self, blocks, want):
        super().__init__(blocks)
        self.want = want

    def _one(self, b, i, hi, depth, out):
        if b.start in self.want:
            out.append(f"L{b.start:04X}:")
        return super()._one(b, i, hi, depth, out)


def structure(blocks, header: str) -> tuple[str, int, int]:
    """Return (text, gotos remaining, blocks). Two passes: the first learns
    which labels survive structuring, the second places them."""
    if not blocks:
        return header, 0, 0
    first = _Structurer(blocks)
    first.emit(0, len(blocks), 1)
    second = _LabelStructurer(blocks, first.labels)
    body = second.emit(0, len(blocks), 1)
    return "\n".join([header] + body), second.gotos, len(blocks)


def structured_fraction(blocks) -> tuple[int, int]:
    """(gotos remaining, blocks) without rendering."""
    if not blocks:
        return 0, 0
    s = _Structurer(blocks)
    s.emit(0, len(blocks), 1)
    return s.gotos, len(blocks)
