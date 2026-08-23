"""Tests for the rule-based baseline extractor.

The baseline is the control the whole project is measured against, so these tests care
about two things beyond "does it find anything": that it obeys the Extractor contract
under abuse, and that every triple it emits is ontology-valid with provenance intact.
A baseline that quietly emitted malformed triples would corrupt the comparison rather
than fail loudly.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.extraction.extractor_base import ExtractionResult
from src.extraction.rule_based import RuleBasedExtractor

REPO_ROOT = Path(__file__).resolve().parents[1]

HKUST = (
    "HKUST-1 was synthesized by dissolving Cu(NO3)2.3H2O (0.42 g, 1.7 mmol) and trimesic "
    "acid (0.21 g, 1.0 mmol) in 30 mL DMF and heating at 120 degrees C for 24 h in a "
    "Teflon-lined autoclave."
)

# Endpoint table from configs/ontology.json v0.2, restated here so the test fails if the
# extractor and the ontology ever drift apart.
ENDPOINTS = {
    "USES_PRECURSOR": ("MOF", "MetalPrecursor"),
    "USES_LINKER": ("MOF", "OrganicLinker"),
    "SYNTHESIZED_BY": ("MOF", "SynthesisMethod"),
    "IN_SOLVENT": ("SynthesisMethod", "Solvent"),
    "AT_CONDITION": ("SynthesisMethod", "Condition"),
    "HAS_PROPERTY": ("MOF", "Property"),
    "MEASURED_AT": ("Property", "Condition"),
    "USED_IN": ("MOF", "Application"),
}


@pytest.fixture
def extractor() -> RuleBasedExtractor:
    return RuleBasedExtractor()


def test_extracts_the_core_record(extractor: RuleBasedExtractor) -> None:
    result = extractor.extract(HKUST, paper_id="PMC1", section="Experimental")
    pairs = {(t.relation, t.object.name.lower()) for t in result.triples}
    assert any(r == "USES_PRECURSOR" and "no3" in o for r, o in pairs)
    assert any(r == "USES_LINKER" and "trimesic" in o for r, o in pairs)
    assert any(r == "IN_SOLVENT" and "dmf" in o for r, o in pairs)
    assert any(r == "AT_CONDITION" and "120" in o for r, o in pairs)
    assert any(r == "AT_CONDITION" and "24" in o for r, o in pairs)


def test_every_triple_is_ontology_valid(extractor: RuleBasedExtractor) -> None:
    result = extractor.extract(HKUST, paper_id="PMC1", section="Experimental")
    assert result.triples
    for t in result.triples:
        assert t.relation in ENDPOINTS, f"unknown relation {t.relation}"
        subject_type, object_type = ENDPOINTS[t.relation]
        assert t.subject.type == subject_type
        assert t.object.type == object_type


def test_provenance_and_evidence_are_populated(extractor: RuleBasedExtractor) -> None:
    result = extractor.extract(HKUST, paper_id="PMC1", section="Experimental")
    for t in result.triples:
        assert t.source_paper_id == "PMC1"
        assert t.source_section == "Experimental"
        assert t.evidence.strip(), "every triple needs the sentence it came from"
        assert t.extractor == extractor.name


def test_spans_point_at_the_real_substring(extractor: RuleBasedExtractor) -> None:
    """A span is a provenance pointer, so it must index back into the passage.

    Property is the documented exception: its span brackets descriptor through unit while
    the name is a composed "term value unit" string.
    """
    result = extractor.extract(HKUST, paper_id="PMC1", section="Experimental")
    for t in result.triples:
        for entity in (t.subject, t.object):
            if entity.span is None or entity.type == "Property":
                continue
            start, end = entity.span
            assert HKUST[start:end] == entity.name


def test_never_emits_pipeline_owned_provenance(extractor: RuleBasedExtractor) -> None:
    result = extractor.extract(HKUST, paper_id="PMC1", section="Experimental")
    assert all(t.relation != "MENTIONED_IN" for t in result.triples)
    assert all(t.subject.type != "Paper" and t.object.type != "Paper" for t in result.triples)


def test_metal_linker_designations_are_recognised(extractor: RuleBasedExtractor) -> None:
    """Cu-BTC is a standard name for HKUST-1 and must not be missed.

    Measured motivation: the metal-linker convention was originally unhandled, which
    suppressed every MOF-subject relation on those passages.
    """
    result = extractor.extract(
        "Cu-BTC was synthesized from copper nitrate and trimesic acid in DMF at 120 degrees C.",
        paper_id="PMC1",
        section="Experimental",
    )
    mofs = {t.subject.name for t in result.triples if t.subject.type == "MOF"}
    assert "Cu-BTC" in mofs


def test_bond_notation_is_not_mistaken_for_a_mof(extractor: RuleBasedExtractor) -> None:
    """The negative case that keeps the metal-linker pattern honest."""
    result = extractor.extract(
        "The Cu-O bond length was 1.95 A and the Zn-Zn separation was 3.1 A.",
        paper_id="PMC1",
        section="Results",
    )
    assert not [t for t in result.triples if t.subject.type == "MOF" or t.object.type == "MOF"]


def test_inferred_method_is_marked_low_confidence(extractor: RuleBasedExtractor) -> None:
    """An unnamed route is a guess, and the evaluation must be able to separate guesses."""
    passage = (
        "ZIF-8 was prepared by dissolving Zn(NO3)2.6H2O and 2-methylimidazole in DMF "
        "and holding the mixture at 120 degrees C for 24 h."
    )
    result = extractor.extract(passage, paper_id="PMC1", section="Experimental")
    inferred = [
        t for t in result.triples if t.relation == "SYNTHESIZED_BY" and t.object.span is None
    ]
    for t in inferred:
        assert t.confidence == "low"


@pytest.mark.parametrize(
    "bad",
    ["", "   ", "\n\n", "...", "!!!", "a" * 5000, "\x00\x01binary", "المعادن العضوية"],
)
def test_never_raises_on_hostile_input(extractor: RuleBasedExtractor, bad: str) -> None:
    """The Extractor contract forbids raising. Problems belong in errors."""
    result = extractor.extract(bad, paper_id="PMC1", section="Experimental")
    assert isinstance(result, ExtractionResult)
    assert isinstance(result.triples, list)
    assert isinstance(result.errors, list)


def test_reports_zero_cost_and_a_latency(extractor: RuleBasedExtractor) -> None:
    """The baseline is free, which is itself a reportable result against the LLM strand."""
    result = extractor.extract(HKUST, paper_id="PMC1", section="Experimental")
    assert result.cost_usd == 0.0
    assert result.latency_ms >= 0.0


def test_runs_over_real_corpus_passages(extractor: RuleBasedExtractor) -> None:
    """Smoke test against genuine text, skipped when the corpus has not been built."""
    path = REPO_ROOT / "data" / "processed" / "passages.jsonl"
    if not path.exists():
        pytest.skip("passages.jsonl not built in this environment")
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("is_synthesis"):
                rows.append(row)
            if len(rows) >= 40:
                break
    if not rows:
        pytest.skip("no synthesis passages available")
    total = 0
    for row in rows:
        result = extractor.extract(
            row["text"], paper_id=row["paper_id"], section=row.get("section_name")
        )
        total += len(result.triples)
        for t in result.triples:
            assert t.relation in ENDPOINTS
            assert t.source_paper_id == row["paper_id"]
    assert total > 0, "the baseline must extract something from real synthesis text"
