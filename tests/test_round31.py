# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 31: omnibus tests, compare_groups and their gates (independent references)."""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from scipy import stats

from census import group_compare, joint_tests
from census import omnibus as om
from census.models import fit_replicate, glm_robust_covariance

ROOT = Path(__file__).resolve().parents[1]
warnings.simplefilter("ignore")


def groups_frame(n=150, seed=31, effect=0.):
    rng = np.random.default_rng(seed)
    f = pd.DataFrame(dict(GEOID=[f"{'26' if i < 80 else '36'}{i:03d}" for i in range(n)], Year=2022,
                          g=rng.choice(list("abcd"), n), h=rng.choice(list("xy"), n), x=rng.normal(size=n)))
    f["y"] = 1+.3*f.x+effect*(f.g == "c")+rng.normal(size=n)
    f["E"] = np.maximum(5, np.rint(rng.lognormal(np.log(100), 1, n)))
    f["cnt"] = rng.poisson(f.E*np.exp(.1*f.x)).astype(float)
    return f


def design(f):
    X = np.column_stack([np.ones(len(f))]+[(f.g == k).to_numpy(float) for k in "bcd"]+[f.x.to_numpy()])
    return X, f.y.to_numpy()


# ---------------------------------------------------------------- candidates

def test_fits_and_hc3_match_statsmodels_and_engine():
    f = groups_frame(); X, y = design(f)
    b, mu, w = om.fit(X, y, "linear")
    V, _ = om.model_covariance(X, y, mu, w, "linear")
    np.testing.assert_allclose(V, sm.OLS(y, X).fit(cov_type="HC3").cov_params(), atol=1e-14)
    b, mu, w = om.fit(X, f.cnt.to_numpy(), "poisson", exposure=f.E.to_numpy())
    ref = sm.GLM(f.cnt.to_numpy(), X, family=sm.families.Poisson(), exposure=f.E.to_numpy()).fit()
    np.testing.assert_allclose(b, ref.params, atol=1e-10)
    np.testing.assert_allclose(om.model_covariance(X, f.cnt.to_numpy(), mu, w, "poisson")[0],
                               glm_robust_covariance(X, f.cnt.to_numpy(), ref.fittedvalues, "poisson")[0], atol=1e-14)
    Y = f.cnt.to_numpy()[None, :]+np.arange(3)[:, None]
    B = om.batched_refits(X, Y, "poisson", b, exposure=f.E.to_numpy())
    for r in range(3):
        np.testing.assert_allclose(B[r], om.fit(X, Y[r], "poisson", exposure=f.E.to_numpy())[0], atol=1e-10)


def test_w1_with_classical_covariance_equals_f_oneway():
    f = groups_frame(); X = design(f)[0][:, :4]; y = f.y.to_numpy()
    b, mu, _ = om.fit(X, y, "linear"); e = y-mu
    V = e@e/(len(y)-4)*np.linalg.inv(X.T@X)
    out = om.w1(b, V, [1, 2, 3], len(y))
    ref = stats.f_oneway(*[y[f.g == k] for k in "abcd"])
    assert out["statistic"] == pytest.approx(ref.statistic) and out["p"] == pytest.approx(ref.pvalue)
    assert (out["df"], out["df_denominator"]) == (3, len(y)-4)


def test_htz_degrees_of_freedom_against_explicit_loops():
    f = groups_frame(n=40); X, y = design(f); test = [1, 2]
    b, mu, w = om.fit(X, y, "linear")
    _, part = om.model_covariance(X, y, mu, w, "linear", kind="HC2")
    nu = om.htz_df(X, w, part["bread"], part["h"], test)
    # Independent loop implementation of the Pustejovsky-Tipton working-model moments.
    n = len(y); B = np.linalg.inv(X.T@X); H = X@B@X.T; M = np.eye(n)-H
    u = [(B@X[i])[test]/np.sqrt(1-H[i, i]) for i in range(n)]
    Sigma = sum(np.outer(u[i], u[i])*M[i, i] for i in range(n))
    T = np.linalg.inv(np.linalg.cholesky(Sigma)); us = [T@v for v in u]
    total = sum(2*us[i][s]*us[i][t]*us[j][s]*us[j][t]*M[i, j]**2
                for s in range(2) for t in range(2) for i in range(n) for j in range(n))
    assert nu == pytest.approx(2*3/total)


