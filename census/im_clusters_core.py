# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 54 frozen core: Ibragimov-Mueller cluster inference with G fixed clusters (G = 4, 6 or 8).

The same per-cluster estimators as ``census.im_acs`` (OLS, or a binomial/Poisson GLM per cluster), averaged
over the G clusters with a t(G - 1) reference. ``census.im_acs`` requires exactly eight clusters; for G = 8
these functions give identical results.
"""
import numpy as np
import statsmodels.api as sm
from scipy.stats import t


def cluster_coefficients(X, y, labels, model, *, trials=None, exposure=None, min_rows=5):
    X, y, labels = np.asarray(X, float), np.asarray(y, float), np.asarray(labels)
    groups = np.unique(labels)
    if len(groups) < 2 or not np.isfinite(X).all() or not np.isfinite(y).all():
        raise ValueError('at least two finite clusters required')
    betas = []
    for g in groups:
        rows = labels == g
        x, z = X[rows], y[rows]
        if rows.sum() < max(min_rows, X.shape[1]+1) or np.linalg.matrix_rank(x) != x.shape[1]:
            raise ValueError('every fixed cluster needs >=5 rows and full rank')
        if model == 'linear':
            b = np.linalg.lstsq(x, z, rcond=None)[0]
        elif model in ('binomial', 'poisson'):
            kwargs = ({'family': sm.families.Binomial(), 'var_weights': np.asarray(trials)[rows]}
                      if model == 'binomial' else
                      {'family': sm.families.Poisson(), 'offset': np.log(np.asarray(exposure)[rows])})
            fit = sm.GLM(z, x, **kwargs).fit()
            if not fit.converged:
                raise ValueError('cluster GLM did not converge')
            b = np.asarray(fit.params)
        else:
            raise ValueError('unknown model')
        if not np.isfinite(b).all():
            raise ValueError('nonfinite cluster estimate')
        betas.append(b)
    return np.asarray(betas)


def summarize(betas, level=.90):
    betas = np.asarray(betas, float)
    G = len(betas)
    if betas.ndim != 2 or G < 2 or not np.isfinite(betas).all():
        raise ValueError('at least two finite cluster coefficient vectors required')
    mean = betas.mean(axis=0)
    se = betas.std(axis=0, ddof=1)/np.sqrt(G)
    critical = t.ppf((1+level)/2, G-1)
    return dict(estimate=mean, se=se, lower=mean-critical*se, upper=mean+critical*se,
                p_two_sided=2*t.sf(np.abs(mean/se), G-1), df=G-1)
