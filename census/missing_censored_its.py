# SPDX-License-Identifier: AGPL-3.0-or-later
"""Missing covariates, hidden (censored) counts and interrupted time series (Round 42).

Validated by ``docs/audits/missing_censored_its_validation.md`` (criterion 5f81de2):
- multiple imputation of one incomplete covariate (20 proper draws, Rubin's rules): .907-.919, also when
  missingness depends on the outcome (complete case fell to .871);
- interval-censored Poisson for counts hidden as 1-9: .839-.856, FAILED narrowly (overdispersion makes the
  Poisson likelihood misspecified) though better than dropping those areas (.824-.828): exploratory;
- interrupted time series with 20 annual points: OLS, Newey-West and AR(1) GLS all FAILED (.47-.81):
  exploratory, and short series should not carry confirmatory claims.
"""
from typing import Any, Dict, Sequence

import numpy as np
import pandas as pd
import patsy

from . import mci_core as mi

AUDIT = "docs/audits/missing_censored_its_validation.md"


CHAINED_AUDIT = "docs/audits/causal_robustness_validation.md"
CHAINED_VALIDATED = True   # Round 47 D1: .898-.916 (MCAR/MAR, 20-40% missing in each of two covariates)


def impute_and_fit(formula: str, frame: pd.DataFrame, incomplete, m: int = 20, seed: int = 20270304) -> Dict[str, Any]:
    """OLS of ``formula`` with ``incomplete`` (a plain numeric covariate) multiply imputed.

    ``incomplete`` may be a list of two covariates (Round 47): chained equations, 10 cycles, Rubin's rules
    with the Barnard-Rubin df (``causal_robustness_core.chained_mi``). One name keeps the Round 42 routine."""
    if not isinstance(incomplete, str):
        names = list(incomplete)
        if len(names) == 1:
            incomplete = names[0]
        elif len(names) == 2:
            return _impute_two(formula, frame, names, m, seed)
        else:
            raise ValueError("impute supports one or two incomplete covariates (validated)")
    outcome = formula.split("~", 1)[0].strip()
    data = frame.dropna(subset=[outcome]).reset_index(drop=True)
    y, X = patsy.dmatrices(formula, data, return_type="dataframe", NA_action=patsy.NAAction(NA_types=[]))
    if incomplete not in X.columns:
        raise ValueError(f"{incomplete!r} must appear as a plain term in the formula")
    others = [c for c in X.columns if c != incomplete]
    if X[others].isna().any().any():
        raise ValueError("only one covariate may be incomplete")
    miss = int(X[incomplete].isna().sum())
    if miss == 0:
        raise ValueError(f"{incomplete!r} has no missing values")
    terms = [j for j, t in enumerate(X.columns) if t != "Intercept"]
    res = _impute_all_terms(y.to_numpy(float)[:, 0], X.to_numpy(float), list(X.columns).index(incomplete),
                            np.random.default_rng(seed), m, terms)
    rows = [dict(term=X.columns[j], **r) for j, r in zip(terms, res)]
    return dict(table=pd.DataFrame(rows), n=len(y), n_missing=miss, imputations=m, validated=True, audit=AUDIT,
                notes=[f"{miss} areas with {incomplete!r} missing were imputed {m} times (Rubin's rules). Assumes "
                       "missing at random given the model's other variables and outcome."])


def _impute_two(formula, frame, names, m, seed):
    from .causal_robustness_core import chained_mi
    outcome = formula.split("~", 1)[0].strip()
    data = frame.dropna(subset=[outcome]).reset_index(drop=True)
    y, X = patsy.dmatrices(formula, data, return_type="dataframe", NA_action=patsy.NAAction(NA_types=[]))
    for v in names:
        if v not in X.columns:
            raise ValueError(f"{v!r} must appear as a plain term in the formula")
        if not X[v].isna().any():
            raise ValueError(f"{v!r} has no missing values")
    others = [c for c in X.columns if c not in names]
    if X[others].isna().any().any():
        raise ValueError("only the declared covariates may be incomplete")
    cols = [list(X.columns).index(v) for v in names]
    res = chained_mi(y.to_numpy(float)[:, 0], X.to_numpy(float), cols, np.random.default_rng(seed), m=m)
    rows = [dict(term=t, **r) for t, r in zip(X.columns, res) if t != "Intercept"]
    miss = {v: int(X[v].isna().sum()) for v in names}
    return dict(table=pd.DataFrame(rows), n=len(y), n_missing=miss, imputations=m, validated=CHAINED_VALIDATED,
                audit=CHAINED_AUDIT,
                notes=[f"Missing values of {names} ({miss}) imputed {m} times by chained equations (10 cycles; "
                       "Rubin's rules, Barnard-Rubin df; Round 47, validated). Assumes missing at random given "
                       "the model's other variables and outcome."])


