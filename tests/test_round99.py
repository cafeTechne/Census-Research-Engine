# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 99: matching estimators and triple differences."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"scripts"))
from census import matching as mt, matching_core as mc  # noqa: E402
import positivity_validation as pv  # noqa: E402
import matching_validation as mv  # noqa: E402


def test_nn_and_cem_recover_effect():
    y, T, z, _ = pv.draw(np.random.default_rng(1), 600, .5, False)
    for est in ("ATT", "ATE"):
        r = mc.nn_match(y, T, z, 4, est)
        assert abs(r["estimate"]-.5) < 3*r["se"]
    c = mc.cem(y, T, z)
    assert 0 < c["share_treated_matched"] <= 1 and c["lower"] < c["upper"]


def test_exact_matching_without_noise():
    X = np.repeat(np.arange(10.), 2)[:, None]; T = np.tile([0, 1], 10); y = X[:, 0]+2*T
    r = mc.nn_match(y, T, X, 1, "ATT")
    assert r["estimate"] == pytest.approx(2.0)


def test_triple_difference_removes_unit_trend():
    R = mv.panel(np.random.default_rng(5), -2., .3)
    r = mc.triple_difference(R[:, 5], R[:, 0], R[:, 1], R[:, 2], R[:, 3], R[:, 4])
    assert abs(r["estimate"]+2) < 4*r["se"] and r["clusters"] == 51
    simple = mv._did(R[R[:, 1] == 1])
    assert abs(simple["estimate"]+2) > 1.0


def test_validated_flags_match_audit():
    out = json.loads((ROOT/"docs/audits/matching_validation.json").read_text())["outcome"]
    r104 = json.loads((ROOT/"docs/audits/repairs104_validation.json").read_text())["outcomes"]
    assert mt.VALIDATED == {"nn_ATE": out["M1-ATE"]["passed"], "nn_ATT": r104["M1b_ATT"], "cem": out["M2"]["passed"],
                            "ps": out["M3"]["passed"], "triple": out["T3"]["passed"]}


def test_tools(tmp_path):
    from census.workflows_inference import estimate_effect
    from census.workflows_microdata import difference_in_differences
    y, T, z, _ = pv.draw(np.random.default_rng(2), 300, .5, False)
    p = tmp_path/"f.csv"
    pd.DataFrame(dict(GEOID=[f"{i:05d}" for i in range(300)], y=y, T=T, z1=z[:, 0], z2=z[:, 1])).to_csv(p, index=False)
    r = estimate_effect(str(p), "matching", "y", treatment="T", confounders=["z1", "z2"], method="nn")
    assert r["success"] and r["summary"].startswith("Matching (nn, ATE)") and r["validated"]
    R = mv.panel(np.random.default_rng(6), 0., .3)
    f = pd.DataFrame(R, columns=["unit", "g", "t", "treated", "post", "y"])
    f["GEOID"] = f.unit.astype(int).astype(str); f["group"] = np.where(f.g == 1, "A", "B"); f["Year"] = 2010+f.t.astype(int)
    q = tmp_path/"p.csv"; f.to_csv(q, index=False)
    d = difference_in_differences(str(q), "y", "treated", 2015, design="triple", group="group", affected_group="A",
                                  product="1-year")
    assert d["success"] and d["effect"]["clusters"] == 51
