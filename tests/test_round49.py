# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 49: survey-weighted PUMS models (solvers, SDR wrapper, flags = audit, MCP routing)."""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from census import pums, pums_models, pums_models_core as pm
from census import pums_tests as pt

ROOT = Path(__file__).resolve().parents[1]
warnings.simplefilter("ignore")


def _data(n=600, seed=49):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=(n, 2))
    lat = x @ [.8, -.5] + rng.logistic(size=n)
    y3 = np.digitize(lat, [-.7, .9])
    return rng, x, y3


def test_flags_equal_audit():
    audit = json.loads((ROOT/"docs/audits/pums_models_validation.json").read_text())
    assert set(pums_models.VALIDATED) == set(pums_models.MODELS)
    for m in pums_models.MODELS:
        assert pums_models.VALIDATED[m] is bool(audit["passed"][pums_models.AUDIT_KEY[m]])
    assert audit["criterion_commit"] == "c0dfd0a"


def test_ordered_logit_and_probit_match_statsmodels():
    from statsmodels.miscmodels.ordinal_model import OrderedModel
    _, x, y = _data()
    w = np.ones(len(y))
    for link, dist in (("logit", "logit"), ("probit", "probit")):
        th, H = pm.ordered_fit(y, x, w, link)
        r = OrderedModel(y, x, distr=dist).fit(method="newton", disp=False, maxiter=200)
        sm_t = np.cumsum(np.r_[r.params[2], np.exp(r.params[3:])])
        assert np.allclose(th[:2], r.params[:2], atol=1e-4)
        assert np.allclose(th[2:], sm_t, atol=1e-4)
        assert np.all(np.linalg.eigvalsh(H) < 0)


def test_mnlogit_and_probit_match_statsmodels():
    import statsmodels.api as sm
    rng, x, y = _data()
    X = np.column_stack((np.ones(len(y)), x)); w = np.ones(len(y))
    B, _ = pm.mnlogit_fit(y, X, w)
    r = sm.MNLogit(y, X).fit(disp=False)
    assert np.allclose(B, r.params.T.ravel(), atol=1e-6)
    yb = (y > 0).astype(float)
    b, _ = pm.probit_fit(yb, X, w)
    assert np.allclose(b, sm.Probit(yb, X).fit(disp=False).params, atol=1e-6)


def test_weights_equal_duplicated_records():
    rng, x, y = _data(300)
    X = np.column_stack((np.ones(len(y)), x)); k = rng.integers(1, 4, len(y))
    rep = np.repeat(np.arange(len(y)), k)
    B1, _ = pm.mnlogit_fit(y, X, k.astype(float))
    B2, _ = pm.mnlogit_fit(y[rep], X[rep], np.ones(len(rep)))
    assert np.allclose(B1, B2, atol=1e-6)
    t1, _ = pm.ordered_fit(y, x, k.astype(float), "probit")
    t2, _ = pm.ordered_fit(y[rep], x[rep], np.ones(len(rep)), "probit")
    assert np.allclose(t1, t2, atol=1e-5)


def test_median_matches_lp_and_quantreg():
    from statsmodels.regression.quantile_regression import QuantReg
    rng = np.random.default_rng(3)
    n = 400; X = np.column_stack((np.ones(n), rng.normal(size=n)))
    y = X @ [1., .5] + rng.standard_t(3, n)
    w = rng.uniform(.5, 2, n)
    b, _ = pm.median_fit(y, X, w)
    lp = pm._median_lp(y, X, w)
    obj = lambda c: np.sum(w*np.abs(y-X @ c))
    assert obj(b) <= obj(lp)*(1+1e-6)
    assert np.allclose(pm.median_fit(y, X, np.ones(n))[0], QuantReg(y, X).fit(q=.5).params, atol=1e-3)


def test_warm_start_at_optimum_returns_immediately():
    _, x, y = _data()
    w = np.ones(len(y))
    th, _ = pm.ordered_fit(y, x, w, "logit")
    th2, _ = pm.ordered_fit(y, x, w, "logit", start=th)
    assert np.allclose(th, th2, atol=1e-8)


