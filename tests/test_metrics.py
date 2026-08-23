"""Tests for the evaluation metrics.

These are the numbers the thesis is graded on, so the tests here are aimed squarely at
the ways a metric can be quietly wrong in our favour: crediting one gold triple twice,
matching across passages, counting pipeline provenance as an extractor success, or
letting a reference database's empty cells look like our agreement. Every test states
which of those it guards.

All offline: no network, no API keys, no database.
"""

from __future__ import annotations

import json
from typing import Any

from sklearn.metrics import precision_recall_fscore_support

from src.evaluation.metrics import (
    DEFAULT_FIELD_TYPES,
    RELAXED_THRESHOLD,
    SCORED_RELATIONS,
    agreement_report,
    compare_record,
    entity_similarity,
    evaluate,
    greedy_one_to_one,
    name_similarity,
    precision_recall_f1,
    relation_endpoints,
    schema_violations,
)
from src.extraction.extractor_base import Entity, Triple

PAPER = "PMC7000001"
SECTION = "Experimental"


def mof(name: str = "HKUST-1") -> Entity:
    return Entity(type="MOF", name=name)


def triple(
    subject: Entity,
    relation: str,
    obj: Entity,
    *,
    evidence: str = "HKUST-1 was prepared solvothermally in DMF.",
    paper: str | None = PAPER,
    section: str | None = SECTION,
    extractor: str = "test",
) -> Triple:
    """Build a fully provenanced triple. Provenance is mandatory in this project, so the
    fixtures carry it by default and the tests that care about passage isolation vary it
    explicitly."""
    return Triple(
        subject=subject,
        relation=relation,  # type: ignore[arg-type]
        object=obj,
        evidence=evidence,
        confidence="high",
        source_paper_id=paper,
        source_section=section,
        extractor=extractor,
    )


def linker(name: str) -> Triple:
    return triple(mof(), "USES_LINKER", Entity(type="OrganicLinker", name=name))


def solvent(name: str) -> Triple:
    return triple(
        Entity(type="SynthesisMethod", name="solvothermal"),
        "IN_SOLVENT",
        Entity(type="Solvent", name=name),
    )


def condition(name: str) -> Triple:
    return triple(
        Entity(type="SynthesisMethod", name="solvothermal"),
        "AT_CONDITION",
        Entity(type="Condition", name=name),
    )


# ---------------------------------------------------------------------------------
# core scoring
# ---------------------------------------------------------------------------------


def test_perfect_prediction_scores_one_everywhere():
    """A prediction identical to gold must give F1 = 1.0 per field, micro and macro."""
    gold = [
        linker("H3BTC"),
        solvent("DMF"),
        condition("120 degrees C"),
        triple(mof(), "USES_PRECURSOR", Entity(type="MetalPrecursor", name="Cu(NO3)2.3H2O")),
    ]
    result = evaluate(list(gold), gold, mode="exact")

    assert result.micro.f1 == 1.0
    assert result.micro.precision == 1.0
    assert result.micro.recall == 1.0
    assert result.macro_f1 == 1.0
    for rel in result.macro_fields:
        assert result.per_field[rel].f1 == 1.0
        assert result.per_field[rel].fp == 0
        assert result.per_field[rel].fn == 0
    assert result.micro.tp == 4


def test_perfect_prediction_survives_surface_variation_via_shared_normaliser():
    """Identity comes from src/normalize.py, so a synonym is still a true positive.

    This is the property that keeps evaluation and the Neo4j loader agreeing about what
    counts as the same node.
    """
    gold = [linker("trimesic acid"), solvent("N,N-dimethylformamide"), condition("24 hours")]
    predicted = [linker("H3BTC"), solvent("DMF"), condition("24 h")]
    assert evaluate(predicted, gold, mode="exact").micro.f1 == 1.0


def test_empty_prediction_gives_zero_recall_and_does_not_divide_by_zero():
    """The classic silent bug: 0/0 defined as 1.0 would make a mute extractor perfect."""
    gold = [linker("H3BTC"), solvent("DMF")]
    result = evaluate([], gold, mode="exact")

    assert result.micro.recall == 0.0
    assert result.micro.precision == 0.0
    assert result.micro.f1 == 0.0
    assert result.micro.fn == 2
    assert result.macro_f1 == 0.0
    # And the mirror case: nothing to predict against, nothing predicted.
    empty = evaluate([], [], mode="exact")
    assert empty.micro.f1 == 0.0
    assert empty.macro_fields == ()
    assert empty.n_passages == 0


