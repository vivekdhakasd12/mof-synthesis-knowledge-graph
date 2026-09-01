# 2. State of the Art

Extracting synthesis knowledge from chemical literature has passed through three phases:
rule-based systems built on hand-written grammars, transformer models pre-trained on domain
text, and most recently large language models prompted rather than trained. This chapter
follows that progression, then states precisely what remains unestablished, because the gap
this work addresses is narrower than "language models have not been tried".

## 2.1 Rule-based extraction and the databases it produced

ChemDataExtractor (Swain & Cole, 2016) established the template for automated chemical
information extraction: a pipeline of tokenisation, chemical named-entity recognition and
grammar-driven parsers producing structured records. Its strength is precision and
auditability. A parser either matches or it does not, and the reason is inspectable.

That toolkit produced the two reference databases this work validates against.
**DigiMOF** (Glasby et al., 2023) adapted ChemDataExtractor with MOF-specific parsers and
applied it to 43,281 articles, yielding 15,501 MOFs and 52,680 synthesis-property records
covering synthesis method, solvent, organic linker, metal precursor and topology.
**SynMOF** (Luo et al., 2022) mined synthesis conditions for 983 MOFs, including metal
source, linker, temperature, time, solvent and additives, and used them to train synthesis
prediction models.

The same approach has been applied beyond MOFs. Kim et al. (2017) mined oxide synthesis
parameters, and Kononova et al. (2019) extracted 19,488 inorganic synthesis recipes into a
codified action-graph schema. The latter is a useful precedent for the present work's
ontology design, since it faced the same question of how finely to decompose a procedure into
discrete steps and conditions.

**What this literature reports about its own limits** is the hinge of this chapter. Analysing
their extracted data, the DigiMOF authors found more hydrothermal than solvothermal records,
which they describe as surprising because solvothermal is the more common laboratory route.
Their explanation is that many papers never name the route and instead imply it through
solvent and temperature, and that such implicit routes "could be easily deduced by a reader
but are challenging to extract using rule-based NLP" (Glasby et al., 2023).

That is a precise, falsifiable claim about where rule-based extraction fails and, by
implication, where a system with broader language understanding should help. It is
testable, and this work tests it.

## 2.2 Domain-specific language models

The second phase replaced hand-written grammars with pre-trained transformers.
Weston et al. (2019) applied named-entity recognition and normalisation to 3.27 million
materials abstracts. MatSciBERT (Gupta et al., 2022) showed that pre-training on materials
text substantially outperforms general-purpose BERT on domain named-entity recognition, and
Trewartha et al. (2022) quantified that advantage systematically. Tshitoyan et al. (2019)
demonstrated that unsupervised embeddings trained on materials literature encode latent
domain knowledge, to the point of anticipating later discoveries. Olivetti et al. (2020)
survey the field as it stood before language models.

These systems improve entity recognition but share two constraints relevant here. They
require labelled training data, and they operate at entity level rather than producing
complete, linked records. Recognising that "DMF" is a solvent does not establish which
synthesis used it.

## 2.3 Large language models for chemical extraction

The third phase prompts general-purpose models rather than training domain-specific ones.
Wei et al. (2023) showed that decomposing extraction into a two-stage dialogue makes
zero-shot information extraction competitive. Dagdelen et al. (2024) demonstrated that
language models can emit structured JSON records combining entities and relations for
materials tasks, and set out a human-in-the-loop annotation scheme. Polak and Morgan (2024)
reported precision and recall above 90 percent on materials property extraction using
conversational follow-up prompts with uncertainty filtering. Jablonka et al. (2024) showed
that fine-tuned models match or exceed bespoke machine learning on chemistry prediction from
small datasets.

Within MOF research specifically, Zheng et al. (2023) used prompt-engineered ChatGPT to mine
synthesis parameters from 228 articles, feeding a synthesis-prediction model.
Shi et al. (2024) showed that selecting few-shot demonstrations markedly improves MOF
synthesis-condition extraction over zero-shot prompting, with roughly four examples
sufficient. Lin et al. (2025) proposed a multi-agent framework dividing planning, extraction
and validation across cooperating agents. Ansari and Moosavi (2024) and Yang et al. (2026)
extend the agentic approach to autonomous dataset construction and to catalytic reaction
data. Bae et al. (2025) survey the whole manual-to-rule-based-to-language-model transition in
MOF text mining.

**Three properties recur across this body of work.** Validation is against small in-house
test sets rather than against the established databases the field already uses. The models
evaluated are almost exclusively commercial GPT variants. And cost is rarely reported at all,
despite being the factor that decides whether a pipeline can be rerun by a group without an
institutional budget.

## 2.4 Language models and knowledge graphs

Pan et al. (2024) provide the organising framework for combining language models with
knowledge graphs, distinguishing knowledge-graph-enhanced models, model-enhanced knowledge
graphs, and synergised systems, and identifying model-driven graph construction as an open
problem.

That problem has since been addressed at scale. Bai et al. (2025) constructed a knowledge
graph for framework materials from over 100,000 articles, producing 2.53 million nodes and
4.01 million relations covering synthesis, properties and applications, and coupled it to a
question-answering system reporting 91.67 percent accuracy. Ye et al. (2024) built a
comparable multidisciplinary materials graph and used it for cross-domain link prediction,
and Yoshitake and Nagata (2025) describe a method for property-focused graph construction.
Dreger et al. (2025) show that tables are a distinct, high-density extraction target that
prose-oriented pipelines miss.

Retrieval-augmented generation (Lewis et al., 2020) and its graph-structured successor
GraphRAG (Edge et al., 2024) establish why such graphs are useful downstream: grounding
generation in retrieved structure improves factuality, and graph structure specifically helps
on aggregation questions that span many documents.

Scale is therefore demonstrated. What these papers do not report is per-field extraction
validity: how often each individual field of an extracted record is correct.

## 2.5 Why validated MOF data matters downstream

The value of accurate synthesis records is not confined to retrieval. Luo et al. (2022) train
synthesis-prediction models directly on mined conditions, so extraction errors propagate into
predictions. MOFGalaxyNet (Jalali et al., 2023) represents the MOF landscape as a network of
linker and metal similarity and predicts guest accessibility using graph convolutional
networks, an approach that depends on reliable structured descriptions of each framework.
CoRE MOF (Chung et al., 2019) provides curated computation-ready structures, and MaScQA
(Zaki et al., 2024) benchmarks language models' materials knowledge, finding strong overall
performance alongside systematic conceptual failure modes.

Extraction quality is therefore an input to a chain of downstream work, which is what makes
measuring it per field worth doing rather than reporting a single aggregate.

## 2.6 The gap

Bringing the three strands together:

1. **Rule-based systems** are precise and auditable, and their own authors identify implicit
   synthesis routes as their characteristic failure (Glasby et al., 2023).
2. **Language models** have been applied to MOF extraction repeatedly, but validated against
   small in-house sets, using commercial models almost exclusively, and rarely with cost
   reported.
3. **Knowledge graph construction** has been demonstrated at a scale of millions of nodes,
   without per-field validity being established.

No published study evaluates language-model MOF synthesis extraction field by field against
both expert annotation and a rule-based baseline built from the same domain vocabulary, while
also reporting what each configuration costs and how an open-weight model compares.

This work occupies that gap. It is deliberately small in scale where the cited work is large,
and correspondingly more careful about what each number means: a hand-annotated gold standard,
a baseline built to succeed rather than to lose, per-field scores reported with their support
counts, and an explicit account of what the evaluation cannot show.
