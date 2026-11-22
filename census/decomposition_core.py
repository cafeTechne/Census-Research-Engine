# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 79 frozen core: Oaxaca-Blinder and Fairlie decompositions with SDR replicate weights (backlog N56).

Groups A (indicator 1) and B (0); gap = mean_A(y) - mean_B(y), weighted. Covariate blocks: each block is a list of
design columns (a categorical covariate is one block of its non-reference dummies).

O1 Oaxaca-Blinder, twofold with the pooled reference (Neumark 1988; Jann 2008: pooled WLS including the group
indicator): explained = (xbar_A - xbar_B)' b*, unexplained = xbar_A'(b_A - b*) + xbar_B'(b* - b_B). Detailed
explained per block = sum over its columns of (xbar_A,k - xbar_B,k) b*_k; detailed unexplained per block and the
intercept, with categorical blocks normalised (Yun 2005: coefficients re-expressed as deviations from their
mean over all levels, the reference level included, and the intercept shifted accordingly). Threefold
(endowments, coefficients, interaction; group B coefficients as reference) is reported.

F1 Fairlie (2005), logit: pooled weighted logit including the group indicator (coefficients b*, the indicator
excluded from predictions). Total explained = mean_A F(x b*) - mean_B F(x b*) (weighted means); unexplained =
gap - explained. Detailed: R orderings; in each, the larger group is subsampled without replacement to the
smaller group's size, both are ranked by the predicted probability and paired by rank, and the blocks are
switched from A's to B's values one at a time in a random block order; block k's contribution is the
pair-weighted mean change of F when it is switched. Pair weights are w_A,i * w_B,j. Contributions are averaged
over orderings, and rescaled so that they sum to the total explained part. The pairs and orders are drawn once
and reused for every replicate weight.

