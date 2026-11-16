# SPDX-License-Identifier: AGPL-3.0-or-later
"""Single registry of manifest analysis execution, validation and reporting metadata.

Schema imports this module; schema-dependent helpers therefore import lazily.
"""
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple
import numpy as np
import pandas as pd

@dataclass(frozen=True)
class MethodSpec:
    name: str
    required: Tuple[str, ...]
    statistics: Tuple[str, ...]
    run: Callable[..., Any]
    replicate: bool = False
    external_outcome: bool = False
    # check(stage, context) preserves the legacy validation error order.
    # Stages: count/external, before_spatial, spatial, after_spatial.
    check: Optional[Callable[..., Any]] = None
    text: Optional[Tuple[str, List[str]]] = None

def _run_fit_replicate(a, args, frame, level, replicates, correction, ctx):
    from .. import correlation, models, multitest, sae, trends
    from .schema import _formula_names
    held_external = ctx["held_external"]
    method = a["method"]
    fixed_vars = list(held_external)
    if a.get("replicate_scope") == "covariates_only":  # pre-registered: the outcome is held fixed
        fixed_vars += [v for v in _formula_names(a["formula"].split("~")[0]) if v not in fixed_vars]
    if fixed_vars:
        args["fixed_variables"] = fixed_vars
    return models.fit_replicate(a["formula"], frame, replicates=replicates, confidence_level=level, **args)

def _run_fit_eiv(a, args, frame, level, replicates, correction, ctx):
    from .. import correlation, models, multitest, sae, trends
    from .schema import _formula_names
    held_external = ctx["held_external"]
    method = a["method"]
    if held_external:
        args["fixed_variables"] = held_external
    return models.fit_eiv(a["formula"], frame, replicates=replicates, confidence_level=level, **args)

def _run_regression_calibration(a, args, frame, level, replicates, correction, ctx):
    from .. import correlation, models, multitest, sae, trends
    from .schema import _formula_names
    held_external = ctx["held_external"]
    method = a["method"]
    return getattr(models, method)(a["formula"], frame, confidence_level=level, **args)

def _run_simex(a, args, frame, level, replicates, correction, ctx):
    from .. import correlation, models, multitest, sae, trends
    from .schema import _formula_names
    held_external = ctx["held_external"]
    method = a["method"]
    return getattr(models, method)(a["formula"], frame, confidence_level=level, **args)

def _run_fay_herriot(a, args, frame, level, replicates, correction, ctx):
    from .. import correlation, models, multitest, sae, trends
    from .schema import _formula_names
    held_external = ctx["held_external"]
    method = a["method"]
    y = a["formula"].split("~")[0].strip()
    args.setdefault("se_col", f"{y}_se")
    return getattr(sae, method)(a["formula"], frame, confidence_level=level, **args)

def _run_fh_regression(a, args, frame, level, replicates, correction, ctx):
    from .. import correlation, models, multitest, sae, trends
    from .schema import _formula_names
    held_external = ctx["held_external"]
    method = a["method"]
    y = a["formula"].split("~")[0].strip()
    args.setdefault("se_col", f"{y}_se")
    return getattr(sae, method)(a["formula"], frame, confidence_level=level, **args)

def _run_correlation_matrix(a, args, frame, level, replicates, correction, ctx):
    from .. import correlation, models, multitest, sae, trends
    from .schema import _formula_names
    held_external = ctx["held_external"]
    method = a["method"]
    return correlation.correlation_matrix(frame, args.pop("variables"), confidence_level=level,
                                          replicates=replicates, correction=correction, **args)

def _run_linear_trend_test(a, args, frame, level, replicates, correction, ctx):
    from .. import correlation, models, multitest, sae, trends
    from .schema import _formula_names
    held_external = ctx["held_external"]
    method = a["method"]
    v, g = args.pop("variable"), str(args.pop("geoid"))
    sub = frame[frame["GEOID"] == g].sort_values("Year")
    return trends.linear_trend_test(sub["Year"].tolist(), sub[v].tolist(), ses=sub[f"{v}_se"].tolist(),
                                    confidence_level=level, **args)

def _run_batch_z_test(a, args, frame, level, replicates, correction, ctx):
    from .. import correlation, models, multitest, sae, trends
    from .schema import _formula_names
    held_external = ctx["held_external"]
    method = a["method"]
    v1, v2 = args.pop("variable_1"), args.pop("variable_2")
    df = frame[["GEOID"]].copy()
    for v, tag in ((v1, "1"), (v2, "2")):
        df[f"e{tag}"] = frame[v].to_numpy(float)
        df[f"m{tag}"] = frame[f"{v}_se"].to_numpy(float) * 1.645
    out = multitest.batch_z_test(df, "e1", "m1", "e2", "m2", confidence_level=level,
                                 correction=correction, **args)
    return out

