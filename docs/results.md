# Experimental results

Run 2026-08-31 to 2026-09-01. 10 extractors, 100 hand-annotated gold passages, 138 gold
triples. Total API spend 3.06 USD. Regenerate with `bash scripts/run_experiments.sh` then
`python -m src.evaluation.run_eval --mode relaxed`.

Every extractor below has complete coverage of all 100 passages. Two configurations were
removed rather than reported partially, see "What is missing".

## Headline: the pre-registered prediction held

Recorded in `docs/baseline_findings.md` before any model ran: the LLM margin over the rule
baseline should be largest on USES_PRECURSOR and USES_LINKER, smallest on AT_CONDITION and
IN_SOLVENT, because the latter two are matched by local surface patterns that rules already
handle.

| Field | Rule baseline F1 | Best LLM F1 | Margin | Prediction |
|---|---|---|---|---|
| USES_PRECURSOR | 0.13 | 0.55 | +0.42 | largest, confirmed |
| USES_LINKER | 0.26 | 0.57 | +0.31 | large, confirmed |
| IN_SOLVENT | 0.23 | 0.48 | +0.25 | smaller, confirmed |
| AT_CONDITION | 0.00 | 0.17 | +0.17 | smallest, confirmed |

The ordering matches exactly. Because the prediction was written before the run, this is a
confirmation rather than a pattern found afterwards.

## Full results (relaxed matching, micro-averaged)

| Extractor | P | R | F1 | Cost USD | Mean latency |
|---|---|---|---|---|---|
| gpt-4o-mini schema-guided | 0.310 | 0.442 | **0.364** | 0.028 | 3.3 s |
| gpt-4o-mini zero-shot | 0.249 | 0.341 | 0.287 | 0.030 | 3.8 s |
| gpt-4o chain-of-thought | 0.281 | 0.275 | 0.278 | 0.701 | 5.8 s |
| gpt-4o-mini chain-of-thought | 0.271 | 0.283 | 0.277 | 0.037 | 5.2 s |
| gpt-4o schema-guided | 0.245 | 0.283 | 0.263 | 0.446 | 6.5 s |
| gpt-4o-mini few-shot | 0.199 | 0.333 | 0.249 | 0.083 | 4.5 s |
| gpt-4o zero-shot | 0.256 | 0.239 | 0.247 | 0.447 | 3.2 s |
| gpt-4o few-shot | 0.226 | 0.268 | 0.245 | 1.289 | 8.0 s |
| qwen3.8-27b zero-shot (open weight) | 0.136 | 0.319 | 0.191 | 0.000 | 13.2 s |
| rule-based baseline | 0.098 | 0.130 | 0.112 | 0.000 | 0.001 s |

## Research question 4: open weight against commercial

Compared like for like on zero-shot, the one strategy where all three models have complete
coverage, so model and strategy are not confounded:

| Model | F1 | Cost | Latency |
|---|---|---|---|
| gpt-4o-mini (commercial) | 0.287 | 0.030 USD | 3.8 s |
| gpt-4o (commercial) | 0.247 | 0.447 USD | 3.2 s |
| qwen3.8-27b (open weight) | 0.191 | 0.000 USD | 13.2 s |
| rule baseline | 0.112 | 0.000 USD | 0.001 s |

The ordering is commercial, then open weight, then rules. The open-weight model reaches
about two thirds of the best commercial F1 at zero marginal cost, and is roughly four times
slower on a free tier that throttles aggressively. For a project that must run repeatedly on
a student budget, that is a real and defensible trade rather than an obvious loss.

**The cheap commercial model beats the expensive one.** gpt-4o-mini outscores gpt-4o on
three of four prompting strategies. The strongest configuration overall, gpt-4o-mini
schema-guided, costs 0.028 USD; the most expensive configuration, gpt-4o few-shot, costs
1.289 USD and scores lower. That is a 47-fold cost difference in favour of the weaker model.

This should be interrogated rather than celebrated. The plausible mechanism is that the
larger model emits more numerous and more elaborate triples, which raises false positives
against a fixed gold standard; its precision figures are consistent with that. A manual
error review of a sample would settle it and belongs in the discussion.

## Research question 2: prompting strategies

Commercial models only, all four strategies complete:

| Model | zero-shot | few-shot | schema-guided | chain-of-thought |
|---|---|---|---|---|
| gpt-4o-mini | 0.287 | 0.249 | **0.364** | 0.277 |
| gpt-4o | 0.247 | 0.245 | 0.263 | **0.278** |

Schema-guided wins clearly on the stronger configuration, which supports the exposé's
premise that constraining output to the ontology helps. It does not win universally: on
gpt-4o, chain-of-thought edges ahead by 0.015, which is within the noise a 138-triple gold
standard can resolve. The honest claim is that schema-guided is the best single choice
observed, not that it dominates.

Few-shot is the weakest strategy on both models despite being by far the most expensive
prompt (4,054 template tokens against 652 for schema-guided). That is a useful negative
result: the worked examples cost roughly six times more per call and bought nothing here.

## Absolute scores are below the exposé target, and partly for measurable reasons

The exposé targeted F1 at or above 0.80; the best measured is 0.364. Manual inspection of
gold against predictions shows a substantial part of the gap is surface form and annotation
granularity rather than extraction failure:

| Gold | Predicted | Scored | Reality |
|---|---|---|---|
| `ZrOCl₂·8H₂O` | `ZrOCl2·8H2O` | match | correct, the normaliser handles it |
| `DMF` | `dimethylformamide (DMF)` | match after fix | see disclosure below |
| `100 °C for 1 h, then additional 1 h` | `100 °C` plus `1 h` | no match | both defensible, different granularity |
| `[emim]Br / bmim` | `1-ethyl-3-methylimidazolium bromide` | no match | same reagent, absent from the dictionary |

**AT_CONDITION is where this bites hardest**: F1 between 0.00 and 0.17 for every extractor,
with 43 false positives for the best model. The annotator recorded a whole condition string
as one value while models emit one triple per condition. Neither is wrong and the metric
punishes the mismatch, so condition accuracy in this study is an evaluation limitation and
must not be reported as a model result. Excluding AT_CONDITION, the best extractor averages
about 0.53 across the remaining three fields.

**Disclosed change made after seeing data.** `normalize_chemical` now resolves
"full name (ABBREV)" through either half. It raised every extractor by between 0.006 and
0.027, including the rule baseline. A uniform lift across all systems is the signature of a
surface-form fix rather than tuning toward a target; both sets of numbers are in git history.

## What is missing, and why it was removed rather than reported

Three of four open-weight strategies could not be completed. Groq's free tier caps this
model at 200,000 tokens per day and 8,000 per minute. The per-minute throttle is handled by
retrying on the provider's own suggested delay, but the daily cap is a hard stop: 26 of 100
passages completed for schema-guided before it was exhausted, and 3 of 100 for few-shot.

Both were deleted from the results file rather than scored. A configuration answering 26 of
100 passages is scored against all 138 gold triples and reports an artificially low recall,
which would misrepresent the model as weak when it was merely rate limited. Reporting a
strategy as not obtained is honest; reporting it as scoring near zero is not.

Consequently research question 4 rests on a single prompting strategy for the open-weight
side. Completing it needs either several more days on the free tier, a paid Groq tier, or a
different host.
