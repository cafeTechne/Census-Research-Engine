# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 61: manifest routing for SCPC, calibrated cluster slopes and spatial correlations (no new statistics)."""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from census import scpc, scpc_core as sc
from census.manifest import methods as mm
from tests.test_round43 import base, errs, with_analysis, corr

ROOT = Path(__file__).resolve().parents[1]
warnings.simplefilter("ignore")


def area_frame(n=90, seed=61):
    rng = np.random.default_rng(seed)
    ids = [f"39{i:03d}" for i in range(n)]
    coords = pd.DataFrame(dict(GEOID=ids, lon=rng.uniform(-84, -80, n), lat=rng.uniform(39, 42, n)))
    x = rng.normal(size=n); E = rng.lognormal(3, .5, n); se = rng.uniform(.2, .4, n)
    f = pd.DataFrame(dict(GEOID=ids, Year=2024, x=x, x_se=se, E=E, y=1+.4*x+rng.normal(size=n)))
    f["c"] = rng.poisson(E*np.exp(.3*x)).astype(float)
    return f, coords


def test_scpc_p_value_consistent_with_interval():
    f, coords = area_frame()
    t = scpc.fit_scpc("y ~ x", f, coords=coords)["table"].iloc[0]
    assert (t.p_value < .10) == (t.lower > 0 or t.upper < 0)
    S = next(iter(scpc._SETUPS.values()))
    assert max(sc._size(V, S["q"], S["cv"]) for V in S["V"]) == pytest.approx(.10, abs=1e-4)


def fr(args, **top):
    return with_analysis(dict(id="m1", method="fit_replicate", formula="income ~ pop", args=args),
                         dict(id="H1", analysis="m1", statistic="coefficient", term="pop", direction="greater"), **top)


def _level(m, level):
    m["geography"] = dict(m["geography"], level=level)
    return m


def test_scpc_manifest_gates():
    # county rules (Rounds 58/62); the base manifest is tract-level, whose benchmarks differ since Round 71
    ok = lambda args, **top: not [e for e in errs(_level(fr(args, **top), "county")) if "scpc" in e.lower() or "SCPC" in e]
    assert ok({"spatial_scpc": {}})
    assert ok({"spatial_scpc": {"rho_bar": .10}})
    assert not ok({"spatial_scpc": {"rho_bar": 2}})
    assert not ok({"spatial_scpc": {}, "model": "poisson"})                       # needs exposure
    assert ok({"spatial_scpc": {}, "model": "poisson", "exposure": "pop"})
    assert not ok({"spatial_scpc": {"rho_bar": .05}, "model": "poisson", "exposure": "pop"})   # not validated
    assert not ok({"spatial_scpc": {"rho_bar": .10}, "model": "binomial", "trials": "pop"})
    assert ok({"spatial_scpc": {"rho_bar": .10}, "model": "binomial", "trials": "pop"}, exploratory=True)
    assert ok({"spatial_scpc": {}, "model": "binomial", "trials": "pop"})          # rho .15 validated (Round 62)
    assert not ok({"spatial_scpc": {}, "scale": "robust", "model": "poisson", "exposure": "pop"})
    assert not ok({"spatial_scpc": {}, "target": "these_areas"})
    tract = lambda args: not [e for e in errs(fr(args)) if "scpc" in e.lower() or "SCPC" in e]
    assert tract({"spatial_scpc": {}}) and tract({"spatial_scpc": {"rho_bar": .30}})      # Round 71: .20 default
    assert not tract({"spatial_scpc": {"rho_bar": .10}})
    assert not tract({"spatial_scpc": {}, "model": "poisson", "exposure": "pop"})


