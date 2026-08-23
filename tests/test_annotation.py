"""Offline tests for the gold-standard annotation logic.

Every test writes to tmp_path: the real data/annotations/gold.jsonl holds irreplaceable
human work and is committed to git, so the suite must never be able to touch it. No
network and no Streamlit import, since only src/annotation/core.py carries logic.
"""

from __future__ import annotations

import json

import pytest

from src.annotation import core
from src.extraction.extractor_base import Triple
from src.ingestion.models import CorpusDoc, Section

# --------------------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------------------
PARA_ONE = (
    "HKUST-1 was prepared solvothermally. Cu(NO3)2.3H2O (0.87 g, 3.6 mmol) and trimesic "
    "acid (0.42 g, 2.0 mmol) were dissolved in 24 mL of DMF and the mixture was heated "
    "at 120 degrees C for 24 h in a Teflon-lined autoclave. Blue crystals were collected "
    "by filtration and washed three times with ethanol."
)
PARA_TWO = (
    "The activated material showed a BET surface area of 1650 m2/g, measured by nitrogen "
    "sorption at 77 K. Thermogravimetric analysis indicated stability up to 300 degrees C, "
    "and the material was subsequently evaluated for CO2 capture under ambient pressure."
)
SHORT_PARA = "All reagents were used as received."


@pytest.fixture
def gold_path(tmp_path):
    return tmp_path / "annotations" / "gold.jsonl"


@pytest.fixture
def corpus_path(tmp_path):
    """A two-paper corpus file in the real CorpusDoc format."""
    path = tmp_path / "corpus.jsonl"
    docs = [
        CorpusDoc(
            paper_id="PMC0000001",
            title="Solvothermal synthesis of HKUST-1",
            source="europepmc",
            doi="10.1000/test.1",
            sections=[
                Section(name="Introduction", text="MOFs are porous crystalline solids."),
                Section(name="Experimental", text=f"{SHORT_PARA}\n{PARA_ONE}\n{PARA_TWO}"),
            ],
        ),
        CorpusDoc(
            paper_id="PMC0000002",
            title="A paper with no experimental section",
            source="europepmc",
            sections=[Section(name="Introduction", text="Nothing to annotate here.")],
        ),
    ]
    path.write_text("\n".join(d.model_dump_json() for d in docs) + "\n", encoding="utf-8")
    return path


def a_triple(**overrides) -> core.GoldTriple:
    """A legal MOF -USES_LINKER-> OrganicLinker annotation."""
    fields = {
        "subject_type": "MOF",
        "subject_name": "HKUST-1",
        "relation": "USES_LINKER",
        "object_type": "OrganicLinker",
        "object_name": "trimesic acid",
        "evidence": PARA_ONE,
        "subject_span": (0, 7),
        "object_span": (60, 73),
        "confidence": "high",
    }
    fields.update(overrides)
    return core.GoldTriple(**fields)


# --------------------------------------------------------------------------------------
# Ontology validation
# --------------------------------------------------------------------------------------
def test_allowed_relations_match_the_ontology_and_exclude_provenance():
    relations = core.allowed_relations()
    assert "MENTIONED_IN" not in relations  # provenance is attached by the pipeline
    assert set(relations) == {
        "USES_PRECURSOR",
        "USES_LINKER",
        "SYNTHESIZED_BY",
        "IN_SOLVENT",
        "AT_CONDITION",
        "HAS_PROPERTY",
        "MEASURED_AT",
        "USED_IN",
    }
    assert core.allowed_endpoints("IN_SOLVENT") == ("SynthesisMethod", "Solvent")
    assert core.allowed_subject_types("AT_CONDITION") == ("SynthesisMethod",)
    assert core.allowed_object_types("AT_CONDITION") == ("Condition",)


def test_validate_triple_accepts_a_legal_combination():
    assert core.validate_triple("MOF", "USES_LINKER", "OrganicLinker") is True
    assert core.validate_triple("SynthesisMethod", "IN_SOLVENT", "Solvent") is True
    assert core.explain_invalid("MOF", "USES_LINKER", "OrganicLinker") is None


def test_validate_triple_rejects_illegal_combinations():
    # right relation, wrong object type: a solvent is not a linker
    assert core.validate_triple("MOF", "USES_LINKER", "Solvent") is False
    # endpoints swapped
    assert core.validate_triple("Solvent", "IN_SOLVENT", "SynthesisMethod") is False
    # provenance is never hand annotated
    assert core.validate_triple("MOF", "MENTIONED_IN", "Paper") is False
    # relation and entity types that are not in the ontology at all
    assert core.validate_triple("MOF", "MADE_OF", "OrganicLinker") is False
    assert core.validate_triple("Reagent", "USES_LINKER", "OrganicLinker") is False


