#!/usr/bin/env python3
"""Analyze ANY resume PDF the way an applicant tracking system would read it.

Usage:
  python ats_analyze.py resume.pdf [--jd job.txt] [--json] [--show 30]

What it does (all local, heuristic, no network):
  1. Parse simulation: extracts the text layer in reading order and shows what a parser sees.
  2. Readability: finds glued words (visible gap but no space in the text layer), multi-column
     layouts, tables, scanned/image-only pages, private-use bullet glyphs.
  3. Structure: recognises section headings, contact details, dates, bullets.
  4. Keyword match against a job description (optional): matched vs missing terms, weighted.
  5. A transparent 0-100 score with the rubric printed, so nothing is a black box.

Honest limits: real ATS products differ and none publish their parsers. This tool finds the
common, well-known failure modes. A high score means "unlikely to be mangled", not "will get
interviews". Missing keywords matter only if the candidate truly has that skill.
"""
import argparse
import json
import re
import sys
from collections import Counter

try:
    import pdfplumber
except ImportError:
    sys.exit("pdfplumber is required: pip install pdfplumber --break-system-packages")

HEADINGS = {
    "summary": r"summary|profile|about|objective|professional summary",
    "experience": r"experience|work experience|professional experience|employment|work history",
    "education": r"education|academic background|qualifications",
    "projects": r"projects|selected projects|personal projects",
    "skills": r"skills|technical skills|core skills|key skills",
    "extras": r"achievements|awards|certifications|certificates|publications|volunteer(ing)?|extras|achievements & extras",
}
STOP = set("""a an and are as at be but by for from has have in into is it its of on or our that the their
this to was we were will with you your they them than then there these those who whom which while within
about above after again all also any can could do does each few more most other over same some such
than too very via per etc using use used new""".split())
GENERIC = set("""experience ability strong work working team role roles responsibilities requirements required
requirement years year skills skill knowledge preferred plus including include includes etc candidate
candidates company job position looking opportunity opportunities join benefits excellent good great
understanding proven demonstrated familiarity familiar must should well able across environment
environments business apply applicants applicant seeking qualified qualifications responsible
develop developing development building build manage managing support supporting collaborate
end comfortable fast moving fast-moving""".split())
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"(\+?\d[\d\s().-]{8,}\d)")
DATE = re.compile(r"\b(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|\d{1,2}/\d{4}|\d{4})\b")
MARK = "\x1f"  # internal marker for a missing space
PUA = re.compile("[\ue000-\uf8ff]")


def scan_chars(page):
    """Return (glued_examples, line_start_xs). Finds visible gaps that have no space character."""
    lines = {}
    for c in page.chars:
        lines.setdefault(round(c["top"] / 3), []).append(c)
    glued, starts = [], []
    for _, cs in sorted(lines.items()):
        cs.sort(key=lambda c: c["x0"])
        starts.append(cs[0]["x0"])
        word, marked = [], ""
        for c in cs:
            t = c["text"]
            if t.isspace():
                if marked and MARK in marked:
                    glued.append(marked)
                word, marked = [], ""
                continue
            if word:
                gap = c["x0"] - word[-1]["x1"]
                if gap > 3.0:  # extractors insert a space here
                    if MARK in marked:
                        glued.append(marked)
                    word, marked = [], ""
                elif (gap > 0.16 * c["size"] and t.isalpha() and word[-1]["text"].isalpha()
                      and not (t.isupper() and word[-1]["text"].isupper())):
                    marked += MARK  # visible space, but no space in the text layer
            word.append(c)
            marked += t
        if MARK in marked:
            glued.append(marked)
    return glued, starts


def collapse_letterspaced(line):
    return re.sub(r"\b(?:[A-Za-z]\s){3,}[A-Za-z]\b", lambda m: m.group(0).replace(" ", ""), line)


def terms(text):
    toks = re.findall(r"[A-Za-z][A-Za-z0-9+#.\-/]*[A-Za-z0-9+#]|[A-Za-z]", text)
    return [t.strip(".-/") for t in toks]


