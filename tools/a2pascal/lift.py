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
from .names import SYMBOLS, SYMBOL_SET_NAMES, globalname, procname
from .syscall import CSP

# Instructions that decide what a two-word LDC constant was: real
# arithmetic means it is a REAL, a set operator means it is a set.
REAL_OPS = {"ADR", "SBR", "MPR", "DVR", "NGR", "ABR", "SQR", "FLT", "FLO"}
SET_OPS = {"UNI", "INT", "DIF", "INN", "SGS", "ADJ"}
CMP_OPS = {"EQU", "NEQ", "LES", "LEQ", "GRT", "GEQ"}   # operand 2 = REAL

_GLOBALS_TEXT = (Path(__file__).resolve().parents[2]
                 / "reference_source" / "ucsd_ii0" / "GLOBALS.TEXT")
try:
    OS_SIG = segment0_signatures(_GLOBALS_TEXT)
except OSError:
    OS_SIG = {}

# CSP number -> (pops, pushes), counted in 16-bit words on the evaluation
# stack -- NOT in Pascal source-level arguments. The two differ whenever an
# argument is a packed-array reference, which the compiler passes as a
# (base, index) pair occupying two words: FILLCHAR looks like three
# arguments in Pascal and pops four words here.
#
# VERIFIED SOURCE FACT for everything below, counted off the pops and pushes
# in each handler of John Brooks' Apple Pascal 1.4 interpreter (Interp.s),
# then confirmed against the binary by tools/probes/probe_csp_check.py --
# adopting these arities raises the number of cleanly balancing procedures,
# which is a result a wrong table could not produce.
#
# This replaces four values that the earlier hand-built table got wrong by
# counting Pascal arguments instead of stack words (CSP 2, 3, 10, 11), and
# supplies the ten that tools/probes/probe_csp_arity.py could not reach. The
# two that probe did solve, 34 and 40, are confirmed exactly: they are
# IORESULT and MEMAVAIL, both zero-argument word-returning functions.
# (segment, procedure number) -> (param words, is function, name).
#
# Only Apple Pascal 1.3 has native procedures, and only these two: the
# hand-coded IDSEARCH and TREESEARCH that replaced 1.1's CSP 7 and CSP 8
# (finding 19). They carry no p-code, so their signatures cannot be read
# off a return instruction the way every other callee's can, and without
# them the four procedures that call them cannot be lifted.
# Native procedures carry no p-code to read a signature out of, so it has
# to be supplied. The word count is the total the call pops, which for a
# function includes the two-word result area the caller reserves
# (tools/probes/probe_funcresult.py): TREESEARCH takes three arguments --
# the same three 1.1 passes to CSP 8 -- plus that area, so five.
NATIVE_SIG = {
    ("PASCALCO", 2): (2, False, "IDSEARCH"),
    ("PASCALCO", 3): (5, True, "TREESEARCH"),
}

