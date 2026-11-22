# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 78 frozen core: staggered-adoption DiD and synthetic control (backlog N55).

Panels are balanced: Y (N units, T periods), first-treated period G_i (np.inf = never treated), periods 0..T-1.

S1 Callaway and Sant'Anna (2021), no covariates (outcome regression and doubly robust coincide):
ATT(g, t) = mean_{G=g}(Y_t - Y_{g-1}) - mean_{C}(Y_t - Y_{g-1}) with a universal base period g - 1 and controls C =
never treated ("never") or not yet treated at t (G > max(t, g - 1); "notyet"). Event-study theta(e) averages
ATT(g, g + e) over cohorts observed at e with cohort-size weights; the overall ATT averages every post-treatment
(g, t) cell with cohort-size weights ("simple" aggregation). Inference: unit-level influence functions,
Rademacher multiplier bootstrap (B draws), SE = (q.75 - q.25) / (z.75 - z.25) of the bootstrap distribution,
pointwise normal intervals and a uniform (sup-t) band for the event study. S1r adds the ACS sampling variance of
the linear estimator, sum c_it^2 se_it^2, in quadrature (reported separately).

S2 Sun and Abraham (2021): OLS of Y on unit and period effects and cohort x relative-period indicators (never
treated as controls; relative period -1 omitted; all other relative periods included), interaction-weighted
event-time effects theta(e) = sum_g share_g(e) beta_{g,e}, overall ATT = average of post (g, e) cells weighted by
cohort size; CR1 state-cluster covariance with the weights fixed; t(N - 1) intervals.

