"""Build the per-file reconstruction report as a PDF.

    python tools/mkreport.py [out.pdf]     # default docs/PascalRecon-1.3-Reconstruction-Report.pdf

Byte counts are parsed from analysis/diskset-account.txt, which
tools/mkdiskset.py writes and probe_diskset.py checks, so the numbers here
are the build's, not retyped. The per-file notes are from docs/FINDINGS.md
and have to be kept in step with it by hand. Needs reportlab. Not part of
build_all.py: the PDF is a document, regenerated when the account or the
notes change.
"""
import re
import subprocess
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

ROOT = Path(__file__).resolve().parent.parent
OUT = (Path(sys.argv[1]) if len(sys.argv) > 1
       else ROOT / "docs" / "PascalRecon-1.3-Reconstruction-Report.pdf")
ACCOUNT = (ROOT / "analysis" / "diskset-account.txt").read_text()
COMMIT = subprocess.run(["git", "-C", str(ROOT), "log", "-1", "--format=%h %cs"],
                        capture_output=True, text=True).stdout.strip()

# ---- parse the account ---------------------------------------------------
regions = []          # (disk, first, blocks, name, category, bytes, differ, source)
disk = None
totals = {}
disk_totals = {}
for line in ACCOUNT.splitlines():
    m = re.match(r"^(APPLE\d)\s+(\d+) bytes, (\d+) identical, (\d+) differ", line)
    if m:
        disk = m.group(1)
        disk_totals[disk] = tuple(int(x) for x in m.groups()[1:])
        continue
    m = re.match(r"^\s+(\d+)\+(\d+)\s+(\S+)\s+(\w+)\s+(\d+)\s+(\d+)\s+(.*)$", line)
    if m and disk:
        regions.append((disk, int(m.group(1)), int(m.group(2)), m.group(3),
                        m.group(4), int(m.group(5)), int(m.group(6)),
                        m.group(7)))
        continue
    m = re.match(r"^\s+(rebuilt|text|boot|directory|free|archived|all)\s+(\d+) bytes\s+(\d+) identical\s+(\d+) differ", line)
    if m:
        totals[m.group(1)] = tuple(int(x) for x in m.groups()[1:])
by_name = {}
for r in regions:
    by_name.setdefault(r[3], []).append(r)

# ---- per-file notes --------------------------------------------------------
# status: IDENTICAL, NEAR (named remainder), EXCEPTION, ARCHIVED
F = {}


def f(name, status, source, route, work, differ_note, exceptions, findings):
    F[name] = dict(status=status, source=source, route=route, work=work,
                   differ=differ_note, exceptions=exceptions,
                   findings=findings)


f("SYSTEM.COMPILER", "IDENTICAL",
  "src/pascal/1.3/ (PASCALCO.text and phases/); src/native/SEARCH.TEXT",
  "Apple's compiler, assembler (IDSEARCH/TREESEARCH), Linker, then the Librarian copies slots 1-15 with Apple's notice",
  "147 of 147 procedures, 15 segments. A direct descendant of Pascal-P2; names from UCSD's II.0 compiler source where the bytes confirm them.",
  "None. All 39,936 bytes, slack included.",
  ["Slot 0 is blank in Apple's file because the release step was the Librarian, not the compile (finding 105a, closed)."],
  "90, 105a, 107, 267e")
f("SYSTEM.ASSMBLER", "IDENTICAL",
  "src/pascal/programs/1.3/ASSMBLER.text",
  "Apple's compiler; the Librarian joins slots 1-6 with slot 0 taken from the shipped file",
  "90 of 95 procedures in six segments are Apple's compiler's output: TLA 38, ASSEMBLE 33, PROCEND 9, INITIALI 6, SYMTBLDU 3, PRINTERR 1. Names from UCSD's I.5 Adaptable Assembler.",
  "None as a file: all 25,600 bytes identical.",
  ["EXCEPTION: the PASCALIO segment (5 procedures) is copied from Apple's shipped file. It is an older unit (version 2) and nothing on the 1.3 disks can rebuild it (finding 235b). The file is identical, but that segment is borrowed, not reconstructed."],
  "235b, 237-266, 267f")
