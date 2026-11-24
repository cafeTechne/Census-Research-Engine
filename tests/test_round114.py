# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 114 tests: final 4 manifest methods (difference_in_differences, interrupted_series, combine_estimates, bias_analysis)."""
import copy

import numpy as np
import pandas as pd

from census.manifest import load_manifest, validate_manifest
from census.manifest.methods import (
    METHODS,
    _run_bias_analysis,
    _run_combine_estimates,
    _run_did,
    _run_its,
    _stat_bias_analysis,
    _stat_combine_estimates,
    _stat_did,
    _stat_its,
)
from tests.test_manifest import EXAMPLE


def test_28_manifest_methods_registered():
    for m in ("difference_in_differences", "interrupted_series", "combine_estimates", "bias_analysis"):
        assert m in METHODS
    assert len(METHODS) == 28


def test_manifest_schema_checks_for_new_methods():
    # difference_in_differences (MSM confirmatory refuses ipw, accepts gformula)
    m = copy.deepcopy(load_manifest(EXAMPLE))
    m["analyses"] = [{"id": "d1", "method": "difference_in_differences", "outcome": "income",
                      "args": {"design": "msm", "method": "gformula"}}]
    m["hypotheses"] = [{"id": "h1", "analysis": "d1", "statistic": "did_effect", "direction": "two-sided"}]
    assert validate_manifest(m, resolve=False) == []
    m_bad = copy.deepcopy(m)
    m_bad["analyses"][0]["args"]["method"] = "ipw"
    assert any("gformula" in e for e in validate_manifest(m_bad, resolve=False))

    # interrupted_series
    m2 = copy.deepcopy(load_manifest(EXAMPLE))
    m2["analyses"] = [{"id": "i1", "method": "interrupted_series", "outcome": "income", "year": "pop",
                       "interruption_year": 2015}]
    m2["hypotheses"] = [{"id": "h1", "analysis": "i1", "statistic": "its_level", "direction": "two-sided"}]
    assert validate_manifest(m2, resolve=False) == []

    # combine_estimates
    m3 = copy.deepcopy(load_manifest(EXAMPLE))
    m3["analyses"] = [{"id": "c1", "method": "combine_estimates", "estimate": "income", "se": "pop"}]
    m3["hypotheses"] = [{"id": "h1", "analysis": "c1", "statistic": "pooled_effect", "direction": "two-sided"}]
    assert validate_manifest(m3, resolve=False) == []

    # bias_analysis
    m4 = copy.deepcopy(load_manifest(EXAMPLE))
    m4["analyses"] = [{"id": "b1", "method": "bias_analysis", "kind": "e_value", "args": {"estimate": 2.0}}]
    m4["hypotheses"] = [{"id": "h1", "analysis": "b1", "statistic": "e_value", "direction": "two-sided"}]
    assert validate_manifest(m4, resolve=False) == []


def test_runners_and_extractors_for_new_methods():
    rng = np.random.default_rng(11401)
    # 1. difference_in_differences (MSM gformula)
    rows = []
    for u in range(36):
        l = rng.normal(0, 1)
        g = np.nan if u < 18 else 2015
        for yr in range(2011, 2019):
            a_prev = 1 if (not np.isnan(g) and yr > g) else 0
            l = 0.5 * l + 0.3 * a_prev + rng.normal(0, 0.7)
            a_cur = 1 if (not np.isnan(g) and yr >= g) else 0
            rows.append({"GEOID": f"{u+1:02d}", "Year": yr, "g": g, "l": l, "y": 10.0 - 1.5 * a_cur + 0.7 * l + rng.normal(0, 0.5)})
    rd = _run_did({"outcome": "y", "first_treated": "g"},
                  {"design": "msm", "method": "gformula", "time_varying_confounders": ["l"], "product": "annual"},
                  pd.DataFrame(rows), 0.90, None, None, {})
    sd = _stat_did({"statistic": "did_effect", "duration": 1}, rd)
    assert "confirmatory_refusal" not in sd and sd["ci_lower"] < sd["estimate"] < sd["ci_upper"]

    # 2. interrupted_series (20 annual points)
    yrs = list(range(2001, 2021))
    vals = [10.0 + 0.1 * i - (2.0 if y >= 2012 else 0.0) + float(rng.normal(0, 0.2)) for i, y in enumerate(yrs)]
    ri = _run_its({"outcome": "v", "year": "yr", "interruption_year": 2012}, {"method": "bootstrap_t_cons"},
                  pd.DataFrame({"yr": yrs, "v": vals}), 0.90, None, None, {})
    si = _stat_its({"statistic": "its_level"}, ri)
    assert "confirmatory_refusal" not in si and si["ci_lower"] < si["estimate"] < si["ci_upper"]

    # 3. combine_estimates (k = 10: all 4 statistics validated simultaneously)
    df_m = pd.DataFrame({"est": rng.normal(0.5, 0.2, 10), "se": rng.uniform(0.08, 0.15, 10), "x": np.linspace(-1, 1, 10)})
    rc = _run_combine_estimates({"estimate": "est", "se": "se"}, {"moderator": "x", "small_study_test": True},
                                df_m, 0.90, None, None, {})
    for st_name in ("pooled_effect", "prediction_interval", "meta_regression", "egger_test"):
        sc = _stat_combine_estimates({"statistic": st_name}, rc)
        assert "confirmatory_refusal" not in sc

    # 4. bias_analysis (e_value + probabilistic misclassification)
    rb1 = _run_bias_analysis({"kind": "e_value"}, {"estimate": 2.0, "lower": 1.4, "upper": 2.8}, None, 0.90, None, None, {})
    sb1 = _stat_bias_analysis({"statistic": "e_value"}, rb1)
    assert sb1["estimate"] > 3.0
    rb2 = _run_bias_analysis({"kind": "misclassification"},
                             {"table": [80, 120, 40, 160], "sensitivity": 0.88, "specificity": 0.92, "prior_sd": 0.03},
                             None, 0.90, None, None, {})
    sb2 = _stat_bias_analysis({"statistic": "corrected_rr"}, rb2)
    assert "confirmatory_refusal" not in sb2 and sb2["ci_lower"] < sb2["estimate"] < sb2["ci_upper"]
