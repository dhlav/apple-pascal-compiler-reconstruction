"""Build and install Apple Pascal exec files (finding 124).

An exec file is a plain UCSD `.TEXT` file whose content is the keystroke
sequence a human would type at the Command level, framed by a `%`
terminator character: `%` + <keystrokes, with each RETURN a real line
break> + `%%` (manual, "Making and Using Exec Files"). `X(ecute` with
`EXEC/<filename>` then replays it -- the OS reads it into the type-ahead
buffer itself, the same path a human's own keystrokes go through.

Building the file directly here, rather than recording it live through
`M(ake`, sidesteps two real problems the emu*.ps1 scripts have fought
since the hard-disk layout was introduced:

  * SendKeys races against SYSTEM.ASSMBLER's/SYSTEM.LINKER's own slow
    disk load, which has repeatedly eaten characters typed right behind
    the command letter (`emuassemble.ps1`/`emulink.ps1`'s own module
    notes). A pre-written exec file has nothing to race -- the OS reads
    its own keystrokes off disk at its own pace, immune to real-world
    SendKeys timing entirely.
  * `%`, the exec terminator itself, is one of the seven characters
    .NET's `SendKeys` treats as modifier/grouping syntax rather than a
    literal character -- `emukeys.ps1` silently sent no terminator at
    all before that bug was fixed. Authoring the file's bytes directly
    here never touches SendKeys, so it never hits that class of bug.

Confirmed end to end against a real compile (finding 124): recorded and
replayed, `SET40COL`'s four procedures came back `params`/`data`-exact,
identical to a live, hand-typed compile.

    python tools/execfile.py build/disks/HD1.hdv GOCOMP \
        "CSYSHD:NAME.TEXT{ENTER}SYSHD:NAME.CODE[*]{ENTER}{ENTER}"

The keystroke string uses the same `{ENTER}` convention as
`emukeys.ps1`'s own `-Keys` -- no other `{TOKEN}` is supported yet;
anything else raises rather than silently write a wrong exec file, since
CONTROL-@/CONTROL-S/CONTROL-F are documented as unrecordable and nothing
else has been tried against a real exec file.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a2pascal.textfile import encode_text  # noqa: E402

CP2 = Path(r"C:\CiderPress2\cp2.exe")

_TOKEN = re.compile(r"\{([^}]+)\}")


def keys_to_exec_text(keys: str) -> str:
    """Convert an `emukeys.ps1`-style keystroke string to exec-file content.

    `{ENTER}` becomes a real line break (encode_text turns it into a CR
    the way every other line in a .TEXT file gets one). Any other
    `{TOKEN}` raises -- see the module docstring.
    """
    out: list[str] = []
    pos = 0
    for m in _TOKEN.finditer(keys):
        out.append(keys[pos:m.start()])
        tok = m.group(1).upper()
        if tok != "ENTER":
            raise ValueError(
                f"keys_to_exec_text: unsupported token {{{tok}}} -- only "
                "{ENTER} is known to translate correctly into an exec "
                "file; add and verify support before using another one")
        out.append("\n")
        pos = m.end()
    out.append(keys[pos:])
    return "".join(out)


def build_exec_file(keys: str) -> bytes:
    """The full on-disk bytes of an exec file for `keys`."""
    content = "%" + keys_to_exec_text(keys) + "%%"
    return encode_text(content)


def install_exec_file(hdv: Path, name: str, keys: str) -> None:
    """Write `NAME.TEXT` as an exec file on `hdv`, replacing any old copy.

    `name` is an 8-significant-character Pascal filename with no
    extension -- the CLAUDE.md 8-char-collision gotcha applies here too,
    same as any other file on the volume.
    """
    if not CP2.exists():
        raise SystemExit(f"{CP2} not found -- CiderPress II is required")
    data = build_exec_file(keys)
    # cp2's "add --no-strip-ext --strip-paths" uses the local filename
    # verbatim as the on-disk name, so the temp file must already be
    # named the way it should land in the catalog.
    tmp = hdv.parent / f"{name}.TEXT"
    tmp.write_bytes(data)
    try:
        # Delete first: cp2's own "add" does not overwrite an existing
        # file of the same name, and this is called fresh on every
        # emu*.ps1 invocation, not just once.
        subprocess.run([str(CP2), "delete", str(hdv), f"{name}.TEXT"],
                       capture_output=True)  # nonzero if it doesn't exist yet -- fine
        r = subprocess.run([str(CP2), "add", "--raw", "--no-strip-ext",
                            "--strip-paths", str(hdv), str(tmp)],
                           capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f"cp2 add {name}.TEXT failed:\n{r.stdout}{r.stderr}")
        r = subprocess.run([str(CP2), "set-attr", str(hdv), "type=PTX",
                            f"{name}.TEXT"],
                           capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f"cp2 set-attr {name}.TEXT failed:\n"
                             f"{r.stdout}{r.stderr}")
    finally:
        tmp.unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("hdv", type=Path)
    ap.add_argument("name", help="exec file name, no extension, <=8 "
                                 "significant characters")
    ap.add_argument("keys", help="emukeys.ps1-style keystroke string, "
                                 "{ENTER} for RETURN")
    args = ap.parse_args()
    install_exec_file(args.hdv, args.name, args.keys)
    print(f"{args.name}.TEXT installed on {args.hdv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
