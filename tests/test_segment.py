"""Offline tests for passage segmentation.

Fully inline fixtures, no network and no corpus file: segmentation is the quality
ceiling of the whole pipeline, so its behaviour has to be pinned down independently of
whatever happens to be in data/processed/ on a given day.
"""

from __future__ import annotations

import json

from src.ingestion.models import CorpusDoc, Section
from src.ingestion.segment import (
    MAX_PASSAGE_CHARS,
    MIN_KEEP_CHARS,
    Passage,
    load_corpus,
    make_passage_id,
    score_passage,
    segment_corpus,
    segment_doc,
)

SYNTHESIS_PARA = (
    "Zn(NO3)2.6H2O (297 mg, 1.0 mmol) and 2-methylimidazole (328 mg, 4.0 mmol) were "
    "dissolved separately in 20 mL of methanol. The two solutions were mixed under "
    "stirring for 30 min at room temperature. The mixture was transferred into a "
    "Teflon-lined autoclave and heated in an oven at 120 degrees C for 24 h. After "
    "cooling to room temperature, the white precipitate was collected by "
    "centrifugation, washed three times with fresh methanol and dried under vacuum at "
    "60 degrees C for 12 h."
)

INTRO_PARA = (
    "Metal–organic frameworks have attracted considerable attention over the past two "
    "decades because of their exceptionally high surface areas and tunable pore "
    "geometries. Applications ranging from gas storage to heterogeneous catalysis have "
    "been reported by many groups. Yaghi et al. described the first reticular "
    "structures, and subsequent work has expanded the field enormously. Here we "
    "summarise the state of the art and outline the remaining challenges."
)

CHARACTERISATION_PARA = (
    "Powder X-ray diffraction patterns were recorded on a Bruker D8 diffractometer "
    "using Cu K-alpha radiation over a 2-theta range of 5 to 50 degrees. Nitrogen "
    "sorption isotherms were measured at 77 K on a Micromeritics ASAP 2020 instrument. "
    "Thermogravimetric spectra were collected under a nitrogen flow, as shown in "
    "Figure 3 and Table 2 of the supplementary material."
)


def _doc(*sections: Section, paper_id: str = "PMC0000001") -> CorpusDoc:
    return CorpusDoc(
        paper_id=paper_id,
        title="Solvothermal synthesis of a zinc imidazolate framework",
        source="europepmc",
        doi="10.1000/test.mof.001",
        sections=list(sections),
    )


def test_splits_a_section_into_one_passage_per_paragraph():
    doc = _doc(
        Section(
            name="Experimental Section",
            text="\n".join([SYNTHESIS_PARA, CHARACTERISATION_PARA, INTRO_PARA]),
        )
    )
    passages = segment_doc(doc)
    assert len(passages) == 3
    assert passages[0].text.startswith("Zn(NO3)2")
    assert passages[1].text.startswith("Powder X-ray")
    assert all(p.section_name == "Experimental Section" for p in passages)
    assert all(p.paper_id == "PMC0000001" and p.doi == "10.1000/test.mof.001" for p in passages)


def test_offsets_are_exact_slices_of_the_section_text():
    section = Section(
        name="Experimental",
        text="  \n" + SYNTHESIS_PARA + "\n" + CHARACTERISATION_PARA + "\n  \n" + INTRO_PARA,
    )
    doc = _doc(section)
    passages = segment_doc(doc)
    assert passages
    for p in passages:
        # The load-bearing invariant: a passage is a contiguous slice of its section, so
        # an annotation tool can highlight it and evidence spans stay traceable.
        assert p.text == section.text[p.char_start : p.char_end]
        assert 0 <= p.char_start < p.char_end <= len(section.text)
        assert p.text == p.text.strip()
    starts = [p.char_start for p in passages]
    assert starts == sorted(starts)


def test_passage_ids_are_deterministic_across_runs_and_survive_a_text_edit():
    first = segment_doc(
        _doc(Section(name="Experimental", text=SYNTHESIS_PARA + "\n" + CHARACTERISATION_PARA))
    )
    second = segment_doc(
        _doc(Section(name="Experimental", text=SYNTHESIS_PARA + "\n" + CHARACTERISATION_PARA))
    )
    assert [p.passage_id for p in first] == [p.passage_id for p in second]

    # A corpus rebuild that fixes a typo must not orphan the gold standard annotations.
    edited = segment_doc(
        _doc(
            Section(
                name="Experimental",
                text=SYNTHESIS_PARA.replace("white precipitate", "pale precipitate")
                + "\n"
                + CHARACTERISATION_PARA,
            )
        )
    )
    assert [p.passage_id for p in edited] == [p.passage_id for p in first]


def test_passage_ids_are_unique_even_when_section_titles_repeat():
    doc = _doc(
        Section(name="Untitled section", text=SYNTHESIS_PARA),
        Section(name="Untitled section", text=CHARACTERISATION_PARA),
        Section(name="Untitled section", text=INTRO_PARA),
    )
    ids = [p.passage_id for p in segment_doc(doc)]
    assert len(ids) == 3
    assert len(set(ids)) == 3
    assert all(i.startswith("PMC0000001-") for i in ids)


