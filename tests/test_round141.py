# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 141 tests: 4-state county deprivation index (PCA) & BEA RPP real-income invariants."""
import json
from pathlib import Path

from scripts.r141_deprivation_rpp_study import protocol_hash

ROOT = Path(__file__).resolve().parents[1]


def test_r141_summary_invariants():
    path = ROOT / "studies_output/r141_deprivation_rpp/summary.json"
    assert path.exists(), "Run scripts/r141_deprivation_rpp_study.py first"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["protocol_sha256"] == protocol_hash()
    assert data["n_counties_total"] == 300
    assert 0.35 < data["variance_explained_pc1"] < 1.0
    assert data["state_real_pci_spread"] < data["state_nominal_pci_spread"]
    assert sum(data["typology_groups"].values()) == 300
    for st in ("26", "36", "39", "42"):
        assert data["states"][st]["median_nominal_pci"] > 20_000
        assert data["states"][st]["median_real_pci"] > 20_000
