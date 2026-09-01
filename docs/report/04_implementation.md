# 4. Implementation

The system is roughly 7,100 lines of Python across twenty modules, covered by 199 tests. This
chapter describes the parts whose design was load bearing, and states the reasoning where a
different choice was available. Implementation detail that follows obviously from Chapter 3 is
omitted.

## 4.1 Architecture

The pipeline is a sequence of stages, each writing a file the next stage reads:

```
Europe PMC  ->  corpus.jsonl  ->  passages.jsonl  ->  results.jsonl  ->  evaluation.json
                                        |                   |
                                   gold.jsonl           Neo4j graph
```

Stages communicate through JSON Lines on disk rather than in-process objects. That costs some
speed and buys three things that mattered more: any stage can be rerun without repeating the
ones before it, intermediate state can be inspected with ordinary command-line tools when a
result looks wrong, and a stage that crashes leaves everything before it intact. During
development every one of those properties was used.

| Package | Responsibility | Lines |
|---|---|---|
| `src/ingestion` | Europe PMC access, JATS parsing, passage segmentation | 980 |
| `src/extraction` | Extractor interface, rule baseline, language models, response cache | 2,221 |
| `src/evaluation` | Per-field metrics, evaluation runner, figures | 1,764 |
| `src/kg` | Neo4j schema, provenance-writing loader, named research queries | 462 |
| `src/annotation` | Gold standard annotation tool | 1,169 |
| `src/normalize.py` | Shared chemical-name normalisation | 180 |
| `src/pipeline.py` | Resumable experiment runner | 288 |

## 4.2 The unified extractor interface

The single most consequential design decision is that every extraction strategy, rule-based
and language-model alike, implements one interface and returns the same shape:

```python
class Extractor(ABC):
    name: str
    @abstractmethod
    def extract(self, passage: str, *, paper_id: str | None = None,
                section: str | None = None) -> ExtractionResult: ...
```

`ExtractionResult` carries the extracted triples together with `cost_usd`, `latency_ms` and
`errors`. Two properties of this contract shaped everything downstream.

**Extractors must not raise.** A provider outage, a malformed response or an unparseable
passage becomes an entry in `errors`, never an exception. The reason is operational: a run is
1,300 sequential calls over roughly an hour, and losing all of it to one awkward passage is
unacceptable. The runner still wraps every call in a guard, and a raised exception is recorded
as a contract violation, which is itself a reportable finding rather than a crash.

**Cost and latency belong to the result, not to a separate log.** Because they travel with the
extraction, accuracy, cost and latency can be joined without reconciling two sources, which is
what made the cost-against-accuracy analysis in Chapter 5 straightforward rather than a data
integration exercise.

## 4.3 Ingestion

`europepmc.py` queries the open-access subset and fetches JATS full text, caching every
response to disk so a paper is never downloaded twice. `parse.py` converts JATS into labelled
sections using namespace-agnostic XPath, because JATS documents may or may not declare a
namespace, and flattens inline markup with `itertext()` so that italics or formulae inside a
sentence do not fragment it.

`segment.py` splits sections into passages with character offsets preserved and assigns each a
deterministic identifier derived from paper, section, section occurrence and index. Determinism
is not cosmetic: the gold standard references these identifiers, so a corpus rebuild that
renumbered passages would silently invalidate every annotation.

That property was tested rather than assumed, and the test failed. Seventeen identifiers
collided, which traced not to the segmenter but to the collector: Europe PMC had returned one
paper on two cursor pages and nothing deduplicated it. Deduplication by PMCID and DOI was added
at collection.

## 4.4 Extraction

**The rule-based baseline** (`rule_based.py`, 1,040 lines) keeps its entire vocabulary in one
marked block so the lexicon can be cited and extended without reading the control flow. Entity
names are the literal substring of the passage, so `passage[start:end] == name` holds and every
span is a genuine provenance pointer; canonical forms are produced on demand by the shared
normaliser rather than by rewriting the name, which would break that correspondence.

It attempts implicit synthesis routes rather than skipping them. An organic solvent with a
temperature above a documented threshold and no route word anywhere in the passage is emitted
as "solvothermal" with low confidence and a null span, the null span marking it as inferred so
that explicit and inferred routes can be scored separately. Skipping these would have flattered
the baseline's precision and understated its recall, which would have made the comparison this
project exists to draw less honest rather than more.