def test_make_passage_id_is_pure_and_position_sensitive():
    a = make_passage_id("PMC1", "Experimental", 0, 0)
    assert a == make_passage_id("PMC1", "Experimental", 0, 0)
    assert a != make_passage_id("PMC1", "Experimental", 0, 1)
    assert a != make_passage_id("PMC1", "Experimental", 1, 0)
    assert a != make_passage_id("PMC1", "Methods", 0, 0)
    assert a != make_passage_id("PMC2", "Experimental", 0, 0)


def test_synthesis_paragraph_scores_strictly_higher_than_an_introduction():
    synth, synth_hits = score_passage(SYNTHESIS_PARA, "Experimental Section")
    intro, _ = score_passage(INTRO_PARA, "Introduction")
    charac, _ = score_passage(CHARACTERISATION_PARA, "Experimental Section")

    assert synth > intro
    assert synth > charac  # instrument prose sits in the same section, must not win
    assert 0.0 <= intro <= 1.0 and 0.0 <= synth <= 1.0
    # The signal counts behind the decision are reported, not hidden.
    assert synth_hits["quantity"] >= 4
    assert synth_hits["apparatus"] >= 1
    assert synth_hits["solvent"] >= 1
    assert synth_hits["verb"] >= 3


def test_is_synthesis_flag_follows_the_min_score_threshold():
    doc = _doc(Section(name="Experimental Section", text=SYNTHESIS_PARA + "\n" + INTRO_PARA))
    default = segment_doc(doc)
    assert default[0].is_synthesis is True

    strict = segment_doc(doc, min_score=1.01)  # nothing can reach this
    assert all(p.is_synthesis is False for p in strict)

    permissive = segment_doc(doc, min_score=0.0)
    assert all(p.is_synthesis is True for p in permissive)


def test_short_fragments_are_merged_into_a_neighbour_not_emitted_alone():
    caption = "Figure 1. Schematic of the ZIF-8 synthesis route."
    heading = "2.1 Synthesis of ZIF-8"
    section = Section(name="Experimental", text=f"{heading}\n{caption}\n{SYNTHESIS_PARA}")
    passages = segment_doc(_doc(section))

    assert len(passages) == 1
    merged = passages[0]
    assert merged.text.startswith(heading)
    assert caption in merged.text
    assert merged.text.endswith("12 h.")
    assert merged.text == section.text[merged.char_start : merged.char_end]
    assert all(p.n_chars >= MIN_KEEP_CHARS for p in passages)


def test_empty_and_whitespace_sections_produce_nothing_and_do_not_raise():
    doc = _doc(
        Section(name="Empty", text=""),
        Section(name="Blank", text="   \n\n \t \n"),
        Section(name="Stub", text="Fig. 2"),  # below MIN_KEEP_CHARS, cannot be merged
        Section(name="Experimental", text=SYNTHESIS_PARA),
    )
    passages = segment_doc(doc)
    assert [p.section_name for p in passages] == ["Experimental"]
    assert segment_doc(_doc()) == []


def test_over_long_paragraphs_are_cut_at_sentence_boundaries():
    long_text = " ".join([SYNTHESIS_PARA] * 12)  # one giant <p>, as some publishers emit
    section = Section(name="Experimental", text=long_text)
    passages = segment_doc(_doc(section))

    assert len(passages) > 1
    assert all(p.n_chars <= MAX_PASSAGE_CHARS for p in passages)
    # No character is lost or duplicated at the seams beyond the whitespace between them.
    assert passages[0].char_start == 0
    assert passages[-1].char_end == len(long_text)
    for prev, nxt in zip(passages, passages[1:], strict=False):
        assert nxt.char_start >= prev.char_end
        assert section.text[prev.char_end : nxt.char_start].strip() == ""
    assert "".join(p.text for p in passages).replace(" ", "") == long_text.replace(" ", "")


def test_segment_corpus_writes_jsonl_and_synthesis_only_filters(tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    docs = [
        _doc(
            Section(name="Introduction", text=INTRO_PARA),
            Section(name="Experimental Section", text=SYNTHESIS_PARA),
            paper_id="PMC0000001",
        ),
        _doc(
            Section(name="Results and Discussion", text=CHARACTERISATION_PARA),
            paper_id="PMC0000002",
        ),
    ]
    corpus.write_text("\n".join(d.model_dump_json() for d in docs) + "\n", encoding="utf-8")

    assert [d.paper_id for d in load_corpus(corpus)] == ["PMC0000001", "PMC0000002"]

    out_all = tmp_path / "passages.jsonl"
    segmented, written = segment_corpus(corpus=corpus, out=out_all)
    rows = [json.loads(line) for line in out_all.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == len(written) == len(segmented) == 3
    assert {r["paper_id"] for r in rows} == {"PMC0000001", "PMC0000002"}
    # Round trip through the model, since the annotation tool reads this file back.
    assert all(Passage(**r).passage_id == w.passage_id for r, w in zip(rows, written, strict=True))

    out_synth = tmp_path / "synth.jsonl"
    segmented_again, only = segment_corpus(corpus=corpus, out=out_synth, synthesis_only=True)
    assert len(segmented_again) == 3  # nothing is dropped before the filter
    assert only and all(p.is_synthesis for p in only)
    assert len(only) < len(written)
    assert {p.section_name for p in only} == {"Experimental Section"}
    synth_rows = [json.loads(line) for line in out_synth.read_text(encoding="utf-8").splitlines()]
    assert len(synth_rows) == len(only)
