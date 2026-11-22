# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 85: area designations as screening tests."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from census import designation as dg, designation_core as dc

ROOT = Path(__file__).resolve().parents[1]
AUDIT = json.loads((ROOT/"docs/audits/designation_validation.json").read_text())


def test_flags_equal_the_audit():
    p = AUDIT["passed"]
    assert dg.VALIDATED == {"q1_direct": p["Q1a"], "q1_fh": p["Q1b"], "q2": p["Q2b"]}
    assert p["Q1b"] and not p["Q1a"] and not p["Q2b"]
    assert "Committed before the full run" in (ROOT/"docs/audits/designation_validation_criterion.md").read_text()


def test_expected_accuracy_by_hand():
    P = np.array([.9, .8, .2, .1]); S = np.array([True, True, False, False])
    e = dc.expected_accuracy(S, P)
    assert e["tp"] == pytest.approx(1.7) and e["ppv"] == pytest.approx(.85)
    assert e["sensitivity"] == pytest.approx(1.7/2.0) and e["npv"] == pytest.approx(1.7/2)
    assert dc.q1_direct(np.array([.2]), np.array([1e6]), .1)[0] == pytest.approx(1.0)
    assert list(dc.designate("point", np.array([.19, .21]), np.array([100, 100]), .2)) == [False, True]


def _frame(seed=0, m=400):
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(m); n = rng.uniform(80, 600, m)
    p = np.sin(np.clip(.4+.1*x+rng.normal(0, .1, m), 0, 1.5))**2
    ph = rng.binomial(n.round().astype(int), p)/n.round()
    return pd.DataFrame(dict(GEOID=[f"{i:05d}" for i in range(m)], pov=100*ph, n=n, x=x))


def test_designation_accuracy_and_tool(tmp_path):
    from census import workflows_inference as wi
    f = _frame()
    r = dg.designation_accuracy(f, "pov", 20, n_col="n", covariates=["x"])
    rules = r["rules"].set_index("rule")
    assert rules.loc["lower", "designated"] <= rules.loc["point", "designated"]
    assert rules.loc["prob80", "ppv"] >= rules.loc["prob50", "ppv"] - 1e-9
    assert r["areas"].probability_above.between(0, 1).all() and r["validated"]["q1_fh"]
    p = tmp_path/"f.csv"; f.to_csv(p, index=False)
    out = wi.designation_accuracy(str(p), "pov", 20, n_col="n", covariates=["x"], output_path=str(tmp_path/"o.csv"))
    assert out["success"] and "exploratory" in out["summary"]
    assert not wi.designation_accuracy(str(p), "pov", 20)["success"]
