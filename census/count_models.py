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
                    level: float = 0.90, spatial: Optional[str] = None, coords: Optional[pd.DataFrame] = None,
                    within_states: bool = False, calibrate=None) -> Dict[str, Any]:
    """Coefficient table for a count outcome with an exposure (offset log exposure).

    ``spatial="clusters"``: IM-8 (Round 45, ``docs/audits/count_repairs_validation.md``): per-cluster count
    GLMs (negbin at the full-sample alpha, or poisson) averaged over the eight fixed clusters, t(7); validated
    for negbin and poisson (.894-.909, MI/NY geometry, spatially correlated residuals).

    ``calibrate`` (Round 53, with ``spatial="clusters"`` only): error-prone covariates as names (SE column
    ``<name>_se``) or ``{name: se_column}``; each is replaced by E[X | W, Z] pooled over all areas
    (``census.models`` regression calibration) before the IM-8 cluster fits. Validated for negbin and
    poisson against the true slope (.877-.909; ``docs/audits/glm_correction2_validation.md``)."""
    if family not in VALIDATED_FAMILIES:
        raise ValueError("family must be negbin (validated), poisson or zip")
    if calibrate is not None and spatial is None:
        raise ValueError("calibrate needs spatial='clusters'; for independent areas use "
                         "models.regression_calibration(model='poisson'|'negbin')")
    if spatial is not None:
        return _fit_count_im(formula, frame, exposure, family, level, spatial, coords, within_states, calibrate)
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
        r = (_negbin_slope(y.to_numpy(float)[:, 0], X.to_numpy(float)[:, cols], E, level) if family == "negbin"
             else mc.count_slope(y.to_numpy(float)[:, 0], X.to_numpy(float)[:, cols], E, family, level))
        rows.append(dict(term=term, **r))
    validated = VALIDATED_FAMILIES[family]
    notes = [f"{family}: slope on the estimates as observed; model (HC3/HC0) SE only, no ACS replicate variance."]
    if not validated:
        notes.append(f"EXPLORATORY: {family} intervals failed validation ({AUDIT}); prefer family='negbin'.")
    return dict(family=family, table=pd.DataFrame(rows), n=len(X), validated=validated, notes=notes, audit=AUDIT)


SPATIAL_VALIDATED = {"negbin": True, "poisson": True, "zip": False}
REPAIRS_AUDIT = "docs/audits/count_repairs_validation.md"
# Round 53 (criterion 8d48956): pooled regression calibration + IM-8 count slopes (rc_spatial_core.rc_im)
# covered the true slope .877-.909 (Poisson, NB2; reliability .7-.9; independent and 100 km fields).
SPATIAL_RC_VALIDATED = {"negbin": True, "poisson": True}
SPATIAL_RC_AUDIT = "docs/audits/glm_correction2_validation.md"


