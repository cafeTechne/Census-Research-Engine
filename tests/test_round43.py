# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 43: manifest routing of validated methods, bundle fix and housekeeping."""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from census.manifest import validate_manifest
from census.manifest import methods as mm

ROOT = Path(__file__).resolve().parents[1]
warnings.simplefilter("ignore")


def base():
    from tests.test_round24 import manifest
    m = manifest(); m.pop("exploratory", None)
    return m


def errs(m):
    return validate_manifest(m, resolve=False)


def with_analysis(a, hyp, **top):
    m = base(); m["analyses"] = [a]; m["hypotheses"] = [hyp]; m.update(top)
    return m


# ------------------------------------------------------------------ M1 correlations
def corr(args, **top):
    return with_analysis(dict(id="r1", method="correlation_matrix", variables=["income", "pop"], args=args),
                         dict(id="H1", analysis="r1", statistic="correlation", variables=["income", "pop"],
                              direction="two-sided"), **top)


def test_m1_validation_gates():
    assert not [e for e in errs(corr({"interval": "validated", "method": "spearman"})) if "correlation" in e or "interval" in e]
    assert any("'fisher' or 'validated'" in e for e in errs(corr({"interval": "nope"})))
    assert any("validated only with ACS replicate" in e for e in errs(corr({"interval": "validated", "method": "pearson"})))
    assert not [e for e in errs(corr({"interval": "validated", "method": "pearson"}, replicates={"source": "census_vre"}))
                if "replicate variance" in e]
    assert any("required with method 'partial'" in e for e in errs(corr({"interval": "validated", "method": "partial"})))
    assert any("only allowed with it" in e for e in errs(corr({"interval": "validated", "method": "spearman", "controls": ["pop"]})))
    two = corr({"interval": "validated", "method": "partial", "controls": ["pop", "income"]}, replicates={"source": "census_vre"})
    assert any("one control" in e for e in errs(two))
    two["exploratory"] = True
    assert not [e for e in errs(two) if "one control" in e]


def test_m1_runner_matches_library_and_refuses_exploratory_pairs():
    from census.correlation import validated_correlations
    rng = np.random.default_rng(43); n = 120
    f = pd.DataFrame(dict(GEOID=[str(i) for i in range(n)], a=rng.normal(size=n)))
    f["b"] = .5*f.a+rng.normal(size=n)
    res = mm._run_correlation_matrix(dict(method="correlation_matrix"), {"interval": "validated", "variables": ["a", "b"],
                                     "method": "spearman", "replicate_policy": "strict"}, f, .9, None, "holm", {"held_external": []})
    ref = validated_correlations(f, ["a", "b"], "spearman").iloc[0]
    s = mm._stat_correlation({"variables": ["a", "b"]}, res)
    assert s["estimate"] == pytest.approx(ref.estimate) and s["ci_lower"] == pytest.approx(ref.ci_lower)
    assert s["se_basis"] == "r33_variant_1" and "confirmatory_refusal" not in s
    from scipy import stats
    se_z = (np.arctanh(ref.ci_upper)-np.arctanh(ref.ci_lower))/(2*stats.norm.ppf(.95))
    assert s["p_two_sided"] == pytest.approx(2*stats.norm.sf(abs(np.arctanh(ref.estimate))/se_z))
    pear = mm._run_correlation_matrix(dict(method="correlation_matrix"), {"interval": "validated", "variables": ["a", "b"],
                                      "method": "pearson"}, f, .9, None, "holm", {"held_external": []})
    assert "needs ACS replicates" in mm._stat_correlation({"variables": ["b", "a"]}, pear)["confirmatory_refusal"]


# ------------------------------------------------------------------ M2 negative binomial
def nb(args):
    return with_analysis(dict(id="m1", method="fit_replicate", formula="income ~ pop", args=args),
                         dict(id="H1", analysis="m1", statistic="coefficient", term="pop", direction="greater"))


def test_m2_validation_gates():
    assert not [e for e in errs(nb({"model": "negbin", "exposure": "pop"})) if "negbin" in e]
    assert any("needs args.exposure" in e for e in errs(nb({"model": "negbin"})))
    assert any("does not take ['scale']" in e for e in errs(nb({"model": "negbin", "exposure": "pop", "scale": "robust"})))
    assert any("spatial_clusters" in e for e in errs(nb({"model": "negbin", "exposure": "pop",
                                                         "spatial_clusters": {"k": 8, "method": "im"}})))
    assert any("target 'population' only" in e for e in errs(nb({"model": "negbin", "exposure": "pop", "target": "conservative"})))
    m = nb({"model": "negbin", "exposure": "pop"})
    m["hypotheses"] = [dict(id="H1", analysis="m1", statistic="joint_test", variable="pop", direction="two_sided")]
    assert any("joint_test supports" in e for e in errs(m))


def counts(n=200, seed=39):
    rng = np.random.default_rng(seed)
    f = pd.DataFrame(dict(GEOID=[str(i) for i in range(n)], x=rng.normal(size=n)))
    f["E"] = np.maximum(5, np.rint(rng.lognormal(np.log(50), 1, n)))
    f["c"] = rng.poisson(f.E*np.exp(.3*f.x)*rng.gamma(4, .25, n)).astype(float)
    return f