CSP_EFFECT = {
    0: (0, 0),    # IOCHECK    -- inspects IOResult, touches no stack
    1: (2, 0),    # NEW(ptr, nwords)
    2: (5, 0),    # MOVELEFT(src[2], dst[2], nbytes)
    3: (5, 0),    # MOVERIGHT  -- same handler as MOVELEFT
    4: (2, 0),    # EXIT(proc, seg)
    5: (6, 0),    # UNITREAD(unit, buf[2], len, blk, mode)
    6: (6, 0),    # UNITWRITE  -- same handler as UNITREAD
    9: (2, 0),    # TIME(hiptr, loptr)
    10: (4, 0),   # FILLCHAR(dst[2], nbytes, char)
    11: (6, 1),   # SCAN(...) -> displacement
    12: (4, 0),   # UNITSTATUS(unit, pab[2], control)
    21: (1, 0),   # LOADSEGMENT(segnum)
    22: (1, 0),   # UNLOADSEGMENT(segnum)
    23: (2, 1),   # TRUNC(real) -> integer
    # ROUND shares TRUNC's handler shape -- PopFPAcc takes a 4-byte real, the
    # handler pushes 2 bytes -- so (2,1) is not in doubt. Recorded here
    # because probe_csp_check reports it as CONTRADICTED: with only two call
    # sites in the whole compiler, (0,0) happens to balance one more
    # procedure. That is the join-straddling limitation of finding 13 showing
    # through, not evidence about ROUND. Source wins; the probe is too weak
    # at n=2 to overturn it.
    24: (2, 1),   # ROUND(real) -> integer
    32: (1, 0),   # MARK(ptr)
    33: (1, 0),   # RELEASE(ptr)
    34: (0, 1),   # IORESULT -> integer
    35: (1, 1),   # UNITBUSY(unit) -> boolean
    36: (1, 2),   # PWROFTEN(integer) -> real
    37: (1, 0),   # UNITWAIT(unit)
    38: (1, 0),   # UNITCLEAR(unit)
    39: (0, 0),   # HALT
    40: (0, 1),   # MEMAVAIL -> integer
    # 7 IDSEARCH and 8 TREESEARCH are the two the 1.4 interpreter cannot
    # settle: every version of Interp.s dispatches them to "not implemented",
    # because they serve only the compiler and the runtime-only system drops
    # them. They are pinned instead by 1.3's native reimplementations, which
    # are disassembled in analysis/native/ (finding 19).
    #
    # IDSEARCH takes two VAR parameters and returns nothing.
    #
    # TREESEARCH is a *function* of three arguments returning an integer, so
    # (3, 1). The binary cannot distinguish this from (2, 0) -- both are a
    # net -1 word, both balance 117 procedures, and the balance test sees
    # only the net. The split comes from the procedure's own code: it pops
    # three parameter addresses and pushes a one-word result. This is the
    # limit of balance testing stated plainly, and the reason finding 14's
    # method needed a source to check it against.
    7: (2, 0),    # IDSEARCH(VAR idrec, VAR id)
    8: (3, 1),    # TREESEARCH(root, VAR node, VAR name) -> integer
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
    # Evaluation stack on entry and exit, after the fixed point below has
    # settled. Kept because a depth disagreement between two predecessors
    # is almost always a wrong callee signature somewhere upstream, and
    # these are what make that diagnosable.
    entry_stack: list = field(default_factory=list)
    exit_stack: list = field(default_factory=list)


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
    def __init__(self, param_words: int, callee_words, release: str = "1.1",
                 sets_only: bool = False):
        self.param_words = param_words
        self.callee_words = callee_words       # (kind, a, b) -> words popped
        self.release = release
        # True when nothing in this procedure touches a real, so a two-word
        # LDC cannot be a REAL constant and must be a set. See `ldc`.
        self.sets_only = sets_only

    @staticmethod
    def _members(words: list[int]) -> list[int]:
        return [16 * j + b for j, w in enumerate(words)
                for b in range(16) if w >> b & 1]

    def _set(self, words: list[int], under: str | None) -> str:
        """Render a set constant, by symbol name where that is warranted.

        `under` is whatever the LDC was pushed on top of, which is what
        says whether these numbers are symbol codes. Two shapes qualify,
        and nothing else does:

            LDO SY ; LDC ... ; ADJ n ; INN          `SY in <set>`
            LAO STATBEGSYS ; LDC ... ; ADJ n ; STM  the COMPINIT setup

        Restricting it this way matters. Plenty of set constants in the
        compiler are not symbol sets at all -- the scanner tests source
        characters against `{48..57}`, and COMPINIT indexes its
        standard-identifier table with two more -- and naming those would
        be worse than leaving them as numbers, not better.
        """
        ms = self._members(words)
        base = (under or "").lstrip("@").rstrip("^").split("<")[0].rstrip("^")
        if base == "SY" or base in SYMBOL_SET_NAMES:
            return "{" + ",".join(SYMBOLS.get(m, str(m)) for m in ms) + "}"
        return "{" + ",".join(str(m) for m in ms) + "}"

    def ldc(self, words: list[int], after=(), under=None) -> str:
        """Render a multi-word constant.

        A set's word j carries members 16j..16j+15, which is far more
        readable than the words -- `{19,20,21,22,23,24,25,26}` rather than
        `[$0000,$07F8]`. But LDC also loads REAL constants, which are two
        words, so members are only shown where the constant cannot be one:
        three words or more, a procedure with no real arithmetic in it, or
        -- for the one site where a procedure does both -- an instruction
        that consumes the value as a set before anything consumes it as a
        real. `after` is the rest of the block.
        """
        if len(words) == 2 and not self.sets_only:
            for i in after:
                if i.mnemonic in SET_OPS:
                    break
                if i.mnemonic in REAL_OPS:
                    return "[" + ",".join(f"${w:04X}" for w in words) + "]"
            else:
                return "[" + ",".join(f"${w:04X}" for w in words) + "]"
            return self._set(words, under)
        if len(words) >= 3 or self.sets_only:
            return self._set(words, under)
        return "[" + ",".join(f"${w:04X}" for w in words) + "]"

    def g(self, n: int) -> str:
        """Render a global by its recovered name where one is known."""
        return globalname(n, self.release) or f"G{n}"

    def run(self, b: Block, entry: list[str] | None = None) -> list[str]:
        st: list[str] = list(entry or [])
        out = b.stmts

        # Width in machine words of each slot, where known. A slot is one
        # value in this model but can be several words on the real stack --
        # LDM n pushes n. Only used to recognise a set's length word; None
        # means "one word, or unknown", which is the safe default.
        wid: list[int | None] = [None] * len(st)

        def push(v, w=None):
            st.append(v)
            wid.append(w)
            while len(wid) > len(st):
                wid.pop()

        def pop():
            if not st:
                # Underflow within a block is not automatically wrong -- a
                # block can consume a value its predecessor left -- but it
                # does mean this block's stack model is not self-contained,
                # and the arity solver must not treat it as a clean fit.
                b.underflow = True
                return "?"
            if wid:
                wid.pop()
            return st.pop()

        for k, i in enumerate(b.insns):
            m, o = i.mnemonic, i.operands
            try:
                if m in ("SLDC", "LDCI"):
                    # A UCSD set lives on the stack as its data words with a
                    # length word pushed on top, and the set operators pop
                    # that length. Modelling the data as one slot but the
                    # length as a second slot makes UNI/INT/DIF pair the
                    # wrong operands -- they union a set with a length.
                    # So when a constant equals the width of the slot just
                    # pushed, it is that slot's length word: absorb it, and
                    # a raw set becomes exactly one slot like every other
                    # value. Interp.s Op8B_INN and OpA0_ADJ both pop this
                    # length word first, which is what fixes the pairing.
                    if st and wid and wid[-1] == o[0]:
                        wid[-1] = None          # now a complete raw set
                    else:
                        push(str(o[0]))
                elif m == "LDCN":
                    st.append("nil")
                elif m in ("SLDL", "LDL"):
                    st.append(f"L{o[0]}")
                elif m in ("SLDO", "LDO"):
                    st.append(self.g(o[0]))
                elif m == "LOD":
                    st.append(f"I{o[0]},{o[1]}")
                elif m == "LLA":
                    st.append(f"@L{o[0]}")
                elif m == "LAO":
                    st.append(f"@{self.g(o[0])}")
                elif m == "LDA":
                    st.append(f"@I{o[0]},{o[1]}")
                elif m in ("SIND", "IND"):
                    a = pop()
                    st.append(f"{a}^" if o[0] == 0 else f"{a}^.f{o[0]}")
                elif m == "LDB":
                    idx, a = pop(), pop()
                    st.append(f"{a}^[{idx}]")
                elif m == "LDM":
                    # pops the source address (Interp.s OpBC_LDM), pushes
                    # o[0] words as one slot
                    push(f"{pop()}^<{o[0]}w>", o[0])
                elif m == "LSA":
                    st.append(repr(o[0].decode("ascii", "replace")))
                elif m == "LPA":
                    st.append("@" + repr(o[0].decode("ascii", "replace")))
                elif m == "LDC":
                    push(self.ldc(o[0], b.insns[k + 1:],
                                   st[-1] if st else None), len(o[0]))
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
                    v = pop(); out.append(f"{self.g(o[0])} := {v};")
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
                    # A store whose target came out as a bare literal means
                    # the stack model already went wrong upstream. Render it
                    # as the anomaly it is rather than as "8 := 2", which
                    # reads like a fact about the program.
                    if r.lstrip("-").isdigit():
                        out.append(f"{{ unmodelled packed store of {v} }}")
                    else:
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
                    # Render by name where the table has one (finding 17);
                    # the number stays for the handful it does not.
                    call = f"{CSP.get(n, 'CSP' + str(n))}({', '.join(args)})"
                    (st.append(call) if pushes else out.append(call + ";"))
                elif m in ("CXP", "CLP", "CGP", "CIP", "CBP"):
                    words, label, isfn = self.callee_words(m, o)
                    if words is None:
                        raise KeyError(label)
                    args = [pop() for _ in range(words)][::-1]
                    if isfn:
                        # A function call reserves two words for the result
                        # at the top of its own parameter area, and the
                        # caller pushes them as two literal zeros -- 154 of
                        # 154 function call sites across both releases, and
                        # 0 of 2961 procedure call sites
                        # (tools/probes/probe_funcresult.py). They are not
                        # arguments, so they do not belong in the argument
                        # list.
                        args = args[:-2]
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


def lift(seg, proc, cf, release: str = "1.1") -> list[Block]:
    """Lift one procedure to blocks of pseudo-Pascal.

    `release` selects the recovered name tables in `names.py`, which are
    SYSTEM.COMPILER's and nothing else. Pass "" when lifting any other
    codefile, or its globals will be labelled with the compiler's names --
    `probe_calibrate.py` lifts the GOTOXY samples that way.
    """
    """Lift one procedure. `cf` supplies callee parameter sizes."""
    body, _ = disassemble(seg.data, proc.enter_ic, proc.exit_ic, proc.jtab)
    ex, _ = sweep_exit(seg.data, proc.exit_ic, proc.jtab - 8, proc.jtab)
    stream = body + ex
    blocks = split_blocks(stream)

    segbynum = {s.seg_num: s for s in cf.segments}

    def named(segname, num):
        nm = procname(segname, num, release)
        return f"{segname}.{num}" + (f":{nm}" if nm else "")

    def callee_words(mnem, ops):
        if mnem == "CXP":
            s, n = ops
            if s == 0 and 0 not in segbynum:
                # Calling out of a user program into the operating system,
                # which is not in this codefile: the signature has to come
                # from OS_SIG, which was read off call sites.
                if n in OS_SIG:
                    name, words, is_fn = OS_SIG[n]
                    return words, name, is_fn
                return None, f"OS.{n} arity unknown", False
            tgt = segbynum.get(s)
            # Lifting the operating system itself. Segment 0 is present, so
            # its own attribute tables give the signature -- better evidence
            # than OS_SIG, and the standing rule is that the binary wins.
            # `probe_os_signatures.py` checks the two against each other.
            label = named(tgt.name, n) if tgt else f"seg{s}.{n}"
            if s == 0 and n in OS_SIG:
                label = f"{label}:{OS_SIG[n][0]}"
        else:
            # CLP/CIP/CGP/CBP all name a procedure in the *current* segment.
            # CGP is the lex-level-1 case (Language Reference IV-73: "Call
            # procedure number UB, which is at lexical level 1 and in the
            # same segment as the currently executing procedure"), which is
            # indistinguishable from segment 1 everywhere except DECLARAT.11,
            # the compiler's one cross-check: it pushes a four-word set and
            # calls CGP 1, and DECLARAT.1 takes eight bytes of parameters
            # where PASCALCO.1 takes four.
            tgt, n = seg, ops[0]
            label = named(seg.name, n)
        if tgt is None:
            return None, label, False
        p = next((x for x in tgt.procedures if x.number == n), None)
        if p is None:
            return None, label, False
        if p.is_native:
            # A native procedure has no p-code to read a signature out of,
            # so it has to be supplied. Both of the two that exist are
            # known from finding 19.
            sig = NATIVE_SIG.get((tgt.name, n))
            if sig is None:
                return None, label, False
            words, isfn, nm = sig
            return words, label if nm in label else f"{label} {nm}", isfn
        isfn = False
        for i in reversed(disassemble(tgt.data, p.enter_ic, p.exit_ic, p.jtab)[0]
                          + sweep_exit(tgt.data, p.exit_ic, p.jtab - 8, p.jtab)[0]):
            if i.mnemonic in ("RNP", "RBP"):
                isfn = i.operands[0] != 0
                break
        return p.param_size // 2, label, isfn

    # Real arithmetic anywhere in the procedure means a two-word LDC might
    # be a REAL constant rather than a set. Only nine such instructions
    # exist in the whole compiler -- it folds real constants at compile
    # time -- so almost every procedure gets the readable rendering.
    sets_only = not any(i.mnemonic in REAL_OPS
                        or (i.mnemonic in CMP_OPS and i.operands[0] == 2)
                        for i in stream)

    lifter = _Lifter(proc.param_size // 2, callee_words, release, sets_only)
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

    # --- successors and predecessors ------------------------------------
    byaddr = {b.start: b for b in blocks}
    for b in blocks:
        s = []
        if b.insns[-1].mnemonic == "XJP":
            o = b.insns[-1].operands
            s = [o[2], *o[3]]
        else:
            s = [t for t in (b.fallthrough, b.branch) if t is not None]
        b.succs = [t for t in s if t in byaddr]
    preds: dict[int, list[int]] = {b.start: [] for b in blocks}
    for b in blocks:
        for t in b.succs:
            preds[t].append(b.start)

    # --- entry stacks, by fixed point ------------------------------------
    #
    # An argument list can straddle a block boundary, so a block's entry
    # stack is whatever its predecessors leave behind. The earlier version
    # only carried a stack along a single-predecessor fallthrough edge,
    # which lost every argument list that spanned a join -- the bulk of the
    # "left on stack" residue.
    #
    # Merge rule at a join: identical stacks merge to themselves. Stacks of
    # equal depth whose slots differ merge slotwise to `phi(a, b)`, which is
    # a real value the program computes two ways and is worth showing.
    # Stacks of *different* depth are not reconciled -- that means the two
    # paths disagree about how much is live, so nothing can be said with
    # confidence and the block starts empty. Recorded rather than guessed.
    def merge(stacks):
        stacks = [s for s in stacks if s is not None]
        if not stacks:
            return []
        if len({len(s) for s in stacks}) != 1:
            return None                      # depth conflict: give up
        out = []
        for slots in zip(*stacks):
            uniq = list(dict.fromkeys(slots))
            out.append(uniq[0] if len(uniq) == 1
                       else "phi(" + ", ".join(uniq) + ")")
        return out

    entry_of: dict[int, list[str] | None] = {b.start: None for b in blocks}
    # None means "not yet known", which is different from "known to be
    # empty". Seeding these to [] instead makes every not-yet-visited
    # predecessor look like an empty stack, and the first join with a real
    # argument list on one side then reports a false depth conflict.
    exits: dict[int, list[str] | None] = {b.start: None for b in blocks}
    conflict: set[int] = set()

    # Iterate to a fixed point. Bounded because a p-code procedure's CFG is
    # small and the merge only ever widens; the cap is a guard against a
    # pathological loop, not an expected outcome.
    for _ in range(len(blocks) + 4):
        changed = False
        conflict = set()
        for b in blocks:
            e = ([] if b.start == blocks[0].start
                 else merge([exits[p] for p in preds[b.start]]))
            if e is None:
                conflict.add(b.start)
                e = []
            if e != entry_of[b.start]:
                entry_of[b.start] = e
                changed = True
            b.stmts = []
            b.cond = None
            b.incomplete = b.underflow = False
            exits[b.start] = lifter.run(b, list(e))
        if not changed:
            break

    for b in blocks:
        b.entry_stack = list(entry_of[b.start] or [])
        b.exit_stack = list(exits[b.start] or [])
    for b in blocks:
        if b.start in conflict:
            b.stmts.insert(0, "{ paths disagree on stack depth here }")
        residue = exits[b.start]
        if residue and not b.succs:
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
