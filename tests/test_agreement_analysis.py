"""Tests for the DigiMOF/SynMOF agreement analysis.

The bug this file exists to prevent is specific and already happened once: the previous
version of `agreement_analysis` printed its central result, the gold-standard overlap, as
a hardcoded `0/33` that no code path computed, and the figure it asserted turned out to be
wrong. So these tests check that the overlap is *derived*, that a known candidate is found,
and that the metal comparison handles the two data shapes that silently corrupted it
before: concatenated bimetallic strings, and the literal '0' that appears in one row.

All offline: no network, no database, no reference files required.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.evaluation.agreement_analysis import (
    MOF_COMPOSITIONS,
    composition_screen,
    elements_in,
    metal_agreement,
)


def _frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows)


class TestElementsIn:
    def test_splits_a_bimetallic_string(self) -> None:
        """'CuEr' is two metals, not a token to compare as a substring.

        Comparing the first two characters of 'CuEr' against SynMOF's 'Er' reported a
        disagreement for every bimetallic MOF, which understated agreement.
        """
        assert elements_in("CuEr") == {"Cu", "Er"}

    def test_single_element(self) -> None:
        assert elements_in("Cu") == {"Cu"}

    @pytest.mark.parametrize("value", ["0", "", "   ", "nan", None, float("nan")])
    def test_unusable_values_yield_nothing(self, value: object) -> None:
        """A metal field of '0' or NaN is missing data, not a metal that disagrees."""
        assert elements_in(value) == set()


class TestMetalAgreement:
    def test_bimetallic_counts_as_agreement(self) -> None:
        """SynMOF names one primary metal; DigiMOF may name several."""
        result = metal_agreement(_frame([{"Metal": "CuEr", "metal_ele1": "Er"}]))
        assert (result["agreed"], result["comparable"]) == (1, 1)

    def test_genuine_conflict_counts_as_disagreement(self) -> None:
        result = metal_agreement(_frame([{"Metal": "Fe", "metal_ele1": "As"}]))
        assert (result["agreed"], result["comparable"]) == (0, 1)

    def test_unusable_row_is_excluded_not_counted_against(self) -> None:
        """The '0' row must not depress the agreement rate as a false disagreement."""
        result = metal_agreement(
            _frame([{"Metal": "0", "metal_ele1": "Cu"}, {"Metal": "Cu", "metal_ele1": "Cu"}])
        )
        assert (result["agreed"], result["comparable"], result["not_comparable"]) == (1, 1, 1)

    def test_percentage_is_over_comparable_rows(self) -> None:
        result = metal_agreement(
            _frame(
                [
                    {"Metal": "Cu", "metal_ele1": "Cu"},
                    {"Metal": "Fe", "metal_ele1": "As"},
                    {"Metal": "0", "metal_ele1": "Zn"},
                ]
            )
        )
        assert result["pct"] == 50.0


class TestCompositionScreen:
    """The overlap must be computed from the data, never asserted."""

    def _intersection(self) -> pd.DataFrame:
        return _frame(
            [
                {
                    "Refcode": "REYMOZ",
                    "Metal": "Cu",
                    "Clean_Linker_1": "1,3,5-Benzenetricarboxylic Acid",
                    "CN_Topology": "tbo",
                },
                {
                    "Refcode": "DOGZIJ",
                    "Metal": "Zn",
                    "Clean_Linker_1": "Terephthalic Acid",
                    "CN_Topology": "pcu",
                },
            ]
        )

    def test_finds_a_real_candidate(self) -> None:
        """Cu3(BTC)2 is HKUST-1, whose composition is present as REYMOZ.

        This is the case that refutes the discarded 'zero overlap' claim, so it is
        pinned here rather than left to a run over the full reference file.
        """
        result = composition_screen(self._intersection(), {"Cu₃(BTC)₂"})
        assert result["with_composition_candidate"] == 1
        assert result["candidates"]["Cu₃(BTC)₂"][0]["refcode"] == "REYMOZ"

    def test_absent_composition_yields_no_candidate(self) -> None:
        result = composition_screen(self._intersection(), {"MOF-801"})
        assert result["with_composition_candidate"] == 0
        assert result["candidates"] == {}

    def test_unmappable_names_are_counted_not_silently_dropped(self) -> None:
        """A generic 'Ce-MOF' has no defensible composition and must be reported as such."""
        result = composition_screen(self._intersection(), {"Cu₃(BTC)₂", "Ce-MOF", "COF"})
        assert result["gold_mofs"] == 3
        assert result["mappable_to_a_composition"] == 1
        assert result["unmappable"] == 2

    def test_screen_does_not_claim_identity(self) -> None:
        """The result must carry its own caveat, since a caller reporting a raw count
        would otherwise present a composition match as a confirmed overlap."""
        result = composition_screen(self._intersection(), {"Cu₃(BTC)₂"})
        assert "not sufficient" in result["interpretation"]

    def test_every_mapping_entry_is_a_metal_and_a_linker(self) -> None:
        """Guards the hand-authored table against a malformed entry."""
        for name, value in MOF_COMPOSITIONS.items():
            metal, linker = value
            assert metal and metal[0].isupper(), name
            assert linker and linker.islower(), name