def _impute_all_terms(y, X, miss_col, rng, m, terms):
    """``mci_core.multiple_imputation`` (frozen, Round 42) for every term from one set of m imputations.

    Draws the same random numbers in the same order as the frozen routine, so each term's result equals
    the per-term call with the same seed (tests/test_round43.py)."""
    import statsmodels.api as sm
    from scipy import stats
    miss = ~np.isfinite(X[:, miss_col]); obs = ~miss
    P = np.column_stack([np.delete(X, miss_col, axis=1), y])
    fit = sm.OLS(X[obs, miss_col], P[obs]).fit()
    n_obs, k = P[obs].shape
    XtX_inv = np.linalg.inv(P[obs].T @ P[obs])
    est, var = [], []
    for _ in range(m):
        sigma2 = fit.ssr/rng.chisquare(n_obs-k)
        beta = rng.multivariate_normal(fit.params, sigma2*XtX_inv)
        Xi = X.copy(); Xi[miss, miss_col] = P[miss] @ beta+rng.standard_normal(miss.sum())*np.sqrt(sigma2)
        r = sm.OLS(y, Xi).fit(cov_type="HC3")
        est.append(np.asarray(r.params)[terms]); var.append(np.asarray(r.bse)[terms]**2)
    est, var = np.array(est), np.array(var)
    out = []
    for c in range(len(terms)):
        qbar, ubar, bvar = est[:, c].mean(), var[:, c].mean(), np.var(est[:, c], ddof=1)
        T = ubar+(1+1/m)*bvar
        df = (m-1)*(1+ubar/((1+1/m)*bvar))**2 if bvar > 0 else np.inf
        out.append(mi._ci(qbar, np.sqrt(T), stats.t.ppf(.95, df)))
    return out


def fit_censored_poisson(frame: pd.DataFrame, count: str, censored: str, exposure: str, covariates: Sequence[str]) -> Dict[str, Any]:
    """EXPLORATORY. Poisson slopes using areas whose counts are hidden as 1-9 (``censored`` true) as interval
    information. No hidden value is estimated or output (WONDER rule)."""
    f = frame.dropna(subset=[exposure]+list(covariates)).reset_index(drop=True)
    cens = f[censored].astype(bool).to_numpy()
    y = pd.to_numeric(f[count].where(~cens), errors="coerce").fillna(0).to_numpy(float)
    X = np.column_stack([np.ones(len(f))]+[f[c].to_numpy(float) for c in covariates])
    rows = [dict(term=c, **mi.censored_poisson(y, X, f[exposure].to_numpy(float), cens, j+1)) for j, c in enumerate(covariates)]
    return dict(table=pd.DataFrame(rows), n=len(f), n_censored=int(cens.sum()), validated=False, audit=AUDIT,
                notes=["EXPLORATORY: the censored Poisson interval under-covered (.839-.856) with overdispersion; "
                       "it is closer to nominal than dropping hidden areas (.824-.828).",
                       "Hidden counts enter only as 'between 1 and 9'; no county value is estimated or reported."])


def fit_censored_negbin(frame: pd.DataFrame, count: str, censored: str, exposure: str, covariates: Sequence[str]) -> Dict[str, Any]:
    """Validated (Round 45, ``docs/audits/count_repairs_validation.md``): NB2 slopes using areas whose counts are
    hidden as 1-9 (``censored`` true) as interval information; coverage .869-.898 where the censored Poisson
    gave .83-.86. No hidden value is estimated or output (WONDER rule)."""
    from . import count_repairs_core as cr
    f = frame.dropna(subset=[exposure]+list(covariates)).reset_index(drop=True)
    cens = f[censored].astype(bool).to_numpy()
    y = pd.to_numeric(f[count].where(~cens), errors="coerce")
    if y[~cens].isna().any():
        raise ValueError("non-hidden counts must be present")
    X = np.column_stack([np.ones(len(f))]+[f[c].to_numpy(float) for c in covariates])
    E = f[exposure].to_numpy(float)
    rows = [dict(term=c, **cr.censored_negbin(y.fillna(0).to_numpy(float), X, E, cens, j+1)) for j, c in enumerate(covariates)]
    return dict(table=pd.DataFrame(rows), n=len(f), n_censored=int(cens.sum()), validated=True,
                audit="docs/audits/count_repairs_validation.md",
                notes=["Hidden counts enter only as 'between 1 and 9'; no county value is estimated or reported.",
                       "Interval-censored NB2 (validated Round 45); prefer it to fit_censored_poisson."])


