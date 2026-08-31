# Rule-based baseline: measured behaviour and what it implies for the LLM comparison

Measured 2026-08-23 against the real corpus (399 open-access papers, 794 synthesis
passages). Every number here was produced by running the code, not estimated. Reproduce
with `python -m src.pipeline --extractors rule_based --no-resume`.

## Headline numbers

| Metric | Value |
|---|---|
| Synthesis passages processed | 794 |
| Triples extracted | 1,864 |
| Mean triples per passage | 2.35 |
| Passages yielding zero triples | 370 (47 percent) |
| Cost | 0.00 USD |
| Mean latency | 0.6 ms per passage |

By relation: AT_CONDITION 1,007, IN_SOLVENT 557, SYNTHESIZED_BY 126, USES_LINKER 90,
USES_PRECURSOR 70, MEASURED_AT 8, HAS_PROPERTY 6.

The shape of that distribution is the finding. Conditions and solvents, which are matched
by local surface patterns (a number next to a unit, a solvent name from a closed list), are
extracted in bulk. The relations that require knowing *which material* is being made are
one order of magnitude rarer.

## Why: MOF identification is the bottleneck

The ontology makes `MOF` the subject of USES_PRECURSOR, USES_LINKER, SYNTHESIZED_BY,
HAS_PROPERTY and USED_IN. If no framework is identified in a passage, none of those five
relations can be formed, however plainly the reagents are written.

Measured: **the baseline identifies a MOF in only 121 of 794 synthesis passages (15 percent).**

Of the 638 passages containing no recognisable MOF name:

| Cause | Count | Can a rule-based system fix it? |
|---|---|---|
| The name appears elsewhere in the same paper, not in this passage | 331 | No, not at passage level |
| A generic or numbered designation is used ("compound 1", "the resulting framework") | 251 | No |
| The name is in the section heading only | 1 | Yes, trivially |

A third failure mode does not fit a count: novel, paper-specific chemical names such as
`Cu3(NDI)3`, which no dictionary can enumerate in advance because they are coined by the
authors of the paper being read.

## A defect that was fixed, and one that was not

**Fixed.** The baseline originally missed the metal-linker naming convention (Cu-BTC,
Zn-BDC, Co-TPA). Cu-BTC is a standard name for HKUST-1, so this was a defect rather than an
honest limit, and a strawman baseline would invalidate the entire comparison. A closed
metal-plus-linker-shorthand pattern was added, verified to accept Cu-BTC and Co-TPA and to
reject bond notations such as `Cu-O` and `Zn-Zn`. Effect: MOF identification 14 to 15
percent, triples 1,839 to 1,864. Small, and reported as small.

**Not fixed, deliberately.** Cross-passage coreference and generic designations are left
unsolved, because they are genuine limits of passage-level rule-based extraction rather
than oversights. They are reported as limitations instead of being engineered around.

## Why the comparison is still fair

This matters for the methodology section. The LLM extractors see exactly the same passage
text as the baseline, with no document-level context. So the 331 cross-passage cases are
hard for **both** systems, and any LLM advantage there would be suspicious rather than
impressive.

The honest hypothesis is therefore narrower and more testable than "LLMs are better":

1. **Novel and ad hoc material names.** An LLM should recognise `Cu3(NDI)3` as a material
   from sentence structure alone. A dictionary cannot, by construction.
2. **Generic designations.** An LLM should link "the resulting framework" to a synthesis
   described in the same passage. Rules cannot.
3. **Implicit synthesis routes.** The DigiMOF authors state that routes implied by solvent
   and temperature rather than named outright are the hard case for rule-based NLP. The
   baseline attempts these anyway via `_infer_method()`, marked low confidence with a null
   span, so explicit and inferred routes can be scored separately.

Prediction, recorded before the LLM runs so it cannot be fitted afterwards: the LLM margin
should be largest on USES_PRECURSOR, USES_LINKER and SYNTHESIZED_BY, and smallest on
AT_CONDITION and IN_SOLVENT, where local patterns already work well.

