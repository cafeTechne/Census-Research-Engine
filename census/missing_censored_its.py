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


def impute_and_fit(formula: str, frame: pd.DataFrame, incomplete: str, m: int = 20, seed: int = 20270304) -> Dict[str, Any]:
    """OLS of ``formula`` with ``incomplete`` (a plain numeric covariate) multiply imputed."""
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
    rows = []
    for j, term in enumerate(X.columns):
        if term == "Intercept":
            continue
        r = mi.multiple_imputation(y.to_numpy(float)[:, 0], X.to_numpy(float), list(X.columns).index(incomplete),
                                   np.random.default_rng(seed), m, j)
        rows.append(dict(term=term, **r))
    return dict(table=pd.DataFrame(rows), n=len(y), n_missing=miss, imputations=m, validated=True, audit=AUDIT,
                notes=[f"{miss} areas with {incomplete!r} missing were imputed {m} times (Rubin's rules). Assumes "
                       "missing at random given the model's other variables and outcome."])


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


def interrupted_series(values: Sequence[float], interruption_index: int, method: str = "ar1") -> Dict[str, Any]:
    """EXPLORATORY. Level and slope change after ``interruption_index`` (0-based position) in an annual series."""
    y = np.asarray(values, float)
    if len(y) < 8 or not 3 <= interruption_index <= len(y)-3:
        raise ValueError("need at least 8 points and 3 on each side of the interruption")
    X = mi.its_design(len(y), interruption_index+1)
    level, slope = mi.interrupted(y, X, method)
    return dict(level_change=level, slope_change=slope, n=len(y), method=method, validated=False, audit=AUDIT,
                notes=["EXPLORATORY: with 20 annual points, OLS, Newey-West and AR(1) GLS intervals all under-covered "
                       "(.47-.81) under autocorrelation; do not base confirmatory claims on short series."])
