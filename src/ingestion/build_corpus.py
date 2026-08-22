"""Build the MOF paper corpus: search Europe PMC, fetch full text, write JSONL.

Run:
    python -m src.ingestion.build_corpus --limit 10
    python -m src.ingestion.build_corpus --query "ZIF-8 synthesis AND OPEN_ACCESS:y ..."

Output: one `CorpusDoc` per line in data/processed/corpus.jsonl. Raw XML is cached
under data/raw/europepmc/ (both paths are gitignored). Open-access papers only.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import typer
from loguru import logger

from .europepmc import DEFAULT_QUERY, fetch_fulltext_xml, search
from .models import CorpusDoc
from .parse import parse_fulltext

app = typer.Typer(add_completion=False)

REPO = Path(__file__).resolve().parents[2]
RAW_DIR = REPO / "data" / "raw" / "europepmc"
OUT_DEFAULT = REPO / "data" / "processed" / "corpus.jsonl"


def build(
    query: str = DEFAULT_QUERY,
    limit: int = 10,
    out: Path = OUT_DEFAULT,
    cache_dir: Path = RAW_DIR,
) -> list[CorpusDoc]:
    """Fetch and parse up to `limit` OA papers; write them to `out`. Returns the docs."""
    logger.info("searching Europe PMC (limit={}): {}", limit, query)
    # Over-fetch: not every OA hit exposes full-text XML, so search for more than we need.
    hits = search(query=query, limit=limit * 3)
    logger.info("{} candidate hits", len(hits))

    docs: list[CorpusDoc] = []
    errors: list[str] = []
    for h in hits:
        if len(docs) >= limit:
            break
        pmcid = h.get("pmcid")
        if not pmcid:
            continue
        try:
            xml = fetch_fulltext_xml(pmcid, cache_dir=cache_dir)
            if xml is None:
                errors.append(f"{pmcid}: no full-text XML")
                continue
            doc = parse_fulltext(xml)
            if doc is None:
                errors.append(f"{pmcid}: unparseable / no body text")
                continue
            # Prefer the search-result DOI/licence if the XML omitted them.
            doc.doi = doc.doi or h.get("doi")
            doc.license = doc.license or h.get("license")
            docs.append(doc)
            logger.info(
                "  [{}/{}] {} | {} sections | {} chars | {}",
                len(docs),
                limit,
                doc.paper_id,
                len(doc.sections),
                doc.n_chars,
                (doc.title[:50] + "...") if len(doc.title) > 50 else doc.title,
            )
        except Exception as exc:  # network/parse hiccup: skip, do not abort the run
            errors.append(f"{pmcid}: {type(exc).__name__}: {exc}")

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for doc in docs:
            fh.write(doc.model_dump_json() + "\n")

    logger.info("wrote {} docs -> {}", len(docs), out)
    if errors:
        logger.warning("{} skipped (see below)", len(errors))
        for e in errors[:10]:
            logger.warning("  skip {}", e)
    lic = Counter((d.license or "unknown") for d in docs)
    logger.info("licence breakdown: {}", dict(lic))
    return docs


@app.command()
def main(
    query: str = typer.Option(DEFAULT_QUERY, help="Europe PMC query string."),
    limit: int = typer.Option(10, help="Number of papers to collect."),
    out: Path = typer.Option(OUT_DEFAULT, help="Output JSONL path."),
) -> None:
    docs = build(query=query, limit=limit, out=out)
    total_chars = sum(d.n_chars for d in docs)
    typer.echo(f"Collected {len(docs)} papers, {total_chars:,} characters -> {out}")


if __name__ == "__main__":
    app()
