# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 108 frozen validation core:
- M5b: vector multi-confounder parametric g-formula (VAR(1) transition L_t ~ 1 + L_{t-1} + A_{t-1} and outcome
  Y_t ~ year_dummies + A_t + L_t) with delete-one-unit cluster jackknife t(G - 1).
- E3c: Croon/Fuller reliability-corrected ecologic/between-area slope (reuses repairs106_core.ecologic_corrected_slope).
- S2b: Shannon entropy diversity with exact SDR replicate bias correction (reuses repairs107_core.diversity_sdr_bc).
"""
from typing import Any, Dict

import numpy as np
from scipy import stats

from . import msm_core as msmc
from . import repairs106_core as r106
from . import repairs107_core as r107

ecologic_corrected_slope = r106.ecologic_corrected_slope
diversity_sdr_bc = r107.diversity_sdr_bc


def gformula_vector_point(Y, A, L, unit, year, K, report: int = msmc.REPORT) -> np.ndarray:
    """Vector parametric g-formula (Hernan & Robins ch. 21) for p >= 1 time-varying confounders:
    1. Fit multivariate VAR(1): L_t = a0 + Phi L_{t-1} + gamma_A A_{t-1} + eps_t over consecutive t >= 2.
    2. Fit outcome model: Y_t = year_dummies + psi * A_t + delta^T L_t + u_t.
    3. Recursively propagate Delta_L(1) = 0, Delta_L(d) = gamma_A + Phi @ Delta_L(d - 1);
       psi_total(d) = psi + delta @ Delta_L(d) for d = 1..report."""
    Y = np.asarray(Y, float)
    A = np.asarray(A, float)
    L = np.asarray(L, float)
    if L.ndim == 1:
        L = L[:, None]
    p = L.shape[1]
    unit = np.asarray(unit)
    year = np.asarray(year, int)

    order = np.lexsort((year, unit))
    u_o, yr_o, A_o, L_o = unit[order], year[order], A[order], L[order]
    same = (u_o[1:] == u_o[:-1]) & (yr_o[1:] == yr_o[:-1] + 1)
    L_cur = L_o[1:][same]      # (m, p)
    L_lag = L_o[:-1][same]     # (m, p)
    A_lag = A_o[:-1][same]     # (m,)

    XL = np.column_stack([np.ones(len(L_cur)), L_lag, A_lag])   # (m, 1 + p + 1)
    BL, *_ = np.linalg.lstsq(XL, L_cur, rcond=None)             # (1 + p + 1, p)
    Phi = BL[1:1 + p, :].T                                      # (p, p): L_t = a0 + Phi @ L_{t-1} + gamma_A * A_{t-1}
    gamma_A = BL[1 + p, :]                                      # (p,)

    XY = np.column_stack([msmc._year_dummies(year, K), A, L])
    bY, *_ = np.linalg.lstsq(XY, Y, rcond=None)
    psi_hat = float(bY[-(p + 1)])
    delta_L = bY[-p:]                                           # (p,)

    out = np.zeros(report)
    dL = np.zeros(p)
    for d in range(report):
        if d > 0:
            dL = gamma_A + Phi @ dL
        out[d] = psi_hat + float(delta_L @ dL)
    return out


def gformula_vector_jackknife(Y, A, L, unit, year, K, level: float = .90, report: int = msmc.REPORT) -> Dict[str, Any]:
    """Vector parametric g-formula with delete-one-unit cluster jackknife t(G - 1) intervals."""
    Y = np.asarray(Y, float)
    A = np.asarray(A, float)
    L = np.asarray(L, float)
    if L.ndim == 1:
        L = L[:, None]
    unit = np.asarray(unit)
    year = np.asarray(year, int)

    est = gformula_vector_point(Y, A, L, unit, year, K, report=report)
    units = np.unique(unit)
    G = len(units)
    J = np.array([
        gformula_vector_point(Y[unit != u], A[unit != u], L[unit != u], unit[unit != u], year[unit != u],
                              K, report=report)
        for u in units
    ])
    jbar = J.mean(axis=0)
    se = np.sqrt((G - 1.0) / G * np.sum((J - jbar) ** 2, axis=0))
    crit = float(stats.t.ppf(0.5 + level / 2.0, G - 1))
    return dict(estimate=est.tolist(), lower=(est - crit * se).tolist(), upper=(est + crit * se).tolist(),
                se=se.tolist(), durations=list(range(1, report + 1)), units=G, confounders=int(L.shape[1]),
                method="gformula_jackknife")
