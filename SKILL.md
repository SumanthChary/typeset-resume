---
name: typeset-resume
description: Create, rewrite, tailor and polish resumes and CVs into one beautifully typeset, ATS-safe PDF (Computer Modern serif, small-caps headings, hairline rules) with honest, specific bullets and a tracked-changes report. Use this skill whenever the user mentions a resume, CV, curriculum vitae, "improve my resume", "tailor my resume to this job", "will my resume pass ATS", "check my resume for ATS", "will AI choose my resume", "AI screening", "make AI love my resume", "AI-friendly resume", "make my resume look better", one-page resume, ATS-friendly resume, fixing weak bullets, or uploads or pastes a resume, LinkedIn profile or career history, even if they never ask for a PDF. Also use it to add or remove resume sections, cut a resume to one page, or turn rough notes into a first resume. If the user wants a Word file, still use this skill for the content and then the docx skill for the file.
---

# Typeset Resume

Turn messy career material into a resume that looks like a person cared: one design, perfect typography, specific writing, and nothing invented.

## The bar

A recruiter spends seconds on a resume. It must (1) look calm and professional at a glance, (2) be readable by ATS parsers, (3) lead with proof, not adjectives, and (4) be 100% true. Quality over quantity: there is exactly one template ("Edition 01"). Do not offer colours, icons, photos, columns or skill bars. Restraint is the product.

## Workflow

Follow these steps in order. Keep the conversation short; do the work, then show it.

### 1. Intake (ask only what you need)

Find out, from the conversation and any uploaded file first:
- **Source material**: an existing resume (PDF/DOCX/text), LinkedIn text, or rough notes. If a file is uploaded, read it with the right tool (pdftotext, or the pdf/docx skill) before asking anything.
- **Target**: a job description or a role type. Optional. If given, use tailoring mode.
- **Page size**: A4 for India, UK, EU, Australia; Letter for the US and Canada. If unknown, default to A4 and say so in one line.

If key facts are missing, ask them **in one batch of at most five questions**, then continue with what you get. Good questions are about proof: numbers (users, revenue, speed, scale), outcomes, team size, tools actually used, and dates. Never ask for things you can already see.

### 2. Build `resume.json`

Create `resume.json` in the working directory following `references/schema.md` (read it once). Sections are an ordered list, so you can reorder, add or delete sections freely. Choose the order for the reader using `references/role-playbooks.md` (students lead with Education; experienced people lead with Experience).

**Honesty rules (non-negotiable):**
- Never invent employers, titles, dates, degrees, tools, metrics, links, or outcomes.
- Keep every fact the user gave you. You may rephrase; you may not upgrade ("helped" to "led") without evidence.
- If a number would strengthen a bullet and you do not have it, write the bullet without it and list the question for the user. Do not guess a number. If you must leave a gap in the file, use `[add number]` so the checker blocks export.
- Estimates are allowed only if the user supplied them ("about 200 users").

### 3. Write the bullets

Read `references/writing-rules.md` before drafting. In short: start with a plain strong verb, say what you did, how or at what scale, and the result; one or two lines; vary the verbs; no buzzwords; no AI-sounding words; sound like the person, not like a press release. Use the user's own phrasing from their other lines as the voice reference.

### 4. Render and verify

Run from the skill folder (`<skill_dir>` is the folder containing this SKILL.md):

```bash
pip install reportlab --break-system-packages   # only if the import fails
python3 <skill_dir>/scripts/render_resume.py resume.json -o Name_Resume.pdf --page A4 --md Name_Resume.md
python3 <skill_dir>/scripts/check_resume.py resume.json --pdf Name_Resume.pdf
python3 <skill_dir>/scripts/ats_analyze.py Name_Resume.pdf [--jd job.txt]
```

- The renderer fits the content to **one page** by gently adjusting type size between 0.90x and 1.08x (never below 9pt body). If it still overflows it exits with code 2: cut the weakest bullets or the least relevant section, do not shrink further. Two pages are acceptable only for 10+ years of experience or academic CVs (`--max-pages 2`).
- The checker blocks on **ERRORS** (placeholders, missing email, text that an ATS cannot read back with proper spaces) and reports **warnings** (weak openers, buzzwords, AI-tell words, em-dash overuse, repeated verbs, long bullets). Fix every ERROR and every warning you agree with, then re-run. Stop after two fix rounds.
- Look at the result: `pdftoppm -r 80 -png Name_Resume.pdf preview` and view `preview-1.png`. Check that nothing is cramped, orphaned or misaligned.

### 5. Improving an existing resume? Show tracked changes

When the user already has a resume, keep their original as `resume.before.json` and your version as `resume.json`, then run:

```bash
python3 <skill_dir>/scripts/diff_resume.py resume.before.json resume.json -o changes.md
```

