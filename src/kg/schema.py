"""Neo4j schema for the MOF synthesis knowledge graph.

The graph mirrors configs/ontology.json v0.2 exactly: node labels are the ontology
entity types and relationship types are the ontology relation names. Keeping the two
in lockstep means a triple that passes extraction validation can always be written to
the graph without a translation layer.

Provenance is structural here, not advisory: every entity node created by the loader
also gets a MENTIONED_IN edge to its Paper node carrying the section and evidence
sentence, so any claim in the graph can be traced back to the exact text that produced
it. That is a hard project rule.
"""

from __future__ import annotations

# Node labels, mirroring ontology v0.2 entity types.
NODE_LABELS = (
    "MOF",
    "MetalPrecursor",
    "OrganicLinker",
    "Solvent",
    "SynthesisMethod",
    "Condition",
    "Property",
    "Application",
    "Paper",
)

# Relationship types, mirroring ontology v0.2 relations.
REL_TYPES = (
    "USES_PRECURSOR",
    "USES_LINKER",
    "SYNTHESIZED_BY",
    "IN_SOLVENT",
    "AT_CONDITION",
    "HAS_PROPERTY",
    "MEASURED_AT",
    "USED_IN",
    "MENTIONED_IN",
)

# Uniqueness constraints. Entities are keyed on their normalised name (`key`) rather than
# the surface form, so "Cu(NO3)2.3H2O" and "copper nitrate trihydrate" can be merged by
# entity resolution into one node while both surface forms are retained as aliases.
CONSTRAINTS: tuple[str, ...] = tuple(
    f"CREATE CONSTRAINT {label.lower()}_key IF NOT EXISTS "
    f"FOR (n:{label}) REQUIRE n.key IS UNIQUE"
    for label in NODE_LABELS
    if label != "Paper"
) + (
    "CREATE CONSTRAINT paper_id IF NOT EXISTS "
    "FOR (p:Paper) REQUIRE p.paper_id IS UNIQUE",
)

# Indexes that matter for the dashboard's lookup and aggregation queries.
INDEXES: tuple[str, ...] = (
    "CREATE INDEX mof_name IF NOT EXISTS FOR (n:MOF) ON (n.name)",
    "CREATE INDEX paper_doi IF NOT EXISTS FOR (p:Paper) ON (p.doi)",
    "CREATE INDEX solvent_name IF NOT EXISTS FOR (n:Solvent) ON (n.name)",
    "CREATE INDEX method_name IF NOT EXISTS FOR (n:SynthesisMethod) ON (n.name)",
)
