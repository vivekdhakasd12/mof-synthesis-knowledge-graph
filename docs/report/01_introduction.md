# 1. Introduction

## 1.1 Motivation

Metal-organic frameworks (MOFs) are porous crystalline materials assembled from metal nodes
and organic linkers. Over 100,000 synthesised structures are recorded in the Cambridge
Structural Database, and their applications span CO2 capture, gas storage and separation,
catalysis, sensing and drug delivery. The knowledge of how any given MOF is actually made,
which metal precursor and which organic linker, in which solvent, by which method, at which
temperature and for how long, remains locked in the prose of tens of thousands of
publications. Synthesis planning therefore still depends heavily on expert intuition and
trial and error.

Large language models (LLMs) and knowledge graphs (KGs) together offer a route from that
prose to a structured, queryable resource (Pan et al., 2024). Recent work demonstrates the
approach at scale: Bai et al. (2025) built a knowledge graph of 2.53 million nodes for
framework materials from more than 100,000 articles, and coupled it to a question-answering
system. What that literature does not establish is reliability. How accurate are
LLM-extracted synthesis records field by field? How do they compare with the text-mined
databases the field already relies on, and with the rule-based systems that produced them?
And what does an open-weight model deliver relative to a commercial API, at what cost?

## 1.2 The gap this work addresses

Three observations define the gap.

First, the existing LLM work on MOF text mining validates against small in-house test sets
and uses commercial GPT models almost exclusively (Zheng et al., 2023; Shi et al., 2024;
Lin et al., 2025). No published study reports per-field accuracy against both expert
annotation and the established text-mined databases.

Second, the authors of DigiMOF, the largest openly available MOF synthesis database, state
the problem directly. Writing about routes that papers imply through solvent and temperature
rather than naming outright, they observe that such implicit routes "could be easily deduced
by a reader but are challenging to extract using rule-based NLP" (Glasby et al., 2023). That
is a precise, testable claim about where a language model should help and where it should
not.

Third, the cost dimension of the open-weight question is unexamined, despite being the
factor that decides whether a pipeline of this kind is reproducible by anyone without an
institutional budget.

## 1.3 Research questions

**Main question.** How accurately and reliably can large language models extract complete
MOF synthesis records, measured against expert annotation and domain-specific baselines?

**RQ1.** How does per-field extraction accuracy compare between LLMs and a rule-based
baseline built from the same domain vocabulary?

**RQ2.** Which prompting strategy, among zero-shot, few-shot, schema-guided and
chain-of-thought, is most reliable for each field of a synthesis record?

**RQ3.** Where and why do LLM extractions disagree with the DigiMOF and SynMOF reference
databases?

**RQ4.** How do open-weight models compare with commercial APIs on per-field accuracy, cost
and latency?

**RQ5.** Can the resulting knowledge graph answer aggregation queries across hundreds of
papers?

## 1.4 Contributions

1. A reproducible, provenance-complete pipeline from open-access literature to a Neo4j
   knowledge graph, in which every entity carries a traceable link to the sentence and paper
   it came from, verified by query rather than asserted.
2. A hand-annotated gold standard of 100 MOF synthesis passages containing 138 triples,
   drawn by a seeded stratified sample that includes an unflagged control stratum, so the
   pre-filter's own error rate is measurable rather than assumed.
3. A per-field comparison of ten extractor configurations spanning a rule-based baseline,
   two commercial models and one open-weight model across four prompting strategies.
4. A pre-registered prediction about where language models should beat rules, recorded
   before any model was run and confirmed by the measurements.
5. An honest account of what the evaluation cannot show, including a field whose scores
   reflect annotation granularity rather than extraction quality, and two configurations
   removed rather than reported from partial data.

## 1.5 Structure of this report

Chapter 2 reviews the state of the art. Chapter 3 sets out the methodology, including the
ontology, corpus construction, annotation protocol and evaluation design. Chapter 4
describes the implementation. Chapter 5 presents the results. Chapter 6 discusses them.
Chapter 7 states the limitations and threats to validity. Chapter 8 concludes.
