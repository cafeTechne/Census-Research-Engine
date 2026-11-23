# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 102: meta-analysis completeness."""
import json
from pathlib import Path

import numpy as np
import pytest

from census import meta_core as mc
from census.evidence import combine_estimates

ROOT = Path(__file__).resolve().parents[1]


def _data(k=15, seed=1, tau=.2):
    rng = np.random.default_rng(seed); v = (.1*10**rng.uniform(0, 1, k))**2
    return .3+rng.normal(0, tau, k)+rng.normal(0, np.sqrt(v)), v


def test_reml_matches_pm_without_heterogeneity_and_q_profile_contains_estimate():
    y, v = _data(tau=0.0)
    assert mc.tau2_reml(y, v) == pytest.approx(0, abs=1e-6) or mc.tau2_reml(y, v) < .005
    y, v = _data()
    lo, hi = mc.q_profile(y, v)
    t2 = mc.meta(y, v)["tau2"]
    assert lo <= t2 <= hi


def test_prediction_interval_wider_than_ci():
    y, v = _data()
    r = mc.meta(y, v)
    assert r["pi_lower"] < r["lower"] and r["upper"] < r["pi_upper"]


def test_meta_regression_and_egger():
    rng = np.random.default_rng(2); k = 30; v = np.full(k, .01); x = rng.normal(size=k)
    y = .3+.5*x+rng.normal(0, .1, k)
    r = mc.meta_regression(y, v, x, perms=99, rng=rng)
    assert r["lower"][1] < .5 < r["upper"][1] and r["p_permutation"][1] <= .02
    e = mc.egger(*_data(k=20))
    assert 0 <= e["p"] <= 1


def test_combine_estimates_options_and_refusals():
    y, v = _data(k=12)
    r = combine_estimates(y, np.sqrt(v), moderators=np.arange(12.), leave_one_out=True, small_study_test=True)
    assert r["heterogeneity"]["tau2_interval"]["validated"] and len(r["leave_one_out"]) == 12
    assert not r["meta_regression"]["validated"] and not r["small_study_test"]["validated"]
    y4, v4 = _data(k=4)
    with pytest.raises(ValueError, match="10"):
        combine_estimates(y4, np.sqrt(v4), small_study_test=True)
    with pytest.raises(ValueError, match="10"):
        combine_estimates(y4, np.sqrt(v4), moderators=[1, 2, 3, 4])


def test_audit_outcome_recorded():
    out = json.loads((ROOT/"docs/audits/meta_validation.json").read_text())["outcome"]
    assert out["H1"]["passed"] and not out["P1-PM"]["passed"] and not out["R1"]["passed"] and not out["E1"]["passed"]
