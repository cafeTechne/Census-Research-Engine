# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 83: stratified analysis, Mantel-Haenszel, homogeneity, additive interaction, covariable roles."""
import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from census import stratified as st, stratified_core as sc
from census.manifest import load_manifest, validate_manifest
from tests.test_manifest import EXAMPLE

ROOT = Path(__file__).resolve().parents[1]
AUDIT = json.loads((ROOT/"docs/audits/stratified_validation.json").read_text())


def test_flags_equal_the_audit():
    o = AUDIT["outcome"]
    assert st.VALIDATED["mh_counts"] == (o["MH_rr"]["passed"] and o["MH_or"]["passed"] and o["MH_rd"]["passed"]
                                         and o["MH_irr"]["passed"])
    assert st.VALIDATED["mh_pums"] == (o["MH2_rr"]["passed"] and o["MH2_or"]["passed"] and o["MH2_rd"]["passed"])
    assert st.VALIDATED["breslow_day"] == o["H1_breslow_day"]["passed"] is True
    assert st.VALIDATED["woolf"] == o["H1_woolf"]["passed"] is False
    assert st.VALIDATED["pums_wald"] == o["H1_pums_wald"]["passed"] is False
    assert st.VALIDATED["reri_counts"] == (o["RERI_delta"]["passed"] and o["RERI_boot"]["passed"])
    assert "Committed before the full run" in (ROOT/"docs/audits/stratified_validation_criterion.md").read_text()


def test_matches_statsmodels():
    from statsmodels.stats.contingency_tables import StratifiedTable
    rng = np.random.default_rng(2)
    a, b, c, d = (rng.integers(5, 60, 4).astype(float) for _ in range(4))
    t = StratifiedTable([np.array([[a[k], b[k]], [c[k], d[k]]]) for k in range(4)])
    m = sc.mh_pooled(a, b, c, d, level=.95)
    assert m["or"]["estimate"] == pytest.approx(t.oddsratio_pooled)
    assert (m["or"]["lower"], m["or"]["upper"]) == pytest.approx(t.oddsratio_pooled_confint())
    assert m["rr"]["estimate"] == pytest.approx(t.riskratio_pooled)
    assert sc.breslow_day_tarone(a, b, c, d)[0] == pytest.approx(t.test_equal_odds(adjust=True).statistic)


def test_book_examples_classification():
    # Foundations of Epidemiology Table 8-5 (crude 2.0)
    assert sc.classify(2.0, 2.0, [1.0, 3.2], True) == "effect_modifier"
    assert sc.classify(2.0, 3.55, [3.5, 3.6], False) == "confounder"
    assert sc.classify(2.0, 1.95, [1.9, 2.0], False) == "neither"
    # book chapter 7 OCP/ovarian cancer: identical stratum ORs .44, crude 1.0
    a = np.array([2., 2.]); b = np.array([3., 3.]); c = np.array([3., 3.]); d = np.array([2., 2.])
    assert sc.mh_pooled(a, b, c, d)["or"]["estimate"] == pytest.approx(4/9)


def test_counts_tool(tmp_path):
    from census import workflows_microdata as wm
    f = pd.DataFrame(dict(age=["<45", "45-64", "65+"], ae=[20, 40, 80], ne=[1000, 900, 700], au=[15, 30, 60],
                          nu=[1500, 1400, 1000]))
    p = tmp_path/"s.csv"; f.to_csv(p, index=False)
    out = wm.stratified_analysis(str(p), "age", "ae", "ne", "au", "nu")
    assert out["success"] and out["classification"]["or"] in ("confounder", "effect_modifier", "neither")
    assert out["homogeneity"]["rr"]["validated"] is False and out["homogeneity"]["or"]["validated"] is True
    pt_out = wm.stratified_analysis(str(p), "age", "ae", "ne", "au", "nu", person_time=True)
    assert pt_out["measure"] == "rate_ratio"
    assert not wm.stratified_analysis(str(p), "age")["success"]


def test_additive_interaction_and_pums():
    r = st.additive_interaction(cases=[100, 150, 150, 300], totals=[1000]*4)
    assert r["reri"] == pytest.approx(1.0) and r["validated"]
    rng = np.random.default_rng(0); n = 6000
    s = rng.integers(0, 2, n); e = rng.integers(0, 2, n)
    y = (rng.random(n) < np.where(e == 1, 1.5, 1.0)*np.where(s == 1, .2, .1)).astype(int)
    W = np.column_stack([np.ones(n)]+[1+.2*rng.standard_normal(n) for _ in range(80)])
    out = st.stratified_pums(y, e, s, W, [0, 1])
    assert abs(out["pooled"]["rr"]["estimate"]-1.5) < .3 and out["validated"]
    assert out["homogeneity"]["rr"]["validated"] is False


def test_manifest_covariable_roles():
    m = load_manifest(EXAMPLE)
    m["covariables"] = {"pop": "mediator"}
    assert any("mediator" in e for e in validate_manifest(m, resolve=False))
    m["covariables"] = {"pop": "confounder"}
    assert validate_manifest(m, resolve=False) == []
    m["covariables"] = {"pop": "effect_modifier"}
    assert any("effect modifier" in e for e in validate_manifest(m, resolve=False))
    m["covariables"] = {"pop": "bogus"}
    assert any("allowed" in e for e in validate_manifest(m, resolve=False))
