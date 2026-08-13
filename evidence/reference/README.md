# Reference material

Third-party documents, kept as supplied. Corroboration only — where any of
these disagrees with the evidence disks, the disks win.

## `Undocumented Secrets of Apple Pascal.html`

Neil Parker. Background on the p-system's on-disk structures.

## `tribby-idsearch-treesearch-1.2.asm`

Dave Tribby's commented 6502 disassembly of `IDSEARCH` and `TREESEARCH`,
taken from the **1.2** `SYSTEM.APPLE` and rewritten as linkable
`.PROC`/`.FUNC` routines, June 1986.

**This is a different release from either evidence disk.** The project's
own disassembly of 1.3's native procedures — `analysis/native/`, produced
by `tools/disasm6502.py` from the 1.3 image — is the authority. Tribby's
listing is used to corroborate it and to supply names and intent, never to
override it.

Held up well as a check (finding 19): 41 of 41 reserved-word entries match
the 1.3 table exactly, name, `SY` and `OP`; his 3-byte empty-letter
sentinel explains a slot that the extraction had found but not accounted
for; and his entry sequence matches the 1.3 code instruction for
instruction. The differences it exposed are real 1.2 → 1.3 changes: 1.3
adds the reserved word `OTHERWISE`, and it moves the routines' zero-page
scratch into `$7E`-`$8F`.

Its declarations `.PROC IDSearch,2` and `.FUNC TreeSearch,3` are the only
statement anywhere of these routines' signatures, and are what pins
`CSP 7` and `CSP 8` in `tools/a2pascal/lift.py`.
