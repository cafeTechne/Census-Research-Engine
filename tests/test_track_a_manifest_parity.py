# SPDX-License-Identifier: AGPL-3.0-or-later
"""Track A regression tests: end-to-end verification of the 9 remaining manifest methods."""
import numpy as np
import pandas as pd

from census.manifest import methods as M


def test_track_a_did_two_group_extracts_effect():
    rng = np.random.default_rng(121)
    rows = []
    for u in range(40):
        tr = 1 if u < 20 else 0
        for yr in (2019, 2024):
            y = 10.0 + 2.0 * tr + (1.5 if yr == 2024 else 0.0) + (3.0 if (tr and yr == 2024) else 0.0) + rng.normal(0, 0.5)
            rows.append({"GEOID": f"26{u:03d}", "Year": yr, "tr": tr, "y": y})
    rd = M._run_did({"outcome": "y", "treated": "tr", "treatment_period": 2024}, {"design": "two_group"},
                    pd.DataFrame(rows), 0.90, None, "holm", {})
    st = M._stat_did({"statistic": "did_effect", "null_value": 0.0}, rd)
    assert np.isfinite(st["estimate"]) and abs(st["estimate"] - 3.0) < 0.6
    assert np.isfinite(st["se"]) and st["se"] > 0
    assert st["ci_lower"] < st["estimate"] < st["ci_upper"]
    assert st["p_two_sided"] < 0.01
    assert "confirmatory_refusal" not in st


def test_track_a_stratified_homogeneity_and_mh_measures():
    df = pd.DataFrame({
        "stratum": ["A", "B", "C"],
        "ce": [30, 40, 35], "te": [200, 250, 220],
        "cu": [15, 20, 18], "tu": [200, 250, 220],
    })
    rs = M._run_stratified(
        {"stratum": "stratum", "cases_exposed": "ce", "total_exposed": "te",
         "cases_unexposed": "cu", "total_unexposed": "tu"},
        {}, df, 0.90, None, "holm", {},
    )
    hom = M._stat_stratified({"statistic": "homogeneity"}, rs)
    assert np.isfinite(hom["estimate"]) and 0.0 <= hom["p_two_sided"] <= 1.0
    assert "confirmatory_refusal" not in hom
    for s in ("mh_rr", "mh_or", "mh_rd"):
        out = M._stat_stratified({"statistic": s}, rs)
        assert np.isfinite(out["estimate"]) and out["ci_lower"] < out["ci_upper"]
        assert "confirmatory_refusal" not in out


def test_track_a_remaining_methods_smoke_end_to_end():
    rng = np.random.default_rng(122)

    # combine_estimates (k=6 validated pooled_effect + k=12 PI/meta-reg/Egger)
    df_k6 = pd.DataFrame({"est": [0.45, 0.52, 0.48, 0.55, 0.50, 0.49], "se": [0.05] * 6})
    rc6 = M._run_combine_estimates({"estimate": "est", "se": "se"}, {}, df_k6, 0.90, None, "holm", {})
    sp6 = M._stat_combine_estimates({"statistic": "pooled_effect"}, rc6)
    assert np.isfinite(sp6["estimate"]) and "confirmatory_refusal" not in sp6

    # bias_analysis (e_value + probabilistic misclassification)
    re = M._run_bias_analysis({"kind": "e_value"}, {"estimate": 2.1, "lower": 1.5, "upper": 2.9},
                              pd.DataFrame(), 0.90, None, "holm", {})
    assert M._stat_bias_analysis({"statistic": "e_value"}, re)["estimate"] > 3.0
    rm = M._run_bias_analysis({"kind": "misclassification"},
                              {"table": [40, 20, 60, 80], "sensitivity": 0.85, "specificity": 0.90, "prior_sd": 0.03},
                              pd.DataFrame(), 0.90, None, "holm", {})
    sm = M._stat_bias_analysis({"statistic": "corrected_rr"}, rm)
    assert np.isfinite(sm["estimate"]) and "confirmatory_refusal" not in sm

    # interrupted_series (20 annual points)
    df_i = pd.DataFrame({
        "year": list(range(2005, 2025)),
        "y": np.linspace(10, 15, 20) + np.where(np.arange(20) >= 10, 2.0, 0.0) + rng.normal(0, 0.25, 20),
    })
    ri = M._run_its({"outcome": "y", "year": "year", "interruption_year": 2015}, {}, df_i, 0.90, None, "holm", {})
    si = M._stat_its({"statistic": "its_level"}, ri)
    assert np.isfinite(si["estimate"]) and "confirmatory_refusal" not in si

    # joinpoint (20 annual points, 500 events/yr)
    df_j = pd.DataFrame({"year": list(range(2005, 2025)), "cnt": rng.poisson(500, 20), "pop": np.full(20, 100000.0)})
    rj = M._run_joinpoint({"year": "year", "counts": "cnt", "population": "pop"},
                          {"max_joinpoints": 1, "permutations": 99, "bootstrap": 60}, df_j, 0.90, None, "holm", {})
    sj = M._stat_joinpoint({"statistic": "aapc"}, rj)
    assert np.isfinite(sj["estimate"]) and "confirmatory_refusal" not in sj

    # demography (Chiang II life table >= 50,000 person-years)
    df_dm = pd.DataFrame({
        "age": [0, 1, 5, 15, 25, 35, 45, 55, 65, 75, 85],
        "d": [50, 10, 15, 40, 80, 120, 250, 600, 1200, 2200, 3500],
        "p": [10000, 40000, 100000, 100000, 100000, 100000, 100000, 90000, 70000, 40000, 15000],
    })
    rdm = M._run_demography({"age_start": "age", "deaths": "d", "population": "p"}, {}, df_dm, 0.90, None, "holm", {})
    sdm = M._stat_demography({"statistic": "e0"}, rdm)
    assert 70 < sdm["estimate"] < 85 and "confirmatory_refusal" not in sdm

    # estimate_effect (treatment AIPW)
    n = 160
    x1 = rng.normal(0, 1, n)
    tr = (rng.uniform(0, 1, n) < 1 / (1 + np.exp(-0.5 * x1))).astype(int)
    y = 2.0 + 1.5 * tr + 0.8 * x1 + rng.normal(0, 0.5, n)
    df_e = pd.DataFrame({"GEOID": [f"26{i:03d}" for i in range(n)], "y": y, "tr": tr, "x1": x1})
    ree = M._run_estimate_effect({"kind": "treatment", "outcome": "y", "treatment": "tr", "confounders": ["x1"]},
                                 {"method": "aipw"}, df_e, 0.90, None, "holm", {})
    see = M._stat_estimate_effect({"statistic": "effect"}, ree)
    assert abs(see["estimate"] - 1.5) < 0.4 and "confirmatory_refusal" not in see
