# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 105 frozen candidate repairs for five exploratory measures (N89-N93).

- R1b (continuous RDD under curvature): CER-optimal bandwidth h_cer = h_ik * n^(-1/20) (Calonico, Cattaneo &
  Farrell 2020) with local-quadratic robust bias-corrected intervals.
- H2b (PUMS replicate Wald homogeneity): Korn-Graubard (1990) Hotelling F(K - 1, R - K + 1) reference distribution.
- Q2b (designation PPV predictive interval): parametric bootstrap over Fay-Herriot (beta, A) propagating shared
  hyperparameter uncertainty across tracts.
- M1b (probabilistic misclassification): observed-data binomial/multinomial sampling draws passed through
  corrected_table (preserving the 1/(Se + Sp - 1)^2 variance inflation; Fox, MacLehose & Lash 2021).
- M4 (IP-weighted MSM): Firth-penalized logistic regression for the rare-event pooled treatment model + baseline
  L0 stabilization + delete-one-unit cluster jackknife t(G - 1).
"""
from typing import Any, Dict, Optional

import numpy as np
from scipy import stats

from . import bias_analysis_core as bac
from . import designation_core as desc
from . import msm_core as msmc
from . import rdd_core as rddc
from . import repairs104_core as r104
from . import sae_extensions_core as sx
from . import stratified_core as stratc


# ---------------------------------------------------------------------------
# 1. Continuous RDD repair (Round 98 -> R1b: CER bandwidth n^(-1/20))
# ---------------------------------------------------------------------------

def rdd_cer(x, y, c: float, d=None, weights=None, vce: str = "hc",
            replicate_weights=None, level: float = .90) -> Dict[str, Any]:
    """RDD with Calonico-Cattaneo-Farrell (2020) CER-optimal bandwidth h_cer = h_ik * n^(-1/20)."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    h_ik = rddc.ik_bandwidth(x, y, c)
    h_cer = float(h_ik * (len(x) ** (-1.0 / 20.0)))
    out = rddc.rdd(x, y, c, h=h_cer, d=d, weights=weights, vce=vce,
                   replicate_weights=replicate_weights, level=level)
    out["bandwidth_ik"] = h_ik
    out["bandwidth_method"] = "cer"
    return out


# ---------------------------------------------------------------------------
# 2. PUMS replicate Wald homogeneity repair (Round 83 -> H2b: Hotelling F)
# ---------------------------------------------------------------------------

def mh_replicate_homogeneity_f(y, e, s, W, strata) -> Dict[str, Dict[str, float]]:
    """Korn-Graubard (1990) Hotelling F(K - 1, R - K + 1) homogeneity test from SDR replicate weights."""
    a, b, c, d = stratc.weighted_cells(y, e, s, W, strata)
    sm = stratc.stratum_measures(a, b, c, d)
    R = W.shape[1] - 1
    hom = {}
    for m, log in (("rr", True), ("or", True), ("rd", False)):
        t = np.log(sm[m]) if log else sm[m]
        K = t.shape[1]
        C = np.hstack([np.eye(K - 1), -np.ones((K - 1, 1))])
        dv = t @ C.T
        dev = dv[1:] - dv[0]
        V = stratc.REP * (dev.T @ dev)
        df1 = K - 1
        df2 = max(1, R - df1)
        try:
            w_stat = float(dv[0] @ np.linalg.solve(V, dv[0]))
            f_stat = (df2 / (R * df1)) * w_stat
            p_val = float(stats.f.sf(f_stat, df1, df2))
        except np.linalg.LinAlgError:
            f_stat, p_val = np.nan, np.nan
        hom[m] = dict(statistic=float(f_stat), p_value=p_val, df1=int(df1), df2=int(df2), method="hotelling_f")
    return hom


# ---------------------------------------------------------------------------
# 3. Designation PPV predictive interval repair (Round 85 -> Q2b: FH bootstrap)
# ---------------------------------------------------------------------------

