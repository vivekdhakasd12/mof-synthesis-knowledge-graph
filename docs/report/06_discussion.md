# 6. Discussion

I want to use this chapter to actually think through the results in Chapter 5, rather than
restate them with different wording. Three questions seem worth answering properly: what the
pre-registered prediction actually tells me, why the cheaper model beat the more expensive
one, and what the rule baseline's weak MOF-identification rate says about maintaining a
system like it. I will end by coming back to the gap I set out in Chapter 2 and being honest
about how much of it this project actually closes.

## 6.1 What the pre-registered prediction confirms, and what it does not

I recorded a prediction before running a single model: the margin over the rule baseline
should be largest on USES_PRECURSOR and USES_LINKER, and smallest on AT_CONDITION and
IN_SOLVENT. The reasoning was that naming the material scattered across a passage takes
something closer to reading comprehension, while matching a condition or a solvent is closer
to pattern spotting. The measured ordering matched that exactly (Section 5.1), and I think
it is fair to call that a real confirmation, not a pattern I noticed after the fact and then
described as expected.

I still want to be careful about what it establishes. It tells me *where* the gap between
rules and language models is largest, and the reasoning I used to predict that turned out to
point the right way. It does not tell me *why* in any mechanistic sense. I never looked at
what happens inside the model, only at what came out the other end, so a prediction holding
up is evidence the reasoning is *consistent* with the result, not proof that the reasoning is
the actual explanation.

Sitting with the numbers a bit longer, I think the result also sharpens something the DigiMOF
authors said rather than just testing it. They wrote that implicit synthesis routes, ones a
paper implies through solvent and temperature instead of naming outright, are "challenging to
extract using rule-based NLP" (Glasby et al., 2023), which is a claim about *inferring a
method*. What I found is a step earlier and, honestly, more basic: the rule baseline's
biggest problem is not inferring the method, it is knowing which MOF the passage is even
about in the first place (Section 6.3). I do not think these two findings contradict each
other. A system that cannot name the product of a synthesis has little chance of correctly
inferring its method from indirect cues either, since five of the eight relations in this
ontology, and probably DigiMOF's extraction logic too, hang off the MOF node. I tested the
prediction relation by relation, but the MOF-identification finding is, I think, a good part
of the reason the rule baseline's disadvantage shows up everywhere rather than only on the
fields that need inference.

## 6.2 Why the cheaper model outperformed the more expensive one

This is the finding I think matters most practically, and it is also the one where my first
explanation turned out to be wrong. gpt-4o-mini beat gpt-4o on three of the four prompting
strategies, at roughly a forty-seven-fold difference in cost. I want to record what I
originally proposed, why I tested it, and what the data actually says, because the second
answer is more useful than the first one would have been.

**What I first proposed.** My initial reading was that gpt-4o produces more elaborate output:
that it surfaces more candidate entities per passage, including plausible ones that were not
part of the specific synthesis being described, and that against a strict matcher this
verbosity converts into false positives rather than extra correct answers. It is a tidy story
and it fits the general intuition that a larger model says more.

**How I tested it.** The prediction that story makes is checkable without spending anything,
because every model's output is already saved in `data/processed/results_gold.jsonl`. If
gpt-4o were the verbose one, it should emit more triples per passage than gpt-4o-mini, and
its extra output should show up as false positives. Counting the triples each configuration
emitted over the 100 gold passages:

| Strategy | Emitted | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|---|
| gpt-4o-mini zero-shot | 189 | 47 | 142 | 91 | 0.249 | 0.341 |
| gpt-4o zero-shot | 129 | 33 | 96 | 105 | 0.256 | 0.239 |
| gpt-4o-mini few-shot | 231 | 46 | 185 | 92 | 0.199 | 0.333 |
| gpt-4o few-shot | 164 | 37 | 127 | 101 | 0.226 | 0.268 |
| gpt-4o-mini schema-guided | 197 | 61 | 136 | 77 | 0.310 | 0.442 |
| gpt-4o schema-guided | 159 | 39 | 120 | 99 | 0.245 | 0.283 |
| gpt-4o-mini chain-of-thought | 144 | 39 | 105 | 99 | 0.271 | 0.283 |
| gpt-4o chain-of-thought | 135 | 38 | 97 | 100 | 0.281 | 0.275 |

