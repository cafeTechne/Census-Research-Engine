# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 38: combining evidence."""
import json
from pathlib import Path

import numpy as np
import pytest
from scipy import stats
from statsmodels.stats.meta_analysis import combine_effects

from census import evidence, evidence_core as ev

ROOT = Path(__file__).resolve().parents[1]
TH, SE = np.array([.1, .4, .25, .9]), np.array([.1, .2, .15, .3])


def test_tau2_and_pooled_match_statsmodels():
    assert ev.tau2_dl(TH, SE) == pytest.approx(combine_effects(TH, SE**2, method_re="chi2").tau2)
    assert ev.tau2_pm(TH, SE) == pytest.approx(combine_effects(TH, SE**2, method_re="iterated").tau2, rel=1e-4)
    assert ev.pooled(TH, SE, "fixed")["estimate"] == pytest.approx(combine_effects(TH, SE**2).mean_effect_fe)


def test_hksj_by_hand():
    t2 = ev.tau2_pm(TH, SE); w = 1/(SE**2+t2); mu = (w*TH).sum()/w.sum()
    var = (w*(TH-mu)**2).sum()/(3*w.sum())
    r = ev.pooled(TH, SE, "hksj")
    assert r["lower"] == pytest.approx(mu-stats.t.ppf(.95, 3)*np.sqrt(var)) and "prediction_interval" in r


def test_tost_and_power_by_hand():
    r = ev.tost(0, 1, 1, 1, 3)
    s = np.sqrt(2)
    assert r["p_lower"] == pytest.approx(stats.norm.sf(4/s)) and r["p_upper"] == pytest.approx(stats.norm.cdf(-2/s))
    assert ev.power_z(ev.mde_z(1.), 1.) == pytest.approx(.80, abs=1e-3)   # two-sided adds a tiny opposite tail


def test_engine_flags():
    out = evidence.combine_estimates([.027, .035], [.0055, .0048])
    assert out["validated"] and out["k"] == 2
    k5 = evidence.combine_estimates(TH.tolist()+[.3], SE.tolist()+[.2])        # k = 5: truncated HKSJ since Round 48
    assert k5["validated"] and k5["pooled"]["method"] == "hksj_truncated"
    assert not evidence.combine_estimates(list(range(11)), [1.]*11)["validated"]     # k = 11
    assert not evidence.combine_estimates([.027, .035], [.0055, .0048], method="fixed")["validated"]
    assert evidence.combine_estimates([.027, .035], [.0055, .0048], method="fixed", assume_homogeneous=True)["validated"]
    with pytest.raises(ValueError, match="margin"):
        evidence.equivalence(0, 1, 0, 1, 0)


def test_flags_equal_the_fixed_audit():
    passed = json.loads((ROOT/"docs/audits/evidence_validation.json").read_text())["passed"]
    assert passed["hksj/k2"] and passed["hksj/k4"] and not passed["hksj/k8"]
    assert evidence.HKSJ_VALIDATED_MAX_K == 4
    assert not any(passed[f"dl/k{k}"] for k in (2, 4, 8)) and passed["tost"] and passed["power"]


def test_tool_offline():
    from census import workflows_inference as wi
    assert wi.combine_estimates("pool", estimates=[.027, .035], ses=[.0055, .0048])["success"]
    assert wi.combine_estimates("equivalence", estimates=[.027, .035], ses=[.0055, .0048], margin=.01)["success"]
    assert wi.combine_estimates("power", se=.005, effect=.01)["success"]
    assert not wi.combine_estimates("power")["success"]
