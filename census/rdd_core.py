# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 98 frozen core: regression discontinuity (backlog N75; Cunningham, *Mixtape*, RDD chapter; Imbens and
Kalyanaraman 2012; Calonico, Cattaneo and Titiunik 2014; McCrary 2008; Lee and Card 2008).

Running variable x, cutoff c, treatment side x >= c.
- Bandwidth: Imbens-Kalyanaraman (2012) MSE-optimal plug-in for local linear regression with a triangular kernel
  (constant 3.4375; pilot 1.84 sd(x) n^(-1/5); second derivatives from local quadratics with the IK pilot
  bandwidths and regularisation).
- Point estimate (conventional): local linear on each side, triangular weights, bandwidth h.
- R1 robust bias-corrected interval (CCT 2014 with pilot bandwidth b = h): the local quadratic estimate at h and its
  heteroskedasticity-robust (HC1) standard error - with b = h the bias-corrected local linear estimator equals the
  local quadratic one and the robust variance is its variance.
- Variance options: "hc" (independent units), "cluster" (clusters = distinct x values; Lee and Card 2008, for
  discrete running variables), or replicate weights (SDR, 4/R sum of squares) refitting the same estimators.
- Fuzzy design: ratio of the outcome and treatment jumps (both local quadratic for the robust interval); delta
  method with the joint HC covariance, or replicate refits.
- D1 density test (McCrary 2008): histogram with bin width 2 sd(x) n^(-1/2), local linear on bin heights on each
  side (triangular kernel; bandwidth by McCrary's rule 3.348 [s^2 (range) / sum f''^2]^(1/5) from a quartic fit of
  bin heights on each side, averaged, at least 6 bins), theta = ln f+ - ln f-, se = sqrt((1/(n h)) (24/5)
  (1/f+ + 1/f-)).
"""
from typing import Any, Dict, Optional

import numpy as np
from scipy import stats

Z90 = stats.norm.ppf(.95)


def _tri(u):
    return np.clip(1-np.abs(u), 0, None)


def _wls(X, y, w):
    XtWX = X.T @ (X*w[:, None])
    beta = np.linalg.solve(XtWX, X.T @ (w*y))
    return beta, XtWX


def _side_fit(x, y, w, c, h, deg, side):
    sel = (x >= c) if side > 0 else (x < c)
    u = (x[sel]-c)/h
    k = _tri(u)*w[sel]
    keep = k > 0
    X = np.vander(x[sel][keep]-c, deg+1, increasing=True)
    if keep.sum() <= deg+1:
        raise ValueError("too few observations within the bandwidth on one side of the cutoff")
    beta, A = _wls(X, y[sel][keep], k[keep])
    resid = y[sel][keep]-X @ beta
    return beta, A, X, k[keep], resid, np.flatnonzero(sel)[keep]


def ik_bandwidth(x, y, c) -> float:
    x = np.asarray(x, float); y = np.asarray(y, float); n = len(x)
    h1 = 1.84*np.std(x, ddof=1)*n**(-1/5)
    left = (x < c) & (x >= c-h1); right = (x >= c) & (x <= c+h1)
    nl, nr = left.sum(), right.sum()
    if nl < 5 or nr < 5:
        raise ValueError("too few observations near the cutoff for the bandwidth")
    f = (nl+nr)/(2*n*h1)
    s2l, s2r = np.var(y[left], ddof=1), np.var(y[right], ddof=1)
    if not ((x < c).any() and (x >= c).any()):
        raise ValueError("observations are needed on both sides of the cutoff")
    sub = (x >= np.median(x[x < c])) & (x <= np.median(x[x >= c]))   # IK: global cubic between the side medians
    xs = x[sub]-c
    X3 = np.column_stack([np.ones(sub.sum()), xs >= 0, xs, xs**2, xs**3])
    m3 = 6*np.linalg.lstsq(X3, y[sub], rcond=None)[0][4]
    m3 = m3 if abs(m3) > 1e-8 else 1e-8
    nL, nR = (x < c).sum(), (x >= c).sum()
    h2l = 3.56*(s2l/(f*m3**2))**(1/7)*nL**(-1/7); h2r = 3.56*(s2r/(f*m3**2))**(1/7)*nR**(-1/7)
    m2 = []
    for side, h2 in ((-1, h2l), (1, h2r)):
        sel = ((x < c) & (x >= c-h2)) if side < 0 else ((x >= c) & (x <= c+h2))
        if sel.sum() < 6:
            m2.append(0.0); continue
        d = x[sel]-c
        m2.append(2*np.linalg.lstsq(np.column_stack([np.ones(sel.sum()), d, d**2]), y[sel], rcond=None)[0][2])
    nl2 = max(((x < c) & (x >= c-h2l)).sum(), 1); nr2 = max(((x >= c) & (x <= c+h2r)).sum(), 1)
    rl = 720*s2l/(nl2*h2l**4); rr = 720*s2r/(nr2*h2r**4)
    return float(3.4375*((s2l+s2r)/(f*((m2[1]-m2[0])**2+rl+rr)))**(1/5)*n**(-1/5))


def _jump(x, y, w, c, h, deg, vce, cluster):
    fits = [_side_fit(x, y, w, c, h, deg, s) for s in (1, -1)]
    est = fits[0][0][0]-fits[1][0][0]
    var = 0.0
    for beta, A, X, k, r, idx in fits:
        Ai = np.linalg.inv(A)
        S = X*(k*r)[:, None]
        if vce == "cluster":
            g = cluster[idx]
            S = np.vstack([S[g == v].sum(0) for v in np.unique(g)])
            G = len(np.unique(g)); adj = G/(G-1) if G > 1 else 1.0
        else:
            adj = len(r)/(len(r)-X.shape[1])
        V = adj*Ai @ (S.T @ S) @ Ai
        var += V[0, 0]
    return float(est), float(np.sqrt(var)), fits


def rdd(x, y, c: float, h: Optional[float] = None, d=None, weights=None, vce: str = "hc",
        replicate_weights=None, level: float = .90) -> Dict[str, Any]:
    """Sharp (d None) or fuzzy RDD. replicate_weights: (n, R) SDR replicate weights (overrides vce)."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    w = np.ones(len(x)) if weights is None else np.asarray(weights, float)
    z = stats.norm.ppf(.5+level/2)
    h = float(h) if h is not None else ik_bandwidth(x, y if d is None else y, c)
    cl = x if vce == "cluster" else None

    def estimates(ww):
        conv, _, _ = _jump(x, y, ww, c, h, 1, "hc", None)
        rob, _, _ = _jump(x, y, ww, c, h, 2, "hc", None)
        if d is None:
            return conv, rob
        dc, _, _ = _jump(x, np.asarray(d, float), ww, c, h, 1, "hc", None)
        dr, _, _ = _jump(x, np.asarray(d, float), ww, c, h, 2, "hc", None)
        return conv/dc, rob/dr
    conv, rob = estimates(w)
    if replicate_weights is not None:
        R = np.asarray(replicate_weights, float)
        reps = np.array([estimates(R[:, j]) for j in range(R.shape[1])])
        f = 4/R.shape[1]
        se_conv = float(np.sqrt(f*np.sum((reps[:, 0]-conv)**2))); se_rob = float(np.sqrt(f*np.sum((reps[:, 1]-rob)**2)))
        basis = "replicate"
    elif d is None:
        _, se_conv, _ = _jump(x, y, w, c, h, 1, vce, cl)
        _, se_rob, _ = _jump(x, y, w, c, h, 2, vce, cl)
        basis = vce
    else:
        se_conv = _fuzzy_se(x, y, np.asarray(d, float), w, c, h, 1, vce, cl)
        se_rob = _fuzzy_se(x, y, np.asarray(d, float), w, c, h, 2, vce, cl)
        basis = vce
    n_eff = int(((np.abs(x-c) < h) & (w > 0)).sum())
    return dict(estimate=conv, se=se_conv, lower=conv-z*se_conv, upper=conv+z*se_conv,
                robust_estimate=rob, robust_se=se_rob, robust_lower=rob-z*se_rob, robust_upper=rob+z*se_rob,
                bandwidth=h, n_within=n_eff, design="fuzzy" if d is not None else "sharp", variance=basis)


