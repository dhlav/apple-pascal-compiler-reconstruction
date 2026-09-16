"""Write docs/Grok-Review-Outstanding.pdf — outstanding issues from the Grok review."""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "Grok-Review-Outstanding.pdf"

ss = getSampleStyleSheet()
title = ParagraphStyle(
    "T", parent=ss["Title"], fontSize=16, leading=20,
    textColor=colors.HexColor("#1f2d3d"), spaceAfter=6, alignment=TA_LEFT,
)
h1 = ParagraphStyle(
    "H1", parent=ss["Heading1"], fontSize=12, leading=15,
    textColor=colors.HexColor("#1f2d3d"), spaceBefore=14, spaceAfter=6,
)
body = ParagraphStyle(
    "B", parent=ss["BodyText"], fontSize=9.5, leading=12.5,
    textColor=colors.HexColor("#222222"), spaceAfter=4,
)
bullet = ParagraphStyle("Bu", parent=body, leftIndent=0, spaceAfter=3)
meta = ParagraphStyle(
    "M", parent=ss["Normal"], fontSize=8.5, leading=11,
    textColor=colors.HexColor("#555555"), spaceAfter=10,
)
small = ParagraphStyle("S", parent=body, fontSize=8.5, leading=11)


def p(text, style=body):
    return Paragraph(text, style)


def bullets(items):
    return ListFlowable(
        [ListItem(Paragraph(i, bullet), leftIndent=12,
                  bulletColor=colors.HexColor("#1f2d3d"))
         for i in items],
        bulletType="bullet", start="bullet", leftIndent=18, bulletFontSize=8,
    )


