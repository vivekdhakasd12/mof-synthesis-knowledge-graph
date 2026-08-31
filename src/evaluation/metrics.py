"""Per-field extraction metrics and reference-database agreement.

This module produces the numbers the project is graded on, so every scoring decision
here is deliberate and written down. The guiding principle throughout: when a choice
could plausibly go either way, take the option that cannot silently inflate a score.
An understated result is a defensible result; an overstated one is worthless.

The five decisions worth defending in the report
------------------------------------------------

1. A "field" is a RelationType. The research question is per-field accuracy (does the
   model get the linker right, the solvent, the temperature), so precision, recall and
   F1 are computed separately per relation and only then aggregated. MENTIONED_IN is
   never scored: it is provenance attached by the pipeline, not something an extractor
   produces, so counting it would add a large block of free true positives to every
   run. See SCORED_RELATIONS.

2. Matching runs inside a passage, never across passages. Two triples can only be
   compared when they carry the same (source_paper_id, source_section). Matching a
   prediction about paper A against gold from paper B would be a leak that quietly
   raises recall, and it is exactly the sort of thing a grader is entitled to check.

3. Identity comes from src/normalize.py, the same module the Neo4j loader keys nodes
   on. If evaluation and the graph disagreed about whether "H3BTC" is "trimesic acid",
   the reported accuracy and the delivered artefact would describe different worlds.
   This module therefore imports normalize_by_type and never defines its own
   normalisation of a chemical name.

4. Relaxed matching relaxes orthography only, never chemistry. It compares sets of
   whole tokens after normalisation. It does NOT use character-level string similarity,
   because in this domain character similarity is actively dangerous: "methanol" and
   "ethanol" are 93 percent similar as strings and are different solvents, as are
   nitrate and nitrite, UiO-66 and UiO-67, MIL-100 and MIL-101. On top of that, two
   names whose digit content differs can never match in relaxed mode (the numeric
   guard), because in MOF text the digits carry the material identity and the
   measurement magnitude. The cost of this conservatism is that a formula written
   against its trivial name ("Ni(NO3)2" versus "nickel nitrate") only matches when the
   shared synonym table covers it. That direction of error understates our accuracy,
   which is the direction this project can afford.

5. Assignment between predictions and gold is one-to-one and greedy. Without it, five
   copies of one correct prediction would each match the same gold triple and precision
   would be reported as 1.0 for a duplicate-spewing extractor. Greedy assignment over
   candidate pairs sorted by descending similarity is not guaranteed to find the
   maximum-cardinality matching, but it can only find the same number of matches or
   fewer than the optimum, so it can only understate the score, never inflate it. Ties
   are broken deterministically by (gold index, prediction index) so a rerun reproduces
   the same numbers.

Nothing here prints. Everything is returned as a dataclass so the report, the
dashboard and the tests read the same objects.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

# pandas-stubs is not a project dependency, so mypy cannot type the import. The
# DataFrame is only a presentation convenience for the report tables; nothing in the
# scoring path depends on it.
import pandas as pd  # type: ignore[import-untyped]

from src.extraction.extractor_base import Entity, RelationType, Triple
from src.normalize import normalize_by_type

MatchMode = Literal["exact", "relaxed"]

#: The eight relations an extractor is scored on. MENTIONED_IN is deliberately absent:
#: it is provenance written by the pipeline for every entity, so scoring it would hand
#: every extractor a large block of free true positives and make the headline numbers
#: incomparable with any per-field claim in the report.
SCORED_RELATIONS: tuple[RelationType, ...] = (
    "USES_PRECURSOR",
    "USES_LINKER",
    "SYNTHESIZED_BY",
    "IN_SOLVENT",
    "AT_CONDITION",
    "HAS_PROPERTY",
    "MEASURED_AT",
    "USED_IN",
)

#: Default Jaccard threshold for relaxed matching.
#:
#: Chosen so that a qualifier or parenthetical variant still matches while a genuinely
#: different quantity does not. Two names sharing two of three tokens score 0.667 and
#: match ("MIL-101(Cr)" versus "MIL-101", "ZIF-8 nanoparticles" versus "ZIF-8"). Two
#: three-token names sharing only the head noun score 0.5 and do not match ("BET surface
#: area" versus "Langmuir surface area"), which is correct because those are different
#: measurements. 0.6 is the largest threshold that keeps the first family and the
#: smallest that rejects the second.
# Relations scored on the object alone, ignoring the identity of the subject.
#
# This is a declared evaluation decision, not a convenience, and the methodology chapter
# must state it. The ontology routes solvents and conditions through a synthesis method
# (SynthesisMethod -[IN_SOLVENT]-> Solvent), so the subject of those two relations is a
# connector rather than a claim: what the extraction is actually asserting is "this
# synthesis used DMF at 120 C". Within a single passage there is normally one synthesis, so
# the connector carries no information that the passage boundary does not already carry.
#
# The concrete reason it is switched on here: the annotation tool had a bug in which a text
# field kept its previous value when the relation changed, so the gold standard records the
# MOF's name in the subject of every IN_SOLVENT and AT_CONDITION triple (68 of the first 138
# triples). Scoring those subjects literally would mark a model WRONG for correctly
# answering "solvothermal", inverting the result on two of the four relations that have
# usable support. Ignoring the subject for exactly these two relations removes that
# artefact without inventing any gold data.
#
# Cost, stated plainly: this evaluation cannot show whether a model attaches a solvent to
# the right synthesis when a passage describes more than one. SYNTHESIZED_BY, which would
# have tested method identification directly, has a support of 1 and is unusable anyway.
SUBJECT_AGNOSTIC_RELATIONS: frozenset[str] = frozenset({"IN_SOLVENT", "AT_CONDITION"})

RELAXED_THRESHOLD: float = 0.6

#: Generic process nouns dropped before relaxed token comparison. These carry no
#: chemical content ("solvothermal" and "solvothermal synthesis" are the same method),
#: and the list is kept short and explicit so a reader can audit it. Chemical words are
#: never dropped. This applies to relaxed mode only; exact mode compares the shared
#: normaliser's output verbatim.
RELAXED_STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "the",
        "of",
        "synthesis",
        "synthesised",
        "synthesized",
        "method",
        "route",
        "process",
        "approach",
        "technique",
    }
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")

#: Values that mean "this cell was never filled in" in a reference-database export.
#: Configurable per call; see agreement_report.
NULL_TOKENS: frozenset[str] = frozenset(
    {"", "na", "n/a", "none", "null", "nan", "-", "--", "unknown", "not reported"}
)

ONTOLOGY_PATH = Path(__file__).resolve().parents[2] / "configs" / "ontology.json"

#: Fallback entity type for record fields whose ontology type the caller did not give.
#: normalize_by_type routes anything that is not MOF or Condition to normalize_chemical,
#: which is the right default for a reagent name.
_FALLBACK_TYPE = "Chemical"

#: Field name to ontology entity type for the DigiMOF/SynMOF agreement analysis.
#: TODO(pre-agreement-run): the mapping from these names onto the actual DigiMOF and
#: SynMOF column headers is still an open question in configs/ontology.json and must be
#: fixed, and recorded in the report, before any agreement number is quoted. Callers
#: pass their own mapping until then; this default only fixes the normalisation type.
DEFAULT_FIELD_TYPES: dict[str, str] = {
    "mof": "MOF",
    "metal_precursor": "MetalPrecursor",
    "linker": "OrganicLinker",
    "solvent": "Solvent",
    "synthesis_method": "SynthesisMethod",
    "temperature": "Condition",
    "time": "Condition",
}


# --------------------------------------------------------------------------------------
# name and triple matching
# --------------------------------------------------------------------------------------


def _tokens(normalised: str) -> frozenset[str]:
    """Alphanumeric tokens of an already normalised name, minus generic process nouns.

    Tokenising on non-alphanumeric characters rather than whitespace means hyphenation
    differences ("room-temperature stirring" versus "room temperature stirring") cost
    nothing, which is a presentation difference and not a chemical one.
    """
    toks = frozenset(_TOKEN_RE.findall(normalised))
    stripped = toks - RELAXED_STOPWORDS
    # Never strip a name down to nothing; if the whole name is generic, keep it as is.
    return stripped or toks


def _numbers(normalised: str) -> tuple[str, ...]:
    """Every digit run in a normalised name, sorted, as the numeric fingerprint.

    Used as a hard guard in relaxed mode: UiO-66 and UiO-67, 120 c and 150 c, MIL-100
    and MIL-101 differ only in a digit, and are different materials or different
    measurements. No amount of token overlap may override that.
    """
    return tuple(sorted(_NUMBER_RE.findall(normalised)))


def normalised_name(entity: Entity) -> str:
    """Canonical name of an entity, via the shared normaliser (never a local copy)."""
    return normalize_by_type(entity.type, entity.name)


def name_similarity(
    entity_type: str,
    left: str,
    right: str,
    *,
    mode: MatchMode = "exact",
    threshold: float = RELAXED_THRESHOLD,
) -> float:
    """Similarity of two entity names in [0, 1]; 0.0 means "not the same entity".

    Exact mode is equality of the shared normaliser's output. Relaxed mode adds token
    set overlap (Jaccard) above `threshold`, guarded by the numeric fingerprint. See the
    module docstring for why character-level fuzziness is refused outright.
    """
    a = normalize_by_type(entity_type, left)
    b = normalize_by_type(entity_type, right)
    if a and a == b:
        return 1.0
    if mode == "exact" or not a or not b:
        return 0.0
    if _numbers(a) != _numbers(b):
        return 0.0
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    jaccard = len(ta & tb) / len(ta | tb)
    return jaccard if jaccard >= threshold else 0.0


def entity_similarity(
    left: Entity,
    right: Entity,
    *,
    mode: MatchMode = "exact",
    threshold: float = RELAXED_THRESHOLD,
) -> float:
    """Similarity of two entities. Entity types must be identical in both modes.

    Types come from a closed nine-item vocabulary, so there is nothing to be fuzzy
    about: a prediction that calls a solvent an organic linker has made a schema error,
    and relaxed matching exists to forgive spelling, not schema.
    """
    if left.type != right.type:
        return 0.0
    return name_similarity(left.type, left.name, right.name, mode=mode, threshold=threshold)


def triple_similarity(
    predicted: Triple,
    gold: Triple,
    *,
    mode: MatchMode = "exact",
    threshold: float = RELAXED_THRESHOLD,
    subject_agnostic: frozenset[str] = SUBJECT_AGNOSTIC_RELATIONS,
) -> float:
    """Similarity of a predicted triple to a gold triple; 0.0 means no match.

    All three positions must agree: the relation exactly (closed vocabulary), and the
    subject and object each independently under the active matching mode. The returned
    score is the mean of the two entity scores and is used only to rank candidate pairs
    during assignment, never as partial credit: scoring is binary, a pair either counts
    as a true positive or it does not.
    """
    if predicted.relation != gold.relation:
        return 0.0
    if predicted.relation in subject_agnostic:
        # Object-only scoring: see SUBJECT_AGNOSTIC_RELATIONS for the reasoning. The subject
        # is treated as satisfied so that assignment ranks on the object alone.
        obj_only = entity_similarity(predicted.object, gold.object, mode=mode, threshold=threshold)
        return obj_only
    subj = entity_similarity(predicted.subject, gold.subject, mode=mode, threshold=threshold)
    if subj == 0.0:
        return 0.0
    obj = entity_similarity(predicted.object, gold.object, mode=mode, threshold=threshold)
    if obj == 0.0:
        return 0.0
    return (subj + obj) / 2.0


@dataclass(frozen=True)
class MatchedPair:
    """A predicted triple credited against a gold triple, keeping both originals.

    Both sides are retained rather than a boolean, because the error taxonomy in the
    report needs the actual strings ("we said 24 h, the annotator said 24 d").
    """

    predicted: Triple
    gold: Triple
    score: float


def greedy_one_to_one(
    predicted: Sequence[Triple],
    gold: Sequence[Triple],
    *,
    mode: MatchMode = "exact",
    threshold: float = RELAXED_THRESHOLD,
    subject_agnostic: frozenset[str] = SUBJECT_AGNOSTIC_RELATIONS,
) -> tuple[list[MatchedPair], list[Triple], list[Triple]]:
    """Assign predictions to gold triples one-to-one; return (matches, unmatched pred,
    unmatched gold).

    Candidate pairs are sorted by descending similarity and consumed greedily, each
    prediction and each gold triple being usable once. The one-to-one constraint is the
    point: it stops a duplicate-emitting extractor from matching one gold triple five
    times and reporting perfect precision. Ties sort by (gold index, prediction index)
    so the assignment, and therefore every reported number, is reproducible.
    """
    candidates: list[tuple[float, int, int]] = []
    for pi, pred in enumerate(predicted):
        for gi, ref in enumerate(gold):
            score = triple_similarity(
                pred, ref, mode=mode, threshold=threshold, subject_agnostic=subject_agnostic
            )
            if score > 0.0:
                candidates.append((-score, gi, pi))
    candidates.sort()

    used_pred: set[int] = set()
    used_gold: set[int] = set()
    matches: list[MatchedPair] = []
    for neg_score, gi, pi in candidates:
        if pi in used_pred or gi in used_gold:
            continue
        used_pred.add(pi)
        used_gold.add(gi)
        matches.append(MatchedPair(predicted=predicted[pi], gold=gold[gi], score=-neg_score))

    false_positives = [t for i, t in enumerate(predicted) if i not in used_pred]
    false_negatives = [t for i, t in enumerate(gold) if i not in used_gold]
    return matches, false_positives, false_negatives


# --------------------------------------------------------------------------------------
# result containers
# --------------------------------------------------------------------------------------


def precision_recall_f1(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    """Precision, recall and F1 with every zero denominator defined as 0.0.

    The sklearn zero_division=0 convention, chosen for the same reason: an extractor
    that predicts nothing must score 0.0, not an undefined or vacuously perfect 1.0.
    """
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


@dataclass(frozen=True)
class FieldScore:
    """Scores for one field (one RelationType), or for the micro aggregate."""

    relation: str
    tp: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1: float

    @property
    def support(self) -> int:
        """Gold triples for this field. Support is a property of the gold standard, so
        it is tp + fn and never involves the predictions."""
        return self.tp + self.fn

    @property
    def n_predicted(self) -> int:
        return self.tp + self.fp

    def as_dict(self) -> dict[str, Any]:
        return {
            "relation": self.relation,
            "tp": self.tp,
            "fp": self.fp,
            "fn": self.fn,
            "support": self.support,
            "n_predicted": self.n_predicted,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
        }


@dataclass
class FieldErrors:
    """The actual triples behind one field's counts, for the report's error taxonomy.

    Counts alone cannot tell a hallucinated reagent from a unit error from a missed
    coreference, and the report has to name real examples, so the offending objects are
    kept rather than summarised.
    """

    relation: str
    true_positives: list[MatchedPair] = field(default_factory=list)
    false_positives: list[Triple] = field(default_factory=list)
    false_negatives: list[Triple] = field(default_factory=list)
    value_mismatches: list[tuple[Triple, Triple]] = field(default_factory=list)

    def as_dict(self, limit: int | None = None) -> dict[str, Any]:
        """Plain-data view for logging. `limit` truncates the example lists only."""

        def cut(seq: list[Any]) -> list[Any]:
            return seq if limit is None else seq[:limit]

        return {
            "relation": self.relation,
            "true_positives": [
                {"predicted": m.predicted.to_dict(), "gold": m.gold.to_dict(), "score": m.score}
                for m in cut(self.true_positives)
            ],
            "false_positives": [t.to_dict() for t in cut(self.false_positives)],
            "false_negatives": [t.to_dict() for t in cut(self.false_negatives)],
            "value_mismatches": [
                {"predicted": p.to_dict(), "gold": g.to_dict()}
                for p, g in cut(self.value_mismatches)
            ],
        }


@dataclass
class EvaluationResult:
    """Everything one evaluation run produced. Structured data only, no printing."""

    mode: MatchMode
    threshold: float
    n_passages: int
    per_field: dict[str, FieldScore]
    micro: FieldScore
    macro_precision: float
    macro_recall: float
    macro_f1: float
    macro_fields: tuple[str, ...]
    errors: dict[str, FieldErrors]
    skipped_relations: dict[str, int] = field(default_factory=dict)
    schema_violations: list[Triple] = field(default_factory=list)
    # Relations that were scored on the object alone. Carried on the result so that any
    # table generated from it can state the concession rather than quietly benefit from it.
    subject_agnostic_relations: tuple[str, ...] = ()

    def to_frame(self) -> pd.DataFrame:
        """Per-field table plus micro and macro rows, in the report's column order."""
        rows = [self.per_field[rel].as_dict() for rel in self.per_field]
        rows.append(self.micro.as_dict())
        rows.append(
            {
                "relation": "macro",
                "tp": self.micro.tp,
                "fp": self.micro.fp,
                "fn": self.micro.fn,
                "support": self.micro.support,
                "n_predicted": self.micro.n_predicted,
                "precision": self.macro_precision,
                "recall": self.macro_recall,
                "f1": self.macro_f1,
            }
        )
        return pd.DataFrame(
            rows,
            columns=[
                "relation",
                "support",
                "n_predicted",
                "tp",
                "fp",
                "fn",
                "precision",
                "recall",
                "f1",
            ],
        )

    def as_dict(self, error_limit: int | None = 20) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "threshold": self.threshold,
            "n_passages": self.n_passages,
            "per_field": {rel: score.as_dict() for rel, score in self.per_field.items()},
            "micro": self.micro.as_dict(),
            "macro": {
                "precision": self.macro_precision,
                "recall": self.macro_recall,
                "f1": self.macro_f1,
                "fields": list(self.macro_fields),
            },
            "skipped_relations": dict(self.skipped_relations),
            "schema_violations": [t.to_dict() for t in self.schema_violations[: error_limit or 0]],
            "errors": {rel: err.as_dict(error_limit) for rel, err in self.errors.items()},
        }


