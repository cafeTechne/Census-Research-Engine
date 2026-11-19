# SPDX-License-Identifier: AGPL-3.0-or-later
"""Count-outcome slopes and multivariate group tests (Round 39).

Validated by ``docs/audits/manova_counts_validation.md`` (criterion 0686bc0):
- negative binomial (NB2, alpha by maximum likelihood, then a GLM with HC3) slope intervals covered
  .885-.901 across expected counts 10-100, gamma overdispersion and 20% structural zeros (naive target:
  the slope on the ACS estimate as observed, model SE only);
- Poisson with HC3 under-covered with strong overdispersion (.808-.867): exploratory here;
- zero-inflated Poisson failed (numerical failures at high counts; under-coverage): exploratory;
- the multivariate wild score bootstrap (several outcomes, one group factor, OLS) held size .090-.101.
"""
from typing import Any, Dict, Optional, Sequence

import numpy as np
import pandas as pd
import patsy

from . import manova_counts_core as mc

AUDIT = "docs/audits/manova_counts_validation.md"
VALIDATED_FAMILIES = {"negbin": True, "poisson": False, "zip": False}


def fit_count_model(formula: str, frame: pd.DataFrame, exposure: str, family: str = "negbin",
                    level: float = 0.90) -> Dict[str, Any]:
    """Coefficient table for a count outcome with an exposure (offset log exposure)."""
    if family not in VALIDATED_FAMILIES:
        raise ValueError("family must be negbin (validated), poisson or zip")
    data = frame.dropna(subset=[exposure]).copy()
    y, X = patsy.dmatrices(formula, data, return_type="dataframe", NA_action="drop")
    E = data.loc[X.index, exposure].to_numpy(float)
    if not (E > 0).all():
        raise ValueError("exposure must be positive")
    rows = []
    for j, term in enumerate(X.columns):
        if term == "Intercept":
            continue
        cols = [0, j] + [k for k in range(1, X.shape[1]) if k != j]
        r = mc.count_slope(y.to_numpy(float)[:, 0], X.to_numpy(float)[:, cols], E, family, level)
        rows.append(dict(term=term, **r))
    validated = VALIDATED_FAMILIES[family]
    notes = [f"{family}: slope on the estimates as observed; model (HC3/HC0) SE only, no ACS replicate variance."]
    if not validated:
        notes.append(f"EXPLORATORY: {family} intervals failed validation ({AUDIT}); prefer family='negbin'.")
    return dict(family=family, table=pd.DataFrame(rows), n=len(X), validated=validated, notes=notes, audit=AUDIT)


def compare_groups_multivariate(frame: pd.DataFrame, outcomes: Sequence[str], group: str, *,
                                replicates: Optional[pd.DataFrame] = None, covariates: Sequence[str] = (),
                                seed: int = 20270211) -> Dict[str, Any]:
    """MANOVA/MANCOVA: does the group factor shift any of ``outcomes``? (OLS; areas independent)."""
    from .models import _replicate_matrices
    outcomes, covariates = list(outcomes), list(covariates)
    if len(outcomes) < 2:
        raise ValueError("a multivariate test needs at least two outcomes (use compare_groups for one)")
    data = frame.dropna(subset=outcomes+[group]+covariates).reset_index(drop=True)
    data[group] = data[group].astype(str)
    if (data[group].value_counts() < 5).any():
        raise ValueError("every group needs at least 5 areas")
    rhs = " + ".join([f"C({group})"]+covariates)
    X_df = patsy.dmatrix(rhs, data, return_type="dataframe")
    X, Y = X_df.to_numpy(float), data[outcomes].to_numpy(float)
    test = [j for j, c in enumerate(X_df.columns) if c.startswith(f"C({group})")]
    b = mc.stacked_coefficients(X, Y, test)
    Vs = np.zeros((len(b), len(b)))
    if replicates is not None:
        mats, _ = _replicate_matrices(data, replicates, outcomes+covariates)
        reps = []
        for r in range(80):
            rep = data.copy()
            for v, m in mats.items():
                rep[v] = m[:, r]
            Xr = np.asarray(patsy.build_design_matrices([X_df.design_info], rep)[0], float)
            reps.append(mc.stacked_coefficients(Xr, rep[outcomes].to_numpy(float), test))
        d = np.array(reps)-b
        Vs = .05*d.T @ d
    out = mc.mv_wild_score(X, Y, test, Vs, np.random.default_rng(seed))
    pil = mc.pillai(X, Y, test)
    return dict(outcomes=outcomes, group=group, n=len(data), q=len(test), test="multivariate wild score bootstrap",
                statistic=out["statistic"], p_value=out["p"], validated=True,
                pillai=dict(pil, note="iid; ignores sampling error; comparison only"),
                notes=["Areas assumed independent (spatial dependence makes p-values too small).",
                       "With replicates, their joint covariance (all outcomes) is added (conservative target)."],
                audit=AUDIT)
