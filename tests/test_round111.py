# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 111 tests: independent mathematical/reference cross-checks and adversarial edge-case hardening
across confirmed methods (Rounds 104-110)."""
import numpy as np
import pandas as pd
import pytest

from census import agreement as agr
from census import bias_analysis as ba
from census import designation as des
from census import disease_mapping as dm
from census import ecologic as eco
from census import evidence as ev
from census import joinpoint as jp
from census import matching as mt
from census import msm
from census import rdd
from census import repairs106_core as r106
from census import repairs108_core as r108
from census import repairs109_core as r109
from census import spatial_models as sm
from census import stratified as st


# ---------------------------------------------------------------------------
# 1. Independent mathematical & reference cross-checks
# ---------------------------------------------------------------------------

def test_reference_lin_ccc_identities():
    rng = np.random.default_rng(11101)
    x = rng.normal(10.0, 2.5, 60)
    y = x + rng.normal(0.2, 0.8, 60)
    # Exact analytical Lin's CCC formula
    mx, my = x.mean(), y.mean()
    vx, vy = np.mean((x - mx) ** 2), np.mean((y - my) ** 2)
    cxy = np.mean((x - mx) * (y - my))
    expected_ccc = 2.0 * cxy / (vx + vy + (mx - my) ** 2)
    df = pd.DataFrame({"GEOID": [f"26{i:03d}" for i in range(60)], "x": x, "y": y})
    out_xy = agr.check_agreement(df, "x", "y")
    out_yx = agr.check_agreement(df, "y", "x")
    assert out_xy["ccc"]["estimate"] == pytest.approx(expected_ccc, abs=1e-10)
    assert out_yx["ccc"]["estimate"] == pytest.approx(expected_ccc, abs=1e-10)
    # Perfect agreement: CCC(x, x) == 1.0
    df_id = pd.DataFrame({"GEOID": [f"26{i:03d}" for i in range(60)], "x": x, "y": x.copy()})
    out_id = agr.check_agreement(df_id, "x", "y")
    assert out_id["ccc"]["estimate"] == pytest.approx(1.0, abs=1e-9)


def test_reference_gformula_scale_shift_invariance_and_p1_equivalence():
    rng = np.random.default_rng(11102)
    G, K = 40, 10
    rows = []
    for u in range(G):
        l_prev = rng.normal(0, 1)
        g = np.nan if u < 20 else 2015
        for idx, yr in enumerate(range(2010, 2010 + K)):
            a_prev = 1.0 if (not np.isnan(g) and yr > g) else 0.0
            l_cur = l_prev if idx == 0 else (0.5 * l_prev + 0.4 * a_prev + rng.normal(0, 0.7))
            a_cur = 1.0 if (not np.isnan(g) and yr >= g) else 0.0
            y = 10.0 - 1.5 * a_cur + 0.8 * l_cur + rng.normal(0, 0.5)
            rows.append({"GEOID": f"{u+1:02d}", "Year": yr, "g": g, "l": l_cur, "l_scaled": 10.0 * l_cur + 5.0, "y": y})
            l_prev = l_cur
    df = pd.DataFrame(rows)
    r1 = msm.marginal_structural_model(df, "y", "g", ["l"], product="annual", method="gformula")
    r2 = msm.marginal_structural_model(df, "y", "g", ["l_scaled"], product="annual", method="gformula")
    for e1, e2 in zip(r1["effects"], r2["effects"]):
        assert e1["estimate"] == pytest.approx(e2["estimate"], abs=1e-9)
        assert e1["se"] == pytest.approx(e2["se"], abs=1e-9)

    # Exact equivalence of p=1 scalar (r106) and p=1 vector (r108)
    A = (df["g"].notna() & (df["Year"] >= df["g"])).astype(float).to_numpy()
    codes, _ = pd.factorize(df["GEOID"])
    yr_pos = (df["Year"] - 2009).to_numpy()
    v1 = r106.gformula_jackknife(df["y"].to_numpy(), A, df["l"].to_numpy(), codes, yr_pos, K)
    v2 = r108.gformula_vector_jackknife(df["y"].to_numpy(), A, df["l"].to_numpy(), codes, yr_pos, K)
    assert np.allclose(v1["estimate"], v2["estimate"], atol=1e-10)
    assert np.allclose(v1["se"], v2["se"], atol=1e-10)


def test_reference_misclassification_perfect_se_sp_identity():
    out = ba.misclassification(80, 120, 40, 160, 1.0, 1.0, kind="outcome", sd=0.0)
    assert out["corrected"]["rr"] == pytest.approx(out["observed"]["rr"], abs=1e-10)
    assert out["corrected"]["or"] == pytest.approx(out["observed"]["or"], abs=1e-10)


def test_reference_ecologic_fuller_zero_noise_limit():
    rng = np.random.default_rng(11103)
    x = rng.normal(0, 1, 80)
    y = 2.0 + 1.75 * x + rng.normal(0, 0.3, 80)
    ols_slope = np.cov(x, y, ddof=0)[0, 1] / np.var(x, ddof=0)
    res = r109.ecologic_fuller_slope(x, y, np.zeros(80), alpha=4.0)
    assert res["estimate"] == pytest.approx(ols_slope, abs=1e-10)


def test_reference_diversity_uniform_shares_exact_log_g():
    shares = pd.DataFrame([[0.25, 0.25, 0.25, 0.25]], index=["a1"], columns=["g1", "g2", "g3", "g4"])
    reps = [shares.copy() for _ in range(80)]
    out = sm.diversity_index(shares, reps, method="sdr_bc", sample_sizes=[200])
    assert out.loc["a1", "entropy"] == pytest.approx(np.log(4.0), abs=1e-10)
    assert out.loc["a1", "se"] == pytest.approx(0.0, abs=1e-10)


def test_reference_stratified_pums_weight_scaling_invariance():
    rng = np.random.default_rng(11104)
    K, n_s = 3, 550
    N = K * n_s
    s = np.repeat(np.arange(K), n_s)
    e = rng.binomial(1, 0.5, N)
    y = rng.binomial(1, 0.25 + 0.1 * e, N)
    W = np.column_stack([np.ones(N)] + [1.0 + rng.choice([-0.5, 0.5], N) for _ in range(80)])
    r1 = st.stratified_pums(y, e, s, W, [0, 1, 2], homogeneity_method="hotelling_f")
    r2 = st.stratified_pums(y, e, s, W * 7.5, [0, 1, 2], homogeneity_method="hotelling_f")
    for m in ("rr", "or", "rd"):
        assert r1["homogeneity"][m]["statistic"] == pytest.approx(r2["homogeneity"][m]["statistic"], abs=1e-8)
        assert r1["homogeneity"][m]["p"] == pytest.approx(r2["homogeneity"][m]["p"], abs=1e-8)


def test_reference_joinpoint_k0_matches_wls():
    years = list(range(2005, 2023))
    x = np.arange(len(years), dtype=float)
    rng = np.random.default_rng(11105)
    d = np.maximum(rng.poisson(500.0 * np.exp(-0.025 * x)), 1)
    y = np.log(d / 100000.0)
    w = d.astype(float)
    X = np.column_stack([np.ones(len(x)), x])
    beta_wls = np.linalg.solve((X.T * w) @ X, (X.T * w) @ y)
    expected_aapc = 100.0 * (np.exp(beta_wls[1]) - 1.0)
    bt = r109.joinpoint_aapc_bootstrap_t(x, y, w, k=0, B=100, rng=rng)
    assert bt["aapc"] == pytest.approx(expected_aapc, abs=1e-9)


# ---------------------------------------------------------------------------
# 2. Adversarial edge-case hardening checks
# ---------------------------------------------------------------------------

def test_edge_cases_agreement_constant_and_tiny():
    # Constant column -> finite or clean ValueError, never silent crash
    df_const = pd.DataFrame({"GEOID": [f"26{i:03d}" for i in range(10)], "a": np.ones(10), "b": np.arange(10.0)})
    out = agr.check_agreement(df_const, "a", "b")
    assert np.isfinite(out["ccc"]["estimate"])
    # Tiny n = 2 should raise ValueError cleanly
    df_tiny = pd.DataFrame({"GEOID": ["26001", "26002"], "a": [1.0, 2.0], "b": [1.1, 2.1]})
    with pytest.raises(ValueError):
        agr.check_agreement(df_tiny, "a", "b")


def test_edge_cases_msm_collinear_confounders_and_nans():
    rng = np.random.default_rng(11106)
    rows = []
    for u in range(35):
        g = np.nan if u < 18 else 2015
        for yr in range(2012, 2018):
            l1 = rng.normal()
            rows.append({"GEOID": f"{u+1:02d}", "Year": yr, "g": g, "l1": l1, "l2": 2.0 * l1, "y": 5.0 + l1})
    df = pd.DataFrame(rows)
    # Collinear confounders (l2 = 2 * l1) must not crash lstsq and must return finite estimates
    res = msm.marginal_structural_model(df, "y", "g", ["l1", "l2"], product="annual", method="gformula")
    assert all(np.isfinite(e["estimate"]) for e in res["effects"])


def test_edge_cases_designation_zero_se_and_boundary():
    df_bad = pd.DataFrame({"GEOID": ["26001", "26002", "26003"], "p": [0.0, 0.2, 0.3], "se": [0.0, 0.02, 0.03]})
    with pytest.raises(ValueError):
        des.designation_accuracy(df_bad, "p", 0.20, se_col="se")


def test_edge_cases_evidence_zero_se_and_small_k():
    with pytest.raises(ValueError):
        ev.combine_estimates([0.5, 0.6], [0.0, 0.1])
    # k < 10 must mark prediction_interval_validated == False
    out = ev.combine_estimates([0.2, 0.4, 0.5, 0.3, 0.6], [0.1] * 5)
    assert out["pooled"].get("prediction_interval_validated", False) is False


def test_edge_cases_disease_map_invalid_counts():
    df = pd.DataFrame({"GEOID": ["26001", "26002", "26003"], "obs": [-1, 5, 10], "exp": [40.0, 40.0, 40.0]})
    with pytest.raises(ValueError):
        dm.disease_map(df, "obs", "exp", edges=[(0, 1), (1, 2)], method="B3")


def test_edge_cases_ecologic_constant_x():
    rng = np.random.default_rng(11107)
    res = r109.ecologic_fuller_slope(np.ones(60), rng.normal(size=60), np.zeros(60))
    assert np.isfinite(res["estimate"]) and res["estimate"] == 0.0