# --------------------------------------------------------------------------------------
# schema checking against the ontology
# --------------------------------------------------------------------------------------


@lru_cache(maxsize=4)
def relation_endpoints(path: str = str(ONTOLOGY_PATH)) -> dict[str, tuple[str, str]]:
    """Allowed (subject type, object type) per relation, read from configs/ontology.json.

    Read from the file rather than restated here, because the ontology is the declared
    source of truth and a second copy in code would drift from it, exactly as the
    EntityType literals once did. If the file cannot be read the mapping is empty and
    schema checking is skipped rather than guessed at.
    """
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    out: dict[str, tuple[str, str]] = {}
    for rel, spec in data.get("relations", {}).items():
        src, dst = spec.get("from"), spec.get("to")
        if isinstance(src, str) and isinstance(dst, str):
            out[rel] = (src, dst)
    return out


def schema_violations(triples: Iterable[Triple]) -> list[Triple]:
    """Triples whose entity types do not match the ontology endpoints for their relation.

    Reported separately from precision and recall. They are already counted as false
    positives (they cannot match any gold triple, since entity types must agree), and
    the separate list exists so the report can quantify schema violation as its own
    failure mode rather than lumping it in with wrong values.
    """
    endpoints = relation_endpoints()
    if not endpoints:
        return []
    bad: list[Triple] = []
    for t in triples:
        allowed = endpoints.get(t.relation)
        if allowed is None:
            continue
        src, dst = allowed
        if src == "*":
            continue
        if t.subject.type != src or t.object.type != dst:
            bad.append(t)
    return bad


