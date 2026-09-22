# Defence Q&A preparation

Twenty-eight questions from four examiner perspectives, generated independently and then checked
against the report, the code and the data. Every number below was verified against
`data/processed/evaluation.json`, `results_gold.jsonl`, `agreement_analysis.json`, the git
history, or the source file named.

Most answers are marked **weak spot**. That is intended: the panel was told to find where the
report is thinnest, because those are the questions that decide a defence. A weak spot does not
mean the work is weak. It means the honest answer is "that was not measured", and you need to be
able to say that calmly and then say what you would do about it.

The single most useful habit: **agree with the true part of the question first, then give the
evidence.** "You are right that..." followed by a number is far stronger than defending a claim
the data does not support.

---

## Read this first: what the submitted report gets wrong

Checking the panel's questions turned up seven places where the report says more than the
evidence supports. The slides and the speaker script have been corrected. **The report has not
been touched**, because it is probably already submitted and changing a submitted document
silently is worse than any of these errors. You should decide whether to send Prof. Jalali a
short erratum; see the end of this section.

### 1. The pre-registered prediction is misquoted

The prediction committed on 23 August (`docs/baseline_findings.md`, lines 77 to 79, commit
`ad0fcc1`) reads:

> the LLM margin should be largest on USES_PRECURSOR, USES_LINKER **and SYNTHESIZED_BY**, and
> smallest on AT_CONDITION and IN_SOLVENT

Section 5.1 of the report, and the original slide, put it in quotation marks **without
SYNTHESIZED_BY**, then say the ordering "matches exactly". SYNTHESIZED_BY has one gold triple, so
it cannot be tested, and its measured margin (+0.07) is actually the smallest of all.

The pre-registration itself is genuine: it was committed eight days before the first model
results (`de7f0a5`, 31 August). The problem is only the quotation.

**If asked:** "You are right, and I should have shown the original wording. The committed
prediction also named SYNTHESIZED_BY. That relation has one gold triple, so it cannot be tested,
and I dropped it from the quote without saying so. That was my mistake. On the four fields that
can be tested, the ordering holds: precursor and linker lead, solvent and condition trail."

### 2. The cost figures are estimates on unverified prices

- **"Total API spend of 3.06 USD" is an estimate**, computed as token counts multiplied by a
  price table (`estimate_cost_usd` in `src/extraction/llm_extractor.py`). It is not an invoice.
- **The OpenAI rows in that table were never verified.** Line 103 of the same file:
  *"OpenAI. NOT yet re-verified in-project; check openai.com/api/pricing before the run."* Every
  gpt-4o and gpt-4o-mini cost in the report, including 0.028, 1.289, 3.06 and 47 times, rests
  on those prices.
- **"Six times more per call" (Section 5.4) is wrong.** 6.2 is the ratio of template lengths,
  4,054 tokens against 652. The measured cost ratio of few-shot to schema-guided is **3.0 times**
  on gpt-4o-mini and **2.9 times** on gpt-4o.
- **47 times mixes model and strategy.** It compares gpt-4o few-shot with gpt-4o-mini
  schema-guided. On the same prompt, gpt-4o costs **15 to 19 times** more.

**Before the defence:** log in to platform.openai.com, open Usage, and look at the spend for 31
August to 1 September. If it is close to 3 USD, the estimate is confirmed and you can say so.
That turns a weak spot into a strong answer in five minutes.

### 3. "Two thirds of the best commercial F1" needs "on zero-shot"

The open-weight model's 0.191 is two thirds of gpt-4o-mini's **zero-shot** score, 0.287. Against
the best configuration overall, 0.364, it is closer to half. Sections 6.4 and 8.2 drop the
qualifier; Section 5.4 has it only by context. The slide now says "on the like-for-like
zero-shot comparison".

### 4. "Three of four strategies" includes two ties

| Strategy | gpt-4o-mini | gpt-4o | Gap | Cost ratio |
|---|---|---|---|---|
| zero-shot | 0.287 | 0.247 | 0.040 | 14.7x |
| few-shot | 0.249 | 0.245 | 0.004 | 15.5x |
| schema-guided | 0.364 | 0.263 | 0.102 | 16.2x |
| chain-of-thought | 0.277 | 0.278 | 0.002 | 18.7x |

Section 7.4 says gaps of about 0.015 cannot be resolved. By that rule, gpt-4o-mini wins **two**
strategies clearly and the other two are ties. The strong version of the claim is: on the same
prompt, gpt-4o costs 15 to 19 times more and never wins by a resolvable margin.

