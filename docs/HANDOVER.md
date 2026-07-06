# Project Handover — Case Study 2

> Paste this entire file into a new Claude / Cowork chat (any account) to resume work with full context.

---

## Who & What

- **Student:** Devendra Singh Dhakad
- **Matriculation number:** 100004684
- **Email:** dhakadvivu5@gmail.com (switch to SRH student address if/when available)
- **Programme:** M.Sc. Data Science and AI (April 2025 cohort)
- **University:** SRH University of Applied Sciences Heidelberg
- **Module:** Case Study 2 (elective, 22 June 2026 → 15 September 2026, 12 weeks)
- **Coordinator:** Sabine Helwig (sabine.helwig@srh.de)
- **Supervisor:** Prof. Dr. Mehrdad Jalali — **mehrdad.jalali@srh.de** (confirmed; AI & Cheminformatics, ex-KIT, editor at Materials Today Communications)

## Supervisor status (the actual record — do not confuse with drafts)

- Student sent a **short topic-interest email** (supervisor selected in Moodle; interest in Topic 6.2 stated). The long drafted email in `docs/supervisor_email_topic_lock.md` was **never sent** — kept as history only.
- Jalali replied: **"The topic is confirmed. Move forward."** → topic + supervisor locked before the 5 June deadline ✓.
- **He has NOT yet seen the exposé.** Sharing it is the live action item (see next steps).
- His reply style is very brief — keep emails to him short.

## Topic decision

