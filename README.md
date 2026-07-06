# Case Study 2 — LLM-Driven Knowledge Graph Construction from Materials Science Literature

**Author:** Devendra Singh Dhakad
**Programme:** M.Sc. Data Science and AI, SRH University of Applied Sciences Heidelberg
**Supervisor:** Prof. Dr. Mehrdad Jalali
**Duration:** 22 June 2026 – 15 September 2026 (12 weeks)

## TL;DR

> **Re-aimed 10 June 2026** — see `docs/HANDOVER.md` for the authoritative framing: *Building and Validating a MOF Synthesis Knowledge Graph with LLMs*.

Build an end-to-end pipeline that uses LLMs to extract MOF synthesis records (metal precursor, organic linker, solvent, method, conditions, properties, applications) from open-access literature, store them in a Neo4j knowledge graph, and validate extraction per field against a hand-annotated gold standard, DigiMOF/SynMOF agreement analysis, and ChemDataExtractor/MatSciBERT baselines. Ship a Streamlit dashboard for natural-language querying with full provenance.

## Repository layout

```
case-study-2/
├── src/
│   ├── ingestion/     # arXiv / ChemRxiv / PMC collectors, PDF parsing
│   ├── extraction/    # LLM-based extractors (zero/few-shot, schema-guided, CoT)
│   ├── baselines/     # ChemDataExtractor, MatSciBERT pipelines
│   ├── kg/            # Neo4j ingestion, entity resolution, Cypher schema
│   ├── evaluation/    # gold-standard, metrics, error analysis
│   └── dashboard/     # Streamlit app, NL→Cypher
├── data/
│   ├── raw/           # PDFs and metadata (gitignored)
│   ├── processed/     # parsed plaintext (gitignored)
│   └── annotations/   # gold-standard (committed)
├── docs/              # exposé, literature review, evaluation report, final report
├── configs/           # ontology JSON-Schema, prompt templates, model configs
├── notebooks/         # exploratory analyses
├── tests/             # pytest suite
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml # neo4j + app
└── PROGRESS.md        # rolling work log
```

## Quick start

```bash
# 1. Install
uv sync   # or: pip install -e ".[dev]"

# 2. Bring up Neo4j
docker compose up -d

# 3. Run a small smoke test
python -m src.ingestion.arxiv_fetcher --query "perovskite solar cell" --max 5
python -m src.extraction.llm_extractor --input data/processed/sample.jsonl --strategy schema_guided

# 4. Launch dashboard
streamlit run src/dashboard/app.py
```

## Phases

See [`docs/expose.docx`](docs/expose.docx) for the full plan. High-level:

| Weeks | Phase | Deliverable |
|-------|-------|-------------|
| 1–2   | Foundation: literature, ontology, scaffolding | `docs/literature_review.md`, `configs/ontology.json` |
| 3     | Corpus collection & PDF parsing | `data/processed/corpus.jsonl` |
| 4–5   | LLM + baseline extractors | `src/extraction`, `src/baselines` |
| 6     | Gold-standard annotation | `data/annotations/gold.jsonl` |
| 7     | KG construction & entity resolution | populated Neo4j graph |
| 8     | Evaluation at scale | `docs/evaluation_report.md` |
| 9     | Error analysis & cost study | extended report |
| 10    | Streamlit dashboard | `src/dashboard/app.py` |
| 11    | Reproducibility, supervisor feedback | clean Docker run |
| 12    | Final report & defence | `docs/final_report.pdf`, slides |

## Working principles

- Reproducibility first: every result reachable from a fresh `docker compose up`.
- Cache LLM calls; never re-pay for the same inference twice.
- Evaluate on a frozen gold standard; never tune on it.
- Provenance is mandatory: every triple in the KG points to a paper, section, and sentence.

## License

Code: MIT. Data: respective sources' open-access licences.
