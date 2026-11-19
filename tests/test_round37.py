# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 37: agreement between sources."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from census import agreement, agreement_core as ag

ROOT = Path(__file__).resolve().parents[1]


def data(n=150, seed=37):
    rng = np.random.default_rng(seed)
    t = rng.normal(size=n); x = t+rng.normal(size=n)*.3; y = .2+1.05*t+rng.normal(size=n)*.4
    return x, y, np.full(n, .3)


def test_bias_limits_ccc_by_hand():
    x, y, a = data(); d = y-x; n = len(d)
    b = ag.bias(x, y)
    assert b["estimate"] == pytest.approx(d.mean())
    assert b["lower"] == pytest.approx(d.mean()-stats.t.ppf(.95, n-1)*d.std(ddof=1)/np.sqrt(n))
    lim = ag.limits_observed(x, y)
    assert lim["upper_limit"] == pytest.approx(d.mean()+1.645*d.std(ddof=1))
    rc = 2*np.mean((x-x.mean())*(y-y.mean()))/(x.var()+y.var()+(x.mean()-y.mean())**2)
    assert ag.ccc(x, y)["estimate"] == pytest.approx(rc)
    t = ag.limits_true(x, y, a)
    assert t["sd_true"] == pytest.approx(np.sqrt(d.var(ddof=1)-.09))


def test_kappa_matches_statsmodels():
    from statsmodels.stats.inter_rater import cohens_kappa
    x, y, _ = data()
    qx = np.digitize(x, np.quantile(x, [.2, .4, .6, .8])); qy = np.digitize(y, np.quantile(y, [.2, .4, .6, .8]))
    tab = pd.crosstab(qx, qy).to_numpy()
    assert ag.kappa_quintiles(x, y)["estimate"] == pytest.approx(cohens_kappa(tab)["kappa"])


def test_engine_flags_and_refusal():
    x, y, a = data()
    f = pd.DataFrame(dict(GEOID=[f"26{i:03d}" for i in range(len(x))], A=x, B=y, A_se=a))
    out = agreement.check_agreement(f, "A", "B", a_se="A_se")
    assert out["bias"]["validated"] and out["kappa_quintiles"]["validated"]
    # Round 48 validated the limits with moment-based SEs (docs/audits/small_spatial_validation.md)
    assert out["limits_observed"]["validated"] and not out["ccc"]["validated"] and "limits_error_free" in out
    no_se = agreement.check_agreement(f, "A", "B")
    assert "limits_error_free" not in no_se
    with pytest.raises(ValueError, match="ten areas"):
        agreement.check_agreement(f.head(5), "A", "B")


def test_flags_equal_the_fixed_audit():
    passed = json.loads((ROOT/"docs/audits/agreement_validation.json").read_text())["passed"]
    assert passed == {"B0": True, "B1": False, "B2": False, "C1": False, "C2": False, "K1": True}


def test_check_agreement_tool_offline(tmp_path):
    from census import workflows_inference as wi
    x, y, a = data()
    p = tmp_path/"f.csv"; pd.DataFrame(dict(GEOID=range(len(x)), A=x, B=y)).to_csv(p, index=False)
    out = wi.check_agreement(str(p), "A", "B")
    assert out["success"] and "kappa" in out["summary"]; json.dumps(out)
