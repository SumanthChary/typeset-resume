# typeset-resume

**A Claude skill that turns messy career notes into a resume that looks like someone cared.**

One design. Real typography. Honest writing. An ATS check that tells you the truth.

Most resume tools give you fifty templates and a pile of adjectives. This skill does the opposite: a single carefully typeset page (Computer Modern serif, small-caps headings, hairline rules), bullets that lead with proof, nothing invented, and a report of every change so you stay in control.

---

## What you get

- **A one-page PDF** in a classic, quiet, LaTeX-style design. Real selectable text, fonts embedded, A4 or US Letter.
- **Bullets that sound like you**: plain verbs, specific results, no buzzwords, no "AI voice".
- **Tracked changes** when it edits an existing resume: ~~old~~ then **new**, with ids so you can accept or reject each one.
- **An ATS analyzer** that reads any resume PDF the way a parser would and tells you what breaks.
- **Job tailoring** that reorders real evidence for a role and tells you which requirements you have no proof for yet.
- **A Markdown export** of the same resume.

## Install

**Claude.ai**: download `typeset-resume.skill`, open *Settings > Skills* (or *Capabilities*), upload it, then say *"Make me a resume from this"* and attach or paste your material.

**Claude Code**: copy the `typeset-resume/` folder into `~/.claude/skills/` and restart.

Requirements: Python 3, `reportlab` (renders the PDF) and `pdfplumber` (ATS analysis). Poppler's `pdftotext` is used when present for extra checks. If an import fails, run `pip install reportlab pdfplumber pypdf`.

## Try these prompts

- *"Here is my old resume. Make it one page and fix the weak bullets."*
- *"Tailor my resume to this job description"* (paste it)
- *"Will this resume pass an ATS?"* (attach any PDF)
- *"Will AI pick my resume for this job?"* (paste the job description)
- *"Add a Skills section and a Writing section."*
- *"I have no experience yet. Build a resume from my projects and college work."*

## How it works

1. **Intake**: reads what you gave it, then asks at most five proof-seeking questions in one batch (numbers, scale, results).
2. **Structure**: builds a `resume.json`, an ordered list of sections, so adding, removing and reordering is trivial.
3. **Write**: applies the bullet rules in `references/writing-rules.md`. It never invents employers, dates, titles or numbers. Missing proof becomes a question, not a guess.
4. **Render and verify**: fits the page by gently adjusting type size (never below 9pt), then runs the checkers.
5. **Review**: shows tracked changes; you accept or reject.
6. **Deliver**: the PDF plus a short note and the questions that would make it stronger.

## The ATS analyzer

```bash
python3 scripts/ats_analyze.py resume.pdf --jd job.txt
```

It looks for the failure modes that actually mangle resumes:

- words that glue together in the text layer (a visible space with no space character)
- multi-column layouts and tables that scramble reading order
- scanned or image-only pages
- private-use symbol bullets that parsers show as boxes
- missing standard headings (Experience, Education, Skills) and missing contact details
- with a job description: matched vs missing terms, weighted

You get a transparent 0 to 100 score with the rubric printed, plus **what a parser sees** in the first lines.

**Honest limits.** Real ATS products differ and none publish their parsers. Different extractors can read the same PDF differently (this tool found one resume that one extractor read cleanly and another glued together). A high score means "unlikely to be mangled", not "will get interviews". Missing keywords matter only if you truly have the skill; never stuff keywords.

## Will AI pick yours? (AI screening readiness)

Employers increasingly use language models to summarise and rank resumes. This mode helps you be **clear and checkable**, not sneaky:

- **Hidden text scan** (`scripts/ai_signals.py`): finds white, near-white, tiny or off-page text, zero-width characters, instruction-like phrases aimed at an AI, and stuffed metadata. A 2026 study of about 200,000 real resumes found hidden prompt injections in roughly 1%, and some people use templates that contain hidden text without knowing it. This check protects you from both.
- **Screener simulation**: Claude plays a sceptical screener against a job description: requirement-by-requirement evidence with exact quotes, risk flags, a 0 to 100 estimate and a Shortlist, Maybe or Pass verdict, plus three honest fixes.
- **Clarity signals**: numbers, named tools, vague words and date consistency.

Honest limits: the verdict is an estimate from a simulated screener, not any employer model. The skill never adds hidden text or stuffs keywords, even if asked.

## Design principles

- **Quality over quantity.** One template. No colours, icons, photos, columns or skill bars.
- **Proof over adjectives.** Every bullet should survive an interview question.
- **Nothing invented.** The honesty rules are the most important part of the skill.
- **You approve every change.** No silent rewrites.
- **Readable by machines too.** One column, standard headings, real text.

## Command line

```bash
python3 scripts/render_resume.py resume.json -o Name_Resume.pdf --page A4 --md Name_Resume.md
python3 scripts/check_resume.py resume.json --pdf Name_Resume.pdf
python3 scripts/ats_analyze.py Name_Resume.pdf --jd job.txt
python3 scripts/ai_signals.py Name_Resume.pdf --json-file resume.json
python3 scripts/diff_resume.py resume.before.json resume.json -o changes.md
```

`render_resume.py` options: `--page A4|LETTER`, `--max-pages N`, `--min-scale 0.9`, `--max-scale 1.08`. It exits with code 2 if the content cannot fit in `--max-pages`; trim the weakest bullets instead of shrinking the type.

## Repository layout

```
typeset-resume/
  SKILL.md                 workflow and rules Claude follows
  scripts/                 render, check, ATS analysis, diff
  references/              schema, writing rules, role playbooks
  examples/sample-resume.json
  assets/fonts/            CMU Serif (OFL) bundled so nothing needs the network
```

## Limitations

- English-language resumes; fonts cover most Latin scripts but not CJK or Indic scripts.
- One page by default; long academic CVs need `--max-pages`.
- The ATS score is a heuristic, not a vendor simulation.
- Tested so far on a small number of resumes. Please open an issue with failures.

## Roadmap

- A second design edition as a limited drop (quality, not quantity)
- Cover letters in the same typography
- A visual editor with tracked changes and history (in development)

## Credits and licence

Code: MIT, see `LICENSE`. Fonts: CMU Serif from the Computer Modern Unicode family by Andrey V. Panov, under the SIL Open Font License 1.1 (`assets/fonts/OFL.txt`). Not affiliated with Anthropic.
