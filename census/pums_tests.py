# SPDX-License-Identifier: AGPL-3.0-or-later
"""Design-based tests and intervals for PUMS microdata (Round 32).

Every procedure works on a weight matrix W (n records x 81: the full weight then the
80 SDR replicate weights) and uses the PUMS variance Var = 4/80 sum_r (theta_r - theta)^2.
Candidates are fixed with the validation criterion (PLAN_ROUND_32); the audit flags in
``VALIDATED`` (set from ``docs/audits/pums_tests_validation.md``) decide which results are
labelled validated. DataFrame wrappers at the end read PUMS columns through census.pums.
"""
from typing import Any, Dict, Optional

import numpy as np
from scipy import stats

REPLICATES = 80
Z90 = stats.norm.ppf(.95)
AUDIT = "docs/audits/pums_tests_validation.md"
# Set after the fixed run; None means "not yet validated" (exploratory).
VALIDATED: Dict[str, Any] = {}


def sdr_cov(theta, reps):
    """theta: (q,), reps: (80, q) -> (q, q) SDR covariance."""
    d = np.atleast_2d(np.asarray(reps, float)) - np.asarray(theta, float)
    return .05 * d.T @ d


def _split(values):
    """values: (81, ...) -> full, replicates."""
    values = np.asarray(values, float)
    return values[0], values[1:]


def _codes(x):
    levels, codes = np.unique(np.asarray(x), return_inverse=True)
    return levels, codes


# ---------------------------------------------------------------- independence

def shares(row, col, W):
    """Weighted r x c cell shares for every weight column: (81, r, c)."""
    rl, ri = _codes(row); cl, ci = _codes(col)
    R = np.eye(len(rl))[ri]; C = np.eye(len(cl))[ci]
    N = np.einsum('ni,nk,nj->kij', R, np.asarray(W, float), C)
    return rl, cl, N/N.sum(axis=(1, 2), keepdims=True)


def _contrasts(P):
    """Interaction contrasts p_ij - p_i. p_.j for i < r-1, j < c-1 (last axes r, c)."""
    r, c = P.shape[-2:]
    rowm, colm = P.sum(axis=-1), P.sum(axis=-2)
    theta = P - rowm[..., :, None]*colm[..., None, :]
    return theta[..., :r-1, :c-1].reshape(P.shape[:-2]+((r-1)*(c-1),))


def _srs_cov(P, n):
    """SRS covariance of the contrasts at the independence fit (multinomial, delta method)."""
    r, c = P.shape
    a, b = P.sum(axis=1), P.sum(axis=0)
    p0 = np.outer(a, b).ravel()
    cov = (np.diag(p0)-np.outer(p0, p0))/n
    J = np.zeros(((r-1)*(c-1), r*c))
    for i in range(r-1):
        for j in range(c-1):
            row = i*(c-1)+j
            for k in range(r):
                for l in range(c):
                    J[row, k*c+l] = (i == k)*(j == l) - (i == k)*b[j] - (j == l)*a[i]
    return J @ cov @ J.T


def independence(row, col, W):
    """T0 Pearson (comparison), T1/T2 Rao-Scott, T3 design Wald F. Needs >= 2 levels each."""
    rl, cl, P = shares(row, col, W)
    r, c = len(rl), len(cl)
    if r < 2 or c < 2:
        raise ValueError('independence needs at least two categories in each variable')
    n = len(np.asarray(row))
    p, preps = _split(P)
    a, b = p.sum(axis=1), p.sum(axis=0)
    expected = np.outer(a, b)
    if np.any(expected <= 0):
        raise ValueError('a category has zero weighted total')
    X2 = float(n*np.sum((p-expected)**2/expected))
    q = (r-1)*(c-1)
    theta, treps = _contrasts(p), _contrasts(preps)
    Vr, V0 = sdr_cov(theta, treps), _srs_cov(p, n)
    delta = np.real(np.linalg.eigvals(np.linalg.solve(V0, Vr)))
    dbar = float(delta.mean())
    a2 = float(np.sum((delta-dbar)**2)/(q*dbar**2))
    np.linalg.cholesky((Vr+Vr.T)/2)
    W_ = float(theta @ np.linalg.solve(Vr, theta))
    F = (REPLICATES-q+1)/(REPLICATES*q)*W_
    return dict(
        levels=(list(rl), list(cl)), n=n, q=q, shares=p, deff_mean=dbar, deff_a2=a2,
        T0=dict(statistic=X2, df=q, p=float(stats.chi2.sf(X2, q))),
        T1=dict(statistic=X2/dbar, df=q, p=float(stats.chi2.sf(X2/dbar, q))),
        T2=dict(statistic=X2/(dbar*(1+a2)), df=q/(1+a2), p=float(stats.chi2.sf(X2/(dbar*(1+a2)), q/(1+a2)))),
        T3=dict(statistic=F, df=q, df_denominator=REPLICATES-q+1, p=float(stats.f.sf(F, q, REPLICATES-q+1))))


# ---------------------------------------------------------------- domains

def domain_means(y, groups, W):
    gl, gi = _codes(groups); G = np.eye(len(gl))[gi]
    W = np.asarray(W, float); y = np.asarray(y, float)
    return gl, (np.einsum('ng,nk,n->kg', G, W, y)/np.einsum('ng,nk->kg', G, W))


