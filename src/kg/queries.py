"""Named Cypher queries that answer the project's research questions.

Sub-question 4 of the exposé asks whether the resulting graph can answer aggregation
queries across hundreds of papers. Those queries are defined here as named, versioned
constants rather than being typed ad hoc into the Neo4j browser, for three reasons:
they are the actual evidence for that research question, they must be rerunnable by a
grader, and the dashboard and the report must show the same numbers.

Every query returns provenance-bearing results (a paper count or a paper list), because
an aggregate with no traceable source is not a defensible research finding.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NamedQuery:
    """A research query with the question it answers, so the report can quote both."""

    name: str
    question: str
    cypher: str
    params: dict[str, Any] | None = None


# Cross-paper aggregation, the direct evidence for research sub-question 4.
SOLVENT_TEMPERATURE_BY_LINKER = NamedQuery(
    name="solvent_temperature_by_linker",
    question=(
        "For each organic linker, which solvent and temperature combinations are most "
        "commonly reported across the corpus?"
    ),
    cypher="""
    MATCH (m:MOF)-[:USES_LINKER]->(l:OrganicLinker)
    MATCH (m)-[:SYNTHESIZED_BY]->(sm:SynthesisMethod)
    OPTIONAL MATCH (sm)-[:IN_SOLVENT]->(s:Solvent)
    OPTIONAL MATCH (sm)-[:AT_CONDITION]->(c:Condition)
    WITH l.name AS linker,
         coalesce(s.name, 'unspecified') AS solvent,
         coalesce(c.name, 'unspecified') AS condition,
         collect(DISTINCT m.name) AS mofs,
         count(DISTINCT m) AS n_mofs
    RETURN linker, solvent, condition, n_mofs, mofs[..5] AS example_mofs
    ORDER BY n_mofs DESC, linker
    LIMIT $limit
    """,
    params={"limit": 50},
)

METHOD_DISTRIBUTION = NamedQuery(
    name="method_distribution",
    question="Which synthesis methods dominate the corpus, and in how many papers?",
    cypher="""
    MATCH (m:MOF)-[:SYNTHESIZED_BY]->(sm:SynthesisMethod)
    MATCH (m)-[:MENTIONED_IN]->(p:Paper)
    RETURN sm.name AS method,
           count(DISTINCT m) AS n_mofs,
           count(DISTINCT p) AS n_papers
    ORDER BY n_papers DESC
    """,
)

PRECURSOR_LINKER_PAIRS = NamedQuery(
    name="precursor_linker_pairs",
    question="Which metal precursor and organic linker pairings recur across papers?",
    cypher="""
    MATCH (m:MOF)-[:USES_PRECURSOR]->(pr:MetalPrecursor)
    MATCH (m)-[:USES_LINKER]->(l:OrganicLinker)
    MATCH (m)-[:MENTIONED_IN]->(p:Paper)
    RETURN pr.name AS precursor, l.name AS linker,
           count(DISTINCT m) AS n_mofs, count(DISTINCT p) AS n_papers
    ORDER BY n_papers DESC, n_mofs DESC
    LIMIT $limit
    """,
    params={"limit": 50},
)

MOF_FULL_RECORD = NamedQuery(
    name="mof_full_record",
    question="What is the complete, source-traceable synthesis record for one named MOF?",
    cypher="""
    MATCH (m:MOF {key: $mof_key})
    OPTIONAL MATCH (m)-[:USES_PRECURSOR]->(pr:MetalPrecursor)
    OPTIONAL MATCH (m)-[:USES_LINKER]->(l:OrganicLinker)
    OPTIONAL MATCH (m)-[:SYNTHESIZED_BY]->(sm:SynthesisMethod)
    OPTIONAL MATCH (sm)-[:IN_SOLVENT]->(s:Solvent)
    OPTIONAL MATCH (sm)-[:AT_CONDITION]->(c:Condition)
    OPTIONAL MATCH (m)-[:HAS_PROPERTY]->(prop:Property)
    OPTIONAL MATCH (m)-[men:MENTIONED_IN]->(p:Paper)
    RETURN m.name AS mof,
           collect(DISTINCT pr.name) AS precursors,
           collect(DISTINCT l.name) AS linkers,
           collect(DISTINCT sm.name) AS methods,
           collect(DISTINCT s.name) AS solvents,
           collect(DISTINCT c.name) AS conditions,
           collect(DISTINCT prop.name) AS properties,
           collect(DISTINCT {paper: p.paper_id, doi: p.doi, evidence: men.evidence}) AS provenance
    """,
    params={"mof_key": "hkust-1"},
)

PROVENANCE_FOR_CLAIM = NamedQuery(
    name="provenance_for_claim",
    question="Which exact sentence and paper support a given extracted claim?",
    cypher="""
    MATCH (s)-[r]->(o)
    WHERE type(r) <> 'MENTIONED_IN' AND s.key = $subject_key
    RETURN s.name AS subject, type(r) AS relation, o.name AS object,
           r.evidence AS evidence, r.paper_id AS paper_id,
           r.section AS section, r.extractor AS extractor, r.confidence AS confidence
    ORDER BY r.confidence DESC
    LIMIT $limit
    """,
    params={"subject_key": "hkust-1", "limit": 25},
)

# Graph statistics reported as the artefact headline numbers.
GRAPH_STATS = NamedQuery(
    name="graph_stats",
    question="How large is the resulting knowledge graph?",
    cypher="""
    MATCH (n)
    WITH count(n) AS nodes
    MATCH ()-[r]->()
    WITH nodes, count(r) AS rels
    MATCH (p:Paper)
    RETURN nodes, rels, count(DISTINCT p) AS papers
    """,
)

NODE_BREAKDOWN = NamedQuery(
    name="node_breakdown",
    question="How are the graph nodes distributed across ontology entity types?",
    cypher="""
    MATCH (n)
    RETURN labels(n)[0] AS entity_type, count(*) AS n
    ORDER BY n DESC
    """,
)

# Coverage of provenance, which the project claims is total. This query exists so the
# claim can be checked rather than asserted: it must return zero rows.
PROVENANCE_VIOLATIONS = NamedQuery(
    name="provenance_violations",
    question="Are there any entities in the graph without a link to a source paper?",
    cypher="""
    MATCH (n)
    WHERE NOT n:Paper AND NOT (n)-[:MENTIONED_IN]->(:Paper)
    RETURN labels(n)[0] AS entity_type, n.name AS name
    LIMIT 100
    """,
)

ALL_QUERIES: tuple[NamedQuery, ...] = (
    GRAPH_STATS,
    NODE_BREAKDOWN,
    METHOD_DISTRIBUTION,
    SOLVENT_TEMPERATURE_BY_LINKER,
    PRECURSOR_LINKER_PAIRS,
    MOF_FULL_RECORD,
    PROVENANCE_FOR_CLAIM,
    PROVENANCE_VIOLATIONS,
)

BY_NAME: dict[str, NamedQuery] = {q.name: q for q in ALL_QUERIES}
