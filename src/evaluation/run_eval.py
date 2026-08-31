"""Score every extractor in a results file against the hand-annotated gold standard.

Kept as a module rather than a notebook so the numbers in the report can be regenerated
with one command and cannot drift from the data they came from.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import typer
from loguru import logger

from src.evaluation.metrics import evaluate
from src.extraction.extractor_base import Entity, Triple

app = typer.Typer(add_completion=False)

REPO = Path(__file__).resolve().parents[2]
GOLD = REPO / "data" / "annotations" / "gold.jsonl"
RESULTS = REPO / "data" / "processed" / "results_gold.jsonl"


def _entity(etype: str, name: str, span: Any) -> Entity:
    return Entity(type=etype, name=name, span=tuple(span) if span else None)


def load_gold(path: Path = GOLD) -> list[Triple]:
    """Gold triples, flattened from the annotation tool's per-passage records.

    The tool writes flat subject_/object_ fields; the evaluation works on Triple objects,
    so the conversion happens here in one place rather than at every call site.
    """
    out: list[Triple] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        for t in rec.get("triples", []):
            out.append(
                Triple(
                    subject=_entity(t["subject_type"], t["subject_name"], t.get("subject_span")),
                    relation=t["relation"],
                    object=_entity(t["object_type"], t["object_name"], t.get("object_span")),
                    evidence=t.get("evidence", ""),
                    confidence=t.get("confidence", "medium"),
                    source_paper_id=rec["passage_id"],  # passage-level scoping, see below
                    source_section=rec.get("section"),
                    extractor="gold",
                )
            )
    return out


def load_predictions(path: Path = RESULTS) -> dict[str, list[Triple]]:
    """Predicted triples grouped by extractor name.

    `source_paper_id` is deliberately set to the PASSAGE id, not the paper id. Matching is
    scoped per (paper, section) by `passage_key`, and several gold passages come from the
    same paper and section, so using the paper id would let a prediction from one passage be
    credited against a gold triple from another and silently inflate every score.
    """
    by: dict[str, list[Triple]] = defaultdict(list)
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        for t in row.get("triples", []):
            by[row["extractor"]].append(
                Triple(
                    subject=_entity(
                        t["subject"]["type"], t["subject"]["name"], t["subject"].get("span")
                    ),
                    relation=t["relation"],
                    object=_entity(
                        t["object"]["type"], t["object"]["name"], t["object"].get("span")
                    ),
                    evidence=t.get("evidence", ""),
                    confidence=t.get("confidence", "medium"),
                    source_paper_id=row["passage_id"],
                    source_section=row.get("section_name"),
                    extractor=row["extractor"],
                )
            )
    return dict(by)


def operational(path: Path = RESULTS) -> dict[str, dict[str, float]]:
    """Cost, latency and failure counts per extractor, straight from the run."""
    agg: dict[str, dict[str, float]] = defaultdict(
        lambda: {"calls": 0.0, "cost_usd": 0.0, "latency_ms": 0.0, "failed_calls": 0.0}
    )
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        a = agg[row["extractor"]]
        a["calls"] += 1
        a["cost_usd"] += row.get("cost_usd", 0.0)
        a["latency_ms"] += row.get("latency_ms", 0.0)
        if any("client call failed" in e for e in row.get("errors", [])):
            a["failed_calls"] += 1
    for a in agg.values():
        a["mean_latency_ms"] = round(a["latency_ms"] / a["calls"], 1) if a["calls"] else 0.0
    return dict(agg)


@app.command()
def main(
    gold: Path = typer.Option(GOLD),
    results: Path = typer.Option(RESULTS),
    mode: str = typer.Option("relaxed", help="exact or relaxed matching"),
    out: Path = typer.Option(REPO / "data" / "processed" / "evaluation.json"),
) -> None:
    gold_triples = load_gold(gold)
    preds = load_predictions(results)
    ops = operational(results)
    logger.info("gold triples: {} | extractors: {}", len(gold_triples), len(preds))

    report: dict[str, Any] = {"mode": mode, "n_gold_triples": len(gold_triples), "extractors": {}}
    for name in sorted(set(preds) | set(ops)):
        res = evaluate(preds.get(name, []), gold_triples, mode=mode)  # type: ignore[arg-type]
        o = ops.get(name, {})
        report["extractors"][name] = {
            "micro_precision": res.micro.precision,
            "micro_recall": res.micro.recall,
            "micro_f1": res.micro.f1,
            "macro_f1": res.macro_f1,
            "per_field": {k: v.as_dict() for k, v in res.per_field.items()},
            "subject_agnostic_relations": list(res.subject_agnostic_relations),
            "cost_usd": round(o.get("cost_usd", 0.0), 4),
            "mean_latency_ms": o.get("mean_latency_ms", 0.0),
            "failed_calls": int(o.get("failed_calls", 0)),
            "calls": int(o.get("calls", 0)),
        }
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    typer.echo(f"wrote {out}")


if __name__ == "__main__":
    app()
