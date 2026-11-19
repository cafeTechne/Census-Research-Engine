# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 47 procedures (frozen with the criterion; PLAN_ROUND_47).

- ``calibrate``: regression calibration E[X | W, C] with known per-area error variances (moments).
- ``aipw_point`` / ``aipw_calibrated``: AIPW with confounders calibrated within treatment groups;
  percentile bootstrap that re-estimates the calibration (T1).
- ``anderson_rubin``: weak-instrument-robust interval by exact inversion of the AR test (W2).
- ``mediation_calibrated``: indirect effect with a calibrated mediator; percentile bootstrap (S1).
- ``chained_mi``: chained-equations multiple imputation of incomplete covariates, Rubin's rules with
  the Barnard-Rubin df (D1).
"""
import numpy as np
from scipy import stats

Z90 = stats.norm.ppf(.95)


def calibrate(W, S2, C=None):
    """E[X | W, C] for error-prone W (n, p) with per-area error variances S2 (n, p), errors independent
    across columns and of X; C (n, q) error-free. Var(X) = Var(W) - mean(S2) (method of moments)."""
    W = np.asarray(W, float).reshape(len(W), -1); S2 = np.asarray(S2, float).reshape(W.shape)
    V = W if C is None else np.column_stack((W, np.asarray(C, float).reshape(len(W), -1)))
    n, p = W.shape; d = V.shape[1]
    mu = V.mean(axis=0)
    star = np.atleast_2d(np.cov(V, rowvar=False))
    star[np.arange(p), np.arange(p)] -= S2.mean(axis=0)
    if np.linalg.eigvalsh(star)[0] <= 0:
        raise ValueError("calibration: estimated error-free covariance is not positive definite")
    A = np.broadcast_to(star, (n, d, d)).copy()
    A[:, np.arange(p), np.arange(p)] += S2
    sol = np.linalg.solve(A, (V-mu)[:, :, None])[:, :, 0]
    return mu[:p]+sol @ star[:p].T


def _logit_fit(X, T, iters=25):
    b = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1/(1+np.exp(-X @ b)); w = p*(1-p)
        step = np.linalg.solve((X*w[:, None]).T @ X, X.T @ (T-p))
        b += step
        if np.max(np.abs(step)) < 1e-10:
            break
    else:
        raise ValueError("propensity model did not converge")
    return 1/(1+np.exp(-X @ b))


def aipw_point(y, T, Z):
    """AIPW ATE: logistic propensity on (1, Z); separate OLS outcome models per arm."""
    y, T = np.asarray(y, float), np.asarray(T, float)
    X = np.column_stack((np.ones(len(y)), np.asarray(Z, float).reshape(len(y), -1)))
    p = _logit_fit(X, T)
    m = []
    for g in (0., 1.):
        s = T == g
        b = np.linalg.lstsq(X[s], y[s], rcond=None)[0]
        m.append(X @ b)
    m0, m1 = m
    return float(np.mean(m1+T*(y-m1)/p)-np.mean(m0+(1-T)*(y-m0)/(1-p)))


def _calibrate_within(T, W, S2):
    Zh = np.empty(np.asarray(W, float).reshape(len(T), -1).shape)
    for g in (0., 1.):
        s = T == g
        Zh[s] = calibrate(np.asarray(W, float).reshape(len(T), -1)[s], np.asarray(S2, float).reshape(Zh.shape)[s])
    return Zh


def aipw_calibrated(y, T, W, S2, rng, boot=200):
    """AIPW on confounders calibrated within each treatment group (E[Z | W, T]); 90% percentile bootstrap."""
    y, T = np.asarray(y, float), np.asarray(T, float)
    W = np.asarray(W, float).reshape(len(y), -1); S2 = np.asarray(S2, float).reshape(W.shape)
    est = aipw_point(y, T, _calibrate_within(T, W, S2))
    n = len(y); reps = []
    for _ in range(boot):
        i = rng.integers(0, n, n)
        if min(T[i].sum(), (1-T[i]).sum()) < W.shape[1]+3:
            continue
        try:
            reps.append(aipw_point(y[i], T[i], _calibrate_within(T[i], W[i], S2[i])))
        except (ValueError, np.linalg.LinAlgError):
            continue
    if len(reps) < .9*boot:
        raise ValueError("too many failed bootstrap resamples")
    lo, hi = np.quantile(reps, [.05, .95])
    return dict(estimate=est, se=float(np.std(reps, ddof=1)), lower=float(lo), upper=float(hi), resamples=len(reps))


def _partial(C, *cols):
    Q = np.linalg.qr(C)[0]
    return [v-Q @ (Q.T @ v) for v in cols]


def anderson_rubin(y, x, z, controls=None, level=.90):
    """Anderson-Rubin confidence set for the slope of x with one instrument z (homoskedastic F(1, n-k-1)).

    Inverts AR(b) = F statistic of z in (y - b x) ~ 1 + controls + z exactly: {b: A b^2 + B b + C <= 0}.
    Returns kind 'bounded' (lower, upper), 'disjoint' (-inf, lower] U [upper, inf), 'real_line' or 'empty'."""
    y, x, z = (np.asarray(v, float) for v in (y, x, z)); n = len(y)
    C = np.ones((n, 1)) if controls is None else np.column_stack((np.ones(n), np.asarray(controls, float)))
    yt, xt, zt = _partial(C, y, x, z)
    df = n-C.shape[1]-1
    F = stats.f.ppf(level, 1, df)
    a = zt @ zt; zy, zx = zt @ yt, zt @ xt; yy, xy, xx = yt @ yt, xt @ yt, xt @ xt
    A = (df+F)*zx**2-F*a*xx
    B = -2*(df+F)*zy*zx+2*F*a*xy
    Cc = (df+F)*zy**2-F*a*yy
    disc = B*B-4*A*Cc
    if abs(A) < 1e-12*max(abs(B), abs(Cc), 1.):
        raise ValueError("degenerate Anderson-Rubin quadratic")
    if disc < 0:
        kind, lo, hi = ("empty", np.nan, np.nan) if A > 0 else ("real_line", -np.inf, np.inf)
    else:
        r = np.sort([(-B-np.sqrt(disc))/(2*A), (-B+np.sqrt(disc))/(2*A)])
        kind, lo, hi = ("bounded" if A > 0 else "disjoint"), float(r[0]), float(r[1])
    return dict(kind=kind, lower=lo, upper=hi, level=level)


def ar_covers(ar, b):
    if ar["kind"] == "bounded":
        return ar["lower"] <= b <= ar["upper"]
    if ar["kind"] == "disjoint":
        return b <= ar["lower"] or b >= ar["upper"]
    return ar["kind"] == "real_line"


def _ols(X, y):
    return np.linalg.lstsq(X, y, rcond=None)[0]


def _med_point(x, w, s2, y):
    n = len(y); one = np.ones(n)
    a = _ols(np.column_stack((one, x)), w)[1]
    mh = calibrate(w, s2, x)[:, 0]
    b = _ols(np.column_stack((one, x, mh)), y)[2]
    return a*b


def mediation_calibrated(x, w, s2, y, rng, draws=400):
    """Indirect effect a*b: a from W ~ X; b from y ~ X + E[M | W, X]; 90% percentile bootstrap."""
    x, w, s2, y = (np.asarray(v, float) for v in (x, w, s2, y))
    est = _med_point(x, w, s2, y)
    n = len(y); reps = []
    for _ in range(draws):
        i = rng.integers(0, n, n)
        try:
            reps.append(_med_point(x[i], w[i], s2[i], y[i]))
        except (ValueError, np.linalg.LinAlgError):
            continue
    if len(reps) < .9*draws:
        raise ValueError("too many failed bootstrap resamples")
    lo, hi = np.quantile(reps, [.05, .95])
    return dict(estimate=float(est), se=float(np.std(reps, ddof=1)), lower=float(lo), upper=float(hi))


def _hc3(X, y):
    b = _ols(X, y); e = y-X @ b
    XtXi = np.linalg.inv(X.T @ X)
    h = np.einsum("ij,jk,ik->i", X, XtXi, X)
    V = XtXi @ (X.T*(e/(1-h))**2) @ X @ XtXi
    return b, np.diag(V)


def chained_mi(y, X, incomplete, rng, m=20, cycles=10):
    """Chained-equations MI of the columns ``incomplete`` of design X (n, k; NaN = missing); OLS of y on X.

    Each conditional model regresses one incomplete column on the other columns of X and y (rows where it
    is observed) and imputes with a proper Bayesian draw (sigma^2 ~ SSR / chi2, beta ~ N), as in Round 42.
    Start: observed means. HC3 within-imputation variances; Rubin's rules with Barnard-Rubin df.
    Returns per-column dicts (estimate, se, df, lower, upper) for every column of X."""
    y = np.asarray(y, float); X = np.asarray(X, float).copy(); n, k = X.shape
    miss = {j: ~np.isfinite(X[:, j]) for j in incomplete}
    for j in incomplete:
        if miss[j].all() or miss[j].sum() == 0:
            raise ValueError("each incomplete column needs observed and missing values")
    others = [c for c in range(k) if c not in incomplete]
    if not np.isfinite(X[:, others]).all() or not np.isfinite(y).all():
        raise ValueError("only the declared columns may be incomplete")
    est, var = [], []
    for _ in range(m):
        Xi = X.copy()
        for j in incomplete:
            Xi[miss[j], j] = np.nanmean(X[:, j])
        for _ in range(cycles):
            for j in incomplete:
                o = ~miss[j]
                P = np.column_stack([np.delete(Xi, j, axis=1), y])
                Po = P[o]; nob, q = Po.shape
                XtXi = np.linalg.inv(Po.T @ Po)
                bh = XtXi @ Po.T @ Xi[o, j]
                ssr = float(np.sum((Xi[o, j]-Po @ bh)**2))
                s2 = ssr/rng.chisquare(nob-q)
                beta = rng.multivariate_normal(bh, s2*XtXi)
                Xi[miss[j], j] = P[miss[j]] @ beta+rng.standard_normal(miss[j].sum())*np.sqrt(s2)
        b, v = _hc3(Xi, y)
        est.append(b); var.append(v)
    est, var = np.array(est), np.array(var)
    nu_com = n-k
    out = []
    for c in range(k):
        qbar, ubar, bvar = est[:, c].mean(), var[:, c].mean(), np.var(est[:, c], ddof=1)
        T = ubar+(1+1/m)*bvar
        lam = (1+1/m)*bvar/T
        if lam > 0:
            nu_old = (m-1)/lam**2
            nu_obs = (nu_com+1)/(nu_com+3)*nu_com*(1-lam)
            df = 1/(1/nu_old+1/nu_obs)
        else:
            df = float(nu_com)
        t = stats.t.ppf(.95, df); se = float(np.sqrt(T))
        out.append(dict(estimate=float(qbar), se=se, df=float(df), lower=float(qbar-t*se), upper=float(qbar+t*se)))
    return out