**The story is wrong, and it is wrong in the opposite direction.** gpt-4o emits *fewer*
triples than gpt-4o-mini in every one of the four strategies, by 32 percent on zero-shot,
29 on few-shot, 19 on schema-guided and 6 on chain-of-thought. It also produces fewer false
positives in absolute terms, which is the reverse of what
my explanation required. Precision is close to identical between the two models: gpt-4o is
marginally ahead on three strategies and clearly behind on the fourth, and no strategy shows
the precision collapse that a verbosity effect would produce.

**What the numbers actually show is a recall gap.** gpt-4o has fewer true positives and more
false negatives in every strategy. Its worst case is schema-guided, where it recovers 39 of
the 138 gold triples against gpt-4o-mini's 61. The larger model is the more conservative
reader: it commits to fewer facts per passage, and on this task the facts it declines to
extract are disproportionately ones the gold standard contains.

That reframes the practical lesson. The cost of caution is asymmetric here. A synthesis
paragraph is dense with recoverable facts, the gold standard is dense to match, and an
extractor that holds back pays in recall immediately while buying almost no precision in
return. On this task, and probably on extraction tasks generally, a model that reaches and is
sometimes wrong beats a model that abstains and is occasionally right.

One further pattern is worth noting without leaning on it. The two models are closest on
chain-of-thought, 39 true positives against 38, and that is the single strategy where gpt-4o
wins on F1. Chain-of-thought is also the strategy that most explicitly asks a model to work
through a passage step by step. It is consistent with the idea that gpt-4o's under-extraction
is a disposition that prompting can partly correct, but one strategy and a one-point
difference cannot establish that, and I am not claiming it.

**What this does not explain.** I now know what gpt-4o does differently, that it extracts
less, but not why it declines. Reading the individual passages where gpt-4o-mini found a
gold triple and gpt-4o did not would answer that, and it is the natural continuation of the
review this section began. I also want to be careful not to over-generalise from a single
run of each configuration on a 138-triple gold standard; Section 7.8 states that limitation
and it applies here.

What I would keep from this whole exercise is procedural rather than about models. The
verbosity explanation sounded right, matched a common intuition, and was consistent with the
F1 column I first looked at. It survived until I counted something it predicted. Chapter 8
lists this review as future work because that was true when I wrote it; the counting half is
now done, and it changed the answer.

## 6.3 What the 15 percent MOF-identification rate means for rule-based pipeline maintainers

The rule baseline names a MOF in only 121 of the 794 synthesis passages in the full corpus,
about 15 percent (Section 8.3; reproducible with
`python -m src.pipeline --extractors rule_based --no-resume`). Figure 8 shows where the other
673 passages go. 331 name the MOF somewhere else in the paper, usually at first mention
rather than in the synthesis paragraph itself, and 251 use a generic label like "compound 1"
that only resolves to an actual chemical identity through a table or a cross-reference the
passage itself does not contain. The remaining 91 are cases such as a name coined by the
authors that no fixed dictionary could have anticipated.

![Why the rule baseline cannot name the material](figures/fig6_baseline_failure_modes.png)

**Figure 8.** The rule baseline's dominant failure is not a missing dictionary entry.
Coreference across a paper and generic numbered designations together account for more than
four times as many passages as successful MOF identification.

Neither of the two big causes is a lexicon gap. You can always grow a vocabulary, and
DigiMOF's own parsers are already extensive, but no amount of vocabulary helps when the
information the parser needs simply is not in the passage it is looking at. If I were
maintaining or extending a rule-based pipeline over this kind of literature, I do not think
I would reach for a bigger dictionary first. I would reach for coreference resolution across
a paper, so a synthesis paragraph can be linked back to the name the compound was given when
it was first introduced, and for table parsing, since a numbered designation is very often
defined in a table that the running text never repeats. Both are engineering problems a
rule-based system can solve without becoming a language model, and honestly both look more
tractable to me than the implicit-route inference problem Glasby et al. (2023) describe,
because neither requires inference. They just require linking two places in the same document
that already state the fact plainly.

