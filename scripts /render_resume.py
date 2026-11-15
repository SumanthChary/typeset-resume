#!/usr/bin/env python3
"""Render a resume JSON file to a typeset PDF ("Edition 01").

Design: one column, Computer Modern (CMU Serif), small-caps name and section
headings, hairline rules, no colour, no icons, no tables used for layout in the
text layer. Text stays real and selectable so ATS parsers read it cleanly.

Usage:
  python render_resume.py resume.json -o resume.pdf [--page A4|LETTER]
         [--max-pages 1] [--md resume.md] [--min-scale 0.9]
Exit codes: 0 ok, 2 content does not fit in --max-pages even at --min-scale.
"""
import argparse
import functools
import io
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import FONT_DIR, die, load, strip_md, typo  # noqa: E402

try:
    from reportlab.lib.colors import black
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.platypus import (BaseDocTemplate, Frame, HRFlowable,
                                    KeepTogether, PageTemplate, Paragraph,
                                    Spacer, Table, TableStyle)
except ImportError:
    die("reportlab is required: pip install reportlab --break-system-packages")

FONTS = {
    "CMU": "CMUSerif-Regular.ttf",
    "CMU-Italic": "CMUSerif-Italic.ttf",
    "CMU-Bold": "CMUSerif-Bold.ttf",
    "CMU-BoldItalic": "CMUSerif-BoldItalic.ttf",
}


def register_fonts():
    for name, fn in FONTS.items():
        pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / fn)))
    pdfmetrics.registerFontFamily(
        "CMU", normal="CMU", bold="CMU-Bold", italic="CMU-Italic", boldItalic="CMU-BoldItalic"
    )


# ---------- text helpers ----------

def inline(text):
    """Escape XML, then allow **bold** and *italic*."""
    t = escape(typo(text))
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<i>\1</i>", t)
    return t


def smallcaps(text, size, ratio=0.8, bold=False):
    """Faux small caps: first letter of each word full size, rest smaller capitals."""
    words = [w for w in typo(text).split(" ") if w]
    out = []
    for w in words:
        first, rest = w[0].upper(), w[1:].upper()
        piece = escape(first)
        if rest:
            piece += '<font size="%.2f">%s</font>' % (size * ratio, escape(rest))
        out.append(piece)
    return " ".join(out)


def href(url):
    url = url.strip()
    if "@" in url and not url.startswith(("http", "mailto:")):
        return "mailto:" + url
    if not re.match(r"^[a-z]+://", url):
        return "https://" + url
    return url


def display_url(url):
    return re.sub(r"^(https?://|mailto:)", "", url.strip()).rstrip("/")


# ---------- styles ----------

def make_styles(s):
    base = dict(fontName="CMU", textColor=black, allowWidows=0, allowOrphans=0)
    return {
        "name": ParagraphStyle("name", fontSize=24 * s, leading=27 * s, alignment=TA_CENTER,
                               spaceAfter=2 * s, **{**base, "fontName": "CMU-Bold"}),
        "headline": ParagraphStyle("headline", fontSize=11.5 * s, leading=14 * s,
                                   alignment=TA_CENTER, spaceAfter=2 * s,
                                   **{**base, "fontName": "CMU-Italic"}),
        "contact": ParagraphStyle("contact", fontSize=9.6 * s, leading=12.4 * s,
                                  alignment=TA_CENTER, **base),
        "h": ParagraphStyle("h", fontSize=12.2 * s, leading=14 * s, spaceBefore=0,
                            **{**base, "fontName": "CMU-Bold"}),
        "body": ParagraphStyle("body", fontSize=10 * s, leading=13 * s, **base),
        "bullet": ParagraphStyle("bullet", fontSize=10 * s, leading=12.9 * s,
                                 leftIndent=13 * s, bulletIndent=2.5 * s,
                                 bulletFontName="CMU", bulletFontSize=10 * s,
                                 spaceAfter=1.6 * s, **base),
        "left_b": ParagraphStyle("left_b", fontSize=10.4 * s, leading=13 * s,
                                 **{**base, "fontName": "CMU-Bold"}),
        "left_i": ParagraphStyle("left_i", fontSize=10 * s, leading=12.6 * s,
                                 **{**base, "fontName": "CMU-Italic"}),
        "right": ParagraphStyle("right", fontSize=10 * s, leading=13 * s, alignment=TA_RIGHT, **base),
        "right_i": ParagraphStyle("right_i", fontSize=10 * s, leading=12.6 * s,
                                  alignment=TA_RIGHT, **{**base, "fontName": "CMU-Italic"}),
        "skill": ParagraphStyle("skill", fontSize=10 * s, leading=13 * s, spaceAfter=1.8 * s,
                                leftIndent=0, **base),
    }


# ---------- flowable builders ----------