f("SYSTEM.LINKER", "IDENTICAL",
  "src/pascal/programs/1.3/LINKER.text",
  "Apple's compiler, then the Librarian copies slot 1 with the notice",
  "51 of 51 procedures. Ancestor: Roger Sumner's I.5 linker; byte-flip and small-memory names from its II.0 revision.",
  "None. All 12,800 bytes.",
  ["Apple's additions past II.0 (intrinsic units, data segments, version check) keep placeholder names: G29, G91, LK2, LK3, LK17, LK51 and some locals."],
  "268, 291")
f("LIBRARY.CODE", "IDENTICAL",
  "src/pascal/programs/1.3/LIBRARY.text (staged as LIBR13)",
  "Apple's compiler, then the shipped Librarian copies slot 1",
  "16 of 16 procedures. Ancestor: UCSD's I.5 Librarian and its II.0 revision (Dismukes).",
  "None. All 4,096 bytes.",
  ["Apple's own additions keep placeholders: G131, LB6, LB15, M2, M3 and some locals."],
  "269, 292")
f("SYSTEM.FILER", "IDENTICAL",
  "src/pascal/programs/1.3/FILER.text",
  "Apple's compiler, then the Librarian copies slot 1",
  "56 of 56 procedures, one segment, from UCSD's II.0 Filer, inside the 1.3 OS declarations.",
  "None. All 15,360 bytes.", [], "271")
f("SYSTEM.EDITOR", "IDENTICAL",
  "src/pascal/programs/1.3/EDITOR.text",
  "Apple's compiler, then the Librarian copies segments 1 and 7-12 into slots 1-7",
  "129 of 129 procedures in seven segments, from UCSD's II.0 screen editor.",
  "None. All 25,600 bytes.", [], "272")
f("128K.APPLE", "IDENTICAL",
  "src/native/interp/ (INTERP, BANK1, TOP), generated from 128K.hints by tools/absdis.py; MAKEINTP",
  "Apple's assembler (three .ABSOLUTE assemblies), joined by MAKEINTP compiled and run on the 1.3 system",
  "The 128K p-machine interpreter.",
  "None. All 16,384 bytes.",
  ["The split between code and data in the three sources is traced, not proven: an absolute assembly has no relocation, so a byte compare cannot tell a data byte written as code from code."],
  "279")
f("SYSTEM.CHARSET", "IDENTICAL", "src/data/CHARSET.TEXT; MAKECHRS",
  "MAKECHRS compiled and run on the 1.3 system", "The hi-res character set.",
  "None. All 1,024 bytes.", [], "278")
f("6502.OPCODES", "IDENTICAL", "src/data/OPS6502.TEXT; MAKEOPS",
  "MAKEOPS compiled and run on the 1.3 system", "Sixty opcode records for the assembler.",
  "None. All 1,024 bytes.", [], "276")
f("SYSTEM.LIBRARY", "EXCEPTION",
  "src/pascal/units/1.3/ (six units, each with a .layout); src/native/LONGINTS.TEXT, TURTLEGR.TEXT, APPLESTF.TEXT",
  "Apple's compiler (6 units), assembler (3 native halves), Linker (3 links), then the Librarian joins them in Apple's slot order with the notice",
  "55 p-code and 14 native procedures. All six code segments and TURTLEGR's data segment byte-identical. Each unit's interface text identical through IMPLEMENTATION.",
  "16,417 of 19,456 bytes agree aligned unit by unit. In place on the disk 16,234 differ, because the rebuilt file is two blocks short and every unit after LONGINTI sits one or two blocks early.",
  ["ACCEPTED EXCEPTION to the whole-file target. Apple's text blocks were written by a compiler other than the shipped one: LONGINTI's text is 2 blocks and TURTLEGR's 3 (the shipped compiler writes 1 and 2), each 10-byte trailer holds N or X at offset 6 (no 1.3 tool writes it), and the extra blocks hold buffer copies.",
   "Those copies preserve fragments of Apple's own source: LONGINTIO declares PROCEDURE DECOPS; EXTERNAL; first (so the engine was renamed DECOPS), TURTLEGRAPHICS has {$endc} and {$SETC SHORT := FALSE} after IMPLEMENTATION, and a development path /P/NEWC/C.CODE appears in two tails.",
   "The editor's encoding of each interface is content, so every unit source carries a .layout recording which lines Apple's editor stored with a DLE code and where pages break."],
  "285, 286, 287, 290, 294")
