"""Europe PMC access: search for open-access MOF papers and fetch full text.

Europe PMC is the primary corpus source because its open-access subset exposes
structured JATS full text (labelled sections), which is far more reliable than
scraping and PDF-parsing publisher pages. Fetched XML is cached to disk so a paper
is never downloaded twice (project reproducibility rule).
"""

from __future__ import annotations

import time
from pathlib import Path

import requests

BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"
USER_AGENT = "case-study-2-mof-kg/0.1 (mailto:dhakadvivu5@gmail.com)"

# Open-access + full-text + hosted in Europe PMC (so fullTextXML is available).
DEFAULT_QUERY = (
    "(metal-organic framework AND synthesis) AND OPEN_ACCESS:y AND HAS_FT:y AND IN_EPMC:y"
)


def search(query: str = DEFAULT_QUERY, limit: int = 25) -> list[dict]:
    """Return up to `limit` search hits as dicts (id, source, pmcid, doi, title, license).

    Paginates via Europe PMC's cursorMark. Network errors raise; the caller decides
    how to handle a failed search.
    """
    results: list[dict] = []
    cursor = "*"
    while len(results) < limit:
        page_size = min(100, limit - len(results))
        params: dict[str, str | int] = {
            "query": query,
            "format": "json",
            "pageSize": page_size,
            "cursorMark": cursor,
            "resultType": "lite",
        }
        resp = requests.get(
            f"{BASE}/search",
            params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=60,
        )
        resp.raise_for_status()
        payload = resp.json()
        hits = payload.get("resultList", {}).get("result", [])
        if not hits:
            break
        for h in hits:
            results.append(
                {
                    "id": h.get("id"),
                    "source": h.get("source"),
                    "pmcid": h.get("pmcid"),
                    "doi": h.get("doi"),
                    "title": h.get("title", ""),
                    "license": h.get("license"),
                }
            )
        next_cursor = payload.get("nextCursorMark")
        if not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor
    return results[:limit]


def fetch_fulltext_xml(pmcid: str, cache_dir: Path | None = None) -> bytes | None:
    """Fetch (and cache) the JATS full-text XML for a PMCID.

    Returns None when Europe PMC has no full-text XML for the id (some OA records are
    only available as PDF at the publisher). `requests` follows the endpoint's
    redirect automatically, which a bare curl without -L does not.
    """
    if not pmcid:
        return None

    cache_path = cache_dir / f"{pmcid}.xml" if cache_dir else None
    if cache_path and cache_path.exists():
        data = cache_path.read_bytes()
        return data or None

    resp = requests.get(
        f"{BASE}/{pmcid}/fullTextXML",
        headers={"User-Agent": USER_AGENT},
        timeout=90,
    )
    if resp.status_code != 200 or not resp.content.strip():
        return None

    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(resp.content)
    time.sleep(0.34)  # be polite to the API (~3 req/s)
    return resp.content