def ppv_interval_bootstrap(S, p, n, X, t, B: int = 100, level: float = .90, rng=None) -> Dict[str, float]:
    """Parametric bootstrap predictive interval for realized PPV of designated set S, propagating Fay-Herriot
    (beta, A) estimation uncertainty across areas."""
    rng = rng if rng is not None else np.random.default_rng(20285051)
    S = np.asarray(S, bool)
    k = int(S.sum())
    if k == 0:
        return dict(ppv=np.nan, ppv_lower=np.nan, ppv_upper=np.nan, draws=0)
    y = desc.arcsine(p); D = 1.0 / (4.0 * np.asarray(n, float))
    X = np.asarray(X, float)
    if X.ndim == 1:
        X = X[:, None]
    f_fit = sx.fh_fit(y, X, D)
    beta_hat = f_fit["beta"]
    A_hat = max(float(f_fit["A"]), 0.0)
    f0 = sx.fh_interval_analytic(y, X, D)
    t_arc = float(desc.arcsine(t))
    P0 = stats.norm.sf((t_arc - f0["estimate"]) / np.sqrt(f0["mse"]))
    ppv0 = float(P0[S].mean())

    # Parametric bootstrap: draw true theta*, draw noisy y*, refit FH, compute (realized PPV* - expected PPV*)
    diffs = []
    n_areas = len(y)
    mu0 = X @ beta_hat
    for _ in range(B):
        theta_b = mu0 + np.sqrt(A_hat) * rng.standard_normal(n_areas)
        y_b = theta_b + np.sqrt(D) * rng.standard_normal(n_areas)
        fb = sx.fh_interval_analytic(y_b, X, D)
        Pb = stats.norm.sf((t_arc - fb["estimate"]) / np.sqrt(fb["mse"]))
        # Realized PPV on the designated set S under the bootstrap truth vs bootstrap expected PPV
        realized_b = float((theta_b[S] >= t_arc).mean())
        expected_b = float(Pb[S].mean())
        diffs.append(realized_b - expected_b)
    a = (1.0 - level) / 2.0
    q_lo, q_hi = np.quantile(diffs, [a, 1.0 - a])
    return dict(ppv=ppv0, ppv_lower=float(np.clip(ppv0 + q_lo, 0.0, 1.0)),
                ppv_upper=float(np.clip(ppv0 + q_hi, 0.0, 1.0)), draws=B)


# ---------------------------------------------------------------------------
# 4. Probabilistic misclassification repair (Round 86 -> M1b: propagate sampling)
# ---------------------------------------------------------------------------

def probabilistic_propagated(a, b, c, d, se_prior, sp_prior, kind: str = "outcome",
                             draws: int = 5000, level: float = .90, rng=None,
                             differential: bool = False) -> Dict[str, Any]:
    """Probabilistic misclassification analysis that propagates observed-table sampling error through the
    misclassification inversion (preserving the 1/(Se + Sp - 1)^2 variance inflation; Fox, MacLehose & Lash 2021)."""
    rng = rng if rng is not None else np.random.default_rng()

    def draw_p(prior):
        if differential:
            return np.stack([rng.beta(*bac.beta_params(*pr), draws) for pr in prior])
        x = rng.beta(*bac.beta_params(*prior), draws)
        return np.stack([x, x])

    se = draw_p(se_prior); sp = draw_p(sp_prior)
    # Systematic-only (observed counts fixed)
    As, Bs, Cs, Ds = bac.corrected_table(a, b, c, d, se, sp, kind)
    ok_s = (As > 0) & (Bs > 0) & (Cs > 0) & (Ds > 0)
    ms = bac._measures(As[ok_s], Bs[ok_s], Cs[ok_s], Ds[ok_s])

    # Total error: draw observed counts first, then invert with (se, sp)
    a_f, b_f, c_f, d_f = float(a), float(b), float(c), float(d)
    if kind == "outcome":
        n1 = int(round(a_f + b_f)); n0 = int(round(c_f + d_f))
        a_d = rng.binomial(n1, np.clip(a_f / n1, 1e-9, 1 - 1e-9), draws).astype(float)
        b_d = n1 - a_d
        c_d = rng.binomial(n0, np.clip(c_f / n0, 1e-9, 1 - 1e-9), draws).astype(float)
        d_d = n0 - c_d
    else:
        tot_n = int(round(a_f + b_f + c_f + d_f))
        probs = np.array([a_f, b_f, c_f, d_f]) / tot_n
        cells = rng.multinomial(tot_n, probs, size=draws).astype(float)
        a_d, b_d, c_d, d_d = cells[:, 0], cells[:, 1], cells[:, 2], cells[:, 3]
    At, Bt, Ct, Dt = bac.corrected_table(a_d, b_d, c_d, d_d, se, sp, kind)
    ok_t = (At > 0) & (Bt > 0) & (Ct > 0) & (Dt > 0)
    mt = bac._measures(At[ok_t], Bt[ok_t], Ct[ok_t], Dt[ok_t])

    q = [(1.0 - level) / 2.0, (1.0 + level) / 2.0]
    out = dict(discarded=float(1.0 - ok_t.mean()), method="propagated_sampling")
    for name in ("rr", "or"):
        sysq = np.quantile(np.log(ms[name][0]), [0.5] + q)
        totq = np.quantile(np.log(mt[name][0]), q)
        out[name] = dict(median=float(np.exp(sysq[0])), systematic_lower=float(np.exp(sysq[1])),
                         systematic_upper=float(np.exp(sysq[2])), lower=float(np.exp(totq[0])),
                         upper=float(np.exp(totq[1])))
    return out