f("128K.PASCAL", "NEAR",
  "src/pascal/os/1.3/PASCALSYSTEM.text; src/pascal/programs/1.3/MAKEOS.text",
  "Apple's compiler (one compile), finished by MAKEOS compiled and run on the 1.3 system, which splits segment 0 the way the 128K boot loads it",
  "All 111 procedures in 7 segments; every segment and SEGKIND Apple's; FIOPRIMS written as INTRINSIC CODE 2.",
  "571 bytes: three slack tails that held another tool's memory.",
  ["Apple's file was finished by a tool that is not on the disks. MAKEOS reproduces the split, the crossing pointers (derived from the 128K boot), word 0x120 and the notice; the slack that tool left cannot be reproduced."],
  "232-233, 280-284")
f("SETUP.CODE", "NEAR",
  "src/pascal/programs/1.3/SETUP.text",
  "Apple's compiler",
  "54 of 54 procedures instruction- and frame-identical, from UCSD's SETUP D1 with Apple's six S.2 edits.",
  "3,943 bytes.",
  ["No 1.3 source can close it: Apple's file predates the SEGINFO version word (0 in every slot) and its compiler left stale bytes in 34 alignment pads that the 1.3 compiler writes as 0."],
  "273")
f("LIBMAP.CODE", "NEAR",
  "src/pascal/programs/1.3/LIBMAP.text; src/native/SEARCH.TEXT",
  "Apple's compiler, assembler and Linker (an ordinary program, no Librarian)",
  "12 of 12 procedures, native IDSEARCH included; block 0 and all 5,300 bytes before the slack identical. Apple's four added globals named from compiler symbol nodes in the shipped slack.",
  "311 bytes of the last block's slack (Linker memory).", [], "109, 270, 293")
f("FORMATTER.CODE", "NEAR",
  "src/pascal/programs/1.3/FORMATTER.text; src/native/FORMATTR.TEXT",
  "Apple's compiler, assembler and Linker",
  "The first whole Pascal-plus-6502 program rebuilt.",
  "394 bytes of the last block's slack (Linker memory).", [], "104")
f("FORMATTER.DATA", "NEAR",
  "src/native/ASMFORMAT.TEXT, BOOTII.TEXT, BOOTPD.TEXT; MAKEBOOT, MAKEFMT",
  "Apple's assembler, joined by two programs compiled and run on the 1.3 system",
  "The Disk II formatter, the Disk II boot (also every disk's blocks 0-1) and the ProDOS boot.",
  "1 byte: the assembler's uncleared buffer byte, session memory.", [], "275")
f("6502.ERRORS", "NEAR", "src/data/ERRS6502.TEXT; MAKEERRS",
  "MAKEERRS compiled and run on the 1.3 system",
  "85 STRING[40] records, record 65 rewritten afterwards as Apple's was.",
  "287 bytes, all descended from the record window's first fill (session memory). Apple's fill substituted into ours gives Apple's file.",
  [], "276")