## Threats to validity

- The 47 percent zero-triple rate is partly a corpus-precision artefact. Some passages
  classified as synthesis are reagent manifests ("Zinc nitrate hexahydrate (99 percent,
  Sigma-Aldrich), ...") that legitimately contain no synthesis relation.
- The attachment heuristic (nearest preceding MOF when several are named) is a known error
  source and is scored with lowered confidence rather than hidden.
- Conditions belonging to drying, activation or centrifugation are currently emitted as
  synthesis conditions. These are real false positives, left visible rather than filtered.

# Gold standard: validation and one declared evaluation concession

Validated 2026-08-31 against `data/annotations/gold.jsonl` (100 records, hand annotated).

## What the file contains

| Check | Result |
|---|---|
| Records | 100, all valid JSON, correct schema |
| Duplicate passage ids | 0 |
| Passage ids matching the real worklist | 100 of 100 |
| Triples | 138 |
| Ontology-invalid triples (type level) | 0 |
| Triples missing evidence or an entity name | 0 |
| Control passages annotated | 10 of 10 |

Status split: 32 passages carry synthesis records, 68 were marked as containing none.

## Measured: the pre-filter's own precision

Of the 90 passages the synthesis pre-filter flagged, **32 actually contained a synthesis
record, a precision of about 36 percent**. None of the 10 unflagged control passages
contained synthesis content, so no miss was detected in that sample, though 10 is too small
to put a useful bound on recall.

This is exactly what the control stratum was included for. Report both numbers, and report
the control sample size next to the recall statement so it is not read as a strong claim.

## Usable relation coverage is four, not eight

| Relation | Gold support | Usable |
|---|---|---|
| USES_PRECURSOR | 39 | yes |
| IN_SOLVENT | 34 | yes |
| AT_CONDITION | 34 | yes |
| USES_LINKER | 30 | yes |
| SYNTHESIZED_BY | 1 | no |
| HAS_PROPERTY | 0 | no |
| MEASURED_AT | 0 | no |
| USED_IN | 0 | no |

The results chapter must print support beside every score and must draw no conclusion about
the bottom four. Their scarcity is itself reportable: properties and applications are rarely
stated inside a synthesis paragraph, which is a fact about where information lives in a
paper rather than a defect in the extractors.

## The concession: IN_SOLVENT and AT_CONDITION are scored on the object alone

**What happened.** The annotation tool kept a text field's previous value when the relation
changed while its label changed underneath, a Streamlit widget-key defect. As a result every
IN_SOLVENT and AT_CONDITION gold triple, 68 of 138, records the MOF's name in the subject
position where the synthesis method belongs. The tool has been fixed (the field now resets
when the expected entity type changes), but the recorded gold standard carries the artefact.

**Why it could not be left alone.** Scoring those subjects literally marks a model wrong for
correctly answering "solvothermal", because the gold says "NU-1000". That inverts the result
on two of the four relations that have usable support.

**What was done instead.** `SUBJECT_AGNOSTIC_RELATIONS` in `src/evaluation/metrics.py` scores
these two relations on the object alone. The justification is not merely convenience: the
ontology routes solvents and conditions through a synthesis method, so the subject is a
connector rather than a claim, and within one passage there is normally one synthesis, so it
carries no information the passage boundary does not already carry.

**What it costs.** This evaluation cannot show whether a model attaches a solvent to the
correct synthesis when a passage describes more than one. SYNTHESIZED_BY, which would have
tested method identification directly, has a support of 1 and is unusable regardless.

**What was deliberately not done.** The gold subjects were not corrected by a model. Filling
them in would mean generating the ground truth used to judge the models, which is the one
shortcut that would make every accuracy figure circular.

The concession is carried on every `EvaluationResult` as `subject_agnostic_relations`, so a
generated table states it rather than quietly benefiting from it. Tests pin all four
behaviours: the correct object is credited, a wrong object still fails, the other relations
still require their subject, and disabling the flag reproduces the penalty.
