# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 30 numerical candidates. Validation does not imply engine eligibility.

This file is frozen with the simulation criterion before the full run. No
fallback, cluster deletion or additive ACS variance is part of either candidate.
"""
import numpy as np
import statsmodels.api as sm
from scipy.stats import t


def constant_columns(X, labels, terms, groups=None):
    """Drop only whole nuisance terms constant within every cluster.

    The intercept absorbs their effects. Partial constancy (across clusters or
    columns of a term) is refused rather than changing the fitted estimand.
    """
    X = np.asarray(X, float)
    groups = groups or {term: [i] for i, term in enumerate(terms)}
    keep = np.ones(X.shape[1], bool)
    dropped = []
    for name, cols in groups.items():
        if name == 'Intercept':
            continue
        flags = np.array([[np.allclose(X[labels == g, j], X[labels == g, j][0], rtol=0, atol=1e-12)
                           for j in cols] for g in np.unique(labels)])
        if flags.any() and not flags.all():
            raise ValueError('term constant in some clusters but not others: '+name)
        if flags.all():
            if 'Intercept' not in terms:
                raise ValueError('constant nuisance terms require a cluster intercept')
            keep[cols] = False
            dropped += [terms[j] for j in cols]
    return keep, dropped


def cluster_coefficients(X, y, labels, model, *, trials=None, exposure=None, covariance=None):
    """Fit an already reduced full-rank design in all eight fixed clusters.

    covariance: per-unit error covariance of X. External y has zero sampling
    covariance with X. This is Fuller's existing unweighted moment estimator.
    """
    X, y, labels = np.asarray(X, float), np.asarray(y, float), np.asarray(labels)
    if len(np.unique(labels)) != 8 or not np.isfinite(X).all() or not np.isfinite(y).all():
        raise ValueError('eight finite clusters required')
    if covariance is not None and model != 'linear':
        raise ValueError('EIV candidate supports linear only')
    betas = []
    for g in np.unique(labels):
        rows = labels == g
        x, z = X[rows], y[rows]
        if rows.sum() < max(5, X.shape[1]+1) or np.linalg.matrix_rank(x) != x.shape[1]:
            raise ValueError('every fixed cluster needs >=5 rows and full rank')
        if covariance is not None:
            M = x.T @ x - np.asarray(covariance)[rows].sum(axis=0)
            np.linalg.cholesky((M+M.T)/2)  # fail the WHOLE fit if not positive definite
            b = np.linalg.solve(M, x.T @ z)
        elif model == 'linear':
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
    if betas.ndim != 2 or len(betas) != 8 or not np.isfinite(betas).all():
        raise ValueError('eight finite cluster coefficient vectors required')
    mean = betas.mean(axis=0)
    se = betas.std(axis=0, ddof=1)/np.sqrt(8)
    critical = t.ppf((1+level)/2, 7)
    return dict(estimate=mean, se=se, lower=mean-critical*se, upper=mean+critical*se,
                p_two_sided=2*t.sf(np.abs(mean/se), 7), df=7)
