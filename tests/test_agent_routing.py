# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 64: the agent routing contract in docs/agent_routing.md, run on offline fixtures."""
import asyncio
import re
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd
import pytest

import mcp_server
from census import mcp_profiles as mp, workflows_inference as wi

ROOT = Path(__file__).resolve().parents[1]
ROWS = {}
for line in (ROOT/"docs/agent_routing.md").read_text().splitlines():
    m = re.match(r"\| (R\d+) \| .*? \| (core|full) \| `(\w+)[^|]*\| ([^|]+) \| (\w+) \|$", line)
    if m:
        ROWS[m.group(1)] = dict(profile=m.group(2), tool=m.group(3), expected=m.group(4).strip(), guidance=m.group(5))
REGISTERED = {t.name for t in asyncio.run(mcp_server.mcp.list_tools())}


def _frame(tmp_path):
    from tests.test_round58 import frame
    f, coords = frame()
    f["p"] = 1/(1+np.exp(-f.x)); f["T"] = 200.
    p = tmp_path/"f.csv"; f.to_csv(p, index=False)
    return str(p), f, coords


def _scpc(tmp_path, **kw):
    p, _, coords = _frame(tmp_path)
    with mock.patch("census.small_spatial.frame_coordinates", return_value=coords):
        return wi.fit_model(p, **kw)


def _censored(tmp_path):
    rng = np.random.default_rng(64)
    n = 300; x = rng.normal(size=n); E = rng.uniform(50, 500, n)
    mu = E*np.exp(-3+.4*x); y = rng.negative_binomial(5, 5/(5+mu)).astype(float)
    hid = (y >= 1) & (y <= 9)
    p = tmp_path/"c.csv"; pd.DataFrame(dict(y=np.where(hid, np.nan, y), x=x, E=E, hid=hid)).to_csv(p, index=False)
    return str(p)


def _eiv(p, method):
    from census import spatial_eiv
    from tests.test_round46 import several
    f, long, coords, rhs = several(p)
    return spatial_eiv.fit_spatial_eiv(f"y ~ {rhs}", f, long, method=method, coords=coords, fixed_variables=("y",))


def _series(n):
    rng = np.random.default_rng(7)
    k = n//2
    return list(np.r_[np.zeros(k), np.ones(n-k)]+.05*np.arange(n)+rng.normal(size=n)*.4), list(range(2023-n, 2023)), 2023-n+k


def _ineq(measure):
    from census import pums_inequality as pq
    from tests.test_round56 import frame
    t = pq.pums_inequality(frame(n=3000)[0], "PINCP")["table"].set_index("measure")
    return dict(success=True, validated=bool(t.loc[measure, "validated"]))


def _who(tmp_path, measure):
    rng = np.random.default_rng(103)
    geoids = ["26001", "26003", "26005"]
    df = pd.DataFrame({
        "GEOID": geoids,
        "g1": [0.10, 0.12, 0.09], "g2": [0.20, 0.22, 0.18], "g3": [0.30, 0.28, 0.25],
        "p1": [10000., 12000., 9000.], "p2": [5000., 6000., 4000.], "p3": [4000., 3500., 3000.],
    })
    rep_rows = []
    for g_col in ("g1", "g2", "g3"):
        for i, gid in enumerate(geoids):
            base = float(df.loc[i, g_col])
            row = {"GEOID": gid, "variable": g_col}
            for r in range(1, 81):
                row[f"rep_{r}"] = base * (1.0 + 0.05 * rng.standard_normal())
            rep_rows.append(row)
    fp = tmp_path / "who.csv"; rp = tmp_path / "who_reps.parquet"
    df.to_csv(fp, index=False); pd.DataFrame(rep_rows).to_parquet(rp, index=False)
    out = wi.disparity_measures(str(fp), ["g1", "g2", "g3"], ["p1", "p2", "p3"],
                                reference="g1", replicates_path=str(rp), who_measures=True)
    rows = [x for x in out["rows"] if x["measure"] == measure]
    return dict(success=out["success"], validated=all(x["validated"] for x in rows))