# --------------------------------------------------------------------------------------
# evaluation
# --------------------------------------------------------------------------------------


def passage_key(triple: Triple) -> tuple[str | None, str | None]:
    """The unit within which predictions may be compared to gold: paper plus section.

    Triples that carry no provenance all land in a single group. That is fine for unit
    tests, but a real run must set source_paper_id and source_section, because grouping
    is the only thing stopping a prediction about one paper from being credited against
    another paper's gold annotation.
    """
    return (triple.source_paper_id, triple.source_section)


def _group(
    triples: Iterable[Triple],
    key: Callable[[Triple], tuple[str | None, str | None]],
) -> dict[tuple[tuple[str | None, str | None], str], list[Triple]]:
    grouped: dict[tuple[tuple[str | None, str | None], str], list[Triple]] = {}
    for t in triples:
        grouped.setdefault((key(t), t.relation), []).append(t)
    return grouped


def _value_mismatches(
    false_positives: Sequence[Triple],
    false_negatives: Sequence[Triple],
    *,
    mode: MatchMode,
    threshold: float,
) -> list[tuple[Triple, Triple]]:
    """Unmatched pairs that agree on subject and relation but not on the object.

    A diagnostic view, not a scoring category: these pairs are already counted once as a
    false positive and once as a false negative, and are listed again here only so the
    report can separate "wrong value for a fact that exists" (unit slips, hallucinated
    magnitudes) from "invented a fact that is not in the text".
    """
    pairs: list[tuple[Triple, Triple]] = []
    used: set[int] = set()
    for fp in false_positives:
        for i, fn in enumerate(false_negatives):
            if i in used:
                continue
            if fp.relation != fn.relation:
                continue
            if entity_similarity(fp.subject, fn.subject, mode=mode, threshold=threshold) > 0.0:
                used.add(i)
                pairs.append((fp, fn))
                break
    return pairs