def means_test(y, groups, W):
    """M1 (z), M2 (t(80)) for two groups; M3 (design Wald F) for k >= 2 groups."""
    gl, M = domain_means(y, groups, W)
    if len(gl) < 2:
        raise ValueError('needs at least two groups')
    d = M[:, 1:]-M[:, :1]
    theta, reps = _split(d)
    V = sdr_cov(theta, reps)
    q = len(theta)
    np.linalg.cholesky((V+V.T)/2)
    W_ = float(theta @ np.linalg.solve(V, theta))
    F = (REPLICATES-q+1)/(REPLICATES*q)*W_
    out = dict(levels=list(gl), means=M[0], differences=theta, cov=V,
               M3=dict(statistic=F, df=q, df_denominator=REPLICATES-q+1, p=float(stats.f.sf(F, q, REPLICATES-q+1))))
    if q == 1:
        z = float(theta[0]/np.sqrt(V[0, 0]))
        out['M1'] = dict(statistic=z, p=float(2*stats.norm.sf(abs(z))))
        out['M2'] = dict(statistic=z, df=REPLICATES, p=float(2*stats.t.sf(abs(z), REPLICATES)))
    return out


def _interval(theta, reps, transform=None):
    theta = float(theta); se = float(np.sqrt(sdr_cov([theta], np.asarray(reps)[:, None])[0, 0]))
    lo, hi = theta-Z90*se, theta+Z90*se
    if transform is not None:
        return dict(estimate=float(transform(theta)), se_log=se, lower=float(transform(lo)), upper=float(transform(hi)))
    return dict(estimate=theta, se=se, lower=lo, upper=hi)


def difference_of_proportions(x, groups, W):
    """I1: share of x among group 1 minus group 0 (groups coded 0/1)."""
    _, M = domain_means(np.asarray(x, float), groups, W)
    if M.shape[1] != 2:
        raise ValueError('needs exactly two groups')
    d = M[:, 1]-M[:, 0]
    return _interval(d[0], d[1:])


def two_by_two(exposure, outcome, W):
    """I2 odds ratio, I3 relative risk (exposure and outcome boolean)."""
    e, o = np.asarray(exposure, bool), np.asarray(outcome, bool)
    W = np.asarray(W, float)
    cells = [W[e & o].sum(0), W[e & ~o].sum(0), W[~e & o].sum(0), W[~e & ~o].sum(0)]
    a, b, c, d = cells
    if np.any(np.array([a[0], b[0], c[0], d[0]]) <= 0):
        raise ValueError('a 2x2 cell is empty; odds and risk ratios are undefined (no continuity correction)')
    with np.errstate(divide='ignore', invalid='ignore'):
        lor = np.log(a*d/(b*c)); lrr = np.log((a/(a+b))/(c/(c+d)))
    if not (np.isfinite(lor).all() and np.isfinite(lrr).all()):
        raise ValueError('a replicate 2x2 cell is empty; ratio SE undefined')
    return dict(odds_ratio=_interval(lor[0], lor[1:], np.exp), relative_risk=_interval(lrr[0], lrr[1:], np.exp))


def difference_of_means(y, groups, W):
    """I4: mean of group 1 minus group 0."""
    _, M = domain_means(y, groups, W)
    if M.shape[1] != 2:
        raise ValueError('needs exactly two groups')
    d = M[:, 1]-M[:, 0]
    return _interval(d[0], d[1:])


def difference_of_medians(y, groups, W):
    """I5: weighted median of group 1 minus group 0 (census.pums.weighted_median per column)."""
    from .pums import weighted_median
    gl, gi = _codes(groups)
    if len(gl) != 2:
        raise ValueError('needs exactly two groups')
    y = np.asarray(y, float); W = np.asarray(W, float)
    m = [weighted_median(y[gi == g], W[gi == g]) for g in (0, 1)]
    d = m[1]-m[0]
    return _interval(d[0], d[1:])


def proportion_interval(x, W, method='korn_graubard'):
    """P1 Wald (clipped) or P2 Korn-Graubard for one weighted proportion."""
    x = np.asarray(x, float); W = np.asarray(W, float)
    pk = (W*x[:, None]).sum(0)/W.sum(0)
    p, reps = pk[0], pk[1:]
    se = float(np.sqrt(sdr_cov([p], reps[:, None])[0, 0]))
    n = len(x)
    if method == 'wald':
        return dict(estimate=float(p), se=se, lower=float(max(0., p-Z90*se)), upper=float(min(1., p+Z90*se)), method='wald')
    if method != 'korn_graubard':
        raise ValueError("method must be 'korn_graubard' or 'wald'")
    n_eff = n if se == 0 or p in (0., 1.) else min(n, p*(1-p)/se**2)
    if n > 1:
        n_eff *= (stats.t.ppf(.95, n-1)/stats.t.ppf(.95, REPLICATES))**2
    k = p*n_eff
    lower = 0. if k <= 0 else float(stats.beta.ppf(.05, k, n_eff-k+1))
    upper = 1. if k >= n_eff else float(stats.beta.ppf(.95, k+1, n_eff-k))
    return dict(estimate=float(p), se=se, lower=lower, upper=upper, effective_n=float(n_eff), method='korn_graubard')


# ---------------------------------------------------------------- SDR factors (validation and tests)

def hadamard80():
    """Paley construction I (q = 79, 79 = 3 mod 4): an 80 x 80 Hadamard matrix."""
    q = 79
    residues = {(i*i) % q for i in range(1, q)}
    chi = np.array([0]+[1 if i in residues else -1 for i in range(1, q)])
    Q = np.array([[chi[(j-i) % q] for j in range(q)] for i in range(q)])
    S = np.zeros((q+1, q+1), int)
    S[0, 1:] = 1; S[1:, 0] = -1; S[1:, 1:] = Q
    return np.eye(q+1, dtype=int)+S


def sdr_factors(order):
    """Replicate factors (len(order), 80) for units in sort order: rows (k mod 80, k+1 mod 80)."""
    H = hadamard80()
    k = np.arange(order)
    return 1+2**-1.5*H[k % 80]-2**-1.5*H[(k+1) % 80]
