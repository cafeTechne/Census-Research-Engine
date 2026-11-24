# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 112 tests: Q2e-lower PPV, D2 count-scale disparity indices (min_events >= 100), and R2_dens RDD density test."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from census import designation as des
from census import disparity as disp
from census import multilevel3 as m3
from census import rdd
from census import stratified as st

ROOT = Path(__file__).resolve().parents[1]


def test_round112_audit_verdicts_match_code():
    v = json.loads((ROOT / "docs/audits/repairs112_validation.json").read_text())["verdicts"]
    assert v["Q2e-lower"] is True and des.PPV_INTERVAL_VALIDATED["lower"] is True
    assert v["Q2e-prob50"] is False and des.PPV_INTERVAL_VALIDATED["prob50"] is False
    for k in ("idisp", "bgv", "theil", "mld"):
        assert v[f"D2-{k}"] is True and k in disp.COUNT_INDEX_VALIDATED
    assert v["R2_dens"] is True and rdd.VALIDATED["density"] is True
    assert v["M3b"] is False and m3.SHARES_VALIDATED is False
    assert v["W3_rr"] is False and st.VALIDATED["woolf"] is False


def test_designation_lower_ppv_interval_validated():
    rng = np.random.default_rng(11201)
    n = 120
    true_p = np.clip(rng.normal(0.22, 0.08, n), 0.04, 0.70)
    se = np.full(n, 0.02)
    df = pd.DataFrame({"GEOID": [f"26{i:03d}" for i in range(n)],
                       "pov": np.clip(true_p + rng.normal(0, se), 0.02, 0.85), "pov_se": se})
    out = des.designation_accuracy(df, "pov", 0.20, se_col="pov_se", rules=("lower", "prob50"),
                                   ppv_intervals=True, ppv_bootstrap=60, seed=42)
    rules = out["rules"].set_index("rule")
    assert bool(rules.loc["lower", "ppv_validated"]) is True
    assert bool(rules.loc["prob50", "ppv_validated"]) is False
    assert 0.0 <= rules.loc["lower", "ppv_lower"] <= rules.loc["lower", "ppv_upper"] <= 1.0


def test_count_disparity_indices_gate():
    df = pd.DataFrame({
        "GEOID": ["26001", "26002"],
        "c1": [150, 30], "c2": [250, 50], "c3": [400, 80],
        "p1": [50000, 50000], "p2": [60000, 60000], "p3": [70000, 70000],
    })
    out = disp.disparity_measures(df, ["c1", "c2", "c3"], "c1", ["p1", "p2", "p3"], counts=True, bootstrap=100)
    hi = out[(out["GEOID"] == "26001") & (out["measure"].isin(["idisp", "bgv", "theil", "mld"]))]
    lo = out[(out["GEOID"] == "26002") & (out["measure"].isin(["idisp", "bgv", "theil", "mld"]))]
    assert hi["validated"].all()
    assert (~lo["validated"]).all()


def test_rdd_density_test_validated_for_continuous_n1000():
    rng = np.random.default_rng(11202)
    x = rng.uniform(-1, 1, 1500)
    y = 1.0 + 0.5 * (x >= 0) + 0.3 * x + rng.normal(0, 0.4, 1500)
    out = rdd.regression_discontinuity(pd.DataFrame({"x": x, "y": y}), "y", "x", 0.0)
    assert out["density_test"]["validated"] is True
    # Small n < 1000 stays exploratory
    out_sm = rdd.regression_discontinuity(pd.DataFrame({"x": x[:400], "y": y[:400]}), "y", "x", 0.0)
    assert out_sm["density_test"]["validated"] is False