C1 synthetic control (Abadie et al. 2010): simplex weights minimising the pre-period squared error of the treated
unit's outcomes (non-negative least squares with a heavily weighted sum-to-one row). Placebo-in-space: refit with
every donor as the treated unit; statistic post/pre RMSPE ratio; p = rank of the treated ratio among all J + 1.
Pre-fit diagnostic: the treated pre-RMSPE over the median donor-placebo pre-RMSPE.
C2 conformal per-period intervals (Chernozhukov, Wuthrich and Zhu 2021): for post period t and a null theta0, refit
the weights on the pre periods plus t with Y_1t - theta0; residuals u; p = share of cyclic shifts pi of the T0 + 1
residuals with |u_pi(last)| >= |u_last|. The interval collects theta0 on a grid with p > alpha.
"""
import numpy as np
from scipy import optimize, stats

IQR_Z = stats.norm.ppf(.75)-stats.norm.ppf(.25)


# ----------------------------------------------------------------------------- S1 Callaway-Sant'Anna
def cs_cells(Y, G, control="never"):
    """ATT(g, t) for every cohort g and period t != g - 1 with g - 1 >= 0. Returns list of dicts with the linear
    coefficient matrix C (N, T) such that ATT = sum C * Y."""
    N, T = Y.shape
    cohorts = sorted(set(G[np.isfinite(G)].astype(int)))
    out = []
    for g in cohorts:
        base = g-1
        if base < 0:
            continue
        tr = G == g
        for t in range(T):
            if t == base:
                continue
            if control == "never":
                ctl = ~np.isfinite(G)
            else:
                ctl = (G > max(t, base)) & (G != g)
            if tr.sum() == 0 or ctl.sum() == 0:
                continue
            C = np.zeros((N, T))
            C[tr, t] += 1/tr.sum(); C[tr, base] -= 1/tr.sum()
            C[ctl, t] -= 1/ctl.sum(); C[ctl, base] += 1/ctl.sum()
            out.append(dict(g=g, t=t, e=t-g, n_g=int(tr.sum()), C=C, att=float((C*Y).sum())))
    return out


def _influence(C, Y):
    """Unit influence of a linear estimator sum C*Y: psi_i = sum_t C_it (Y_it - mean of Y_t over units sharing the
    coefficient pattern). For difference-of-means estimators this is C_i . (Y_i - group mean)."""
    psi = np.zeros(Y.shape[0])
    # group units by identical coefficient rows
    keys = {}
    for i, row in enumerate(C):
        if np.any(row):
            keys.setdefault(row.tobytes(), []).append(i)
    for idx in keys.values():
        idx = np.array(idx)
        dev = Y[idx]-Y[idx].mean(axis=0)
        psi[idx] = (C[idx]*dev).sum(axis=1)
    return psi


def cs_estimate(Y, G, control="never", B=999, level=.90, rng=None, se_y=None, max_e=None, min_e=None):
    """S1: event-study and overall ATT with multiplier-bootstrap intervals. ``se_y`` (N, T): ACS sampling SEs for
    S1r. Returns dict(event=list of rows, overall=row, band_crit)."""
    rng = rng if rng is not None else np.random.default_rng()
    cells = cs_cells(Y, G, control)
    z = stats.norm.ppf(.5+level/2)
    es = sorted({c["e"] for c in cells})
    if max_e is not None:
        es = [e for e in es if e <= max_e]
    if min_e is not None:
        es = [e for e in es if e >= min_e]
    combos = {}
    for e in es:
        cs = [c for c in cells if c["e"] == e]
        tot = sum(c["n_g"] for c in cs)
        combos[e] = sum(c["C"]*c["n_g"]/tot for c in cs)
    post = [c for c in cells if c["e"] >= 0]
    tot = sum(c["n_g"] for c in post)
    combos["overall"] = sum(c["C"]*c["n_g"]/tot for c in post)
    keys = list(combos)
    psi = np.array([_influence(combos[k], Y) for k in keys])  # (K, N)
    v = rng.choice([-1.0, 1.0], size=(B, Y.shape[0]))
    boot = v@psi.T  # (B, K)
    se = (np.quantile(boot, .75, axis=0)-np.quantile(boot, .25, axis=0))/IQR_Z
    est = np.array([(combos[k]*Y).sum() for k in keys])
    ev = [i for i, k in enumerate(keys) if k != "overall"]
    tmax = np.max(np.abs(boot[:, ev])/se[ev], axis=1) if ev else np.array([np.nan])
    crit = float(np.quantile(tmax, level))
    samp = np.array([np.sqrt(((combos[k]**2)*se_y**2).sum()) for k in keys]) if se_y is not None else np.zeros(len(keys))
    rows = []
    for i, k in enumerate(keys):
        se_r = float(np.sqrt(se[i]**2+samp[i]**2))
        rows.append(dict(key=k, estimate=float(est[i]), se=float(se[i]), lower=float(est[i]-z*se[i]),
                         upper=float(est[i]+z*se[i]), band_lower=float(est[i]-crit*se[i]) if k != "overall" else np.nan,
                         band_upper=float(est[i]+crit*se[i]) if k != "overall" else np.nan,
                         se_acs=float(samp[i]), se_r=se_r, lower_r=float(est[i]-z*se_r), upper_r=float(est[i]+z*se_r)))
    return dict(event=[r for r in rows if r["key"] != "overall"], overall=rows[-1], band_crit=crit)


# ----------------------------------------------------------------------------- S2 Sun-Abraham
def sun_abraham(Y, G, level=.90):
    """S2: interaction-weighted event study with never-treated controls; CR1 cluster covariance by unit."""
    N, T = Y.shape
    cohorts = sorted(set(G[np.isfinite(G)].astype(int)))
    rel_cols = []
    for g in cohorts:
        for e in range(-g, T-g):
            if e != -1:
                rel_cols.append((g, e))
    n = N*T
    unit = np.repeat(np.arange(N), T); per = np.tile(np.arange(T), N)
    X = np.zeros((n, N+T-1+len(rel_cols)))
    X[np.arange(n), unit] = 1.0
    for t in range(1, T):
        X[per == t, N+t-1] = 1.0
    gi = G[unit]
    for j, (g, e) in enumerate(rel_cols):
        X[(gi == g) & (per-g == e), N+T-1+j] = 1.0
    y = Y.reshape(-1)
    keep = X.any(axis=0)
    Xk = X[:, keep]
    beta, *_ = np.linalg.lstsq(Xk, y, rcond=None)
    resid = y-Xk@beta
    XtX_inv = np.linalg.pinv(Xk.T@Xk)
    meat = np.zeros((Xk.shape[1], Xk.shape[1]))
    for i in range(N):
        s = Xk[unit == i].T@resid[unit == i]
        meat += np.outer(s, s)
    p = Xk.shape[1]
    cov = (N/(N-1))*((n-1)/(n-p))*XtX_inv@meat@XtX_inv
    full_idx = np.cumsum(keep)-1
    col = {rc: full_idx[N+T-1+j] for j, rc in enumerate(rel_cols) if keep[N+T-1+j]}
    size = {g: int((G == g).sum()) for g in cohorts}
    tq = stats.t.ppf(.5+level/2, N-1)
    out = {}
    es = sorted({e for (_, e) in col})
    for e in es:
        gs = [g for g in cohorts if (g, e) in col]
        tot = sum(size[g] for g in gs)
        L = np.zeros(p)
        for g in gs:
            L[col[(g, e)]] = size[g]/tot
        out[e] = L
    post = [(g, e) for (g, e) in col if e >= 0]
    tot = sum(size[g] for g, _ in post)
    L = np.zeros(p)
    for g, e in post:
        L[col[(g, e)]] = size[g]/tot
    out["overall"] = L
    rows = []
    for k, L in out.items():
        est = float(L@beta); se = float(np.sqrt(L@cov@L))
        rows.append(dict(key=k, estimate=est, se=se, lower=est-tq*se, upper=est+tq*se))
    return dict(event=[r for r in rows if r["key"] != "overall"], overall=rows[-1])


# ----------------------------------------------------------------------------- C1/C2 synthetic control
def sc_weights(y1, Y0, penalty=1e4):
    """Simplex weights w minimising ||y1 - Y0 w||^2 (Y0: T0 x J). NNLS with a heavily weighted sum-to-one row."""
    scale = max(np.abs(Y0).max(), 1e-12)
    A = np.vstack([Y0/scale, penalty*np.ones((1, Y0.shape[1]))])
    b = np.concatenate([y1/scale, [penalty]])
    w, _ = optimize.nnls(A, b, maxiter=50*A.shape[1])
    s = w.sum()
    return w/s if s > 0 else np.full(Y0.shape[1], 1/Y0.shape[1])


def synth(Y, treated, T0):
    """C1: weights, gaps (T,), pre/post RMSPE for unit ``treated`` with donors = all other rows of Y."""
    donors = [j for j in range(Y.shape[0]) if j != treated]
    w = sc_weights(Y[treated, :T0], Y[donors, :T0].T)
    gap = Y[treated]-w@Y[donors]
    pre = float(np.sqrt(np.mean(gap[:T0]**2))); post = float(np.sqrt(np.mean(gap[T0:]**2)))
    return dict(weights=w, donors=donors, gap=gap, pre_rmspe=pre, post_rmspe=post)


def placebo_test(Y, treated, T0):
    """Placebo-in-space p-value of the post/pre RMSPE ratio and the pre-fit ratio diagnostic."""
    main = synth(Y, treated, T0)
    ratios, pres = [], []
    for j in range(Y.shape[0]):
        if j == treated:
            continue
        s = synth(np.delete(Y, treated, axis=0), j if j < treated else j-1, T0)
        ratios.append(s["post_rmspe"]/max(s["pre_rmspe"], 1e-12)); pres.append(s["pre_rmspe"])
    r = main["post_rmspe"]/max(main["pre_rmspe"], 1e-12)
    p = (1+np.sum(np.array(ratios) >= r))/(len(ratios)+1)
    return dict(main=main, p=float(p), ratio=float(r), prefit_ratio=float(main["pre_rmspe"]/np.median(pres)))


def conformal_interval(Y, treated, T0, t, grid, alpha=.10):
    """C2: conformal interval for the effect at post period t (index >= T0) by test inversion over ``grid``."""
    donors = [j for j in range(Y.shape[0]) if j != treated]
    idx = list(range(T0))+[t]
    Y0 = Y[donors][:, idx].T
    keep = []
    for th in grid:
        y1 = Y[treated, idx].astype(float).copy(); y1[-1] -= th
        w = sc_weights(y1, Y0)
        u = y1-Y0@w
        m = len(u)
        stat = np.abs(np.array([u[(m-1-s) % m] for s in range(m)]))  # cyclic shifts: value landing in last slot
        p = np.mean(stat >= abs(u[-1])-1e-12)
        if p > alpha:
            keep.append(th)
    if not keep:
        return np.nan, np.nan
    return float(min(keep)), float(max(keep))
