# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 47: calibrated AIPW and mediation, Anderson-Rubin intervals, chained-equations MI."""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from census import causal, causal_core as cc, causal_robustness_core as cr
from census.missing_censored_its import CHAINED_VALIDATED, impute_and_fit

ROOT = Path(__file__).resolve().parents[1]
warnings.simplefilter("ignore")
AUDIT = json.loads((ROOT/"docs/audits/causal_robustness_validation.json").read_text())


def test_flags_equal_the_fixed_audit():
    p = AUDIT["passed"]
    assert p == {"T1": True, "S1": True, "D1": True, "W2": True, "W1_cutoff_f": 0}
    assert AUDIT["criterion_commit"] == "cbdc97f" and AUDIT["draws_per_cell"] == 2000
    assert causal.CALIBRATED_TREATMENT_VALIDATED == p["T1"] and causal.CALIBRATED_MEDIATION_VALIDATED == p["S1"]
    assert causal.AR_VALIDATED == p["W2"] and causal.IV_WALD_F_CUTOFF == p["W1_cutoff_f"] and CHAINED_VALIDATED == p["D1"]


def test_aipw_point_matches_statsmodels():
    rng = np.random.default_rng(1); n = 145
    z = rng.normal(size=(n, 2)); T = rng.binomial(1, 1/(1+np.exp(-z.sum(1)/2))).astype(float)
    y = 1+.5*T+z.sum(1)/2+rng.normal(size=n)
    assert cr.aipw_point(y, T, z) == pytest.approx(cc.treatment_effect(y, T, z, "aipw")["estimate"], abs=1e-10)


def test_calibrate_matches_engine_regression_calibration():
    from census import models
    rng = np.random.default_rng(2); n = 120
    x, c = rng.normal(size=n), rng.normal(size=n); s = .4*rng.lognormal(0, .5, n); w = x+rng.normal(size=n)*s
    f = pd.DataFrame(dict(w=w, w_se=s, c=c, y=x+c+rng.normal(size=n)))
    ref = models._calibrate(f, {"w": "w_se"}, ["c"])["w"].to_numpy()
    np.testing.assert_allclose(cr.calibrate(w, s**2, c)[:, 0], ref, atol=1e-12)


@pytest.mark.parametrize("seed,pi", [(2, .6), (5, .15), (11, .02)])
def test_anderson_rubin_matches_grid_inversion(seed, pi):
    rng = np.random.default_rng(seed); n = 145
    z = rng.normal(size=n); x = pi*z+rng.normal(size=n); y = 1+.5*x+rng.normal(size=n)
    ar = cr.anderson_rubin(y, x, z)
    grid = np.linspace(-40, 40, 160001)
    zt, u = z-z.mean(), (y-y.mean())[None, :]-grid[:, None]*(x-x.mean())[None, :]
    g = (u @ zt)/(zt @ zt); F = g**2*(zt @ zt)/(((u**2).sum(1)-g**2*(zt @ zt))/(n-2))
    accept = F <= stats.f.ppf(.9, 1, n-2)
    assert all(cr.ar_covers(ar, b) == a for b, a in zip(grid[::97], accept[::97]))


def noisy_treatment(n=145, seed=3):
    rng = np.random.default_rng(seed)
    z = rng.normal(size=(n, 2)); T = rng.binomial(1, 1/(1+np.exp(-(.5*z[:, 0]+.5*z[:, 1])))).astype(float)
    y = 1+.5*T+.5*z.sum(1)+rng.normal(size=n); s = np.full((n, 2), .6)
    W = z+rng.normal(size=(n, 2))*s
    return pd.DataFrame(dict(y=y, T=T, a=W[:, 0], b=W[:, 1], a_se=s[:, 0], b_moe=1.645*s[:, 1])), W, s


def test_estimate_effect_calibrated_equals_frozen_core():
    f, W, s = noisy_treatment()
    out = causal.estimate_effect(f, "y", "T", ["a", "b"], calibrate=True, seed=7)
    ref = cr.aipw_calibrated(f.y.to_numpy(), f["T"].to_numpy(), W, s**2, np.random.default_rng(7))
    assert out["ate"]["estimate"] == pytest.approx(ref["estimate"]) and out["ate"]["lower"] == pytest.approx(ref["lower"])
    assert out["validated"] and out["calibrated"] == ["a", "b"]
    plain = causal.estimate_effect(f, "y", "T", ["a", "b"])
    assert not plain["validated"] and any("calibrate=True" in n for n in plain["notes"])
    with pytest.raises(ValueError, match="aipw"):
        causal.estimate_effect(f, "y", "T", ["a", "b"], method="ipw", calibrate=True)