def _joinpoint_ears():
    rng = np.random.default_rng(1031)
    yrs = list(range(2004, 2024))
    pop = [100000.0] * len(yrs)
    cnt = [float(rng.poisson(200)) for _ in yrs]
    out = wi.joinpoint(years=yrs, counts=cnt, population=pop, aberration="ears_c2")
    return dict(success=out["success"],
                validated=bool(out["validated"]["selection"] and out["aberration"]["validated"]))


def _staggered(tmp_path):
    from census import workflows_microdata as wm
    rng = np.random.default_rng(1032)
    rows = []
    for u in range(30):
        g = 0 if u < 12 else (2014 if u < 21 else 2017)
        ui = rng.normal(0, 1)
        for yr in range(2010, 2020):
            tr = 1.0 if (g > 0 and yr >= g) else 0.0
            rows.append({"GEOID": f"{u+1:02d}", "Year": yr, "first_treated": g,
                         "y": 10.0 + ui + 0.1 * (yr - 2010) - 1.5 * tr + rng.normal(0, 0.3), "y_se": 0.2})
    p = tmp_path / "stag.csv"; pd.DataFrame(rows).to_csv(p, index=False)
    out = wm.difference_in_differences(str(p), outcome="y", treated="first_treated", period="Year",
                                       unit="GEOID", design="staggered", first_treated="first_treated",
                                       se="y_se", product="1-year")
    return dict(success=out["success"], validated=bool(out["validated"]))


def _msm(tmp_path, method="sun_abraham"):
    from census import workflows_microdata as wm
    rng = np.random.default_rng(1033)
    rows = []
    for u in range(40):
        l_prev = rng.normal(0, 1); g = np.nan if u < 20 else (2015 if u < 30 else 2017)
        for yr in range(2012, 2020):
            a_prev = 1 if (not np.isnan(g) and yr > g) else 0
            l_cur = 0.5 * l_prev + 0.3 * a_prev + rng.normal(0, 0.8)
            a_cur = 1 if (not np.isnan(g) and yr >= g) else 0
            y = 10.0 - 1.2 * a_cur + 0.8 * l_cur + rng.normal(0, 0.5)
            rows.append({"GEOID": f"{u+1:02d}", "Year": yr, "first_treated": g, "l": l_cur, "y": y})
            l_prev = l_cur
    p = tmp_path / "msm.csv"; pd.DataFrame(rows).to_csv(p, index=False)
    out = wm.difference_in_differences(str(p), outcome="y", treated="first_treated", period="Year", unit="GEOID",
                                       design="msm", first_treated="first_treated", method=method,
                                       time_varying_confounders=["l"], product="1-year")
    return dict(success=out["success"], validated=bool(out["validated"]))


def _triple(tmp_path):
    from census import workflows_microdata as wm
    rng = np.random.default_rng(1034)
    rows = []
    for s in range(30):
        tr = int(s < 15); se_s = rng.normal(0, 0.5)
        for g in ("inelig", "elig"):
            for yr in (2012, 2018):
                post = int(yr >= 2018)
                y = 10.0 + se_s + 2.0 * (g == "elig") - 0.5 * post - 1.5 * tr * (g == "elig") * post + rng.normal(0, 0.4)
                rows.append({"state": f"{s+1:02d}", "tr": tr, "grp": g, "Year": yr, "y": y})
    p = tmp_path / "ddd.csv"; pd.DataFrame(rows).to_csv(p, index=False)
    out = wm.difference_in_differences(str(p), outcome="y", treated="tr", treatment_period=2018, period="Year",
                                       unit="state", design="triple", group="grp", affected_group="elig")
    return dict(success=out["success"], validated=bool(out["validated"]))


def _stratified(tmp_path):
    from census import workflows_microdata as wm
    df = pd.DataFrame({
        "stratum": ["young", "old"],
        "ce": [40, 80], "te": [200, 200], "cu": [25, 60], "tu": [200, 200],
    })
    p = tmp_path / "strat.csv"; df.to_csv(p, index=False)
    out = wm.stratified_analysis(str(p), stratum="stratum", cases_exposed="ce", total_exposed="te",
                                 cases_unexposed="cu", total_unexposed="tu")
    return dict(success=out["success"], validated=bool(out["validated"]))


