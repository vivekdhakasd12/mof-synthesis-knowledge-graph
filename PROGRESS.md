# Project Progress Log

A rolling log. Append a new dated entry every working session. Newest at the top.

## 2026-08-23 (session 8) — Full extraction pipeline built, tested, and measured

**Status:** The pipeline now runs end to end on real data. 180 tests pass, ruff and mypy are
clean, coverage 82 percent. Two commits on `feat/pipeline-foundation` (`ddecdd2`, `ad0fcc1`).
The graded core is now buildable: what remains blocking is the human gold standard and the
API keys.

Done in this session:
- **Recovered a failed parallel build.** The five build agents were killed mid-run by a usage
  limit, leaving partial modules and three missing test files. Rather than rerun them, the
  surviving code was verified, corrected and completed by hand.
- **`src/ingestion/segment.py`**: papers to scored synthesis passages with stable
  deterministic ids. Real run: 22,086 passages from 399 papers, **794 flagged synthesis
  across 224 papers**, mean 929 characters. Threshold sensitivity recorded (0.25 gives 2,369
  passages, 0.45 gives 794, 0.65 gives 268) so the cutoff is a defended choice.
- **Data bug found and fixed.** Verifying passage id uniqueness (the gold standard keys on
  those ids) exposed 17 collisions. Cause was upstream in `build_corpus.py`: Europe PMC
  returned one paper on two cursor pages and the collector never deduplicated. Now
  deduplicated by PMCID and DOI; corpus 400 to 399, zero collisions.
- **`src/extraction/rule_based.py`** plus **`llm_extractor.py`**, **`cache.py`**, and all four
  prompt templates (zero-shot, few-shot, schema-guided, chain-of-thought). LLM strand is
  fully testable offline against a fake client, with sockets severed by an autouse fixture,
  so it needs no key until it runs for real.
- **`src/evaluation/metrics.py`**: per-field precision, recall and F1 with exact and relaxed
  matching on the shared normaliser, plus record-level agreement where a missing reference
  field counts as not comparable rather than as a disagreement.
- **`src/pipeline.py`** (written here, not by an agent): the experiment runner. Resumable on
  (passage, extractor) so an interrupted paid run is never billed twice; records a raising
  extractor as a contract violation instead of aborting the run. Coverage 89 percent.
- **`src/annotation/`**: Streamlit tool, ontology-constrained so an invalid triple cannot be
  created, autosaving to `data/annotations/gold.jsonl`. Worklist is 200 passages, 180 from
  the synthesis pool plus **20 unflagged controls so the pre-filter's own miss rate is
  measurable**, seeded and deterministic, interleaved against fatigue bias. README written
  with concrete annotation conventions.
- **Baseline measured honestly** (`docs/baseline_findings.md`): 1,864 triples over 794
  passages at zero cost and 0.6 ms per passage, but **a MOF is identified in only 15 percent
  of passages**, which structurally suppresses the five relations the ontology roots at MOF.
  Of 638 passages with no recognised MOF, 331 name it elsewhere in the paper and 251 use a
  generic designation. The metal-linker convention (Cu-BTC, Co-TPA) was unhandled and has
  been added, since missing a standard name for HKUST-1 was a defect, not an honest limit,
  and a strawman baseline would invalidate the comparison.
- **Pre-registered prediction recorded before any LLM runs**, so it cannot be fitted after
  the fact: the LLM margin should be largest on USES_PRECURSOR, USES_LINKER and
  SYNTHESIZED_BY, and smallest on AT_CONDITION and IN_SOLVENT where local patterns already
  work. Fairness note: the LLM sees the same single passage, so cross-passage coreference is
  hard for both systems and an LLM win there would be suspicious rather than impressive.
- Integration defects caught by type checking rather than at runtime: the runner called a
  client factory the LLM module does not expose, and the Neo4j protocol needed a documented
  cast. Both fixed.
- **API keys were pasted into chat three times and are burned.** Containment verified: `.env`
  is gitignored and no key string exists in any tracked file. `scripts/set_keys.sh` now
  prompts for keys with input hidden so the safe path is the easy one.

Next (deadline order):
1. **User:** rotate all three keys (OpenAI, Anthropic, Groq), run `bash scripts/set_keys.sh`.
2. **User:** annotate 150 to 200 passages via the Streamlit tool. Critical path, roughly 3 to
   5 hours, cannot be delegated without invalidating the evaluation.
3. Start Neo4j (colima plus docker compose), load triples, verify `provenance_violations`
   returns zero rows.
4. Wire the real ChemDataExtractor baseline from the vendored DigiMOF parsers; assess
   MatSciBERT.
