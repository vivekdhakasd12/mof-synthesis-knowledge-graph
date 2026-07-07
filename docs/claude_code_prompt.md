# Claude Code Kickoff Prompt (Case Study 2)

> Paste this file as the first message in a fresh Claude Code session in this repo when starting a working session without prior context (CLAUDE.md auto-loads, but this file carries the full project brief). Then follow the First Action at the bottom.
>
> Revised 2026-07-07 to the MOF framing; supersedes the pre-start broad-materials version (recoverable from git history).

---

# Project: Building and Validating a MOF Synthesis Knowledge Graph with LLMs

## Context

This is my Master's Case Study 2 at SRH University of Applied Sciences Heidelberg (M.Sc. Data Science and AI). Supervisor: Prof. Dr. Mehrdad Jalali. Official window: 22 June 2026 to 15 September 2026; after a two-week slip the execution plan is re-baselined to 10 weeks, 6 July to 15 September 2026 (schedule: PROGRESS.md session 5 entry and the "Case Study 2" calendar in Apple Calendar). Final report due 15 September 2026.

This is a graded research output: reproducibility and defensible evaluation beat feature richness. You are my engineering and research partner; you do the heavy lifting on code, literature scanning, and drafting, and I review and decide.

## Goal

Build an end-to-end pipeline that uses LLMs to extract complete MOF synthesis records (metal precursor, organic linker, solvent, synthesis method, conditions, properties, applications) from 300–500 open-access papers into a provenance-aware Neo4j knowledge graph, and validate extraction quality per field against (a) a hand-annotated gold standard, (b) agreement with the DigiMOF and SynMOF text-mined databases, and (c) ChemDataExtractor 2.0 and MatSciBERT baselines, comparing prompting strategies and open-weight vs. commercial models on accuracy, cost, and latency. Stretch goal: KG-RAG vs. vanilla-RAG question answering.

## Research Questions

1. **Main:** How accurately and reliably can LLMs extract complete MOF synthesis records (precursor, linker, solvent, method, conditions) from the scientific literature, measured against expert annotation, established text-mined databases (DigiMOF, SynMOF), and domain-specific baselines?
2. Which prompting strategy (zero-shot, few-shot, schema-guided, chain-of-thought) is most reliable for each field of a synthesis record?
3. Where and why do LLM extractions disagree with DigiMOF and SynMOF, and which source is correct when they do?
4. How do open-weight models (Llama-3) compare to commercial APIs on per-field accuracy, cost, and latency?
5. Can the resulting KG answer cross-paper aggregation queries, and (stretch) support KG-grounded QA?

## Tech Stack (locked; do not swap without strong justification)

- **Language:** Python 3.11 (pinned in `.python-version`; blis/spaCy has no 3.13 wheels)
- **LLMs:** OpenAI API + Anthropic API (commercial strand), local Llama-3 via Ollama (open-weight strand)
- **Orchestration:** LangChain or LlamaIndex
- **Baselines:** ChemDataExtractor 2.0, MatSciBERT (HuggingFace)
- **Graph DB:** Neo4j 5.20 Community (Docker) + APOC
- **NLP utilities:** spaCy, scispaCy
- **Corpus sources:** CSD MOF subset DOIs, DigiMOF article index, ChemRxiv, PubMed Central OA (open-access, permissively licensed only)
- **Gold standard:** Label Studio
- **Evaluation:** scikit-learn metrics, custom per-field triple matcher
- **Dashboard:** Streamlit (NL-to-Cypher + provenance views)
- **Repo hygiene:** Git, ruff, pytest, mypy, Docker for one-command reproducibility

## Phase Plan (re-baselined, 10 weeks from 6 July 2026)

| Dates (2026) | Phase | Key outputs |
|---|---|---|
| 06–12 Jul | Week 0: catch-up + foundations | Ontology drift fix + first commits (done 06 Jul); ontology v0.2 to supervisor; literature deep dive; corpus DOI lists started |
| 13–19 Jul | Week 1: corpus + parsing | 300–500 OA MOF papers; GROBID/PyMuPDF pipeline; cleaned text + metadata; checkpoint 17 Jul |
| 20–26 Jul | Week 2: LLM pipelines I | Unified Extractor end-to-end; first LLM strand (4 prompting arms); caching on from call one |
| 27 Jul–02 Aug | Week 3: pipelines II + baselines | Llama-3 + second commercial model; ChemDataExtractor + MatSciBERT; identical Triple schema everywhere |
| 03–09 Aug | Week 4: gold standard | 150–200 hand-annotated synthesis paragraphs; **freeze eval protocol + DigiMOF/SynMOF field mapping 07 Aug** |
| 10–16 Aug | Week 5: KG construction | Neo4j ingestion; SBERT entity resolution + chemical-name normalisation; provenance edges |
| 17–23 Aug | Week 6: scale run + metrics | All extractors over full corpus; KG populated (5k+ entities, 25k+ relations); per-field P/R/F1 |
| 24–30 Aug | Week 7: validation core | DigiMOF/SynMOF agreement analysis; error taxonomy; cost/latency table; ablations; status to supervisor 28 Aug |
| 31 Aug–06 Sep | Week 8: dashboard + report start | Minimal Streamlit dashboard; report methods + results drafted |
| 07–13 Sep | Week 9: reproducibility + report | Fresh-Docker end-to-end check (11 Sep); supervisor feedback folded in; report + slides |
| 14–15 Sep | Final polish + **submit 15 Sep** | Report, reproducible repo, KG dump + ontology + gold standard, defence slides |

**Cut order if a week slips (validation core is never cut):** KG-RAG QA first, then NL-to-Cypher (ship canned Cypher queries instead), then trim ablations, then corpus 500 to 300 and annotation 200 to 150.

## Domain Rules (non-negotiable)

- `configs/ontology.json` (v0.2) is the source of truth for entity/relation types; `extractor_base.py`, the prompt templates, and the drift-guard tests must stay aligned with it.
- **Provenance is mandatory:** every triple carries paper id, section, and evidence sentence; every KG entity gets a `MENTIONED_IN` edge to its `Paper`.
- **Never tune on the gold standard** (`data/annotations/`); it is frozen once the eval protocol is set (07 Aug 2026).
- **Cache every LLM call** (logged + replayable); never re-pay for the same inference.
- Every extractor implements the `Extractor` ABC and must not raise from `extract()`; errors go into `ExtractionResult.errors`.
- Corpus: open-access, permissively licensed papers only. `data/raw/` and `data/processed/` stay gitignored.
- Never cite a paper without verifying it against a live source first (`verify-citation` skill). Never invent measurement results; unmeasured numbers are TODO.
- No em dashes in any project writing; en dashes only in number/date ranges and "metal–organic framework".

## Working Style

- Propose a short plan, get my confirmation, then execute. Incremental commits with clear messages; tests alongside code.
- When you make a design decision, state the trade-off in 1–2 lines so I can override.
- Flag risks early with options (cut scope, parallelize, change approach). If the schedule slips unrecoverably, I tell the supervisor in August, not September.
- Update `PROGRESS.md` at the end of every working session (`progress-log` skill).
- Emails to Prof. Jalali: short, draft only; I send them.

## First Action

1. Read the newest entry in `PROGRESS.md` and today's task in the "Case Study 2" Apple Calendar.
2. Confirm you understand the current project state in 3–4 sentences (what is done, what is next, nearest deadline).
3. Propose today's plan and wait for my approval before writing code.