def _fuzzy_se(x, y, d, w, c, h, deg, vce, cl):
    """Delta method for the ratio of jumps with the joint (stacked) HC or cluster covariance."""
    ty, _, fy = _jump(x, y, w, c, h, deg, vce, cl)
    td, _, fd = _jump(x, d, w, c, h, deg, vce, cl)
    tau = ty/td
    var = 0.0
    for (by, A, X, k, ry, idx), (bd, _, _, _, rd, _) in zip(fy, fd):
        Ai = np.linalg.inv(A)
        S = X*(k*(ry-tau*rd))[:, None]           # influence of ty - tau td
        if vce == "cluster":
            g = cl[idx]
            S = np.vstack([S[g == v].sum(0) for v in np.unique(g)])
        V = Ai @ (S.T @ S) @ Ai
        var += V[0, 0]
    return float(np.sqrt(var)/abs(td))


def density_test(x, c: float) -> Dict[str, Any]:
    """McCrary (2008) density discontinuity test."""
    x = np.asarray(x, float); n = len(x)
    b = 2*np.std(x, ddof=1)*n**(-.5)
    lo = c-np.ceil((c-x.min())/b)*b; hi = c+np.ceil((x.max()-c)/b)*b
    edges = np.arange(lo, hi+b/2, b)
    counts, _ = np.histogram(x, edges)
    mids = (edges[:-1]+edges[1:])/2
    hgt = counts/(n*b)
    hs = []
    for side in (1, -1):                         # McCrary (2008) bandwidth rule on each side, averaged
        sel = (mids >= c) if side > 0 else (mids < c)
        u = mids[sel]-c
        P = np.vander(u, 5, increasing=True)
        coef = np.linalg.lstsq(P, hgt[sel], rcond=None)[0]
        s2 = np.mean((hgt[sel]-P @ coef)**2)
        f2 = 2*coef[2]+6*coef[3]*u+12*coef[4]*u**2
        rng_ = np.ptp(u)+b
        hs.append(3.348*(s2*rng_/max(np.sum(f2**2), 1e-300))**(1/5))
    h = max(float(np.mean(hs)), 6*b)
    fs = []
    for side in (1, -1):
        sel = (mids >= c) if side > 0 else (mids < c)
        u = (mids[sel]-c)/h; k = _tri(u); keep = k > 0
        X = np.column_stack([np.ones(keep.sum()), mids[sel][keep]-c])
        fs.append(_wls(X, hgt[sel][keep], k[keep])[0][0])
    fp, fm = fs
    if fp <= 0 or fm <= 0:
        return dict(theta=np.nan, se=np.nan, z=np.nan, p=np.nan, bandwidth=h, bin_width=b)
    theta = np.log(fp)-np.log(fm)
    se = np.sqrt((1/(n*h))*(24/5)*(1/fp+1/fm))
    zz = theta/se
    return dict(theta=float(theta), se=float(se), z=float(zz), p=float(2*stats.norm.sf(abs(zz))), bandwidth=float(h),
                bin_width=float(b))