def test_explain_invalid_tells_the_annotator_what_the_ontology_wants():
    message = core.explain_invalid("MOF", "USES_LINKER", "Solvent")
    assert message is not None
    assert "MOF -> OrganicLinker" in message


def test_allowed_endpoints_raises_on_an_unknown_relation():
    with pytest.raises(ValueError, match="unknown or non-annotatable"):
        core.allowed_endpoints("MENTIONED_IN")


# --------------------------------------------------------------------------------------
# Write, resume, progress
# --------------------------------------------------------------------------------------
def test_append_then_resume_produces_no_duplicates(gold_path):
    core.append_annotation("p1", "PMC1", "Experimental", [a_triple()], path=gold_path)
    core.append_annotation("p2", "PMC1", "Experimental", [], status="no_synthesis", path=gold_path)
    # reopening the session and re-saving p1 with a second triple must replace, not append
    core.append_annotation(
        "p1",
        "PMC1",
        "Experimental",
        [
            a_triple(),
            a_triple(
                relation="USES_PRECURSOR", object_type="MetalPrecursor", object_name="Cu(NO3)2.3H2O"
            ),
        ],
        path=gold_path,
    )

    records = core.load_gold(gold_path)
    assert [r.passage_id for r in records] == ["p1", "p2"]
    assert len(records[0].triples) == 2
    assert core.annotated_passage_ids(gold_path) == {"p1", "p2"}


def test_a_duplicate_left_by_an_older_file_is_collapsed_on_the_next_write(gold_path):
    gold_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(
        core.GoldRecord(
            passage_id="p1", paper_id="PMC1", section="Experimental", status="skipped"
        ).to_dict()
    )
    gold_path.write_text(f"{line}\n{line}\n", encoding="utf-8")
    assert len(core.load_gold(gold_path)) == 2

    core.append_annotation("p1", "PMC1", "Experimental", [a_triple()], path=gold_path)
    records = core.load_gold(gold_path)
    assert len(records) == 1
    assert records[0].status == "annotated"


def test_append_annotation_refuses_to_store_an_invalid_triple(gold_path):
    with pytest.raises(ValueError, match="USES_LINKER goes MOF -> OrganicLinker"):
        core.append_annotation(
            "p1", "PMC1", "Experimental", [a_triple(object_type="Solvent")], path=gold_path
        )
    assert not gold_path.exists()  # nothing was written


def test_append_annotation_requires_evidence_and_names(gold_path):
    with pytest.raises(ValueError, match="evidence"):
        core.append_annotation("p1", "PMC1", "Exp", [a_triple(evidence="  ")], path=gold_path)
    with pytest.raises(ValueError, match="names are required"):
        core.append_annotation("p1", "PMC1", "Exp", [a_triple(subject_name="")], path=gold_path)
    with pytest.raises(ValueError, match="confidence"):
        core.append_annotation("p1", "PMC1", "Exp", [a_triple(confidence="sure")], path=gold_path)


def test_status_and_triples_have_to_agree(gold_path):
    with pytest.raises(ValueError, match="at least one triple"):
        core.append_annotation("p1", "PMC1", "Exp", [], path=gold_path)
    with pytest.raises(ValueError, match="cannot carry triples"):
        core.append_annotation(
            "p1", "PMC1", "Exp", [a_triple()], status="no_synthesis", path=gold_path
        )
    with pytest.raises(ValueError, match="status must be one of"):
        core.append_annotation("p1", "PMC1", "Exp", [], status="done", path=gold_path)
    with pytest.raises(ValueError, match="passage_id is required"):
        core.append_annotation("  ", "PMC1", "Exp", [a_triple()], path=gold_path)


def test_progress_stats_counts_against_the_target_range(gold_path):
    assert core.progress_stats(gold_path).annotated == 0
    for i in range(3):
        core.append_annotation(f"p{i}", "PMC1", "Exp", [a_triple(), a_triple()], path=gold_path)
    core.append_annotation("p9", "PMC1", "Exp", [], status="no_synthesis", path=gold_path)
    core.append_annotation("p10", "PMC1", "Exp", [], status="skipped", path=gold_path)

    stats = core.progress_stats(gold_path)
    assert (stats.annotated, stats.no_synthesis, stats.skipped) == (3, 1, 1)
    assert stats.reviewed == 5
    assert stats.triples == 6
    assert stats.target_range == (core.TARGET_MIN, core.TARGET_MAX) == (150, 200)
    assert stats.remaining == core.TARGET_MIN - 3
    assert stats.is_complete is False
    assert 0 < stats.fraction_of_target < 1


def test_delete_annotation_makes_a_passage_undecided_again(gold_path):
    core.append_annotation("p1", "PMC1", "Exp", [a_triple()], path=gold_path)
    assert core.delete_annotation("p1", gold_path) is True
    assert core.load_gold(gold_path) == []
    assert core.delete_annotation("p1", gold_path) is False