def test_precision_recall_f1_zero_division_convention():
    assert precision_recall_f1(0, 0, 0) == (0.0, 0.0, 0.0)
    assert precision_recall_f1(0, 5, 0) == (0.0, 0.0, 0.0)
    assert precision_recall_f1(1, 1, 1) == (0.5, 0.5, 0.5)


# ---------------------------------------------------------------------------------
# exact versus relaxed matching
# ---------------------------------------------------------------------------------


def test_exact_and_relaxed_differ_on_a_real_surface_variant():
    """Exact matching is too strict for chemistry text; relaxed must recover the pair.

    Note on the fixture: the pair usually quoted for this ("Cu(NO3)2.3H2O" versus
    "copper nitrate trihydrate") does NOT separate the two modes, because the shared
    normaliser already drops hydrate notation and resolves the salt synonym, so both
    modes match it. That is asserted below so the behaviour is on the record. The pair
    that genuinely separates the modes is the oxidation-state variant, which no synonym
    rule covers.
    """
    gold = [triple(mof(), "USES_PRECURSOR", Entity(type="MetalPrecursor", name="Cu(NO3)2.3H2O"))]
    variant = [
        triple(
            mof(),
            "USES_PRECURSOR",
            Entity(type="MetalPrecursor", name="copper(II) nitrate trihydrate"),
        )
    ]
    assert evaluate(variant, gold, mode="exact").micro.f1 == 0.0
    assert evaluate(variant, gold, mode="relaxed").micro.f1 == 1.0

    # The normaliser already handles the plain hydrate form, in both modes.
    plain = [
        triple(
            mof(), "USES_PRECURSOR", Entity(type="MetalPrecursor", name="copper nitrate trihydrate")
        )
    ]
    assert evaluate(plain, gold, mode="exact").micro.f1 == 1.0
    assert evaluate(plain, gold, mode="relaxed").micro.f1 == 1.0


def test_relaxed_accepts_qualifiers_but_never_merges_different_materials():
    """Relaxed mode relaxes orthography only.

    Character-level similarity would be catastrophic here: methanol and ethanol are 93
    percent similar as strings, UiO-66 and UiO-67 differ by one digit. Both must stay
    apart at every threshold, while parentheticals and qualifiers must be forgiven.
    """
    assert name_similarity("MOF", "MIL-101(Cr)", "MIL-101", mode="relaxed") > 0.0
    assert name_similarity("MOF", "ZIF-8 nanoparticles", "ZIF-8", mode="relaxed") > 0.0
    assert (
        name_similarity("SynthesisMethod", "solvothermal", "solvothermal synthesis", mode="relaxed")
        == 1.0
    )

    assert name_similarity("MOF", "UiO-66", "UiO-67", mode="relaxed") == 0.0
    assert name_similarity("Solvent", "methanol", "ethanol", mode="relaxed") == 0.0
    assert name_similarity("MetalPrecursor", "zinc nitrate", "zinc nitrite", mode="relaxed") == 0.0
    assert name_similarity("Condition", "120 C", "150 C", mode="relaxed") == 0.0
    assert (
        name_similarity("Property", "BET surface area", "Langmuir surface area", mode="relaxed")
        == 0.0
    )


def test_relaxed_matching_does_not_forgive_a_schema_error():
    """Entity types are a closed vocabulary; calling a solvent a linker is not a typo."""
    same_name_wrong_type = entity_similarity(
        Entity(type="Solvent", name="water"),
        Entity(type="OrganicLinker", name="water"),
        mode="relaxed",
    )
    assert same_name_wrong_type == 0.0


