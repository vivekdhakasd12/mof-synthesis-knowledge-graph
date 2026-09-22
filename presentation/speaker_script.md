# Speaker script: Case Study 2 final presentation

**Length:** about 15 minutes spoken, at a normal pace of roughly 130 words a minute. Each slide
carries a target time; if you are given less time, the slides marked *(can shorten)* are the
ones to trim first.

**How to use this.** Do not read it word for word; examiners notice, and it sounds flat. Read it
aloud two or three times until you know the order of the ideas, then speak from the
**Remember** line on each slide. That one line is the thing that slide exists to say. Words in
[brackets] are what to do or point at, not what to say.

The same text is embedded in the `.pptx` as speaker notes, so PowerPoint's Presenter View shows
it on your laptop while the audience sees only the slides.

---

## Slide 1: Title

**Time:** 0:30
**Remember:** I measured how accurately language models read chemistry papers, and what it costs.

Good morning. My name is Devendra Singh Dhakad, and this is my Case Study 2, supervised by
Professor Jalali.

The title is Building and Validating a Metal–Organic Framework Synthesis Knowledge Graph with
Large Language Models.

In one sentence: I measured how accurately AI language models can read chemistry papers and pull
out how a material was made, and what that accuracy costs.

---

## Slide 2: The problem

**Time:** 1:15
**Remember:** The recipes exist, but only as sentences in papers.

First, the problem.

Metal–organic frameworks, or MOFs, are crystals built from metal nodes connected by organic
linkers. Inside they are mostly empty space, and that is what makes them useful: capturing
carbon dioxide, storing gas, catalysis, drug delivery. More than a hundred thousand of them are
recorded in the Cambridge Structural Database.

Every one was made by following a recipe: a metal precursor, a linker, a solvent, a method, a
temperature and a time. But those recipes are written as sentences, inside tens of thousands of
papers. There is no complete structured table of them.

The databases that do exist, like DigiMOF, were built with rule-based text mining. And their own
authors wrote that routes a paper only implies are hard for rules to extract.

[point to the box] So the gap is this. Nobody had measured language-model extraction of MOF
recipes field by field, against both a human answer key and a rule-based baseline, and reported
the cost.

---

## Slide 3: Research questions

**Time:** 1:00 *(can shorten)*
**Remember:** Five questions, four answered, and the fifth has a reason.

That gives five research questions.

RQ1: field by field, how do language models compare with a rule-based baseline built from the
same vocabulary?

RQ2: which of four prompting strategies works best?

RQ3: where do the extractions disagree with DigiMOF and SynMOF?

RQ4: open-weight models against commercial ones, on accuracy, cost and latency.

And RQ5: can the knowledge graph answer questions across hundreds of papers?

I answered four of the five. RQ3 I could not answer, and I will explain exactly why near the
end, because I think the reason is a finding in itself.

---

## Slide 4: What was built

**Time:** 1:30
**Remember:** Every extractor has the same interface, so the comparison is fair.

This is the pipeline.

[start at the top left] I collected 399 open-access papers from Europe PMC, with their sections
already labelled. The segmentation step cut them into 22,086 passages and scored each one on how
much it looks like a synthesis procedure. 794 passed the threshold.

[point to Extraction] Then extraction. The rule-based baseline and the language models sit
inside one stage, because they all implement the same interface and return exactly the same
output shape. That is the design decision that makes the comparison fair: every extractor is
scored on identical terms.

[point to the orange boxes] Notice that every stage writes a file to disk, and the next stage
reads it. So I can rerun any single stage without rerunning the rest, and every intermediate
result can be opened and checked. Every language-model response is also cached, so I never paid
twice for the same call.

[point to the green boxes] At the end, the results go to evaluation, and into a Neo4j knowledge
graph.

---

## Slide 5: The gold standard

**Time:** 1:15
**Remember:** The answer key was made by hand, because a model-made one would be circular.

The most important part of the whole project is this one: the gold standard, the answer key.

I annotated 100 passages by hand, which gave 138 facts, or triples.

The sample was stratified with a fixed seed: 90 passages the filter had flagged as synthesis,
and 10 it had not. Those 10 controls let me measure how often the filter itself misses a recipe,
instead of simply assuming it works.

[point to the box] And I deliberately did not let any model pre-fill it. The gold standard is
the ruler every model is measured against. If a language model had written it, the evaluation
would be circular: any mistake the models share would be counted as correct.

---

## Slide 6: How accuracy was measured

**Time:** 1:15
**Remember:** Provenance is added by the pipeline, so it cannot be hallucinated.

This is the ontology: the schema of what gets extracted. Nine entity types and nine relations,
with the MOF at the centre.

Two details matter. [point] Solvent and Condition attach to the SynthesisMethod, not directly to
the MOF. And MENTIONED_IN, the link back to the source paper, is added by the pipeline and never
by a model, so provenance cannot be hallucinated.

Matching is done per passage and per relation, one to one, so no answer can be credited twice.

And one thing I declare openly. My annotation tool had a bug: it kept the MOF name in the
subject field of the solvent and condition triples. Rather than let a model rewrite the gold
standard, I scored those two relations on the object only, and the report says so.

---

## Slide 7: Results, overall

**Time:** 1:00
**Remember:** Every model beat the rules, and the best one was also one of the cheapest.

Now the results. Ten configurations: the rule baseline, two commercial models, gpt-4o and
gpt-4o-mini, and one open-weight model, with different prompting strategies. The complete set of
experiments cost an estimated 3.06 US dollars, calculated from the recorded token counts at the
providers' published prices.

