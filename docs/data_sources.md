# Reference data acquisition notes

Working notes on obtaining the databases this project validates against. Written
2026-08-22. Every claim here was verified by direct download or inspection, not assumed.

## Corpus (done)

- Source: Europe PMC open-access subset, JATS full-text XML, section-labelled.
- Query: `(metal-organic framework AND synthesis) AND OPEN_ACCESS:y AND HAS_FT:y AND IN_EPMC:y`
- Collected: **400 papers, 20,597,681 characters**, 100 percent with a DOI.
- 233 of 400 (58 percent) have an identifiable synthesis or experimental section. Raising
  this share is a corpus-precision task, see the query-tuning work.
- Licences: 299 CC BY, 56 CC BY-NC-ND, 43 CC BY-NC, 2 unrecognised.
  The 2 unrecognised (`PMC6311690`, `PMC9057490`) must be verified or dropped before use.
- Publisher spread by DOI prefix: RSC 107, MDPI 78, ACS 75, Nature 40, Wiley 40,
  Elsevier 11, others smaller. This matters: RSC, ACS and Wiley are exactly the publishers
  DigiMOF drew from, so the earlier worry that a Europe PMC corpus would not overlap the
  reference databases is not supported by the data.
- DOI index for joining: `data/processed/paper_index.json` (399 unique DOIs, 1 duplicate).

## DigiMOF (partially obtained, with a caveat that affects method)

- Paper: Glasby et al. 2023, Chem. Mater. 35(11) 4510-4524, doi 10.1021/acs.chemmater.3c00788.
  The paper is itself in our corpus as PMC10269341.
- Code repository (cloned to `data/raw/reference/digimof`):
  https://github.com/peymanzmoghadam/DigiMOF-database-master-main.git
  Contains the **MOF-adapted ChemDataExtractor source**, including
  `chemdataextractor/parse/synthesis.py`, `parse/organic_precursor.py`,
  `parse/mof_topology.py`. This is valuable in its own right: it is the exact rule-based
  system DigiMOF used, so our ChemDataExtractor baseline can be the real thing rather than
  a generic approximation. The repository contains **no data files**.
- Supporting Information (downloaded to `data/raw/reference/digimof_si`, fetched from
  Europe PMC `/PMC10269341/supplementaryFiles`, so openly licensed):
  - `cm3c00788_si_001.xlsx`, sheets `Master`, `Topology_breakdown`, `CSD_transformed_data`.
    Keyed by **CSD refcode**. Holds cleaned linkers, metal, topology, solvents, and
    structural properties (LCD, PLD, density, ASA, void fraction).
  - `cm3c00788_si_002.xlsx`, TCI chemical cost data, 154 rows.

**Caveat that changes the join strategy.** The SI is keyed by CSD refcode and contains
structure-derived fields. It is not the text-mined synthesis-route table (the paper reports
9,705 synthesis route records over 43,281 papers). Our corpus is keyed by DOI and PMCID.
A per-paper join therefore needs a refcode to DOI mapping, which normally comes from the
CSD, a licensed resource.

Options, to be decided once the scouting report lands:
1. Locate the full DigiMOF text-mined table with DOIs (leads: wiz.shef.ac.uk, a Zenodo or
   figshare deposit, or contacting the authors).
2. Join on MOF name instead of identifier, accepting and reporting the ambiguity.
3. Compare at the distribution level (for example the share of hydrothermal versus
   solvothermal reports) rather than per paper.
4. Lean on SynMOF for the per-record comparison if it carries DOIs.
Whichever is chosen must be stated plainly in the methodology, since it bounds what the
agreement analysis can claim.

## A finding worth using in the report

DigiMOF's own authors write that many papers do not name the synthesis route explicitly but
imply it through solvents and temperatures, and that such implicit routes "could be easily
deduced by a reader but are challenging to extract using rule-based NLP" (Data Analysis
section of the DigiMOF paper). That is precisely the gap an LLM extractor should close, and
it gives this project a concrete, pre-registered hypothesis from the baseline's own authors:
LLM extraction should beat rule-based extraction by the largest margin on implicit synthesis
routes, and by much less on explicitly named reagents.

## SynMOF (outstanding)

Luo et al. 2022, Angew. Chem. Int. Ed. 61, e202200242. The aimat-lab repository
`MOF_Synthesis_Prediction` was inspected and holds mostly machine-learning feature dumps
(`RAC_features`, `Fingerprint_features`), not a clean DOI-indexed record table. Still being
scouted.
