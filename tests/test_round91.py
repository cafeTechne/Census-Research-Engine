# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 91: IP-weighted marginal structural models for annual panels."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"scripts"))
from census import msm, msm_core as mc  # noqa: E402
import msm_validation as mv  # noqa: E402


def _panel(seed=5, g=1., psi=-2., K=12, n=51):
    Y, A, L, u, yr = mv.panel(np.random.default_rng(seed), K, g, psi, n=n)
    df = pd.DataFrame(dict(GEOID=[f"{i:02d}" for i in u], Year=2005+yr, y=Y, unemp=L))
    df["first"] = df.GEOID.map(df[A == 1].groupby("GEOID").Year.min())
    return df, (Y, A, L, u, yr)


def test_durations_and_weights():
    A = np.array([0, 0, 1, 1, 0, 0, 0, 1]); u = np.array([0, 0, 0, 0, 1, 1, 1, 1]); yr = np.array([1, 2, 3, 4]*2)
    assert mc.durations(A, u, yr).tolist() == [0, 0, 1, 2, 0, 0, 0, 1]
    _, (Y, A, L, u, yr) = _panel()
    w = mc.weights(A, L, u, yr, 12)
    first = {}
    for i in np.argsort(yr, kind="stable"):
        if A[i] == 1:
            first.setdefault(u[i], yr[i])
    after = np.array([yr[i] > first.get(u[i], 99) for i in range(len(A))])
    # after the first treated year the weight stays constant within unit
    for unit in np.unique(u[after]):
        assert np.ptp(w[(u == unit) & after]) == pytest.approx(0)
    assert np.all(w[yr == 1] == 1)


def test_large_panel_recovers_targets():
    _, (Y, A, L, u, yr) = _panel(seed=11, n=6000)
    est = mc.msm_point(Y, A, L, u, yr, 12)[0]
    assert np.allclose(est, mv.targets(1., -2.), atol=.12)
    naive = mc.msm_point(Y, A, L, u, yr, 12, adjust_L=True)[0]
    assert naive[2] < mv.targets(1., -2.)[2]-.8          # adjusting for L blocks the feedback path


def test_validated_flags_match_audit():
    out = json.loads((ROOT/"docs/audits/msm_validation.json").read_text())["outcome"]
    assert msm.VALIDATED == {"stabilized": out["M1"]["passed"], "truncated": out["M2"]["passed"]}


def test_engine_and_refusals():
    df, _ = _panel()
    r = msm.marginal_structural_model(df, "y", "first", ["unemp"], bootstrap=50)
    assert [e["duration"] for e in r["effects"]] == [1, 2, 3] and r["units"] == 51 and len(r["naive_adjusted"]) == 3
    with pytest.raises(ValueError, match="five-year|overlapping"):
        msm.marginal_structural_model(df, "y", "first", ["unemp"], product="5-year")
    with pytest.raises(ValueError, match="required"):
        msm.marginal_structural_model(df, "y", "first", [])
    bad = df.copy(); bad.loc[bad.GEOID == "00", "first"] = 2006
    with pytest.raises(ValueError, match="time zero"):
        msm.marginal_structural_model(bad, "y", "first", ["unemp"])
    with pytest.raises(ValueError, match="balanced"):
        msm.marginal_structural_model(df.iloc[1:], "y", "first", ["unemp"])
    with pytest.raises(ValueError, match="at least"):
        msm.marginal_structural_model(df[df.GEOID < "20"], "y", "first", ["unemp"])


def test_tool(tmp_path):
    from census.workflows_microdata import difference_in_differences
    df, _ = _panel()
    p = tmp_path/"p.csv"; df.to_csv(p, index=False)
    r = difference_in_differences(str(p), "y", "treated", design="msm", first_treated="first",
                                  time_varying_confounders=["unemp"], product="1-year")
    assert r["success"] and r["summary"].startswith("Marginal structural model") and "causal_assessment" in r
    assert difference_in_differences(str(p), "y", "treated", design="msm", product="1-year")["success"] is False
