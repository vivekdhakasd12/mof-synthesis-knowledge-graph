# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Master's Case Study 2 (SRH Heidelberg, supervisor Prof. Dr. Mehrdad Jalali): **Building and Validating a MOF Synthesis Knowledge Graph with LLMs**. Project window 22 June – 15 September 2026; graded research output, so reproducibility and defensible evaluation beat feature richness.

**Start every session by reading the newest entry in `PROGRESS.md`.** Full project state, deadlines, and decisions live in `docs/HANDOVER.md`. The framing was re-aimed on 2026-06-10 from broad materials benchmarking to MOF synthesis records validated against DigiMOF/SynMOF — older files may still describe the old framing (README TL;DR, `docs/claude_code_prompt.md`); `docs/HANDOVER.md` and `docs/expose.docx` are authoritative.

## Commands

```bash
uv sync                                   # install (or: pip install -e ".[dev]")
pytest                                    # tests; coverage on src/ is auto-added via pyproject addopts
pytest tests/test_extractor_base.py -k triple   # single file / single test
ruff check src tests && ruff format src tests   # lint + format (line length 100, py311)
mypy src                                  # type check
docker compose up -d                      # Neo4j 5.20 + APOC (browser :7474, bolt :7687)
                                          # auth from NEO4J_PASSWORD env (see .env.example)
streamlit run src/dashboard/app.py        # dashboard (Week 10+, not yet implemented)
```

Most `src/` packages are empty scaffolding until the project starts; the README quick-start module commands (`src.ingestion.arxiv_fetcher`, …) are planned interfaces, not working code yet.

## Architecture

Pipeline: `src/ingestion` (corpus DOI lists → PDF → text) → `src/extraction` + `src/baselines` (parallel strands) → `src/evaluation` (frozen gold standard + DigiMOF/SynMOF agreement) → `src/kg` (Neo4j + provenance) → `src/dashboard`.

The load-bearing design decision: **every extractor — LLM or baseline — implements the `Extractor` ABC in `src/extraction/extractor_base.py` and returns the same `Triple` shape**, so all strategies are evaluated head-to-head on identical terms. New extraction strategies subclass `Extractor`; they must not raise from `extract()` (collect into `ExtractionResult.errors`).

`configs/ontology.json` (v0.2, MOF-specific) is the **source of truth** for entity/relation types. ⚠️ Known drift: the `EntityType`/`RelationType` Literals in `extractor_base.py` still reflect ontology v0.1 — align them with v0.2 (plus tests) before writing any extractor.

Prompt templates live in `configs/prompts/` (versioned files, not inline strings).

## Domain rules (non-negotiable)

- **Provenance is mandatory**: every triple carries paper id, section, and evidence sentence; every KG entity gets a `MENTIONED_IN` edge to its `Paper`.
- **Never tune on the gold standard** (`data/annotations/`); it is frozen once the eval protocol is set (Week 6).
- **Cache every LLM call** (responses logged + replayable); never re-pay for the same inference.
- Corpus: open-access, permissively licensed papers only.
- `data/raw/` and `data/processed/` are gitignored; only `data/annotations/` is committed.

## Writing style (user mandate, 2026-06-11)

**Never use an em dash (—) in any document, email, report, or commit message.** Rewrite with a comma, colon, semicolon, parentheses, or a separate sentence. En dashes (–) are allowed only in number/date ranges and in the term "metal–organic framework". This applies to the exposé and everything else produced in this project.

## Research integrity

- **Never cite a paper without verifying it against a live source first** — use the `verify-citation` skill (Crossref/OpenAlex/arXiv). This applies to code comments, docs, reports, everything.
- Never invent measurement results; unmeasured numbers are written as TODO.
- Student identity for documents: Devendra Singh Dhakad, matriculation 100004684, M.Sc. Data Science and AI. (Scaffold files briefly carried a wrong author name/programme — if one resurfaces, fix it.)

## User-private files

`MY_NOTES.md` (repo root, gitignored) is the user's personal scratchpad. Never read, edit, or act on its contents; it is not project context. `/mynotes` opens it in their editor — that is the only interaction allowed.

## Session workflow

- Propose a plan → get confirmation → execute. Incremental commits, tests alongside code, flag risks early.
- End every working session by updating `PROGRESS.md` — use the `progress-log` skill for the format.
- Emails to the supervisor: short (he writes one-liners), draft only — the user sends them.
