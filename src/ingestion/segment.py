"""Split corpus papers into passages and score each one for synthesis content.

Why this module exists
----------------------
The unit of extraction in this project is the synthesis *paragraph*, not the paper.
A paper in `data/processed/corpus.jsonl` runs tens of thousands of characters, of
which usually one or two paragraphs actually contain a recipe. Feeding whole papers
to an extractor would blow the context budget, bury the recipe in unrelated prose and
make per-field accuracy impossible to attribute to a specific piece of text. So the
pipeline is: paper -> passages -> triples, and everything downstream (the human gold
standard, the extractors, the evaluation) is keyed on `passage_id`.

Two design decisions are load bearing:

1. **`passage_id` is deterministic**, derived from `paper_id`, the section name, the
   occurrence index of that section name inside the paper and the passage index inside
   the section. It deliberately does *not* hash the passage text. The gold standard
   references these ids, and a corpus rebuild that re-downloads the same papers must
   produce the same ids, otherwise annotations silently detach from their text. Because
   the id is not text derived, a passage whose text shifts slightly (parser change,
   publisher correction) keeps its id and the annotation stays attached to the same
   place in the paper. The tradeoff is accepted knowingly: an id is a *location*, not a
   checksum, and `text` is stored alongside it so drift is still auditable.

2. **The synthesis scorer is a transparent weighted rule set**, not a classifier. The
   weights live in one constant block below so that they can be tuned, reported and
   defended in the write-up, and so that a grader can recompute any score by hand. A
   learned filter would need labelled data that this project spends on the gold
   standard instead, and it could not be justified in the report without its own
   evaluation.

Boilerplate sections (acknowledgements, funding, conflicts of interest) are *not*
dropped: discarding text at segmentation time is irreversible and hides parser bugs.
They simply score near zero and are removed by `--synthesis-only` at write time.

Run:
    python -m src.ingestion.segment
    python -m src.ingestion.segment --synthesis-only --min-score 0.5

Output: one `Passage` per line in data/processed/passages.jsonl.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import typer
from loguru import logger
from pydantic import BaseModel, Field

from .models import CorpusDoc

app = typer.Typer(add_completion=False)

REPO = Path(__file__).resolve().parents[2]
CORPUS_DEFAULT = REPO / "data" / "processed" / "corpus.jsonl"
OUT_DEFAULT = REPO / "data" / "processed" / "passages.jsonl"

# --------------------------------------------------------------------------------------
# Segmentation geometry (tunable)
# --------------------------------------------------------------------------------------
# Europe PMC JATS parsing (src/ingestion/parse.py) joins the <p> elements of a section
# with a single "\n", so in this corpus a newline run *is* a paragraph boundary.
_PARAGRAPH_BLOCK = re.compile(r"[^\n]+")

# Sentence boundary used only to cut over-long paragraphs; deliberately crude, because a
# wrong cut costs a slightly odd passage boundary, never a lost character.
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")

# A fragment shorter than this is a figure caption, a stray heading or a table remnant
# rather than a recipe, so it is merged into its neighbour instead of being emitted as a
# one-line passage that a human would have to annotate with no context.
MIN_PASSAGE_CHARS = 200

# Merging stops here so that a section made of many short lines does not collapse into a
# single unreadable blob.
MERGE_LIMIT_CHARS = 3000

# Upper bound on an emitted passage. Long enough to hold a complete MOF recipe (the
# longest real synthesis paragraphs in this corpus are ~2 kB), short enough to stay
# inside a cheap prompt and to be read in one sitting by a human annotator.
MAX_PASSAGE_CHARS = 2500

# Anything shorter than this after merging carries no annotatable content at all.
MIN_KEEP_CHARS = 40

# --------------------------------------------------------------------------------------
# Synthesis scoring weights (tunable; this block is the one cited in the report)
# --------------------------------------------------------------------------------------
# Score = sum over signal groups of  weight * min(hits, saturation) / saturation,
# clipped to [0, 1]. The positive weights sum to 1.0, so a score reads as "fraction of
# the synthesis evidence we look for that this passage shows". Saturation caps stop one
# repeated word (or one very long paragraph) from carrying a passage on its own, which
# is the main failure mode of naive keyword counting.
#
# The precursor and product groups were added after inspecting a random sample of
# high-scoring passages from the real 400 paper corpus: without them, adsorption
# experiments, catalysis tests and cell assays scored like recipes, because those
# paragraphs are also full of masses, volumes, temperatures and procedure verbs. What a
# synthesis paragraph has and a use-of-the-material paragraph does not is *reagent
# chemistry going in* (a metal salt plus a linker) and *a material coming out*.
W_SECTION_CUE = 0.20
W_METHOD = 0.15
W_QUANTITY = 0.15
W_APPARATUS = 0.10
W_SOLVENT = 0.10
W_VERB = 0.10
W_PRECURSOR = 0.10
W_PRODUCT = 0.10
# Characterisation, front/back matter, and downstream-application language. Negative
# because the highest precision loss comes from paragraphs that sit inside the very same
# "Experimental" section as the recipe but describe measuring or using the material.
W_NEGATIVE = -0.25

SATURATION: dict[str, int] = {
    "method": 1,
    "quantity": 4,
    "apparatus": 1,
    "solvent": 2,
    "verb": 3,
    "precursor": 2,
    "product": 1,
    "negative": 3,
}

# Passages at or above this score are marked `is_synthesis`. Chosen by inspecting the
# score distribution over the real 400 paper corpus, never on the gold standard (the
# gold standard is frozen and must not be tuned against). Overridable with --min-score.
DEFAULT_MIN_SCORE = 0.45

SECTION_TITLE_CUES: tuple[str, ...] = (
    "experimental",
    "synthesis",
    "syntheses",
    "synthesized",
    "materials and methods",
    "materials & methods",
    "method",
    "preparation",
    "general procedure",
    "fabrication",
)

METHOD_WORDS: tuple[str, ...] = (
    "solvothermal",
    "hydrothermal",
    "microwave",
    "mechanochemical",
    "sonochemical",
    "ultrasonic",
    "electrochemical synthesis",
    "reflux",
    "refluxed",
    "room temperature synthesis",
    "one-pot",
    "in situ growth",
)

APPARATUS_WORDS: tuple[str, ...] = (
    "autoclave",
    "teflon",
    "ptfe",
    "vial",
    "oven",
    "centrifuge",
    "muffle furnace",
    "hot plate",
    "round-bottom flask",
    "round bottom flask",
    "schlenk",
)

SOLVENT_WORDS: tuple[str, ...] = (
    "dmf",
    "n,n-dimethylformamide",
    "def",
    "n,n-diethylformamide",
    "dmso",
    "dimethyl sulfoxide",
    "dma",
    "n,n-dimethylacetamide",
    "methanol",
    "ethanol",
    "acetonitrile",
    "deionized water",
    "deionised water",
    "distilled water",
    "aqueous solution",
)

PROCEDURE_VERBS: tuple[str, ...] = (
    "dissolved",
    "added",
    "mixed",
    "heated",
    "stirred",
    "stirring",
    "washed",
    "filtered",
    "dried",
    "cooled",
    "centrifuged",
    "sonicated",
    "precipitated",
    "collected",
    "evacuated",
    "activated",
    "degassed",
)

# Reagent chemistry entering a MOF synthesis: metal salts and the carboxylate/azolate
# linkers that dominate this literature. Matched as substrings of words where the term is
# a fragment (e.g. "imidazol" covers imidazole and imidazolate).
PRECURSOR_CUES: tuple[str, ...] = (
    "nitrate",
    "chloride",
    "sulfate",
    "sulphate",
    "acetate",
    "hexahydrate",
    "tetrahydrate",
    "trihydrate",
    "terephthalic",
    "trimesic",
    "fumaric",
    "benzenedicarboxylic",
    "benzenetricarboxylic",
    "imidazol",
    "h2bdc",
    "h3btc",
    "bdc",
    "btc",
    "linker",
    "ligand",
    "precursor",
    "molar ratio",
    "stoichiometric",
)

# A material coming out of the paragraph, as opposed to a material being used in it.
PRODUCT_CUES: tuple[str, ...] = (
    "was synthesized",
    "were synthesized",
    "was synthesised",
    "were synthesised",
    "was prepared",
    "were prepared",
    "synthesis of",
    "preparation of",
    "typical synthesis",
    "typical procedure",
    "as-synthesized",
    "as-synthesised",
    "yield",
    "crystals were obtained",
    "product was obtained",
)

NEGATIVE_CUES: tuple[str, ...] = (
    "et al",
    "figure",
    "fig.",
    "table",
    "spectra",
    "spectrum",
    "diffraction",
    "isotherm",
    # Downstream use of a finished material, the dominant false positive mode.
    "adsorption experiment",
    "adsorption kinetic",
    "adsorption capacit",
    "adsorption isotherm",
    "photocatalytic degradation",
    "calibration curve",
    "cell viability",
    "cytotoxicity",
    "antibacterial activity",
    "machine learning",
    "density functional",
    "acknowledg",
    "conflict of interest",
    "conflicts of interest",
    "funding",
    "author contribution",
    "supplementary",
    "supporting information",
    "data availability",
    "in conclusion",
    "this review",
    "in this study, we",
    "have attracted",
    "promising candidate",
)

# Quantities: a number immediately followed by a synthesis-relevant unit. This is the
# single strongest cue that a paragraph states a recipe rather than describing one.
QUANTITY_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])\d+(?:[.,]\d+)?\s*"
    r"(?:mg|g|kg|mmol|mol|m|mm|nm|ml|l|µl|ul|wt\s*%|%|"
    r"h|hr|hrs|hour|hours|min|mins|minute|minutes|"
    r"°\s*c|º\s*c|degrees?\s*c|k|rpm|bar|mpa)"
    r"(?![A-Za-z])",
    re.IGNORECASE,
)


def _phrase_regex(
    phrases: tuple[str, ...], *, left_boundary: bool = True, right_boundary: bool = True
) -> re.Pattern[str]:
    """Alternation over a phrase list, compiled once at import time.

    Scoring runs over ~20 million characters, so compiling per call would dominate the
    runtime of the whole segmentation step. The boundary flags exist because chemistry
    text needs three different matching strictnesses: whole words for verbs, prefixes for
    cues with inflections ("yield" -> "yielded"), and bare substrings for fragments that
    sit inside formulae ("bdc" inside "H2bdc", "imidazol" inside "imidazolate").
    """
    parts = []
    for p in phrases:
        left = r"\b" if left_boundary and p[0].isalnum() else ""
        right = r"\b" if right_boundary and p[-1].isalnum() else ""
        parts.append(f"{left}{re.escape(p)}{right}")
    return re.compile("|".join(parts), re.IGNORECASE)


_METHOD_RE = _phrase_regex(METHOD_WORDS)
_APPARATUS_RE = _phrase_regex(APPARATUS_WORDS)
_SOLVENT_RE = _phrase_regex(SOLVENT_WORDS)
_VERB_RE = _phrase_regex(PROCEDURE_VERBS)
_PRECURSOR_RE = _phrase_regex(PRECURSOR_CUES, left_boundary=False, right_boundary=False)
_PRODUCT_RE = _phrase_regex(PRODUCT_CUES, right_boundary=False)
_NEGATIVE_RE = _phrase_regex(NEGATIVE_CUES)


class Passage(BaseModel):
    """One annotatable, extractable unit of text with full provenance back to the paper.

    `char_start`/`char_end` are offsets into the *section* text (not the whole paper), so
    the invariant `text == doc.sections[i].text[char_start:char_end]` holds exactly. That
    is what lets an annotation tool highlight a passage inside its section and lets a
    triple's evidence sentence be traced back to a character range in the source.
    """

    passage_id: str
    paper_id: str
    doi: str | None = None
    section_name: str
    text: str
    char_start: int
    char_end: int
    is_synthesis: bool = False
    synthesis_score: float = 0.0
    # Per group hit counts behind the score. Stored so any classification in the report
    # can be explained ("this passage scored 0.72 because ...") without re-running.
    signals: dict[str, int] = Field(default_factory=dict)

    @property
    def n_chars(self) -> int:
        return len(self.text)


def make_passage_id(paper_id: str, section_name: str, section_occurrence: int, index: int) -> str:
    """Stable id for a passage location: `<paper_id>-<10 hex>`.

    `section_occurrence` disambiguates papers that repeat a section title (the corpus has
    107 sections literally named "Untitled section"), so ids stay unique without falling
    back on a global section index, which would shift for every later section whenever the
    parser gains or loses one section early in a paper.
    """
    key = f"{paper_id}|{section_name}|{section_occurrence}|{index}"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]
    return f"{paper_id}-{digest}"


def score_passage(text: str, section_name: str = "") -> tuple[float, dict[str, int]]:
    """Score `text` in [0, 1] for "this paragraph states a synthesis recipe".

    Returns the score and the raw hit counts per signal group, so the decision is
    always inspectable. See the weight block above for the rationale of each group.
    """
    title = section_name.lower()
    hits: dict[str, int] = {
        "section_cue": int(any(cue in title for cue in SECTION_TITLE_CUES)),
        "method": len(_METHOD_RE.findall(text)),
        "quantity": len(QUANTITY_PATTERN.findall(text)),
        "apparatus": len(_APPARATUS_RE.findall(text)),
        "solvent": len(_SOLVENT_RE.findall(text)),
        "verb": len(_VERB_RE.findall(text)),
        "precursor": len(_PRECURSOR_RE.findall(text)),
        "product": len(_PRODUCT_RE.findall(text)),
        "negative": len(_NEGATIVE_RE.findall(text)),
    }

    def group(name: str, weight: float) -> float:
        cap = SATURATION[name]
        return weight * min(hits[name], cap) / cap

    score = (
        W_SECTION_CUE * hits["section_cue"]
        + group("method", W_METHOD)
        + group("quantity", W_QUANTITY)
        + group("apparatus", W_APPARATUS)
        + group("solvent", W_SOLVENT)
        + group("verb", W_VERB)
        + group("precursor", W_PRECURSOR)
        + group("product", W_PRODUCT)
        + group("negative", W_NEGATIVE)
    )
    return max(0.0, min(1.0, round(score, 4))), hits


def _block_spans(text: str) -> list[tuple[int, int]]:
    """Paragraph spans (start, end) into `text`, whitespace trimmed, empties dropped."""
    spans: list[tuple[int, int]] = []
    for m in _PARAGRAPH_BLOCK.finditer(text):
        start, end = m.start(), m.end()
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1].isspace():
            end -= 1
        if end > start:
            spans.append((start, end))
    return spans


def _merge_short(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge fragments below `MIN_PASSAGE_CHARS` into their neighbour.

    A merged passage keeps the outer offsets, so its text is the *contiguous* slice of
    the section including the newline between the fragments. Keeping the slice contiguous
    (rather than re-joining stripped pieces) is what preserves the offset invariant.
    """
    merged: list[tuple[int, int]] = []
    for span in spans:
        if merged:
            prev = merged[-1]
            too_short = (span[1] - span[0]) < MIN_PASSAGE_CHARS
            prev_too_short = (prev[1] - prev[0]) < MIN_PASSAGE_CHARS
            combined = span[1] - prev[0]
            if (too_short or prev_too_short) and combined <= MERGE_LIMIT_CHARS:
                merged[-1] = (prev[0], span[1])
                continue
        merged.append(span)
    return merged