**The language-model extractors** (`llm_extractor.py`, 861 lines) separate the provider from
the strategy. An `LLMClient` protocol has one method, so OpenAI, Anthropic, Groq and NVIDIA
differ only in a base URL and an environment variable, and tests inject a deterministic fake
client. An autouse fixture severs `socket.socket` for the whole offline suite, so "these tests
do not touch the network" is enforced by the suite rather than asserted in a comment.

Response parsing is deliberately defensive. Models wrap JSON in prose or code fences, emit
trailing commas, return an object where a list was requested, and occasionally invent relation
types. Everything recoverable is recovered; everything else is recorded. Triples whose endpoints
violate the ontology are dropped with the reason logged, which turns model misbehaviour into
the error taxonomy of Chapter 5 rather than into silent contamination of the results.

One defect found here is worth recording because of what it would have cost. An empty
completion was originally treated as a successful call that found nothing. A reasoning model
that spends its entire token budget thinking returns exactly that, so a model failing every
call was indistinguishable from a model reading carefully and finding nothing. In the
open-weight comparison that would have appeared as a genuine result. An empty completion is now
an error naming the token count and the likely cause.

## 4.5 Cost control

Two mechanisms make repeated experimentation affordable, which for a self-funded project is a
functional requirement rather than an optimisation.

**The response cache** (`cache.py`) keys on a hash of provider, model, prompt template name and
version, strategy, passage text, temperature and maximum tokens. The template *version* is part
of the key so that editing a prompt correctly invalidates its cached answers instead of
silently mixing responses to two different prompts. The key function takes keyword arguments
only: a positional call site that swapped model and strategy would produce a plausible but
wrong key, and that failure would surface as inexplicable cache misses rather than as an error.

**The runner** (`pipeline.py`) is resumable on `(passage_id, extractor)` and flushes after every
row, so an interrupted run loses at most the call in flight and a rerun re-bills nothing. It
also retries on rate limits using the delay the provider itself states, after an early run
discarded 76 of 100 passages by treating a two-second throttle as a permanent failure.

## 4.6 Knowledge graph

`kg/loader.py` writes provenance as structure. Every entity receives a `MENTIONED_IN` edge to
its source paper carrying section and evidence sentence, and every relation edge carries the
evidence, extractor and confidence. Loading is idempotent, using `MERGE` on a normalised key
rather than `CREATE` on the surface form, so a reproducibility rerun cannot inflate the graph
statistics reported in this document.

`kg/queries.py` holds the research queries as named constants rather than leaving them to be
typed into a browser, because they are evidence for a research question and must be rerunnable.
One of them, `provenance_violations`, returns any entity lacking a link to a source paper. It is
included specifically so the central integrity claim of this project can be checked by a reader
rather than trusted. It returns zero rows.

## 4.7 Evaluation

`evaluation/metrics.py` implements per-field scoring with greedy one-to-one assignment, so a
duplicate-emitting extractor cannot match one gold triple repeatedly and inflate its precision.
Matching is built on the same `src/normalize.py` used by the graph loader. That sharing is the
point: if the evaluation decided that `H3BTC` matched `trimesic acid` while the loader created
two separate nodes, the reported accuracy and the delivered artefact would disagree about what
the data contains.

`evaluation/figures.py` generates every figure from `evaluation.json`, so no number in a chart
is transcribed by hand and none can drift from the table beside it.

## 4.8 Reproducibility and quality gates

Python is pinned to 3.11 (a spaCy dependency has no 3.13 wheels). Neo4j runs from
`docker-compose.yml`, so the database is a declared version rather than a local installation.
Every commit passes `ruff`, `ruff format`, `mypy` on all source files, and 199 tests. Coverage
is 73 percent, concentrated on the modules where a silent error would corrupt a result: the
normaliser, the metrics and the extractors.

The whole study is reproducible from a clean checkout with the commands in the repository
README. The response cache means a rerun of the analysis costs nothing; only a deliberate cache
clear re-incurs API spend.
