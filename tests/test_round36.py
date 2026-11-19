# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 36: composite indices, Cronbach's alpha and the build_index tool."""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from census import composite_index as ci, index_core as ic
from census.simulation import make_replicates

ROOT = Path(__file__).resolve().parents[1]
warnings.simplefilter("ignore")


def frame(n=120, seed=36):
    rng = np.random.default_rng(seed)
    f = rng.normal(size=n)
    X = np.column_stack([.8*f+.6*rng.normal(size=n) for _ in range(4)])
    df = pd.DataFrame(X, columns=["a", "b", "c", "d"]); df.insert(0, "GEOID", [f"26{i:03d}" for i in range(n)]); df["Year"] = 2022
    se = np.full(X.shape, .2)
    rep = make_replicates(X, se, rng)
    rows = []
    for j, c in enumerate(["a", "b", "c", "d"]):
        b = pd.DataFrame(rep[:, j, :], columns=[f"rep_{k+1}" for k in range(80)])
        b.insert(0, "estimate", X[:, j]); b.insert(0, "variable", c); b.insert(0, "Year", 2022); b.insert(0, "GEOID", df.GEOID)
        rows.append(b)
    return df, pd.concat(rows, ignore_index=True), X, rep


def test_loadings_alpha_and_feldt_by_hand():
    df, _, X, _ = frame()
    m, s = ic.standardize(X); Z = (X-m)/s
    l, share = ic.loadings(Z)
    vals, vecs = np.linalg.eigh(np.corrcoef(Z, rowvar=False))
    assert np.allclose(np.abs(l), np.abs(vecs[:, -1])) and l.sum() > 0 and share == pytest.approx(vals[-1]/4)
    k = 4; a = k/(k-1)*(1-Z.var(axis=0, ddof=1).sum()/Z.sum(axis=1).var(ddof=1))
    assert ic.cronbach(Z) == pytest.approx(a)
    r = ic.alpha_interval(Z)
    n = len(Z)
    assert r["lower"] == pytest.approx(1-(1-a)*stats.f.ppf(.95, n-1, (n-1)*3))
    assert r["upper"] == pytest.approx(1-(1-a)*stats.f.ppf(.05, n-1, (n-1)*3))


def test_score_se_by_hand():
    df, _, X, rep = frame()
    m, s = ic.standardize(X); l, _ = ic.loadings((X-m)/s, "equal")
    sc, se, lo, hi = ic.score_intervals(X, rep, m, s, l)
    rs = np.array([((rep[:, :, r]-m)/s) @ l for r in range(80)]).T
    np.testing.assert_allclose(se, np.sqrt(.05*((rs-sc[:, None])**2).sum(axis=1)))
    np.testing.assert_allclose(l, .5)


def test_build_index_engine_reverse_circularity_and_typology():
    df, reps, X, _ = frame()
    out = ci.build_index(df, ["a", "b", "c", "d"], replicates=reps, typology_k=3)
    assert out["validated_scores"] and set(out["table"].quintile) == {1, 2, 3, 4, 5}
    assert out["table"].quintile_stability.between(0, 1).all()
    assert "replicate_adjusted_rand_median" in out["typology"]
    flipped = ci.build_index(df, ["a", "b", "c", "d"], replicates=reps, reverse=["d"])
    assert flipped["loadings"]["d"] != pytest.approx(out["loadings"]["d"])
    with pytest.raises(ValueError, match="CIRCULARITY"):
        ci.build_index(df, ["a", "b", "c"], outcome="a")
    with pytest.raises(ValueError, match="at least three"):
        ci.build_index(df, ["a", "b"])
    plain = ci.build_index(df, ["a", "b", "c"])
    assert not plain["validated_scores"] and plain["table"].se.isna().all()


def test_ari_identity_and_permutation():
    a = np.array([0, 0, 1, 1, 2, 2]); assert ci._ari(a, a) == pytest.approx(1.)
    assert ci._ari(a, np.array([2, 2, 0, 0, 1, 1])) == pytest.approx(1.)


def test_flags_equal_the_fixed_audit():
    passed = json.loads((ROOT/"docs/audits/index_validation.json").read_text())["passed"]
    assert passed["S1/pca"] and passed["S1/equal"] and passed["A1"]


def test_build_index_tool_offline(tmp_path):
    from census import workflows_inference as wi
    df, reps, _, _ = frame()
    fp, rp = tmp_path/"f.csv", tmp_path/"r.parquet"; df.to_csv(fp, index=False); reps.to_parquet(rp)
    out = wi.build_index(str(fp), ["a", "b", "c", "d"], replicates_path=str(rp))
    assert out["success"] and "alpha" in out["summary"] and len(out["table"]) == len(df)
    assert not wi.build_index(str(fp), ["a", "b", "c"], outcome="a")["success"]
    json.dumps(out)