def row(left_html, right_text, left_style, right_style, width, font_for_width):
    """Two-column line: left text, right-aligned text (dates/location)."""
    right_text = typo(right_text or "")
    rw = pdfmetrics.stringWidth(right_text, font_for_width, right_style.fontSize) + 8 if right_text else 0
    t = Table(
        [[Paragraph(left_html, left_style), Paragraph(escape(right_text), right_style)]],
        colWidths=[width - rw, rw] if rw else [width, 0],
    )
    t.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def heading(title, st, s, width):
    return [
        Paragraph(smallcaps(title, 12.2 * s, 0.8), st["h"]),
        HRFlowable(width="100%", thickness=0.55 * max(s, 0.9), color=black, spaceBefore=1.5 * s,
                   spaceAfter=4.2 * s),
    ]


def bullets(items, st):
    return [Paragraph(inline(b), st["bullet"], bulletText="\u2022") for b in items]


def entry(it, kind, st, s, width):
    """Return a list of flowables for one item (header + bullets)."""
    out = []
    if kind == "experience":
        out.append(row(inline(it.get("role", "")), it.get("dates"), st["left_b"], st["right"], width, "CMU"))
        if it.get("org") or it.get("location"):
            out.append(row(inline(it.get("org", "")), it.get("location"), st["left_i"], st["right_i"],
                           width, "CMU-Italic"))
    elif kind == "education":
        out.append(row(inline(it.get("org", "")), it.get("dates"), st["left_b"], st["right"], width, "CMU"))
        if it.get("degree") or it.get("location"):
            out.append(row(inline(it.get("degree", "")), it.get("location"), st["left_i"], st["right_i"],
                           width, "CMU-Italic"))
    else:  # projects and anything else with a name
        name = inline(it.get("name", it.get("role", "")))
        if it.get("link"):
            name = '<link href="%s">%s</link>' % (escape(href(it["link"])), name)
        left = "<b>%s</b>" % name
        if it.get("tagline"):
            left += " \u2013 " + inline(it["tagline"])
        out.append(row(left, it.get("dates"), st["left_b"], st["right"], width, "CMU"))
    lines = bullets(it.get("details", []), st) + bullets(it.get("bullets", []), st)
    if lines:
        out.append(Spacer(1, 1.2 * s))
        out.extend(lines)
    out.append(Spacer(1, 5.2 * s))
    # a plain list means "keep these together": header rows + spacer + first bullet
    n_head = 2 if kind in ("experience", "education") and (it.get("org") or it.get("degree") or it.get("location")) else 1
    group = out[: n_head + 2]
    return [group] + out[n_head + 2:]


def build_story(data, s, width):
    st = make_styles(s)
    b = data.get("basics", {})
    story = [Paragraph(smallcaps(b.get("name", ""), 24 * s, 0.88), st["name"])]  # 0.88 keeps the name on one text line for parsers
    if b.get("headline"):
        story.append(Paragraph(inline(b["headline"]), st["headline"]))
    if b.get("location"):
        story.append(Paragraph(inline(b["location"]), st["contact"]))
    bits = []
    if b.get("phone"):
        tel = "tel:" + re.sub(r"[^\d+]", "", b["phone"])
        bits.append('<link href="%s">%s</link>' % (tel, escape(typo(b["phone"]))))
    if b.get("email"):
        bits.append('<link href="%s">%s</link>' % (escape(href(b["email"])), escape(b["email"])))
    for l in b.get("links", []):
        label = l.get("label") or display_url(l.get("url", ""))
        bits.append('<link href="%s">%s</link>' % (escape(href(l.get("url", label))), escape(label)))
    if bits:
        story.append(Paragraph(" | ".join(bits), st["contact"]))
    story.append(Spacer(1, 7 * s))

    def section(title, flow):
        first = flow[0] if isinstance(flow[0], list) else [flow[0]]
        story.append(KeepTogether(heading(title, st, s, width) + first))
        for item in flow[1:]:
            story.append(KeepTogether(item) if isinstance(item, list) else item)
        story.append(Spacer(1, 4.5 * s))

    if data.get("summary"):
        section(data.get("summary_title", "Summary"), [Paragraph(inline(data["summary"]), st["body"])])
    for sec in data.get("sections", []):
        kind, title = sec.get("type", "list"), sec.get("title", sec.get("type", "").title())
        flow = []
        if kind in ("experience", "education", "projects"):
            for it in sec.get("items", []):
                flow.extend(entry(it, kind, st, s, width))
        elif kind == "skills":
            for g in sec.get("groups", []):
                flow.append(Paragraph("<b>%s:</b> %s" % (inline(g.get("label", "")), inline(g.get("items", ""))),
                                      st["skill"]))
        elif kind == "text":
            flow.append(Paragraph(inline(sec.get("text", "")), st["body"]))
        else:  # "list"
            flow.extend(bullets(sec.get("bullets", []), st))
        if flow:
            section(title, flow)
    return story