def evaluate(
    predicted: Iterable[Triple],
    gold: Iterable[Triple],
    *,
    mode: MatchMode = "exact",
    threshold: float = RELAXED_THRESHOLD,
    relations: Sequence[str] = SCORED_RELATIONS,
    key: Callable[[Triple], tuple[str | None, str | None]] = passage_key,
    subject_agnostic: frozenset[str] = SUBJECT_AGNOSTIC_RELATIONS,
) -> EvaluationResult:
    """Score predicted triples against gold triples, per field and in aggregate.

    Matching happens per (passage, relation) group with one-to-one greedy assignment,
    so no prediction can be credited outside its own passage and no gold triple can be
    matched twice.

    Aggregation: micro sums tp, fp and fn over all fields and then computes the metrics,
    so it is dominated by frequent fields and counts every hallucination, including
    hallucinations in fields the gold standard never exercises. Macro averages the
    per-field metrics unweighted over the fields with non-zero gold support, which is
    the standard convention and the only one that is well defined (recall of a field
    with no gold triples is 0/0). Fields excluded from the macro average are still
    present in per_field and still counted in micro, so a field where the extractor only
    ever hallucinates cannot hide: macro_fields records exactly which fields were
    averaged.
    """
    scored = set(relations)
    pred_list = list(predicted)
    gold_list = list(gold)

    skipped: dict[str, int] = {}
    for t in pred_list + gold_list:
        if t.relation not in scored:
            skipped[t.relation] = skipped.get(t.relation, 0) + 1

    pred_scored = [t for t in pred_list if t.relation in scored]
    gold_scored = [t for t in gold_list if t.relation in scored]

    pred_groups = _group(pred_scored, key)
    gold_groups = _group(gold_scored, key)

    per_field: dict[str, FieldScore] = {}
    errors: dict[str, FieldErrors] = {rel: FieldErrors(relation=rel) for rel in relations}
    counts: dict[str, list[int]] = {rel: [0, 0, 0] for rel in relations}

    group_keys = sorted(
        {k for k, _ in pred_groups} | {k for k, _ in gold_groups},
        key=lambda k: (str(k[0]), str(k[1])),
    )
    for pkey in group_keys:
        for rel in relations:
            preds = pred_groups.get((pkey, rel), [])
            golds = gold_groups.get((pkey, rel), [])
            if not preds and not golds:
                continue
            matches, fps, fns = greedy_one_to_one(
                preds, golds, mode=mode, threshold=threshold, subject_agnostic=subject_agnostic
            )
            counts[rel][0] += len(matches)
            counts[rel][1] += len(fps)
            counts[rel][2] += len(fns)
            bucket = errors[rel]
            bucket.true_positives.extend(matches)
            bucket.false_positives.extend(fps)
            bucket.false_negatives.extend(fns)
            bucket.value_mismatches.extend(
                _value_mismatches(fps, fns, mode=mode, threshold=threshold)
            )

    for rel in relations:
        tp, fp, fn = counts[rel]
        precision, recall, f1 = precision_recall_f1(tp, fp, fn)
        per_field[rel] = FieldScore(
            relation=rel, tp=tp, fp=fp, fn=fn, precision=precision, recall=recall, f1=f1
        )

    total_tp = sum(s.tp for s in per_field.values())
    total_fp = sum(s.fp for s in per_field.values())
    total_fn = sum(s.fn for s in per_field.values())
    micro_p, micro_r, micro_f1 = precision_recall_f1(total_tp, total_fp, total_fn)
    micro = FieldScore(
        relation="micro",
        tp=total_tp,
        fp=total_fp,
        fn=total_fn,
        precision=micro_p,
        recall=micro_r,
        f1=micro_f1,
    )

    macro_fields = tuple(rel for rel in relations if per_field[rel].support > 0)
    if macro_fields:
        n = len(macro_fields)
        macro_p = sum(per_field[r].precision for r in macro_fields) / n
        macro_r = sum(per_field[r].recall for r in macro_fields) / n
        macro_f1 = sum(per_field[r].f1 for r in macro_fields) / n
    else:
        macro_p = macro_r = macro_f1 = 0.0

    n_passages = len({key(t) for t in pred_scored} | {key(t) for t in gold_scored})

    return EvaluationResult(
        mode=mode,
        threshold=threshold,
        n_passages=n_passages,
        per_field=per_field,
        micro=micro,
        macro_precision=macro_p,
        macro_recall=macro_r,
        macro_f1=macro_f1,
        macro_fields=macro_fields,
        errors=errors,
        skipped_relations=skipped,
        schema_violations=schema_violations(pred_scored),
        # The configured set intersected with the relations in scope for this run. It is
        # deliberately not narrowed to the relations the gold standard happened to contain:
        # a reader needs to see that the concession was in force, not only where it bit.
        subject_agnostic_relations=tuple(sorted(subject_agnostic & set(scored))),
    )