def interrupted_series(values: Sequence[float], interruption_index: int, method: str = "ar1",
                       seed: int = 20270601) -> Dict[str, Any]:
    """Level and slope change after ``interruption_index`` (0-based position) in an annual series.

    ``method``: "bootstrap_t_cons" (Round 63: bootstrap_t_bc with critical values at least the t(n - p - 1)
    quantile; validated for 17+ points), "bootstrap_t_bb" (Round 63: bootstrap series at a bootstrap-bias-corrected
    AR coefficient; validated for 19+ points), "bootstrap_t_bc" (Round 55: the bootstrap-t with bootstrap series at a
    bias-corrected AR coefficient; validated for 20+ points), "bootstrap_t" (AR(1) residual bootstrap-t around a REML AR(1) fit,
    499 resamples; validated for 30+ points, Round 48), "reml" (REML AR(1) GLS, t reference; exploratory),
    "ewc" (OLS with an equal-weighted cosine HAR t test; failed, exploratory), or the Round 42 "ar1", "ols",
    "hac" (exploratory)."""
    from . import small_spatial as ss
    from . import small_spatial_core as sc
    y = np.asarray(values, float)
    if len(y) < 8 or not 3 <= interruption_index <= len(y)-3:
        raise ValueError("need at least 8 points and 3 on each side of the interruption")
    X = mi.its_design(len(y), interruption_index+1)
    from . import its_small_core as isc
    phi_bc = None
    if method == "bootstrap_t_bc":
        (level, slope), phi, phi_bc = isc.its_bootstrap_t_bc(y, X, np.random.default_rng(seed))
    elif method == "bootstrap_t_cons":
        (level, slope), phi, phi_bc = isc.its_bootstrap_t_cons(y, X, np.random.default_rng(seed))
    elif method == "bootstrap_t_bb":
        (level, slope), phi, phi_bc = isc.its_bootstrap_t_bb(y, X, np.random.default_rng(seed))
    elif method == "ewc":
        level, slope = isc.its_ewc(y, X); phi = None
    elif method == "bootstrap_t":
        (level, slope), phi = sc.its_bootstrap_t(y, X, np.random.default_rng(seed))
    elif method == "reml":
        (level, slope), phi = sc.its_reml(y, X)
    else:
        level, slope = mi.interrupted(y, X, method); phi = None
    validated = ((method == "bootstrap_t" and len(y) >= ss.ITS_BOOTSTRAP_MIN_N)
                 or (method == "bootstrap_t_bc" and len(y) >= ss.ITS_BOOTSTRAP_BC_MIN_N)
                 or (method == "bootstrap_t_cons" and len(y) >= ss.ITS_BOOTSTRAP_CONS_MIN_N)
                 or (method == "bootstrap_t_bb" and len(y) >= ss.ITS_BOOTSTRAP_BB_MIN_N))
    if validated and method in ("bootstrap_t_cons", "bootstrap_t_bb"):
        mn = ss.ITS_BOOTSTRAP_CONS_MIN_N if method == "bootstrap_t_cons" else ss.ITS_BOOTSTRAP_BB_MIN_N
        notes = [f"{method} (Round 63, {ss.SMALL_SERIES_AUDIT}): validated for {mn}+ annual points. Assumes AR(1) "
                 "errors and a linear trend on each side."]
    elif validated and method == "bootstrap_t_bc":
        notes = [f"AR(1) bootstrap-t at a bias-corrected AR coefficient (Round 55, {ss.SHORT_SERIES_AUDIT}): validated for "
                 f"{ss.ITS_BOOTSTRAP_BC_MIN_N}+ annual points (.867-.889). Assumes AR(1) errors and a linear trend on each side."]
    elif validated:
        notes = [f"AR(1) bootstrap-t (Round 48, {ss.AUDIT}): validated for {ss.ITS_BOOTSTRAP_MIN_N}+ annual points "
                 f"(.883-.896); with 20-29 points use method='bootstrap_t_bc' (Round 55). Assumes AR(1) errors and a "
                 "linear trend on each side."]
    else:
        notes = [f"EXPLORATORY: short-series intervals under-covered (Round 42: OLS, Newey-West, AR(1) GLS .47-.81 at 20 "
                 f"points; Round 48: REML .79-.88; Round 55: EWC .61-.72, {ss.SHORT_SERIES_AUDIT}). Use "
                 f"method='bootstrap_t_cons' with {ss.ITS_BOOTSTRAP_CONS_MIN_N}+ points for confirmatory claims (Round "
                 f"63); below {ss.ITS_BOOTSTRAP_CONS_MIN_N} points no method is validated (all failed at 15)."]
    return dict(level_change=level, slope_change=slope, n=len(y), method=method, phi=phi, phi_bias_corrected=phi_bc,
                validated=validated, audit=(ss.SMALL_SERIES_AUDIT if method in ("bootstrap_t_cons", "bootstrap_t_bb") else
                                            ss.SHORT_SERIES_AUDIT if method in ("bootstrap_t_bc", "ewc") else ss.AUDIT),
                notes=notes)