def test_relaxed_threshold_is_configurable_and_defaulted():
    """The threshold is a reported parameter, not a hidden constant."""
    assert 0.0 < RELAXED_THRESHOLD < 1.0
    # 2 of 3 tokens shared scores 0.667: accepted at the default, rejected at 0.7.
    assert name_similarity("MOF", "MIL-101(Cr)", "MIL-101", mode="relaxed", threshold=0.7) == 0.0
    result = evaluate(
        [
            triple(
                mof("MIL-101(Cr)"),
                "SYNTHESIZED_BY",
                Entity(type="SynthesisMethod", name="solvothermal"),
            )
        ],
        [
            triple(
                mof("MIL-101"),
                "SYNTHESIZED_BY",
                Entity(type="SynthesisMethod", name="solvothermal"),
            )
        ],
        mode="relaxed",
        threshold=0.7,
    )
    assert result.micro.tp == 0
    assert result.threshold == 0.7


# ---------------------------------------------------------------------------------
# assignment
# ---------------------------------------------------------------------------------


def test_one_to_one_assignment_prevents_double_counting():
    """Three copies of one correct answer must not each be credited.

    Without the one-to-one constraint an extractor that repeats itself would report
    precision 1.0, which is the single easiest way to fake a good result.
    """
    gold = [linker("H3BTC")]
    predicted = [linker("H3BTC"), linker("trimesic acid"), linker("H3BTC")]
    result = evaluate(predicted, gold, mode="exact")

    assert result.micro.tp == 1
    assert result.micro.fp == 2
    assert result.micro.precision == 1 / 3
    assert result.micro.recall == 1.0
    assert len(result.errors["USES_LINKER"].false_positives) == 2


def test_greedy_assignment_is_deterministic_and_prefers_the_better_pair():
    """A rerun must reproduce the same assignment, and the exact pair must win the tie."""
    gold = [linker("MIL-101"), linker("terephthalic acid")]
    predicted = [linker("MIL-101(Cr)"), linker("MIL-101")]
    first = greedy_one_to_one(predicted, gold, mode="relaxed")
    second = greedy_one_to_one(predicted, gold, mode="relaxed")

    assert [m.score for m in first[0]] == [m.score for m in second[0]]
    assert first[0][0].score == 1.0
    assert first[0][0].predicted.object.name == "MIL-101"
    assert len(first[0]) == 1


def test_matching_never_crosses_passages():
    """A correct-looking answer about the wrong paper is not a true positive.

    Cross-passage matching would be a leak that inflates recall, and it is invisible in
    the headline numbers unless it is tested for.
    """
    gold = [linker("H3BTC")]
    other_paper = [
        triple(mof(), "USES_LINKER", Entity(type="OrganicLinker", name="H3BTC"), paper="PMC9999999")
    ]
    result = evaluate(other_paper, gold, mode="exact")

    assert result.micro.tp == 0
    assert result.micro.fp == 1
    assert result.micro.fn == 1
    assert result.n_passages == 2

    other_section = [
        triple(mof(), "USES_LINKER", Entity(type="OrganicLinker", name="H3BTC"), section="Results")
    ]
    assert evaluate(other_section, gold, mode="exact").micro.tp == 0


# ---------------------------------------------------------------------------------
# aggregation and support
# ---------------------------------------------------------------------------------


def _imbalanced() -> tuple[list[Triple], list[Triple]]:
    """Ten linker triples all correct, one condition triple wrong: macro punishes the
    rare field, micro barely notices it."""
    gold = [
        triple(mof(f"MOF-{i}"), "USES_LINKER", Entity(type="OrganicLinker", name=f"linker {i}"))
        for i in range(10)
    ] + [condition("120 degrees C")]
    predicted = [
        triple(mof(f"MOF-{i}"), "USES_LINKER", Entity(type="OrganicLinker", name=f"linker {i}"))
        for i in range(10)
    ] + [condition("150 degrees C")]
    return predicted, gold


def test_micro_and_macro_differ_on_an_imbalanced_example():
    predicted, gold = _imbalanced()
    result = evaluate(predicted, gold, mode="exact")

    assert result.per_field["USES_LINKER"].f1 == 1.0
    assert result.per_field["AT_CONDITION"].f1 == 0.0
    assert result.micro.f1 == 10 / 11
    assert result.macro_f1 == 0.5
    assert result.macro_f1 != result.micro.f1
    assert result.macro_fields == ("USES_LINKER", "AT_CONDITION")


