# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 99 frozen core: matching estimators and triple differences (backlog N76; Cunningham, *Mixtape*; Abadie and
Imbens 2006, 2011; Iacus, King and Porro 2012; Gruber 1994).

M1 nearest-neighbour matching (with replacement) on covariates scaled by their standard deviations (normalised
Euclidean distance), M matches per unit:
- bias correction (Abadie-Imbens 2011): imputed Y_i(w) = mean_j [Y_j + mu_w(X_i) - mu_w(X_j)] with mu_w the OLS fit
  in group w;
- variance (Abadie-Imbens 2006): sigma^2(X_i) = (Y_i - Y_l)^2 / 2 with l the nearest unit of the same group;
  ATT: V = [sum_treated (Y_i - Yhat_i(0) - tau)^2 + sum_controls K_i (K_i - 1) / M^2 sigma^2(X_i)] / N1^2;
  ATE: V = sum_i [(Yhat_i(1) - Yhat_i(0) - tau)^2 + ((K_i/M)^2 + (2M - 1)/M * K_i/M) sigma^2(X_i)] / N^2,
  K_i = number of times unit i is used as a match.
M2 coarsened exact matching: each covariate cut at its sample quintiles (or declared cut points); strata with both
groups kept; weights 1 (treated) and (n_T^s / n_C^s)(N_C^m / N_T^m) (controls); ATT among matched treated units by
weighted least squares of y on T with an HC1 standard error.
M3 propensity-score matching: logit propensity, 1:1 nearest neighbour on the logit with caliper 0.2 SD, with
replacement; ATT; 90% percentile interval from 200 bootstrap resamples of units (known to be invalid; Abadie and
Imbens 2008).
T3 triple differences: y_ugt for units u, groups g in {A (affected), B}, periods t; OLS with unit x group, group x
period and unit x period fixed effects and D = treated_u x 1(g = A) x post_t; CR1 standard error clustered by unit.
"""
from typing import Dict, Optional, Sequence

import numpy as np
from scipy import stats

Z90 = stats.norm.ppf(.95)


def _ols(X, y):
    A = np.column_stack([np.ones(len(X)), X])
    return np.linalg.lstsq(A, y, rcond=None)[0]


def _pred(b, X):
    return np.column_stack([np.ones(len(X)), X]) @ b


def _nn(Xs_from, Xs_to, M):
    D = np.sum((Xs_from[:, None, :]-Xs_to[None, :, :])**2, -1)
    return np.argsort(D, 1)[:, :M]


def nn_match(y, T, X, M: int = 4, estimand: str = "ATT") -> Dict[str, float]:
    y = np.asarray(y, float); T = np.asarray(T, int); X = np.asarray(X, float).reshape(len(y), -1)
    Xs = X/X.std(0, ddof=1)
    t, c = np.flatnonzero(T == 1), np.flatnonzero(T == 0)
    b0, b1 = _ols(X[c], y[c]), _ols(X[t], y[t])
    mu = {0: lambda Z: _pred(b0, Z), 1: lambda Z: _pred(b1, Z)}
    K = np.zeros(len(y))
    yhat0 = y.astype(float).copy(); yhat1 = y.astype(float).copy()
    for grp_from, grp_to, w in ((t, c, 0), (c, t, 1)):
        if estimand == "ATT" and w == 1:
            continue
        idx = grp_to[_nn(Xs[grp_from], Xs[grp_to], M)]
        np.add.at(K, idx.ravel(), 1)
        imp = (y[idx]+mu[w](X[grp_from])[:, None]-mu[w](X[idx.ravel()]).reshape(idx.shape)).mean(1)
        (yhat0 if w == 0 else yhat1)[grp_from] = imp
    s2 = np.zeros(len(y))
    for g in (t, c):
        j = g[_nn(Xs[g], Xs[g], 2)[:, 1]]
        s2[g] = (y[g]-y[j])**2/2
    if estimand == "ATT":
        tau = float(np.mean(y[t]-yhat0[t]))
        V = (np.sum((y[t]-yhat0[t]-tau)**2)+np.sum((K[c]*(K[c]-1)/M**2)*s2[c]))/len(t)**2
    else:
        d = yhat1-yhat0; tau = float(d.mean())
        V = np.sum((d-tau)**2+((K/M)**2+(2*M-1)/M*K/M)*s2)/len(y)**2
    se = float(np.sqrt(V))
    return dict(estimate=tau, se=se, lower=tau-Z90*se, upper=tau+Z90*se, estimand=estimand, matches=M)


def cem(y, T, X, cuts: Optional[Sequence[Sequence[float]]] = None) -> Dict[str, float]:
    y = np.asarray(y, float); T = np.asarray(T, int); X = np.asarray(X, float).reshape(len(y), -1)
    codes = []
    for j in range(X.shape[1]):
        cp = np.quantile(X[:, j], [.2, .4, .6, .8]) if cuts is None else np.asarray(cuts[j], float)
        codes.append(np.searchsorted(cp, X[:, j], side="right"))
    key = np.unique(np.column_stack(codes), axis=0, return_inverse=True)[1].ravel()
    nT = np.bincount(key, T == 1); nC = np.bincount(key, T == 0)
    keep = (nT[key] > 0) & (nC[key] > 0)
    NTm, NCm = (keep & (T == 1)).sum(), (keep & (T == 0)).sum()
    if NTm < 2 or NCm < 2:
        raise ValueError("too few matched units after coarsening")
    w = np.where(T == 1, 1.0, (nT[key]/np.maximum(nC[key], 1))*(NCm/NTm))*keep
    A = np.column_stack([np.ones(keep.sum()), T[keep]]); ww = w[keep]; yy = y[keep]
    XtWX = A.T @ (A*ww[:, None]); beta = np.linalg.solve(XtWX, A.T @ (ww*yy))
    r = yy-A @ beta; Ai = np.linalg.inv(XtWX)
    S = A*(ww*r)[:, None]; n = len(yy)
    V = n/(n-2)*Ai @ (S.T @ S) @ Ai
    se = float(np.sqrt(V[1, 1]))
    return dict(estimate=float(beta[1]), se=se, lower=float(beta[1])-Z90*se, upper=float(beta[1])+Z90*se,
                estimand="ATT among matched treated", share_treated_matched=float(NTm/(T == 1).sum()),
                matched=keep)


def ps_match(y, T, X, rng, boot: int = 200) -> Dict[str, float]:
    from .positivity_core import propensity
    y = np.asarray(y, float); T = np.asarray(T, int); X = np.asarray(X, float).reshape(len(y), -1)

    def att(idx):
        yy, TT, XX = y[idx], T[idx], X[idx]
        _, e = propensity(TT, XX)
        lg = np.log(e/(1-e)); cal = .2*lg.std(ddof=1)
        t, c = np.flatnonzero(TT == 1), np.flatnonzero(TT == 0)
        d = np.abs(lg[t][:, None]-lg[c][None, :]); j = d.argmin(1); ok = d[np.arange(len(t)), j] <= cal
        if ok.sum() < 2:
            raise ValueError("no matches within the caliper")
        return float(np.mean(yy[t][ok]-yy[c][j[ok]]))
    est = att(np.arange(len(y)))
    reps = []
    for _ in range(boot):
        try:
            reps.append(att(rng.integers(0, len(y), len(y))))
        except (ValueError, np.linalg.LinAlgError):
            continue
    lo, hi = np.quantile(reps, [.05, .95])
    return dict(estimate=est, se=float(np.std(reps, ddof=1)), lower=float(lo), upper=float(hi), estimand="ATT (caliper)")


def triple_difference(y, unit, group_a, period, treated_unit, post) -> Dict[str, float]:
    """OLS with unit x group, group x period and unit x period fixed effects; D = treated x A x post; CR1 by unit."""
    y = np.asarray(y, float); unit = np.asarray(unit); ga = np.asarray(group_a, int); per = np.asarray(period)
    D = (np.asarray(treated_unit, int)*ga*np.asarray(post, int)).astype(float)

    def dummies(*keys):
        k = np.unique(np.column_stack([np.asarray(x).astype(str) for x in keys]), axis=0, return_inverse=True)[1].ravel()
        M = np.zeros((len(y), k.max()+1)); M[np.arange(len(y)), k] = 1
        return M
    F = np.hstack([dummies(unit, ga), dummies(ga, per), dummies(unit, per)])
    X = np.column_stack([D, F])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y-X @ beta
    # FWL: residualize D on the fixed effects for the sandwich
    dres = D-F @ np.linalg.lstsq(F, D, rcond=None)[0]
    den = float(dres @ dres)
    ug = np.unique(unit); G = len(ug)
    meat = sum(float(np.sum(dres[unit == u]*r[unit == u]))**2 for u in ug)
    n, k = len(y), np.linalg.matrix_rank(X)
    V = G/(G-1)*(n-1)/(n-k)*meat/den**2
    tau, se = float(beta[0]), float(np.sqrt(V))
    t = stats.t.ppf(.95, G-1)
    return dict(estimate=tau, se=se, lower=tau-t*se, upper=tau+t*se, clusters=G)
