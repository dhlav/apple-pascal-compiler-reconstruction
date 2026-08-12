"""Recover the compiler's global data layout from p-code global accesses.

Every segment of a UCSD program shares one global data area: the activation
record of the outermost block (here PASCALCO procedure 1, lex level 0). Four
instructions address it, all by WORD offset:

    SLDO n   load global word n            (short form, n = 1..16)
    LDO  b   load global word b
    SRO  b   store global word b
    LAO  b   push the ADDRESS of global word b

A scalar word variable shows up as LDO/SRO/SLDO traffic at a single offset.
Anything larger -- an array, record, string, set, file buffer -- is reached
by taking its address with LAO and then indexing or dereferencing, so the
instructions that FOLLOW an LAO are what reveal an object's shape and size.
This module collects both, and turns the address-taken sites into typed
evidence.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from .pcode import disassemble, sweep_exit, Insn

# How far past an LAO to look for the instruction that reveals its use.
LOOKAHEAD = 8


@dataclass
class Access:
    version: str
    segment: str
    proc: int
    addr: int
    kind: str            # "read" | "write" | "addr"
    mnemonic: str


@dataclass
class Evidence:
    """One inference about an object's shape, drawn from an LAO use site."""
    kind: str            # "array" | "deref" | "block" | "arg" | "setop" | "cmp"
    detail: str
    words: int | None    # size in words, when the instruction implies one
    site: str


@dataclass
class GlobalVar:
    offset: int
    reads: int = 0
    writes: int = 0
    addr_taken: int = 0
    touched_by: set = field(default_factory=set)
    evidence: list = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.reads + self.writes + self.addr_taken

    @property
    def scalar_only(self) -> bool:
        return self.addr_taken == 0

    def best_size(self) -> int | None:
        """Largest directly-evidenced size in words, if any."""
        sizes = [e.words for e in self.evidence if e.words]
        return max(sizes) if sizes else None


def _classify_use(stream: list[Insn], k: int, site: str) -> list[Evidence]:
    """Interpret what happens to the address pushed by stream[k] (an LAO)."""
    out = []
    for j in range(k + 1, min(k + 1 + LOOKAHEAD, len(stream))):
        ins = stream[j]
        m = ins.mnemonic
        if m == "IXA":
            out.append(Evidence("array", f"IXA element={ins.operands[0]} word(s)",
                                None, site))
            break
        if m in ("SIND", "IND"):
            out.append(Evidence("deref", f"{m} {ins.operands[0]}", None, site))
            break
        if m in ("LDB", "STB"):
            out.append(Evidence("deref", f"{m} (byte)", None, site))
            break
        if m == "MOV":
            out.append(Evidence("block", f"MOV {ins.operands[0]} word(s)",
                                ins.operands[0], site))
            break
        if m in ("LDM", "STM"):
            out.append(Evidence("block", f"{m} {ins.operands[0]} word(s)",
                                ins.operands[0], site))
            break
        if m in ("EQU", "NEQ", "LES", "LEQ", "GRT", "GEQ"):
            t = ins.operands[0]
            n = ins.operands[1] if len(ins.operands) > 1 else None
            # type 10 = byte array, length in BYTES; type 12 = record, in words
            words = None if n is None else (-(-n // 2) if t == 10 else n)
            out.append(Evidence("cmp", f"{m} type={'BYTE' if t == 10 else 'WORD'}"
                                + (f" len={n}" if n else ""), words, site))
            break
        if m in ("CXP", "CLP", "CGP", "CIP", "CBP", "CSP"):
            out.append(Evidence("arg", f"passed to {ins.text}", None, site))
            break
        if m in ("UNI", "INT", "DIF", "SRS", "INN", "SGS"):
            out.append(Evidence("setop", m, None, site))
            break
        if m == "STO":
            out.append(Evidence("deref", "STO (indirect store)", None, site))
            break
    return out


def collect(cf, version: str) -> tuple[dict[int, GlobalVar], list[Access], int | None]:
    """Walk every p-code procedure and tabulate global accesses.

    Returns (offset -> GlobalVar, all accesses, global area size in words).
    """
    table: dict[int, GlobalVar] = {}
    accesses: list[Access] = []

    def var(off: int) -> GlobalVar:
        return table.setdefault(off, GlobalVar(off))

    outer_words = None
    for seg in cf.segments:
        for p in seg.procedures:
            if p.lex_level == 0 and not p.is_native:
                outer_words = p.data_size // 2

    for seg in cf.segments:
        for p in seg.pcode_procedures:
            body, _ = disassemble(seg.data, p.enter_ic, p.exit_ic, p.jtab)
            ex, _ = sweep_exit(seg.data, p.exit_ic, p.jtab - 8, p.jtab)
            stream = body + ex
            where = f"{seg.name}.{p.number}"
            for k, ins in enumerate(stream):
                m = ins.mnemonic
                if m in ("LDO", "SLDO"):
                    off, kind = ins.operands[0], "read"
                elif m == "SRO":
                    off, kind = ins.operands[0], "write"
                elif m == "LAO":
                    off, kind = ins.operands[0], "addr"
                else:
                    continue
                v = var(off)
                v.touched_by.add(where)
                site = f"{where}@${ins.addr:04X}"
                if kind == "read":
                    v.reads += 1
                elif kind == "write":
                    v.writes += 1
                else:
                    v.addr_taken += 1
                    v.evidence.extend(_classify_use(stream, k, site))
                accesses.append(Access(version, seg.name, p.number, ins.addr,
                                       kind, m))
    return table, accesses, outer_words


def infer_objects(table: dict[int, GlobalVar], area_words: int | None) -> list[dict]:
    """Group offsets into candidate objects.

    An offset whose address is never taken and that is only ever read or
    written as a whole word is a scalar. An offset whose address IS taken
    starts an aggregate; its extent is bounded above by the next touched
    offset, and sometimes pinned exactly by MOV/LDM/STM evidence.
    """
    offsets = sorted(table)
    out = []
    for i, off in enumerate(offsets):
        v = table[off]
        nxt = offsets[i + 1] if i + 1 < len(offsets) else area_words
        gap = (nxt - off) if nxt is not None else None
        evidenced = v.best_size()
        by_ref_only = (v.addr_taken > 0
                       and all(e.kind == "arg" for e in v.evidence)
                       and bool(v.evidence))
        if v.scalar_only:
            kind, size, how = "scalar", 1, "word access only"
        elif evidenced:
            size, how = evidenced, "sized by MOV/LDM/STM/compare"
            if gap and evidenced > gap:
                # The object is copied whole but its interior words are also
                # loaded and stored individually: a record whose fields are
                # addressed directly. Keep the evidenced size; the overlap is
                # the finding, not an error.
                kind = "record"
                how += (f"; spans {evidenced} words but words "
                        f"{off + 1}..{off + evidenced - 1} are also addressed "
                        f"individually, so these are its fields")
            else:
                kind = "aggregate"
        elif by_ref_only and gap == 1:
            kind, size, how = "scalar-byref", 1, "address taken only to pass it"
        elif gap:
            kind, size, how = "aggregate", gap, "bounded by next touched offset"
        else:
            kind, size, how = "aggregate", None, "unbounded"
        out.append({
            "offset": off, "kind": kind, "words": size, "sizing": how,
            "gap_to_next": gap, "reads": v.reads, "writes": v.writes,
            "addr_taken": v.addr_taken, "users": len(v.touched_by),
            "evidence": v.evidence,
        })
    return out
