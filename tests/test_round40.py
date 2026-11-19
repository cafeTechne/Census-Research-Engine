# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 40: beta and median regression."""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from statsmodels.othermod.betareg import BetaModel
from statsmodels.regression.quantile_regression import QuantReg

from census import regression_families as rf

ROOT = Path(__file__).resolve().parents[1]
warnings.simplefilter("ignore")


def frame(n=150, seed=40):
    rng = np.random.default_rng(seed); x = rng.normal(size=n)
    mu = 1/(1+np.exp(-(-1.5+.4*x)))
    return pd.DataFrame(dict(x=x, share=rng.beta(30*mu, 30*(1-mu)), y=1+.5*x+rng.lognormal(0, .8, n)))


def test_beta_matches_statsmodels_hc0():
    f = frame(); X = np.column_stack((np.ones(len(f)), f.x))
    ref = BetaModel(f.share.to_numpy(), X).fit(disp=0, cov_type="HC0")
    out = rf.fit_beta("share ~ x", f)
    t = out["table"].set_index("term")
    assert t.loc["x", "estimate"] == pytest.approx(np.asarray(ref.params)[1]) and t.loc["x", "se"] == pytest.approx(np.asarray(ref.bse)[1])
    with pytest.raises(ValueError, match="between 0 and 1"):
        rf.fit_beta("y ~ x", f.assign(y=f.y*10))


def test_median_matches_statsmodels():
    f = frame(); X = np.column_stack((np.ones(len(f)), f.x))
    ref = QuantReg(f.y.to_numpy(), X).fit(q=.5, max_iter=5000)
    t = rf.fit_median("y ~ x", f)["table"].set_index("term")
    assert t.loc["x", "estimate"] == pytest.approx(np.asarray(ref.params)[1]) and t.loc["x", "se"] == pytest.approx(np.asarray(ref.bse)[1])


def test_flags_equal_the_fixed_audit():
    passed = json.loads((ROOT/"docs/audits/beta_median_validation.json").read_text())["passed"]
    assert passed["B2"] and not passed["B1"] and passed["Q1"]


def test_fit_model_tool_offline(tmp_path):
    from census import workflows_inference as wi
    f = frame(); p = tmp_path/"f.csv"; f.to_csv(p, index=False)
    assert wi.fit_model(str(p), "share ~ x", model="beta")["success"]
    assert wi.fit_model(str(p), "y ~ x", model="median")["success"]
