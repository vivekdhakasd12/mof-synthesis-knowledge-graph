"""Build the DigiMOF/SynMOF reference join from the two published source files.

This exists so that no number in the agreement analysis rests on a file whose origin
cannot be traced. The merged CSV was previously an undocumented input; this module
regenerates it from the published artefacts, and records the counts it derived.

Sources, neither of which is redistributed by this repository:

* DigiMOF: Supporting Information spreadsheet `cm3c00788_si_001.xlsx`, sheet `Master`,
  from Glasby et al. (2023), https://doi.org/10.1021/acs.chemmater.3c00788. Keyed by
  CSD refcode.
* SynMOF: `SynMOF_M.csv`, the manually curated subset, from Luo et al. (2022),
  https://doi.org/10.1002/anie.202200242. Keyed by a `filename` column of the form
  `REFCODE_clean`, from which the refcode is recovered.

**Both sides are deduplicated on refcode before joining.** DigiMOF's Master sheet
contains repeated refcodes, and joining without deduplication multiplies them into the
result: the undeduplicated join returns 513 rows for 509 distinct MOFs. Reporting 513
would inflate the denominator of every coverage and agreement statistic computed from
it, which is the same failure mode as the duplicated corpus paper described in
Section 3.2 of the report.

Run: python -m src.evaluation.build_reference_join
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
DIGIMOF_XLSX = REPO / "data" / "raw" / "reference" / "digimof_si" / "cm3c00788_si_001.xlsx"
DIGIMOF_SHEET = "Master"
SYNMOF_CSV = REPO / "data" / "external" / "SynMOF_M.csv"
OUT_CSV = REPO / "data" / "external" / "digimof_synmof_merged.csv"
OUT_JSON = REPO / "data" / "processed" / "reference_join_provenance.json"


class SourceMissingError(FileNotFoundError):
    """Raised with instructions rather than a bare path, because the fix is a download."""


def _require(path: Path, what: str, where: str) -> None:
    if not path.exists():
        raise SourceMissingError(
            f"{what} not found at {path}.\nObtain it from {where} and place it there. "
            f"This repository does not redistribute it; see docs/data_sources.md."
        )


def load_digimof() -> pd.DataFrame:
    """DigiMOF Master sheet, deduplicated on refcode."""
    _require(
        DIGIMOF_XLSX,
        "DigiMOF Supporting Information",
        "https://doi.org/10.1021/acs.chemmater.3c00788 (file cm3c00788_si_001.xlsx)",
    )
    df = pd.read_excel(DIGIMOF_XLSX, sheet_name=DIGIMOF_SHEET)
    df = df[df["Refcode"].notna()].copy()
    df["Refcode"] = df["Refcode"].astype(str).str.strip()
    return df


def load_synmof() -> pd.DataFrame:
    """SynMOF manual subset, with the refcode recovered from the filename column."""
    _require(
        SYNMOF_CSV,
        "SynMOF manual subset (SynMOF_M.csv)",
        "https://doi.org/10.1002/anie.202200242 (supporting data)",
    )
    df = pd.read_csv(SYNMOF_CSV)
    df["refcode"] = df["filename"].astype(str).str.replace("_clean", "", regex=False).str.strip()
    return df


def build() -> dict[str, Any]:
    digimof, synmof = load_digimof(), load_synmof()

    d_unique = digimof.drop_duplicates(subset="Refcode", keep="first")
    s_unique = synmof.drop_duplicates(subset="refcode", keep="first")

    merged = d_unique.merge(s_unique, left_on="Refcode", right_on="refcode", how="inner")

    # A join that deduplicated both sides cannot itself contain duplicates. Asserting it
    # here means a future change to either loader fails loudly rather than silently
    # reinflating the counts this module exists to correct.
    assert merged["Refcode"].is_unique, "join produced duplicate refcodes"

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(OUT_CSV, index=False)

    provenance = {
        "digimof": {
            "source": str(DIGIMOF_XLSX.relative_to(REPO)),
            "sheet": DIGIMOF_SHEET,
            "rows": int(len(digimof)),
            "unique_refcodes": int(len(d_unique)),
            "duplicate_rows_dropped": int(len(digimof) - len(d_unique)),
        },
        "synmof": {
            "source": str(SYNMOF_CSV.relative_to(REPO)),
            "subset": "manual (SynMOF_M)",
            "rows": int(len(synmof)),
            "unique_refcodes": int(len(s_unique)),
            "duplicate_rows_dropped": int(len(synmof) - len(s_unique)),
        },
        "intersection": {
            "unique_mofs": int(len(merged)),
            "note": (
                "Joining without deduplicating DigiMOF first returns 513 rows for these "
                "same MOFs, because the Master sheet repeats some refcodes."
            ),
        },
        "output": str(OUT_CSV.relative_to(REPO)),
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(provenance, indent=2))
    return provenance


def main() -> None:
    p = build()
    print(f"DigiMOF   : {p['digimof']['rows']:,} rows, {p['digimof']['unique_refcodes']:,} unique")
    print(f"SynMOF    : {p['synmof']['rows']:,} rows, {p['synmof']['unique_refcodes']:,} unique")
    print(f"Intersect : {p['intersection']['unique_mofs']:,} unique MOFs")
    print(f"  wrote {p['output']}")
    print(f"  wrote {OUT_JSON.relative_to(REPO)}")


if __name__ == "__main__":
    main()
