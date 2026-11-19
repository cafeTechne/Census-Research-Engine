# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 36 composite-index procedures (frozen with the validation criterion; PLAN_ROUND_36).

Standardisation (means, SDs) and loadings are fixed at their full-sample values in every replicate.
"""
import numpy as np
from scipy import stats

Z90 = stats.norm.ppf(.95)


def standardize(X):
    X = np.asarray(X, float)
    m, s = X.mean(axis=0), X.std(axis=0, ddof=1)
    if not (s > 0).all():
        raise ValueError("an indicator has no variation")
    return m, s


def loadings(Z, method="pca"):
    k = Z.shape[1]
    if method == "equal":
        return np.full(k, 1/np.sqrt(k)), None
    if method != "pca":
        raise ValueError("method must be 'pca' or 'equal'")
    vals, vecs = np.linalg.eigh(np.corrcoef(Z, rowvar=False))
    l = vecs[:, -1]
    if l.sum() < 0:
        l = -l
    return l, float(vals[-1]/vals.sum())


def scores(X, m, s, l):
    return ((np.asarray(X, float)-m)/s) @ l


def score_intervals(X, reps, m, s, l, level=.90):
    """reps: (n, k, 80) replicate indicator values. Returns score, SE, lower, upper."""
    sc = scores(X, m, s, l)
    rs = np.einsum("nkr,k->nr", (np.asarray(reps, float)-m[None, :, None])/s[None, :, None], l)
    se = np.sqrt(.05*np.sum((rs-sc[:, None])**2, axis=1))
    z = stats.norm.ppf((1+level)/2)
    return sc, se, sc-z*se, sc+z*se


def cronbach(Z):
    Z = np.asarray(Z, float); k = Z.shape[1]
    return float(k/(k-1)*(1-Z.var(axis=0, ddof=1).sum()/Z.sum(axis=1).var(ddof=1)))


def alpha_interval(Z, level=.90, reps=None, m=None, s=None):
    """A1 Feldt; A2 (reps given) adds the replicate variance of log(1 - alpha) on that scale."""
    Z = np.asarray(Z, float); n, k = Z.shape
    a = cronbach(Z)
    d1, d2 = n-1, (n-1)*(k-1)
    q = (1-level)/2
    if reps is None:
        lo = 1-(1-a)*stats.f.ppf(1-q, d1, d2); hi = 1-(1-a)*stats.f.ppf(q, d1, d2)
        return dict(estimate=a, lower=float(lo), upper=float(hi), variant=1)
    # Feldt's variance of log(1 - alpha) via the F distribution's log-variance, plus replicates.
    var_f = 2*(d1+d2-2)/(d1*(d2-4)) if d2 > 4 else np.inf   # delta-method Var(log F) approx = Var(F)/E(F)^2
    ar = np.array([cronbach((np.asarray(reps)[:, :, r]-m)/s) for r in range(np.asarray(reps).shape[2])])
    var_r = .05*np.sum((np.log(1-ar)-np.log(1-a))**2)
    se = np.sqrt(var_f+var_r)
    lo, hi = 1-(1-a)*np.exp(Z90*se), 1-(1-a)*np.exp(-Z90*se)
    return dict(estimate=a, lower=float(lo), upper=float(hi), variant=2)
