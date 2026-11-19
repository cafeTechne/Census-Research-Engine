# SPDX-License-Identifier: AGPL-3.0-or-later
"""Beta regression for shares and median regression for skewed outcomes (Round 40).

Validated by ``docs/audits/beta_median_validation.md`` (criterion d5c9b02), independent areas, naive
target (the slope on the ACS estimates as observed):
- beta regression (logit mean) with the HC0 sandwich: .885-.903 (model-based SEs failed, .856);
- median regression with statsmodels' kernel SE: .912-.917.
Adding the ACS replicate variance over-covered (.95-.99): the outcome's sampling error is already in
the residual variation, so it is not added.
"""
from typing import Any, Dict

import numpy as np
import pandas as pd
import patsy

from . import beta_median_core as bm

AUDIT = "docs/audits/beta_median_validation.md"


def _design(formula, frame):
    y, X = patsy.dmatrices(formula, frame, return_type="dataframe", NA_action="drop")
    return y.to_numpy(float)[:, 0], X


def fit_beta(formula: str, frame: pd.DataFrame, level: float = 0.90) -> Dict[str, Any]:
    """Outcome must be a share in (0, 1) (divide percentages by 100); values are clipped to [0.001, 0.999]."""
    y, X = _design(formula, frame)
    if not ((y >= 0) & (y <= 1)).all():
        raise ValueError("beta regression needs a share between 0 and 1 (divide percentages by 100)")
    b, se = bm.beta_fit(y, X.to_numpy(float), "hc0")
    return _table("beta (logit link, HC0)", b, se, X.columns, len(y), level,
                  ["Coefficients are on the log-odds scale of the mean share; exp(b) is an odds ratio for the mean share."])


def fit_median(formula: str, frame: pd.DataFrame, level: float = 0.90) -> Dict[str, Any]:
    y, X = _design(formula, frame)
    b, se = bm.median_fit(y, X.to_numpy(float))
    return _table("median regression (kernel SE)", b, se, X.columns, len(y), level,
                  ["Coefficients describe the conditional median, robust to skewed outcomes and outliers."])


def _table(name, b, se, columns, n, level, notes):
    from scipy import stats
    z = stats.norm.ppf((1+level)/2)
    table = pd.DataFrame(dict(term=list(columns), estimate=b, se=se, ci_lower=b-z*se, ci_upper=b+z*se,
                              p_value=2*stats.norm.sf(np.abs(b/se))))
    return dict(model=name, table=table, n=n, validated=True, audit=AUDIT,
                notes=notes+["Naive target: the coefficient on the ACS estimates as observed; areas assumed independent."])
