# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 34: rank intervals, reference comparisons and the rank_areas tool."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from census import ranking, ranking_core as rc
from census.simulation import make_replicates

ROOT = Path(__file__).resolve().parents[1]


def test_rank_intervals_by_hand():
    x, s = np.array([10., 9., 5.]), np.array([.5, .5, .5])
    lo, hi = rc.rank_intervals(x, s)
    crit = stats.norm.ppf(1-.10/(2*2))
    assert (10-9)/np.sqrt(.5) < crit < (9-5)/np.sqrt(.5)   # 10 vs 9 not significant; 9 vs 5 significant
    assert list(lo) == [1, 1, 3] and list(hi) == [2, 2, 3]
    jl, jh = rc.rank_intervals(x, s, joint=True)
    assert np.all(jl <= lo) and np.all(jh >= hi)       # joint intervals contain individual ones


def test_reference_covariance_formula_and_replicates():
    rng = np.random.default_rng(1); K = 6
    s = rng.lognormal(0, .4, K); w = rng.random(K); w /= w.sum()
    cov = rc.reference_covariance(s, w)
    i, j = 1, 3
    expect = -w[i]*s[i]**2-w[j]*s[j]**2+np.sum(w**2*s**2)
    assert cov[i, j] == pytest.approx(expect)
    assert cov[i, i] == pytest.approx(s[i]**2*(1-2*w[i])+np.sum(w**2*s**2))
    sims = rng.standard_normal((200000, K))*s
    emp = np.cov((sims-(sims@w)[:, None]).T)
    np.testing.assert_allclose(emp, cov, atol=.02)


def test_engine_tables_exclusions_and_replicates():
    rng = np.random.default_rng(2); K = 25
    f = pd.DataFrame(dict(GEOID=[f"26{i:03d}" for i in range(K)], y=rng.normal(10, 2, K), y_se=rng.lognormal(0, .4, K),
                          pop=rng.lognormal(10, 1, K)))
    f["y"] = f["y"].astype(object); f.loc[4, "y"] = "suppressed"
    r = ranking.rank_intervals(f, "y", se_col="y_se")
    assert r["K"] == 24 and r["excluded"] == ["26004"] and r["validated"]
    assert (r["table"].rank_lower <= r["table"]["rank"]).all() and (r["table"]["rank"] <= r["table"].rank_upper).all()
    g = f.drop(index=4).reset_index(drop=True); g["y"] = g.y.astype(float)
    rep = make_replicates(g[["y"]].to_numpy(float), g[["y_se"]].to_numpy(float), rng)
    long = pd.DataFrame(rep[:, 0, :], columns=[f"rep_{k+1}" for k in range(80)])
    long.insert(0, "estimate", g.y); long.insert(0, "variable", "y"); long.insert(0, "GEOID", g.GEOID)
    c = ranking.compare_to_reference(g, "y", replicates=long, weights="pop", method="simultaneous")
    w = g["pop"].to_numpy()/g["pop"].sum()
    assert c["reference_value"] == pytest.approx(w@g.y.to_numpy())
    assert {"lower", "upper", "differs"} <= set(c["table"].columns)
    fixed = ranking.compare_to_reference(g, "y", se_col="y_se", reference=10.0)
    np.testing.assert_allclose(fixed["table"].se, g.y_se)
    with pytest.raises(ValueError, match="weights"):
        ranking.compare_to_reference(g, "y", se_col="y_se")


def test_flags_equal_the_fixed_audit():
    passed = json.loads((ROOT/"docs/audits/ranking_validation.json").read_text())["passed"]
    assert passed == {"R1": True, "R2": True, "R3": False, "V1": True, "V2": True}
    assert not hasattr(ranking, "bootstrap_rank_intervals")       # failed R3 is not exposed by the engine


def test_rank_areas_tool_offline(tmp_path):
    from census import workflows_inference as wi
    rng = np.random.default_rng(3); K = 20
    f = pd.DataFrame(dict(GEOID=[f"26{i:03d}" for i in range(K)], y=rng.normal(10, 2, K), y_moe=1.645*rng.lognormal(0, .4, K),
                          pop=rng.lognormal(10, 1, K)))
    path = tmp_path/"f.csv"; f.to_csv(path, index=False)
    a = wi.rank_areas(str(path), "y", moe_col="y_moe")
    assert a["success"] and len(a["table"]) == K and "rank interval" in a["next_step"]
    b = wi.rank_areas(str(path), "y", kind="versus_reference", moe_col="y_moe", weights="pop")
    assert b["success"] and "differ" in b["summary"]
    assert not wi.rank_areas(str(path), "y")["success"]          # no uncertainty given
    json.dumps(a); json.dumps(b)