def stem(w):
    w = w.lower()
    for suf in ("ing", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[: -len(suf)]
    return w


def jd_keywords(jd, top=25):
    lines = [l.strip() for l in jd.splitlines() if l.strip()]
    score, shown = Counter(), {}
    in_req = False
    for l in lines:
        if re.match(r"^(requirements|qualifications|must have|what you.ll need|you have|skills)", l, re.I):
            in_req = True
        elif re.match(r"^(benefits|about us|what we offer|perks|responsibilities)", l, re.I):
            in_req = False
        w = 1.5 if in_req else 1.0
        if re.match(r"^[\u2022\-*\u2013\u25aa]", l):
            w += 0.5
        toks = terms(l)
        for i, t in enumerate(toks):
            lo = t.lower()
            if lo in STOP or lo in GENERIC or len(lo) < 2 or lo.isdigit():
                continue
            bonus = 1.0
            if re.search(r"[+#.0-9]", t) or (t[0].isupper() and i > 0) or t.isupper():
                bonus = 1.6  # likely a tool, language or proper term
            score[stem(lo)] += w * bonus
            shown.setdefault(stem(lo), t)
            if i + 1 < len(toks):
                n = toks[i + 1].lower()
                if n not in STOP and n not in GENERIC and len(n) > 2 and lo not in STOP:
                    bg = f"{stem(lo)} {stem(n)}"
                    score[bg] += w * 0.9
                    shown.setdefault(bg, f"{t} {toks[i + 1]}")
    ranked = [(k, v) for k, v in score.most_common(80)]
    out, used = [], set()
    for k, v in ranked:  # prefer bigrams that contain strong unigrams, avoid duplicates
        parts = k.split()
        if len(parts) == 1 and any(k in o[0].split() for o in out if " " in o[0]):
            continue
        if v < 2.0:
            continue
        out.append((k, v))
        if len(out) >= top:
            break
    return [(k, shown[k], v) for k, v in out]


def match_terms(resume_text, kws):
    toks = [stem(t) for t in terms(resume_text)]
    bag, joined = set(toks), " ".join(toks)
    got, miss = [], []
    for k, shown, v in kws:
        parts = k.split()
        ok = (all(p in bag for p in parts) and (len(parts) == 1 or k in joined)) if len(parts) > 1 else k in bag
        if len(parts) > 1 and not ok and all(p in bag for p in parts):
            ok = True
        (got if ok else miss).append((shown, v))
    return got, miss


def analyze(path, jd=None, show=30):
    r = {"findings": [], "sections": {}, "contact": {}, "score": {}}
    add = lambda sev, msg: r["findings"].append({"severity": sev, "message": msg})
    glued, starts, images, tables, texts = [], [], 0, 0, []
    with pdfplumber.open(path) as doc:
        r["pages"] = len(doc.pages)
        width = doc.pages[0].width
        for p in doc.pages:
            g, s = scan_chars(p)
            glued += g
            starts += s
            images += len(p.images)
            try:
                tables += len(p.find_tables())
            except Exception:
                pass
            texts.append(p.extract_text(x_tolerance=3, y_tolerance=3) or "")
    text = "\n".join(texts)
    lines = [collapse_letterspaced(l.strip()) for l in text.splitlines() if l.strip()]
    flat = "\n".join(lines)
    words = len(re.findall(r"\w+", flat))
    r["words"] = words
    r["parser_view"] = lines[:show]

    # ---- readability ----
    read = 40
    if words < 40:
        read = 0
        add("ERROR", "No readable text layer. This looks scanned or image-only; an ATS would see an empty page.")
    if glued:
        uniq = list(dict.fromkeys(glued))
        read -= min(30, 5 + 3 * len(uniq))
        add("ERROR", f"{len(uniq)} place(s) where a visible space is missing from the text layer, so words glue together "
                     f"when parsed. Examples: " + "; ".join(u.replace(MARK, " + ") for u in uniq[:5]))
    if PUA.search(text):
        read -= 5
        add("WARN", "Private-use symbol glyphs found (usually fancy bullets or icons). Parsers often show them as boxes.")
    if tables:
        read -= 6
        add("WARN", f"{tables} table-like structure(s). Some ATS read table cells out of order.")
    if images and words < 150:
        read -= 10
        add("WARN", "Page contains images and little text; text inside images is invisible to an ATS.")
    c = Counter(round(x / 12) * 12 for x in starts)
    main = c.most_common(1)[0][0] if c else 0
    far = sum(v for k, v in c.items() if k > main + width * 0.30)
    if starts and far / len(starts) > 0.22:
        read -= 8
        add("WARN", "Content starts in a second column. Multi-column layouts are the most common cause of scrambled order.")
    r["score"]["readability (40)"] = max(read, 0)

    # ---- structure ----
    found = {}
    for l in lines:
        clean = re.sub(r"[^A-Za-z& ]", "", l).strip().lower()
        if 0 < len(clean.split()) <= 4:
            for key, pat in HEADINGS.items():
                if re.fullmatch(pat, clean) and key not in found:
                    found[key] = l
    r["sections"] = found
    core = [k for k in ("experience", "education", "skills") if k in found]
    for k in ("experience", "education", "skills"):
        if k not in found:
            add("WARN", f"No clear \u201c{k.title()}\u201d heading found. Use standard headings so sections are recognised.")
    r["score"]["structure (20)"] = min(20, 7 * len(core))

    # ---- contact ----
    head = "\n".join(lines[:10])
    email, phone = EMAIL.search(flat), PHONE.search(head)
    link = re.search(r"linkedin\.com/in/[\w-]+|github\.com/[\w-]+", flat, re.I)
    r["contact"] = {"email": bool(email), "phone": bool(phone), "link": bool(link)}
    if not email:
        add("ERROR", "No email address found in the text layer.")
    if email and email.start() > len(flat) * 0.35:
        add("WARN", "Email is not near the top. Put contact details in the first lines (not in a header/footer).")
    r["score"]["contact (10)"] = 5 * bool(email) + 2 * bool(phone) + 3 * bool(link)

    # ---- dates & bullets ----
    dates = DATE.findall(flat)
    fmts = {("month" if re.match(r"[A-Za-z]", d) else "slash" if "/" in d else "year") for d in dates}
    if "month" in fmts and "slash" in fmts:
        add("INFO", "Mixed date formats (e.g. Sep 2024 and 09/2024). Pick one.")
    bullets = [l for l in lines if re.match(r"^[\u2022\u25aa\u25cf\-\u2013*]\s", l)]
    r["bullets"] = len(bullets)
    if words > 0 and len(bullets) < 3:
        add("INFO", "Few bullet points detected. Recruiters scan bullets, not paragraphs.")
    fmt = 10
    if r["pages"] == 3:
        fmt -= 5
    elif r["pages"] > 3:
        fmt = 0
    if words and not 250 <= words <= 800:
        fmt -= 3
        add("INFO", f"{words} words. Most strong resumes sit around 350 to 650.")
    r["score"]["format (10)"] = max(fmt, 0)

    # ---- job description match ----
    if jd:
        kws = jd_keywords(jd)
        got, miss = match_terms(flat, kws)
        tot = sum(v for _, v in got) + sum(v for _, v in miss) or 1
        pct = round(100 * sum(v for _, v in got) / tot)
        r["jd"] = {"match_pct": pct, "matched": [g for g, _ in got], "missing": [m for m, _ in miss]}
        r["score"]["keywords (20)"] = round(20 * pct / 100)
        if miss:
            add("INFO", "Missing job terms matter only if you truly have that skill. Add real evidence, never stuff keywords.")
    total = sum(r["score"].values())
    maxs = 100 if jd else 80
    r["total"] = round(100 * total / maxs)
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf")
    ap.add_argument("--jd", help="path to a text file with the job description")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--show", type=int, default=30, help="lines of the parser view to print")
    a = ap.parse_args()
    jd = open(a.jd, encoding="utf-8").read() if a.jd else None
    r = analyze(a.pdf, jd, a.show)
    if a.json:
        print(json.dumps(r, indent=2, ensure_ascii=False))
        return
    print(f"ATS READBACK SCORE: {r['total']}/100 (heuristic) | {r['pages']} page(s) | {r['words']} words")
    print("Rubric: " + ", ".join(f"{k} {v}" for k, v in r["score"].items()) +
          ("" if jd else "  [no job description given: scaled to 100]"))
    errs = [f for f in r["findings"] if f["severity"] == "ERROR"]
    print(f"\nProblems ({len(errs)} error(s)):" if r["findings"] else "\nNo problems found.")
    for f in sorted(r["findings"], key=lambda f: ["ERROR", "WARN", "INFO"].index(f["severity"])):
        print(f"  [{f['severity']}] {f['message']}")
    print("\nSections found: " + (", ".join(r["sections"]) or "none"))
    print("Contact: " + ", ".join(f"{k}={'yes' if v else 'NO'}" for k, v in r["contact"].items()))
    if jd:
        j = r["jd"]
        print(f"\nJob match: {j['match_pct']}% of weighted terms")
        print("  Found:   " + (", ".join(j["matched"][:15]) or "-"))
        print("  Missing: " + (", ".join(j["missing"][:15]) or "-"))
    print("\nWHAT A PARSER SEES (first lines):")
    for l in r["parser_view"]:
        print("  | " + l)
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
