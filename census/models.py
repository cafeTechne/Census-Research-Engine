# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression with known ACS sampling error (PLAN_ROUND_8 workstream B).

Inputs follow the analysis-frame convention of :mod:`census.results` (built by
:func:`census.analysis.analysis_frame`); results are
:class:`census.results.ModelResult`.

B1. Replicate inference (preferred), :func:`fit_replicate`. The model is fit
    on the full-sample estimates and refit on each of the 80 replicate data
    sets (every ACS variable replaced by its r-th replicate value). Then

        Var_sampling(b) = 4/80 * sum_r (b_r - b)^2

    the successive-difference replication formula of the ACS Variance
    Replicate Estimate tables (U.S. Census Bureau, "Variance Replicate
    Estimate Tables Documentation";
    https://www.census.gov/programs-surveys/acs/data/variance-tables.html; and
    ACS Design and Methodology, 2014, ch. 13). Following decision 2 of
    PLAN_ROUND_8, ``se_total = sqrt(se_model^2 + se_sampling^2)``: the model
    SE of the full fit plus the replicate sampling SE. Because the model
    residual variance already absorbs some outcome sampling noise, the total
    is conservative; both components are always reported.

B2. Model-based corrections for covariates measured with known error
    (when replicates are unavailable):

    * :func:`regression_calibration`: each noisy covariate is replaced by its
      best linear predictor given all observed covariates, with
      heteroscedastic known error variances s_i^2 (Carroll, Ruppert,
      Stefanski & Crainiceanu, "Measurement Error in Nonlinear Models: A
      Modern Perspective", 2nd ed., 2006, ch. 4). SEs by row bootstrap that
      re-estimates the calibration (Carroll et al. 2006, sec. 4.6 / App. B.5).
    * :func:`simex`: simulation-extrapolation (Cook & Stefanski 1994, JASA
      89:1314-1328), heteroscedastic form W + sqrt(lambda) s_i Z
      (Devanarayan & Stefanski 2002, Stat. Prob. Letters 59:219-225),
      quadratic extrapolation to lambda = -1; variance by the SIMEX
      "measurement-error jackknife" (Stefanski & Cook 1995, JASA 90:1247-1256).

    Both always report the naive fit alongside (``naive_estimate``,
    ``naive_se`` columns and ``diagnostics["naive"]``).

    Outcomes with known sampling variance (Fay-Herriot / meta-regression
    structure, weights 1/(sigma_u^2 + s_i^2)) are handled by
    ``census.sae.fh_regression``, not here.

B3. Models: ``ols``, ``wls`` (``weights`` column), ``binomial`` (GLM for
    proportions in [0, 1], trials = a column or the effective sample size
    p(1-p)/SE(p)^2 (Kish 1965 design-effect logic)), ``poisson`` (GLM with
    ``exposure``), ``negbin`` (statsmodels NegativeBinomial with ``exposure``).
    Fitting uses statsmodels formula models (patsy).
B4. Numeric diagnostics: share of residual variance attributable to known
    outcome sampling error, influence of high-CV observations, coefficient
    stability across replicates, and the reliability screen (CV > 30% kept and
    reported, decision 4).
"""

import math
import re
import warnings
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats as sps

from .analysis import formula_variables
from .results import (
    COEFFICIENT_COLUMNS,
    TARGET_SE,
    interval_description,
    SOURCE_MODEL,
    SOURCE_SAMPLING_MODEL,
    SOURCE_SAMPLING_REPLICATE,
    ModelResult,
    check_refit_count,
    check_replicate_policy,
    precheck_replicates,
    replicate_completeness,
    stochastic_variables,
)
from .variance import REPLICATE_COLUMNS, REPLICATE_COUNT, REPLICATE_FACTOR

MODELS = ("ols", "wls", "binomial", "poisson", "negbin")
DEFAULT_CV_THRESHOLD = 30.0
FH_POINTER = (
    "for an outcome with known sampling variance use census.sae.fh_regression "
    "(Fay-Herriot weights 1/(sigma_u^2 + s_i^2))"
)
SCALES = ("X2", "robust")
ROBUST_SE_NOTE = (
    "Robust (HC3 sandwich) SEs for the binomial/Poisson GLM: valid under extra-binomial or extra-Poisson "
    "variation between areas, which Pearson X2 scaling does not repair when the overdispersion does not "
    "shrink with the denominator (validated, docs/audits/robust_se_validation.md). Units are treated as "
    "independent: spatial dependence in the residuals is not covered."
)


def glm_robust_covariance(X: np.ndarray, y: np.ndarray, mu: np.ndarray, model: str,
                          trials: Optional[np.ndarray] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
    """HC3 sandwich covariance of a canonical-link binomial or Poisson GLM.

    Binomial: ``y`` and ``mu`` are proportions, ``trials`` the denominators
    (the GLM's var_weights); score_i = x_i t_i (y_i - mu_i), weight t_i mu_i (1 - mu_i).
    Poisson: ``y`` and ``mu`` are counts; score_i = x_i (y_i - mu_i), weight mu_i.
    Bread B = (X'WX)^-1, leverage h_i = w_i x_i'B x_i, meat sum s_i s_i' / (1 - h_i)^2.
    Returns the covariance and ``{"estimator": "HC3", "max_leverage": ...}``.
    """
    X = np.asarray(X, float)
    y, mu = np.asarray(y, float), np.asarray(mu, float)
    if model == "binomial":
        if trials is None:
            raise ValueError("binomial robust covariance needs trials")
        t = np.asarray(trials, float)
        resid, w = t * (y - mu), t * mu * (1 - mu)
    elif model == "poisson":
        resid, w = y - mu, mu
    else:
        raise ValueError("robust GLM covariance supports binomial and poisson")
    bread = np.linalg.inv(X.T @ (w[:, None] * X))
    h = w * np.einsum("ij,jk,ik->i", X, bread, X)
    if np.any(h >= 1 - 1e-12):
        raise ValueError("a unit has leverage 1; HC3 is undefined (drop or merge that unit)")
    s = X * (resid / (1 - h))[:, None]
    return bread @ (s.T @ s) @ bread, {"estimator": "HC3", "max_leverage": float(h.max())}


# ---------------------------------------------------------------------------
# Fitting
# ---------------------------------------------------------------------------


def _outcome(formula: str) -> str:
    return formula.split("~", 1)[0].strip()


def _fit(
    formula: str,
    data: pd.DataFrame,
    model: str,
    weights: Optional[str] = None,
    exposure: Optional[str] = None,
    trials: Optional[np.ndarray] = None,
    scale: Optional[str] = None,
) -> Any:
    model = model.lower()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if model == "ols":
            return smf.ols(formula, data, missing="drop").fit()
        if model == "wls":
            if not weights:
                raise ValueError("model='wls' needs weights=<column>")
            return smf.wls(formula, data, weights=data[weights], missing="drop").fit()
        if model == "binomial":
            if trials is None:
                raise ValueError("model='binomial' needs trials")
            return smf.glm(formula, data, family=sm.families.Binomial(),
                           var_weights=np.asarray(trials, float), missing="drop").fit(**({"scale": scale} if scale else {}))
        expo = data[exposure].to_numpy(float) if exposure else None
        if model == "poisson":
            return smf.glm(formula, data, family=sm.families.Poisson(), exposure=expo, missing="drop").fit(**({"scale": scale} if scale else {}))
        if model == "negbin":
            return smf.negativebinomial(formula, data, exposure=expo, missing="drop").fit(disp=0, maxiter=200)
    raise ValueError(f"unknown model {model!r}; expected one of {MODELS}")


def _complete_rows(frame: pd.DataFrame, formula: str, extra: Sequence[Optional[str]]) -> pd.DataFrame:
    cols = formula_variables(formula, frame) + [c for c in extra if c]
    num = [c for c in cols if pd.api.types.is_numeric_dtype(frame[c])]
    mask = np.isfinite(frame[num].to_numpy(float)).all(axis=1) if num else np.ones(len(frame), bool)
    mask &= frame[[c for c in cols if c not in num]].notna().all(axis=1).to_numpy() if len(cols) > len(num) else True
    return frame.loc[mask].reset_index(drop=True)


def effective_trials(p: np.ndarray, se: np.ndarray) -> np.ndarray:
    """Effective sample size p(1-p)/SE^2 of a proportion estimate (NaN when undefined)."""
    p, se = np.asarray(p, float), np.asarray(se, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        n = p * (1 - p) / se ** 2
    return np.where((p > 0) & (p < 1) & (se > 0) & np.isfinite(n), n, np.nan)


def _prepare(frame, formula, model, weights, exposure, trials):
    data = _complete_rows(frame, formula, [weights, exposure, trials if isinstance(trials, str) else None])
    n_trials = None
    notes: List[str] = []
    if model == "binomial":
        y = _outcome(formula)
        if isinstance(trials, str):
            n_trials = data[trials].to_numpy(float)
        else:
            if f"{y}_se" not in data:
                raise ValueError(f"binomial model needs trials=<column> or a '{y}_se' column for effective trials")
            n_trials = effective_trials(data[y].to_numpy(float), data[f"{y}_se"].to_numpy(float))
            notes.append("binomial trials = effective sample size p(1-p)/SE(p)^2 of the outcome")
        if np.nanmax(data[y].to_numpy(float)) > 1 or np.nanmin(data[y].to_numpy(float)) < 0:
            raise ValueError("binomial outcome must be a proportion in [0, 1] (divide percents by 100)")
        keep = np.isfinite(n_trials) & (n_trials > 0)
        if (~keep).any():
            notes.append(f"{int((~keep).sum())} row(s) dropped: effective trials undefined (p in {{0,1}} or SE 0/missing)")
        data, n_trials = data.loc[keep].reset_index(drop=True), n_trials[keep]
    return data, n_trials, notes


def _z(confidence_level: float) -> float:
    return float(sps.norm.ppf(0.5 + confidence_level / 2.0))


# Which standard error the interval and p-value use (validated in
# docs/audits/inference_validation.md, 1,000 simulated datasets, nominal 90%):
#   "population"   se_model:    coverage 0.896 for the superpopulation coefficient.
#                  The model residual already absorbs outcome sampling error.
#   "these_areas"  se_sampling: coverage 0.895 for the coefficient among these
#                  areas in this period (finite population), from replicates.
#   "conservative" se_total = sqrt(se_model^2 + se_sampling^2): coverage 0.961;
#                  double-counts outcome sampling error (PLAN_ROUND_8 decision 2,
#                  revised after validation).
INTERVAL_TARGETS = ("population", "these_areas", "conservative")


_TARGET_SE = TARGET_SE


def interval_se_column(result: Any) -> str:
    """The SE column that a result's p-values and intervals are based on.

    fit_replicate records ``diagnostics['interval_target']``; corrected
    methods (regression calibration, SIMEX) and Fay-Herriot use se_total.
    See census.results.interval_description for the full interpretation.
    """
    return interval_description(result)["basis_column"]


def _table(params: pd.Series, se_model: pd.Series, se_sampling: pd.Series, confidence_level: float,
           target: str = "population") -> pd.DataFrame:
    se_total = np.sqrt(se_model.to_numpy(float) ** 2 + np.nan_to_num(se_sampling.to_numpy(float)) ** 2)
    se_total = np.where(np.isnan(se_model.to_numpy(float)), np.nan, se_total)
    basis = {"population": se_model.to_numpy(float), "these_areas": se_sampling.to_numpy(float),
             "conservative": se_total}[target]
    z = _z(confidence_level)
    est = params.to_numpy(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        p = 2 * sps.norm.sf(np.abs(est / basis))
    return pd.DataFrame({
        "term": list(params.index), "estimate": est,
        "se_model": se_model.to_numpy(float), "se_sampling": se_sampling.to_numpy(float),
        "se_total": se_total, "ci_lower": est - z * basis, "ci_upper": est + z * basis,
        "p_value": p,
    })[COEFFICIENT_COLUMNS]


# ---------------------------------------------------------------------------
# B2. reliability screen
# ---------------------------------------------------------------------------


def reliability_screen(
    frame: pd.DataFrame,
    variables: Optional[Union[str, Sequence[str]]] = None,
    threshold: float = DEFAULT_CV_THRESHOLD,
) -> pd.DataFrame:
    """Observations whose CV (percent) exceeds ``threshold`` (Census: >30% is low reliability).

    ``variables``: names, or a formula whose frame variables are screened.
    Rows are reported, never dropped (PLAN_ROUND_8 decision 4).
    """
    if isinstance(variables, str):
        variables = formula_variables(variables, frame) if "~" in variables else [variables]
    names = [v for v in (variables or [c for c in frame.columns if f"{c}_cv" in frame.columns])
             if f"{v}_cv" in frame.columns]
    keys = [c for c in ("GEOID", "Year", "NAME") if c in frame.columns]
    parts = []
    for v in names:
        cv = frame[f"{v}_cv"].to_numpy(float)
        hit = cv > threshold
        if hit.any():
            part = frame.loc[hit, keys].copy()
            part["variable"] = v
            part["estimate"] = frame.loc[hit, v].to_numpy(float)
            part["se"] = frame.loc[hit, f"{v}_se"].to_numpy(float)
            part["cv"] = cv[hit]
            parts.append(part)
    cols = keys + ["variable", "estimate", "se", "cv"]
    out = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=cols)
    out.attrs["threshold"] = threshold
    return out


def _screen_summary(frame: pd.DataFrame, formula: str, threshold: float) -> Dict[str, Any]:
    screen = reliability_screen(frame, formula, threshold)
    counts = screen["variable"].value_counts().to_dict() if len(screen) else {}
    return {"threshold_cv_percent": threshold, "rows_flagged_by_variable": counts,
            "n_flags": int(len(screen))}


# ---------------------------------------------------------------------------
# B1. replicate refits
# ---------------------------------------------------------------------------


def _replicate_matrices(data: pd.DataFrame, replicates: pd.DataFrame, used: Sequence[str]) -> Tuple[Dict[str, np.ndarray], Dict[str, int]]:
    keys = ["GEOID"] + (["Year"] if "Year" in data.columns and "Year" in replicates.columns else [])
    idx = pd.MultiIndex.from_frame(data[keys]) if len(keys) > 1 else pd.Index(data["GEOID"].astype(str))
    mats: Dict[str, np.ndarray] = {}
    fixed: Dict[str, int] = {}
    for v in used:
        sub = replicates[replicates["variable"] == v]
        if not len(sub):
            continue
        sub = sub.assign(GEOID=sub["GEOID"].astype(str)).set_index(keys)
        m = sub[REPLICATE_COLUMNS].reindex(idx).to_numpy(float, copy=True)  # (n, 80)
        miss = ~np.isfinite(m).all(axis=1)
        if miss.any():  # hold the full-sample value fixed where no replicates exist
            m[miss] = data[v].to_numpy(float)[miss, None]
            fixed[v] = int(miss.sum())
        mats[v] = m
    return mats, fixed


RELIABILITY_NOTE_THRESHOLD = 0.9
RELIABILITY_GROUP_SPREAD = 0.02


def _factor_expressions(formula: str) -> List[str]:
    """The expressions inside every C(...) of a formula, with balanced parentheses
    (``C(GEOID.str[:2])`` -> ``GEOID.str[:2]``; contrast arguments are dropped)."""
    out: List[str] = []
    i = 0
    while True:
        j = formula.find("C(", i)
        if j < 0:
            return out
        if j > 0 and (formula[j - 1].isalnum() or formula[j - 1] == "_"):
            i = j + 2
            continue
        depth, k = 1, j + 2
        while k < len(formula) and depth:
            depth += {"(": 1, ")": -1}.get(formula[k], 0)
            k += 1
        inner = formula[j + 2:k - 1]
        # drop a contrast argument at depth 0 (C(x, Treatment))
        d, cut = 0, len(inner)
        for pos, ch in enumerate(inner):
            d += {"(": 1, "[": 1, ")": -1, "]": -1}.get(ch, 0)
            if ch == "," and d == 0:
                cut = pos
                break
        expr = inner[:cut].strip()
        if expr and expr not in out:
            out.append(expr)
        i = k


def _factor_groups(formula: str, data: pd.DataFrame, max_groups: int = 50) -> Dict[str, np.ndarray]:
    """Group labels of every factor C(<expr>) in the formula, evaluated by patsy on ``data``
    (so C(GEOID.str[:2]) groups by state, not by tract). Factors with more than ``max_groups``
    levels (unit identifiers) or that fail to evaluate are skipped."""
    import patsy
    out: Dict[str, np.ndarray] = {}
    for expr in _factor_expressions(formula):
        try:
            dm = patsy.dmatrix(f"C({expr}) - 1", data, return_type="dataframe", NA_action="raise")
        except Exception:  # noqa: BLE001 - a diagnostic never fails the fit
            continue
        if dm.shape[1] < 2 or dm.shape[1] > max_groups or len(dm) != len(data):
            continue
        labels = np.asarray(dm.columns)[dm.to_numpy().argmax(axis=1)]
        out[f"C({expr})"] = np.array([str(c).rsplit("[", 1)[-1][:-1] for c in labels])
    return out


def covariate_reliability(formula: str, data: pd.DataFrame, mats: Mapping[str, np.ndarray]) -> Dict[str, Any]:
    """Replicate reliability 1 - mean(SE^2) / Var(x) of each numeric covariate with replicates
    (PLAN_ROUND_20 A3), overall and within each group of every factor named as C(<column>) in the
    formula. ``low``: covariates below RELIABILITY_NOTE_THRESHOLD; ``uneven``: covariates whose
    group reliabilities differ by more than RELIABILITY_GROUP_SPREAD (a slope comparison
    between those groups is then biased by measurement error alone)."""
    y = _outcome(formula)
    factors = _factor_groups(formula, data)
    out: Dict[str, Any] = {"covariates": {}, "by_group": {}, "low": [], "uneven": []}

    def rel_of(x: np.ndarray, m: np.ndarray) -> float:
        if len(x) < 3:
            return float("nan")
        err = float(np.mean(REPLICATE_FACTOR * ((m - x[:, None]) ** 2).sum(axis=1)))
        v = float(np.var(x, ddof=1))
        return 1.0 - err / v if v > 0 else float("nan")

    for v, m in mats.items():
        if v == y or v not in data.columns or not pd.api.types.is_numeric_dtype(data[v]):
            continue
        x = data[v].to_numpy(float)
        r = rel_of(x, m)
        out["covariates"][v] = r
        if np.isfinite(r) and r < RELIABILITY_NOTE_THRESHOLD:
            out["low"].append(v)
        for fcol, groups in factors.items():
            per = {g: rel_of(x[groups == g], m[groups == g]) for g in sorted(set(groups))}
            out["by_group"].setdefault(v, {})[fcol] = per
            vals = [q for q in per.values() if np.isfinite(q)]
            if len(vals) > 1 and max(vals) - min(vals) > RELIABILITY_GROUP_SPREAD and v not in out["uneven"]:
                out["uneven"].append(v)
    return out


def fit_replicate(
    formula: str,
    frame: pd.DataFrame,
    replicates: Optional[pd.DataFrame] = None,
    model: str = "ols",
    weights: Optional[str] = None,
    exposure: Optional[str] = None,
    trials: Optional[str] = None,
    confidence_level: float = 0.90,
    cv_threshold: float = DEFAULT_CV_THRESHOLD,
    max_failed_replicates: int = 0,
    target: str = "population",
    replicate_policy: str = "flag",
    fixed_variables: Sequence[str] = (),
    scale: Optional[str] = None,
    spatial_se: Optional[Mapping] = None,
    coords: Optional[pd.DataFrame] = None,
    spatial_clusters: Optional[Mapping] = None,
) -> ModelResult:
    """Fit a statsmodels formula model with ACS replicate sampling SEs.

    ``replicates`` is the long frame from
    :func:`census.analysis.attach_replicates`. Every formula variable present
    there is replaced by its replicate values in each of the 80 refits;
    others (and weights, exposure, trials) stay at their full-sample values.
    Without replicates only model SEs are reported, with a note pointing to
    :func:`regression_calibration`, :func:`simex`, or census.sae.fh_regression.
    ``target`` chooses the SE behind ``ci_lower``/``ci_upper``/``p_value``
    (see INTERVAL_TARGETS): "population" (default, se_model) for the general
    relationship; "these_areas" (se_sampling, needs replicates) for the
    relationship among these areas given ACS sampling error; "conservative"
    (se_total). All three SEs are always reported. ``replicate_policy``
    (census.results.replicate_completeness): "flag" (default, exploratory)
    keeps the estimate when refits failed (up to ``max_failed_replicates``),
    rows lack replicates, or a variable with an SE column has no replicates,
    and records diagnostics["replicates_incomplete"]; "strict" (confirmatory,
    used by census.manifest) raises ValueError instead. Replicates do not correct
    attenuation from noisy covariates; use regression_calibration for that.
    ``fixed_variables``: variables declared in advance (a manifest's
    ``replicate_scope: "covariates_only"``) to be held at their estimates in
    every refit, whether or not replicates exist; they are not counted as
    incomplete replicates, and the result records them
    (diagnostics["replicates_declared_fixed"], a note): se_sampling then excludes
    their sampling error.
    ``spatial_clusters``: {"k": integer, "method": "cr1_t" | "im" | "wcr"}.
    Only IM with eight fixed geographic clusters passed Round 26 validation.
    IM/WCR require the population target. Round 30 C1 accepts analysed ACS
    replicates for OLS/binomial/Poisson; independent sampling error enters between-cluster
    spread, without an additive replicate variance. WCR still refuses ACS replicates.
    C2 EIV failed. IM reports a between-cluster mean SE, not an additive model
    SE; WCR reports test-inverted intervals without a scalar SE. CR1 uses t(G-1)
    intervals with the usual target-specific SE. CR1/WCR remain exploratory.
    Round 30 C1 supports unweighted OLS/binomial/Poisson, not EIV/WLS.
    ``cr(x, df=3|4|5)`` uses centered natural splines with full-sample state
    frozen in every refit. Splines and joint Wald inference remain exploratory
    after failing the fixed Round 27 size criterion. Full sampling covariance
    is diagnostics["sampling_covariance"] (NaN if absent). Non-spatial supported
    models also expose explicitly labelled "joint_model_covariance" (HC3) and
    column membership for joint tests. Existing non-spline coefficient SEs keep
    their previous convention; spline coefficient model SEs use HC3.
    """
    from .splines import has_spline, spline_formula
    original_formula = formula
    spline = has_spline(formula)
    if spline and (model.lower() not in ("ols", "wls", "binomial", "poisson") or spatial_se is not None or spatial_clusters is not None):
        raise ValueError("cr splines are supported only by non-spatial fit_replicate OLS/WLS/binomial/Poisson")
    if spline:
        formula = spline_formula(formula)
    if spatial_clusters is not None and (spatial_se is not None or scale == "robust"):
        raise ValueError("spatial_clusters is mutually exclusive with spatial_se and scale='robust'")
    if spatial_se is not None and model.lower() not in ("binomial", "poisson"):
        raise ValueError("spatial_se is supported for binomial and poisson models")
    if spatial_se is not None and coords is None:
        raise ValueError("spatial_se requires coords")
    model = model.lower()
    if scale is not None and (scale not in SCALES or model not in ("binomial", "poisson")):
        raise ValueError(f"scale must be one of {SCALES} for binomial or poisson models only")
    if scale == "robust" and spatial_se is not None:
        raise ValueError("scale='robust' and spatial_se are alternatives; choose one")
    check_replicate_policy(replicate_policy)
    if target not in INTERVAL_TARGETS:
        raise ValueError(f"target must be one of {INTERVAL_TARGETS}")
    if target == "these_areas" and (replicates is None or not len(replicates)):
        raise ValueError("target='these_areas' needs replicates (se_sampling)")
    if model not in MODELS:
        raise ValueError(f"unknown model {model!r}; expected one of {MODELS}")
    cluster_assignment = None
    if spatial_clusters is not None:
        from .spatial_clusters import check_config, assignment_for_frame, supports_im_acs
        check_config(spatial_clusters)
        if model not in ("ols", "binomial") and not supports_im_acs(spatial_clusters,model):
            raise ValueError("spatial_clusters supports OLS and binomial only; EIV/Poisson were not validated")
        if weights is not None:
            raise ValueError("spatial_clusters does not support weighted linear fits (not validated)")
        if spatial_clusters["method"] in ("im", "wcr"):
            if target != "population":
                raise ValueError("IM/WCR spatial clusters require target='population'; ACS SE combination is unavailable")
            analysed = set(formula_variables(formula, frame)) | {v for v in (weights, exposure, trials) if isinstance(v, str)}
            if (replicates is not None and len(replicates) and set(replicates["variable"].astype(str)) & analysed
                    and not supports_im_acs(spatial_clusters,model)):
                raise ValueError("IM/WCR spatial clusters refuse analysed variables with ACS replicates; not validated (docs/audits/im_acs_validation.md)")
        # Fixed geographic input, before any outcome/formula filtering or fit.
        cluster_assignment = assignment_for_frame(frame, coords, spatial_clusters)
    data, n_trials, notes = _prepare(frame, formula, model, weights, exposure, trials)
    fit_scale = "X2" if scale == "X2" else None   # 'robust' changes the covariance, not the fit
    full = _fit(formula, data, model, weights, exposure, n_trials, fit_scale)
    rows = np.asarray(full.model.data.row_labels if full.model.data.row_labels is not None else data.index)
    if len(rows) != len(data):
        notes.append(f"{len(data) - len(rows)} row(s) dropped by the formula (non-finite transforms)")
    params, bse = full.params, full.bse
    # A separate, explicitly labelled HC3 covariance supplies joint inference.
    # Existing non-spline coefficient-SE conventions are preserved.
    joint_cov = None
    if spatial_se is None and spatial_clusters is None and model in ("ols", "wls"):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            joint_cov = np.asarray(full.get_robustcov_results(cov_type="HC3").cov_params(), float)
        if spline:
            bse = pd.Series(np.sqrt(np.diag(joint_cov)), index=params.index)
    used = formula_variables(formula, data)
    diagnostics: Dict[str, Any] = {"reliability_screen": _screen_summary(data, formula, cv_threshold)}
    if model in ("binomial", "poisson"):
        dispersion = float(full.pearson_chi2 / full.df_resid) if full.df_resid > 0 else float("nan")
        diagnostics["pearson_dispersion"] = dispersion
        diagnostics["scale"] = scale
        if dispersion > 1.5 and scale is None and spatial_se is None and spatial_clusters is None:
            notes.append(f"Pearson dispersion {dispersion:.6g}: model SEs assume no overdispersion; use "
                         "scale='robust'")
        elif dispersion > 1.5 and scale == "X2" and spatial_clusters is None:
            notes.append(f"Pearson dispersion {dispersion:.6g} with scale='X2': X2 SEs under-cover when the "
                         "overdispersion is between-area variation (validated coverage 0.69-0.79 at nominal 0.90, "
                         "docs/audits/robust_se_validation.md); prefer scale='robust'")
        if scale == "robust":
            t_rows = np.asarray(n_trials, float)[rows] if model == "binomial" else None
            cov, info = glm_robust_covariance(np.asarray(full.model.exog, float), np.asarray(full.model.endog, float),
                                              np.asarray(full.fittedvalues, float), model, t_rows)
            joint_cov = cov
            diagnostics["se_model_unadjusted"] = dict(zip(params.index, map(float, bse)))
            diagnostics["robust_se"] = info
            bse = pd.Series(np.sqrt(np.diag(cov)), index=params.index)
            notes.append(ROBUST_SE_NOTE)
    if joint_cov is None and model in ("binomial", "poisson") and spatial_se is None and spatial_clusters is None:
        try:
            joint_cov, _ = glm_robust_covariance(np.asarray(full.model.exog,float), np.asarray(full.model.endog,float),
                                                np.asarray(full.fittedvalues,float), model,
                                                np.asarray(n_trials,float)[rows] if model == "binomial" else None)
        except (ValueError, np.linalg.LinAlgError):
            joint_cov = np.full((len(params),len(params)), np.nan)
    if spline:
        bse = pd.Series(np.sqrt(np.diag(joint_cov)), index=params.index)
        notes.append("Centered natural cubic splines; full-sample quantile knots and centering are frozen in every replicate; coefficient model SEs use HC3.")
        from .splines import JOINT_WALD_VALIDATED
        from .joint_tests import VALIDATED as JOINT_TEST_VALIDATED
        if (model, "spline") in JOINT_TEST_VALIDATED:
            notes.append("Splines: test the spline variable jointly with census.joint_tests.joint_test (manifest statistic "
                         "joint_test; Round 31 validated for binomial/Poisson). Individual spline coefficients and the "
                         "chi-squared joint_wald remain exploratory.")
        elif not JOINT_WALD_VALIDATED:
            notes.append("EXPLORATORY ONLY: splines/joint Wald did not pass Round 27 validation.")
    provenance: Dict[str, Any] = {"model_library": "statsmodels", "rows_used": int(len(rows))}
    se_sampling = pd.Series(np.nan, index=params.index)
    sampling_cov = np.full((len(params),len(params)), np.nan)
    sources = [SOURCE_MODEL]
    method = "full_sample_fit"

    if replicates is not None and len(replicates):
        declared = [v for v in used if v in set(fixed_variables)]
        if declared and target == "these_areas":
            raise ValueError("fixed_variables cannot be combined with target='these_areas': its interval would "
                             f"use a sampling SE without the sampling error of {declared}")
        mats, fixed = _replicate_matrices(data, replicates, [v for v in used if v not in declared])
        if not mats:
            raise ValueError("no formula variable has replicates in the replicate frame")
        missing = [v for v in used if v not in mats and v not in declared]
        stoch_missing = stochastic_variables(frame, missing)
        precheck_replicates(replicate_policy, rows_held_fixed=fixed, variables_without_replicates=stoch_missing,
                            context="fit_replicate")
        coefs, failed = [], 0
        for r in range(REPLICATE_COUNT):
            d = data.copy()
            for v, m in mats.items():
                d[v] = m[:, r]
            try:
                if spline:
                    from .splines import frozen_refit
                    b = frozen_refit(full, d, model, weights, exposure, n_trials, fit_scale).to_numpy(float)
                else:
                    res = _fit(formula, d, model, weights, exposure, n_trials, fit_scale)
                    b = res.params.reindex(params.index).to_numpy(float)
                if not np.isfinite(b).all():
                    raise ValueError("non-finite coefficients")
                coefs.append(b)
            except Exception:  # noqa: BLE001 - any refit failure is counted and reported
                failed += 1
        replicate_completeness(replicate_policy, failed_refits=failed, rows_held_fixed=fixed,
                               variables_without_replicates=stoch_missing,
                               context="fit_replicate", diagnostics=diagnostics, notes=notes)
        check_refit_count(failed, len(coefs), max_failed_replicates, "fit_replicate")
        B = np.vstack(coefs)  # (n_ok, k)
        b0 = params.to_numpy(float)
        sampling_cov = REPLICATE_FACTOR * (B-b0).T @ (B-b0)
        se_sampling = pd.Series(np.sqrt(REPLICATE_FACTOR * ((B - b0) ** 2).sum(axis=0)), index=params.index)
        sources.append(SOURCE_SAMPLING_REPLICATE)
        method = "replicate_refit"
        fixed_vars = [v for v in missing if v not in stoch_missing]
        if fixed_vars:   # no SE column: genuinely fixed (stochastic ones are in REPLICATES INCOMPLETE)
            notes.append(f"variables without replicates or SEs treated as fixed: {fixed_vars}")
        diagnostics["replicate_stability"] = {
            t: {"sd": float(B[:, j].std(ddof=1)) if len(B) > 1 else np.nan,
                "share_same_sign": float(np.mean(np.sign(B[:, j]) == np.sign(b0[j])))}
            for j, t in enumerate(params.index)
        }
        diagnostics["replicate_failures"] = failed
        rel = covariate_reliability(formula, data, mats)
        if rel["covariates"]:
            diagnostics["covariate_reliability"] = rel
            if rel["low"] or rel["uneven"]:
                notes.append("COVARIATE MEASUREMENT ERROR: "
                             + (f"reliability below {RELIABILITY_NOTE_THRESHOLD} for {rel['low']}" if rel["low"] else "")
                             + ("; " if rel["low"] and rel["uneven"] else "")
                             + (f"reliability differs by more than {RELIABILITY_GROUP_SPREAD} between groups of "
                                f"{rel['uneven']}" if rel["uneven"] else "")
                             + ". Replicate refits widen intervals for this noise but do not remove the bias it "
                             "causes (attenuation, uneven across groups); "
                             + ("use fit_eiv (census.models.fit_eiv, fit_model method='eiv') for the corrected "
                                "coefficients" if model in EIV_MODELS else
                                f"fit_eiv supports ols/wls only; for this {model} model, regression_calibration "
                                "corrects the attenuation approximately (not the outcome-covariate error "
                                "correlation)"))
        provenance["replicate_variables"] = sorted(mats)
        if declared:
            diagnostics["replicates_declared_fixed"] = declared
            notes.append(f"DECLARED COVARIATE-ONLY REPLICATES: {declared} held at their estimates in every refit "
                         "as pre-declared; se_sampling covers the sampling error of "
                         f"{sorted(mats)} only, not of {declared}")
        notes.append("se_total = sqrt(se_model^2 + se_sampling^2) is reported but conservative (validated "
                     "coverage 0.961 at nominal 0.90): the model residual already absorbs outcome sampling error")
    else:
        notes.append("no replicates: SEs reflect model error only, not ACS sampling error of inputs; use "
                     "replicates, regression_calibration/simex for noisy covariates, or " + FH_POINTER)

    if spatial_se is not None:
        from .spatial_hac import conley_covariance, coordinate_distances
        X = np.asarray(full.model.exog, float)
        mu = np.asarray(full.fittedvalues, float)
        y = np.asarray(full.model.endog, float)
        t = np.asarray(n_trials, float)[rows] if model == "binomial" else np.ones(len(mu))
        scores = X * (t * (y - mu))[:, None]
        weights_h = t * mu * (1 - mu) if model == "binomial" else mu
        bread = np.linalg.inv(X.T @ (weights_h[:, None] * X))
        cov, info = conley_covariance(scores, bread, coordinate_distances(data.loc[rows], coords), spatial_se["cutoff_km"])
        diagnostics["se_model_unadjusted"] = dict(zip(params.index, map(float, bse)))
        diagnostics["spatial_se"] = info
        bse = pd.Series(np.sqrt(np.diag(cov)), index=params.index)
        notes.append(f"Spatial HAC (Conley) SEs, Bartlett kernel, cutoff {spatial_se['cutoff_km']} km")
    if spatial_clusters is not None:
        from .spatial_clusters import inference_table
        table, cluster_info = inference_table(full, data, n_trials, model, spatial_clusters,
                                               cluster_assignment, target, confidence_level, se_sampling)
        diagnostics["spatial_clusters"] = cluster_info
        diagnostics["se_model_unadjusted"] = dict(zip(params.index, map(float, bse)))
        method = "spatial_cluster_"+spatial_clusters["method"]
        if spatial_clusters["method"] == "im" and cluster_info.get("validation_audit"):
            notes.append("IM targets the coefficient on the ACS estimates as observed; attenuated toward 0 if covariates have sampling error, and not corrected. With noisy controls the bias need not be toward 0; true-slope inference is not validated.")
            notes.append("Independent ACS error enters between-cluster spread; ACS replicates are not added to se_cluster_mean. Population target only; docs/audits/im_acs_validation.md.")
            if cluster_info['not_estimable_terms']:
                notes.append(f"Within-cluster constant nuisance terms absorbed by cluster intercepts, not estimable under IM: {cluster_info['not_estimable_terms']}")
        elif spatial_clusters["method"] in ("im", "wcr"):
            notes.append("ACS sampling error is not included. IM's cluster-mean SE / WCR test cannot be combined with ACS replicates.")
        if spatial_clusters["method"] == "im":
            notes.append("IM estimates are unweighted means of separately fitted cluster coefficients; se_cluster_mean is their one-sample SE, not an additive full-sample model SE.")
            cluster_info["residual_diagnostics_basis"] = "full-sample reference fit, not the cluster-mean estimator"
        if not cluster_info["validated"]:
            notes.append("EXPLORATORY ONLY: this spatial-cluster method/count did not pass Round 26 validation.")
        notes.append(f"Spatial clusters: {spatial_clusters['method']}, G={spatial_clusters['k']}; see docs/audits/spatial_cluster_validation.md")
    else:
        table = _table(params, bse, se_sampling, confidence_level, target)
    if spatial_clusters is not None and spatial_clusters["method"] in ("im", "wcr"):
        inference_basis = "se_cluster_mean with t(G-1)" if spatial_clusters["method"] == "im" else "restricted bootstrap test inversion"
        notes.append(f"intervals and p-values use the population target ({inference_basis}); no additive ACS SE")
    else:
        notes.append(f"intervals and p-values use the '{target}' target ({TARGET_SE[target]})")
    diagnostics["interval_target"] = target
    diagnostics.update(_numeric_diagnostics(formula, data, full, model, table, weights, exposure,
                                            n_trials, cv_threshold))
    diagnostics["sampling_covariance"] = pd.DataFrame(sampling_cov, index=pd.Index(params.index,name="term"), columns=params.index)
    if joint_cov is not None:
        from .splines import variable_columns
        diagnostics["joint_model_covariance"] = pd.DataFrame(joint_cov, index=pd.Index(params.index,name="term"), columns=params.index)
        diagnostics["joint_model_covariance_estimator"] = "HC3"
        diagnostics["joint_has_replicates"] = method == "replicate_refit"
        diagnostics["joint_full_rank"] = np.linalg.matrix_rank(full.model.exog) == len(params)
        diagnostics["joint_columns"] = {v: variable_columns(full.model.data.orig_exog.design_info,v,data.columns) for v in used}
    result = ModelResult(model_type=model, formula=original_formula, n_obs=int(full.nobs), coefficients=table,
                         method=method, uncertainty_sources=sources, confidence_level=confidence_level,
                         notes=notes, diagnostics=diagnostics, provenance=provenance)
    # Inputs for census.joint_tests (Round 31), kept off the serialized result.
    design_info = full.model.data.orig_exog.design_info
    expo = getattr(full.model, "exposure", None)
    result.joint_inputs = dict(
        X=np.asarray(full.model.exog, float), y=np.asarray(full.model.endog, float),
        trials=np.asarray(n_trials, float)[rows] if model == "binomial" else None,
        exposure=None if expo is None else np.exp(np.asarray(expo, float)),
        column_names=list(params.index), target=target, has_replicates=method == "replicate_refit",
        sampling_covariance=np.nan_to_num(np.asarray(sampling_cov, float)),
        full_rank=bool(np.linalg.matrix_rank(full.model.exog) == len(params)),
        geoids=(data.loc[rows, "GEOID"].astype(str).tolist() if "GEOID" in data.columns else None),
        term_columns={t.name(): list(design_info.column_names[design_info.term_name_slices[t.name()]])
                      for t in design_info.terms})
    return result


def _numeric_diagnostics(formula, data, full, model, table, weights, exposure, n_trials, threshold) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    y = _outcome(formula)
    rows = full.model.data.row_labels
    used = data.loc[rows] if rows is not None else data
    if model in ("ols", "wls") and f"{y}_se" in used.columns:
        s2 = np.nanmean(used[f"{y}_se"].to_numpy(float) ** 2)
        r2 = float(np.mean(np.asarray(full.resid) ** 2))
        out["sampling_share_of_residual_variance"] = float(s2 / r2) if r2 > 0 else np.nan
    cv_cols = [f"{v}_cv" for v in formula_variables(formula, data) if f"{v}_cv" in data.columns]
    if cv_cols:
        high = (data[cv_cols].to_numpy(float) > threshold).any(axis=1)
        k = len(table)
        info: Dict[str, Any] = {"n_high_cv_rows": int(high.sum())}
        if 0 < high.sum() and (~high).sum() > k + 1:
            try:
                from .splines import has_spline, frozen_refit
                subset = data.loc[~high].reset_index(drop=True)
                trials_subset = None if n_trials is None else n_trials[~high]
                if has_spline(formula):
                    b = frozen_refit(full, subset, model, weights, exposure, trials_subset).reindex(table["term"]).to_numpy(float)
                else:
                    res = _fit(formula, subset, model, weights, exposure, trials_subset)
                    b = res.params.reindex(table["term"]).to_numpy(float)
                shift = (b - table["estimate"].to_numpy(float)) / table["se_total"].to_numpy(float)
                info["coef_shift_in_se_total_without_high_cv"] = dict(zip(table["term"], shift.tolist()))
            except Exception as exc:  # noqa: BLE001
                info["error"] = str(exc)
        out["high_cv_influence"] = info
    return out


# ---------------------------------------------------------------------------
# B2. measurement-error corrections for covariates
# ---------------------------------------------------------------------------


def _error_spec(frame: pd.DataFrame, error_covariates: Union[Sequence[str], Mapping[str, str]]) -> Dict[str, str]:
    spec = dict(error_covariates) if isinstance(error_covariates, Mapping) else {
        v: f"{v}_se" for v in error_covariates}
    for v, s in spec.items():
        if v not in frame.columns or s not in frame.columns:
            raise KeyError(f"error covariate {v!r} needs columns {v!r} and {s!r}")
    if not spec:
        raise ValueError("error_covariates is empty")
    return spec


def _calibrate(data: pd.DataFrame, spec: Dict[str, str], others: List[str]) -> pd.DataFrame:
    """Replace each W by E[X | W, Z] (Carroll et al. 2006, eq. 4.4, heteroscedastic Sigma_uu,i)."""
    ws = list(spec)
    obs = data[ws + others].to_numpy(float)  # (n, k+m)
    s2 = data[[spec[w] for w in ws]].to_numpy(float) ** 2  # (n, k)
    mu = obs.mean(axis=0)
    cov = np.atleast_2d(np.cov(obs, rowvar=False))
    k = len(ws)
    sig = cov.copy()
    sig[np.arange(k), np.arange(k)] -= s2.mean(axis=0)  # Sigma_xx = Sigma_ww - mean Sigma_uu
    floor = 1e-6 * np.maximum(cov[np.arange(k), np.arange(k)], 1e-12)
    sig[np.arange(k), np.arange(k)] = np.maximum(sig[np.arange(k), np.arange(k)], floor)
    C = sig[:k, :]  # Cov(X, (W, Z))
    out = data.copy()
    centered = obs - mu
    xhat = np.empty((len(data), k))
    for i in range(len(data)):
        S = sig.copy()
        S[np.arange(k), np.arange(k)] += s2[i]
        xhat[i] = mu[:k] + C @ np.linalg.solve(S, centered[i])
    for j, w in enumerate(ws):
        out[w] = xhat[:, j]
    return out


def _corrected_result(formula, model, naive, est, se_total, confidence_level, method, notes, diagnostics, n) -> ModelResult:
    se_model = naive.bse.reindex(est.index)
    se_samp = pd.Series(np.sqrt(np.maximum(se_total.to_numpy(float) ** 2 - se_model.to_numpy(float) ** 2, 0.0)),
                        index=est.index)
    table = _table(est, se_model, se_samp, confidence_level)
    # keep the reported total exactly (it is not reconstructed from components)
    z = _z(confidence_level)
    table["se_total"] = se_total.to_numpy(float)
    table["ci_lower"] = table["estimate"] - z * table["se_total"]
    table["ci_upper"] = table["estimate"] + z * table["se_total"]
    with np.errstate(divide="ignore", invalid="ignore"):
        table["p_value"] = 2 * sps.norm.sf(np.abs(table["estimate"] / table["se_total"]))
    table["naive_estimate"] = naive.params.reindex(est.index).to_numpy(float)
    table["naive_se"] = se_model.to_numpy(float)
    diagnostics["naive"] = pd.DataFrame({"term": list(naive.params.index), "estimate": naive.params.to_numpy(float),
                                         "se_model": naive.bse.to_numpy(float)})
    notes = notes + ["se_model is the naive-fit model SE; se_sampling = sqrt(max(se_total^2 - se_model^2, 0)); "
                     "naive_estimate shows the uncorrected (attenuated) coefficients"]
    return ModelResult(model_type=model, formula=formula, n_obs=n, coefficients=table, method=method,
                       uncertainty_sources=[SOURCE_MODEL, SOURCE_SAMPLING_MODEL],
                       confidence_level=confidence_level, notes=notes, diagnostics=diagnostics)


def _setup(formula, frame, error_covariates, model, weights, exposure, trials):
    from .splines import has_spline
    if has_spline(formula):
        raise ValueError("cr splines are supported only by non-spatial fit_replicate")
    model = model.lower()
    if model not in MODELS:
        raise ValueError(f"unknown model {model!r}; expected one of {MODELS}")
    spec = _error_spec(frame, error_covariates)
    data, n_trials, notes = _prepare(frame, formula, model, weights, exposure, trials)
    keep = np.isfinite(data[list(spec.values())].to_numpy(float)).all(axis=1)
    data = data.loc[keep].reset_index(drop=True)
    if n_trials is not None:
        n_trials = n_trials[keep]
    y = _outcome(formula)
    others = [v for v in formula_variables(formula, data)
              if v not in spec and v != y and v not in (weights, exposure)
              and pd.api.types.is_numeric_dtype(data[v])]
    return model, spec, data, n_trials, notes, others


def regression_calibration(
    formula: str,
    frame: pd.DataFrame,
    error_covariates: Union[Sequence[str], Mapping[str, str]],
    model: str = "ols",
    weights: Optional[str] = None,
    exposure: Optional[str] = None,
    trials: Optional[str] = None,
    confidence_level: float = 0.90,
    n_boot: int = 200,
    seed: Optional[int] = 0,
    cv_threshold: float = DEFAULT_CV_THRESHOLD,
) -> ModelResult:
    """Regression calibration for covariates with known sampling SEs.

    ``error_covariates``: names (SE column ``<name>_se``) or ``{name: se_column}``.
    Each W is replaced by E[X | W, Z] = mu + Cov(X,(W,Z)) Var_i(W,Z)^{-1} ((W,Z) - mu),
    where Var_i adds row i's known error variance s_i^2 to the W block and
    Var(X) = Var(W) - mean(s^2) (method of moments). Other numeric formula
    variables are the error-free Z. Source: Carroll, Ruppert, Stefanski &
    Crainiceanu (2006), "Measurement Error in Nonlinear Models", 2nd ed., ch. 4.
    Exact for linear models; an approximation for GLMs (ch. 4.8). SEs from
    ``n_boot`` row-bootstrap replicates that re-estimate the calibration.
    """
    model, spec, data, n_trials, notes, others = _setup(formula, frame, error_covariates, model, weights, exposure, trials)
    naive = _fit(formula, data, model, weights, exposure, n_trials)
    cal = _fit(formula, _calibrate(data, spec, others), model, weights, exposure, n_trials)
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(data), len(data))
        d = data.iloc[idx].reset_index(drop=True)
        try:
            res = _fit(formula, _calibrate(d, spec, others), model, weights, exposure,
                       None if n_trials is None else n_trials[idx])
            boots.append(res.params.reindex(cal.params.index).to_numpy(float))
        except Exception:  # noqa: BLE001
            continue
    B = np.vstack(boots)
    se_total = pd.Series(B.std(axis=0, ddof=1), index=cal.params.index)
    diagnostics = {"reliability_screen": _screen_summary(data, formula, cv_threshold),
                   "bootstrap_replicates": len(boots),
                   "reliability_ratio": {w: float(1 - np.mean(data[s] ** 2) / np.var(data[w], ddof=1))
                                         for w, s in spec.items()}}
    notes = notes + [f"regression calibration of {list(spec)} given {others}; se_total from {len(boots)} "
                     "row-bootstrap refits including calibration", FH_POINTER]
    return _corrected_result(formula, model, naive, cal.params, se_total, confidence_level,
                             "regression_calibration", notes, diagnostics, int(cal.nobs))


# ---------------------------------------------------------------------------
# B2b. fit_eiv: moment-corrected least squares with replicate error covariances
# ---------------------------------------------------------------------------

EIV_MODELS = ("ols", "wls")
EIV_LOW_RELIABILITY = 0.5


def _design_deviations(formula: str, data: pd.DataFrame, mats: Mapping[str, np.ndarray]):
    """Design matrices of the estimates and the per-replicate deviations of every design column.

    Returns (y (n,), X (n, k) DataFrame, D (R, n, k), e (R, n), kept row positions). Replicate
    design rows reuse the estimates' patsy design information, so factor coding is identical and
    error-free columns (constant, factors) have zero deviation."""
    import patsy
    y_df, X_df = patsy.dmatrices(formula, data, return_type="dataframe", NA_action="drop")
    rows = np.asarray(X_df.index)
    cols = list(dict.fromkeys([c for c in ("GEOID", "Year") if c in data.columns] + formula_variables(formula, data)))
    sub = data.loc[rows, cols].reset_index(drop=True)
    keep_nan = patsy.NAAction(NA_types=[])  # undefined replicate values stay NaN (handled by the caller)
    y = y_df.iloc[:, 0].to_numpy(float)
    X = X_df.to_numpy(float)
    R = REPLICATE_COUNT
    D = np.zeros((R, len(sub), X.shape[1]))
    e = np.zeros((R, len(sub)))
    pos = data.index.get_indexer(rows)
    for r in range(R):
        d = sub.copy()
        for v, m in mats.items():
            d[v] = m[pos, r]
        Xr = np.asarray(patsy.build_design_matrices([X_df.design_info], d, NA_action=keep_nan)[0], float)
        yr = np.asarray(patsy.build_design_matrices([y_df.design_info], d, NA_action=keep_nan)[0], float)[:, 0]
        D[r] = Xr - X
        e[r] = yr - y
    return y, X_df, D, e, rows


CLUSTER_PREFIX_RE = re.compile(r"^GEOID\.str\[:(\d+)\]$")


def _cluster_jackknife(X: np.ndarray, y: np.ndarray, w: np.ndarray, D: np.ndarray, e: np.ndarray,
                       inv: np.ndarray, G: int, f: float) -> np.ndarray:
    """Delete-one-cluster jackknife covariance of the fit_eiv moment estimator (CR3)."""
    k = X.shape[1]
    M_g = np.zeros((G, k, k))
    XX_g = np.zeros((G, k, k))
    r_g = np.zeros((G, k))
    for g in range(G):
        idx = np.flatnonzero(inv == g)
        Xg, wg = X[idx], w[idx]
        Dg, eg = D[:, idx], e[:, idx]
        XX_g[g] = Xg.T @ (wg[:, None] * Xg)
        M_g[g] = XX_g[g] - f * np.einsum("rnj,n,rnl->jl", Dg, wg, Dg)
        r_g[g] = Xg.T @ (wg * y[idx]) - f * np.einsum("rnj,n,rn->j", Dg, wg, eg)
    M, r, XX = M_g.sum(axis=0), r_g.sum(axis=0), XX_g.sum(axis=0)
    present = np.zeros((G, k))
    np.add.at(present, inv, (X != 0).astype(float))
    total_nz = present.sum(axis=0)
    const = np.all(X == 1, axis=0)
    indicator = np.all((X == 0) | (X == 1), axis=0) & ~const

    def full_rank(cols: np.ndarray, g: int) -> bool:
        A = (XX - XX_g[g])[np.ix_(cols, cols)]
        d = np.sqrt(np.clip(np.diag(A), 1e-300, None))
        return float(np.linalg.eigvalsh(A / np.outer(d, d))[0]) > 1e-10

    B = np.full((G, k), np.nan)
    for g in range(G):
        keep = (total_nz - present[g]) > 0
        report = keep.copy()
        if not full_rank(np.flatnonzero(keep), g) and const.any():
            # deleting the reference cluster of cluster fixed effects leaves the intercept collinear with the
            # remaining dummies: drop the intercept; the dummies then measure levels, not contrasts, so neither
            # they nor the intercept enter this refit's jackknife (the other terms are unaffected)
            keep &= ~const
            report = keep & ~indicator
        if not full_rank(np.flatnonzero(keep), g):
            continue  # not identified without this cluster: the refit is left out
        Mk = (M - M_g[g])[np.ix_(keep, keep)]
        try:
            sol = np.linalg.solve(Mk, (r - r_g[g])[keep])
        except np.linalg.LinAlgError:
            continue
        row = np.full(k, np.nan)
        row[keep] = sol
        B[g, report] = row[report]
    ok = np.isfinite(B)
    if not ok.any(axis=0).all():
        raise ValueError("fit_eiv jackknife: some term is not estimable in any delete-one-cluster refit")
    mean = np.nanmean(B, axis=0)
    dev = np.where(ok, B - mean, 0.0)
    cnt = ok.sum(axis=0).astype(float)
    V = dev.T @ dev
    scale = np.sqrt((cnt - 1) / cnt)
    return V * np.outer(scale, scale)


def cluster_labels(data: pd.DataFrame, cluster: str) -> np.ndarray:
    """Cluster labels from a column, or from a GEOID prefix written ``GEOID.str[:N]``."""
    m = CLUSTER_PREFIX_RE.match(str(cluster))
    if m:
        return data["GEOID"].astype(str).str[: int(m.group(1))].to_numpy()
    if cluster not in data.columns:
        raise ValueError(f"cluster {cluster!r} is neither a frame column nor GEOID.str[:N]")
    return data[cluster].astype(str).to_numpy()


def fit_eiv(
    formula: str,
    frame: pd.DataFrame,
    replicates: Optional[pd.DataFrame] = None,
    model: str = "ols",
    weights: Optional[str] = None,
    confidence_level: float = 0.90,
    cv_threshold: float = DEFAULT_CV_THRESHOLD,
    replicate_policy: str = "flag",
    cluster: Optional[str] = None,
    fixed_variables: Sequence[str] = (),
    cluster_se: str = "cr1",
    spatial_se: Optional[Mapping] = None,
    coords: Optional[pd.DataFrame] = None,
    spatial_clusters: Optional[Mapping] = None,
) -> ModelResult:
    """Least squares corrected for ACS sampling error in covariates and outcome (PLAN_ROUND_20 A2).

    With x_i the design row of unit i from the estimates, x_i^(r) the same row from replicate r
    and y likewise, the per-unit error covariances are estimated from the replicates (the VRE
    successive-difference formula):

        S_i = 4/80 sum_r (x_i^(r) - x_i)(x_i^(r) - x_i)',   s_i = 4/80 sum_r (x_i^(r) - x_i)(y_i^(r) - y_i)

    and the coefficients are Fuller's moment estimator with known heteroscedastic error
    covariance (Fuller 1987, Measurement Error Models, sections 2.2 and 3.1):

        b = (sum w_i x_i x_i' - sum w_i S_i)^-1 (sum w_i x_i y_i - sum w_i s_i).

    Unlike regression_calibration, it removes the bias from the correlation between the
    outcome's and the covariates' sampling errors (s_i), which arises when both are estimated
    from the same ACS sample, and it handles transformed and interaction columns (their error
    comes from their own replicate design rows). Error-free columns (constant, factors) have
    S_i = 0.

    Variance: sandwich M^-1 (sum psi_i psi_i') M^-1 * n/(n-k), psi_i = w_i [x_i (y_i - x_i'b) -
    (s_i - S_i b)], M = sum w_i x_i x_i' - sum w_i S_i, units independent (tract sampling errors
    are nearly uncorrelated between neighbours, Round 16). It covers model and sampling error:
    reported as se_total, the basis of intervals and p-values; se_model is the naive fit's
    model SE and the naive (uncorrected) coefficients are reported alongside.

    ``model``: "ols", or "wls" with an error-free ``weights`` column. Needs ``replicates`` (the
    long frame of census.analysis.attach_replicates) for every stochastic formula variable;
    ``replicate_policy`` as in fit_replicate ("strict" refuses rows or variables without them).
    Refuses a fit whose corrected moment matrix is not positive definite; notes covariates whose
    reliability is below 0.5, where moment corrections become unstable.

    ``cluster``: a column naming groups (e.g. county) whose units may be correlated (spatially
    autocorrelated model errors); the sandwich then sums psi within clusters, with the
    G/(G-1) * (n-1)/(n-k) small-sample factor. Needs at least 20 clusters. ``GEOID.str[:N]``
    (e.g. ``GEOID.str[:5]``, counties of tracts) clusters by a GEOID prefix without a column.
    Validated by simulation in docs/audits/eiv_cluster_validation.md (PLAN_ROUND_21 B1).
    ``cluster_se="jackknife"`` uses the delete-one-cluster jackknife (CR3) instead:
    V = (G-1)/G sum_g (b_(g) - mean b_(g))(...)', each b_(g) the moment estimator from the
    other clusters' sums (exact; the error covariances are not re-estimated). A term whose
    column is all zero without cluster g (that cluster's own fixed effect) is left out of
    that refit, and its variance uses the other refits. Less anti-conservative than CR1 with
    few or unequal clusters (PLAN_ROUND_21 Part 2, C5).

    ``fixed_variables``: variables whose error is independent of the ACS sampling error and
    which have no replicates (external outcomes, e.g. CDC PLACES; PLAN_ROUND_21 B3). They are
    held at their estimates in every replicate design row (zero deviation, so s_i has no term
    from them) and are not counted as missing replicates; as an outcome their error enters the
    residual, which the sandwich covers. Only the outcome may be fixed: a fixed covariate's
    error would go uncorrected.
    """
    if spatial_clusters is not None:
        from .spatial_clusters import check_config
        check_config(spatial_clusters)
        if (spatial_clusters != {'k':8,'method':'im'} or model.lower()!='ols' or weights is not None
                or cluster is not None or spatial_se is not None or cluster_se != 'cr1'):
            raise ValueError("IM EIV requires unweighted OLS, k=8/method=im, and refuses cluster, cluster_se and spatial_se")
        raise ValueError("IM EIV C2 failed validation and is refused; docs/audits/im_acs_validation.md")
    from .splines import has_spline
    if has_spline(formula):
        raise ValueError("cr splines are supported only by non-spatial fit_replicate")
    import scipy.linalg as sla

    if spatial_se is not None and cluster:
        raise ValueError("spatial_se and cluster are mutually exclusive")
    if spatial_se is not None and coords is None:
        raise ValueError("spatial_se requires coords")
    model = model.lower()
    check_replicate_policy(replicate_policy)
    if cluster_se not in ("cr1", "jackknife"):
        raise ValueError("cluster_se must be 'cr1' or 'jackknife'")
    if cluster_se == "jackknife" and not cluster:
        raise ValueError("cluster_se='jackknife' needs cluster")
    if model not in EIV_MODELS:
        raise ValueError(f"fit_eiv supports models {EIV_MODELS}; got {model!r}")
    if model == "wls" and not weights:
        raise ValueError("model='wls' needs weights=<column>")
    if replicates is None or not len(replicates):
        raise ValueError("fit_eiv needs replicates (the error covariances come from them)")
    data, _, notes = _prepare(frame, formula, model, weights if model == "wls" else None, None, None)
    used = formula_variables(formula, data)
    if weights and model == "wls":
        if weights in set(replicates["variable"].astype(str)) or weights in used:
            raise ValueError(f"weights column {weights!r} must be error-free (not a replicated or formula variable)")
    declared = [v for v in used if v in set(fixed_variables)]
    if declared:
        outcome_vars = set(formula_variables(formula.split("~")[0] + "~ 1", data))
        bad_fixed = [v for v in declared if v not in outcome_vars]
        if bad_fixed:
            raise ValueError(f"fixed_variables {bad_fixed} are covariates; only the outcome may be held fixed (a "
                             "covariate's error would go uncorrected)")
    mats, fixed = _replicate_matrices(data, replicates, [v for v in used if v not in declared])
    if not mats:
        raise ValueError("no formula variable has replicates in the replicate frame")
    missing = [v for v in used if v not in mats and v not in declared]
    stoch_missing = stochastic_variables(frame, missing)
    precheck_replicates(replicate_policy, rows_held_fixed=fixed, variables_without_replicates=stoch_missing,
                        context="fit_eiv")
    diagnostics: Dict[str, Any] = {"reliability_screen": _screen_summary(data, formula, cv_threshold)}
    replicate_completeness(replicate_policy, rows_held_fixed=fixed, variables_without_replicates=stoch_missing,
                           context="fit_eiv", diagnostics=diagnostics, notes=notes)

    y, X_df, D, e, rows = _design_deviations(formula, data, mats)
    used_data = data.loc[rows].reset_index(drop=True)
    with np.errstate(invalid="ignore"):
        bad = ~(np.isfinite(D).all(axis=(0, 2)) & np.isfinite(e).all(axis=0))
    if bad.any():
        # a transform undefined on some replicate (e.g. log of a replicate 0): those units' error
        # covariance is undefined; strict refuses, flag drops them and records it
        replicate_completeness(replicate_policy, rows_held_fixed={"undefined transformed replicate": int(bad.sum())},
                               context="fit_eiv", diagnostics=diagnostics, notes=notes,
                               rows_label="units dropped (a formula term is undefined on some replicate)")
        keep = ~bad
        y, D, e = y[keep], D[:, keep], e[:, keep]
        X_df = X_df.iloc[np.flatnonzero(keep)]
        used_data = used_data.loc[keep].reset_index(drop=True)
    n, k = X_df.shape
    if n <= k:
        raise ValueError(f"fit_eiv: {n} rows for {k} coefficients")
    w = used_data[weights].to_numpy(float) if model == "wls" else np.ones(n)
    if not (np.isfinite(w).all() and (w >= 0).all()):
        raise ValueError("weights must be non-negative and finite")
    if (w == 0).any():  # zero weight = the unit does not enter the weighted fit (as in WLS)
        keep = w > 0
        notes.append(f"{int((~keep).sum())} unit(s) with weight 0 left out of the weighted fit")
        y, D, e, w = y[keep], D[:, keep], e[:, keep], w[keep]
        X_df = X_df.iloc[np.flatnonzero(keep)]
        used_data = used_data.loc[keep].reset_index(drop=True)
        n = len(y)
        if n <= k:
            raise ValueError(f"fit_eiv: {n} rows with positive weight for {k} coefficients")
    X = X_df.to_numpy(float)
    terms = list(X_df.columns)
    f = REPLICATE_FACTOR
    S_sum = f * np.einsum("rnj,n,rnl->jl", D, w, D)        # sum_i w_i S_i
    s_sum = f * np.einsum("rnj,n,rn->j", D, w, e)          # sum_i w_i s_i
    XtWX = X.T @ (w[:, None] * X)
    M = XtWX - S_sum
    try:
        rel_eig = float(sla.eigh(M, XtWX, eigvals_only=True)[0])
    except (np.linalg.LinAlgError, ValueError) as exc:
        raise ValueError(f"fit_eiv: design matrix is singular ({exc})") from exc
    if not rel_eig > 0:
        raise ValueError("fit_eiv: the corrected moment matrix X'WX - sum S_i is not positive definite "
                         f"(smallest relative eigenvalue {rel_eig:.3g}): the covariates' sampling error is as large as "
                         "their spread; the correction is not identified for this model")
    b = np.linalg.solve(M, X.T @ (w * y) - s_sum)
    resid = y - X @ b
    s_i = f * np.einsum("rnj,rn->nj", D, e)                 # (n, k)
    Sb_i = f * np.einsum("rnj,rn->nj", D, D @ b)            # (n, k): S_i b
    psi = w[:, None] * (X * resid[:, None] - (s_i - Sb_i))
    Minv = np.linalg.inv(M)
    if cluster:
        groups = cluster_labels(used_data, cluster)
        codes, inv = np.unique(groups, return_inverse=True)
        G = len(codes)
        if G < 20:
            raise ValueError(f"cluster {cluster!r} has {G} groups; the clustered sandwich needs at least 20")
        psi_g = np.zeros((G, k))
        np.add.at(psi_g, inv, psi)
        V = Minv @ (psi_g.T @ psi_g) @ Minv * (G / (G - 1)) * ((n - 1) / (n - k))
        V_ind = Minv @ (psi.T @ psi) @ Minv * n / (n - k)
        diagnostics["clusters"] = {"column": cluster, "groups": int(G), "se": cluster_se}
        if cluster_se == "jackknife":
            diagnostics["se_total_cr1"] = dict(zip(map(str, X_df.columns),
                                                   map(float, np.sqrt(np.maximum(np.diag(V), 0.0)))))
            V = _cluster_jackknife(X, y, w, D, e, inv, G, f)
        diagnostics["se_total_independent"] = dict(zip(map(str, X_df.columns),
                                                       map(float, np.sqrt(np.maximum(np.diag(V_ind), 0.0)))))
        notes.append(f"se_total clustered by {cluster!r} ({G} clusters, "
                     + ("delete-one-cluster jackknife" if cluster_se == "jackknife" else "CR1") + ")")
    else:
        V = Minv @ (psi.T @ psi) @ Minv * n / (n - k)
    if spatial_se is not None:
        from .spatial_hac import conley_covariance, coordinate_distances
        diagnostics["se_independent"] = dict(zip(terms, map(float, np.sqrt(np.diag(V)))))
        V, info = conley_covariance(psi, Minv, coordinate_distances(used_data, coords), spatial_se["cutoff_km"])
        diagnostics["spatial_se"] = info
        notes.append(f"Spatial HAC (Conley) SEs, Bartlett kernel, cutoff {spatial_se['cutoff_km']} km")
    se_total = pd.Series(np.sqrt(np.maximum(np.diag(V), 0.0)), index=terms)

    naive = _fit(formula, used_data, model, weights if model == "wls" else None, None, None)
    noisy = [j for j in range(k) if np.any(D[:, :, j] != 0)]
    clean = [j for j in range(k) if j not in noisy]
    reliability: Dict[str, float] = {}
    for j in noisy:
        xj = X[:, j]
        if clean:
            Z = X[:, clean]
            coef, *_ = np.linalg.lstsq(Z * np.sqrt(w)[:, None], xj * np.sqrt(w), rcond=None)
            xj = xj - Z @ coef
        var_obs = float(np.sum(w * xj**2) / np.sum(w))
        err = float(f * np.einsum("rn,n,rn->", D[:, :, j], w, D[:, :, j]) / np.sum(w))
        reliability[terms[j]] = 1.0 - err / var_obs if var_obs > 0 else float("nan")
    err_corr: Dict[str, float] = {}
    var_y = f * np.einsum("rn,rn->n", e, e)
    for j in noisy:
        var_x = f * np.einsum("rn,rn->n", D[:, :, j], D[:, :, j])
        den = np.sqrt(np.mean(var_x) * np.mean(var_y))
        err_corr[terms[j]] = float(np.mean(s_i[:, j]) / den) if den > 0 else float("nan")
    diagnostics.update({
        "reliability": reliability,
        "outcome_error_correlation": err_corr,
        "smallest_relative_eigenvalue": rel_eig,
        "error_covariance_from": "replicates (4/80 sum over 80 replicates)",
        "noisy_terms": [terms[j] for j in noisy],
    })
    low = [t for t, r in reliability.items() if np.isfinite(r) and r < EIV_LOW_RELIABILITY]
    if low:
        notes.append(f"LOW RELIABILITY: {low} have reliability below {EIV_LOW_RELIABILITY}; moment corrections are "
                     "unstable there (large variance, possible sign changes)")
    if declared:
        diagnostics["replicates_declared_fixed"] = declared
        notes.append(f"{declared} held fixed in the replicate design rows (declared: error independent of the ACS "
                     "sampling error, no replicates); their error enters the residual and the sandwich")
    notes.append("fit_eiv: moment-corrected least squares (Fuller 1987) with per-unit error covariances, including "
                 "the outcome-covariate error covariance, from the ACS replicates; sandwich se_total ("
                 + (f"clustered by {cluster!r}" if cluster else "units independent")
                 + ") is the basis of intervals and p-values")
    res = _corrected_result(formula, model, naive, pd.Series(b, index=terms), se_total, confidence_level,
                            "fit_eiv", notes, diagnostics, int(n))
    res.uncertainty_sources = [SOURCE_MODEL, SOURCE_SAMPLING_REPLICATE]
    res.provenance = {**(res.provenance or {}), "replicate_variables": sorted(mats), "rows_used": int(n)}
    return res


def simex(
    formula: str,
    frame: pd.DataFrame,
    error_covariates: Union[Sequence[str], Mapping[str, str]],
    model: str = "ols",
    weights: Optional[str] = None,
    exposure: Optional[str] = None,
    trials: Optional[str] = None,
    confidence_level: float = 0.90,
    lambdas: Sequence[float] = (0.5, 1.0, 1.5, 2.0),
    n_sim: int = 100,
    extrapolation: str = "quadratic",
    seed: Optional[int] = 0,
    cv_threshold: float = DEFAULT_CV_THRESHOLD,
) -> ModelResult:
    """SIMEX for covariates with known (heteroscedastic) sampling SEs.

    NOT VALIDATED as a default: in docs/audits/inference_validation.md, quadratic
    SIMEX under-corrects attenuation and its 90% intervals covered 0.81 at
    covariate reliability 0.71 (0.29 at reliability 0.38). Prefer
    :func:`regression_calibration` (coverage 0.89, bias removed). Results
    carry a note saying so.

    For each lambda, ``n_sim`` data sets W + sqrt(lambda) * s_i * Z (Z ~ N(0,1))
    are refit; mean coefficients are extrapolated (``quadratic`` or
    ``linear`` in lambda, through lambda = 0, the naive fit) to lambda = -1
    (Cook & Stefanski 1994; heteroscedastic form Devanarayan & Stefanski
    2002). Variance: tau^2(lambda) = mean model variance - between-simulation
    variance, extrapolated to -1 (Stefanski & Cook 1995). Quadratic
    extrapolation is approximate and typically leaves some residual
    attenuation when reliability is low.
    """
    model, spec, data, n_trials, notes, _ = _setup(formula, frame, error_covariates, model, weights, exposure, trials)
    if extrapolation not in ("quadratic", "linear"):
        raise ValueError("extrapolation must be 'quadratic' or 'linear'")
    naive = _fit(formula, data, model, weights, exposure, n_trials)
    terms = naive.params.index
    rng = np.random.default_rng(seed)
    lam = [0.0] + [float(x) for x in lambdas]
    means = [naive.params.to_numpy(float)]
    taus = [naive.bse.to_numpy(float) ** 2]
    failed = 0
    for lv in lambdas:
        bs, vs = [], []
        for _ in range(n_sim):
            d = data.copy()
            for w, s in spec.items():
                d[w] = d[w].to_numpy(float) + math.sqrt(lv) * d[s].to_numpy(float) * rng.standard_normal(len(d))
            try:
                res = _fit(formula, d, model, weights, exposure, n_trials)
                bs.append(res.params.reindex(terms).to_numpy(float))
                vs.append(res.bse.reindex(terms).to_numpy(float) ** 2)
            except Exception:  # noqa: BLE001
                failed += 1
        bs_arr = np.vstack(bs)
        means.append(bs_arr.mean(axis=0))
        taus.append(np.vstack(vs).mean(axis=0) - bs_arr.var(axis=0, ddof=1))
    deg = 2 if extrapolation == "quadratic" else 1
    lam_a = np.asarray(lam)
    M, T = np.vstack(means), np.vstack(taus)
    est = np.array([np.polyval(np.polyfit(lam_a, M[:, j], deg), -1.0) for j in range(M.shape[1])])
    var = np.array([np.polyval(np.polyfit(lam_a, T[:, j], deg), -1.0) for j in range(T.shape[1])])
    if (var <= 0).any():
        notes.append("extrapolated SIMEX variance non-positive for some terms; se_total set to NaN there")
    se_total = pd.Series(np.sqrt(np.where(var > 0, var, np.nan)), index=terms)
    diagnostics = {"reliability_screen": _screen_summary(data, formula, cv_threshold),
                   "simex_path": pd.DataFrame(M, columns=list(terms)).assign(**{"lambda": lam_a}),
                   "failed_simulations": failed}
    notes = notes + [f"SIMEX ({extrapolation} extrapolation, lambdas {lam}, {n_sim} simulations each) for "
                     f"{list(spec)}", FH_POINTER,
                     "SIMEX is not validated for confirmatory use: simulated 90% interval coverage was 0.81 "
                     "(docs/audits/inference_validation.md); prefer regression_calibration"]
    return _corrected_result(formula, model, naive, pd.Series(est, index=terms), se_total, confidence_level,
                             "simex", notes, diagnostics, int(naive.nobs))
