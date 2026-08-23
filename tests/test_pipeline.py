"""Tests for the experiment runner.

The runner is what actually produces the numbers the thesis reports, so the properties
tested here are the ones whose failure would be expensive rather than merely annoying:
resume must not redo paid work, a crashing extractor must not abort a long run, and a
contract violation must be recorded rather than swallowed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.extraction.extractor_base import Entity, ExtractionResult, Extractor, Triple
from src.pipeline import (
    ResultRecord,
    build_extractor,
    load_done,
    load_passages,
    run,
    run_one,
    summarise,
)


def _triple(name: str = "HKUST-1") -> Triple:
    return Triple(
        subject=Entity(type="MOF", name=name),
        relation="USES_PRECURSOR",
        object=Entity(type="MetalPrecursor", name="Cu(NO3)2"),
        evidence=f"{name} was made from Cu(NO3)2.",
        source_paper_id="PMC1",
        source_section="Experimental",
        extractor="fake",
    )


class FakeExtractor(Extractor):
    name = "fake"

    def __init__(self, n_triples: int = 1, cost: float = 0.01) -> None:
        self.n_triples = n_triples
        self.cost = cost
        self.calls = 0

    def extract(self, passage, *, paper_id=None, section=None) -> ExtractionResult:  # type: ignore[no-untyped-def]
        self.calls += 1
        return ExtractionResult(
            triples=[_triple() for _ in range(self.n_triples)],
            cost_usd=self.cost,
            latency_ms=12.5,
        )


class RaisingExtractor(Extractor):
    """Violates the contract on purpose, to prove the runner survives it."""

    name = "raiser"

    def extract(self, passage, *, paper_id=None, section=None) -> ExtractionResult:  # type: ignore[no-untyped-def]
        raise RuntimeError("upstream exploded")


def _passages(n: int = 3) -> list[dict]:
    return [
        {
            "passage_id": f"p{i}",
            "paper_id": "PMC1",
            "section_name": "Experimental",
            "text": f"passage {i}",
            "is_synthesis": True,
        }
        for i in range(n)
    ]


def test_run_one_captures_triples_cost_and_latency() -> None:
    rec = run_one(FakeExtractor(n_triples=2, cost=0.03), _passages(1)[0])
    assert rec.n_triples == 2
    assert len(rec.triples) == 2
    assert rec.cost_usd == pytest.approx(0.03)
    assert rec.latency_ms == pytest.approx(12.5)
    assert rec.errors == []
    assert rec.passage_id == "p0"


def test_a_raising_extractor_is_recorded_not_propagated() -> None:
    """The contract forbids raising, so a raise is a finding the run must survive."""
    rec = run_one(RaisingExtractor(), _passages(1)[0])
    assert rec.n_triples == 0
    assert rec.errors and "CONTRACT VIOLATION" in rec.errors[0]
    assert "upstream exploded" in rec.errors[0]


def test_run_writes_one_row_per_passage(tmp_path: Path) -> None:
    out = tmp_path / "results.jsonl"
    records = run([FakeExtractor()], _passages(3), out=out, resume=False)
    assert len(records) == 3
    lines = [json.loads(x) for x in out.read_text().splitlines() if x.strip()]
    assert len(lines) == 3
    assert {row["passage_id"] for row in lines} == {"p0", "p1", "p2"}


def test_resume_does_not_repeat_completed_work(tmp_path: Path) -> None:
    """The property that stops an interrupted paid run from being billed twice."""
    out = tmp_path / "results.jsonl"
    first = FakeExtractor()
    run([first], _passages(3), out=out, resume=False)
    assert first.calls == 3

    second = FakeExtractor()
    new_records = run([second], _passages(3), out=out, resume=True)
    assert second.calls == 0, "already-completed pairs must not be re-run"
    assert new_records == []


def test_resume_only_skips_the_pairs_already_present(tmp_path: Path) -> None:
    out = tmp_path / "results.jsonl"
    run([FakeExtractor()], _passages(2), out=out, resume=False)
    third = FakeExtractor()
    run([third], _passages(3), out=out, resume=True)
    assert third.calls == 1, "only the genuinely new passage should be processed"


def test_load_done_survives_a_truncated_final_line(tmp_path: Path) -> None:
    """An interrupted run leaves a half-written line; resume must tolerate it."""
    out = tmp_path / "results.jsonl"
    out.write_text(
        json.dumps({"passage_id": "p0", "extractor": "fake"}) + "\n" + '{"passage_id": "p1", "extr'
    )
    done = load_done(out)
    assert done == {("p0", "fake")}


def test_load_passages_filters_to_synthesis_by_default(tmp_path: Path) -> None:
    path = tmp_path / "passages.jsonl"
    rows = _passages(2) + [
        {
            "passage_id": "p9",
            "paper_id": "PMC1",
            "section_name": "Introduction",
            "text": "background",
            "is_synthesis": False,
        }
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    assert len(load_passages(path)) == 2
    assert len(load_passages(path, synthesis_only=False)) == 3


def test_load_passages_gives_an_actionable_error_when_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="src.ingestion.segment"):
        load_passages(tmp_path / "nope.jsonl")


def test_build_extractor_returns_the_rule_baseline() -> None:
    assert build_extractor("rule_based").name == "rule_based_v1"


@pytest.mark.parametrize("spec", ["nonsense", "openai:gpt-4o", "a:b:c:d"])
def test_build_extractor_rejects_malformed_specs(spec: str) -> None:
    with pytest.raises(ValueError):
        build_extractor(spec)


def test_build_extractor_rejects_an_unknown_provider() -> None:
    with pytest.raises(ValueError, match="unknown provider"):
        build_extractor("notaprovider:some-model:zero_shot")


def test_summarise_aggregates_per_extractor() -> None:
    records = [
        ResultRecord(
            passage_id=f"p{i}",
            paper_id="PMC1",
            extractor="fake",
            n_triples=2,
            cost_usd=0.01,
            latency_ms=10.0,
            errors=["boom"] if i == 0 else [],
        )
        for i in range(3)
    ]
    stats = summarise(records)["fake"]
    assert stats["passages"] == 3
    assert stats["triples"] == 6
    assert stats["cost_usd"] == pytest.approx(0.03)
    assert stats["errors"] == 1
    assert stats["mean_triples"] == pytest.approx(2.0)
    assert stats["mean_latency_ms"] == pytest.approx(10.0)
