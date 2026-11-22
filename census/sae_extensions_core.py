# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 80 frozen core: arcsine Fay-Herriot for proportions and the Rao-Yu temporal Fay-Herriot (backlog N57).

FH (REML): y_i = x_i'b + u_i + e_i, u ~ N(0, A), e ~ N(0, D_i) with D_i known; A maximises the restricted likelihood
on [0, upper] (bounded scalar search); EBLUP theta_i = g_i y_i + (1 - g_i) x_i'b, g_i = A / (A + D_i).

P1 (arcsine; Hadam, Wurz and Kreutzmann 2020): y_i = asin(sqrt(p_i)), D_i = 1 / (4 n_eff_i) with
n_eff_i = p(1 - p) / var from the published direct estimate (a property of the design, so areas with a direct
estimate of 0 keep a positive D). Back-transform with bias correction E[sin^2 t], t ~ N(theta_i, g_i D_i):
p_i = (1 - exp(-2 g_i D_i) cos(2 theta_i)) / 2. MSE by parametric bootstrap (B fits): u* ~ N(0, A),
truth p* = sin^2(clip(x'b + u*, 0, pi/2)), y* = x'b + u* + N(0, D), refit; errors e* = p_hat* - p*.
Intervals: P1 p_i +- z sqrt(mean e*^2), clipped to [0, 1]; P1q [p_i - q_.95(e*), p_i - q_.05(e*)], clipped;
P1b (comparison) the naive back-transform sin^2(theta_i) with its own bootstrap MSE.

T1 (Rao and Yu 1994): y_it = x_it'b + v_i + u_it + e_it, v ~ N(0, s_v), u_it stationary AR(1) with innovation
variance s_u (var s_u / (1 - rho^2)), e_it ~ N(0, D_it), releases t = 1..T non-overlapping. REML over
(log s_v, log s_u, atanh rho) by L-BFGS-B; EBLUP for the last release: x_iT'b + Cov(v_i + u_iT, y_i) V_i^-1 r_i.
MSE by parametric bootstrap (B fits) of the last-release prediction error; normal interval.
"""
import numpy as np
from scipy import optimize, stats

LOG_FLOOR = np.log(1e-8)


# ------------------------------------------------------------------ cross-sectional FH
def fh_fit(y, X, D):
    y = np.asarray(y, float); X = np.asarray(X, float); D = np.asarray(D, float)

    def nll(A):
        V = A+D; Vi = 1/V
        XtViX = X.T@(X*Vi[:, None])
        b = np.linalg.solve(XtViX, X.T@(Vi*y)); r = y-X@b
        return .5*(np.log(V).sum()+np.linalg.slogdet(XtViX)[1]+(r*r*Vi).sum())
    upper = max(4*np.var(y), 1e-6)
    res = optimize.minimize_scalar(nll, bounds=(0.0, upper), method="bounded", options={"xatol": 1e-10})
    A = float(res.x) if nll(res.x) <= nll(0.0) else 0.0
    V = A+D; Vi = 1/V
    b = np.linalg.solve(X.T@(X*Vi[:, None]), X.T@(Vi*y))
    g = A/(A+D)
    return dict(A=A, beta=b, gamma=g, theta=g*y+(1-g)*(X@b), post_var=g*D)


def _backtransform(f):
    th = f["theta"]; v = f["post_var"]
    return (1-np.exp(-2*v)*np.cos(2*th))/2, np.sin(np.clip(th, 0, np.pi/2))**2


def arcsine_fh(p_hat, n_eff, X, B=200, level=.90, rng=None):
    """P1/P1q/P1b for direct proportions p_hat with effective sample sizes n_eff. Returns dict of arrays."""
    rng = rng if rng is not None else np.random.default_rng()
    p_hat = np.clip(np.asarray(p_hat, float), 0, 1); n_eff = np.asarray(n_eff, float)
    if (n_eff <= 0).any():
        raise ValueError("effective sample sizes must be positive")
    y = np.arcsin(np.sqrt(p_hat)); D = 1/(4*n_eff)
    f = fh_fit(y, X, D)
    p_bc, p_nv = _backtransform(f)
    mu = X@f["beta"]
    e_bc = np.empty((B, len(y))); e_nv = np.empty((B, len(y)))
    for b in range(B):
        th = mu+rng.normal(0, np.sqrt(f["A"]), len(y))
        truth = np.sin(np.clip(th, 0, np.pi/2))**2
        fb = fh_fit(th+rng.normal(0, np.sqrt(D)), X, D)
        bc, nv = _backtransform(fb)
        e_bc[b] = bc-truth; e_nv[b] = nv-truth
    z = stats.norm.ppf(.5+level/2)
    mse_bc = (e_bc**2).mean(axis=0); mse_nv = (e_nv**2).mean(axis=0)
    qlo, qhi = np.quantile(e_bc, [(1-level)/2, (1+level)/2], axis=0)
    c = lambda a: np.clip(a, 0, 1)  # noqa: E731
    return dict(estimate=p_bc, mse=mse_bc, lower=c(p_bc-z*np.sqrt(mse_bc)), upper=c(p_bc+z*np.sqrt(mse_bc)),
                q_lower=c(p_bc-qhi), q_upper=c(p_bc-qlo),
                naive=p_nv, naive_mse=mse_nv, naive_lower=c(p_nv-z*np.sqrt(mse_nv)), naive_upper=c(p_nv+z*np.sqrt(mse_nv)),
                A=f["A"], beta=f["beta"], direct_var_transformed=D)


# ------------------------------------------------------------------ Rao-Yu temporal FH
def _ar_corr(rho, T):
    i = np.arange(T)
    return rho**np.abs(i[:, None]-i[None, :])/(1-rho**2)


def _V(par, D):
    sv, su, rho = par
    T = D.shape[1]
    return sv*np.ones((T, T))[None]+su*_ar_corr(rho, T)[None]+np.einsum("it,ts->its", D, np.eye(T))


def ry_fit(y, X, D, start=None):
    """T1 REML. y, D: (m, T); X: (m, T, p). Returns dict(par=(sv, su, rho), beta, Vi)."""
    y = np.asarray(y, float); X = np.asarray(X, float); D = np.asarray(D, float)

    def unpack(t):
        return np.exp(t[0]), np.exp(t[1]), np.tanh(t[2])

    def nll(t):
        par = unpack(t)
        V = _V(par, D)
        sign, logdet = np.linalg.slogdet(V)
        Vi = np.linalg.inv(V)
        XtViX = np.einsum("itp,its,isq->pq", X, Vi, X)
        b = np.linalg.solve(XtViX, np.einsum("itp,its,is->p", X, Vi, y))
        r = y-np.einsum("itp,p->it", X, b)
        return .5*(logdet.sum()+np.linalg.slogdet(XtViX)[1]+np.einsum("it,its,is->", r, Vi, r))
    v0 = max(np.var(y)/3, 1e-4)
    t0 = np.array([np.log(v0), np.log(v0), .3]) if start is None else start
    res = optimize.minimize(nll, t0, method="L-BFGS-B",
                            bounds=[(LOG_FLOOR, np.log(10*v0+1)), (LOG_FLOOR, np.log(10*v0+1)), (-2.5, 2.5)])
    par = unpack(res.x)
    V = _V(par, D); Vi = np.linalg.inv(V)
    XtViX = np.einsum("itp,its,isq->pq", X, Vi, X)
    b = np.linalg.solve(XtViX, np.einsum("itp,its,is->p", X, Vi, y))
    return dict(par=par, beta=b, Vi=Vi, theta_raw=res.x)


def ry_predict_last(f, y, X, D):
    sv, su, rho = f["par"]
    T = y.shape[1]
    c = sv*np.ones(T)+su*_ar_corr(rho, T)[:, T-1]
    r = y-np.einsum("itp,p->it", X, f["beta"])
    return X[:, -1, :]@f["beta"]+np.einsum("t,its,is->i", c, f["Vi"], r)


def rao_yu(y, X, D, B=100, level=.90, rng=None):
    """T1: last-release EBLUP with a parametric-bootstrap MSE and a normal interval."""
    rng = rng if rng is not None else np.random.default_rng()
    y = np.asarray(y, float); X = np.asarray(X, float); D = np.asarray(D, float)
    f = ry_fit(y, X, D)
    est = ry_predict_last(f, y, X, D)
    sv, su, rho = f["par"]
    m, T = y.shape
    mu = np.einsum("itp,p->it", X, f["beta"])
    L = np.linalg.cholesky(_ar_corr(rho, T)*su+1e-12*np.eye(T))
    err = np.empty((B, m))
    for b in range(B):
        v = rng.normal(0, np.sqrt(sv), m)
        u = rng.standard_normal((m, T))@L.T
        truth = mu+v[:, None]+u
        yb = truth+rng.normal(0, np.sqrt(D))
        fb = ry_fit(yb, X, D, start=f["theta_raw"])
        err[b] = ry_predict_last(fb, yb, X, D)-truth[:, -1]
    mse = (err**2).mean(axis=0)
    z = stats.norm.ppf(.5+level/2)
    return dict(estimate=est, mse=mse, lower=est-z*np.sqrt(mse), upper=est+z*np.sqrt(mse), par=f["par"], beta=f["beta"])


def fh_interval_analytic(y, X, D, level=.90):
    """Comparison: single-release FH EBLUP with the g1 + g2 MSE part (no g3), normal interval."""
    f = fh_fit(y, X, D)
    A = f["A"]; Vi = 1/(A+D)
    g1 = f["gamma"]*D
    XtViX_inv = np.linalg.inv(X.T@(X*Vi[:, None]))
    g2 = (1-f["gamma"])**2*np.einsum("ip,pq,iq->i", X, XtViX_inv, X)
    z = stats.norm.ppf(.5+level/2)
    mse = g1+g2
    return dict(estimate=f["theta"], mse=mse, lower=f["theta"]-z*np.sqrt(mse), upper=f["theta"]+z*np.sqrt(mse))
