# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 56 frozen core: income inequality measures with SDR replicate variance (PUMS).

For incomes y (n,) and weights W (n, 81) = full-sample weight and 80 SDR replicates, every measure is computed
for every weight column after one sort by y. Measures: Gini, Theil T, Atkinson (eps .5, 1), log P90/P10,
log P80/P20, top-decile share. SE = sqrt(4/80 sum (theta_r - theta)^2), normal interval.
"""
import numpy as np
from scipy.stats import norm

MEASURES = ("gini", "theil_t", "atkinson_0.5", "atkinson_1", "log_p90_p10", "log_p80_p20", "top10_share")
NEEDS_POSITIVE = ("theil_t", "atkinson_0.5", "atkinson_1", "log_p90_p10", "log_p80_p20")


def _quantile(ys, cum, q):
    """Inverse weighted ECDF per column: smallest y with cumulative share >= q. cum (n, k), ys (n,)."""
    idx = np.argmax(cum >= q-1e-12, axis=0)
    return ys[idx]


def measures(y, W):
    """Dict measure -> array (k,) over the weight columns of W (n, k)."""
    y = np.asarray(y, float); W = np.asarray(W, float)
    if W.ndim == 1:
        W = W[:, None]
    if y.ndim != 1 or len(y) != len(W) or not np.isfinite(y).all() or not np.isfinite(W).all():
        raise ValueError("finite incomes and weights of matching length required")
    if (y < 0).any():
        raise ValueError("negative incomes are refused")
    o = np.argsort(y, kind="mergesort"); ys = y[o]; Ws = W[o]
    tot = Ws.sum(axis=0)
    if (tot <= 0).any():
        raise ValueError("weights must have a positive total in every column")
    p = Ws/tot
    mu = ys @ p
    if (mu <= 0).any():
        raise ValueError("mean income must be positive")
    share = p*ys[:, None]/mu
    L = np.cumsum(share, axis=0); Lprev = np.vstack((np.zeros((1, W.shape[1])), L[:-1]))
    P = np.cumsum(p, axis=0)
    out = {"gini": 1-np.sum(p*(L+Lprev), axis=0)}
    # top-decile share: 1 - L(.9), L linear in the cumulative population share
    top = np.empty(W.shape[1])
    for k in range(W.shape[1]):
        top[k] = 1-np.interp(.9, np.r_[0, P[:, k]], np.r_[0, L[:, k]])
    out["top10_share"] = top
    if (ys > 0).all():
        r = ys[:, None]/mu
        out["theil_t"] = np.sum(p*r*np.log(r), axis=0)
        out["atkinson_0.5"] = 1-np.sum(p*np.sqrt(r), axis=0)**2
        out["atkinson_1"] = 1-np.exp(np.sum(p*np.log(ys)[:, None], axis=0))/mu
        q = {qq: _quantile(ys, P, qq) for qq in (.1, .2, .8, .9)}
        out["log_p90_p10"] = np.log(q[.9]/q[.1])
        out["log_p80_p20"] = np.log(q[.8]/q[.2])
    return out


def sdr_summary(theta, level=.90):
    """theta (81,) -> estimate, SE, interval."""
    theta = np.asarray(theta, float)
    if theta.shape != (81,) or not np.isfinite(theta).all():
        raise ValueError("81 finite full-sample and replicate values required")
    est = float(theta[0]); se = float(np.sqrt(.05*np.sum((theta[1:]-est)**2)))
    z = norm.ppf((1+level)/2)
    return dict(estimate=est, se=se, lower=est-z*se, upper=est+z*se)


# Round 60: transformed and bias-corrected SDR intervals for the measures that failed Round 56.
TRANSFORM = {"theil_t": "log", "atkinson_0.5": "logit", "atkinson_1": "logit", "top10_share": "logit"}


def _fwd(x, kind):
    x = np.asarray(x, float)
    return np.log(x) if kind == "log" else np.log(x/(1-x))


def _inv(y, kind):
    return float(np.exp(y)) if kind == "log" else float(1/(1+np.exp(-y)))


def transformed_summary(theta, kind, center=None, level=.90):
    """T1 (center None) / T2 (center = bias-corrected value): SDR SE of the transformed replicates, normal interval
    on the transformed scale around the (possibly corrected) estimate, back-transformed."""
    theta = np.asarray(theta, float)
    if theta.shape != (81,) or not np.isfinite(theta).all():
        raise ValueError("81 finite full-sample and replicate values required")
    lo_ok = theta > 0 if kind == "log" else (theta > 0) & (theta < 1)
    if not lo_ok.all():
        raise ValueError("values outside the transform's domain")
    t = _fwd(theta, kind)
    se = float(np.sqrt(.05*np.sum((t[1:]-t[0])**2)))
    est = float(theta[0]) if center is None else float(center)
    if not (est > 0 if kind == "log" else 0 < est < 1):
        raise ValueError("corrected estimate outside the transform's domain")
    c = float(_fwd(est, kind)); z = norm.ppf((1+level)/2)
    return dict(estimate=est, se_transformed=se, lower=_inv(c-z*se, kind), upper=_inv(c+z*se, kind))


def bias_corrected(theta):
    """Round 50's SDR bias correction: theta - 4 (mean theta_r - theta)."""
    theta = np.asarray(theta, float)
    return float(theta[0]-4*(theta[1:].mean()-theta[0]))
