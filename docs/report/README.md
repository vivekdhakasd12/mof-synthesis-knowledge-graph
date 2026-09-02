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

The report is built with LaTeX:

```bash
python docs/report/build_report.py          # report.tex + report.pdf
python docs/report/build_report.py --no-pdf # .tex only, while writing
```

The markdown chapters are the single source of truth; `report.tex` is generated and should
never be edited by hand, because the next build overwrites it.

**What the build gives you.** The contents page is hyperlinked, every entry jumping to its
section, and the PDF carries a bookmark tree that a reader's sidebar shows, so the document
can be navigated without scrolling. The 30 DOIs in Chapter 9 are clickable. Figures are
pulled in as vector PDFs rather than PNGs.

The engine is Tectonic (`brew install tectonic`), chosen over a full TeX Live because it
resolves and caches the packages it needs on first run, so the document rebuilds on a clean
machine without a multi-gigabyte install.

A headless-Chrome HTML build previously ran alongside this one and was retired on
2026-09-02: it produced a second document to keep in sync for no benefit the LaTeX output
did not already cover.

`build_report.py` converts the markdown itself rather than shelling out to pandoc, which is
not a dependency here. It handles the subset the chapters actually use: headings, tables,
figures with their captions, block quotes, lists, code spans and links. Two details worth
knowing if you extend it. Unicode subscripts are rewritten to `\textsubscript`, because the
default font has no glyph for them and would silently drop the digits from a formula like
Cu₃(BTC)₂. And figures are placed with `[H]`, holding them where they were written,
because the chapters were authored assuming a figure sits directly under the sentence
introducing it.

**Figure numbering is by reading order.** LaTeX numbers the figures itself, straight
through rather than per chapter, and the builder strips the `**Figure N.**` prefix the
markdown captions carry so the number is not printed twice. Those manual numbers therefore
only matter to someone reading the markdown directly, with one exception that does matter:
Section 6.3 refers to "Figure 6" in its body text. If you insert a figure before it, that
reference silently points at the wrong figure. Renumber the captions after any insertion,
or replace the body-text reference with a real cross-reference.

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
