"""Lift UCSD p-code to expression-level pseudo-Pascal.

The p-machine is a plain stack machine, so most of a procedure can be
recovered by symbolically executing the evaluation stack across a basic
block: pushes build expression trees, and the store instructions
(SRO/STL/STO/STB/...) are what turn them into statements.

Naming follows the raw storage, deliberately: G<n> is global word n, L<n>
local word n, I<lex>,<n> an intermediate. Nothing here invents a source
identifier -- that mapping belongs in the analysis documents, where it can
carry a confidence level.

Where the stack effect of an instruction is not known (chiefly a CSP whose
arity we have not established), the block is marked and the remaining
instructions are emitted verbatim rather than guessed at.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pathlib import Path

from .pcode import Insn, disassemble, sweep_exit
from .syscall import segment0_signatures

_GLOBALS_TEXT = (Path(__file__).resolve().parents[2]
                 / "reference_source" / "ucsd_ii0" / "GLOBALS.TEXT")
try:
    OS_SIG = segment0_signatures(_GLOBALS_TEXT)
except OSError:
    OS_SIG = {}

# CSP number -> (pops, pushes). Only the ones whose arity is established.
# 0-11 are the documented UCSD II.0 set. 34 and 40 were recovered by
# tools/probes/probe_csp_arity.py, which searches for the arity that makes
# the most procedures' evaluation stacks balance; both came out as
# zero-argument word-returning functions with a clear margin over the
# runner-up, which fits IORESULT and MEMAVAIL (both are interpreter
# routines in Apple Pascal 1.1 -- Hyde pp.347 and 342).
# CSP 6, 21, 22, 23, 24, 32, 33 and 36 remain unresolved: 36 tied, and the
# rest occur only in procedures already blocked for other reasons.
CSP_EFFECT = {
    0: (0, 0),    # IOCHECK
    1: (2, 0),    # NEW(ptr, size)
    2: (3, 0),    # MOVELEFT(src, dst, n)
    3: (3, 0),    # MOVERIGHT
    4: (2, 0),    # EXIT
    7: (2, 0),    # IDSEARCH
    8: (3, 0),    # TREESEARCH
    9: (2, 0),    # TIME
    10: (3, 0),   # FILLCHAR
    11: (4, 1),   # SCAN -> count
    34: (0, 1),   # solved; consistent with IORESULT
    40: (0, 1),   # solved; consistent with MEMAVAIL
}

BINOP = {
    "ADI": "+", "SBI": "-", "MPI": "*", "DVI": " div ", "MODI": " mod ",
    "ADR": "+", "SBR": "-", "MPR": "*", "DVR": "/",
    "LAND": " and ", "LOR": " or ",
    "EQUI": " = ", "NEQI": " <> ", "LESI": " < ", "LEQI": " <= ",
    "GRTI": " > ", "GEQI": " >= ",
    "UNI": " + ", "INT": " * ", "DIF": " - ", "INN": " in ",
}
CMPOP = {"EQU": " = ", "NEQ": " <> ", "LES": " < ", "LEQ": " <= ",
         "GRT": " > ", "GEQ": " >= "}
UNOP = {"NGI": "-", "NGR": "-", "LNOT": "not ", "ABI": "abs", "SQI": "sqr",
        "ABR": "abs", "SQR": "sqr", "FLT": "flt", "FLO": "flo"}


@dataclass
class Block:
    start: int
    insns: list = field(default_factory=list)
    stmts: list = field(default_factory=list)
    succs: list = field(default_factory=list)
    cond: str | None = None       # condition of a trailing FJP
    fallthrough: int | None = None
    branch: int | None = None
    incomplete: bool = False
    underflow: bool = False


def _targets(stream: list[Insn]) -> set[int]:
    t = set()
    for i in stream:
        if i.target is not None:
            t.add(i.target)
        if i.mnemonic == "XJP":
            t.add(i.operands[2])
            t.update(i.operands[3])
    return t


def split_blocks(stream: list[Insn]) -> list[Block]:
    leaders = _targets(stream)
    if stream:
        leaders.add(stream[0].addr)
    for k, i in enumerate(stream):
        if i.mnemonic in ("FJP", "UJP", "XJP", "RNP", "RBP") and k + 1 < len(stream):
            leaders.add(stream[k + 1].addr)
    blocks, cur = [], None
    for i in stream:
        if cur is None or i.addr in leaders:
            cur = Block(i.addr)
            blocks.append(cur)
        cur.insns.append(i)
    return blocks


class _Lifter:
    def __init__(self, param_words: int, callee_words):
        self.param_words = param_words
        self.callee_words = callee_words       # (kind, a, b) -> words popped

    def run(self, b: Block, entry: list[str] | None = None) -> list[str]:
        st: list[str] = list(entry or [])
        out = b.stmts

        def pop():
            if not st:
                # Underflow within a block is not automatically wrong -- a
                # block can consume a value its predecessor left -- but it
                # does mean this block's stack model is not self-contained,
                # and the arity solver must not treat it as a clean fit.
                b.underflow = True
                return "?"
            return st.pop()

        for k, i in enumerate(b.insns):
            m, o = i.mnemonic, i.operands
            try:
                if m == "SLDC":
                    st.append(str(o[0]))
                elif m == "LDCI":
                    st.append(str(o[0]))
                elif m == "LDCN":
                    st.append("nil")
                elif m in ("SLDL", "LDL"):
                    st.append(f"L{o[0]}")
                elif m in ("SLDO", "LDO"):
                    st.append(f"G{o[0]}")
                elif m == "LOD":
                    st.append(f"I{o[0]},{o[1]}")
                elif m == "LLA":
                    st.append(f"@L{o[0]}")
                elif m == "LAO":
                    st.append(f"@G{o[0]}")
                elif m == "LDA":
                    st.append(f"@I{o[0]},{o[1]}")
                elif m in ("SIND", "IND"):
                    a = pop()
                    st.append(f"{a}^" if o[0] == 0 else f"{a}^.f{o[0]}")
                elif m == "LDB":
                    idx, a = pop(), pop()
                    st.append(f"{a}^[{idx}]")
                elif m == "LDM":
                    st.append(f"{pop()}^<{o[0]}w>")
                elif m == "LSA":
                    st.append(repr(o[0].decode("ascii", "replace")))
                elif m == "LPA":
                    st.append("@" + repr(o[0].decode("ascii", "replace")))
                elif m == "LDC":
                    st.append("[" + ",".join(f"${w:04X}" for w in o[0]) + "]")
                elif m == "IXA":
                    idx, a = pop(), pop()
                    st.append(f"{a}[{idx}]" if o[0] == 1 else f"{a}[{idx}*{o[0]}w]")
                elif m == "INC":
                    st.append(f"({pop()}+{o[0]})")
                elif m in BINOP:
                    r, l = pop(), pop()
                    st.append(f"({l}{BINOP[m]}{r})")
                elif m in CMPOP:
                    r, l = pop(), pop()
                    st.append(f"({l}{CMPOP[m]}{r})")
                elif m in UNOP:
                    st.append(f"{UNOP[m]}({pop()})")
                elif m == "STL":
                    v = pop(); out.append(f"L{o[0]} := {v};")
                elif m == "SRO":
                    v = pop(); out.append(f"G{o[0]} := {v};")
                elif m == "STR":
                    v = pop(); out.append(f"I{o[0]},{o[1]} := {v};")
                elif m == "STO":
                    v, a = pop(), pop(); out.append(f"{a}^ := {v};")
                elif m == "STB":
                    v, idx, a = pop(), pop(), pop()
                    out.append(f"{a}^[{idx}] := {v};")
                elif m == "STM":
                    v, a = pop(), pop()
                    out.append(f"{a}^ := {v}  {{{o[0]} words}};")
                elif m == "SAS":
                    v, a = pop(), pop(); out.append(f"{a}^ := {v}  {{string}};")
                elif m == "MOV":
                    src, dst = pop(), pop()
                    out.append(f"move({dst}, {src}, {o[0]} words);")
                elif m == "ADJ":
                    st.append(f"adjust({pop()},{o[0]})")
                elif m == "CHK":
                    hi, lo, v = pop(), pop(), pop()
                    st.append(f"chk({v},{lo}..{hi})")
                elif m == "IXP":
                    # index packed array: leaves a 2-word packed-field
                    # reference, modelled here as one symbolic item
                    idx, a = pop(), pop()
                    st.append(f"{a}~[{idx}]{{{o[0]}per word,{o[1]} bits}}")
                elif m == "LDP":
                    st.append(f"{pop()}")
                elif m == "STP":
                    v, r = pop(), pop()
                    out.append(f"{r} := {v};")
                elif m == "SGS":
                    st.append(f"[{pop()}]")
                elif m == "SRS":
                    hi, lo = pop(), pop()
                    st.append(f"[{lo}..{hi}]")
                elif m == "CSP":
                    n = o[0]
                    if n not in CSP_EFFECT:
                        raise KeyError(f"CSP {n}")
                    pops, pushes = CSP_EFFECT[n]
                    args = [pop() for _ in range(pops)][::-1]
                    call = f"CSP{n}({', '.join(args)})"
                    (st.append(call) if pushes else out.append(call + ";"))
                elif m in ("CXP", "CLP", "CGP", "CIP", "CBP"):
                    words, label, isfn = self.callee_words(m, o)
                    if words is None:
                        raise KeyError(label)
                    args = [pop() for _ in range(words)][::-1]
                    call = f"{label}({', '.join(args)})"
                    (st.append(call) if isfn else out.append(call + ";"))
                elif m in ("FJP", "UJP", "RNP", "RBP", "NOP", "XJP"):
                    if m == "FJP":
                        b.cond = pop()
                    elif m == "XJP":
                        b.cond = pop()
                else:
                    raise KeyError(m)
            except KeyError as e:
                b.incomplete = True
                out.append(f"{{ stack tracking stopped: {e} }}")
                for j in b.insns[k:]:
                    out.append(f"{{ {j.text} }}")
                return []
        return st


def lift(seg, proc, cf) -> list[Block]:
    """Lift one procedure. `cf` supplies callee parameter sizes."""
    body, _ = disassemble(seg.data, proc.enter_ic, proc.exit_ic, proc.jtab)
    ex, _ = sweep_exit(seg.data, proc.exit_ic, proc.jtab - 8, proc.jtab)
    stream = body + ex
    blocks = split_blocks(stream)

    segbynum = {s.seg_num: s for s in cf.segments}

    def callee_words(mnem, ops):
        if mnem == "CXP":
            s, n = ops
            if s == 0:
                if n in OS_SIG:
                    name, words, is_fn = OS_SIG[n]
                    return words, name, is_fn
                return None, f"OS.{n} arity unknown", False
            tgt, label = segbynum.get(s), f"{segbynum[s].name}.{ops[1]}" \
                if ops[0] in segbynum else f"seg{s}.{n}"
        elif mnem == "CGP":
            tgt, n = segbynum.get(1), ops[0]
            label = f"{tgt.name}.{n}" if tgt else f"?.{n}"
        else:
            tgt, n = seg, ops[0]
            label = f"{seg.name}.{n}"
        if tgt is None:
            return None, label, False
        p = next((x for x in tgt.procedures if x.number == n), None)
        if p is None or p.is_native:
            return None, label, False
        isfn = False
        for i in reversed(disassemble(tgt.data, p.enter_ic, p.exit_ic, p.jtab)[0]
                          + sweep_exit(tgt.data, p.exit_ic, p.jtab - 8, p.jtab)[0]):
            if i.mnemonic in ("RNP", "RBP"):
                isfn = i.operands[0] != 0
                break
        return p.param_size // 2, label, isfn

    lifter = _Lifter(proc.param_size // 2, callee_words)
    addrs = [b.start for b in blocks]
    for k, b in enumerate(blocks):
        last = b.insns[-1]
        if last.mnemonic == "FJP":
            b.branch = last.target
            b.fallthrough = addrs[k + 1] if k + 1 < len(addrs) else None
        elif last.mnemonic == "UJP":
            b.branch = last.target
        elif last.mnemonic in ("RNP", "RBP", "XJP"):
            pass
        else:
            b.fallthrough = addrs[k + 1] if k + 1 < len(addrs) else None

    # Predecessor counts, so a stack can be carried across an edge only when
    # it is unambiguous which stack arrives.
    preds: dict[int, int] = {b.start: 0 for b in blocks}
    for b in blocks:
        for t in (b.branch, b.fallthrough):
            if t in preds:
                preds[t] += 1
        if b.insns[-1].mnemonic == "XJP":
            o = b.insns[-1].operands
            for t in [o[2], *o[3]]:
                if t in preds:
                    preds[t] += 1

    # An argument list can straddle a block boundary, so carry the residual
    # stack forward along a fallthrough edge when the successor has exactly
    # one predecessor. Anywhere else, start empty and report the residue.
    exits: dict[int, list[str]] = {}
    for k, b in enumerate(blocks):
        entry = None
        if k and blocks[k - 1].fallthrough == b.start and preds[b.start] == 1:
            entry = exits.get(blocks[k - 1].start)
        exits[b.start] = lifter.run(b, entry)

    for k, b in enumerate(blocks):
        residue = exits.get(b.start) or []
        carried = (k + 1 < len(blocks) and b.fallthrough == blocks[k + 1].start
                   and preds[blocks[k + 1].start] == 1)
        if residue and not carried:
            for leftover in residue:
                b.stmts.append(f"{{ left on stack: {leftover} }}")
    return blocks


def render(blocks: list[Block], header: str) -> str:
    used = {b.branch for b in blocks if b.branch is not None}
    out = [header]
    for b in blocks:
        if b.start in used:
            out.append(f"L{b.start:04X}:")
        for s in b.stmts:
            out.append("  " + s)
        if b.cond is not None and b.branch is not None:
            out.append(f"  if not ({b.cond}) then goto L{b.branch:04X};")
        elif b.branch is not None and b.cond is None:
            out.append(f"  goto L{b.branch:04X};")
    return "\n".join(out)
