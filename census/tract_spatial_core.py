# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 71 frozen core: tract-level spatial interval candidates (backlog N49).

T1 spatial error ML slope interval (spreg ML_Error, queen contiguity); T2 SCPC with stronger benchmarks (rho_bar .20,
.30); T3 SCPC with the benchmark set by distance (the average pairwise correlation of a field with a 100 km
exponential range on this geometry, so the benchmark adapts to density); T4 HC3 (comparison). The SCPC core
(census/scpc_core.py) is reused unchanged.
"""
import warnings

import numpy as np
from scipy import stats

from . import scpc_core as sc

Z90 = stats.norm.ppf(.95)


def distance_rho(D, range_km=100.):
    """Average off-diagonal correlation of an exponential field with this range on distance matrix D."""
    D = np.asarray(D, float); off = ~np.eye(len(D), dtype=bool)
    return float(np.exp(-D[off]/range_km).mean())


def hc3(X, y, j=1, level=.90):
    XtX = np.linalg.inv(X.T@X); b = XtX@X.T@y; u = y-X@b
    h = np.einsum("ij,jk,ik->i", X, XtX, X)
    V = XtX@(X.T*(u/(1-h))**2)@X@XtX
    z = stats.norm.ppf(.5+level/2); s = float(np.sqrt(V[j, j]))
    return float(b[j]), float(b[j]-z*s), float(b[j]+z*s)


def sem(X, y, w, j=1, level=.90):
    """Spatial error ML slope interval (normal, model-based SE)."""
    from spreg import ML_Error
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = ML_Error(y[:, None], X[:, 1:], w, method="full")
    b, s = float(m.betas[j, 0]), float(np.sqrt(m.vm[j, j]))
    z = stats.norm.ppf(.5+level/2)
    return b, b-z*s, b+z*s


def scpc_interval(X, y, S, j=1):
    theta, e = sc.influence(X, y, "linear", j)
    iv = sc.interval(theta, e, S)
    return float(theta), float(iv["lower"]), float(iv["upper"])
