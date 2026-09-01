# Gold standard: provenance and licensing

`gold.jsonl` contains 100 hand-annotated passages and 138 triples. Each record carries the
verbatim passage text, because an annotation is not checkable without the text it refers to.

## The text is not mine to relicense

Every passage is an excerpt from a third-party open-access paper. The MIT licence on this
repository covers the code and the annotations, **not** the quoted passages. Each record
therefore carries `source_doi`, `source_title`, `source_license` and `source_url` so the
excerpt can always be traced and credited.

Licences of the source papers for these 100 passages:

| Licence | Passages |
|---|---|
| CC BY | 71 |
| CC BY-NC-ND | 19 |
| CC BY-NC | 10 |

**What this permits.** All three licences allow redistribution of verbatim excerpts with
attribution. The NonCommercial terms restrict commercial reuse, and the NoDerivatives terms
restrict adaptation, so anyone reusing this file must respect the licence of the specific
paper an excerpt came from rather than treating the file as uniformly MIT.

**If you want only the annotations**, strip `passage_text` and join back to the source by
`source_doi`. The annotations themselves, the triples, are original work and are MIT licensed.

## What the records contain

| Field | Meaning |
|---|---|
| `passage_id` | Stable identifier, deterministic from paper, section and position |
| `paper_id`, `source_doi`, `source_title`, `source_url` | Provenance of the excerpt |
| `source_license` | Licence family of the source paper |
| `section`, `passage_text` | Where the excerpt came from, and the excerpt |
| `status` | `annotated`, `no_synthesis` or `skipped` |
| `triples` | The annotations, with subject, relation, object, evidence and confidence |
| `annotator`, `annotated_at` | Who annotated it and when |

## How it was produced

Annotated by hand by the author. It was deliberately never pre-filled with model output,
because it is the instrument the models are measured against and a model-generated reference
would make every accuracy figure circular.

The sample is 100 passages drawn with a fixed seed: 90 from the passages a rule-based
pre-filter flagged as synthesis text, and 10 unflagged controls included so the pre-filter's
own error rate is measurable. Of the 90 flagged, 32 contained a synthesis record, giving the
pre-filter a measured precision of about 36 percent. None of the 10 controls contained missed
synthesis content.

Two known limitations are documented in `docs/report/07_limitations.md`: the subject field of
every `IN_SOLVENT` and `AT_CONDITION` triple records the MOF name rather than the synthesis
method, a defect of the annotation tool at the time, and condition values were recorded as
single combined strings rather than one condition per triple.
