# Literature Review — Building and Validating a MOF Synthesis Knowledge Graph with LLMs

**Status:** Groundwork pass, 10 June 2026 (pre-start). All 30 citations verified against live sources (Crossref/OpenAlex/arXiv/Europe PMC) on 10 June 2026 — none are from memory. Key findings below are **abstract/summary-level**; full-text reading happens in Weeks 1–2 per the reading plan at the end.

**Legend:** ★ = cited in exposé v2 (13 papers). RQ mapping: RQ1 = per-field accuracy vs. baselines · RQ2 = prompting strategies · RQ3 = agreement with DigiMOF/SynMOF · RQ4 = open-weight vs. commercial · RQ5 = KG utility (aggregation/QA).

---

## A. LLM–KG integration and graph-grounded retrieval (RQ5)

1. ★ **Pan, S., Luo, L., Wang, Y., Chen, C., Wang, J., & Wu, X. (2024).** Unifying Large Language Models and Knowledge Graphs: A Roadmap. *IEEE TKDE, 36*(7), 3580–3599. https://doi.org/10.1109/TKDE.2024.3352100
   - Finding: Framework paper defining the three integration patterns (KG-enhanced LLM, LLM-enhanced KG, synergised). Positions LLM-driven KG construction as a core open problem.
   - Relevance: Conceptual frame for the whole project; cite in intro.

2. ★ **Bai, X., He, S., Li, Y., et al. (2025).** Construction of a Knowledge Graph for Framework Material Enabled by Large Language Models and Its Application. *npj Computational Materials, 11*, 51. https://doi.org/10.1038/s41524-025-01540-6
   - Finding: KG-FM — LLM-built KG over 100,000+ articles on MOFs/COFs/HOFs (2.53M nodes, 4.01M relations); KG-coupled QA (Qwen2-KG) reaches 91.67% accuracy.
   - Relevance: **The paper this project positions against.** Demonstrates scale; per-field extraction validity is not its focus — our gap. Also the benchmark for the stretch KG-RAG comparison (RQ5).

3. **Ye, Y., Ren, J., Wang, S., Wan, Y., et al. (2024).** Construction and Application of Materials Knowledge Graph in Multidisciplinary Materials Science via Large Language Model. *NeurIPS 2024*; arXiv:2404.03080. https://arxiv.org/abs/2404.03080
   - Finding: Functional-materials KG built via LLM extraction across multidisciplinary literature; graph used for cross-domain link prediction.
   - Relevance: Closest general-materials analogue; contrast with our domain-deep, validation-first approach.

4. **Yoshitake, M., & Nagata, T. (2025).** A Method for LLM-Based Construction of a Materials Property Knowledge Graph: A Case Study. *Applied Sciences, 15*(19), 10511. https://doi.org/10.3390/app151910511
   - Finding: Recipe-style method paper for LLM property-KG construction; properties unevenly reported across literature motivate KG aggregation.
   - Relevance: Methodological comparison for KG schema and ingestion choices.

5. **Dreger, M., Malek, K., Eikerling, M., et al. (2025).** Large Language Models for Knowledge Graph Extraction from Tables in Materials Science. *Digital Discovery, 4*, 1221–1231. https://doi.org/10.1039/D4DD00362D
   - Finding: GPT-4-class models extract KG triples from materials tables with high accuracy; tables are a distinct, high-density source.
   - Relevance: MOF synthesis details often live in tables — informs corpus parsing scope (Week 3 decision: include tables or text-only).

6. ★ **Edge, D., Trinh, H., Cheng, N., et al. (2024).** From Local to Global: A GraphRAG Approach to Query-Focused Summarization. arXiv:2404.16130. https://arxiv.org/abs/2404.16130
   - Finding: Graph-grounded retrieval beats vanilla RAG on global/aggregation questions over corpora.
   - Relevance: Motivates the stretch KG-RAG vs. RAG experiment (RQ5).

7. **Lewis, P., Perez, E., Piktus, A., et al. (2020).** Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. *NeurIPS 33*. arXiv:2005.11401. https://arxiv.org/abs/2005.11401
   - Finding: Foundational RAG formulation.
   - Relevance: Baseline condition for the stretch QA comparison.

## B. LLM-based extraction in chemistry and materials (RQ1, RQ2, RQ4)

