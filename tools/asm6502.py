"""A minimal assembler for the Apple Pascal Assembler's source language.

Not a general 6502 assembler and not meant to become one. It exists so that
the reconstructed source of 1.3's two native procedures in `src/native/` can
be held against the bytes on the disk *here*, without an emulator -- the
acceptance test is still `SYSTEM.ASSMBLER` under AppleWin (finding 44e), but
a reconstruction that this cannot assemble to the right bytes will not
assemble to them there either.

It implements exactly the subset the two procedures use, and raises on
anything else, so silence is not the same as support.

Syntax, per the 1.3 manual Part II chapter 6:
  * a label starts in column 1; anything indented is an opcode or directive
  * `;` starts a comment
  * **the default number base is hexadecimal**; a trailing `.` means decimal;
    a constant must start with a digit, so $FF is written `0FF`
  * `"c"` is a character constant
  * `@` before a zero-page symbol is (indirect),Y
  * directives: .PROC .FUNC .END .EQU .BYTE .WORD .ASCII .TITLE

Relocation is the part that matters. A label defined inside the procedure is
*procedure-relative*: its value is its offset from the procedure's first
byte, and every operand that mentions one goes into the procedure-relative
relocation table, which the Linker uses to fix the operand up when the
segment is loaded. `.EQU` symbols are absolute and never relocate.

A label one procedure exports with `.DEF` and another imports with `.REF` is
*segment-relative* instead: the Linker resolves it to an offset within the
whole segment, so its final value depends on where the defining procedure
lands, which the assembler cannot know. `assemble_file(path, bases=...)`
supplies those procedure bases, exactly as the Linker does, and the
reference goes into the segment-relative table. APPLESTUFF needs this --
RANDOMIZE reseeds four bytes that live inside RANDOM.

Nothing here is base-relative or Interpreter-relative yet.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a2pascal.m6502 import (TABLE, IMP, ACC, IMM, ZP, ZPX, ZPY,
                            IZX, IZY, IND, ABS, ABX, ABY, REL)

# opcode for (mnemonic, mode)
ENCODE = {ent: op for op, ent in enumerate(TABLE) if ent is not None}
BRANCHES = {m for m, mode in ENCODE if mode == REL}


class AsmError(Exception):
    pass


@dataclass
class Proc:
    name: str
    kind: str                     # "PROC" or "FUNC"
    words: int                    # declared parameter words
    code: bytearray = field(default_factory=bytearray)
    # offset of every operand that mentions a label in this procedure
    reloc: list[int] = field(default_factory=list)
    # ... and of every operand that mentions another procedure's .DEF
    segreloc: list[int] = field(default_factory=list)
    # ... and of every operand written against .INTERP
    interpreloc: list[int] = field(default_factory=list)
    labels: dict[str, int] = field(default_factory=dict)
    defs: set[str] = field(default_factory=set)
    refs: set[str] = field(default_factory=set)
    enter: int = 0

    def define(self, label: str, off: int) -> None:
        """Bind a label. In the final pass it is already bound by the sizing
        pass, and must land on the same offset -- if it does not, something
        assembled to a different length the second time round."""
        if label in self.labels and self.labels[label] != off:
            raise AsmError(f"{label} moved from {self.labels[label]} to {off} "
                           f"between passes")
        self.labels[label] = off

    def image(self, relocseg: int = 0) -> bytes:
        """Code, relocation area and attribute table, as the Linker sees it.

        Layout is finding 44: low to high, the four relocation tables run
        interp, procedure, segment, base -- each its entries then its count,
        since a table's count is its *highest* word -- then ENTER IC, then
        the procedure-number/RELOCSEG word.
        """
        out = bytearray(self.code)
        if len(out) % 2:
            out.append(0)          # tables are word-aligned
        def w(v: int) -> None:
            out.extend((v & 0xFF, (v >> 8) & 0xFF))
        for off in self.interpreloc:           # interp, ascending
            w(len(out) - off)
        w(len(self.interpreloc))
        for off in self.reloc:                 # procedure, ascending
            w(len(out) - off)                  # self-relative, downward
        w(len(self.reloc))
        for off in self.segreloc:              # segment, ascending
            w(len(out) - off)
        w(len(self.segreloc))
        w(0)                                   # base
        w(len(out) - self.enter)               # ENTER IC
        # Procedure number 0 marks a native procedure; the high byte is
        # RELOCSEG, which the Linker fills in and nothing in the source
        # determines. PASCALCO's two come out 0; the library's come out 1.
        w(relocseg << 8)
        return bytes(out)


def _number(tok: str) -> int | None:
    if re.fullmatch(r"\d+\.", tok):
        return int(tok[:-1])
    if re.fullmatch(r"\d[0-9A-Fa-f]*", tok):
        return int(tok, 16)
    if re.fullmatch(r'".?"', tok):
        return ord(tok[1])
    return None


class Assembler:
    def __init__(self) -> None:
        self.procs: list[Proc] = []
        self.abs: dict[str, int] = {}     # .EQU symbols, never relocatable
        # .DEF symbol -> (defining procedure, offset within it)
        self.exported: dict[str, tuple[str, int]] = {}
        # procedure -> its offset within the linked segment, from the caller
        self.bases: dict[str, int] = {}
        # Labels carried from the sizing pass, so the final pass can resolve
        # forward references.
        self.seed: dict[str, dict[str, int]] = {}
        self.final = False

    # -- expressions ------------------------------------------------------
    def value(self, expr: str, p: Proc | None) -> tuple[int, str]:
        """Return (value, kind), kind being "", "proc" or "seg".

        "" is absolute -- a literal or an `.EQU`. "proc" is a label in this
        procedure, whose value is an offset from the procedure's first byte.
        "seg" is another procedure's `.DEF`, which the Linker resolves to an
        offset within the segment; `bases` supplies where each procedure
        lands, since nothing in the source says.
        """
        m = re.fullmatch(r"([^-+]+?)\s*(?:([-+])\s*(.+))?", expr.strip())
        if not m:
            raise AsmError(f"cannot parse expression {expr!r}")
        head, op, tail = m.group(1), m.group(2), m.group(3)
        n = _number(head)
        if head.upper() == ".INTERP":
            base, rel = 0, "interp"
        elif n is not None:
            base, rel = n, ""
        elif head in self.abs:
            base, rel = self.abs[head], ""
        elif p is not None and head in p.labels:
            base, rel = p.labels[head], "proc"
        elif p is not None and head in p.refs:
            if head not in self.exported:
                if self.final:
                    raise AsmError(f".REF {head} is not .DEF'd anywhere")
                base, rel = 0, "seg"
            else:
                owner, off = self.exported[head]
                base, rel = self.bases.get(owner, 0) + off, "seg"
        elif not self.final:
            # Sizing pass: a forward reference is a label we have not reached
            # yet, so assume the relocatable (and therefore wider) form.
            base, rel = 0, "proc"
        else:
            raise AsmError(f"undefined symbol {head!r}")
        if op:
            off = _number(tail)
            if off is None:
                off, off_rel = self.value(tail, p)
                if off_rel:
                    raise AsmError(f"two relocatable terms in {expr!r}")
            base = base + off if op == "+" else base - off
        return base, rel

    # -- one pass ---------------------------------------------------------
    def _pass(self, lines: list[str], final: bool) -> None:
        p: Proc | None = None
        self.procs = []
        self.final = final
        for lineno, raw in enumerate(lines, 1):
            line = raw.split(";")[0].rstrip()
            if not line.strip():
                continue
            label = ""
            if not line[0].isspace():
                parts = re.split(r"\s+", line, maxsplit=1)
                label, line = parts[0], parts[1] if len(parts) > 1 else ""
            line = line.strip()
            if not line:
                if p is None:
                    raise AsmError(f"line {lineno}: label outside a procedure")
                p.define(label, len(p.code))
                continue
            parts = re.split(r"\s+", line, maxsplit=1)
            op = parts[0].upper()
            arg = parts[1].strip() if len(parts) > 1 else ""
            try:
                if op.startswith("."):
                    self._directive(op, arg, label, p)
                    if op in (".PROC", ".FUNC"):
                        p = self.procs[-1]
                    continue
                if label:
                    if p is None:
                        raise AsmError("label outside a procedure")
                    p.define(label, len(p.code))
                if p is None:
                    raise AsmError("instruction outside a procedure")
                self._instruction(op, arg, p)
            except AsmError as e:
                raise AsmError(f"line {lineno}: {raw.rstrip()}\n    {e}") from None

    def _directive(self, op: str, arg: str, label: str,
                   p: Proc | None) -> None:
        if op in (".PROC", ".FUNC"):
            name, _, n = arg.partition(",")
            name = name.strip()
            self.procs.append(Proc(name, op[1:], int(n) if n.strip() else 0,
                                   labels=dict(self.seed.get(name, {}))))
            return
        if op == ".TITLE":
            return
        if op in (".DEF", ".REF"):
            if p is None:
                raise AsmError(f"{op} outside a procedure")
            for sym in arg.split(","):
                sym = sym.strip()
                if not sym:
                    raise AsmError(f"{op} with no symbol")
                (p.defs if op == ".DEF" else p.refs).add(sym)
            return
        if op == ".END":
            return
        if op == ".EQU":
            if not label:
                raise AsmError(".EQU without a label")
            self.abs[label] = self.value(arg, p)[0]
            return
        if p is None:
            raise AsmError(f"{op} outside a procedure")
        if label:
            p.define(label, len(p.code))
        if op == ".ASCII":
            if not (arg.startswith('"') and arg.endswith('"')):
                raise AsmError(".ASCII argument is not a quoted string")
            p.code.extend(arg[1:-1].encode("ascii"))
            return
        if op == ".BYTE":
            for t in arg.split(","):
                v, rel = self.value(t, p)
                if rel:
                    raise AsmError(".BYTE of a relocatable label")
                p.code.append(v & 0xFF)
            return
        if op == ".WORD":
            for t in arg.split(","):
                v, rel = self.value(t, p)
                if rel == "proc":
                    p.reloc.append(len(p.code))
                elif rel == "seg":
                    p.segreloc.append(len(p.code))
                elif rel == "interp":
                    p.interpreloc.append(len(p.code))
                p.code.extend((v & 0xFF, (v >> 8) & 0xFF))
            return
        raise AsmError(f"unsupported directive {op}")

    def _instruction(self, mnem: str, arg: str, p: Proc) -> None:
        here = len(p.code)
        mode, expr, index = self._mode(mnem, arg)
        if mode is REL:
            v, _rel = self.value(expr, p)
            d = v - (here + 2)
            if self.final and not -128 <= d <= 127:
                raise AsmError(f"branch out of range ({d})")
            p.code.extend((ENCODE[(mnem, REL)], d & 0xFF))
            return
        if mode in (IMP, ACC):
            p.code.append(ENCODE[(mnem, mode)])
            return
        v, rel = self.value(expr, p)
        if mode in (IZY, IZX):
            p.code.extend((ENCODE[(mnem, mode)], v & 0xFF))
            return
        if mode is IND:
            if rel == "proc":
                p.reloc.append(len(p.code) + 1)
            elif rel == "seg":
                p.segreloc.append(len(p.code) + 1)
            elif rel == "interp":
                p.interpreloc.append(len(p.code) + 1)
            p.code.extend((ENCODE[(mnem, IND)], v & 0xFF, (v >> 8) & 0xFF))
            return
        if mode is IMM:
            p.code.extend((ENCODE[(mnem, IMM)], v & 0xFF))
            return
        # A reference to a label in this procedure is always a 16-bit
        # relocatable operand, even when its value would fit in a byte:
        # the loader adds the procedure's base to it.
        wide = bool(rel) or not 0 <= v <= 0xFF
        forms = {("", True): ABS, ("", False): ZP,
                 ("X", True): ABX, ("X", False): ZPX,
                 ("Y", True): ABY, ("Y", False): ZPY}
        m = forms[(index, wide)]
        if not wide and (mnem, m) not in ENCODE:
            # STA and LDX have no zero page,Y; the assembler widens rather
            # than refusing, and the operand is then two bytes.
            wide = True
            m = forms[(index, True)]
        if (mnem, m) not in ENCODE:
            raise AsmError(f"{mnem} has no {'absolute' if wide else 'zero page'}"
                           f"{',' + index if index else ''} form")
        if wide and rel == "proc":
            p.reloc.append(len(p.code) + 1)
        elif wide and rel == "seg":
            p.segreloc.append(len(p.code) + 1)
        elif wide and rel == "interp":
            p.interpreloc.append(len(p.code) + 1)
        p.code.append(ENCODE[(mnem, m)])
        if wide:
            p.code.extend((v & 0xFF, (v >> 8) & 0xFF))
        else:
            p.code.append(v & 0xFF)

    def _mode(self, mnem: str, arg: str):
        if mnem in BRANCHES:
            return REL, arg, ""
        if not arg:
            return IMP, "", ""
        if arg.upper() == "A":
            return ACC, "", ""
        if arg.startswith("#"):
            return IMM, arg[1:], ""
        index = ""
        m = re.fullmatch(r"(.*?),\s*([XY])", arg, re.I)
        if m:
            arg, index = m.group(1).strip(), m.group(2).upper()
        if arg.startswith("@"):
            if index == "Y":
                return IZY, arg[1:], ""
            if index == "X":
                return IZX, arg[1:], ""
            if mnem == "JMP":
                return IND, arg[1:], ""
            raise AsmError("@sym is (zero page),Y, (zero page,X) or JMP @")
        
        return None, arg, index

    def assemble(self, text: str) -> list[Proc]:
        lines = text.splitlines()
        self._pass(lines, final=False)      # sizing: fixes every label
        self.seed = {pr.name: dict(pr.labels) for pr in self.procs}
        # What each procedure exports is only known once it has been sized.
        self.exported = {}
        for pr in self.procs:
            for sym in pr.defs:
                if sym not in pr.labels:
                    raise AsmError(f"{pr.name}: .DEF {sym} is never defined")
                self.exported[sym] = (pr.name, pr.labels[sym])
        self._pass(lines, final=True)       # Proc.define re-checks each one
        return self.procs


def assemble_file(path: Path,
                  bases: dict[str, int] | None = None) -> list[Proc]:
    """Assemble, and link at `bases` -- procedure name to segment offset.

    Only `.REF` operands need a base: everything else is either absolute or
    procedure-relative, and neither depends on where the procedure lands.
    """
    a = Assembler()
    a.bases = dict(bases or {})
    return a.assemble(path.read_text())


def main() -> None:
    for arg in sys.argv[1:]:
        for pr in assemble_file(Path(arg)):
            img = pr.image()
            print(f"{pr.kind} {pr.name},{pr.words}: {len(pr.code)} bytes of "
                  f"code, {len(pr.reloc)} procedure-relative, "
                  f"{len(pr.segreloc)} segment-relative and "
                  f"{len(pr.interpreloc)} Interpreter-relative relocations, "
                  f"{len(img)} bytes linked")


if __name__ == "__main__":
    main()