5. Run all four prompting strategies across GPT-4o, Claude and Groq Llama-3.3-70B once keys
   land; compute per-field metrics against the frozen gold standard.
6. **2026-09-15** hard submission.

Open items / risks:
- Carried and now urgent: the gold standard is the critical path and needs the user's hours.
- Carried: the DigiMOF join is by CSD refcode, not DOI, which bounds the agreement analysis.
  Recommendation remains to join on MOF name and report the ambiguity.
- New: 47 percent of synthesis passages yield zero triples from the baseline. Partly genuine
  (reagent manifests contain no relation), partly corpus precision. Quantify before writing
  the results chapter.
- Carried: 8 GB RAM means Neo4j and heavy jobs should not run concurrently.
- Carried: two corpus papers have unrecognised licences and must be verified or dropped.

## 2026-08-14 (session 7) — Build begins; ingestion/corpus pipeline live (10 OA papers, tested)

**Status:** Reality check at session start: despite the calendar/plan showing ~Week 5-6, the repo was **scaffold-only** (just the `Extractor` interface + tests). No pipeline code, no data. So the real build begins now with **~4.5 weeks to the 2026-09-15 deadline**. User re-confirmed the lean-MVP approach: protect the graded core (per-field validation + DigiMOF/SynMOF agreement); cut stretch goals early (KG-RAG QA, NL-to-Cypher, big ablation grid, likely the slow local-Llama strand). This session built the corpus foundation everything else needs.

Done in this session:
- **`src/ingestion` built and proven.** Modules: `models.py` (`CorpusDoc`/`Section`, mandatory provenance: paper_id, doi, pmcid, licence, retrieved_at; `.section()` helper to target the synthesis/experimental block), `europepmc.py` (search + disk-cached full-text-XML fetch; `requests` follows the endpoint redirect that a bare `curl` misses), `parse.py` (JATS XML -> sectioned text, namespace-agnostic `{*}` XPath, `itertext()` flatten so inline markup does not fragment sentences), `build_corpus.py` (typer CLI).
- **Source decision: Europe PMC** as primary corpus source. Rationale: 49,627 OA MOF-synthesis papers expose *structured* JATS full text (labelled sections) far more reliably than scraping + PDF parsing. Open-access subset only.
- **Live run proven:** `python -m src.ingestion.build_corpus --limit 10` -> `data/processed/corpus.jsonl`: 10 real OA papers, 352,739 chars, all Creative Commons (CC-BY / CC-BY-NC-ND); 9/10 have an identifiable synthesis/experimental section; real precursor/solvent text confirmed in output; the DigiMOF paper itself (PMC10269341) is in the set. Raw XML cached to `data/raw/europepmc/` (gitignored, verified).
- **Quality gates green:** 6 new offline unit tests (JATS parse, provenance, nested-paragraph flatten, section lookup, empty-XML guard, JSONL roundtrip); full suite **12 passed**. ruff + ruff format + mypy all clean. Added `types-requests` + `lxml-stubs` to dev deps and a ruff `flake8-bugbear` allowlist for `typer.Option` (silences the B008 false-positive).

Next (deadline order):
1. **(user, parallel; still blocks the LLM strand at scale)** create OpenAI + Anthropic API accounts, paste keys into `.env`; send Jalali the ontology-signoff + ~EUR 60 funding email (drafted-ready on request).
2. Scale corpus to ~150-300 papers: diversify queries beyond the default, add a CC-only licence filter, normalise licence strings to short codes; add Unpaywall/arXiv fetchers for OA chemistry papers not in Europe PMC.
3. Acquire the DigiMOF + SynMOF reference records (for the agreement analysis) - the aimat-lab repo is ML-feature dumps, not a clean DOI-indexed record file; find the real database export (paper SI / Zenodo).
4. Build the first `Extractor` subclass on the unified interface (rule-based/baseline first, key-free) running over `corpus.jsonl`.
5. **2026-09-15** hard submission.

Open items / risks:
- New: corpus is Europe-PMC-only right now; much OA chemistry (RSC, ACS AuthorChoice, ChemRxiv) is not in EPMC, so the subset overlapping DigiMOF/SynMOF may be small. Mitigation: add Unpaywall/arXiv fetchers next; document coverage as a threat to validity.
- New: not every OA "MOF synthesis" hit is a synthesis paper (PMC11835274 was a perspective, no experimental section). The query + a section-presence filter need tightening at scale.
- Carried: **API keys still empty** -> LLM strand blocked once we scale; Jalali funding email unsent.
- Carried: **schedule risk is now high** - 10-week plan had no slack and the build only starts at ~4.5 weeks out. If a week slips, tell Jalali in August (now), not September.
- Carried: git commits authored "vivekdhakasd12 <dhakadvivu5@gmail.com>"; decide before the repo goes public.

