# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 87 frozen core: ecologic versus individual-level associations on PUMS (backlog N64; Foundations of
Epidemiology chapter 9).

Persons i in areas j (PUMAs) with weight w_i, exposure x_i, outcome y_i, optional covariates Z.
C1 (within / between / contextual): weighted regression of y on (x_i - xbar_j), xbar_j and Z, where xbar_j is the
weighted area mean of x (recomputed with each weight column). within = coefficient on the centred exposure (the
individual-level association inside areas), between = coefficient on xbar_j, contextual = between - within (the
area-mean association beyond the person's own exposure). Linear model (identity link; for 0/1 outcomes a linear
probability model on the risk-difference scale) - C1; logistic model - C1l (log-odds scale).
C2 (ecologic regression): weighted regression of the area mean outcome ybar_j on xbar_j (and area means of Z), area
weights sum w; the slope is what an area-level (ACS-only) analysis estimates. ecologic gap = C2 slope - C1 within
slope (identity scale).
SEs: refit with each of the 80 SDR replicate weights (area means recomputed); var = 4/80 sum(theta_r - theta)^2.
"""
import numpy as np
from scipy import stats

REP = 4/80


def _area_means(v, area, w, n_areas):
    s = np.bincount(area, weights=w*v, minlength=n_areas)
    t = np.bincount(area, weights=w, minlength=n_areas)
    with np.errstate(divide="ignore", invalid="ignore"):
        return s/t, t


def _wls(y, X, w):
    Xw = X*w[:, None]
    return np.linalg.solve(X.T@Xw, Xw.T@y)


def _logit(y, X, w, start=None):
    b = np.zeros(X.shape[1]) if start is None else start.copy()
    for _ in range(60):
        p = 1/(1+np.exp(-np.clip(X@b, -30, 30)))
        step = np.linalg.solve((X*(w*p*(1-p))[:, None]).T@X, X.T@(w*(y-p)))
        b += step
        if np.max(np.abs(step)) < 1e-10:
            break
    return b


def _one(y, x, area, Z, w, n_areas, logit=False, start=None):
    xbar, _ = _area_means(x, area, w, n_areas)
    X = np.column_stack([np.ones(len(y)), x-xbar[area], xbar[area]]+([Z] if Z is not None else []))
    b = _logit(y, X, w, start) if logit else _wls(y, X, w)
    ybar, tot = _area_means(y, area, w, n_areas)
    keep = tot > 0
    A = [np.ones(keep.sum()), xbar[keep]]
    if Z is not None:
        for k in range(Z.shape[1]):
            A.append(_area_means(Z[:, k], area, w, n_areas)[0][keep])
    eco = _wls(ybar[keep], np.column_stack(A), tot[keep]/tot[keep].sum())[1]
    return b, np.array([b[1], b[2], b[2]-b[1], eco, eco-b[1]])


def decompose(y, x, area, W, Z=None, logit=False, level=.90):
    """C1/C2 (logit=False) or C1l (logit=True; the ecologic slope and gap stay on the identity scale).
    Returns {name: (estimate, se, lower, upper)} for within, between, contextual, ecologic and ecologic_gap."""
    y = np.asarray(y, float); x = np.asarray(x, float); area = np.asarray(area)
    codes, area_i = np.unique(area, return_inverse=True)
    n_areas = len(codes)
    Z = None if Z is None else np.asarray(Z, float).reshape(len(y), -1)
    b0, t0 = _one(y, x, area_i, Z, W[:, 0], n_areas, logit)
    reps = np.array([_one(y, x, area_i, Z, W[:, k], n_areas, logit, b0 if logit else None)[1] for k in range(1, W.shape[1])])
    se = np.sqrt(REP*((reps-t0)**2).sum(axis=0))
    z = stats.norm.ppf(.5+level/2)
    names = ("within", "between", "contextual", "ecologic", "ecologic_gap")
    out = {n: (float(t0[i]), float(se[i]), float(t0[i]-z*se[i]), float(t0[i]+z*se[i])) for i, n in enumerate(names)}
    if logit:
        out.pop("ecologic"); out.pop("ecologic_gap")
    return out, n_areas