def _stat_coefficient(h, res):
    c = res.coefficients.set_index("term")
    if h["term"] not in c.index:
        raise KeyError(f"term {h['term']!r} not in model (terms: {list(c.index)})")
    row = c.loc[h["term"]]
    from ..models import interval_se_column
    se_col = interval_se_column(res)  # the SE behind p_value and the interval
    return {"estimate": float(row["estimate"]), "se": float(row[se_col]), "se_basis": se_col,
            "p_two_sided": float(row["p_value"]),
            "ci_lower": float(row["ci_lower"]), "ci_upper": float(row["ci_upper"])}

def _stat_correlation(h, res):
    a, b = h["variables"]
    return {"estimate": float(res.matrix.loc[a, b]), "se": None, "p_two_sided": float(res.p_values.loc[a, b]),
            "ci_lower": float(res.ci_lower.loc[a, b]), "ci_upper": float(res.ci_upper.loc[a, b])}

def _stat_trend_slope(h, res):
    return {"estimate": res["slope"], "se": res["se_slope"], "p_two_sided": res["p_value"],
            "ci_lower": res["ci_lower"], "ci_upper": res["ci_upper"]}

def _stat_z_difference(h, res):
    row = res[res["GEOID"] == str(h["geoid"])]
    if row.empty:
        raise KeyError(f"GEOID {h['geoid']} not in the test frame")
    r = row.iloc[0]
    diff = float(r.get("difference", r["e1"] - r["e2"]))
    return {"estimate": diff, "se": None, "p_two_sided": float(r["p_value"]), "ci_lower": None, "ci_upper": None}

def _check_spatial(stage, ctx):
    if stage != "spatial":
        return
    a, manifest, errors, method = (ctx[k] for k in ("a", "manifest", "errors", "method"))
    spatial = (a.get("args") or {}).get("spatial_se")
    if spatial is not None:
        valid_spatial = (isinstance(spatial, Mapping) and set(spatial) == {"cutoff_km"}
                         and type(spatial["cutoff_km"]) in (int, float)
                         and np.isfinite(spatial["cutoff_km"]) and spatial["cutoff_km"] > 0)
        if not valid_spatial:
            errors.append("spatial_se must be an object with exactly cutoff_km (finite number > 0)")
        from ..spatial_hac import SPATIAL_HAC_VALIDATED
        if not SPATIAL_HAC_VALIDATED and not manifest.get("exploratory", False):
            errors.append("spatial_se failed its validation (docs/audits/spatial_hac_validation.md); exploratory only")
        if (a.get("args") or {}).get("cluster"):
            errors.append("spatial_se and cluster are mutually exclusive")
        if method not in ("fit_eiv", "fit_replicate") or (method == "fit_replicate" and
                (a.get("args") or {}).get("model", "ols") not in ("binomial", "poisson")):
            errors.append("spatial_se is supported for fit_eiv and fit_replicate binomial/poisson")

