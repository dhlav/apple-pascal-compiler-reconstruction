"""Recover the compiler's standard type descriptors and record layouts.

COMPINIT has two initialisation procedures that between them pin down more
of the compiler's own data structures than anything else in the binary:

  * one builds the standard *type* descriptors -- the `structure` records
    for INTEGER, REAL, CHAR, BOOLEAN, STRING, TEXT and so on -- by
    `NEW`ing a record and storing constants into its fields;
  * the next enters the standard *identifiers*, and for each one stores a
    name with `LPA 'INTEGER '` and then the type pointer it refers to.

The second is what makes the first readable. A descriptor on its own is an
anonymous bag of numbers; the identifier table says which global holds it.
So this walks both, in both releases, and prints:

  1. name -> global, from the identifier table (`LPA` then `INC 6`);
  2. every field stored into each standard descriptor, so the `structure`
     record's layout and the `structform` enumeration can be read off.

Everything here is pattern matching over the decoded instruction stream --
no hand-entered addresses beyond finding COMPINIT -- so it re-runs against
either disk and fails loudly if the shape is not there.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.pcode import disassemble

ROOT = Path(__file__).resolve().parents[2]
DISKS = (("1.1", "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk"),
         ("1.3", "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk"))

LOADG = ("LDO", "SLDO")        # load global word
ADDRG = ("LAO",)               # address of global
PUSHK = ("SLDC", "LDCI")       # push an integer constant


def gnum(i):
    return i.operands[-1]


def scan_idents(body):
    """name -> global holding its type pointer, from `LPA` ... `INC 6`."""
    out = []
    name = None
    for k, i in enumerate(body):
        if i.mnemonic == "LPA":
            name = i.operands[0].decode("ascii", "replace").rstrip()
        elif (i.mnemonic == "INC" and i.operands[0] == 6 and name
                and k + 1 < len(body) and body[k + 1].mnemonic in LOADG):
            out.append((name, gnum(body[k + 1])))
            name = None
    return out


def scan_descriptors(body):
    """global -> [(field offset, value)] for each NEWed standard descriptor.

    The shape the compiler emits is always the same:

        LAO g / SLDC n / CSP NEW      allocate n words into global g
        LDO g / STL 1                 keep the pointer in a local
        SLDL 1 [/ INC k] / <push> / STO   store one field

    so tracking the most recent NEWed global and reading off the INC/STO
    pairs recovers the whole record.
    """
    recs: dict[int, list] = {}
    order: list[int] = []
    cur = None
    k = 0
    while k < len(body):
        i = body[k]
        if (i.mnemonic in ADDRG + ("LLA",) and k + 2 < len(body)
                and body[k + 1].mnemonic in PUSHK
                and body[k + 2].mnemonic == "CSP"
                and body[k + 2].operands[0] == 1):
            if i.mnemonic == "LLA":
                # allocated into a local, not a standard descriptor: stop
                # attributing stores to the previous global.
                cur = None
                k += 3
                continue
            cur = gnum(i)
            recs.setdefault(cur, [])
            if cur not in order:
                order.append(cur)
            recs[cur].append(("words", body[k + 1].operands[0]))
            k += 3
            continue
        if cur is not None and i.mnemonic in ("SLDL", "LDL"):
            j = k + 1
            off = 0
            if j < len(body) and body[j].mnemonic == "INC":
                off = body[j].operands[0]
                j += 1
            # a single-instruction value followed by STO
            if j + 1 < len(body) and body[j + 1].mnemonic == "STO":
                v = body[j]
                if v.mnemonic in PUSHK:
                    recs[cur].append((off, v.operands[0]))
                elif v.mnemonic in LOADG:
                    recs[cur].append((off, f"G{gnum(v)}"))
                elif v.mnemonic == "LDCN":
                    recs[cur].append((off, "nil"))
                k = j + 2
                continue
        k += 1
    return order, recs


for rel, fname in DISKS:
    d = PascalDisk.from_file(ROOT / "evidence" / "disks" / fname)
    e = d.find("SYSTEM.COMPILER")
    cf = CodeFile(d.read_blocks(e.first_block, e.blocks))
    seg = cf.segment("COMPINIT")

    idents, descriptors, order = [], {}, []
    for p in seg.pcode_procedures:
        body = disassemble(seg.data, p.enter_ic, p.exit_ic, p.jtab)[0]
        found = scan_idents(body)
        if found:
            idents += found
        o, r = scan_descriptors(body)
        for g in o:
            if g not in descriptors:
                order.append(g)
            descriptors.setdefault(g, []).extend(r[g])

    byglobal: dict[int, str] = {}
    for name, g in idents:
        byglobal.setdefault(g, name)

    print(f"=== {rel} ===")
    print("standard identifiers -> type-pointer global")
    for name, g in idents:
        print(f"  {name:<10} G{g}")
    print("\nstandard type descriptors (offset: value)")
    for g in order:
        fields = descriptors[g]
        if not any(isinstance(o, int) for o, _ in fields):
            continue        # allocated but filled in elsewhere
        label = byglobal.get(g, "-")
        body = "  ".join(f"w{o}={v}" if o != "words" else f"[{v}w]"
                         for o, v in fields)
        print(f"  G{g:<4}{label:<12}{body}")
    print()
