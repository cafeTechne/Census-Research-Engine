# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 109 frozen validation core:
- E3d: Fuller (1987, Theorem 2.5.1, alpha=4) modified-denominator reliability-corrected ecologic/between-area slope
  with delete-one-area jackknife t(J - 2) intervals.
- J3c: Joinpoint AAPC parametric residual bootstrap with joinpoint-location re-estimation and t(n - 2k - 2) SE.
"""
from typing import Dict

import numpy as np
from scipy import stats

from . import joinpoint_core as jc


def ecologic_fuller_slope(area_x, area_y, var_xbar, alpha: float = 4.0, level: float = .90) -> Dict[str, float]:
    """Fuller (1987, alpha=4) modified-denominator reliability-corrected ecologic/between-area slope
    with delete-one-area jackknife t(J - 2) intervals."""
    x = np.asarray(area_x, float)
    y = np.asarray(area_y, float)
    vx = np.asarray(var_xbar, float)
    J = len(x)

    def _est(xx, yy, vvx):
        xm = xx.mean()
        ym = yy.mean()
        sxx = float(np.mean((xx - xm) ** 2))
        sxy = float(np.mean((xx - xm) * (yy - ym)))
        mv = float(np.mean(vvx))
        # Fuller (1987) finite-sample modification removes O(1/J) upward ratio bias
        den = max(sxx - mv + alpha * mv / max(len(xx), 2), sxx / max(len(xx), 2))
        return (sxy / den if den > 0 else 0.0), (max(0.0, (sxx - mv) / sxx) if sxx > 0 else 0.0)

    est, rel = _est(x, y, vx)
    jacks = np.array([_est(np.delete(x, i), np.delete(y, i), np.delete(vx, i))[0] for i in range(J)])
    se = float(np.sqrt((J - 1.0) / J * np.sum((jacks - jacks.mean()) ** 2)))
    crit = float(stats.t.ppf(0.5 + level / 2.0, max(J - 2, 1)))
    return dict(estimate=float(est), se=se, lower=float(est - crit * se), upper=float(est + crit * se),
                reliability=float(rel), areas=J, alpha=float(alpha))


def _aapc_from_fit(x, cfg, beta) -> float:
    """Average annual percent change (log-scale mean slope) across [x[0], x[-1]]."""
    span = float(x[-1] - x[0])
    if span <= 0:
        return 0.0
    # Fitted values at endpoints determine the exact length-weighted average slope
    def _eval(x0):
        v = float(beta[0] + beta[1] * x0)
        for j, idx in enumerate(cfg):
            v += float(beta[2 + j]) * max(x0 - float(x[int(idx)]), 0.0)
        return v
    return (_eval(float(x[-1])) - _eval(float(x[0]))) / span


def joinpoint_aapc_bootstrap_t(x, y, w, k: int, B: int = 150, level: float = .90, rng=None) -> Dict[str, float]:
    """Parametric residual bootstrap for joinpoint AAPC (mean log-slope) re-estimating joinpoint locations
    in each draw and forming a t(n - 2k - 2) interval from the bootstrap SE."""
    rng = rng if rng is not None else np.random.default_rng(20289109)
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    w = np.asarray(w, float)
    f0 = jc.fit(x, y, w, k)
    mean_slope0 = _aapc_from_fit(x, f0["cfg"], f0["beta"])
    n = len(x)
    df = max(int(f0["df"]), 1)
    # Use max(mse, 1.0) so known Poisson variance 1/w is never under-estimated when SSE happens to be tiny
    sigma2 = max(float(f0["sse"]) / df, 1.0)
    sd_y = np.sqrt(sigma2 / w)

    Y_boot = f0["fitted"][:, None] + sd_y[:, None] * rng.standard_normal((n, B))
    cfg_all, _, _, beta_all, sse_all = jc._fit_all(x, Y_boot, w, k)
    best_c = np.argmin(sse_all, axis=0)  # (B,)
    slopes_b = np.empty(B)
    for b in range(B):
        c = int(best_c[b])
        slopes_b[b] = _aapc_from_fit(x, cfg_all[c], beta_all[c, :, b])

    se = float(np.std(slopes_b, ddof=1))
    crit = float(stats.t.ppf(0.5 + level / 2.0, df))
    lo_s = mean_slope0 - crit * se
    hi_s = mean_slope0 + crit * se
    return dict(
        aapc=float(100.0 * (np.exp(mean_slope0) - 1.0)),
        lower=float(100.0 * (np.exp(lo_s) - 1.0)),
        upper=float(100.0 * (np.exp(hi_s) - 1.0)),
        mean_slope=float(mean_slope0),
        se_slope=se,
        df=df,
        k=int(k),
        method="bootstrap_t",
    )