8. ★ **Zheng, Z., Zhang, O., Borgs, C., Chayes, J. T., & Yaghi, O. M. (2023).** ChatGPT Chemistry Assistant for Text Mining and the Prediction of MOF Synthesis. *JACS, 145*(32), 18048–18062. https://doi.org/10.1021/jacs.3c05819
   - Finding: Prompt-engineered ChatGPT mined synthesis parameters from 228 MOF papers (reported ~90%+ accuracy on their set); data fed a synthesis-prediction model.
   - Relevance: Direct predecessor for RQ1/RQ2; its in-house-only validation is exactly what our gold-set + database agreement design improves on.

9. ★ **Dagdelen, J., Dunn, A., Lee, S., et al. (2024).** Structured Information Extraction from Scientific Text with Large Language Models. *Nature Communications, 15*, 1418. https://doi.org/10.1038/s41467-024-45563-x
   - Finding: Fine-tuned LLMs extract entities+relations as structured (JSON) records across materials tasks; human-in-the-loop annotation scheme.
   - Relevance: Template for our schema-guided output format and annotation protocol (Week 6).

10. ★ **Polak, M. P., & Morgan, D. (2024).** Extracting Accurate Materials Data from Research Papers with Conversational Language Models and Prompt Engineering. *Nature Communications, 15*, 1569. https://doi.org/10.1038/s41467-024-45914-8
    - Finding: ChatExtract: conversational follow-up prompts with uncertainty filtering push extraction precision/recall above 90% on materials property data.
    - Relevance: Candidate prompting strategy for RQ2 (add conversational-verification variant?).

11. ★ **Shi, L., Liu, Z., Yang, Y., et al. (2024).** LLM-Based MOFs Synthesis Condition Extraction Using Few-Shot Demonstrations. arXiv:2408.04665. https://arxiv.org/abs/2408.04665
    - Finding: Few-shot demonstration selection markedly improves MOF synthesis-condition extraction over zero-shot (GPT-4-turbo, ~4 examples enough).
    - Relevance: Sets the few-shot arm of RQ2; GPT-only scope is part of the gap we close with open-weight models (RQ4).

12. ★ **Lin, Z., Ren, D., Ran, K., et al. (2025).** Reshaping MOFs Text Mining with a Dynamic Multi-Agent Framework of Large Language Models. arXiv:2504.18880. https://arxiv.org/abs/2504.18880
    - Finding: Multi-agent pipeline (planning/extraction/validation agents) for MOF text mining; accepted at Trans. Materials Research (2026).
    - Relevance: Agentic alternative to single-shot prompting; candidate ablation in Week 9; no systematic database-agreement validation — gap confirmation.

13. **Wei, X., Cui, X., Cheng, N., et al. (2023).** Zero-Shot Information Extraction via Chatting with ChatGPT. arXiv:2302.10205. https://arxiv.org/abs/2302.10205
    - Finding: Two-stage chat decomposition makes zero-shot IE competitive.
    - Relevance: Zero-shot arm design for RQ2.

14. **Jablonka, K. M., Schwaller, P., Ortega-Guerrero, A., & Smit, B. (2024).** Leveraging Large Language Models for Predictive Chemistry. *Nature Machine Intelligence, 6*, 161–169. https://doi.org/10.1038/s42256-023-00788-1
    - Finding: Fine-tuned GPT models match/beat bespoke ML on diverse chemistry prediction tasks from tiny datasets.
    - Relevance: Context for why LLMs are credible chemistry workhorses; supports fine-tuning discussion (out of scope but cite-worthy).

15. **Ansari, M., & Moosavi, S. M. (2024).** Agent-Based Learning of Materials Datasets from the Scientific Literature. *Digital Discovery, 3*, 2607–2617. https://doi.org/10.1039/D4DD00252K
    - Finding: Eunomia — LLM agent autonomously builds materials datasets from literature without fine-tuning.
    - Relevance: Agentic extraction comparison point; dataset-construction QA ideas.

16. **Yang, W., Liu, Z., Tan, T., Hu, X., et al. (2026).** AgentCAT: An LLM Agent for Extracting and Analyzing Catalytic Reaction Data from Chemical Engineering Literature. arXiv:2602.18479. https://arxiv.org/abs/2602.18479
    - Finding: Agent pipeline for catalytic reaction data extraction + analysis (2026 — state of the art for agentic chem-IE).
    - Relevance: Adjacent-domain design patterns; shows the field is moving agentic — strengthens our "validation is the missing piece" framing.

## C. MOF and inorganic text-mining lineage; reference databases (RQ1, RQ3)

