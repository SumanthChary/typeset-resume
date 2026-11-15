#!/usr/bin/env python3
"""Show what changed between two resume JSON files as tracked changes.

Usage:
  python diff_resume.py before.json after.json [-o changes.md]

Output is Markdown the user can approve line by line:
  ~~old text~~   removed or replaced
  **new text**   added or rewritten
Every change gets an id (C1, C2, ...) so the user can say "accept C1, C3, reject C2".
"""
import argparse
import difflib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import load, strip_md  # noqa: E402


def item_key(sec, it):
    kind = sec.get("type")
    if kind == "experience":
        return f"{it.get('role', '')} \u00b7 {it.get('org', '')}"
    if kind == "education":
        return it.get("org", "")
    return it.get("name", it.get("role", it.get("org", "")))


def flat(data):
    """-> ordered dict: (section, item) -> list of lines (bullets, details, skills groups, text)."""
    out = {}
    out[("Header", "headline")] = [data.get("basics", {}).get("headline", "")]
    out[("Summary", "")] = [data.get("summary", "")] if data.get("summary") else []
    for sec in data.get("sections", []):
        title = sec.get("title", sec.get("type", ""))
        if sec.get("items"):
            for it in sec["items"]:
                lines = list(it.get("details", [])) + list(it.get("bullets", []))
                for k in ("dates", "location", "degree", "tagline"):
                    if it.get(k):
                        lines.insert(0, f"[{k}] {it[k]}")
                out[(title, item_key(sec, it))] = lines
        elif sec.get("groups"):
            out[(title, "")] = [f"{g.get('label', '')}: {g.get('items', '')}" for g in sec["groups"]]
        elif sec.get("bullets"):
            out[(title, "")] = list(sec["bullets"])
        elif sec.get("text"):
            out[(title, "")] = [sec["text"]]
        else:
            out[(title, "")] = []
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("before")
    ap.add_argument("after")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    A, B = flat(load(a.before)), flat(load(a.after))
    A = {k: [strip_md(x) for x in v] for k, v in A.items()}
    B = {k: [strip_md(x) for x in v] for k, v in B.items()}
    lines, n = [], 0

    def cid():
        nonlocal n
        n += 1
        return f"C{n}"

    keys = list(B.keys()) + [k for k in A if k not in B]
    for key in keys:
        sec, item = key
        label = f"{sec}" + (f" \u00b7 {item}" if item else "")
        if key not in A:
            body = [f"- {cid()} **added** \u2192 " + (f"**{x}**" if x else "") for x in B[key]] or [f"- {cid()} **new section/item**"]
            lines += [f"### {label}"] + body
            continue
        if key not in B:
            lines += [f"### {label}", f"- {cid()} ~~whole entry removed~~"] + [f"  - ~~{x}~~" for x in A[key]]
            continue
        sm = difflib.SequenceMatcher(None, A[key], B[key], autojunk=False)
        block = []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                continue
            old, new = A[key][i1:i2], B[key][j1:j2]
            if tag == "replace":
                for k in range(max(len(old), len(new))):
                    o = old[k] if k < len(old) else None
                    nw = new[k] if k < len(new) else None
                    if o and nw:
                        block.append(f"- {cid()} ~~{o}~~\n  \u2192 **{nw}**")
                    elif o:
                        block.append(f"- {cid()} ~~{o}~~ (removed)")
                    else:
                        block.append(f"- {cid()} **{nw}** (added)")
            elif tag == "delete":
                block += [f"- {cid()} ~~{o}~~ (removed)" for o in old]
            elif tag == "insert":
                block += [f"- {cid()} **{x}** (added)" for x in new]
        if block:
            lines += [f"### {label}"] + block
    report = f"# Changes ({n})\n\nLegend: ~~removed~~ \u00b7 **added**. Say which ids to accept or reject.\n\n" + "\n".join(lines) + "\n"
    if n == 0:
        report = "# Changes (0)\n\nNo differences.\n"
    if a.out:
        Path(a.out).write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
