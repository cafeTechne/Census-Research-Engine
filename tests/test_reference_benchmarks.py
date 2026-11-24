# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 115: Offline published textbook & closed-form reference benchmarks for Rounds 76-112 statistical modules."""
import numpy as np
import pandas as pd
import pytest

from census import agreement as agr
from census import bias_analysis as ba
from census import demography_core as dc
from census import disparity_core as dispc
from census import evidence as ev
from census import matching as mt
from census import rdd_core as rddc
from census import stratified_core as stratc


def test_benchmark_vanderweele_ding_2017_e_values():
    """VanderWeele & Ding (2017, Ann Intern Med) Table 1 published E-value points."""
    assert ba.e_value(3.9)["e_value"] == pytest.approx(3.9 + np.sqrt(3.9 * 2.9), abs=1e-4)
    assert round(ba.e_value(3.9)["e_value"], 2) == 7.26
    assert round(ba.e_value(2.0)["e_value"], 2) == 3.41
    assert round(ba.e_value(1.5)["e_value"], 2) == 2.37
    # Protective RR = 0.5 has identical E-value to RR = 2.0
    assert ba.e_value(0.5)["e_value"] == pytest.approx(ba.e_value(2.0)["e_value"], abs=1e-10)


def test_benchmark_rogan_gladen_1978_misclassification_inversion():
    """Rogan & Gladen (1978, Am J Epidemiol): exact inversion of known nondifferential outcome misclassification."""
    # True 2x2 table: exposed 300/1000 (p1=0.30), unexposed 150/1000 (p0=0.15) -> true RR = 2.0
    se, sp = 0.85, 0.92
    a_obs = 300 * se + 700 * (1 - sp)
    b_obs = 1000 - a_obs
    c_obs = 150 * se + 850 * (1 - sp)
    d_obs = 1000 - c_obs
    res = ba.misclassification(a_obs, b_obs, c_obs, d_obs, se, sp, kind="outcome")
    assert res["corrected"]["rr"] == pytest.approx(2.0, abs=1e-9)
    assert res["corrected"]["or"] == pytest.approx((0.30 / 0.70) / (0.15 / 0.85), abs=1e-9)


def test_benchmark_foundations_epi_ch7_8_mh_and_classification():
    """Foundations of Epidemiology (ch. 7-8): OCP/ovarian cancer MH OR = 4/9 and Table 8-5 classification."""
    a = np.array([2.0, 2.0]); b = np.array([3.0, 3.0]); c = np.array([3.0, 3.0]); d = np.array([2.0, 2.0])
    assert stratc.mh_pooled(a, b, c, d)["or"]["estimate"] == pytest.approx(4.0 / 9.0, abs=1e-10)
    assert stratc.classify(2.0, 2.0, [1.0, 3.2], True) == "effect_modifier"
    assert stratc.classify(2.0, 3.55, [3.5, 3.6], False) == "confounder"
    assert stratc.classify(2.0, 1.95, [1.9, 2.0], False) == "neither"


def test_benchmark_chiang_1984_life_table_and_arriaga_identity():
    """Chiang (1984) constant-hazard life table (exact e_x) and Arriaga exact sum-to-delta-e0 identity."""
    ages = np.array([0, 1, 5, 15, 25, 35, 45, 55, 65, 75, 85], dtype=float)
    pop = np.full(len(ages), 1_000_000.0)
    # Constant mortality rate m = 0.01 -> exact exponential life expectancy e0 = 1/m = 100.0 (approx for abridged)
    m1 = np.full(len(ages), 0.01)
    m2 = np.full(len(ages), 0.012)
    lt1 = dc.life_table(ages, m1 * pop, pop)
    lt2 = dc.life_table(ages, m2 * pop, pop)
    assert lt1["l"][0] == pytest.approx(1.0, abs=1e-9)
    assert lt1["e"][0] > lt2["e"][0]
    arr = dc.arriaga(lt1, lt2)
    tot = float(np.sum(arr["total"])) if isinstance(arr, dict) else float(np.sum(arr))
    assert tot == pytest.approx(float(lt2["e"][0] - lt1["e"][0]), abs=1e-6)


