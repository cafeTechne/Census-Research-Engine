# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 49 survey-weighted PUMS models (frozen with the criterion; PLAN_ROUND_49).

Weighted fits (Newton / IRLS) and the ACS successive-difference replicate (SDR) variance:
Var = 4/80 * sum_r (theta_r - theta)^2 over the 80 replicate-weight refits, each warm-started at the
full-sample estimate. ``W``: (n, 81) with the full-sample weight in column 0.

- ``ordered_fit`` (logit | probit): P(y = j) = F(t_j - x b) - F(t_{j-1} - x b), no intercept in X.
- ``mnlogit_fit``: baseline category 0; X includes the constant.
- ``probit_fit``: binary probit, Fisher scoring.
- ``median_fit``: weighted median (q = .5) regression by iteratively reweighted least squares.
- ``sdr_fit``: full fit + 80 replicate refits -> estimate, SDR SE, normal 90% interval per parameter;
  ``model_se`` gives the comparison model-based SE (weights normalised to n).
"""
import numpy as np
from scipy import stats
from scipy.special import expit

Z90 = stats.norm.ppf(.95)
TOL = 1e-9
MAX_IT = 100
DECREMENT = 1e-14     # Newton decrement g' H^-1 g / 2 below which the start is already the optimum


def _accept(nll, ll):
    return nll >= ll-1e-10*(1+abs(ll))


def _cdf_pdf(link):
    if link == "logit":
        return expit, lambda a: expit(a)*(1-expit(a))
    if link == "probit":
        return stats.norm.cdf, stats.norm.pdf
    raise ValueError("link must be logit or probit")


# ---------------------------------------------------------------- ordered
def _ordered_parts(theta, y, X, link):
    F, f = _cdf_pdf(link)
    p = X.shape[1]; b, t = theta[:p], theta[p:]
    if np.any(np.diff(t) <= 0):
        return None
    eta = X @ b
    J = len(t)+1
    up = np.where(y < J-1, t[np.minimum(y, J-2)], np.inf)-eta
    lo = np.where(y > 0, t[np.maximum(y-1, 0)], -np.inf)-eta
    Fu, Fl = F(up), F(lo)
    P = Fu-Fl
    fu = np.where(np.isfinite(up), f(np.where(np.isfinite(up), up, 0.)), 0.)
    fl = np.where(np.isfinite(lo), f(np.where(np.isfinite(lo), lo, 0.)), 0.)
    return P, fu, fl, J


def _ordered_ll_grad(theta, y, X, w, link):
    parts = _ordered_parts(theta, y, X, link)
    if parts is None:
        return -np.inf, None
    P, fu, fl, J = parts
    if np.any(P <= 0):
        return -np.inf, None
    ll = float(w @ np.log(P))
    gb = -X.T @ (w*(fu-fl)/P)
    gt = np.zeros(J-1)
    for k in range(J-1):
        gt[k] = np.sum(w*((y == k)*fu-(y == k+1)*fl)/P)
    return ll, np.concatenate((gb, gt))


def _newton(fun, theta, h=1e-5):
    """Maximise with Newton steps; Hessian by central differences of the analytic gradient; halving."""
    ll, g = fun(theta)
    if g is None:
        raise ValueError("invalid start")
    for _ in range(MAX_IT):
        k = len(theta); H = np.empty((k, k))
        for i in range(k):
            e = np.zeros(k); e[i] = h
            gp, gm = fun(theta+e)[1], fun(theta-e)[1]
            if gp is None or gm is None:
                raise ValueError("gradient undefined near the estimate")
            H[:, i] = (gp-gm)/(2*h)
        H = (H+H.T)/2
        step = np.linalg.solve(H, -g)
        if g @ step/2 < DECREMENT*(1+abs(ll)):      # Newton decrement (H negative definite)
            return theta, H
        s = 1.
        while s > 1e-6:
            new = theta+s*step; nll, ng = fun(new)
            if ng is not None and _accept(nll, ll):
                break
            s /= 2
        else:
            raise ValueError("Newton step failed")
        theta, ll, g = new, nll, ng
        if np.max(np.abs(s*step)) < TOL:
            return theta, H
    raise ValueError("did not converge")


def ordered_fit(y, X, w, link="logit", start=None):
    y = np.asarray(y, int); X = np.asarray(X, float).reshape(len(y), -1); w = np.asarray(w, float)
    J = int(y.max())+1
    if start is None:
        cum = np.cumsum(np.bincount(y, weights=w, minlength=J))[:-1]/w.sum()
        F = _cdf_pdf(link)[0]
        grid = np.linspace(-8, 8, 16001); t0 = np.interp(cum, F(grid), grid)
        start = np.concatenate((np.zeros(X.shape[1]), t0))
    theta, H = _newton(lambda th: _ordered_ll_grad(th, y, X, w, link), np.asarray(start, float))
    return theta, H


# ---------------------------------------------------------------- multinomial
def mnlogit_fit(y, X, w, start=None):
    y = np.asarray(y, int); X = np.asarray(X, float); w = np.asarray(w, float)
    n, p = X.shape; J = int(y.max())+1; K = (J-1)*p
    Y = np.eye(J)[y][:, 1:]
    B = np.zeros(K) if start is None else np.asarray(start, float).copy()

    def ll_parts(B):
        eta = np.column_stack((np.zeros(n), X @ B.reshape(J-1, p).T))
        eta -= eta.max(axis=1, keepdims=True)
        P = np.exp(eta); P /= P.sum(axis=1, keepdims=True)
        return float(w @ np.log(P[np.arange(n), y])), P[:, 1:]
    ll, P = ll_parts(B)
    for _ in range(MAX_IT):
        g = ((w[:, None]*(Y-P)).T @ X).ravel()
        H = np.zeros((K, K))
        for a in range(J-1):
            for c in range(J-1):
                d = w*P[:, a]*((a == c)-P[:, c])
                H[a*p:(a+1)*p, c*p:(c+1)*p] = -(X.T*d) @ X
        step = np.linalg.solve(H, -g)
        if g @ step/2 < DECREMENT*(1+abs(ll)):      # Newton decrement (H negative definite)
            return B, H
        s = 1.
        while s > 1e-6:
            nll, nP = ll_parts(B+s*step)
            if _accept(nll, ll):
                break
            s /= 2
        else:
            raise ValueError("Newton step failed")
        B, ll, P = B+s*step, nll, nP
        if np.max(np.abs(s*step)) < TOL:
            return B, H
    raise ValueError("did not converge")


# ---------------------------------------------------------------- probit
def probit_fit(y, X, w, start=None):
    y = np.asarray(y, float); X = np.asarray(X, float); w = np.asarray(w, float)
    b = np.zeros(X.shape[1]) if start is None else np.asarray(start, float).copy()
    for _ in range(MAX_IT):
        eta = X @ b
        P = np.clip(stats.norm.cdf(eta), 1e-12, 1-1e-12); f = stats.norm.pdf(eta)
        g = X.T @ (w*f*(y-P)/(P*(1-P)))
        I = (X.T*(w*f**2/(P*(1-P)))) @ X
        step = np.linalg.solve(I, g)
        b = b+step
        if np.max(np.abs(step)) < TOL:
            return b, -I
    raise ValueError("did not converge")


# ---------------------------------------------------------------- median regression
def _median_lp(y, X, w):
    """Exact weighted L1 regression (HiGHS linear program)."""
    from scipy.optimize import linprog
    from scipy.sparse import eye, hstack, csr_matrix
    n, k = X.shape
    A = hstack([csr_matrix(X), eye(n), -eye(n)], format="csr")
    r = linprog(np.concatenate((np.zeros(k), w, w)), A_eq=A, b_eq=y,
                bounds=[(None, None)]*k+[(0, None)]*(2*n), method="highs")
    if not r.success:
        raise ValueError("median regression LP failed")
    return r.x[:k]


def median_fit(y, X, w, start=None, max_it=2000, tol=1e-7):
    """Weighted median regression by IRLS (weights w / max(|r|, 1e-6)), as statsmodels QuantReg for q = .5;
    the exact linear program if IRLS has not converged after ``max_it`` iterations."""
    y = np.asarray(y, float); X = np.asarray(X, float); w = np.asarray(w, float)
    b = np.linalg.lstsq(X*np.sqrt(w)[:, None], y*np.sqrt(w), rcond=None)[0] if start is None else np.asarray(start, float).copy()
    for _ in range(max_it):
        r = np.abs(y-X @ b)
        v = w/np.maximum(r, 1e-6)
        nb = np.linalg.solve((X.T*v) @ X, X.T @ (v*y))
        if np.max(np.abs(nb-b)) < tol:
            return nb, None
        b = nb
    return _median_lp(y, X, w), None


# ---------------------------------------------------------------- SDR wrapper
FITS = dict(ordered_logit=lambda y, X, w, s: ordered_fit(y, X, w, "logit", s),
            ordered_probit=lambda y, X, w, s: ordered_fit(y, X, w, "probit", s),
            mnlogit=mnlogit_fit, probit=probit_fit, median=median_fit)


def sdr_fit(kind, y, X, W, level=.90):
    """Estimate, SDR SE and normal interval for every parameter of ``kind`` (see FITS)."""
    W = np.asarray(W, float)
    fit = FITS[kind]
    theta, H = fit(y, X, W[:, 0], None)
    reps = np.array([fit(y, X, W[:, r], theta)[0] for r in range(1, W.shape[1])])
    d = reps-theta
    se = np.sqrt(4/(W.shape[1]-1)*np.sum(d**2, axis=0))
    z = stats.norm.ppf((1+level)/2)
    return dict(estimate=theta, se=se, lower=theta-z*se, upper=theta+z*se, hessian=H)


def model_se(kind, y, X, w):
    """Comparison: model-based SE with the weights normalised to sum to n (not for median)."""
    w = np.asarray(w, float); wn = w*len(w)/w.sum()
    theta, H = FITS[kind](y, X, wn, None)
    return theta, np.sqrt(np.diag(np.linalg.inv(-H)))
