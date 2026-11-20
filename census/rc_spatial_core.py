# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 53 frozen core: regression calibration with IM-8 clusters for count slopes.

``rc_im`` replaces the error-prone covariates W by E[X | W, Z] with the engine's pooled calibration
(``census.models._calibrate``: all areas, per-area error variances, Var(X) by moments), then applies the
frozen Round 45 IM-8 count estimator (``census.count_repairs_core.im_counts``: per-cluster Poisson or NB2 GLM
at the full-sample alpha, mean of the cluster slopes, t(G - 1)). The calibration is not re-estimated per
cluster; its estimation error is ignored by the cluster summary (the validation judges whether that matters).
"""
import numpy as np
import pandas as pd

from .count_repairs_core import im_counts
from .models import _calibrate


def rc_im(y, W, se, Z, exposure, labels, family, j=1):
    """y (n,), W (n, k) error-prone covariates, se (n, k) their sampling SEs, Z (n, m) error-free covariates
    (may be empty), exposure (n,), labels (n,) cluster ids, family 'poisson' | 'negbin'.

    Returns the IM summary dict (estimate, se, lower, upper, ...) for design column ``j`` of
    [1, calibrated W, Z] (j = 1 is the first error-prone covariate)."""
    W = np.atleast_2d(np.asarray(W, float)); se = np.atleast_2d(np.asarray(se, float))
    Z = np.zeros((len(W), 0)) if Z is None else np.asarray(Z, float).reshape(len(W), -1)
    k, m = W.shape[1], Z.shape[1]
    ws = [f"w{i}" for i in range(k)]; zs = [f"z{i}" for i in range(m)]
    frame = pd.DataFrame(np.column_stack((W, se, Z)), columns=ws+[w+"_se" for w in ws]+zs)
    xhat = _calibrate(frame, {w: w+"_se" for w in ws}, zs)[ws].to_numpy(float)
    X = np.column_stack((np.ones(len(W)), xhat, Z))
    return im_counts(y, X, exposure, labels, family, j=j)


def rc_im_binomial(y, W, se, Z, trials, labels, j=1):
    """Round 58: binomial counterpart of ``rc_im``. Pooled calibration (``models._calibrate``), then IM over the
    fixed clusters with a binomial GLM per cluster (``im_clusters_core``; t(G - 1)). Terms constant within every
    cluster (e.g. a state indicator with within-state clusters) are absorbed by the cluster intercepts."""
    from .im_acs import constant_columns
    from . import im_clusters_core as imc
    W = np.atleast_2d(np.asarray(W, float)); se = np.atleast_2d(np.asarray(se, float))
    Z = np.zeros((len(W), 0)) if Z is None else np.asarray(Z, float).reshape(len(W), -1)
    k, m = W.shape[1], Z.shape[1]
    ws = [f"w{i}" for i in range(k)]; zs = [f"z{i}" for i in range(m)]
    frame = pd.DataFrame(np.column_stack((W, se, Z)), columns=ws+[w+"_se" for w in ws]+zs)
    xhat = _calibrate(frame, {w: w+"_se" for w in ws}, zs)[ws].to_numpy(float)
    X = np.column_stack((np.ones(len(W)), xhat, Z))
    labels = np.asarray(labels)
    keep, _ = constant_columns(X, labels, ["Intercept"]+ws+zs)
    if not keep[j]:
        raise ValueError("slope column constant within clusters")
    s = imc.summarize(imc.cluster_coefficients(X[:, keep], y, labels, "binomial", trials=trials))
    jj = int(np.flatnonzero(keep).tolist().index(j))
    return dict(estimate=float(s["estimate"][jj]), se=float(s["se"][jj]), lower=float(s["lower"][jj]),
                upper=float(s["upper"][jj]), df=s["df"])
