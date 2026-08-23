"""Gold-standard annotation logic, deliberately kept out of the Streamlit script.

Why this module exists as plain, importable Python:

1. A Streamlit script re-runs top to bottom on every widget interaction and cannot be
   imported by pytest without a server, so logic living there would be untestable in
   practice. The gold standard is the yardstick every accuracy number in this project is
   measured against, so its read and write path has to be covered by tests.
2. The evaluation code will later read `data/annotations/gold.jsonl` in an environment
   where Streamlit is not installed. Keeping the record format here makes that a plain
   import instead of a copy of the parsing rules.

RESEARCH INTEGRITY, non-negotiable: nothing in this package suggests, drafts or pre-fills
an annotation, and there is no model call anywhere in it. The gold standard is what LLM
output is judged against, so seeding it with model output would make the evaluation
circular and would invalidate every number in the report. The only automation offered is
mechanical text lookup: locating a string the annotator has already typed inside the
passage, so character spans and the verbatim evidence sentence do not have to be
transcribed by hand. That is a locator, not a judgement.

Storage format: one JSON record per *passage decision*, not per triple. A reviewed
passage that contains no synthesis content is itself a result (it is the negative case
that makes precision measurable), so it has to be recorded, and keying records on
`passage_id` is what makes an interrupted session resumable without duplicates.
"""

from __future__ import annotations

import json
import os
import random
import re
import tempfile
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, cast, get_args

from loguru import logger

