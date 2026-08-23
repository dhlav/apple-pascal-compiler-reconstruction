"""OSPROC43 against both operating systems and both compilers (finding 89).

Finding 79b established that the compiler names the operating system by
declaring 42 unresolved FORWARDs and calling the 43rd, and left what the
43rd *does* open. It is `FILEPROC.8`, the file-title normaliser, and this
re-derives the whole chain from the four binaries rather than trusting the
write-up:

  1. `SYSTEM.PASCAL`'s procedure 43 is a seven-instruction forwarder into
     `FILEPROC`'s four-arm dispatcher, arm 4;
  2. `FILEPROC.8` deletes blanks, honours a trailing `'.'`, holds a
     `[...]` size specification aside, leaves a volume name alone and
     otherwise upshifts and appends `'.TEXT'` or `'.CODE'`;
  3. 1.3 adds the control-character clamp and 1.1 has not got it;
  4. every `CXP 0,43` in `SYSTEM.COMPILER` pushes an address, a 0/1 flag
     and a length -- and there are two in 1.1 and three in 1.3, the extra
     one being the listing-file title 1.3's COMPINIT prompts for
     (finding 88a).

Each check is written so the binary can fail it: an operand, a count or a
literal, never a property of our own text.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from a2pascal.disk import PascalDisk
from a2pascal.codefile import CodeFile
from a2pascal.pcode import disassemble

ROOT = Path(__file__).resolve().parents[2]
OS_DISKS = (("1.1", "UCSD Pascal 1.1_1.dsk"),
            ("1.3", "Apple II Pascal 1.3 APPLE1_ 680-0283-A.dsk"))
CO_DISKS = (("1.1", "Apple II Pascal 1.1 APPLE2_ 680-0005-01.dsk"),
            ("1.3", "Apple II Pascal 1.3 APPLE2_ 680-0284-A.dsk"))

# The forwarder, in full. `4` selects FILEPROC.1's fourth arm; @G4 and G294
# are procedure 43's own local buffer, which that arm never reads -- they
# are there because the dispatcher's signature is shared with arms 1..3.
FORWARDER = [("SLDC", [4]), ("LAO", [4]), ("SLDO", [3]), ("SLDO", [2]),
             ("LDO", [294]), ("SLDO", [1]), ("CXP", [6, 1])]

fail = []


def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what)
    if not ok:
        fail.append(what)


def body(seg, p):
    return disassemble(seg.data, p.enter_ic, p.exit_ic, p.jtab)[0]


def segment(cf, name):
    for s in cf.segments:
        if s.name.startswith(name):
            return s
    raise SystemExit(f"no segment {name}")


def procedure(seg, n):
    for p in seg.procedures:
        if p.number == n:
            return p
    raise SystemExit(f"no procedure {n} in {seg.name}")


def load(fname, member):
    disk = PascalDisk.from_file(ROOT / "evidence" / "disks" / fname)
    e = disk.find(member)
    return CodeFile(disk.read_blocks(e.first_block, e.blocks))


def opcodes(ins):
    return [(i.mnemonic, list(i.operands)) for i in ins]


def literals(ins):
    return {i.operands[0] for i in ins if i.mnemonic == "LSA"}


for rel, fname in OS_DISKS:
    print(f"=== SYSTEM.PASCAL {rel} ===")
    cf = load(fname, "SYSTEM.PASCAL")
    sys0 = segment(cf, "PASCALSY")
    p43 = procedure(sys0, 43)
    check(p43.param_size == 6, f"{rel}: procedure 43 takes three words")
    check(opcodes(body(sys0, p43)) == FORWARDER,
          f"{rel}: procedure 43 is the forwarder into FILEPROC arm 4")

    fp = segment(cf, "FILEPROC")
    disp = opcodes(body(fp, procedure(fp, 1)))
    check(procedure(fp, 1).param_size == 12,
          f"{rel}: FILEPROC.1 takes the six-word shared signature")
    check(any(m in ("CLP", "CGP") and o == [8] for m, o in disp),
          f"{rel}: FILEPROC.1 calls procedure 8")

    p8 = procedure(fp, 8)
    ins = body(fp, p8)
    ops = opcodes(ins)
    lits = literals(ins)
    check(p8.param_size == 6, f"{rel}: FILEPROC.8 takes S, the flag and N")
    check({b" ", b"[", b".TEXT", b".CODE"} <= lits,
          f"{rel}: FILEPROC.8 carries ' ', '[', '.TEXT' and '.CODE'")
    check(("SLDC", [46]) in ops and ("SLDC", [58]) in ops,
          f"{rel}: FILEPROC.8 tests for '.' and ':'")
    check(any(ops[k] == ("SLDC", [32]) and ops[k + 1] == ("SBI", [])
              for k in range(len(ops) - 1)),
          f"{rel}: FILEPROC.8 upshifts with ORD(c) - 32")
    # The length guard is what makes N the caller's *declared* length:
    # ... ADI ; SLDL 1 ; SLDC 5 ; SBI ; LEQI -- room for five more.
    check(any(ops[k:k + 4] == [("SLDL", [1]), ("SLDC", [5]),
                               ("SBI", []), ("LEQI", [])]
              for k in range(len(ops))),
          f"{rel}: the suffix is appended only if N leaves five characters")
    clamp = any(ops[k:k + 2] == [("SLDC", [63]), ("STB", [])]
                for k in range(len(ops)))
    check(clamp == (rel == "1.3"),
          f"{rel}: control characters become '?'"
          + ("" if rel == "1.3" else " -- absent, as 1.1 has it"))

for rel, fname in CO_DISKS:
    print(f"=== SYSTEM.COMPILER {rel} ===")
    cf = load(fname, "SYSTEM.COMPILER")
    sites = []
    for seg in cf.segments:
        for p in getattr(seg, "pcode_procedures", seg.procedures):
            ops = opcodes(body(seg, p))
            for k, (m, o) in enumerate(ops):
                if m == "CXP" and o == [0, 43]:
                    sites.append((seg.name, p.number, ops[k - 3:k]))
    for name, num, push in sites:
        print(f"       {name}.{num}: "
              + " ; ".join(f"{m}{o}" for m, o in push))
    check(len(sites) == (3 if rel == "1.3" else 2),
          f"{rel}: {'three' if rel == '1.3' else 'two'} call sites")
    check(all(push[0][0] in ("LAO", "LLA") for _, _, push in sites),
          f"{rel}: every site passes a VAR string")
    check(all(push[1] == ("SLDC", [0]) or push[1] == ("SLDC", [1])
              for _, _, push in sites),
          f"{rel}: every site passes a 0/1 suffix flag")
    check(all(push[2][0] in ("SLDC", "LDCI") for _, _, push in sites),
          f"{rel}: every site passes a constant length")

print()
if fail:
    raise SystemExit(f"{len(fail)} check(s) failed")
print("OSPROC43: every check passed")
