#!/usr/bin/env python3
"""AI-screening safety and clarity signals for a resume.

Usage:
  python ai_signals.py resume.pdf [--json-file resume.json] [--json]

Two parts:
  1. HIDDEN TEXT SCAN (PDF): finds text a human cannot see but an AI or parser reads:
     white or near-white text, tiny text, text outside the page, zero-width characters,
     injection-style phrases, keyword-stuffed metadata. Hidden text is never acceptable:
     employers now scan for it, and some templates contain it by accident.
  2. CLARITY SIGNALS (from resume.json, optional): how much checkable evidence the resume
     gives a reader or model: numbers, named tools, vague words, date consistency.

Honest limits: this checks the file, not any employer's model. Exit code 1 if hidden text
is found.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import bullets_of, load, strip_md  # noqa: E402

INJECT = re.compile(
    r"ignore (all |any )?(previous|prior|above) (instructions|prompts)|rate (this|the) candidate|"
    r"rank (this|me)|10\s*/\s*10|perfect candidate|best candidate|hire (me|this)|"
    r"system prompt|as an ai|you are (an?|the) (ai|assistant|recruiter)|do not (mention|reveal)|"
    r"disregard|score (this|me) (highly|10)|top candidate", re.I)
ZW = re.compile("[\u200b\u200c\u200d\u2060\ufeff]")
VAGUE = ["various", "numerous", "multiple", "many", "several", "significant", "significantly", "successful",
         "successfully", "extensive", "a lot", "wide range", "strong", "excellent", "key", "major"]
STOP = set("the and for with that this from have has are was were you your our their into over than then "
           "using used use new work worked working team".split())


def near_white(col):
    if col is None:
        return False
    if isinstance(col, (int, float)):
        col = (col,)
    col = tuple(col)
    if len(col) == 1:
        return col[0] >= 0.94
    if len(col) == 3:
        return min(col) >= 0.94
    if len(col) == 4:  # CMYK
        return max(col) <= 0.04
    return False


def scan_pdf(path):
    import pdfplumber
    out = {"white": [], "tiny": [], "offpage": [], "zero_width": 0, "inject": [], "meta": [], "stuff": []}
    words = []
    with pdfplumber.open(path) as doc:
        for pn, p in enumerate(doc.pages, 1):
            groups = {"white": [], "tiny": [], "offpage": []}
            for c in p.chars:
                t = c["text"]
                if t.isspace():
                    continue
                if near_white(c.get("non_stroking_color")):
                    groups["white"].append(t)
                if c.get("size", 10) < 4:
                    groups["tiny"].append(t)
                if c["x1"] < -1 or c["x0"] > p.width + 1 or c["bottom"] < -1 or c["top"] > p.height + 1:
                    groups["offpage"].append(t)
            for k, chars in groups.items():
                if chars:
                    out[k].append((pn, "".join(chars)[:140]))
            txt = p.extract_text() or ""
            out["zero_width"] += len(ZW.findall(txt))
            out["inject"] += [m.group(0) for m in INJECT.finditer(txt)]
            words += re.findall(r"[a-z][a-z+#.]{3,}", txt.lower())
        meta = doc.metadata or {}
    for k, v in meta.items():
        if isinstance(v, str) and (len(v) > 300 or INJECT.search(v)):
            out["meta"].append(f"{k}: {v[:100]}")
    tot = len(words) or 1
    for w, n in Counter(w for w in words if w not in STOP).most_common(3):
        if n >= 9 and n / tot > 0.03:
            out["stuff"].append(f"\u201c{w}\u201d appears {n} times ({100*n/tot:.1f}% of words)")
    return out


def clarity(data):
    bl = [strip_md(t) for _, t in bullets_of(data)]
    if not bl:
        return None
    n = len(bl)
    nums = sum(bool(re.search(r"\d", b)) for b in bl)
    tools = sum(bool(re.search(r"\b[A-Z][A-Za-z+#.]{2,}\b.*\b[A-Z][A-Za-z+#.]{1,}\b|\b[A-Za-z]+\.js\b|\bAPI\b|\bSQL\b", b[1:])) for b in bl)
    vague = [(b[:60], w) for b in bl for w in VAGUE if re.search(r"\b" + w + r"\b", b, re.I)]
    long_ = sum(len(b) > 230 for b in bl)
    years = []
    for sec in data.get("sections", []):
        for it in sec.get("items", []):
            m = re.findall(r"(?:19|20)\d{2}", it.get("dates", "") or "")
            if m:
                a = int(m[0]); e = int(m[-1]) if len(m) > 1 else a
                if "present" in (it.get("dates", "").lower()):
                    e = 2026
                years.append((sec.get("title"), it.get("role") or it.get("name") or it.get("org"), a, e))
    issues = []
    for t, name, a, e in years:
        if e < a:
            issues.append(f"End year before start year in \u201c{name}\u201d")
    return {"bullets": n, "with_numbers": nums, "with_named_tools": tools, "vague": vague[:6],
            "too_long": long_, "date_issues": issues}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf")
    ap.add_argument("--json-file")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    s = scan_pdf(a.pdf)
    found = bool(s["white"] or s["tiny"] or s["offpage"] or s["zero_width"] or s["inject"] or s["meta"])
    c = clarity(load(a.json_file)) if a.json_file else None
    if a.json:
        print(json.dumps({"hidden_text_found": found, "scan": s, "clarity": c}, indent=2, ensure_ascii=False))
        sys.exit(1 if found else 0)
    print("HIDDEN TEXT SCAN: " + ("FOUND SOMETHING" if found else "clean"))
    labels = {"white": "White or near-white text", "tiny": "Tiny text (under 4pt)", "offpage": "Text outside the page"}
    for k, lab in labels.items():
        for pn, t in s[k]:
            print(f"  [ERROR] {lab} on page {pn}: \u201c{t}\u201d")
    if s["zero_width"]:
        print(f"  [ERROR] {s['zero_width']} zero-width character(s) in the text layer")
    for m in sorted(set(s["inject"])):
        print(f"  [ERROR] Instruction-like phrase aimed at an AI: \u201c{m}\u201d")
    for m in s["meta"]:
        print(f"  [WARN] Suspicious metadata: {m}")
    for m in s["stuff"]:
        print(f"  [WARN] Possible keyword stuffing: {m}")
    if found:
        print("  Remove it. Employers scan for hidden text, and some templates contain it by accident.")
    if c:
        print(f"\nCLARITY SIGNALS: {c['with_numbers']}/{c['bullets']} bullets contain a number, "
              f"{c['with_named_tools']}/{c['bullets']} name a tool or product, {c['too_long']} too long")
        for b, w in c["vague"]:
            print(f"  [WARN] Vague word \u201c{w}\u201d: {b}\u2026")
        for i in c["date_issues"]:
            print(f"  [WARN] {i}")
    sys.exit(1 if found else 0)


if __name__ == "__main__":
    main()
