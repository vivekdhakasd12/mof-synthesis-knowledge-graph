# Gold standard annotation

## Launch

```bash
cd "/Users/dev/Agentic Workflows /case-study-2"
.venv/bin/streamlit run src/annotation/app.py
```

Work is saved to `data/annotations/gold.jsonl` after every action. That directory is the
one part of `data/` committed to git, so the gold standard is versioned with the code.
Closing the browser loses nothing; reopening resumes at the first unreviewed passage.

## What you are annotating and why it is you doing it

The gold standard is the yardstick every accuracy number in this project is measured
against. It has to be human work: pre-filling it with model output would mean judging the
models against their own output, which is circular and would not survive a viva. The tool
therefore constrains and speeds up your choices, but never proposes an answer.

Your worklist is **100 passages**, drawn deterministically (seed fixed, so it can be
regenerated from the corpus for a reproducibility check):

- **90 from the synthesis pool** flagged by the pre-filter, because the graded question is
  per-field accuracy on synthesis records.
- **10 control passages the filter did NOT flag.** These exist so the pre-filter's own miss
  rate is measurable. Without them, every recall figure in the report would be silently
  conditional on an unvalidated heuristic. Annotate them exactly as honestly as the rest;
  finding synthesis content in a control passage is a useful result, not a mistake.

The two strata are interleaved rather than blocked, so fatigue does not fall on one stratum.

Target: **80 to 100 annotated. Budget 2 to 3 hours.** Do it in several sittings; consistency
degrades quickly when tired, and consistency matters more here than speed.

**On the sample size.** The exposé said 150 to 200; this was cut to 80 to 100 on 2026-08-31
because annotator hours are the binding constraint and the submission date is fixed. State
that plainly in the methodology, along with what it costs: wider confidence intervals on
every per-field score, and possibly too little support to say anything about the rarer
relations. Print per-field support counts next to every score and do not draw conclusions
from a field whose support is in single figures.

**The cut is extensible, not destructive.** Because the seed and the strata are unchanged,
these 100 passages are a strict subset of the original 200-item worklist. If time appears
later, raise `TARGET_MAX` back to 200 and keep annotating; nothing already done is wasted or
needs redoing.

## The rules. Follow them even when you disagree

Consistency beats correctness on judgement calls: a rule applied uniformly can be described
in the methodology and reasoned about, while a rule applied half the time is noise that
depresses every score.

**Only annotate what the passage itself states.** The extractors see this passage and
nothing else, so a fact you know from elsewhere in the paper is not available to them.
Annotating it would measure their telepathy rather than their extraction.

**Solvents.** Annotate the reaction solvent via `SynthesisMethod -[IN_SOLVENT]-> Solvent`.
Do **not** annotate washing, rinsing or solvent-exchange solvents. Rationale: the ontology
models the synthesis route, and washing solvents would swamp the reaction solvent in any
cross-paper aggregation. If the same solvent is used for both, annotate it once.

**Temperature and time ranges.** Record the surface form as written: "100 to 120 C" stays
"100 to 120 C", not "110 C". Never convert units; "393 K" stays Kelvin. The evaluation
normalises unit spelling but must never see a magnitude you invented.

**Drying, activation and degassing conditions.** Do not annotate these as `AT_CONDITION`.
Only conditions of the framework-forming step count. This is the single most common
inconsistency, so when in doubt ask whether the MOF exists yet at that point.

**Linkers named only by abbreviation.** Annotate the abbreviation exactly as it appears
("H3BTC", "HmIM"). The shared normaliser resolves it to the full name at scoring time, so
you do not need to expand it and should not guess an expansion.

**A framework named only as "compound 1" or "the resulting solid".** If the passage never
gives a chemical or trivial name, mark the passage **no synthesis content** only when there
is genuinely no extractable record. If reagents and conditions are stated but the material
is unnamed, annotate the relations you can anchor and leave the MOF-subject relations out.
Do not invent a name.

**Multi-step syntheses (a linker is made first, then the MOF).** Annotate only the
framework-forming step. Ligand synthesis is real chemistry but it is not MOF synthesis, and
mixing the two would make precursor counts meaningless.

**Several MOFs in one passage.** Annotate each relation against the MOF it truly belongs
to, even when that is tedious. This is exactly where the rule-based baseline is expected to
fail, so accuracy here carries a lot of the project's evidential weight.

**When genuinely unsure, skip.** There are 794 candidate synthesis passages and you need
150 to 200. Skipping an ambiguous passage costs nothing; a coin-flip annotation silently
corrupts the yardstick.

## After you finish

Freeze it. Once the evaluation protocol is set the gold standard must not be edited, or
results stop being comparable across runs. If you find a genuine error afterwards, record
the correction and rerun everything rather than editing quietly.
