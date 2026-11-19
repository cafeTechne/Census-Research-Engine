# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 41: causal tools."""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from statsmodels.sandbox.regression.gmm import IV2SLS

from census import causal, causal_core as cc

ROOT = Path(__file__).resolve().parents[1]
warnings.simplefilter("ignore")


def frame(n=200, seed=41):
    rng = np.random.default_rng(seed)
    z = rng.normal(size=(n, 2)); T = rng.binomial(1, 1/(1+np.exp(-(.5*z[:, 0]-.5*z[:, 1]))))
    x = rng.normal(size=n)
    return pd.DataFrame(dict(z1=z[:, 0], z2=z[:, 1], T=T, y=1+.5*T+z.sum(axis=1)+rng.normal(size=n),
                             x1=x+rng.normal(size=n)*.6, x2=x+rng.normal(size=n)*.6, yx=1+.5*x+rng.normal(size=n),
                             X=x, M=.4*x+rng.normal(size=n)))


def test_2sls_point_estimate_matches_statsmodels():
    f = frame()
    ref = IV2SLS(f.yx, sm.add_constant(f.x1), sm.add_constant(f.x2)).fit()
    assert cc.iv_2sls(f.yx, f.x1, f.x2)["estimate"] == pytest.approx(ref.params.iloc[1])


def test_sobel_by_hand():
    f = frame(); f["Y"] = .3*f.X+.5*f.M+np.random.default_rng(1).normal(size=len(f))
    a, sa, b, sb = cc._paths(f.X.to_numpy(), f.M.to_numpy(), f.Y.to_numpy())
    r = cc.mediation(f.X, f.M, f.Y, "sobel")
    assert r["estimate"] == pytest.approx(a*b) and r["se"] == pytest.approx(np.sqrt(b**2*sa**2+a**2*sb**2))


def test_engine_flags_and_refusals():
    f = frame()
    t = causal.estimate_effect(f, "y", "T", ["z1", "z2"])
    assert t["validated"] and 0 < t["ate"]["estimate"] < 1.5
    f2 = f.assign(z1_se=.3)
    assert any("residual confounding" in n for n in causal.estimate_effect(f2, "y", "T", ["z1", "z2"])["notes"])
    with pytest.raises(ValueError, match="0/1"):
        causal.estimate_effect(f.assign(T=f["T"]*2), "y", "T", ["z1"])
    iv = causal.iv_slope(f, "yx", "x1", "x2")
    assert iv["validated"] and abs(iv["iv"]["estimate"]-.5) < abs(iv["ols_naive"]["estimate"]-.5)
    f["Y"] = .3*f.X+.5*f.M
    assert causal.mediation(f, "X", "M", "Y", method="sobel")["validated"]
    assert not causal.mediation(f.assign(M_se=.2), "X", "M", "Y", method="sobel")["validated"]


def test_flags_equal_the_fixed_audit():
    passed = json.loads((ROOT/"docs/audits/causal_validation.json").read_text())["passed"]
    assert all(passed[k] for k in ("T1", "T2", "T3", "I1", "S1", "S2"))


def test_tool_offline(tmp_path):
    from census import workflows_inference as wi
    f = frame(); p = tmp_path/"f.csv"; f.to_csv(p, index=False)
    assert wi.estimate_effect(str(p), "treatment", "y", treatment="T", confounders=["z1", "z2"])["success"]
    assert wi.estimate_effect(str(p), "iv", "yx", x="x1", instrument="x2")["success"]
    assert not wi.estimate_effect(str(p), "nope", "y")["success"]
