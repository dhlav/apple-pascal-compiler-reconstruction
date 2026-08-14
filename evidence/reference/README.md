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

## `manuals/`

Vendor and third-party documentation. These are copyrighted and are kept
here because this repository is private and because a citation that cannot
be checked is not evidence. Filenames are the ones the scans arrived with:
each `.html` refers to a sibling `<basename>_files/` directory of page
images, so renaming either half breaks the link.

| file | what it is |
|---|---|
| `Image071217212805.pdf.duplex_text.pdf` / `.html` | **Apple II Pascal 1.3** manual set, 932 pages, all five parts. Part IV Ch. 3-4 is the P-machine and its instruction set. Findings 23, 24, 25. |
| `Apple Pascal Language Reference Manual.pdf` / `.html` | The 1980 edition, Apple #A2L0027 — the **1.1-era** language reference. |
| `Apple_Pascal_Update_v1.1_text.pdf` / `.html` | The Version 1.1 update notice, bound with the 1.2 addendum. Finding 23e. |
| `Hyde_P-Source-A Guide to the APPLE Pascal System_1983.pdf` | Randall Hyde, *P-Source*, 1983. 462 pages, **no text layer**. Finding 7a. |

The `.pdf` is the scan; the `.html` is an OCR pass over it, and it is the
only text layer the first three have. `tools/reference_text.py` strips the
markup into `analysis/reference/*.txt`, which is what the citations in
`docs/FINDINGS.md` were read from and what to `grep`.

**The OCR is not clean.** It splits table columns onto separate lines,
reads `{$S-}` as `{$5 --}`, drops the decimal column from part of Table
4-1, and says a bit "is cleared" where the binary says set. Check anything
load-bearing against the rendered page — `tools/pdfpage.py` does that.

SHA-256, for the same reason the disk images carry them:

    0b0febc1c0169541d4b7e32aa0d39b8ad61f79f505fba519a3d8cf4d7ede6441  Apple Pascal Language Reference Manual.html
    70eb71c62ae541a25d1a5a3d7712e2ed5cac4ecf6602c291c7f6cc87036afcf7  Apple Pascal Language Reference Manual.pdf
    cdc1192df949e33f2f3f83d035029643d7fdcfc917cdeb5c3b94f7742700bca6  Apple_Pascal_Update_v1.1_text.html
    be3eeca234095b122f33570072343bdf45c653bf9b119cae189726717cb549ae  Apple_Pascal_Update_v1.1_text.pdf
    bd92432e2e8ee930d0eb18252c6cd571bf36129597dd9202c5aeeb30065c2335  Hyde_P-Source-A Guide to the APPLE Pascal System_1983.pdf
    f3cb3660189d731d86b5dea0473f595ec6b550ad688ac48ab2fa54b786bd793d  Image071217212805.pdf.duplex_text.html
    3802bf925eb9eb291e16c75536358f3db8a28ffa56cb4ae5e8df8252bef2046e  Image071217212805.pdf.duplex_text.pdf
