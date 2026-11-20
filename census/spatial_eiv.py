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

Round 44 re-check on the 155 OH/PA counties (state-respecting clusters, ``docs/audits/ohpa_revalidation.md``):
G1 .867-.909 and G2 .863-.921, so both replicate outside MI/NY.
"""
from typing import Any, Dict, Optional, Sequence

import numpy as np
import pandas as pd
import patsy
from scipy import stats

from . import spatial_eiv_core as core

AUDIT = "docs/audits/spatial_eiv_validation.md"
VALIDATED = {"g1": True, "g2": True}
# Round 35 validated p <= 2; Round 46 (docs/audits/glm_correction_validation.md) p = 3 and 4; Round 53
# (docs/audits/glm_correction2_validation.md) p = 5 (G1 .864-.908, G2 .884-.925); p = 6 failed (.804-.811
# at reliability .7 with 100 km fields).
VALIDATED_MAX_ERROR_COVARIATES = 5
MORE_COVARIATES_AUDIT = "docs/audits/glm_correction_validation.md"
FIVE_COVARIATES_AUDIT = "docs/audits/glm_correction2_validation.md"
OHPA2_AUDIT = "docs/audits/ohpa_revalidation2.md"
# Round 58 (criterion e8c6c8c; docs/audits/spatial_outside_validation.md): with every error-prone covariate at
# reliability .8, G1 and G2 with three to five covariates covered .886-.934 on both MI/NY and OH/PA.
RELIABILITY_GATE = .8
# Round 63 (criterion ac2f34c; docs/audits/small_many_validation.md): under the reliability gate (every error-prone
# covariate >= .8), G1 passed with six to eight error-prone covariates (.873-.918) and G2 with six and seven
# (.876-.940; eight failed at .856 on OH/PA). Without the gate the cap stays 5 (six failed at reliability .7).
GATED_MAX_ERROR_COVARIATES = {"g1": 8, "g2": 7}
MANY_COVARIATES_AUDIT = "docs/audits/small_many_validation.md"
GATE_AUDIT = "docs/audits/spatial_outside_validation.md"


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
                    level: float = 0.90, within_states: bool = False) -> Dict[str, Any]:
    """Corrected slopes with spatially robust inference. ``coords``: GEOID, lon, lat (else Census boundaries).

    ``within_states``: assign the eight clusters equally within each state (adjacent states; G1 replicated
    on OH/PA with two states x four clusters, Round 44)."""
    if method not in VALIDATED:
        raise ValueError("method must be 'g1' or 'g2'")
    data, X, y, D, e, names, error_prone = _design(formula, frame, replicates, fixed_variables)
    if not error_prone:
        raise ValueError("no design column has replicates: use fit_replicate (no correction is needed)")
    from .spatial_clusters import assignment_for_frame
    config = {"k": 8, "method": "im"}
    assign = assignment_for_frame(data, coords, config, within_states=within_states).set_index("GEOID")
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
    if method == "g1":
        from .spatial_clusters import geography_notes
        notes.extend(n for n in geography_notes(assign.loc[ids].reset_index()) if n.startswith("CLUSTERS CROSS"))
    outside = sorted(set(ids.str[:2]) - {"26", "36"})
    cols = [names.index(c) for c in error_prone]
    rel = {c: float(1-np.mean(.05*np.sum(D[:, :, j]**2, axis=0))/np.var(X[:, j], ddof=1)) for c, j in zip(error_prone, cols)}
    min_rel = min(rel.values())
    gated = (VALIDATED_MAX_ERROR_COVARIATES < len(error_prone) <= GATED_MAX_ERROR_COVARIATES[method]
             and min_rel >= RELIABILITY_GATE)
    validated = len(error_prone) <= VALIDATED_MAX_ERROR_COVARIATES or gated
    if gated:
        notes.append(f"{len(error_prone)} error-prone covariates, every estimated reliability >= {RELIABILITY_GATE} "
                     f"(lowest {min_rel:.2f}): validated under the reliability gate (Round 63, {MANY_COVARIATES_AUDIT}; "
                     f"up to {GATED_MAX_ERROR_COVARIATES[method]} for {method.upper()}). Many fits failed in the "
                     "correlated-field cells, so check that the fit converged.")
    if outside and ((method == "g1" and len(error_prone) >= 3) or (method == "g2" and len(error_prone) >= 5)):
        if min_rel >= RELIABILITY_GATE:
            notes.append(f"Outside MI/NY (states {outside}) with {len(error_prone)} error-prone covariates: every estimated "
                         f"reliability is >= {RELIABILITY_GATE} (lowest {min_rel:.2f}), the range validated on OH/PA in "
                         f"Round 58 ({GATE_AUDIT}).")
        else:
            notes.append(f"EXPLORATORY OUTSIDE MI/NY (states {outside}): {method.upper()} with {len(error_prone)} error-prone "
                         f"covariates and a covariate reliability of {min_rel:.2f} (< {RELIABILITY_GATE}) under-covered in the "
                         f"Round 54 OH/PA re-check (.807-.859; {OHPA2_AUDIT}); at reliability {RELIABILITY_GATE} it passed "
                         f"(Round 58, {GATE_AUDIT}).")
    if 3 <= len(error_prone) <= 4:
        notes.append("With 3-4 error-prone covariates, low reliability (.7) and spatially correlated fields, Round 46 "
                     "point estimates were unstable (mean bias up to +.17 on a slope of .5; up to 5.7% failed fits) "
                     f"although interval coverage held (.88-.93; {MORE_COVARIATES_AUDIT}).")
    if len(error_prone) == 5:
        notes.append("With 5 error-prone covariates, low reliability (.7) and spatially correlated fields, Round 53 "
                     "point estimates were very unstable (mean bias -.21 (G1) and +1.24 (G2) on a slope of .5; 3.4% and "
                     "10% failed fits) although interval coverage held (.864-.925; "
                     f"{FIVE_COVARIATES_AUDIT}). Check each covariate's reliability before relying on it.")
    if not validated:
        notes.append(f"EXPLORATORY: {len(error_prone)} error-prone covariates; validated with at most "
                     f"{VALIDATED_MAX_ERROR_COVARIATES}, or up to {GATED_MAX_ERROR_COVARIATES[method]} for "
                     f"{method.upper()} when every reliability is >= {RELIABILITY_GATE} (lowest here {min_rel:.2f}; "
                     f"{AUDIT}; {MORE_COVARIATES_AUDIT}; {FIVE_COVARIATES_AUDIT}; {MANY_COVARIATES_AUDIT}).")
    return dict(method=method, table=table, n=len(y), validated=validated, error_prone=error_prone, reliability=rel,
                notes=notes, audit=AUDIT, **extra)