def _split_long(text: str, span: tuple[int, int]) -> list[tuple[int, int]]:
    """Cut an over-long paragraph at sentence boundaries into <= MAX_PASSAGE_CHARS chunks.

    Some publishers emit a whole experimental section as one <p>. Such a block is too long
    to prompt with and too long to annotate reliably, so it is cut at sentence boundaries;
    offsets remain exact because the cut points are taken from the original string.
    """
    start, end = span
    if end - start <= MAX_PASSAGE_CHARS:
        return [span]

    # Candidate cut points: the start of every sentence inside the span.
    cuts = [start] + [start + m.end() for m in _SENTENCE_END.finditer(text[start:end])]
    chunks: list[tuple[int, int]] = []
    chunk_start = start
    for i, cut in enumerate(cuts):
        nxt = cuts[i + 1] if i + 1 < len(cuts) else end
        if nxt - chunk_start >= MAX_PASSAGE_CHARS:
            stop = nxt if cut == chunk_start else cut
            chunks.append((chunk_start, stop))
            chunk_start = stop
    if end > chunk_start:
        chunks.append((chunk_start, end))

    # Trim whitespace introduced at the seams so `text` never starts or ends with a space.
    trimmed: list[tuple[int, int]] = []
    for c_start, c_end in chunks:
        while c_start < c_end and text[c_start].isspace():
            c_start += 1
        while c_end > c_start and text[c_end - 1].isspace():
            c_end -= 1
        if c_end > c_start:
            trimmed.append((c_start, c_end))
    return trimmed


