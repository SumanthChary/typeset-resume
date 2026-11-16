# Contributing

Thanks for helping make resumes better.

## The most useful contribution: a resume that broke
Open an issue using the **Resume broke** template. **Remove personal details first** (name, phone, email, employers if sensitive). A short anonymised `resume.json` plus what you expected is perfect.

## Ground rules
- One design on purpose. We do not add colours, icons, photos or columns. Improvements to typography, spacing and fit are welcome.
- Honesty rules are sacred: the skill must never invent facts or help hide text.
- Keep scripts dependency-light (reportlab, pdfplumber, pypdf).
- Every change to a script should keep `check_resume.py` and `ats_analyze.py` passing on `typeset-resume/examples/sample-resume.json`.

## Development
```bash
pip install reportlab pdfplumber pypdf
python3 typeset-resume/scripts/render_resume.py typeset-resume/examples/sample-resume.json -o out.pdf
python3 typeset-resume/scripts/check_resume.py typeset-resume/examples/sample-resume.json --pdf out.pdf
python3 typeset-resume/scripts/ats_analyze.py out.pdf
python3 typeset-resume/scripts/ai_signals.py out.pdf --json-file typeset-resume/examples/sample-resume.json
```
