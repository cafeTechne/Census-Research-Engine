# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 112 frozen validation core for the 5 remaining repairable exploratory candidates:
- M3b: Three-level variance-share logit jackknife (reuses census.multilevel3_core).
- Q2e: Designation PPV parametric bootstrap with Li-Lahiri positive-A floor for rule='lower' and 'prob50'.
- D2: Count-scale disparity indices (idisp, bgv, theil, mld) parametric Poisson bootstrap on log-scale (min_events >= 100).
- R2_dens: RDD density/manipulation test (reuses census.rdd_core.density_test).
- W3_rr: Stratified count RR homogeneity test (reuses census.stratified_core.woolf_rr, gated at min_cases >= 15).
"""
from typing import Dict

import numpy as np
from scipy import stats

from . import designation_core as desc
from . import disparity_core as dc
from . import multilevel3_core as m3c
from . import rdd_core as rddc
from . import sae_extensions_core as sx
from . import stratified_core as stratc

jackknife_shares = m3c.jackknife_shares
rdd_density_test = rddc.density_test
woolf_rr = stratc.woolf_rr


def ppv_interval_ll(rule: str, S, p, n, X, t, B: int = 120, level: float = .90, rng=None) -> Dict[str, float]:
    """FH parametric bootstrap PPV interval with Li-Lahiri positive-A floor and rule re-selection."""
    rng = rng if rng is not None else np.random.default_rng(20292112)
    S = np.asarray(S, bool)
    if int(S.sum()) == 0:
        return dict(ppv=np.nan, ppv_lower=np.nan, ppv_upper=np.nan, draws=0)
    y = desc.arcsine(p); D = 1.0 / (4.0 * np.asarray(n, float))
    X = np.asarray(X, float)
    if X.ndim == 1:
        X = X[:, None]
    f_fit = sx.fh_fit(y, X, D)
    beta_hat = f_fit["beta"]
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


def count_disparity_indices_boot(counts: np.ndarray, pops: np.ndarray, ref_idx: int = 0,
                                 B: int = 200, level: float = .90, rng=None) -> Dict[str, Dict[str, float]]:
    """Parametric Poisson bootstrap for count-scale disparity indices (idisp, bgv, theil, mld) on log scale."""
    rng = rng if rng is not None else np.random.default_rng(20292113)
    c = np.asarray(counts, float)
    n = np.asarray(pops, float)
    r0 = c / n
    w = n / n.sum()
    mu0 = float(np.sum(w * r0))

    def _indices(r):
        mu = np.sum(w * r, axis=-1)
        idisp = np.mean(np.abs(r - r[..., ref_idx:ref_idx + 1]), axis=-1) / np.maximum(r[..., ref_idx], 1e-12)
        bgv = np.sum(w * (r - mu[..., None]) ** 2, axis=-1)
        ratio = np.clip(r / np.maximum(mu[..., None], 1e-12), 1e-12, None)
        theil = np.sum(w * ratio * np.log(ratio), axis=-1)
        mld = -np.sum(w * np.log(ratio), axis=-1)
        return dict(idisp=idisp, bgv=bgv, theil=theil, mld=mld)

    est0 = _indices(r0)
    cb = rng.poisson(np.maximum(c, 1.0), size=(B, len(c)))
    rb = cb / n[None, :]
    boot = _indices(rb)
    z = float(stats.norm.ppf(0.5 + level / 2.0))
    out = {}
    for k in ("idisp", "bgv", "theil", "mld"):
        e0 = float(est0[k])
        vals = np.clip(boot[k], 1e-12, None)
        lvals = np.log(vals)
        se_log = float(np.std(lvals, ddof=1))
        lo = float(np.exp(np.log(max(e0, 1e-12)) - z * se_log))
        hi = float(np.exp(np.log(max(e0, 1e-12)) + z * se_log))
        out[k] = dict(estimate=e0, se_log=se_log, lower=lo, upper=hi)
    return out