def _check_fit_replicate(stage, ctx):
    from .schema import FORMULA_ID_COLUMNS, LEGACY_X2_MANIFESTS, manifest_hash
    from .replicates import census_vre_source
    i, a, manifest, names, ext_names, errors = (ctx[k] for k in ("i", "a", "manifest", "names", "ext_names", "errors"))
    aargs = a.get("args") or {}
    outcome_name = str(a.get("formula", "")).split("~")[0].strip()
    if stage == "count":
        return (outcome_name if aargs.get("model") == "poisson"
                and outcome_name.endswith("_numerator") and outcome_name[:-10] in ext_names else None)
    if stage == "external" and aargs.get("target", "population") == "these_areas":
        errors.append(f"analyses[{i}] ({a.get('id')}): an external outcome is held fixed in the refits, so "
                      "target 'these_areas' (replicate SE alone) is refused; use 'population' or "
                      "'conservative'")
    count_outcome = ctx.get("count_outcome")
    if stage == "before_spatial":
        allowed = {"model", "weights", "exposure", "trials", "cv_threshold", "max_failed_replicates",
                   "target", "scale", "spatial_se"}
        unknown = sorted(set(aargs) - allowed)
        if unknown:
            errors.append(f"fit_replicate does not take args {unknown}")
        glm = aargs.get("model", "ols")
        if aargs.get("scale") is not None and (aargs["scale"] not in ("X2", "robust")
                                                or glm not in ("binomial", "poisson")):
            errors.append("scale must be 'robust' or 'X2' for binomial or poisson models only")
        if aargs.get("scale") == "robust" and aargs.get("spatial_se") is not None:
            errors.append("scale 'robust' and spatial_se are alternatives; choose one")
        parent = outcome_name if outcome_name in ext_names else count_outcome[:-10] if count_outcome else None
        if parent is not None:
            if glm not in ("ols", "binomial", "poisson"):
                errors.append(f"{glm} not validated for external outcomes (PLAN_ROUND_22 out of scope)")
            if glm == "binomial" and aargs.get("trials") != parent + "_denominator":
                errors.append(f"external binomial outcome requires trials '{parent}_denominator'; effective trials refused")
            if glm == "poisson" and (count_outcome is None or aargs.get("exposure") != parent + "_denominator"):
                errors.append(f"external poisson needs {parent}_numerator outcome and exposure '{parent}_denominator'")
            if glm in ("binomial", "poisson") and aargs.get("scale") is None and aargs.get("spatial_se") is None:
                errors.append("overdispersion would be ignored: set scale 'robust'")
            elif (glm in ("binomial", "poisson") and aargs.get("scale") == "X2"
                  and manifest_hash(manifest) not in LEGACY_X2_MANIFESTS):
                errors.append("external count outcome with scale 'X2' refused: Pearson X2 SEs under-cover when "
                              "areas differ beyond binomial/Poisson chance (validated coverage 0.69-0.79 at "
                              "nominal 0.90, docs/audits/robust_se_validation.md); set scale 'robust' (HC3)")
        for role in ("weights", "exposure", "trials"):
            column = aargs.get(role)
            valid_count = parent and ((glm == "binomial" and role == "trials") or
                                      (glm == "poisson" and role == "exposure")) and column == parent+"_denominator"
            if column is not None and column not in names and column not in FORMULA_ID_COLUMNS and not valid_count:
                errors.append(f"fit_replicate {role} {column!r} is not a manifest variable in this role")
    _check_spatial(stage, ctx)

def _check_fit_eiv(stage, ctx):
    from .schema import FORMULA_ID_COLUMNS, LEGACY_X2_MANIFESTS, manifest_hash
    from .replicates import census_vre_source
    i, a, manifest, names, ext_names, errors = (ctx[k] for k in ("i", "a", "manifest", "names", "ext_names", "errors"))
    aargs = a.get("args") or {}
    outcome_name = str(a.get("formula", "")).split("~")[0].strip()
    if stage == "after_spatial":
        eargs = a.get("args") or {}
        unknown = sorted(set(eargs) - {"model", "weights", "cv_threshold", "target", "cluster", "cluster_se", "spatial_se"})
        if unknown:
            errors.append(f"analyses[{i}] ({a.get('id')}): fit_eiv does not take args {unknown} (allowed: "
                          "model, weights, cv_threshold, cluster, cluster_se)")
        if "cluster_se" in eargs and (eargs["cluster_se"] not in ("cr1", "jackknife") or "cluster" not in eargs):
            errors.append(f"analyses[{i}] ({a.get('id')}): fit_eiv args.cluster_se must be 'cr1' or 'jackknife' "
                          "and needs args.cluster")
        if "target" in eargs:
            errors.append(f"analyses[{i}] ({a.get('id')}): fit_eiv takes no 'target': its intervals use the "
                          "sandwich se_total (a measurement-error correction is a claim about the population "
                          "relationship, not about these areas)")
        if "cluster" in eargs:
            cl = eargs["cluster"]
            from ..models import CLUSTER_PREFIX_RE
            mm = CLUSTER_PREFIX_RE.match(str(cl)) if isinstance(cl, str) else None
            if not isinstance(cl, str) or not (cl in names or cl in FORMULA_ID_COLUMNS
                                               or (mm and 1 <= int(mm.group(1)) <= 11)):
                errors.append(f"analyses[{i}] ({a.get('id')}): fit_eiv args.cluster must be a manifest variable "
                              "or GEOID.str[:N] (e.g. GEOID.str[:5] for counties of tracts)")
        if str(eargs.get("model", "ols")).lower() not in ("ols", "wls"):
            errors.append(f"analyses[{i}] ({a.get('id')}): fit_eiv supports model 'ols' or 'wls'")
        if str(eargs.get("model", "ols")).lower() == "wls" and not eargs.get("weights"):
            errors.append(f"analyses[{i}] ({a.get('id')}): fit_eiv with model 'wls' needs args.weights")
        if not census_vre_source(manifest) and a.get("replicates") != "required":
            errors.append(f"analyses[{i}] ({a.get('id')}): fit_eiv needs replicates: declare "
                          "replicates.source 'census_vre' or \"replicates\": \"required\"")
    _check_spatial(stage, ctx)

