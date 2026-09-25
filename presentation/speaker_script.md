# Speaker script: Case Study 2 final presentation

**Length:** about 10 minutes at a normal speaking pace, which leaves room for questions in a
15 minute slot. Slides marked *(can cut)* go first if you are running long.

**How to use this.** Don't read it out. Say it aloud a few times until the order of ideas sticks,
then present from the **Remember** line on each slide. That line is the one thing the slide
exists to say. Anything in [brackets] is what to do, not what to say.

The same text sits in the `.pptx` as speaker notes, so Presenter View shows it on your laptop
while the audience sees only the slide.

---

## Slide 1: Title

**Time:** 0:25
**Remember:** How well can AI read a chemistry paper, and what does it cost.

Good morning. I'm Devendra Singh Dhakad, and this is my Case Study 2, supervised by Professor
Jalali.

The question I set out to answer is easy to say. How accurately can an AI read a chemistry paper
and pull out how the material was made? And what does that accuracy cost?

---

## Slide 2: The problem

**Time:** 1:05
**Remember:** The recipes exist. They're just sentences in papers.

So, MOFs. They're crystals built from metal nodes joined by organic linkers, and inside they're
mostly empty space. That's what makes them useful, for capturing CO2, storing gas, catalysis,
drug delivery. Over a hundred thousand of them are in the Cambridge database.

Every one was made by following a recipe. A metal precursor, a linker, a solvent, a temperature,
a time. But those recipes are just sentences, sitting inside thousands of papers. Nobody has
them as data.

[point to the box] The databases that do exist were built with rule-based text mining, and their
own authors say the hard cases are the routes a paper only hints at. What nobody had done is
measure how well an AI does this, field by field, against a human answer key, and report what
it costs.

---

## Slide 3: Research questions

**Time:** 0:45 *(can cut)*
**Remember:** Five questions, four answered, and the fifth has a reason.

That gave me five questions.

How do language models compare with a rule-based baseline, field by field. Which way of asking
works best. Where do my extractions disagree with the DigiMOF and SynMOF databases. How does a
free open-weight model compare with the paid ones. And can the knowledge graph answer questions
across hundreds of papers.

I answered four of them. The third I couldn't, and I'll come back to why, because I think the
reason is worth hearing.

---

## Slide 4: What was built

**Time:** 1:10
**Remember:** Same interface for every extractor, so the comparison is fair.

Here's the pipeline.

[top left] I pulled 399 open-access papers from Europe PMC. Cut them into 22,086 paragraphs, and
scored each one on how much it looks like a recipe. 794 passed.

[Extraction] Then extraction. The rule-based baseline and the language models sit in the same
box, because they all implement one interface and return the same shape. That's the thing that
makes the comparison fair.

[orange boxes] And every stage writes a file that the next stage reads. So I can rerun one stage
without the others, and I can open any intermediate result and check it. Every model response is
cached too, so I never paid twice for the same call.

---

## Slide 5: The gold standard

**Time:** 1:00
**Remember:** Made by hand, because a model-made answer key would be circular.

This slide is the one that matters most. The gold standard. The answer key.

I annotated 100 passages by hand, and that gave me 138 facts.

90 of them the filter had flagged as synthesis, 10 it hadn't. Those 10 are controls. They tell
me whether my filter is missing recipes, instead of me just assuming it isn't.

[point to the box] And no model touched it. That was deliberate. This is the ruler I measure
every model against. If an AI had written it, any mistake the models share would count as
correct, and the whole evaluation would be circular.

---

## Slide 6: How accuracy was measured

**Time:** 1:00
**Remember:** Provenance is added by the pipeline, so it can't be hallucinated.

This is the ontology. Nine entity types, nine relations, the MOF in the middle.

Two things to notice. [point] Solvent and condition hang off the synthesis method, not off the
MOF. And MENTIONED_IN, the link back to the paper, is added by my pipeline and never by a model.
So provenance can't be hallucinated.

I should also be upfront about one thing. My annotation tool had a bug. It left the MOF name in
the subject field for solvent and condition. I could have had a model clean that up, but that
would contaminate my ruler. So instead I score those two relations on the object only, and I say
so in the report.

---

## Slide 7: Results, overall

**Time:** 0:50
**Remember:** Everything beat the rules, and the best was also nearly the cheapest.

Now the results. Ten configurations. The rule baseline, gpt-4o, gpt-4o-mini, and one free
open-weight model, across different prompting strategies. The whole thing cost about three
dollars, and I should say that's an estimate from token counts, not an invoice.

