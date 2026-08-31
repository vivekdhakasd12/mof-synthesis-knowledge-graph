# Knowledge graph: first populated build

Measured 2026-08-31 from the rule-based baseline over 794 synthesis passages. Reproduce with
`docker compose up -d` then the loader against `data/processed/results.jsonl`.

## Load

| Metric | Value |
|---|---|
| Triples offered | 1,864 |
| Triples written | 1,864 |
| Triples skipped | 0 |
| Load errors | 0 |
| Distinct nodes | 485 |
| Relationships | 2,429 |
| Papers represented | 182 |

Entity resolution is doing real work: 3,728 node merge operations collapsed to 485 distinct
nodes, so surface variants of the same reagent are being unified rather than duplicated.

## Provenance: verified, not asserted

`provenance_violations` returns **0 rows**. Every non-Paper entity in the graph has a
MENTIONED_IN edge to the paper it came from. This is the project's central integrity claim
and it is now checkable by anyone with a single query rather than taken on trust.

## Node distribution

Paper 182, Condition 164, MOF 44, MetalPrecursor 28, SynthesisMethod 27, Solvent 20,
OrganicLinker 11, Property 9.

The shape mirrors the extractor's known bias: conditions and solvents are matched by local
surface patterns and are plentiful, while MOF, linker and precursor nodes are scarce because
the baseline identifies a framework in only 15 percent of passages.

## Cross-paper aggregation (research sub-question 4)

Synthesis method distribution across the corpus:

| Method | Papers | MOFs |
|---|---|---|
| solvothermal | 61 | 30 |
| hydrothermal | 43 | 12 |
| electrochemical | 36 | 6 |
| microwave-assisted | 36 | 6 |
| stirred at room temperature | 35 | 5 |
| reflux | 21 | 3 |

**A comparison worth making in the report.** DigiMOF reported *more* hydrothermal (5,677) than
solvothermal (3,672) records and called that surprising, since solvothermal is the more common
laboratory route; they attributed it to implicit routes going unnamed. Our corpus shows the
opposite ordering, solvothermal ahead of hydrothermal. That difference is a real finding to
interrogate rather than to smooth over: it may reflect corpus composition (Europe PMC open
access versus their CSD-derived set), or a difference in how each system infers an unnamed
route. Worth a paragraph either way.

## A limitation the graph makes visible

The solvent-and-temperature-by-linker query runs, but returns a near cross product: the same
13 terephthalic acid MOFs appear against many solvent and condition combinations. This is the
attachment heuristic showing through. Conditions attach to a synthesis method within a
sentence window, so drying, activation and washing conditions land alongside the
framework-forming ones and multiply out in aggregation.

This is a genuine, reportable weakness of the baseline rather than a bug to hide, and it is a
second testable prediction: LLM extraction, which can tell a framework-forming step from a
workup step, should produce a materially cleaner aggregation here. Compare the two once the
LLM runs land.