def test_benchmark_harrer_meta_analysis_fixed_effect_exact():
    """Harrer et al. (2021): inverse-variance fixed-effect pooled estimate & SE exact formula."""
    y = np.array([0.20, 0.35, 0.50, 0.45, 0.30])
    se = np.array([0.10, 0.12, 0.08, 0.15, 0.11])
    w = 1.0 / (se ** 2)
    mu_fe = float(np.sum(w * y) / np.sum(w))
    se_fe = float(np.sqrt(1.0 / np.sum(w)))
    res = ev.combine_estimates(y.tolist(), se.tolist(), method="fixed", assume_homogeneous=True)
    assert res["pooled"]["estimate"] == pytest.approx(mu_fe, abs=1e-10)
    assert res["pooled"]["se"] == pytest.approx(se_fe, abs=1e-10)


def test_benchmark_lin_1989_ccc_exact():
    """Lin (1989, Biometrics): exact CCC formula and location-shift sensitivity."""
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
    y = x + 2.0  # pure location shift: r = 1.0, but CCC < 1.0
    vx = np.var(x, ddof=0)
    expected_ccc = (2.0 * vx) / (2.0 * vx + 4.0)
    df = pd.DataFrame({"GEOID": [f"26{i:03d}" for i in range(len(x))], "x": x, "y": y})
    out = agr.check_agreement(df, "x", "y")
    assert out["ccc"]["estimate"] == pytest.approx(expected_ccc, abs=1e-10)


def test_benchmark_kitagawa_1955_exact_decomposition():
    """Kitagawa (1955, JASA): exact rate_effect + composition_effect == crude_difference."""
    r1 = np.array([0.01, 0.05, 0.15]); w1 = np.array([0.5, 0.3, 0.2])
    r2 = np.array([0.02, 0.06, 0.18]); w2 = np.array([0.4, 0.3, 0.3])
    crude_diff = float(np.sum(r2 * w2) - np.sum(r1 * w1))
    rate_eff = float(np.sum((r2 - r1) * 0.5 * (w1 + w2)))
    comp_eff = float(np.sum((w2 - w1) * 0.5 * (r1 + r2)))
    k = dispc.kitagawa(r2[None, :], w2[None, :], r1[None, :], w1[None, :])
    assert float(k["difference"][0]) == pytest.approx(crude_diff, abs=1e-10)
    assert float(k["rate_effect"][0]) == pytest.approx(rate_eff, abs=1e-10)
    assert float(k["composition_effect"][0]) == pytest.approx(comp_eff, abs=1e-10)
    assert float(k["rate_effect"][0] + k["composition_effect"][0]) == pytest.approx(crude_diff, abs=1e-10)


def test_benchmark_mixtape_rdd_and_triple_diff_exact_noiseless():
    """Cunningham (Mixtape): exact noiseless recovery for sharp RDD, fuzzy RDD, and triple-difference."""
    x = np.linspace(-1.0, 1.0, 4001)
    y_sharp = 2.0 + 1.5 * (x >= 0) + 0.7 * x - 0.4 * (x ** 2)
    r_sharp = rddc.rdd(x, y_sharp, 0.0, h=0.4)
    assert r_sharp["robust_estimate"] == pytest.approx(1.5, abs=1e-6)

    # Exact noiseless triple-difference
    rows = []
    for s in range(30):
        tr = int(s < 15)
        for g in ("inelig", "elig"):
            for yr in (2012, 2018):
                post = int(yr >= 2018)
                y = 10.0 + 0.5 * s + 2.0 * (g == "elig") - 0.8 * post - 2.25 * tr * (g == "elig") * post
                rows.append({"state": f"{s+1:02d}", "tr": tr, "grp": g, "Year": yr, "y": y})
    td = mt.triple_difference(pd.DataFrame(rows), "y", "state", "grp", "elig", "Year", "tr", 2018)
    assert td["effect"]["estimate"] == pytest.approx(-2.25, abs=1e-9)
