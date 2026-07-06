"""Unified Extractor interface.

Every extractor (LLM, ChemDataExtractor, MatSciBERT) returns the same Triple shape
so they can be evaluated against a common gold standard.

The type Literals below mirror configs/ontology.json (v0.2, MOF-specific), which is
the source of truth; tests/test_extractor_base.py enforces the match.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal

EntityType = Literal[
    "MOF",
    "MetalPrecursor",
    "OrganicLinker",
    "Solvent",
    "SynthesisMethod",
    "Condition",
    "Property",
    "Application",
    "Paper",
]
RelationType = Literal[
    "USES_PRECURSOR",
    "USES_LINKER",
    "SYNTHESIZED_BY",
    "IN_SOLVENT",
    "AT_CONDITION",
    "HAS_PROPERTY",
    "MEASURED_AT",
    "USED_IN",
    "MENTIONED_IN",
]
Confidence = Literal["high", "medium", "low"]


@dataclass(frozen=True)
class Entity:
    type: EntityType
    name: str
    span: tuple[int, int] | None = None  # char offsets in source passage


@dataclass(frozen=True)
class Triple:
    subject: Entity
    relation: RelationType
    object: Entity
    evidence: str
    confidence: Confidence = "medium"
    source_paper_id: str | None = None
    source_section: str | None = None
    extractor: str = "unknown"  # set by subclass

    def to_dict(self) -> dict:
        return {
            "subject": {
                "type": self.subject.type,
                "name": self.subject.name,
                "span": self.subject.span,
            },
            "relation": self.relation,
            "object": {
                "type": self.object.type,
                "name": self.object.name,
                "span": self.object.span,
            },
            "evidence": self.evidence,
            "confidence": self.confidence,
            "source_paper_id": self.source_paper_id,
            "source_section": self.source_section,
            "extractor": self.extractor,
        }


@dataclass
class ExtractionResult:
    triples: list[Triple] = field(default_factory=list)
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    errors: list[str] = field(default_factory=list)


class Extractor(ABC):
    """Subclass for each extraction strategy."""

    name: str

    @abstractmethod
    def extract(
        self,
        passage: str,
        *,
        paper_id: str | None = None,
        section: str | None = None,
    ) -> ExtractionResult:
        """Extract triples from a single passage. Must not raise; collect errors instead."""
        ...
