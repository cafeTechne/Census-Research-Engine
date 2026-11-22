# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 76 frozen core: between-group disparity measures and Kitagawa decomposition (backlog N53).

Groups g = 0..G-1 within one area, each with a rate r_g and a population share p_g (shares sum to one over the
declared groups); ``ref`` is the declared reference group.

Measures (Harper and Lynch 2005; Pearcy and Keppel 2002):
- rd: r_g - r_ref and log_rr: log(r_g / r_ref), one per non-reference group;
- idisp: 100 * mean over non-reference groups of |r_g - r_ref| / r_ref (Index of Disparity);
- bgv: sum p_g (r_g - rbar)^2 with rbar = sum p_g r_g (between-group variance);
- theil: sum p_g (r_g/rbar) ln(r_g/rbar); mld: sum p_g ln(rbar/r_g).

Interval candidates (90% by default):
- ACS replicates (D1-D4): SE = sqrt(4/80 sum (theta_r - theta)^2) on the analysis scale (identity for rd and
  log_rr; log for idisp, bgv, theil and mld), normal interval, back-transformed.
- Counts (Poisson): D1 delta method for rd (var r_g/n_g + r_ref/n_ref) and log_rr (1/d_g + 1/d_ref); D2b
  parametric bootstrap (d* ~ Poisson(d), B draws) for idisp, bgv, theil and mld: SE of the log statistic, normal
  interval on the log scale.