def main() -> int:
    story = []
    story.append(p("Grok Review — Outstanding Issues and Concerns", title))
    story.append(p(
        "PascalRecon (Apple Pascal 1.3 / 128K). Branch <b>Grok-Review</b>, "
        "2026-09-15. Omits reconstructions that already match the shipped "
        "bytes exactly. Full verification record: "
        "<font face='Courier'>docs/GROK-REVIEW.md</font>.",
        meta,
    ))

    story.append(p("Accepted exception", h1))
    story.append(p(
        "<b>SYSTEM.LIBRARY</b> — code segments and interface text through "
        "<font face='Courier'>IMPLEMENTATION</font> match; the <b>file "
        "cannot match whole</b>. Text blocks came from a compiler other "
        "than the shipped one (wrong block counts, "
        "<font face='Courier'>N</font>/<font face='Courier'>X</font> "
        "trailer bytes, buffer copies). In place on disk: <b>16,234</b> "
        "differ; slot-aligned: <b>16,417 / 19,456</b>. HANDOFF §6.1: do "
        "not reopen without new evidence; a reviewer may still examine "
        "<font face='Courier'>UNITPART</font>'s block-count rule if new "
        "evidence appears.",
    ))

    story.append(p(
        "Named remainders (believed unclosable with shipped tools)", h1))
    story.append(p(
        "Leftover session memory or version stamps — not missing logic:"))
    rows = [
        [p("<b>File</b>", small), p("<b>Bytes</b>", small),
         p("<b>Why they stay</b>", small)],
        [p("128K.PASCAL", small), p("571", small),
         p("Finishing-tool slack", small)],
        [p("SETUP.CODE", small), p("3,943", small),
         p("Pre-version-word + stale pads", small)],
        [p("LINEFEED.CODE", small), p("467", small),
         p("1.1 version bits + slack", small)],
        [p("FORMATTER.CODE", small), p("394", small),
         p("Linker slack", small)],
        [p("LIBMAP.CODE", small), p("311", small),
         p("Linker slack as <i>difference</i> count; tail past SEGEND is "
           "332 bytes (21 matching)", small)],
        [p("6502.ERRORS", small), p("287", small),
         p("First record-window fill", small)],
        [p("Four .MISCINFO", small), p("556", small),
         p("Memory SETUP never writes", small)],
        [p("BINDER / SET40COLS", small), p("16 each", small),
         p("SEGINFO version 2 vs 6", small)],
        [p("FORMATTER.DATA / boot", small), p("1", small),
         p("Uncleared assembler byte", small)],
        [p("Directory / free residue", small), p("—", small),
         p("Dead Filer space; APPLE2 block 187 (LINKER.INFO)", small)],
    ]
    t = Table(rows, colWidths=[1.6 * inch, 0.7 * inch, 4.5 * inch])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b0b7c0")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dfe6ee")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f6f8fa")]),
    ]))
    story.append(t)

    story.append(p("Copied, not rebuilt", h1))
    story.append(p(
        "<b>SYSTEM.ASSMBLER</b>'s <font face='Courier'>PASCALIO</font> "
        "segment — nothing on the 1.3 disks rebuilds it; borrowed from "
        "Apple's file (finding 235b).",
    ))

    story.append(p("Active work: placeholder names (bytes unchanged)", h1))
    story.append(bullets([
        "<font face='Courier'>TURTLEGR.TEXT</font> — ~121 "
        "<font face='Courier'>L&lt;nnnn&gt;</font> labels (II.0 "
        "<font face='Courier'>turtle_graphics/</font> is a lead)",
        "<font face='Courier'>pascalio/</font> and "
        "<font face='Courier'>transcendental/</font> against those units",
        "Leftover placeholders: Linker (<font face='Courier'>G29</font>, "
        "<font face='Courier'>G91</font>, <font face='Courier'>LK2</font>"
        "…), Librarian, LibMap (<font face='Courier'>L85</font>), "
        "Filer (~12), Editor (~24), "
        "<font face='Courier'>PASCALSYSTEM</font> (~14)",
        "<b>SYSTEM.ASSMBLER</b> — ~204 placeholders (UCSD I.5 only; no "
        "II.0 assembler found)",
        "<b>128K.APPLE</b> interpreter — ~800 labels; edit "
        "<font face='Courier'>128K.hints</font>, not generated "
        "<font face='Courier'>.TEXT</font> (Brooks 1.4 is a candidate)",
    ]))

    story.append(p("Probe / verification gaps", h1))
    story.append(bullets([
        "<b>SYSTEM.COMPILER</b>: no kept-source lock in the librarian "
        "epoch (only <font face='Courier'>LIBCOMP.CODE</font>); a rename "
        "that does not move bytes would not fail that probe",
        "Finding 290 TURTLEGR buffer fragments "
        "(<font face='Courier'>{$endc}</font>, path strings) are "
        "documented, not asserted by probes "
        "(LONGINTI/<font face='Courier'>DECOPS</font> is)",
        "<font face='Courier'>mkimages</font> / SRCHD: file counts "
        "verified (35 / 73); <b>UTURTLE compile from SRCHD</b> and "
        "commented <font face='Courier'>BODY13</font> slack still "
        "unverified under the emulator",
        "<font face='Courier'>mkimages.py</font> / "
        "<font face='Courier'>mkreport.py</font> are outside "
        "<font face='Courier'>build_all.py</font> — delivery artifacts "
        "can drift without failing the mandatory build",
        "FINDINGS §287 / §289 headlines still show pre-290 totals; live "
        "canon is <b>359,323</b> and library <b>16,417</b> (290d)",
    ]))

    story.append(p("Environment / process risks", h1))
    story.append(bullets([
        "Port <b>1977</b> can be stolen by Windows; SYSHD left armed "
        "with <font face='Courier'>SYSTEM.STARTUP</font> looks like a "
        "dead boot",
        "<font face='Courier'>cp2</font> never overwrites — delete "
        "destinations first or you score a stale run",
        "<font face='Courier'>stagefile.py</font> can refuse a moved "
        "<font face='Courier'>.layout</font> while a batch keeps "
        "compiling the <b>old</b> staged file",
        "AppleWin must not mount <font face='Courier'>evidence/</font> "
        "read-write (date stamps)",
    ]))

    story.append(p("Disk account (context, not a failure)", h1))
    story.append(p(
        "Overall <b>359,323 / 430,080</b> identical; every remaining "
        "difference is named in "
        "<font face='Courier'>probe_diskset.py</font> and balanced on "
        "the last <font face='Courier'>build_all</font> run. The large "
        "in-place gap is mostly <b>SYSTEM.LIBRARY</b> plus the archived "
        "64K pair and the remainders above.",
    ))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawString(
            0.75 * inch, 0.5 * inch,
            "PascalRecon — Grok Review outstanding issues")
        canvas.drawRightString(
            letter[0] - 0.75 * inch, 0.5 * inch, f"page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        str(OUT), pagesize=letter,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.7 * inch, bottomMargin=0.75 * inch,
        title="Grok Review — Outstanding Issues and Concerns",
        author="Grok Review",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