### 5. The abstention instruction is a confound in Section 6.2

Every one of the four prompt templates tells the model to leave facts out when unsure.
Schema-guided says *"If unsure, omit."* The other three say *"Omitting a relation is always
better than inventing one."* So gpt-4o's lower recall might be caution, or it might simply be
better obedience to your own instruction. The design cannot separate the two. Section 6.2 says
it does not know *why* gpt-4o extracts less, which is correct, but its closing lesson ("a model
that reaches beats a model that abstains") reads as a claim about models when it may be a claim
about the prompts.

### 6. Knowledge graph provenance is weaker at the edge than the report says

In `src/kg/loader.py`, lines 189 to 190, a relationship is `MERGE`d on subject, relation and
object, then `SET r.evidence = ...` **overwrites**. When two papers state the same MOF-linker
fact, the graph keeps one edge carrying only the **last** paper's evidence sentence. Entity-level
provenance through `MENTIONED_IN` is intact, and that is what the zero-violations query checks.
Also, "3,728 merge operations" is simply two merge calls per triple over 1,864 triples; it says
nothing about how well entities were resolved.

### 7. The pre-filter's miss rate is never reported

Sections 1.4 and 3.4 say the ten control passages make the filter's miss rate "measurable". The
report never gives the measurement. From the data: **0 of the 10 controls** contained a synthesis
record, so no miss was observed, and **32 of the 90 flagged passages** did, a precision of
**36 percent**. Ten controls is too few to bound recall usefully.

### Should you send an erratum?

Item 1 is the only one that is a genuine misstatement rather than a missing qualifier, and it
concerns the one piece of evidence the report calls a "confirmation". The repository is public,
so an examiner can find the original wording in two minutes. A two-line email to Prof. Jalali
before the defence ("I noticed that the quoted prediction in 5.1 omits one field from the
committed version; the testable part is unchanged") costs you nothing and removes the risk of it
being found for you. Your call.

---

## Rehearse these eight first

If you prepare nothing else, prepare these. They are the most likely, and the most damaging if
you are caught without an answer.

**1. "Your pre-registered quote leaves out SYNTHESIZED_BY. Why?"**
See item 1 above. Admit it first, then give the four testable margins: +0.42, +0.31, +0.25,
+0.17.

**2. "Your prompts tell the model to omit when unsure. Isn't that why gpt-4o has lower recall?"**
"That is a fair alternative, and I did not test it. What I measured is that gpt-4o extracts
less: fewer triples in all four strategies, and 39 of 138 gold triples on schema-guided against
61. Whether that is caution or better instruction-following, my design cannot tell apart. The
clean test is to remove that line and rerun both models."

**3. "Is 3.06 USD an invoice? And isn't 47 times comparing different strategies?"**
"It is an estimate from recorded token counts and list prices, and the OpenAI prices in the code
were not re-verified during the project. You are right that 47 times mixes model and strategy.
On the same prompt, gpt-4o costs 15 to 19 times more, and never wins by a margin my gold standard
can resolve." (Better still, if you have checked the OpenAI dashboard: "I checked the invoice,
and it was X.")

**4. "0.364 against a target of 0.80. Is this system useful at all?"**
"For one paper, reading it is better. The system makes sense at scale with a person checking,
and every triple carries its evidence sentence so that checking is fast. 0.364 is also a lower
bound: strict text matching scores correct extractions as wrong. Excluding the condition field,
whose scores measure my annotation style, the best configuration averages about 0.53."

**5. "Why was the join key for DigiMOF and SynMOF not checked before you annotated?"**
"It was an evaluation design mistake, and I say so in Section 6.5. I chose the corpus for open
full text and the references for coverage, and did not check they shared an identifier. The
overlap is undetermined, not zero. What I could measure, 98.9 percent metal agreement across 509
MOFs, is about the two databases, not about my extractions."

**6. "You built the knowledge graph from your worst extractor. Why?"**
"Because the language models were only run on the 100 gold passages, and the rule baseline was
the only extractor run over all 794. So RQ5 shows the loading and provenance machinery works,
not that the graph content is reliable. Running the best configuration over all 794 passages
would cost about 22 US cents, and it is the obvious next step."

**7. "One annotator, 100 passages, one run each. Which of your differences are real?"**
"I did not compute confidence intervals or run a significance test. The claim I stand behind
most is that every language model beats the rule baseline: 0.191 at worst against 0.112. The
strategy comparisons are indicative, not established. A second annotator and repeated runs are
in my future work."

**8. "Why did you delete two open-weight runs?"**
"They hit a free-tier daily limit at 26 and 3 of 100 passages. A partial run is still scored
against all 138 gold triples, so it reports artificially low recall and makes a rate-limited
model look like a weak one. The deletion is stated in Section 5.6. The cost is that RQ4 rests on
zero-shot alone."

---

## Full question bank, by examiner

### Methodology examiner

**M1. The committed prediction also named SYNTHESIZED_BY. Why was it dropped, and how is
"matches exactly" justified when the prediction only split four fields into two groups?**
*Weak spot. Sources: 5.1, 5.3, 6.1, 7.1; `docs/baseline_findings.md` lines 77 to 79.*
You are right, and I should have shown the original wording. The committed prediction also named
SYNTHESIZED_BY, but that relation has a gold support of one, so it cannot be tested, and I
dropped it without saying so. The prediction was also only two groups, so the honest claim is
narrower: precursor and linker, at +0.42 and +0.31, beat solvent and condition, at +0.25 and
+0.17. And AT_CONDITION is one of those four, even though I say its scores measure annotation
granularity. So this is consistent with my reasoning, not strong evidence.

**M2. 68 of your 138 gold triples came from a broken tool, and you changed the scoring rule for
exactly those two relations. How do I know you did not choose the concession because it helped?**
*Weak spot. Sources: 3.6, 7.5; commits `4afd559`, `de7f0a5`.*
In the commit history, the concession was committed on 31 August at 19:12, and the first
experimental results were recorded that evening at 23:16. It is also stored on every evaluation
result, so any generated table states it. The ontology justifies it too: the method is only a
connector, and the solvent or condition is the actual claim. The cost is real: I cannot show
whether a model links a solvent to the right synthesis when a passage describes several.

**M3. You changed the normaliser after seeing failures. Why is that not tuning on the gold
standard? And why report only relaxed matching?**
*Weak spot. Sources: 3.6, 7.2, 7.3.*
I made the change after looking at the data, and I say so in Section 7.3. It lets a name like
dimethylformamide (DMF) match either half. It raised every extractor by 0.006 to 0.027,
including the rule baseline, and both sets of numbers are in the repository history. A lift
across every system is consistent with a genuine fix, but strictly the gold standard informed
the scorer. I did not report exact-mode numbers, and I should have, as a sensitivity check.

**M4. 100 passages, 32 with any synthesis record, one run each. Which differences are real?**
*Weak spot. Sources: 5.2, 5.4, 7.4, 7.8.*
I did not compute any confidence interval or significance test. The report says a gap of 0.015
cannot be resolved, and some of my claims rest on smaller gaps: mini beats gpt-4o on few-shot by
0.004. The claim I would defend most is that every language model beats the rule baseline, 0.191
at worst against 0.112. The strategy comparisons are indicative, not established.

**M5. One annotator, and AT_CONDITION depends on your conventions. Is it legitimate to drop it
after seeing it score badly and then quote 0.53?**
*Weak spot. Sources: 5.3, 7.1, 7.4.*
I cannot measure the gold standard's consistency with one annotator, and I state that. I found
the condition mismatch after seeing the scores. That is why the headline stays 0.364 over all
scored relations, condition included, and 0.53 is only a secondary figure with the exclusion
stated.

**M6. You deleted two runs. Why not score them on the passages they answered?**
*Weak spot. Sources: 5.6, 7.6.*
A partial run is scored against all 138 gold triples, which gives artificially low recall and
makes a rate-limited model look weak. The deletion is stated, not hidden. I did not try scoring
them on only the passages they answered, so that alternative was never tested. The cost is that
RQ4 rests on zero-shot alone.

**M7. The ten controls make the pre-filter's miss rate measurable. What is it?**
*Weak spot. Sources: 3.4; verified against `passages.jsonl`.*
The report does not give it, and it should. None of the ten controls contained a synthesis
record, so no miss was observed, but ten is too few to bound recall. Of the 90 flagged passages,
32 had a synthesis record, a precision of 36 percent. So every gold triple comes from a flagged
passage, and my recall figures are conditional on the filter.

### Language-model examiner

**L1. Three of four strategies, but two gaps are 0.004 and 0.002. By your own rule, how many
wins are real?**
*Weak spot. Sources: 5.4, 7.4, 7.8.*
By my own standard, two are clear and two are ties. Schema-guided, 0.364 against 0.263, and
zero-shot, 0.287 against 0.247, are clear. Few-shot and chain-of-thought are both well under the
0.015 I said the gold standard cannot resolve. What I stand behind are the counts: gpt-4o emits
fewer triples in all four strategies.

**L2. Your prompts say "if unsure, omit". Isn't gpt-4o's lower recall just obedience?**
*Weak spot. Sources: 3.5, 6.2; `configs/prompts/*.txt`.*
That is a fair alternative, and I did not test it. Every template tells the model to omit rather
than invent. A model that follows that more literally would extract less, which fits what I see.
Section 6.2 establishes that gpt-4o extracts less, and says plainly that I do not know why. The
clean test is to remove that instruction and rerun both models.

**L3. Where does 3.06 come from? And 47 times mixes model and strategy.**
*Weak spot. Sources: 5.4; `src/extraction/llm_extractor.py` line 103.*
It is computed from recorded token counts and a table of list prices, so it is an estimate, and
the OpenAI prices in that table were not re-verified during the project. Like for like, on the
same prompt, gpt-4o costs 15 to 19 times more: 16 times on schema-guided, 15 on zero-shot. The
cheaper model wins both, so the conclusion holds, but the headline ratio overstates the clean
comparison.

**L4. Shi et al. found that selected few-shot demonstrations help. Why believe few-shot is weak
rather than your examples being poor? And is "six times more per call" measured?**
*Weak spot. Sources: 2.3, 5.4; `configs/prompts/extraction_few_shot.txt`.*
I used one fixed set of three hand-constructed examples, one of them a passage with no
synthesis. There was no per-passage selection of the kind Shi et al. studied, so my result is
about this example set, not few-shot prompting in general. And the six times is the template
length ratio. The measured cost ratio is about three times: 1.289 against 0.446 USD on gpt-4o.
The narrower claim is that my few-shot prompt cost three times more and bought nothing
measurable.

**L5. Temperature 0 is not deterministic on hosted APIs. Is the study reproducible by replaying
the cache, or by calling the models again?**
*Weak spot. Sources: 4.5, 7.8.*
By replay. The cache key covers provider, model, template and version, strategy, passage,
temperature and maximum tokens, so rerunning the analysis replays the same responses at no cost.
That makes the analysis reproducible, not the model outputs. I did not measure run-to-run
variation.

**L6. Qwen instead of Llama-3, one strategy, free tier. Two thirds of which number? And did you
measure that the latency is the serving tier?**
*Weak spot. Sources: 5.4, 7.6.*
Two thirds of the best commercial zero-shot score, 0.191 against 0.287. Against the overall best,
0.364, it is closer to half, and I should have said so. The latency explanation is my
interpretation, not a measurement; I never ran the same model on another host. Llama-3 was
impractical on 8 GB of RAM locally, and the hosted provider had retired its Llama models.

**L7. Both models are one vendor and already superseded. Would the finding hold for newer
models?**
*Weak spot. Sources: 4.2, 4.5, 7.8.*
I cannot claim it generalises. What the pipeline does is make the check cheap: every extractor
returns the same triple shape, the model is part of the cache key, and a new model is scored
against the same gold standard on identical terms. Empty completions from a reasoning model that
runs out of tokens are recorded as errors, so a failing model cannot look like a careful one.

### Chemistry examiner

**C1. Your graph comes from the rule baseline, and SYNTHESIZED_BY has one gold triple. How can
you compare method counts with DigiMOF?**
*Weak spot. Sources: 5.5, 5.3.*
You are right. The graph shows the pipeline works, not that the chemistry is accurate. Some
method labels are routes the baseline inferred at low confidence, and with one gold triple I
cannot claim the method counts are correct. That is why the ordering difference with DigiMOF is
recorded as an open question, not a finding.

**C2. A condition like "100 °C for 1 h, then another hour" is a sequence of steps. Isn't
AT_CONDITION an ontology problem?**
*Weak spot. Sources: 7.1, 3.1.*
Partly, yes. The mismatch I measured is annotation granularity, but you are right that neither
form captures step order, because every condition attaches to one method node. So the study
cannot tell a reaction temperature from an activation temperature. A proper fix needs step-level
structure in the ontology, and the report does not propose that.

**C3. Could a chemist reproduce a synthesis from your records?**
*Weak spot. Sources: 3.1, 3.4; `configs/ontology.json`.*
No, not as they stand. The ontology has amount fields, but I only scored relation triples, so
amounts and ratios were never measured. Modulators have no entity type, and activation is not a
separate stage. These records are an index of what was used, linked to the evidence sentence,
not a recipe.

**C4. Your normaliser merges ZrOCl₂ octahydrate with the anhydrous salt. Why trust 0.364 as a
lower bound?**
*Weak spot. Sources: 3.6, 7.2, 7.3.*
Dropping hydrates was a deliberate matching choice, and it means I cannot say whether a model got
the hydration state right. So the lower-bound argument only covers surface-form misses like
[emim]Br against its full name. Hydrate merging could err the other way, and I did not measure
how often. A PubChem-style identifier service is the proper fix.

**C5. How did you classify the 91 remaining passages? And what was the language models' own MOF
identification rate?**
*Weak spot. Sources: 6.3; `docs/baseline_findings.md`.*
The 121, 331 and 251 were counted; 91 is what remains of 794, not a classified category.
My working note also says 638 passages lacked a MOF, which does not match 673, and I should have
reconciled that. I did not measure a MOF identification rate for the language models. My
evidence that they identify the material better is indirect: the larger margins on precursor
and linker.

**C6. Would a chemist be better off reading the paper?**
*Weak spot. Sources: 5.3, 7.4, 7.5.*
For one paper, yes. The system makes sense at scale with a person checking. Excluding
conditions, the best configuration averages about 0.53, so roughly half the gold facts are found
and roughly half of what is emitted is right. Every triple carries its evidence sentence so it
can be checked. I cannot show a solvent is attached to the right synthesis when a passage
describes several.

**C7. CSD refcodes are the standard key. Why did you only find out after annotating? And isn't
98.9 percent about their data, not yours?**
*Weak spot. Sources: 5.7, 6.5, 7.7.*
Yes, that was a design mistake, and I say so in the discussion. The 98.9 percent is only about
the reference databases themselves: 468 of 473 comparable records across 509 shared MOFs. The
overlap with my gold standard is undetermined, not zero; HKUST-1 matches refcode REYMOZ at
composition level, which does not confirm it is the same material. And DigiMOF has a linker for
only 31 percent of those MOFs.

### Supervisor (graph machine learning on MOFs)

**G1. Why load the worst extractor into the graph, and how accurate is the graph?**
*Weak spot. Sources: 5.2, 5.5.*
The language models were only run on the 100 gold passages; the rule baseline was the only one
run over all 794. The report does not justify that, and it should. I did not measure the graph's
accuracy, so RQ5 shows the machinery works, not that the content is reliable.

**G2. Two papers say the same MOF uses the same linker. How many edges, and whose evidence
survives?**
*Weak spot. Sources: 4.6; `src/kg/loader.py` lines 189 to 190.*
One edge. The relationship is merged on subject, relation and object, and the evidence is then
overwritten, so only the last paper's sentence survives on that edge. The MENTIONED_IN edges
still link each entity to both papers, which is what the provenance query checks. The fix is to
include the paper in the relationship key, or to store evidence as a list.

**G3. How do you know the 3,728 merges into 485 nodes are correct?**
*Weak spot. Sources: 3.6, 4.6, 7.2.*
The 3,728 is two merge calls per triple over 1,864 triples, not a count of resolved synonyms. I
did not measure merge quality. The key is global, not per paper, so a generic label used in two
papers would become one node.

**G4. Your RQ5 evidence is a GROUP BY. What does the graph give that a table would not?**
*Weak spot. Sources: 3.1, 4.6, 5.5.*
Honestly, the query I report could run on a flat table. The graph adds queryable provenance and
shared precursor and linker nodes across papers, which multi-hop questions need. But the method
node is keyed only by its name, so there is one global "solvothermal" node, and the graph cannot
say which solvent went with which MOF's synthesis. I did not demonstrate a multi-hop query.

**G5. Is the solvothermal against hydrothermal ordering a finding at all?**
*Weak spot. Sources: 5.5, 6.3.*
I record it as an open question, and I think that is the right strength. It could reflect corpus
composition, extraction error, or how routes are inferred, and I cannot separate those.

**G6. Why was the join key not checked before annotation?**
*Weak spot. Sources: 5.7, 6.5.*
Same answer as C7: a design mistake, stated in 6.5. The lesson is that an agreement study needs
the join key and field coverage settled before the corpus is collected.

**G7. What is the next step, and how would this connect to MOFGalaxyNet?**
*Sources: 8.4.*
First, rebuild the graph from the best language-model configuration over all 794 passages;
it would cost about 22 US cents. Second, obtain a name-to-refcode mapping and close RQ3. With
identifiers on the MOF nodes, synthesis records could sit alongside a similarity network like
MOFGalaxyNet, and one could ask whether structurally similar frameworks share synthesis routes.
That last part is my proposal, not something I tested.
