# SPDX-License-Identifier: AGPL-3.0-or-later
"""Corrected (EIV) linear slopes under spatial dependence (Round 35).

Validated by ``docs/audits/spatial_eiv_validation.md`` (criterion 46fab40): both procedures
covered the true slope at .863-.918 (nominal .90) on the 145 MI/NY counties, with one or two
error-prone covariates, covariate reliability .7-.9, outcome-covariate error correlation 0-.3,
and independent or spatially correlated (range 100 km) fields.

- ``g1``: the eight fixed spatial clusters (Round 26/30 assignment); each cluster's naive slopes
  are corrected by the pooled within-cluster reliability matrix; t(7) on the eight values.
- ``g2``: a spatial-error model's lambda (k = 6 nearest neighbours) whitens the data and the
  replicate deviations; Fuller's estimator and sandwich (as ``fit_eiv``); t(n - p).

Linear models only; the estimand is the true (error-free) slope.
"""
from typing import Any, Dict, Optional, Sequence

import numpy as np
import pandas as pd
import patsy
from scipy import stats

from . import spatial_eiv_core as core

AUDIT = "docs/audits/spatial_eiv_validation.md"
VALIDATED = {"g1": True, "g2": True}
VALIDATED_MAX_ERROR_COVARIATES = 2


def _design(formula, frame, replicates, fixed_variables):
    from .models import _replicate_matrices, formula_variables
    used = formula_variables(formula, frame)
    data = frame.dropna(subset=[c for c in used if c in frame.columns]).reset_index(drop=True)
    y_df, X_df = patsy.dmatrices(formula, data, return_type="dataframe", NA_action="raise")
    outcome = formula.split("~", 1)[0].strip()
    stochastic = [v for v in used if v not in set(fixed_variables) | {outcome}]
    mats, _ = _replicate_matrices(data, replicates, stochastic+([outcome] if outcome not in fixed_variables else []))
    X, y = X_df.to_numpy(float), y_df.to_numpy(float)[:, 0]
    D = np.zeros((80,)+X.shape); e = np.zeros((80, len(y)))
    info = X_df.design_info
    for r in range(80):
        rep = data.copy()
        for v, m in mats.items():
            rep[v] = m[:, r]
        D[r] = np.asarray(patsy.build_design_matrices([info], rep, NA_action="raise")[0], float)-X
        if outcome in mats:
            e[r] = mats[outcome][:, r]-y
    error_prone = [c for j, c in enumerate(X_df.columns) if np.abs(D[:, :, j]).max() > 0]
    return data, X, y, D, e, list(X_df.columns), error_prone


def fit_spatial_eiv(formula: str, frame: pd.DataFrame, replicates: pd.DataFrame, *, method: str = "g1",
                    coords: Optional[pd.DataFrame] = None, fixed_variables: Sequence[str] = (),
                    level: float = 0.90) -> Dict[str, Any]:
    """Corrected slopes with spatially robust inference. ``coords``: GEOID, lon, lat (else Census boundaries)."""
    if method not in VALIDATED:
        raise ValueError("method must be 'g1' or 'g2'")
    data, X, y, D, e, names, error_prone = _design(formula, frame, replicates, fixed_variables)
    if not error_prone:
        raise ValueError("no design column has replicates: use fit_replicate (no correction is needed)")
    from .spatial_clusters import assignment_for_frame
    config = {"k": 8, "method": "im"}
    assign = assignment_for_frame(data, coords, config).set_index("GEOID")
    ids = data["GEOID"].astype(str)
    notes = [f"Estimand: the error-free slope (corrected for ACS sampling error in {error_prone})."]
    if method == "g1":
        labels = assign.loc[ids, "cluster"].to_numpy()
        slope = [j for j, c in enumerate(names) if c != "Intercept"]
        constant = [j for j in slope if all(np.ptp(X[labels == g, j]) == 0 for g in np.unique(labels))]
        partial = [j for j in slope if j not in constant and any(np.ptp(X[labels == g, j]) == 0 for g in np.unique(labels))]
        if partial:
            raise ValueError(f"terms constant in some clusters but not others: {[names[j] for j in partial]}")
        keep = [j for j in slope if j not in constant]
        est = core.g1(X[:, keep], y, D[:, :, keep], e, labels)
        s = core.im_summary(est, level)
        terms = [names[j] for j in keep]
        table = pd.DataFrame(dict(term=terms, estimate=s["estimate"], se=s["se"], ci_lower=s["lower"],
                                  ci_upper=s["upper"], df=s["df"]))
        if constant:
            notes.append(f"Absorbed by the cluster intercepts (not estimable): {[names[j] for j in constant]}")
        extra = {"cluster_estimates": est.tolist(), "cluster_terms": terms}
    else:
        lonlat = assign.loc[ids, ["lon", "lat"]].to_numpy(float)
        W = core.knn_weights(lonlat[:, 0], lonlat[:, 1], 6)
        b, V, lam = core.g2(X, y, D, e, W, np.linalg.eigvals(W))
        df = len(y)-X.shape[1]
        se = np.sqrt(np.diag(V)); crit = stats.t.ppf((1+level)/2, df)
        table = pd.DataFrame(dict(term=names, estimate=b, se=se, ci_lower=b-crit*se, ci_upper=b+crit*se, df=df))
        extra = {"lambda": lam}
        notes.append(f"Spatial-error lambda = {lam:.3f} (k = 6 nearest neighbours).")
    table["p_value"] = 2*stats.t.sf(np.abs(table.estimate/table.se), table.df)
    validated = len(error_prone) <= VALIDATED_MAX_ERROR_COVARIATES
    if not validated:
        notes.append(f"EXPLORATORY: {len(error_prone)} error-prone covariates; validated with at most "
                     f"{VALIDATED_MAX_ERROR_COVARIATES} ({AUDIT}).")
    return dict(method=method, table=table, n=len(y), validated=validated, error_prone=error_prone,
                notes=notes, audit=AUDIT, **extra)
