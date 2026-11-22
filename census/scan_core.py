# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 81 frozen core: Kulldorff Poisson spatial scan statistic (backlog N58).

Areas i with representative points (lon, lat), observed counts c_i and null expected counts mu_i (scaled so that
sum mu = sum c = C). Windows: for every centre i, the k nearest areas (great-circle distance, centre first) for
k = 1, 2, ... while the window's share of the expected count is <= max_share (Kulldorff 1997 circular windows).
High-rate scan: LLR_z = c_z log(c_z / mu_z) + (C - c_z) log((C - c_z) / (C - mu_z)) when c_z > mu_z, else 0.
Primary cluster: the window with the largest LLR. Monte Carlo p-value: R null data sets, multinomial(C, mu / C)
(conditional on the total), p = (1 + #{max LLR* >= LLR}) / (R + 1). Secondary clusters: windows sharing no area
with a more likely reported cluster, in decreasing LLR, with the same max-LLR Monte Carlo p-value (conservative,
as SaTScan) and a Gumbel approximation fitted to the null max-LLR sample (method of moments) as a comparison.
"""
import numpy as np

EARTH_KM = 6371.0


def distances(lon, lat):
    lo, la = np.radians(lon), np.radians(lat)
    d = np.sin((la[:, None]-la[None, :])/2)**2+np.cos(la[:, None])*np.cos(la[None, :])*np.sin((lo[:, None]-lo[None, :])/2)**2
    return 2*EARTH_KM*np.arcsin(np.sqrt(np.clip(d, 0, 1)))


def windows(lon, lat, mu, max_share=.5):
    """Neighbour order (m, K) and a validity mask (m, K): window (i, k) = the k + 1 nearest areas to centre i."""
    D = distances(np.asarray(lon, float), np.asarray(lat, float))
    order = np.argsort(D, axis=1, kind="stable")
    share = np.cumsum(np.asarray(mu, float)[order], axis=1)/np.sum(mu)
    valid = share <= max_share+1e-12
    valid[:, 0] = True  # a single area is always a window
    K = int(valid.sum(axis=1).max())
    return order[:, :K], valid[:, :K]


def _llr(cz, mz, C):
    with np.errstate(divide="ignore", invalid="ignore"):
        rest_c, rest_m = C-cz, C-mz
        v = cz*np.log(cz/mz)+np.where(rest_c > 0, rest_c*np.log(rest_c/rest_m), 0.0)
    return np.where(cz > mz, v, 0.0)


def window_llr(c, mu, order, valid):
    """LLR of every window for count vectors c (..., m). Returns (..., m, K)."""
    c = np.asarray(c, float)
    tot = c.sum(axis=-1, keepdims=True)  # (..., 1)
    mus = np.asarray(mu, float)*tot/np.sum(mu)  # expected scaled to the observed total, (..., m)
    cz = np.cumsum(c[..., order], axis=-1)
    mz = np.cumsum(mus[..., order], axis=-1)
    return np.where(valid, _llr(cz, mz, tot[..., None]), 0.0)


def scan(c, mu, lon, lat, max_share=.5, R=999, rng=None, secondary=3, chunk=100):
    """K1: primary and secondary clusters with Monte Carlo (and Gumbel) p-values."""
    rng = rng if rng is not None else np.random.default_rng()
    c = np.asarray(c, float); mu = np.asarray(mu, float)
    order, valid = windows(lon, lat, mu, max_share)
    L = window_llr(c, mu, order, valid)
    C = int(round(c.sum()))
    null_max = []
    for s in range(0, R, chunk):
        n = min(chunk, R-s)
        sims = rng.multinomial(C, mu/mu.sum(), size=n).astype(float)
        null_max.append(window_llr(sims, mu, order, valid).reshape(n, -1).max(axis=1))
    null_max = np.concatenate(null_max)
    mean, sd = null_max.mean(), null_max.std(ddof=1)
    beta = sd*np.sqrt(6)/np.pi; loc = mean-.5772156649*beta
    flat = np.argsort(L, axis=None)[::-1]
    used = np.zeros(len(c), bool); out = []
    for f in flat:
        i, k = np.unravel_index(f, L.shape)
        if L[i, k] <= 0 or len(out) > secondary:
            break
        members = order[i, :k+1]
        if used[members].any():
            continue
        used[members] = True
        cz, mz = c[members].sum(), mu[members].sum()*c.sum()/mu.sum()
        llr = float(L[i, k])
        out.append(dict(center=int(i), members=members.tolist(), cases=float(cz), expected=float(mz),
                        rr=float((cz/mz)/((c.sum()-cz)/(c.sum()-mz))) if c.sum() > cz else np.inf, llr=llr,
                        p_mc=float((1+np.sum(null_max >= llr))/(R+1)),
                        p_gumbel=float(1-np.exp(-np.exp(-(llr-loc)/beta)))))
    return dict(primary=out[0] if out else None, secondary=out[1:], null_max=null_max, windows=int(valid.sum()))