def segment_doc(doc: CorpusDoc, *, min_score: float = DEFAULT_MIN_SCORE) -> list[Passage]:
    """Split every section of `doc` into scored passages, in reading order.

    Never raises on odd input: empty, whitespace-only or heading-only sections simply
    contribute no passages, because a corpus of 400 papers always contains a few that
    parsed badly and the run must not die on them.
    """
    passages: list[Passage] = []
    seen_names: Counter[str] = Counter()

    for section in doc.sections:
        occurrence = seen_names[section.name]
        seen_names[section.name] += 1
        text = section.text
        if not text or not text.strip():
            continue

        spans: list[tuple[int, int]] = []
        for span in _merge_short(_block_spans(text)):
            spans.extend(_split_long(text, span))

        index = 0
        for start, end in spans:
            chunk = text[start:end]
            if len(chunk) < MIN_KEEP_CHARS:
                continue
            score, signals = score_passage(chunk, section.name)
            passages.append(
                Passage(
                    passage_id=make_passage_id(doc.paper_id, section.name, occurrence, index),
                    paper_id=doc.paper_id,
                    doi=doc.doi,
                    section_name=section.name,
                    text=chunk,
                    char_start=start,
                    char_end=end,
                    is_synthesis=score >= min_score,
                    synthesis_score=score,
                    signals=signals,
                )
            )
            index += 1

    return passages


