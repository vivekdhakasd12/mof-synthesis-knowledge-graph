# Building and Validating a MOF Synthesis Knowledge Graph with Large Language Models

**Case Study 2**, M.Sc. Data Science and Artificial Intelligence
SRH University of Applied Sciences Heidelberg

**Author:** Devendra Singh Dhakad (Matriculation No. 100004684)
**Supervisor:** Prof. Dr. Mehrdad Jalali

---

## What this is

An end-to-end pipeline that extracts structured metal-organic framework (MOF) synthesis
records from open-access scientific literature, loads them into a Neo4j knowledge graph with
complete provenance, and **validates** the extractions field by field against a
hand-annotated gold standard and a rule-based baseline.

The emphasis is on validation rather than scale. Prior work demonstrates that language models
can build large materials knowledge graphs; what is less established is how accurate those
extractions are per field, how they compare with the rule-based systems the field already
relies on, and what an open-weight model delivers relative to a commercial API at what cost.

## Key results

| Field | Rule baseline F1 | Best LLM F1 | Margin |
|---|---|---|---|
| USES_PRECURSOR | 0.13 | 0.55 | +0.42 |
| USES_LINKER | 0.26 | 0.57 | +0.31 |
| IN_SOLVENT | 0.23 | 0.48 | +0.25 |
| AT_CONDITION | 0.00 | 0.17 | +0.17 |

This ordering was **predicted and recorded before the models were run**, on the reasoning
that solvents and conditions are matched by local surface patterns that rules already handle
well, whereas identifying which material is being made is not. The prediction held.

A second finding: **the cheaper commercial model outperformed the more expensive one** on
three of four prompting strategies, at a 47-fold cost difference. The strongest configuration
cost 0.028 USD for 100 passages; the most expensive cost 1.289 USD and scored lower.

Full results, including what the evaluation cannot show, are in `docs/results.md` and
`docs/report/`.

## Scale

- **399** open-access papers, 20.6 million characters, every one carrying a DOI
- **22,086** segmented passages, **794** classified as synthesis text
- **100** hand-annotated gold passages containing **138** triples
- **1,000** extraction runs across 10 configurations, 3.06 USD total
- Knowledge graph of **485** nodes and **2,429** relationships across 182 papers, with
  **zero** provenance violations (every entity traces to its source paper by query)

## Repository layout

```
src/ingestion/     corpus collection from Europe PMC, JATS parsing, passage segmentation
src/extraction/    unified extractor interface, rule-based baseline, LLM extractors, cache
src/evaluation/    per-field metrics, agreement analysis, figures
src/kg/            Neo4j schema, provenance-writing loader, named research queries
src/annotation/    gold standard annotation tool
src/pipeline.py    resumable experiment runner
configs/           ontology (source of truth for the type system), prompt templates
docs/              data sources, findings, results, report
tests/             199 tests
```

## Running it

```bash
uv sync                                     # install
pytest                                      # 199 tests
docker compose up -d                        # Neo4j with APOC

python -m src.ingestion.build_corpus --limit 400
python -m src.ingestion.segment --synthesis-only
bash scripts/run_experiments.sh --smoke     # verify API keys cheaply
bash scripts/run_experiments.sh             # full grid
python -m src.evaluation.run_eval --mode relaxed
python -m src.evaluation.figures
python docs/report/build_report.py
```

API keys go in `.env` (see `.env.example`); `scripts/set_keys.sh` writes them without
echoing. The response cache means a rerun costs nothing, and the experiment runner resumes
per (passage, extractor) so an interrupted run is never billed twice.

## Design decisions worth reading the code for

- **Provenance is structural, not advisory.** Every entity in the graph carries a
  `MENTIONED_IN` edge to its source paper with the section and evidence sentence. The claim
  is checkable: `src/kg/queries.py` includes a query that must return zero rows.
- **One shared normaliser** (`src/normalize.py`) is used by both the evaluation and the graph
  loader, so the reported accuracy and the delivered artefact cannot disagree about whether
  two chemical names denote the same reagent.
- **The gold standard was annotated by hand**, deliberately never pre-filled by a model,
  because it is the instrument the models are measured against.
- **Extractors never raise.** Failures are recorded in the result so a single awkward passage
  cannot abort a multi-hour run, and an empty model response is recorded as an error rather
  than silently counted as "found nothing".

## Licence

**Code and annotations: MIT.**

**Quoted paper text is not covered by that licence.** `data/annotations/gold.jsonl` embeds
verbatim excerpts from third-party open-access papers (71 CC BY, 19 CC BY-NC-ND, 10 CC BY-NC),
each carrying its own `source_doi`, `source_title`, `source_license` and `source_url` so it can
be traced and credited. Anyone reusing that file must respect the licence of the specific paper
an excerpt came from. See `data/annotations/README.md`.

The corpus itself (`data/raw/`, `data/processed/`) is not redistributed here and is rebuilt
from Europe PMC by `src/ingestion/build_corpus.py`.
