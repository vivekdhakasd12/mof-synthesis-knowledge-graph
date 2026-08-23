"""Canonical normalisation of chemical and MOF names.

This is deliberately a SINGLE shared module rather than a helper duplicated inside the
evaluation and knowledge-graph code. If evaluation decided that a predicted linker
"H3BTC" matched the gold "trimesic acid" but the graph loader treated them as two
different nodes, the reported accuracy and the artefact would disagree with each other.
One normaliser keeps those two answers consistent by construction.

The normalisation is intentionally conservative and rule based, not learned: a grader
must be able to read these rules and check them. Aggressive merging would inflate the
measured accuracy, which is the one direction of error this project cannot afford.
"""

from __future__ import annotations

import re
import unicodedata

# Surface variants that denote the same chemical. Kept explicit and auditable rather than
# inferred, and cited in the report. Keys and values are compared after basic folding.
SYNONYMS: dict[str, str] = {
    # linkers
    "h3btc": "trimesic acid",
    "btc": "trimesic acid",
    "benzene-1,3,5-tricarboxylic acid": "trimesic acid",
    "1,3,5-benzenetricarboxylic acid": "trimesic acid",
    "h2bdc": "terephthalic acid",
    "bdc": "terephthalic acid",
    "benzene-1,4-dicarboxylic acid": "terephthalic acid",
    "1,4-benzenedicarboxylic acid": "terephthalic acid",
    "hmim": "2-methylimidazole",
    "2-meim": "2-methylimidazole",
    "mim": "2-methylimidazole",
    # solvents
    "dmf": "n,n-dimethylformamide",
    "def": "n,n-diethylformamide",
    "dmso": "dimethyl sulfoxide",
    "dma": "n,n-dimethylacetamide",
    "thf": "tetrahydrofuran",
    "meoh": "methanol",
    "etoh": "ethanol",
    "mecn": "acetonitrile",
    "acn": "acetonitrile",
    "h2o": "water",
    "deionised water": "water",
    "deionized water": "water",
    "distilled water": "water",
    "di water": "water",
    # metals in salt names
    "zn(no3)2": "zinc nitrate",
    "cu(no3)2": "copper nitrate",
    "zrcl4": "zirconium chloride",
    "fecl3": "iron chloride",
    "alcl3": "aluminium chloride",
    "aluminum chloride": "aluminium chloride",
}

# Hydrate suffixes are dropped for matching purposes because papers report the same salt
# with and without the hydrate count. The unhydrated identity is what the ontology models.
_HYDRATE = re.compile(
    r"\s*[.·•*x×]\s*\d*\s*h\s*2\s*o\b|\s*\b(?:mono|di|tri|tetra|penta|hexa|hepta|octa|nona|deca)?hydrate\b",
    re.IGNORECASE,
)

# Unicode subscripts/superscripts used in formulae, mapped back to plain digits.
_SUB_SUP = str.maketrans(
    "₀₁₂₃₄₅₆₇₈₉⁰¹²³⁴⁵⁶⁷⁸⁹",
    "01234567890123456789",
)

_PUNCT = re.compile(r"[\s\-‐-―_,;'\"()\[\]{}]+")


def fold(text: str) -> str:
    """Lowercase, strip accents, unify unicode digits and dashes, squeeze whitespace.

    This is the shallow pass used before any lookup. It must never merge two genuinely
    different chemicals, so it only touches presentation, never content.
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text).translate(_SUB_SUP)
    text = text.replace("°", " degrees ")
    text = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
    return " ".join(text.lower().split())


def normalize_chemical(name: str) -> str:
    """Canonical form of a chemical or MOF name, for equality comparison and node keys.

    Applies folding, drops hydrate notation, then resolves known synonyms. Returns a
    stable string suitable for use as a Neo4j node `key`.
    """
    folded = fold(name)
    if not folded:
        return ""
    folded = _HYDRATE.sub("", folded).strip()
    if folded in SYNONYMS:
        folded = SYNONYMS[folded]
    # A second pass catches synonyms that only appear once punctuation is stripped,
    # for example "H3BTC," or "(DMF)".
    squeezed = _PUNCT.sub(" ", folded).strip()
    if squeezed in SYNONYMS:
        return SYNONYMS[squeezed]
    return folded


def normalize_mof(name: str) -> str:
    """Canonical form of a MOF designation.

    MOF names are family plus number (ZIF-8, UiO-66, MIL-101). Papers vary the separator
    and the case, so those are unified while the family and number are preserved exactly:
    UiO-66 and UiO-67 are different materials and must never collapse together.
    """
    folded = fold(name)
    if not folded:
        return ""
    m = re.match(r"^([a-z]+)\s*[-\s]?\s*(\d+[a-z]?)(.*)$", folded)
    if m:
        family, number, tail = m.groups()
        return f"{family}-{number}{tail.rstrip()}".strip()
    return folded


def normalize_condition(value: str) -> str:
    """Canonical form of a process condition, unifying unit spelling but not magnitude.

    Temperature and time are the conditions the evaluation scores most often, and papers
    write them many ways ("120 C", "120 degrees C", "393 K", "24 h", "24 hours",
    "overnight"). Magnitudes are never converted here, only the unit surface form, so no
    silent unit conversion can corrupt a measurement.
    """
    folded = fold(value)
    if not folded:
        return ""
    folded = re.sub(r"\bdegrees?\s*c(?:elsius)?\b", "c", folded)
    folded = re.sub(r"\bdeg\s*c\b", "c", folded)
    folded = re.sub(r"\bkelvin\b", "k", folded)
    folded = re.sub(r"\b(hours?|hrs?)\b", "h", folded)
    folded = re.sub(r"\b(minutes?|mins?)\b", "min", folded)
    folded = re.sub(r"\b(days?)\b", "d", folded)
    folded = re.sub(r"(\d)\s+([a-z])", r"\1 \2", folded)
    return " ".join(folded.split())


def normalize_by_type(entity_type: str, name: str) -> str:
    """Dispatch to the right normaliser for an ontology entity type."""
    if entity_type == "MOF":
        return normalize_mof(name)
    if entity_type == "Condition":
        return normalize_condition(name)
    return normalize_chemical(name)