def test_a_torn_final_line_does_not_lose_earlier_work(gold_path):
    """A crash mid-write must never cost the annotator the records already on disk."""
    core.append_annotation("p1", "PMC1", "Exp", [a_triple()], path=gold_path)
    with gold_path.open("a", encoding="utf-8") as handle:
        handle.write('{"passage_id": "p2", "trip')  # simulated torn line

    records = core.load_gold(gold_path)
    assert [r.passage_id for r in records] == ["p1"]

    core.append_annotation("p3", "PMC1", "Exp", [a_triple()], path=gold_path)
    assert [r.passage_id for r in core.load_gold(gold_path)] == ["p1", "p3"]


def test_pending_passages_treats_a_skip_as_still_to_do(gold_path):
    passages = [
        core.Passage(passage_id=f"p{i}", paper_id="PMC1", section="Exp", text=PARA_ONE)
        for i in range(3)
    ]
    core.append_annotation("p0", "PMC1", "Exp", [a_triple()], path=gold_path)
    core.append_annotation("p1", "PMC1", "Exp", [], status="skipped", path=gold_path)
    pending = core.pending_passages(passages, gold_path)
    assert [p.passage_id for p in pending] == ["p1", "p2"]


# --------------------------------------------------------------------------------------
# Conversion into the frozen Triple contract
# --------------------------------------------------------------------------------------
def test_gold_record_converts_to_triple_shape_keeping_provenance(gold_path):
    core.append_annotation(
        "PMC1:experimental:001",
        "PMC1",
        "Experimental",
        [a_triple()],
        passage_text=PARA_ONE,
        path=gold_path,
    )
    record = core.load_gold(gold_path)[0]

    triple = record.to_triples()[0]
    assert isinstance(triple, Triple)
    assert triple.source_paper_id == "PMC1"
    assert triple.source_section == "Experimental"
    assert triple.evidence == PARA_ONE
    assert triple.extractor == "human-gold"
    assert (triple.subject.type, triple.subject.name) == ("MOF", "HKUST-1")
    assert (triple.object.type, triple.object.name) == ("OrganicLinker", "trimesic acid")
    assert triple.subject.span == (0, 7)
    assert triple.confidence == "high"
    # to_dict is what the evaluation and the KG loader consume
    assert triple.to_dict()["relation"] == "USES_LINKER"

    # the frozen Triple has no passage field, so passage_id travels alongside it
    pairs = list(core.iter_gold_triples(core.load_gold(gold_path)))
    assert pairs[0][0] == "PMC1:experimental:001"
    assert pairs[0][1].evidence == PARA_ONE


def test_gold_record_round_trips_through_json(gold_path):
    core.append_annotation("p1", "PMC1", "Exp", [a_triple()], path=gold_path, note="check")
    raw = json.loads(gold_path.read_text(encoding="utf-8").splitlines()[0])
    rebuilt = core.GoldRecord.from_dict(raw)
    assert rebuilt.triples[0] == a_triple()
    assert rebuilt.note == "check"
    assert rebuilt.annotated_at  # every record is timestamped for the audit trail


# --------------------------------------------------------------------------------------
# Passage loading
# --------------------------------------------------------------------------------------
def test_corpus_fallback_when_the_passages_file_is_missing(tmp_path, corpus_path):
    missing = tmp_path / "passages.jsonl"
    passages = core.load_passages(missing, corpus_path=corpus_path)

    assert passages, "the fallback must produce passages so annotation is never blocked"
    assert all(p.source == "corpus-fallback" for p in passages)
    assert {p.paper_id for p in passages} == {"PMC0000001"}  # paper 2 has no such section
    assert all(p.section == "Experimental" for p in passages)
    texts = [p.text for p in passages]
    assert PARA_ONE in texts and PARA_TWO in texts
    assert SHORT_PARA not in texts  # too short to carry a synthesis record
    assert [p.passage_id for p in passages] == [
        "PMC0000001:experimental:000",
        "PMC0000001:experimental:001",
    ]
    assert passages[0].doi == "10.1000/test.1"
    assert passages[0].is_synthesis is True


def test_corpus_fallback_ids_are_stable_across_runs(tmp_path, corpus_path):
    missing = tmp_path / "passages.jsonl"
    first = core.load_passages(missing, corpus_path=corpus_path)
    second = core.load_passages(missing, corpus_path=corpus_path)
    assert [p.passage_id for p in first] == [p.passage_id for p in second]


