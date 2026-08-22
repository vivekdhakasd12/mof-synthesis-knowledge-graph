"""Corpus data model.

One `CorpusDoc` per source paper. Provenance is mandatory (project domain rule):
every document carries its source, an id, and, where available, a DOI and licence,
so any downstream triple can be traced back to the paper and section it came from.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Section(BaseModel):
    """A titled block of body text (e.g. Abstract, Experimental, Results)."""

    name: str
    text: str


class CorpusDoc(BaseModel):
    """A single parsed paper ready for extraction.

    `paper_id` is the canonical, stable identifier used everywhere downstream
    (KG provenance edges, the evaluation gold standard, the call cache).
    """

    paper_id: str
    title: str
    source: str  # e.g. "europepmc"
    doi: str | None = None
    pmcid: str | None = None
    license: str | None = None
    sections: list[Section] = Field(default_factory=list)
    retrieved_at: str = Field(default_factory=_utcnow_iso)

    @property
    def full_text(self) -> str:
        """Sections joined with markdown-style headings, in reading order."""
        return "\n\n".join(f"## {s.name}\n{s.text}".strip() for s in self.sections)

    @property
    def n_chars(self) -> int:
        return sum(len(s.text) for s in self.sections)

    def section(self, *keywords: str) -> Section | None:
        """First section whose title contains any of `keywords` (case-insensitive).

        Used downstream to target the synthesis/experimental section, which carries
        most MOF synthesis records.
        """
        lowered = [k.lower() for k in keywords]
        for s in self.sections:
            title = s.name.lower()
            if any(k in title for k in lowered):
                return s
        return None
