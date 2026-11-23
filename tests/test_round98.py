# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 98: regression discontinuity."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from census import rdd as rd
from census import rdd_core as rc

ROOT = Path(__file__).resolve().parents[1]


def test_sharp_recovers_jump_and_robust_wider():
    rng = np.random.default_rng(1)
    x = rng.uniform(-1, 1, 20000); y = .5*x+.3*(x >= 0)+rng.normal(0, .3, 20000)
    r = rc.rdd(x, y, 0.)
    assert abs(r["robust_estimate"]-.3) < 3*r["robust_se"] and r["robust_se"] > r["se"]
    assert abs(r["estimate"]-.3) < .05


def test_fuzzy_ratio():
    rng = np.random.default_rng(2)
    x = rng.uniform(-1, 1, 50000); d = (rng.random(50000) < .2+.6*(x >= 0)).astype(float)
    y = x+.5*d+rng.normal(0, .3, 50000)
    r = rc.rdd(x, y, 0., d=d)
    assert r["robust_lower"] < .5 < r["robust_upper"]


def test_density_test_detects_bunching():
    rng = np.random.default_rng(3)
    x = rng.uniform(-1, 1, 5000)
    assert rc.density_test(np.r_[x, rng.uniform(0, .05, 300)], 0.)["p"] < .01
    assert rc.density_test(x, 0.)["bandwidth"] > 0


def test_discrete_replicates_and_tool(tmp_path):
    rng = np.random.default_rng(4); n = 20000
    age = rng.integers(45, 85, n); w = rng.lognormal(0, .5, n)
    y = (rng.random(n) < .8+.003*(age-65)+.05*(age >= 65)).astype(float)
    f = pd.DataFrame({"AGEP": age, "y": y, "PWGTP": w})
    for i in range(1, 81):
        f[f"PWGTP{i}"] = w*(1+.3*rng.standard_normal(n))
    r = rd.regression_discontinuity(f, "y", "AGEP", 65, weight="PWGTP", replicate_prefix="PWGTP", placebo_cutoffs=[60])
    assert r["validated"] and r["bandwidth"] >= 4 and r["variance"] == "replicate" and "60" in r["placebo"]
    p = tmp_path/"f.parquet"; f.to_parquet(p)
    from census.workflows_microdata import regression_discontinuity
    out = regression_discontinuity(str(p), "y", "AGEP", 65, weight="PWGTP", replicate_prefix="PWGTP")
    assert out["success"] and "validated" in out["summary"]
    assert regression_discontinuity(str(p), "y", "AGEP", 65, replicate_prefix="NOPE")["success"] is False


def test_validated_flags_match_audit():
    out = json.loads((ROOT/"docs/audits/rdd_validation.json").read_text())["outcome"]
    assert rd.VALIDATED == {"discrete_replicate": out["R1-rep"]["passed"], "continuous": out["R1"]["passed"],
                            "density": out["D1"]["passed"]}