def test_m2_runner_matches_count_models():
    from census.count_models import fit_count_model
    from census.results import interval_description
    f = counts()
    res = mm._run_fit_replicate(dict(method="fit_replicate", formula="c ~ x"), {"model": "negbin", "exposure": "E",
                                "replicate_policy": "strict"}, f, .9, None, "holm", {"held_external": []})
    ref = fit_count_model("c ~ x", f, "E", "negbin").get("table").iloc[0]
    s = mm._stat_coefficient({"term": "x"}, res)
    assert s["estimate"] == pytest.approx(ref.estimate) and s["se"] == pytest.approx(ref.se)
    assert s["ci_lower"] == pytest.approx(ref.lower) and s["se_basis"] == "se_model"
    assert interval_description(res)["target"] == "population"


# ------------------------------------------------------------------ M3 spatial EIV
def eiv(args, **top):
    return with_analysis(dict(id="m1", method="fit_eiv", formula="income ~ pop", args=args),
                         dict(id="H1", analysis="m1", statistic="coefficient", term="pop", direction="greater"),
                         replicates={"source": "census_vre"}, **top)


def test_m3_validation_gates():
    assert not [e for e in errs(eiv({"spatial": "clusters"})) if "spatial" in e]
    assert not [e for e in errs(eiv({"spatial": "error"})) if "spatial" in e]
    assert any("must be 'clusters'" in e for e in errs(eiv({"spatial": "knn"})))
    assert any("unweighted OLS only" in e for e in errs(eiv({"spatial": "error", "cluster": "GEOID.str[:5]"})))
    assert any("unweighted OLS only" in e for e in errs(eiv({"spatial": "clusters", "model": "wls", "weights": "pop"})))


def test_m3_runner_matches_spatial_eiv_and_refuses_three_covariates():
    from census import spatial_eiv
    from tests.test_round35 import synthetic
    f, long, coords = synthetic()
    for sp, meth in (("clusters", "g1"), ("error", "g2")):
        res = mm._run_fit_eiv(dict(method="fit_eiv", formula="y ~ x"), {"spatial": sp, "replicate_policy": "strict"},
                              f, .9, long, "holm", {"held_external": ["y"], "coords": coords})
        ref = spatial_eiv.fit_spatial_eiv("y ~ x", f, long, method=meth, coords=coords, fixed_variables=("y",))
        s = mm._stat_coefficient({"term": "x"}, res)
        r = ref["table"].set_index("term").loc["x"]
        assert s["estimate"] == pytest.approx(r.estimate) and s["se"] == pytest.approx(r.se)
        assert s["se_basis"] == "se_total" and "confirmatory_refusal" not in s
    res.diagnostics["spatial_eiv"]["validated"] = False; res.diagnostics["spatial_eiv"]["error_prone"] = ["a", "b", "c"]
    assert "exploratory" in mm._stat_coefficient({"term": "x"}, res)["confirmatory_refusal"]


# ------------------------------------------------------------------ methods text
def test_methods_text_for_new_options_and_default_unchanged():
    from census.manifest.methods_text import _METHOD_TEXT
    base_text = _METHOD_TEXT["correlation_matrix"][0]
    assert mm._text_correlation({"args": {}}, base_text) == base_text
    assert "rank_validation.md" in mm._text_correlation({"args": {"interval": "validated", "method": "kendall"}}, base_text)
    t = _METHOD_TEXT["fit_replicate"][0]
    assert mm._text_fit_replicate({"args": {"model": "poisson"}}, t) == t
    assert "NB2" in mm._text_fit_replicate({"args": {"model": "negbin", "exposure": "E"}}, t)
    t = _METHOD_TEXT["fit_eiv"][0]
    assert mm._text_fit_eiv({"args": {}}, t) == t
    assert "t(7)" in mm._text_fit_eiv({"args": {"spatial": "clusters"}}, t)
    assert "lambda" in mm._text_fit_eiv({"args": {"spatial": "error"}}, t)


def test_offline_manifest_run_with_validated_correlation(tmp_path, monkeypatch):
    import tests.test_manifest as fixtures
    from census.manifest import run_manifest
    m = corr({"interval": "validated", "method": "spearman"})
    m["data_source"] = {"synthetic": True, "description": "offline Round 43 example"}
    client = fixtures.FakeClient(); client.synthetic = True
    out = run_manifest(m, tmp_path/"ok", client=client, use_cache=False)
    assert out["success"], out.get("deviations", out.get("errors"))
    h = out["hypotheses"].iloc[0]
    assert h.status == "tested" and -1 < h.estimate < 1
    assert "docs/audits/rank_validation.md" in (tmp_path/"ok/bundle/methods.md").read_text()


