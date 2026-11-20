# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 55 frozen core: interrupted series with fewer than 30 points.

I3 ``its_bootstrap_t_bc``: Round 48's AR(1) residual bootstrap-t (``small_spatial_core.its_bootstrap_t``) with
the bootstrap series generated at a bias-corrected AR coefficient, phi_bc = min(.95, phi + (1 + 3 phi)/n)
(Kendall's first-order bias of the AR(1) estimator; phi the REML estimate).
I4 ``its_ewc``: OLS with an equal-weighted cosine (EWC) long-run variance of the scores x_t u_t, nu =
max(2, round(0.4 n^(2/3))) cosine terms, t(nu) reference (Lazarus, Lewis, Stock and Watson 2018).
Both return intervals for the level change (column 2) and slope change (column 3) of ``mci_core.its_design``.
"""
import numpy as np
from scipy import stats

from .small_spatial_core import reml_ar1

T90 = .95


def its_bootstrap_t_bc(y, X, rng, B=499, cols=(2, 3), level=.90):
    y, X = np.asarray(y, float), np.asarray(X, float); n = len(y)
    b, se, phi = reml_ar1(y, X)
    phi_bc = float(min(.95, phi+(1+3*phi)/n))
    u = y-X @ b
    eps = u[1:]-phi*u[:-1]; eps = eps-eps.mean()
    tstats = []
    for _ in range(B):
        e = rng.choice(eps, n, replace=True)
        us = np.empty(n); us[0] = e[0]/np.sqrt(1-phi_bc**2)
        for t in range(1, n):
            us[t] = phi_bc*us[t-1]+e[t]
        try:
            bs, ses, _ = reml_ar1(X @ b+us, X)
        except np.linalg.LinAlgError:
            continue
        tstats.append([(bs[j]-b[j])/ses[j] for j in cols])
    if len(tstats) < .9*B:
        raise ValueError("too many failed bootstrap refits")
    T = np.array(tstats)
    a = (1-level)/2
    out = []
    for i, j in enumerate(cols):
        lo_q, hi_q = np.quantile(T[:, i], [a, 1-a])
        out.append(dict(estimate=float(b[j]), se=float(se[j]), lower=float(b[j]-hi_q*se[j]), upper=float(b[j]-lo_q*se[j])))
    return out, phi, phi_bc


def ewc_terms(n):
    return int(max(2, round(.4*n**(2/3))))


def its_ewc(y, X, cols=(2, 3), level=.90):
    y, X = np.asarray(y, float), np.asarray(X, float); n = len(y)
    XtX_inv = np.linalg.inv(X.T @ X)
    b = XtX_inv @ X.T @ y
    v = X*(y-X @ b)[:, None]
    nu = ewc_terms(n)
    t = np.arange(1, n+1)
    lam = np.array([np.sqrt(2/n)*(np.cos(np.pi*j*(t-.5)/n) @ v) for j in range(1, nu+1)])
    omega = lam.T @ lam/nu
    V = XtX_inv @ (n*omega) @ XtX_inv
    crit = stats.t.ppf((1+level)/2, nu)
    out = []
    for j in cols:
        s = float(np.sqrt(V[j, j]))
        if not np.isfinite(s) or s <= 0:
            raise ValueError("EWC variance undefined")
        out.append(dict(estimate=float(b[j]), se=s, lower=float(b[j]-crit*s), upper=float(b[j]+crit*s), df=nu))
    return out


# Round 63: interrupted series below 20 points.
def _bootstrap_tstats(y, X, b, phi_gen, phi_resid, rng, B, cols):
    n = len(y)
    u = y-X @ b
    eps = u[1:]-phi_resid*u[:-1]; eps = eps-eps.mean()
    tstats = []
    for _ in range(B):
        e = rng.choice(eps, n, replace=True)
        us = np.empty(n); us[0] = e[0]/np.sqrt(1-phi_gen**2)
        for t in range(1, n):
            us[t] = phi_gen*us[t-1]+e[t]
        try:
            bs, ses, _ = reml_ar1(X @ b+us, X)
        except np.linalg.LinAlgError:
            continue
        tstats.append([(bs[j]-b[j])/ses[j] for j in cols])
    if len(tstats) < .9*B:
        raise ValueError("too many failed bootstrap refits")
    return np.array(tstats)


def its_bootstrap_t_cons(y, X, rng, B=499, cols=(2, 3), level=.90):
    """I6: I3 with each critical value the larger of the bootstrap-t quantile and the t(n - p - 1) quantile."""
    y, X = np.asarray(y, float), np.asarray(X, float); n, k = X.shape
    b, se, phi = reml_ar1(y, X)
    phi_bc = float(min(.95, phi+(1+3*phi)/n))
    T = _bootstrap_tstats(y, X, b, phi_bc, phi, rng, B, cols)
    a = (1-level)/2; tq = stats.t.ppf(1-a, n-k-1)
    out = []
    for i, j in enumerate(cols):
        lo_q, hi_q = np.quantile(T[:, i], [a, 1-a])
        hi_c, lo_c = max(hi_q, tq), min(lo_q, -tq)
        out.append(dict(estimate=float(b[j]), se=float(se[j]), lower=float(b[j]-hi_c*se[j]), upper=float(b[j]-lo_c*se[j])))
    return out, phi, phi_bc


def its_bootstrap_t_bb(y, X, rng, B=499, B1=199, cols=(2, 3), level=.90):
    """I7: bootstrap-t at an AR coefficient bias-corrected by a first-level parametric bootstrap (199 series at the
    REML phi; phi_bb = min(.95, 2 phi - mean phi*))."""
    y, X = np.asarray(y, float), np.asarray(X, float); n = len(y)
    b, se, phi = reml_ar1(y, X)
    u = y-X @ b
    sd = float(np.std(u[1:]-phi*u[:-1], ddof=1))
    phis = []
    for _ in range(B1):
        e = rng.standard_normal(n)*sd
        us = np.empty(n); us[0] = e[0]/np.sqrt(1-phi**2)
        for t in range(1, n):
            us[t] = phi*us[t-1]+e[t]
        try:
            phis.append(reml_ar1(X @ b+us, X)[2])
        except np.linalg.LinAlgError:
            continue
    if len(phis) < .9*B1:
        raise ValueError("too many failed first-level refits")
    phi_bb = float(np.clip(2*phi-np.mean(phis), -.95, .95))
    T = _bootstrap_tstats(y, X, b, phi_bb, phi, rng, B, cols)
    a = (1-level)/2
    out = []
    for i, j in enumerate(cols):
        lo_q, hi_q = np.quantile(T[:, i], [a, 1-a])
        out.append(dict(estimate=float(b[j]), se=float(se[j]), lower=float(b[j]-hi_q*se[j]), upper=float(b[j]-lo_q*se[j])))
    return out, phi, phi_bb
