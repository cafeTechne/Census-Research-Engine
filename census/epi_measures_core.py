# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 84 frozen core: marginal (standardized) risk ratios and differences, prevalence ratios, attributable
fractions and dose-response trends (backlog N61).

Notation: X design matrix (first column intercept), ``col`` the exposure column(s); w analysis weights.

G1 g-computation: fit a weighted logistic model (area binomial: y = successes / trials with weights = trials, a
quasi-binomial mean model; PUMS: 0/1 outcomes with person weights). Marginal risk under exposure value v:
r(v) = sum w_i expit(x_i(v)' b) / sum w_i, where x_i(v) sets the exposure columns to v. RR = r(hi) / r(lo),
RD = r(hi) - r(lo).
- Area SEs (G1a): delta method with the HC3 sandwich covariance of b (population target), log scale for RR.
- PUMS SEs (G1p): refit with each of the 80 SDR replicate weights; var = 4/80 sum(theta_r - theta)^2 (log RR).
P1 prevalence ratio: weighted Poisson log-link fit of the 0/1 outcome (modified Poisson); PR = exp(b_exposure).
P1 SE from SDR refits; P1b the model-based robust sandwich SE (design-blind), reported only.
F1 attributable fraction: PAF = 1 - r(reference) / r(observed), r(observed) = sum w_i expit(x_i' b) / sum w_i;
interval on log(1 - PAF) (G1 SE machinery), back-transformed.
D1 dose-response: L ordered levels (dummies), marginal risks r_0..r_{L-1}; trend statistic = linear contrast
c' r with centred scores c, z = c'r / se, two-sided; departure from linearity: Wald test of the L - 2 orthogonal
higher-order contrasts. SEs as G1 (area delta / PUMS SDR).
"""
import numpy as np
from scipy import stats

REP = 4/80


def expit(x):
    return 1/(1+np.exp(-np.clip(x, -35, 35)))


def logit_fit(y, X, w, start=None, it=100):
    """Weighted logistic (quasi-binomial) fit: y in [0, 1] (proportions with w = trials, or 0/1)."""
    b = np.zeros(X.shape[1]) if start is None else np.array(start, float)
    for _ in range(it):
        p = expit(X@b)
        H = (X*(w*p*(1-p))[:, None]).T@X
        step = np.linalg.solve(H, X.T@(w*(y-p)))
        b = b+step
        if np.max(np.abs(step)) < 1e-10:
            break
    return b


def poisson_fit(y, X, w, start=None, it=100):
    b = np.zeros(X.shape[1]) if start is None else np.array(start, float)
    if start is None:
        b[0] = np.log(max(np.average(y, weights=w), 1e-6))
    for _ in range(it):
        mu = np.exp(np.clip(X@b, -35, 35))
        H = (X*(w*mu)[:, None]).T@X
        step = np.linalg.solve(H, X.T@(w*(y-mu)))
        b = b+step
        if np.max(np.abs(step)) < 1e-10:
            break
    return b


def hc3_cov(y, X, w, b):
    """HC3 sandwich covariance for the weighted logistic fit (area units)."""
    p = expit(X@b)
    V = w*p*(1-p)
    bread = np.linalg.inv((X*V[:, None]).T@X)
    h = np.einsum("ij,jk,ik->i", X*np.sqrt(V)[:, None], bread, X*np.sqrt(V)[:, None])
    u = (w*(y-p))/(1-np.clip(h, 0, .999))
    meat = (X*u[:, None]).T@(X*u[:, None])
    return bread@meat@bread


def set_exposure(X, cols, values):
    Z = X.copy()
    Z[:, cols] = values
    return Z


def marginal_risks(b, X, w, cols, settings):
    """r(v) for each setting v (list of arrays for the exposure columns) and gradients d r / d b."""
    out, grads = [], []
    W = w/w.sum()
    for v in settings:
        Z = set_exposure(X, cols, v)
        p = expit(Z@b)
        out.append(float(W@p))
        grads.append((W*p*(1-p))@Z)
    return np.array(out), np.array(grads)


def observed_risk(b, X, w):
    W = w/w.sum()
    p = expit(X@b)
    return float(W@p), (W*p*(1-p))@X


def _ratio_diff(r, g, cov, level, lo=0, hi=1):
    z = stats.norm.ppf(.5+level/2)
    rr = r[hi]/r[lo]; rd = r[hi]-r[lo]
    g_lrr = g[hi]/r[hi]-g[lo]/r[lo]
    g_rd = g[hi]-g[lo]
    se_l = float(np.sqrt(g_lrr@cov@g_lrr)); se_d = float(np.sqrt(g_rd@cov@g_rd))
    return dict(rr=rr, rr_se_log=se_l, rr_lower=rr*np.exp(-z*se_l), rr_upper=rr*np.exp(z*se_l),
                rd=rd, rd_se=se_d, rd_lower=rd-z*se_d, rd_upper=rd+z*se_d)


def area_marginal(y, X, w, cols, lo, hi, level=.90):
    """G1a + F1 (area binomial): marginal RR, RD (exposure hi vs lo) and PAF (exposure set to lo), HC3 delta."""
    b = logit_fit(y, X, w)
    cov = hc3_cov(y, X, w, b)
    r, g = marginal_risks(b, X, w, cols, [lo, hi])
    out = _ratio_diff(r, g, cov, level)
    ro, go = observed_risk(b, X, w)
    l1 = np.log(r[0]/ro)  # log(1 - PAF)
    gl = g[0]/r[0]-go/ro
    se = float(np.sqrt(gl@cov@gl))
    z = stats.norm.ppf(.5+level/2)
    out.update(paf=1-np.exp(l1), paf_lower=1-np.exp(l1+z*se), paf_upper=1-np.exp(l1-z*se), risks=r, coef=b, cov=cov)
    return out


def replicate_marginal(y, X, W, cols, lo, hi, level=.90):
    """G1p + F1 (PUMS): marginal RR, RD and PAF from weighted logit fits with SDR replicate SEs. W: (n, 81)."""
    def one(w, start=None):
        b = logit_fit(y, X, w, start)
        r, _ = marginal_risks(b, X, w, cols, [lo, hi])
        ro, _ = observed_risk(b, X, w)
        return b, np.array([np.log(r[1]/r[0]), r[1]-r[0], np.log(r[0]/ro)])
    b0, t0 = one(W[:, 0])
    reps = np.array([one(W[:, k], b0)[1] for k in range(1, W.shape[1])])
    se = np.sqrt(REP*((reps-t0)**2).sum(axis=0))
    z = stats.norm.ppf(.5+level/2)
    return dict(rr=np.exp(t0[0]), rr_lower=np.exp(t0[0]-z*se[0]), rr_upper=np.exp(t0[0]+z*se[0]),
                rd=t0[1], rd_lower=t0[1]-z*se[1], rd_upper=t0[1]+z*se[1],
                paf=1-np.exp(t0[2]), paf_lower=1-np.exp(t0[2]+z*se[2]), paf_upper=1-np.exp(t0[2]-z*se[2]),
                se=se)


def prevalence_ratio(y, X, W, col, level=.90):
    """P1 (SDR) and P1b (model robust sandwich) for exp(b_col) from a weighted Poisson log-link fit of 0/1 y."""
    b0 = poisson_fit(y, X, W[:, 0])
    reps = np.array([poisson_fit(y, X, W[:, k], b0)[col] for k in range(1, W.shape[1])])
    se = float(np.sqrt(REP*((reps-b0[col])**2).sum()))
    w = W[:, 0]
    mu = np.exp(X@b0)
    bread = np.linalg.inv((X*(w*mu)[:, None]).T@X)
    u = w*(y-mu)
    cov = bread@((X*u[:, None]).T@(X*u[:, None]))@bread
    se_b = float(np.sqrt(cov[col, col]))
    z = stats.norm.ppf(.5+level/2)
    e = b0[col]
    return dict(pr=float(np.exp(e)), lower=float(np.exp(e-z*se)), upper=float(np.exp(e+z*se)),
                robust_lower=float(np.exp(e-z*se_b)), robust_upper=float(np.exp(e+z*se_b)), se=se, se_robust=se_b)


def _contrasts(L):
    """Orthogonal polynomial contrasts for L levels (rows: linear, then higher order)."""
    x = np.arange(L, dtype=float)
    V = np.vander(x-x.mean(), L, increasing=True)
    Q, _ = np.linalg.qr(V)
    C = Q[:, 1:].T
    if C[0, -1] < 0:
        C[0] = -C[0]
    return C


def dose_response(risks, cov_r, level=.90):
    """D1: linear trend z test and departure-from-linearity Wald test on marginal risks with covariance cov_r."""
    r = np.asarray(risks, float)
    L = len(r)
    C = _contrasts(L)
    lin = C[0]@r
    se = float(np.sqrt(C[0]@cov_r@C[0]))
    zst = lin/se
    out = dict(trend=float(lin), trend_se=se, trend_z=float(zst), trend_p=float(2*stats.norm.sf(abs(zst))))
    if L > 2:
        H = C[1:]
        d = H@r
        V = H@cov_r@H.T
        stat = float(d@np.linalg.solve(V, d))
        out.update(nonlinearity_stat=stat, nonlinearity_df=L-2, nonlinearity_p=float(stats.chi2.sf(stat, L-2)))
    return out


def area_dose(y, X, w, cols, levels, level=.90):
    """D1 for area data: ``cols`` are the L - 1 level dummies; ``levels`` the L settings (rows of dummy values)."""
    b = logit_fit(y, X, w)
    cov = hc3_cov(y, X, w, b)
    r, g = marginal_risks(b, X, w, cols, levels)
    return dose_response(r, g@cov@g.T, level) | dict(risks=r)


def replicate_dose(y, X, W, cols, levels, level=.90):
    """D1 for PUMS: marginal risks per level with SDR covariance."""
    b0 = logit_fit(y, X, W[:, 0])
    r0, _ = marginal_risks(b0, X, W[:, 0], cols, levels)
    reps = np.array([marginal_risks(logit_fit(y, X, W[:, k], b0), X, W[:, k], cols, levels)[0]
                     for k in range(1, W.shape[1])])
    dev = reps-r0
    return dose_response(r0, REP*dev.T@dev, level) | dict(risks=r0)
