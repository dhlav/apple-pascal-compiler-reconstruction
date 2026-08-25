# Acceptance runs

What Apple's own tools produced, kept as it came off the emulator.

Everything else in this repository is either evidence (Apple's shipped
media, never modified) or generated (`build/`, `analysis/`,
`reference_source/`, rebuilt by `tools/build_all.py`). This is neither. An
acceptance run happens inside AppleWin, driven by hand through
`tools/emucompile.ps1`, `tools/emuassemble.ps1` or `tools/emulink.ps1`, and its output would be
gone the next time `WORK2.dsk` is rewritten. So the output is kept here, and
a probe under `tools/probes/` compares it against the shipped binary on
every build -- which turns a one-off emulator session into a check that goes
on being run.

One directory per run: the codefile Apple's tool wrote, and the screen at
the moment it finished.

| run | what was run | result |
|---|---|---|
| `2026-08-24-formatter-native` | `SYSTEM.ASSMBLER` 1.3 on `src/native/FORMATTR.TEXT` (as `FMTNATIV.TEXT`) | 225 lines, **0 errors**; 354 bytes **identical** to `FORMATTER.CODE`'s procedure 2, relocation table included (finding 103e) |
| `2026-08-24-formatter-linked` | `SYSTEM.COMPILER` 1.3 on `FORMATTER.text`, then `SYSTEM.LINKER` joining it to the above | the whole codefile **identical** to `FORMATTER.CODE` -- dictionary and all 2672 bytes of segment `FORMATTE` -- to the end of the segment (finding 104) |
| `2026-08-25-compiler-search-asm` | `SYSTEM.ASSMBLER` 1.3 on `src/native/SEARCH.TEXT` | 519 lines, **0 errors**; the assembled `IDSEARCH`/`TREESEARCH` are what the linked run below copies in |
| `2026-08-25-compiler-linked` | `SYSTEM.COMPILER` 1.3 on the fifteen-segment `BODY13.TEXT` splice, then `SYSTEM.LINKER` joining it to the above | **not** an exact match, and not wired into `probe_acceptance.py`. 14 of 15 segments byte-identical; both native routines land at the right offset and match byte for byte; `PASCALCO` itself differs by an extra empty host segment (512 bytes) and a different physical ordering of its own procedure bodies (finding 105) |