## 2026-07-07 (session 6) — Day-1 prompt re-aimed to MOF framing; API-key status checked; LLM budget planned

**Status:** Week 0 Day 2 tasks done. `docs/claude_code_prompt.md` now matches the approved exposé and the re-baselined schedule (commit `933e4d1`). API keys do NOT exist yet on this machine (no .env, no env vars, Ollama not installed); a gitignored `.env` scaffold is in place waiting for keys. The LLM budget is planned with verified July-2026 pricing and a free-first strategy; the funding question goes to Jalali in the 2026-07-08 ontology email.

Done in this session:
- `docs/claude_code_prompt.md` rewritten from the superseded broad-materials framing to the MOF synthesis KG framing: exposé RQs, locked stack, 10-week re-baselined phase table with cut order, non-negotiable domain rules, First Action now starts from PROGRESS.md + the project calendar instead of an empty repo. Zero em dashes. Committed as `933e4d1`.
- API-key audit: no `.env`, no `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` in the environment, Ollama not installed. Created `.env` from the example with a generated Neo4j password (confirmed gitignored); key fields empty, user must create accounts and paste keys.
- Hardware check for the open-weight strand: Apple M1, 8 GB RAM, 51 GB free disk. Llama-3 8B quantized via Ollama is feasible but slow (full 6,000-call grid is a multi-night overnight job; do not run Neo4j concurrently). Ollama install + ~5 GB model pull scheduled with Week 3 (2026-07-27).
- LLM budget planned with pricing verified live this session (claude-api skill + web): GPT-4o $2.50/$10 per MTok, Claude Sonnet 5 $2/$10 intro through 2026-08-31 (then $3/$15), both providers 50% off via batch APIs. Workload model: ~1,500 passages x 4 strategies = 6,000 calls/model at ~1,500 in / 400 out tokens.
- **Budget decision (user asked for free options; no preference on mix):** GPT-4o + Claude Sonnet 5 + local Llama-3 8B. Free-first: develop on free tiers (GitHub Models GPT-4o ~50 req/day; Groq Llama-3.3-70B 1,000 req/day) and the mandatory call cache; pay only for batched final scale runs, ~$66/~EUR 61 for both commercial models (EUR ~45 at 300 papers). Ceiling EUR 70; target EUR 0 personal by asking Jalali/SRH to cover it. Rationale: free tiers cannot serve the 6,000-call study runs (rate limits, reproducibility), and dropping the commercial strand would contradict the approved exposé (RQ4).

Next (deadline order):
1. **2026-07-08:** draft ontology v0.2 sign-off email to mehrdad.jalali@srh.de (short, he writes one-liners) INCLUDING the ~EUR 60 API-funding question; user sends. Confirm SynMOF licence (github.com/aimat-lab/MOF_Synthesis_Prediction).
2. **2026-07-08:** user creates OpenAI + Anthropic API accounts and pastes keys into `.env` (blocking for Week 2, 2026-07-20).
3. **2026-07-09 to 2026-07-12:** literature deep dive (P0-P3 from `docs/literature_review.md`); start corpus DOI lists; Week 0 wrap on 2026-07-12.
4. **2026-07-13 to 2026-07-17:** Week 1 corpus collection + parsing; checkpoint 2026-07-17: 300-500 papers or cut to 300.
5. **2026-09-15:** hard submission deadline.

Open items / risks:
- New: API keys still missing; if not in `.env` by 2026-07-14 this blocks Week 2 pipeline work.
- New: 8 GB M1 makes local Llama-3 the slowest strand; if overnight runs prove impractical, fallback is Groq free tier for a reduced open-weight subset (document the endpoint change) or a smaller local model (llama3.2:3b), both need a note in the report's threats-to-validity.
- New: Sonnet 5 intro pricing ends 2026-08-31; scale runs are scheduled Week 6 (2026-08-17 to 2026-08-23), inside the window, but slippage past August costs ~50% more on the Anthropic strand.
- Carried: 10-week plan has no slack; renegotiate scope with Jalali in August if a week slips unrecoverably.
- Carried: SynMOF licence/availability unconfirmed.
- Carried: git commits authored as "vivekdhakasd12 <dhakadvivu5@gmail.com>"; decide before the repo goes public.
- Carried: MOF-only corpus collection harder than broad scrape; mitigations DigiMOF article index, CoRE MOF DOI lists.
- Carried: schedule lives only in the local Mac calendar; recreate on Google calendar if phone reminders are needed.

## 2026-07-06 (session 5) — Exposé approved + uploaded; 2-week slip; re-baselined schedule; ontology v0.2 alignment; first commits

