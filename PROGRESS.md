# Project Progress Log

A rolling log. Append a new dated entry every working session. Newest at the top.

## 2026-06-11 (session 4) — Exposé visual design finalised; project infra (skills, CLAUDE.md, rules)

**Status:** Content of the exposé is frozen and unchanged from session 3 (same MOF framing, same 13 verified references). This session was about the *look* and the project's working infrastructure. Exposé is ready to send; next action is still the user emailing it to Jalali and uploading to Moodle by 21 June.

**Exposé deliverable, now canonical:**
- The user designed the exposé in Claude Design and handed off an HTML/CSS mockup (`Research proposal formatting-handoff.zip`). That design is now the source of truth.
- `docs/expose.html` = **primary editable source** (Lato bundled locally via `@font-face` from `docs/assets/fonts/`, real orange SRH logo at `docs/assets/srh_logo.jpg`, SRH-orange accents, dedicated cover page, uppercase section headings, borderless tables, clickable DOI links).
- `docs/expose.pdf` = **the deliverable**, rendered from the HTML with headless Chrome. **Render command** (re-run after any HTML edit):
  `"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --no-pdf-header-footer --virtual-time-budget=4000 --print-to-pdf="expose.pdf" "file:///Users/dev/Agentic%20Workflows%20/case-study-2/docs/expose.html"`
- **6 pages, A4** (user-approved: dedicated cover page + 5 pages content/refs; a cover page is not counted toward a content-page limit). Verified on the final PDF: **0 em dashes**, **13 clickable reference links**, logo present.
- Tightened body line-height (1.55→1.4) and section/paragraph margins to bring the design from 8 pages down to 6 without touching fonts, colours, or content.
- Superseded versions archived: `docs/expose.latex.bak.tex` (the Tectonic/LaTeX build, also valid, 5 pages, no cover), `docs/expose.v3.bak.docx` (Word/Aptos build), plus older `expose.v0/v1/v2.bak.docx`.

**Project infrastructure added this session:**
- `CLAUDE.md` created (commands, architecture, domain rules, integrity rules, writing-style rule, session workflow).
- Skills in `.claude/skills/`: `progress-log`, `verify-citation` (with stdlib `cite_check.py`), and `mynotes` (opens `MY_NOTES.md`, a gitignored private scratchpad).
- **Writing rule (user mandate): no em dashes anywhere** in project output; use comma/colon/parens; en dash only for ranges and "metal–organic". Saved to `CLAUDE.md` and memory.
- Tooling installed locally: Tectonic, LibreOffice, poppler. Chrome extension connected. These make docx/LaTeX/HTML → PDF rendering + visual verification possible for all future documents (useful again at Week 12 for the final report).
- `README.md` author corrected ("Abhi" → Devendra Singh Dhakad) and re-aimed TL;DR.

**Next (unchanged, deadline order):** user opens `docs/expose.pdf`, confirms it looks right, sends to `mehrdad.jalali@srh.de` (by ~12 June); incorporate any comments by 18 June; upload to Moodle by **21 June** regardless; project starts 22 June.

## 2026-06-10 (session 3) — Supervisor confirmed; project re-aimed to MOF synthesis KG; exposé v2

**Status:** Topic 6.2 + supervisor locked in Moodle ✓ (before the 5 June hard deadline). Prof. Jalali replied from `mehrdad.jalali@srh.de`: *"The topic is confirmed. Move forward."* Correction to the record: the long topic-lock email drafted in session 2 was **never sent** — a short topic-interest email went instead, so **Jalali has not yet seen any exposé**. Exposé share is now the top priority (Moodle upload hard deadline 21 June).

Decision (user-approved after research review): **re-aim within Topic 6.2 from "broad materials benchmarking" to "Building and Validating a MOF Synthesis Knowledge Graph with LLMs."** Rationale: (a) Bai et al. 2025 (npj Comput. Mater. 11:51) already built a 100k-paper LLM KG for framework materials incl. QA — the broad framing's novelty is gone; (b) MOFs are the supervisor's research line (MOFGalaxyNet, J. Cheminformatics 15:94); (c) DigiMOF + SynMOF enable a per-field validation/agreement study nobody has published, incl. open-weight vs. commercial cost analysis. Old benchmark framing is superseded.

