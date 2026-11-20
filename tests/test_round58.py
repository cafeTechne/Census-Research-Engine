# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 58: SCPC naive slopes, IM-8 rerun note, spatial EIV reliability gate, calibrated binomial IM-8."""
import json
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd
import pytest

from census import models, scpc, scpc_core as sc, spatial_eiv

ROOT = Path(__file__).resolve().parents[1]
AUDIT = json.loads((ROOT/"docs/audits/spatial_outside_validation.json").read_text())


def test_flags_equal_the_fixed_audit():
    p = AUDIT["passed"]
    assert AUDIT["criterion_commit"] == "e8c6c8c"
    for model in ("linear", "poisson", "binomial"):
        key = "ols" if model == "linear" else model
        passing = tuple(r for r in (.05, .10) if p[f"SCPC{int(100*r):02d}_{model}"])
        assert tuple(r for r in scpc.VALIDATED_RHO[key] if r in (.05, .10)) == passing   # Round 62 added .15/.20 for binomial
    assert scpc.DEFAULT_RHO["ols"] == .05 and scpc.DEFAULT_RHO["poisson"] == .10
    assert all(p[f"{g}_p{k}_rel80"] for g in ("G1", "G2") for k in (3, 4, 5)) and spatial_eiv.RELIABILITY_GATE == .8
    assert p["B1_binomial"] is models.RC_CLUSTERS_BINOMIAL_VALIDATED is True
    assert p["IM8_R_linear"] is False and p["IM8_R_binomial"] and p["IM8_R_poisson"]


def test_scpc_critical_value_against_simulation():
    rng = np.random.default_rng(58)
    lon, lat = rng.uniform(-84, -80, 60), rng.uniform(40, 42, 60)
    D = sc.haversine(lon, lat)
    S = sc.setup(D, .10, qmax=8, grid=8)
    n = len(D); L = np.linalg.cholesky(np.exp(-S["c0"]*D)+1e-10*np.eye(n))
    E = rng.standard_normal((20000, n)) @ L.T
    tau = (E.sum(1)/np.sqrt(n))/np.sqrt(np.mean((E @ S["W"])**2, axis=1))
    assert np.mean(np.abs(tau) > S["cv"]) == pytest.approx(.10, abs=.012)
    assert S["cv"] >= sc.stats.t.ppf(.95, S["q"]) - 1e-9   # never below the independent t(q) value


def test_influence_matches_ols():
    rng = np.random.default_rng(1)
    X = np.column_stack((np.ones(50), rng.normal(size=50))); y = X @ [1, .5]+rng.normal(size=50)
    theta, e = sc.influence(X, y, "linear", 1)
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    assert theta == pytest.approx(b[1]) and e.mean() == pytest.approx(0, abs=1e-10)


def frame(n=80, seed=58):
    rng = np.random.default_rng(seed)
    ids = [f"39{i:03d}" for i in range(n)]
    coords = pd.DataFrame(dict(GEOID=ids, lon=rng.uniform(-84, -80, n), lat=rng.uniform(39, 42, n)))
    x = rng.normal(size=n); E = rng.lognormal(3, .5, n)
    f = pd.DataFrame(dict(GEOID=ids, Year=2024, x=x, E=E, y=1+.5*x+rng.normal(size=n)))
    f["c"] = rng.poisson(E*np.exp(.3*x)).astype(float)
    return f, coords


def test_fit_scpc_flags_and_mcp(tmp_path):
    f, coords = frame()
    ols = scpc.fit_scpc("y ~ x", f, coords=coords)
    assert ols["validated"] and ols["rho_bar"] == .05 and ols["table"].term.tolist() == ["x"]
    poi = scpc.fit_scpc("c ~ x", f, "poisson", exposure="E", coords=coords)
    assert poi["validated"] and poi["rho_bar"] == .10
    assert not scpc.fit_scpc("c ~ x", f, "poisson", exposure="E", coords=coords, rho_bar=.05)["validated"]
    f["p"] = 1/(1+np.exp(-f.x)); f["T"] = 200.
    assert not scpc.fit_scpc("p ~ x", f, "binomial", trials="T", coords=coords, rho_bar=.10)["validated"]   # .15 since Round 62
    from census import workflows_inference as wi
    p = tmp_path/"f.csv"; f.to_csv(p, index=False)
    with mock.patch("census.small_spatial.frame_coordinates", return_value=coords):
        out = wi.fit_model(str(p), "y ~ x", spatial="scpc")
    assert out["success"] and out["validated"], out


def test_reliability_gate_note():
    from tests.test_round46 import several
    f, long, coords, rhs = several(3)
    f = f.assign(GEOID="39"+f.GEOID.str[2:]); long = long.assign(GEOID="39"+long.GEOID.str[2:])
    coords = coords.assign(GEOID="39"+coords.GEOID.str[2:])
    out = spatial_eiv.fit_spatial_eiv(f"y ~ {rhs}", f, long, method="g1", coords=coords, fixed_variables=("y",))
    rel = min(out["reliability"].values())
    assert 0 < rel < 1
    note = "Outside MI/NY" if rel >= .8 else "EXPLORATORY OUTSIDE MI/NY"
    assert any(n.startswith(note) for n in out["notes"])


def test_binomial_calibrated_clusters():
    rng = np.random.default_rng(3); n = 160
    ids = [f"{'26' if i < 80 else '36'}{i:03d}" for i in range(n)]
    lon = -85+np.arange(n) % 16*.25+np.where(np.arange(n) < 80, 0, 10)
    coords = pd.DataFrame(dict(GEOID=ids, lon=lon, lat=41+np.arange(n)//16*.25))
    x = rng.normal(size=n); se = rng.uniform(.2, .4, n); T = rng.integers(500, 5000, n).astype(float)
    f = pd.DataFrame(dict(GEOID=ids, Year=2022, w=x+rng.normal(size=n)*se, w_se=se, T=T,
                          NY=[float(i.startswith("36")) for i in ids]))
    f["y"] = rng.binomial(T.astype(int), 1/(1+np.exp(2-.3*x)))/T
    out = models.regression_calibration_clusters("y ~ w + NY", f, ["w"], "T", coords=coords)
    t = out["table"].set_index("term")
    assert out["validated"] and list(t.index) == ["w"] and t.loc["w", "df"] == 7
    assert any("Absorbed" in n for n in out["notes"])
    with pytest.raises(ValueError, match="90%"):
        models.regression_calibration_clusters("y ~ w", f, ["w"], "T", coords=coords, level=.95)


def test_rule_text_mirrored():
    from census import mcp_profiles
    for path in ("docs/agent_protocol.md", "mcp_server.py", "docs/recipes/regression_sampling_error.md",
                 "docs/recipes/external_health_outcome.md"):
        text = " ".join((ROOT/path).read_text().split())
        assert "SCPC" in text and "Round 58" in text
    assert "scpc" in mcp_profiles.CORE_INSTRUCTIONS