def _designation(tmp_path):
    rng = np.random.default_rng(1035)
    n = 40; true_p = rng.uniform(0.08, 0.32, n); se = np.full(n, 0.03)
    obs = np.clip(true_p + rng.normal(0, se), 0.01, 0.99)
    p = tmp_path / "des.csv"
    pd.DataFrame({"GEOID": [f"26{i:03d}" for i in range(n)], "pov": obs, "pov_se": se}).to_csv(p, index=False)
    out = wi.designation_accuracy(str(p), "pov", 0.20, se_col="pov_se")
    return dict(success=out["success"], validated=bool(out["validated"]["q1_fh"]))


def _causal_frame(tmp_path):
    rng = np.random.default_rng(1036)
    n = 150; x = rng.normal(size=n); z = rng.normal(size=n)
    pr = 1.0 / (1.0 + np.exp(-(0.5 * x + 0.3 * z)))
    a = (rng.random(n) < pr).astype(int)
    y = 2.0 + 1.5 * a + 0.8 * x - 0.5 * z + rng.normal(0, 1.0, n)
    p = tmp_path / "causal.csv"
    pd.DataFrame({"GEOID": [f"26{i:03d}" for i in range(n)], "y": y, "a": a, "x": x, "z": z}).to_csv(p, index=False)
    return str(p)


def _rdd(tmp_path):
    from census import workflows_microdata as wm
    rng = np.random.default_rng(1037)
    n = 1200; age = rng.integers(55, 76, n)
    y = (0.7 + 0.12 * (age >= 65) + 0.005 * (age - 65) + rng.normal(0, 0.15, n))
    df = pd.DataFrame({"AGEP": age, "y": y, "PWGTP": 10.0})
    for i in range(1, 81):
        df[f"PWGTP{i}"] = 10.0 * (1.0 + 0.2 * rng.standard_normal(n))
    p = tmp_path / "rdd.parquet"; df.to_parquet(p, index=False)
    out = wm.regression_discontinuity(str(p), outcome="y", running="AGEP", cutoff=65,
                                      weight="PWGTP", replicate_prefix="PWGTP")
    return dict(success=out["success"], validated=bool(out["validated"]))


def _disease_map(tmp_path, method=None, exp_low=15.0, exp_high=40.0):
    import geopandas as gpd
    from shapely.geometry import box
    from census import workflows_geo as wg
    rng = np.random.default_rng(1038)
    rows = []
    for r in range(5):
        for c in range(5):
            idx = r * 5 + c
            exp = float(rng.uniform(exp_low, exp_high))
            obs = float(rng.poisson(exp * (1.2 if r < 2 else 0.9)))
            rows.append({"GEOID": f"26{idx:03d}", "deaths": obs, "expected": exp,
                         "geometry": box(c * 10000, r * 10000, (c + 1) * 10000, (r + 1) * 10000)})
    gdf = gpd.GeoDataFrame(rows, crs="EPSG:5070")
    p = tmp_path / f"dm_{method or 'default'}.csv"; pd.DataFrame(gdf.drop(columns="geometry")).to_csv(p, index=False)
    kw = {"method": method} if method is not None else {}
    with mock.patch("census.workflows_geo._with_boundaries", return_value=gdf):
        out = wg.spatial_model(str(p), "disease_map", "county", 2022, outcome="deaths", expected="expected", **kw)
    return dict(success=out["success"], validated=bool(out["validated"]))


def _meta_k12():
    rng = np.random.default_rng(1071)
    est = rng.normal(0.5, 0.25, 12).tolist()
    se = rng.uniform(0.08, 0.16, 12).tolist()
    mod = np.linspace(-1, 1, 12).tolist()
    out = wi.combine_estimates("pool", estimates=est, ses=se, moderators=mod, small_study_test=True)
    pi_ok = bool(out.get("pooled", {}).get("prediction_interval_validated") or
                 out.get("heterogeneity", {}).get("prediction_interval_validated"))
    v = (pi_ok and out.get("meta_regression", {}).get("validated") and
         out.get("small_study_test", {}).get("validated"))
    return dict(success=out["success"], validated=bool(v))


