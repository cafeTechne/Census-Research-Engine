# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 45: censored NB2, IM-8 count slopes, noisy offsets, state-respecting clusters."""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from census import count_repairs_core as cr
from census.count_models import fit_count_model
from census.missing_censored_its import fit_censored_negbin
from census.spatial_clusters import within_state_points

ROOT = Path(__file__).resolve().parents[1]
warnings.simplefilter("ignore")


def test_censored_nb_loglik_matches_scipy():
    mu = np.array([2., 9., 40.]); a = .3; r = 1/a
    X = np.ones((3, 1)); logE = np.log(mu); theta = np.array([0., np.log(a)])
    hidden = np.exp(cr._censored_nb_obs(theta, np.zeros(3), X, logE, np.ones(3, bool)))
    np.testing.assert_allclose(hidden, stats.nbinom.cdf(9, r, r/(r+mu))-stats.nbinom.pmf(0, r, r/(r+mu)))
    full = np.exp(cr._censored_nb_obs(theta, np.array([1., 0., 55.]), X, logE, np.zeros(3, bool)))
    np.testing.assert_allclose(full, stats.nbinom.pmf([1, 0, 55], r, r/(r+mu)))


def test_censored_nb_without_hidden_counts_equals_nb2_mle():
    rng = np.random.default_rng(45); n = 300
    x = rng.normal(size=n); E = rng.lognormal(np.log(30), 1, n)
    y = rng.poisson(E*np.exp(.3*x)*rng.gamma(4, .25, n)).astype(float)
    X = np.column_stack((np.ones(n), x))
    out = cr.censored_negbin(y, X, E, np.zeros(n, bool))
    assert out["estimate"] == pytest.approx(cr.nb2_fit(y, X, E)[1], abs=1e-4)


def test_fit_censored_negbin_engine():
    rng = np.random.default_rng(1); n = 300
    x = rng.normal(size=n); E = rng.lognormal(np.log(10), 1, n)
    c = rng.poisson(E*np.exp(.3*x)*rng.gamma(4, .25, n)).astype(float)
    f = pd.DataFrame(dict(x=x, E=E, c=np.where((c >= 1) & (c <= 9), np.nan, c), hidden=(c >= 1) & (c <= 9)))
    out = fit_censored_negbin(f, "c", "hidden", "E", ["x"])
    assert out["validated"] and out["n_censored"] == int(f.hidden.sum()) and abs(out["table"].estimate.iloc[0]-.3) < .15
    with pytest.raises(ValueError, match="non-hidden counts"):
        fit_censored_negbin(f.assign(hidden=False), "c", "hidden", "E", ["x"])


def test_im_counts_by_hand_poisson():
    import statsmodels.api as sm
    rng = np.random.default_rng(2); n = 80; labels = np.repeat(np.arange(8), 10)
    x = rng.normal(size=n); E = np.full(n, 20.); y = rng.poisson(E*np.exp(.3*x)).astype(float)
    X = np.column_stack((np.ones(n), x, (labels >= 4).astype(float)))
    out = cr.im_counts(y, X, E, labels, "poisson")
    b = [sm.GLM(y[labels == g], X[labels == g][:, :2], family=sm.families.Poisson(), exposure=E[labels == g]).fit().params[1]
         for g in range(8)]
    assert out["estimate"] == pytest.approx(np.mean(b))
    assert out["se"] == pytest.approx(np.std(b, ddof=1)/np.sqrt(8))
    assert out["upper"]-out["estimate"] == pytest.approx(stats.t.ppf(.95, 7)*out["se"])


def counties(n=160, seed=45, states=("26", "36")):
    rng = np.random.default_rng(seed)
    ids = [f"{states[0] if i < n//2 else states[1]}{i:03d}" for i in range(n)]
    lon = -85+np.arange(n) % 16*.25+np.where(np.arange(n) < n//2, 0, 10)
    coords = pd.DataFrame(dict(GEOID=ids, lon=lon, lat=41+np.arange(n)//16*.25))
    x = rng.normal(size=n); E = rng.lognormal(np.log(30), 1, n)
    f = pd.DataFrame(dict(GEOID=ids, Year=2022, x=x, E=E, NY=[float(i.startswith(states[1])) for i in ids]))
    f["c"] = rng.poisson(E*np.exp(.3*x+.2*f.NY)*rng.gamma(4, .25, n)).astype(float)
    return f, coords


def test_fit_count_model_spatial_clusters():
    f, coords = counties()
    out = fit_count_model("c ~ x + NY", f, "E", spatial="clusters", coords=coords)
    t = out["table"].set_index("term")
    assert list(t.index) == ["x"] and out["validated"] and t.loc["x", "df"] == 7
    assert any("Absorbed" in s and "NY" in s for s in out["notes"])
    with pytest.raises(ValueError, match="90% level"):
        fit_count_model("c ~ x", f, "E", level=.95, spatial="clusters", coords=coords)


def test_within_state_points_and_engine_option():
    f, coords = counties(states=("39", "42"))
    lab = within_state_points(coords, 8)
    a = coords.assign(cluster=lab)
    assert a.cluster.nunique() == 8 and all(s.str[:2].nunique() == 1 for _, s in a.groupby("cluster").GEOID)
    with pytest.raises(ValueError, match="divisible"):
        within_state_points(coords, 7)
    out = fit_count_model("c ~ x + NY", f, "E", spatial="clusters", coords=coords, within_states=True)
    # Round 54: IM-8 count slopes replicated on OH/PA, so the outside-geometry note says so.
    assert not any("CROSS STATE" in s for s in out["notes"]) and any("replicated on OH/PA" in s for s in out["notes"])


def test_flags_equal_the_fixed_audit():
    from census.count_models import SPATIAL_VALIDATED
    passed = json.loads((ROOT/"docs/audits/count_repairs_validation.json").read_text())["passed"]
    assert passed == {"K1a": True, "K2a": True, "K2b": True, "K3a": True}
    assert SPATIAL_VALIDATED["negbin"] == passed["K2a"] and SPATIAL_VALIDATED["poisson"] == passed["K2b"]


def test_mcp_fit_model_negbin_clusters(tmp_path):
    from census import workflows_inference as wi
    f, coords = counties()
    p = tmp_path/"f.csv"; f.to_csv(p, index=False)
    assert not wi.fit_model(str(p), "c ~ x", model="negbin", exposure="E", spatial="error")["success"]
    from unittest import mock
    with mock.patch("census.spatial_clusters.unit_coordinates", return_value=(coords.copy(), {})):
        out = wi.fit_model(str(p), "c ~ x + NY", model="negbin", exposure="E", spatial="clusters")
    assert out["success"], out
