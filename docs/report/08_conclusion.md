# 8. Conclusion and outlook

## 8.1 What was built

An end-to-end, reproducible pipeline that collects open-access MOF literature, segments it
into synthesis passages, extracts structured synthesis records with either a rule-based
system or a language model under four prompting strategies, evaluates those extractions
per field against a hand-annotated gold standard, and loads them into a Neo4j knowledge graph
in which every entity is traceable to the sentence that produced it. Provenance completeness
is verified by query rather than asserted.

## 8.2 What was found

**Language models beat the rule-based baseline on every configuration tested**, and they beat
it by the largest margin exactly where a pre-registered prediction said they would: on
identifying which material is being made and from what. The margin is +0.42 F1 on metal
precursors and +0.31 on organic linkers, falling to +0.25 on solvents and +0.17 on
conditions, which are the fields local surface patterns already handle.

**The cheaper commercial model outperformed the more expensive one** on three of four
prompting strategies, at a 47-fold cost difference in favour of the cheaper model. The
mechanism is a recall gap rather than a precision one. gpt-4o emits fewer triples than
gpt-4o-mini in every strategy, by 6 to 32 percent depending on the prompt, recovers fewer of
the gold triples, and
gains almost nothing in precision for the caution. The larger model is the more conservative
reader, and on a task whose passages are dense with recoverable facts, holding back costs more
than reaching does. An earlier reading of this result proposed the opposite, that the larger
model over-extracted; Section 6.2 records that explanation and the count that refuted it.

**Schema-guided prompting was the best single choice observed**, though not universally, and
few-shot prompting was the weakest strategy on both commercial models despite the most
expensive prompt by a factor of six.

**The open-weight model reached approximately two thirds of the best commercial F1 at zero
marginal cost.** For a pipeline that must be reproducible without an institutional budget,
that is a meaningful result rather than a shortfall.

**Absolute accuracy is well below the target stated in the exposé.** The best configuration
reaches 0.364 micro-F1 against a target of 0.80. Chapter 7 sets out how much of that gap is
attributable to surface-form matching and annotation granularity rather than extraction
quality, and reports that the best configuration reaches approximately 0.53 when the field
whose scores measure granularity is excluded.

## 8.3 What this says about the field

The DigiMOF authors observed that synthesis routes implied rather than named are hard for
rule-based extraction. This work provides a quantified version of that observation from the
other direction: the rule-based baseline identified a MOF in only 15 percent of synthesis
passages, and because the ontology roots five relations at the MOF node, that single failure
suppresses most of what a rule-based system could otherwise extract. Of the passages where no
MOF was identified, 331 named it elsewhere in the same paper and 251 used a generic
designation such as "compound 1". Those are not lexicon gaps that a larger dictionary would
close.

## 8.4 Future work

1. **Complete RQ3.** The blocker is an identifier mismatch, not a missing analysis: the
   reference databases are keyed by CSD refcode and this corpus by DOI and MOF name.
   Obtain a name-or-DOI-to-refcode mapping, then run the per-record comparison that
   Section 5.7 sets up but cannot execute. Note that DigiMOF carries a linker for only 31
   percent of the shared MOFs, so linker agreement will rest on a small subset even then.
2. **Complete the open-weight strategy sweep**, which requires either a paid serving tier or
   several days of free-tier quota.
3. **Repair the condition evaluation**, either by changing the annotation convention to one
   condition per triple or by implementing set-valued comparison for that field.
4. **Add chemical identifier resolution** so that surface-form variation stops being scored
   as extraction error.
5. **Enlarge the gold standard and add a second annotator**, which would both narrow the
   confidence intervals and allow an inter-annotator agreement statistic.
6. **Finish the error review of the cheap-model result.** Section 6.2 establishes *what*
   gpt-4o does differently, that it extracts less, by counting emitted triples. What remains
   is *why* it declines: reading the individual passages where gpt-4o-mini recovered a gold
   triple and gpt-4o did not.
