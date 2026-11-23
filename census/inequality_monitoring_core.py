# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 94 frozen core: WHO health inequality monitoring measures (backlog N71; WHO 2013, chapters 3-4).

Groups g = 0..G-1 within one area with rates r_g (an adverse outcome: lower is better) and population shares p_g.
- mdm_u: mean over groups of |r_g - rbar| (unweighted), rbar = sum p_g r_g the population average;
  mdm_w: sum p_g |r_g - rbar| (weighted).
- mdb_u: mean over non-reference groups of |r_g - r_ref|; mdb_w: sum over non-reference groups of
  p_g |r_g - r_ref| / sum p_g (weighted).
- par: rbar - r_ref (absolute population attributable risk); par_pct: 100 (rbar - r_ref) / rbar.
- sii: slope index of inequality, weighted least squares of r_g on the ridit midpoint of the groups in the given
  (ordered) sequence (Round 24 convention: rank 0 = first group).
Reference: a declared group index, or "best" = the group with the lowest rate, chosen from the data. For "best",
each replicate re-selects its own best group, so the interval reflects the selection.
Intervals (90% by default): replicate SE = sqrt(4/80 sum (theta_r - theta)^2); normal interval on the log scale for
the non-negative measures (mdm, mdb), on the identity scale for par, par_pct and sii. Change between two releases
(independent samples): difference of the measures with SE = sqrt(se_1^2 + se_2^2) on the identity scale.
"""
from typing import Dict, Optional, Union

import numpy as np
from scipy import stats

REP_FACTOR = 4/80
POSITIVE = ("mdm_u", "mdm_w", "mdb_u", "mdb_w")
IDENTITY = ("par", "par_pct", "sii")
MEASURES = POSITIVE+IDENTITY


def _ref_index(r, ref):
    if isinstance(ref, str):
        if ref != "best":
            raise ValueError("reference must be a group index or 'best'")
        return np.argmin(r, axis=-1)
    return np.full(r.shape[:-1], int(ref))


def measures(r, p, ref: Union[int, str] = "best") -> Dict[str, np.ndarray]:
    """All measures for rates and shares of shape (..., G)."""
    r = np.asarray(r, float); p = np.asarray(p, float)
    p = p/p.sum(axis=-1, keepdims=True)
    G = r.shape[-1]
    k = _ref_index(r, ref)
    rref = np.take_along_axis(r, k[..., None], -1)
    other = np.arange(G) != k[..., None]
    rbar = (p*r).sum(-1, keepdims=True)
    ad = np.abs(r-rref)
    po = np.where(other, p, 0)
    cum = np.cumsum(p, -1); mid = cum-p/2
    mw = (p*mid).sum(-1, keepdims=True)
    sii = (p*(mid-mw)*(r-rbar)).sum(-1)/(p*(mid-mw)**2).sum(-1)
    return dict(mdm_u=np.abs(r-rbar).mean(-1), mdm_w=(p*np.abs(r-rbar)).sum(-1),
                mdb_u=np.where(other, ad, 0).sum(-1)/(G-1), mdb_w=(po*ad).sum(-1)/po.sum(-1),
                par=(rbar-rref)[..., 0], par_pct=100*((rbar-rref)/rbar)[..., 0], sii=sii)


def replicate_intervals(r, p, r_reps, p_reps, ref: Union[int, str] = "best", level: float = .90):
    """r, p: (..., G); r_reps, p_reps: (..., G, 80) (p_reps None: fixed shares). {measure: estimate, se, lower, upper}
    (se on the analysis scale: log for mdm/mdb)."""
    z = stats.norm.ppf(.5+level/2)
    full = measures(r, p, ref)
    rr = np.moveaxis(np.asarray(r_reps, float), -1, -2)
    pr = np.broadcast_to(np.asarray(p, float)[..., None, :], rr.shape) if p_reps is None else \
        np.moveaxis(np.asarray(p_reps, float), -1, -2)
    reps = measures(rr, pr, ref)
    out = {}
    for m in MEASURES:
        est = full[m]; rep = reps[m]
        with np.errstate(divide="ignore", invalid="ignore"):
            if m in POSITIVE:
                ce, cr = np.log(np.where(est > 0, est, np.nan)), np.log(np.where(rep > 0, rep, np.nan))
            else:
                ce, cr = est, rep
            se = np.sqrt(REP_FACTOR*np.sum((cr-ce[..., None])**2, -1))
            lo, hi = ce-z*se, ce+z*se
            if m in POSITIVE:
                lo, hi = np.exp(lo), np.exp(hi)
        out[m] = dict(estimate=est, se=se, lower=lo, upper=hi)
    return out


def change(iv1: Dict[str, Dict[str, np.ndarray]], iv2: Dict[str, Dict[str, np.ndarray]], level: float = .90,
           measures_: Optional[tuple] = None) -> Dict[str, Dict[str, np.ndarray]]:
    """Release 2 minus release 1 for each measure, identity scale (independent releases)."""
    z = stats.norm.ppf(.5+level/2)
    out = {}
    for m in measures_ or MEASURES:
        a, b = iv1[m], iv2[m]
        if m in POSITIVE:   # delta method back to the identity scale: se(x) ~ x * se(log x)
            s1, s2 = a["estimate"]*a["se"], b["estimate"]*b["se"]
        else:
            s1, s2 = a["se"], b["se"]
        d = b["estimate"]-a["estimate"]; se = np.sqrt(s1**2+s2**2)
        out[m] = dict(estimate=d, se=se, lower=d-z*se, upper=d+z*se)
    return out
