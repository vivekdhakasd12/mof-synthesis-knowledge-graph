"""The experiment runner: passages in, extraction results out.

This is the engine every research question is answered from. Given a set of passages and a
set of extractors, it runs each extractor over each passage and records what came out
together with what it cost, so that accuracy, cost and latency can all be reported from one
artefact rather than assembled by hand afterwards.

Three design choices worth defending:

1. **Resumability.** Runs are keyed by (passage_id, extractor) and an existing results file
   is read back before starting. A commercial-model run over thousands of passages cannot be
   allowed to lose everything to one network error, and rerunning it would cost real money a
   second time. Combined with the response cache in the extractors themselves, an
   interrupted run resumes almost free.

2. **Failures are recorded, never raised.** An extractor that dies on one awkward passage
   must not abort a multi-hour run. Every result row carries an `errors` list, and a row with
   zero triples and a populated error is a genuine, reportable finding rather than a gap in
   the data.

3. **Extractors are constructed lazily by name.** The runner does not import the LLM or
   baseline modules at import time, so the pipeline stays usable (and testable) even when a
   provider SDK is missing or an API key is absent.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Iterable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import typer
from loguru import logger
from pydantic import BaseModel, Field

from src.extraction.extractor_base import Extractor, Triple

app = typer.Typer(add_completion=False)

REPO = Path(__file__).resolve().parents[1]
PASSAGES_DEFAULT = REPO / "data" / "processed" / "passages.jsonl"
RESULTS_DEFAULT = REPO / "data" / "processed" / "results.jsonl"


class ResultRecord(BaseModel):
    """One extractor applied to one passage: the atomic unit of the experiment."""

    passage_id: str
    paper_id: str
    section_name: str | None = None
    extractor: str
    triples: list[dict[str, Any]] = Field(default_factory=list)
    n_triples: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    errors: list[str] = Field(default_factory=list)
    run_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds"))

    @property
    def key(self) -> tuple[str, str]:
        return (self.passage_id, self.extractor)


def load_passages(path: Path = PASSAGES_DEFAULT, *, synthesis_only: bool = True) -> list[dict]:
    """Load passages as plain dicts.

    Deliberately dicts rather than the Passage model: the runner only needs a handful of
    fields, and staying schema-loose here means a change to Passage cannot break a run that
    is already in flight.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Build it first with: "
            "python -m src.ingestion.segment --synthesis-only"
        )
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            if synthesis_only and not row.get("is_synthesis", False):
                continue
            rows.append(row)
    return rows


def load_done(path: Path) -> set[tuple[str, str]]:
    """Read back which (passage, extractor) pairs already have a result."""
    if not path.exists():
        return set()
    done: set[tuple[str, str]] = set()
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                done.add((row["passage_id"], row["extractor"]))
            except (json.JSONDecodeError, KeyError):
                continue  # a truncated final line from an interrupted run is expected
    return done


def run_one(extractor: Extractor, passage: dict) -> ResultRecord:
    """Apply one extractor to one passage, capturing cost, latency and any failure."""
    text = passage.get("text", "")
    paper_id = passage.get("paper_id", "")
    section = passage.get("section_name")
    started = time.perf_counter()
    try:
        result = extractor.extract(text, paper_id=paper_id, section=section)
        triples: Sequence[Triple] = result.triples
        errors = list(result.errors)
        cost = float(result.cost_usd)
        # Trust the extractor's own latency when it reports one (it knows about cache hits),
        # otherwise fall back to wall clock.
        latency = float(result.latency_ms) or (time.perf_counter() - started) * 1000.0
    except Exception as exc:
        # The Extractor contract forbids raising, so reaching here is itself a finding.
        triples, errors = [], [f"CONTRACT VIOLATION, extract() raised: {type(exc).__name__}: {exc}"]
        cost = 0.0
        latency = (time.perf_counter() - started) * 1000.0
        logger.error("{} raised on {}: {}", extractor.name, passage.get("passage_id"), exc)

    return ResultRecord(
        passage_id=passage.get("passage_id", ""),
        paper_id=paper_id,
        section_name=section,
        extractor=extractor.name,
        triples=[t.to_dict() for t in triples],
        n_triples=len(triples),
        cost_usd=cost,
        latency_ms=latency,
        errors=errors,
    )