def _rdd_continuous(tmp_path):
    from census import workflows_microdata as wm
    rng = np.random.default_rng(1072)
    n = 1500
    x = rng.uniform(-1, 1, n)
    y = 1.0 + 0.8 * (x >= 0) + 0.5 * x - 0.3 * x ** 2 + rng.normal(0, 0.5, n)
    p = tmp_path / "rdd_cont.csv"
    pd.DataFrame({"x": x, "y": y}).to_csv(p, index=False)
    out = wm.regression_discontinuity(str(p), outcome="y", running="x", cutoff=0.0)
    return dict(success=out["success"], validated=bool(out["validated"]))


def _prob_misclass():
    out = wi.bias_analysis("misclassification", table=[80, 120, 40, 160], sensitivity=0.88, specificity=0.92,
                           misclassified="outcome", prior_sd=0.03)
    return dict(success=out["success"], validated=bool(out.get("probabilistic", {}).get("validated", out.get("validated"))))


def _agreement_ccc(tmp_path):
    rng = np.random.default_rng(1073)
    n = 60
    x = rng.normal(10.0, 2.0, n)
    y = x + rng.normal(0.1, 0.5, n)
    p = tmp_path / "agree.csv"
    pd.DataFrame({"GEOID": [f"26{i:03d}" for i in range(n)], "a": x, "b": y}).to_csv(p, index=False)
    out = wi.check_agreement(str(p), "a", "b")
    return dict(success=out["success"], validated=bool(out["ccc"]["validated"]))


def _designation_ppv():
    from census import designation as des
    rng = np.random.default_rng(1101)
    n = 100
    true_p = np.clip(rng.normal(0.18, 0.08, n), 0.03, 0.70)
    se = np.full(n, 0.025)
    df = pd.DataFrame({"GEOID": [f"26{i:03d}" for i in range(n)],
                       "pov": np.clip(true_p + rng.normal(0, se), 0.02, 0.85), "pov_se": se})
    out = des.designation_accuracy(df, "pov", 0.20, se_col="pov_se", rules=("prob80",),
                                   ppv_intervals=True, ppv_bootstrap=50, seed=42)
    return dict(success=True, validated=bool(out["rules"].iloc[0]["ppv_validated"]))


def _msm_multi(tmp_path):
    from census import workflows_microdata as wm
    rng = np.random.default_rng(1102)
    rows = []
    for u in range(40):
        l1, l2 = rng.normal(0, 1), rng.normal(0, 1)
        g = np.nan if u < 20 else (2015 if u < 30 else 2017)
        for yr in range(2012, 2020):
            a_prev = 1 if (not np.isnan(g) and yr > g) else 0
            l1, l2 = 0.5 * l1 + 0.1 * l2 + 0.3 * a_prev + rng.normal(0, 0.7), 0.4 * l2 - 0.2 * a_prev + rng.normal(0, 0.7)
            a_cur = 1 if (not np.isnan(g) and yr >= g) else 0
            y = 10.0 - 1.5 * a_cur + 0.8 * l1 - 0.5 * l2 + rng.normal(0, 0.5)
            rows.append({"GEOID": f"{u+1:02d}", "Year": yr, "first_treated": g, "l1": l1, "l2": l2, "y": y})
    p = tmp_path / "msm2.csv"; pd.DataFrame(rows).to_csv(p, index=False)
    out = wm.difference_in_differences(str(p), outcome="y", treated="first_treated", period="Year", unit="GEOID",
                                       design="msm", first_treated="first_treated", method="gformula",
                                       time_varying_confounders=["l1", "l2"], product="1-year")
    return dict(success=out["success"], validated=bool(out["validated"]))


def _joinpoint_aapc():
    from census import joinpoint as jp
    rng = np.random.default_rng(1103)
    years = list(range(2005, 2023))
    x = np.arange(len(years), dtype=float)
    counts = np.maximum(rng.poisson(400.0 * np.exp(-0.02 * x)), 1)
    out = jp.joinpoint(years, counts=counts, population=np.full(len(years), 100000.0),
                       max_joinpoints=1, permutations=199, bootstrap=100)
    return dict(success=True, validated=bool(out["aapc_bootstrap_t"]["validated"]))


