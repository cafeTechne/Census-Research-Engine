# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 85 frozen core: area designations as screening tests (backlog N62).

Areas i with direct proportions p_i, effective sample sizes n_i (n_eff = p(1 - p) / se^2, Round 80) and a
threshold t. Work on the arcsine scale, theta = asin(sqrt(p)), with sampling variance 1 / (4 n).

Q1a (direct): P_i = 1 - Phi((asin sqrt t - asin sqrt p_i) * 2 sqrt n_i), the probability under a flat prior.
Q1b (Fay-Herriot posterior, Round 80 core): EBLUP theta_i and its g1 + g2 MSE from
sae_extensions_core.fh_interval_analytic on (y = asin sqrt p, D = 1 / (4 n), covariates X);
P_i = 1 - Phi((asin sqrt t - theta_i) / sqrt(mse_i)).
Q2 (expected accuracy of a rule designating the set S): E[TP] = sum_{S} P, E[FP] = sum_{S} (1 - P),
E[FN] = sum_{not S} P, E[TN] = sum_{not S} (1 - P); Sn = TP/(TP+FN), Sp = TN/(TN+FP), PPV = TP/(TP+FP),
NPV = TN/(TN+FN) from the expectations; a 90% predictive interval for the realized PPV from the normal
approximation to the Poisson-binomial count of true positives in S (var sum_{S} P(1 - P)).
Rules: "point" p_i >= t; "lower" direct lower 90% bound >= t (arcsine scale); "prob50" and "prob80" P_i >= .5 / .8
(with the Q1 probabilities supplied).
Q3 (rank designation, top k): expected overlap with the true top k by simulation from the Q1b normal posteriors
(reported only).
"""
import numpy as np
from scipy import stats

from . import sae_extensions_core as sx


def arcsine(p):
    return np.arcsin(np.sqrt(np.clip(np.asarray(p, float), 0, 1)))


def q1_direct(p, n, t):
    """Q1a: flat-prior probability that the true proportion exceeds t."""
    return stats.norm.sf((arcsine(t)-arcsine(p))*2*np.sqrt(np.asarray(n, float)))


def q1_fh(p, n, X, t):
    """Q1b: Fay-Herriot (arcsine) posterior probability that the true proportion exceeds t; returns (P, theta, mse)."""
    y = arcsine(p); D = 1/(4*np.asarray(n, float))
    f = sx.fh_interval_analytic(y, X, D)
    P = stats.norm.sf((arcsine(t)-f["estimate"])/np.sqrt(f["mse"]))
    return P, f["estimate"], f["mse"]


def designate(rule, p, n, t, P=None, level=.90):
    """Boolean designation vector for a rule."""
    p = np.asarray(p, float)
    if rule == "point":
        return p >= t
    if rule == "lower":
        z = stats.norm.ppf(.5+level/2)
        lo = np.clip(arcsine(p)-z/(2*np.sqrt(np.asarray(n, float))), 0, np.pi/2)
        return np.sin(lo)**2 >= t
    if rule in ("prob50", "prob80"):
        if P is None:
            raise ValueError("probability rules need P")
        return np.asarray(P) >= (.5 if rule == "prob50" else .8)
    raise ValueError(rule)


def expected_accuracy(S, P, level=.90):
    """Q2: expected TP/FP/FN/TN, Sn, Sp, PPV, NPV for designated set S given probabilities P, with a predictive
    interval for the realized PPV and sensitivity."""
    S = np.asarray(S, bool); P = np.asarray(P, float)
    tp, fp = P[S].sum(), (1-P[S]).sum(); fn, tn = P[~S].sum(), (1-P[~S]).sum()
    z = stats.norm.ppf(.5+level/2)
    k = S.sum()
    sd_tp = np.sqrt((P[S]*(1-P[S])).sum())
    with np.errstate(divide="ignore", invalid="ignore"):
        ppv = tp/k if k else np.nan
        ppv_lo, ppv_hi = (max(0., (tp-z*sd_tp)/k), min(1., (tp+z*sd_tp)/k)) if k else (np.nan, np.nan)
        pos = tp+fn
        sd_pos = np.sqrt((P*(1-P)).sum())
        sn = tp/pos if pos else np.nan
    return dict(designated=int(k), tp=float(tp), fp=float(fp), fn=float(fn), tn=float(tn), sensitivity=float(sn),
                specificity=float(tn/(tn+fp)) if tn+fp else np.nan, ppv=float(ppv),
                npv=float(tn/(tn+fn)) if tn+fn else np.nan, ppv_lower=float(ppv_lo), ppv_upper=float(ppv_hi),
                expected_true_positives_sd=float(sd_tp), expected_qualifying=float(pos), qualifying_sd=float(sd_pos))


def top_k_overlap(theta, mse, k, draws=2000, rng=None):
    """Q3: expected overlap between the estimated top k (by theta) and the true top k under normal posteriors."""
    rng = rng if rng is not None else np.random.default_rng()
    theta = np.asarray(theta, float); sd = np.sqrt(np.asarray(mse, float))
    est = set(np.argsort(-theta)[:k])
    sims = theta[None, :]+sd[None, :]*rng.standard_normal((draws, len(theta)))
    top = np.argsort(-sims, axis=1)[:, :k]
    return float(np.mean([len(est & set(r)) for r in top])/k)
