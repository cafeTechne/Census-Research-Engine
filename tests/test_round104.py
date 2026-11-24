# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 104: exploratory-measure repairs (Part 1) and manifest support for validated methods (Part 2)."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from census import disease_mapping as dmap
from census import evidence as ev
from census import matching as mt
from census import repairs104_core as r104
from census.manifest import validate_manifest
from census.manifest.methods import METHODS, STATISTIC_EXTRACTORS

ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Part 1: Exploratory-measure repairs
# ---------------------------------------------------------------------------

def test_part1_audit_matches_engine_flags():
    audit = json.loads((ROOT / "docs/audits/repairs104_validation.json").read_text())
    out = audit["outcomes"]
    assert out["P2_all"] is True and out["R2_all"] is True and out["E2_all"] is True
    assert out["M1b_ATT"] is True and out["B3_E30"] is True
    assert out["M3_all"] is False and out["MD2_bc_all"] is False
    assert mt.VALIDATED["nn_ATT"] is out["M1b_ATT"]


def test_meta_repairs_validated_from_k10():
    rng = np.random.default_rng(1041)
    k = 12
    se = np.geomspace(0.05, 0.15, k)
    x = rng.standard_normal(k)
    y = 0.2 + 0.4 * x + rng.normal(0.0, np.sqrt(0.04 + se ** 2))
    res = ev.combine_estimates(y, se, moderators=x, small_study_test=True)
    assert res["pooled"]["prediction_interval_validated"] is True
    assert res["pooled"]["prediction_interval_method"] == "nnf"
    assert res["pooled"]["prediction_interval"][0] < res["pooled"]["lower"]
    assert res["pooled"]["prediction_interval"][1] > res["pooled"]["upper"]
    assert res["meta_regression"]["validated"] is True
    assert res["meta_regression"]["q_factor"] >= 1.0
    assert res["small_study_test"]["validated"] is True
    assert res["small_study_test"]["method"] == "egger_re"

    # Below k = 10, prediction interval stays exploratory
    res6 = ev.combine_estimates(y[:6], se[:6])
    assert res6["pooled"].get("prediction_interval_validated") is False


def test_matching_nn_att_validated_with_kish_t():
    rng = np.random.default_rng(1042)
    n = 145
    X = rng.standard_normal((n, 2))
    p = 1.0 / (1.0 + np.exp(-(1.2 * X[:, 0] + 0.8 * X[:, 1])))
    T = (rng.random(n) < p).astype(int)
    y = 1.0 + 0.5 * X[:, 0] + 1.5 * T + rng.standard_normal(n)
    df = pd.DataFrame({"GEOID": [f"{i:05d}" for i in range(n)], "y": y, "T": T, "x1": X[:, 0], "x2": X[:, 1]})
    out = mt.matching_effect(df, "y", "T", ["x1", "x2"], method="nn", estimand="ATT")
    assert out["validated"] is True
    assert out["effect"]["df_eff"] >= 2.0 and out["effect"]["lower"] < out["effect"]["estimate"] < out["effect"]["upper"]


def test_bym2_b3_validated_gate():
    k = 6; n = k * k
    edges = [(i, i + 1) for i in range(n) if (i + 1) % k] + [(i, i + k) for i in range(n - k)]
    rng = np.random.default_rng(1043)
    df_hi = pd.DataFrame({"GEOID": [f"{i:05d}" for i in range(n)],
                          "y": rng.poisson(35.0, n).astype(float), "E": np.full(n, 35.0)})
    r_hi = dmap.disease_map(df_hi, "y", "E", edges, method="B3")
    assert r_hi["validated"] is True and r_hi["audit"] == dmap.REPAIRS_AUDIT

    df_lo = pd.DataFrame({"GEOID": [f"{i:05d}" for i in range(n)],
                          "y": rng.poisson(5.0, n).astype(float), "E": np.full(n, 5.0)})
    r_lo = dmap.disease_map(df_lo, "y", "E", edges, method="B3")
    assert r_lo["validated"] is False