METHODS: Dict[str, MethodSpec] = {
    'fit_replicate': MethodSpec('fit_replicate', ('formula',), ('coefficient',), _run_fit_replicate, replicate=True, external_outcome=True, check=_check_fit_replicate, text=('Coefficients were estimated with {model} regression (statsmodels) on the full-sample estimates; sampling standard errors came from refitting on each of {rep_source}, Var = 4/80 sum (b_r - b)^2, combined with the model standard error as se_total = sqrt(se_model^2 + se_sampling^2). Reported standard errors, intervals and p-values use the {target_se} ({target} target: {estimand}), with normal-theory intervals. Without replicates only model standard errors are reported.', ['vre', 'design', 'statsmodels'])),
    'fit_eiv': MethodSpec('fit_eiv', ('formula',), ('coefficient',), _run_fit_eiv, replicate=True, external_outcome=True, check=_check_fit_eiv, text=('Coefficients were estimated by moment-corrected least squares ({model}; Fuller 1987) with per-unit sampling-error covariances of every design column and of the outcome, including the outcome-covariate error covariance, estimated from {rep_source} (4/80 sum over replicates). Standard errors are {se_basis} (se_total, used for normal-theory intervals and p-values); naive coefficients are reported alongside. Coefficients are {estimand}.', ['fuller', 'vre', 'design'])),
    'regression_calibration': MethodSpec('regression_calibration', ('formula', 'error_covariates'), ('coefficient',), _run_regression_calibration, replicate=False, external_outcome=False, check=_check_spatial, text=('Covariates measured with known ACS sampling error ({cov}) were corrected by regression calibration with heteroscedastic known error variances; standard errors (se_total, used for normal-theory intervals and p-values) by row bootstrap re-estimating the calibration. Coefficients are {estimand}.', ['carroll'])),
    'simex': MethodSpec('simex', ('formula', 'error_covariates'), ('coefficient',), _run_simex, replicate=False, external_outcome=False, check=_check_spatial, text=('Covariates measured with known ACS sampling error ({cov}) were corrected by simulation-extrapolation (SIMEX, quadratic extrapolation) with the measurement-error jackknife variance (se_total, used for normal-theory intervals and p-values). Coefficients are {estimand}.', ['simex', 'carroll'])),
    'fh_regression': MethodSpec('fh_regression', ('formula',), ('coefficient',), _run_fh_regression, replicate=False, external_outcome=True, check=_check_spatial, text=("The outcome's known sampling variance was modelled with an area-level Fay-Herriot model (GLS coefficients, REML variance component).", ['fh'])),
    'fay_herriot': MethodSpec('fay_herriot', ('formula',), ('coefficient',), _run_fay_herriot, replicate=False, external_outcome=False, check=_check_spatial, text=('Small-area estimates are Fay-Herriot EBLUPs (REML) with Prasad-Rao/Datta-Lahiri MSE.', ['fh'])),
    'correlation_matrix': MethodSpec('correlation_matrix', ('variables',), ('correlation',), _run_correlation_matrix, replicate=True, external_outcome=False, check=_check_spatial, text=('Correlations with Fisher-z intervals{rep}.', ['fisher', 'vre'])),
    'linear_trend_test': MethodSpec('linear_trend_test', ('variable', 'geoid'), ('trend_slope',), _run_linear_trend_test, replicate=False, external_outcome=False, check=_check_spatial, text=('Linear trends across non-overlapping 5-year periods were tested by GLS with known sampling variances.', ['testing'])),
    'batch_z_test': MethodSpec('batch_z_test', ('variable_1', 'variable_2'), ('z_difference',), _run_batch_z_test, replicate=False, external_outcome=False, check=_check_spatial, text=('Differences were tested with the Census two-sample z test, SE = MOE/1.645.', ['testing'])),
}

STATISTIC_EXTRACTORS = {
    'coefficient': _stat_coefficient,
    'correlation': _stat_correlation,
    'trend_slope': _stat_trend_slope,
    'z_difference': _stat_z_difference,
}

ANALYSIS_METHODS = {name: (spec.required, spec.statistics) for name, spec in METHODS.items()}
STATISTICS = tuple(dict.fromkeys(stat for spec in METHODS.values() for stat in spec.statistics))
# Preserve the historical public tuple order; future entries follow registry order.
REPLICATE_METHODS = tuple(sorted((name for name, spec in METHODS.items() if spec.replicate),
    key=lambda name: {"fit_replicate": 0, "correlation_matrix": 1, "fit_eiv": 2}.get(name, 3)))
EXTERNAL_OUTCOME_METHODS = tuple(sorted((name for name, spec in METHODS.items() if spec.external_outcome),
    key=lambda name: {"fit_eiv": 0, "fit_replicate": 1, "fh_regression": 2}.get(name, 3)))