def test_w3_score_statistic_and_reproducibility():
    f = groups_frame(); X, y = design(f); test = [1, 2, 3]
    a = om.w3(X, y, "linear", test, np.zeros((5, 5)), np.random.default_rng(5))
    b = om.w3(X, y, "linear", test, np.zeros((5, 5)), np.random.default_rng(5))
    assert a == b and 1/400 <= a["p"] <= 1
    keep = [0, 4]; br = np.linalg.lstsq(X[:, keep], y, rcond=None)[0]; r = y-X[:, keep]@br
    contrib = np.linalg.solve(X.T@X, (X*r[:, None]).T)[test]
    A = contrib.sum(axis=1); omega = contrib@contrib.T
    assert a["statistic"] == pytest.approx(A@np.linalg.solve(omega, A))


def test_w4_hotelling_by_hand():
    rng = np.random.default_rng(4); B = rng.normal(size=(8, 3))
    d = B[:, [1, 2]]; m = d.mean(0); S = np.cov(d, rowvar=False)
    T2 = 8*m@np.linalg.solve(S, m); F = (8-2)/(2*7)*T2
    out = om.w4(B, [1, 2])
    assert out["T2"] == pytest.approx(T2) and out["p"] == pytest.approx(stats.f.sf(F, 2, 6))
    with pytest.raises(ValueError, match="more clusters"):
        om.w4(rng.normal(size=(8, 9)), list(range(8)))


def test_pairwise_holm_and_simultaneous():
    effects = np.array([.3, .1]); V = np.array([[.02, .005], [.005, .03]])
    r = om.pairwise(effects, V, 50)
    diffs = {(0, 1): .3, (0, 2): .1, (1, 2): -.2}
    for m, pair in enumerate(r["pairs"]):
        assert r["difference"][m] == pytest.approx(diffs[pair])
    raw = r["p_raw"]; order = np.argsort(raw)
    holm = np.maximum.accumulate(np.minimum(1, (3-np.arange(3))*raw[order]))
    np.testing.assert_allclose(r["p_holm"][order], holm)
    # Monte Carlo max-|t| critical value agrees with the multivariate t distribution.
    C = np.array([[1, 0], [0, 1], [-1, 1]]); cov = C@V@C.T; se = np.sqrt(np.diag(cov))
    corr = cov/np.outer(se, se)   # rank 2: simulate independently instead of a singular cdf
    rng = np.random.default_rng(99); z = rng.multivariate_normal(np.zeros(2), V, 200000)@C.T/se
    t = np.max(np.abs(z), axis=1)/np.sqrt(rng.chisquare(50, 200000)/50)
    assert np.mean(t <= r["critical"]) == pytest.approx(.90, abs=.005)
    assert np.allclose(np.diag(corr), 1)
    assert np.all(r["p_simultaneous"] >= r["p_raw"]-1e-12)


# ---------------------------------------------------------------- joint_test

def test_joint_test_columns_variable_term_and_interaction():
    f = groups_frame()
    r = fit_replicate("y ~ C(g) * C(h) + x", f)
    by_var = joint_tests.joint_test(r, variable="x")
    assert by_var["columns"] == ["x"] and by_var["df"] == 1
    main = joint_tests.joint_test(r, term="C(g)")
    assert main["df"] == 3 and all(c.startswith("C(g)[T.") for c in main["columns"])
    inter = joint_tests.joint_test(r, term="C(g):C(h)")
    assert inter["df"] == 3 and all(":" in c for c in inter["columns"]) and inter["validated"]
    with pytest.raises(ValueError, match="exactly one"):
        joint_tests.joint_test(r, variable="x", term="C(g)")
    with pytest.raises(ValueError, match="not in the model"):
        joint_tests.joint_test(r, term="C(nope)")


def test_joint_test_gates():
    f = groups_frame()
    pois = fit_replicate("cnt ~ C(g) + x", f, model="poisson", exposure="E", scale="robust")
    out = joint_tests.joint_test(pois, term="C(g)")
    assert not out["validated"] and "not validated for poisson factor" in out["confirmatory_refusal"]
    small = fit_replicate("y ~ C(g) + x", f.iloc[:100])
    assert "n = 145" in joint_tests.joint_test(small, term="C(g)")["confirmatory_refusal"]
    assert joint_tests.family(["cr(x, df=3, constraints=\"center\")[0]"]) == "spline"
    assert joint_tests.VALIDATED == {("ols", "factor"), ("binomial", "spline"), ("poisson", "spline")}


