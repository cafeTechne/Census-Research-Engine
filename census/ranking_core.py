# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 34 ranking procedures (frozen with the validation criterion; PLAN_ROUND_34).

Rank intervals follow Klein, Wright and Wieczorek (2020), "A joint confidence region for an overall
ranking of populations", Annals of Applied Statistics 14(2): area i's interval is
[1 + #{j significantly above i}, K - #{j significantly below i}] from pairwise z tests with
Bonferroni over K-1 (individual) or K(K-1)/2 (joint) comparisons. Rank 1 is the highest value.
"""
import numpy as np
from scipy import stats

MC_DRAWS = 20000
MC_SEED = (20270107, 34)
BOOTSTRAP_DRAWS = 2000


def rank_intervals(x, s, joint=False, level=.90):
    x, s = np.asarray(x, float), np.asarray(s, float)
    K = len(x)
    if K < 2 or not (np.isfinite(x).all() and np.isfinite(s).all() and (s > 0).all()):
        raise ValueError("need at least two areas with finite estimates and positive SEs")
    m = K*(K-1)/2 if joint else K-1
    crit = stats.norm.ppf(1-(1-level)/(2*m))
    above = (x[None, :]-x[:, None]) > crit*np.sqrt(s[:, None]**2+s[None, :]**2)   # j significantly above i
    return 1+above.sum(axis=1), K-above.sum(axis=0)


def bootstrap_rank_intervals(x, s, rng, level=.90, draws=BOOTSTRAP_DRAWS):
    x, s = np.asarray(x, float), np.asarray(s, float)
    sims = x+rng.standard_normal((draws, len(x)))*s
    ranks = len(x)-stats.rankdata(sims, axis=1, method="ordinal").astype(int)+1
    a = (1-level)/2
    return np.quantile(ranks, a, axis=0, method="lower"), np.quantile(ranks, 1-a, axis=0, method="higher")


def reference_covariance(s, w):
    """Cov(x - S 1) for independent area errors (variances s^2) and S = sum w x (w sums to 1)."""
    s, w = np.asarray(s, float), np.asarray(w, float)/np.sum(w)
    A = np.eye(len(s))-np.outer(np.ones(len(s)), w)
    return A @ np.diag(s**2) @ A.T


def versus_reference(d, cov, level=.90, seed=MC_SEED, draws=MC_DRAWS):
    """V1 Holm and V2 simultaneous max-|z| for differences d with covariance cov."""
    d, cov = np.asarray(d, float), np.asarray(cov, float)
    se = np.sqrt(np.diag(cov))
    if not (se > 0).all():
        raise ValueError("a difference has zero variance")
    z = d/se
    raw = 2*stats.norm.sf(np.abs(z))
    order = np.argsort(raw); m = len(raw); holm = np.empty(m); running = 0.
    for rank, i in enumerate(order):
        running = max(running, min(1., (m-rank)*raw[i])); holm[i] = running
    rng = np.random.default_rng(np.random.SeedSequence(list(seed)))
    vals, vecs = np.linalg.eigh((cov+cov.T)/2)
    root = vecs*np.sqrt(np.clip(vals, 0, None))
    maxz = np.max(np.abs(rng.standard_normal((draws, m))@root.T/se), axis=1)
    crit = float(np.quantile(maxz, level))
    adjusted = np.array([(1+np.sum(maxz >= abs(v)))/(draws+1) for v in z])
    return dict(difference=d, se=se, z=z, p_raw=raw, p_holm=holm, p_simultaneous=adjusted, critical=crit,
                lower=d-crit*se, upper=d+crit*se)
