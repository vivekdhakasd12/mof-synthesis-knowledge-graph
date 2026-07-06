"""Smoke tests for the Triple data model."""
from src.extraction.extractor_base import Entity, Triple


def test_triple_to_dict_roundtrip():
    t = Triple(
        subject=Entity(type="Material", name="TiO2", span=(0, 4)),
        relation="HAS_PROPERTY",
        object=Entity(type="Property", name="bandgap = 3.2 eV", span=(20, 36)),
        evidence="TiO2 has a bandgap = 3.2 eV.",
        confidence="high",
        source_paper_id="arxiv:2406.00001",
        source_section="results",
        extractor="llm-schema-guided",
    )
    d = t.to_dict()
    assert d["relation"] == "HAS_PROPERTY"
    assert d["subject"]["name"] == "TiO2"
    assert d["object"]["name"] == "bandgap = 3.2 eV"
    assert d["confidence"] == "high"
