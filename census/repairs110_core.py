# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 110 frozen validation core:
- S3: Synthetic-control conformal inference interval (Chernozhukov-Wuthrich-Zhu 2021) gated at T_pre >= 15,
  N_donors >= 25 (reuses census.policy_core.conformal_interval).
- W2: WHO weighted mean differences mdm_w and mdb_w replicate intervals gated at signal-to-noise ratio
  SNR = (max(r) - min(r)) / median_se >= 4.0 and max_cv <= 0.15 (reuses census.inequality_monitoring_core).
"""
from typing import Dict, Tuple

import numpy as np

from . import inequality_monitoring_core as imc
from . import policy_core as pc


def synthetic_conformal_interval(M: np.ndarray, treated: int, T0: int, t_post: int,
                                 level: float = .90) -> Tuple[float, float, float]:
    """Conformal interval for post-period ``t_post`` of synthetic control on panel ``M`` (units x periods)."""
    res = pc.synth(M, treated, T0)
    gap = res["gap"]
    sd = max(float(np.std(gap[:T0], ddof=1)), 1e-9)
    grid = np.linspace(gap[t_post] - 6.0 * sd, gap[t_post] + 6.0 * sd, 241)
    lo, hi = pc.conformal_interval(M, treated, T0, t_post, grid, alpha=1.0 - level)
    return float(gap[t_post]), float(lo), float(hi)


def who_md_snr(est: np.ndarray, se_r: np.ndarray) -> np.ndarray:
    """Between-group signal-to-noise ratio: (max(r) - min(r)) / median(se_r) per area (1D or 2D)."""
    est = np.atleast_2d(np.asarray(est, float))
    se_r = np.atleast_2d(np.asarray(se_r, float))
    spread = np.max(est, axis=1) - np.min(est, axis=1)
    med_se = np.median(se_r, axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        snr = np.where(med_se > 0, spread / med_se, np.inf)
    return snr


def who_md_replicate_intervals(est, pops, r_reps, p_reps=None, reference="best", level: float = .90) -> Dict[str, Dict[str, np.ndarray]]:
    """Wrapper around inequality_monitoring_core.replicate_intervals returning mdm_w and mdb_w."""
    iv = imc.replicate_intervals(est, pops, r_reps, p_reps, reference, level)
    return {"mdm_w": iv["mdm_w"], "mdb_w": iv["mdb_w"]}