17. ★ **Swain, M. C., & Cole, J. M. (2016).** ChemDataExtractor: A Toolkit for Automated Extraction of Chemical Information from the Scientific Literature. *JCIM, 56*(10), 1894–1904. https://doi.org/10.1021/acs.jcim.6b00207
    - Finding: Rule/grammar-based chemical NER + property extraction toolkit.
    - Relevance: Baseline #1 (RQ1); also the engine behind DigiMOF — so the agreement analysis (RQ3) doubles as an LLM-vs-CDE comparison at scale.

18. **Kim, E., Huang, K., Saunders, A., et al. (2017).** Materials Synthesis Insights from Scientific Literature via Text Extraction and Machine Learning. *Chemistry of Materials, 29*(21), 9436–9444. https://doi.org/10.1021/acs.chemmater.7b03500
    - Finding: Early synthesis-parameter mining (oxides) with NN-assisted extraction.
    - Relevance: Historical anchor for synthesis-condition extraction; error types to expect.

19. **Kononova, O., Huo, H., He, T., et al. (2019).** Text-Mined Dataset of Inorganic Materials Synthesis Recipes. *Scientific Data, 6*, 203. https://doi.org/10.1038/s41597-019-0224-1
    - Finding: 19,488 inorganic synthesis recipes auto-extracted into a codified action-graph schema.
    - Relevance: Schema design precedent for SynthesisMethod/Condition modelling (ontology open question #3).

20. ★ **Glasby, L. T., Gubsch, K., Bence, R., et al. (2023).** DigiMOF: A Database of Metal–Organic Framework Synthesis Information Generated via Text Mining. *Chemistry of Materials, 35*(11), 4510–4524. https://doi.org/10.1021/acs.chemmater.3c00788
    - Finding: CDE-built open database: 43,281 MOF articles → 15,501 MOFs, 52,680 synthesis-property records (method, solvent, linker, metal precursor, topology).
    - Relevance: **Reference database #1 for RQ3.** Its article index also seeds our corpus (Week 3). Open-source — confirm licence in Week 1.

21. ★ **Luo, Y., Bag, S., Zaremba, O., et al. (2022).** MOF Synthesis Prediction Enabled by Automatic Data Mining and Machine Learning. *Angew. Chem. Int. Ed., 61*, e202200242. https://doi.org/10.1002/anie.202200242
    - Finding: SynMOF database (983 MOFs with mined synthesis conditions: metal source, linker, temperature, time, solvent, additives) + ML synthesis prediction; code/data on GitHub (aimat-lab).
    - Relevance: **Reference database #2 for RQ3**; also the downstream consumer of validated data (outlook).

22. **Bae, S., Jeon, M., Moon, H., et al. (2025).** Text Mining in MOF Research: From Manual Curation to Large Language Model-Based Automation. *Chemical Communications, 61*, 11083–11094. https://doi.org/10.1039/D5CC02511G
    - Finding: Review charting the manual → rule-based → LLM transition in MOF text mining; catalogues open challenges.
    - Relevance: Field map for Section 4 of the report; checks our gap claim against the field's own framing.

## D. Domain language models and embeddings — baselines (RQ1)

23. **Weston, L., Tshitoyan, V., Dagdelen, J., et al. (2019).** Named Entity Recognition and Normalization Applied to Large-Scale Information Extraction from the Materials Science Literature. *JCIM, 59*(9), 3692–3702. https://doi.org/10.1021/acs.jcim.9b00470
    - Finding: Foundational materials NER + normalisation at scale (3.27M abstracts).
    - Relevance: Entity-normalisation precedent for our chemical-name resolution (Week 7).

24. ★ **Gupta, T., Zaki, M., Krishnan, N. M. A., & Mausam. (2022).** MatSciBERT: A Materials Domain Language Model for Text Mining and Information Extraction. *npj Computational Materials, 8*, 102. https://doi.org/10.1038/s41524-022-00784-w
    - Finding: Domain pre-training beats SciBERT/BERT on materials NER/classification benchmarks.
    - Relevance: Baseline #2 (RQ1) — fine-tune for relation/field extraction on our gold set.

25. **Trewartha, A., Walker, N., Huo, H., et al. (2022).** Quantifying the Advantage of Domain-Specific Pre-training on Named Entity Recognition Tasks in Materials Science. *Patterns, 3*(4), 100488. https://doi.org/10.1016/j.patter.2022.100488
    - Finding: Systematic quantification of domain-pre-training gains (incl. MatBERT).
    - Relevance: Baseline-selection justification; expected baseline ceiling for RQ1.

26. **Tshitoyan, V., Dagdelen, J., Weston, L., et al. (2019).** Unsupervised Word Embeddings Capture Latent Knowledge from Materials Science Literature. *Nature, 571*, 95–98. https://doi.org/10.1038/s41586-019-1335-8
    - Finding: mat2vec embeddings encode materials knowledge; predicted discoveries before publication.
    - Relevance: Classic motivation for literature-as-data; embedding-based entity resolution context (Week 7).

27. **Olivetti, E., Cole, J., Kim, E., et al. (2020).** Data-Driven Materials Research Enabled by Natural Language Processing and Information Extraction. *Applied Physics Reviews, 7*, 041317. https://doi.org/10.1063/5.0021106
    - Finding: Survey of NLP/IE for materials pre-LLM.
    - Relevance: Background section scaffolding; pre-LLM error taxonomies to reuse in Week 9.

## E. MOF data resources and graph ML (RQ3, RQ5)

28. **Chung, Y. G., Haldoupis, E., Bucior, B. J., et al. (2019).** Advances, Updates, and Analytics for the Computation-Ready, Experimental Metal–Organic Framework Database: CoRE MOF 2019. *J. Chem. Eng. Data, 64*(12), 5985–5998. https://doi.org/10.1021/acs.jced.9b00835
    - Finding: 14,000+ curated, computation-ready experimental MOF structures.
    - Relevance: Corpus seed (DOI lists) + canonical MOF identifiers for entity resolution; SynMOF links to CoRE entries.

29. ★ **Jalali, M., Wonanke, A. D. D., & Wöll, C. (2023).** MOFGalaxyNet: A Social Network Analysis for Predicting Guest Accessibility in Metal–Organic Frameworks Utilizing Graph Convolutional Networks. *Journal of Cheminformatics, 15*, 94. https://doi.org/10.1186/s13321-023-00764-2
    - Finding: MOF landscape as a network (linker/metal similarity); GCN predicts guest accessibility from network position.
    - Relevance: **Supervisor's research line.** The kind of downstream graph-ML consumer our validated KG feeds; potential Week-10+ integration discussion.

## F. Evaluation and benchmarks (RQ1)

30. **Zaki, M., Jayadeva, Mausam, & Krishnan, N. M. A. (2024).** MaScQA: Investigating Materials Science Knowledge of Large Language Models. *Digital Discovery, 3*, 313–327. https://doi.org/10.1039/D3DD00188A
    - Finding: 650-question materials QA benchmark; LLMs strong but with systematic conceptual failure modes.
    - Relevance: Failure-mode vocabulary for our error taxonomy (Week 9); QA-style eval contrast for RQ5.

---

## Cross-cutting observations (for supervisor discussion, Week 1)

1. **The gap claim holds across A–C:** scale (Bai), prompting (Shi, Zheng), and agents (Lin, Ansari, Yang) are all demonstrated for MOF/chem extraction — but none validates per-field against expert annotation *plus* the existing text-mined databases, and open-weight models are absent everywhere. RQ3 + RQ4 are genuinely open.
2. **Schema precedent:** Kononova's action-graph recipes vs. DigiMOF's flat fields vs. our graph ontology — decide condition granularity (ontology open question #3) after reading both in full.
3. **Tables matter:** Dreger 2025 suggests MOF synthesis tables may carry data the prose lacks — scope decision for Week 3 (GROBID table extraction on/off).
4. **Tooling note:** spaCy (Honnibal et al., 2020) remains the NLP substrate; not listed as a numbered entry since it is infrastructure, not prior art.

## Reading plan (Weeks 1–2)

| Priority | Papers | Why first |
|----------|--------|-----------|
| P0 (full read, week 1) | Bai 2025; Glasby 2023; Luo 2022; Zheng 2023; Shi 2024 | Define the gap, the reference databases, and the closest methods |
| P1 (full read, week 1–2) | Dagdelen 2024; Polak & Morgan 2024; Lin 2025; Bae 2025; Kononova 2019 | Annotation protocol, prompting arms, schema design |
| P2 (targeted read, week 2) | Pan 2024; Edge 2024; Ye 2024; Gupta 2022; Trewartha 2022; Chung 2019; Jalali 2023 | Framing, baselines, resources |
| P3 (skim/reference) | Remainder | Background and report writing |