- **Topic:** 6.2 — LLM-Driven Knowledge Graph Construction from Text (from Jalali's list; confirmed by him)
- **Framing (re-aimed 10 June 2026, user-approved — do not relitigate unless user asks):** **Building and Validating a MOF Synthesis Knowledge Graph with LLMs.** The earlier broad "benchmark LLMs across materials literature" framing was dropped because:
  - Bai et al. 2025 (npj Comput. Mater. 11:51) already built a 100k-article LLM KG for framework materials incl. a 91.67%-accuracy QA system — broad framing's novelty is gone
  - MOFs are Jalali's own research line (MOFGalaxyNet, J. Cheminformatics 15:94, 2023) → maximum supervisor alignment
  - DigiMOF (Chem. Mater. 35:4510, 15,501 MOFs) + SynMOF (Angew. Chem. 61:e202200242) enable a **validation/agreement study nobody has published**: per-field LLM accuracy vs. expert gold standard AND vs. existing text-mined databases, incl. open-weight vs. commercial cost/latency — prior LLM-MOF work is GPT-only with in-house validation

## Project framing (1 sentence)

Use LLMs to extract complete MOF synthesis records (metal precursor, organic linker, solvent, method, conditions, properties, applications) from 300–500 open-access papers into a provenance-aware Neo4j knowledge graph, and validate extraction per field against a hand-annotated gold standard, DigiMOF/SynMOF agreement analysis, and ChemDataExtractor/MatSciBERT baselines — comparing prompting strategies and open-weight (Llama-3) vs. commercial (GPT-4o, Claude) models on accuracy, cost, and latency; stretch: KG-RAG vs. vanilla-RAG QA.

## Research questions

1. **Main:** How accurately/reliably can LLMs extract complete MOF synthesis records, measured against expert annotation, DigiMOF/SynMOF, and domain baselines?
2. Which prompting strategy (zero-shot, few-shot, schema-guided, CoT) is most reliable per field?
3. Where and why do LLM extractions disagree with DigiMOF/SynMOF — and which is correct?
4. Open-weight (Llama-3) vs. commercial (GPT-4o, Claude): per-field accuracy, cost, latency?
5. Can the KG answer cross-paper aggregation queries (+ stretch: KG-grounded QA vs. vanilla RAG)?

## Tech stack (locked)

Python 3.11+ · GPT-4o/GPT-4o-mini, Claude, Llama-3 via Ollama · LangChain or LlamaIndex · Baselines: ChemDataExtractor 2.0, MatSciBERT · Neo4j 5.20 Community (Docker) + APOC · spaCy/scispaCy · Corpus: CSD MOF subset + DigiMOF article index DOIs, ChemRxiv, PMC OA · Label Studio (gold standard) · Streamlit · Git, ruff, pytest, Docker

## Deadlines (all 2026)

| Date | Action | Status |
|------|--------|--------|
| 5 Jun | HARD: supervisor + topic locked in Moodle | ✓ DONE |
| ~12 Jun | Send exposé to Jalali (`docs/supervisor_email_expose_share.md`) | ← NEXT |
| 18 Jun | Last day to incorporate supervisor comments | |
| **21 Jun 23:55** | **HARD: exposé uploaded to Moodle** (upload even without feedback) | |
| 22 Jun | Project starts (revise `docs/claude_code_prompt.md` to MOF framing first) | |
| 15 Sep | Final report due | |

## Repo state (this folder IS the live workspace)

- `docs/expose.docx` — **fresh MOF-framed exposé v2** (10 June 2026): title block (name/matriculation/supervisor — v1 had none), 7 SRH sections, 5-row methodology table, 12-week plan, 13 references all verified against live sources. 1,769 words; user must do the 5-page visual check in Word before sending (checklist in the email draft).
- `docs/expose.v1.bak.docx`, `docs/expose.v0.bak.docx` — superseded drafts (old broad framing).
- `docs/supervisor_email_expose_share.md` — ready-to-send share email + pre-send checklist. **User sends it.**
- `docs/supervisor_email_topic_lock.md` — UNSENT historical draft; superseded.
- `docs/literature_review.md` — 30 verified papers (★ = in exposé), themed A–F, reading plan for Weeks 1–2.
- `configs/ontology.json` — **v0.2 MOF-specific** (9 entities / 9 relations / provenance required / 5 open questions for supervisor).
- `docs/claude_code_prompt.md` — Day-1 kickoff prompt; **still has old framing**, gets revised before 22 June (note at top).
- `src/extraction/extractor_base.py` + `tests/` — unified Triple/Extractor ABC, pytest green.
- `PROGRESS.md` — session log, newest first. **Update every session.**

## Phase plan (12 weeks from 22 June)

| Weeks | Phase |
|-------|-------|
| 1–2 | Lit deep dive (reading plan in literature_review.md); finalise ontology with supervisor; corpus DOI lists |
| 3 | PDF parsing (GROBID/PyMuPDF); cleaned corpus; synthesis-paragraph coverage EDA |
| 4–5 | LLM pipelines (4 prompting arms) + baselines (CDE, MatSciBERT) on unified Extractor interface |
| 6 | Gold standard (~150–200 synthesis paragraphs, Label Studio); freeze eval protocol + DigiMOF/SynMOF field mapping |
| 7 | Neo4j ingestion; SBERT entity resolution + chemical-name normalisation |
| 8 | Run extractors at scale; populate KG (target 5k+ entities, 25k+ relations); per-field metrics |
| 9 | DigiMOF/SynMOF agreement analysis; error taxonomy; cost/latency; ablations |
| 10 | Streamlit dashboard + NL→Cypher; stretch: KG-RAG vs. RAG QA |
| 11 | Reproducibility (fresh Docker); supervisor feedback round |
| 12 | Final report (40–60 pages) + slides + submission package |

## Open decisions for supervisor (Week 1) — also in ontology.json `open_questions`

- Property values as nodes vs. attributes; confidence score form (float vs. categorical)
- Condition granularity (one typed entity vs. Temperature/Time/pH split)
- DigiMOF/SynMOF field mapping for the agreement analysis
- Characterization as first-class entity in v0.3?
- LLM budget: commercial vs. mostly-open-weight mix

## Working style preferences (carry forward)

- Straight, concise, practical answers with research backing. No fluff.
- Plan → confirm → execute. Incremental commits. Tests with code. **Never fabricate citations or numbers — verify against live sources before citing.** Update `PROGRESS.md` each session. Flag risks early.
- Emails to Jalali: short.

## Immediate next steps (deadline order)

1. **User:** open `docs/expose.docx` in Word — confirm 5 pages (if 6, trim Section 4 bullets) — then send `docs/supervisor_email_expose_share.md` content to mehrdad.jalali@srh.de with the docx attached, replying in the confirmation thread. Log send date in PROGRESS.md.
2. By 18 June: fold in any comments from Jalali.
3. By 21 June 23:55: upload exposé to Moodle (hard deadline, upload regardless).
4. Before 22 June: revise `docs/claude_code_prompt.md` to the MOF framing; confirm SynMOF data access (github.com/aimat-lab/MOF_Synthesis_Prediction) and DigiMOF licence.
5. 22 June: start Phase 1 (reading plan P0 papers first).

## What to ask the new chat to do first

Tell it: *"Read this handover, then `PROGRESS.md`, then continue from the immediate next steps."*

---

*Regenerated 10 June 2026 (supersedes the 8 May / 16 May version, which predated the supervisor exchange and the MOF re-aim).*
