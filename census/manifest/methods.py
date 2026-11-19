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
    if args.get("model") == "negbin":  # Round 43 M2: NB2-HC3 (Round 39), model SE, naive target
        result = _negbin_result(a["formula"], frame, args["exposure"], level)
    else:
        if fixed_vars:
            args["fixed_variables"] = fixed_vars
        result = models.fit_replicate(a["formula"], frame, replicates=replicates, confidence_level=level, **args)
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
    if args.pop("interval", "fisher") == "validated":  # Round 43 M1: Round 33 validated intervals
        return _validated_correlation_result(frame, args.pop("variables"), args.get("method", "pearson"),
                                             replicates, args.get("controls") or [], level)
    return correlation.correlation_matrix(frame, args.pop("variables"), confidence_level=level,
                                          replicates=replicates, correction=correction, **args)


def _validated_correlation_result(frame, variables, method, replicates, controls, level):
    from scipy import stats
    from ..correlation import validated_correlations
    from ..results import CorrelationResult
    rows = validated_correlations(frame, variables, method=method, replicates=replicates, controls=controls,
                                  confidence_level=level)
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
             "under-covered under spatial dependence)."]
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
                                        "(validated with at most 4; docs/audits/spatial_eiv_validation.md, "
                                        "docs/audits/glm_correction_validation.md)"}
    if res.diagnostics.get("regression_calibration_validated") is False:
        return {"estimate": float(row["estimate"]), "se": float(row[se_col]), "se_basis": se_col,
                "p_two_sided": float(row["p_value"]), "ci_lower": float(row["ci_lower"]), "ci_upper": float(row["ci_upper"]),
                "confirmatory_refusal": f"regression calibration for {res.model_type} slopes is exploratory "
                                        "(docs/audits/glm_correction_validation.md)"}
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
                   "target", "scale", "spatial_se", "spatial_clusters"}
        unknown = sorted(set(aargs) - allowed)
        if unknown:
            errors.append(f"fit_replicate does not take args {unknown}")
        glm = aargs.get("model", "ols")
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
            if glm in ("binomial", "poisson") and aargs.get("scale") is None and aargs.get("spatial_se") is None and clusters is None:
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
            "and under spatial dependence these intervals under-covered in validation.")


def _text_fit_replicate(a, text):
    args = a.get("args") or {}
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
                                      period_years=a.get("period_years",1), reference_counts=counts)
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
    if set(args)-{"target"}:
        errors.append(prefix+f"smr does not take args {sorted(set(args)-{'target'})}")
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
    from ..segregation import segregation_replicate
    return segregation_replicate(frame, a["groups"], replicates, within=a["within"], level=level,
                                 bias_correction=args.get("bias_correction"))


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
        if set(args)-{"bias_correction"}:
            errors.append(f"segregation does not take args {sorted(set(args)-{'bias_correction'})}")
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


def _text_smr(a, text):
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
    return text+" Chosen versions: "+versions+". Groups: "+", ".join(a["groups"])+"."


METHODS: Dict[str, MethodSpec] = {
    'fit_replicate': MethodSpec(
        'fit_replicate', ('formula',), ('coefficient', 'joint_wald', 'joint_test'), _run_fit_replicate,
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
        check=_check_spatial,
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

STATISTIC_EXTRACTORS = {
    'coefficient': _stat_coefficient,
    'joint_wald': _stat_joint_wald,
    'joint_test': _stat_joint_test,
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
}

ANALYSIS_METHODS = {name: (spec.required, spec.statistics) for name, spec in METHODS.items()}
STATISTICS = tuple(dict.fromkeys(stat for spec in METHODS.values() for stat in spec.statistics))
# Preserve the historical public tuple order; future entries follow registry order.
REPLICATE_METHODS = tuple(sorted((name for name, spec in METHODS.items() if spec.replicate),
    key=lambda name: {"fit_replicate": 0, "correlation_matrix": 1, "fit_eiv": 2}.get(name, 3)))
EXTERNAL_OUTCOME_METHODS = tuple(sorted((name for name, spec in METHODS.items() if spec.external_outcome),
    key=lambda name: {"fit_eiv": 0, "fit_replicate": 1, "fh_regression": 2}.get(name, 3)))