def test_validated_flags_equal_the_fixed_full_run():
    audit = json.loads((ROOT/"docs/audits/omnibus_validation.json").read_text())
    passed = audit["passed"]; name = {"linear": "ols", "binomial": "binomial", "poisson": "poisson"}
    w3 = {(name[k.split("/")[1]], k.split("/")[2]) for k, v in passed.items() if k.startswith("W3/") and v}
    w4 = {(name[k.split("/")[1]], k.split("/")[2]) for k, v in passed.items() if k.startswith("W4/") and v}
    assert joint_tests.VALIDATED == w3 and joint_tests.SPATIAL_VALIDATED == w4
    assert not any(v for k, v in passed.items() if k.startswith(("W1/", "W2/")))
    for proc, models in joint_tests.PAIRWISE_VALIDATED.items():
        key = "P1" if proc == "holm" else "P2"
        assert models == {name[k.split("/")[1]] for k, v in passed.items() if k.startswith(key+"/") and v}


def test_spatial_joint_test_uses_cluster_estimates():
    rng = np.random.default_rng(7); n = 160
    ids = [f"36{i:03d}" for i in range(n)]
    f = pd.DataFrame(dict(GEOID=ids, Year=2022, g=np.tile(list("ab"), n//2), x=rng.normal(size=n)))
    f["y"] = 1+.3*f.x+rng.normal(size=n)
    coords = pd.DataFrame(dict(GEOID=ids, lon=-80+np.arange(n) % 16*.2, lat=40+np.arange(n)//16*.2))
    r = fit_replicate("y ~ C(g) + x", f, spatial_clusters={"k": 8, "method": "im"}, coords=coords)
    out = joint_tests.joint_test(r, term="C(g)")
    info = r.diagnostics["spatial_clusters"]
    idx = info["cluster_terms"].index("C(g)[T.b]")
    assert out["p_two_sided"] == pytest.approx(om.w4(np.asarray(info["cluster_estimates"]), [idx])["p"])
    assert out["validated"] and out["df_denominator"] == 7


# ---------------------------------------------------------------- compare_groups

def test_compare_groups_oneway_means_pairwise_and_effects():
    f = groups_frame(effect=.5)
    r = group_compare.compare_groups(f, "y", "g", design="oneway", posthoc="simultaneous")
    fit = sm.OLS(f.y, pd.get_dummies(f.g, drop_first=True, dtype=float).assign(const=1.)).fit()
    for _, row in r.adjusted_means.iterrows():
        assert row.estimate == pytest.approx(f.y[f.g == row.group].mean())
    ab = r.pairwise.set_index(["group_a", "group_b"]).loc[("a", "c")]
    assert ab.difference == pytest.approx(fit.params["c"])
    assert r.validation["omnibus"] and r.validation["posthoc_validated"]
    ss_res = fit.ssr; ss_tot_restricted = ((f.y-f.y.mean())**2).sum()
    eta = (ss_tot_restricted-ss_res)/ss_tot_restricted
    assert r.effect_sizes["partial_eta_squared"] == pytest.approx(eta)
    assert "classical_comparison" in r.diagnostics
    assert r.diagnostics["classical_comparison"]["f_oneway"]["p"] == pytest.approx(
        stats.f_oneway(*[f.y[f.g == k] for k in "abcd"]).pvalue)
    json.dumps(r.to_dict())


def test_compare_groups_ancova_twoway_two_group_and_glm():
    f = groups_frame()
    anc = group_compare.compare_groups(f, "y", "g", design="ancova", covariates=["x"])
    X = np.column_stack((np.ones(len(f)), *[(f.g == k).to_numpy(float) for k in "bcd"], f.x))
    b = np.linalg.lstsq(X, f.y, rcond=None)[0]
    assert anc.adjusted_means.set_index("group").loc["b", "estimate"] == pytest.approx(b[0]+b[1]+b[4]*f.x.mean())
    two = group_compare.compare_groups(f, "y", "state", design="two_group")
    coef = fit_replicate("y ~ C(state, Treatment(reference='26'))", f.assign(state=f.GEOID.str[:2]))
    assert two.pairwise.difference.iloc[0] == pytest.approx(coef.coefficients.estimate.iloc[1])
    tw = group_compare.compare_groups(f, "y", "g", design="twoway", group2="h")
    assert tw.omnibus["df"] == 3 and ":" in tw.omnibus["term"] and tw.pairwise is None
    pois = group_compare.compare_groups(f, "cnt", "g", model="poisson", exposure="E")
    assert not pois.validation["omnibus"] and pois.validation["posthoc_validated"]
    assert any(n.startswith("EXPLORATORY") for n in pois.notes)


@pytest.mark.parametrize("kwargs,match", [
    (dict(design="nope"), "design must be"), (dict(design="ancova"), "needs covariates"),
    (dict(design="twoway"), "needs group2"), (dict(model="binomial"), "needs trials"),
    (dict(design="two_group"), "exactly 2 groups"),
    (dict(posthoc="simultaneous", spatial_clusters={"k": 8, "method": "im"}), "not available with spatial"),
])
def test_compare_groups_refusals(kwargs, match):
    with pytest.raises(ValueError, match=match):
        group_compare.compare_groups(groups_frame(), "y", "g", **kwargs)


def test_compare_groups_small_group_refused():
    f = groups_frame(); f.loc[f.index[:146], "g"] = "a"
    with pytest.raises(ValueError, match="at least 5 areas"):
        group_compare.compare_groups(f, "y", "g")


# ---------------------------------------------------------------- manifests

def test_manifest_joint_test_validation_gates():
    from tests.test_round26 import manifest
    from census.manifest import validate_manifest
    m = manifest(); m["analyses"][0]["args"] = {}
    m["analyses"][0]["formula"] = "income ~ pop + C(GEOID.str[:5])"
    h = dict(id="H1", analysis="m1", statistic="joint_test", term="C(GEOID.str[:5])", direction="two_sided")
    m["hypotheses"] = [h]
    assert not [e for e in validate_manifest(m, resolve=False) if "joint_test" in e]
    for bad, msg in ((dict(direction="greater"), "two_sided"), (dict(variable="pop"), "exactly one")):
        mm = json.loads(json.dumps(m)); mm["hypotheses"][0].update(bad)
        assert any(msg in e for e in validate_manifest(mm, resolve=False))


def test_manifest_spline_confirmatory_needs_joint_test_and_glm():
    from tests.test_round26 import manifest
    from census.manifest import validate_manifest
    m = manifest(); m["analyses"][0]["args"] = {"model": "poisson", "exposure": "pop", "scale": "robust"}
    m["analyses"][0]["formula"] = "income ~ cr(pop, df=3)"
    m["hypotheses"] = [dict(id="H1", analysis="m1", statistic="joint_test", variable="pop", direction="two_sided")]
    assert not [e for e in validate_manifest(m, resolve=False) if "spline" in e]
    m["hypotheses"][0] = dict(id="H1", analysis="m1", statistic="coefficient", term="pop", direction="greater")
    assert any("support only joint_test" in e for e in validate_manifest(m, resolve=False))
    m["analyses"][0]["args"] = {}
    assert any("cr spline failed" in e for e in validate_manifest(m, resolve=False))


def test_offline_manifest_run_with_joint_test(tmp_path, monkeypatch):
    import tests.test_manifest as fixtures
    from tests.test_round26 import manifest
    from census.manifest import run_manifest
    monkeypatch.setattr(fixtures, "N_TRACTS", 150)
    m = manifest(); m["analyses"][0]["args"] = {"target": "conservative"}
    m["analyses"][0]["formula"] = "income ~ pop + C(GEOID.str[-3:-2])"
    m["data_source"] = {"synthetic": True, "description": "offline Round 31 joint_test example"}
    m["hypotheses"] = [dict(id="H1", analysis="m1", statistic="joint_test", term="C(GEOID.str[-3:-2])",
                            direction="two_sided")]
    client = fixtures.FakeClient(); client.synthetic = True
    out = run_manifest(m, tmp_path/"ok", client=client, use_cache=False)
    assert out["success"], out.get("deviations", out.get("errors"))
    h = out["hypotheses"].iloc[0]
    assert h.status == "tested" and h["df"] == 9 and 0 < h.p_value <= 1
    assert "wild score-bootstrap" in (tmp_path/"ok/bundle/methods.md").read_text()
    monkeypatch.setattr(fixtures, "N_TRACTS", 96)
    small = run_manifest(m, tmp_path/"small", client=fixtures.FakeClient(), use_cache=False)
    assert small["hypotheses"].iloc[0].status == "not_tested"
    assert any("n = 145" in d["detail"] for d in small["deviations"] if d["kind"] == "hypothesis_not_tested")
