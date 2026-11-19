# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 39: multivariate group tests and count models."""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from statsmodels.multivariate.manova import MANOVA

from census import count_models as cm, manova_counts_core as mc

ROOT = Path(__file__).resolve().parents[1]
warnings.simplefilter("ignore")


def data(n=150, seed=39):
    rng = np.random.default_rng(seed)
    f = pd.DataFrame(dict(GEOID=[f"26{i:03d}" for i in range(n)], Year=2022, x=rng.normal(size=n), g=rng.choice(list("abc"), n)))
    f["a"] = rng.normal(size=n); f["b"] = .5*f.a+rng.normal(size=n)
    f["E"] = rng.lognormal(3, 1, n); f["y"] = rng.poisson(f.E*np.exp(.3*f.x)*rng.gamma(2, .5, n)).astype(float)
    return f


def test_pillai_matches_statsmodels():
    f = data()
    X = np.column_stack((np.ones(len(f)), (f.g == "b").astype(float), (f.g == "c").astype(float)))
    ours = mc.pillai(X, f[["a", "b"]].to_numpy(), [1, 2])
    ref = MANOVA.from_formula("a + b ~ C(g)", f).mv_test().results["C(g)"]["stat"]
    assert ours["statistic"] == pytest.approx(ref.loc["Pillai's trace", "Value"])
    assert ours["p"] == pytest.approx(ref.loc["Pillai's trace", "Pr > F"])


def test_multivariate_score_by_hand():
    f = data(); X = np.column_stack((np.ones(len(f)), (f.g == "b").astype(float), (f.g == "c").astype(float)))
    Y = f[["a", "b"]].to_numpy()
    a = mc._contrib(X, Y, [1, 2])
    R = Y-Y.mean(axis=0)                                   # restricted model: intercept only
    J = np.linalg.inv(X.T@X)
    expect = np.concatenate([(J@(X*R[:, [k]]).T)[[1, 2]].T for k in range(2)], axis=1)
    np.testing.assert_allclose(a, expect, atol=1e-12)
    r1 = mc.mv_wild_score(X, Y, [1, 2], np.zeros((4, 4)), np.random.default_rng(1))
    r2 = mc.mv_wild_score(X, Y, [1, 2], np.zeros((4, 4)), np.random.default_rng(1))
    assert r1 == r2 and r1["df"] == 4


def test_negbin_matches_statsmodels_glm_hc3():
    f = data(); X = sm.add_constant(f[["x"]]).to_numpy()
    alpha = np.asarray(sm.NegativeBinomial(f.y.to_numpy(), X, exposure=f.E.to_numpy()).fit(disp=0).params)[-1]
    ref = sm.GLM(f.y.to_numpy(), X, family=sm.families.NegativeBinomial(alpha=alpha), exposure=f.E.to_numpy()).fit(cov_type="HC3")
    out = cm.fit_count_model("y ~ x", f, "E")
    assert out["table"].estimate.iloc[0] == pytest.approx(ref.params[1]) and out["table"].se.iloc[0] == pytest.approx(ref.bse[1])
    assert out["validated"] and not cm.fit_count_model("y ~ x", f, "E", "poisson")["validated"]


def test_multivariate_engine_and_refusals():
    f = data()
    out = cm.compare_groups_multivariate(f, ["a", "b"], "g", covariates=["x"])
    assert out["q"] == 2 and 0 < out["p_value"] <= 1 and "pillai" in out
    with pytest.raises(ValueError, match="two outcomes"):
        cm.compare_groups_multivariate(f, ["a"], "g")


def test_flags_equal_the_fixed_audit():
    passed = json.loads((ROOT/"docs/audits/manova_counts_validation.json").read_text())["passed"]
    assert passed == {"V1": True, "negbin": True, "poisson": False, "zip": False}
    assert cm.VALIDATED_FAMILIES == {"negbin": True, "poisson": False, "zip": False}


def test_mcp_paths_offline(tmp_path):
    from census import workflows_inference as wi
    f = data(); p = tmp_path/"f.csv"; f.to_csv(p, index=False)
    assert wi.compare_groups(str(p), "a", "g", outcomes=["a", "b"])["success"]
    nb = wi.fit_model(str(p), "y ~ x", model="negbin", exposure="E")
    assert nb["success"] and nb["validated"]