def test_per_field_support_counts_come_from_the_gold_side_only():
    """Support must be tp + fn. If predictions could raise it, an extractor could dilute
    its own error rate by predicting more."""
    predicted, gold = _imbalanced()
    predicted = predicted + [solvent("DMF"), solvent("ethanol")]
    result = evaluate(predicted, gold, mode="exact")

    assert result.per_field["USES_LINKER"].support == 10
    assert result.per_field["AT_CONDITION"].support == 1
    assert result.per_field["IN_SOLVENT"].support == 0
    assert result.per_field["IN_SOLVENT"].n_predicted == 2
    assert result.per_field["USES_PRECURSOR"].support == 0
    assert sum(result.per_field[r].support for r in SCORED_RELATIONS) == len(gold)


def test_hallucinated_field_is_excluded_from_macro_but_still_punishes_micro():
    """A field with no gold support has an undefined recall, so it cannot enter the macro
    average, but its false positives must still show up somewhere: micro counts them and
    macro_fields records exactly what was averaged."""
    predicted, gold = _imbalanced()
    predicted = predicted + [solvent("DMF")]
    with_hallucination = evaluate(predicted, gold, mode="exact")
    without = evaluate(*_imbalanced(), mode="exact")

    assert "IN_SOLVENT" not in with_hallucination.macro_fields
    assert with_hallucination.macro_f1 == without.macro_f1
    assert with_hallucination.micro.fp > without.micro.fp
    assert with_hallucination.micro.precision < without.micro.precision


def test_metrics_agree_with_scikit_learn():
    """Cross-check the arithmetic against a reference implementation.

    The matching is ours, but once tp/fp/fn are fixed the per-field, micro and macro
    numbers are standard, and there is no excuse for them to differ from sklearn.
    """
    predicted, gold = _imbalanced()
    result = evaluate(predicted, gold, mode="exact")

    y_true: list[int] = []
    y_pred: list[int] = []
    per_field_expected = {}
    for rel in result.macro_fields:
        score = result.per_field[rel]
        yt = [1] * score.tp + [1] * score.fn + [0] * score.fp
        yp = [1] * score.tp + [0] * score.fn + [1] * score.fp
        p, r, f, _ = precision_recall_fscore_support(yt, yp, average="binary", zero_division=0)
        per_field_expected[rel] = (p, r, f)
        y_true.extend(yt)
        y_pred.extend(yp)

    for rel, (p, r, f) in per_field_expected.items():
        assert result.per_field[rel].precision == p
        assert result.per_field[rel].recall == r
        assert abs(result.per_field[rel].f1 - f) < 1e-12

    micro_p, micro_r, micro_f, _ = precision_recall_fscore_support(
        y_true, y_pred, average="binary", zero_division=0
    )
    assert abs(result.micro.precision - micro_p) < 1e-12
    assert abs(result.micro.recall - micro_r) < 1e-12
    assert abs(result.micro.f1 - micro_f) < 1e-12

    n = len(per_field_expected)
    assert abs(result.macro_f1 - sum(v[2] for v in per_field_expected.values()) / n) < 1e-12


# ---------------------------------------------------------------------------------
# provenance, skipping and error breakdown
# ---------------------------------------------------------------------------------


def test_mentioned_in_is_never_scored():
    """MENTIONED_IN is provenance written by the pipeline, not an extraction. Scoring it
    would hand every extractor a block of free true positives."""
    provenance = triple(mof(), "MENTIONED_IN", Entity(type="Paper", name=PAPER))
    result = evaluate([provenance, linker("H3BTC")], [provenance, linker("H3BTC")])

    assert "MENTIONED_IN" not in result.per_field
    assert result.skipped_relations["MENTIONED_IN"] == 2
    assert result.micro.tp == 1