def _fit_count_im(formula, frame, exposure, family, level, spatial, coords, within_states, calibrate=None):
    from scipy import stats
    from . import count_repairs_core as cr
    from .spatial_clusters import assignment_for_frame, geography_notes
    if spatial != "clusters":
        raise ValueError("spatial must be 'clusters' for count models")
    if family == "zip":
        raise ValueError("spatial clusters support negbin and poisson")
    if abs(level-.90) > 1e-12:
        raise ValueError("IM-8 count intervals are validated at the 90% level only")
    data = frame.dropna(subset=[exposure]).copy()
    assign = assignment_for_frame(data, coords, {"k": 8, "method": "im"}, within_states=within_states).set_index("GEOID")
    cal_note = None
    if calibrate is not None:
        from .models import _calibrate, _error_spec, formula_variables
        spec = _error_spec(data, calibrate)
        outcome = formula.split("~", 1)[0].strip()
        used = [v for v in formula_variables(formula, data) if v in data.columns]
        data = data.dropna(subset=used+list(spec.values())).reset_index(drop=True)
        others = [v for v in used if v not in spec and v not in (outcome, exposure)
                  and pd.api.types.is_numeric_dtype(data[v])]
        data = _calibrate(data, spec, others)
        cal_note = (f"Regression calibration of {list(spec)} given {others} (pooled over all areas) before the IM-8 "
                    f"fits; validated for {family} against the true slope (Round 53, {SPATIAL_RC_AUDIT}).")
    y, X = patsy.dmatrices(formula, data, return_type="dataframe", NA_action="drop")
    E = data.loc[X.index, exposure].to_numpy(float)
    labels = assign.loc[data.loc[X.index, "GEOID"].astype(str), "cluster"].to_numpy()
    Xa = X.to_numpy(float)
    rows, absorbed = [], []
    for j, term in enumerate(X.columns):
        if term == "Intercept":
            continue
        per = [np.ptp(Xa[labels == g, j]) > 0 for g in np.unique(labels)]
        if not any(per):
            absorbed.append(term); continue
        if not all(per):
            raise ValueError(f"term {term!r} is constant in some clusters but not others")
        r = cr.im_counts(y.to_numpy(float)[:, 0], Xa, E, labels, family, j)
        rows.append(dict(term=term, df=7, **r))
    notes = [f"IM-8 {family} slopes: per-cluster count GLMs averaged over eight fixed clusters, t(7) "
             f"({REPAIRS_AUDIT}); exposure held fixed (NB2 with noisy ACS exposures covered .888-.891)."]
    if cal_note:
        notes.append(cal_note)
    if absorbed:
        notes.append(f"Absorbed by the cluster intercepts (not estimable): {absorbed}")
    notes += geography_notes(assign.reset_index())
    validated = SPATIAL_VALIDATED[family] and (calibrate is None or SPATIAL_RC_VALIDATED.get(family, False))
    return dict(family=family, spatial="clusters", table=pd.DataFrame(rows), n=len(X), validated=validated,
                notes=notes, audit=REPAIRS_AUDIT)


def _negbin_slope(y, X, exposure, level=.90):
    """``manova_counts_core.count_slope(family="negbin")`` with an optimizer fallback (Round 44).

    The estimator is unchanged (alpha by maximum likelihood, then a GLM with that alpha and HC3). The frozen
    core uses statsmodels' default BFGS; with large counts and little overdispersion (Round 29 premature and
    heart-disease deaths) BFGS can stop unconverged and Newton returns NaN. When BFGS fails, Nelder-Mead
    (from BFGS's last point) is tried and then polished by BFGS; the result is used only if converged, finite
    and at least as good in log-likelihood. When BFGS converges the result equals the frozen core exactly."""
    import warnings
    import statsmodels.api as sm
    from scipy import stats
    try:
        return mc.count_slope(y, X, exposure, "negbin", level)
    except ValueError as exc:
        if "did not converge" not in str(exc):
            raise
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = sm.NegativeBinomial(y, X, exposure=exposure)
        first = model.fit(disp=0, maxiter=200)
        nm = model.fit(start_params=first.params, method="nm", disp=0, maxiter=20000)
        fit = model.fit(start_params=nm.params, method="bfgs", disp=0, maxiter=2000)
        best = fit if (fit.mle_retvals.get("converged", False) and np.isfinite(fit.llf) and fit.llf >= nm.llf-1e-8) else nm
        if not (best.mle_retvals.get("converged", False) and np.all(np.isfinite(best.params))):
            raise ValueError("NB alpha did not converge (BFGS and Nelder-Mead)")
        alpha = float(np.asarray(best.params)[-1])
        if not alpha > 0:
            raise ValueError("NB alpha estimate is not positive")
        r = sm.GLM(y, X, family=sm.families.NegativeBinomial(alpha=alpha), exposure=exposure).fit(cov_type="HC3")
    z = stats.norm.ppf((1+level)/2)
    b, se = float(np.asarray(r.params)[1]), float(np.asarray(r.bse)[1])
    if not (np.isfinite(b) and np.isfinite(se) and se > 0):
        raise ValueError("non-finite slope or SE")
    return dict(estimate=b, se=se, lower=b-z*se, upper=b+z*se)


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
