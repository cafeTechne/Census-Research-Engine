# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 56: PUMS income inequality measures with SDR replicate variance (flags = audit)."""
import json
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd
import pytest

from census import pums_inequality as pq, pums_inequality_core as pc, pums_tests as pt

ROOT = Path(__file__).resolve().parents[1]
AUDIT = json.loads((ROOT/"docs/audits/pums_inequality_validation.json").read_text())


def test_flags_equal_the_fixed_audit():
    assert AUDIT["criterion_commit"] == "d91201b"
    p = AUDIT["passed"]
    for m in pc.MEASURES:
        assert pq.VALIDATED[m] is p[m]
    assert pq.GINI_DIFFERENCE_VALIDATED is p["gini_diff_A2_A0"] is True
    assert [m for m in pc.MEASURES if pq.VALIDATED[m]] == ["gini", "log_p90_p10", "log_p80_p20"]


def test_core_formulas_by_hand():
    y = np.array([1., 2, 3, 4, 10]); w = np.array([1., 1, 2, 1, 1])
    m = {k: float(v[0]) for k, v in pc.measures(y, w).items()}
    p = w/w.sum(); mu = p @ y
    gini = np.sum(p[:, None]*p[None, :]*np.abs(y[:, None]-y[None, :]))/(2*mu)
    assert m["gini"] == pytest.approx(gini)
    assert m["theil_t"] == pytest.approx(np.sum(p*y/mu*np.log(y/mu)))
    assert m["atkinson_0.5"] == pytest.approx(1-np.sum(p*np.sqrt(y/mu))**2)
    assert m["atkinson_1"] == pytest.approx(1-np.exp(np.sum(p*np.log(y)))/mu)
    assert m["log_p90_p10"] == pytest.approx(np.log(10/1)) and m["log_p80_p20"] == pytest.approx(np.log(4/2))
    assert pc.measures(np.array([1., 2, 3, 4, 10]), np.ones(5))["top10_share"][0] == pytest.approx(.25)
    zero = pc.measures(np.array([0., 1, 1, 2]), np.ones(4))
    assert "theil_t" not in zero and zero["gini"][0] == pytest.approx(np.abs(np.subtract.outer([0, 1, 1, 2], [0, 1, 1, 2])).sum()/16/2/1)
    with pytest.raises(ValueError, match="negative"):
        pc.measures(np.array([-1., 2]), np.ones(2))


def frame(n=3000, seed=56):
    rng = np.random.default_rng(seed)
    w = rng.uniform(5, 40, n); W = w[:, None]*np.column_stack((np.ones(n), pt.sdr_factors(n)))
    inc = np.exp(10+.8*rng.standard_normal(n))*(rng.uniform(size=n) > .1)
    return pd.DataFrame({"PWGTP": W[:, 0], **{f"PWGTP{i}": W[:, i] for i in range(1, 81)},
                         "PINCP": inc, "DIS": rng.integers(1, 3, n)}), W


def test_engine_table_groups_and_zero_handling():
    df, W = frame()
    out = pq.pums_inequality(df, "PINCP", by="DIS")
    t = out["table"].set_index("measure")
    assert t.loc["gini", "validated"] and not t.loc["theil_t", "validated"]
    assert any("zero income" in n for n in out["notes"])
    y = df.PINCP.to_numpy(); pos = y > 0
    assert t.loc["theil_t", "estimate"] == pytest.approx(pc.measures(y[pos], W[pos, 0])["theil_t"][0])
    a, b = (df.DIS == 1).to_numpy(), (df.DIS == 2).to_numpy()
    diff = pc.measures(y[b], W[b])["gini"]-pc.measures(y[a], W[a])["gini"]
    assert out["gini_difference"]["estimate"] == pytest.approx(diff[0])
    assert out["gini_difference"]["se"] == pytest.approx(np.sqrt(.05*np.sum((diff[1:]-diff[0])**2)))
    df2 = df.copy(); df2.loc[0, "PINCP"] = -50.
    with pytest.raises(ValueError, match="negative incomes"):
        pq.pums_inequality(df2, "PINCP")


def test_heaped_quantiles_flagged():
    df, _ = frame()
    df["PINCP"] = np.where(df.PINCP < 30000, 20000., df.PINCP)      # a heap at the lower quantiles
    t = pq.pums_inequality(df, "PINCP")["table"].set_index("measure")
    assert not t.loc["log_p90_p10", "validated"] and "heaped" in t.loc["log_p90_p10", "note"]
    assert t.loc["gini", "validated"]


def test_mcp_kind_inequality():
    from census import workflows_microdata as wm
    df, _ = frame()
    with mock.patch("census.pums.fetch_pums", return_value=df):
        out = wm.test_association("26", 2022, "inequality", var="PINCP", by="DIS")
    assert out["success"] and "Gini of PINCP" in out["summary"] and "gini_difference" in out, out
    assert not wm.test_association("26", 2022, "inequality")["success"]


def test_rule_text_mirrored():
    from census import mcp_profiles
    for path in ("docs/agent_protocol.md", "census/mcp_instructions.py", "docs/recipes/pums_tests.md"):
        text = " ".join((ROOT/path).read_text().split())
        assert "Round 56" in text and "inequality" in text and "Gini" in text
    assert "inequality" in mcp_profiles.CORE_INSTRUCTIONS