def _fcs_pmm(tmp_path):
    rng = np.random.default_rng(1039)
    n = 120; x1 = rng.normal(size=n); x2 = 0.5 * x1 + rng.normal(size=n); x3 = 0.4 * x2 + rng.normal(size=n)
    y = 1.0 + 0.8 * x1 - 0.5 * x2 + 0.4 * x3 + rng.normal(0, 0.8, n)
    df = pd.DataFrame({"GEOID": [f"26{i:03d}" for i in range(n)], "y": y, "x1": x1, "x2": x2, "x3": x3})
    for col in ("x1", "x2", "x3"):
        df.loc[rng.random(n) < 0.15, col] = np.nan
    p = tmp_path / "fcs.csv"; df.to_csv(p, index=False)
    out = wi.fit_model(str(p), "y ~ x1 + x2 + x3", impute=["x1", "x2", "x3"], impute_method="pmm")
    return dict(success=out["success"], validated=bool(out["validated"]))


def _wonder_tsv(tmp_path):
    bands = [
        ("< 1 year", 20000, 3700000), ("1-4 years", 3500, 15000000), ("5-14 years", 5000, 41000000),
        ("15-24 years", 34000, 43000000), ("25-34 years", 58000, 45000000), ("35-44 years", 85000, 43000000),
        ("45-54 years", 160000, 41000000), ("55-64 years", 360000, 42000000), ("65-74 years", 560000, 33000000),
        ("75-84 years", 680000, 16000000), ("85+ years", 850000, 6500000),
    ]
    lines = ["Notes\tTen-Year Age Groups\tGender\tDeaths\tPopulation"]
    for label, d, n in bands:
        lines.append(f"\t{label}\tMale\t{d // 2}\t{n // 2}")
        lines.append(f"\t{label}\tFemale\t{d - d // 2}\t{n - n // 2}")
    lines += ["---", "Dataset: Underlying Cause of Death, 2018-2022",
              "Query Parameters:", "Year/Month: 2018; 2019; 2020; 2021; 2022"]
    p = tmp_path / "wonder_all.tsv"; p.write_text("\n".join(lines), encoding="utf-8")
    return str(p)


