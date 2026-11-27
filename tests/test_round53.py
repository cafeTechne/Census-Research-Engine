# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 53: RC jackknife SEs, calibrated IM-8 count slopes, G1/G2 with five covariates (flags = audit)."""
import json
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from census import count_models, models, spatial_eiv
from census.count_models import fit_count_model
from census.rc_spatial_core import rc_im

ROOT = Path(__file__).resolve().parents[1]
AUDIT = json.loads((ROOT/"docs/audits/glm_correction2_validation.json").read_text())


def test_flags_equal_the_fixed_audit():
    passed = AUDIT["passed"]
    assert AUDIT["criterion_commit"] == "8d48956"
    for m in ("binomial", "poisson", "negbin"):
        assert models.RC_VALIDATED_SE["jackknife"][m] is passed[f"J1_{m}"] is True
        assert count_models.SPATIAL_RC_VALIDATED.get(m, False) is passed.get(f"S1_{m}", False)
    assert models.RC_VALIDATED_SE["bootstrap"] == models.RC_VALIDATED and not models.RC_VALIDATED["binomial"]
    assert not models.RC_VALIDATED_SE["jackknife"]["ols"]          # linear models not re-tested
    largest = max(p for p in (4, 5, 6) if p == 4 or (passed[f"G1_p{p}"] and passed[f"G2_p{p}"]))
    assert spatial_eiv.VALIDATED_MAX_ERROR_COVARIATES == largest == 5
    assert passed["G1_p6"] is False and passed["G2_p6"] is False


def frame(model, n=60, seed=53):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=n); se = np.full(n, .4); w = x+rng.normal(size=n)*se
    f = pd.DataFrame(dict(w=w, w_se=se, z=rng.normal(size=n)))
    if model == "binomial":
        f["T"] = 2000.; f["y"] = rng.binomial(2000, 1/(1+np.exp(2.6-.3*x)))/2000
    else:
        f["E"] = rng.lognormal(np.log(30), .5, n); f["y"] = rng.poisson(f.E*np.exp(.3*x)).astype(float)
    return f


def test_jackknife_matches_manual_delete_one_refits():
    f = frame("poisson")
    r = models.regression_calibration("y ~ w + z", f, ["w"], model="poisson", exposure="E", se_method="jackknife")
    t = r.coefficients.set_index("term")
    b = []
    for i in range(len(f)):
        d = f.drop(index=i).reset_index(drop=True)
        cal = models._calibrate(d, {"w": "w_se"}, ["z"])
        b.append(models._fit("y ~ w + z", cal, "poisson", None, "E", None).params["w"])
    b = np.array(b); n = len(f)
    assert t.loc["w", "se_total"] == pytest.approx(np.sqrt((n-1)/n*np.sum((b-b.mean())**2)), rel=1e-8)
    crit = stats.t.ppf(.95, n-3)
    assert t.loc["w", "ci_upper"]-t.loc["w", "estimate"] == pytest.approx(crit*t.loc["w", "se_total"])
    assert r.diagnostics["jackknife_refits"] == n and r.diagnostics["regression_calibration_validated"] is True
    with pytest.raises(ValueError, match="se_method"):
        models.regression_calibration("y ~ w", f, ["w"], model="poisson", exposure="E", se_method="hc3")


def test_binomial_validated_only_with_jackknife():
    f = frame("binomial")
    boot = models.regression_calibration("y ~ w", f, ["w"], model="binomial", trials="T", n_boot=20)
    jack = models.regression_calibration("y ~ w", f, ["w"], model="binomial", trials="T", se_method="jackknife")
    assert boot.diagnostics["regression_calibration_validated"] is False
    assert any("se_method='jackknife' is validated" in n for n in boot.notes)
    assert jack.diagnostics["regression_calibration_validated"] is True
    ols = models.regression_calibration("y ~ w", f, ["w"], model="ols", se_method="jackknife")
    assert ols.diagnostics["regression_calibration_validated"] is False