Variance: the estimator is recomputed with each of the 80 replicate weights (and refitted coefficients);
var = 4/80 sum (theta_r - theta)^2. Normal 90% intervals.
"""
import numpy as np
from scipy import stats

REP = 4/80


def _wmean(X, w):
    return (w[:, None]*X).sum(axis=0)/w.sum() if X.ndim == 2 else (w*X).sum()/w.sum()


def wls(y, X, w):
    Xw = X*w[:, None]
    return np.linalg.solve(X.T@Xw, Xw.T@y)


def logit(y, X, w, start=None, it=50):
    b = np.zeros(X.shape[1]) if start is None else start.copy()
    for _ in range(it):
        eta = np.clip(X@b, -30, 30); p = 1/(1+np.exp(-eta))
        H = (X*(w*p*(1-p))[:, None]).T@X
        step = np.linalg.solve(H, X.T@(w*(y-p)))
        b = b+step
        if np.max(np.abs(step)) < 1e-10:
            break
    return b


def _yun(b, blocks, cat_blocks):
    """Normalise categorical blocks: deviations from the mean over all levels (reference level coefficient 0)."""
    b = b.copy(); shift = 0.0
    for bl in cat_blocks:
        cols = blocks[bl]
        m = b[cols].sum()/(len(cols)+1)
        b[cols] -= m; shift += m
    b[0] += shift
    return b


def _cat_ref_mean(X, w, blocks, cat_blocks):
    """Mean of the omitted reference level of each categorical block (1 - sum of its dummies)."""
    return {bl: 1-_wmean(X[:, blocks[bl]], w).sum() for bl in cat_blocks}


def oaxaca(y, X, group, w, blocks, cat_blocks=()):
    """O1 point estimates. X includes the intercept in column 0; blocks: dict name -> column indices (not 0)."""
    a, bmask = group == 1, group == 0
    XA, XB, wA, wB = X[a], X[bmask], w[a], w[bmask]
    bA, bB = wls(y[a], XA, wA), wls(y[bmask], XB, wB)
    Xp = np.column_stack([X, group.astype(float)])
    bS = wls(y, Xp, w)[:-1]
    mA, mB = _wmean(XA, wA), _wmean(XB, wB)
    out = dict(gap=float(_wmean(y[a], wA)-_wmean(y[bmask], wB)), explained=float((mA-mB)@bS))
    out["unexplained"] = float(mA@(bA-bS)+mB@(bS-bB))
    out["endowments"] = float((mA-mB)@bB); out["coefficients"] = float(mB@(bA-bB)); out["interaction"] = float((mA-mB)@(bA-bB))
    for name, cols in blocks.items():
        out[f"explained:{name}"] = float((mA[cols]-mB[cols])@bS[cols])
    nA, nB, nS = (_yun(b, blocks, cat_blocks) for b in (bA, bB, bS))
    refA, refB = _cat_ref_mean(XA, wA, blocks, cat_blocks), _cat_ref_mean(XB, wB, blocks, cat_blocks)
    for name, cols in blocks.items():
        u = mA[cols]@(nA[cols]-nS[cols])+mB[cols]@(nS[cols]-nB[cols])
        if name in cat_blocks:  # the reference level's normalised coefficient is -(sum of the others' raw)/(L)
            ra = -(bA[cols].sum()/(len(cols)+1)); rb = -(bB[cols].sum()/(len(cols)+1)); rs = -(bS[cols].sum()/(len(cols)+1))
            u += refA[name]*(ra-rs)+refB[name]*(rs-rb)
        out[f"unexplained:{name}"] = float(u)
    out["unexplained:intercept"] = float(nA[0]-nB[0])
    return out


def fairlie_pairs(X, group, w, b_full, R=100, rng=None, blocks=None):
    """Draw the matched pairs and block orders once (from the full-sample fit)."""
    rng = rng if rng is not None else np.random.default_rng()
    ia, ib = np.flatnonzero(group == 1), np.flatnonzero(group == 0)
    n = min(len(ia), len(ib))
    xb = X@b_full
    out = []
    names = list(blocks)
    for _ in range(R):
        sa = ia if len(ia) == n else rng.choice(ia, n, replace=False)
        sb = ib if len(ib) == n else rng.choice(ib, n, replace=False)
        sa = sa[np.argsort(xb[sa], kind="stable")]; sb = sb[np.argsort(xb[sb], kind="stable")]
        out.append((sa, sb, [names[i] for i in rng.permutation(len(names))]))
    return out


def fairlie(y, X, group, w, blocks, pairs=None, R=100, rng=None, start=None):
    """F1 point estimates; returns (dict, b*, pairs). X has the intercept in column 0."""
    Xp = np.column_stack([X, group.astype(float)])
    b = logit(y, Xp, w, start=start)[:-1]
    bfull = np.concatenate([b, [0.0]])
    a = group == 1
    F = lambda Z: 1/(1+np.exp(-np.clip(Z@b, -30, 30)))  # noqa: E731
    gap = _wmean(y[a], w[a])-_wmean(y[~a], w[~a])
    expl = _wmean(F(X[a]), w[a])-_wmean(F(X[~a]), w[~a])
    if pairs is None:
        pairs = fairlie_pairs(X, group, w, b, R=R, rng=rng, blocks=blocks)
    contrib = {k: 0.0 for k in blocks}
    for sa, sb, order in pairs:
        pw = w[sa]*w[sb]; pw = pw/pw.sum()
        Z = X[sa].copy()
        prev = (pw*F(Z)).sum()
        for name in order:
            cols = blocks[name]
            Z[:, cols] = X[sb][:, cols]
            cur = (pw*F(Z)).sum()
            contrib[name] += (prev-cur)/len(pairs)
            prev = cur
    tot = sum(contrib.values())
    out = dict(gap=float(gap), explained=float(expl), unexplained=float(gap-expl))
    for k, v in contrib.items():
        out[f"explained:{k}"] = float(v*expl/tot) if tot != 0 else np.nan
    return out, np.concatenate([b, [0.0]]), pairs


def with_replicates(kind, y, X, group, W, blocks, cat_blocks=(), R=100, rng=None, level=.90):
    """Full-sample estimates (W[:, 0]) and SDR SEs from W[:, 1:81]. Returns {name: (est, se, lower, upper)}."""
    z = stats.norm.ppf(.5+level/2)
    if kind == "oaxaca":
        full = oaxaca(y, X, group, W[:, 0], blocks, cat_blocks)
        reps = [oaxaca(y, X, group, W[:, r], blocks, cat_blocks) for r in range(1, W.shape[1])]
    else:
        full, b, pairs = fairlie(y, X, group, W[:, 0], blocks, R=R, rng=rng)
        reps = [fairlie(y, X, group, W[:, r], blocks, pairs=pairs, start=b)[0] for r in range(1, W.shape[1])]
    out = {}
    for k, v in full.items():
        r = np.array([x[k] for x in reps])
        se = float(np.sqrt(REP*np.sum((r-v)**2)))
        out[k] = (v, se, v-z*se, v+z*se)
    return out