# --------------------------------------------------------------------------------------
# record-level agreement with DigiMOF / SynMOF
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldAgreement:
    """Agreement on one record field, aggregated over papers."""

    field: str
    comparable: int
    agreed: int
    not_comparable: int

    @property
    def disagreed(self) -> int:
        return self.comparable - self.agreed

    @property
    def agreement_rate(self) -> float | None:
        """Agreed over comparable, or None when nothing was comparable.

        None rather than 0.0 on purpose. A field the reference database never fills in
        has no agreement rate, and writing 0.0 would put a false zero into the report's
        table. The caller has to decide how to display "no basis for comparison".
        """
        return self.agreed / self.comparable if self.comparable else None

    def as_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "comparable": self.comparable,
            "agreed": self.agreed,
            "disagreed": self.disagreed,
            "not_comparable": self.not_comparable,
            "agreement_rate": self.agreement_rate,
        }


@dataclass(frozen=True)
class Disagreement:
    """One concrete field-level disagreement, keeping both sides verbatim.

    The report needs the real strings to classify what went wrong, and the overlap value
    separates "completely different answer" from "we found three of their four linkers".
    """

    paper_id: str
    field: str
    ours: tuple[str, ...]
    reference: tuple[str, ...]
    overlap: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "paper_id": self.paper_id,
            "field": self.field,
            "ours": list(self.ours),
            "reference": list(self.reference),
            "overlap": self.overlap,
        }


