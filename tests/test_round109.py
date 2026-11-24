# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 109 tests: Fuller ecologic slope (E3d), Joinpoint AAPC bootstrap-t (J3c), and rdd/disease_map manifests."""
import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd

from census import ecologic as eco
from census import joinpoint as jp
from census.manifest import load_manifest, validate_manifest
from census.manifest.methods import METHODS, _run_disease_map, _run_rdd, _stat_disease_map, _stat_rdd
from tests.test_manifest import EXAMPLE

ROOT = Path(__file__).resolve().parents[1]


def test_round109_audit_verdicts_match_code():
    audit = json.loads((ROOT / "docs/audits/repairs109_validation.json").read_text())
    assert audit["verdicts"]["E3d"] is True
    assert audit["verdicts"]["J3c"] is True
    assert eco.FULLER_ECOLOGIC_VALIDATED is True
    assert jp.AAPC_BOOTSTRAP_T_VALIDATED is True
    assert "rdd" in METHODS and "disease_map" in METHODS


def test_ecologic_fuller_slope_gate():
    rng = np.random.default_rng(10901)
    # 60 areas x 100 records -> validated
    J, nj = 60, 100
    mu_x = rng.normal(0, 0.35, J)
    mu_y = 1.5 * mu_x + rng.normal(0, 0.4, J)
    x = (mu_x[:, None] + rng.normal(0, 0.9, (J, nj))).reshape(-1)
    y = (mu_y[:, None] + 0.5 * (x.reshape(J, nj) - mu_x[:, None]) + rng.normal(0, 1.0, (J, nj))).reshape(-1)
    area = np.repeat(np.arange(J), nj)
    W = np.column_stack([np.ones(J * nj)] + [1.0 + rng.choice([-0.5, 0.5], J * nj) for _ in range(80)])
    out = eco.ecologic_check(y, x, area, W)
    fe = out["ecologic_fuller"]
    assert fe["validated"] is True
    assert abs(fe["estimate"] - 1.5) < 0.6 and fe["lower"] < fe["estimate"] < fe["upper"]

    # Small areas (n_j = 30 < 80) -> exploratory
    keep = np.concatenate([np.arange(j * nj, j * nj + 30) for j in range(J)])
    out_small = eco.ecologic_check(y[keep], x[keep], area[keep], W[keep])
    assert out_small["ecologic_fuller"]["validated"] is False


def test_joinpoint_aapc_bootstrap_t():
    rng = np.random.default_rng(10902)
    years = list(range(2005, 2023))  # 18 annual points
    x = np.arange(len(years), dtype=float)
    mu = 500.0 * np.exp(-0.03 * x + 0.06 * np.maximum(x - 9, 0.0))
    counts = np.maximum(rng.poisson(mu), 1)
    pop = np.full(len(years), 100000.0)
    out = jp.joinpoint(years, counts=counts, population=pop, max_joinpoints=1, permutations=199, bootstrap=120)
    bt = out["aapc_bootstrap_t"]
    assert bt["validated"] is True
    assert bt["lower"] < bt["aapc"] < bt["upper"]


def test_manifest_rdd_and_disease_map():
    # Schema validation for rdd
    m = copy.deepcopy(load_manifest(EXAMPLE))
    m["analyses"] = [{"id": "r1", "method": "rdd", "outcome": "income", "running": "pop", "cutoff": 1000.0}]
    m["hypotheses"] = [{"id": "h1", "analysis": "r1", "statistic": "jump", "direction": "two-sided"}]
    assert validate_manifest(m, resolve=False) == []

    # Confirmatory RDD refuses custom bandwidth
    m_bad = copy.deepcopy(m)
    m_bad["analyses"][0]["args"] = {"bandwidth": 50.0}
    assert any("bandwidth" in e for e in validate_manifest(m_bad, resolve=False))

    # Schema validation for disease_map
    m2 = copy.deepcopy(load_manifest(EXAMPLE))
    m2["analyses"] = [{"id": "dm1", "method": "disease_map", "observed": "income", "expected": "pop",
                       "args": {"method": "B3"}}]
    m2["hypotheses"] = [{"id": "h1", "analysis": "dm1", "statistic": "relative_risk", "geoid": "26001",
                         "direction": "two-sided"}]
    assert validate_manifest(m2, resolve=False) == []

    # Confirmatory disease_map refuses B2
    m2_bad = copy.deepcopy(m2)
    m2_bad["analyses"][0]["args"]["method"] = "B2"
    assert any("B3" in e for e in validate_manifest(m2_bad, resolve=False))

    # Direct runner + extractor checks
    rng = np.random.default_rng(10903)
    n = 1200
    rx = rng.uniform(-1, 1, n)
    ry = 1.0 + 0.9 * (rx >= 0) + 0.4 * rx + rng.normal(0, 0.5, n)
    rr = _run_rdd({"outcome": "y", "running": "x", "cutoff": 0.0}, {}, pd.DataFrame({"x": rx, "y": ry}),
                  0.90, None, None, {})
    sr = _stat_rdd({"statistic": "jump", "null_value": 0.0}, rr)
    assert abs(sr["estimate"] - 0.9) < 0.35 and "confirmatory_refusal" not in sr

    # 5x5 grid disease_map with median E >= 30
    edges = []
    for r in range(5):
        for c in range(5):
            idx = r * 5 + c
            if c + 1 < 5:
                edges.append((idx, idx + 1))
            if r + 1 < 5:
                edges.append((idx, idx + 5))
    exp = rng.uniform(40, 80, 25)
    obs = rng.poisson(exp * 1.1)
    df_dm = pd.DataFrame({"GEOID": [f"26{i:03d}" for i in range(25)], "obs": obs, "exp": exp})
    rdm = _run_disease_map({"observed": "obs", "expected": "exp"}, {"method": "B3", "edges": edges},
                           df_dm, 0.90, None, None, {})
    sdm = _stat_disease_map({"statistic": "relative_risk", "geoid": "26000", "null_value": 1.0}, rdm)
    assert sdm["ci_lower"] < sdm["estimate"] < sdm["ci_upper"] and "confirmatory_refusal" not in sdm