def test_estimate_effect_calibrated_with_an_error_free_confounder():
    f, _, _ = noisy_treatment()
    f["c"] = np.random.default_rng(4).normal(size=len(f))
    out = causal.estimate_effect(f, "y", "T", ["a", "c"], calibrate=True)
    assert out["calibrated"] == ["a"] and any("Error-free confounders" in n for n in out["notes"])


def test_mediation_calibrated_equals_frozen_core():
    rng = np.random.default_rng(5); n = 145
    x = rng.normal(size=n); m = .4*x+rng.normal(size=n); y = .3*x+.5*m+rng.normal(size=n); s = np.full(n, .5)
    f = pd.DataFrame(dict(x=x, w=m+rng.normal(size=n)*s, w_se=s, y=y))
    out = causal.mediation(f, "x", "w", "y", calibrate=True, seed=9)
    ref = cr.mediation_calibrated(x, f.w.to_numpy(), s**2, y, np.random.default_rng(9))
    assert out["indirect"]["estimate"] == pytest.approx(ref["estimate"]) and out["validated"]
    naive = causal.mediation(f, "x", "w", "y")
    assert out["indirect"]["estimate"] > naive["indirect"]["estimate"]
    with pytest.raises(ValueError, match="without controls"):
        causal.mediation(f.assign(c=1.), "x", "w", "y", controls=["c"], calibrate=True)


def test_iv_reports_anderson_rubin_and_weak_note():
    rng = np.random.default_rng(6); n = 145; t = rng.normal(size=n)
    f = pd.DataFrame(dict(x=t+rng.normal(size=n)*.5, z=.05*t+rng.normal(size=n), y=.5*t+rng.normal(size=n)))
    out = causal.iv_slope(f, "y", "x", "z")
    assert out["ar_interval"]["kind"] in ("bounded", "disjoint", "real_line", "empty") and out["ar_validated"]
    assert out["first_stage_f"] < 10 and any("WEAK INSTRUMENT" in n for n in out["notes"])


def two_missing(n=200, seed=8):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=(n, 2)); y = 1+.5*x.sum(1)+rng.normal(size=n)
    f = pd.DataFrame(dict(y=y, a=x[:, 0], b=x[:, 1], c=rng.normal(size=n)))
    f.loc[rng.random(n) < .25, "a"] = np.nan; f.loc[rng.random(n) < .25, "b"] = np.nan
    return f


def test_impute_two_covariates_equals_chained_core():
    f = two_missing()
    out = impute_and_fit("y ~ a + b + c", f, ["a", "b"], seed=1)
    X = np.column_stack((np.ones(len(f)), f[["a", "b", "c"]].to_numpy()))
    ref = cr.chained_mi(f.y.to_numpy(), X, [1, 2], np.random.default_rng(1))
    t = out["table"].set_index("term")
    assert t.loc["a", "estimate"] == pytest.approx(ref[1]["estimate"]) and t.loc["b", "upper"] == pytest.approx(ref[2]["upper"])
    assert all(0 < d <= len(f)-4 for d in t.df) and out["validated"]
    single = f.assign(b=f.b.fillna(0.))
    assert impute_and_fit("y ~ a + b", single, ["a"]).keys() == impute_and_fit("y ~ a + b", single, "a").keys()
    with pytest.raises(ValueError, match="one or two"):
        impute_and_fit("y ~ a + b + c", f, ["a", "b", "c"])


def test_mcp_wrappers(tmp_path):
    from census import workflows_inference as wi
    f = two_missing(); p = tmp_path/"f.csv"; f.to_csv(p, index=False)
    out = wi.fit_model(str(p), "y ~ a + b + c", impute=["a", "b"])
    assert out["success"] and "chained equations" in out["summary"]
    rng = np.random.default_rng(6); n = 145; t = rng.normal(size=n)
    g = pd.DataFrame(dict(x=t+rng.normal(size=n)*.5, z=t+rng.normal(size=n)*.5, y=.5*t+rng.normal(size=n)))
    q = tmp_path/"g.csv"; g.to_csv(q, index=False)
    out = wi.estimate_effect(str(q), "iv", "y", x="x", instrument="z")
    assert out["success"] and "Anderson-Rubin" in out["summary"]
    h, _, _ = noisy_treatment(); r = tmp_path/"h.csv"; h.to_csv(r, index=False)
    out = wi.estimate_effect(str(r), "treatment", "y", treatment="T", confounders=["a", "b"], calibrate=True)
    assert out["success"] and "Validated" in out["summary"]