CALLS = {
    "R1": lambda t: mcp_server.calculate_significance(14.1, 1.2, 11.0, 1.1),
    "R2": lambda t: wi.fit_model(_frame(t)[0], "y ~ x"),
    "R3": lambda t: _scpc(t, formula="y ~ x", spatial="scpc"),
    "R4": lambda t: _scpc(t, formula="p ~ x", model="binomial", trials="T", spatial="scpc"),
    "R5": lambda t: __import__("census.scpc", fromlist=["x"]).fit_scpc(
        "p ~ x", _frame(t)[1], "binomial", trials="T", coords=_frame(t)[2], rho_bar=.10) | dict(success=True),
    "R6": lambda t: wi.fit_model(_frame(t)[0], "c ~ x", model="negbin", exposure="E"),
    "R7": lambda t: wi.fit_model(_censored(t), "y ~ x", model="negbin", exposure="E", censored="hid"),
    "R8": lambda t: _eiv(6, "g1") | dict(success=True),
    "R9": lambda t: _eiv(9, "g2") | dict(success=True),
    "R10": lambda t: (lambda v, y, b: wi.interrupted_series(values=v, years=y, interruption_year=b))(*_series(18)),
    "R11": lambda t: (lambda v, y, b: wi.interrupted_series(values=v, years=y, interruption_year=b))(*_series(15)),
    "R12": lambda t: wi.interrupted_series(values=[14.1, 13.6, 13.0, 12.2, 11.8], years=[2013, 2015, 2018, 2020, 2023],
                                           interruption_year=2018),
    "R13": lambda t: mcp_server.trend_test([2013, 2018, 2023], [14.1, 13.0, 11.8], [0.4, 0.4, 0.3]),
    "R14": lambda t: _ineq("gini"),
    "R15": lambda t: _ineq("theil_t"),
    "R16": lambda t: _who(t, "par"),
    "R17": lambda t: _who(t, "mdm_w"),
    "R18": lambda t: _joinpoint_ears(),
    "R19": lambda t: _staggered(t),
    "R20": lambda t: _msm(t),
    "R21": lambda t: _triple(t),
    "R22": lambda t: _stratified(t),
    "R23": lambda t: _designation(t),
    "R24": lambda t: wi.bias_analysis("e_value", estimate=1.8, lower=1.3, upper=2.5),
    "R25": lambda t: wi.estimate_effect(_causal_frame(t), kind="treatment", outcome="y", treatment="a",
                                        confounders=["x", "z"], method="ipw", weights="overlap"),
    "R26": lambda t: wi.estimate_effect(_causal_frame(t), kind="matching", outcome="y", treatment="a",
                                        confounders=["x", "z"], method="nn"),
    "R27": lambda t: _rdd(t),
    "R28": lambda t: _disease_map(t),
    "R29": lambda t: _fcs_pmm(t),
    "R30": lambda t: wi.demography_analysis("life_table", input_path=_wonder_tsv(t)),
    "R31": lambda t: _meta_k12(),
    "R32": lambda t: wi.estimate_effect(_causal_frame(t), kind="matching", outcome="y", treatment="a",
                                        confounders=["x", "z"], method="nn_att"),
    "R33": lambda t: _disease_map(t, method="B3", exp_low=40.0, exp_high=80.0),
    "R34": lambda t: _rdd_continuous(t),
    "R35": lambda t: _prob_misclass(),
    "R36": lambda t: _msm(t, method="gformula"),
    "R37": lambda t: _agreement_ccc(t),
    "R38": lambda t: _designation_ppv(),
    "R39": lambda t: _msm_multi(t),
    "R40": lambda t: _joinpoint_aapc(),
}


def test_contract_rows_match_the_runners():
    assert sorted(ROWS) == sorted(CALLS) and len(ROWS) == 40


@pytest.mark.parametrize("rid", sorted(CALLS, key=lambda r: int(r[1:])))
def test_routing_row(rid, tmp_path):
    row = ROWS[rid]
    assert row["tool"] in REGISTERED
    assert row["tool"] in mp.tools_for(row["profile"], sorted(REGISTERED))
    guide = (ROOT/f"docs/recipes/{row['guidance']}.md").read_text()
    assert row["tool"] in guide or row["tool"] in mcp_server.INSTRUCTIONS
    out = CALLS[rid](tmp_path)
    exp = row["expected"]
    ok = out.get("success", "error_code" not in out)   # some older tools omit success on success
    if exp.startswith("refused"):
        assert ok is False
        return
    assert ok is True, out
    if exp == "validated":
        assert out["validated"] is True, out
    elif exp == "exploratory":
        assert out["validated"] is False, out
    else:
        assert exp == "answered"


def test_core_text_names_only_reachable_tools():
    """Core-style profiles may name a tool outside the profile only as "<tool> [full]" or next to "full profile"."""
    for profile in mp.CORE_STYLE_PROFILES:
        have = set(mp.tools_for(profile, sorted(REGISTERED)))
        texts = re.split(r"\n(?=\d+\. )", mp.CORE_INSTRUCTIONS) + [mp.DESCRIPTION_OVERRIDES[t] for t in have
                                                                   if t in mp.DESCRIPTION_OVERRIDES]
        for text in texts:
            outside = {n for n in re.findall(r"\b[a-z_]+\b", text) if n in REGISTERED and n not in have}
            unmarked = {n for n in outside if f"{n} [full]" not in text}
            assert not unmarked or "full profile" in text, (profile, unmarked, text[:120])


def test_rule_text_generated_from_protocol():
    import subprocess, sys
    assert subprocess.run([sys.executable, str(ROOT/"scripts/sync_rule_text.py"), "--check"]).returncode == 0
    proto = (ROOT/"docs/agent_protocol.md").read_text()
    assert proto.count("<!-- mcp-rules:A -->") >= 15 and "<!-- mcp-rules:B -->" in proto