def test_sdr_fit_variance_formula():
    rng, x, y = _data(400)
    X = np.column_stack((np.ones(len(y)), x)); yb = (y > 0).astype(float)
    W = np.column_stack([np.ones(len(y))]+[rng.uniform(.5, 1.5, len(y)) for _ in range(80)])
    r = pm.sdr_fit("probit", yb, X, W)
    reps = np.array([pm.probit_fit(yb, X, W[:, j])[0] for j in range(1, 81)])
    se = np.sqrt(4/80*np.sum((reps-r["estimate"])**2, axis=0))
    assert np.allclose(r["se"], se, rtol=1e-6)
    assert np.allclose(r["upper"]-r["estimate"], stats.norm.ppf(.95)*se)


def synthetic(n=900, seed=49):
    rng = np.random.default_rng(seed)
    hh = np.sort(rng.integers(0, n//2, n))
    order = np.unique(hh, return_inverse=True)[1]
    w = rng.lognormal(3, .5, hh.max()+1)[hh]
    f = pt.sdr_factors(hh.max()+1)[order]
    age = rng.integers(18, 80, n)
    lat = .02*(age-45)+rng.logistic(size=n)
    df = pd.DataFrame({"SERIALNO": hh, "PWGTP": np.rint(w), "AGEP": age,
                       "BAND": np.digitize(lat, [-1, 0, 1])+1, "DIS": rng.choice([1, 2], n, p=[.2, .8]),
                       "EARN": np.exp(10+.01*(age-45)+rng.normal(size=n))})
    for r in range(80):
        df[f"PWGTP{r+1}"] = np.rint(df.PWGTP*f[:, r])
    return df


@pytest.mark.parametrize("model,formula", [
    ("ordered_logit", "BAND ~ AGEP"), ("ordered_probit", "BAND ~ AGEP"), ("mnlogit", "BAND ~ AGEP"),
    ("median", "np.log(EARN) ~ AGEP"), ("probit", "I((DIS == 1)*1.) ~ AGEP")])
def test_fit_pums_model(model, formula):
    out = pums_models.fit_pums_model(formula, synthetic(), model, where="AGEP >= 18")
    t = out["table"]
    assert out["validated"] is True and out["n"] == 900
    assert np.all(t.lower < t.estimate) and np.all(t.estimate < t.upper)
    if model.startswith("ordered"):
        assert list(t.term) == ["AGEP", "threshold 1|2", "threshold 2|3", "threshold 3|4"]
        assert out["levels"] == ["1", "2", "3", "4"]
    if model == "mnlogit":
        assert len(t) == 6 and "[2 vs 1]" in t.term[0]
        assert any("Baseline category: 1" in s for s in out["notes"])
    assert not any("EXPLORATORY" in s for s in out["notes"])


def test_fit_pums_model_refusals(monkeypatch):
    df = synthetic()
    with pytest.raises(ValueError):
        pums_models.fit_pums_model("BAND ~ AGEP", df, "tobit")
    with pytest.raises(ValueError):
        pums_models.fit_pums_model("BAND ~ AGEP", df, "probit")
    with pytest.raises(ValueError):
        pums_models.fit_pums_model("I((BAND > 2)*1.) ~ AGEP", df, "ordered_logit")
    monkeypatch.setitem(pums_models.VALIDATED, "probit", False)
    out = pums_models.fit_pums_model("I((DIS == 1)*1.) ~ AGEP", df, "probit")
    assert not out["validated"] and any("EXPLORATORY" in s for s in out["notes"])


def test_pums_regression_tool_routes(monkeypatch):
    from census import workflows_microdata as wm
    monkeypatch.setattr(pums, "fetch_pums", lambda *a, **k: synthetic())
    out = wm.pums_regression("26", 2023, "BAND ~ AGEP", model="ordered_probit")
    assert out["success"], out
    assert out["validated"] and "Round 49" in out["summary"]
    json.dumps(out)
    bad = wm.pums_regression("26", 2023, "BAND ~ AGEP", model="probit")
    assert not bad["success"]
    from census import mcp_profiles
    assert "mnlogit" in mcp_profiles.CORE_INSTRUCTIONS


def test_rule_text_mirrored():
    proto = (ROOT/"docs/agent_protocol.md").read_text()
    recipe = (ROOT/"docs/recipes/pums_tests.md").read_text()
    for text in (proto, recipe):
        assert "ordered_probit" in text and "mnlogit" in text
    assert "not available yet" not in proto
