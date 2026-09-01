# 6. Discussion

This chapter interprets the results in Chapter 5 rather than restating them. It takes up
three questions in turn: what the pre-registered prediction confirms and what it leaves
unresolved, why the cheaper commercial model beat the more expensive one, and what the
rule-based baseline's 15 percent MOF-identification rate implies for anyone maintaining a
rule-based extraction pipeline. It then returns to the gap identified in Chapter 2 and states
plainly how much of it this work closes.

## 6.1 What the pre-registered prediction confirms, and what it does not

The prediction recorded before any model was run, that the margin over the rule baseline
would be largest on USES_PRECURSOR and USES_LINKER and smallest on AT_CONDITION and
IN_SOLVENT, matched the measured ordering exactly (Section 5.1). That is a genuine
confirmation, not a pattern noticed after the fact, and it is worth being precise about what
it does and does not establish.

It establishes that the reasoning behind the prediction, that identifying which material is
being made requires synthesising information scattered across a passage while matching a
condition or solvent is closer to local pattern recognition, correctly predicts *where* the
gap between the two approaches is largest. It does not establish *why* in a mechanistic
sense: the study did not instrument the models' internal reasoning, only their output. A
result consistent with a mechanism is not proof of that mechanism, and the correct claim is
the narrower one already made in Chapter 5, that the ordering matches the prediction, not
that the underlying cognitive story is confirmed.

The result also sharpens the claim from Glasby et al. (2023) that implicit synthesis routes
are "challenging to extract using rule-based NLP" (Section 2.1). That claim was about
inferring a method from indirect cues. This work measures something adjacent and, in a
sense, more basic: the rule-based baseline's largest deficit is not in inferring an implicit
method, it is in identifying which MOF a passage is even about (Section 6.3). The two
findings are compatible rather than contradictory. A rule-based system that cannot name the
product of a synthesis is unlikely to correctly infer its method from indirect cues either,
since the ontology in this study, and plausibly DigiMOF's underlying extraction logic, routes
method-dependent relations through the MOF node. The pre-registered prediction was tested at
the level of individual relation types; the MOF-identification finding explains, at least in
part, why the rule baseline's disadvantage is not confined to inference-heavy relations but
appears across the record.

## 6.2 Why the cheaper model outperformed the more expensive one

The central practical finding of this study, that gpt-4o-mini beat gpt-4o on three of four
prompting strategies at a 47-fold cost difference, is also the one this evaluation is least
equipped to fully explain. Two properties of the measurement are relevant before any
mechanism is proposed.

First, the metric is F1 against a fixed gold standard, which penalises both missed triples
and incorrect ones equally. A model that extracts more triples per passage does not
necessarily gain recall if many of the additional triples are wrong, and it will lose
precision doing so. Second, the per-field table in Section 5.3 shows gpt-4o-mini's advantage
concentrated in USES_PRECURSOR and USES_LINKER, the two fields with the most gold support
(39 and 30 triples respectively) and the two on which the rule baseline already showed the
largest LLM margin. That is where the two commercial models had the most room to be
distinguished by the data available.

The most plausible mechanism, consistent with but not established by these numbers, is that
gpt-4o's outputs are more elaborate: it reports more candidate entities per passage,
including plausible but incorrect ones, such as reagents mentioned in passing that were not
part of the specific synthesis being described. Against a strict matching regime and a
138-triple gold standard, that verbosity converts into false positives rather than
additional true positives. This is consistent with the precision figures in Section 5.2,
where gpt-4o's precision is not systematically higher than gpt-4o-mini's despite the larger
model's greater capability on other benchmarks, but consistency is not confirmation. Chapter
8 lists a manual error review, reading the actual false positives from both models
side by side, as the concrete next step to test this mechanism directly. Until that review is
done, the correct claim is the one already stated in Chapter 5: the cheaper model wins on
this evaluation, at this cost, and the reason is a hypothesis rather than a finding.

