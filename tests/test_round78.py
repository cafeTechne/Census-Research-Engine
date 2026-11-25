# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 78: staggered-adoption DiD (Sun-Abraham, Callaway-Sant'Anna) and exploratory synthetic control."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from census import policy_core as pc, staggered as sg

ROOT = Path(__file__).resolve().parents[1]
AUDIT = json.loads((ROOT/"docs/audits/policy_validation.json").read_text(encoding="utf-8"))


def _panel(noise=.5, n=51, seed=3, years=None, drop2020=True):
    rng = np.random.default_rng(seed)
    years = years or [y for y in range(2010, 2024) if not (drop2020 and y == 2020)]
    rows = []
    for i in range(n):
        g = [2014, 2016, 2019][i % 3] if i < 30 else np.nan
        a = rng.normal(10, 3)
        for y in years:
            tau = -2.0 if (not np.isnan(g) and y >= g) else 0.0
            rows.append(dict(GEOID=f"{i:02d}", Year=y, unins=a+.1*(y-2010)+tau+rng.normal(0, noise), se=.2, first=g))
    return pd.DataFrame(rows)


def test_flags_equal_the_audit():
    p = AUDIT["passed"]
    assert sg.VALIDATED["sun_abraham"] == p["S2"] is True
    assert sg.VALIDATED["callaway_santanna"] == p["S1"] is False
    assert sg.VALIDATED["callaway_santanna_acs"] == p["S1r"] is True
    assert sg.VALIDATED["synthetic_control"] is False and not p["C1"] and not p["C2"]
    assert AUDIT["draws"] == 1000
    assert "Committed before the full run" in (ROOT/"docs/audits/policy_validation_criterion.md").read_text(encoding="utf-8")


def test_noiseless_recovery():
    f = _panel(noise=0.0)
    for m in ("sun_abraham", "callaway_santanna"):
        r = sg.staggered_did(f, "unins", "first", se="se" if m == "callaway_santanna" else None, method=m)
        assert r["overall"]["estimate"] == pytest.approx(-2.0, abs=1e-9)
        ev = r["event_study"].set_index("event_time")["estimate"]
        assert ev.loc[0] == pytest.approx(-2.0, abs=1e-9) and abs(ev.loc[-3]) < 1e-9


def test_validity_and_notes():
    f = _panel()
    sa = sg.staggered_did(f, "unins", "first")
    assert sa["validated"] and sa["units"] == 51 and sa["never_treated"] == 21
    assert any("2020 skipped" in n for n in sa["notes"]) and sa["pretrend_min_holm_p"] is not None
    cs = sg.staggered_did(f, "unins", "first", method="callaway_santanna")
    assert not cs["validated"] and any("under-covered" in n for n in cs["notes"])
    assert sg.staggered_did(f, "unins", "first", method="callaway_santanna", se="se")["validated"]
    small = f[f.GEOID.astype(int) < 20]
    small = small.assign(first=np.where(small.GEOID.astype(int) < 10, small["first"], np.nan))
    assert not sg.staggered_did(small, "unins", "first")["validated"]


def test_refusals():
    f = _panel()
    with pytest.raises(ValueError, match="five-year"):
        sg.staggered_did(f, "unins", "first", product="5-year")
    with pytest.raises(ValueError, match="2020"):
        sg.staggered_did(_panel(drop2020=False), "unins", "first")
    with pytest.raises(ValueError, match="balanced|unbalanced"):
        sg.staggered_did(f.iloc[1:], "unins", "first")
    with pytest.raises(ValueError, match="never-treated"):
        sg.staggered_did(f.assign(first=2014), "unins", "first")


def test_tool(tmp_path):
    from census import workflows_microdata as wm
    p = tmp_path/"panel.csv"; _panel().to_csv(p, index=False)
    out = wm.difference_in_differences(str(p), "unins", None, design="staggered", first_treated="first", product="1-year")
    assert out["success"] and "validated" in out["summary"] and out["event_study"]
    assert not wm.difference_in_differences(str(p), "unins", None, design="staggered")["success"]
    assert not wm.difference_in_differences(str(p), "unins", "first", design="two_group")["success"]


def test_synthetic_control_is_exploratory():
    rng = np.random.default_rng(1)
    rows = []
    for i in range(20):
        a = rng.normal(10, 3)
        for y in range(2005, 2020):
            rows.append(dict(GEOID=f"{i:02d}", Year=y, v=a+.1*(y-2005)+rng.normal(0, .3)-(2 if i == 0 and y >= 2016 else 0)))
    r = sg.synthetic_control(pd.DataFrame(rows), "v", "00", 2016)
    assert r["validated"] is False and abs(sum(r["weights"].values())-1) < 1e-6
    assert len(r["gaps"]) == 4 and 0 < r["placebo_p"] <= 1
    w = pc.sc_weights(np.array([1., 2.]), np.array([[1., 0.], [2., 0.]]))
    assert w == pytest.approx([1, 0], abs=1e-6)