Kitagawa (1955), symmetric weights, areas A and B with stratum rates r_s and composition shares c_s:
crude difference = rate effect sum (c_As + c_Bs)/2 (r_As - r_Bs) + composition effect sum (r_As + r_Bs)/2 (c_As - c_Bs).
K1 intervals: replicate SE (ACS) or, for counts with known populations, Poisson variance of the stratum rates
(var r_s = d_s / n_s^2) through the linear weights. Normal intervals on the identity scale.
"""
import numpy as np
from scipy import stats

REP_FACTOR = 4/80
GROUP_MEASURES = ("rd", "log_rr")
INDEX_MEASURES = ("idisp", "bgv", "theil", "mld")
LOG_SCALE = {"rd": False, "log_rr": False, "idisp": True, "bgv": True, "theil": True, "mld": True}


def measures(r, p, ref: int):
    """All measures for rates ``r`` and shares ``p`` with shape (..., G). rd/log_rr have shape (..., G-1)."""
    r = np.asarray(r, float); p = np.asarray(p, float)
    p = p/p.sum(axis=-1, keepdims=True)
    G = r.shape[-1]
    others = [g for g in range(G) if g != ref]
    rr = r[..., ref:ref+1]
    ro = r[..., others]
    with np.errstate(divide="ignore", invalid="ignore"):
        rbar = (p*r).sum(axis=-1, keepdims=True)
        q = r/rbar
        theil = (p*np.where(q > 0, q*np.log(np.where(q > 0, q, 1)), 0.0)).sum(axis=-1)
        mld = (p*np.log(rbar/r)).sum(axis=-1)
        return dict(rd=ro-rr, log_rr=np.log(ro/rr), idisp=100*np.abs(ro-rr).mean(axis=-1)/rr[..., 0],
                    bgv=(p*(r-rbar)**2).sum(axis=-1), theil=theil, mld=mld)


def _scale(name, x):
    if not LOG_SCALE[name]:
        return x
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(x > 0, np.log(np.where(x > 0, x, 1)), np.nan)


def _interval(name, est, se, z):
    c = _scale(name, est)
    lo, hi = c-z*se, c+z*se
    if LOG_SCALE[name]:
        lo, hi = np.exp(lo), np.exp(hi)
    return lo, hi


def replicate_intervals(r, p, r_reps, p_reps, ref: int, level=.90):
    """D1-D4: replicate intervals. r, p: (..., G); r_reps, p_reps: (..., G, 80) (p_reps may be None: fixed shares).

    Returns {measure: dict(estimate, se, lower, upper)}; se is on the analysis scale (log for index measures).
    Non-finite replicate statistics make the interval NaN (no clipping)."""
    z = stats.norm.ppf(.5+level/2)
    full = measures(r, p, ref)
    rr = np.moveaxis(np.asarray(r_reps, float), -1, -2)  # (..., 80, G)
    pr = np.broadcast_to(np.asarray(p, float)[..., None, :], rr.shape) if p_reps is None else \
        np.moveaxis(np.asarray(p_reps, float), -1, -2)
    reps = measures(rr, pr, ref)
    out = {}
    for name, est in full.items():
        rep = reps[name]
        # rep: (..., 80) or (..., 80, G-1); align the replicate axis
        e = est[..., None, :] if name in GROUP_MEASURES else est[..., None]
        se = np.sqrt(REP_FACTOR*((_scale(name, rep)-_scale(name, e))**2).sum(axis=-2 if name in GROUP_MEASURES else -1))
        lo, hi = _interval(name, est, se, z)
        out[name] = dict(estimate=est, se=se, lower=lo, upper=hi)
    return out


def poisson_intervals(d, n, ref: int, level=.90, B=500, rng=None):
    """D1 (delta: rd, log_rr) and D2b (Poisson parametric bootstrap on the log scale: idisp, bgv, theil, mld).

    d: counts (..., G); n: populations (..., G), treated as known; shares p = n / sum n."""
    z = stats.norm.ppf(.5+level/2)
    d = np.asarray(d, float); n = np.asarray(n, float)
    r = d/n
    full = measures(r, n, ref)
    G = d.shape[-1]; others = [g for g in range(G) if g != ref]
    out = {}
    with np.errstate(divide="ignore", invalid="ignore"):
        se_rd = np.sqrt(d[..., others]/n[..., others]**2+(d[..., ref]/n[..., ref]**2)[..., None])
        se_lrr = np.sqrt(1/d[..., others]+(1/d[..., ref])[..., None])
    for name, se in (("rd", se_rd), ("log_rr", se_lrr)):
        lo, hi = _interval(name, full[name], se, z)
        out[name] = dict(estimate=full[name], se=se, lower=lo, upper=hi)
    rng = rng if rng is not None else np.random.default_rng()
    db = rng.poisson(np.broadcast_to(d[..., None, :], d.shape[:-1]+(B, G)))
    boot = measures(db/n[..., None, :], np.broadcast_to(n[..., None, :], db.shape), ref)
    for name in INDEX_MEASURES:
        lb = _scale(name, boot[name])
        se = np.nanstd(lb, axis=-1, ddof=1)
        bad = ~np.isfinite(lb).all(axis=-1)
        se = np.where(bad, np.nan, se)
        lo, hi = _interval(name, full[name], se, z)
        out[name] = dict(estimate=full[name], se=se, lower=lo, upper=hi)
    return out


def kitagawa(r_a, c_a, r_b, c_b):
    """Symmetric Kitagawa decomposition. Arrays (..., S); c_* are normalised to shares.
    Returns dict(difference, rate_effect, composition_effect)."""
    r_a, r_b = np.asarray(r_a, float), np.asarray(r_b, float)
    c_a = np.asarray(c_a, float); c_b = np.asarray(c_b, float)
    c_a = c_a/c_a.sum(axis=-1, keepdims=True); c_b = c_b/c_b.sum(axis=-1, keepdims=True)
    rate = ((c_a+c_b)/2*(r_a-r_b)).sum(axis=-1)
    comp = ((r_a+r_b)/2*(c_a-c_b)).sum(axis=-1)
    return dict(difference=(c_a*r_a).sum(axis=-1)-(c_b*r_b).sum(axis=-1), rate_effect=rate, composition_effect=comp)


def kitagawa_replicate(r_a, c_a, r_b, c_b, reps_a, creps_a, reps_b, creps_b, level=.90):
    """K1 (ACS): replicate SE of each component. reps_*: (..., S, 80); creps_* may be None (fixed composition)."""
    z = stats.norm.ppf(.5+level/2)
    full = kitagawa(r_a, c_a, r_b, c_b)
    mv = lambda x: np.moveaxis(np.asarray(x, float), -1, -2)  # noqa: E731
    ca = np.broadcast_to(np.asarray(c_a, float)[..., None, :], mv(reps_a).shape) if creps_a is None else mv(creps_a)
    cb = np.broadcast_to(np.asarray(c_b, float)[..., None, :], mv(reps_b).shape) if creps_b is None else mv(creps_b)
    rep = kitagawa(mv(reps_a), ca, mv(reps_b), cb)
    out = {}
    for k, est in full.items():
        se = np.sqrt(REP_FACTOR*((rep[k]-est[..., None])**2).sum(axis=-1))
        out[k] = dict(estimate=est, se=se, lower=est-z*se, upper=est+z*se)
    return out


def kitagawa_poisson(d_a, n_a, d_b, n_b, level=.90):
    """K1 (counts): known populations, Poisson stratum counts; delta variance through the linear weights."""
    z = stats.norm.ppf(.5+level/2)
    d_a, n_a, d_b, n_b = (np.asarray(x, float) for x in (d_a, n_a, d_b, n_b))
    c_a = n_a/n_a.sum(axis=-1, keepdims=True); c_b = n_b/n_b.sum(axis=-1, keepdims=True)
    full = kitagawa(d_a/n_a, c_a, d_b/n_b, c_b)
    va, vb = d_a/n_a**2, d_b/n_b**2
    wr = (c_a+c_b)/2; wc = (c_a-c_b)/2
    var = dict(difference=(c_a**2*va+c_b**2*vb).sum(axis=-1), rate_effect=(wr**2*(va+vb)).sum(axis=-1),
               composition_effect=(wc**2*(va+vb)).sum(axis=-1))
    out = {}
    for k, est in full.items():
        se = np.sqrt(var[k])
        out[k] = dict(estimate=est, se=se, lower=est-z*se, upper=est+z*se)
    return out