# ---------------------------------------------------------------------------
# Part 2: Manifest methods and opt-in validated args
# ---------------------------------------------------------------------------

def _base_manifest(analyses, hypotheses, extra=None):
    from census.manifest import load_manifest
    from tests.test_manifest import EXAMPLE
    m = load_manifest(EXAMPLE)
    m["geography"] = {"level": "county", "states": ["26"]}
    m["variables"] = [
        {"name": "y", "ref": "2019:B19013_001"},
        {"name": "trt", "ref": "2019:B17001_002"},
        {"name": "x1", "ref": "2019:B15003_022"},
        {"name": "x2", "ref": "2019:B23025_005"},
        {"name": "pop", "ref": "2019:B01003_001"},
    ]
    m.pop("derivations", None)
    m.pop("adjustments", None)
    m.pop("exclusions", None)
    m["analyses"] = analyses
    for h in hypotheses:
        h.setdefault("statement", "test hypothesis")
    m["hypotheses"] = hypotheses
    if extra:
        m.update(extra)
    return m


def _errs(m):
    return validate_manifest(m, resolve=False)


def test_manifest_methods_registered():
    for name in ("estimate_effect", "spatial_scan", "stratified"):
        assert name in METHODS
    for stat in ("effect", "primary_rr", "mh_rr", "mh_or", "mh_rd", "mh_irr", "reri", "homogeneity",
                 "marginal_rr", "marginal_rd", "attributable_fraction", "par", "par_pct", "who_sii"):
        assert stat in STATISTIC_EXTRACTORS


def test_estimate_effect_manifest_validation_and_runner():
    cq = {
        "eligibility": "Michigan counties", "intervention": "trt = 1", "comparator": "trt = 0",
        "time_zero": "2019", "outcome": "y", "follow_up": "cross-sectional",
        "contrast": "effect_in_treated", "target": "super_population",
    }
    dag = {"edges": ["x1 -> trt", "x1 -> y", "trt -> y", "trt -> x2", "y -> x2"], "treatment": "trt", "outcome": "y"}

    # Refused without causal_question in confirmatory manifest
    m_no_cq = _base_manifest(
        [{"id": "c1", "method": "estimate_effect", "kind": "matching", "outcome": "y",
          "treatment": "trt", "confounders": ["x1"], "args": {"method": "nn", "estimand": "ATT"}}],
        [{"id": "h1", "analysis": "c1", "statistic": "effect", "direction": "two-sided"}],
    )
    errs = _errs(m_no_cq)
    assert any("causal_question" in e for e in errs), errs

    # Refused when collider x2 is in confounders under DAG
    m_col = _base_manifest(
        [{"id": "c1", "method": "estimate_effect", "kind": "matching", "outcome": "y",
          "treatment": "trt", "confounders": ["x1", "x2"], "args": {"method": "nn", "estimand": "ATT"}}],
        [{"id": "h1", "analysis": "c1", "statistic": "effect", "direction": "two-sided"}],
        extra={"causal_question": cq, "dag": dag},
    )
    errs_col = _errs(m_col)
    assert any("DAG" in e or "collider" in e.lower() for e in errs_col), errs_col

    # Passes validation with valid adjustment set [x1]
    m_ok = _base_manifest(
        [{"id": "c1", "method": "estimate_effect", "kind": "matching", "outcome": "y",
          "treatment": "trt", "confounders": ["x1"], "args": {"method": "nn", "estimand": "ATT"}}],
        [{"id": "h1", "analysis": "c1", "statistic": "effect", "direction": "two-sided"}],
        extra={"causal_question": cq, "dag": dag},
    )
    assert _errs(m_ok) == []

    # Runner + extractor check on synthetic frame
    rng = np.random.default_rng(1044)
    n = 120; x1 = rng.standard_normal(n); trt = (rng.random(n) < 1 / (1 + np.exp(-0.5 * x1))).astype(int)
    y = 2.0 + 1.2 * trt + 0.7 * x1 + rng.standard_normal(n)
    df = pd.DataFrame({"GEOID": [f"26{i:03d}" for i in range(n)], "y": y, "trt": trt, "x1": x1})
    spec = METHODS["estimate_effect"]
    res = spec.run(m_ok["analyses"][0], m_ok["analyses"][0]["args"], df, 0.90, None, "holm", {})
    stat = STATISTIC_EXTRACTORS["effect"](m_ok["hypotheses"][0], res)
    assert "confirmatory_refusal" not in stat and stat["ci_lower"] < stat["estimate"] < stat["ci_upper"]


