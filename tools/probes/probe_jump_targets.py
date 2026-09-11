"""Can the comparison see a jump that goes to the wrong place?

`oscmp` calls two procedures identical when their instruction listings
match. Until finding 252 those listings had every absolute address blanked
out, on the reasoning recorded in `procbuild.strip_targets`: that a jump to
the wrong place would show up anyway, because the instructions after it
would land in the wrong order.

That reasoning is false. A statement written one nesting level too deep
emits the same instructions in the same order and moves only a jump's
destination -- `ASSEMBLE.33` did exactly that and was scored exact, and
three procedures of `128K.PASCAL` had been scored exact the same way.

So this is a discrimination check, and it is built to fail if the fix is
ever undone: it takes a real procedure of Apple's, moves ONE forward jump
to the next instruction boundary, and requires that

  * the old blanking comparison still calls the mutant identical, and
  * the comparison `oscmp` uses now does not.

If the first stops holding, the mutation stopped being target-only and the
probe is no longer testing what it claims. If the second stops holding, the
hole is back.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from a2pascal.pcode import decode                             # noqa: E402
from oscmp import shipped_codefile, procedures                # noqa: E402
from procbuild import listing, strip_targets, relative_targets  # noqa: E402

TARGET = "SYSTEM.ASSMBLER"
fail = []


def check(ok: bool, label: str) -> None:
    print(("  ok   " if ok else "  FAIL ") + label)
    if not ok:
        fail.append(label)


def blind(seg, p):
    return [strip_targets(t) for t in listing(seg, p)]


def mutate(seg, p):
    """Move one forward jump on by a single instruction. (name, seg') or None.

    A forward SB displacement is self-relative to the byte after it, so
    adding the length of the instruction it lands on retargets it to the
    next one -- the same one-instruction slip a misplaced BEGIN/END makes.
    """
    data = seg.data
    ic = p.enter_ic
    while ic < p.exit_ic:
        i = decode(data, ic, p.jtab)
        if i.mnemonic in ("UJP", "FJP") and i.operands and i.operands[0] > 0:
            disp_at = ic + 1
            tgt = disp_at + 1 + data[disp_at]
            if tgt < p.exit_ic:
                grown = data[disp_at] + decode(data, tgt, p.jtab).length
                if grown < 128:
                    out = bytearray(data)
                    out[disp_at] = grown
                    return SimpleNamespace(data=bytes(out), name=seg.name)
        ic += i.length
    return None


def main() -> int:
    cf = shipped_codefile(TARGET)
    procs = procedures(cf)

    print("=== a procedure compares equal to itself ===")
    seg, p = procs["ASSEMBLE.33"]
    check(relative_targets(seg, p) == relative_targets(seg, p),
          "ASSEMBLE.33 against itself")

    print("=== one jump moved on by one instruction ===")
    tried = 0
    for key in ("ASSEMBLE.33", "PROCEND.1", "TLA.1", "ASSEMBLE.12"):
        if key not in procs:
            continue
        seg, p = procs[key]
        m = mutate(seg, p)
        if m is None:
            continue
        tried += 1
        check(blind(m, p) == blind(seg, p),
              f"{key}: the mutation is target-only -- blanked listings agree")
        check(relative_targets(m, p) != relative_targets(seg, p),
              f"{key}: the comparison oscmp uses now rejects it")
    check(tried >= 3, f"mutated {tried} procedures, wanted at least 3")

    if fail:
        print(f"\njump targets: {len(fail)} check(s) failed")
        return 1
    print("\njump-targets-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
