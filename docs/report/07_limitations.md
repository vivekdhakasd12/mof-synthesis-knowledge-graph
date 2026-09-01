# 7. Limitations and threats to validity

This chapter states what the study cannot show. Several of these limitations were discovered
during the work and are recorded with the evidence that produced them, so that a reader can
judge their severity rather than take the assessment on trust.

## 7.1 The AT_CONDITION scores measure annotation granularity, not extraction quality

AT_CONDITION scores between 0.00 and 0.17 for every extractor, with 43 false positives for
the best configuration. The cause is a granularity mismatch, not extraction failure. The
annotator recorded a complete condition string as one value, for example
"100 °C for 1 h, then additional 1 h", while the models emit one triple per condition,
"100 °C" and "1 h" separately. Neither convention is wrong and the metric punishes the
mismatch.

**Consequence.** No claim about condition-extraction accuracy in this study is trustworthy.
The field is reported for completeness and excluded from conclusions. Excluding it, the best
configuration averages approximately 0.53 across the three remaining fields.

**Remedy for future work.** Either fix the annotation convention to one condition per triple,
or implement a set-valued comparison for this field that credits a decomposition of a
combined gold value.

## 7.2 Absolute scores are depressed by surface-form mismatch

Manual inspection of gold against predicted triples shows correct extractions scored as
failures because of surface form. Examples observed:

| Gold | Predicted | Status |
|---|---|---|
| `ZrOCl₂·8H₂O` | `ZrOCl2·8H2O` | matched, the normaliser handles Unicode subscripts |
| `DMF` | `dimethylformamide (DMF)` | matched only after a fix, see 7.3 |
| `[emim]Br / bmim` | `1-ethyl-3-methylimidazolium bromide` | not matched, same reagent, absent from the synonym table |

The measured F1 of 0.364 is therefore a lower bound on semantic extraction quality. A study
with a chemical-name resolution service, for example one backed by PubChem or ChemSpider
identifiers, would report higher numbers for identical extractions. This limits comparability
with published figures obtained under different matching regimes.

## 7.3 One normalisation change was made after seeing the data

`normalize_chemical` was extended to resolve "full name (ABBREV)" through either half after
inspection of failures revealed the pattern. This is disclosed rather than folded in
silently. The change raised every extractor by between 0.006 and 0.027, including the rule
baseline, and both sets of numbers are preserved in the repository history. A uniform lift
across all systems is consistent with a genuine surface-form fix rather than tuning toward a
target, but the reader should know the change was made in response to the data.

## 7.4 The gold standard is small, and smaller than planned

The exposé specified 150 to 200 annotated passages; 100 were annotated, yielding 138 triples.
The reduction was a deliberate response to a fixed submission date and the fact that the gold
standard must be produced by hand. The consequence is wide confidence intervals on every
per-field score and insufficient support for four of the eight relations. Differences of the
order of 0.015, such as the schema-guided against chain-of-thought gap on gpt-4o, cannot be
resolved at this sample size and are not treated as findings.

Single-annotator annotation is a further limitation: no inter-annotator agreement statistic
can be computed, so the gold standard's own consistency is unmeasured.

## 7.5 A defect in the annotation tool required an evaluation concession

The annotation interface retained a text field's previous value when the relation changed
while its label changed underneath. Consequently every IN_SOLVENT and AT_CONDITION gold
triple, 68 of 138, records the MOF's name in the subject position where the synthesis method
belongs. The tool was fixed, but the recorded gold standard carries the artefact.

The evaluation therefore scores those two relations on the object alone. This is
independently defensible, because the ontology routes solvents and conditions through a
method that acts as a connector rather than a claim, but it means the study cannot show
whether a model attaches a solvent to the correct synthesis when a passage describes several.
Correcting the gold subjects with a model was rejected, since generating ground truth with a
language model would make the evaluation circular.

## 7.6 The open-weight comparison rests on one prompting strategy

Free-tier token caps prevented three of four open-weight strategies from completing. RQ4 is
therefore answered on zero-shot only. The comparison is like for like, since all three models
have complete zero-shot coverage, but it cannot show whether the open-weight model responds
to prompting strategy in the same way the commercial models do.

The exposé specified Llama-3 via a local Ollama installation. That plan was abandoned twice:
first because 8 GB of RAM made several thousand local inferences impractical within the
schedule, and then because the chosen hosted provider had retired every Llama chat model by
the time of the run. The substitute, qwen3.8-27b, is genuinely open-weight and independent of
the commercial models' lineage, but it is not the model the exposé named.

## 7.7 Corpus scope and its effect on RQ3

The corpus is restricted to the Europe PMC open-access subset. Much open-access chemistry is
not indexed there, so the corpus is not a random sample of MOF literature. The publisher
distribution does overlap DigiMOF's sources, which supports the feasibility of the agreement
analysis, but coverage bias remains.

The DigiMOF supporting information is keyed by CSD refcode while this corpus is keyed by DOI,
and a per-paper join requires a refcode-to-DOI mapping that is normally obtained from a
licensed resource. RQ3 is consequently not answered in this report and is carried as future
work.

## 7.8 Single run, no variance estimate

Every configuration was run once, at temperature 0. No variance across repeated runs is
reported, so apparent differences between configurations include an unmeasured sampling
component even at temperature 0, where provider-side non-determinism can still occur.
