"""Tests for the Triple data model and its alignment with the ontology.

configs/ontology.json is the source of truth for entity and relation types;
the drift-guard tests here fail if extractor_base.py falls out of sync with it.
"""

import json
from pathlib import Path
from typing import get_args

from src.extraction.extractor_base import Entity, EntityType, RelationType, Triple

ONTOLOGY_PATH = Path(__file__).parents[1] / "configs" / "ontology.json"


def load_ontology() -> dict:
    return json.loads(ONTOLOGY_PATH.read_text(encoding="utf-8"))


def test_triple_to_dict_roundtrip():
    t = Triple(
        subject=Entity(type="MOF", name="HKUST-1", span=(0, 7)),
        relation="USES_LINKER",
        object=Entity(type="OrganicLinker", name="trimesic acid (H3BTC)", span=(29, 50)),
        evidence="HKUST-1 was synthesized from trimesic acid (H3BTC) and copper nitrate.",
        confidence="high",
        source_paper_id="doi:10.1126/science.283.5405.1148",
        source_section="synthesis",
        extractor="llm-schema-guided",
    )
    d = t.to_dict()
    assert d["relation"] == "USES_LINKER"
    assert d["subject"]["name"] == "HKUST-1"
    assert d["object"]["name"] == "trimesic acid (H3BTC)"
    assert d["confidence"] == "high"
    assert d["source_paper_id"] == "doi:10.1126/science.283.5405.1148"


def test_entity_types_match_ontology():
    ontology_entities = set(load_ontology()["entities"])
    literal_entities = set(get_args(EntityType))
    assert literal_entities == ontology_entities, (
        f"EntityType drifted from configs/ontology.json: "
        f"missing {ontology_entities - literal_entities or '{}'}, "
        f"extra {literal_entities - ontology_entities or '{}'}"
    )


def test_relation_types_match_ontology():
    ontology_relations = set(load_ontology()["relations"])
    literal_relations = set(get_args(RelationType))
    assert literal_relations == ontology_relations, (
        f"RelationType drifted from configs/ontology.json: "
        f"missing {ontology_relations - literal_relations or '{}'}, "
        f"extra {literal_relations - ontology_relations or '{}'}"
    )


def test_ontology_relations_have_valid_endpoints():
    ontology = load_ontology()
    entities = set(ontology["entities"])
    for name, spec in ontology["relations"].items():
        for endpoint in (spec["from"], spec["to"]):
            assert endpoint == "*" or endpoint in entities, (
                f"Relation {name} references unknown entity {endpoint!r}"
            )


def test_ontology_provenance_invariant_locked():
    """Provenance is mandatory (CLAUDE.md); a future ontology edit must not relax it silently."""
    ontology = load_ontology()
    assert ontology["provenance_required"] is True
    mentioned_in = ontology["relations"]["MENTIONED_IN"]
    assert mentioned_in["required"] is True
    assert mentioned_in["from"] == "*"
    assert mentioned_in["to"] == "Paper"


def test_prompt_template_matches_ontology():
    """The schema-guided prompt must enumerate every extractable v0.2 type.

    Paper and MENTIONED_IN are excluded: provenance is attached by the pipeline,
    not extracted from passage text.
    """
    template = (
        Path(__file__).parents[1] / "configs" / "prompts" / "extraction_schema_guided.txt"
    ).read_text(encoding="utf-8")
    ontology = load_ontology()
    for entity in set(ontology["entities"]) - {"Paper"}:
        assert entity in template, f"Prompt template missing entity type {entity}"
    for relation in set(ontology["relations"]) - {"MENTIONED_IN"}:
        assert relation in template, f"Prompt template missing relation {relation}"