[point to the chart] Cost along the bottom, accuracy up the side.

Two things stand out. Every language model beats the baseline. And the best one sits at the top
left, so it's also one of the cheapest.

---

## Slide 8: Per field, and a pre-registered prediction

**Time:** 1:10
**Remember:** I wrote it down first, and the testable part held.

Field by field now.

Back in August, before I ran a single model, I wrote down a prediction and committed it.
[point to the box] The models should beat the rules by the most on the precursor, the linker and
the method, and by the least on conditions and solvents. My thinking was that working out which
material is being made takes real reading, whereas a temperature is just a pattern.

One of those three, the method, has only a single triple in my gold standard, so I can't test it
either way. On the four I can test, the margins came out plus 0.42, 0.31, 0.25 and 0.17.
Precursor and linker lead, solvent and condition trail. That's what I predicted, and it was
timestamped before I ran anything.

---

## Slide 9: The headline finding

**Time:** 1:20
**Remember:** gpt-4o extracts less. That's measured. Why, I don't know yet.

This is the result I care about most. The cheap model beat the expensive one. 0.364 for under
three cents, against 0.245 for a dollar twenty-nine.

My first explanation was that the bigger model writes more, and the extra turns into wrong
answers. I could test that for free, because I'd saved every output. So I counted.

I was wrong, and backwards. gpt-4o produces fewer facts than the mini, in all four strategies.
It isn't a precision problem, it's recall. On the best strategy gpt-4o finds 39 of the 138, and
the mini finds 61.

So gpt-4o extracts less. But I have to be honest about one thing. Every one of my prompts tells
the model to leave a fact out when it's unsure. So maybe gpt-4o is more cautious, or maybe it
just follows my instruction better. My setup can't separate those two.

---

## Slide 10: Why the rule baseline fails

**Time:** 1:00
**Remember:** Not a dictionary problem. A linking problem.

So why is the rule baseline so bad?

[point to the chart] It works out which MOF the passage is about only 121 times out of 794.
Fifteen percent. And five of my eight relations need the MOF, so when that's missing, most of
the recipe goes with it.

The why is the interesting part. In 331 cases the MOF is named somewhere else in the paper. In
251 it's called something like "compound 1", and defined in a table. Neither of those is a
missing word in a dictionary. So if you maintain one of these systems, the fix is linking across
the paper and reading tables, not a bigger dictionary.

---

## Slide 11: The knowledge graph

**Time:** 0:50 *(can cut)*
**Remember:** Every fact traces back to its paper, and I check that with a query.

The knowledge graph. 485 nodes, 2,429 relationships, across 182 papers.

Every entity links back to the paper it came from. And I don't just claim that, I check it.
There's a query that looks for any entity without that link, and it comes back empty.

It answers questions across papers too. Solvothermal shows up in 61 papers, covering 30 MOFs.

[point to the box] One thing I can't explain. DigiMOF found more hydrothermal than solvothermal
and called that surprising. I get the opposite. I'm recording it, not explaining it.

---

## Slide 12: What this cannot show

**Time:** 1:15
**Remember:** Undetermined isn't the same as zero.

Now what this doesn't show. I want to be direct about it.

RQ3 isn't answered. The reference databases identify each material by a CSD refcode. I use DOIs
and the names written in the papers. Joining them needs a licensed mapping I don't have. So the
overlap is undetermined, and that isn't the same as zero. What I could measure is that those two
databases agree with each other 98.9 percent of the time, on the 509 MOFs they share.

My best score, 0.364, is below the 0.80 I aimed for. Some of that is strict text matching, where
a right answer spelled differently counts as wrong.

One annotator and 100 passages, so I can't report agreement between annotators.

Two runs hit a free-tier daily limit, and I deleted them rather than score them, because a
half-finished run makes a rate-limited model look like a bad one.

And everything ran once, so I have no variance.

---

## Slide 13: Conclusion

**Time:** 0:45
**Remember:** Beat the rules, called it in advance, measured what the cheap one does better.

To finish.

Language models beat the rule baseline every time, and the testable part of my prediction held.
The cheap model won because the bigger one extracts less. That part is measured. Why it does,
I don't know yet. On the like-for-like comparison the free model got about two thirds of the
commercial score. And the graph traces every fact back to its paper.

Next steps: get the refcode mapping and close RQ3, rerun both models without the "omit when
unsure" line, fix the condition scoring, and add a second annotator.

Thank you. I'm happy to take questions.