def build_pdf(data, page, s, margins):
    buf = io.BytesIO()
    lm, rm, tm, bm = margins
    doc = BaseDocTemplate(buf, pagesize=page, leftMargin=lm, rightMargin=rm, topMargin=tm,
                          bottomMargin=bm, title=typo(data["basics"].get("name", "Resume")) + " \u2013 Resume",
                          author=typo(data["basics"].get("name", "")), creator="typeset-resume")
    width = page[0] - lm - rm
    frame = Frame(lm, bm, width, page[1] - tm - bm, leftPadding=0, rightPadding=0, topPadding=0,
                  bottomPadding=0, id="main")
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame])])
    doc.build(build_story(data, s, width),
              canvasmaker=functools.partial(Canvas, initialFontName="CMU", initialFontSize=10))
    return buf.getvalue(), doc.page


def to_markdown(data):
    b = data.get("basics", {})
    L = ["# " + typo(b.get("name", ""))]
    if b.get("headline"):
        L.append("*" + typo(b["headline"]) + "*")
    contact = [x for x in [b.get("location"), b.get("phone"), b.get("email")] if x]
    contact += [("[%s](%s)" % (l.get("label") or display_url(l["url"]), href(l["url"]))) for l in b.get("links", [])]
    if contact:
        L.append(" | ".join(typo(c) for c in contact))
    if data.get("summary"):
        L += ["", "## " + data.get("summary_title", "Summary"), typo(data["summary"])]
    for sec in data.get("sections", []):
        kind, title = sec.get("type", "list"), sec.get("title", "")
        L += ["", "## " + typo(title)]
        for it in sec.get("items", []):
            head = it.get("role") or it.get("name") or it.get("org", "")
            sub = it.get("org") if it.get("role") else it.get("degree", it.get("tagline", ""))
            line = "### " + typo(head) + (" \u2013 " + typo(sub) if sub else "")
            meta = " \u00b7 ".join(typo(x) for x in [it.get("dates"), it.get("location")] if x)
            L.append(line)
            if meta:
                L.append("*" + meta + "*")
            for d in it.get("details", []) + it.get("bullets", []):
                L.append("- " + typo(d))
            L.append("")
        for g in sec.get("groups", []):
            L.append("- **%s:** %s" % (typo(g.get("label", "")), typo(g.get("items", ""))))
        if sec.get("text"):
            L.append(typo(sec["text"]))
        for bl in sec.get("bullets", []):
            L.append("- " + typo(bl))
    return "\n".join(L).replace("\n\n\n", "\n\n").strip() + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("resume_json")
    ap.add_argument("-o", "--out", default="resume.pdf")
    ap.add_argument("--page", default="A4", choices=["A4", "LETTER", "a4", "letter"])
    ap.add_argument("--max-pages", type=int, default=1)
    ap.add_argument("--min-scale", type=float, default=0.9, help="never shrink type below this (0.9 = 9pt body)")
    ap.add_argument("--max-scale", type=float, default=1.08,
                    help="short resumes are gently enlarged up to this scale so the page feels full, not empty")
    ap.add_argument("--md", help="also write a Markdown export here")
    a = ap.parse_args()

    data = load(a.resume_json)
    if not data.get("basics", {}).get("name"):
        die("resume.json needs basics.name")
    register_fonts()
    page = A4 if a.page.upper() == "A4" else letter
    margins = (0.72 * inch, 0.72 * inch, 0.6 * inch, 0.55 * inch)

    s = 1.0
    pdf, pages = build_pdf(data, page, s, margins)
    if pages > a.max_pages:  # too long: shrink gently, never below --min-scale
        while pages > a.max_pages and s > a.min_scale:
            s = round(s - 0.02, 2)
            pdf, pages = build_pdf(data, page, s, margins)
    else:  # fits: grow while it still fits, so short resumes breathe
        while s + 0.02 <= a.max_scale + 1e-9:
            trial, tpages = build_pdf(data, page, round(s + 0.02, 2), margins)
            if tpages > a.max_pages:
                break
            s, pdf, pages = round(s + 0.02, 2), trial, tpages

    Path(a.out).write_bytes(pdf)
    if a.md:
        Path(a.md).write_text(to_markdown(data), encoding="utf-8")
    msg = f"wrote {a.out} | {pages} page(s) | type scale {s:.2f} | {a.page.upper()}"
    print(msg)
    if pages > a.max_pages:
        print(f"WARNING: content needs {pages} pages even at scale {s:.2f}. Trim the weakest bullets "
              f"or allow --max-pages {pages}.", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
