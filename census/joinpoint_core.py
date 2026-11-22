# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 77 frozen core: joinpoint regression and rate ratios of age-adjusted rates (backlog N54).

Model (log-linear segments, as NCI Joinpoint): log r_t = b0 + b1 x_t + sum_j d_j (x_t - x_{tau_j})_+, fitted by
weighted least squares with weights w_t = 1 / var(log r_t) (Poisson: the event count). Joinpoints sit at observed
x values, with at least two observations between a joinpoint and either end and between two joinpoints (Joinpoint
defaults). For a given number of joinpoints k the locations are chosen by grid search (minimum weighted SSE).

- J1 (number of joinpoints): Kim et al. (2000) sequential permutation tests. Test k0 = 0 against K; if rejected,
  k0 + 1 against K, and so on; each test at level alpha / K (Bonferroni). Permutation statistic
  (SSE_k0 - SSE_K) / SSE_K, where permuted data are the k0 fit plus permuted standardised residuals
  sqrt(w)(y - fit); p = (1 + #{T* >= T}) / (B + 1).
- J2 (APC per segment, k known): APC_s = 100 (exp(slope_s) - 1), slope_s = b1 + sum_{j<s} d_j; covariance
  MSE (X'WX)^-1, t interval with n - 2k - 2 df (joinpoint locations counted as parameters), transformed.
- J3 (AAPC over the whole window): exp of the length-weighted mean slope; delta-method SE, t(n - 2k - 2).
- J2b/J3b (empirical quantile, as Joinpoint 5): residual bootstrap of the selected fit (standardised residuals
  resampled with replacement), refit with k fixed and locations re-searched; percentile interval of the last
  segment's APC and of the AAPC.
- R1 (rate ratio of two directly age-adjusted rates; Tiwari et al. 2006): with y, v = sum w^2 d/n^2 and
  wM = max w/n per rate, a = y^2/v (gamma shape), LB = y1/(y2+wM2) * F_{a/2}(2 a1, 2 a2U),
  UB = (y1+wM1)/y2 * F_{1-a/2}(2 a1U, 2 a2), where a2U and a1U use (y + wM, v + wM^2) (Fay-Feuer modification).
- R1b: log-ratio delta method with the gamma variances: var log R = v1/y1^2 + v2/y2^2, normal interval.
"""
import itertools
from functools import lru_cache

import numpy as np
from scipy import stats

MIN_END, MIN_BETWEEN = 2, 2


@lru_cache(maxsize=None)
def configs(n: int, k: int):
    """Joinpoint index tuples (0-based) allowed for n points and k joinpoints; shape (C, k)."""
    if k == 0:
        return np.zeros((1, 0), int)
    idx = range(MIN_END, n-1-MIN_END+1)
    out = [c for c in itertools.combinations(idx, k) if all(b-a >= MIN_BETWEEN+1 for a, b in zip(c, c[1:]))]
    return np.array(out, int).reshape(-1, k)


def max_feasible(n: int) -> int:
    k = 0
    while len(configs(n, k+1)):
        k += 1
    return k


def design(x, cfg):
    """Design matrices (C, n, 2 + k) for joinpoint configurations cfg (C, k)."""
    x = np.asarray(x, float)
    C, k = cfg.shape
    X = np.empty((C, len(x), 2+k))
    X[:, :, 0] = 1.0; X[:, :, 1] = x
    for j in range(k):
        X[:, :, 2+j] = np.maximum(x[None, :]-x[cfg[:, j]][:, None], 0.0)
    return X


def _fit_all(x, Y, w, k):
    """WLS of every column of Y (n,) or (n, B) on every configuration. Returns SSE (C, B) and coefficients."""
    cfg = configs(len(x), k)
    X = design(x, cfg)
    sw = np.sqrt(w)
    Xs = X*sw[None, :, None]
    Y2 = np.atleast_2d(np.asarray(Y, float).T).T if np.ndim(Y) == 2 else np.asarray(Y, float)[:, None]
    Ys = Y2*sw[:, None]
    XtX = np.einsum("cnp,cnq->cpq", Xs, Xs)
    XtY = np.einsum("cnp,nb->cpb", Xs, Ys)
    beta = np.linalg.solve(XtX, XtY)  # (C, p, B)
    resid = Ys[None, :, :]-np.einsum("cnp,cpb->cnb", Xs, beta)
    return cfg, X, XtX, beta, (resid**2).sum(axis=1)


def fit(x, y, w, k):
    """Best k-joinpoint WLS fit: dict(cfg, beta, cov, sse, df, fitted, x)."""
    x = np.asarray(x, float); y = np.asarray(y, float); w = np.asarray(w, float)
    cfg, X, XtX, beta, sse = _fit_all(x, y, w, k)
    c = int(np.argmin(sse[:, 0]))
    n = len(x); df = n-2*k-2
    mse = sse[c, 0]/df if df > 0 else np.nan
    cov = mse*np.linalg.inv(XtX[c])
    return dict(cfg=cfg[c], beta=beta[c, :, 0], cov=cov, sse=float(sse[c, 0]), df=df, fitted=X[c]@beta[c, :, 0],
                x=x, k=k)


def best_sse(x, Y, w, k):
    """Minimum SSE over configurations for each column of Y (n, B)."""
    return _fit_all(x, Y, w, k)[4].min(axis=0)


def permutation_p(x, y, w, k0, k1, B, rng):
    f0 = fit(x, y, w, k0)
    t_obs = (f0["sse"]-best_sse(x, y[:, None], w, k1)[0])/best_sse(x, y[:, None], w, k1)[0]
    sw = np.sqrt(w)
    e = (y-f0["fitted"])*sw
    perm = np.array([rng.permutation(e) for _ in range(B)]).T  # (n, B)
    Ys = f0["fitted"][:, None]+perm/sw[:, None]
    s0 = best_sse(x, Ys, w, k0); s1 = best_sse(x, Ys, w, k1)
    t = (s0-s1)/s1
    return float((1+np.sum(t >= t_obs-1e-12))/(B+1))


def select_k(x, y, w, K, alpha=.05, B=4999, rng=None):
    """J1: Kim et al. (2000) sequential permutation tests, each at alpha / K. Returns (k, p-values)."""
    rng = rng if rng is not None else np.random.default_rng()
    if K == 0:
        return 0, []
    ps = []
    for k0 in range(K):
        p = permutation_p(x, y, w, k0, K, B, rng)
        ps.append(p)
        if p > alpha/K:
            return k0, ps
    return K, ps


def slopes(f):
    k = f["k"]
    L = np.zeros((k+1, 2+k)); L[:, 1] = 1.0
    for s in range(1, k+1):
        L[s, 2:2+s] = 1.0
    return L


def apc_intervals(f, level=.90):
    """J2: per-segment APC with t(n - 2k - 2) intervals. Returns arrays (k+1,) apc, lower, upper, slope, se."""
    L = slopes(f)
    s = L@f["beta"]; se = np.sqrt(np.einsum("sp,pq,sq->s", L, f["cov"], L))
    t = stats.t.ppf(.5+level/2, f["df"]) if f["df"] > 0 else np.nan
    tr = lambda b: 100*(np.exp(b)-1)  # noqa: E731
    return dict(apc=tr(s), lower=tr(s-t*se), upper=tr(s+t*se), slope=s, se=se)


def segment_lengths(f, a=None, b=None):
    x = f["x"]; a = x[0] if a is None else a; b = x[-1] if b is None else b
    cuts = np.concatenate([[x[0]], x[f["cfg"]], [x[-1]]])
    lo = np.clip(cuts[:-1], a, b); hi = np.clip(cuts[1:], a, b)
    if lo[0] > a:
        lo[0] = a
    return hi-lo


def aapc_interval(f, level=.90, a=None, b=None):
    """J3: AAPC over [a, b] (default: the whole series), delta method with t(n - 2k - 2)."""
    Lw = segment_lengths(f, a, b); Lw = Lw/Lw.sum()
    g = Lw@slopes(f)
    m = float(g@f["beta"]); se = float(np.sqrt(g@f["cov"]@g))
    t = stats.t.ppf(.5+level/2, f["df"]) if f["df"] > 0 else np.nan
    tr = lambda b_: 100*(np.exp(b_)-1)  # noqa: E731
    return dict(aapc=tr(m), lower=tr(m-t*se), upper=tr(m+t*se), slope=m, se=se)


def bootstrap_intervals(f, w, B=999, level=.90, rng=None):
    """J2b/J3b: empirical-quantile bootstrap with k fixed (locations re-searched). ``f`` comes from
    fit_with_residuals. Percentile intervals for the last segment's APC and the whole-window AAPC."""
    rng = rng if rng is not None else np.random.default_rng()
    x, k, fitted = f["x"], f["k"], f["fitted"]
    sw = np.sqrt(np.asarray(w, float))
    idx = rng.integers(0, len(x), (len(x), B))
    Ys = fitted[:, None]+f["resid_std"][idx]/sw[:, None]
    cfg, X, XtX, beta, sse = _fit_all(x, Ys, w, k)
    best = np.argmin(sse, axis=0)
    bb = beta[best, :, np.arange(B)]  # (B, p)
    seg = np.cumsum(bb[:, 1:], axis=1)  # slope of each segment
    cuts = np.concatenate([np.full((B, 1), x[0]), x[cfg[best]], np.full((B, 1), x[-1])], axis=1)
    lengths = np.diff(cuts, axis=1)/(x[-1]-x[0])
    mean_slope = (lengths*seg).sum(axis=1)
    q = [(1-level)/2, (1+level)/2]
    tr = lambda b_: 100*(np.exp(b_)-1)  # noqa: E731
    lo, hi = np.quantile(seg[:, -1], q); alo, ahi = np.quantile(mean_slope, q)
    return dict(last_apc_lower=float(tr(lo)), last_apc_upper=float(tr(hi)), aapc_lower=float(tr(alo)),
                aapc_upper=float(tr(ahi)))


def fit_with_residuals(x, y, w, k):
    f = fit(x, y, w, k)
    f["resid_std"] = (np.asarray(y, float)-f["fitted"])*np.sqrt(np.asarray(w, float))
    return f


def tiwari_ratio(d1, n1, d2, n2, wstd, level=.90):
    """R1 (Tiwari et al. 2006) and R1b (log-ratio delta) intervals for the ratio of two directly age-adjusted rates.

    d*, n*: counts and populations per age stratum; wstd: standard weights (normalised to sum 1). Arrays may have a
    leading batch axis."""
    w = np.asarray(wstd, float); w = w/w.sum()
    d1, n1, d2, n2 = (np.asarray(a, float) for a in (d1, n1, d2, n2))
    y1 = (w*d1/n1).sum(axis=-1); y2 = (w*d2/n2).sum(axis=-1)
    v1 = (w**2*d1/n1**2).sum(axis=-1); v2 = (w**2*d2/n2**2).sum(axis=-1)
    m1 = (w/n1).max(axis=-1); m2 = (w/n2).max(axis=-1)
    al = 1-level
    with np.errstate(divide="ignore", invalid="ignore"):
        a1 = y1**2/v1; a2u = (y2+m2)**2/(v2+m2**2); a1u = (y1+m1)**2/(v1+m1**2); a2 = y2**2/v2
        lb = y1/(y2+m2)*stats.f.ppf(al/2, 2*a1, 2*a2u)
        ub = (y1+m1)/y2*stats.f.ppf(1-al/2, 2*a1u, 2*a2)
        lb = np.where(y1 == 0, 0.0, lb)
        ratio = y1/y2
        se = np.sqrt(v1/y1**2+v2/y2**2)
        z = stats.norm.ppf(1-al/2)
    return dict(ratio=ratio, tiwari_lower=lb, tiwari_upper=ub, delta_lower=ratio*np.exp(-z*se),
                delta_upper=ratio*np.exp(z*se), rate1=y1, rate2=y2)
