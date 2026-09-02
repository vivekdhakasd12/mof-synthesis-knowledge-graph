"""DigiMOF/SynMOF agreement analysis, and what it can say about our gold standard.

Every figure this module reports is computed from the joined reference databases built by
`src.evaluation.build_reference_join`. Nothing is asserted as a literal, which matters
because an earlier version of this file printed its central result, the overlap between
the gold standard and the reference intersection, as a hardcoded `0/33` that no code path
ever derived.

**On the overlap question specifically.** DigiMOF and SynMOF are keyed by CSD refcode; the
gold standard is keyed by the MOF name as written in the paper. Joining them needs a
name-to-refcode resource this project does not have, so the true overlap is *undetermined*
rather than zero. What can be computed without that resource is a weaker screen: whether a
gold MOF's declared composition (metal plus linker) also occurs in the intersection. A
composition match is necessary but not sufficient for identity, since the same metal and
linker can assemble into different frameworks with different refcodes. It can therefore
refute a claim of zero overlap, but it cannot confirm a match.

Run: python -m src.evaluation.agreement_analysis
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
MERGED = REPO / "data" / "external" / "digimof_synmof_merged.csv"
GOLD = REPO / "data" / "annotations" / "gold.jsonl"
OUT = REPO / "data" / "processed" / "agreement_analysis.json"

# PubChem CIDs, because SynMOF stores solvents as identifiers rather than names. Only CIDs
# that actually occur in the intersection are named; anything else is reported as its bare
# CID rather than guessed at.
CID_TO_SOLVENT = {
    962: "water",
    6228: "DMF",
    174: "ethanol",
    887: "methanol",
    31374: "DEF",
}

# Hand-authored, deliberately small, and auditable line by line. Each entry maps a MOF name
# in the gold standard to the metal and linker its own literature definition specifies. It
# screens for composition candidates only, and never asserts that a gold MOF and a refcode
# are the same material. Names whose composition is not settled enough to write down are
# left out on purpose and counted as unmappable, which is the honest outcome for a generic
# label such as "Ce-MOF" or a bare "COF".
MOF_COMPOSITIONS: dict[str, tuple[str, str]] = {
    "Cu₃(BTC)₂": ("Cu", "benzenetricarboxylic"),  # HKUST-1; the name itself states Cu and BTC
    "MIL-101(Cr)": ("Cr", "terephthalic"),
    "ZIF-8": ("Zn", "methylimidazole"),
    "UiO-66 node": ("Zr", "terephthalic"),
    "UiO-66-NH₂": ("Zr", "terephthalic"),
    "%AA UiO-66-NH₂": ("Zr", "terephthalic"),
    "MM@UiO-66": ("Zr", "terephthalic"),
    "UiO-67-Ti": ("Zr", "biphenyl"),
    "MOF-801": ("Zr", "fumaric"),
}

_ELEMENT = re.compile(r"[A-Z][a-z]?")


def elements_in(value: object) -> set[str]:
    """Split a DigiMOF metal string such as 'CuBa' into {'Cu', 'Ba'}.

    DigiMOF concatenates the metals of a bimetallic framework into one string, so comparing
    substrings against SynMOF's single primary metal misreads 'CuEr' against 'Er' as a
    disagreement. Values containing no element symbol at all, such as the literal '0'
    present in one row, yield an empty set and are treated as not comparable rather than as
    a disagreement.
    """
    # Guard missing values before stringifying: str(None) is "None", whose first two
    # characters parse as the element symbol for nobelium.
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return set()
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return set()
    return set(_ELEMENT.findall(text))


def load_gold_mof_names() -> set[str]:
    """Distinct MOF names in the gold standard.

    Filters on subject *type* rather than taking every subject, because the annotation
    defect described in Section 7.5 of the report leaves the MOF's name in the subject slot
    of IN_SOLVENT and AT_CONDITION triples, whose subject should be the synthesis method.
    Both routes happen to yield the same names here, but only one of them says what it
    means.
    """
    names: set[str] = set()
    with GOLD.open() as fh:
        for line in fh:
            for triple in json.loads(line).get("triples", []):
                if triple.get("subject_type") == "MOF":
                    names.add(triple["subject_name"])
    return names


def metal_agreement(merged: pd.DataFrame) -> dict[str, Any]:
    """Do the two databases name the same metal for the MOFs they share?"""
    agree = comparable = 0
    for _, row in merged.iterrows():
        digimof = elements_in(row.get("Metal"))
        synmof = elements_in(row.get("metal_ele1"))
        if not digimof or not synmof:
            continue
        comparable += 1
        # SynMOF records one primary metal, DigiMOF may record several. Agreement means
        # SynMOF's metal is among DigiMOF's, not that the two strings are equal.
        if synmof <= digimof:
            agree += 1
    return {
        "agreed": agree,
        "comparable": comparable,
        "not_comparable": int(len(merged)) - comparable,
        "pct": round(100 * agree / comparable, 1) if comparable else 0.0,
    }


def composition_screen(merged: pd.DataFrame, gold_names: set[str]) -> dict[str, Any]:
    """Which gold MOFs have their declared composition present in the intersection?"""
    cols = merged[["Refcode", "Metal", "Clean_Linker_1", "CN_Topology"]].copy()
    cols["_linker"] = cols["Clean_Linker_1"].astype(str).str.lower()

    candidates: dict[str, list[dict[str, str]]] = {}
    for name in sorted(gold_names & MOF_COMPOSITIONS.keys()):
        metal, linker_sub = MOF_COMPOSITIONS[name]
        hits = cols[
            cols["Metal"].apply(lambda v, m=metal: m in elements_in(v))
            & cols["_linker"].str.contains(linker_sub, na=False)
        ]
        if len(hits):
            candidates[name] = [
                {
                    "refcode": str(r.Refcode),
                    "metal": str(r.Metal),
                    "linker": str(r.Clean_Linker_1),
                    "topology": str(r.CN_Topology),
                }
                for r in hits.itertuples()
            ]

    mappable = sorted(gold_names & MOF_COMPOSITIONS.keys())
    return {
        "gold_mofs": len(gold_names),
        "mappable_to_a_composition": len(mappable),
        "unmappable": len(gold_names) - len(mappable),
        "with_composition_candidate": len(candidates),
        "candidates": candidates,
        "interpretation": (
            "A composition match is necessary but not sufficient for identity. These are "
            "candidate overlaps, not confirmed ones. The refcode-level overlap remains "
            "undetermined without a name-to-refcode resource."
        ),
    }


def analyse() -> dict[str, Any]:
    if not MERGED.exists():
        raise FileNotFoundError(
            f"{MERGED} not found. Run `python -m src.evaluation.build_reference_join` first."
        )
    merged = pd.read_csv(MERGED)
    if not merged["Refcode"].is_unique:
        raise ValueError(
            "merged file contains duplicate refcodes; rebuild it with "
            "`python -m src.evaluation.build_reference_join`"
        )
    gold_names = load_gold_mof_names()

    fields = {
        "Metal (DigiMOF)": "Metal",
        "Linker (DigiMOF)": "Clean_Linker_1",
        "Topology (DigiMOF)": "CN_Topology",
        "Temperature (SynMOF)": "temperature_Celsius",
        "Time (SynMOF)": "time_h",
        "Yield (SynMOF)": "Yield_Percent",
        "Primary metal (SynMOF)": "metal_ele1",
        "Solvent 1 (SynMOF)": "solvent1",
    }
    n = len(merged)
    coverage = {
        label: {
            "count": int(merged[col].notna().sum()),
            "total": n,
            "pct": round(100 * merged[col].notna().sum() / n, 1),
        }
        for label, col in fields.items()
    }

    solvents: Counter[str] = Counter()
    for col in ("solvent1", "solvent2", "solvent3", "solvent4", "solvent5"):
        for cid in merged[col].dropna():
            solvents[CID_TO_SOLVENT.get(int(cid), f"CID_{int(cid)}")] += 1

    yields = pd.to_numeric(merged["Yield_Percent"], errors="coerce")
    metals = {str(k): int(v) for k, v in merged["metal_ele1"].value_counts().items()}

    return {
        "intersection_size": n,
        "note_on_size": (
            "Distinct MOFs. Joining without deduplicating DigiMOF's repeated refcodes "
            "returns 513 rows for the same materials."
        ),
        "field_coverage": coverage,
        "solvent_distribution": dict(solvents.most_common()),
        "metal_distribution": metals,
        "conditions": {
            "temperature_c": {
                "min": float(merged["temperature_Celsius"].min()),
                "max": float(merged["temperature_Celsius"].max()),
                "median": float(merged["temperature_Celsius"].median()),
            },
            "time_h": {
                "min": float(merged["time_h"].min()),
                "max": float(merged["time_h"].max()),
                "median": float(merged["time_h"].median()),
            },
            "yield_pct": {
                "median": float(yields.median()),
                "n": int(yields.notna().sum()),
            },
        },
        "metal_agreement": metal_agreement(merged),
        "gold_overlap": composition_screen(merged, gold_names),
    }


def main() -> None:
    result = analyse()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2))

    print(f"Intersection: {result['intersection_size']} distinct MOFs")
    ma = result["metal_agreement"]
    print(f"Metal agreement: {ma['agreed']}/{ma['comparable']} ({ma['pct']} percent)")
    print(f"  not comparable: {ma['not_comparable']}")

    go = result["gold_overlap"]
    print(f"\nGold standard: {go['gold_mofs']} distinct MOF names")
    print(f"  mappable to a known composition: {go['mappable_to_a_composition']}")
    print(f"  with a composition candidate in the intersection: {go['with_composition_candidate']}")
    for name, hits in go["candidates"].items():
        for h in hits:
            print(f"    {name} -> {h['refcode']} ({h['metal']}, {h['linker']}, {h['topology']})")
    print(f"  unmappable without a name-to-refcode resource: {go['unmappable']}")
    print(f"\n  wrote {OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
