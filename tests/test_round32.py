# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 32: design-based PUMS procedures, wrappers and the test_association tool."""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from census import pums, pums_inference as pi, pums_tests as pt

ROOT = Path(__file__).resolve().parents[1]
warnings.simplefilter("ignore")


def synthetic(n=900, seed=32):
    """A PUMS-like person frame: households, codes, PWGTP and 80 SDR replicate weights."""
    rng = np.random.default_rng(seed)
    hh = np.sort(rng.integers(0, n//2, n))
    order = np.unique(hh, return_inverse=True)[1]
    w = rng.lognormal(3, .5, hh.max()+1)[hh]
    f = pt.sdr_factors(hh.max()+1)[order]
    df = pd.DataFrame({"SERIALNO": hh, "PWGTP": np.rint(w), "AGEP": rng.integers(0, 90, n),
                       "DIS": rng.choice([1, 2], n, p=[.15, .85]), "HICOV": rng.choice([1, 2], n, p=[.9, .1]),
                       "SEX": rng.choice([1, 2], n), "PINCP": np.where(rng.random(n) < .1, np.nan, rng.lognormal(10, 1, n)),
                       "POVPIP": rng.integers(0, 501, n).astype(float), "REG": rng.choice(["a", "b", "c"], n)})
    for r in range(80):
        df[f"PWGTP{r+1}"] = np.rint(df.PWGTP*f[:, r])
    return df


def weights(df):
    return pums._weight_matrix(df, "person")[1]


# ---------------------------------------------------------------- frozen procedures

def test_hadamard_and_sdr_factors():
    H = pt.hadamard80()
    assert H.shape == (80, 80) and np.array_equal(H@H.T, 80*np.eye(80, dtype=int))
    f = pt.sdr_factors(4)
    np.testing.assert_allclose(f[2], 1+2**-1.5*H[2]-2**-1.5*H[3])
    assert set(np.round(np.unique(f), 6)) <= {round(1-2**-.5, 6), 1., round(1+2**-.5, 6)}


def test_pearson_equals_scipy_and_rao_scott_by_hand():
    df = synthetic(); W = weights(df)
    Wu = np.column_stack((np.ones(len(df)), W[:, 1:]/W[:, :1]))   # unit full weight, valid replicates
    out = pt.independence(df.REG.to_numpy(), df.SEX.to_numpy(), Wu)
    tab = pd.crosstab(df.REG, df.SEX).to_numpy()
    assert out["T0"]["statistic"] == pytest.approx(stats.chi2_contingency(tab, correction=False)[0])
    full = pt.independence(df.REG.to_numpy(), df.SEX.to_numpy(), W)
    P = pt.shares(df.REG.to_numpy(), df.SEX.to_numpy(), W)[2]
    theta, reps = pt._contrasts(P[0]), pt._contrasts(P[1:])
    Vr = .05*(reps-theta).T@(reps-theta); V0 = pt._srs_cov(P[0], len(df))
    dbar = np.trace(np.linalg.solve(V0, Vr))/2
    assert full["T1"]["statistic"] == pytest.approx(full["T0"]["statistic"]/dbar)
    W_ = theta@np.linalg.solve(Vr, theta)
    assert full["T3"]["statistic"] == pytest.approx((80-2+1)/(80*2)*W_)


def test_two_by_two_ratios_and_ses_by_hand():
    df = synthetic(); W = weights(df)
    e, o = (df.DIS == 1).to_numpy(), (df.POVPIP < 100).to_numpy()
    out = pt.two_by_two(e, o, W)
    a, b, c, d = (W[e & o].sum(0), W[e & ~o].sum(0), W[~e & o].sum(0), W[~e & ~o].sum(0))
    lor = np.log(a*d/(b*c))
    assert out["odds_ratio"]["estimate"] == pytest.approx(np.exp(lor[0]))
    assert out["odds_ratio"]["se_log"] == pytest.approx(np.sqrt(.05*np.sum((lor[1:]-lor[0])**2)))
    lrr = np.log((a/(a+b))/(c/(c+d)))
    assert out["relative_risk"]["estimate"] == pytest.approx(np.exp(lrr[0]))
    with pytest.raises(ValueError, match="empty"):
        pt.two_by_two(e, np.zeros(len(e), bool), W)


def test_korn_graubard_by_hand():
    df = synthetic(); W = weights(df); x = (df.HICOV == 2).to_numpy(float)
    out = pt.proportion_interval(x, W)
    pk = (W*x[:, None]).sum(0)/W.sum(0); p = pk[0]; se = np.sqrt(.05*np.sum((pk[1:]-p)**2))
    n_eff = min(len(x), p*(1-p)/se**2)*(stats.t.ppf(.95, len(x)-1)/stats.t.ppf(.95, 80))**2
    k = p*n_eff
    assert out["lower"] == pytest.approx(stats.beta.ppf(.05, k, n_eff-k+1))
    assert out["upper"] == pytest.approx(stats.beta.ppf(.95, k+1, n_eff-k))
    wald = pt.proportion_interval(x, W, "wald")
    assert wald["lower"] == pytest.approx(max(0, p-pt.Z90*se))


def test_means_and_medians_tests():
    df = synthetic().dropna(subset=["PINCP"]); W = weights(df)
    two = pt.means_test(df.PINCP.to_numpy(), df.SEX.to_numpy(), W)
    assert set(two) >= {"M1", "M2", "M3"} and two["M1"]["p"] == pytest.approx(2*stats.norm.sf(abs(two["M1"]["statistic"])))
    assert two["M3"]["statistic"] == pytest.approx(two["M1"]["statistic"]**2)   # (80-1+1)/80 = 1
    three = pt.means_test(df.PINCP.to_numpy(), df.REG.to_numpy(), W)
    assert "M1" not in three and three["M3"]["df"] == 2
    med = pt.difference_of_medians(df.PINCP.to_numpy(), (df.SEX == 2).astype(int).to_numpy(), W)
    m = [pums.weighted_median(df.PINCP[df.SEX == s].to_numpy(), W[(df.SEX == s).to_numpy()])[0] for s in (1, 2)]
    assert med["estimate"] == pytest.approx(m[1]-m[0])


# ---------------------------------------------------------------- wrappers and flags

def test_wrappers_universe_missing_values_and_flags():
    df = synthetic()
    ind = pi.independence_test(df, "REG", "SEX", where="AGEP >= 18")
    assert ind["validated"] and ind["n"] == int((df.AGEP >= 18).sum()) and ind["q"] == 2
    tb = pi.two_by_two(df, "DIS == 1", "POVPIP < 100")
    assert tb["validated"] and tb["n_exposed"] == int((df.DIS == 1).sum())
    means = pi.compare_means(df, "PINCP", "SEX")
    assert means["test"] == "z test" and len(means["differences"]) == 1
    assert pi.compare_means(df, "PINCP", "REG")["test"] == "design Wald F"
    med = pi.compare_medians(df, "PINCP", "SEX")
    assert med["groups"] == ["1", "2"]
    prop = pi.proportion_interval(df, "HICOV == 2")
    assert prop["validated"] and prop["method"] == "korn_graubard"
    assert not pi.proportion_interval(df, "HICOV == 2", method="wald")["validated"]
    small = pi.two_by_two(df, "DIS == 1", "POVPIP < 100", where="AGEP < 12")
    assert any("fewer than 30" in n for n in small["notes"])
    with pytest.raises(ValueError, match="exactly two"):
        pi.compare_medians(df, "PINCP", "REG")
    assert med["validated"] and med["heaping_share"] < .02
    heaped = df.assign(PINCP=np.round(df.PINCP, -4))           # round-number reporting
    hm = pi.compare_medians(heaped, "PINCP", "SEX")
    assert not hm["validated"] and any("heaped" in n for n in hm["notes"])


def test_large_tables_are_exploratory():
    df = synthetic(); df["BIG"] = np.random.default_rng(1).integers(0, 5, len(df))
    out = pi.independence_test(df, "REG", "BIG")
    assert out["q"] == 8 and not out["validated"] and any("EXPLORATORY" in n for n in out["notes"])


def test_flags_match_the_fixed_audit():
    audit = json.loads((ROOT/"docs/audits/pums_tests_validation.json").read_text())["passed"]
    assert audit["T1/2x2"] and audit["T1/3x4"] and not audit["T3/3x4"] and not audit["T0/2x2"]
    assert pi.INDEPENDENCE_MAX_Q == 6        # 3 x 4 is the largest validated table
    assert audit["P2"] and not audit["P1"] and pi.VALIDATED_PROPORTION_METHOD == "korn_graubard"
    assert all(audit[k] for k in ("I1", "I2", "I3", "I4", "I5", "M1/2group", "M3/3group"))


# ---------------------------------------------------------------- MCP tool

@pytest.mark.parametrize("kwargs", [
    dict(kind="independence", row="REG", col="SEX"),
    dict(kind="two_by_two", exposure="DIS == 1", outcome="POVPIP < 100"),
    dict(kind="means", var="PINCP", by="SEX"),
    dict(kind="medians", var="PINCP", by="SEX"),
    dict(kind="proportion", var="HICOV == 2", where="AGEP >= 19"),
])
def test_test_association_tool_offline(monkeypatch, kwargs):
    from census import workflows_microdata as wm
    monkeypatch.setattr(pums, "fetch_pums", lambda *a, **k: synthetic())
    out = wm.test_association("26", 2022, **kwargs)
    assert out["success"], out
    assert out["summary"] and out["next_step"]
    json.dumps(out)


def test_test_association_tool_failures(monkeypatch):
    from census import workflows_microdata as wm
    monkeypatch.setattr(pums, "fetch_pums", lambda *a, **k: synthetic())
    assert not wm.test_association("26", 2022, "nope")["success"]
    bad = wm.test_association("26", 2022, "two_by_two", exposure="DIS == 1")
    assert not bad["success"] and "outcome" in bad["error"]
    assert not wm.test_association("26", 2022, "two_by_two", exposure="DIS == 1", outcome="AGEP > 200")["success"]
