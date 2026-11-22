# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 93: GWR, classification, regionalization and diversity."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from census import spatial_models as smod
from census import spatial_models_core as sm

ROOT = Path(__file__).resolve().parents[1]


def _grid(n=12):
    x, y = np.meshgrid(np.arange(n, dtype=float), np.arange(n, dtype=float))
    x, y = x.ravel(), y.ravel()
    D = np.hypot(x[:, None]-x[None], y[:, None]-y[None])
    E = [(i, j) for i in range(len(x)) for j in range(i+1, len(x)) if D[i, j] == 1]
    return x, y, D, E


def test_gwr_recovers_constant_and_varying_slopes():
    x, y, D, _ = _grid()
    rng = np.random.default_rng(1)
    z = rng.standard_normal(len(x))
    r = sm.gwr(1+2*z+.01*rng.standard_normal(len(x)), z[:, None], D, perms=0)
    assert np.allclose(r["coef"][:, 1], 2, atol=.05) and r["nonstationarity_p"] is None
    b = 1+x/x.max()
    r = sm.gwr(b*z+.01*rng.standard_normal(len(x)), z[:, None], D, bw=1.5, perms=19, rng=rng)
    assert np.corrcoef(r["coef"][:, 1], b)[0, 1] > .95 and r["nonstationarity_p"] <= .1
    assert (r["se"] > 0).all()


def test_skater_contiguous_and_recovers_planted_regions():
    x, y, _, E = _grid()
    truth = (x >= 6).astype(int)*2+(y >= 6)
    rng = np.random.default_rng(2)
    centres = np.array([[0, 0], [5, 0], [0, 5], [5, 5]], float)
    F = centres[truth]+.3*rng.standard_normal((len(x), 2))
    lab = sm.skater(F, E, 4)
    assert sm.adjusted_rand(truth, lab) > .9
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import connected_components
    for g in range(4):                       # every region is connected
        idx = np.flatnonzero(lab == g); s = set(idx.tolist())
        sub = [(a, b) for a, b in E if a in s and b in s]
        m = {v: k for k, v in enumerate(idx)}
        A = csr_matrix(([1]*len(sub), ([m[a] for a, _ in sub], [m[b] for _, b in sub])), shape=(len(idx), len(idx)))
        assert connected_components(A, directed=False)[0] == 1


def test_label_matching_and_stability():
    a = np.array([0, 0, 1, 1, 2, 2]); b = np.array([2, 2, 0, 0, 1, 1])
    assert (sm.match_labels(a, b, 3) == a).all() and sm.adjusted_rand(a, b) == 1
    assert (sm.stability(a, [b, b], 3) == 1).all()


def test_diversity_index():
    sh = pd.DataFrame([[.25]*4, [1, 0, 0, 0]], columns=list("abcd"))
    reps = [sh.copy() for _ in range(80)]
    out = smod.diversity_index(sh, reps)
    assert out.entropy.iloc[0] == pytest.approx(np.log(4)) and out.entropy.iloc[1] == pytest.approx(0, abs=1e-9)
    assert (out.se == 0).all() and out["max"].iloc[0] == pytest.approx(np.log(4))


def test_classify_wrapper_and_refusals():
    rng = np.random.default_rng(3)
    f = pd.DataFrame({"GEOID": [f"{i:05d}" for i in range(80)], "a": np.r_[rng.normal(0, .3, 40), rng.normal(3, .3, 40)],
                      "b": rng.normal(size=80), "a_se": .1, "b_moe": .2})
    r = smod.classify(f, ["a", "b"], 2, replicates=5)
    assert set(r["assignments"].group) == {1, 2} and r["assignments"].stability.between(0, 1).all()
    assert r["validated"] is False
    with pytest.raises(ValueError, match="_se"):
        smod.classify(f.drop(columns="a_se"), ["a", "b"], 2)
    with pytest.raises(ValueError):
        smod.classify(f, ["a", "b"], 1)
    with pytest.raises(ValueError):
        smod.classify(f, ["a", "b"], 2, method="skater")


def test_validated_flags_match_audit():
    out = json.loads((ROOT/"docs/audits/spatial_models_validation.json").read_text())["outcome"]
    assert smod.VALIDATED == {"gwr": out["R1"]["passed"], "diversity": out["D1"]["passed"],
                              "diversity_bc": out["D1bc"]["passed"]}


def test_tool_registered_and_refuses_bad_kind():
    from census.workflows_geo import spatial_model
    assert spatial_model("x.csv", "bogus", "tract", 2023)["success"] is False
    from census.references import tool_entries
    assert {"brunsdon1996", "assuncao2006", "walker2023"} <= {s for s, _ in tool_entries("spatial_model")}
