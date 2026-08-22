"""Parse Europe PMC JATS full-text XML into a `CorpusDoc`.

JATS articles may or may not declare an XML namespace, so every XPath uses the
`{*}` wildcard to match a tag in any (or no) namespace. Body text is flattened
with `itertext()` so inline markup (italics, formulae, links) does not fragment a
sentence, which matters for downstream sentence-level extraction.
"""

from __future__ import annotations

from lxml import etree

from .models import CorpusDoc, Section


def _text(node: etree._Element | None) -> str:
    """All descendant text of a node, whitespace-normalised."""
    if node is None:
        return ""
    joined = "".join(str(t) for t in node.itertext())
    return " ".join(joined.split())


def _paragraphs(sec: etree._Element) -> str:
    """Concatenate the <p> paragraphs directly and indirectly under a <sec>."""
    parts = [_text(p) for p in sec.findall(".//{*}p")]
    return "\n".join(p for p in parts if p)


def _sec_title(sec: etree._Element) -> str:
    title = sec.find("{*}title")
    return _text(title) if title is not None else "Untitled section"


def parse_fulltext(xml_bytes: bytes) -> CorpusDoc | None:
    """Turn a JATS full-text XML document into a `CorpusDoc`.

    Returns None if the XML is empty or has no usable body text, so the caller can
    skip it without raising.
    """
    if not xml_bytes or not xml_bytes.strip():
        return None
    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError:
        return None

    title = _text(root.find(".//{*}article-title")) or "Untitled"

    doi = None
    for aid in root.findall(".//{*}article-id"):
        if aid.get("pub-id-type") == "doi":
            doi = _text(aid)
            break

    pmcid = None
    for aid in root.findall(".//{*}article-id"):
        if aid.get("pub-id-type") == "pmcid" or aid.get("pub-id-type") == "pmc":
            pmcid = _text(aid)
            break

    lic_node = root.find(".//{*}permissions/{*}license")
    license_ = _text(lic_node) or None
    if license_ is None:
        lic_ref = root.find(".//{*}permissions/{*}license/{*}license-p")
        license_ = _text(lic_ref) or None

    sections: list[Section] = []

    abstract = root.find(".//{*}abstract")
    if abstract is not None:
        abs_text = _paragraphs(abstract) or _text(abstract)
        if abs_text:
            sections.append(Section(name="Abstract", text=abs_text))

    body = root.find(".//{*}body")
    if body is not None:
        for sec in body.findall("{*}sec"):
            text = _paragraphs(sec)
            if text:
                sections.append(Section(name=_sec_title(sec), text=text))
        # Some articles put body text in loose <p> outside any <sec>.
        loose = [_text(p) for p in body.findall("{*}p")]
        loose_text = "\n".join(p for p in loose if p)
        if loose_text:
            sections.append(Section(name="Body", text=loose_text))

    if not sections:
        return None

    paper_id = pmcid or (f"doi:{doi}" if doi else title[:40])
    return CorpusDoc(
        paper_id=paper_id,
        title=title,
        source="europepmc",
        doi=doi,
        pmcid=pmcid,
        license=license_,
        sections=sections,
    )