def test_long_paragraphs_are_split_not_truncated(tmp_path):
    long_paragraph = " ".join(f"Step {i} was carried out at 120 degrees C." for i in range(200))
    path = tmp_path / "corpus.jsonl"
    doc = CorpusDoc(
        paper_id="PMC1",
        title="long",
        source="test",
        sections=[Section(name="Synthesis", text=long_paragraph)],
    )
    path.write_text(doc.model_dump_json() + "\n", encoding="utf-8")

    passages = core.passages_from_corpus(path)
    assert len(passages) > 1
    assert all(p.n_chars <= core.MAX_PASSAGE_CHARS for p in passages)
    rejoined = " ".join(p.text for p in passages)
    assert rejoined == long_paragraph  # nothing is dropped


def test_passages_file_is_preferred_and_key_aliases_are_tolerated(tmp_path, corpus_path):
    path = tmp_path / "passages.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "passage_id": "PMC7-abc",
                        "paper_id": "PMC7",
                        "section_name": "Experimental Section",
                        "text": PARA_ONE,
                        "doi": "10.1000/test.7",
                        "is_synthesis": True,
                        "synthesis_score": 0.71,
                        "char_start": 10,
                        "char_end": 20,
                    }
                ),
                json.dumps({"id": "PMC8-1", "paper": "PMC8", "body": PARA_TWO}),
                "",
                "{not json at all",
                json.dumps({"passage_id": "PMC9-1", "paper_id": "PMC9", "text": "   "}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    passages = core.load_passages(path, corpus_path=corpus_path)
    assert [p.passage_id for p in passages] == ["PMC7-abc", "PMC8-1"]
    assert passages[0].source == "passages.jsonl"
    assert passages[0].section == "Experimental Section"
    assert passages[0].synthesis_score == 0.71
    assert passages[0].char_start == 10
    assert passages[1].paper_id == "PMC8"
    assert passages[1].is_synthesis is True  # missing flag means "unclassified", kept in scope


def test_empty_passages_file_falls_back_to_the_corpus(tmp_path, corpus_path):
    path = tmp_path / "passages.jsonl"
    path.write_text("\n", encoding="utf-8")
    passages = core.load_passages(path, corpus_path=corpus_path)
    assert passages and all(p.source == "corpus-fallback" for p in passages)


def test_build_worklist_is_deterministic_and_keeps_a_control_stratum():
    passages = [
        core.Passage(
            passage_id=f"s{i:03d}",
            paper_id=f"PMC{i}",
            section="Exp",
            text=PARA_ONE,
            is_synthesis=True,
        )
        for i in range(300)
    ] + [
        core.Passage(
            passage_id=f"c{i:03d}",
            paper_id=f"PMC{i}",
            section="Intro",
            text=PARA_TWO,
            is_synthesis=False,
        )
        for i in range(300)
    ]

    worklist = core.build_worklist(passages, n=200, control_fraction=0.1)
    assert len(worklist) == 200
    assert sum(1 for p in worklist if not p.is_synthesis) == 20
    assert len({p.passage_id for p in worklist}) == 200
    assert [p.passage_id for p in worklist] == [
        p.passage_id for p in core.build_worklist(passages, n=200, control_fraction=0.1)
    ]
    # the strata are interleaved, not annotated in two blocks
    assert any(not p.is_synthesis for p in worklist[:100])


def test_build_worklist_degrades_when_there_is_no_control_pool():
    passages = [
        core.Passage(passage_id=f"s{i}", paper_id="PMC1", section="Exp", text=PARA_ONE)
        for i in range(30)
    ]
    worklist = core.build_worklist(passages, n=20, control_fraction=0.1)
    assert len(worklist) == 20
    assert all(p.is_synthesis for p in worklist)


def test_sample_passages_returns_everything_when_the_pool_is_small():
    passages = [
        core.Passage(passage_id=f"s{i}", paper_id="PMC1", section="Exp", text=PARA_ONE)
        for i in range(5)
    ]
    assert len(core.sample_passages(passages, 50)) == 5


# --------------------------------------------------------------------------------------
# Mechanical helpers (span and evidence lookup, never a suggestion of what to annotate)
# --------------------------------------------------------------------------------------
def test_find_span_locates_a_mention_case_insensitively():
    span = core.find_span(PARA_ONE, "trimesic ACID")
    assert span is not None
    assert PARA_ONE[span[0] : span[1]].lower() == "trimesic acid"
    assert core.find_span(PARA_ONE, "ZIF-8") is None
    assert core.find_span(PARA_ONE, "   ") is None


def test_sentence_containing_returns_verbatim_source_text():
    sentence = core.sentence_containing(PARA_ONE, "trimesic acid")
    assert sentence in PARA_ONE  # verbatim, never generated
    assert "24 mL of DMF" in sentence
    assert "Blue crystals" not in sentence
    assert core.sentence_containing(PARA_ONE, "ZIF-8") == ""
