# Role playbooks and tailoring

## Section order by situation
- **Student or fresh graduate**: Education, Projects, Experience (internships, freelance), Skills, Achievements.
- **Early career (0 to 3 years)**: Experience, Projects, Education, Skills.
- **Experienced (4+ years)**: Summary, Experience, Skills, Education. Projects only if relevant.
- **Career changer**: Summary naming the target role, Projects or relevant Experience first, transferable skills, then the rest.
- **Freelancer or founder**: group clients or products under one heading with concrete results per product; state what was shipped and who used it. Say "sold" or "acquired" only if it happened.
- **Academic CV** (allowed two or more pages, `--max-pages 3`): Education, Publications, Research, Teaching, Awards, Skills.

## Per-field defaults
- Headline: target role plus specialty, plain ("Backend Engineer | Payments").
- Education details: only coursework or honours that support the target role.
- Hackathons and certificates: one line each at the end, never above real experience.

## Tailoring to a job description
1. Extract the 6 to 10 requirements that matter (tools, outcomes, domain, seniority). Ignore boilerplate.
2. Map each to **real** evidence in the user's material. Write a short table in your head: requirement, evidence, strength.
3. Reorder sections and bullets so the strongest evidence for the top requirements comes first; rewrite those bullets to lead with the matching skill or outcome using the job's own vocabulary where it is true.
4. Cut or compress what does not support the role.
5. Tell the user which requirements have no evidence yet and what small, honest step could create it (a small project, a certification, a question about whether they did it and forgot).
6. Run `ats_analyze.py resume.pdf --jd job.txt` and report the matched and missing terms. Missing terms are not a to-do list for stuffing.
7. Save as a separate file per company. Never overwrite the base resume.

## Questions that unlock strong bullets
- How many people used it, and what changed for them?
- What got faster, cheaper, bigger or more reliable, and by how much?
- What did you own that nobody asked you to?
- Which tools did you actually use daily?
- Any rank, award, quote or result you are proud of?
