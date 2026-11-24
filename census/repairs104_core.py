# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 104 frozen candidate repairs for five exploratory measures (N83-N87).

Each candidate addresses a concrete defect identified in the Round 91, 94, 96, 99 and 102 audits:
- P2 (meta prediction interval): Nagashima-Noma-Furukawa (2019) confidence-distribution prediction interval using the
  exact Q-profile tau^2 distribution (fixes point-plug-in tau^2 = 0 under-coverage at moderate I^2).
- R2 (meta-regression): truncated Knapp-Hartung variance factor s^2 = max(1.0, sum w e^2 / (k - p)) (matching Round
  48's pooling repair).
- E2 (small-study test): random-effects weighted Egger / Thompson-Sharp regression (weights 1 / (v_i + tau^2_reml)).
- M1b-ATT (nearest-neighbour matching ATT): Abadie-Imbens bias-corrected matching with Kish effective control sample
  size t(df_eff) critical value (replaces normal Z90 under limited overlap).
- B3 (BYM2 disease mapping): grid integration with the Riebler et al. (2016) PC prior on sigma times the log-grid
  Jacobian (log w_prior = log(sigma) - lambda * sigma, fixing the implicit 1/sigma pile-up at sigma = 0.03).
- M3 (IP-weighted MSM): baseline-L0-stabilized IP weights (Hernan & Robins ch. 19-21) with delete-one-unit cluster
  jackknife t(G - 1) intervals.
- MD2 (WHO mean differences mdm_w, mdb_w): replicate bias-corrected estimate max(0, 2*est - mean(reps)) with
  identity-scale replicate SE, plus evaluation of the max_group_cv <= 0.10 gate on uncorrected mdm_w/mdb_w.
"""
from typing import Any, Dict, Optional, Sequence, Tuple, Union

import numpy as np
from scipy import optimize, stats

from . import disease_mapping_core as dmc
from . import inequality_monitoring_core as imc
from . import matching_core as matc
from . import meta_core as metac
from . import msm_core as msmc


# ---------------------------------------------------------------------------
# 1. Meta-analysis repairs (Round 102 -> P2, R2, E2)
# ---------------------------------------------------------------------------

def prediction_interval_nnf(y, v, level: float = .90, draws: int = 2000, rng=None) -> Tuple[float, float]:
    """Nagashima-Noma-Furukawa (2019) parametric prediction interval integrating over the exact Q-profile tau^2
    confidence distribution: draw q_b ~ chi2(k-1), invert Q_gen(tau^2_b) = q_b (0 if Q_gen(0) <= q_b), and sample
    theta_new - mu_hat from N(0, tau^2_b + 1 / sum(1/(v + tau^2_b)))."""
    y = np.asarray(y, float); v = np.asarray(v, float); k = len(y)
    if k < 3:
        return (-np.inf, np.inf)
    rng = rng or np.random.default_rng(20284041)

    def Q_gen(t):
        w = 1.0 / (v + t)
        mu = np.sum(w * y) / np.sum(w)
        return float(np.sum(w * (y - mu) ** 2))

    # Build a fast monotone interpolation grid for Q_gen(t) -> t so 2000 draws take < 1 ms
    q0 = Q_gen(0.0)
    t_hi = max(1.0, 20.0 * float(np.var(y, ddof=1)))
    while Q_gen(t_hi) > stats.chi2.ppf(1e-4, k - 1) and t_hi < 1e8:
        t_hi *= 4.0
    t_grid = np.concatenate([[0.0], np.geomspace(1e-6 * max(float(np.mean(v)), 1e-6), t_hi, 120)])
    q_grid = np.array([Q_gen(t) for t in t_grid])
    # q_grid is strictly decreasing in t_grid; reverse for np.interp
    q_rev = q_grid[::-1]
    t_rev = t_grid[::-1]

    q_draws = rng.chisquare(k - 1, size=draws)
    t2_draws = np.where(q_draws >= q0, 0.0, np.interp(q_draws, q_rev, t_rev))
    w_sum = np.sum(1.0 / (v[None, :] + t2_draws[:, None]), axis=1)
    # Center at the REML/PM pooled mean
    t2_hat = metac.tau2_reml(y, v)
    w_hat = 1.0 / (v + t2_hat)
    mu_hat = float(np.sum(w_hat * y) / np.sum(w_hat))
    sd_draws = np.sqrt(t2_draws + 1.0 / w_sum)
    diffs = rng.standard_normal(draws) * sd_draws
    a = (1.0 - level) / 2.0
    lo, hi = np.quantile(diffs, [a, 1.0 - a])
    return float(mu_hat + lo), float(mu_hat + hi)


def meta_regression_trunc(y, v, X, level: float = .90) -> Dict[str, np.ndarray]:
    """Meta-regression with REML tau^2 and truncated Knapp-Hartung s^2 = max(1.0, sum w e^2 / (k - p))."""
    y = np.asarray(y, float); v = np.asarray(v, float)
    Xm = np.column_stack([np.ones(len(y)), np.asarray(X, float).reshape(len(y), -1)])
    k, p = Xm.shape
    t2 = metac.tau2_reml(y, v, Xm)
    w = 1.0 / (v + t2)
    XtWX = Xm.T @ (Xm * w[:, None])
    b = np.linalg.solve(XtWX, Xm.T @ (w * y))
    e = y - Xm @ b
    s2 = max(1.0, float(np.sum(w * e ** 2) / (k - p)))
    se = np.sqrt(np.diag(s2 * np.linalg.inv(XtWX)))
    c = stats.t.ppf((1.0 + level) / 2.0, k - p)
    return dict(coef=b, se=se, lower=b - c * se, upper=b + c * se, tau2=t2, df=k - p, q_factor=s2)


def egger_re(y, v) -> Dict[str, float]:
    """Random-effects Egger / Thompson-Sharp test: WLS of y on se with weights 1 / (v + tau^2_reml), t(k - 2)."""
    y = np.asarray(y, float); v = np.asarray(v, float); se = np.sqrt(v); k = len(y)
    X = np.column_stack([np.ones(k), se])
    t2 = metac.tau2_reml(y, v, X)
    w = 1.0 / (v + t2)
    XtWX = X.T @ (X * w[:, None])
    b = np.linalg.solve(XtWX, X.T @ (w * y))
    r = y - X @ b
    s2 = max(1.0, float(np.sum(w * r ** 2) / (k - 2)))
    V = s2 * np.linalg.inv(XtWX)
    slope_se = float(np.sqrt(V[1, 1]))
    t = float(b[1] / slope_se)
    return dict(slope=float(b[1]), se=slope_se, t=t, p=float(2.0 * stats.t.sf(abs(t), k - 2)), k=k, tau2=t2)


# ---------------------------------------------------------------------------
# 2. Nearest-neighbour matching ATT repair (Round 99 -> M1b-ATT)
# ---------------------------------------------------------------------------

def nn_match_att_t(y, T, X, M: int = 4, level: float = .90) -> Dict[str, float]:
    """Abadie-Imbens bias-corrected ATT with Kish effective-control-sample-size t(df_eff) critical value."""
    y = np.asarray(y, float); T = np.asarray(T, int); X = np.asarray(X, float).reshape(len(y), -1)
    Xs = X / X.std(0, ddof=1)
    t, c = np.flatnonzero(T == 1), np.flatnonzero(T == 0)
    b0 = matc._ols(X[c], y[c])
    K = np.zeros(len(y))
    idx = c[matc._nn(Xs[t], Xs[c], M)]
    np.add.at(K, idx.ravel(), 1)
    imp = (y[idx] + matc._pred(b0, X[t])[:, None] - matc._pred(b0, X[idx.ravel()]).reshape(idx.shape)).mean(1)
    s2 = np.zeros(len(y))
    j_c = c[matc._nn(Xs[c], Xs[c], 2)[:, 1]]
    s2[c] = (y[c] - y[j_c]) ** 2 / 2.0
    tau = float(np.mean(y[t] - imp))
    V = (np.sum((y[t] - imp - tau) ** 2) + np.sum((K[c] * (K[c] - 1.0) / M ** 2) * s2[c])) / len(t) ** 2
    se = float(np.sqrt(V))
    kc = K[c]
    n_c_eff = float((kc.sum() ** 2) / np.sum(kc ** 2)) if np.sum(kc ** 2) > 0 else float(len(c))
    df_eff = max(2.0, min(float(len(t) - 1), n_c_eff - 1.0))
    crit = float(stats.t.ppf(0.5 + level / 2.0, df_eff))
    return dict(estimate=tau, se=se, lower=tau - crit * se, upper=tau + crit * se,
                estimand="ATT", matches=M, df_eff=df_eff, n_c_eff=n_c_eff)


# ---------------------------------------------------------------------------
# 3. BYM2 disease mapping repair (Round 96 -> B3: PC prior + log-grid Jacobian)
# ---------------------------------------------------------------------------

PC_LAMBDA = -np.log(0.01) / 1.0  # P(sigma > 1.0) = 0.01 (Riebler et al. 2016 default)


def bym2_pc(y, E, X=None, eigen=None, edges=None, level: float = .90) -> Dict[str, Any]:
    """BYM2 grid integration with Riebler et al. (2016) PC prior on sigma and log-grid Jacobian (log w_prior =
    log(sigma) - lambda * sigma), fixing the implicit 1/sigma pile-up at sigma = 0.03."""
    y = np.asarray(y, float); E = np.asarray(E, float); n = len(y)
    X = np.ones((n, 1)) if X is None else np.column_stack([np.ones(n), np.asarray(X, float).reshape(n, -1)])
    V, lam = eigen if eigen is not None else dmc.scaled_icar_eigen(n, edges)
    fits, z0 = [], None
    for s in dmc.SIGMA_GRID:
        # Prior on log(sigma): p(sigma) * |d sigma / d log sigma| = lambda * exp(-lambda * sigma) * sigma
        log_prior = float(np.log(s) - PC_LAMBDA * s)
        for ph in dmc.PHI_GRID:
            ll, z, eta, cf, A = dmc._fit(y, E, X, V, lam, s, ph, z0)
            z0 = z
            fits.append([ll + log_prior, s, ph, eta, cf, A])
    lps = np.array([f[0] for f in fits])
    k = int(np.argmax(lps))
    w = np.exp(lps - lps.max()); w /= w.sum()
    keep = np.flatnonzero(w > 1e-4)
    w2 = w[keep] / w[keep].sum()
    var = {int(i): dmc._var(fits[i][4], fits[i][5]) for i in set(keep.tolist()) | {k}}
    M = np.array([fits[i][3] for i in keep]); S2 = np.array([var[int(i)] for i in keep])
    m2 = w2 @ M; v2 = w2 @ (S2 + M ** 2) - m2 ** 2
    sd = np.sqrt(np.clip(v2, 1e-12, None))
    zcrit = float(stats.norm.ppf(0.5 + level / 2.0))
    return dict(log_rr=m2, se=sd, rr=np.exp(m2), lower=np.exp(m2 - zcrit * sd), upper=np.exp(m2 + zcrit * sd),
                sigma=float(fits[k][1]), phi=float(fits[k][2]), logpost=float(lps[k]), method="B3_pc")


# ---------------------------------------------------------------------------
# 4. IP-weighted MSM repair (Round 91 -> M3: baseline L0 stabilization + cluster jackknife)
# ---------------------------------------------------------------------------

def _baseline_L0(L, unit, year):
    L0 = np.zeros_like(L, dtype=float)
    first_val = {}
    for i in np.argsort(year, kind="stable"):
        u = unit[i]
        if u not in first_val:
            first_val[u] = float(L[i])
    for i, u in enumerate(unit):
        L0[i] = first_val[u]
    return L0


def msm_point_l0(Y, A, L, unit, year, K, truncate=False, report=msmc.REPORT):
    """Baseline-L0-stabilized IP-weighted MSM (Hernan & Robins ch. 19-21): numerator P(A_t | year, L_0) and outcome
    Y ~ year + durations + L_0."""
    d = msmc.durations(A, unit, year)
    for k in range(1, report + 1):
        if not (d == k).any():
            raise ValueError(f"no unit-year with treatment duration {k}")
    L0 = _baseline_L0(L, unit, year)
    first = {}
    for i in np.argsort(year, kind="stable"):
        if A[i] == 1:
            first.setdefault(unit[i], year[i])
    if any(v == 1 for v in first.values()):
        raise ValueError("units treated in the first year: time zero must precede treatment")
    risk = np.array([1 < year[i] <= first.get(unit[i], np.inf) for i in range(len(A))])
    t = (year - 1) / K
    Xn = np.column_stack([np.ones(len(A)), t, L0])
    Xd = np.column_stack([np.ones(len(A)), t, L0, L])
    a = A[risk].astype(float)
    bn = msmc._logit(Xn[risk], a); bd = msmc._logit(Xd[risk], a)
    pn = 1.0 / (1.0 + np.exp(-np.clip(Xn @ bn, -30, 30)))
    pd_ = 1.0 / (1.0 + np.exp(-np.clip(Xd @ bd, -30, 30)))
    f = np.where(risk, np.where(A == 1, pn / pd_, (1.0 - pn) / (1.0 - pd_)), 1.0)
    w = np.ones(len(A))
    order = np.lexsort((year, unit))
    run, prev = 1.0, None
    for i in order:
        if unit[i] != prev:
            run, prev = 1.0, unit[i]
        run *= f[i]
        w[i] = run
    if truncate:
        lo, hi = np.quantile(w, [.01, .99])
        w = np.clip(w, lo, hi)
    D = np.column_stack([d == k for k in range(1, K)]).astype(float)
    D = D[:, D.sum(0) > 0]
    X = np.column_stack([msmc._year_dummies(year, K), D, L0])
    b = msmc._wls(Y, X, w)
    ny = int((msmc._year_dummies(year, K).sum(0) > 0).sum())
    return b[ny:ny + report], w


def msm_jackknife(Y, A, L, unit, year, K, truncate=False, level=.90, report=msmc.REPORT) -> Dict[str, Any]:
    """Delete-one-unit cluster jackknife with t(G - 1) intervals for baseline-L0-stabilized MSM."""
    est, w = msm_point_l0(Y, A, L, unit, year, K, truncate=truncate, report=report)
    units = np.unique(unit)
    G = len(units)
    jacks = []
    for u in units:
        keep = unit != u
        try:
            jacks.append(msm_point_l0(Y[keep], A[keep], L[keep], unit[keep], year[keep], K,
                                      truncate=truncate, report=report)[0])
        except (ValueError, np.linalg.LinAlgError):
            continue
    if len(jacks) < max(5, int(0.9 * G)):
        raise ValueError("too many failed jackknife replicates")
    J = np.array(jacks)
    m = len(J)
    jbar = J.mean(axis=0)
    se = np.sqrt((m - 1.0) / m * np.sum((J - jbar) ** 2, axis=0))
    crit = float(stats.t.ppf(0.5 + level / 2.0, m - 1))
    return dict(estimate=est.tolist(), lower=(est - crit * se).tolist(), upper=(est + crit * se).tolist(),
                se=se.tolist(), durations=list(range(1, report + 1)), max_weight=float(w.max()), units=m)


# ---------------------------------------------------------------------------
# 5. WHO mean differences repair (Round 94 -> MD2: replicate bias correction)
# ---------------------------------------------------------------------------

def md_bias_corrected(r, p, r_reps, p_reps, ref: Union[int, str] = "best", level: float = .90) -> Dict[str, Dict[str, np.ndarray]]:
    """Replicate bias-corrected mdm_w and mdb_w (max(0, 2*est - mean(reps))) with identity-scale replicate SE."""
    z = float(stats.norm.ppf(0.5 + level / 2.0))
    full = imc.measures(r, p, ref)
    rr = np.moveaxis(np.asarray(r_reps, float), -1, -2)
    pr = np.broadcast_to(np.asarray(p, float)[..., None, :], rr.shape) if p_reps is None else \
        np.moveaxis(np.asarray(p_reps, float), -1, -2)
    reps = imc.measures(rr, pr, ref)
    out = {}
    for m in ("mdm_w", "mdb_w"):
        est = full[m]; rep = reps[m]
        rep_mean = rep.mean(-1)
        est_bc = np.maximum(0.0, 2.0 * est - rep_mean)
        se = np.sqrt(imc.REP_FACTOR * np.sum((rep - est[..., None]) ** 2, -1))
        lo = np.maximum(0.0, est_bc - z * se)
        hi = est_bc + z * se
        out[m] = dict(estimate=est_bc, se=se, lower=lo, upper=hi)
    return out