Present the changes as a short list with ids (C1, C2, ...), ~~old~~ then **new**, each with a one-line reason. Say "accept all, or tell me which ids to reject". Apply their decisions to `resume.json`, re-render, re-check. This is the "AI edits, you approve" loop; never silently rewrite someone's resume.

### 6. Deliver

- Save the PDF (and the Markdown export if useful) to `/mnt/user-data/outputs/` when that folder exists, then present the files. Name them `Firstname_Lastname_Resume.pdf`.
- Reply in a few lines: what you changed in plain words, anything you could not verify, and **the questions that would make it stronger** (numbers you lack). Do not paste the whole resume back into chat. Do not add a long explanation of the template.

## Modes

- **Create from notes**: interview in one batch, build, render, check.
- **ATS analysis** (the user uploads any resume PDF and asks if it will parse, or wants a job match): run `python3 <skill_dir>/scripts/ats_analyze.py resume.pdf [--jd job.txt]`. Report, in plain words: the score and what it measures, every ERROR and WARN with the fix, what the parser sees in the first lines (quote 3 to 5 of them), and with a job description the matched and missing terms. Be honest about limits: it is a heuristic that finds common failure modes (glued words, columns, tables, image-only text, odd bullet glyphs, missing headings or contact info), not a vendor ATS, and a high score does not predict interviews. Offer to rebuild the resume in this design if the problems are structural. Different parsers behave differently; say so if only some extractors show a problem.
- **AI screening readiness** ("Will AI pick yours?", "make AI love my resume"): first run `python3 <skill_dir>/scripts/ai_signals.py resume.pdf --json-file resume.json`. If it finds hidden text (white, tiny or off-page text, zero-width characters, instructions aimed at an AI), stop and tell the user plainly: remove it, it is detected and risky, and some templates contain it by accident. Then read `references/ai-screening.md` and play the screener against the job description: requirement-by-requirement evidence with exact quotes, risk flags, a 0 to 100 estimate, a Shortlist/Maybe/Pass verdict with confidence, and three honest fixes. Label it an estimate from a simulated screener, not an employer model. Offer to apply the fixes through the normal tracked-changes flow. Never add hidden text or stuff keywords, even if asked.
- **Improve**: step 5 flow with tracked changes.
- **Tailor to a job**: read `references/role-playbooks.md` (Tailoring). Extract the 6 to 10 requirements that matter, reorder sections and bullets so real evidence for them comes first, mirror the job's vocabulary only where it is true, and tell the user which requirements have no evidence yet. Never stuff keywords the user cannot defend in an interview. Save as `Name_Resume_<Company>.pdf`.
- **Add a section** (Skills, Projects, Achievements, Writing, Volunteering, Publications, Certifications): add it to `sections` using only information the user gave; use `type: "list"` or `"skills"` as fits.
- **Cut to one page**: remove the lowest-value bullets first, then older roles to a single line, then merge sections. Never reduce below 9pt.
- **Word or other formats**: render content here, then use the docx skill for .docx. The PDF from this skill is the reference design.

## Design is fixed

Do not edit the renderer's look for individual users. The only knobs are `--page`, `--max-pages`, `--min-scale` and `--max-scale`. If the user asks for colours, columns, icons or a photo, explain once, in one sentence, that the single clean design is deliberate and ATS-safe, and offer to improve the writing instead.

## Hard rules

- Real text only: the PDF must pass `check_resume.py` (no images of text, no glued words).
- One column. Standard headings (Summary, Experience, Education, Projects, Skills) so parsers recognise them.
- Quotes and apostrophes are curly, dates use an en dash (2024 – Present), bullets are plain. The renderer handles this.
- Contact line must include a working email. Links are clickable and shown as readable text.
- Do not include: photo, age, marital status, full address, "References available on request", an objective statement, or personal pronouns.
- Never claim the resume will "beat the ATS" or "beat the AI", and never guarantee interviews.
- Never add hidden, white, tiny or off-page text, zero-width characters, or instructions addressed to an AI reader.

## Files

- `scripts/render_resume.py` JSON to PDF (and Markdown), fit-to-page.
- `scripts/check_resume.py` writing lint plus a readback test of the PDF against the JSON.
- `scripts/ats_analyze.py` ATS simulation for any resume PDF: parser view, structure, readability, job-description keyword match, transparent score.
- `scripts/diff_resume.py` tracked-changes report between two versions.
- `scripts/ai_signals.py` hidden-text scan (white, tiny, off-page, zero-width, injection phrases) plus clarity signals.
- `references/ai-screening.md` how AI screeners read resumes, the simulation rubric, and the hard rules.
- `references/schema.md` the resume.json format and a full example pointer.
- `references/writing-rules.md` bullet formula, verbs, metrics, voice, banned phrases.
- `references/role-playbooks.md` section order and emphasis by situation, plus tailoring.
- `examples/sample-resume.json` a complete, valid example.
- `assets/fonts/` bundled CMU Serif (OFL licensed) so rendering never needs the network.
