---
name: verify-citation
description: Verify a paper's citation against live bibliographic sources (Crossref, OpenAlex, arXiv) before it enters any document. Use this whenever adding or editing references in the exposé, literature review, evaluation report, final report, or any docs/ file; whenever the user gives a paper title, DOI, or arXiv id to cite; and whenever about to write a citation from memory — citing from memory is forbidden in this project, so every reference must pass through this check first.
---

# verify-citation

This is a graded research project: one hallucinated or wrong reference in the final report can cost more than a missing experiment. The rule is absolute — **no citation enters a document without being matched against a live source first**. This skill makes that cheap.

## Procedure

1. Run the bundled lookup script (stdlib-only, no install needed):

   ```bash
   python3 .claude/skills/verify-citation/scripts/cite_check.py doi   "10.1021/acs.chemmater.3c00788"
   python3 .claude/skills/verify-citation/scripts/cite_check.py title "MOF synthesis prediction data mining"
   python3 .claude/skills/verify-citation/scripts/cite_check.py arxiv "2408.04665"
   ```

2. **Compare the returned title and authors against the paper you intended.** A search returning *a* paper is not verification — bibliographic queries often return a similar-but-wrong paper. If the title doesn't clearly match the intent, it is not verified.

3. Write the reference in the project's citation style and include the link:
   - APA-like, as in `docs/literature_review.md`: `Family, I., Family, I., & Family, I. (Year). Title. *Venue, Vol*(Issue), pages. https://doi.org/...`
   - Long author lists: first 3 + "et al." (established in exposé v2).

4. If the paper cannot be verified in any source: **do not cite it.** Say so explicitly and let the user decide. Fewer verified references beat padded ones.

## Known traps (each one bit us before)

- **Supplementary DOIs**: Crossref title searches sometimes return `10.xxxx/....s001` — that's the *supplementary material*, not the paper. The script warns and strips the suffix on `doi` lookups; if you see `.s001` in a `title` search result, re-look-up the parent DOI.
- **Preprint vs. journal version**: a paper may exist as ChemRxiv/arXiv preprint *and* a journal article with different years and DOIs (e.g., Jablonka 2023 preprint → Nat. Mach. Intell. 2024). Prefer the journal version; check OpenAlex results for it before settling on a preprint.
- **Paywalled landing pages** (nature.com, link.springer.com) often fail direct fetching — that's why the script uses the APIs (Crossref/OpenAlex/arXiv, plus Europe PMC at `https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:"..."&resultType=core&format=json` for biomedical-indexed journals). Don't burn time fetching publisher pages.
- **Semantic Scholar** rate-limits anonymous API calls aggressively — OpenAlex is the reliable fallback, not S2.

## Output contract

When verifying for a document, report per paper: the formatted reference, the canonical link, and which source confirmed it. When verifying a whole reference list, end with a count: "N/N verified".
