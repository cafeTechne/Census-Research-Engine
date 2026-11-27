# SPDX-License-Identifier: AGPL-3.0-or-later
"""Single registry of manifest analysis execution, validation and reporting metadata.

Schema imports this module; schema-dependent helpers therefore import lazily.
"""
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple
import numpy as np
import pandas as pd
from scipy import stats

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
    default_target: str = "population"
    optional: Tuple[str, ...] = ()
    format_text: Optional[Callable[..., str]] = None
    required_alternatives: Tuple[Tuple[str, str], ...] = ()

def _run_fit_replicate(a, args, frame, level, replicates, correction, ctx):
    from .. import correlation, models, multitest, sae, trends
    from .schema import _formula_names
    held_external = ctx["held_external"]
    method = a["method"]
    fixed_vars = list(held_external)
    if a.get("replicate_scope") == "covariates_only":  # pre-registered: the outcome is held fixed
        fixed_vars += [v for v in _formula_names(a["formula"].split("~")[0]) if v not in fixed_vars]
    if args.get("impute") is not None:  # Round 104: FCS multiple imputation (Round 100)
        from ..mice import impute_fcs, AUDIT as _MICE_AUDIT
        delta = ({args["impute_delta_variable"]: args["impute_delta_shifts"]}
                 if args.get("impute_delta_variable") and args.get("impute_delta_shifts") else None)
        out = impute_fcs(a["formula"], frame, args["impute"], method=args.get("impute_method", "pmm"),
                         delta=delta, level=level)
        wrapped_in = {**out, "table": out["table"].rename(columns={"ci_lower": "lower", "ci_upper": "upper"})}
        result = _wrap_table(wrapped_in, f"OLS with FCS imputation ({out['method']})", a["formula"], "fit_replicate",
                             list(out.get("notes", [])),
                             {"fcs_imputation": {"method": out["method"], "imputations": out.get("imputations", 20),
                                                 "incomplete": list(args["impute"]),
                                                 "validated": out["validated"], "audit": _MICE_AUDIT,
                                                 "delta": out.get("delta")}})
        result.confidence_level = level
    elif args.get("spatial_scpc") is not None:  # Round 61: SCPC naive slopes (Round 58)
        result = _scpc_result(a["formula"], frame, args, level, ctx.get("coords"))
    elif args.get("model") == "negbin":  # Round 43 M2: NB2-HC3 (Round 39), model SE, naive target
        result = _negbin_result(a["formula"], frame, args["exposure"], level)
    else:
        fit_args = {k: v for k, v in args.items() if k not in ("marginal", "impute", "impute_method",
                                                               "impute_delta_variable", "impute_delta_shifts")}
        if fixed_vars:
            fit_args["fixed_variables"] = fixed_vars
        result = models.fit_replicate(a["formula"], frame, replicates=replicates, confidence_level=level, **fit_args)
    if args.get("marginal") is not None:  # Round 104: marginal binomial RR/RD/AF (Round 84)
        from ..epi_measures import area_marginal_measures
        m_cfg = args["marginal"]
        m_out = area_marginal_measures(frame, a["formula"], args["trials"], m_cfg["exposure"],
                                       values=m_cfg.get("contrast"), level=level)
        result.diagnostics["marginal"] = m_out
    outcome = str(a["formula"]).split("~")[0].strip()
    parent = next((n for n in ctx.get("wonder_names",()) if outcome in (n,n+"_numerator")),None)
    if parent:
        from ..wonder_outputs import suppression_info
        info = suppression_info(frame,parent)
        result.diagnostics["wonder_suppression"] = info
        if info["excluded_counties"]:
            result.notes.append(f"WONDER complete-case exclusions: {info['suppressed_counties']}; excluded deaths bounded by {info['excluded_deaths_bounds']}, not imputed.")
            result.diagnostics["deviations"] = [{"kind":"wonder_suppressed","geoid":g,"detail":"Suppressed county excluded from regression."} for g in info["suppressed_counties"]]
        if args.get("exposure"):
            result.notes.append(f"Exposure {args['exposure']} held fixed in every replicate; offset/reference-rate uncertainty is excluded from this regression; reference-aware SMR intervals are the sensitivity check.")
    return result

def _run_fit_eiv(a, args, frame, level, replicates, correction, ctx):
    from .. import correlation, models, multitest, sae, trends
    from .schema import _formula_names
    held_external = ctx["held_external"]
    method = a["method"]
    if held_external:
        args["fixed_variables"] = held_external
    if args.get("spatial") is not None:  # Round 43 M3: corrected slopes with spatial inference (Round 35)
        return _spatial_eiv_result(a["formula"], frame, replicates, args["spatial"], held_external, level, ctx.get("coords"))
    return models.fit_eiv(a["formula"], frame, replicates=replicates, confidence_level=level, **args)