f("BINDER.CODE", "NEAR", "src/pascal/programs/1.3/BINDER.text", "Apple's compiler",
  "6 of 6 procedures.",
  "16 bytes: SEGINFO version bits.",
  ["Apple never rebuilt this file for 1.3: it is a 1.1 binary stamped version 2, and any 1.3 compile writes 6. With version 2 written in, the whole file is Apple's."],
  "99c, 274")
f("SET40COLS.CODE", "NEAR", "src/pascal/programs/1.3/SET40COLS.text", "Apple's compiler",
  "4 of 4 procedures.", "16 bytes: SEGINFO version bits.",
  ["A 1.1 binary (version 2) carried into 1.3; same cause as BINDER."],
  "99c, 112, 274")
f("LINEFEED.CODE", "NEAR", "src/pascal/programs/1.3/LINEFEED.text (Apple's own 1.1 source, unaltered)",
  "Apple's compiler", "1 procedure, 38 bytes of code.",
  "467 bytes: 16 SEGINFO version bits (a 1.1 binary, version 2 against 6) and 451 bytes of compile slack past the code.",
  ["Every byte through the end of the code is Apple's but the version field."],
  "99a, 99c, 288c")
for n, d in (("SYSTEM.MISCINFO", "Screen and keyboard profile for the boot system"),
             ("II40.MISCINFO", "40-column Apple II profile"),
             ("II80.MISCINFO", "80-column profile"),
             ("HAZEL.MISCINFO", "Hazeltine terminal profile")):
    f(n, "NEAR", f"src/data/miscinfo/{n.split('.')[0]}.recipe",
      "Apple's shipped SETUP, driven from the recipe on the 1.3 system",
      f"{d}: every setting and the zero tail.",
      "The rest of the 512 bytes is memory SETUP never writes.",
      ["Apple's SYSTEM.MISCINFO held SYSTEM.FILER's code there; a 128K run does not leave it."] if n == "SYSTEM.MISCINFO" else [],
      "277")
TEXTS = ["SYSTEM.SYNTAX", "BALANCED.TEXT", "CROSSREF.TEXT", "DISKIO.TEXT",
         "GRAFCHARS.TEXT", "GRAFDEMO.TEXT", "HAZELGOTO.TEXT", "HILBERT.TEXT",
         "SPIRODEMO.TEXT", "TREE.TEXT"]
for n in TEXTS:
    stem = n[:-5] if n.endswith(".TEXT") else n
    ex = ["Produced by this repository's encoder from the text and its .layout, checked against Apple's bytes; no Apple tool is run."]
    if n == "SYSTEM.SYNTAX":
        ex.append("Plain text with a DLE code on six lines only (the other nine files have one on nearly every line).")
    if n == "HAZELGOTO.TEXT":
        ex.append("Its page zero is not SYSTEM.EDITOR's HEADER record: the environment sits 142 bytes later; recorded as raw bytes.")
    f(n, "IDENTICAL", f"src/text/{stem}.text and {stem}.layout",
      "Encoded by tools/a2pascal/textfile.py (Layout)",
      "Lines, per-line DLE encoding, greedy page packing, and the editor's page zero (margins, command character, created and last-used dates).",
      "None.", ex, "288")
for n in ("SYSTEM.APPLE", "SYSTEM.PASCAL"):
    f(n, "ARCHIVED", "--", "Not rebuilt",
      "The 64K system. Out of scope by decision; the build writes zero here.",
      "Every nonzero byte of Apple's counts as a difference.",
      ["Archived with Apple Pascal 1.1; the project targets the 128K system only."], "--")

# ---- document ------------------------------------------------------------
ss = getSampleStyleSheet()
body = ParagraphStyle("b", parent=ss["BodyText"], fontName="Helvetica",
                      fontSize=9, leading=12)
small = ParagraphStyle("s", parent=body, fontSize=8, leading=10)
cell = ParagraphStyle("c", parent=body, fontSize=7.5, leading=9.2, alignment=TA_LEFT)
cellb = ParagraphStyle("cb", parent=cell, fontName="Helvetica-Bold")
h1 = ParagraphStyle("h1", parent=ss["Heading1"], fontName="Helvetica-Bold",
                    fontSize=17, spaceAfter=8, textColor=colors.HexColor("#1f2d3d"))
