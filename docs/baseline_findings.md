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
