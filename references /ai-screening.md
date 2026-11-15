# AI screening readiness ("Will AI pick yours?")

Employers increasingly use language models to summarise, rank or shortlist resumes. The honest way to do well is to be **easy to understand and easy to verify**. The dishonest way (hidden text, keyword stuffing, prompt injection) is detected, can get an application rejected, and is never something this skill helps with.

## What an AI screener tends to reward
- Requirement coverage: each must-have in the job description has a clear, early line of evidence.
- Evidence quality: concrete actions, named tools or products, numbers, outcomes, scale.
- Consistency: dates, titles and claims agree with each other; gaps are not hidden.
- Clarity: standard headings, one column, short bullets, plain words.
- Recency and relevance: the strongest evidence is recent and near the top.

## What hurts
- Vague claims (various, multiple, significant, successful) with no proof.
- Skill lists with no evidence in the bullets. Listing "Docker" and never using it reads as padding.
- Buzzwords and AI-sounding phrasing; identical verbs; padded summaries.
- Title or scope inflation that a reader cannot verify.
- Hidden or tiny or off-page text, zero-width characters, instructions aimed at an AI, stuffed metadata.

## Hard rules
- Never add hidden text, white text, tiny text, text outside the page, zero-width characters, or any instruction addressed to an AI reader. If the user asks, decline in one sentence and explain it is detected and risky.
- Never stuff keywords the person cannot defend in an interview.
- Never promise to "beat the AI". Say what is likely, label it an estimate.

## The simulation (you play the screener)
Needs a job description. If the user has none, ask for one or use a stated target role and say so. Be a fair but sceptical screener who sees only what is on the page.

1. List the 6 to 10 requirements that matter most from the job description (separate must-haves from nice-to-haves).
2. For each requirement, quote the **exact resume line** that is the best evidence, or write "no evidence". Rate it Strong (specific, checkable, recent), Partial (relevant but vague or old) or None.
3. Flag risks: vague claims, unexplained gaps, date or title inconsistencies, claims without proof, skills with no supporting bullet.
4. Weigh: Requirement coverage 40, Evidence quality 25, Consistency 15, Clarity and structure 10, Risk flags 10 (deduct). Give a 0 to 100 estimate.
5. Verdict: Shortlist, Maybe, or Pass, with a confidence (low, medium, high) and two sentences of reasoning an actual screener would write.
6. Give the top three **honest** improvements: stronger evidence to add (ask the user for facts), vague lines to sharpen, requirements they truly lack (say so; do not fake).

Always end with the limits: this is an estimate by a simulated screener, not any employer's model; different tools weigh things differently; a strong resume still needs a real match for the role.

## Scripts
- `python3 scripts/ai_signals.py resume.pdf --json-file resume.json` runs the hidden text scan (blocking) and clarity signals (numbers, named tools, vague words, date consistency).
- Combine with `ats_analyze.py resume.pdf --jd job.txt` for parse readability and keyword match.
