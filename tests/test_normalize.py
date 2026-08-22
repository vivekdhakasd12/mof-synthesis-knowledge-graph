"""Tests for the shared chemical-name normaliser.

These matter more than they look: the normaliser decides when two strings count as the
same chemical, which directly sets the measured accuracy of every extractor. Tests here
guard against the failure mode that would quietly inflate results, namely merging two
genuinely different materials.
"""

from __future__ import annotations

from src.normalize import (
    fold,
    normalize_by_type,
    normalize_chemical,
    normalize_condition,
    normalize_mof,
)


def test_fold_handles_case_accents_and_unicode_digits():
    assert fold("  DMF  ") == "dmf"
    assert fold("Ångström") == "angstrom"
    assert "2" in fold("H₂O")


def test_hydrate_notation_is_dropped():
    assert normalize_chemical("Cu(NO3)2.3H2O") == normalize_chemical("Cu(NO3)2")
    assert normalize_chemical("Zn(NO3)2·6H2O") == normalize_chemical("Zn(NO3)2")
    assert normalize_chemical("zinc nitrate hexahydrate") == "zinc nitrate"


def test_known_synonyms_resolve_to_one_canonical_form():
    assert normalize_chemical("H3BTC") == normalize_chemical("trimesic acid")
    assert normalize_chemical("benzene-1,3,5-tricarboxylic acid") == "trimesic acid"
    assert normalize_chemical("H2BDC") == normalize_chemical("terephthalic acid")
    assert normalize_chemical("HmIM") == "2-methylimidazole"
    assert normalize_chemical("DMF") == "n,n-dimethylformamide"
    assert normalize_chemical("deionised water") == normalize_chemical("distilled water")


def test_mof_family_and_number_are_preserved_separately():
    assert normalize_mof("ZIF 8") == normalize_mof("ZIF-8") == "zif-8"
    assert normalize_mof("UiO-66") == "uio-66"
    # The critical negative case: different numbers are different materials.
    assert normalize_mof("UiO-66") != normalize_mof("UiO-67")
    assert normalize_mof("MOF-5") != normalize_mof("MOF-74")


def test_conditions_unify_units_without_converting_magnitude():
    assert normalize_condition("120 degrees C") == normalize_condition("120 C")
    assert normalize_condition("24 hours") == normalize_condition("24 h")
    assert normalize_condition("30 minutes") == normalize_condition("30 min")
    # No unit conversion may happen: Celsius and Kelvin must stay distinct.
    assert normalize_condition("393 K") != normalize_condition("120 C")
    # Different magnitudes must never merge.
    assert normalize_condition("24 h") != normalize_condition("48 h")


def test_dispatch_by_entity_type():
    assert normalize_by_type("MOF", "ZIF 8") == "zif-8"
    assert normalize_by_type("Condition", "120 degrees C") == "120 c"
    assert normalize_by_type("Solvent", "DMF") == "n,n-dimethylformamide"


def test_empty_input_is_safe():
    for fn in (normalize_chemical, normalize_mof, normalize_condition, fold):
        assert fn("") == ""
