# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 100: multiple imputation by fully conditional specification."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"scripts"))
from census import mice as mi, mice_core as mc  # noqa: E402
import mice_validation as mv  # noqa: E402


def _frame(seed=3, n=400, c=-.5):
    return pd.DataFrame(mv.data(np.random.default_rng(seed), n, c), columns=["y", "x1", "x2", "x3"])


def test_pmm_imputes_observed_values_only():
    f = _frame(); D = f.to_numpy()
    imps = mc.mice(D, {0: "pmm", 1: "pmm", 2: "pmm"}, m=3, rng=np.random.default_rng(1))
    obs2 = set(D[~np.isnan(D[:, 2]), 2])
    for Z in imps:
        assert not np.isnan(Z).any() and set(Z[np.isnan(D[:, 2]), 2]) <= obs2


def test_pool_rubin_and_fmi():
    est = [np.array([1.0]), np.array([1.2]), np.array([0.8])]; var = [np.array([.04])]*3
    p = mc.pool(est, var, df_complete=100)
    assert p["estimate"][0] == pytest.approx(1.0)
    assert p["se"][0] == pytest.approx(np.sqrt(.04+(1+1/3)*.04))
    assert 0 < p["fmi"][0] < 1 and p["df"][0] < 100


def test_delta_zero_equals_mar_and_shift_moves():
    f = _frame()
    a = mi.impute_fcs("y ~ x1 + x2 + x3", f, ["y", "x1", "x2"], m=5, delta={"x1": [0.0, 1.0]})
    base = a["table"].set_index("term").estimate["x1"]
    sens = {d["delta"]: d["estimate[x1]"] for d in a["delta_sensitivity"]}
    assert sens[0.0] == pytest.approx(base) and sens[1.0] != pytest.approx(base)


def test_refusals():
    f = _frame()
    with pytest.raises(ValueError, match="not listed"):
        mi.impute_fcs("y ~ x1 + x2 + x3", f, ["y"], m=2)
    with pytest.raises(ValueError):
        mi.impute_fcs("y ~ x1 + x2 + x3", f, ["y", "x1", "x2"], method="hotdeck", m=2)


def test_validated_flags_match_audit():
    out = json.loads((ROOT/"docs/audits/mice_validation.json").read_text())["outcome"]
    assert mi.VALIDATED == {"pmm": out["pmm"]["passed"], "norm": out["norm"]["passed"]}


def test_fit_model_route(tmp_path):
    from census.workflows_inference import fit_model
    f = _frame().assign(GEOID=[f"{i:05d}" for i in range(400)])
    p = tmp_path/"f.csv"; f.to_csv(p, index=False)
    r = fit_model(str(p), "y ~ x1 + x2 + x3", method="replicate", impute=["y", "x1", "x2"], impute_method="pmm")
    assert r["success"] and "Round 100" in r["summary"] and "fmi" in r["table"][0]
