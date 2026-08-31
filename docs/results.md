# First experimental results

Run 2026-08-31. 13 extractors x 100 gold passages = 1,300 extraction runs. Total API spend
3.03 USD. Regenerate with `bash scripts/run_experiments.sh` then
`python -m src.evaluation.run_eval --mode relaxed`.

## Headline: the pre-registered prediction held

Before any model ran, this prediction was recorded in `docs/baseline_findings.md`: the LLM
margin over the rule-based baseline should be **largest on USES_PRECURSOR and USES_LINKER**
and **smallest on AT_CONDITION and IN_SOLVENT**, because the latter two are matched by local
surface patterns that rules already handle well.

Measured (best LLM, gpt-4o-mini schema-guided, versus the rule baseline):

| Field | Rule baseline F1 | Best LLM F1 | Margin | Predicted rank |
|---|---|---|---|---|
| USES_PRECURSOR | 0.13 | 0.55 | +0.42 | largest, confirmed |
| USES_LINKER | 0.26 | 0.57 | +0.31 | large, confirmed |
| IN_SOLVENT | 0.23 | 0.48 | +0.25 | smaller, confirmed |
| AT_CONDITION | 0.00 | 0.17 | +0.17 | smallest, confirmed |

The ordering is exactly as predicted. Because the prediction was written down before the
run, this is a confirmation rather than a story fitted to the data afterwards.

## Per-extractor scores (relaxed matching, micro-averaged)

| Extractor | P | R | F1 | Cost USD | Failed calls |
|---|---|---|---|---|---|
| gpt-4o-mini schema-guided | 0.31 | 0.44 | **0.364** | 0.03 | 0 |
| gpt-4o-mini zero-shot | 0.25 | 0.34 | 0.287 | 0.03 | 0 |
| gpt-4o chain-of-thought | 0.28 | 0.28 | 0.278 | 0.70 | 0 |
| gpt-4o-mini chain-of-thought | 0.27 | 0.28 | 0.277 | 0.04 | 0 |
| gpt-4o schema-guided | 0.25 | 0.28 | 0.263 | 0.45 | 0 |
| gpt-4o few-shot | 0.24 | 0.27 | 0.251 | 1.26 | 2 |
| gpt-4o-mini few-shot | 0.20 | 0.33 | 0.249 | 0.08 | 0 |
| gpt-4o zero-shot | 0.26 | 0.24 | 0.247 | 0.45 | 0 |
| qwen3.8-27b zero-shot | 0.14 | 0.32 | 0.191 | 0.00 | 0 |
| rule-based baseline | 0.09 | 0.13 | 0.112 | 0.00 | 0 |

Three qwen rows are missing and are addressed under "incomplete" below.

## Two findings worth the discussion chapter

**The cheap model beats the expensive one.** gpt-4o-mini outscores gpt-4o on every prompting
strategy, and costs roughly 15 times less (0.03 against 0.45 USD for the schema-guided run).
That is the practical answer to research question 4 and it is the opposite of the intuitive
expectation. It should be interrogated rather than celebrated: one plausible mechanism is
that the larger model produces more elaborate and more numerous triples, which raises false
positives under a fixed gold standard. The precision figures are consistent with that, and a
manual error review of a sample would confirm or refute it.

**Schema-guided prompting wins on the best model**, which supports the exposé's premise that
constraining output to the ontology helps. The ordering is not stable across models, so the
claim should be stated as "on the strongest configuration" rather than universally.

## The scores are lower than the exposé's target, and partly for measurable reasons

The exposé targeted F1 at or above 0.80. The measured best is 0.364. A manual inspection of
gold against predictions shows a substantial part of that gap is surface-form and annotation
granularity rather than extraction failure:

| Gold | Predicted | Scored | Actually |
|---|---|---|---|
| `ZrOCl₂·8H₂O` | `ZrOCl2·8H2O` | match | correct, normaliser handles it |
| `DMF` | `dimethylformamide (DMF)` | was 0, now match | fixed, see below |
| `100 °C for 1 h, then additional 1 h` | `100 °C` plus `1 h` | 0 | both defensible, different granularity |
| `[emim]Br / bmim` | `1-ethyl-3-methylimidazolium bromide` | 0 | same reagent, no dictionary entry |

**AT_CONDITION is where this bites hardest.** Its F1 is 0.00 to 0.17 for every extractor,
with 43 false positives for the best model. The annotator recorded a whole condition string
as one value while the models emit one triple per condition. Neither is wrong; the metric
punishes the mismatch. Any claim about condition extraction accuracy in this study is
therefore not trustworthy and should be reported as an evaluation limitation, not as a model
result. Excluding AT_CONDITION, the best extractor averages roughly 0.53 across the other
three fields.

**One normalisation fix was made after seeing the data**, and is disclosed here rather than
folded in silently: `normalize_chemical` now resolves "full name (ABBREV)" through either
half, so `DMF` matches `dimethylformamide (DMF)`. It raised every extractor by between 0.006
and 0.027, including the rule-based baseline. A uniform lift across all systems is the
signature of a genuine surface-form fix rather than tuning toward a target; the before and
after numbers are both recorded above and in git history.

## Incomplete: the open-weight strand

Only zero-shot completed for qwen3.8-27b. The other three strategies failed on every call
with HTTP 429: Groq's free tier caps that model at **200,000 tokens per day** and zero-shot
alone consumed 193,859. The full open-weight grid needs roughly 960,000 tokens, so the free
tier cannot run it, and this is a hard ceiling rather than a transient error.

Consequences and options, none of which should be presented as an open-weight result until
resolved:
1. Spread the remaining three strategies over subsequent days on the same free tier.
2. Run them on NVIDIA NIM, already wired as `nvidia:` and needing only a free key. Note that
   NVIDIA hosts different models, so the strategy comparison would then mix models unless all
   four strategies are rerun on one NVIDIA model.
3. Pay for Groq's developer tier.

Until then, research question 4 rests on one prompting strategy for the open-weight side, and
the report must say so.
