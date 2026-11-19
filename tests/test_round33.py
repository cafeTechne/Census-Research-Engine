# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 33: rank/partial correlation intervals, rank group comparisons and diagnostics."""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from scipy import stats

from census import correlation, rank_methods as rm
from census.group_compare import compare_groups
from census.models import fit_replicate
from census.simulation import make_replicates

ROOT = Path(__file__).resolve().parents[1]
warnings.simplefilter("ignore")


def frame(n=150, seed=33):
    rng = np.random.default_rng(seed)
    f = pd.DataFrame(dict(GEOID=[f"26{i:03d}" for i in range(n)], Year=2022, a=rng.normal(size=n),
                          g=rng.choice(list("abc"), n)))
    f["b"] = .4*f.a+rng.normal(size=n); f["c"] = .5*f.a+rng.normal(size=n)
    return f


def long_replicates(f, cols, seed=1):
    rng = np.random.default_rng(seed)
    obs = f[cols].to_numpy(float); se = np.full(obs.shape, .2)
    rep = make_replicates(obs, se, rng)
    rows = []
    for j, c in enumerate(cols):
        block = pd.DataFrame(rep[:, j, :], columns=[f"rep_{k+1}" for k in range(80)])
        block.insert(0, "estimate", obs[:, j]); block.insert(0, "variable", c)
        block.insert(0, "Year", 2022); block.insert(0, "GEOID", f.GEOID.to_numpy())
        rows.append(block)
    return pd.concat(rows, ignore_index=True), rep


def test_coefficients_equal_scipy_and_partial_residuals():
    f = frame()
    assert rm.coefficient(f.a, f.b, "spearman") == pytest.approx(stats.spearmanr(f.a, f.b)[0])
    assert rm.coefficient(f.a, f.b, "kendall") == pytest.approx(stats.kendalltau(f.a, f.b)[0])
    Z = sm.add_constant(f.c)
    ra, rb = sm.OLS(f.a, Z).fit().resid, sm.OLS(f.b, Z).fit().resid
    assert rm.coefficient(f.a, f.b, "partial", f.c) == pytest.approx(np.corrcoef(ra, rb)[0, 1])


def test_interval_formulas_by_hand():
    f = frame(); n = len(f)
    for method, scale, k in (("pearson", 1., 3), ("spearman", 1.06, 3), ("kendall", .437, 4)):
        out = rm.correlation_interval(f.a, f.b, method)
        z = np.arctanh(out["estimate"]); se = np.sqrt(scale/(n-k))
        assert out["lower"] == pytest.approx(np.tanh(z-stats.norm.ppf(.95)*se))
    _, rep = long_replicates(f, ["a", "b"])
    out = rm.correlation_interval(f.a, f.b, "pearson", 2, reps_x=rep[:, 0], reps_y=rep[:, 1])
    rr = np.array([np.corrcoef(rep[:, 0, k], rep[:, 1, k])[0, 1] for k in range(80)])
    var = 1/(n-3)+.05*np.sum((np.arctanh(rr)-np.arctanh(out["estimate"]))**2)
    assert out["se_z"] == pytest.approx(np.sqrt(var))


def test_superiority_matches_scipy_brunner_munzel():
    rng = np.random.default_rng(5); x, y = rng.normal(size=40), rng.normal(.4, 1.5, size=55)
    p, se, df = rm.superiority(x, y)
    ref = stats.brunnermunzel(x, y)
    assert (p-.5)/se == pytest.approx(ref.statistic)
    pairs = (x[:, None] < y[None, :]).mean()+.5*(x[:, None] == y[None, :]).mean()
    assert p == pytest.approx(pairs)
    out = rm.superiority_interval(x, y)
    assert out["p_value"] == pytest.approx(ref.pvalue, rel=1e-6)
    z = rng.normal(size=30); kw = rm.kruskal([x, y, z])
    assert kw["p"] == pytest.approx(stats.kruskal(x, y, z).pvalue) and kw["df"] == 2


