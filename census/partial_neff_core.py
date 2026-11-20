# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 59 frozen core: effective-sample-size interval for a partial correlation under spatial dependence.

x and y are residualised on [1, z]; n_eff is the Clifford-Richardson-Hemon effective size of the two residual
series (``small_spatial_core.effective_n``, Moran's I in distance classes); var(atanh r) = 1/(n_eff - 3 - k) plus
the Round 33 ACS replicate variance term (variant 2: the replicate variance of atanh r, from
``rank_methods.correlation_interval``); k is the number of controls. Normal interval on the atanh scale.
"""
import numpy as np
from scipy import stats

from . import rank_methods as rm
from .small_spatial_core import effective_n


def partial_neff(x, y, z, cls, reps_x=None, reps_y=None, reps_z=None, level=.90):
    x, y = np.asarray(x, float), np.asarray(y, float)
    Z = np.asarray(z, float).reshape(len(x), -1); k = Z.shape[1]
    D = np.column_stack((np.ones(len(x)), Z))
    rx = x-D @ np.linalg.lstsq(D, x, rcond=None)[0]; ry = y-D @ np.linalg.lstsq(D, y, rcond=None)[0]
    ne = effective_n(rx, ry, cls)
    variant = 2 if reps_x is not None else 1
    base = rm.correlation_interval(x, y, "partial", variant, level, reps_x, reps_y, z=Z if k > 1 else Z[:, 0],
                                   reps_z=reps_z)
    n = len(x)
    var_rep = base["se_z"]**2-rm._iid_var("partial", n, k)
    if ne <= 4+k:
        raise ValueError("effective sample size too small")
    var = 1/(ne-3-k)+var_rep
    zr = np.arctanh(base["estimate"]); c = stats.norm.ppf((1+level)/2)
    return dict(estimate=base["estimate"], lower=float(np.tanh(zr-c*np.sqrt(var))), upper=float(np.tanh(zr+c*np.sqrt(var))),
                n_eff=ne, method="partial", variant=variant)