def test_scpc_runner_and_hypothesis():
    f, coords = area_frame()
    ctx = {"held_external": [], "coords": coords, "wonder_names": ()}
    res = mm._run_fit_replicate(dict(method="fit_replicate", formula="y ~ x"), {"spatial_scpc": {}, "replicate_policy": "strict"},
                                f, .9, None, "holm", ctx)
    ref = scpc.fit_scpc("y ~ x", f, coords=coords)["table"].iloc[0]
    s = mm._stat_coefficient({"term": "x"}, res)
    assert s["estimate"] == pytest.approx(ref.estimate) and s["ci_upper"] == pytest.approx(ref.upper)
    assert s["p_two_sided"] == pytest.approx(ref.p_value) and "confirmatory_refusal" not in s
    f["p"] = 1/(1+np.exp(-f.x)); f["T"] = 300.
    b = mm._run_fit_replicate(dict(method="fit_replicate", formula="p ~ x"),
                              {"spatial_scpc": {"rho_bar": .10}, "model": "binomial", "trials": "T"}, f, .9, None, "holm", ctx)
    assert "SCPC is validated for county OLS" in mm._stat_coefficient({"term": "x"}, b)["confirmatory_refusal"]


def rc(args, **top):
    return with_analysis(dict(id="m1", method="regression_calibration", formula="income ~ pop", error_covariates=["pop"], args=args),
                         dict(id="H1", analysis="m1", statistic="coefficient", term="pop", direction="greater"), **top)


def test_rc_clusters_gates_and_runner():
    msgs = lambda args: [e for e in errs(rc(args)) if "spatial regression calibration" in e or "args.spatial" in e]
    assert not msgs({"spatial": "clusters", "model": "negbin", "exposure": "pop"})
    assert msgs({"spatial": "clusters", "model": "negbin"})
    assert msgs({"spatial": "clusters", "model": "ols"})
    assert msgs({"spatial": "error", "model": "poisson", "exposure": "pop"})
    from census.count_models import fit_count_model
    from tests.test_round53 import counties
    f, coords = counties()
    ctx = {"held_external": [], "coords": coords}
    res = mm._run_regression_calibration(dict(method="regression_calibration", formula="c ~ w + NY"),
                                         {"spatial": "clusters", "model": "negbin", "exposure": "E", "error_covariates": ["w"]},
                                         f, .9, None, "holm", ctx)
    ref = fit_count_model("c ~ w + NY", f, "E", spatial="clusters", coords=coords, calibrate=["w"])["table"].set_index("term")
    s = mm._stat_coefficient({"term": "w"}, res)
    assert s["estimate"] == pytest.approx(ref.loc["w", "estimate"]) and s["ci_lower"] == pytest.approx(ref.loc["w", "lower"])
    assert "confirmatory_refusal" not in s
    text = mm._text_regression_calibration({"args": {"spatial": "clusters"}}, mm.METHODS["regression_calibration"].text[0])
    assert "eight fixed spatial clusters" in text


def test_spatial_correlation_route():
    assert any("needs interval 'validated'" in e for e in errs(corr({"spatial": True})))
    assert not [e for e in errs(corr({"interval": "validated", "method": "spearman", "spatial": True})) if "spatial" in e]
    from census.correlation import validated_correlations
    f, coords = area_frame()
    res = mm._run_correlation_matrix(dict(method="correlation_matrix"), {"interval": "validated", "variables": ["x", "y"],
                                     "method": "spearman", "spatial": True}, f, .9, None, "holm",
                                     {"held_external": [], "coords": coords})
    ref = validated_correlations(f, ["x", "y"], "spearman", coords=coords).iloc[0]
    s = mm._stat_correlation({"variables": ["x", "y"]}, res)
    assert s["ci_lower"] == pytest.approx(ref.ci_lower) and "effective-sample-size" in res.notes[0]
    assert "effective sample size" in mm._text_correlation({"args": {"interval": "validated", "method": "spearman", "spatial": True}}, "")


def test_scpc_text_and_rule_text():
    from census import mcp_profiles
    assert "SCPC" in mm._text_fit_replicate({"args": {"spatial_scpc": {}}}, "x")
    for path in ("docs/agent_protocol.md", "mcp_server.py", "docs/recipes/regression_sampling_error.md"):
        text = " ".join((ROOT/path).read_text().split())
        assert "Round 61" in text and "spatial_scpc" in text
    assert "spatial_scpc" in mcp_profiles.CORE_INSTRUCTIONS