@dataclass
class AgreementResult:
    """Record-level agreement against a reference database."""

    mode: MatchMode
    threshold: float
    n_records: int
    n_records_missing_from_reference: int
    per_field: dict[str, FieldAgreement]
    disagreements: list[Disagreement]

    @property
    def comparable(self) -> int:
        return sum(f.comparable for f in self.per_field.values())

    @property
    def agreed(self) -> int:
        return sum(f.agreed for f in self.per_field.values())

    @property
    def not_comparable(self) -> int:
        return sum(f.not_comparable for f in self.per_field.values())

    @property
    def agreement_rate(self) -> float | None:
        return self.agreed / self.comparable if self.comparable else None

    def to_frame(self) -> pd.DataFrame:
        rows = [f.as_dict() for f in self.per_field.values()]
        rows.append(
            {
                "field": "overall",
                "comparable": self.comparable,
                "agreed": self.agreed,
                "disagreed": self.comparable - self.agreed,
                "not_comparable": self.not_comparable,
                "agreement_rate": self.agreement_rate,
            }
        )
        return pd.DataFrame(
            rows,
            columns=[
                "field",
                "comparable",
                "agreed",
                "disagreed",
                "not_comparable",
                "agreement_rate",
            ],
        )

    def as_dict(self, disagreement_limit: int | None = 50) -> dict[str, Any]:
        cut = (
            self.disagreements
            if disagreement_limit is None
            else self.disagreements[:disagreement_limit]
        )
        return {
            "mode": self.mode,
            "threshold": self.threshold,
            "n_records": self.n_records,
            "n_records_missing_from_reference": self.n_records_missing_from_reference,
            "comparable": self.comparable,
            "agreed": self.agreed,
            "not_comparable": self.not_comparable,
            "agreement_rate": self.agreement_rate,
            "per_field": {name: f.as_dict() for name, f in self.per_field.items()},
            "disagreements": [d.as_dict() for d in cut],
        }


