# Final report, working draft

Chapters are separate files so they can be revised independently and rendered together.

| File | Chapter | Status |
|---|---|---|
| `01_introduction.md` | Introduction, research questions, contributions | drafted |
| `02_state_of_the_art.md` | Related work | TO WRITE, expand from the exposé's 13 verified references |
| `03_methodology.md` | Ontology, corpus, segmentation, gold standard, evaluation design | drafted |
| `04_implementation.md` | Architecture, modules, reproducibility | TO WRITE |
| `05_results.md` | All measured results | drafted |
| `06_discussion.md` | Interpretation | TO WRITE, see prompts below |
| `07_limitations.md` | Limitations and threats to validity | drafted |
| `08_conclusion.md` | Conclusion and future work | drafted |
| `09_references.md` | References | TO WRITE, reuse the exposé's verified list |

## Rules this draft follows, and any revision must keep

1. **Every number traces to an artefact.** No figure appears here that was not produced by
   the pipeline. The sources are `docs/results.md`, `docs/kg_results.md`,
   `docs/baseline_findings.md` and `docs/data_sources.md`, all regenerable.
2. **No em dashes**, per the project writing rule.
3. **Support counts accompany every score.** Four of the eight relations have too little gold
   support to conclude from, and the text must keep saying so.
4. **Nothing is claimed that the evaluation cannot show.** In particular, condition-extraction
   accuracy and any comparison of commercial vendors against each other.
5. **Citations are verified before they enter the text**, using the `verify-citation` skill.
   No reference is written from memory.

## What still needs the author

**Chapter 2, state of the art.** The exposé's 13 references are already verified against live
sources and can be lifted. The chapter needs expanding into a narrative with the gap argument
made explicitly, using the DigiMOF authors' own statement about implicit synthesis routes as
the hinge.

**Chapter 4, implementation.** Describe the module structure, the unified extractor interface,
the response cache and the resumable runner. Most of the material exists as module docstrings
written for this purpose.

**Chapter 6, discussion.** The three questions worth answering are: why the cheaper model
outperformed the more expensive one, whether the pre-registered prediction holding validates
the mechanism proposed for it, and what the 15 percent MOF-identification rate of the rule
baseline implies for anyone maintaining a rule-based pipeline.

**Figures.** None are drawn yet. The obvious candidates are a per-field grouped bar chart
across extractors, a cost-against-F1 scatter plot which makes the cheap-model result visible
at a glance, and a schematic of the pipeline.

## Rendering

Follow the exposé's approach: author in HTML, render with headless Chrome. The exposé's
stylesheet in `docs/expose.html` can be reused for visual consistency, including the SRH
logo and the section rules.
