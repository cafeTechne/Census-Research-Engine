# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 48 procedures (frozen with the criterion; PLAN_ROUND_48).

- ``its_reml`` (I1) / ``its_bootstrap_t`` (I2): interrupted series with AR(1) errors, REML phi.
- ``effective_n`` (C1/A3): Clifford-Richardson-Hemon effective sample size from Moran's I in
  equal-width distance classes (the approximation behind Dutilleul's modified t test).
- ``correlation_neff`` (C1), ``correlation_im`` (C2), ``alpha_neff`` (A3), ``alpha_im`` (A4).
- ``hksj_truncated`` (H2): Paule-Mandel + Hartung-Knapp with the variance factor truncated at 1.
- ``limits_robust`` (B1r/B2r): Bland-Altman limits with moment-based (skewness/kurtosis) SEs.
"""
import numpy as np
from scipy import stats
from scipy.optimize import minimize_scalar

from . import evidence_core as ev
from . import rank_methods as rm

T90 = .95
ZL = 1.645


# ----------------------------------------------------------------- I: interrupted series
def _pw(phi, n):
    """Prais-Winsten transform rows: first row sqrt(1 - phi^2), then x_t - phi x_{t-1}."""
    P = np.eye(n)-phi*np.eye(n, k=-1)
    P[0, 0] = np.sqrt(1-phi**2)
    return P


def _gls(y, X, phi):
    P = _pw(phi, len(y)); Xt, yt = P @ X, P @ y
    XtX = Xt.T @ Xt
    b = np.linalg.solve(XtX, Xt.T @ yt)
    rss = float(np.sum((yt-Xt @ b)**2))
    return b, rss, XtX


def _neg_reml(phi, y, X):
    n, k = X.shape
    _, rss, XtX = _gls(y, X, phi)
    return .5*((n-k)*np.log(rss)+np.linalg.slogdet(XtX)[1]-np.log(1-phi**2))


def reml_ar1(y, X):
    """REML AR(1) regression: phi maximises the restricted likelihood on (-.95, .95)."""
    y, X = np.asarray(y, float), np.asarray(X, float)
    phi = float(minimize_scalar(_neg_reml, bounds=(-.95, .95), args=(y, X), method="bounded",
                                options={"xatol": 1e-6}).x)
    b, rss, XtX = _gls(y, X, phi)
    n, k = X.shape
    s2 = rss/(n-k)
    se = np.sqrt(np.diag(np.linalg.inv(XtX))*s2)
    return b, se, phi


def its_reml(y, X, cols=(2, 3)):
    """I1: REML AR(1) GLS with a t(n - k) reference; intervals for ``cols``."""
    b, se, phi = reml_ar1(y, X)
    c = stats.t.ppf(T90, len(y)-X.shape[1])
    return [dict(estimate=float(b[j]), se=float(se[j]), lower=float(b[j]-c*se[j]), upper=float(b[j]+c*se[j]))
            for j in cols], phi


def its_bootstrap_t(y, X, rng, B=499, cols=(2, 3)):
    """I2: AR(1) residual bootstrap-t around the I1 fit (centred innovations; stationary first value)."""
    y, X = np.asarray(y, float), np.asarray(X, float); n = len(y)
    b, se, phi = reml_ar1(y, X)
    u = y-X @ b
    eps = u[1:]-phi*u[:-1]; eps = eps-eps.mean()
    tstats = []
    for _ in range(B):
        e = rng.choice(eps, n, replace=True)
        us = np.empty(n); us[0] = e[0]/np.sqrt(1-phi**2)
        for t in range(1, n):
            us[t] = phi*us[t-1]+e[t]
        try:
            bs, ses, _ = reml_ar1(X @ b+us, X)
        except np.linalg.LinAlgError:
            continue
        tstats.append([(bs[j]-b[j])/ses[j] for j in cols])
    if len(tstats) < .9*B:
        raise ValueError("too many failed bootstrap refits")
    T = np.array(tstats)
    out = []
    for i, j in enumerate(cols):
        lo_q, hi_q = np.quantile(T[:, i], [.05, .95])
        out.append(dict(estimate=float(b[j]), se=float(se[j]), lower=float(b[j]-hi_q*se[j]), upper=float(b[j]-lo_q*se[j])))
    return out, phi


# ----------------------------------------------------------------- C/A: effective sample size
CLASSES = 13


def class_index(D, classes=CLASSES):
    """Equal-width distance classes on (0, max D]; diagonal gets -1."""
    D = np.asarray(D, float)
    edges = np.linspace(0, D.max(), classes+1)
    idx = np.clip(np.searchsorted(edges, D, side="left")-1, 0, classes-1)
    np.fill_diagonal(idx, -1)
    return idx


def moran_matrix(v, cls, classes=CLASSES):
    """n x n matrix of Moran's I of ``v`` by distance class (1 on the diagonal)."""
    z = np.asarray(v, float); z = z-z.mean(); n = len(z)
    zz = np.outer(z, z); denom = float(z @ z)
    R = np.ones((n, n))
    for c in range(classes):
        m = cls == c
        cnt = m.sum()
        R[m] = (n/cnt)*zz[m].sum()/denom if cnt else 0.
    return R


def effective_n(v, w, cls, classes=CLASSES):
    """Clifford et al. (1989): Var(r) ~ tr(Rx Ry)/n^2 and n_eff = 1 + 1/Var(r), capped at n."""
    n = len(v)
    s = float(np.sum(moran_matrix(v, cls, classes)*moran_matrix(w, cls, classes)))/n**2
    return float(min(n, 1+1/s)) if s > 0 else float(n)


def correlation_neff(x, y, method, cls, variant=1, reps_x=None, reps_y=None, level=.90):
    """C1: the Round 33 interval with n replaced by n_eff (ranks for spearman/kendall)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    vx, vy = (stats.rankdata(x), stats.rankdata(y)) if method in ("spearman", "kendall") else (x, y)
    ne = effective_n(vx, vy, cls)
    base = rm.correlation_interval(x, y, method, variant, level, reps_x, reps_y)
    n = len(x)
    var_iid = rm._iid_var(method, n, 0)
    var_rep = base["se_z"]**2-var_iid
    off = 4 if method == "kendall" else 3
    if ne <= off+1:
        raise ValueError("effective sample size too small")
    var = rm.FIELLER[method]/(ne-off)+var_rep
    zr = np.arctanh(base["estimate"]); c = stats.norm.ppf((1+level)/2)
    return dict(estimate=base["estimate"], lower=float(np.tanh(zr-c*np.sqrt(var))), upper=float(np.tanh(zr+c*np.sqrt(var))),
                n_eff=ne, method=method)


def correlation_im(x, y, method, labels, level=.90):
    """C2: Fisher z of within-cluster coefficients, t(G - 1) interval for their mean."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    zs = []
    for g in np.unique(labels):
        r = rm.coefficient(x[labels == g], y[labels == g], method)
        if not np.isfinite(r) or abs(r) >= 1:
            raise ValueError("cluster coefficient undefined")
        zs.append(np.arctanh(r))
    zs = np.array(zs); G = len(zs)
    m, s = zs.mean(), zs.std(ddof=1)/np.sqrt(G); c = stats.t.ppf((1+level)/2, G-1)
    return dict(estimate=float(np.tanh(m)), lower=float(np.tanh(m-c*s)), upper=float(np.tanh(m+c*s)), method=method)


def cronbach(Z):
    Z = np.asarray(Z, float); k = Z.shape[1]
    return float(k/(k-1)*(1-Z.var(axis=0, ddof=1).sum()/Z.sum(axis=1).var(ddof=1)))


def alpha_neff(Z, cls, level=.90):
    """A3: Feldt's F interval with n replaced by n_eff of the total score (with itself)."""
    Z = np.asarray(Z, float); n, k = Z.shape
    a = cronbach(Z); tot = Z.sum(axis=1)
    ne = effective_n(tot, tot, cls)
    d1, d2 = ne-1, (ne-1)*(k-1); q = (1-level)/2
    return dict(estimate=a, lower=float(1-(1-a)*stats.f.ppf(1-q, d1, d2)), upper=float(1-(1-a)*stats.f.ppf(q, d1, d2)),
                n_eff=ne)


def alpha_im(Z, labels, level=.90):
    """A4: t(G - 1) interval for the mean of log(1 - alpha_g) over clusters."""
    Z = np.asarray(Z, float)
    v = []
    for g in np.unique(labels):
        a = cronbach(Z[labels == g])
        if not a < 1:
            raise ValueError("cluster alpha >= 1")
        v.append(np.log(1-a))
    v = np.array(v); G = len(v)
    m, s = v.mean(), v.std(ddof=1)/np.sqrt(G); c = stats.t.ppf((1+level)/2, G-1)
    return dict(estimate=float(1-np.exp(m)), lower=float(1-np.exp(m+c*s)), upper=float(1-np.exp(m-c*s)))


# ----------------------------------------------------------------- H: pooling
def hksj_truncated(theta, se, level=.90):
    """H2: Paule-Mandel + Hartung-Knapp with var = max(1, q) x the fixed-weight variance 1/sum(w)."""
    theta, se = ev._arr(theta, se); k = len(theta)
    t2 = ev.tau2_pm(theta, se)
    w = 1/(se**2+t2); mu = float(np.sum(w*theta)/w.sum())
    q = float(np.sum(w*(theta-mu)**2)/(k-1))
    var = max(1., q)/w.sum()
    c = stats.t.ppf((1+level)/2, k-1); s = np.sqrt(var)
    return dict(estimate=mu, se=float(s), lower=mu-c*s, upper=mu+c*s, tau2=t2, q=q)


# ----------------------------------------------------------------- B: limits of agreement
def limits_robust(x, y, a_se=None, b_se=None, level=.90):
    """B1r (no SEs) / B2r (SEs given): limits m -+ 1.645 s with Var(s^2) = (m4 - s^4)/n and
    Cov(m, s^2) = m3/n (delta method for s); t(n - 1) critical value."""
    d = np.asarray(y, float)-np.asarray(x, float); n = len(d)
    m = d.mean(); c = d-m
    s2, m3, m4 = c.var(ddof=1), np.mean(c**3), np.mean(c**4)
    err = 0. if a_se is None else float(np.mean(np.asarray(a_se, float)**2+(0 if b_se is None else np.asarray(b_se, float)**2)))
    st2 = s2-err
    if not st2 > 0:
        raise ValueError("sampling error explains all the disagreement; error-free limits undefined")
    st = np.sqrt(st2)
    var_s = max(m4-s2**2, 0.)/n/(4*st2)
    cov_ms = m3/n/(2*st)
    crit = stats.t.ppf((1+level)/2, n-1)
    out = {}
    for name, sign in (("lower", -1), ("upper", 1)):
        lim = m+sign*ZL*st
        se = np.sqrt(max(s2/n+ZL**2*var_s+2*sign*ZL*cov_ms, 0.))
        out[f"{name}_limit"] = float(lim); out[f"{name}_ci"] = (float(lim-crit*se), float(lim+crit*se))
    out["sd"] = float(st)
    return out
