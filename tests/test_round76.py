# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 76: between-group disparity measures and Kitagawa decomposition."""
import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from census import disparity as d, disparity_core as dc
from census.manifest import load_manifest, validate_manifest
from census.manifest import methods as mm
from census.simulation import make_replicates, replicate_long
from tests.test_manifest import EXAMPLE

ROOT = Path(__file__).resolve().parents[1]
AUDIT = json.loads((ROOT/"docs/audits/disparity_validation.json").read_text())
GEO = ["26001", "26003", "26005"]


def _acs(cv=(.05, .2, .25), seed=1):
    rng = np.random.default_rng(seed)
    est = np.array([[.1, .25, .3, 1000, 200, 100]]*3)*np.array([1, 1.1, .9])[:, None]
    se = est*np.array([*cv, .01, .1, .12])
    names = ["r_w", "r_b", "r_h", "p_w", "p_b", "p_h"]
    return pd.DataFrame(est, columns=names).assign(GEOID=GEO), replicate_long(GEO, names, est, make_replicates(est, se, rng))


def test_flags_equal_the_audit():
    acs = AUDIT["acs"]
    for m, cap in d.ACS_MAX_CV.items():
        assert (cap == .50) == acs[m]["passed"] and (cap == .30) == (not acs[m]["passed"] and acs[m]["range_gated"])
    cnt = AUDIT["counts"]
    assert set(d.COUNT_VALIDATED) == {m for m, v in cnt.items() if v["passed"]}
    assert all(v["passed"] for k in ("kitagawa_acs", "kitagawa_counts") for v in AUDIT[k].values())
    assert AUDIT["draws"] == 2000
    crit = (ROOT/"docs/audits/disparity_validation_criterion.md").read_text()
    assert "Committed before the full run" in crit


def test_core_measures_by_hand():
    m = dc.measures(np.array([.1, .3]), np.array([3., 1.]), 0)
    rbar = .75*.1+.25*.3
    assert m["rd"][0] == pytest.approx(.2) and m["log_rr"][0] == pytest.approx(np.log(3))
    assert m["idisp"] == pytest.approx(200)
    assert m["bgv"] == pytest.approx(.75*(.1-rbar)**2+.25*(.3-rbar)**2)
    assert m["theil"] == pytest.approx(.75*(.1/rbar)*np.log(.1/rbar)+.25*(.3/rbar)*np.log(.3/rbar))
    assert m["mld"] == pytest.approx(.75*np.log(rbar/.1)+.25*np.log(rbar/.3))
    k = dc.kitagawa([.1, .3], [3, 1], [.2, .4], [1, 1])
    assert k["rate_effect"]+k["composition_effect"] == pytest.approx(k["difference"])


def test_replicate_se_matches_hand_formula():
    f, R = _acs()
    out = d.disparity_measures(f, ["r_w", "r_b", "r_h"], "r_w", ["p_w", "p_b", "p_h"], replicates=R)
    row = out[(out.GEOID == "26001") & (out.measure == "rd") & (out.group == "r_b")].iloc[0]
    rb = R[(R.GEOID == "26001") & (R.variable == "r_b")].iloc[0, 3:].to_numpy(float)
    rw = R[(R.GEOID == "26001") & (R.variable == "r_w")].iloc[0, 3:].to_numpy(float)
    assert row.se == pytest.approx(np.sqrt(4/80*(((rb-rw)-row.estimate)**2).sum()))
    assert out.validated.all() and np.allclose(out.max_group_cv, .25)
    assert any("mutually exclusive" in n for n in row.notes)


def test_cv_gate_and_group_limit():
    f, R = _acs(cv=(.05, .2, .4))
    out = d.disparity_measures(f, ["r_w", "r_b", "r_h"], "r_w", ["p_w", "p_b", "p_h"], replicates=R)
    v = out.groupby("measure").validated.all()
    assert v["rd"] and v["idisp"] and not v["log_rr"] and not v["mld"]
    assert any("exceeds the validated 0.30" in n for n in out[out.measure == "bgv"].iloc[0].notes)


def test_missing_replicates_make_rows_undefined():
    f, R = _acs()
    R.loc[(R.GEOID == "26003") & (R.variable == "r_h"), "rep_5"] = np.nan
    out = d.disparity_measures(f, ["r_w", "r_b", "r_h"], "r_w", ["p_w", "p_b", "p_h"], replicates=R)
    assert not out[out.GEOID == "26003"].validated.any() and out[out.GEOID == "26001"].validated.all()
    with pytest.raises(ValueError, match="need replicates"):
        d.disparity_measures(f, ["r_w", "r_b"], "r_w", ["p_w", "p_b"], replicates=R[R.variable != "r_b"])


def test_counts_gate():
    c = pd.DataFrame(dict(GEOID=GEO, d1=[30, 40, 50], d2=[60, 15, 90], n1=[1e4]*3, n2=[8e3]*3))
    out = d.disparity_measures(c, ["d1", "d2"], "d1", ["n1", "n2"], counts=True)
    v = out.set_index(["GEOID", "measure"]).validated
    assert v[("26001", "rd")] and v[("26001", "log_rr")] and not v[("26003", "rd")]
    assert not out[out.measure.isin(["idisp", "bgv", "theil", "mld"])].validated.any()
    with pytest.raises(ValueError, match="integer"):
        d.disparity_measures(c.assign(d1=[1.5, 2, 3]), ["d1", "d2"], "d1", ["n1", "n2"], counts=True)