def run(
    extractors: Iterable[Extractor],
    passages: list[dict],
    *,
    out: Path = RESULTS_DEFAULT,
    resume: bool = True,
    limit: int | None = None,
) -> list[ResultRecord]:
    """Run every extractor over every passage, appending results as they complete.

    Results are flushed after each row so that killing the process loses at most one call.
    """
    extractors = list(extractors)
    if limit is not None:
        passages = passages[:limit]

    done = load_done(out) if resume else set()
    if done:
        logger.info("resuming: {} results already present in {}", len(done), out)

    out.parent.mkdir(parents=True, exist_ok=True)
    records: list[ResultRecord] = []
    total = len(extractors) * len(passages)
    n = 0
    spend = 0.0

    with out.open("a" if resume else "w", encoding="utf-8") as fh:
        for extractor in extractors:
            for passage in passages:
                n += 1
                pid = passage.get("passage_id", "")
                if (pid, extractor.name) in done:
                    continue
                rec = run_one(extractor, passage)
                fh.write(rec.model_dump_json() + "\n")
                fh.flush()
                records.append(rec)
                spend += rec.cost_usd
                if n % 25 == 0 or rec.errors:
                    logger.info(
                        "[{}/{}] {} | {} triples | ${:.4f} cumulative{}",
                        n,
                        total,
                        extractor.name,
                        rec.n_triples,
                        spend,
                        f" | errors: {rec.errors[:1]}" if rec.errors else "",
                    )

    logger.info(
        "run complete: {} new results, {} triples, ${:.4f} total",
        len(records),
        sum(r.n_triples for r in records),
        spend,
    )
    return records


def build_extractor(spec: str) -> Extractor:
    """Construct an extractor from a short spec string.

    Specs:
      rule_based
      openai:<model>:<strategy>      for example openai:gpt-4o:schema_guided
      anthropic:<model>:<strategy>
      groq:<model>:<strategy>

    Imported lazily so that a missing SDK or absent API key cannot break the whole module.
    """
    spec = spec.strip()
    if spec in {"rule_based", "rule"}:
        from src.extraction.rule_based import RuleBasedExtractor

        return RuleBasedExtractor()

    parts = spec.split(":")
    if len(parts) != 3:
        raise ValueError(
            f"cannot parse extractor spec {spec!r}. "
            "Use 'rule_based' or '<provider>:<model>:<strategy>'."
        )
    provider, model, strategy = parts
    from src.extraction.llm_extractor import (
        AnthropicClient,
        GroqClient,
        LLMClient,
        LLMExtractor,
        OpenAIClient,
    )

    # Typed as factories rather than as classes: the Anthropic client does not share the
    # OpenAI-compatible base, so without this annotation the dict widens to `object` and
    # the constructor call below loses its type guarantee.
    clients: dict[str, Callable[[], LLMClient]] = {
        "openai": OpenAIClient,
        "anthropic": AnthropicClient,
        "groq": GroqClient,
    }
    if provider not in clients:
        raise ValueError(f"unknown provider {provider!r}. Known providers: {sorted(clients)}")
    # Clients are stateless: the model travels with each generate() call, so a single
    # instance per provider is all that is ever needed.
    return LLMExtractor(clients[provider](), strategy, model)


def summarise(records: Sequence[ResultRecord]) -> dict[str, dict[str, float]]:
    """Per-extractor totals, the headline operational numbers for the report."""
    out: dict[str, dict[str, float]] = {}
    for r in records:
        s = out.setdefault(
            r.extractor,
            {"passages": 0.0, "triples": 0.0, "cost_usd": 0.0, "latency_ms": 0.0, "errors": 0.0},
        )
        s["passages"] += 1
        s["triples"] += r.n_triples
        s["cost_usd"] += r.cost_usd
        s["latency_ms"] += r.latency_ms
        s["errors"] += 1 if r.errors else 0
    for s in out.values():
        if s["passages"]:
            s["mean_triples"] = round(s["triples"] / s["passages"], 2)
            s["mean_latency_ms"] = round(s["latency_ms"] / s["passages"], 1)
    return out


@app.command()
def main(
    extractors: str = typer.Option("rule_based", help="Comma separated extractor specs."),
    passages: Path = typer.Option(PASSAGES_DEFAULT, help="Passages JSONL."),
    out: Path = typer.Option(RESULTS_DEFAULT, help="Results JSONL."),
    limit: int | None = typer.Option(None, help="Only the first N passages (for smoke runs)."),
    all_passages: bool = typer.Option(False, help="Include non-synthesis passages too."),
    no_resume: bool = typer.Option(False, help="Ignore existing results and start fresh."),
) -> None:
    specs = [s for s in extractors.split(",") if s.strip()]
    built = [build_extractor(s) for s in specs]
    rows = load_passages(passages, synthesis_only=not all_passages)
    typer.echo(f"{len(rows)} passages x {len(built)} extractors")
    records = run(built, rows, out=out, resume=not no_resume, limit=limit)
    for name, stats in summarise(records).items():
        typer.echo(f"  {name}: {stats}")


if __name__ == "__main__":
    app()