def test_error_breakdown_keeps_the_actual_offending_triples():
    """The report's error taxonomy needs real strings, so counts alone are not enough."""
    gold = [condition("24 h"), linker("H3BTC")]
    predicted = [condition("24 d"), linker("fumaric acid")]
    result = evaluate(predicted, gold, mode="exact")

    cond = result.errors["AT_CONDITION"]
    assert cond.false_positives[0].object.name == "24 d"
    assert cond.false_negatives[0].object.name == "24 h"
    assert cond.false_positives[0].source_paper_id == PAPER
    assert cond.false_positives[0].source_section == SECTION
    assert cond.false_positives[0].evidence

    # Same subject and relation, different object: a wrong value, not an invented fact.
    assert len(cond.value_mismatches) == 1
    wrong_pred, wrong_gold = cond.value_mismatches[0]
    assert (wrong_pred.object.name, wrong_gold.object.name) == ("24 d", "24 h")

    tps = evaluate(gold, gold, mode="exact").errors["AT_CONDITION"].true_positives
    assert tps[0].predicted.object.name == "24 h"
    assert tps[0].gold.object.name == "24 h"
    assert tps[0].score == 1.0


def test_schema_violations_are_reported_against_the_ontology_file():
    """configs/ontology.json is the source of truth for relation endpoints."""
    endpoints = relation_endpoints()
    assert endpoints["USES_LINKER"] == ("MOF", "OrganicLinker")

    bad = triple(mof(), "USES_LINKER", Entity(type="Solvent", name="DMF"))
    assert schema_violations([bad]) == [bad]
    assert schema_violations([linker("H3BTC")]) == []

    result = evaluate([bad], [linker("H3BTC")], mode="exact")
    assert result.schema_violations == [bad]
    # Still counted as an ordinary false positive; the list is a diagnostic, not a
    # second penalty.
    assert result.micro.fp == 1


def test_result_is_structured_data_not_strings():
    predicted, gold = _imbalanced()
    result = evaluate(predicted, gold, mode="exact")

    frame = result.to_frame()
    assert list(frame["relation"])[-2:] == ["micro", "macro"]
    assert len(frame) == len(SCORED_RELATIONS) + 2
    assert float(frame.loc[frame["relation"] == "USES_LINKER", "f1"].iloc[0]) == 1.0

    payload: dict[str, Any] = result.as_dict()
    assert json.loads(json.dumps(payload))["micro"]["support"] == 11


# ---------------------------------------------------------------------------------
# record-level agreement with DigiMOF / SynMOF
# ---------------------------------------------------------------------------------


def test_missing_reference_field_is_not_comparable_rather_than_wrong():
    """The load-bearing methodological rule of the agreement analysis.

    DigiMOF and SynMOF are themselves incomplete text-mining output. An empty cell is
    evidence about their coverage, not about our accuracy, so it must not be scored as a
    disagreement.
    """
    ours = {"PMC1": {"linker": "H3BTC", "solvent": "DMF", "temperature": "120 degrees C"}}
    reference = {"PMC1": {"linker": "trimesic acid", "solvent": "", "temperature": None}}
    result = agreement_report(ours, reference, mode="exact")

    assert result.per_field["linker"].comparable == 1
    assert result.per_field["linker"].agreed == 1
    assert result.per_field["solvent"].comparable == 0
    assert result.per_field["solvent"].not_comparable == 1
    assert result.per_field["temperature"].not_comparable == 1
    assert result.agreement_rate == 1.0
    assert result.disagreements == []


def test_null_tokens_in_the_reference_export_count_as_missing():
    ours = {"PMC1": {"solvent": "DMF"}}
    for empty in ("n/a", "NA", "unknown", "-", "  "):
        reference = {"PMC1": {"solvent": empty}}
        result = agreement_report(ours, reference, mode="exact")
        assert result.per_field["solvent"].comparable == 0, empty
        assert result.agreement_rate is None


def test_a_field_we_miss_but_the_reference_has_is_a_disagreement():
    """The asymmetry that keeps the rule honest: their gap is not comparable, our gap is
    our error."""
    ours = {"PMC1": {"linker": "H3BTC", "solvent": None}}
    reference = {"PMC1": {"linker": "trimesic acid", "solvent": "DMF"}}
    result = agreement_report(ours, reference, mode="exact")

    assert result.per_field["solvent"].comparable == 1
    assert result.per_field["solvent"].agreed == 0
    assert result.agreement_rate == 0.5
    assert result.disagreements[0].field == "solvent"
    assert result.disagreements[0].ours == ()
    assert result.disagreements[0].reference == ("DMF",)