# ------------------------------------------------------------------ saturated-model bundle (backlog 7)
def test_saturated_fit_reports_missing_uncertainty_and_plots(tmp_path):
    from census.figures import coefficient_plot
    from census.models import fit_replicate
    from census.results import interval_description
    f = pd.DataFrame(dict(GEOID=["1", "2"], y=[1., 3.], x=[0., 1.]))
    r = fit_replicate("y ~ x", f)
    c = r.coefficients.set_index("term")
    assert c.loc["x", "estimate"] == pytest.approx(2.)
    assert c[["se_model", "se_total", "ci_lower", "ci_upper", "p_value"]].isna().all().all()
    assert r.diagnostics["saturated"] and any("SATURATED" in n for n in r.notes)
    assert "x" in interval_description(r)["undefined_terms"]
    out = coefficient_plot(r, out_dir=tmp_path, formats=("png",))
    assert "no bar is drawn" in out.caption
    json.dumps(r.to_dict(), allow_nan=True)


# ------------------------------------------------------------------ H1/H2 agent-facing text
def _tools():
    import asyncio
    import mcp_server
    return [t.name for t in asyncio.run(mcp_server.mcp.list_tools())]


def test_core_instructions_budget_and_tool_marks():
    import re
    from census import mcp_profiles as p
    assert len(p.CORE_INSTRUCTIONS) <= 8000
    names = _tools(); core = set(p.tools_for("core", names))
    for line in p.CORE_INSTRUCTIONS.splitlines():
        for w in set(re.findall(r"[a-z_]+", line)) & set(names) - core:
            assert f"{w} [full]" in line, f"{w} is not a core tool: mark it [full]"


def test_tool_counts_in_readme_and_status():
    from census import mcp_profiles as p
    names = _tools()
    full, core, cs = len(names), len(p.tools_for("core", names)), len(p.tools_for("core_spatial", names))
    readme = (ROOT/"README.md").read_text(); status = (ROOT/"STATUS.md").read_text()
    assert f"({full} tools; `--profile core` gives {core} for local models)" in readme
    assert f"MCP server ({full} tools; {core} in `core`, {cs} in `core_spatial`;" in status
    assert "32 tools" not in readme


def test_local_models_doc_lists_the_core_tools():
    from census import mcp_profiles as p
    names = _tools(); core = p.tools_for("core", names)
    text = (ROOT/"docs/local_models.md").read_text()
    row = next(line for line in text.splitlines() if line.startswith("| `core` |"))
    assert f"{len(core)} tools" in row and all(f"`{t}`" in row for t in core)
    assert f"({len(p.tools_for('core_spatial', names))} tools)" in text


# ------------------------------------------------------------------ H3-H5 code fixes
def test_estimate_effect_names_missing_arguments(tmp_path):
    from census import workflows_inference as wi
    p = tmp_path/"f.csv"; pd.DataFrame(dict(y=[1., 2.], x=[0., 1.])).to_csv(p, index=False)
    out = wi.estimate_effect(str(p), "iv", "y", x="x")
    assert not out["success"] and "instrument" in out["summary"]
    out = wi.estimate_effect(str(p), "treatment", "y", treatment="x")
    assert not out["success"] and "confounders" in out["summary"]
    assert not wi.estimate_effect(str(p), "nope", "y")["success"]


def test_single_imputation_loop_equals_frozen_per_term_path():
    from census import mci_core as mi
    from census.missing_censored_its import _impute_all_terms, impute_and_fit
    rng = np.random.default_rng(7); n = 150
    x = rng.normal(size=n); w = .5*x+rng.normal(size=n); z = rng.normal(size=n)
    y = 1+.5*x+.5*w+.2*z+rng.normal(size=n)
    X = np.column_stack((np.ones(n), x, np.where(rng.random(n) < .25, np.nan, w), z))
    fast = _impute_all_terms(y, X, 2, np.random.default_rng(11), 20, [1, 2, 3])
    for j, r in zip([1, 2, 3], fast):
        ref = mi.multiple_imputation(y, X, 2, np.random.default_rng(11), 20, j)
        for k in ("estimate", "se", "lower", "upper"):
            assert r[k] == pytest.approx(ref[k], abs=1e-12, rel=1e-12)
    f = pd.DataFrame(dict(x=x, w=X[:, 2], z=z, y=y))
    assert list(impute_and_fit("y ~ x + w + z", f, "w")["table"].term) == ["x", "w", "z"]


def test_iv_reports_first_stage_f():
    import statsmodels.api as sm
    from census import causal
    rng = np.random.default_rng(3); n = 200; t = rng.normal(size=n)
    f = pd.DataFrame(dict(x1=t+rng.normal(size=n)*.6, x2=t+rng.normal(size=n)*.6, y=.5*t+rng.normal(size=n)))
    out = causal.iv_slope(f, "y", "x1", "x2")
    ref = sm.OLS(f.x1, sm.add_constant(f.x2)).fit().fvalue
    assert out["first_stage_f"] == pytest.approx(ref) and any("not yet validated" in s for s in out["notes"])


def test_m2_external_wonder_style_count_outcome_validates():
    from tests.test_round22 import count_manifest
    m = count_manifest("poisson")
    a = m["analyses"][0]["args"]; a.pop("scale"); a["model"] = "negbin"
    assert validate_manifest(m, resolve=False) == []
    a["exposure"] = "pov_rate"
    assert any("denominator" in e for e in validate_manifest(m, resolve=False))
