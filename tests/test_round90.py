# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 90: positivity diagnostics, stabilized/truncated/overlap weights, g-formula."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"scripts"))

from census import causal, causal_core as cc, positivity as pz, positivity_core as pc  # noqa: E402
import positivity_validation as pv  # noqa: E402


def _data(a=1.502, n=600, seed=1):
    return pv.draw(np.random.default_rng(seed), n, a, True)


def test_estimators_match_statsmodels():
    y, T, z, _ = _data()
    w1 = pc.weighted_effect(y, T, z, "stabilized")[0]; p0 = cc.treatment_effect(y, T, z, "ipw")
    assert w1["estimate"] == pytest.approx(p0["estimate"], abs=1e-10) and w1["se"] == pytest.approx(p0["se"], rel=1e-4)
    g = pc.g_formula(y, T, z); ra = cc.treatment_effect(y, T, z, "ra")
    assert g["estimate"] == pytest.approx(ra["estimate"], abs=1e-10) and g["se"] == pytest.approx(ra["se"], rel=1e-6)


def test_overlap_weights_balance_exactly_and_diagnostics():
    y, T, z, _ = _data()
    r, e, w = pc.weighted_effect(y, T, z, "overlap")
    d = pc.diagnostics(T, z, e, w)
    assert max(abs(x) for x in d["smd_after"]) < 1e-10 and r["estimand"] == "overlap-population effect"
    assert 0 < d["overlap_coefficient"] <= 1 and d["effective_n"]["treated"] <= d["n"]["treated"]


def test_truncated_weights_are_clipped():
    y, T, z, _ = _data(a=2.045)
    _, e, w = pc.weighted_effect(y, T, z, "truncated")
    w0 = np.where(T == 1, T.mean()/e, (1-T.mean())/(1-e))
    assert w.max() <= np.quantile(w0, .99)+1e-12


def test_separation_is_refused():
    T = np.r_[np.zeros(20), np.ones(20)]; z = np.r_[np.linspace(-2, -1, 20), np.linspace(1, 2, 20)]
    with pytest.raises(ValueError, match="positivity|converge"):
        pc.propensity(T, z)


def test_validated_flags_match_audit():
    out = json.loads((ROOT/"docs/audits/positivity_validation.json").read_text())["outcome"]
    assert pz.VALIDATED == {"stabilized": out["W1"]["passed"], "truncated": out["W2"]["passed"],
                            "overlap": out["W3"]["passed"], "g_formula": out["G1"]["passed"], "flag": out["flag"]["passed"]}


def _frame(a, seed=3):
    y, T, z, _ = _data(a=a, n=300, seed=seed)
    return pd.DataFrame(dict(y=y, T=T, z1=z[:, 0], z2=z[:, 1]))


def test_engine_limited_overlap_marks_ipw_exploratory():
    f = _frame(2.045)
    r = causal.estimate_effect(f, "y", "T", ["z1", "z2"], method="ipw")
    assert r["positivity"]["limited_overlap"] and r["validated"] is False
    assert any("Limited overlap" in n for n in r["notes"])
    r = causal.estimate_effect(f, "y", "T", ["z1", "z2"], method="ra")
    assert r["validated"] is True
    good = causal.estimate_effect(_frame(.5), "y", "T", ["z1", "z2"], method="ipw")
    assert not good["positivity"]["limited_overlap"] and good["validated"] is True


@pytest.mark.parametrize("w,validated", [("stabilized", False), ("truncated", True), ("overlap", True)])
def test_engine_weights(w, validated):
    r = causal.estimate_effect(_frame(1.502), "y", "T", ["z1", "z2"], weights=w)
    assert r["validated"] is validated and "g_formula" in r and "agreement" in r and r["method"] == f"ipw_{w}"


def test_engine_refusals():
    f = _frame(1.0)
    with pytest.raises(ValueError):
        causal.estimate_effect(f, "y", "T", ["z1"], weights="bogus")
    with pytest.raises(ValueError):
        causal.estimate_effect(f, "y", "T", ["z1"], weights="overlap", calibrate=True)


def test_tool_summary_names_estimand(tmp_path):
    from census.workflows_inference import estimate_effect
    p = tmp_path/"f.csv"; _frame(2.045).assign(GEOID=[f"{i:05d}" for i in range(300)]).to_csv(p, index=False)
    r = estimate_effect(str(p), "treatment", "y", treatment="T", confounders=["z1", "z2"], weights="overlap")
    assert r["success"] and r["summary"].startswith("Overlap-population effect") and "Limited overlap" in r["summary"]
    assert any(s.get("id") == "li_morgan_zaslavsky2018" for s in __import__("census.references", fromlist=["x"])
               .sources_for_tool("estimate_effect"))
