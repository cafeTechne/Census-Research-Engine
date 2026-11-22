# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 82: epidemiologic reporting conventions (measure types, design labels, templates, allocation, Table 1)."""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from census import epi_reporting as er
from census.manifest import load_manifest, methods_section

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT/"examples/manifests"


def test_measure_types_from_manifests():
    smr = load_manifest(EX/"r29_mi_ny_mortality_smr.json")
    t = er.manifest_measure_types(smr)
    assert t["h1_numerator"] == "count" and t["h1"] == "incidence_rate"
    assert er.manifest_measure_types(load_manifest(EX/"r20_mi_ny_disability_determinants.json"))["asdp"] == "prevalence"
    assert er.manifest_measure_types(load_manifest(EX/"r22_mi_ny_county_low_birth_weight.json"))["lbw"] == "incidence_proportion"
    assert er.external_measure_type({"source": "file", "measure_type": "prevalence"}) == "prevalence"
    assert er.external_measure_type({"source": "file"}) == "unspecified"


def test_methods_text_has_design_and_limitations_without_causal_words():
    for f in sorted(EX.glob("*.json")):
        text = methods_section(load_manifest(f))
        assert "### Study design and measures" in text and "### Limitations" in text, f.name
        assert "ecologic fallacy" in text
        lim = text[text.index("### Limitations"):text.index("### References")]
        assert not er.causal_terms(lim.replace("one causes the other", "")), f.name


def test_registered_manifest_hashes_unchanged():
    from census.manifest import manifest_hash
    for f in EX.glob("*.json"):
        m = json.loads(f.read_text())
        if "manifest_hash" in m:
            assert manifest_hash(m) == m["manifest_hash"], f.name


def test_interpretation_templates():
    s = er.interpret_ratio("prevalence", 1.4, 1.1, 1.8, "disability", "high-poverty counties", "low-poverty counties",
                           period="2019-2023")
    assert "1.40 times as high in high-poverty counties compared with low-poverty counties over 2019-2023" in s
    s = er.interpret_ratio("rate", 1.05, .9, 1.2, "deaths", "A", "B")
    assert "no evidence of a difference (not evidence of no difference)" in s
    d = er.interpret_difference("prevalence", -2.5, -4, -1, "uninsurance", "A", "B")
    assert "2.50 percentage points lower" in d
    r = er.rescale_interval(2.0, 1.5, 2.6667, .90, .95, log_scale=True)
    assert r["lower"] < 1.5 and r["upper"] > 2.6667 and r["estimate"] == pytest.approx(2.0)
    assert er.causal_terms("Poverty leads to disability") == ["leads to"]


def test_allocation_lines_and_shares():
    labels = {"T_001": "Estimate!!Total:", "T_002": "Estimate!!Total:!!Allocated",
              "T_003": "Estimate!!Total:!!Not allocated"}
    v = pd.DataFrame({"T_001": [100, 50], "T_002": [10, 5], "T_003": [90, 45]})
    assert er.allocation_lines(labels) == {"allocated": ["T_002"], "not_allocated": ["T_003"]}
    assert er.allocation_shares(v, labels).tolist() == [.1, .1]
    inc = {"I_001": "Total:", "I_002": "Percent of income allocated --!!No income allocated",
           "I_003": "Percent of income allocated --!!Dollar value of zero allocated",
           "I_004": "Percent of income allocated --!!More than 0 to less than 10 percent of total income allocated"}
    assert er.allocation_lines(inc) == {"allocated": ["I_003", "I_004"], "not_allocated": ["I_002"]}
    assert er.allocation_tables_for("2023:B27010_017") == ["B992701"]
    assert er.allocation_tables_for("B25003_002") == ["B99252"] and er.allocation_tables_for("B01003_001") == []
    s = er.allocation_summary(pd.DataFrame({"GEOID": ["1", "2"], "table": "B992701", "allocated_share": [.2, .1]}))
    assert s[0]["above_limit"] and "15.0%" in er.allocation_note(s)[0]


def test_table_one_and_tool(tmp_path):
    from census import workflows_inference as wi
    rng = np.random.default_rng(0)
    f = pd.DataFrame(dict(GEOID=[f"26{i:03d}" for i in range(30)], pov=rng.uniform(5, 30, 30), dis=rng.uniform(8, 20, 30),
                          pop=rng.integers(1000, 9000, 30)))
    t = er.table_one(f, "pov", ["dis"], population="pop")
    assert list(t.columns) == ["Q1", "Q2", "Q3", "All"] and t.loc["areas", "All"] == 30
    assert t.loc["population", "All"] == pytest.approx(f["pop"].sum())
    p = tmp_path/"f.csv"; f.to_csv(p, index=False)
    out = wi.make_table("table1", str(p), str(tmp_path), variables=["dis"], exposure="pov", population="pop")
    assert out["success"] and "ecologic fallacy" in out["markdown"]
    assert not wi.make_table("table1", str(p), str(tmp_path))["success"]


def test_comparison_table_rescaled():
    from census.report_tables import comparison_table
    df = pd.DataFrame(dict(GEOID=["a"], difference=[2.0], se_difference=[1.0], z=[2.0], p_value=[.045],
                           p_adjusted=[.045], significant_adjusted=[True], confidence_level=[.90]))
    t90, t95 = comparison_table(df), comparison_table(df, confidence_level=.95)
    assert "90% CI" in t90.display.columns and "95% CI" in t95.display.columns
    assert t95.data.ci_lower[0] < t90.data.ci_lower[0]


def test_bundle_design_lines(tmp_path):
    from census import workflows_inference as wi
    r = tmp_path/"r.json"; r.write_text(json.dumps({"success": True, "summary": "x"}))
    out = wi.make_results_bundle(str(tmp_path/"b"), {"r": str(r)})
    text = (tmp_path/"b"/"methods.md").read_text()
    assert out["success"] and "ecologic fallacy" in text
    wi.make_results_bundle(str(tmp_path/"c"), {"r": str(r)}, design="individual")
    text = (tmp_path/"c"/"methods.md").read_text()
    assert "ecologic fallacy" not in text and "Cross-sectional" in text


def test_protocol_language_rule_in_mcp_text():
    from census import mcp_profiles as p
    assert "never \"causes\"" in p.CORE_INSTRUCTIONS.replace("never “causes”", "never \"causes\"") or "never \"causes\"" in p.CORE_INSTRUCTIONS
    assert "ECOLOGIC" in (ROOT/"mcp_server.py").read_text()
