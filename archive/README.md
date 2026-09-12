# Archive

Everything here was set aside on 2026-09-12, when the project's scope was
narrowed to **Apple Pascal 1.3 on the 128K system only** (`128K.APPLE` +
`128K.PASCAL`). None of it is read by `tools/build_all.py`, and none of it
is a target. It is kept, not deleted, because the findings that cite it are
still the project's history.

| where | what |
|---|---|
| `evidence/archive/1.1/` | the three 1.1 disk images -- Apple's 1.1 `APPLE2` and UCSD 1.1 `_1`/`_3` -- moved with `git mv`, bytes unchanged and still read-only (CLAUDE.md hard rule 1) |
| `archive/src/pascal/1.1/` | the 1.1 compiler source, `PASCALCO.text` and its phases |
| `archive/tools/` | `globaldiff.py` (the 1.1 -> 1.3 correspondence), `pairdiff.py`, `liftdiff.py` |
| `archive/tools/probes/` | every probe whose purpose was 1.1, or 1.1 against 1.3: the lifter's GOTOXY calibration (`probe_calibrate.py`), the host compile of the same (`probe_xcompile.py`), the stale-utilities check, and about thirty investigation probes that were never build steps |
| `archive/analysis/` | the generated 1.1 listings, lifts, maps and interfaces, and the 64K `SYSTEM.PASCAL`'s own listings -- the last output the build wrote for them |

The 64K `SYSTEM.APPLE` and `SYSTEM.PASCAL` themselves are not here: they are
files *inside* the 1.3 `APPLE1` image, which cannot change. The tools that
sweep that disk skip them by name (`disasm_utils.py`, `lift_utils.py`,
`probe_split_segment.py`).

**These scripts no longer run as they are.** They still name
`evidence/disks/` and `src/pascal/1.1/`. To use one again, point its disk
and source paths at the archive locations above; nothing else about them
changed.

What stopped being checked when they were archived, so nobody assumes it
still is:

- the lifter's calibration against Apple's own source-and-output pairs (the
  1.1 GOTOXY programs, findings 49 and 55);
- the 1.1 -> 1.3 global correspondence (finding 11);
- the check that the three APPLE3 utilities 1.3 did not rebuild differ from
  their 1.1 copies only in SEGINFO;
- 1.1's side of the OS probes: no FIOPRIMS in 1.1's OS, OSPROC43's missing
  control-character clamp, the two-versus-three `CXP 0,43` sites.

Two OS calibration probes that had only ever run against the 64K build were
retargeted to `128K.PASCAL` rather than archived, and their expectations
held unchanged: `probe_os_calibrate.py` and `probe_case_calibrate.py`.