from src.extraction.extractor_base import (
    Confidence,
    Entity,
    EntityType,
    RelationType,
    Triple,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PASSAGES_PATH = REPO_ROOT / "data" / "processed" / "passages.jsonl"
CORPUS_PATH = REPO_ROOT / "data" / "processed" / "corpus.jsonl"
GOLD_PATH = REPO_ROOT / "data" / "annotations" / "gold.jsonl"
ONTOLOGY_PATH = REPO_ROOT / "configs" / "ontology.json"

# Sample size agreed in the exposé. `remaining` counts down to the lower bound, because
# 150 is the point at which the evaluation is defensible and 200 is the stretch target.
TARGET_MIN = 150
TARGET_MAX = 200

# MENTIONED_IN is provenance, attached by the pipeline from the passage metadata. It is
# never hand annotated, so it is excluded from every UI dropdown and rejected by
# validate_triple: letting it be drawn by hand would double record provenance and would
# put an entity type on the left of an edge the loader already writes for every entity.
PROVENANCE_RELATION = "MENTIONED_IN"

# Fallback passage construction (used only when data/processed/passages.jsonl is absent).
SYNTHESIS_SECTION_KEYWORDS = (
    "synthesis",
    "experimental",
    "materials and methods",
    "method",
    "preparation",
    "syntheses",
)
# Short paragraphs are headings, table captions or single sentences such as "All reagents
# were used as received": they cannot carry a full synthesis record, and putting them in
# front of the annotator costs time without producing a triple.
MIN_PASSAGE_CHARS = 200
# Very long paragraphs are split at sentence boundaries rather than truncated. Truncation
# would silently hide part of a synthesis record from the annotator, which would show up
# later as a false "missed by the human" recall error.
MAX_PASSAGE_CHARS = 2500

SAMPLE_SEED = 2026  # fixed so the annotated sample is reproducible from the corpus alone

AnnotationStatus = Literal["annotated", "no_synthesis", "skipped"]
ANNOTATION_STATUSES: tuple[str, ...] = ("annotated", "no_synthesis", "skipped")

GOLD_EXTRACTOR_NAME = "human-gold"

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(\[])")


# --------------------------------------------------------------------------------------
# Ontology (configs/ontology.json is the source of truth)
# --------------------------------------------------------------------------------------
@lru_cache(maxsize=8)
def load_endpoints(ontology_path: Path = ONTOLOGY_PATH) -> dict[str, tuple[str, str]]:
    """Relation -> (legal subject type, legal object type), read from the ontology file.

    Read from `configs/ontology.json` rather than hard coded here so that the annotation
    tool cannot drift away from the schema the extractors and the KG loader use. The
    cross-check against the frozen Literals in `extraction/extractor_base.py` is
    deliberate: if the two ever disagree the tool fails loudly at start-up instead of
    quietly letting the student record hours of annotations against a dead schema.
    """
    data = json.loads(Path(ontology_path).read_text(encoding="utf-8"))
    entity_types = set(get_args(EntityType))
    relation_types = set(get_args(RelationType))
    endpoints: dict[str, tuple[str, str]] = {}
    for name, spec in data.get("relations", {}).items():
        if name == PROVENANCE_RELATION:
            continue
        if name not in relation_types:
            raise ValueError(f"ontology relation {name!r} is not in the frozen RelationType")
        subject_type, object_type = spec["from"], spec["to"]
        if subject_type not in entity_types or object_type not in entity_types:
            raise ValueError(f"ontology relation {name!r} uses an unknown entity type")
        endpoints[name] = (subject_type, object_type)
    missing = relation_types - {PROVENANCE_RELATION} - set(endpoints)
    if missing:
        raise ValueError(f"relations missing from the ontology file: {sorted(missing)}")
    return endpoints


def allowed_relations() -> tuple[str, ...]:
    """Relations a human may annotate, in ontology order. Excludes the provenance edge."""
    return tuple(load_endpoints())


def allowed_endpoints(relation: str) -> tuple[str, str]:
    """(subject type, object type) legal for `relation`. Raises on an unknown relation."""
    try:
        return load_endpoints()[relation]
    except KeyError:
        raise ValueError(
            f"unknown or non-annotatable relation {relation!r}; "
            f"choose one of {list(allowed_relations())}"
        ) from None


def allowed_subject_types(relation: str) -> tuple[str, ...]:
    """Subject types the UI may offer for `relation`.

    Returns a tuple even though v0.2 defines exactly one legal subject per relation, so
    the UI code stays correct if a later ontology version widens an endpoint.
    """
    return (allowed_endpoints(relation)[0],)


def allowed_object_types(relation: str) -> tuple[str, ...]:
    """Object types the UI may offer for `relation`. Tuple for the same reason as above."""
    return (allowed_endpoints(relation)[1],)


def validate_triple(subject_type: str, relation: str, object_type: str) -> bool:
    """True when this subject/relation/object combination is legal under the ontology.

    Returns a bool instead of raising because the UI calls it on every keystroke and a
    wrong selection is a normal thing for a human to do, not an exceptional one. The
    write path (`append_annotation`) raises on the same condition, so an invalid triple
    cannot reach the gold file even if a caller ignores this answer.
    """
    if relation == PROVENANCE_RELATION:
        return False
    endpoints = load_endpoints().get(relation)
    if endpoints is None:
        return False
    return (subject_type, object_type) == endpoints


def explain_invalid(subject_type: str, relation: str, object_type: str) -> str | None:
    """Human readable reason a combination is rejected, or None when it is legal."""
    if validate_triple(subject_type, relation, object_type):
        return None
    if relation == PROVENANCE_RELATION:
        return (
            f"{PROVENANCE_RELATION} is provenance and is attached automatically by the "
            "pipeline, so it is never annotated by hand."
        )
    if relation not in load_endpoints():
        return f"{relation!r} is not a relation in the ontology."
    want_subject, want_object = allowed_endpoints(relation)
    return (
        f"{relation} goes {want_subject} -> {want_object}, "
        f"not {subject_type or '?'} -> {object_type or '?'}."
    )


# --------------------------------------------------------------------------------------
# Passages
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Passage:
    """One unit of annotation: the text the annotator reads and judges as a whole."""

    passage_id: str
    paper_id: str
    section: str
    text: str
    title: str = ""
    doi: str | None = None
    source: str = "passages.jsonl"  # or "corpus-fallback", shown in the UI
    # Set by the passage builder's rule-based pre-filter, not by a model. Carried here so
    # the worklist can be stratified and so the report can state which pool each annotated
    # passage came from, which is what makes the sampling reproducible and auditable.
    is_synthesis: bool = True
    synthesis_score: float | None = None
    char_start: int | None = None
    char_end: int | None = None

    @property
    def n_chars(self) -> int:
        return len(self.text)


# The passages file is produced by a different module. Its exact key names are not frozen
# yet, so reading is tolerant of the obvious aliases: an annotation session must not be
# blocked by a key rename upstream.
_ID_KEYS = ("passage_id", "id", "pid")
_TEXT_KEYS = ("text", "passage", "body", "content")
_SECTION_KEYS = ("section", "section_name", "section_title")
_PAPER_KEYS = ("paper_id", "paper", "doc_id", "document_id")
_TITLE_KEYS = ("title", "paper_title")


def _first(record: dict[str, Any], keys: Sequence[str], default: str = "") -> str:
    for key in keys:
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return default


def slug(text: str) -> str:
    """Lowercase, punctuation free token used inside deterministic passage ids."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "section"


def split_sentences(text: str) -> list[str]:
    """Approximate sentence split, good enough to offer the annotator a starting point.

    Chemistry text breaks naive splitters (decimals, "et al.", "cf."), so this is not
    presented as ground truth anywhere: the annotator edits the evidence field freely and
    what is stored is whatever they confirmed.
    """
    return [s.strip() for s in _SENTENCE_SPLIT.split(text.strip()) if s.strip()]


def _chunk_paragraph(paragraph: str, max_chars: int = MAX_PASSAGE_CHARS) -> list[str]:
    """Split an over-long paragraph on sentence boundaries, losing no text."""
    if len(paragraph) <= max_chars:
        return [paragraph]
    chunks: list[str] = []
    current = ""
    for sentence in split_sentences(paragraph):
        candidate = f"{current} {sentence}".strip()
        if current and len(candidate) > max_chars:
            chunks.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def passages_from_corpus(
    corpus_path: Path | str = CORPUS_PATH,
    *,
    section_keywords: Sequence[str] = SYNTHESIS_SECTION_KEYWORDS,
    min_chars: int = MIN_PASSAGE_CHARS,
    max_chars: int = MAX_PASSAGE_CHARS,
) -> list[Passage]:
    """Derive annotation passages straight from the corpus.

    This is the documented fallback for `load_passages` when
    `data/processed/passages.jsonl` has not been built yet, so annotation is never
    blocked on another part of the pipeline. It takes the first synthesis-like section of
    each paper and splits it into paragraphs.

    Deliberately no keyword filtering of paragraphs: selecting only paragraphs that
    already mention "mmol" or "solvothermal" would stack the sample with easy positives
    and inflate every accuracy number measured against it. Order is deterministic (corpus
    order, then position in the section) so the same file always yields the same ids.
    """
    from src.ingestion.models import CorpusDoc  # local import: keeps core import-light

    corpus_path = Path(corpus_path)
    passages: list[Passage] = []
    with corpus_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            doc = CorpusDoc(**json.loads(line))
            section = doc.section(*section_keywords)
            if section is None:
                continue
            index = 0
            for paragraph in section.text.split("\n"):
                paragraph = paragraph.strip()
                if len(paragraph) < min_chars:
                    continue
                for chunk in _chunk_paragraph(paragraph, max_chars):
                    if len(chunk) < min_chars:
                        continue
                    passages.append(
                        Passage(
                            passage_id=f"{doc.paper_id}:{slug(section.name)}:{index:03d}",
                            paper_id=doc.paper_id,
                            section=section.name,
                            text=chunk,
                            title=doc.title,
                            doi=doc.doi,
                            source="corpus-fallback",
                            # The section keyword match is this path's equivalent of the
                            # passage builder's pre-filter, so these count as the
                            # synthesis pool. The fallback therefore has no control pool,
                            # which is one reason the real passages file is preferred.
                            is_synthesis=True,
                        )
                    )
                    index += 1
    return passages


def load_passages(
    passages_path: Path | str = PASSAGES_PATH,
    *,
    corpus_path: Path | str = CORPUS_PATH,
    limit: int | None = None,
) -> list[Passage]:
    """Load annotation passages, preferring the passages file and falling back to corpus.

    The fallback exists because the passages file is built by a separate module that may
    not have run yet; the annotator should never be blocked by that. `source` on each
    Passage records which path was taken, and the UI shows it, so a session is always
    traceable to the input it actually used.
    """
    passages_path = Path(passages_path)
    if passages_path.exists() and passages_path.stat().st_size > 0:
        passages = _read_passages_file(passages_path)
        if passages:
            return passages[:limit] if limit else passages
        logger.warning("{} exists but yielded no usable passages; using corpus", passages_path)
    return passages_from_corpus(corpus_path)[:limit] if limit else passages_from_corpus(corpus_path)


def _read_passages_file(path: Path) -> list[Passage]:
    passages: list[Passage] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("{}:{} is not valid JSON, skipped", path, line_no)
                continue
            text = _first(record, _TEXT_KEYS)
            if not text.strip():
                continue
            paper_id = _first(record, _PAPER_KEYS, default="unknown")
            passages.append(
                Passage(
                    passage_id=_first(record, _ID_KEYS, default=f"{paper_id}:{line_no:05d}"),
                    paper_id=paper_id,
                    section=_first(record, _SECTION_KEYS, default="unknown"),
                    text=text,
                    title=_first(record, _TITLE_KEYS),
                    doi=record.get("doi"),
                    source="passages.jsonl",
                    # Absent flag means "unclassified", and an unclassified passage is
                    # treated as in scope rather than dropped: losing a real synthesis
                    # passage costs more than showing the annotator one extra paragraph.
                    is_synthesis=bool(record.get("is_synthesis", True)),
                    synthesis_score=_as_float(record.get("synthesis_score")),
                    char_start=_as_int(record.get("char_start")),
                    char_end=_as_int(record.get("char_end")),
                )
            )
    return passages


def _as_float(value: Any) -> float | None:
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else None


def _as_int(value: Any) -> int | None:
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else None


def sample_passages(
    passages: Sequence[Passage], n: int = TARGET_MAX, *, seed: int = SAMPLE_SEED
) -> list[Passage]:
    """Reproducible random subset, so the annotated set is not the alphabetical first N.

    Annotating the first N passages would concentrate the gold standard in a handful of
    papers and would make the reported accuracy a property of those papers. A seeded
    sample spreads it and stays reproducible from the corpus plus this seed.
    """
    ordered = sorted(passages, key=lambda p: p.passage_id)
    if n >= len(ordered):
        return ordered
    picked = random.Random(seed).sample(range(len(ordered)), n)
    return [ordered[i] for i in sorted(picked)]


def build_worklist(
    passages: Sequence[Passage],
    *,
    n: int = TARGET_MAX,
    control_fraction: float = 0.1,
    seed: int = SAMPLE_SEED,
) -> list[Passage]:
    """The passages to annotate: a seeded sample, stratified by the synthesis pre-filter.

    Three research decisions are encoded here, and all three belong in the report:

    1. The bulk of the sample is drawn from passages the rule-based pre-filter flagged as
       synthesis text. Annotating a uniform sample of the whole corpus would spend most of
       the student's hours on introductions and reference lists, and the graded question
       is per-field accuracy on synthesis records.
    2. A `control_fraction` of the sample is drawn from *unflagged* passages anyway. Those
       are what make the pre-filter's own miss rate measurable; without them the reported
       recall would silently be conditional on a heuristic nobody validated.
    3. The two strata are interleaved by a seeded shuffle rather than annotated in blocks,
       so annotator fatigue and drift do not land entirely on one stratum.

    Everything is deterministic given `seed`, so the exact worklist can be regenerated
    from the corpus for a reproducibility check.
    """
    flagged = [p for p in passages if p.is_synthesis]
    control_pool = [p for p in passages if not p.is_synthesis]
    n_control = min(len(control_pool), round(n * control_fraction))
    selected = sample_passages(flagged, n - n_control, seed=seed)
    selected += sample_passages(control_pool, n_control, seed=seed + 1)
    random.Random(seed).shuffle(selected)
    return selected


def find_span(text: str, mention: str) -> tuple[int, int] | None:
    """Character offsets of `mention` in `text`, case-insensitive, or None.

    Mechanical lookup of a string the annotator typed. It never proposes what to
    annotate; it only saves the annotator from counting characters by hand.
    """
    if not mention.strip():
        return None
    lowered, needle = text.lower(), mention.strip().lower()
    start = lowered.find(needle)
    if start < 0:
        return None
    return (start, start + len(needle))


def sentence_containing(text: str, mention: str) -> str:
    """The verbatim sentence of `text` containing `mention` (empty string if not found).

    Used only to pre-fill the evidence box *after* the annotator has already decided and
    typed the entity, and the box stays editable. The returned string is source text, not
    generated text, which is what keeps the gold standard model-free.
    """
    span = find_span(text, mention)
    if span is None:
        return ""
    offset = 0
    for sentence in split_sentences(text):
        start = text.find(sentence, offset)
        if start < 0:
            continue
        offset = start + len(sentence)
        if start <= span[0] < offset:
            return sentence
    return text.strip()


# --------------------------------------------------------------------------------------
# Gold records
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class GoldTriple:
    """One human-annotated relation inside a passage.

    Names are stored as the surface form written in the passage. Canonicalisation is
    src/normalize.py's job at evaluation time, and doing it here would bake one
    normalisation version into a file that is meant to be frozen and re-used.
    """

    subject_type: str
    subject_name: str
    relation: str
    object_type: str
    object_name: str
    evidence: str
    subject_span: tuple[int, int] | None = None
    object_span: tuple[int, int] | None = None
    confidence: str = "high"
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject_type": self.subject_type,
            "subject_name": self.subject_name,
            "subject_span": list(self.subject_span) if self.subject_span else None,
            "relation": self.relation,
            "object_type": self.object_type,
            "object_name": self.object_name,
            "object_span": list(self.object_span) if self.object_span else None,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GoldTriple:
        def span(key: str) -> tuple[int, int] | None:
            value = data.get(key)
            if isinstance(value, list | tuple) and len(value) == 2:
                return (int(value[0]), int(value[1]))
            return None

        return cls(
            subject_type=str(data["subject_type"]),
            subject_name=str(data["subject_name"]),
            relation=str(data["relation"]),
            object_type=str(data["object_type"]),
            object_name=str(data["object_name"]),
            evidence=str(data.get("evidence", "")),
            subject_span=span("subject_span"),
            object_span=span("object_span"),
            confidence=str(data.get("confidence", "high")),
            note=str(data.get("note", "")),
        )

    def to_triple(
        self,
        *,
        paper_id: str,
        section: str,
        extractor: str = GOLD_EXTRACTOR_NAME,
    ) -> Triple:
        """Convert into the frozen `Triple` shape used by every extractor and the loader.

        The gold standard has to be comparable with predictions field by field, so it is
        converted into the same dataclass rather than into a parallel structure that the
        evaluation would have to special-case. The casts are safe because
        `append_annotation` validated the types against the ontology before writing.
        """
        return Triple(
            subject=Entity(
                type=cast(EntityType, self.subject_type),
                name=self.subject_name,
                span=self.subject_span,
            ),
            relation=cast(RelationType, self.relation),
            object=Entity(
                type=cast(EntityType, self.object_type),
                name=self.object_name,
                span=self.object_span,
            ),
            evidence=self.evidence,
            confidence=cast(Confidence, self.confidence),
            source_paper_id=paper_id,
            source_section=section,
            extractor=extractor,
        )


@dataclass(frozen=True)
class GoldRecord:
    """One reviewed passage: the annotator's complete decision about it.

    `passage_id` is the primary key. Re-saving a passage replaces its record instead of
    appending a second one, which is what makes an interrupted session resumable without
    the duplicates that would silently double-count a triple in the evaluation.
    """

    passage_id: str
    paper_id: str
    section: str
    status: str = "annotated"
    triples: list[GoldTriple] = field(default_factory=list)
    annotator: str = "human"
    annotated_at: str = ""
    note: str = ""
    passage_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "passage_id": self.passage_id,
            "paper_id": self.paper_id,
            "section": self.section,
            "status": self.status,
            "triples": [t.to_dict() for t in self.triples],
            "annotator": self.annotator,
            "annotated_at": self.annotated_at,
            "note": self.note,
            "passage_text": self.passage_text,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GoldRecord:
        return cls(
            passage_id=str(data["passage_id"]),
            paper_id=str(data.get("paper_id", "")),
            section=str(data.get("section", "")),
            status=str(data.get("status", "annotated")),
            triples=[GoldTriple.from_dict(t) for t in data.get("triples", [])],
            annotator=str(data.get("annotator", "human")),
            annotated_at=str(data.get("annotated_at", "")),
            note=str(data.get("note", "")),
            passage_text=str(data.get("passage_text", "")),
        )

    def to_triples(self, *, extractor: str = GOLD_EXTRACTOR_NAME) -> list[Triple]:
        """All triples of this record in the frozen `Triple` shape, provenance attached."""
        return [
            t.to_triple(paper_id=self.paper_id, section=self.section, extractor=extractor)
            for t in self.triples
        ]


def iter_gold_triples(
    records: Iterable[GoldRecord], *, extractor: str = GOLD_EXTRACTOR_NAME
) -> Iterator[tuple[str, Triple]]:
    """Yield (passage_id, Triple) pairs.

    `Triple` is a frozen contract with no passage field and must not be edited, so the
    passage id travels alongside the triple rather than inside it. Evaluation needs the
    pairing to score per passage; the KG loader only needs the Triple.
    """
    for record in records:
        for triple in record.to_triples(extractor=extractor):
            yield record.passage_id, triple


# --------------------------------------------------------------------------------------
# Persistence
# --------------------------------------------------------------------------------------
def load_gold(path: Path | str = GOLD_PATH) -> list[GoldRecord]:
    """Read gold.jsonl in file order. Unreadable lines are skipped with a warning.

    Skipping rather than raising is the resume-safe choice: if a crash ever leaves a torn
    final line, the annotator must still be able to open the tool and continue, and the
    session's earlier work must still load. Every skip is logged so nothing is lost
    silently.
    """
    path = Path(path)
    if not path.exists():
        return []
    records: list[GoldRecord] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(GoldRecord.from_dict(json.loads(line)))
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                logger.warning("{}:{} skipped, not a readable gold record: {}", path, line_no, exc)
    return records


def annotated_passage_ids(path: Path | str = GOLD_PATH) -> set[str]:
    """Passage ids already decided, for resuming where the previous session stopped."""
    return {r.passage_id for r in load_gold(path)}


def _write_all(path: Path, records: Sequence[GoldRecord]) -> None:
    """Rewrite the whole gold file atomically.

    data/annotations/ is the one committed data directory and it holds work that cannot
    be regenerated: hours of human judgement. So the file is written to a temporary file
    in the same directory, flushed, fsynced, and moved into place with os.replace, which
    is atomic on POSIX. A crash therefore leaves either the old complete file or the new
    complete file, never a half-written one. Rewriting everything (rather than appending)
    is what allows a passage to be corrected in place, and at 150 to 200 records the cost
    is irrelevant.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".gold-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def _validate_for_write(triple: GoldTriple) -> None:
    if not validate_triple(triple.subject_type, triple.relation, triple.object_type):
        raise ValueError(
            explain_invalid(triple.subject_type, triple.relation, triple.object_type)
            or "invalid triple"
        )
    if not triple.subject_name.strip() or not triple.object_name.strip():
        raise ValueError("subject and object names are required")
    if not triple.evidence.strip():
        raise ValueError("evidence sentence is required: provenance is mandatory")
    if triple.confidence not in get_args(Confidence):
        raise ValueError(f"confidence must be one of {list(get_args(Confidence))}")


def append_annotation(
    passage_id: str,
    paper_id: str,
    section: str,
    triples: Sequence[GoldTriple] = (),
    *,
    status: str = "annotated",
    note: str = "",
    annotator: str | None = None,
    passage_text: str = "",
    path: Path | str = GOLD_PATH,
) -> GoldRecord:
    """Record the annotator's decision about one passage and persist it immediately.

    Upsert, not blind append: a record for `passage_id` replaces any earlier record for
    the same passage. That is what keeps "add a second triple", "fix a typo" and "resume
    after a crash" from producing duplicate gold entries, which would quietly inflate or
    deflate every score computed from this file.

    Raises ValueError on an invalid triple. Unlike an extractor (which must never raise),
    this is a human-facing write path: refusing the write and telling the annotator why
    is strictly better than storing something the ontology forbids.
    """
    passage_id = passage_id.strip()
    if not passage_id:
        raise ValueError("passage_id is required: it is the key that makes resume work")
    if status not in ANNOTATION_STATUSES:
        raise ValueError(f"status must be one of {list(ANNOTATION_STATUSES)}")
    if status != "annotated" and triples:
        raise ValueError(f"status {status!r} cannot carry triples")
    if status == "annotated" and not triples:
        raise ValueError(
            "an 'annotated' record needs at least one triple; use status='no_synthesis' "
            "for a reviewed passage that contains none"
        )
    for triple in triples:
        _validate_for_write(triple)

    record = GoldRecord(
        passage_id=passage_id,
        paper_id=paper_id,
        section=section,
        status=status,
        triples=list(triples),
        annotator=annotator or os.environ.get("GOLD_ANNOTATOR", "human"),
        annotated_at=datetime.now(UTC).isoformat(timespec="seconds"),
        note=note,
        passage_text=passage_text,
    )

    path = Path(path)
    existing = load_gold(path)
    replaced = False
    merged: list[GoldRecord] = []
    for previous in existing:
        if previous.passage_id == passage_id:
            if not replaced:
                merged.append(record)
                replaced = True
            continue  # drops any duplicate left by an older tool version
        merged.append(previous)
    if not replaced:
        merged.append(record)
    _write_all(path, merged)
    return record


def delete_annotation(passage_id: str, path: Path | str = GOLD_PATH) -> bool:
    """Remove the record for `passage_id`, returning True if one was there.

    Needed because "I recorded that triple by mistake" must leave the passage genuinely
    undecided, not leave behind an empty record that would later be counted as a reviewed
    negative and would distort precision.
    """
    path = Path(path)
    records = load_gold(path)
    kept = [r for r in records if r.passage_id != passage_id]
    if len(kept) == len(records):
        return False
    _write_all(path, kept)
    return True


# --------------------------------------------------------------------------------------
# Progress
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class ProgressStats:
    """Counts shown in the UI header, and the numbers quoted in the report."""

    reviewed: int
    annotated: int
    no_synthesis: int
    skipped: int
    triples: int
    target_min: int = TARGET_MIN
    target_max: int = TARGET_MAX

    @property
    def remaining(self) -> int:
        """Passages still needed to reach the lower bound of the target range."""
        return max(0, self.target_min - self.annotated)

    @property
    def target_range(self) -> tuple[int, int]:
        return (self.target_min, self.target_max)

    @property
    def is_complete(self) -> bool:
        return self.annotated >= self.target_min

    @property
    def fraction_of_target(self) -> float:
        return min(1.0, self.annotated / self.target_min) if self.target_min else 1.0


def progress_stats(path: Path | str = GOLD_PATH) -> ProgressStats:
    """Progress against the 150 to 200 passage target.

    `annotated` counts passages that yielded at least one triple, because that is the
    quantity the exposé committed to. Reviewed-but-empty passages are counted separately:
    they are real work and they are needed as negatives when precision is measured, but
    they are not what the target range refers to.
    """
    records = load_gold(path)
    annotated = sum(1 for r in records if r.status == "annotated")
    return ProgressStats(
        reviewed=len(records),
        annotated=annotated,
        no_synthesis=sum(1 for r in records if r.status == "no_synthesis"),
        skipped=sum(1 for r in records if r.status == "skipped"),
        triples=sum(len(r.triples) for r in records),
    )


def pending_passages(passages: Sequence[Passage], path: Path | str = GOLD_PATH) -> list[Passage]:
    """Passages with no decision yet, in input order. Skipped ones count as pending."""
    decided = {r.passage_id for r in load_gold(path) if r.status != "skipped"}
    return [p for p in passages if p.passage_id not in decided]
