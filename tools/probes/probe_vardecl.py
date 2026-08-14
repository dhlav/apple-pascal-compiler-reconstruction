"""Does the compiler allocate a VAR declaration list backwards?

`VARDECLARATION` in the UCSD II.0 source (decpart.b.text) collects the
identifiers of one declaration by **prepending** them to a list:

    NEW(LCP); WITH LCP^ DO BEGIN NAME := ID; NEXT := NXT; ... END;
    ENTERID(LCP); NXT := LCP;

and then assigns addresses by walking that list:

    WHILE NXT <> NIL DO
      WITH NXT^ DO BEGIN VADDR := LC; LC := LC + LSIZE; NXT := NEXT END;

so the last identifier written gets the lowest address. `VAR LC,IC:
ADDRRANGE` allocates IC first.

That is a claim about Apple's binary, not just about the source, and the
binary can refute it: for every declaration in II.0 where two or more of
the identifiers are names this project has independently recovered in
Apple's global map, their Apple offsets must come out in **reverse**
declaration order. Recovering those names never used declaration order --
they came from behaviour, from error numbers, and from the listing
columns -- so this is a real prediction.

The eight `SETOFSYS` globals are the sharpest case: one declaration, eight
identifiers, and finding 26c assigned every one of them by the error its
guard raises. If that assignment were wrong, the eight would not come out
in exactly reverse order.

Finding 33.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import vardecl
from a2pascal.names import GLOBALS_11, GLOBALS_13


def main() -> int:
    bad, checked, groups = [], 0, 0
    for rel, glob in (("1.1", GLOBALS_11), ("1.3", GLOBALS_13)):
        where = {name: off for off, name in glob.items()}
        for ids, _typ in vardecl.var_block():
            known = [(i, where[i]) for i in ids if i in where]
            if len(known) < 2:
                continue
            groups += 1
            checked += len(known)
            offs = [o for _n, o in known]
            if offs != sorted(offs, reverse=True):
                bad.append(
                    f"{rel}: `VAR {', '.join(ids)}` -- Apple allocates "
                    + ", ".join(f"{n}={o}" for n, o in known)
                    + ", which is not reverse declaration order")
        print(f"{rel}: every multi-name declaration with 2+ recovered names "
              f"allocates in reverse")

    if bad:
        print("\n".join(bad))
        return 1
    print(f"{groups} declaration groups, {checked} names, all reversed")
    print("vardecl-ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
