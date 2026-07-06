# Claude Code — Project Kickoff Prompt

> ⚠️ **STALE (10 June 2026):** the project was re-aimed to **"Building and Validating a MOF Synthesis Knowledge Graph with LLMs"** (see `docs/HANDOVER.md` and exposé v2). Revise this prompt to the MOF framing before using it on 22 June — the phases below still describe the old broad-materials benchmark.

> Paste this entire file as your first message in Claude Code (`claude` CLI) inside an empty `case-study-2/` folder.

---

# Project: LLM-Driven Knowledge Graph Construction from Materials Science Literature

## Context
This is my Master's Case Study 2 at SRH University Heidelberg (M.Sc. Applied Computer Science / Applied Data Science). Supervisor: Prof. Dr. Mehrdad Jalali. Official duration: 22 June 2026 → 15 September 2026 (12 weeks). Final report due 15.09.2026.

You are my engineering + research partner for the entire project. Treat me as the project owner; you do the heavy lifting on code, literature scanning, and drafting documents, and I review and decide.

## Goal
Build an end-to-end pipeline that uses Large Language Models (LLMs) to extract structured knowledge — specifically (Material → Synthesis Method → Property → Application) relationships — from materials science publications, store it as a queryable knowledge graph, and benchmark LLM extraction quality against established domain baselines (ChemDataExtractor, MatSciBERT).

## Research Questions
1. **Main:** How accurately can general-purpose LLMs (GPT-4-class, Llama-3, domain-tuned variants) extract materials–synthesis–property triples from scientific text compared to specialized NER/RE baselines?
2. Which prompting strategies (zero-shot, few-shot, chain-of-thought, schema-guided) produce the most reliable triples?
3. How does extraction quality vary across paper sections (abstract vs. methods vs. results)?
4. Can the resulting KG support useful downstream queries (e.g., "find materials synthesized via sol-gel with bandgap < 2 eV")?

## Tech Stack (lock these unless we have a strong reason to change)
- **Language:** Python 3.11+
- **LLMs:** OpenAI API (GPT-4o / GPT-4o-mini), Anthropic API (Claude), local Llama-3 via Ollama for cost control
- **Orchestration:** LangChain or LlamaIndex
- **Baselines:** ChemDataExtractor 2.0, MatSciBERT (HuggingFace)
- **Graph DB:** Neo4j (Community Edition, Docker)
- **NLP utilities:** spaCy, scispaCy
- **Data sources:** arXiv (cond-mat), ChemRxiv, PubMed Central OA subset, Materials Project API
- **Evaluation:** scikit-learn metrics, custom triple-matching evaluator
- **Frontend (final phase):** Streamlit dashboard for KG querying
- **Repo hygiene:** Git, pre-commit hooks, ruff, pytest, Docker for reproducibility

## Phases & Deliverables (12 weeks)

### Phase 0 — Exposé (BEFORE project start, due 21 June 2026)
- 5-page exposé in SRH format (Title, Introduction & Relevance, Research Question & Objectives, State of the Art with 10–13 references, Methodology table, 12-week Work Plan, Expected Results, References)
- Output: `docs/expose.docx`

### Phase 1 — Foundation (Weeks 1–2)
- Literature deep-dive: 25–30 papers on LLMs+KG, materials NER, GraphRAG, schema-guided extraction. Output: `docs/literature_review.md`.
- Repo scaffolding: project structure, `pyproject.toml`, Docker setup, README, CI.
- Define the target ontology/schema (entity types, relation types) as a JSON schema.

### Phase 2 — Data (Week 3)
- Build a corpus collector: pull 500–1000 open-access materials science papers (PDF + metadata).
- Parse PDFs to clean text (GROBID or PyMuPDF + post-processing).
- Output: versioned dataset under `data/raw` and `data/processed`.

### Phase 3 — Extraction Pipeline (Weeks 4–5)
- Implement LLM-based triple extraction with multiple prompting strategies (zero-shot, few-shot, schema-guided, CoT).
- Implement baseline pipelines: ChemDataExtractor + MatSciBERT-based RE.
- Create a unified `Extractor` interface so all approaches output the same triple format.

### Phase 4 — Knowledge Graph (Weeks 6–7)
- Set up Neo4j, design Cypher schema matching the ontology.
- Build the ingestion pipeline (triples → graph nodes/edges with provenance and confidence scores).
- Implement entity resolution / deduplication (string + embedding similarity).
- Output: a populated KG with 10k+ entities, 50k+ relations.

### Phase 5 — Evaluation (Week 8)
- Hand-annotate a gold standard (~200 sentences) — guide me through this.
- Compute precision / recall / F1 per extractor, per relation type, per paper section.
- Run statistical significance tests where appropriate.
- Output: `docs/evaluation_report.md`.

### Phase 6 — Interpretability & Analysis (Week 9)
- Error taxonomy (hallucination, schema violation, missed entity, wrong relation).
- Cost/latency analysis per extractor.
- Qualitative case studies of strongest and weakest examples.

### Phase 7 — Streamlit Dashboard (Week 10)
- Build a UI that lets a user (a) query the KG with natural language → Cypher (LLM-generated), (b) browse entities and their neighborhoods, (c) view provenance back to source papers.

### Phase 8 — Refinement & Testing (Week 11)
- End-to-end reproducibility check (fresh Docker run from scratch).
- User feedback round (I'll show it to my supervisor — help me prep questions).
- Polish, write tests, fix gaps.

### Phase 9 — Final Report & Defense (Week 12)
- Final report in academic style (~40–60 pages, SRH formatting): abstract, intro, related work, methodology, implementation, evaluation, discussion, conclusion, references.
- Slide deck (~15 slides) for the defense.
- Submission package: report PDF, code repo, KG dump, dashboard demo video.

## Working Style
- Always start a new phase by proposing a short plan, then ask me to confirm before executing.
- Prefer **incremental commits** with clear messages over big-bang changes.
- When you write code, also write tests for it.
- When you cite a paper, give the full reference (authors, year, venue, link).
- When you make a design decision, briefly state the trade-off (1–2 lines) so I can override if needed.
- Track progress in a `PROGRESS.md` file at the repo root, updated at the end of every working session.
- Flag risks early. If a deadline is at risk, tell me immediately with options (cut scope, parallelize, change approach).
- Do not invent data. If a result is not yet measured, mark it as TODO.
- Default to concise, practical responses with research backing — no fluff.

## First Action
Confirm you've understood the scope, then propose:
1. The exact repo directory structure you want to create
2. The target ontology/schema (entities + relation types) for the KG
3. A list of the first 10 papers I should read this week

Wait for my approval before writing any code.