def load_corpus(path: Path) -> list[CorpusDoc]:
    """Read `corpus.jsonl` into `CorpusDoc` objects."""
    with path.open(encoding="utf-8") as fh:
        return [CorpusDoc(**json.loads(line)) for line in fh if line.strip()]


def segment_corpus(
    corpus: Path = CORPUS_DEFAULT,
    out: Path = OUT_DEFAULT,
    min_score: float = DEFAULT_MIN_SCORE,
    synthesis_only: bool = False,
) -> tuple[list[Passage], list[Passage]]:
    """Segment the whole corpus and write `out`.

    Returns `(segmented, written)`: every passage produced, and the subset written to
    disk. Both are returned because the run summary has to report the denominator (how
    much text was segmented) as well as the numerator, and `--synthesis-only` makes
    those two different numbers.
    """
    docs = load_corpus(corpus)
    logger.info("loaded {} papers from {}", len(docs), corpus)

    segmented: list[Passage] = []
    for doc in docs:
        segmented.extend(segment_doc(doc, min_score=min_score))

    written = [p for p in segmented if p.is_synthesis] if synthesis_only else segmented
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for p in written:
            fh.write(p.model_dump_json() + "\n")
    logger.info("wrote {} of {} passages -> {}", len(written), len(segmented), out)
    return segmented, written


