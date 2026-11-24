# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 108 tests: multi-confounder parametric g-formula (M5b), SDR bias-corrected Shannon entropy (S2b),
and designation/agreement manifest methods."""
import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd

from census import msm
from census import spatial_models as sm
from census.manifest import load_manifest, validate_manifest
from census.manifest.methods import METHODS, _run_agreement, _run_designation, _stat_agreement, _stat_designation
from tests.test_manifest import EXAMPLE

ROOT = Path(__file__).resolve().parents[1]


def test_round108_audit_verdicts_match_code():
    audit = json.loads((ROOT / "docs/audits/repairs108_validation.json").read_text())
    assert audit["verdicts"]["M5b"] is True
    assert audit["verdicts"]["S2b"] is True
    assert audit["verdicts"]["E3c"] is False
    assert msm.GFORMULA_VALIDATED is True
    assert sm.DIVERSITY_SDR_BC_VALIDATED is True
    assert sm.DIVERSITY_SDR_BC_MIN_N == 150
    assert "designation" in METHODS and "agreement" in METHODS


def test_msm_gformula_multiple_confounders():
    rng = np.random.default_rng(10801)
    G, K = 51, 12
    Phi = np.array([[0.5, 0.15], [0.1, 0.45]])
    gamma_A = np.array([0.5, -0.25])
    delta = np.array([0.8, -0.6])
    psi = -2.0
    rows = []
    for u in range(G):
        L_prev = rng.normal(0, 1, 2)
        g = np.nan if u < 25 else (2015 if u < 38 else 2017)
        u_eff = rng.normal(0, 0.5)
        for idx, yr in enumerate(range(2010, 2010 + K)):
            a_prev = 1.0 if (not np.isnan(g) and yr > g) else 0.0
            L_cur = L_prev if idx == 0 else (Phi @ L_prev + gamma_A * a_prev + rng.normal(0, 0.6, 2))
            a_cur = 1.0 if (not np.isnan(g) and yr >= g) else 0.0
            y = 10.0 + u_eff + 0.1 * idx + psi * a_cur + float(delta @ L_cur) + rng.normal(0, 0.5)
            rows.append({"GEOID": f"{u+1:02d}", "Year": yr, "first_treated": g,
                         "l1": L_cur[0], "l2": L_cur[1], "y": y})
            L_prev = L_cur
    df = pd.DataFrame(rows)
    res = msm.marginal_structural_model(df, "y", "first_treated", ["l1", "l2"], product="annual", method="gformula")
    assert res["validated"] is True
    assert res["confounders"] == 2
    assert res["method"] == "gformula_jackknife"
    assert len(res["effects"]) == 3
    # True duration-1 effect is psi = -2.0
    assert abs(res["effects"][0]["estimate"] - (-2.0)) < 0.35


def test_diversity_index_sdr_bc_gate():
    rng = np.random.default_rng(10802)
    p_true = np.array([[0.55, 0.25, 0.12, 0.08], [0.40, 0.30, 0.20, 0.10]])
    shares = pd.DataFrame(p_true, index=["a1", "a2"], columns=["g1", "g2", "g3", "g4"])
    reps = []
    for _ in range(80):
        r = np.clip(p_true + rng.normal(0, 0.015, p_true.shape), 0.005, 0.99)
        r = r / r.sum(axis=1, keepdims=True)
        reps.append(pd.DataFrame(r, index=shares.index, columns=shares.columns))
    out = sm.diversity_index(shares, reps, method="sdr_bc", sample_sizes=[200, 80])
    assert bool(out.loc["a1", "validated"]) is True
    assert bool(out.loc["a2", "validated"]) is False
    assert (out["lower"] < out["entropy"]).all() and (out["entropy"] < out["upper"]).all()


def test_manifest_designation_and_agreement_validation_and_runners():
    # Validate manifest schema checks for designation
    m = copy.deepcopy(load_manifest(EXAMPLE))
    m["analyses"] = [{"id": "d1", "method": "designation", "outcome": "income", "threshold": 0.20,
                      "args": {"rule": "prob80"}}]
    m["hypotheses"] = [{"id": "h1", "analysis": "d1", "statistic": "ppv", "direction": "two-sided"}]
    assert validate_manifest(m, resolve=False) == []

    # Confirmatory manifest refuses exploratory rule 'prob50' ('lower' validated in Round 112)
    m_bad = copy.deepcopy(m)
    m_bad["analyses"][0]["args"]["rule"] = "prob50"
    errs = validate_manifest(m_bad, resolve=False)
    assert any("prob80" in e for e in errs)

    # Validate manifest schema checks for agreement
    m2 = copy.deepcopy(load_manifest(EXAMPLE))
    m2["analyses"] = [{"id": "a1", "method": "agreement", "first": "income", "second": "pop"}]
    m2["hypotheses"] = [{"id": "h1", "analysis": "a1", "statistic": "ccc", "direction": "two-sided"}]
    assert validate_manifest(m2, resolve=False) == []

    # Exercise runners + extractors directly
    rng = np.random.default_rng(10803)
    n = 100
    p = np.clip(rng.normal(0.18, 0.08, n), 0.03, 0.70)
    se = np.full(n, 0.025)
    df_d = pd.DataFrame({"GEOID": [f"26{i:03d}" for i in range(n)], "pov": np.clip(p + rng.normal(0, se), 0.02, 0.85),
                         "pov_se": se})
    rd = _run_designation({"outcome": "pov", "threshold": 0.20}, {"rule": "prob80", "ppv_bootstrap": 50},
                          df_d, 0.90, None, None, {})
    sd = _stat_designation({"statistic": "ppv", "null_value": 0.5}, rd)
    assert np.isfinite(sd["estimate"]) and "confirmatory_refusal" not in sd

    x = rng.normal(10.0, 2.0, 60)
    df_a = pd.DataFrame({"GEOID": [f"26{i:03d}" for i in range(60)], "a": x, "b": x + rng.normal(0.05, 0.4, 60)})
    ra = _run_agreement({"first": "a", "second": "b"}, {}, df_a, 0.90, None, None, {})
    sa = _stat_agreement({"statistic": "ccc", "null_value": 0.0}, ra)
    assert np.isfinite(sa["estimate"]) and sa["ci_lower"] < sa["ci_upper"] and "confirmatory_refusal" not in sa