def test_validated_correlations_flags_and_replicates():
    f = frame(); reps, _ = long_replicates(f, ["a", "b", "c"])
    sp = correlation.validated_correlations(f, ["a", "b"], "spearman")
    assert sp.validated.all() and (sp.variant == 1).all()
    pe = correlation.validated_correlations(f, ["a", "b"], "pearson")
    assert not pe.validated.any() and "replicates" in pe.note.iloc[0]
    pr = correlation.validated_correlations(f, ["a", "b"], "pearson", reps)
    assert pr.validated.all() and (pr.variant == 2).all()
    pa = correlation.validated_correlations(f, ["a", "b"], "partial", reps, controls=["c"])
    assert pa.validated.all()
    with pytest.raises(ValueError, match="controls"):
        correlation.validated_correlations(f, ["a", "b"], "partial")


def test_flags_equal_the_fixed_audit():
    audit = json.loads((ROOT/"docs/audits/rank_validation.json").read_text())["passed"]
    for method, variant in correlation.VALIDATED_VARIANT.items():
        assert audit[f"{method}/{variant}"]
        if variant == 2:
            assert not audit[f"{method}/1"]
    assert audit["B1"] and audit["KW"]


def test_rank_group_comparison():
    f = frame()
    two = compare_groups(f[f.g != "c"], "a", "g", design="two_group", method="rank")
    p, se, df = rm.superiority(f.a[f.g == "a"].to_numpy(), f.a[f.g == "b"].to_numpy())
    assert two.effect_sizes["probability_of_superiority"] == pytest.approx(p) and two.validation["omnibus"]
    three = compare_groups(f, "a", "g", method="rank")
    assert three.omnibus["test"] == "Kruskal-Wallis"
    assert three.omnibus["p_two_sided"] == pytest.approx(stats.kruskal(*[f.a[f.g == k] for k in "abc"]).pvalue)
    with pytest.raises(ValueError, match="without covariates"):
        compare_groups(f, "a", "g", design="ancova", covariates=["b"], method="rank")
    json.dumps(three.to_dict())


def test_model_diagnostics_match_statsmodels():
    from census.diagnostics import model_diagnostics
    from statsmodels.stats.diagnostic import het_breuschpagan
    from statsmodels.stats.outliers_influence import OLSInfluence, variance_inflation_factor
    f = frame(); fit = fit_replicate("a ~ b + c", f)
    d = model_diagnostics(fit)
    X = sm.add_constant(f[["b", "c"]]).to_numpy(); ols = sm.OLS(f.a.to_numpy(), X).fit()
    assert d["vif"]["b"] == pytest.approx(variance_inflation_factor(X, 1))
    assert d["breusch_pagan_p"] == pytest.approx(het_breuschpagan(ols.resid, X)[1])
    top = int(np.argmax(OLSInfluence(ols).cooks_distance[0]))
    assert d["cooks_distance_top5"][0]["unit"] == f.GEOID.iloc[top]
    assert "never a gate" in d["note"]
    pois = fit_replicate("a ~ b", f.assign(a=np.abs(f.a)))
    assert "vif" not in model_diagnostics(pois)    # one predictor: no VIF


def test_mcp_correlation_tool_kendall_and_partial(tmp_path):
    from census import workflows_inference as wi
    f = frame(); path = tmp_path/"f.csv"; f.to_csv(path, index=False)
    k = wi.correlation_matrix(str(path), ["a", "b"], method="kendall")
    assert k["success"] and k["validated_intervals"][0]["validated"]
    p = wi.correlation_matrix(str(path), ["a", "b"], method="partial", controls=["c"])
    assert p["success"] and not p["validated_intervals"][0]["validated"]
    s = wi.correlation_matrix(str(path), ["a", "b"], method="spearman")
    assert s["success"] and "validated_intervals" in s