h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontName="Helvetica-Bold",
                    fontSize=12.5, spaceBefore=10, spaceAfter=5,
                    textColor=colors.HexColor("#1f2d3d"))
h3 = ParagraphStyle("h3", parent=ss["Heading3"], fontName="Helvetica-Bold",
                    fontSize=10.5, spaceBefore=6, spaceAfter=3)
STATUS_COLOR = {"IDENTICAL": "#2e7d32", "NEAR": "#1565c0",
                "EXCEPTION": "#c62828", "ARCHIVED": "#757575"}
STATUS_LABEL = {"IDENTICAL": "Identical", "NEAR": "Named remainder",
                "EXCEPTION": "Accepted exception", "ARCHIVED": "Out of scope"}


def esc(t):
    return (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def P(t, st=body):
    return Paragraph(t, st)


def grid(data, widths, header=True, zebra=True):
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b0b7c0")),
             ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("LEFTPADDING", (0, 0), (-1, -1), 3),
             ("RIGHTPADDING", (0, 0), (-1, -1), 3),
             ("TOPPADDING", (0, 0), (-1, -1), 2),
             ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dfe6ee"))]
    if zebra:
        for i in range(1 if header else 0, len(data)):
            if i % 2 == 0:
                style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f6f8fa")))
    t.setStyle(TableStyle(style))
    return t


def num(n):
    return f"{n:,}"


story = []
story.append(P("Apple Pascal 1.3 Disk Set: Reconstruction Report", h1))
story.append(P(f"PascalRecon, commit {esc(COMMIT)}. Byte counts are parsed from "
               "<font face='Courier'>analysis/diskset-account.txt</font>, written by "
               "<font face='Courier'>tools/mkdiskset.py</font> and checked by "
               "<font face='Courier'>tools/probes/probe_diskset.py</font>. "
               "Finding numbers refer to <font face='Courier'>docs/FINDINGS.md</font>.", small))
story.append(Spacer(1, 8))

story.append(P("Summary", h2))
a = totals["all"]; ar = totals["archived"]
ins = (a[0] - ar[0], a[1] - ar[1])
story.append(P(
    f"The goal is source for every file on the Apple Pascal 1.3 disk set (128K system) that "
    f"Apple's own tools, run under AppleWin, turn back into the shipped bytes. The three disks "
    f"were rebuilt block for block from that work: <b>{num(a[1])} of {num(a[0])} bytes</b> are "
    f"identical to Apple's images. Excluding the archived 64K system, <b>{num(ins[1])} of "
    f"{num(ins[0])}</b>. Every remaining difference is accounted for by region and has a named "
    f"cause; the per-region counts add up to a direct compare of the image files."))
story.append(Spacer(1, 6))
cat_rows = [[P("Category", cellb), P("Bytes", cellb), P("Identical", cellb),
             P("Differ", cellb), P("What it is", cellb)]]
CAT_DESC = {
    "rebuilt": "Files produced by Apple's compiler, assembler, Linker, Librarian or SETUP from this repository's source",
    "text": "Text files encoded from src/text/ and their .layout files",
    "boot": "Blocks 0-1 of each disk, from the rebuilt FORMATTER.DATA",
    "directory": "Apple's directory entries re-encoded; dead space written as zero",
    "free": "Unallocated blocks, written as zero",
    "archived": "The 64K SYSTEM.APPLE and SYSTEM.PASCAL, out of scope, written as zero",
    "all": "The three disks"}
for k in ("rebuilt", "text", "boot", "directory", "free", "archived", "all"):
    b, i, d = totals[k]
    st = cellb if k == "all" else cell
    cat_rows.append([P(k, st), P(num(b), st), P(num(i), st), P(num(d), st), P(CAT_DESC[k], cell)])
story.append(grid(cat_rows, [0.85 * inch, 0.75 * inch, 0.75 * inch, 0.65 * inch, 4.0 * inch]))
story.append(Spacer(1, 8))

counts = {}
for n, info in F.items():
    counts[info["status"]] = counts.get(info["status"], 0) + 1
story.append(P(
    f"Of the {len(F)} distinct files: <font color='{STATUS_COLOR['IDENTICAL']}'><b>{counts['IDENTICAL']} identical</b></font>, "
    f"<font color='{STATUS_COLOR['NEAR']}'><b>{counts['NEAR']} with a named remainder</b></font> "
    f"(slack, version stamps or session memory that the shipped tools cannot reproduce), "
    f"<font color='{STATUS_COLOR['EXCEPTION']}'><b>{counts['EXCEPTION']} accepted exception</b></font> "
    f"(SYSTEM.LIBRARY) and <font color='{STATUS_COLOR['ARCHIVED']}'><b>{counts['ARCHIVED']} out of scope</b></font>."))

# per-disk tables
story.append(P("Files by disk", h2))
for dname in ("APPLE1", "APPLE2", "APPLE3"):
    b, i, d = disk_totals[dname]
    rows = [[P("Blocks", cellb), P("File / region", cellb), P("Bytes", cellb),
             P("Identical", cellb), P("Differ", cellb), P("Status", cellb)]]
    for r in regions:
        if r[0] != dname:
            continue
        name = r[3]
        if name.startswith("<"):
            status = "residue" if r[6] else "identical"
            label = {"<boot>": "boot blocks", "<directory>": "directory",
                     "<free>": "free space"}[name]
            scol = "#555555"
        else:
            status = STATUS_LABEL[F[name]["status"]]
            label = name
            scol = STATUS_COLOR[F[name]["status"]]
        rows.append([P(f"{r[1]}+{r[2]}", cell), P(esc(label), cell), P(num(r[5]), cell),
                     P(num(r[5] - r[6]), cell), P(num(r[6]), cell),
                     P(f"<font color='{scol}'>{status}</font>", cell)])
    rows.append([P("", cell), P("<b>disk total</b>", cell), P(f"<b>{num(b)}</b>", cell),
                 P(f"<b>{num(i)}</b>", cell), P(f"<b>{num(d)}</b>", cell), P("", cell)])
    story.append(KeepTogether([P(dname, h3),
                               grid(rows, [0.6 * inch, 1.6 * inch, 0.8 * inch,
                                           0.8 * inch, 0.7 * inch, 2.5 * inch])]))
    story.append(Spacer(1, 4))

# exceptions summary
story.append(PageBreak())
story.append(P("Exceptions and remainders at a glance", h2))
ex_rows = [[P("File", cellb), P("Differ", cellb), P("Why it cannot be closed", cellb)]]
ORDER = ["SYSTEM.LIBRARY", "SETUP.CODE", "128K.PASCAL", "LINEFEED.CODE",
         "FORMATTER.CODE", "LIBMAP.CODE", "6502.ERRORS", "SYSTEM.MISCINFO",
         "II40.MISCINFO", "II80.MISCINFO", "HAZEL.MISCINFO", "BINDER.CODE",
         "SET40COLS.CODE", "FORMATTER.DATA", "SYSTEM.ASSMBLER",
         "SYSTEM.APPLE", "SYSTEM.PASCAL"]
WHY = {
    "SYSTEM.LIBRARY": "Accepted exception: text blocks from a compiler other than the shipped one (block counts, trailer flag, buffer copies); file two blocks short, so misaligned in place. Unit by unit 16,417 of 19,456 agree, all code identical.",
    "SETUP.CODE": "Apple's file predates the version word and carries 34 stale alignment pads.",
    "128K.PASCAL": "Slack left by Apple's finishing tool, which is not on the disks.",
    "LINEFEED.CODE": "1.1 binary: version bits; plus compile slack past the code.",
    "FORMATTER.CODE": "Linker memory in the last block's slack.",
    "LIBMAP.CODE": "Linker memory in the last block's slack.",
    "6502.ERRORS": "The record window's first fill was session memory.",
    "SYSTEM.MISCINFO": "Memory SETUP never writes (Apple's held SYSTEM.FILER code).",
    "II40.MISCINFO": "Memory SETUP never writes.",
    "II80.MISCINFO": "Memory SETUP never writes.",
    "HAZEL.MISCINFO": "Memory SETUP never writes.",
    "BINDER.CODE": "1.1 binary: SEGINFO version 2 against a 1.3 compile's 6.",
    "SET40COLS.CODE": "1.1 binary: SEGINFO version 2 against 6.",
    "FORMATTER.DATA": "One uncleared assembler buffer byte (the same byte appears in every disk's boot blocks).",
    "SYSTEM.ASSMBLER": "File identical, but the PASCALIO segment is copied from Apple's file: nothing on the 1.3 disks rebuilds it.",
    "SYSTEM.APPLE": "64K system, archived, not rebuilt (appears on APPLE1 and APPLE3).",
    "SYSTEM.PASCAL": "64K system, archived, not rebuilt.",
}
for n in ORDER:
    d = sum(r[6] for r in by_name[n])
    ex_rows.append([P(esc(n), cell), P(num(d), cell), P(esc(WHY[n]), cell)])
for name, disk_, why in (("boot blocks", "all", "The FORMATTER.DATA byte above, once per disk (3)."),
                         ("directories", "all", "Dead space past the live entries: Filer text, and on APPLE2 a removed LINKER.INFO entry (68)."),
                         ("free space", "APPLE2", "Block 187 still holds that LINKER.INFO file: linker records for FORMATDI (44).")):
    d = sum(r[6] for r in regions if r[3] == {"boot blocks": "<boot>", "directories": "<directory>", "free space": "<free>"}[name])
    ex_rows.append([P(name, cell), P(num(d), cell), P(why, cell)])
story.append(grid(ex_rows, [1.35 * inch, 0.7 * inch, 4.95 * inch]))
story.append(Spacer(1, 8))
story.append(P(
    "What the total does not claim: the text files, the boot-block placement and the directory "
    "are produced by this repository's encoders and checked against Apple's bytes; no Apple tool "
    "wrote them. The directory's names, placement and dates are Apple's history, carried over "
    "rather than reconstructed.", small))

# per-file detail
story.append(PageBreak())
story.append(P("File by file", h2))
disk_of = {}
for r in regions:
    if not r[3].startswith("<"):
        disk_of.setdefault(r[3], []).append(r[0])
FILE_ORDER = (["SYSTEM.COMPILER", "SYSTEM.ASSMBLER", "SYSTEM.LINKER", "SYSTEM.EDITOR",
               "SYSTEM.FILER", "LIBRARY.CODE", "128K.APPLE", "128K.PASCAL",
               "SYSTEM.LIBRARY", "LIBMAP.CODE", "FORMATTER.CODE", "FORMATTER.DATA",
               "SETUP.CODE", "BINDER.CODE", "SET40COLS.CODE", "LINEFEED.CODE",
               "SYSTEM.CHARSET", "6502.OPCODES", "6502.ERRORS", "SYSTEM.MISCINFO",
               "II40.MISCINFO", "II80.MISCINFO", "HAZEL.MISCINFO"] + TEXTS +
              ["SYSTEM.APPLE", "SYSTEM.PASCAL"])
assert sorted(FILE_ORDER) == sorted(F), set(F) ^ set(FILE_ORDER)
assert set(FILE_ORDER) == {k for k in by_name if not k.startswith("<")}
for n in FILE_ORDER:
    info = F[n]
    rs = by_name[n]
    size = rs[0][5]
    differ = rs[0][6]
    color = STATUS_COLOR[info["status"]]
    head = (f"{esc(n)} &nbsp;<font size=8 color='{color}'>[{STATUS_LABEL[info['status']]}]</font>")
    disks = ", ".join(sorted(set(disk_of[n])))
    if len(rs) > 1:
        disks += " (figures are for each copy)"
    rows = [
        [P("Disk", cellb), P(disks, cell), P("Size", cellb), P(f"{num(size)} bytes", cell)],
        [P("Identical", cellb), P(f"{num(size - differ)}", cell), P("Differ", cellb),
         P(f"<font color='{color}'>{num(differ)}</font>", cell)],
        [P("Source", cellb), P(esc(info["source"]), cell), P("Findings", cellb), P(esc(info["findings"]), cell)],
        [P("Rebuilt by", cellb), P(esc(info["route"]), cell), P("", cell), P("", cell)],
        [P("Reconstructed", cellb), P(esc(info["work"]), cell), P("", cell), P("", cell)],
        [P("Differences", cellb), P(esc(info["differ"]), cell), P("", cell), P("", cell)],
    ]
    t = Table(rows, colWidths=[0.95 * inch, 3.6 * inch, 0.75 * inch, 1.7 * inch])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c5ccd4")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef2f6")),
        ("BACKGROUND", (2, 0), (2, 2), colors.HexColor("#eef2f6")),
        ("SPAN", (1, 3), (3, 3)), ("SPAN", (1, 4), (3, 4)), ("SPAN", (1, 5), (3, 5)),
        ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    block = [P(head, h3), t]
    for e in info["exceptions"]:
        block.append(Spacer(1, 2))
        block.append(P("&bull; " + esc(e), small))
    block.append(Spacer(1, 6))
    story.append(KeepTogether(block))