def _negbin_result(formula, frame, exposure, level):
    from scipy import stats
    from ..count_models import fit_count_model
    from ..results import ModelResult, SOURCE_MODEL
    out = fit_count_model(formula, frame, exposure, "negbin", level)
    t = out["table"]
    se = t["se"].to_numpy(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        p = 2*stats.norm.sf(np.abs(t["estimate"].to_numpy(float)/se))
    table = pd.DataFrame({"term": t["term"], "estimate": t["estimate"], "se_model": se, "se_sampling": np.nan,
                          "se_total": se, "ci_lower": t["lower"], "ci_upper": t["upper"], "p_value": p})
    notes = list(out["notes"]) + [f"Negative binomial (NB2; alpha by maximum likelihood, then GLM HC3), offset log({exposure}); "
                                  "validated in Round 39 (docs/audits/manova_counts_validation.md)."]
    return ModelResult(model_type="negbin", formula=formula, n_obs=int(out["n"]), coefficients=table, method="fit_replicate",
                       uncertainty_sources=[SOURCE_MODEL], confidence_level=level, notes=notes,
                       diagnostics={"interval_target": "population", "family": "negbin", "validated": bool(out["validated"])})


def _wrap_table(out, model, formula, method, notes, diag, se_name="se"):
    """A library result dict (table with term/estimate/se/lower/upper[/p_value]) as a ModelResult."""
    from scipy import stats
    from ..results import ModelResult, SOURCE_MODEL
    t = out["table"]
    se = t[se_name].to_numpy(float)
    if "p_value" in t:
        p = t["p_value"].to_numpy(float)
    else:
        df = t["df"].to_numpy(float) if "df" in t else None
        with np.errstate(divide="ignore", invalid="ignore"):
            z = np.abs(t["estimate"].to_numpy(float)/se)
            p = 2*stats.t.sf(z, df) if df is not None else 2*stats.norm.sf(z)
    table = pd.DataFrame({"term": t["term"], "estimate": t["estimate"], "se_model": se, "se_sampling": np.nan,
                          "se_total": se, "ci_lower": t["lower"], "ci_upper": t["upper"], "p_value": p})
    return ModelResult(model_type=model, formula=formula, n_obs=int(out["n"]), coefficients=table, method=method,
                       uncertainty_sources=[SOURCE_MODEL], confidence_level=.90, notes=list(out["notes"])+notes,
                       diagnostics={"interval_target": "population", **diag})


def _scpc_result(formula, frame, args, level, coords):
    from ..scpc import fit_scpc
    spec = args.get("spatial_scpc") or {}
    out = fit_scpc(formula, frame, args.get("model", "ols"), trials=args.get("trials"), exposure=args.get("exposure"),
                   coords=coords, rho_bar=spec.get("rho_bar"), level=level)
    return _wrap_table(out, args.get("model", "ols"), formula, "fit_replicate",
                       ["SCPC spatial-correlation-robust intervals and p-values (Round 58; manifests since Round 61)."],
                       {"spatial_scpc": {"rho_bar": out["rho_bar"], "validated": bool(out["validated"]),
                                         "q": int(out["table"]["q"].iloc[0]) if len(out["table"]) else None}})


def _rc_clusters_result(formula, frame, args, level, coords):
    from ..count_models import fit_count_model
    from ..models import regression_calibration_clusters
    model = args.get("model", "ols"); cov = args["error_covariates"]
    if model in ("poisson", "negbin"):
        out = fit_count_model(formula, frame, args["exposure"], model, level, spatial="clusters", coords=coords,
                              calibrate=cov)
    else:
        out = regression_calibration_clusters(formula, frame, cov, args["trials"], coords=coords, level=level)
    return _wrap_table(out, model, formula, "regression_calibration",
                       ["Regression calibration (pooled) with IM-8 cluster slopes, t(7) (Rounds 53/58; manifests since Round 61)."],
                       {"rc_clusters": {"validated": bool(out["validated"])}, "regression_calibration_validated": bool(out["validated"])})


SPATIAL_EIV_METHODS = {"clusters": "g1", "error": "g2"}


def _spatial_eiv_result(formula, frame, replicates, spatial, fixed, level, coords):
    from ..results import ModelResult, SOURCE_MODEL, SOURCE_SAMPLING_MODEL
    from ..spatial_eiv import fit_spatial_eiv
    if replicates is None:
        raise ValueError("spatial fit_eiv needs ACS replicates")
    out = fit_spatial_eiv(formula, frame, replicates, method=SPATIAL_EIV_METHODS[spatial], coords=coords,
                          fixed_variables=fixed, level=level)
    t = out["table"]
    table = pd.DataFrame({"term": t["term"], "estimate": t["estimate"], "se_model": np.nan, "se_sampling": np.nan,
                          "se_total": t["se"], "ci_lower": t["ci_lower"], "ci_upper": t["ci_upper"],
                          "p_value": t["p_value"], "df": t["df"]})
    diag = {"spatial_eiv": {"method": out["method"], "spatial": spatial, "validated": bool(out["validated"]),
                            "error_prone": out["error_prone"],
                            **({"lambda": out["lambda"]} if "lambda" in out else {"cluster_estimates": out["cluster_estimates"],
                                                                                   "cluster_terms": out["cluster_terms"]})}}
    return ModelResult(model_type="ols", formula=formula, n_obs=int(out["n"]), coefficients=table, method="fit_eiv",
                       uncertainty_sources=[SOURCE_MODEL, SOURCE_SAMPLING_MODEL], confidence_level=level,
                       notes=list(out["notes"]), diagnostics=diag)

def _run_regression_calibration(a, args, frame, level, replicates, correction, ctx):
    from .. import correlation, models, multitest, sae, trends
    from .schema import _formula_names
    held_external = ctx["held_external"]
    method = a["method"]
    if args.get("spatial") is not None:  # Round 61: calibrated IM-8 cluster slopes
        return _rc_clusters_result(a["formula"], frame, args, level, ctx.get("coords"))
    return getattr(models, method)(a["formula"], frame, confidence_level=level, **args)


def _check_regression_calibration(stage, ctx):
    if stage == "before_spatial":
        a, errors = ctx["a"], ctx["errors"]
        args = a.get("args") or {}
        if args.get("spatial") is not None:
            prefix = f"analyses[{ctx['i']}] ({a.get('id')}): "
            model = args.get("model", "ols")
            if args["spatial"] != "clusters":
                errors.append(prefix+"regression_calibration args.spatial must be 'clusters' (Round 61)")
            if model not in ("poisson", "negbin", "binomial"):
                errors.append(prefix+"spatial regression calibration supports model poisson, negbin (exposure) or "
                              "binomial (trials) (Rounds 53/58)")
            need = "trials" if model == "binomial" else "exposure"
            if model in ("poisson", "negbin", "binomial") and not args.get(need):
                errors.append(prefix+f"spatial regression calibration with model {model} needs args.{need}")
            bad = sorted(set(args) - {"spatial", "model", "exposure", "trials"})
            if bad:
                errors.append(prefix+f"spatial regression calibration does not take args {bad}")
    _check_spatial(stage, ctx)

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
    spatial = args.pop("spatial", False)
    if args.pop("interval", "fisher") == "validated":  # Round 43 M1: Round 33 validated intervals
        coords = None
        if spatial:  # Round 61: effective-n intervals (Rounds 48/59)
            coords = ctx.get("coords")
            if coords is None:
                from ..small_spatial import frame_coordinates
                coords = frame_coordinates(frame)
        return _validated_correlation_result(frame, args.pop("variables"), args.get("method", "pearson"),
                                             replicates, args.get("controls") or [], level, coords)
    return correlation.correlation_matrix(frame, args.pop("variables"), confidence_level=level,
                                          replicates=replicates, correction=correction, **args)


def _validated_correlation_result(frame, variables, method, replicates, controls, level, coords=None):
    from scipy import stats
    from ..correlation import validated_correlations
    from ..results import CorrelationResult
    rows = validated_correlations(frame, variables, method=method, replicates=replicates, controls=controls,
                                  confidence_level=level, coords=coords)
    v = list(variables)
    sq = lambda: pd.DataFrame(np.nan, index=v, columns=v)
    mat, n, pv, lo, hi = sq(), sq(), sq(), sq(), sq()
    validated = {}
    crit = stats.norm.ppf((1+level)/2)
    for r in rows.itertuples():
        se_z = (np.arctanh(r.ci_upper)-np.arctanh(r.ci_lower))/(2*crit)
        p = float(2*stats.norm.sf(abs(np.arctanh(r.estimate))/se_z)) if np.isfinite(se_z) and se_z > 0 else np.nan
        for a_, b_ in ((r.var_a, r.var_b), (r.var_b, r.var_a)):
            mat.loc[a_, b_], n.loc[a_, b_], pv.loc[a_, b_] = r.estimate, r.n, p
            lo.loc[a_, b_], hi.loc[a_, b_] = r.ci_lower, r.ci_upper
        validated[f"{r.var_a}|{r.var_b}"] = {"validated": bool(r.validated), "variant": int(r.variant), "note": r.note}
    for x in v:
        mat.loc[x, x] = 1.0
    notes = [f"{method} correlations with the Round 33 validated interval (docs/audits/rank_validation.md); estimand: "
             "the coefficient on the ACS estimates as observed; areas assumed independent (every interval "
             "under-covered under spatial dependence)."] if coords is None else [
             f"{method} correlations with effective-sample-size intervals for spatially dependent areas (Rounds 48/59, "
             "docs/audits/small_spatial_validation.md, docs/audits/spatial_correlation_validation.md); estimand: the "
             "coefficient on the ACS estimates as observed."]
    return CorrelationResult(matrix=mat, n=n, p_values=pv, ci_lower=lo, ci_upper=hi, method=method,
                             confidence_level=level, notes=notes,
                             provenance={"interval": "validated", "pairs": validated, "controls": list(controls)})

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
    if h['term'] in (res.diagnostics.get('spatial_clusters') or {}).get('not_estimable_terms',()):
        raise ValueError(f"term {h['term']!r} is not estimable under IM; absorbed by cluster intercepts")
    from ..models import interval_se_column
    se_col = interval_se_column(res)  # the SE behind p_value and the interval
    sp = res.diagnostics.get("spatial_eiv")
    if sp is not None and not sp["validated"]:
        return {"estimate": float(row["estimate"]), "se": float(row[se_col]), "se_basis": se_col,
                "p_two_sided": float(row["p_value"]), "ci_lower": float(row["ci_lower"]), "ci_upper": float(row["ci_upper"]),
                "confirmatory_refusal": f"spatial EIV with {len(sp['error_prone'])} error-prone covariates is exploratory "
                                        "(validated with at most 5, or up to 8 (G1) / 7 (G2) when every reliability is >= .8; "
                                        "docs/audits/spatial_eiv_validation.md, docs/audits/small_many_validation.md, "
                                        "docs/audits/glm_correction_validation.md, docs/audits/glm_correction2_validation.md)"}
    scpc = res.diagnostics.get("spatial_scpc")
    if scpc is not None and not scpc["validated"]:
        return {"estimate": float(row["estimate"]), "se": float(row[se_col]), "se_basis": se_col,
                "p_two_sided": float(row["p_value"]), "ci_lower": float(row["ci_lower"]), "ci_upper": float(row["ci_upper"]),
                "confirmatory_refusal": "SCPC is validated for county OLS (rho_bar .05, .10), Poisson (.10) and binomial "
                                        "(.15, .20) and tract OLS (.20, .30) only (docs/audits/spatial_outside_validation.md, "
                                        "docs/audits/leftover_failures_validation.md, docs/audits/tract_spatial_validation.md)"}
    if res.diagnostics.get("regression_calibration_validated") is False:
        return {"estimate": float(row["estimate"]), "se": float(row[se_col]), "se_basis": se_col,
                "p_two_sided": float(row["p_value"]), "ci_lower": float(row["ci_lower"]), "ci_upper": float(row["ci_upper"]),
                "confirmatory_refusal": f"regression calibration for {res.model_type} slopes is exploratory with this "
                                        "SE method (docs/audits/glm_correction_validation.md; binomial needs "
                                        "args.se_method 'jackknife', docs/audits/glm_correction2_validation.md)"}
    return {"estimate": float(row["estimate"]), "se": (None if se_col == "bootstrap_test" else float(row[se_col])), "se_basis": se_col,
            "p_two_sided": float(row["p_value"]),
            "ci_lower": float(row["ci_lower"]), "ci_upper": float(row["ci_upper"])}

def _stat_joint_wald(h, res):
    from ..splines import joint_wald
    return joint_wald(res, h["variable"])


def _stat_joint_test(h, res):
    from ..joint_tests import joint_test
    out = joint_test(res, variable=h.get("variable"), term=h.get("term"))
    out.pop("columns", None); out.pop("family", None)
    return out


def _stat_correlation(h, res):
    a, b = h["variables"]
    out = {"estimate": float(res.matrix.loc[a, b]), "se": None, "p_two_sided": float(res.p_values.loc[a, b]),
           "ci_lower": float(res.ci_lower.loc[a, b]), "ci_upper": float(res.ci_upper.loc[a, b])}
    prov = getattr(res, "provenance", None) or {}
    if prov.get("interval") == "validated":
        pair = prov["pairs"].get(f"{a}|{b}") or prov["pairs"].get(f"{b}|{a}")
        out["se_basis"] = f"r33_variant_{pair['variant']}"
        if not pair["validated"]:
            out["confirmatory_refusal"] = f"correlation {a}/{b}: {pair['note'] or 'interval not validated'}"
    return out

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
    if stage == "hypothesis":
        h, a, manifest, errors = (ctx[k] for k in ("h", "a", "manifest", "errors"))
        if h.get("statistic") == "joint_wald":
            from ..splines import JOINT_WALD_VALIDATED
            from .schema import _formula_names
            if not isinstance(h.get("variable"), str) or not h.get("variable") or h["variable"] not in _formula_names(a.get("formula", "")):
                errors.append("joint_wald requires variable: a manifest variable in the analysis formula")
            if "term" in h:
                errors.append("joint_wald takes variable, not term")
            if h.get("direction", "two_sided") not in ("two_sided", "two-sided"):
                errors.append("joint_wald direction must be two_sided (two-sided); one-sided tests are refused")
            args = a.get("args") or {}
            if args.get("model", "ols") not in ("ols", "wls", "binomial", "poisson") or args.get("spatial_se") is not None or args.get("spatial_clusters") is not None:
                errors.append("joint_wald supports only non-spatial fit_replicate OLS/WLS/binomial/Poisson")
            if not JOINT_WALD_VALIDATED and not manifest.get("exploratory", False):
                errors.append("joint_wald failed or was not validated; exploratory only (docs/audits/joint_wald_validation.md); use joint_test")
        if h.get("statistic") == "joint_test":
            from .schema import _formula_names
            has_var, has_term = isinstance(h.get("variable"), str) and bool(h.get("variable")), isinstance(h.get("term"), str) and bool(h.get("term"))
            if has_var == has_term:
                errors.append("joint_test requires exactly one of variable (a manifest variable in the formula) or term (a formula term such as 'C(group)' or 'a:b')")
            elif has_var and h["variable"] not in _formula_names(a.get("formula", "")):
                errors.append("joint_test variable must be a manifest variable in the analysis formula")
            if h.get("direction", "two_sided") not in ("two_sided", "two-sided"):
                errors.append("joint_test direction must be two_sided (two-sided); one-sided tests are refused")
            args = a.get("args") or {}
            clusters = args.get("spatial_clusters")
            if args.get("model", "ols") not in ("ols", "binomial", "poisson") or args.get("spatial_se") is not None:
                errors.append("joint_test supports fit_replicate OLS/binomial/Poisson without spatial_se")
            if clusters is not None and clusters != {"k": 8, "method": "im"}:
                errors.append("joint_test with spatial clusters supports only IM with k=8")
        return
    from .schema import FORMULA_ID_COLUMNS, LEGACY_X2_MANIFESTS, manifest_hash
    from .replicates import census_vre_source
    i, a, manifest, names, ext_names, errors = (ctx[k] for k in ("i", "a", "manifest", "names", "ext_names", "errors"))
    aargs = a.get("args") or {}
    outcome_name = str(a.get("formula", "")).split("~")[0].strip()
    if stage == "count":
        return (outcome_name if aargs.get("model") in ("poisson", "negbin")
                and outcome_name.endswith("_numerator") and outcome_name[:-10] in ext_names else None)
    if stage == "external" and aargs.get("target", "population") == "these_areas":
        errors.append(f"analyses[{i}] ({a.get('id')}): an external outcome is held fixed in the refits, so "
                      "target 'these_areas' (replicate SE alone) is refused; use 'population' or "
                      "'conservative'")
    count_outcome = ctx.get("count_outcome")
    if stage == "before_spatial":
        allowed = {"model", "weights", "exposure", "trials", "cv_threshold", "max_failed_replicates",
                   "target", "scale", "spatial_se", "spatial_clusters", "spatial_scpc",
                   "marginal", "impute", "impute_method", "impute_delta_variable", "impute_delta_shifts"}
        unknown = sorted(set(aargs) - allowed)
        if unknown:
            errors.append(f"fit_replicate does not take args {unknown}")
        if aargs.get("marginal") is not None:
            m_cfg = aargs["marginal"]
            if aargs.get("model") != "binomial" or not aargs.get("trials"):
                errors.append("fit_replicate args.marginal requires model 'binomial' and args.trials")
            elif not isinstance(m_cfg, dict) or not isinstance(m_cfg.get("exposure"), str) or m_cfg["exposure"] not in names:
                errors.append("fit_replicate args.marginal must be {exposure: <manifest variable>[, contrast: [lo, hi]]}")
        if aargs.get("impute") is not None:
            imp = aargs["impute"]
            if not isinstance(imp, list) or not imp or not all(isinstance(v, str) and v in names for v in imp):
                errors.append("fit_replicate args.impute must be a non-empty list of manifest variables")
            if aargs.get("impute_method", "pmm") not in ("pmm", "norm"):
                errors.append("fit_replicate args.impute_method must be 'pmm' or 'norm'")
            if aargs.get("model", "ols") != "ols":
                errors.append("fit_replicate args.impute is validated for OLS only")
        glm = aargs.get("model", "ols")
        scpc = aargs.get("spatial_scpc")
        if scpc is not None:  # Round 61: SCPC naive slopes (Round 58)
            from ..scpc import validated_rho, default_rho
            tract = manifest.get("geography", {}).get("level") == "tract"
            prefix = f"analyses[{i}] ({a.get('id')}): "
            rho = scpc.get("rho_bar") if isinstance(scpc, dict) else None
            if not isinstance(scpc, dict) or set(scpc) - {"rho_bar"} or (rho is not None and (type(rho) not in (int, float) or not 0 < rho < 1)):
                errors.append(prefix+"spatial_scpc must be {} or {rho_bar: number in (0, 1)}")
            elif glm not in ("ols", "poisson", "binomial"):
                errors.append(prefix+"spatial_scpc supports model ols, poisson or binomial")
            elif (rho if rho is not None else default_rho(glm, tract)) not in validated_rho(glm, tract) and not manifest.get("exploratory", False):
                errors.append(prefix+f"SCPC with model {glm} and this rho_bar was not validated (Rounds 58/62 counties: ols "
                              ".05/.10, poisson .10, binomial .15/.20; Round 71 tracts: ols .20/.30); exploratory only")
            bad = sorted(k for k in ("weights", "scale", "spatial_se", "spatial_clusters") if aargs.get(k) is not None)
            if bad:
                errors.append(prefix+f"spatial_scpc does not combine with {bad}")
            if aargs.get("target", "population") != "population":
                errors.append(prefix+"spatial_scpc supports target 'population' only (no ACS replicate variance)")
            if glm == "poisson" and not aargs.get("exposure"):
                errors.append(prefix+"spatial_scpc with model poisson needs args.exposure")
            if glm == "binomial" and not aargs.get("trials"):
                errors.append(prefix+"spatial_scpc with model binomial needs args.trials")
        if glm == "negbin":  # Round 43 M2: only the Round 39 validated configuration
            prefix = f"analyses[{i}] ({a.get('id')}): "
            bad = sorted(k for k in ("weights", "trials", "scale", "spatial_se", "spatial_clusters") if aargs.get(k) is not None)
            if bad:
                errors.append(prefix+f"negbin does not take {bad}: NB2-HC3 was validated without weights, scale "
                              "options or spatial inference (docs/audits/manova_counts_validation.md)")
            if not aargs.get("exposure"):
                errors.append(prefix+"negbin needs args.exposure (offset log exposure)")
            if aargs.get("target", "population") != "population":
                errors.append(prefix+"negbin supports target 'population' only (model HC3 SE; no ACS replicate "
                              "variance was validated)")
        if aargs.get("scale") is not None and (aargs["scale"] not in ("X2", "robust")
                                                or glm not in ("binomial", "poisson")):
            errors.append("scale must be 'robust' or 'X2' for binomial or poisson models only")
        if aargs.get("scale") == "robust" and aargs.get("spatial_se") is not None:
            errors.append("scale 'robust' and spatial_se are alternatives; choose one")
        clusters = aargs.get("spatial_clusters")
        if clusters is not None:
            from ..spatial_clusters import check_config, SPATIAL_CLUSTERS_VALIDATED, VALIDATED_CLUSTER_COUNTS, supports_im_acs
            prefix = f"analyses[{i}] ({a.get('id')}): "
            try:
                check_config(clusters)
            except ValueError as exc:
                errors.append(prefix+str(exc))
            else:
                cluster_method = clusters["method"]
                if (not SPATIAL_CLUSTERS_VALIDATED[cluster_method] or clusters["k"] not in VALIDATED_CLUSTER_COUNTS[cluster_method]) and not manifest.get("exploratory", False):
                    errors.append(prefix+"spatial_clusters method/count failed or was not validated; exploratory only (docs/audits/spatial_cluster_validation.md)")
                if cluster_method in ("im", "wcr"):
                    if aargs.get("target", "population") != "population":
                        errors.append(prefix+"IM/WCR spatial_clusters require target population; no ACS SE combination")
                    if (census_vre_source(manifest) or a.get("replicates") == "required") and not supports_im_acs(clusters,glm):
                        errors.append(prefix+"IM/WCR spatial_clusters cannot use declared ACS replicates; not validated (docs/audits/im_acs_validation.md)")
            if aargs.get("spatial_se") is not None or aargs.get("scale") == "robust":
                errors.append(prefix+"spatial_clusters is mutually exclusive with spatial_se and scale robust")
            if (glm not in ("ols", "binomial") and not supports_im_acs(clusters,glm)) or aargs.get("weights") is not None:
                errors.append(prefix+"spatial_clusters supports unweighted OLS and binomial only; EIV/Poisson/WLS were not validated")
        parent = outcome_name if outcome_name in ext_names else count_outcome[:-10] if count_outcome else None
        if parent is not None:
            if glm not in ("ols", "binomial", "poisson", "negbin"):
                errors.append(f"{glm} not validated for external outcomes (PLAN_ROUND_22 out of scope)")
            if glm == "binomial" and aargs.get("trials") != parent + "_denominator":
                errors.append(f"external binomial outcome requires trials '{parent}_denominator'; effective trials refused")
            expected_offset = any(d.get("op")=="expected_count" and d.get("name")==aargs.get("exposure") for d in manifest.get("derivations",[]))
            if glm in ("poisson", "negbin") and (count_outcome is None or (aargs.get("exposure") != parent + "_denominator" and not expected_offset)):
                errors.append(f"external poisson needs {parent}_numerator outcome and exposure '{parent}_denominator'")
            if glm in ("binomial", "poisson") and aargs.get("scale") is None and aargs.get("spatial_se") is None and clusters is None and scpc is None:
                errors.append("overdispersion would be ignored: set scale 'robust'")
            elif (glm in ("binomial", "poisson") and aargs.get("scale") == "X2"
                  and manifest_hash(manifest) not in LEGACY_X2_MANIFESTS):
                errors.append("external count outcome with scale 'X2' refused: Pearson X2 SEs under-cover when "
                              "areas differ beyond binomial/Poisson chance (validated coverage 0.69-0.79 at "
                              "nominal 0.90, docs/audits/robust_se_validation.md); set scale 'robust' (HC3)")
        for role in ("weights", "exposure", "trials"):
            column = aargs.get(role)
            valid_count = parent and ((glm == "binomial" and role == "trials") or
                                      (glm in ("poisson", "negbin") and role == "exposure")) and column == parent+"_denominator"
            if column is not None and column not in names and column not in FORMULA_ID_COLUMNS and not valid_count:
                errors.append(f"fit_replicate {role} {column!r} is not a manifest variable in this role")
    _check_spatial(stage, ctx)

def _check_correlation(stage, ctx):
    if stage == "before_spatial":
        from .replicates import census_vre_source
        from ..correlation import VALIDATED_VARIANT
        i, a, manifest, names, errors = (ctx[k] for k in ("i", "a", "manifest", "names", "errors"))
        args = a.get("args") or {}
        prefix = f"analyses[{i}] ({a.get('id')}): "
        interval = args.get("interval", "fisher")
        if interval not in ("fisher", "validated"):
            errors.append(prefix+"correlation_matrix args.interval must be 'fisher' or 'validated'")
        if args.get("spatial") is not None and (type(args["spatial"]) is not bool or (args["spatial"] and interval != "validated")):
            errors.append(prefix+"correlation_matrix args.spatial must be true/false and needs interval 'validated' (Round 61)")
        elif interval == "validated":
            method, controls = args.get("method", "pearson"), args.get("controls") or []
            exploratory = manifest.get("exploratory", False)
            if method not in VALIDATED_VARIANT:
                errors.append(prefix+f"interval 'validated' supports method {sorted(VALIDATED_VARIANT)}")
            if (method == "partial") != bool(controls):
                errors.append(prefix+"controls are required with method 'partial' and only allowed with it")
            if not isinstance(controls, list) or any(c not in names for c in controls):
                errors.append(prefix+"controls must be a list of manifest variables")
            elif len(controls) > 1 and not exploratory:
                errors.append(prefix+"partial correlation was validated with one control; exploratory only "
                              "(docs/audits/rank_validation.md)")
            if (VALIDATED_VARIANT.get(method) == 2 and not census_vre_source(manifest)
                    and a.get("replicates") != "required" and not exploratory):
                errors.append(prefix+f"{method} intervals are validated only with ACS replicate variance: declare "
                              "replicates.source 'census_vre' or \"replicates\": \"required\"")
            if args.get("spatial_se") is not None:
                errors.append(prefix+"validated correlation intervals assume independent areas; spatial_se refused")
    _check_spatial(stage, ctx)


def _text_correlation(a, text):
    args = a.get("args") or {}
    if args.get("interval", "fisher") != "validated":
        return text
    method = args.get("method", "pearson")
    from ..correlation import VALIDATED_VARIANT
    form = ("the independent-area variance of atanh(r) plus the ACS replicate variance 4/80 sum(atanh r_r - "
            "atanh r)^2" if VALIDATED_VARIANT.get(method) == 2 else "the independent-area variance of atanh(r)")
    ctl = f" given {', '.join(args.get('controls') or [])}" if method == "partial" else ""
    return (f"{method.capitalize()} correlations{ctl} with normal intervals on the atanh scale using {form} "
            "(validated by simulation, docs/audits/rank_validation.md). The estimand is the correlation of the ACS "
            "estimates as observed (attenuated by sampling error, not corrected); areas are treated as independent, "
            "and under spatial dependence these intervals under-covered in validation."
            if not args.get("spatial") else
            "estimates as observed (attenuated by sampling error, not corrected); n is replaced by the "
            "Clifford-Richardson-Hemon effective sample size for spatially dependent areas (validated in Rounds 48 "
            "and 59).")


def _text_fit_replicate(a, text):
    args = a.get("args") or {}
    if args.get("spatial_scpc") is not None:
        model = {"ols": "OLS", "poisson": "Poisson", "binomial": "binomial"}.get(args.get("model", "ols"), args.get("model"))
        return (f"Coefficients were estimated by {model} regression on the ACS estimates as observed. Intervals and "
                "p-values are spatial-correlation-robust (SCPC, Mueller and Watson 2022): influence values projected on "
                "the leading principal components of an exponential spatial correlation, with a critical value and "
                "p-value that hold for any correlation range up to the benchmark (validated in Round 58, "
                "docs/audits/spatial_outside_validation.md). ACS replicate variance is not added (population target).")
    if args.get("model") != "negbin":
        return text
    return (f"Coefficients were estimated by negative binomial (NB2) regression with offset log({args.get('exposure')}): "
            "alpha by maximum likelihood, then a GLM with fixed alpha and HC3 standard errors (statsmodels), "
            "validated by simulation (docs/audits/manova_counts_validation.md). Normal-theory intervals and p-values "
            "use the HC3 model SE (population target: the slope on the ACS estimates as observed); ACS replicate "
            "variance and offset uncertainty are not included.")


def _text_fit_eiv(a, text):
    args = a.get("args") or {}
    sp = args.get("spatial")
    if sp is None:
        return text
    base = ("Coefficients were corrected for ACS sampling error (Fuller moment correction with replicate-estimated "
            "error covariances) with spatially robust inference, validated by simulation for up to four error-prone "
            "covariates (docs/audits/spatial_eiv_validation.md; docs/audits/glm_correction_validation.md). ")
    if sp == "clusters":
        return base+("Units were split into the eight fixed geographic clusters; each cluster's naive slopes were "
                     "corrected by the pooled within-cluster reliability matrix, and the eight corrected values give a "
                     "t(7) interval (Ibragimov-Müller). Terms constant within every cluster are absorbed and not estimable.")
    return base+("A spatial-error model (k = 6 nearest neighbours) estimated lambda, which whitened the data and the "
                 "replicate deviations before the Fuller estimator and its sandwich SE; t(n - p) intervals.")


def _check_fit_eiv(stage, ctx):
    if stage == "hypothesis":
        return
    from .schema import FORMULA_ID_COLUMNS, LEGACY_X2_MANIFESTS, manifest_hash
    from .replicates import census_vre_source
    i, a, manifest, names, ext_names, errors = (ctx[k] for k in ("i", "a", "manifest", "names", "ext_names", "errors"))
    aargs = a.get("args") or {}
    outcome_name = str(a.get("formula", "")).split("~")[0].strip()
    if stage == "after_spatial":
        eargs = a.get("args") or {}
        unknown = sorted(set(eargs) - {"model", "weights", "cv_threshold", "target", "cluster", "cluster_se", "spatial_se", "spatial_clusters", "spatial"})
        if unknown:
            errors.append(f"analyses[{i}] ({a.get('id')}): fit_eiv does not take args {unknown} (allowed: "
                          "model, weights, cv_threshold, cluster, cluster_se)")
        if "spatial" in eargs:  # Round 43 M3: Round 35 G1/G2
            if eargs["spatial"] not in ("clusters", "error"):
                errors.append(f"analyses[{i}] ({a.get('id')}): fit_eiv args.spatial must be 'clusters' (eight fixed "
                              "IM clusters, G1) or 'error' (spatial-error whitening, G2)")
            clash = sorted(k for k in ("cluster", "cluster_se", "spatial_se", "spatial_clusters", "weights") if eargs.get(k) is not None)
            if clash or str(eargs.get("model", "ols")).lower() != "ols":
                errors.append(f"analyses[{i}] ({a.get('id')}): fit_eiv args.spatial supports unweighted OLS only and "
                              f"excludes {clash or ['model wls']} (docs/audits/spatial_eiv_validation.md)")
        if eargs.get('spatial_clusters') is not None:
            errors.append(f"analyses[{i}] ({a.get('id')}): IM EIV C2 failed validation and is refused; docs/audits/im_acs_validation.md")
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

def _run_inequality(a, args, frame, level, replicates, correction, ctx):
    from ..inequality import inequality_replicate
    external = set(ctx["external"])
    fixed = [a["outcome"]] if a["outcome"] in external else []
    if fixed and a["weights"] == a["outcome"]+"_denominator":
        fixed.append(a["weights"])
    args.pop("replicate_policy", None)  # library always enforces strict completeness
    # Manifests support complete_case only; filter before aligning replicates.
    used = frame.dropna(subset=[a[k] for k in ("outcome", "rank_by", "weights")])
    result = inequality_replicate(used, a["outcome"], a["rank_by"], a["weights"],
                                replicates=replicates, fixed=fixed, level=level, **args)
    dropped = frame.loc[~frame.index.isin(used.index), "GEOID"].astype(str).tolist()
    result.diagnostics["complete_case"] = {"input_rows": len(frame), "used_rows": len(used),
                                            "dropped_geoids": dropped}
    if dropped:
        result.notes.append(f"Complete-case analysis excluded {len(dropped)} area row(s) with missing outcome, rank or weights.")
    return result


def _run_smr(a, args, frame, level, replicates, correction, ctx):
    from ..standardize import indirect_standardize
    from ..models import _replicate_matrices
    from ..results import precheck_replicates, stochastic_variables, IncompleteReplicatesError
    bands = a["population_bands"]
    input_rows = len(frame)
    original = frame
    parent = next((n for n in ctx.get("wonder_names",()) if a["observed"] in (n,n+"_numerator")),None)
    rates, counts = a.get("reference_rates"), a.get("reference_counts")
    if a.get("reference_export") is not None:
        from ..wonder_reference import resolve_reference_export
        rates, counts, _ = resolve_reference_export(a["reference_export"],a.get("period_years",1),bands)
    frame = frame.dropna(subset=[a["observed"]]+bands)
    mats, held = _replicate_matrices(frame, replicates, bands) if replicates is not None else ({}, {})
    precheck_replicates("strict", rows_held_fixed=held,
                       variables_without_replicates=[v for v in stochastic_variables(frame, bands) if v not in mats],
                       context="smr")
    reps = (np.stack([mats.get(v, np.broadcast_to(frame[v].to_numpy(float)[:, None], (len(frame), 80)))
                      for v in bands], axis=1) if mats else None)
    idx = pd.Index(frame["GEOID"].astype(str))
    observed = pd.Series(frame[a["observed"]].to_numpy(float), index=idx)
    populations = frame[bands].set_axis(idx)
    try:
        result = indirect_standardize(observed, populations, rates, reps, level,
                                      period_years=a.get("period_years",1), reference_counts=counts,
                                      negative_replicates=args.get("negative_replicates", "refuse"),
                                      reference_population_se=args.get("reference_population_se"))
        if len(frame) != input_rows:
            note = f"Complete-case analysis excluded {input_rows-len(frame)} area row(s) with missing observed counts or populations."
            result["notes"] = result["notes"].map(lambda notes: notes+[note])
        if parent:
            from ..wonder_outputs import suppression_info
            info = suppression_info(original,parent)
            if info["excluded_counties"]:
                note = f"Suppressed counties excluded: {info['suppressed_counties']}; excluded deaths bounded by {info['excluded_deaths_bounds']}. Pooled totals are complete-case only."
                result["notes"] = result["notes"].map(lambda notes: notes+[note])
                result.attrs["deviations"] = [{"kind":"wonder_suppressed","geoid":g,"detail":"Suppressed county excluded; no per-county SMR reported."} for g in info["suppressed_counties"]]
        return result
    except ValueError as exc:
        if reps is not None and "replicate" in str(exc):
            raise IncompleteReplicatesError(f"smr: {exc}") from exc
        raise


def _stat_inequality(h, res):
    result = _stat_coefficient({"term": h["statistic"]}, res)
    if not all(np.isfinite(result[k]) for k in ("estimate", "se", "p_two_sided", "ci_lower", "ci_upper")):
        raise ValueError(f"{h['statistic']} or its uncertainty is undefined; see analysis notes")
    return result


def _stat_smr(h, res):
    row = res[res["GEOID"] == str(h["geoid"])]
    if row.empty:
        raise KeyError(f"GEOID {h['geoid']} not in the SMR frame")
    r = row.iloc[0]
    if not np.isfinite(r["log_smr"]) or not np.isfinite(r["se_log_smr"]):
        raise ValueError("log SMR undefined at O=0; only the fixed-E exact interval is available")
    return {"estimate": float(r["log_smr"]), "se": float(r["se_log_smr"]), "se_basis": "se_log_smr",
            "p_two_sided": float(r["p_value"]), "ci_lower": float(np.log(r["smr_lower"])),
            "ci_upper": float(np.log(r["smr_upper"]))}


def _check_inequality(stage, ctx):
    if stage == "spatial":
        return _check_spatial(stage, ctx)
    if stage == "hypothesis":
        h, errors = ctx["h"], ctx["errors"]
        if "term" in h:
            errors.append(f"hypotheses[{ctx['i']}] ({h.get('analysis')}): inequality names a statistic only, no term")
        return
    if stage != "before_spatial":
        return
    from ..inequality import INEQUALITY_VALIDATED
    a, errors, names, external = (ctx[k] for k in ("a", "errors", "names", "ext_names"))
    prefix = f"analyses[{ctx['i']}] ({a.get('id')}): "
    args = a.get("args") or {}
    if not INEQUALITY_VALIDATED and not ctx["manifest"].get("exploratory", False):
        errors.append(prefix+"inequality failed validation; exploratory only (docs/audits/inequality_validation.md)")
    if type(args.get("higher_is_more_deprived")) is not bool:
        errors.append(prefix+"higher_is_more_deprived must be an explicit boolean")
    if args.get("target", "conservative") not in ("population", "these_areas", "conservative"):
        errors.append(prefix+"target must be population, these_areas or conservative")
    unknown = sorted(set(args)-{"higher_is_more_deprived", "target"})
    if unknown:
        errors.append(prefix+f"inequality does not take args {unknown}")
    outcome = a.get("outcome")
    for role in ("outcome", "rank_by", "weights"):
        v = a.get(role)
        allowed_external = (role == "outcome" and v in external) or (
            role == "weights" and outcome in external and v == str(outcome)+"_denominator")
        if not isinstance(v, str) or (v not in names and not allowed_external):
            errors.append(prefix+f"{role} {v!r} is not a manifest variable in this role")
    if outcome in external and args.get("target") == "these_areas":
        errors.append(prefix+"external outcome is held fixed; target these_areas omits its uncertainty")


def _check_smr(stage, ctx):
    if stage == "spatial":
        return _check_spatial(stage, ctx)
    if stage == "hypothesis":
        h, errors = ctx["h"], ctx["errors"]
        g = h.get("geoid")
        if not isinstance(g, str) or not g or (g != "all" and not (g.isascii() and g.isdigit())):
            errors.append(f"hypotheses[{ctx['i']}] ({h.get('analysis')}): smr requires geoid (one GEOID or 'all')")
        if "term" in h:
            errors.append(f"hypotheses[{ctx['i']}] ({h.get('analysis')}): smr uses geoid, not term")
        return
    if stage != "before_spatial":
        return
    from ..standardize import SMR_VALIDATED
    a, errors, names, external = (ctx[k] for k in ("a", "errors", "names", "ext_names"))
    prefix = f"analyses[{ctx['i']}] ({a.get('id')}): "
    args = a.get("args") or {}
    if not SMR_VALIDATED and not ctx["manifest"].get("exploratory", False):
        errors.append(prefix+"smr failed validation; exploratory only (docs/audits/smr_validation.md)")
    allowed = {"target", "negative_replicates", "reference_population_se"}
    if set(args)-allowed:
        errors.append(prefix+f"smr does not take args {sorted(set(args)-allowed)}")
    rpse = args.get("reference_population_se")
    if rpse is not None:
        bands_ = a.get("population_bands")
        if (a.get("reference_counts") is None or not isinstance(rpse, list) or not isinstance(bands_, list)
                or len(rpse) != len(bands_) or not all(type(v) in (int, float) and np.isfinite(v) and v >= 0 for v in rpse)):
            errors.append(prefix+"smr reference_population_se must be finite nonnegative numbers, one per band, with "
                          "literal reference_counts (Round 55)")
    if args.get("negative_replicates", "refuse") not in ("refuse", "accept", "clip"):
        errors.append(prefix+"smr negative_replicates must be 'refuse' (default for registered manifests), 'accept' or 'clip' (Round 51)")
    if args.get("target", "conservative") != "conservative":
        errors.append(prefix+"smr target must be conservative (combined Poisson and expected-count uncertainty)")
    observed = a.get("observed")
    allowed_count = isinstance(observed, str) and observed.endswith("_numerator") and observed[:-10] in external
    if not isinstance(observed, str) or (observed not in names and not allowed_count):
        errors.append(prefix+f"observed {observed!r} must be a manifest variable or external <name>_numerator")
    bands, rates = a.get("population_bands"), a.get("reference_rates")
    if not isinstance(bands, list) or not bands or not all(isinstance(v,str) and v in names for v in bands):
        errors.append(prefix+"population_bands must be a non-empty list of manifest variables")
    elif len(set(bands)) != len(bands):
        errors.append(prefix+"population_bands must not repeat a band")
    reference_export = a.get("reference_export")
    if reference_export is not None:
        if "reference_rates" in a or a.get("reference_counts") is not None:
            errors.append(prefix+"reference_export is an alternative to literal reference_rates/reference_counts, not an override")
        try:
            from ..wonder_reference import resolve_reference_export
            resolve_reference_export(reference_export,a.get("period_years",1),bands,validate_only=True)
        except (ValueError, OSError, TypeError) as exc:
            errors.append(prefix+str(exc))
    if reference_export is None and (not isinstance(rates, list) or not rates or not isinstance(bands, list) or len(rates) != len(bands)
            or not all(type(r) in (int,float) and np.isfinite(r) and r>0 for r in rates)):
        errors.append(prefix+"reference_rates must be finite positive numbers, one per population band")
    period=a.get("period_years",1)
    if type(period) is not int or period<=0:
        errors.append(prefix+"period_years must be a positive integer")
    counts=a.get("reference_counts")
    if counts is not None:
        from ..standardize import SMR_REFERENCE_VALIDATED
        if not isinstance(counts,list) or not isinstance(bands,list) or len(counts)!=len(bands) or not all(type(d) is int and d>0 for d in counts):
            errors.append(prefix+"reference_counts must be positive integers, one per band; zero reference deaths refused")
        if not SMR_REFERENCE_VALIDATED and not ctx["manifest"].get("exploratory",False):
            errors.append(prefix+"SMR reference-rate uncertainty failed or lacks validation; exploratory only")
    if reference_export is not None:
        from ..standardize import SMR_REFERENCE_VALIDATED
        if not SMR_REFERENCE_VALIDATED and not ctx["manifest"].get("exploratory",False):
            errors.append(prefix+"SMR reference-rate uncertainty failed or lacks validation; exploratory only")
    source = a.get("reference_source")
    if not isinstance(source, str) or not source.strip():
        errors.append(prefix+"reference_source must be a non-empty citation string")


def _run_segregation(a, args, frame, level, replicates, correction, ctx):
    from ..segregation import segregation_replicate, group_quarters_tracts
    gq = args.get("group_quarters")
    exclude = (group_quarters_tracts(frame, gq["gq"], gq["total"], gq.get("max_share", .5)) if gq else None)
    return segregation_replicate(frame, a["groups"], replicates, within=a["within"], level=level,
                                 bias_correction=args.get("bias_correction"),
                                 negative_replicates=args.get("negative_replicates", "refuse"),
                                 exclude_tracts=exclude)


def _stat_segregation(h, res):
    from ..segregation import segregation_test
    return segregation_test(res,h["statistic"],h["geoid"],null_value=h.get("null_value"),
                            compare_geoid=h.get("compare_geoid"),release=h.get("release"),
                            compare_release=h.get("compare_release"))


def _check_segregation(stage, ctx):
    if stage == "spatial":
        return _check_spatial(stage,ctx)
    if stage not in ("hypothesis", "before_spatial"):
        return
    from ..segregation import SEGREGATION_VALIDATED, DEFAULT_BIAS_CORRECTION, variant_validated
    from .schema import manifest_releases, release_overlap_message
    a, manifest, errors = ctx["a"], ctx["manifest"], ctx["errors"]
    args=a.get("args") or {}; groups=a.get("groups")
    if stage == "before_spatial":
        if not isinstance(groups,list) or len(groups)<2 or not all(isinstance(g,str) and g in ctx["names"] for g in groups):
            errors.append("segregation groups must be at least two distinct tract manifest variables")
        elif len(set(groups))!=len(groups):
            errors.append("segregation groups must be distinct")
        if a.get("within")!="county" or manifest.get("geography",{}).get("level")!="tract" or manifest.get("aggregation"):
            errors.append("segregation requires tract geography, within county, and no pre-aggregation; metro/CBSA unsupported")
        allowed={"bias_correction", "negative_replicates", "group_quarters"}
        if set(args)-allowed:
            errors.append(f"segregation does not take args {sorted(set(args)-allowed)}")
        gq=args.get("group_quarters")
        if gq is not None:
            share=gq.get("max_share", .5) if isinstance(gq, dict) else None
            if (not isinstance(gq, dict) or set(gq)-{"gq","total","max_share"} or gq.get("gq") not in ctx["names"]
                    or gq.get("total") not in ctx["names"] or type(share) not in (int, float) or not 0 < share <= 1):
                errors.append("segregation group_quarters must be {gq: manifest variable, total: manifest variable, "
                              "max_share: number in (0, 1]} (Round 57)")
        if args.get("negative_replicates", "refuse") not in ("refuse", "clip"):
            errors.append("segregation negative_replicates must be 'refuse' (default for registered manifests) or 'clip' (Round 51)")
        if args.get("bias_correction") is not None and type(args["bias_correction"]) is not bool:
            errors.append("segregation bias_correction must be boolean")
        overlap=release_overlap_message(manifest_releases(manifest),"segregation releases")
        if overlap:errors.append(overlap)
        return
    h=ctx["h"];stat=h.get("statistic");releases=manifest_releases(manifest)
    for key in ("geoid","compare_geoid"):
        val=h.get(key)
        if key=="geoid" or val is not None:
            if not isinstance(val,str) or len(val)!=5 or not val.isascii() or not val.isdigit():
                errors.append(f"segregation {key} must be a five-digit county GEOID")
    for key in ("term","variable"):
        if key in h:errors.append("segregation hypotheses name statistic and county, not term/variable")
    if stat in ("dissimilarity","isolation") and (not isinstance(groups,list) or len(groups)!=2):
        errors.append(f"segregation {stat} requires exactly two groups")
    contrast=h.get("compare_geoid") is not None or h.get("compare_release") is not None
    val=h.get("null_value")
    if (not contrast and val is None) or (val is not None and (type(val) not in (int,float) or not np.isfinite(val))):
        errors.append("segregation one-area test requires a finite pre-registered null_value; contrasts default to zero")
    for key in ("release","compare_release"):
        year=h.get(key)
        if year is not None and (type(year) is not int or year not in releases):
            errors.append(f"segregation {key} must name a declared release integer")
    if len(releases)>1 and h.get("release") is None:
        errors.append("segregation hypotheses over multiple releases require an explicit release selector")
    if h.get("compare_release") is not None and h.get("release") is None:
        errors.append("segregation compare_release also requires release")
    if contrast and h.get("geoid")==h.get("compare_geoid",h.get("geoid")) and h.get("release")==h.get("compare_release",h.get("release")):
        errors.append("segregation cannot compare an area/release with itself")
    if isinstance(stat,str) and stat in SEGREGATION_VALIDATED:
        corrected=args.get("bias_correction")
        if corrected is None: corrected=DEFAULT_BIAS_CORRECTION[stat]
        variant="bias_corrected" if corrected else "naive"
        passed=isinstance(groups,list) and variant_validated(stat,variant,len(groups))
        if not passed and not manifest.get("exploratory",False):
            errors.append(f"segregation {stat}/{variant}/group count failed or lacks coverage validation; exploratory only")


def _text_regression_calibration(a, text):
    if (a.get("args") or {}).get("spatial") == "clusters":
        return text.replace("standard errors (se_total, used for normal-theory intervals and p-values) by row bootstrap "
                            "re-estimating the calibration",
                            "slopes then fitted separately in eight fixed spatial clusters and averaged, with t(7) "
                            "intervals and p-values (Rounds 53/58)")
    if (a.get("args") or {}).get("se_method") != "jackknife":
        return text
    return text.replace("standard errors (se_total, used for normal-theory intervals and p-values) by row bootstrap "
                        "re-estimating the calibration",
                        "standard errors (se_total, used for t intervals with n - p df and p-values) by delete-one-area "
                        "jackknife re-estimating the calibration (Round 53)")


def _text_smr(a, text):
    policy=(a.get("args") or {}).get("negative_replicates", "refuse")
    if policy != "refuse":
        extra=(" Negative ACS band replicates were used as published (Round 51)." if policy == "accept"
               else " Negative ACS band replicates were set to zero before the expected-count refits (Round 51).")
        return _text_smr({**a, "args": {}}, text)+extra
    period=a.get("period_years",1);counts=a.get("reference_counts")
    if a.get("reference_export") is not None:
        counts = "from pinned reference export"
    if period==1 and counts is None:
        return text
    return (f"Indirect SMR is observed/expected, E=period_years*sum_b population_b*rate_b; period_years={period}, "
            f"rates per person-year. Reference: {a['reference_source']}. Pool counts, expected counts and band contributions first. "
            "Tests use log SMR with 1/O + 4/80 sum(log E_r-log E)^2"
            + (" + sum_b (E_b/E)^2/D_b for independent Poisson reference deaths. " if counts is not None else ". Reference rates are fixed. ")
            + ("Reference person-years are fixed. Shared rates induce covariance between areas; pooled band weights are squared after pooling. "
               "For internal standardization, ignoring positive study/reference covariance makes intervals conservative. "
               if counts is not None else "Reference-rate uncertainty is excluded. ")
            + "Exact Garwood limits condition on E and exclude both population and reference-rate uncertainty; O=0 has no log-Wald test. "
            "Absent ACS replicates the population component is zero, noted. Spatial dependence is excluded.")


def _text_segregation(a, text):
    from ..segregation import DEFAULT_BIAS_CORRECTION
    specified=(a.get("args") or {}).get("bias_correction")
    versions=", ".join(f"{name}: {'bias-corrected' if (DEFAULT_BIAS_CORRECTION[name] if specified is None else specified) else 'naive'}" for name in DEFAULT_BIAS_CORRECTION)
    gq=(a.get("args") or {}).get("group_quarters")
    if gq:
        text=text+(f" Tracts whose group-quarters share ({gq['gq']} / {gq['total']}) was at least "
                   f"{gq.get('max_share', .5):g} were left out (Round 57), so the indices describe the remaining tracts.")
    if (a.get("args") or {}).get("negative_replicates", "refuse") == "clip":
        text=text.replace("with no negative-count clipping", "with negative replicate counts set to zero before the refits "
                          "(Round 51; counties with a clipped count are validated only for the bias-corrected versions)")
    return text+" Chosen versions: "+versions+". Groups: "+", ".join(a["groups"])+"."


METHODS: Dict[str, MethodSpec] = {
    'fit_replicate': MethodSpec(
        'fit_replicate', ('formula',), ('coefficient', 'joint_wald', 'joint_test',
                                        'marginal_rr', 'marginal_rd', 'attributable_fraction'), _run_fit_replicate,
        replicate=True,
        external_outcome=True,
        check=_check_fit_replicate,
        format_text=_text_fit_replicate,
        text=(
            'Coefficients were estimated with {model} regression (statsmodels) on the full-sample estimates; '
            'sampling standard errors came from refitting on each of {rep_source}, Var = 4/80 sum (b_r - '
            'b)^2, combined with the model standard error as se_total = sqrt(se_model^2 + se_sampling^2). '
            'Reported standard errors, intervals and p-values use the {target_se} ({target} target: '
            '{estimand}), with normal-theory intervals. Without replicates only model standard errors are '
            'reported.',
            ['vre', 'design', 'statsmodels'],
        ),
    ),
    'fit_eiv': MethodSpec(
        'fit_eiv', ('formula',), ('coefficient',), _run_fit_eiv,
        replicate=True,
        external_outcome=True,
        check=_check_fit_eiv,
        format_text=_text_fit_eiv,
        text=(
            'Coefficients were estimated by moment-corrected least squares ({model}; Fuller 1987) with '
            'per-unit sampling-error covariances of every design column and of the outcome, including the '
            'outcome-covariate error covariance, estimated from {rep_source} (4/80 sum over replicates). '
            'Standard errors are {se_basis} (se_total, used for normal-theory intervals and p-values); naive '
            'coefficients are reported alongside. Coefficients are {estimand}.',
            ['fuller', 'vre', 'design'],
        ),
    ),
    'regression_calibration': MethodSpec(
        'regression_calibration', ('formula', 'error_covariates'), ('coefficient',), _run_regression_calibration,
        replicate=False,
        external_outcome=False,
        check=_check_regression_calibration,
        format_text=_text_regression_calibration,
        text=(
            'Covariates measured with known ACS sampling error ({cov}) were corrected by regression '
            'calibration with heteroscedastic known error variances; standard errors (se_total, used for '
            'normal-theory intervals and p-values) by row bootstrap re-estimating the calibration. '
            'Coefficients are {estimand}.',
            ['carroll'],
        ),
    ),
    'simex': MethodSpec(
        'simex', ('formula', 'error_covariates'), ('coefficient',), _run_simex,
        replicate=False,
        external_outcome=False,
        check=_check_spatial,
        text=(
            'Covariates measured with known ACS sampling error ({cov}) were corrected by '
            'simulation-extrapolation (SIMEX, quadratic extrapolation) with the measurement-error jackknife '
            'variance (se_total, used for normal-theory intervals and p-values). Coefficients are {estimand}.',
            ['simex', 'carroll'],
        ),
    ),
    'fh_regression': MethodSpec(
        'fh_regression', ('formula',), ('coefficient',), _run_fh_regression,
        replicate=False,
        external_outcome=True,
        check=_check_spatial,
        text=(
            "The outcome's known sampling variance was modelled with an area-level Fay-Herriot model (GLS "
            'coefficients, REML variance component).',
            ['fh'],
        ),
    ),
    'fay_herriot': MethodSpec(
        'fay_herriot', ('formula',), ('coefficient',), _run_fay_herriot,
        replicate=False,
        external_outcome=False,
        check=_check_spatial,
        text=(
            'Small-area estimates are Fay-Herriot EBLUPs (REML) with Prasad-Rao/Datta-Lahiri MSE.',
            ['fh'],
        ),
    ),
    'correlation_matrix': MethodSpec(
        'correlation_matrix', ('variables',), ('correlation',), _run_correlation_matrix,
        replicate=True,
        external_outcome=False,
        check=_check_correlation,
        format_text=_text_correlation,
        text=(
            'Correlations with Fisher-z intervals{rep}.',
            ['fisher', 'vre'],
        ),
    ),
    'linear_trend_test': MethodSpec(
        'linear_trend_test', ('variable', 'geoid'), ('trend_slope',), _run_linear_trend_test,
        replicate=False,
        external_outcome=False,
        check=_check_spatial,
        text=(
            'Linear trends across non-overlapping 5-year periods were tested by GLS with known sampling '
            'variances.',
            ['testing'],
        ),
    ),
    'batch_z_test': MethodSpec(
        'batch_z_test', ('variable_1', 'variable_2'), ('z_difference',), _run_batch_z_test,
        replicate=False,
        external_outcome=False,
        check=_check_spatial,
        text=(
            'Differences were tested with the Census two-sample z test, SE = MOE/1.645.',
            ['testing'],
        ),
    ),
    'inequality': MethodSpec(
        "inequality", ("outcome", "rank_by", "weights"), ("sii", "log_rii", "concentration_index"), _run_inequality,
        replicate=True,
        external_outcome=True,
        check=_check_inequality,
        default_target="conservative",
        text=(
            'Area inequality uses positive population weights and weighted ridits from least (0) to most (1) '
            'deprived, with tied blocks assigned their weighted mid-rank; {rank_direction}. SII is the WLS '
            'slope, log RII is log((a+b)/a), and concentration is 2 cov_w(y,r)/mean_w(y). Positive indices '
            'mean higher outcomes among more deprived areas; concentration has the reverse sign of the usual '
            'income-ranked convention. Independent-area HC3 SEs (delta method for log RII; '
            'convenient-regression approximation for concentration) combine with 80 ACS replicate refits, '
            'recomputing ridits, by quadrature. Target: {target}. External outcomes and their denominator '
            'weights stay fixed. Median rank CV <=15% is the validated range; above it estimates may be '
            'attenuated by rank error. These are area associations, not individual inequality or causal '
            'effects.',
            ['pamuk', 'kakwani', 'vre', 'statsmodels'],
        ),
    ),
    'segregation': MethodSpec(
        "segregation", ("groups", "within"), ("dissimilarity", "isolation", "theil_h"), _run_segregation,
        replicate=True, check=_check_segregation, default_target="these_areas", format_text=_text_segregation,
        text=(
            "Tract group counts were aggregated within counties. Dissimilarity D is half the sum of absolute "
            "group tract-share differences; isolation xPx is the group-one weighted tract group-one share; "
            "Theil H is population-weighted between-tract entropy divided by county entropy (natural logs). "
            "Declared groups are mutually exclusive and their sum defines tract population. Zero-total tracts "
            "are excluded in each refit; absent county groups make indices undefined. Sampling SE is sqrt(4/80 "
            "sum(I_r-I)^2) using 80 complete tract-count replicates, with no negative-count clipping. "
            "When selected, the fixed bias correction is I-4*(mean(I_r)-I), using the same SE and unbounded "
            "normal intervals. County contrasts use per-replicate differences; independent non-overlapping "
            "releases add variances, first area/release minus comparison. One-area tests require a registered "
            "null_value. Only the passing two-group versions are confirmatory; multigroup H and failed "
            "versions are exploratory. Counties with any tract group-count CV above .15, the validated "
            "simulation range, are exploratory only; confirmatory tests on them are refused.",
            ["duncan", "massey", "reardon", "vre"],
        ),
    ),
    'smr': MethodSpec(
        "smr", ("observed", "population_bands", "reference_rates", "reference_source"), ("log_smr",), _run_smr,
        replicate=True,
        external_outcome=True,
        check=_check_smr,
        optional=("period_years", "reference_counts", "reference_export"), format_text=_text_smr,
        required_alternatives=(("reference_rates","reference_export"),),
        default_target="conservative",
        text=(
            'Indirect SMR is observed/expected, expected=sum_b population_b*reference_rate_b; pooling sums '
            'counts and expected counts first. Fixed reference rates: {reference_source}. Exact Garwood '
            'limits condition on expected counts. Tests use log SMR against zero, with combined variance 1/O '
            '+ 4/80 sum(log E_r-log E)^2 and exponentiated normal intervals (target: {target}). Without band '
            'replicates the expected-count component is zero, explicitly noted; at O=0 only the exact fixed-E'
            ' interval is defined. External observed counts stay fixed in band refits. Reference-rate '
            'uncertainty and spatial dependence are not included.',
            ['garwood', 'breslow', 'vre'],
        ),
    ),
}

def _run_multilevel(a, args, frame, level, replicates, correction, ctx):
    """Round 75: two-level (fit_multilevel, Kenward-Roger) or three-level (Round 73) random-intercept models."""
    g = a["groups"]
    if isinstance(g, str):
        from ..multilevel import fit_multilevel
        return fit_multilevel(a["formula"], frame, g, sampling_se=True if args.get("sampling_se") else None,
                              replicates=replicates, target=args.get("target", "population"), confidence_level=level,
                              replicate_policy=args.get("replicate_policy", "flag"))
    from ..multilevel3 import fit_three_level, AUDIT
    out = fit_three_level(a["formula"], frame, list(g), level=level, share_intervals=False)
    res = _wrap_table(out, "three-level mixed model (REML)", a["formula"], "multilevel",
                      ["ACS sampling error is not included: the three-level model was validated without it (Round 73); "
                       "variance shares are descriptive (their intervals are exploratory)."],
                      {"three_level": {"groups": list(g), "shares": out["shares"], "n_top": out["n_top"],
                                       "n_middle": out["n_middle"], "validated": out["validated"], "audit": AUDIT}})
    res.confidence_level = level
    return res


def _check_multilevel(stage, ctx):
    if stage != "before_spatial":
        return
    a, errors, names = ctx["a"], ctx["errors"], ctx["names"]
    g = a.get("groups")
    args = a.get("args") or {}
    p = f"analyses ({a.get('id')}) multilevel: "
    if isinstance(g, str):
        if g not in names:
            errors.append(p+f"groups {g!r} is not a manifest variable (or state_fips/county_fips)")
        bad = set(args)-{"target", "sampling_se"}
        if bad:
            errors.append(p+f"two-level models take args target and sampling_se only, not {sorted(bad)}")
        if "sampling_se" in args and type(args["sampling_se"]) is not bool:
            errors.append(p+"sampling_se must be boolean (true uses the outcome's SE column)")
        if args.get("target", "population") not in ("population", "these_areas", "conservative"):
            errors.append(p+"target must be population, these_areas or conservative")
    elif isinstance(g, list) and len(g) == 2 and all(isinstance(x, str) for x in g) and g[0] != g[1]:
        for x in g:
            if x not in names:
                errors.append(p+f"groups {x!r} is not a manifest variable (or state_fips/county_fips)")
        if args:
            errors.append(p+f"three-level models take no args (no replicates, sampling_se or target); got {sorted(args)}")
    else:
        errors.append(p+"groups must be a grouping column or [top, middle] (two distinct columns)")


METHODS["multilevel"] = MethodSpec(
    "multilevel", ("formula", "groups"), ("coefficient",), _run_multilevel,
    replicate=True, external_outcome=True, check=_check_multilevel,
    text=(
        "Random-intercept models were fitted by REML (statsmodels MixedLM). Two-level models use Kenward-Roger "
        "small-sample intervals, with ACS sampling error from replicate refits or the outcome's known SE where "
        "declared; three-level models (top and middle grouping levels) use t(G_top - 1) Wald intervals for fixed "
        "effects and exclude ACS sampling error, as validated (Round 73). Variance shares are descriptive.",
        ["statsmodels"],
    ),
)


# ---------------------------------------------------------------- Round 76: disparity, kitagawa
def _run_disparity(a, args, frame, level, replicates, correction, ctx):
    if args.get("who_measures") or args.get("compare_years"):
        from ..inequality_monitoring import monitoring_measures
        return monitoring_measures(frame, a["groups"], a["populations"], replicates, reference=a["reference"],
                                   level=level, compare_years=args.get("compare_years"))
    from ..disparity import disparity_measures
    return disparity_measures(frame, a["groups"], a["reference"], a["populations"], replicates=replicates,
                              level=level, omitted_groups=args.get("omitted_groups"), total=args.get("total"))


def _run_kitagawa(a, args, frame, level, replicates, correction, ctx):
    from ..disparity import kitagawa_decomposition
    area, other = a["areas"]
    years = sorted(frame["Year"].unique()) if "Year" in frame.columns else [None]
    parts = [kitagawa_decomposition(frame, area, other, a["rates"], a["populations"], replicates=replicates,
                                    level=level, year=y).assign(Year=y) for y in years]
    out = pd.concat(parts, ignore_index=True)
    if years == [None]:
        out = out.drop(columns="Year")
    return out


def _release_row(res, h, mask):
    sub = res[mask]
    if "Year" in sub.columns and h.get("release") is not None:
        sub = sub[sub["Year"] == h["release"]]
    if len(sub) != 1:
        raise ValueError("the hypothesis must select exactly one result row (give release for multiple releases)")
    return sub.iloc[0]


def _refusal(row, what):
    if bool(row["validated"]):
        return {}
    reason = "; ".join(n for n in row["notes"] if n.startswith("Exploratory") or n.startswith("Uncertainty")) or \
        "outside the validated range"
    from ..disparity import AUDIT
    return {"confirmatory_refusal": f"{what}: {reason} ({AUDIT})"}


def _stat_disparity(h, res):
    from ..disparity import index_test
    stat = h["statistic"]
    measure_name = "sii" if stat == "who_sii" else stat
    mask = (res["GEOID"].astype(str) == str(h["geoid"])) & (res["measure"] == measure_name)
    if stat in ("rd", "log_rr"):
        mask &= res["group"] == h["group"]
    row = _release_row(res, h, mask)
    est_col = "change" if "change" in row.index and "estimate" not in row.index else "estimate"
    if not (np.isfinite(row[est_col]) and np.isfinite(row["se"])):
        raise ValueError(f"{stat} or its uncertainty is undefined; see analysis notes")
    basis = row["basis"] if "basis" in row.index else "replicate"
    scale = row["se_scale"] if "se_scale" in row.index else "identity"
    out = {"estimate": float(row[est_col]), "se": float(row["se"]), "se_basis": f"{basis} ({scale} scale)",
           "ci_lower": float(row["ci_lower"]), "ci_upper": float(row["ci_upper"])}
    if stat in ("rd", "log_rr"):
        out["p_two_sided"] = float(row["p_value"])
    elif stat in ("par", "par_pct", "who_sii"):
        null_v = float(h.get("null_value", 0.0))
        z = abs(out["estimate"] - null_v) / out["se"] if out["se"] > 0 else np.inf
        out["p_two_sided"] = float(2.0 * stats.norm.sf(z))
    else:
        out.update(index_test(row, h["null_value"]))
    out.update(_refusal(row, f"disparity {stat} for {h['geoid']}"))
    return out


def _stat_kitagawa(h, res):
    row = _release_row(res, h, res["component"] == h["statistic"])
    out = {"estimate": float(row["estimate"]), "se": float(row["se"]), "se_basis": row["basis"],
           "p_two_sided": float(row["p_value"]), "ci_lower": float(row["ci_lower"]), "ci_upper": float(row["ci_upper"])}
    out.update(_refusal(row, f"kitagawa {h['statistic']}"))
    return out


def _hyp_release(ctx, label):
    from .schema import manifest_releases
    h, errors = ctx["h"], ctx["errors"]
    releases = manifest_releases(ctx["manifest"])
    year = h.get("release")
    if year is not None and (type(year) is not int or year not in releases):
        errors.append(f"{label} release must name a declared release integer")
    if len(releases) > 1 and year is None:
        errors.append(f"{label} hypotheses over multiple releases require an explicit release selector")


def _check_var_list(a, key, names, errors, label, n=None):
    v = a.get(key)
    if not isinstance(v, list) or len(v) < 2 or not all(isinstance(x, str) and x in names for x in v) \
            or len(set(v)) != len(v):
        errors.append(f"{label}: {key} must be a list of at least two distinct manifest variables")
        return False
    if n is not None and len(v) != n:
        errors.append(f"{label}: {key} must have one entry per group/stratum, in the same order")
        return False
    return True


def _check_disparity(stage, ctx):
    label = f"analyses ({ctx['a'].get('id')}) disparity"
    if stage == "before_spatial":
        a, errors, names = ctx["a"], ctx["errors"], ctx["names"]
        ok = _check_var_list(a, "groups", names, errors, label)
        args = a.get("args") or {}
        if ok:
            _check_var_list(a, "populations", names, errors, label, len(a["groups"]))
            allow_best = bool(args.get("who_measures") or args.get("compare_years"))
            if a.get("reference") not in a["groups"] and not (allow_best and a.get("reference") == "best"):
                errors.append(f"{label}: reference must be one of the groups, declared in advance")
        bad = set(args)-{"omitted_groups", "total", "who_measures", "compare_years"}
        if bad:
            errors.append(f"{label}: takes args omitted_groups, total, who_measures and compare_years only, not {sorted(bad)}")
        og = args.get("omitted_groups")
        if og is not None and (not isinstance(og, list) or not all(isinstance(x, str) for x in og)):
            errors.append(f"{label}: omitted_groups must be a list of group names")
        if args.get("total") is not None and args["total"] not in names:
            errors.append(f"{label}: total must be a manifest variable (the universe population)")
        if ctx["manifest"].get("geography", {}).get("level") not in (None, "county", "state", "tract", "place", "zcta",
                                                                      "puma", "county_subdivision", "cbsa"):
            errors.append(f"{label}: unsupported geography level")
        return
    if stage != "hypothesis":
        return
    h, errors = ctx["h"], ctx["errors"]
    a = ctx["a"]; stat = h.get("statistic")
    if not isinstance(h.get("geoid"), str):
        errors.append(f"{label}: hypotheses need a geoid (string)")
    if stat in ("rd", "log_rr"):
        if h.get("group") not in (a.get("groups") or []) or h.get("group") == a.get("reference"):
            errors.append(f"{label}: {stat} hypotheses name a non-reference group from the analysis")
        if h.get("null_value", 0) != 0:
            errors.append(f"{label}: {stat} is tested against zero (no difference)")
    elif stat in ("par", "par_pct", "who_sii"):
        if not ((a.get("args") or {}).get("who_measures") or (a.get("args") or {}).get("compare_years")):
            errors.append(f"{label}: {stat} requires args.who_measures=true or args.compare_years")
        if "group" in h:
            errors.append(f"{label}: {stat} summarises all groups; it takes no group")
    else:
        nv = h.get("null_value")
        if type(nv) not in (int, float) or not np.isfinite(nv) or nv <= 0:
            errors.append(f"{label}: {stat} hypotheses need a pre-registered positive null_value (tested on the log scale)")
        if "group" in h:
            errors.append(f"{label}: {stat} summarises all groups; it takes no group")
    _hyp_release(ctx, label)


def _check_kitagawa(stage, ctx):
    label = f"analyses ({ctx['a'].get('id')}) kitagawa"
    if stage == "before_spatial":
        a, errors, names = ctx["a"], ctx["errors"], ctx["names"]
        if _check_var_list(a, "rates", names, errors, label):
            _check_var_list(a, "populations", names, errors, label, len(a["rates"]))
        ar = a.get("areas")
        if not isinstance(ar, list) or len(ar) != 2 or not all(isinstance(x, str) for x in ar) or ar[0] == ar[1]:
            errors.append(f"{label}: areas must be [area, comparison area], two distinct GEOID strings")
        if a.get("args"):
            errors.append(f"{label}: takes no args")
        return
    if stage == "hypothesis":
        if "geoid" in ctx["h"] or "group" in ctx["h"]:
            ctx["errors"].append(f"{label}: the areas are fixed by the analysis; hypotheses name a component only")
        if ctx["h"].get("null_value", 0) != 0:
            ctx["errors"].append(f"{label}: components are tested against zero")
        _hyp_release(ctx, label)


METHODS["disparity"] = MethodSpec(
    "disparity", ("groups", "populations", "reference"),
    ("rd", "log_rr", "idisp", "bgv", "theil", "mld", "par", "par_pct", "who_sii"),
    _run_disparity, replicate=True, check=_check_disparity, default_target="these_areas",
    text=(
        "Between-group disparities compare mutually exclusive population groups within each area against a "
        "reference group declared in advance: rate difference and log rate ratio per group, Pearcy-Keppel Index of "
        "Disparity, population-weighted between-group variance, and Theil and mean log deviation over the declared "
        "groups (absolute and relative measures together). Sampling SEs are sqrt(4/80 sum(theta_r - theta)^2) from "
        "80 replicate refits on the identity scale (differences, log ratios) or the log scale (indices), with normal "
        "intervals back-transformed. Validated (Round 76): differences and the Index of Disparity up to a largest "
        "group-rate CV of .50; log ratios, between-group variance, Theil and MLD up to .30; two to six groups. "
        "Index measures are tested against pre-registered positive values on the log scale.",
        ["harper_lynch", "pearcy_keppel", "vre"],
    ),
)

METHODS["kitagawa"] = MethodSpec(
    "kitagawa", ("rates", "populations", "areas"), ("crude_difference", "rate_effect", "composition_effect"),
    _run_kitagawa, replicate=True, check=_check_kitagawa, default_target="these_areas",
    text=(
        "The difference in crude rates between the two declared areas was split into a rate effect and a "
        "composition effect across strata with symmetric (Kitagawa) weights; the two sum to the crude difference. "
        "SEs come from 80 replicate refits of each component, with normal intervals; validated (Round 76) up to "
        "a largest stratum-rate CV of .50.",
        ["kitagawa", "vre"],
    ),
)


# ---------------------------------------------------------------- Round 104: marginal, estimate_effect, spatial_scan, stratified
def _stat_marginal(h, res):
    m = (getattr(res, "diagnostics", None) or {}).get("marginal")
    if not m:
        raise ValueError("marginal statistics require args.marginal on fit_replicate")
    stat = h["statistic"]
    key = {"marginal_rr": "rr", "marginal_rd": "rd", "attributable_fraction": "af"}[stat]
    part = m[key]
    est = float(part["estimate"]); lo = float(part["lower"]); hi = float(part["upper"])
    se = float(part.get("se", (hi - lo) / (2.0 * stats.norm.ppf(0.5 + getattr(res, "confidence_level", 0.90) / 2.0))))
    null_v = float(h.get("null_value", 1.0 if stat == "marginal_rr" else 0.0))
    if stat == "marginal_rr":
        se_log = (np.log(hi) - np.log(lo)) / (2.0 * stats.norm.ppf(0.95)) if lo > 0 and hi > 0 else np.nan
        z = abs(np.log(est) - np.log(null_v)) / se_log if np.isfinite(se_log) and se_log > 0 else np.inf
    else:
        z = abs(est - null_v) / se if se > 0 else np.inf
    out = {"estimate": est, "se": se, "se_basis": "g-computation HC3 delta", "ci_lower": lo, "ci_upper": hi,
           "p_two_sided": float(2.0 * stats.norm.sf(z))}
    if not m.get("validated", True):
        out["confirmatory_refusal"] = f"marginal {stat} was not validated"
    return out



from census.manifest.methods_epi import (  # noqa: E402, F401
    _check_estimate_effect,
    _check_spatial_scan,
    _check_stratified,
    _run_estimate_effect,
    _run_spatial_scan,
    _run_stratified,
    _stat_estimate_effect,
    _stat_spatial_scan,
    _stat_stratified,
)

METHODS["estimate_effect"] = MethodSpec(
    "estimate_effect", ("kind", "outcome"), ("effect",), _run_estimate_effect,
    replicate=True, external_outcome=True, check=_check_estimate_effect,
    text=(
        "Causal effect estimation followed the pre-registered causal question and DAG adjustment checks (Round 89), "
        "using validated treatment-effect (AIPW/IPW/RA with positivity diagnostics and overlap/truncated weights), "
        "matching (bias-corrected nearest-neighbour ATE/ATT, CEM or caliper), 2SLS with Anderson-Rubin intervals, "
        "or mediation estimators (Rounds 41, 47, 90, 99, 104).",
        ["hernan_robins2020", "abadie_imbens2006"],
    ),
)

METHODS["spatial_scan"] = MethodSpec(
    "spatial_scan", ("cases",), ("primary_rr",), _run_spatial_scan,
    external_outcome=True, check=_check_spatial_scan, required_alternatives=(("population", "expected"),),
    text=(
        "County cluster detection used the pre-specified Kulldorff Poisson spatial scan (50% maximum window share, "
        "999 Monte Carlo replicates; Round 81) on exact denominators, with any WONDER-suppressed counties excluded "
        "under the declared rule.",
        ["kulldorff1997"],
    ),
)

METHODS["stratified"] = MethodSpec(
    "stratified", ("stratum", "cases_exposed", "total_exposed", "cases_unexposed", "total_unexposed"),
    ("mh_rr", "mh_or", "mh_rd", "mh_irr", "reri", "homogeneity"), _run_stratified,
    external_outcome=True, check=_check_stratified,
    text=(
        "Stratified count tables were pooled with Mantel-Haenszel risk/odds/rate ratios and risk differences, "
        "Breslow-Day-Tarone homogeneity tests, and additive interaction (RERI) (Round 83).",
        ["mantel_haenszel1959", "breslow"],
    ),
)


def _run_designation(a, args, frame, level, replicates, correction, ctx):
    from ..designation import designation_accuracy
    rule = str(args.get("rule", "prob80"))
    col = a["outcome"]
    se_col = args.get("se_col") or (f"{col}_se" if f"{col}_se" in frame.columns else None)
    n_col = args.get("n_col")
    res = designation_accuracy(frame, col, float(a["threshold"]), se_col=se_col, n_col=n_col,
                               covariates=args.get("covariates") or (), percent=args.get("percent"),
                               rules=(rule,), ppv_intervals=True,
                               ppv_bootstrap=int(args.get("ppv_bootstrap", 150)))
    res["selected_rule"] = rule
    return res


def _stat_designation(h, res):
    rule = res.get("selected_rule", "prob80")
    row = res["rules"].set_index("rule").loc[rule]
    est = float(row["ppv"])
    lo = float(row.get("ppv_lower", float("nan")))
    hi = float(row.get("ppv_upper", float("nan")))
    se = (hi - lo) / (2.0 * stats.norm.ppf(0.95)) if np.isfinite(lo) and np.isfinite(hi) else float("nan")
    null_v = float(h.get("null_value", 0.5))
    z = abs(est - null_v) / se if np.isfinite(se) and se > 0 else float("nan")
    out = {"estimate": est, "se": se, "se_basis": f"FH parametric bootstrap PPV ({rule})",
           "ci_lower": lo, "ci_upper": hi,
           "p_two_sided": float(2.0 * stats.norm.sf(z)) if np.isfinite(z) else float("nan")}
    if not bool(row.get("ppv_validated", False)):
        out["confirmatory_refusal"] = f"designation PPV interval for rule={rule!r} is exploratory (validated for 'prob80' and 'point')"
    return out


def _check_designation(stage, ctx):
    a, errors = ctx["a"], ctx["errors"]
    label = f"analyses ({a.get('id')}) designation"
    if stage == "before_spatial":
        names = ctx["names"]
        ext_names = ctx.get("ext_names") or ()
        out_v = a.get("outcome")
        out_ok = isinstance(out_v, str) and (
            out_v in names or out_v in ext_names or (out_v.endswith("_numerator") and out_v[:-10] in ext_names)
        )
        if not out_ok:
            errors.append(f"{label}: outcome {out_v!r} is not a manifest variable")
        args = a.get("args") or {}
        bad = set(args) - {"covariates", "rule", "percent", "ppv_bootstrap", "se_col", "n_col"}
        if bad:
            errors.append(f"{label}: unsupported args {sorted(bad)}")
        rule = args.get("rule", "prob80")
        if rule not in ("point", "lower", "prob50", "prob80"):
            errors.append(f"{label}: rule must be one of point, lower, prob50, prob80")
        if not ctx.get("exploratory") and rule not in ("prob80", "point", "lower"):
            errors.append(f"{label}: confirmatory designation requires rule 'prob80', 'point', or 'lower' (Rounds 107/112)")
        for cov in args.get("covariates") or ():
            if cov not in names:
                errors.append(f"{label}: covariate {cov!r} is not a manifest variable")


def _run_agreement(a, args, frame, level, replicates, correction, ctx):
    from ..agreement import check_agreement
    return check_agreement(frame, a["first"], a["second"], level=level)


def _stat_agreement(h, res):
    stat = h["statistic"]
    m = res[stat]
    est = float(m["estimate"])
    lo = float(m["lower"])
    hi = float(m["upper"])
    se = float(m.get("se", (hi - lo) / (2.0 * stats.norm.ppf(0.95))))
    null_v = float(h.get("null_value", 0.0))
    z = abs(est - null_v) / se if np.isfinite(se) and se > 0 else float("nan")
    out = {"estimate": est, "se": se, "se_basis": f"agreement ({stat})",
           "ci_lower": lo, "ci_upper": hi,
           "p_two_sided": float(2.0 * stats.norm.sf(z)) if np.isfinite(z) else float("nan")}
    if not bool(m.get("validated", True)):
        out["confirmatory_refusal"] = f"agreement statistic {stat!r} is exploratory"
    return out


def _check_agreement(stage, ctx):
    a, errors = ctx["a"], ctx["errors"]
    label = f"analyses ({a.get('id')}) agreement"
    if stage == "before_spatial":
        names = ctx["names"]
        ext_names = ctx.get("ext_names") or ()
        for k in ("first", "second"):
            v = a.get(k)
            ok = isinstance(v, str) and (
                v in names or v in ext_names
                or (v.endswith("_numerator") and v[:-10] in ext_names)
                or (v.endswith("_denominator") and v[:-12] in ext_names)
            )
            if not ok:
                errors.append(f"{label}: {k} {v!r} is not a manifest variable")
        args = a.get("args") or {}
        if args:
            errors.append(f"{label}: takes no args, got {sorted(args)}")


METHODS["designation"] = MethodSpec(
    "designation", ("outcome", "threshold"), ("ppv",), _run_designation,
    check=_check_designation,
    text=(
        "Area threshold designation probabilities used arcsine Fay-Herriot posterior probabilities (Round 85), with "
        "positive predictive value (PPV) predictive intervals from the validated Round 107 FH parametric bootstrap "
        "(rules 'prob80' and 'point').",
        ["fay_herriot1979"],
    ),
)

METHODS["agreement"] = MethodSpec(
    "agreement", ("first", "second"), ("bias", "ccc", "kappa_quintiles"), _run_agreement,
    external_outcome=True, check=_check_agreement,
    text=(
        "Source-to-source agreement reported mean bias, observed Bland-Altman limits (Round 48), quintile weighted "
        "kappa (Round 37), and observed Lin's concordance correlation coefficient with delete-one-area Fisher-z "
        "jackknife intervals (Round 106).",
        ["lin1989", "bland_altman1986"],
    ),
)


def _run_rdd(a, args, frame, level, replicates, correction, ctx):
    from ..rdd import regression_discontinuity
    return regression_discontinuity(
        frame, a["outcome"], a["running"], float(a["cutoff"]),
        treatment=args.get("treatment"), weight=args.get("weight"),
        replicate_prefix=args.get("replicate_prefix"), bandwidth=args.get("bandwidth"),
        covariates=args.get("covariates") or (), placebo_cutoffs=args.get("placebo_cutoffs") or (),
        level=level,
    )


def _stat_rdd(h, res):
    est = float(res["estimate"])
    se = float(res["se"])
    lo = float(res["lower"])
    hi = float(res["upper"])
    null_v = float(h.get("null_value", 0.0))
    z = abs(est - null_v) / se if np.isfinite(se) and se > 0 else float("nan")
    out = {"estimate": est, "se": se, "se_basis": f"RDD robust bias-corrected ({res.get('variance', 'hc')})",
           "ci_lower": lo, "ci_upper": hi,
           "p_two_sided": float(2.0 * stats.norm.sf(z)) if np.isfinite(z) else float("nan")}
    if not bool(res.get("validated", False)):
        out["confirmatory_refusal"] = "RDD configuration is exploratory (use automatic CCT CER bandwidth for continuous or survey replicates for discrete)"
    return out


def _check_rdd(stage, ctx):
    a, errors = ctx["a"], ctx["errors"]
    label = f"analyses ({a.get('id')}) rdd"
    if stage == "before_spatial":
        names = ctx["names"]
        for k in ("outcome", "running"):
            if a.get(k) not in names:
                errors.append(f"{label}: {k} {a.get(k)!r} is not a manifest variable")
        args = a.get("args") or {}
        bad = set(args) - {"treatment", "weight", "replicate_prefix", "bandwidth", "covariates", "placebo_cutoffs"}
        if bad:
            errors.append(f"{label}: unsupported args {sorted(bad)}")
        if not ctx.get("exploratory") and args.get("bandwidth") is not None:
            errors.append(f"{label}: confirmatory RDD requires automatic bandwidth (no custom args.bandwidth)")


def _run_disease_map(a, args, frame, level, replicates, correction, ctx):
    from ..disease_mapping import disease_map
    edges = args.get("edges")
    bridges = []
    if edges is None:
        if ctx.get("edges") is not None:
            edges = ctx["edges"]
        elif "GEOID" in frame.columns:
            import geopandas as gpd
            from ..workflows_geo import _bridge_components, _weights_for, _with_boundaries
            geoids = frame["GEOID"].astype(str)
            geo_level = ("county" if (geoids.str.len() == 5).all()
                         else ("tract" if (geoids.str.len() == 11).all() else None))
            if geo_level is not None:
                year = int(frame["Year"].iloc[0]) if "Year" in frame.columns else 2022
                gdf_joined = _with_boundaries(frame[["GEOID"]].copy(), geo_level, year)
                gdf_aligned = gdf_joined.set_index("GEOID").loc[geoids].reset_index()
                gdf_aligned = gpd.GeoDataFrame(gdf_aligned, geometry="geometry", crs=gdf_joined.crs)
                _, w = _weights_for(gdf_aligned, "queen")
                pos = {g: k_ for k_, g in enumerate(w.id_order)}
                edges = sorted({tuple(sorted((pos[u], pos[v]))) for u, nb in w.neighbors.items() for v in nb})
                edges, bridges = _bridge_components(gdf_aligned, edges)
        if edges is None:
            raise ValueError("disease_map requires neighbour edges (args.edges or spatial boundary context)")
    res = disease_map(
        frame, a["observed"], a["expected"], edges=edges,
        covariates=args.get("covariates") or (), threshold=float(args.get("threshold", 1.2)),
        method=str(args.get("method", "B3")),
    )
    if bridges:
        res.setdefault("notes", []).append(
            f"The contiguity graph had separate parts; {len(bridges)} bridge edge(s) join each part to its nearest area: {bridges}."
        )
    return res


def _stat_disease_map(h, res):
    geoid = str(h.get("geoid") or h.get("area") or "")
    tbl = res["table"]
    row = tbl[tbl["GEOID"].astype(str) == geoid]
    if row.empty:
        raise KeyError(f"disease_map: GEOID {geoid!r} not in result table")
    r = row.iloc[0]
    est = float(r["relative_risk"])
    lo = float(r["ci_lower"])
    hi = float(r["ci_upper"])
    se_log = (np.log(hi) - np.log(lo)) / (2.0 * stats.norm.ppf(0.95)) if lo > 0 and hi > 0 else float("nan")
    null_v = float(h.get("null_value", 1.0))
    z = abs(np.log(est) - np.log(null_v)) / se_log if np.isfinite(se_log) and se_log > 0 else float("nan")
    out = {"estimate": est, "se": se_log, "se_basis": f"BYM2 {res.get('method', 'B3')} log-RR",
           "ci_lower": lo, "ci_upper": hi,
           "p_two_sided": float(2.0 * stats.norm.sf(z)) if np.isfinite(z) else float("nan"),
           "p_exceed": float(r["p_exceed"])}
    if not bool(res.get("validated", False)):
        out["confirmatory_refusal"] = "disease_map relative-risk intervals are exploratory (requires method='B3', median E >= 30, no suppressed counts)"
    return out


def _check_disease_map(stage, ctx):
    a, errors = ctx["a"], ctx["errors"]
    label = f"analyses ({a.get('id')}) disease_map"
    if stage == "before_spatial":
        names = ctx["names"]
        ext_names = ctx.get("ext_names") or ()
        obs = a.get("observed")
        obs_ok = isinstance(obs, str) and (
            obs in names or obs in ext_names or (obs.endswith("_numerator") and obs[:-10] in ext_names)
        )
        if not obs_ok:
            errors.append(f"{label}: observed {obs!r} is not a manifest variable")
        exp = a.get("expected")
        if exp not in names:
            errors.append(f"{label}: expected {exp!r} is not a manifest variable")
        args = a.get("args") or {}
        bad = set(args) - {"covariates", "threshold", "method", "edges"}
        if bad:
            errors.append(f"{label}: unsupported args {sorted(bad)}")
        method = str(args.get("method", "B3"))
        if method not in ("B1", "B2", "B3"):
            errors.append(f"{label}: method must be one of B1, B2, B3")
        if not ctx.get("exploratory") and method != "B3":
            errors.append(f"{label}: confirmatory disease_map requires args.method='B3' (Round 104)")
    elif stage == "hypothesis":
        h = ctx["h"]
        if not (h.get("geoid") or h.get("area")):
            errors.append(f"{label}: relative_risk hypothesis requires geoid")


METHODS["rdd"] = MethodSpec(
    "rdd", ("outcome", "running", "cutoff"), ("jump",), _run_rdd,
    check=_check_rdd,
    text=(
        "Regression discontinuity used robust bias-corrected local-quadratic estimation with automatic CCT CER "
        "bandwidth for continuous running variables (Round 105) or survey replicate weights for discrete running "
        "variables (Round 98).",
        ["calonico2014", "imbens_kalyanaraman2012"],
    ),
)

METHODS["disease_map"] = MethodSpec(
    "disease_map", ("observed", "expected"), ("relative_risk",), _run_disease_map,
    external_outcome=True, check=_check_disease_map,
    text=(
        "Count-scale spatial disease mapping used the BYM2 Poisson model with Riebler et al. PC prior and log-grid "
        "Jacobian (method B3, validated for median expected count >= 30 without suppressed counts; Rounds 96, 104).",
        ["riebler2016", "moraga2023"],
    ),
)


def _run_joinpoint(a, args, frame, level, replicates, correction, ctx):
    from ..joinpoint import joinpoint
    yr_col = a["year"]
    f = frame.sort_values(yr_col)
    years = pd.to_numeric(f[yr_col]).astype(int).tolist()
    kw = dict(max_joinpoints=int(args.get("max_joinpoints", 3)),
              permutations=int(args.get("permutations", 499)),
              bootstrap=int(args.get("bootstrap", 200)),
              level=level, product=str(args.get("product", "annual")))
    if "counts" in a and "population" in a:
        return joinpoint(years, counts=f[a["counts"]].to_numpy(float),
                         population=f[a["population"]].to_numpy(float), **kw)
    r_col = a["rates"]
    se_col = args.get("se_col") or f"{r_col}_se"
    return joinpoint(years, rates=f[r_col].to_numpy(float), se=f[se_col].to_numpy(float), **kw)


def _stat_joinpoint(h, res):
    stat = h["statistic"]
    if stat == "n_joinpoints":
        k = int(res["n_joinpoints"])
        pvals = res.get("permutation_p") or []
        p_val = float(pvals[0]) if pvals else float("nan")
        out = {"estimate": float(k), "se": float("nan"), "se_basis": "Kim et al. permutation test",
               "ci_lower": float("nan"), "ci_upper": float("nan"), "p_two_sided": p_val}
        if not bool(res.get("validated", {}).get("selection", False)):
            out["confirmatory_refusal"] = "joinpoint selection outside validated range (15+ annual points, 50+ events/year)"
        return out
    bt = res["aapc_bootstrap_t"]
    est = float(bt["aapc"]); lo = float(bt["lower"]); hi = float(bt["upper"])
    se = (hi - lo) / (2.0 * stats.norm.ppf(0.95)) if np.isfinite(lo) and np.isfinite(hi) else float("nan")
    null_v = float(h.get("null_value", 0.0))
    z = abs(est - null_v) / se if np.isfinite(se) and se > 0 else float("nan")
    out = {"estimate": est, "se": se, "se_basis": "Joinpoint AAPC bootstrap-t (Round 109)",
           "ci_lower": lo, "ci_upper": hi,
           "p_two_sided": float(2.0 * stats.norm.sf(z)) if np.isfinite(z) else float("nan")}
    if not bool(bt.get("validated", False)):
        out["confirmatory_refusal"] = "joinpoint AAPC bootstrap-t outside validated range (15+ points, 200+ events/year, k <= 1)"
    return out


def _check_joinpoint(stage, ctx):
    a, errors = ctx["a"], ctx["errors"]
    label = f"analyses ({a.get('id')}) joinpoint"
    if stage == "before_spatial":
        names = ctx["names"]
        if a.get("year") not in names:
            errors.append(f"{label}: year {a.get('year')!r} is not a manifest variable")
        has_cp = ("counts" in a and "population" in a)
        has_r = ("rates" in a)
        if not (has_cp or has_r):
            errors.append(f"{label}: requires (counts, population) or rates")
        args = a.get("args") or {}
        bad = set(args) - {"max_joinpoints", "permutations", "bootstrap", "product", "se_col"}
        if bad:
            errors.append(f"{label}: unsupported args {sorted(bad)}")


def _run_demography(a, args, frame, level, replicates, correction, ctx):
    from .. import demography_core as dc
    f = frame.sort_values(a["age_start"])
    ages = pd.to_numeric(f[a["age_start"]]).to_numpy(float)
    deaths = pd.to_numeric(f[a["deaths"]]).to_numpy(float)
    pop = pd.to_numeric(f[a["population"]]).to_numpy(float)
    lt = dc.life_table(ages, deaths, pop, level=level)
    return dict(ages=ages.tolist(), e=lt["e"].tolist(), se_e=lt["se_e"].tolist(),
                lower=lt["lower"].tolist(), upper=lt["upper"].tolist(),
                total_pop=float(np.sum(pop)), validated=bool(np.sum(pop) >= 50000))


def _stat_demography(h, res):
    stat = h["statistic"]
    ages = res["ages"]
    idx = 0 if stat == "e0" else (ages.index(65.0) if 65.0 in ages else -1)
    if idx < 0:
        raise KeyError("demography: age_start=65 not found for e65")
    est = float(res["e"][idx]); se = float(res["se_e"][idx])
    lo = float(res["lower"][idx]); hi = float(res["upper"][idx])
    null_v = float(h.get("null_value", 0.0))
    z = abs(est - null_v) / se if np.isfinite(se) and se > 0 else float("nan")
    out = {"estimate": est, "se": se, "se_basis": "Chiang II life table SE",
           "ci_lower": lo, "ci_upper": hi,
           "p_two_sided": float(2.0 * stats.norm.sf(z)) if np.isfinite(z) else float("nan")}
    if not bool(res.get("validated", False)):
        out["confirmatory_refusal"] = "life table person-years below validated threshold (50,000)"
    return out


def _check_demography(stage, ctx):
    a, errors = ctx["a"], ctx["errors"]
    label = f"analyses ({a.get('id')}) demography"
    if stage == "before_spatial":
        names = ctx["names"]
        for k in ("age_start", "deaths", "population"):
            if a.get(k) not in names:
                errors.append(f"{label}: {k} {a.get(k)!r} is not a manifest variable")
        args = a.get("args") or {}
        if args:
            errors.append(f"{label}: takes no args, got {sorted(args)}")


METHODS["joinpoint"] = MethodSpec(
    "joinpoint", ("year",), ("n_joinpoints", "aapc"), _run_joinpoint,
    external_outcome=True, check=_check_joinpoint,
    text=(
        "Annual rate trend changes used log-linear joinpoint regression with Kim et al. permutation selection (Round 77) "
        "and parametric residual bootstrap-t AAPC intervals re-estimating joinpoint locations (Round 109).",
        ["kim2000"],
    ),
)

METHODS["demography"] = MethodSpec(
    "demography", ("age_start", "deaths", "population"), ("e0", "e65"), _run_demography,
    external_outcome=True, check=_check_demography,
    text=(
        "Abridged life tables and life-expectancy intervals (e0, e65) used Chiang II standard errors (validated for "
        "50,000+ person-years; Round 101).",
        ["chiang1984"],
    ),
)


def _run_did(a, args, frame, level, replicates, correction, ctx):
    design = str(args.get("design", "two_group"))
    period = str(args.get("period", "Year"))
    unit = str(args.get("unit", "GEOID"))
    product = str(args.get("product", "5-year"))
    if design == "staggered":
        from ..staggered import staggered_did
        return dict(design="staggered",
                    result=staggered_did(frame, a["outcome"], a["first_treated"], period=period, unit=unit,
                                         se=args.get("se"), method=str(args.get("method", "sun_abraham")),
                                         product=product))
    if design == "triple":
        from ..matching import triple_difference
        return dict(design="triple",
                    result=triple_difference(frame, a["outcome"], unit, args["group"], args["affected_group"],
                                             period, a["treated"], int(a["treatment_period"])))
    if design == "msm":
        from ..msm import marginal_structural_model
        return dict(design="msm",
                    result=marginal_structural_model(frame, a["outcome"], a["first_treated"],
                                                     args.get("time_varying_confounders") or [],
                                                     period=period, unit=unit, product=product,
                                                     method=str(args.get("method", "gformula"))))
    from ..did import difference_in_differences
    res = difference_in_differences(frame, a["outcome"], a["treated"], int(a["treatment_period"]),
                                    period=period, se=args.get("se"), design=design,
                                    reference=args.get("reference"), replicates=replicates,
                                    target=str(args.get("target", "population")),
                                    period_years=1 if product in ("1-year", "annual") else 5)
    return dict(design=design, result=res.to_dict())


def _stat_did(h, res):
    design = res["design"]
    r = res["result"]
    if design == "staggered":
        o = r["overall"]
        est, lo, hi = float(o["estimate"]), float(o["ci_lower"]), float(o["ci_upper"])
        se = float(o.get("se", (hi - lo) / (2.0 * stats.norm.ppf(0.95))))
        valid = bool(r.get("validated", False))
        basis = f"staggered DiD ({r.get('method', 'sun_abraham')})"
    elif design == "triple":
        e = r["effect"]
        est, lo, hi, se = float(e["estimate"]), float(e["lower"]), float(e["upper"]), float(e["se"])
        valid = bool(r.get("validated", False))
        basis = "triple difference (clustered)"
    elif design == "msm":
        dur = int(h.get("duration", 1))
        e = next(x for x in r["effects"] if int(x["duration"]) == dur)
        est, lo, hi, se = float(e["estimate"]), float(e["lower"]), float(e["upper"]), float(e["se"])
        valid = bool(r.get("validated", False))
        basis = f"MSM ({r.get('method', 'gformula_jackknife')}, d={dur})"
    else:
        coefs = r.get("coefficients") or []
        eff_rows = [c for c in coefs if c.get("role") == "effect"] or [c for c in coefs if c.get("term") == "did"]
        tbl = r.get("table") or []
        row = eff_rows[0] if eff_rows else (tbl[0] if tbl else r)
        est = float(row.get("estimate", float("nan")))
        se_col = r.get("interval_se_column", "se_total")
        se_val = row.get(se_col) if row.get(se_col) is not None else row.get("se_total", row.get("se_model", row.get("se", float("nan"))))
        se = float(se_val) if se_val is not None else float("nan")
        lo = float(row.get("ci_lower", row.get("lower", float("nan"))))
        hi = float(row.get("ci_upper", row.get("upper", float("nan"))))
        valid = True
        basis = f"DiD ({design})"
    null_v = float(h.get("null_value", 0.0))
    z = abs(est - null_v) / se if np.isfinite(se) and se > 0 else float("nan")
    out = {"estimate": est, "se": se, "se_basis": basis, "ci_lower": lo, "ci_upper": hi,
           "p_two_sided": float(2.0 * stats.norm.sf(z)) if np.isfinite(z) else float("nan")}
    if not valid:
        out["confirmatory_refusal"] = f"difference_in_differences design={design!r} is exploratory"
    return out


def _check_did(stage, ctx):
    a, errors = ctx["a"], ctx["errors"]
    label = f"analyses ({a.get('id')}) difference_in_differences"
    if stage == "before_spatial":
        names = ctx["names"]
        ext_names = ctx.get("ext_names") or ()
        out_v = a.get("outcome")
        out_ok = isinstance(out_v, str) and (
            out_v in names or out_v in ext_names or (out_v.endswith("_numerator") and out_v[:-10] in ext_names)
        )
        if not out_ok:
            errors.append(f"{label}: outcome {out_v!r} is not a manifest variable")
        args = a.get("args") or {}
        design = str(args.get("design", "two_group"))
        if design not in ("two_group", "event", "staggered", "triple", "msm"):
            errors.append(f"{label}: design must be one of two_group, event, staggered, triple, msm")
        if design == "msm" and not ctx.get("exploratory") and str(args.get("method", "gformula")) != "gformula":
            errors.append(f"{label}: confirmatory design='msm' requires args.method='gformula' (Rounds 106/108)")


def _run_its(a, args, frame, level, replicates, correction, ctx):
    from ..missing_censored_its import interrupted_series
    yr_col = a["year"]
    f = frame.sort_values(yr_col)
    years = pd.to_numeric(f[yr_col]).astype(int).tolist()
    if any(b - x != 1 for x, b in zip(years, years[1:])):
        raise ValueError("interrupted_series requires consecutive annual years (overlapping 5-year series refused)")
    idx = years.index(int(a["interruption_year"]))
    return interrupted_series(f[a["outcome"]].to_numpy(float), idx,
                              method=str(args.get("method", "bootstrap_t_cons")))


def _stat_its(h, res):
    stat = h["statistic"]
    key = "level_change" if stat == "its_level" else "slope_change"
    m = res[key]
    est, lo, hi = float(m["estimate"]), float(m["lower"]), float(m["upper"])
    se = float(m.get("se", (hi - lo) / (2.0 * stats.norm.ppf(0.95))))
    null_v = float(h.get("null_value", 0.0))
    z = abs(est - null_v) / se if np.isfinite(se) and se > 0 else float("nan")
    out = {"estimate": est, "se": se, "se_basis": f"ITS ({res.get('method', 'bootstrap_t_cons')})",
           "ci_lower": lo, "ci_upper": hi,
           "p_two_sided": float(2.0 * stats.norm.sf(z)) if np.isfinite(z) else float("nan")}
    if not bool(res.get("validated", False)):
        out["confirmatory_refusal"] = "interrupted_series configuration is exploratory (validated from 17+ annual points with bootstrap_t_cons)"
    return out


def _check_its(stage, ctx):
    a, errors = ctx["a"], ctx["errors"]
    label = f"analyses ({a.get('id')}) interrupted_series"
    if stage == "before_spatial":
        names = ctx["names"]
        for k in ("outcome", "year"):
            if a.get(k) not in names:
                errors.append(f"{label}: {k} {a.get(k)!r} is not a manifest variable")
        args = a.get("args") or {}
        bad = set(args) - {"method"}
        if bad:
            errors.append(f"{label}: unsupported args {sorted(bad)}")
        method = str(args.get("method", "bootstrap_t_cons"))
        if not ctx.get("exploratory") and method not in ("bootstrap_t_cons", "bootstrap_t_bb", "bootstrap_t_bc", "bootstrap_t"):
            errors.append(f"{label}: confirmatory interrupted_series requires a validated bootstrap_t method")


def _run_combine_estimates(a, args, frame, level, replicates, correction, ctx):
    from ..evidence import combine_estimates
    est = pd.to_numeric(frame[a["estimate"]]).to_numpy(float).tolist()
    ses = pd.to_numeric(frame[a["se"]]).to_numpy(float).tolist()
    mod = pd.to_numeric(frame[args["moderator"]]).to_numpy(float).tolist() if args.get("moderator") else None
    return combine_estimates(est, ses, method=str(args.get("method", "hksj")),
                             assume_homogeneous=bool(args.get("assume_homogeneous", False)),
                             moderators=mod, small_study_test=bool(args.get("small_study_test", len(est) >= 10)),
                             level=level)


def _stat_combine_estimates(h, res):
    stat = h["statistic"]
    if stat == "pooled_effect":
        p = res["pooled"]
        est, lo, hi = float(p["estimate"]), float(p["lower"]), float(p["upper"])
        se = float(p.get("se", (hi - lo) / (2.0 * stats.norm.ppf(0.95))))
        valid = bool(res.get("validated", False))
        basis = f"meta-analysis ({p.get('method', 'hksj')})"
    elif stat == "prediction_interval":
        p = res["pooled"]
        pi = p.get("prediction_interval")
        if not pi:
            raise KeyError("combine_estimates: prediction_interval not present")
        est, lo, hi = float(p["estimate"]), float(pi[0]), float(pi[1])
        se = (hi - lo) / (2.0 * stats.norm.ppf(0.95))
        valid = bool(p.get("prediction_interval_validated", False))
        basis = "NNF prediction interval (Round 104)"
    elif stat == "meta_regression":
        mr = res["meta_regression"]
        est, lo, hi, se = float(mr["slope"]), float(mr["lower"]), float(mr["upper"]), float(mr["se"])
        valid = bool(mr.get("validated", False))
        basis = "truncated Knapp-Hartung meta-regression (Round 104)"
    else:  # egger_test
        eg = res["small_study_test"]
        est = float(eg.get("intercept", eg.get("slope", eg.get("t", 0.0))))
        se = float(eg.get("se", float("nan")))
        lo = hi = float("nan")
        valid = bool(eg.get("validated", False))
        out = {"estimate": est, "se": se, "se_basis": "Thompson-Sharp RE Egger (Round 104)",
               "ci_lower": lo, "ci_upper": hi, "p_two_sided": float(eg["p"])}
        if not valid:
            out["confirmatory_refusal"] = "egger_test requires k >= 10 estimates"
        return out
    null_v = float(h.get("null_value", 0.0))
    z = abs(est - null_v) / se if np.isfinite(se) and se > 0 else float("nan")
    out = {"estimate": est, "se": se, "se_basis": basis, "ci_lower": lo, "ci_upper": hi,
           "p_two_sided": float(2.0 * stats.norm.sf(z)) if np.isfinite(z) else float("nan")}
    if not valid:
        out["confirmatory_refusal"] = f"combine_estimates statistic {stat!r} is exploratory (check k gate)"
    return out


def _check_combine_estimates(stage, ctx):
    a, errors = ctx["a"], ctx["errors"]
    label = f"analyses ({a.get('id')}) combine_estimates"
    if stage == "before_spatial":
        names = ctx["names"]
        for k in ("estimate", "se"):
            if a.get(k) not in names:
                errors.append(f"{label}: {k} {a.get(k)!r} is not a manifest variable")
        args = a.get("args") or {}
        bad = set(args) - {"method", "assume_homogeneous", "moderator", "small_study_test"}
        if bad:
            errors.append(f"{label}: unsupported args {sorted(bad)}")
        if args.get("moderator") and args["moderator"] not in names:
            errors.append(f"{label}: moderator {args['moderator']!r} is not a manifest variable")


def _run_bias_analysis(a, args, frame, level, replicates, correction, ctx):
    from .. import bias_analysis as ba
    kind = str(a["kind"])
    if kind == "e_value":
        return dict(kind="e_value",
                    result=ba.e_value(float(args["estimate"]), args.get("lower"), args.get("upper"),
                                      measure=str(args.get("measure", "rr")), prevalence=args.get("prevalence")))
    tbl = args["table"]
    return dict(kind="misclassification",
                result=ba.misclassification(*map(float, tbl), args["sensitivity"], args["specificity"],
                                            kind=str(args.get("misclassified", "outcome")),
                                            sd=args.get("prior_sd")))


def _stat_bias_analysis(h, res):
    stat = h["statistic"]
    r = res["result"]
    if stat == "e_value":
        return {"estimate": float(r["e_value"]), "se": float("nan"), "se_basis": "VanderWeele-Ding deterministic E-value",
                "ci_lower": float(r.get("e_value_limit", float("nan"))), "ci_upper": float("nan"),
                "p_two_sided": float("nan")}
    key = "rr" if stat == "corrected_rr" else "or"
    prob = r.get("probabilistic") or {}
    m = prob.get(key)
    if not m:
        return {"estimate": float(r["corrected"][key]), "se": float("nan"), "se_basis": "simple misclassification",
                "ci_lower": float("nan"), "ci_upper": float("nan"), "p_two_sided": float("nan"),
                "confirmatory_refusal": "probabilistic misclassification (args.prior_sd) is required for confirmatory intervals"}
    est = float(m["median"]); lo = float(m["lower"]); hi = float(m["upper"])
    se_log = (np.log(hi) - np.log(lo)) / (2.0 * stats.norm.ppf(0.95)) if lo > 0 and hi > 0 else float("nan")
    null_v = float(h.get("null_value", 1.0))
    z = abs(np.log(est) - np.log(null_v)) / se_log if np.isfinite(se_log) and se_log > 0 else float("nan")
    out = {"estimate": est, "se": se_log, "se_basis": "probabilistic misclassification (Round 105)",
           "ci_lower": lo, "ci_upper": hi,
           "p_two_sided": float(2.0 * stats.norm.sf(z)) if np.isfinite(z) else float("nan")}
    if not bool(r.get("validated", False)):
        out["confirmatory_refusal"] = "misclassification interval not validated"
    return out


def _check_bias_analysis(stage, ctx):
    a, errors = ctx["a"], ctx["errors"]
    label = f"analyses ({a.get('id')}) bias_analysis"
    if stage == "before_spatial":
        kind = a.get("kind")
        if kind not in ("e_value", "misclassification"):
            errors.append(f"{label}: kind must be 'e_value' or 'misclassification'")
        args = a.get("args") or {}
        if kind == "e_value" and "estimate" not in args:
            errors.append(f"{label}: kind='e_value' requires args.estimate")
        if kind == "misclassification":
            for k in ("table", "sensitivity", "specificity"):
                if k not in args:
                    errors.append(f"{label}: kind='misclassification' requires args.{k}")


METHODS["difference_in_differences"] = MethodSpec(
    "difference_in_differences", ("outcome",), ("did_effect",), _run_did,
    replicate=True, external_outcome=True, check=_check_did,
    text=(
        "Policy evaluation used validated difference-in-differences (two-group/event, staggered Sun-Abraham or "
        "Callaway-Sant'Anna with ACS SEs, triple-difference, or multi-confounder parametric g-formula MSM; "
        "Rounds 10, 78, 99, 106, 108).",
        ["sun_abraham2021", "hernan_robins2020"],
    ),
)

METHODS["interrupted_series"] = MethodSpec(
    "interrupted_series", ("outcome", "year", "interruption_year"), ("its_level", "its_slope"), _run_its,
    external_outcome=True, check=_check_its,
    text=(
        "Interrupted time-series evaluation on consecutive annual rates used AR(1) bootstrap-t intervals "
        "(bootstrap_t_cons validated from 17+ annual points; Rounds 48, 55, 63).",
        ["bernal2017"],
    ),
)

METHODS["combine_estimates"] = MethodSpec(
    "combine_estimates", ("estimate", "se"), ("pooled_effect", "prediction_interval", "meta_regression", "egger_test"),
    _run_combine_estimates, external_outcome=True, check=_check_combine_estimates,
    text=(
        "Evidence synthesis used Paule-Mandel / Hartung-Knapp pooling (truncated from k >= 5; Rounds 38, 48) and, "
        "for k >= 10 estimates, validated Nagashima-Noma-Furukawa prediction intervals, truncated Knapp-Hartung "
        "meta-regression, and Thompson-Sharp random-effects Egger tests (Round 104).",
        ["harrer2021", "nagashima2019"],
    ),
)

METHODS["bias_analysis"] = MethodSpec(
    "bias_analysis", ("kind",), ("e_value", "corrected_rr", "corrected_or"), _run_bias_analysis,
    check=_check_bias_analysis,
    text=(
        "Quantitative bias analysis reported VanderWeele-Ding E-values (Round 86) and probabilistic misclassification "
        "intervals propagating observed-table sampling variance through Rogan-Gladen inversion (Round 105).",
        ["vanderweele_ding2017", "lash2009"],
    ),
)


STATISTIC_EXTRACTORS = {
    'coefficient': _stat_coefficient,
    'joint_wald': _stat_joint_wald,
    'joint_test': _stat_joint_test,
    'marginal_rr': _stat_marginal,
    'marginal_rd': _stat_marginal,
    'attributable_fraction': _stat_marginal,
    'correlation': _stat_correlation,
    'trend_slope': _stat_trend_slope,
    'z_difference': _stat_z_difference,
    "sii": _stat_inequality,
    "log_rii": _stat_inequality,
    "concentration_index": _stat_inequality,
    "log_smr": _stat_smr,
    "dissimilarity": _stat_segregation,
    "isolation": _stat_segregation,
    "theil_h": _stat_segregation,
    **{k: _stat_disparity for k in ("rd", "log_rr", "idisp", "bgv", "theil", "mld", "par", "par_pct", "who_sii")},
    **{k: _stat_kitagawa for k in ("crude_difference", "rate_effect", "composition_effect")},
    "effect": _stat_estimate_effect,
    "primary_rr": _stat_spatial_scan,
    **{k: _stat_stratified for k in ("mh_rr", "mh_or", "mh_rd", "mh_irr", "reri", "homogeneity")},
    "ppv": _stat_designation,
    **{k: _stat_agreement for k in ("bias", "ccc", "kappa_quintiles")},
    "jump": _stat_rdd,
    "relative_risk": _stat_disease_map,
    "n_joinpoints": _stat_joinpoint,
    "aapc": _stat_joinpoint,
    "e0": _stat_demography,
    "e65": _stat_demography,
    "did_effect": _stat_did,
    "its_level": _stat_its,
    "its_slope": _stat_its,
    **{k: _stat_combine_estimates for k in ("pooled_effect", "prediction_interval", "meta_regression", "egger_test")},
    **{k: _stat_bias_analysis for k in ("e_value", "corrected_rr", "corrected_or")},
}

ANALYSIS_METHODS = {name: (spec.required, spec.statistics) for name, spec in METHODS.items()}
STATISTICS = tuple(dict.fromkeys(stat for spec in METHODS.values() for stat in spec.statistics))
# Preserve the historical public tuple order; future entries follow registry order.
REPLICATE_METHODS = tuple(sorted((name for name, spec in METHODS.items() if spec.replicate),
    key=lambda name: {"fit_replicate": 0, "correlation_matrix": 1, "fit_eiv": 2}.get(name, 3)))
EXTERNAL_OUTCOME_METHODS = tuple(sorted((name for name, spec in METHODS.items() if spec.external_outcome),
    key=lambda name: {"fit_eiv": 0, "fit_replicate": 1, "fh_regression": 2}.get(name, 3)))