def _clean_values(value: Any, null_tokens: frozenset[str]) -> list[str]:
    """A record cell as a list of non-empty strings.

    Scalars, lists and None are all accepted because a reference export gives one
    solvent as a string and three as a list, and an unfilled cell as an empty string,
    None, NaN or a literal "n/a".
    """
    if value is None:
        return []
    items = list(value) if isinstance(value, (list, tuple, set, frozenset)) else [value]
    out: list[str] = []
    for item in items:
        if item is None:
            continue
        text = str(item).strip()
        if text and text.lower() not in null_tokens:
            out.append(text)
    return out


def _match_value_sets(
    ours: set[str],
    reference: set[str],
    *,
    entity_type: str,
    mode: MatchMode,
    threshold: float,
) -> int:
    """How many normalised values pair up one-to-one across the two sets."""
    if mode == "exact":
        return len(ours & reference)
    ours_list, ref_list = sorted(ours), sorted(reference)
    candidates: list[tuple[float, int, int]] = []
    for i, a in enumerate(ours_list):
        for j, b in enumerate(ref_list):
            score = name_similarity(entity_type, a, b, mode=mode, threshold=threshold)
            if score > 0.0:
                candidates.append((-score, j, i))
    candidates.sort()
    used_a: set[int] = set()
    used_b: set[int] = set()
    for _, j, i in candidates:
        if i in used_a or j in used_b:
            continue
        used_a.add(i)
        used_b.add(j)
    return len(used_a)


