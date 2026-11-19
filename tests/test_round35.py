# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 35: corrected slopes under spatial dependence (G1, G2)."""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from census import spatial_eiv, spatial_eiv_core as core
from census.models import fit_eiv
from census.simulation import make_replicates

ROOT = Path(__file__).resolve().parents[1]
warnings.simplefilter("ignore")


def synthetic(n=160, seed=35):
    rng = np.random.default_rng(seed)
    ids = [f"{'26' if i < 80 else '36'}{i:03d}" for i in range(n)]
    x = rng.normal(size=n); y = 1+.5*x+rng.normal(size=n)
    se = np.full(n, .3); obs = x+rng.normal(size=n)*se
    rep = make_replicates(obs[:, None], se[:, None], rng)
    long = pd.DataFrame(rep[:, 0, :], columns=[f"rep_{k+1}" for k in range(80)])
    long.insert(0, "estimate", obs); long.insert(0, "variable", "x"); long.insert(0, "Year", 2022); long.insert(0, "GEOID", ids)
    f = pd.DataFrame(dict(GEOID=ids, Year=2022, x=obs, y=y))
    lon = -85+np.arange(n) % 16*.25+np.where(np.arange(n) < 80, 0, 10)       # NY far east of MI: no cluster mixes states
    coords = pd.DataFrame(dict(GEOID=ids, lon=lon, lat=41+np.arange(n)//16*.25))
    return f, long, coords


def test_g2_with_lambda_zero_equals_fit_eiv():
    f, long, _ = synthetic()
    ref = fit_eiv("y ~ x", f, long)
    from census.spatial_eiv import _design
    _, X, y, D, e, names, _ = _design("y ~ x", f, long, ("y",))
    b, V = core.fuller(X, y, D, e)
    est = ref.coefficients.set_index("term")
    assert b[1] == pytest.approx(est.loc["x", "estimate"])
    assert np.sqrt(V[1, 1]) == pytest.approx(est.loc["x", "se_total"], rel=1e-6)


def test_sem_lambda_matches_grid_search():
    rng = np.random.default_rng(1); n = 60
    lon, lat = rng.uniform(-85, -82, n), rng.uniform(41, 44, n)
    W = core.knn_weights(lon, lat, 6); eig = np.linalg.eigvals(W)
    assert np.allclose(W.sum(axis=1), 1) and (np.count_nonzero(W, axis=1) == 6).all()
    X = np.column_stack((np.ones(n), rng.normal(size=n)))
    y = np.linalg.solve(np.eye(n)-.5*W, X@[1, .5]+rng.normal(size=n))
    lam = core.sem_lambda(X, y, W, eig)
    def ll(l):
        B = np.eye(n)-l*W; Xw, yw = B@X, B@y; r = yw-Xw@np.linalg.lstsq(Xw, yw, rcond=None)[0]
        return -n/2*np.log(r@r/n)+np.linalg.slogdet(B)[1]
    grid = np.linspace(-.95, .95, 1901)
    assert lam == pytest.approx(grid[np.argmax([ll(g) for g in grid])], abs=2e-3)


def test_g1_correction_by_hand():
    rng = np.random.default_rng(2); n = 40
    labels = np.repeat(np.arange(8), 5)
    Xs = rng.normal(size=(n, 1)); y = 2*Xs[:, 0]+rng.normal(size=n)
    Ds = rng.normal(size=(80, n, 1))*.1; e = np.zeros((80, n))
    out = core.g1(Xs, y, Ds, e, labels)
    Q = sum(((Xs[labels == g]-Xs[labels == g].mean(0))**2).sum() for g in range(8))
    Sw = sum((1-1/5)*.05*(Ds[:, labels == g]**2).sum() for g in range(8))
    b0 = [np.polyfit(Xs[labels == g, 0], y[labels == g], 1)[0] for g in range(8)]
    np.testing.assert_allclose(out[:, 0], np.array(b0)*Q/(Q-Sw))


def test_engine_both_methods_and_refusals():
    f, long, coords = synthetic()
    f["NY"] = f.GEOID.str.startswith("36").astype(float)
    g1 = spatial_eiv.fit_spatial_eiv("y ~ x + C(GEOID.str[:2])", f, long, method="g1", coords=coords, fixed_variables=("y",))
    assert list(g1["table"].term) == ["x"] and g1["validated"] and any("Absorbed" in n for n in g1["notes"])
    g2 = spatial_eiv.fit_spatial_eiv("y ~ x", f, long, method="g2", coords=coords, fixed_variables=("y",))
    assert "lambda" in g2 and g2["table"].set_index("term").loc["x", "df"] == len(f)-2
    with pytest.raises(ValueError, match="no design column"):
        spatial_eiv.fit_spatial_eiv("y ~ NY", f, long, coords=coords, fixed_variables=("y",))
    with pytest.raises(ValueError, match="g1"):
        spatial_eiv.fit_spatial_eiv("y ~ x", f, long, method="nope", coords=coords)


def test_flags_equal_the_fixed_audit():
    passed = json.loads((ROOT/"docs/audits/spatial_eiv_validation.json").read_text())["passed"]
    assert spatial_eiv.VALIDATED == {"g1": passed["G1"], "g2": passed["G2"]}
