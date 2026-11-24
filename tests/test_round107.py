# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 107 tests: final-wave validated repairs (Q2d-prob80, Q2d-point, H2d) and MCP g-formula wiring."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from census import designation as des
from census import repairs107_core as r107
from census import stratified as st
from census import workflows_microdata as wm

ROOT = Path(__file__).resolve().parents[1]


def test_round107_audit_verdicts_match_code():
    audit = json.loads((ROOT / "docs/audits/repairs107_validation.json").read_text())
    v = audit["verdicts"]
    assert v["Q2d-prob80"] is True
    assert v["Q2d-point"] is True
    assert v["H2d"] is True
    assert v["E3b"] is False
    assert v["S2_all"] is False
    assert des.PPV_INTERVAL_VALIDATED["prob80"] is True
    assert des.PPV_INTERVAL_VALIDATED["point"] is True
    assert des.VALIDATED["q2"] is False
    assert st.VALIDATED["pums_hotelling_f"] is True
    assert st.VALIDATED["pums_wald"] is False


def test_designation_ppv_intervals_prob80_and_point():
    rng = np.random.default_rng(10701)
    n = 120
    true_p = np.clip(rng.normal(0.18, 0.08, n), 0.03, 0.70)
    se = np.full(n, 0.025)
    obs = np.clip(true_p + rng.normal(0, se), 0.02, 0.85)
    df = pd.DataFrame({"GEOID": [f"26{i:03d}" for i in range(n)], "pov": obs, "pov_se": se})
    out = des.designation_accuracy(df, "pov", 0.20, se_col="pov_se", ppv_intervals=True, ppv_bootstrap=60, seed=42)
    rules = out["rules"].set_index("rule")
    assert bool(rules.loc["prob80", "ppv_validated"]) is True
    assert bool(rules.loc["point", "ppv_validated"]) is True
    assert bool(rules.loc["prob50", "ppv_validated"]) is False  # 'lower' validated in Round 112
    for r in ("prob80", "point"):
        lo, hi = rules.loc[r, "ppv_lower"], rules.loc[r, "ppv_upper"]
        assert np.isfinite(lo) and np.isfinite(hi) and 0.0 <= lo <= hi <= 1.0


def test_stratified_pums_hotelling_f_gate():
    rng = np.random.default_rng(10702)
    # 3 strata x 600 records -> validated
    K, n_s = 3, 600
    N = K * n_s
    s = np.repeat(np.arange(K), n_s)
    e = rng.binomial(1, 0.5, N)
    p0 = np.array([0.15, 0.25, 0.35])[s]
    y = rng.binomial(1, np.where(e == 1, np.clip(p0 * 1.4, 0.02, 0.98), p0))
    W = np.column_stack([np.ones(N)] + [1.0 + rng.choice([-0.5, 0.5], N) for _ in range(80)])
    out_ok = st.stratified_pums(y, e, s, W, [0, 1, 2], homogeneity_method="hotelling_f")
    assert out_ok["homogeneity"]["rr"]["test"] == "Hotelling F"
    assert out_ok["homogeneity"]["rr"]["validated"] is True
    assert 0.0 <= out_ok["homogeneity"]["rr"]["p"] <= 1.0

    # Small stratum (< 500) -> exploratory
    keep = np.concatenate([np.arange(350), np.arange(600, 1200), np.arange(1200, 1800)])
    out_small = st.stratified_pums(y[keep], e[keep], s[keep], W[keep], [0, 1, 2], homogeneity_method="hotelling_f")
    assert out_small["homogeneity"]["rr"]["validated"] is False


def test_msm_gformula_via_difference_in_differences(tmp_path):
    rng = np.random.default_rng(10703)
    rows = []
    for u in range(40):
        l_prev = rng.normal(0, 1)
        g = np.nan if u < 20 else (2015 if u < 30 else 2017)
        for yr in range(2012, 2020):
            a_prev = 1 if (not np.isnan(g) and yr > g) else 0
            l_cur = 0.5 * l_prev + 0.3 * a_prev + rng.normal(0, 0.8)
            a_cur = 1 if (not np.isnan(g) and yr >= g) else 0
            y = 10.0 - 1.5 * a_cur + 0.7 * l_cur + rng.normal(0, 0.5)
            rows.append({"GEOID": f"{u+1:02d}", "Year": yr, "first_treated": g, "l": l_cur, "y": y})
            l_prev = l_cur
    p = tmp_path / "msm_gf.csv"
    pd.DataFrame(rows).to_csv(p, index=False)
    out = wm.difference_in_differences(str(p), outcome="y", treated="first_treated", period="Year", unit="GEOID",
                                       design="msm", first_treated="first_treated", method="gformula",
                                       time_varying_confounders=["l"], product="1-year")
    assert out["success"] is True
    assert out["validated"] is True
    assert out["method"] == "gformula_jackknife"
    assert len(out["effects"]) == 3


def test_failed_candidates_remain_callable_and_exploratory():
    rng = np.random.default_rng(10704)
    P = np.array([[0.5, 0.3, 0.15, 0.05]])
    Pr = np.clip(P + rng.normal(0, 0.01, (80, 1, 4)), 0.01, 0.99)
    Pr = Pr / Pr.sum(axis=-1, keepdims=True)
    res = r107.diversity_sdr_bc(P, Pr)
    assert np.isfinite(res["estimate"][0]) and res["lower"][0] < res["upper"][0]
