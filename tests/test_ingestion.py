"""Offline tests for the ingestion pipeline.

No network: the JATS parser is exercised against an inline fixture so the suite is
fast and deterministic. Live Europe PMC access is covered by the build_corpus CLI,
not the unit tests.
"""

from __future__ import annotations

import json

from src.ingestion.models import CorpusDoc, Section
from src.ingestion.parse import parse_fulltext

JATS_FIXTURE = b"""<?xml version="1.0" encoding="UTF-8"?>
<article article-type="research-article">
  <front>
    <article-meta>
      <article-id pub-id-type="pmcid">PMC9999999</article-id>
      <article-id pub-id-type="doi">10.1021/example.mof.001</article-id>
      <title-group><article-title>Solvothermal synthesis of
      <italic>HKUST-1</italic></article-title></title-group>
      <permissions><license license-type="open-access">
        <license-p>This is an open access article under the CC BY licence.</license-p>
      </license></permissions>
      <abstract><p>We report a MOF made from copper nitrate and trimesic acid.</p></abstract>
    </article-meta>
  </front>
  <body>
    <sec><title>Introduction</title><p>MOFs are porous.</p></sec>
    <sec>
      <title>Experimental</title>
      <p>Cu(NO3)2 and H3BTC were dissolved in DMF and heated at 120 degrees C.</p>
      <sec><title>Characterisation</title><p>PXRD confirmed the structure.</p></sec>
    </sec>
  </body>
</article>"""


def test_parse_extracts_metadata_and_provenance():
    doc = parse_fulltext(JATS_FIXTURE)
    assert doc is not None
    assert doc.pmcid == "PMC9999999"
    assert doc.doi == "10.1021/example.mof.001"
    assert doc.paper_id == "PMC9999999"  # canonical id prefers the PMCID
    assert doc.source == "europepmc"
    assert "HKUST-1" in doc.title
    assert doc.license and "CC BY" in doc.license
    assert doc.retrieved_at  # provenance timestamp is always set


def test_parse_captures_sections_including_abstract():
    doc = parse_fulltext(JATS_FIXTURE)
    names = [s.name for s in doc.sections]
    assert names[0] == "Abstract"
    assert "Introduction" in names
    assert "Experimental" in names


def test_experimental_section_flattens_nested_paragraphs():
    doc = parse_fulltext(JATS_FIXTURE)
    exp = doc.section("experimental")
    assert exp is not None
    # Inline <italic> must not fragment text; nested <sec> <p> must be included.
    assert "Cu(NO3)2 and H3BTC" in exp.text
    assert "PXRD confirmed" in exp.text


def test_section_lookup_targets_synthesis():
    doc = parse_fulltext(JATS_FIXTURE)
    assert doc.section("experimental", "synthesis") is not None
    assert doc.section("nonexistent-heading") is None


def test_empty_or_garbage_xml_returns_none():
    assert parse_fulltext(b"") is None
    assert parse_fulltext(b"   ") is None
    assert parse_fulltext(b"<not-xml") is None


def test_corpusdoc_jsonl_roundtrip():
    doc = CorpusDoc(
        paper_id="PMC1",
        title="t",
        source="europepmc",
        sections=[Section(name="Abstract", text="hello")],
    )
    line = doc.model_dump_json()
    back = CorpusDoc(**json.loads(line))
    assert back == doc
    assert back.full_text.startswith("## Abstract")
    assert back.n_chars == len("hello")