Done in this session:
- `configs/ontology.json` → **v0.2, MOF-specific** (9 entities: MOF, MetalPrecursor, OrganicLinker, Solvent, SynthesisMethod, Condition, Property, Application, Paper; 9 relations; fixed v0.1's dangling `MEASURED_AT`→`Conditions`; refreshed open questions incl. DigiMOF/SynMOF field alignment). JSON validated, no dangling endpoints.
- **Fresh `docs/expose.docx`** (old v1 backed up to `docs/expose.v1.bak.docx`): new working title, MOF-validated-KG framing, revised RQs, SoTA repositioned around Bai 2025 + MOF text-mining lineage with Gap line, 5-row methodology table (de-scoped: 300–500 papers, 5k+/25k+ KG targets, KG-RAG QA as stretch), 12-week plan, **proper title block added** (v1 had none — name/matriculation/supervisor were missing entirely). 1,769 words, 13 references — every one verified against Crossref/OpenAlex/arXiv/Europe PMC this session. docx validation passed.
- `docs/supervisor_email_expose_share.md` — short share-email draft to `mehrdad.jalali@srh.de` (matches his brevity), attach exposé, comments-by-18-June + upload-by-21-June plan, pre-send checklist.
- `docs/literature_review.md` — 30 verified papers, themed A–F mapped to the revised RQs, abstract-level findings, cross-cutting observations, Weeks-1–2 reading plan (P0–P3).
- `docs/HANDOVER.md` — regenerated cross-chat handover (the May version was stale: wrong email narrative, old framing).
- Sanity: `pytest` green (1 passed); extractor interface untouched.
- **`CLAUDE.md` created** (auto-loaded project instructions for Claude Code: commands, architecture, domain rules, integrity rules, session workflow).
- **Project skills created** in `.claude/skills/`: `progress-log` (this log's format + rules) and `verify-citation` (SKILL.md + stdlib `cite_check.py` for Crossref/OpenAlex/arXiv lookups; tested on 4 known cases incl. the supplementary-DOI trap, which the script now filters in title searches).
- `README.md` fixed: author was wrong in the scaffold ("Abhi" → Devendra Singh Dhakad), programme corrected to M.Sc. Data Science and AI, TL;DR updated with the MOF re-aim banner.
- Known drift flagged in CLAUDE.md: `src/extraction/extractor_base.py` type Literals still reflect ontology v0.1 — align with v0.2 (+ tests) before any extractor work (Week 1 task).
- **2026-06-11 — Exposé redesigned to match `Sample Expose.pdf`** (official SRH sample, Mehraeen): Aptos font, centered title block, thin gray section rules, borderless tables, numbered sub-questions, bold-italic *Gap:* lead, ALL-CAPS REFERENCES with italic titles. Added: SRH logo (Wikimedia Commons, public domain → `docs/assets/srh_logo.png`) and 13 clickable DOI/arXiv hyperlinks. Old build backed up to `docs/expose.v2.bak.docx`. Verified: docx validation passed; LibreOffice render (Arial substitute, metrically close to Aptos) = exactly **5 pages**; 1,746 words; 13 refs/links intact. Installed LibreOffice + poppler, so docx→PDF render checks are now possible locally for all future documents.
- `MY_NOTES.md` created (user-private scratchpad, gitignored) + `/mynotes` skill; privacy contract added to CLAUDE.md.
- **Em dash banned project-wide** (user mandate): rule recorded in CLAUDE.md + memory; purged from the exposé and supervisor email.
- **Exposé rebuilt in LaTeX (new primary format).** `docs/expose.tex` compiled with **Tectonic** (installed via brew) to `docs/expose.pdf`. Why LaTeX: editable version-controlled source, genuinely clickable links, publication-grade typesetting. Design: real SRH orange "srh" logo (`docs/assets/srh_logo.jpg`, from user), bundled Lato font (`docs/assets/fonts/`, OFL), SRH-orange section numbers + rules, borderless tables. Verified: 5 pages, 1,747 words, 0 em dashes in output, 13 references all clickable (13 distinct /URI link annotations confirmed by decompressing the PDF streams). Opened in Chrome for the user to review. The Word version is archived to `docs/expose.v3.bak.docx` (superseded; still contains em dashes). Installed poppler + Tectonic + LibreOffice, so the repo can now render docx/tex to PDF locally (reuse for the Week-12 final report).
- Next: user eyeballs `expose.pdf`, then sends with the share email; if the supervisor wants to comment inline, ask Claude for an em-dash-free Word export.
- **2026-06-11 — Writing rule (user mandate): no em dashes anywhere in project output.** Rule saved to CLAUDE.md + assistant memory. Exposé rebuilt with zero em dashes in the entire docx package (verified by grep over the unzipped XML; still 5 pages, 13 links intact, validation passed; en dashes kept only for ranges and "metal–organic"). Supervisor email draft rewritten clean (v2).
- `docs/PROJECT_WALKTHROUGH.md` created: first-person account of what was done and why, written so a newcomer can read it and continue the work without prior context.
- Final exposé PDF rendered and displayed in Safari for visual review (computer-use, read tier). Note: the LibreOffice-rendered PDF substitutes a serif font for Aptos; Word renders the real design.

Next (deadline order):
1. **Now → 12 June:** user opens `expose.docx` in Word (5-page visual check per pre-send checklist), then sends the share email to Jalali — reply in the existing confirmation thread.
2. **→ 18 June:** incorporate any supervisor comments (v2 → v3 if needed).
3. **→ 21 June 23:55:** upload exposé to Moodle (HARD DEADLINE) — upload regardless of whether feedback arrived.
4. **22 June:** project start; revise `docs/claude_code_prompt.md` Day-1 prompt to the MOF framing before kickoff (note added at its top).

Open items / risks:
- 1,769 words is ~10% above v1's 1,610 — if Word renders >5 pages, trim Section 4 bullets first (noted in pre-send checklist).
- SynMOF licence/availability unconfirmed — exposé words it as "DigiMOF and, where accessible, SynMOF"; confirm in Week 1 (data: github.com/aimat-lab/MOF_Synthesis_Prediction).
- MOF-only corpus collection slightly harder than broad scrape — mitigations: DigiMOF article index, CoRE MOF DOI lists (Chung 2019).
- Carried: LLM budget (commercial vs. open-weight mix), API key access.

## 2026-05-08 (session 2) — Exposé v0 → v1 revision

**Status:** Pre-project-start. Exposé revised against the SRH sample format; ready for supervisor review pass.

Done in this session:
- Locked SRH format from `Sample Expose.pdf`: 5 pages incl. references, APA 7, 13-ref target, 7 numbered sections, bold-lead-in SoTA bullets ending with italic "Gap:" line, 5-row methodology table, 12-row work plan.
- Confirmed working title (option B): **"Benchmarking Large Language Models for Knowledge Graph Construction from Materials Science Literature"**.
- Backed up prior draft to `docs/expose.v0.bak.docx` and revised `docs/expose.docx` in place:
  1. **Title swapped** to the short benchmark-led version (Section 1).
  2. **Methodology table consolidated 6 → 5 rows**: merged former "LLM Extraction Pipelines" + "Baseline Pipelines" into a single "Extraction Pipelines (LLM + Baselines)" row anchored by the unified Extractor interface; renumbered downstream rows.
  3. **Reference list reconciled to 13 entries**: dropped Chen & Guestrin 2016 (XGBoost — sample-template residue, irrelevant to scope); added Dagdelen et al. 2024 (Nat Comms, structured info extraction with LLMs) and Weston et al. 2019 (J. Chem. Inf. Model., foundational materials NER).
  4. **State-of-the-Art body updated** to cite Dagdelen 2024 in the LLM-extraction bullet and Weston 2019 in the domain-LM bullet.
- Repack passed all docx validations; word count 1719, within the sample's 5-page envelope.

Next (deadline order):
1. **Now → 5 June 2026:** send supervisor email; lock topic; book in Moodle.
2. **5 June → 14 June:** literature deep dive (25–30 papers); revise ontology with supervisor.
3. **14 June → 18 June:** share `docs/expose.docx` (v1) with supervisor; collect feedback and produce v2.
4. **18 June → 21 June:** revise + upload exposé to Moodle (HARD DEADLINE 21.06.2026).
5. **22 June:** project officially starts.

Open items / risks (carried from session 1):
- Supervisor sign-off on entity/relation ontology before annotation phase.
- Commercial vs. open-source LLM mix decision (cost control).
- API-key access (OpenAI/Anthropic) — confirm budget or SRH allowance.
- Page count: 1719 words is sample-equivalent but Word may render slightly different from the sample template; verify in Word/LibreOffice before submission and trim Expected Results if it spills past 5 pages.

## 2026-05-08 — Project bootstrap (pre-start)

**Status:** Pre-project-start phase. Official start is 22 June 2026.

Done:
- Chose topic 6.2 (LLM-Driven KG Construction from Text), domain: materials science.
- Drafted supervisor email (`../supervisor_email.md`).
- Drafted Case Study 2 exposé in SRH format (`docs/expose.docx`).
- Scaffolded repo skeleton: `src/`, `data/`, `docs/`, `configs/`, `tests/`.
- `pyproject.toml`, `Dockerfile`, `docker-compose.yml` (Neo4j 5.20 + APOC), `.gitignore`, `.env.example`.
- Initial ontology spec at `configs/ontology.json` (v0.1, expects supervisor revisions).
- Locked `claude_code_prompt.md` for Day 1.

Next (deadline order):
1. **Now → 5 June 2026:** send supervisor email; lock topic; book in Moodle.
2. **5 June → 14 June:** literature deep dive (25–30 papers); revise ontology with supervisor.
3. **14 June → 18 June:** share exposé draft with supervisor for feedback.
4. **18 June → 21 June:** revise + upload exposé to Moodle (HARD DEADLINE 21.06.2026).
5. **22 June:** project officially starts; open Claude Code with `claude_code_prompt.md`.

Risks / open questions:
- Confirm supervisor's preferred entity/relation set before annotation phase.
- Decide on commercial vs. open-source LLM mix early to control budget.
- Verify access to OpenAI/Anthropic API keys (or budget request to SRH).