def compare_record(
    paper_id: str,
    ours: Mapping[str, Any],
    reference: Mapping[str, Any] | None,
    *,
    fields: Sequence[str] | None = None,
    field_types: Mapping[str, str] = DEFAULT_FIELD_TYPES,
    mode: MatchMode = "exact",
    threshold: float = RELAXED_THRESHOLD,
    null_tokens: frozenset[str] = NULL_TOKENS,
) -> tuple[dict[str, str], list[Disagreement]]:
    """Compare one extracted record with the reference record for the same paper.

    Returns a per-field verdict in {"agree", "disagree", "not_comparable"} plus the
    disagreements with their actual values.

    Two asymmetric rules, and the reason for each:

    * A field the REFERENCE does not fill in is NOT COMPARABLE, not a disagreement.
      DigiMOF and SynMOF are themselves text-mining output over a different corpus and
      are known to be incomplete, so an empty reference cell is evidence about their
      coverage, not about our accuracy. Charging their gaps to us would understate our
      agreement for reasons that have nothing to do with our extractor.

    * A field WE do not fill in, where the reference has a value, IS a disagreement.
      That is our miss, and hiding it would be the inflating version of the same rule.

    Field-level agreement is all-or-nothing on the set of values, because "the solvent
    is DMF and water" is a different claim from "the solvent is DMF". Partial overlap is
    not silently credited; it is recorded on the Disagreement so the report can quantify
    how near the misses were.
    """
    reference = reference or {}
    names = list(fields) if fields is not None else sorted(set(ours) | set(reference))
    verdicts: dict[str, str] = {}
    found: list[Disagreement] = []

    for name in names:
        entity_type = field_types.get(name, _FALLBACK_TYPE)
        ref_vals = _clean_values(reference.get(name), null_tokens)
        if not ref_vals:
            verdicts[name] = "not_comparable"
            continue
        our_vals = _clean_values(ours.get(name), null_tokens)
        ours_norm = {normalize_by_type(entity_type, v) for v in our_vals}
        ours_norm.discard("")
        ref_norm = {normalize_by_type(entity_type, v) for v in ref_vals}
        ref_norm.discard("")
        matched = _match_value_sets(
            ours_norm, ref_norm, entity_type=entity_type, mode=mode, threshold=threshold
        )
        if matched == len(ours_norm) == len(ref_norm) and ref_norm:
            verdicts[name] = "agree"
            continue
        union = len(ours_norm) + len(ref_norm) - matched
        verdicts[name] = "disagree"
        found.append(
            Disagreement(
                paper_id=paper_id,
                field=name,
                ours=tuple(our_vals),
                reference=tuple(ref_vals),
                overlap=matched / union if union else 0.0,
            )
        )
    return verdicts, found


def agreement_report(
    ours: Mapping[str, Mapping[str, Any]],
    reference: Mapping[str, Mapping[str, Any]],
    *,
    fields: Sequence[str] | None = None,
    field_types: Mapping[str, str] = DEFAULT_FIELD_TYPES,
    mode: MatchMode = "exact",
    threshold: float = RELAXED_THRESHOLD,
    null_tokens: frozenset[str] = NULL_TOKENS,
) -> AgreementResult:
    """Per-field agreement rate between our records and a reference database.

    Both arguments map paper id to a record (field name to value or list of values).
    Papers absent from the reference contribute nothing comparable and are counted in
    n_records_missing_from_reference, for the same reason an empty cell is not a
    disagreement: no reference record means no basis for comparison, not an error.

    The field list defaults to the union of the fields present on both sides, so a field
    the reference reports and we never produce still counts against us.
    """
    if fields is None:
        names = sorted(
            {k for rec in ours.values() for k in rec}
            | {k for rec in reference.values() for k in rec}
        )
    else:
        names = list(fields)

    comparable = {name: 0 for name in names}
    agreed = {name: 0 for name in names}
    not_comparable = {name: 0 for name in names}
    disagreements: list[Disagreement] = []
    missing_records = 0

    for paper_id in sorted(ours):
        ref_record = reference.get(paper_id)
        if ref_record is None:
            missing_records += 1
        verdicts, found = compare_record(
            paper_id,
            ours[paper_id],
            ref_record,
            fields=names,
            field_types=field_types,
            mode=mode,
            threshold=threshold,
            null_tokens=null_tokens,
        )
        for name, verdict in verdicts.items():
            if verdict == "not_comparable":
                not_comparable[name] += 1
            else:
                comparable[name] += 1
                if verdict == "agree":
                    agreed[name] += 1
        disagreements.extend(found)

    per_field = {
        name: FieldAgreement(
            field=name,
            comparable=comparable[name],
            agreed=agreed[name],
            not_comparable=not_comparable[name],
        )
        for name in names
    }
    return AgreementResult(
        mode=mode,
        threshold=threshold,
        n_records=len(ours),
        n_records_missing_from_reference=missing_records,
        per_field=per_field,
        disagreements=disagreements,
    )
