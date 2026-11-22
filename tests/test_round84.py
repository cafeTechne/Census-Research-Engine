# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 84: marginal risk ratios and differences, prevalence ratios, attributable fractions, dose-response."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from census import epi_measures as ep, epi_measures_core as em

ROOT = Path(__file__).resolve().parents[1]
AUDIT = json.loads((ROOT/"docs/audits/epi_measures_validation.json").read_text())


def test_flags_equal_the_audit():
    o = AUDIT["outcome"]
    assert ep.VALIDATED["area_marginal"] == (o["G1a_rr"]["passed"] and o["G1a_rd"]["passed"]) is True
    assert ep.VALIDATED["area_paf"] == o["F1a_paf"]["passed"] and ep.VALIDATED["area_dose"] == o["D1a_size"]["passed"]
    assert ep.VALIDATED["pums_marginal"] == (o["G1p_rr"]["passed"] and o["G1p_rd"]["passed"])
    assert ep.VALIDATED["prevalence_ratio"] == o["P1_pr"]["passed"] and ep.VALIDATED["pums_dose"] == o["D1p_size"]["passed"]
    assert "Committed before the full run" in (ROOT/"docs/audits/epi_measures_validation_criterion.md").read_text()


def _area(seed=0, n=300):
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(n); z = .4*x+rng.standard_normal(n)*.9
    trials = rng.integers(200, 3000, n).astype(float)
    p = em.expit(-1.5+.4*x+.3*z)
    return pd.DataFrame(dict(GEOID=[f"{i:05d}" for i in range(n)], rate=rng.binomial(trials.astype(int), p)/trials,
                             x=x, z=z, trials=trials))


def test_area_marginal_and_dose():
    f = _area()
    r = ep.area_marginal_measures(f, "rate ~ x + z", "trials", "x", [-1, 1], dose_levels=5)
    assert r["rr_lower"] < r["rr"] < r["rr_upper"] and r["rr"] > 1.5 and r["validated"]
    assert r["dose_response"]["trend_p"] < .05 and len(r["dose_response"]["risks"]) == 5
    assert any("odds ratios overstate" in n for n in r["notes"])  # prevalence about 20%
    with pytest.raises(ValueError, match="numeric term"):
        ep.area_marginal_measures(f, "rate ~ z", "trials", "x")


def test_fit_model_option(tmp_path):
    from census import workflows_inference as wi
    p = tmp_path/"f.csv"; _area().to_csv(p, index=False)
    out = wi.fit_model(str(p), "rate ~ x + z", model="binomial", trials="trials", marginal="x", spatial_check="off")
    assert out["success"] and out["marginal"]["rr"] > 1
    assert not wi.fit_model(str(p), "rate ~ x + z", marginal="x", spatial_check="off")["success"]


def test_pums_marginal_and_pr():
    rng = np.random.default_rng(1); n = 4000
    e = rng.integers(0, 2, n).astype(float); z = rng.standard_normal(n)
    y = (rng.random(n) < em.expit(-1.2+.5*e+.4*z)).astype(float)
    X = np.column_stack([np.ones(n), e, z])
    W = np.column_stack([np.ones(n)]+[1+.25*rng.standard_normal(n) for _ in range(80)])
    r = ep.pums_marginal_measures(y, X, W, 1)
    assert 1 < r["rr"] < 2 and r["rr_lower"] < r["rr"] < r["rr_upper"]
    assert 1 < r["prevalence_ratio"]["pr"] < 2 and r["paf_lower"] <= r["paf"] <= r["paf_upper"]


def test_dose_response_contrasts():
    C = em._contrasts(5)
    assert np.allclose(C@C.T, np.eye(4)) and C[0, -1] > 0
    flat = em.dose_response([.1]*5, np.eye(5)*1e-4)
    assert flat["trend_p"] == pytest.approx(1.0)
