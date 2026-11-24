# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 106 frozen candidate repairs for five exploratory measures (N94-N98).

- H2c (PUMS replicate Wald homogeneity): Korn-Graubard Hotelling F(K - 1, R - K + 1) (reuses repairs105_core).
- Q2c (designation PPV predictive interval): FH parametric bootstrap re-applying S_b = designate(rule, p_b, n, t, Pb)
  inside every bootstrap draw (captures selection-rule winner's-curse variance).
- E3 (ecologic / between-area slope with many small areas): Croon/Fuller reliability-corrected between-area slope
  with delete-one-area / replicate intervals.
- C2 (Lin's CCC): delete-one-area jackknife on Fisher-z(CCC) with t(n - 2) critical value.
- M5 (parametric g-formula for annual policy panels with treatment-confounder feedback; Hernan & Robins ch. 21):
  outcome model Y_t ~ year + A_t + L_t + L_{t-1} and confounder transition L_t ~ L_{t-1} + A_{t-1}, recursive
  counterfactual prediction for durations 1..report vs never-treated, delete-one-unit cluster jackknife t(G - 1).
"""
from typing import Any, Dict, Optional

import numpy as np
from scipy import stats

from . import agreement_core as ac
from . import designation_core as desc
from . import msm_core as msmc
from . import repairs105_core as r105
from . import sae_extensions_core as sx

mh_replicate_homogeneity_f = r105.mh_replicate_homogeneity_f


# ---------------------------------------------------------------------------
# 2. Designation PPV predictive interval with rule re-selection (Q2c)
# ---------------------------------------------------------------------------

def ppv_interval_reselect(rule: str, S, p, n, X, t, B: int = 100, level: float = .90, rng=None) -> Dict[str, float]:
    """Parametric FH bootstrap that re-applies the designation rule S_b on every bootstrap sample."""
    rng = rng if rng is not None else np.random.default_rng(20286061)
    S = np.asarray(S, bool)
    k = int(S.sum())
    if k == 0:
        return dict(ppv=np.nan, ppv_lower=np.nan, ppv_upper=np.nan, draws=0)
    y = desc.arcsine(p); D = 1.0 / (4.0 * np.asarray(n, float))
    X = np.asarray(X, float)
    if X.ndim == 1:
        X = X[:, None]
    f_fit = sx.fh_fit(y, X, D)
    beta_hat = f_fit["beta"]; A_hat = max(float(f_fit["A"]), 0.0)
    f0 = sx.fh_interval_analytic(y, X, D)
    t_arc = float(desc.arcsine(t))
    P0 = stats.norm.sf((t_arc - f0["estimate"]) / np.sqrt(f0["mse"]))
    ppv0 = float(P0[S].mean())

    diffs = []
    n_areas = len(y); mu0 = X @ beta_hat
    for _ in range(B):
        theta_b = mu0 + np.sqrt(A_hat) * rng.standard_normal(n_areas)
        y_b = np.clip(theta_b + np.sqrt(D) * rng.standard_normal(n_areas), 0.01, np.pi / 2 - 0.01)
        p_b = np.sin(y_b) ** 2
        fb = sx.fh_interval_analytic(y_b, X, D)
        Pb = stats.norm.sf((t_arc - fb["estimate"]) / np.sqrt(fb["mse"]))
        S_b = desc.designate(rule, p_b, n, t, P=Pb, level=level)
        if S_b.sum() < 1:
            continue
        diffs.append(float((theta_b[S_b] >= t_arc).mean()) - float(Pb[S_b].mean()))
    if len(diffs) < max(10, B // 4):
        return dict(ppv=ppv0, ppv_lower=np.nan, ppv_upper=np.nan, draws=len(diffs))
    a = (1.0 - level) / 2.0
    q_lo, q_hi = np.quantile(diffs, [a, 1.0 - a])
    return dict(ppv=ppv0, ppv_lower=float(np.clip(ppv0 + q_lo, 0.0, 1.0)),
                ppv_upper=float(np.clip(ppv0 + q_hi, 0.0, 1.0)), draws=len(diffs))


# ---------------------------------------------------------------------------
# 3. Ecologic / between-area slope reliability correction (E3)
# ---------------------------------------------------------------------------

def ecologic_corrected_slope(area_x, area_y, var_xbar, level: float = .90) -> Dict[str, float]:
    """Fuller/Croon reliability-corrected ecologic (between-area) slope with delete-one-area jackknife t(J - 2).
    area_x, area_y: area sample means (J,); var_xbar: within-area sampling variance of area_x (s^2_j / n_j)."""
    x = np.asarray(area_x, float); y = np.asarray(area_y, float); vx = np.asarray(var_xbar, float)
    J = len(x)

    def _est(xx, yy, vvx):
        xm = xx.mean(); ym = yy.mean()
        sxx = float(np.mean((xx - xm) ** 2))
        sxy = float(np.mean((xx - xm) * (yy - ym)))
        mv = float(np.mean(vvx))
        # Fuller (1987) small-sample guard: denominator floored at 1 / len(xx) of sxx
        den = max(sxx - mv, sxx / max(len(xx), 2))
        return (sxy / den if den > 0 else 0.0), (max(0.0, (sxx - mv) / sxx) if sxx > 0 else 0.0)

    est, rel = _est(x, y, vx)
    jacks = np.array([_est(np.delete(x, i), np.delete(y, i), np.delete(vx, i))[0] for i in range(J)])
    se = float(np.sqrt((J - 1.0) / J * np.sum((jacks - jacks.mean()) ** 2)))
    crit = float(stats.t.ppf(0.5 + level / 2.0, max(J - 2, 1)))
    return dict(estimate=float(est), se=se, lower=float(est - crit * se), upper=float(est + crit * se),
                reliability=float(rel), areas=J)


# ---------------------------------------------------------------------------
# 4. Lin's CCC jackknife on Fisher-z (C2)
# ---------------------------------------------------------------------------

def _lin_ccc(x, y) -> float:
    mx, my = float(np.mean(x)), float(np.mean(y))
    vx = float(np.mean((x - mx) ** 2))
    vy = float(np.mean((y - my) ** 2))
    cxy = float(np.mean((x - mx) * (y - my)))
    den = vx + vy + (mx - my) ** 2
    return float(2.0 * cxy / den) if den > 0 else 0.0


def ccc_jackknife(x, y, level: float = .90) -> Dict[str, float]:
    """Lin's CCC with delete-one-area jackknife SE on the Fisher-z scale and t(n - 2) critical value."""
    x = np.asarray(x, float); y = np.asarray(y, float); n = len(x)
    c0 = _lin_ccc(x, y)
    z0 = float(np.arctanh(np.clip(c0, -0.999999, 0.999999)))
    zj = np.array([
        np.arctanh(np.clip(_lin_ccc(np.delete(x, i), np.delete(y, i)), -0.999999, 0.999999))
        for i in range(n)
    ])
    se_z = float(np.sqrt((n - 1.0) / n * np.sum((zj - zj.mean()) ** 2)))
    crit = float(stats.t.ppf(0.5 + level / 2.0, max(n - 2, 1)))
    return dict(estimate=c0, se_z=se_z, lower=float(np.tanh(z0 - crit * se_z)),
                upper=float(np.tanh(z0 + crit * se_z)), n=n, method="jackknife_fisher_z")


# ---------------------------------------------------------------------------
# 5. Parametric g-formula for annual panels with feedback (M5)
# ---------------------------------------------------------------------------

def gformula_point(Y, A, L, unit, year, K, report: int = msmc.REPORT) -> np.ndarray:
    """Parametric g-formula (Hernan & Robins ch. 21):
    1. Fit L_t ~ 1 + L_{t-1} + A_{t-1} over t >= 2 -> (a0, rho_L, gamma_A).
    2. Fit Y_t ~ year_dummies + A_t + L_t over all t -> direct effect psi_hat and confounder slope delta_L.
    3. Recursively compute total effect of duration d = 1..report vs never-treated:
       Delta_L(1) = 0, Delta_L(d) = gamma_A + rho_L * Delta_L(d - 1);
       psi_total(d) = psi_hat + delta_L * Delta_L(d)."""
    Y = np.asarray(Y, float); A = np.asarray(A, float); L = np.asarray(L, float)
    unit = np.asarray(unit); year = np.asarray(year, int)
    # Build lagged (L_{t-1}, A_{t-1}) within each unit
    order = np.lexsort((year, unit))
    u_o, yr_o, A_o, L_o = unit[order], year[order], A[order], L[order]
    same = (u_o[1:] == u_o[:-1]) & (yr_o[1:] == yr_o[:-1] + 1)
    L_cur = L_o[1:][same]; L_lag = L_o[:-1][same]; A_lag = A_o[:-1][same]
    XL = np.column_stack([np.ones(len(L_cur)), L_lag, A_lag])
    bL, *_ = np.linalg.lstsq(XL, L_cur, rcond=None)
    rho_L, gamma_A = float(bL[1]), float(bL[2])

    XY = np.column_stack([msmc._year_dummies(year, K), A, L])
    bY, *_ = np.linalg.lstsq(XY, Y, rcond=None)
    psi_hat, delta_L = float(bY[-2]), float(bY[-1])

    out = np.zeros(report)
    dL = 0.0
    for d in range(report):
        if d > 0:
            dL = gamma_A + rho_L * dL
        out[d] = psi_hat + delta_L * dL
    return out


def gformula_jackknife(Y, A, L, unit, year, K, level: float = .90, report: int = msmc.REPORT) -> Dict[str, Any]:
    """Parametric g-formula with delete-one-unit cluster jackknife t(G - 1) intervals."""
    est = gformula_point(Y, A, L, unit, year, K, report=report)
    units = np.unique(unit)
    G = len(units)
    J = np.array([gformula_point(Y[unit != u], A[unit != u], L[unit != u], unit[unit != u], year[unit != u],
                                 K, report=report) for u in units])
    jbar = J.mean(axis=0)
    se = np.sqrt((G - 1.0) / G * np.sum((J - jbar) ** 2, axis=0))
    crit = float(stats.t.ppf(0.5 + level / 2.0, G - 1))
    return dict(estimate=est.tolist(), lower=(est - crit * se).tolist(), upper=(est + crit * se).tolist(),
                se=se.tolist(), durations=list(range(1, report + 1)), units=G, method="gformula_jackknife")