def test_a_field_only_the_reference_reports_still_counts_against_us():
    """Field list defaults to the union of both sides, so we cannot improve the number by
    simply never emitting a field."""
    ours = {"PMC1": {"linker": "H3BTC"}}
    reference = {"PMC1": {"linker": "trimesic acid", "temperature": "120 C"}}
    result = agreement_report(ours, reference, mode="exact")

    assert "temperature" in result.per_field
    assert result.per_field["temperature"].comparable == 1
    assert result.per_field["temperature"].agreed == 0


def test_paper_absent_from_the_reference_database_is_not_comparable():
    ours = {"PMC1": {"linker": "H3BTC"}, "PMC2": {"linker": "H2BDC"}}
    reference = {"PMC1": {"linker": "trimesic acid"}}
    result = agreement_report(ours, reference, mode="exact")

    assert result.n_records == 2
    assert result.n_records_missing_from_reference == 1
    assert result.per_field["linker"].comparable == 1
    assert result.per_field["linker"].not_comparable == 1
    assert result.agreement_rate == 1.0


def test_agreement_uses_the_shared_normaliser_and_the_declared_field_types():
    """Agreement must apply the same identity rules as extraction scoring and the graph."""
    assert DEFAULT_FIELD_TYPES["temperature"] == "Condition"
    ours = {"PMC1": {"solvent": "DMF", "temperature": "120 degrees C", "mof": "UiO-66"}}
    reference = {
        "PMC1": {"solvent": "N,N-dimethylformamide", "temperature": "120 C", "mof": "UiO 66"}
    }
    assert agreement_report(ours, reference, mode="exact").agreement_rate == 1.0

    # And a genuinely different material still disagrees.
    wrong = {"PMC1": {"solvent": "DMF", "temperature": "120 degrees C", "mof": "UiO-67"}}
    result = agreement_report(wrong, reference, mode="exact")
    assert result.per_field["mof"].agreed == 0


def test_multi_valued_field_agreement_is_all_or_nothing_with_overlap_recorded():
    """ "Solvent is DMF and water" is a different claim from "solvent is DMF", so partial
    overlap is not credited, but it is recorded so the report can quantify near misses."""
    ours = {"PMC1": {"solvent": ["DMF", "water", "ethanol"]}}
    reference = {"PMC1": {"solvent": ["DMF", "H2O"]}}
    result = agreement_report(ours, reference, mode="exact")

    assert result.per_field["solvent"].agreed == 0
    assert result.disagreements[0].overlap == 2 / 3
    assert result.disagreements[0].ours == ("DMF", "water", "ethanol")
    assert result.disagreements[0].reference == ("DMF", "H2O")

    exact_match = agreement_report({"PMC1": {"solvent": ["DMF", "water"]}}, reference, mode="exact")
    assert exact_match.per_field["solvent"].agreed == 1


def test_relaxed_mode_reaches_agreement_that_exact_mode_misses():
    ours = {"PMC1": {"mof": "MIL-101(Cr)"}}
    reference = {"PMC1": {"mof": "MIL-101"}}
    assert agreement_report(ours, reference, mode="exact").agreement_rate == 0.0
    assert agreement_report(ours, reference, mode="relaxed").agreement_rate == 1.0


def test_compare_record_reports_a_verdict_per_field():
    verdicts, disagreements = compare_record(
        "PMC1",
        {"linker": "H3BTC", "solvent": "ethanol"},
        {"linker": "trimesic acid", "solvent": "DMF", "temperature": ""},
    )
    assert verdicts == {
        "linker": "agree",
        "solvent": "disagree",
        "temperature": "not_comparable",
    }
    assert [d.field for d in disagreements] == ["solvent"]


def test_agreement_result_is_structured_data():
    ours = {"PMC1": {"linker": "H3BTC", "solvent": "ethanol"}}
    reference = {"PMC1": {"linker": "trimesic acid", "solvent": "DMF"}}
    result = agreement_report(ours, reference, mode="exact")

    frame = result.to_frame()
    assert list(frame["field"])[-1] == "overall"
    assert json.loads(json.dumps(result.as_dict()))["agreement_rate"] == 0.5