# method
story.append(PageBreak())
story.append(P("How it was checked", h2))
for t in [
    "<b>Acceptance tier.</b> Apple's own compiler, assembler, Linker, Librarian and SETUP, run under AppleWin on the 128K 1.3 system and driven over a redirected console (tools/emuremote.py). Their output is kept verbatim in acceptance/, and probes compare it with Apple's disks on every build (python tools/build_all.py, which must exit 0).",
    "<b>Fast tier.</b> Host reimplementations (ucsdpsys_compile, tools/asm6502.py) can only falsify, never accept.",
    "<b>The disk account.</b> tools/mkdiskset.py writes APPLE1-3 from the rebuilt files. probe_diskset.py requires the regions to tile each disk, their difference counts to equal a direct compare of the image files, the same build from Apple's own regions to reproduce Apple's images exactly (so placement is not a source of difference), and each region to differ by exactly the count its finding explains.",
    "<b>Names.</b> Identifiers are taken from UCSD's I.5 and II.0 sources, Apple's own source fragments and compiler symbol nodes left in slack, and only where the code matches. Apple's own additions with no ancestor keep placeholder names (LK&lt;n&gt;, G&lt;n&gt;, L&lt;n&gt;); renames were re-verified byte-identical on the acceptance tier (findings 291-294).",
    "<b>Labels.</b> Every claim in docs/FINDINGS.md is labelled VERIFIED BINARY FACT, VERIFIED SOURCE FACT, STRONG INFERENCE or SPECULATION.",
]:
    story.append(P(t))
    story.append(Spacer(1, 4))


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawString(0.75 * inch, 0.5 * inch, "Apple Pascal 1.3 reconstruction report")
    canvas.drawRightString(7.75 * inch, 0.5 * inch, f"Page {doc.page}")
    canvas.restoreState()


doc = SimpleDocTemplate(str(OUT), pagesize=letter, leftMargin=0.75 * inch,
                        rightMargin=0.75 * inch, topMargin=0.7 * inch,
                        bottomMargin=0.75 * inch,
                        title="Apple Pascal 1.3 Reconstruction Report",
                        author="PascalRecon")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print("wrote", OUT)