def test_kitagawa_poisson_and_replicate():
    c = pd.DataFrame(dict(GEOID=["A", "B"], a=[50, 80], b=[40, 30], na=[1e4, 2e4], nb=[5e3, 4e3]))
    k = d.kitagawa_decomposition(c, "A", "B", ["a", "b"], ["na", "nb"], counts=True).set_index("component")
    assert k.loc["rate_effect", "estimate"]+k.loc["composition_effect", "estimate"] == pytest.approx(
        k.loc["crude_difference", "estimate"])
    assert k.validated.all()
    low = d.kitagawa_decomposition(c.assign(a=[5, 8], b=[4, 3]), "A", "B", ["a", "b"], ["na", "nb"], counts=True)
    assert not low.validated.any()
    with pytest.raises(ValueError, match="itself"):
        d.kitagawa_decomposition(c, "A", "A", ["a", "b"], ["na", "nb"], counts=True)


def _manifest():
    m = load_manifest(EXAMPLE)
    m["analyses"] = [dict(id="dp", method="disparity", groups=["income", "pop"], populations=["pop", "income"],
                          reference="income")]
    m["hypotheses"] = [dict(id="H1", analysis="dp", statistic="log_rr", geoid="26001000100", group="pop",
                            direction="greater", statement="s"),
                       dict(id="H2", analysis="dp", statistic="idisp", geoid="26001000100", null_value=50,
                            statement="s")]
    return m


def test_manifest_validation():
    m = _manifest()
    assert validate_manifest(m, resolve=False) == []
    bad = copy.deepcopy(m); bad["analyses"][0]["reference"] = "nope"
    assert any("reference must be one of the groups" in e for e in validate_manifest(bad, resolve=False))
    bad = copy.deepcopy(m); del bad["hypotheses"][1]["null_value"]
    assert any("positive null_value" in e for e in validate_manifest(bad, resolve=False))
    bad = copy.deepcopy(m); bad["hypotheses"][0]["group"] = "income"
    assert any("non-reference group" in e for e in validate_manifest(bad, resolve=False))
    bad = copy.deepcopy(m); bad["analyses"][0]["populations"] = ["pop", "income", "income2"]
    assert any("populations must" in e for e in validate_manifest(bad, resolve=False))
    k = load_manifest(EXAMPLE)
    k["analyses"] = [dict(id="kg", method="kitagawa", rates=["income", "pop"], populations=["pop", "income"],
                          areas=["26001000100", "26001000200"])]
    k["hypotheses"] = [dict(id="H1", analysis="kg", statistic="rate_effect", statement="s")]
    assert validate_manifest(k, resolve=False) == []
    k["analyses"][0]["areas"] = ["26001000100"]
    assert any("two distinct GEOID" in e for e in validate_manifest(k, resolve=False))


def test_runner_extractor_and_refusal():
    f, R = _acs(cv=(.05, .2, .4))
    a = dict(groups=["r_w", "r_b", "r_h"], populations=["p_w", "p_b", "p_h"], reference="r_w")
    res = mm._run_disparity(a, {}, f, .9, R, "holm", {})
    s = mm._stat_disparity(dict(statistic="rd", geoid="26001", group="r_b"), res)
    assert "confirmatory_refusal" not in s and s["ci_lower"] < s["estimate"] < s["ci_upper"]
    s = mm._stat_disparity(dict(statistic="log_rr", geoid="26001", group="r_h"), res)
    assert "exceeds the validated" in s["confirmatory_refusal"]
    s = mm._stat_disparity(dict(statistic="idisp", geoid="26001", null_value=50.0), res)
    assert s["test_estimate"] == pytest.approx(np.log(s["estimate"])-np.log(50)) and 0 <= s["p_two_sided"] <= 1
    rng = np.random.default_rng(3)
    est = np.array([[.1, .3, 100, 50], [.2, .4, 50, 50]])
    kf = pd.DataFrame(est, columns=["a", "b", "na", "nb"]).assign(GEOID=["A", "B"])
    kr = replicate_long(["A", "B"], ["a", "b", "na", "nb"], est, make_replicates(est, est*.1, rng))
    kres = mm._run_kitagawa(dict(rates=["a", "b"], populations=["na", "nb"], areas=["A", "B"]), {}, kf, .9, kr, "holm", {})
    s = mm._stat_kitagawa(dict(statistic="composition_effect"), kres)
    assert "confirmatory_refusal" not in s and np.isfinite(s["p_two_sided"])


def test_tool(tmp_path):
    from census import workflows_inference as wi
    f, R = _acs()
    f.to_csv(tmp_path/"f.csv", index=False); R.to_csv(tmp_path/"r.csv", index=False)
    out = wi.disparity_measures(str(tmp_path/"f.csv"), ["r_w", "r_b", "r_h"], ["p_w", "p_b", "p_h"], reference="r_w",
                                replicates_path=str(tmp_path/"r.csv"))
    assert out["success"] and "24 measure rows, 24 validated" in out["summary"]
    assert not wi.disparity_measures(str(tmp_path/"f.csv"), ["r_w", "r_b"], ["p_w", "p_b"])["success"]
    c = pd.DataFrame(dict(GEOID=["A", "B"], a=[50, 80], b=[40, 30], na=[1e4, 2e4], nb=[5e3, 4e3]))
    c.to_csv(tmp_path/"c.csv", index=False)
    k = wi.disparity_measures(str(tmp_path/"c.csv"), ["a", "b"], ["na", "nb"], counts=True, decompose_areas=["A", "B"])
    assert k["success"] and "rate effect" in k["summary"]
