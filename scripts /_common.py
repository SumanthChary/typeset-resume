"""Shared helpers for typeset-resume scripts.

Keep this file dependency-free so check/diff scripts run anywhere.
"""
import json
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
FONT_DIR = SKILL_DIR / "assets" / "fonts"


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def typo(s):
    """Light typographic cleanup applied identically in the PDF, Markdown and checks.

    - curly apostrophes and quotes
    - '--' becomes an en dash
    - collapses repeated spaces
    The user's words are never changed, only their punctuation.
    """
    if not isinstance(s, str):
        return s
    s = s.replace("--", "\u2013")
    s = re.sub(r"(\w)'(\w)", "\\1\u2019\\2", s)
    s = re.sub(r"(\w)'(\s|$)", "\\1\u2019\\2", s)
    s = re.sub(r'"(\S)', "\u201c\\1", s)
    s = s.replace('"', "\u201d")
    s = re.sub(r"[ \t]{2,}", " ", s)
    return s.strip()


def strip_md(s):
    """Remove the tiny inline markdown we allow (**bold**, *italic*)."""
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"\1", s)
    return s


def iter_fields(data):
    """Yield (path, text) for every text field in a resume JSON."""
    b = data.get("basics", {})
    for k in ("name", "headline", "location", "email", "phone"):
        if b.get(k):
            yield f"basics.{k}", b[k]
    for i, l in enumerate(b.get("links", [])):
        yield f"basics.links[{i}]", l.get("label") or l.get("url", "")
    if data.get("summary"):
        yield "summary", data["summary"]
    for si, sec in enumerate(data.get("sections", [])):
        t = sec.get("title", sec.get("type", "section"))
        base = f"sections[{si}]({t})"
        yield base + ".title", t
        if sec.get("text"):
            yield base + ".text", sec["text"]
        for b_i, b_ in enumerate(sec.get("bullets", [])):
            yield f"{base}.bullets[{b_i}]", b_
        for g_i, g in enumerate(sec.get("groups", [])):
            yield f"{base}.groups[{g_i}].label", g.get("label", "")
            yield f"{base}.groups[{g_i}].items", g.get("items", "")
        for ii, it in enumerate(sec.get("items", [])):
            for k in ("role", "org", "degree", "name", "tagline", "dates", "location"):
                if it.get(k):
                    yield f"{base}.items[{ii}].{k}", it[k]
            for b_i, b_ in enumerate(it.get("bullets", [])):
                yield f"{base}.items[{ii}].bullets[{b_i}]", b_
            for d_i, d_ in enumerate(it.get("details", [])):
                yield f"{base}.items[{ii}].details[{d_i}]", d_


def bullets_of(data):
    """Yield (path, text) for bullet-like lines only (what recruiters scan)."""
    for path, text in iter_fields(data):
        if ".bullets[" in path:
            yield path, text


def die(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)