A second, more mundane possibility deserves equal weight rather than being discounted in
favour of the more interesting story: gpt-4o-mini may simply be better tuned to the kind of
concise, schema-constrained extraction task this study poses, independent of any verbosity
mechanism. Both explanations point to the same practical conclusion. Model capability on
general benchmarks did not predict performance on this task, and a study designed to compare
vendors' flagship models against each other would have reached the wrong conclusion by
assumption rather than measurement had it not included the cheaper model at all.

## 6.3 What the 15 percent MOF-identification rate means for rule-based pipeline maintainers

The rule-based baseline identifies a MOF in only 121 of the 794 synthesis passages in the
full corpus, 15 percent (Section 8.3; reproducible with
`python -m src.pipeline --extractors rule_based --no-resume`). Figure 6 breaks down the
remaining 673 passages. 331 name the MOF elsewhere in the paper, most often at first mention
rather than in the synthesis section itself, and 251 use a generic designation such as
"compound 1" that only resolves to a chemical identity via a table or a cross-reference the
passage does not contain. The remaining 91 are cases such as a novel, paper-coined name no
fixed dictionary could anticipate.

![Why the rule baseline cannot name the material](figures/fig6_baseline_failure_modes.png)

**Figure 6.** The rule baseline's dominant failure mode is not a missing dictionary entry.
Coreference across a paper and generic numbered designations together account for more than
four times as many passages as successful MOF identification.

Neither cause is a lexicon gap. A rule-based system's vocabulary can always be extended, and
DigiMOF's own parsers are already extensive, but no vocabulary addition helps when the
information needed is not in the passage being parsed. This has a direct implication for
anyone maintaining or extending a rule-based extraction pipeline over MOF literature: the
highest-leverage improvement is very unlikely to be a bigger dictionary. It is more likely to
be coreference resolution across a paper, linking a synthesis paragraph back to the name
assigned when the compound was first introduced, and table parsing, since a numbered
designation is frequently defined in a table the running text never repeats. Both of those
are engineering problems a rule-based system can in principle solve without becoming a
language model, and both are more tractable than the implicit-route inference problem
Glasby et al. (2023) describe, because they do not require inference, only linking two
places in the same document that already state the fact plainly.

This reframes, rather than overturns, the state-of-the-art claim this work set out to test.
Implicit method inference is a real difficulty for rule-based extraction, and the smaller
LLM margins on IN_SOLVENT and AT_CONDITION are consistent with rules already handling the
easier, locally-patterned end of that spectrum reasonably well. But for MOF synthesis
extraction specifically, the larger and more basic obstacle sits earlier in the pipeline,
at subject identification, and a language model's advantage over rules in this study is
correspondingly larger on the fields that depend on knowing which compound is being
discussed than the original framing anticipated.

## 6.4 What this means for building such a pipeline today

Two decisions in this study, taken for cost reasons rather than as a research design choice,
turned out to also be the ones the results best support. Schema-guided prompting, the
cheapest prompt template tested at 652 tokens against 4,054 for few-shot, was also the best
performing strategy on the strongest model. And the free-tier open-weight model, at zero
marginal cost, reached roughly two thirds of the best commercial F1. Together with the
cheaper-model result in Section 6.2, the practical shape of this evaluation is that the most
expensive choices tested, few-shot prompting and the larger commercial model, were dominated
by cheaper alternatives on every axis measured. That is not a claim that expensive
configurations are never justified; it is a claim that, for this task, on this gold standard,
they were not, and a team building a similar pipeline on a constrained budget has direct
evidence rather than an assumption to start from.

The absolute numbers remain modest. Chapter 7 sets out why 0.364 micro-F1, or approximately
0.53 excluding the field whose scores measure annotation granularity rather than extraction
quality, is a lower bound rather than a ceiling, and what would need to change to close the
remaining gap to the exposé's original target.
