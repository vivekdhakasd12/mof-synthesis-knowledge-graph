"""Load extracted triples into Neo4j with mandatory provenance.

Design notes worth defending in the report:

1. Every write is a MERGE on a normalised `key`, never a CREATE on the surface form.
   Papers write the same reagent a dozen ways, so keying on the raw string would produce
   a graph full of near-duplicate nodes and would make any cross-paper aggregation query
   (the point of building the graph at all) meaningless. Normalisation lives in
   src/normalize.py, shared with the evaluation code so both agree on identity.

2. Loading is idempotent. Re-running the loader over the same extractions must not
   multiply nodes or edges, otherwise a reproducibility rerun would silently change the
   graph statistics reported in the thesis.

3. Provenance is written as structure, not as a comment. Each entity gets a MENTIONED_IN
   edge to its Paper carrying section and evidence, and each relation edge carries the
   evidence sentence, extractor name and confidence. That makes "show me the sentence
   this claim came from" a one hop query, which the dashboard needs and which a grader
   is entitled to ask for.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Protocol

from loguru import logger

from src.extraction.extractor_base import Triple
from src.kg.schema import CONSTRAINTS, INDEXES
from src.normalize import normalize_by_type


class SessionLike(Protocol):
    """Minimal surface of a neo4j Session, so tests can inject a fake without a server."""

    def run(self, query: str, /, **kwargs: Any) -> Any: ...


class DriverLike(Protocol):
    def session(self, **kwargs: Any) -> Any: ...
    def close(self) -> None: ...


@dataclass
class LoadStats:
    """What a load actually did, for the reproducibility appendix."""

    papers: int = 0
    triples_in: int = 0
    triples_written: int = 0
    triples_skipped: int = 0
    nodes_merged: int = 0
    provenance_edges: int = 0
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "papers": self.papers,
            "triples_in": self.triples_in,
            "triples_written": self.triples_written,
            "triples_skipped": self.triples_skipped,
            "nodes_merged": self.nodes_merged,
            "provenance_edges": self.provenance_edges,
            "errors": self.errors[:20],
        }


def neo4j_config() -> tuple[str, str, str]:
    """Read connection settings from the environment (see .env.example)."""
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "")
    return uri, user, password


class KGLoader:
    """Writes triples into Neo4j. Accepts any driver satisfying DriverLike."""

    def __init__(self, driver: DriverLike, database: str | None = None) -> None:
        self.driver = driver
        self.database = database

    @classmethod
    def from_env(cls) -> KGLoader:
        """Build a loader from environment settings.

        Imported lazily so the rest of the package, and the whole test suite, does not
        require the neo4j driver or a running database.
        """
        from neo4j import GraphDatabase

        uri, user, password = neo4j_config()
        if not password:
            raise RuntimeError(
                "NEO4J_PASSWORD is not set. Copy .env.example to .env and set it, "
                "then start the database with: docker compose up -d"
            )
        return cls(GraphDatabase.driver(uri, auth=(user, password)))

    def _session(self) -> Any:
        return self.driver.session(database=self.database) if self.database else self.driver.session()

    def ensure_schema(self) -> None:
        """Apply uniqueness constraints and indexes. Safe to call repeatedly."""
        with self._session() as session:
            for stmt in CONSTRAINTS + INDEXES:
                session.run(stmt)
        logger.info("schema ensured ({} constraints, {} indexes)", len(CONSTRAINTS), len(INDEXES))

    def merge_paper(self, session: SessionLike, paper_id: str, **props: Any) -> None:
        """Create or update the Paper node that all provenance edges point at."""
        session.run(
            "MERGE (p:Paper {paper_id: $paper_id}) "
            "SET p.doi = coalesce($doi, p.doi), "
            "    p.title = coalesce($title, p.title), "
            "    p.license = coalesce($license, p.license), "
            "    p.source = coalesce($source, p.source)",
            paper_id=paper_id,
            doi=props.get("doi"),
            title=props.get("title"),
            license=props.get("license"),
            source=props.get("source"),
        )

    def _merge_entity(self, session: SessionLike, etype: str, name: str) -> str:
        """MERGE an entity node on its normalised key, keeping the surface form as an alias.

        Returns the key so the caller can link edges without a second lookup.
        """
        key = normalize_by_type(etype, name)
        session.run(
            f"MERGE (n:{etype} {{key: $key}}) "
            "SET n.name = coalesce(n.name, $name) "
            "SET n.aliases = CASE WHEN $name IN coalesce(n.aliases, []) "
            "                THEN n.aliases ELSE coalesce(n.aliases, []) + $name END",
            key=key,
            name=name,
        )
        return key

    def load_triples(
        self,
        triples: list[Triple],
        *,
        paper_props: dict[str, dict[str, Any]] | None = None,
    ) -> LoadStats:
        """Write triples plus their provenance. Idempotent.

        `paper_props` optionally maps paper_id to metadata (doi, title, license, source)
        so Paper nodes carry citable information rather than a bare id.
        """
        stats = LoadStats(triples_in=len(triples))
        papers_seen: set[str] = set()
        paper_props = paper_props or {}

        with self._session() as session:
            for t in triples:
                # Provenance is mandatory. A triple without a paper cannot be traced, so
                # it is rejected rather than written as an orphan.
                if not t.source_paper_id:
                    stats.triples_skipped += 1
                    stats.errors.append(f"missing source_paper_id: {t.subject.name} {t.relation}")
                    continue
                if t.relation == "MENTIONED_IN":
                    # Provenance is attached by this loader, never taken from an extractor.
                    stats.triples_skipped += 1
                    continue
                try:
                    pid = t.source_paper_id
                    if pid not in papers_seen:
                        self.merge_paper(session, pid, **paper_props.get(pid, {}))
                        papers_seen.add(pid)

                    skey = self._merge_entity(session, t.subject.type, t.subject.name)
                    okey = self._merge_entity(session, t.object.type, t.object.name)
                    stats.nodes_merged += 2

                    session.run(
                        f"MATCH (s:{t.subject.type} {{key: $skey}}), "
                        f"      (o:{t.object.type} {{key: $okey}}) "
                        f"MERGE (s)-[r:{t.relation}]->(o) "
                        "SET r.evidence = $evidence, r.confidence = $confidence, "
                        "    r.extractor = $extractor, r.paper_id = $pid, r.section = $section",
                        skey=skey,
                        okey=okey,
                        evidence=t.evidence,
                        confidence=t.confidence,
                        extractor=t.extractor,
                        pid=pid,
                        section=t.source_section,
                    )

                    # MENTIONED_IN for both endpoints: the hard provenance rule.
                    for etype, ekey in ((t.subject.type, skey), (t.object.type, okey)):
                        session.run(
                            f"MATCH (n:{etype} {{key: $ekey}}), (p:Paper {{paper_id: $pid}}) "
                            "MERGE (n)-[m:MENTIONED_IN]->(p) "
                            "SET m.section = $section, m.evidence = $evidence",
                            ekey=ekey,
                            pid=pid,
                            section=t.source_section,
                            evidence=t.evidence,
                        )
                        stats.provenance_edges += 1

                    stats.triples_written += 1
                except Exception as exc:
                    stats.triples_skipped += 1
                    stats.errors.append(f"{type(exc).__name__}: {exc}")

        stats.papers = len(papers_seen)
        logger.info("load complete: {}", stats.as_dict())
        return stats

    def wipe(self) -> None:
        """Delete every node and relationship. Used to guarantee a clean rebuild."""
        with self._session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        logger.warning("graph wiped")

    def counts(self) -> dict[str, int]:
        """Node and relationship totals, the headline graph statistics for the report."""
        with self._session() as session:
            nodes = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
            rels = session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
        return {"nodes": int(nodes), "relationships": int(rels)}

    def close(self) -> None:
        self.driver.close()