def test_spatial_scan_and_stratified_manifest_validation_and_runner():
    m_scan = _base_manifest(
        [{"id": "s1", "method": "spatial_scan", "cases": "trt", "population": "pop", "args": {"max_share": 0.5}}],
        [{"id": "h1", "analysis": "s1", "statistic": "primary_rr", "direction": "two-sided"}],
    )
    assert _errs(m_scan) == []

    m_scan_bad = _base_manifest(
        [{"id": "s1", "method": "spatial_scan", "cases": "trt", "population": "pop", "args": {"max_share": 0.3}}],
        [{"id": "h1", "analysis": "s1", "statistic": "primary_rr", "direction": "two-sided"}],
    )
    assert any("max_share=0.5" in e for e in _errs(m_scan_bad))

    m_strat = _base_manifest(
        [{"id": "st1", "method": "stratified", "stratum": "x1", "cases_exposed": "y",
          "total_exposed": "trt", "cases_unexposed": "x2", "total_unexposed": "pop"}],
        [{"id": "h1", "analysis": "st1", "statistic": "mh_rr", "direction": "two-sided"}],
    )
    assert _errs(m_strat) == []

    df_st = pd.DataFrame({"x1": ["a", "b"], "y": [40, 80], "trt": [200, 200], "x2": [25, 60], "pop": [200, 200]})
    res = METHODS["stratified"].run(m_strat["analyses"][0], {}, df_st, 0.90, None, "holm", {})
    st_out = STATISTIC_EXTRACTORS["mh_rr"](m_strat["hypotheses"][0], res)
    assert st_out["estimate"] > 1.0 and "confirmatory_refusal" not in st_out


def test_fit_replicate_impute_and_marginal_in_manifest():
    m_imp = _base_manifest(
        [{"id": "m1", "method": "fit_replicate", "formula": "y ~ x1 + x2",
          "args": {"impute": ["x1", "x2"], "impute_method": "pmm"}}],
        [{"id": "h1", "analysis": "m1", "statistic": "coefficient", "term": "x1", "direction": "two-sided"}],
    )
    assert _errs(m_imp) == []
    rng = np.random.default_rng(1045)
    n = 100; x1 = rng.standard_normal(n); x2 = 0.4 * x1 + rng.standard_normal(n)
    y = 1.0 + 0.9 * x1 - 0.5 * x2 + rng.standard_normal(n)
    df = pd.DataFrame({"GEOID": [f"26{i:03d}" for i in range(n)], "y": y, "x1": x1, "x2": x2})
    df.loc[:10, "x1"] = np.nan; df.loc[11:20, "x2"] = np.nan
    res = METHODS["fit_replicate"].run(m_imp["analyses"][0], dict(m_imp["analyses"][0]["args"]),
                                       df, 0.90, None, "holm", {"held_external": []})
    assert "fcs_imputation" in res.diagnostics and res.diagnostics["fcs_imputation"]["validated"] is True

    m_marg = _base_manifest(
        [{"id": "m2", "method": "fit_replicate", "formula": "y ~ x1",
          "args": {"model": "binomial", "trials": "pop", "scale": "robust",
                   "marginal": {"exposure": "x1", "contrast": [0.0, 1.0]}}}],
        [{"id": "h2", "analysis": "m2", "statistic": "marginal_rr", "direction": "two-sided"}],
    )
    assert _errs(m_marg) == []
