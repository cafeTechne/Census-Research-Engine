# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression tests for manifest-integration fixes discovered in the R120 cancer surveillance study."""
import copy
from pathlib import Path

from census.manifest import load_manifest, validate_manifest
from census.manifest.methods import _stat_spatial_scan

ROOT = Path(__file__).resolve().parents[1]


def test_r120_registered_manifests_validate_offline():
    for name in (
        "r120_mi_ny_cancer_surveillance.json",
        "r120_oh_pa_cancer_replication.json",
    ):
        m = load_manifest(str(ROOT / "examples/manifests" / name))
        errs = validate_manifest(m, resolve=False)
        assert errs == [], f"{name} failed validation: {errs}"


def test_stat_spatial_scan_accepts_confirmatory_and_validated_p():
    res = {
        "primary": {"relative_risk": 1.28, "p_value": 0.001, "counties": ["26001"]},
        "validated_p": True,
        "confirmatory": True,
        "audit": "docs/audits/scan_validation.md",
    }
    stat = _stat_spatial_scan({"statistic": "primary_rr"}, res)
    assert "confirmatory_refusal" not in stat
    assert stat["estimate"] == 1.28
    assert stat["p_two_sided"] == 0.001

    res_exp = copy.deepcopy(res)
    res_exp["confirmatory"] = False
    stat_exp = _stat_spatial_scan({"statistic": "primary_rr"}, res_exp)
    assert "confirmatory_refusal" in stat_exp


def test_methods_section_renders_targets_and_registry_references():
    from census.manifest import methods_section

    m = load_manifest(str(ROOT / "examples/manifests/r120_mi_ny_cancer_surveillance.json"))
    txt = methods_section(m)
    assert "(`None`)" not in txt
    assert "**dm_cancer** (`cancer_numerator / E_cancer`)" in txt
    assert "**scan_cancer** (`cancer_numerator / E_cancer`)" in txt
    assert "**des_poverty** (`poverty_prop >= 0.15`)" in txt
    assert "**ag_counts** (`cancer_numerator vs E_cancer`)" in txt
    refs_section = txt.split("### References", 1)[1]
    for author in ("Riebler", "Moraga", "Kulldorff", "Fay", "Lin"):
        assert author in refs_section, f"Missing reference for {author} in methods.md References"
