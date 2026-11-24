# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 107 frozen candidate repairs for four remaining exploratory measures.

- Q2d-prob80 / Q2d-point (designation PPV predictive interval): FH parametric bootstrap with rule re-selection
  (reusing repairs106_core.ppv_interval_reselect for prob80; adding Li-Lahiri positive-A floor for point).
- E3b (ecologic / between-area slope): Croon/Fuller reliability-corrected slope with delete-one-area jackknife
  t(J - 2), gated at median_area_n >= 40 and areas >= 50 (reuses repairs106_core.ecologic_corrected_slope).
- H2d (PUMS homogeneity): Korn-Graubard Hotelling F(K - 1, R - K + 1), gated at min_stratum_n >= 500
  (reuses repairs105_core.mh_replicate_homogeneity_f).
- S2 (Shannon entropy diversity): exact SDR replicate bias correction E_bc = E - 4 * (mean(Er) - E) with
  t(R - 1) critical value (same replicate bias-correction principle validated for segregation H in Rounds 50/52).
"""
from typing import Any, Dict

import numpy as np
from scipy import stats

from . import designation_core as desc
from . import repairs105_core as r105
from . import repairs106_core as r106
from . import sae_extensions_core as sx
from . import spatial_models_core as smc

ppv_interval_prob80 = r106.ppv_interval_reselect
ecologic_corrected_slope = r106.ecologic_corrected_slope
mh_replicate_homogeneity_f = r105.mh_replicate_homogeneity_f


def ppv_interval_point_ll(S, p, n, X, t, B: int = 150, level: float = .90, rng=None) -> Dict[str, float]:
    """FH parametric bootstrap for rule='point' with a positive Li-Lahiri-style variance floor on A_hat."""
    rng = rng if rng is not None else np.random.default_rng(20287071)
    S = np.asarray(S, bool)
    if int(S.sum()) == 0:
        return dict(ppv=np.nan, ppv_lower=np.nan, ppv_upper=np.nan, draws=0)
    y = desc.arcsine(p); D = 1.0 / (4.0 * np.asarray(n, float))
    X = np.asarray(X, float)
    if X.ndim == 1:
        X = X[:, None]
    f_fit = sx.fh_fit(y, X, D)
    beta_hat = f_fit["beta"]
    # Positive floor prevents boundary A_hat == 0 collapse in small-A cells
    A_hat = max(float(f_fit["A"]), float(np.median(D)) * 0.25)
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
        S_b = desc.designate("point", p_b, n, t, P=Pb, level=level)
        if S_b.sum() < 1:
            continue
        diffs.append(float((theta_b[S_b] >= t_arc).mean()) - float(Pb[S_b].mean()))
    if len(diffs) < max(10, B // 4):
        return dict(ppv=ppv0, ppv_lower=np.nan, ppv_upper=np.nan, draws=len(diffs))
    a = (1.0 - level) / 2.0
    q_lo, q_hi = np.quantile(diffs, [a, 1.0 - a])
    return dict(ppv=ppv0, ppv_lower=float(np.clip(ppv0 + q_lo, 0.0, 1.0)),
                ppv_upper=float(np.clip(ppv0 + q_hi, 0.0, 1.0)), draws=len(diffs))


def diversity_sdr_bc(P, P_reps, level: float = .90) -> Dict[str, np.ndarray]:
    """Shannon entropy with exact SDR replicate bias correction E_bc = E - 4 * (mean(Er) - E) and t(R - 1).
    P: (n, G) shares; P_reps: (R, n, G) replicate shares (SDR factor 4/R)."""
    P = np.asarray(P, float); Pr = np.asarray(P_reps, float)
    R = Pr.shape[0]
    f = 4.0 / R
    E = smc.entropy(P)
    Er = smc.entropy(Pr)
    E_bc = E - 4.0 * (Er.mean(axis=0) - E)
    se = np.sqrt(f * np.sum((Er - E) ** 2, axis=0))
    crit = float(stats.t.ppf(0.5 + level / 2.0, max(R - 1, 1)))
    return dict(estimate=E_bc, se=se, lower=E_bc - crit * se, upper=E_bc + crit * se)
