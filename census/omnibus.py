# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 31 omnibus-test and pairwise candidates (PLAN_ROUND_31 section 1).

Frozen with the simulation criterion before the full run. Validation results,
not this module, decide which candidate the engine uses. Every tested
restriction is a subset of coefficients set to 0.

Notation: X (n x p) design, y outcome (proportions for binomial, counts for
Poisson), ``test`` the indices of the q tested coefficients, ``V_sampling``
the 4/80 replicate covariance of the full coefficient vector (zeros when no
analysed variable has replicates).
"""
import numpy as np
from scipy import stats

MC_DRAWS = 20000
MC_SEED = (20261218, 31)
BOOTSTRAP_DRAWS = 399


# ---------------------------------------------------------------------------
# Fits (canonical links; identical to statsmodels at convergence)
# ---------------------------------------------------------------------------

def _glm_parts(eta, model, trials, exposure):
    if model == 'binomial':
        mu = 1/(1+np.exp(-eta))
        return mu, trials*mu*(1-mu)
    mu = np.exp(eta + np.log(exposure))
    return mu, mu


def fit(X, y, model, trials=None, exposure=None, start=None, tol=1e-10, maxiter=100):
    """Return (b, mu, w): coefficients, fitted means and working weights."""
    X, y = np.asarray(X, float), np.asarray(y, float)
    if model == 'linear':
        b = np.linalg.lstsq(X, y, rcond=None)[0]
        return b, X @ b, np.ones(len(y))
    trials = None if trials is None else np.asarray(trials, float)
    exposure = None if exposure is None else np.asarray(exposure, float)
    b = np.zeros(X.shape[1]) if start is None else np.asarray(start, float).copy()
    if start is None:
        if model == 'binomial':
            m = np.clip(np.average(y, weights=trials), 1e-6, 1-1e-6); b[0] = np.log(m/(1-m))
        else:
            b[0] = np.log(max(y.sum(), .5)/exposure.sum())
    for _ in range(maxiter):
        mu, w = _glm_parts(X @ b, model, trials, exposure)
        score = X.T @ ((trials*(y-mu)) if model == 'binomial' else (y-mu))
        step = np.linalg.solve(X.T @ (w[:, None]*X), score)
        b = b + step
        if np.max(np.abs(step)) < tol:
            mu, w = _glm_parts(X @ b, model, trials, exposure)
            return b, mu, w
    raise RuntimeError('IRLS did not converge')


def batched_refits(X, Y, model, start, trials=None, exposure=None, tol=1e-10, maxiter=100):
    """Replicate refits. X: (n,p) or (R,n,p); Y: (n,) or (R,n). Returns (R,p)."""
    X, Y = np.asarray(X, float), np.asarray(Y, float)
    R = X.shape[0] if X.ndim == 3 else Y.shape[0]
    Xs = X if X.ndim == 3 else np.broadcast_to(X, (R,)+X.shape)
    Ys = Y if Y.ndim == 2 else np.broadcast_to(Y, (R, len(Y)))
    if model == 'linear':
        A = np.einsum('rni,rnj->rij', Xs, Xs)
        return np.linalg.solve(A, np.einsum('rni,rn->ri', Xs, Ys)[..., None])[..., 0]
    B = np.broadcast_to(np.asarray(start, float), (R, Xs.shape[2])).copy()
    for _ in range(maxiter):
        eta = np.einsum('rni,ri->rn', Xs, B)
        mu, w = _glm_parts(eta, model, trials, exposure)
        resid = trials*(Ys-mu) if model == 'binomial' else Ys-mu
        step = np.linalg.solve(np.einsum('rni,rn,rnj->rij', Xs, w, Xs), np.einsum('rni,rn->ri', Xs, resid)[..., None])[..., 0]
        B = B + step
        if np.max(np.abs(step)) < tol:
            return B
    raise RuntimeError('replicate IRLS did not converge')


def sampling_covariance(b, replicate_b):
    d = np.asarray(replicate_b, float) - np.asarray(b, float)
    return .05 * d.T @ d


def model_covariance(X, y, mu, w, model, trials=None, kind='HC3'):
    """HC3 (engine default; equals census.models.glm_robust_covariance) or HC2."""
    X, y, mu, w = (np.asarray(a, float) for a in (X, y, mu, w))
    resid = y - mu if model != 'binomial' else np.asarray(trials, float)*(y-mu)
    bread = np.linalg.inv(X.T @ (w[:, None]*X))
    h = w*np.einsum('ij,jk,ik->i', X, bread, X)
    if np.any(h >= 1-1e-12):
        raise ValueError('leverage 1; robust covariance undefined')
    power = {'HC3': 1., 'HC2': .5}[kind]
    s = X*(resid/(1-h)**power)[:, None]
    return bread @ (s.T @ s) @ bread, dict(bread=bread, h=h, resid=resid)


# ---------------------------------------------------------------------------
# Omnibus candidates
# ---------------------------------------------------------------------------

def wald(b, V, test):
    test = np.asarray(test)
    rb, omega = np.asarray(b, float)[test], np.asarray(V, float)[np.ix_(test, test)]
    np.linalg.cholesky((omega+omega.T)/2)
    return float(rb @ np.linalg.solve(omega, rb))


def w0(b, V, test):
    W = wald(b, V, test)
    return dict(statistic=W, p=float(stats.chi2.sf(W, len(test))), df=len(test), reference='chi2')


def w1(b, V, test, n):
    q, p = len(test), len(b)
    if n-p < 1:
        raise ValueError('no residual degrees of freedom')
    F = wald(b, V, test)/q
    return dict(statistic=F, p=float(stats.f.sf(F, q, n-p)), df=q, df_denominator=n-p, reference='F')


def htz_df(X, w, bread, h, test):
    """Hotelling-T2 approximation degrees of freedom (Pustejovsky-Tipton 2018) with
    each unit its own cluster, under the working model; standardised so the result
    does not depend on the scale of the tested coefficients."""
    X, w = np.asarray(X, float), np.asarray(w, float)
    Xt = np.sqrt(w)[:, None]*X
    H = Xt @ bread @ Xt.T
    Q = (np.eye(len(X))-H)**2
    U = (bread @ Xt.T)[np.asarray(test)] / np.sqrt(1-h)        # q x n
    Sigma = (U*np.diag(np.eye(len(X))-H)) @ U.T
    T = np.linalg.inv(np.linalg.cholesky((Sigma+Sigma.T)/2))
    Us = T @ U
    q = len(test)
    total = 0.
    for s_ in range(q):
        for t_ in range(q):
            P = Us[s_]*Us[t_]
            total += 2*float(P @ Q @ P)
    return q*(q+1)/total


def w2(b, V_hc2, V_sampling, test, X, w, bread, h):
    q = len(test)
    nu = htz_df(X, w, bread, h, test)
    if nu-q+1 <= 0:
        raise ValueError('HTZ degrees of freedom too small')
    W = wald(b, np.asarray(V_hc2)+np.asarray(V_sampling), test)
    F = (nu-q+1)/(nu*q)*W
    return dict(statistic=F, p=float(stats.f.sf(F, q, nu-q+1)), df=q, df_denominator=float(nu-q+1),
                nu=float(nu), reference='HTZ F')


def w3(X, y, model, test, V_sampling, rng, trials=None, exposure=None, draws=BOOTSTRAP_DRAWS):
    """Restricted score statistic with a Rademacher wild score bootstrap."""
    X, y, test = np.asarray(X, float), np.asarray(y, float), np.asarray(test)
    keep = np.setdiff1d(np.arange(X.shape[1]), test)
    _, mu, w = fit(X[:, keep], y, model, trials, exposure)
    resid = y-mu if model != 'binomial' else np.asarray(trials, float)*(y-mu)
    J = X.T @ (w[:, None]*X)
    a = np.linalg.solve(J, (X*resid[:, None]).T)[test]        # q x n
    omega = a @ a.T + np.asarray(V_sampling, float)[np.ix_(test, test)]
    L = np.linalg.cholesky((omega+omega.T)/2)
    A = np.linalg.solve(L, a)                                  # whitened, q x n
    S = float(np.sum(A.sum(axis=1)**2))
    signs = rng.choice((-1., 1.), size=(draws, a.shape[1]))
    Sb = np.sum((signs @ A.T)**2, axis=1)
    return dict(statistic=S, p=float((1+np.sum(Sb >= S))/(draws+1)), df=len(test), reference='wild score bootstrap')


def w4(cluster_b, test):
    """Hotelling T2 on the G cluster estimates of the tested coefficients."""
    d = np.asarray(cluster_b, float)[:, np.asarray(test)]
    G, q = d.shape
    if G-q < 1:
        raise ValueError('Hotelling T2 needs more clusters than tested coefficients')
    S = np.cov(d, rowvar=False, ddof=1).reshape(q, q)
    mean = d.mean(axis=0)
    np.linalg.cholesky((S+S.T)/2)
    T2 = float(G*mean @ np.linalg.solve(S, mean))
    F = (G-q)/(q*(G-1))*T2
    return dict(statistic=F, T2=T2, p=float(stats.f.sf(F, q, G-q)), df=q, df_denominator=G-q, reference='Hotelling F')


# ---------------------------------------------------------------------------
# Pairwise comparisons of k groups (reference group's effect is 0)
# ---------------------------------------------------------------------------

def pairs(k):
    return [(i, j) for i in range(k) for j in range(i+1, k)]


def pairwise(effects, V_effects, df, level=.90, seed=MC_SEED, draws=MC_DRAWS):
    """effects: the k-1 non-reference group coefficients; V_effects their covariance.

    Returns differences (group j minus group i, link scale), SEs, t, raw and Holm
    p-values (P1), and max-|t| adjusted p-values with simultaneous intervals (P2).
    """
    g = np.concatenate(([0.], np.asarray(effects, float)))
    k = len(g)
    Vg = np.zeros((k, k)); Vg[1:, 1:] = np.asarray(V_effects, float)
    C = np.zeros((len(pairs(k)), k))
    for r, (i, j) in enumerate(pairs(k)):
        C[r, j], C[r, i] = 1., -1.
    diff = C @ g
    cov = C @ Vg @ C.T
    se = np.sqrt(np.diag(cov))
    if not np.all(se > 0):
        raise ValueError('a pairwise difference has zero variance')
    tval = diff/se
    raw = 2*stats.t.sf(np.abs(tval), df)
    order = np.argsort(raw); m = len(raw); holm = np.empty(m); running = 0.
    for rank, idx in enumerate(order):
        running = max(running, min(1., (m-rank)*raw[idx])); holm[idx] = running
    rng = np.random.default_rng(np.random.SeedSequence(list(seed)))
    Lg = np.linalg.cholesky(Vg[1:, 1:]+1e-15*np.eye(k-1))
    z = np.zeros((draws, k)); z[:, 1:] = rng.standard_normal((draws, k-1)) @ Lg.T
    scale = np.sqrt(rng.chisquare(df, draws)/df)
    maxt = np.max(np.abs((z @ C.T)/se)/scale[:, None], axis=1)
    critical = float(np.quantile(maxt, level))
    adjusted = np.array([(1+np.sum(maxt >= abs(v)))/(draws+1) for v in tval])
    return dict(pairs=pairs(k), difference=diff, se=se, t=tval, p_raw=raw, p_holm=holm,
                p_simultaneous=adjusted, critical=critical,
                lower=diff-critical*se, upper=diff+critical*se)
