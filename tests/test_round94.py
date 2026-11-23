# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 94: WHO inequality monitoring measures."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from census import inequality_monitoring as imon
from census import inequality_monitoring_core as im
from census.replicate import REPLICATE_COLUMNS

ROOT = Path(__file__).resolve().parents[1]


def test_measures_by_hand():
    m = im.measures(np.array([.1, .2, .3]), np.array([.5, .3, .2]), 0)
    assert m["mdm_u"] == pytest.approx((.07+.03+.13)/3) and m["mdm_w"] == pytest.approx(.07)
    assert m["mdb_u"] == pytest.approx(.15) and m["mdb_w"] == pytest.approx(.14)
    assert m["par"] == pytest.approx(.07) and m["par_pct"] == pytest.approx(700/17)
    best = im.measures(np.array([.3, .1, .2]), np.array([.2, .5, .3]), "best")
    assert best["par"] == pytest.approx(.07)          # rbar .17 minus the best (lowest) rate .10


def test_best_reselected_in_replicates():
    r = np.array([[.20, .21, .40]]); p = np.array([[.4, .4, .2]])
    reps = np.repeat(r[:, :, None], 80, 2).copy(); reps[0, 0, :40] = .22   # best flips to group 1 in half the replicates
    out = im.replicate_intervals(r, p, reps, None, "best")
    fixed = im.replicate_intervals(r, p, reps, None, 0)
    # replicates where group 0 rises above group 1 switch the best group in the re-selected version only
    assert not np.isclose(out["par"]["se"][0], fixed["par"]["se"][0])
    assert out["par"]["se"][0] < fixed["par"]["se"][0]


def test_change_identity():
    iv = {m: dict(estimate=np.array([1.0]), se=np.array([.1]), lower=None, upper=None) for m in im.MEASURES}
    iv2 = {m: dict(estimate=np.array([1.5]), se=np.array([.1]), lower=None, upper=None) for m in im.MEASURES}
    d = im.change(iv, iv2)
    assert d["par"]["estimate"][0] == pytest.approx(.5) and d["par"]["se"][0] == pytest.approx(np.sqrt(.02))
    assert d["mdm_w"]["se"][0] == pytest.approx(np.sqrt((1*.1)**2+(1.5*.1)**2))


def test_validated_flags_match_audit():
    out = json.loads((ROOT/"docs/audits/inequality_monitoring_validation.json").read_text())["outcome"]
    assert imon.VALIDATED["par"] is (out["PAR-declared"]["passed"] and out["PAR-best"]["passed"])
    assert imon.VALIDATED["mdm_w"] is out["MDM"]["passed"] and imon.VALIDATED["mdb_w"] is out["MDB-declared"]["passed"]
    assert imon.VALIDATED["sii"] is out["SII"]["passed"] and out["T1"]["passed"]


def _frame(years=(2024,), seed=1):
    rng = np.random.default_rng(seed); rows, reps = [], []
    for y in years:
        for g in ("26001", "26003"):
            r = {"r_a": .10, "r_b": .25, "r_c": .18}; n = {"n_a": 5000., "n_b": 1500., "n_c": 800.}
            rows.append({"GEOID": g, "Year": y, **r, **n})
            for k, v in {**r, **n}.items():
                rep = v*(1+.03*rng.standard_normal(80))
                reps.append({"GEOID": g, "Year": y, "variable": k, **dict(zip(REPLICATE_COLUMNS, rep))})
    return pd.DataFrame(rows), pd.DataFrame(reps)


def test_monitoring_and_change():
    f, r = _frame()
    out = imon.monitoring_measures(f, ["r_a", "r_b", "r_c"], ["n_a", "n_b", "n_c"], r)
    par = out[out.measure == "par"]
    assert (par.reference == "r_a").all() and par.validated.all()
    assert not out[out.measure.str.startswith("md")].validated.any()
    f2, r2 = _frame((2019, 2024))
    ch = imon.monitoring_measures(f2, ["r_a", "r_b", "r_c"], ["n_a", "n_b", "n_c"], r2, compare_years=[2019, 2024])
    assert set(ch.measure) == set(im.MEASURES) and ch[ch.measure == "par"].validated.all()
    with pytest.raises(ValueError, match="non-overlapping"):
        imon.monitoring_measures(f2, ["r_a", "r_b", "r_c"], ["n_a", "n_b", "n_c"], r2, compare_years=[2021, 2024])


def test_double_disaggregation_and_quadrants():
    f = pd.DataFrame({"GEOID": ["1", "2"], "x": [10., 20.], "x_moe": [1.645, 16.45], "y": [5., 5.], "y_se": [.5, .5]})
    t = imon.double_disaggregation(f, {"poor": {"black": "x"}, "nonpoor": {"black": "y"}})
    assert len(t) == 4 and not t[(t.GEOID == "2") & (t.stratifier_1 == "poor")].reliable.iloc[0]
    q = pd.DataFrame({"lvl": [10, 30, 20], "lvl_lower": [8, 28, 10], "lvl_upper": [12, 32, 30],
                      "ineq": [1, 5, 3], "ineq_lower": [.5, 4.5, 1], "ineq_upper": [1.5, 5.5, 5]})
    out = imon.priority_quadrants(q, "lvl", "ineq")
    assert out.priority.tolist()[1].startswith("high") and out.priority.tolist()[2] == "uncertain"


def test_tool_option(tmp_path):
    from census.workflows_inference import disparity_measures
    f, r = _frame()
    fp, rp = tmp_path/"f.csv", tmp_path/"r.parquet"
    f.to_csv(fp, index=False); r.to_parquet(rp)
    out = disparity_measures(str(fp), ["r_a", "r_b", "r_c"], ["n_a", "n_b", "n_c"], reference="best",
                             replicates_path=str(rp), who_measures=True)
    assert out["success"] and "WHO measures" in out["summary"]
