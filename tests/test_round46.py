# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 46: GLM regression calibration flags and spatial EIV with 3-4 error-prone covariates."""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from census import spatial_eiv
from census.models import RC_VALIDATED, regression_calibration
from census.simulation import make_replicates

ROOT = Path(__file__).resolve().parents[1]
warnings.simplefilter("ignore")
AUDIT = json.loads((ROOT/"docs/audits/glm_correction_validation.json").read_text())


def test_flags_equal_the_fixed_audit():
    passed = AUDIT["passed"]
    assert passed == {"R1_binomial": False, "R1_poisson": True, "R1_negbin": True,
                      "G1_p3": True, "G2_p3": True, "G1_p4": True, "G2_p4": True}
    assert AUDIT["criterion_commit"] == "4aceb22" and AUDIT["draws_per_cell"] == 2000
    for m in ("binomial", "poisson", "negbin"):
        assert RC_VALIDATED[m] == passed[f"R1_{m}"]
    assert RC_VALIDATED["ols"] and RC_VALIDATED["wls"]
    largest = max(p for p in (3, 4) if passed[f"G1_p{p}"] and passed[f"G2_p{p}"])
    assert largest == 4
    # Round 53 (tests/test_round53.py) raised the cap to five error-prone covariates.
    assert spatial_eiv.VALIDATED_MAX_ERROR_COVARIATES >= largest


def frame(model, n=150, seed=46):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=n); se = np.full(n, .4); w = x+rng.normal(size=n)*se
    f = pd.DataFrame(dict(w=w, w_se=se))
    if model == "binomial":
        f["T"] = 2000.; f["y"] = rng.binomial(2000, 1/(1+np.exp(2.6-.3*x)))/2000
        return f, dict(trials="T")
    f["E"] = 30.; mu = 30*np.exp(.3*x)
    f["y"] = rng.poisson(mu*(rng.gamma(4, .25, n) if model == "negbin" else 1)).astype(float)
    return f, dict(exposure="E")


@pytest.mark.parametrize("model", ["binomial", "poisson", "negbin"])
def test_rc_reports_its_validation_status(model):
    f, extra = frame(model)
    r = regression_calibration("y ~ w", f, ["w"], model=model, n_boot=30, seed=1, **extra)
    assert r.diagnostics["regression_calibration_validated"] is RC_VALIDATED[model]
    text = " ".join(r.notes)
    assert ("EXPLORATORY" in text) is (model == "binomial")
    est = r.coefficients.set_index("term").loc["w"]
    assert abs(est.estimate) > abs(est.naive_estimate)   # attenuation corrected


def test_manifest_refuses_binomial_rc_confirmatory():
    from census.manifest import methods as mm
    f, extra = frame("binomial")
    res = regression_calibration("y ~ w", f, ["w"], model="binomial", n_boot=20, seed=1, **extra)
    assert "exploratory" in mm._stat_coefficient({"term": "w"}, res)["confirmatory_refusal"]
    f, extra = frame("poisson")
    res = regression_calibration("y ~ w", f, ["w"], model="poisson", n_boot=20, seed=1, **extra)
    assert "confirmatory_refusal" not in mm._stat_coefficient({"term": "w"}, res)


def test_mcp_binomial_rc_next_step_says_exploratory(tmp_path):
    from census import workflows_inference as wi
    f, _ = frame("binomial")
    p = tmp_path/"f.csv"; f.to_csv(p, index=False)
    out = wi.fit_model(str(p), "y ~ w", method="regression_calibration", model="binomial", trials="T",
                       error_covariates=["w"])
    assert out["success"], out
    assert "exploratory" in out["next_step"]


def several(p, n=160, seed=46):
    rng = np.random.default_rng(seed)
    ids = [f"{'26' if i < 80 else '36'}{i:03d}" for i in range(n)]
    X = rng.normal(size=(n, p)); y = 1+.5*X.sum(axis=1)+rng.normal(size=n)
    se = np.full((n, p), .3); obs = X+rng.normal(size=(n, p))*se
    rep = make_replicates(obs, se, rng)
    names = [f"x{k+1}" for k in range(p)]
    long = pd.concat([pd.DataFrame(rep[:, k, :], columns=[f"rep_{r+1}" for r in range(80)])
                      .assign(GEOID=ids, Year=2022, variable=names[k], estimate=obs[:, k]) for k in range(p)])
    f = pd.DataFrame(dict(GEOID=ids, Year=2022, y=y, **{v: obs[:, k] for k, v in enumerate(names)}))
    lon = -85+np.arange(n) % 16*.25+np.where(np.arange(n) < 80, 0, 10)
    coords = pd.DataFrame(dict(GEOID=ids, lon=lon, lat=41+np.arange(n)//16*.25))
    return f, long, coords, " + ".join(names)


@pytest.mark.parametrize("p,ok", [(4, True), (5, True), (6, False)])  # five validated in Round 53
def test_spatial_eiv_validated_up_to_four(p, ok):
    f, long, coords, rhs = several(p)
    out = spatial_eiv.fit_spatial_eiv(f"y ~ {rhs}", f, long, method="g2", coords=coords, fixed_variables=("y",))
    assert len(out["error_prone"]) == p and out["validated"] is ok
    assert any("EXPLORATORY" in n for n in out["notes"]) is (not ok)