# ---------------------------------------------------------------------------
# 5. IP-weighted MSM repair (Round 91/104 -> M4: Firth logit + L0 + jackknife)
# ---------------------------------------------------------------------------

def _logit_firth(X, y, iters: int = 60):
    """Firth (1993) bias-reduced penalized logistic regression (Jeffreys prior penalty 0.5 log|I(b)|)."""
    b = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1.0 / (1.0 + np.exp(-np.clip(X @ b, -30, 30)))
        w = p * (1.0 - p)
        H = X.T @ (X * w[:, None]) + 1e-9 * np.eye(X.shape[1])
        Hinv = np.linalg.inv(H)
        # Hat-matrix diagonal h_i = w_i * x_i' H^-1 x_i
        h = w * np.einsum("ij,jk,ik->i", X, Hinv, X)
        score = X.T @ (y - p + h * (0.5 - p))
        step = Hinv @ score
        b += step
        if np.max(np.abs(step)) < 1e-8:
            return b
    raise ValueError("Firth treatment model did not converge")


def msm_point_firth(Y, A, L, unit, year, K, truncate=False, report=msmc.REPORT):
    d = msmc.durations(A, unit, year)
    for k in range(1, report + 1):
        if not (d == k).any():
            raise ValueError(f"no unit-year with treatment duration {k}")
    L0 = r104._baseline_L0(L, unit, year)
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
    bn = _logit_firth(Xn[risk], a); bd = _logit_firth(Xd[risk], a)
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


def msm_firth_jackknife(Y, A, L, unit, year, K, truncate=False, level=.90, report=msmc.REPORT) -> Dict[str, Any]:
    est, w = msm_point_firth(Y, A, L, unit, year, K, truncate=truncate, report=report)
    units = np.unique(unit)
    G = len(units)
    jacks = []
    for u in units:
        keep = unit != u
        try:
            jacks.append(msm_point_firth(Y[keep], A[keep], L[keep], unit[keep], year[keep], K,
                                         truncate=truncate, report=report)[0])
        except (ValueError, np.linalg.LinAlgError):
            continue
    if len(jacks) < max(5, int(0.9 * G)):
        raise ValueError("too many failed jackknife replicates")
    J = np.array(jacks); m = len(J); jbar = J.mean(axis=0)
    se = np.sqrt((m - 1.0) / m * np.sum((J - jbar) ** 2, axis=0))
    crit = float(stats.t.ppf(0.5 + level / 2.0, m - 1))
    return dict(estimate=est.tolist(), lower=(est - crit * se).tolist(), upper=(est + crit * se).tolist(),
                se=se.tolist(), durations=list(range(1, report + 1)), max_weight=float(w.max()), units=m)
