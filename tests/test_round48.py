# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 48: interrupted series bootstrap-t, effective-n correlations and alpha, truncated HKSJ, robust limits."""
import json
import warnings
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd
import pytest

from census import agreement_core as ag, evidence, evidence_core as ev, mci_core as mi
from census import small_spatial as ss, small_spatial_core as sc

ROOT = Path(__file__).resolve().parents[1]
warnings.simplefilter("ignore")
AUDIT = json.loads((ROOT/"docs/audits/small_spatial_validation.json").read_text())


def test_flags_equal_the_fixed_audit():
    p = AUDIT["passed"]
    assert AUDIT["criterion_commit"] == "3fb07d3" and AUDIT["draws_per_cell"] == 2000
    assert p["I2_min_n"] == ss.ITS_BOOTSTRAP_MIN_N == 30 and p["I1_min_n"] is None and not ss.ITS_REML_VALIDATED
    for m in ("spearman", "kendall", "pearson"):
        assert p[f"C1_{m}"] == ss.NEFF_CORRELATION_VALIDATED[m]
    assert p["A3"] == ss.NEFF_ALPHA_VALIDATED and not p["A4"]
    assert p["H2"] and ss.HKSJ_TRUNCATED_MAX_K == 10
    assert p["B1r"] and p["B2r"] and ss.LIMITS_ROBUST_VALIDATED


def test_reml_phi_maximises_restricted_likelihood_and_phi0_is_ols():
    rng = np.random.default_rng(1); n = 30
    X = mi.its_design(n, 16)
    e = rng.standard_normal(n); u = np.empty(n); u[0] = e[0]/np.sqrt(1-.36)
    for t in range(1, n):
        u[t] = .6*u[t-1]+e[t]
    y = X @ [0, 0, 1, .2]+u
    b, se, phi = sc.reml_ar1(y, X)
    grid = np.linspace(-.95, .95, 3801)
    assert phi == pytest.approx(grid[np.argmin([sc._neg_reml(g, y, X) for g in grid])], abs=1e-3)
    b0, _, _ = sc._gls(y, X, 0.)
    np.testing.assert_allclose(b0, np.linalg.lstsq(X, y, rcond=None)[0], atol=1e-10)


def test_interrupted_series_engine_flags():
    from census.missing_censored_its import interrupted_series
    rng = np.random.default_rng(2)
    y30, y20 = rng.normal(size=30).cumsum()*.1, rng.normal(size=20)
    v = interrupted_series(y30, 15, method="bootstrap_t")
    assert v["validated"] and v["level_change"]["lower"] < v["level_change"]["upper"]
    assert not interrupted_series(y20, 10, method="bootstrap_t")["validated"]
    assert not interrupted_series(y30, 15, method="reml")["validated"]


def grid_coords(n=144):
    ids = [f"{26 if i < 72 else 36}{i:03d}" for i in range(n)]
    return pd.DataFrame(dict(GEOID=ids, lon=-85+(np.arange(n) % 12)*.3, lat=41+(np.arange(n)//12)*.3))


def test_effective_n_iid_near_n_and_smaller_for_smooth_fields():
    c = grid_coords(); n = len(c)
    from census.spatial_hac import haversine_matrix
    D = haversine_matrix(c.lon, c.lat); cls = sc.class_index(D)
    rng = np.random.default_rng(3)
    iid = sc.effective_n(rng.normal(size=n), rng.normal(size=n), cls)
    L = np.linalg.cholesky(np.exp(-D/100)+1e-10*np.eye(n))
    smooth = sc.effective_n(L @ rng.normal(size=n), L @ rng.normal(size=n), cls)
    assert iid > .7*n and smooth < .6*iid


def test_limits_robust_close_to_bland_altman_for_normal_differences():
    rng = np.random.default_rng(4); x = rng.normal(size=4000); y = x+.3+rng.normal(size=4000)*.5
    r, base = sc.limits_robust(x, y), ag.limits_observed(x, y)
    assert r["lower_limit"] == pytest.approx(base["lower_limit"])
    w = lambda d: d["lower_ci"][1]-d["lower_ci"][0]
    assert w(r) == pytest.approx(w(base), rel=.1)


def test_hksj_truncated_equals_hksj_when_q_at_least_one():
    th, se = np.array([0., 1., -1., 2., .5]), np.full(5, .3)
    t, h = sc.hksj_truncated(th, se), ev.pooled(th, se, "hksj")
    assert t["q"] == pytest.approx(1) and t["lower"] == pytest.approx(h["lower"])   # Paule-Mandel sets q = 1 when tau2 > 0
    flat, s2 = np.zeros(6), np.full(6, 1.)
    assert sc.hksj_truncated(flat, s2)["se"] == pytest.approx(np.sqrt(1/6))


def test_engine_correlations_alpha_pooling_and_agreement_flags():
    from census.agreement import check_agreement
    from census.composite_index import build_index
    from census.correlation import validated_correlations
    c = grid_coords(); n = len(c); rng = np.random.default_rng(5)
    f = c[["GEOID"]].assign(a=rng.normal(size=n), b=rng.normal(size=n), d=rng.normal(size=n))
    t = validated_correlations(f, ["a", "b"], "spearman", coords=c)
    assert t.validated.all() and "n_eff" in t and 0 < t.n_eff.iloc[0] <= n
    base = validated_correlations(f, ["a", "b"], "spearman")
    assert base.estimate.iloc[0] == pytest.approx(t.estimate.iloc[0])
    z = rng.normal(size=n)
    g = c[["GEOID"]].assign(**{k: z+rng.normal(size=n) for k in ("p", "q", "r")})
    a = build_index(g, ["p", "q", "r"], coords=c)["cronbach_alpha"]
    assert a["validated"] and "effective" in a["method"]
    k7 = evidence.combine_estimates(rng.normal(size=7).tolist(), [.5]*7)
    assert k7["validated"] and k7["pooled"]["method"] == "hksj_truncated"
    out = check_agreement(f, "a", "b")
    assert out["limits_observed"]["validated"] and not out["ccc"]["validated"]


def test_mcp_correlation_matrix_spatial(tmp_path):
    from census import workflows_inference as wi
    c = grid_coords(); rng = np.random.default_rng(6)
    f = c[["GEOID"]].assign(Year=2022, a=rng.normal(size=len(c)), b=rng.normal(size=len(c)))
    p = tmp_path/"f.csv"; f.to_csv(p, index=False)
    with mock.patch("census.small_spatial.frame_coordinates", return_value=c):
        out = wi.correlation_matrix(str(p), ["a", "b"], method="kendall", spatial=True)
    assert out["success"] and "n_eff" in out["validated_intervals"][0]
