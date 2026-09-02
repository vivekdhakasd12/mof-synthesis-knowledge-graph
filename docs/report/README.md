# Final report, working draft

Chapters are separate files so they can be revised independently and rendered together.

| File | Chapter | Status |
|---|---|---|
| `01_introduction.md` | Introduction, research questions, contributions | drafted |
| `02_state_of_the_art.md` | Related work | drafted |
| `03_methodology.md` | Ontology, corpus, segmentation, gold standard, evaluation design | drafted |
| `04_implementation.md` | Architecture, modules, reproducibility | drafted |
| `05_results.md` | All measured results | drafted |
| `06_discussion.md` | Interpretation | drafted, full draft for the author to rewrite in their own voice |
| `07_limitations.md` | Limitations and threats to validity | drafted |
| `08_conclusion.md` | Conclusion and future work | drafted |
| `09_references.md` | References | drafted |

All nine chapters now have draft text. What remains is the author's own pass over Chapter 6
(see below), a final proofread, and the outstanding items tracked in `PROGRESS.md`.

## Rules this draft follows, and any revision must keep

1. **Every number traces to an artefact.** No figure appears here that was not produced by
   the pipeline. The sources are `docs/results.md`, `docs/kg_results.md`,
   `docs/baseline_findings.md` and `docs/data_sources.md`, all regenerable. This rule is
   load-bearing rather than decorative: a draft of Section 5.7 once reported an overlap
   figure that was a hardcoded literal in the analysis script rather than a computed
   result, and the figure was wrong. Anything a script prints must be derived by that
   script.
2. **No em dashes**, per the project writing rule.
3. **Support counts accompany every score.** Four of the eight relations have too little gold
   support to conclude from, and the text must keep saying so.
4. **Nothing is claimed that the evaluation cannot show.** In particular, condition-extraction
   accuracy and any comparison of commercial vendors against each other.
5. **Citations are verified before they enter the text**, using the `verify-citation` skill.
   No reference is written from memory.

## What still needs the author

**Chapter 6, discussion, was written as a full draft rather than an outline**, at the
author's request. It argues why the cheaper model likely outperformed the more expensive
one, what the pre-registered prediction's holding does and does not establish, and what the
15 percent MOF-identification rate implies for anyone maintaining a rule-based pipeline. It
carries interpretive claims that a thesis's discussion chapter should ultimately be the
student's own, especially given the project's AI-disclosure obligations: the author should
read it critically, rewrite it in their own voice, and confirm or revise the two
hypotheses it proposes (Sections 6.2 and 6.3) rather than submit it unread.

**Everything else** is drafted from measured artefacts and should need only a proofread, not
a rewrite.

## Rendering

Follow the exposé's approach: author in HTML, render with headless Chrome. The exposé's
stylesheet in `docs/expose.html` can be reused for visual consistency, including the SRH
logo and the section rules.

## Figures

Generated from `data/processed/evaluation.json` with `python -m src.evaluation.figures`, so
they cannot drift from the numbers in the text. Each is written as PDF for print and PNG for
drafts.

| File | Shows | Belongs in |
|---|---|---|
| `figures/fig1_cost_vs_f1` | Accuracy against cost, all ten configurations | 5.2 |
| `figures/fig2_per_field_f1` | Per-field F1 for four representative extractors, with gold support on the axis | 5.3 |
| `figures/fig3_prompting_strategies` | Prompting strategy by commercial model | 5.4 |
| `figures/fig4_precision_recall` | Precision/recall with iso-F1 contours, all ten configurations | 5.2 |
| `figures/fig5_corpus_and_threshold` | Corpus funnel and synthesis-score threshold sensitivity | 3.3 |
| `figures/fig6_baseline_failure_modes` | Why the rule baseline fails to name the MOF, four causes | 6.3 |

**Design constraints these follow, and any new figure must too.** Colour never carries
identity alone: every series also has a marker shape or a hatch pattern, so the figures
survive greyscale printing and colourblind readers. The palette is the Okabe-Ito set in an
order checked with a validator, worst adjacent colour-vision separation Delta E 11.0
against a target of 8.0. No figure uses two y-axes. Gold support is printed on the axis of
the per-field chart rather than hidden in the caption, because a reader must not compare a
field backed by 39 annotations against one backed by 30 without seeing it.
