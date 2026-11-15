#!/usr/bin/env python3
"""Check a resume for ATS safety (PDF) and writing quality (JSON).

Usage:
  python check_resume.py resume.json [--pdf resume.pdf] [--json]

PDF checks (when --pdf is given):
  - every text field from the JSON can be read back from the PDF with normal spaces
    (catches glued words like "ideato" that confuse ATS parsers)
  - fonts are embedded, page count
Writing checks (always):
  - leftover placeholders, weak openers, first person, buzzwords, AI-sounding words,
    em-dash overuse, repeated verbs, long/short bullets, bullets with no numbers.
Exit code 1 if any ERROR, else 0.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import bullets_of, iter_fields, load, strip_md, typo  # noqa: E402

WEAK_OPENERS = ["responsible for", "worked on", "helped", "assisted", "participated in", "involved in",
                "duties included", "tasked with", "was part of", "contributed to"]
BUZZ = ["results-driven", "results driven", "passionate", "hard-working", "hardworking", "team player",
        "detail-oriented", "detail oriented", "dynamic", "go-getter", "rockstar", "ninja", "guru",
        "synergy", "self-starter", "think outside the box", "proven track record", "highly motivated"]
AI_TELLS = ["delve", "tapestry", "seamlessly", "cutting-edge", "cutting edge", "robust", "testament",
            "elevate", "unlock", "harness", "in today's", "ever-evolving", "game-changer", "game changer",
            "spearhead", "leverag", "holistic", "transformative", "revolutioniz", "empower"]
FIRST_PERSON = re.compile(r"\b(I|my|me|I'm|I’ve|I've)\b")


def norm(s):
    s = strip_md(typo(s)).lower()
    s = s.replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    return re.sub(r"\s+", " ", s).strip()


def pdf_text(path):
    if shutil.which("pdftotext"):
        return subprocess.run(["pdftotext", "-enc", "UTF-8", str(path), "-"], capture_output=True,
                              text=True).stdout
    try:
        import pypdf
        return "\n".join(p.extract_text() or "" for p in pypdf.PdfReader(str(path)).pages)
    except Exception:
        return ""


def pdf_fonts_embedded(path):
    if not shutil.which("pdffonts"):
        return None
    rows = [l.split() for l in subprocess.run(["pdffonts", str(path)], capture_output=True,
                                              text=True).stdout.splitlines()[2:] if l.strip()]
    std14 = ("Helvetica", "Times", "Courier", "Symbol", "ZapfDingbats")  # unused base-font stubs are harmless
    rows = [r for r in rows if not r[0].startswith(std14)]
    return all(r[-5] == "yes" for r in rows) if rows else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("resume_json")
    ap.add_argument("--pdf")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    a = ap.parse_args()

    data = load(a.resume_json)
    findings = []  # (severity, where, message)

    def add(sev, where, msg):
        findings.append({"severity": sev, "where": where, "message": msg})

    b = data.get("basics", {})
    if not b.get("email"):
        add("ERROR", "basics.email", "No email address. Recruiters need one.")
    if not b.get("name"):
        add("ERROR", "basics.name", "No name.")

    # ---- placeholders ----
    for path, text in iter_fields(data):
        if re.search(r"\[(add|todo|tbd|number|x+|\?)[^\]]*\]|\bTODO\b|lorem ipsum", text, re.I):
            add("ERROR", path, f"Unfilled placeholder: {text[:70]}")

    # ---- PDF readability ----
    pages = None
    if a.pdf:
        raw = pdf_text(a.pdf)
        if not raw.strip():
            add("ERROR", "pdf", "No extractable text. An ATS would see an empty page.")
        else:
            spaced = norm(raw)
            squashed = re.sub(r"\s+", "", spaced)
            glued, missing = [], []
            for path, text in iter_fields(data):
                t = norm(text)
                if not t or len(t) < 4:
                    continue
                if t in spaced:
                    continue
                if re.sub(r"\s+", "", t) in squashed:
                    glued.append((path, text))
                else:
                    missing.append((path, text))
            for path, text in glued[:8]:
                add("ERROR", path, f"Words are glued or split in the PDF text layer: {text[:60]}")
            for path, text in missing[:8]:
                add("ERROR", path, f"Text not found in the PDF (font glyph missing?): {text[:60]}")
        try:
            import pypdf
            pages = len(pypdf.PdfReader(a.pdf).pages)
        except Exception:
            pages = None
        emb = pdf_fonts_embedded(a.pdf)
        if emb is False:
            add("WARN", "pdf", "Some fonts are not embedded; text may render differently on other machines.")

    # ---- writing quality ----
    starts = Counter()
    n_bul, n_num = 0, 0
    for path, text in bullets_of(data):
        t = strip_md(typo(text)).strip()
        low = t.lower()
        n_bul += 1
        if re.search(r"\d", t):
            n_num += 1
        first = re.sub(r"[^a-z]", "", low.split(" ")[0]) if low else ""
        starts[first] += 1
        for w in WEAK_OPENERS:
            if low.startswith(w):
                add("WARN", path, f"Weak opener \u201c{w}\u201d. Start with what you did: {t[:60]}")
        if FIRST_PERSON.search(t):
            add("WARN", path, f"First person in a bullet: {t[:60]}")
        if len(t) > 230:
            add("WARN", path, f"Long bullet ({len(t)} chars). Aim for two lines or less: {t[:50]}\u2026")
        if len(t) < 28:
            add("INFO", path, f"Very short bullet: {t}")
    for word, n in starts.items():
        if word and n >= 3:
            add("WARN", "bullets", f"The verb \u201c{word}\u201d starts {n} bullets. Vary the openers.")
    if n_bul >= 4 and n_num / max(n_bul, 1) < 0.35:
        add("INFO", "bullets", f"Only {n_num} of {n_bul} bullets contain a number. Add scale, speed, money or users where true.")

    alltext = " \n".join(t for _, t in iter_fields(data)).lower()
    for w in BUZZ:
        if w in alltext:
            add("WARN", "text", f"Empty buzzword: \u201c{w}\u201d. Replace with a fact.")
    hits = sorted({w for w in AI_TELLS if w in alltext})
    if hits:
        add("WARN", "text", "AI-sounding words a recruiter may notice: " + ", ".join(hits))
    em = alltext.count("\u2014")
    if em > 2:
        add("WARN", "text", f"{em} em dashes. Heavy em-dash use reads as AI-written; use commas or full stops.")

    if pages and pages > 2:
        add("WARN", "pdf", f"{pages} pages. Most recruiters want one page (two at most for senior roles).")

    sev_order = {"ERROR": 0, "WARN": 1, "INFO": 2}
    findings.sort(key=lambda f: sev_order[f["severity"]])
    errors = [f for f in findings if f["severity"] == "ERROR"]

    if a.json:
        print(json.dumps({"ok": not errors, "pages": pages, "findings": findings}, indent=2))
    else:
        head = "PASS" if not errors else "FAIL"
        print(f"{head}: {len(errors)} error(s), {sum(f['severity']=='WARN' for f in findings)} warning(s), "
              f"{sum(f['severity']=='INFO' for f in findings)} note(s)" + (f" | {pages} page(s)" if pages else ""))
        for f in findings:
            print(f"  [{f['severity']}] {f['where']}: {f['message']}")
        if a.pdf and not any("PDF" in f["message"] or f["where"] == "pdf" for f in errors):
            print("  [OK] PDF text layer reads back cleanly with normal spaces.")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
