# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 42: multiple imputation, censored Poisson, interrupted series."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from scipy import special

from census import mci_core as mi, missing_censored_its as mc

ROOT = Path(__file__).resolve().parents[1]


def test_rubins_rules_and_engine():
    rng = np.random.default_rng(42); n = 200
    x = rng.normal(size=n); w = .5*x+rng.normal(size=n)*.87; y = 1+.5*x+.5*w+rng.normal(size=n)
    f = pd.DataFrame(dict(x=x, w=np.where(rng.random(n) < .2, np.nan, w), y=y))
    out = mc.impute_and_fit("y ~ x + w", f, "w")
    assert out["validated"] and out["n_missing"] == int(f.w.isna().sum()) and set(out["table"].term) == {"x", "w"}
    with pytest.raises(ValueError, match="no missing"):
        mc.impute_and_fit("y ~ x + w", f.assign(w=w), "w")


def test_censored_loglik_by_hand_and_no_hidden_values_output():
    y = np.array([0., 12., 0.]); X = np.ones((3, 1)); logE = np.log([5., 10., 8.]); cens = np.array([False, False, True])
    ll = mi._censored_loglik_obs(np.array([0.]), y, X, logE, cens)
    assert ll[0] == pytest.approx(-5.) and ll[1] == pytest.approx(12*np.log(10)-10-special.gammaln(13))
    assert ll[2] == pytest.approx(np.log(special.pdtr(9, 8.)-np.exp(-8.)))
    rng = np.random.default_rng(1); n = 300; x = rng.normal(size=n); E = rng.lognormal(np.log(10), 1, n)
    cnt = rng.poisson(E*np.exp(.3*x)).astype(float); f = pd.DataFrame(dict(x=x, E=E, c=cnt, hidden=(cnt >= 1) & (cnt <= 9)))
    out = mc.fit_censored_poisson(f, "c", "hidden", "E", ["x"])
    assert not out["validated"] and out["n_censored"] == int(f.hidden.sum()) and list(out["table"].term) == ["x"]
    assert abs(out["table"].estimate.iloc[0]-.3) < .15


def test_interrupted_series_design_and_guard():
    X = mi.its_design(6, 4)
    np.testing.assert_array_equal(X[:, 2], [0, 0, 0, 1, 1, 1]); np.testing.assert_array_equal(X[:, 3], [0, 0, 0, 1, 2, 3])
    y = X @ np.array([10, .1, 1, .2])+np.random.default_rng(2).normal(size=6)*.1
    with pytest.raises(ValueError, match="at least 8"):
        mc.interrupted_series(y, 3)
    out = mc.interrupted_series(np.r_[y, y+3, y+4][:12], 6, "ols")
    assert not out["validated"] and "EXPLORATORY" in out["notes"][0]


def test_flags_equal_the_fixed_audit():
    passed = json.loads((ROOT/"docs/audits/missing_censored_its_validation.json").read_text())["passed"]
    assert passed == {"A1": False, "A2": False, "C1": False, "D1": True}


def test_fit_model_impute_offline(tmp_path):
    from census import workflows_inference as wi
    rng = np.random.default_rng(3); n = 150; x = rng.normal(size=n); w = x+rng.normal(size=n)
    f = pd.DataFrame(dict(x=x, w=np.where(rng.random(n) < .2, np.nan, w), y=x+w+rng.normal(size=n)))
    p = tmp_path/"f.csv"; f.to_csv(p, index=False)
    assert wi.fit_model(str(p), "y ~ x + w", impute="w")["success"]