def counties(n=160, seed=53):
    rng = np.random.default_rng(seed)
    ids = [f"{'26' if i < n//2 else '36'}{i:03d}" for i in range(n)]
    lon = -85+np.arange(n) % 16*.25+np.where(np.arange(n) < n//2, 0, 10)
    coords = pd.DataFrame(dict(GEOID=ids, lon=lon, lat=41+np.arange(n)//16*.25))
    x = rng.normal(size=n); se = rng.uniform(.2, .5, n); E = rng.lognormal(np.log(30), 1, n)
    f = pd.DataFrame(dict(GEOID=ids, Year=2022, w=x+rng.normal(size=n)*se, w_se=se, E=E,
                          NY=[float(i.startswith("36")) for i in ids]))
    f["c"] = rng.poisson(E*np.exp(.3*x+.2*f.NY)*rng.gamma(4, .25, n)).astype(float)
    return f, coords


def test_calibrated_im_counts_engine_equals_core():
    f, coords = counties()
    out = fit_count_model("c ~ w + NY", f, "E", spatial="clusters", coords=coords, calibrate=["w"])
    row = out["table"].set_index("term").loc["w"]
    assert out["validated"] and any("Regression calibration of ['w']" in n for n in out["notes"])
    from census.spatial_clusters import assignment_for_frame
    lab = assignment_for_frame(f, coords, {"k": 8, "method": "im"}).set_index("GEOID").loc[f.GEOID, "cluster"].to_numpy()
    core = rc_im(f.c, f[["w"]], f[["w_se"]], f[["NY"]], f.E, lab, "negbin")
    assert row.estimate == pytest.approx(core["estimate"]) and row.upper == pytest.approx(core["upper"])
    naive = fit_count_model("c ~ w + NY", f, "E", spatial="clusters", coords=coords)
    assert abs(row.estimate) >= abs(naive["table"].set_index("term").loc["w", "estimate"])   # attenuation undone
    with pytest.raises(ValueError, match="calibrate needs spatial"):
        fit_count_model("c ~ w", f, "E", calibrate=["w"])


def test_mcp_routes(tmp_path):
    from census import workflows_inference as wi
    f, coords = counties()
    p = tmp_path/"f.csv"; f.to_csv(p, index=False)
    with mock.patch("census.spatial_clusters.unit_coordinates", return_value=(coords.copy(), {})):
        out = wi.fit_model(str(p), "c ~ w + NY", method="regression_calibration", model="negbin", exposure="E",
                           spatial="clusters", error_covariates=["w"])
    assert out["success"] and out["validated"], out
    bad = wi.fit_model(str(p), "c ~ w", method="regression_calibration", model="binomial", spatial="clusters",
                       error_covariates=["w"])
    assert not bad["success"]
    b = frame("binomial"); b["GEOID"] = [f"{i:05d}" for i in range(len(b))]
    q = tmp_path/"b.csv"; b.to_csv(q, index=False)
    jk = wi.fit_model(str(q), "y ~ w", method="regression_calibration", model="binomial", trials="T",
                      error_covariates=["w"], se_method="jackknife")
    assert jk["success"] and "exploratory" not in jk["next_step"]
    bs = wi.fit_model(str(q), "y ~ w", method="regression_calibration", model="binomial", trials="T",
                      error_covariates=["w"])
    assert "se_method='jackknife'" in bs["next_step"]


def test_manifest_text_for_jackknife():
    from census.manifest import methods
    base = methods.METHODS["regression_calibration"].text[0]
    assert methods._text_regression_calibration({"args": {}}, base) == base
    jt = methods._text_regression_calibration({"args": {"se_method": "jackknife"}}, base)
    assert "delete-one-area jackknife" in jt and "row bootstrap" not in jt


def test_rule_text_mirrored():
    from census import mcp_profiles
    proto = (ROOT/"docs/agent_protocol.md").read_text()
    recipe = (ROOT/"docs/recipes/regression_sampling_error.md").read_text()
    server = (ROOT/"census/mcp_instructions.py").read_text()
    for text in (proto, recipe, mcp_profiles.CORE_INSTRUCTIONS, server):
        flat = " ".join(text.split())
        assert "jackknife" in flat and "Round 53" in flat
    assert "<=5 noisy" in mcp_profiles.CORE_INSTRUCTIONS
    assert "binomial is exploratory (.851)" not in proto