@app.command()
def main(
    corpus: Path = typer.Option(CORPUS_DEFAULT, help="Input corpus JSONL."),
    out: Path = typer.Option(OUT_DEFAULT, help="Output passages JSONL."),
    min_score: float = typer.Option(
        DEFAULT_MIN_SCORE, help="Synthesis score at or above which a passage is is_synthesis."
    ),
    synthesis_only: bool = typer.Option(
        False,
        "--synthesis-only/--all-passages",
        help="Write only the passages classified as synthesis.",
    ),
) -> None:
    n_papers = sum(1 for line in corpus.open(encoding="utf-8") if line.strip())
    segmented, written = segment_corpus(
        corpus=corpus, out=out, min_score=min_score, synthesis_only=synthesis_only
    )
    if not segmented:
        typer.echo(f"papers in: {n_papers} | no passages produced -> {out}")
        return

    n_synth = sum(1 for p in segmented if p.is_synthesis)
    mean_len = sum(p.n_chars for p in segmented) / len(segmented)
    n_papers_with_synth = len({p.paper_id for p in segmented if p.is_synthesis})
    typer.echo(
        f"papers in: {n_papers} | passages out: {len(written)} "
        f"(of {len(segmented)} segmented) | synthesis: {n_synth} "
        f"({n_synth / len(segmented):.1%} of segmented, in {n_papers_with_synth} papers) | "
        f"mean passage length: {mean_len:.0f} chars | min-score: {min_score} -> {out}"
    )


if __name__ == "__main__":
    app()