[point to the chart] Cost runs along the bottom, accuracy up the side, measured as F1.

Two things stand out. Every language-model configuration beats the rule baseline: the weakest
scores 0.191, the baseline 0.112. And the best configuration, here at the top left, is also one
of the cheapest.

---

## Slide 8: Per field, and a pre-registered prediction

**Time:** 1:30
**Remember:** I predicted it in advance; the part that can be tested held.

Now field by field.

On 23 August, eight days before the first model results were recorded, I wrote down a
prediction and committed it to the repository. [point to the box] The language models should beat the rules by
the most on the metal precursor, the linker and the synthesis method, and by the least on
conditions and solvents. My reasoning was that working out which material is being made needs
reading comprehension, whereas a temperature or a solvent name is a simple pattern.

One of those three, the synthesis method, has only a single triple in my gold standard, so it
cannot be tested either way. On the four fields that can be tested, the margins were plus 0.42,
0.31, 0.25 and 0.17. Precursor and linker lead, solvent and condition trail, as predicted. And
because it was written down first, that part is a genuine confirmation.

One caveat. The condition scores are low for every system, because I annotated conditions as one
combined string, while the models split them into separate parts. So that field measures
annotation style rather than accuracy, and I leave it out of my conclusions. Without it, the best
configuration averages about 0.53.

---

## Slide 9: The headline finding

**Time:** 1:45
**Remember:** gpt-4o extracts less. Measured. Why, not yet.

This is the result I think matters most. The cheap model beat the expensive one.

[point to the numbers] gpt-4o-mini with schema-guided prompting scored 0.364, for under three
cents. gpt-4o with few-shot prompting cost 1.29 dollars and scored 0.245. That is a 47 times
cost difference, in favour of the weaker model.

My first explanation was that the bigger model writes more, and the extra output turns into
false positives. But that is a claim I could test for free, because every output was saved. So
I counted.

It was wrong, and wrong in the opposite direction. gpt-4o produces fewer triples than
gpt-4o-mini in all four strategies. The gap is not precision, it is recall. On schema-guided,
gpt-4o finds 39 of the 138 correct facts, gpt-4o-mini finds 61, and precision is almost the
same.

So the larger model extracts less. But I have to be honest about one thing. Every one of my
prompts tells the model to leave a fact out if it is unsure. So gpt-4o might be more cautious
by nature, or it might simply follow my instruction more faithfully. My design cannot tell those
two apart. The fix is simple: run both models again without that line.

---

## Slide 10: Why the rule baseline fails

**Time:** 1:15
**Remember:** It is not a dictionary problem, it is a linking problem.

So why does the rule baseline do so badly?

[point to the chart] It identifies which MOF a passage is about in only 121 of 794 passages,
about 15 percent. And five of the eight relations have the MOF as their subject, so when the MOF
is missing, most of the recipe cannot be extracted at all.

The interesting part is why. In 331 passages, the MOF is named somewhere else in the paper. In
251, it is called something like "compound 1", which is defined in a table. Neither of those is
a missing word in a dictionary.

So for anyone maintaining a rule-based system, the fix is linking across the paper and reading
tables, not a bigger dictionary.

---

## Slide 11: The knowledge graph

**Time:** 1:00 *(can shorten)*
**Remember:** Every fact traces back to its paper, and I checked that with a query.

RQ5, the knowledge graph. Built from the rule-based extractions over all 794 passages, it has
485 distinct nodes and 2,429 relationships, across 182 papers.

Every entity has a MENTIONED_IN edge back to its source paper. I verify that with a query that
looks for any entity without one, and it returns zero rows. So provenance is checked, not just
claimed.

The graph can answer questions across papers. For example, solvothermal synthesis appears in 61
papers, covering 30 MOFs.

[point to the box] One open question. DigiMOF found more hydrothermal than solvothermal records,
and called that surprising. My corpus shows the opposite. I record that; I do not claim to
explain it.

---

## Slide 12: What this cannot show

**Time:** 1:30
**Remember:** Undetermined is not the same as zero.

This slide is what the study cannot show, and I want to be direct about it.

RQ3 is not answered. DigiMOF and SynMOF identify each material by a CSD refcode. My corpus uses
DOIs and the names written in the papers. Joining the two needs a licensed mapping that I did not
have. So the overlap is undetermined, and that is not the same as zero. What I could measure is
that the two databases agree with each other on the metal 98.9 percent of the time, across the
509 MOFs they share.

The best F1, 0.364, is below the 0.80 I targeted in the exposé. Part of that is strict text
matching: a correct answer written differently counts as wrong. So 0.364 is a lower bound.

The gold standard is 100 passages with one annotator, so I cannot compute agreement between
annotators.

Two open-weight runs hit a daily free-tier limit, and I deleted them rather than score them,
because a half-finished run makes a rate-limited model look like a bad model.

And every configuration ran once, so there is no estimate of variance.

---

## Slide 13: Conclusion

**Time:** 0:45
**Remember:** Beat the rules, predicted where, measured what the cheap one does better.

To conclude.

Language models beat the rule baseline in every configuration, and the testable part of my
pre-registered prediction held. The cheaper model won because the larger one extracts less.
That is measured; why it extracts less is not yet. On the like-for-like zero-shot comparison, a free open-weight model reached about
two thirds of the commercial score. And the knowledge graph is provenance-complete, verified by
query.

For future work: obtain a refcode mapping and close RQ3, rerun both models without the
"omit when unsure" instruction to separate caution from obedience, repair the condition
evaluation, and add a second annotator.

Thank you. I am happy to take your questions.