**Status:** Pre-project phase closed: Prof. Jalali approved the exposé (user reported approval on 2026-06-21, no verbatim quote on file) and the user uploaded it to Moodle on 2026-06-21, meeting the hard deadline. However, no project work happened between the official start (2026-06-22) and 2026-07-05: roughly 2 of 12 weeks lost. The plan is re-baselined to a 10-week run (2026-07-06 to 2026-09-15) with a defined cut order protecting the validation core. Week 0 Day 1 tasks are done; the repo now has its first commits and a v0.2-aligned type system, so extractor work is unblocked.

Done in this session:
- Re-baselined 10-week schedule agreed (Week 0 catch-up 2026-07-06 to 2026-07-12, then corpus, pipelines, gold standard freeze 2026-08-07, KG, scale run, validation, dashboard/report, repro, submit 2026-09-15). Cut order if slipping: KG-RAG QA, then NL-to-Cypher (canned Cypher instead), then ablations, then corpus 500 to 300 / annotation 200 to 150. Rationale: the per-field validation plus DigiMOF/SynMOF agreement is the graded contribution; stretch goals go first.
- Schedule written to Apple Calendar: new local "Case Study 2" calendar on the user's Mac, 22 all-day events (day-level tasks for Week 0, Monday kickoffs per week, 3 checkpoints, gold-freeze milestone, final deadline). Note: local calendar, does not sync to phone.
- First git commit `a8b3887`: full scaffold, exposé, docs (51 files). Second commit `a98dff9`: ontology alignment (below). Added Office lock-file rule to `.gitignore` (docs/~$expose.docx was about to be committed).
- **Ontology v0.2 alignment done** (was the blocking Week 1 task from session 3): `src/extraction/extractor_base.py` EntityType/RelationType Literals now mirror `configs/ontology.json` v0.2 (9 entities, 9 relations); `configs/prompts/extraction_schema_guided.txt` rewritten from v0.1 generic-materials to v0.2 MOF vocabulary with per-relation endpoint constraints (Paper/MENTIONED_IN deliberately excluded: provenance is pipeline-attached, not LLM-extracted).
- Tests grown 1 to 6 (all passing, 100% coverage on extractor_base): drift guards both directions for entities and relations, relation endpoint validity, provenance invariant lock (provenance_required, MENTIONED_IN required to Paper), prompt-template completeness check, plus the roundtrip test re-typed to a MOF example.
- Multi-agent diff review before commit: 4 findings, 3 confirmed and fixed (off-by-one span in test fixture, stale v0.1 prompt template, unlocked provenance invariant), 1 rejected (runtime type validation: deferred to the first extractor by design, a raising constructor would conflict with the extract-must-not-raise contract).
- Environment repaired: `uv sync` was broken (blis, a spaCy dependency, has no Python 3.13 wheels; old .venv was bare). Pinned Python 3.11 via `.python-version`, rebuilt venv, full dependency set installs cleanly; pytest, ruff, mypy all green.
- `pyproject.toml`: scaffold author "Abhi" resurfaced and is fixed to Devendra Singh Dhakad (CLAUDE.md rule); description updated to the MOF re-aim.

Next (deadline order):
1. **2026-07-07:** re-aim `docs/claude_code_prompt.md` to the MOF framing; confirm OpenAI/Anthropic API keys and LLM budget.
2. **2026-07-08:** email ontology v0.2 to mehrdad.jalali@srh.de for sign-off (blocks annotation); confirm SynMOF licence (github.com/aimat-lab/MOF_Synthesis_Prediction).
3. **2026-07-09 to 2026-07-12:** literature deep dive (P0 to P3 from `docs/literature_review.md`); start corpus DOI lists; Week 0 wrap + PROGRESS.md update on 2026-07-12.
4. **2026-07-13 to 2026-07-17:** Week 1 corpus collection + parsing; checkpoint 2026-07-17: 300-500 papers or cut to 300.
5. **2026-09-15:** hard submission deadline (report, repo, slides).

Open items / risks:
- New: 10-week plan has no slack; if a week slips and cannot be recovered, tell Jalali in August, not September (renegotiate scope early).
- New: git commits are authored as "vivekdhakasd12 <dhakadvivu5@gmail.com>"; decide before the repo goes public whether commits should carry the real student name.
- New: project schedule lives only in the local Mac calendar; recreate on Google calendar if phone reminders are needed.
- Carried: SynMOF licence/availability unconfirmed (exposé words it as "where accessible").
- Carried: LLM budget (commercial vs open-weight mix) and API key access unconfirmed; becomes blocking in Week 2 (2026-07-20).
- Carried: MOF-only corpus collection slightly harder than broad scrape; mitigations are the DigiMOF article index and CoRE MOF DOI lists (Chung 2019).

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
