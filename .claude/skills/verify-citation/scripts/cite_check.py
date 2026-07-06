#!/usr/bin/env python3
"""Look up a paper in live bibliographic sources (Crossref, OpenAlex, arXiv).

Stdlib only — no project dependencies. Exit code 0 = at least one record found.

Usage:
  python cite_check.py doi 10.1186/s13321-023-00764-2
  python cite_check.py title "MOF synthesis prediction data mining machine learning"
  python cite_check.py arxiv 2408.04665
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request

TIMEOUT = 20
UA = {"User-Agent": "case-study-2-cite-check/1.0 (mailto:dhakadvivu5@gmail.com)"}


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read()


def _fmt_authors(names: list[str]) -> str:
    if not names:
        return "(no authors listed)"
    shown = "; ".join(names[:3])
    return f"{shown}; et al. ({len(names)} total)" if len(names) > 3 else shown


def _print_record(source: str, title: str, authors: list[str], venue: str | None,
                  year, extra: str, link: str) -> None:
    print(f"[{source}]")
    print(f"  title  : {title}")
    print(f"  authors: {_fmt_authors(authors)}")
    print(f"  venue  : {venue or '?'} ({year or '?'}) {extra}".rstrip())
    print(f"  link   : {link}")


def _crossref_item(it: dict) -> None:
    authors = [f"{a.get('family', '?')}, {a.get('given', '')}".strip(", ")
               for a in it.get("author", [])]
    year = (it.get("issued", {}).get("date-parts") or [[None]])[0][0]
    vol = it.get("volume") or ""
    page = it.get("page") or it.get("article-number") or ""
    _print_record(
        "Crossref",
        (it.get("title") or ["?"])[0],
        authors,
        (it.get("container-title") or [None])[0],
        year,
        f"vol {vol} p.{page}".strip() if (vol or page) else "",
        f"https://doi.org/{it['DOI']}",
    )


def cmd_doi(doi: str) -> int:
    doi = doi.removeprefix("https://doi.org/").strip()
    if re.search(r"\.s\d{3}$", doi):
        print(f"WARNING: '{doi}' looks like a SUPPLEMENTARY-material DOI (.sNNN). "
              f"Retrying with the parent DOI.")
        doi = re.sub(r"\.s\d{3}$", "", doi)
    try:
        it = json.loads(_get(f"https://api.crossref.org/works/{urllib.parse.quote(doi)}"))["message"]
        _crossref_item(it)
        return 0
    except Exception as e:
        print(f"Crossref lookup failed for {doi}: {e}")
        return cmd_title(doi)  # last resort: search it as text


def cmd_title(query: str) -> int:
    found = 0
    try:
        items = json.loads(_get(
            "https://api.crossref.org/works?query.bibliographic="
            f"{urllib.parse.quote(query)}&rows=8"))["message"]["items"]
        # Supplementary-material records (.sNNN) shadow their parent paper in
        # bibliographic searches and carry no authors/venue — skip them.
        supp = [it for it in items if re.search(r"\.s\d{3}$", it.get("DOI", ""))]
        clean = [it for it in items if it not in supp]
        for it in clean[:3]:
            _crossref_item(it)
            found += 1
        if supp and not clean:
            parent = re.sub(r"\.s\d{3}$", "", supp[0]["DOI"])
            print(f"NOTE: only supplementary DOIs matched; trying parent {parent}")
            return cmd_doi(parent)
        if supp:
            print(f"  (skipped {len(supp)} supplementary-material record(s))")
    except Exception as e:
        print(f"Crossref search failed: {e}")
    try:
        results = json.loads(_get(
            f"https://api.openalex.org/works?search={urllib.parse.quote(query)}&per-page=3"))["results"]
        for w in results:
            src = (w.get("primary_location") or {}).get("source") or {}
            _print_record(
                "OpenAlex",
                w.get("title") or "?",
                [a["author"]["display_name"] for a in w.get("authorships", [])],
                src.get("display_name"),
                w.get("publication_year"),
                "",
                w.get("doi") or w.get("id", "?"),
            )
            found += 1
    except Exception as e:
        print(f"OpenAlex search failed: {e}")
    return 0 if found else 1


def cmd_arxiv(ident: str) -> int:
    ident = ident.removeprefix("arXiv:").strip()
    try:
        xml = _get(f"https://export.arxiv.org/api/query?id_list={urllib.parse.quote(ident)}").decode()
        entries = re.findall(r"<entry>.*?</entry>", xml, re.S)
        if not entries:
            print(f"arXiv: no entry for {ident}")
            return 1
        e = entries[0]
        title = re.sub(r"\s+", " ", re.search(r"<title>(.*?)</title>", e, re.S).group(1)).strip()
        authors = re.findall(r"<name>(.*?)</name>", e)
        year = re.search(r"<published>(\d{4})", e).group(1)
        _print_record("arXiv", title, authors, "arXiv preprint", year, "",
                      f"https://arxiv.org/abs/{ident}")
        return 0
    except Exception as e:
        print(f"arXiv lookup failed for {ident}: {e}")
        return 1


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doi").add_argument("value")
    sub.add_parser("title").add_argument("value")
    sub.add_parser("arxiv").add_argument("value")
    args = p.parse_args()
    return {"doi": cmd_doi, "title": cmd_title, "arxiv": cmd_arxiv}[args.cmd](args.value)


if __name__ == "__main__":
    sys.exit(main())