I read this as reframing rather than overturning the claim I set out to test in Chapter 2.
Implicit method inference is a real difficulty for rule-based extraction, and the smaller LLM
margins I measured on IN_SOLVENT and AT_CONDITION are consistent with rules already handling
the easier, locally-patterned end of that spectrum reasonably well. But for MOF synthesis
specifically, the bigger and more basic obstacle sits earlier in the pipeline, at working out
which compound is even being discussed, and that is why the language model's advantage over
rules in this study turned out larger on those identity-dependent fields than the original
framing led me to expect.

## 6.4 What this means for building such a pipeline today

Two choices in this project were made for cost reasons, not as a deliberate research design,
and both turned out to also be the ones the results actually support. Schema-guided
prompting, the cheapest template I tested at 652 tokens against 4,054 for few-shot, was also
the best-performing strategy on the strongest model. And the free-tier open-weight model, at
zero marginal cost, reached about two thirds of the best commercial F1. Put together with the
cheaper-model result in Section 6.2, the shape of this whole evaluation is that the most
expensive choices I tested, few-shot prompting and the larger commercial model, were beaten by
cheaper alternatives on every axis I measured. I do not think that means an expensive
configuration is never worth it. It means that for this task, on this gold standard, it was
not, and anyone building something similar on a tight budget now has an actual measurement to
start from instead of an assumption.

The absolute numbers are still modest, and I do not want to end this chapter sounding more
confident than they warrant. Chapter 7 sets out why 0.364 micro-F1, or roughly 0.53 once the
field whose scores measure annotation granularity rather than extraction quality is excluded,
is a lower bound rather than a ceiling, and what it would actually take to close the remaining
gap to the target I set in the exposé.

## 6.5 What the reference databases could and could not tell me

I set out in Chapter 2 to validate extractions against DigiMOF and SynMOF, and that is the
research question this project does not answer. It is worth being precise about why, because
the reason is not that the analysis failed but that it was posed against the wrong key.

The two databases share 509 MOFs by CSD refcode, and on those they agree about the metal
98.9 percent of the time. I find that number genuinely useful, and not for the reason I
expected. It says two independently built text-mining efforts, one rule-based over full text
and one manually curated, converge almost completely on the metal when they describe the
same material. That is a reassuring result about the reference databases themselves, and it
sets a rough ceiling on what agreement between any two extraction systems ought to look like
on a field this well defined.

The obstacle is the key. DigiMOF and SynMOF are indexed by CSD refcode, and my gold standard
is indexed by whatever name the paper used. Getting from "MOF-303" to a refcode needs a
mapping resource I do not have, so I cannot compute the overlap, and I want to say plainly
that undetermined is not the same as zero. An earlier draft of this chapter asserted that the
overlap was zero and that the corpus contained no classic MOFs. Both claims were wrong. The
gold standard contains ZIF-8, MIL-101(Cr), UiO-66-NH₂, NU-1000 and Cu₃(BTC)₂, and that last
one is HKUST-1, whose composition sits in the intersection as refcode REYMOZ. I could only
establish a composition-level match rather than a confirmed identity, since the same metal
and linker can build different frameworks, but it is enough to rule out the disjointness I
had claimed.

What I take from this is a lesson about evaluation design rather than about extraction. I
chose the corpus for one property, open access with structured full text, and chose the
reference databases for another, coverage of MOF synthesis. Nothing forced those two choices
to share an identifier, and I did not check that they did until after the corpus was built
and annotated. The 31 percent linker coverage inside the intersection points the same way:
even had the join worked, the field I most wanted to validate is the field DigiMOF is
thinnest on. An agreement study needs the join key and the field coverage settled before the
corpus is collected, not after.

So RQ3 stays open, and Chapter 8 records what closing it would take. What I can offer in its
place is narrower but real: the reference databases are highly self-consistent on the
material they share, my corpus is not disjoint from them, and the specific reason a
per-record comparison is out of reach is an identifier mismatch rather than anything about
how well the models read a paper.
