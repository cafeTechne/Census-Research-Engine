# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 33 rank and partial correlation intervals and rank-based group procedures.

Frozen with the validation criterion (PLAN_ROUND_33). Variant 1 uses the iid formula;
variant 2 adds the ACS replicate variance (4/80 sum over the 80 replicate sets) on the same
scale. Estimand: the coefficient on the ACS estimates as observed (not corrected for
attenuation). Validation status lives in the calling modules.
"""
import numpy as np
from scipy import stats

FIELLER = {"pearson": 1.0, "spearman": 1.06, "kendall": .437}


def coefficient(x, y, method, z=None):
    x, y = np.asarray(x, float), np.asarray(y, float)
    if method == "pearson":
        return float(np.corrcoef(x, y)[0, 1])
    if method == "spearman":
        return float(stats.spearmanr(x, y)[0])
    if method == "kendall":
        return float(stats.kendalltau(x, y)[0])
    if method == "partial":
        Z = np.column_stack((np.ones(len(x)), np.asarray(z, float)))
        rx = x - Z @ np.linalg.lstsq(Z, x, rcond=None)[0]
        ry = y - Z @ np.linalg.lstsq(Z, y, rcond=None)[0]
        return float(np.corrcoef(rx, ry)[0, 1])
    raise ValueError(f"unknown method {method!r}")


def _iid_var(method, n, n_controls=1):
    if method == "partial":
        return 1.0/(n-3-n_controls)
    return FIELLER[method]/(n-(4 if method == "kendall" else 3))


def correlation_interval(x, y, method, variant=1, level=.90, reps_x=None, reps_y=None, z=None, reps_z=None):
    """r and its interval on atanh scale. reps_*: (n, 80) replicate values (variant 2)."""
    n = len(np.asarray(x))
    r = coefficient(x, y, method, z)
    if not np.isfinite(r) or abs(r) >= 1:
        raise ValueError("coefficient undefined or at +-1")
    var = _iid_var(method, n, 0 if z is None else np.asarray(z).reshape(n, -1).shape[1])
    if variant == 2:
        rr = np.array([coefficient(reps_x[:, k], reps_y[:, k], method,
                                   None if z is None else reps_z[:, k] if reps_z is not None else z)
                       for k in range(np.asarray(reps_x).shape[1])])
        if not np.all(np.abs(rr) < 1):
            raise ValueError("a replicate coefficient is undefined")
        var += .05*np.sum((np.arctanh(rr)-np.arctanh(r))**2)
    crit = stats.norm.ppf((1+level)/2)
    zr = np.arctanh(r)
    return dict(estimate=r, lower=float(np.tanh(zr-crit*np.sqrt(var))), upper=float(np.tanh(zr+crit*np.sqrt(var))),
                se_z=float(np.sqrt(var)), variant=variant, method=method)


def superiority(x, y):
    """Brunner-Munzel: p = P(X < Y) + P(X = Y)/2, its SE and Satterthwaite df."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    nx, ny = len(x), len(y)
    if nx < 2 or ny < 2:
        raise ValueError("each group needs at least two areas")
    rc = stats.rankdata(np.concatenate((x, y)))
    rcx, rcy = rc[:nx], rc[nx:]
    rx, ry = stats.rankdata(x), stats.rankdata(y)
    sx = np.sum((rcx-rx-rcx.mean()+(nx+1)/2)**2)/(nx-1)
    sy = np.sum((rcy-ry-rcy.mean()+(ny+1)/2)**2)/(ny-1)
    p = (rcy.mean()-rcx.mean())/(nx+ny)+.5
    se = np.sqrt(nx*sx+ny*sy)/(nx*ny)
    df = (nx*sx+ny*sy)**2/((nx*sx)**2/(nx-1)+(ny*sy)**2/(ny-1)) if (sx+sy) > 0 else np.inf
    return float(p), float(se), float(df)


def superiority_interval(x, y, variant=1, level=.90, reps_x=None, reps_y=None):
    p, se, df = superiority(x, y)
    if not se > 0:
        raise ValueError("no variation in ranks")
    var = se**2
    if variant == 2:
        pr = np.array([superiority(reps_x[:, k], reps_y[:, k])[0] for k in range(np.asarray(reps_x).shape[1])])
        var += .05*np.sum((pr-p)**2)
    crit = stats.t.ppf((1+level)/2, df)
    s = np.sqrt(var)
    t0 = (p-.5)/s
    return dict(estimate=p, lower=float(max(0., p-crit*s)), upper=float(min(1., p+crit*s)), se=float(s), df=df,
                p_value=float(2*stats.t.sf(abs(t0), df)), variant=variant)


def kruskal(groups):
    groups = [np.asarray(g, float) for g in groups]
    res = stats.kruskal(*groups)
    n = sum(len(g) for g in groups)
    eps2 = float(res.statistic*(n+1)/(n**2-1))
    return dict(statistic=float(res.statistic), p=float(res.pvalue), df=len(groups)-1, epsilon_squared=eps2)
