# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 8 inference workflows shared by the MCP server and the CLI.

Plain arguments in (paths, lists, numbers), JSON-safe dicts out. Every result
carries ``success``, a one-sentence ``summary``, and a ``next_step`` naming the
tool to call next, so smaller local models can follow the workflow
(PLAN_ROUND_8 workstream J). Failures carry ``error_code`` (census.errors).
"""

import json
import os
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

from census import errors
from census.workflows import ROOT, _jsonable, _load_frame, _records, _replicates_for, _write_frame
from census.results import interval_description

try:  # statsmodels formulas raise patsy errors for bad formulas
    from patsy import PatsyError as _PatsyError
except ImportError:  # pragma: no cover
    class _PatsyError(Exception):
        pass

# Errors from user input or numerically degenerate data -> INVALID_INPUT.
_INPUT_ERRORS = (FileNotFoundError, OSError, KeyError, ValueError, TypeError, RuntimeError,
                 ZeroDivisionError, np.linalg.LinAlgError, _PatsyError)

_MODEL_METHODS = ("replicate", "eiv", "regression_calibration", "simex", "fay_herriot")
_FIGURE_KINDS = ("estimates", "forest", "trend")


def _ok(summary: str, next_step: str, **payload: Any) -> Dict[str, Any]:
    return _jsonable({"success": True, "summary": summary, "next_step": next_step, **payload})


def replicate_flag(result: Any) -> str:
    """Summary suffix for results flagged with incomplete replicates (PLAN_ROUND_11 Q2/D7), else ""."""
    info = ((getattr(result, "diagnostics", None) or {}).get("replicates_incomplete")
            or (getattr(result, "provenance", None) or {}).get("replicates_incomplete"))
    if not info:
        return ""
    return f" (REPLICATES INCOMPLETE: {info['note']})"


def result_summary(result: Any) -> str:
    """``result.summary()`` plus the REPLICATES INCOMPLETE flag, which appears at most once."""
    text = result.summary()
    return text if "REPLICATES INCOMPLETE" in text else text + replicate_flag(result)


def interval_next_step(info: Dict[str, Any]) -> str:
    """next_step guidance from census.results.interval_description (one wording for every model workflow)."""
    dist = "t with each coefficient's df" if info["distribution"] == "t" else "normal"
    step = (f"make_table or make_figure; report each coefficient with {info['basis_column']} (the SE behind its "
            f"{info['level'] * 100:g}% {dist} confidence interval and p-value; includes "
            f"{', '.join(info['basis_sources']) or 'no listed source'}) as {info['estimand']}")
    if info["undefined_terms"]:
        step += f"; uncertainty is undefined for {info['undefined_terms']}: report no interval or significance there"
    if info["replicates_incomplete"]:
        step += "; disclose that replicates were incomplete (sampling SE may be understated)"
    return step


def _fail(code: str, message: str, next_step: str = "") -> Dict[str, Any]:
    out = errors.error_result(code, message)
    out["summary"] = message
    if next_step:
        out["next_step"] = next_step
    return out


def _out_dir(path: Optional[str], default: str) -> str:
    folder = path or os.path.join(ROOT, "downloads", default)
    os.makedirs(folder, exist_ok=True)
    return folder


def _read_replicates(path: Optional[str]) -> Optional[pd.DataFrame]:
    if not path:
        return None
    from census.manifest import read_replicates
    return read_replicates(path)


def _load_frames(input_path: Any) -> pd.DataFrame:
    """One file, or several merged into one row per GEOID (and Year): files of
    different tables add columns, files of different states add rows. A cell
    given different values by two files is an error, never resolved silently."""
    if isinstance(input_path, str):
        return _load_frame(input_path)
    paths = list(input_path or [])
    if not paths:
        raise ValueError("input_path is an empty list")
    frames = [_load_frame(str(p)) for p in paths]
    if len(frames) == 1:
        return frames[0]
    keys = ["GEOID"] + (["Year"] if any("Year" in f.columns for f in frames) else [])
    # rows without a key would be dropped by the merge (groupby drops missing keys): refuse instead
    for path, frame in zip(paths, frames):
        for key in keys:
            if key not in frame.columns:
                raise ValueError(f"{path} has no {key} column" + (" (another input file has one); every file "
                                 "must carry the same keys" if key != "GEOID" else "; every input file needs one"))
            missing = int(frame[key].isna().sum())
            if missing:
                raise ValueError(f"{path} has {missing} row(s) with a missing {key}; fix or drop them first")
    from census.analysis import load_source

    df = load_source(frames)  # validate/preserve declared product before merging cells
    df["GEOID"] = df["GEOID"].astype(str)
    grouped = df.groupby(keys, sort=False)
    conflicts = [c for c in df.columns if c not in keys and (grouped[c].nunique(dropna=True) > 1).any()]
    if conflicts:
        raise ValueError(f"input files disagree on {conflicts[:5]} for the same {'/'.join(keys)}")
    out = grouped.first().reset_index()
    out.attrs = dict(df.attrs)
    return out


def build_analysis_frame(
    input_path: Union[str, List[str]],
    variables: Optional[List[str]] = None,
    derive: Optional[List[Dict[str, Any]]] = None,
    use_replicates: bool = False,
    table_code: Optional[Union[str, List[str]]] = None,
    year: Optional[int] = None,
    output_path: Optional[str] = None,
    context: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Make a model-ready table from a downloaded file: each variable gets its
    estimate, standard error (_se), CV (_cv), and method, plus optional Census
    replicate values for exact sampling error.

    Args:
        input_path: CSV/Parquet from batch_download, or a list of them (other
            tables are joined on GEOID/Year; other states are stacked).
        variables: Estimate columns to keep, e.g. ["B19013_001E"]. Default: all.
        derive: Optional derived variables, e.g. [{"name": "poverty_rate",
            "op": "proportion", "num": "B17001_002E", "den": "B17001_001E"}].
        use_replicates: Download Census replicate estimates (needs table_code, year).
        table_code, year: Detailed table(s) (one code or a list) and release for replicates.
        output_path: Where to write the frame (default downloads/analysis_frame.parquet).
        context: Optional county covariates from other sources (Round 72; list_health_sources(kind="context")),
            e.g. [{"source": "ers_rucc", "name": "rucc", "field": "RuralUrbanContinuumCode2013"}]; tracts get
            their county's value.

    Example: build_analysis_frame("out/B17001_county_panel_2023.csv", derive=[...])
    """
    from census.analysis import analysis_frame, attach_replicates, coverage_report

    try:
        df = _load_frames(input_path)
        if year is not None and "Year" in df.columns:
            df = df[df["Year"] == year]
        frame = analysis_frame(df, variables=variables, derive=derive)
        replicates = None
        if use_replicates:
            if not (table_code and year):
                return _fail(errors.INVALID_INPUT, "use_replicates needs table_code and year.")
            tables = [table_code] if isinstance(table_code, str) else list(table_code)
            geoids = list(df["GEOID"].astype(str))
            rep = pd.concat([_replicates_for(t, year, df, geoids) for t in tables], ignore_index=True)
            frame, replicates = attach_replicates(frame, rep, derive=derive)
        ctx_info = None
        if context:
            from census.context_sources import context_frame, join_context, validate_context
            errs = validate_context(context, list(frame.columns))
            if errs:
                return _fail(errors.INVALID_INPUT, "; ".join(errs), "fix the context entries")
            ctx, prov = context_frame(context, frame)
            frame, join = join_context(frame, ctx)
            ctx_info = {"provenance": prov, "join": join}
        report = coverage_report(frame, replicates)
    except _INPUT_ERRORS as exc:
        return _fail(errors.INVALID_INPUT, f"{type(exc).__name__}: {exc}",
                     "check the formula, column names, and input file, then retry")
    path = _write_frame(frame, output_path or os.path.join(ROOT, "downloads", "analysis_frame.parquet"),
                        "analysis_frame.parquet")
    rep_path = None
    if replicates is not None:
        rep_path = os.path.splitext(path)[0] + "_replicates.parquet"
        replicates.to_parquet(rep_path, index=False)
    noisy = int((report.get("share_cv_over_threshold", pd.Series(dtype=float)) > 0.25).sum()) if len(report) else 0
    return _ok(
        f"Analysis frame with {len(frame)} rows written; {noisy} variable(s) have over 25% of rows with CV above the reliability threshold.",
        "fit_model (or correlation_matrix) with input_path=output_path"
        + (" and replicates_path" if rep_path else ""),
        output_path=path, replicates_path=rep_path, coverage=_records(report),
        **({"context": ctx_info} if ctx_info else {}),
    )


def fit_model(
    input_path: str,
    formula: str,
    method: str = "replicate",
    model: str = "ols",
    replicates_path: Optional[str] = None,
    error_covariates: Optional[List[str]] = None,
    se_col: Optional[str] = None,
    confidence_level: float = 0.90,
    figure_dir: Optional[str] = None,
    target: str = "population",
    weights: Optional[str] = None,
    exposure: Optional[str] = None,
    trials: Optional[str] = None,
    spatial: Optional[str] = None,
    impute: Optional[Union[str, List[str]]] = None,
    se_method: Optional[str] = None,
    censored: Optional[str] = None,
    spatial_check: str = "auto",
) -> Dict[str, Any]:
    """Fit a regression whose standard errors account for ACS sampling error.

    Args:
        input_path: Analysis frame from build_analysis_frame.
        formula: e.g. "poverty_rate ~ median_rent + unemployment_rate".
        method: "replicate" (refit on Census replicates), "eiv" (predictors and outcome
            measured with ACS error; corrects attenuation and correlated errors from the
            replicates; needs replicates_path; model ols or wls), "regression_calibration"
            (predictors measured with error; corrects attenuation; validated for ols, wls,
            poisson and negbin; binomial needs se_method="jackknife"), "simex" (not
            validated for confirmatory use), "fay_herriot" (outcome with known SE in se_col).
        target: "population" (default: the general relationship, model SE),
            "these_areas" (these areas in this period, replicate SE), or
            "conservative" (both added; intervals too wide).
        model: "ols", "wls", "binomial", "poisson", "negbin", "beta" (shares in 0-1) or "median"
            (median regression for skewed outcomes).
        replicates_path: From build_analysis_frame (needed for exact sampling error).
        error_covariates: Predictors measured with error (regression_calibration/simex).
        se_col: Outcome SE column (fay_herriot).
        confidence_level: 0.90 matches ACS margins of error.
        figure_dir: Also write a coefficient plot here.
        weights: Weight column (model="wls").
        exposure: Exposure column (model="poisson"/"negbin").
        trials: Trials column (model="binomial"; default effective sample size).

        impute: A covariate with missing values to multiply impute (OLS; Round 42; validated), or a
            list of two (chained equations; Round 47; validated).
        spatial: method="eiv": "clusters" (8 fixed spatial clusters, pooled correction) or
            "error" (spatial-error whitening) for corrected slopes when areas are spatially
            correlated (Rounds 35, 46 and 53; linear; validated with up to five error-prone covariates).
            model="negbin": "clusters" gives IM-8 count slopes (Round 45; validated).
            method="regression_calibration", model "poisson"/"negbin": "clusters" calibrates the
            error_covariates, then fits IM-8 count slopes (Round 53; validated; needs exposure);
            model "binomial" with trials likewise (Round 58; validated).
            method="replicate": "scpc" gives SCPC spatial intervals for naive slopes (Round 58;
            validated for ols, poisson and (Round 62) binomial, also outside MI/NY).
        se_method: method="regression_calibration": "bootstrap" (default) or "jackknife"
            (delete-one-area; Round 53; validated for binomial, poisson and negbin).
        censored: model="negbin": a true/false column marking counts hidden as 1-9 (e.g. WONDER
            suppression). They enter as "between 1 and 9" (interval-censored NB2, Round 45;
            validated); no hidden value is estimated or output. Needs exposure; formula terms
            must be plain column names.
        spatial_check: "auto" (default; Round 71) tests the residuals for spatial dependence with cached boundary
            files and adds a note naming the validated spatial interval; "on" may download them; "off" skips.

    target applies to method="replicate" only; corrected methods report se_total.
    Results report se_model, se_sampling, se_total and which sources are included.
    Example: fit_model("downloads/analysis_frame.parquet", "rate ~ rent", replicates_path="...")
    """
    from census import models, sae

    if method not in _MODEL_METHODS:
        return _fail(errors.INVALID_INPUT, f"method must be one of {_MODEL_METHODS}.")
    if method != "replicate" and target != "population":
        return _fail(errors.INVALID_INPUT,
                     f"target applies only to method='replicate'; {method} reports se_total.",
                     "call fit_model again without target")
    if method == "fay_herriot" and (weights or exposure or trials or model != "ols"):
        return _fail(errors.INVALID_INPUT,
                     "fay_herriot is a linear model with its own weights; model/weights/exposure/trials do not apply.",
                     "call fit_model again without model, weights, exposure, trials")
    if censored is not None and (method != "replicate" or model != "negbin" or impute):
        return _fail(errors.INVALID_INPUT, "censored needs method='replicate' and model='negbin' (interval-censored NB2).",
                     "call fit_model again with model='negbin', exposure and censored")
    extra = {"weights": weights, "exposure": exposure, "trials": trials}
    try:
        frame = _load_frame(input_path)
        if method == "eiv" and spatial:
            if spatial not in ("clusters", "error") or not replicates_path or model != "ols" or weights:
                return _fail(errors.INVALID_INPUT, "spatial EIV needs spatial='clusters' or 'error', replicates_path, "
                             "model='ols' and no weights.")
            from census.spatial_eiv import fit_spatial_eiv
            outcome = formula.split("~", 1)[0].strip()
            res = fit_spatial_eiv(formula, frame, _read_replicates(replicates_path),
                                  method="g1" if spatial == "clusters" else "g2", level=confidence_level)
            from census.results import _jsonable
            res["table"] = res["table"].to_dict("records")
            return _ok(f"Corrected slopes with spatially robust inference ({spatial}); "
                       f"{'validated' if res['validated'] else 'exploratory'}.",
                       "report the corrected slope with its interval", **_jsonable(res))
        if method == "eiv":
            if not replicates_path:
                return _fail(errors.INVALID_INPUT, "method='eiv' needs replicates_path (from build_analysis_frame).",
                             "call build_analysis_frame with use_replicates, then fit_model with replicates_path")
            if exposure or trials or model not in ("ols", "wls"):
                return _fail(errors.INVALID_INPUT, "method='eiv' supports model 'ols' or 'wls' only.",
                             "call fit_model again with model='ols' (or 'wls' and weights)")
            result = models.fit_eiv(formula, frame, _read_replicates(replicates_path), model=model,
                                    weights=weights, confidence_level=confidence_level)
        elif method == "replicate" and impute:
            from census.missing_censored_its import impute_and_fit
            res = impute_and_fit(formula, frame, impute)
            from census.results import _jsonable
            res["table"] = res["table"].to_dict("records")
            rnd = "Round 42" if isinstance(res["n_missing"], int) else "chained equations, Round 47"
            return _ok(f"OLS with missing values {res['n_missing']} of {impute} multiply imputed; validated ({rnd}).",
                       "report coefficients with intervals and the missing-at-random assumption", **_jsonable(res))
        elif method == "replicate" and model in ("beta", "median"):
            from census.regression_families import fit_beta, fit_median
            res = (fit_beta if model == "beta" else fit_median)(formula, frame, confidence_level)
            from census.results import _jsonable
            res["table"] = res["table"].to_dict("records")
            return _ok(f"{res['model']} coefficients; validated (Round 40).", "report coefficients with intervals",
                       **_jsonable(res))
        elif censored is not None:
            if method != "replicate" or model != "negbin" or not exposure or spatial or weights or trials:
                return _fail(errors.INVALID_INPUT, "censored needs method='replicate', model='negbin' and exposure "
                             "(no spatial, weights or trials).")
            from census.missing_censored_its import fit_censored_negbin
            outcome, rhs = (x.strip() for x in formula.split("~", 1))
            terms = [t.strip() for t in rhs.split("+")]
            bad = [t for t in [outcome, censored, exposure] + terms if t not in frame.columns]
            if bad:
                return _fail(errors.INVALID_INPUT, f"censored NB2 needs plain column names; not columns: {bad}.")
            res = fit_censored_negbin(frame, outcome, censored, exposure, terms)
            from census.results import _jsonable
            res["table"] = res["table"].to_dict("records")
            return _ok(f"Interval-censored NB2 slopes; {res['n_censored']} of {res['n']} counts hidden as 1-9 used "
                       "as intervals; validated (Round 45).",
                       "report the slopes; never report or derive the hidden counts", **_jsonable(res))
        elif method == "replicate" and model == "negbin":
            from census.count_models import fit_count_model
            if not exposure:
                return _fail(errors.INVALID_INPUT, "model='negbin' needs exposure (expected counts or population).")
            if spatial not in (None, "clusters"):
                return _fail(errors.INVALID_INPUT, "model='negbin' takes spatial='clusters' only.")
            res = fit_count_model(formula, frame, exposure, "negbin", confidence_level, spatial=spatial)
            from census.results import _jsonable
            res["table"] = res["table"].to_dict("records")
            what = "IM-8 negative binomial slopes (Round 45)" if spatial else "Negative binomial (NB2, HC3) slopes (Round 39)"
            return _ok(f"{what}; validated.", "report slopes with their intervals", **_jsonable(res))
        elif method == "replicate" and spatial == "scpc":
            from census.scpc import fit_scpc
            if model not in ("ols", "poisson", "binomial"):
                return _fail(errors.INVALID_INPUT, "spatial='scpc' supports model ols, poisson or binomial.")
            res = fit_scpc(formula, frame, model, trials=trials, exposure=exposure, level=confidence_level)
            from census.results import _jsonable
            res["table"] = res["table"].to_dict("records")
            return _ok(f"Naive {model} slopes with SCPC spatial intervals (Round 58); "
                       f"{'validated' if res['validated'] else 'exploratory'}.",
                       "report slopes with their intervals; the target is the slope on the estimates as observed",
                       **_jsonable(res))
        elif method == "replicate":
            result = models.fit_replicate(formula, frame, _read_replicates(replicates_path), model=model,
                                          confidence_level=confidence_level, target=target, **extra)
        elif method == "regression_calibration" and spatial and model == "binomial":
            if spatial != "clusters" or not trials or not error_covariates:
                return _fail(errors.INVALID_INPUT, "binomial spatial regression calibration needs spatial='clusters', "
                             "trials and error_covariates.")
            res = models.regression_calibration_clusters(formula, frame, error_covariates, trials,
                                                         level=confidence_level)
            from census.results import _jsonable
            res["table"] = res["table"].to_dict("records")
            return _ok("Calibrated IM-8 binomial slopes (Round 58); validated.",
                       "report the corrected slopes with their intervals", **_jsonable(res))
        elif method == "regression_calibration" and spatial:
            from census.count_models import fit_count_model
            if spatial != "clusters" or model not in ("poisson", "negbin") or not exposure or not error_covariates:
                return _fail(errors.INVALID_INPUT, "spatial regression calibration needs spatial='clusters', "
                             "model 'poisson' or 'negbin', exposure and error_covariates.")
            res = fit_count_model(formula, frame, exposure, model, confidence_level, spatial="clusters",
                                  calibrate=error_covariates)
            from census.results import _jsonable
            res["table"] = res["table"].to_dict("records")
            return _ok(f"Calibrated IM-8 {model} slopes (Round 53); {'validated' if res['validated'] else 'exploratory'}.",
                       "report the corrected slopes with their intervals", **_jsonable(res))
        elif method in ("regression_calibration", "simex"):
            if not error_covariates:
                return _fail(errors.INVALID_INPUT, f"{method} needs error_covariates.")
            if se_method is not None and method != "regression_calibration":
                return _fail(errors.INVALID_INPUT, "se_method applies to method='regression_calibration' only.")
            fn = models.regression_calibration if method == "regression_calibration" else models.simex
            kw = {"se_method": se_method} if se_method else {}
            result = fn(formula, frame, error_covariates, model=model, confidence_level=confidence_level, **extra, **kw)
        else:
            if not se_col:
                return _fail(errors.INVALID_INPUT, "fay_herriot needs se_col (the outcome's SE column).")
            result = sae.fh_regression(formula, frame, se_col, confidence_level=confidence_level)
    except _INPUT_ERRORS as exc:
        return _fail(errors.INVALID_INPUT, f"{type(exc).__name__}: {exc}",
                     "check the formula, column names, and input file, then retry")
    out = result.to_dict()
    if method == "replicate" and model == "ols":
        from census.diagnostics import model_diagnostics
        out["model_diagnostics"] = model_diagnostics(result)
    if figure_dir:
        from census.figures import coefficient_plot

        fig = coefficient_plot(result, out_dir=_out_dir(figure_dir, "figures"), name="coefficients")
        out["figure_paths"] = [str(p) for p in fig.paths.values()] if isinstance(fig.paths, dict) else [str(p) for p in fig.paths]
    if method == "replicate" and not replicates_path:
        out["notes"] = list(out.get("notes") or []) + [
            "No replicates supplied: standard errors include model error only, not ACS sampling error."
        ]
    if method == "replicate" and spatial is None and spatial_check in ("auto", "on"):
        from census import residual_dependence as rd
        chk = rd.check(frame, formula, mode=spatial_check)
        msg = rd.note(chk, rd.recommended(chk))
        if msg:
            out["spatial_dependence"] = chk
            out["notes"] = list(out.get("notes") or []) + [msg]
    # Report the SE that the displayed intervals and p-values actually use
    # (PLAN_ROUND_11 C7): se_model for target="population", se_sampling for
    # "these_areas", se_total for "conservative" and the corrected methods.
    info = interval_description(result)
    se_basis = info["basis_column"]
    out["interval_se_column"] = se_basis
    next_step = interval_next_step(info)
    if method == "simex":
        next_step += "; SIMEX under-covers and is exploratory only, not for confirmatory claims"
    if method == "regression_calibration" and model == "binomial" and se_method != "jackknife":
        next_step += ("; binomial regression calibration with bootstrap SEs under-covers and is exploratory only; "
                      "use se_method='jackknife' (validated, Round 53)")
    return _ok(f"{result_summary(result)}; intervals and p-values use {se_basis}", next_step,
               **{k: v for k, v in out.items() if k != "summary"})


def compare_groups(
    input_path: str,
    outcome: str,
    group: str,
    design: str = "oneway",
    covariates: Optional[List[str]] = None,
    group2: Optional[str] = None,
    model: str = "ols",
    replicates_path: Optional[str] = None,
    trials: Optional[str] = None,
    exposure: Optional[str] = None,
    posthoc: str = "holm",
    reference_group: Optional[str] = None,
    spatial: bool = False,
    confidence_level: float = 0.90,
    method: str = "model",
    outcomes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Compare an area outcome across groups of areas: t-test, ANOVA, ANCOVA or two-way interaction.

    Args:
        input_path: Analysis frame from build_analysis_frame, with a group column.
        outcome: Outcome column, e.g. "poverty_rate".
        group: Categorical column (e.g. "metro_class"), or "state" (first two GEOID digits).
        design: "two_group" (t-test), "oneway" (ANOVA), "ancova" (adjusted for covariates)
            or "twoway" (tests the group x group2 interaction).
        covariates: Adjustment columns (design="ancova"; optional for "twoway").
        group2: Second categorical column (design="twoway").
        model: "ols" (default), "binomial" (needs trials) or "poisson" (needs exposure).
        replicates_path: From build_analysis_frame (includes ACS sampling error).
        posthoc: "holm" (default), "simultaneous" (OLS only) or "none".
        reference_group: Group used as the baseline (default: first in sort order).
        spatial: True uses 8 fixed spatial clusters (IM-8) for spatially dependent areas.
        confidence_level: 0.90 matches ACS margins of error.
        method: "model" (default) or "rank" (Brunner-Munzel for two groups, Kruskal-Wallis for more;
            no covariates; robust to skewed values).
        outcomes: Two or more outcome columns for a joint (MANOVA/MANCOVA) test of the group effect
            on all of them (Round 39; OLS; covariates allowed); outcome is then ignored.

    Returns the joint (omnibus) test, adjusted group means with intervals, pairwise
    differences, effect sizes (OLS), and whether each result is validated or exploratory.
    Example: compare_groups("downloads/frame.parquet", "poverty_rate", "metro_class")
    """
    from census.group_compare import compare_groups as _compare

    if outcomes:
        from census.count_models import compare_groups_multivariate
        try:
            res = compare_groups_multivariate(_load_frame(input_path), outcomes, group,
                                              replicates=_read_replicates(replicates_path) if replicates_path else None,
                                              covariates=covariates or ())
        except _INPUT_ERRORS as exc:
            return _fail(errors.INVALID_INPUT, f"{type(exc).__name__}: {exc}", "check the outcomes, group and covariates")
        from census.results import _jsonable
        return _ok(f"Joint test of {group} on {len(outcomes)} outcomes: p = {res['p_value']:.3g} (validated).",
                   "then compare each outcome with compare_groups", **_jsonable(res))
    try:
        frame = _load_frame(input_path)
        result = _compare(frame, outcome, group, replicates=_read_replicates(replicates_path) if replicates_path else None,
                          covariates=covariates or (), design=design, group2=group2, model=model, trials=trials,
                          exposure=exposure, posthoc=posthoc, reference_group=reference_group,
                          spatial_clusters={"k": 8, "method": "im"} if spatial else None,
                          confidence_level=confidence_level, method=method)
    except _INPUT_ERRORS as exc:
        return _fail(errors.INVALID_INPUT, f"{type(exc).__name__}: {exc}",
                     "check the column names, design and group sizes (at least 5 areas per group), then retry")
    out = result.to_dict()
    validated = result.validation["omnibus"] and (posthoc == "none" or design == "twoway" or result.validation["posthoc_validated"])
    next_step = ("report the joint test, then the pairwise differences" if validated else
                 "treat these results as exploratory: see notes for why; do not use them as confirmatory evidence")
    return _ok(result.summary(), next_step, **out)


def rank_areas(
    input_path: str,
    variable: str,
    kind: str = "ranks",
    replicates_path: Optional[str] = None,
    se_col: Optional[str] = None,
    moe_col: Optional[str] = None,
    joint: bool = False,
    reference: Optional[float] = None,
    weights: Optional[str] = None,
    method: str = "holm",
    confidence_level: float = 0.90,
) -> Dict[str, Any]:
    """Rank areas with honest uncertainty, or find areas that differ from a reference value.

    Args:
        input_path: Analysis frame (GEOID per row).
        variable: Estimate column, e.g. "poverty_rate".
        kind: "ranks" (rank intervals; rank 1 = highest) or "versus_reference"
            (each area minus the reference).
        replicates_path / se_col / moe_col: the estimates' uncertainty (replicates preferred).
        joint: Rank intervals that hold for all areas together (wider) instead of each area.
        reference: A fixed number; omit it and give weights for the weighted mean of the areas
            (e.g. weights="population" gives the state value, which shares the areas' errors).
        method: "holm" or "simultaneous" (versus_reference).
    Validated (Round 34). Bootstrap percentile ranks are not offered: they under-cover badly.
    Example: rank_areas("downloads/frame.parquet", "poverty_rate", moe_col="poverty_rate_moe")
    """
    from census.ranking import compare_to_reference, rank_intervals

    if kind not in ("ranks", "versus_reference"):
        return _fail(errors.INVALID_INPUT, "kind must be 'ranks' or 'versus_reference'.")
    try:
        frame = _load_frame(input_path)
        reps = _read_replicates(replicates_path) if replicates_path else None
        if kind == "ranks":
            out = rank_intervals(frame, variable, replicates=reps, se_col=se_col, moe_col=moe_col, joint=joint,
                                 level=confidence_level)
            summary = (f"{out['K']} areas ranked; median rank interval spans {out['median_interval_width']:.0f} ranks; "
                       f"{len(out['surely_top_decile'])} area(s) are surely in the top 10%.")
        else:
            out = compare_to_reference(frame, variable, replicates=reps, se_col=se_col, moe_col=moe_col,
                                       reference="weighted_mean" if reference is None else reference,
                                       weights=weights, method=method, level=confidence_level)
            summary = (f"{out['n_differ']} of {out['K']} areas differ from the reference "
                       f"{out['reference_value']:.4g} ({method}).")
    except _INPUT_ERRORS as exc:
        return _fail(errors.INVALID_INPUT, f"{type(exc).__name__}: {exc}",
                     "check the variable, its uncertainty column or replicates, and the weights, then retry")
    from census.results import _jsonable
    out["table"] = out["table"].to_dict("records")
    return _ok(summary, "report rank intervals, not point ranks; areas with overlapping intervals cannot be ordered",
               **_jsonable(out))


def build_index(
    input_path: str,
    indicators: List[str],
    replicates_path: Optional[str] = None,
    method: str = "pca",
    reverse: Optional[List[str]] = None,
    outcome: Optional[str] = None,
    typology_k: Optional[int] = None,
    spatial: bool = False,
    loadings: Optional[Dict[str, float]] = None,
    standardize: bool = False,
) -> Dict[str, Any]:
    """Build a composite (e.g. deprivation) index from three or more ACS estimates, with
    per-area score intervals, quintiles and their stability, Cronbach's alpha and an
    optional typology (k groups).

    Args:
        input_path: Analysis frame (GEOID per row).
        indicators: Estimate columns; higher = more deprived unless listed in reverse.
        replicates_path: From build_analysis_frame (needed for score intervals).
        method: "pca" (first principal component), "equal" weights, or "loadings" (Round 73: published fixed
            weights given in loadings={indicator: weight}, e.g. a paper's factor loadings; two indicators allowed).
        standardize: rescale the scores to mean 0, SD 1 (for "per SD" models).
        reverse: Indicators where higher means less deprived (e.g. median income).
        outcome: The outcome you will relate the index to; refused if it is an indicator.
        typology_k: Also group areas into k types (descriptive), with replicate stability.
        spatial: Spatially dependent areas: Cronbach's alpha interval with the effective sample
            size (Round 48; validated).
    Example: build_index("frame.parquet", ["poverty", "no_vehicle", "cost_burden"], replicates_path="reps.parquet")
    """
    from census.composite_index import build_index as _build

    try:
        frame = _load_frame(input_path)
        coords = None
        if spatial:
            from census.small_spatial import frame_coordinates
            coords = frame_coordinates(frame)
        out = _build(frame, indicators, replicates=_read_replicates(replicates_path) if replicates_path else None,
                     method=method, reverse=reverse or (), outcome=outcome, typology_k=typology_k, coords=coords,
                     loadings=loadings, standardize=standardize)
    except _INPUT_ERRORS as exc:
        return _fail(errors.INVALID_INPUT, f"{type(exc).__name__}: {exc}",
                     "check the indicator names (at least three) and replicates, then retry")
    from census.results import _jsonable
    out["table"] = out["table"].to_dict("records")
    a = out["cronbach_alpha"]
    return _ok(f"{method.upper()} index of {len(indicators)} indicators over {out['n']} areas; alpha {a['estimate']:.2f} "
               f"({a['lower']:.2f}-{a['upper']:.2f}); score intervals {'validated' if out['validated_scores'] else 'unavailable'}.",
               "report scores with intervals and quintile stability; do not use the outcome as an indicator",
               **_jsonable(out))


def check_agreement(
    input_path: str,
    a: str,
    b: str,
    replicates_path: Optional[str] = None,
    a_se: Optional[str] = None,
    b_se: Optional[str] = None,
) -> Dict[str, Any]:
    """How well do two sources of the same quantity agree (e.g. ACS vs PLACES, ACS vs
    population estimates)? Bias (b minus a), Cohen's kappa of quintile classes, limits of
    agreement and concordance, for the observed and (with SEs) the error-free values.

    Args:
        input_path: Frame with both columns, one row per area.
        a, b: The two sources' columns (difference = b - a).
        replicates_path / a_se / b_se: Standard errors (needed for error-free quantities).
    Validated: bias and kappa. Limits and concordance intervals failed validation (exploratory).
    Example: check_agreement("frame.parquet", "acs_population", "pep_population")
    """
    from census.agreement import check_agreement as _check

    try:
        out = _check(_load_frame(input_path), a, b, a_se=a_se, b_se=b_se,
                     replicates=_read_replicates(replicates_path) if replicates_path else None)
    except _INPUT_ERRORS as exc:
        return _fail(errors.INVALID_INPUT, f"{type(exc).__name__}: {exc}", "check both column names, then retry")
    from census.results import _jsonable
    bias, kap = out["bias"], out["kappa_quintiles"]
    return _ok(f"{b} minus {a}: bias {bias['estimate']:.4g} ({bias['lower']:.4g} to {bias['upper']:.4g}); "
               f"quintile kappa {kap['estimate']:.2f}.",
               "report bias, kappa and limits of agreement with their intervals; concordance intervals are exploratory",
               **_jsonable(out))


def combine_estimates(
    kind: str,
    estimates: Optional[List[float]] = None,
    ses: Optional[List[float]] = None,
    labels: Optional[List[str]] = None,
    method: str = "hksj",
    assume_homogeneous: bool = False,
    margin: Optional[float] = None,
    effect: Optional[float] = None,
    se: Optional[float] = None,
    target_power: float = 0.80,
) -> Dict[str, Any]:
    """Combine evidence: pool several estimates of one effect, test whether two estimates are
    equivalent, or compute power / the minimum detectable effect.

    Args:
        kind: "pool" (estimates, ses; method "hksj" default), "equivalence" (two estimates and
            ses, margin set in advance) or "power" (se, and effect for its power).
        assume_homogeneous: Declared in advance; needed for a validated fixed-effect interval.
    Validated (Round 38): HKSJ pooling for up to 4 estimates; TOST; z-test power.
    Example: combine_estimates("pool", estimates=[0.027, 0.035], ses=[0.0055, 0.0048])
    """
    from census import evidence

    try:
        if kind == "pool":
            out = evidence.combine_estimates(estimates or [], ses or [], method=method,
                                             assume_homogeneous=assume_homogeneous, labels=labels)
            p = out["pooled"]
            summary = (f"Pooled {p['estimate']:.4g} (90% CI {p['lower']:.4g} to {p['upper']:.4g}; {method}); "
                       f"I² {out['heterogeneity']['I2']:.0%}; {'validated' if out['validated'] else 'exploratory'}.")
        elif kind == "equivalence":
            if not (estimates and ses and len(estimates) == 2 and len(ses) == 2 and margin):
                return _fail(errors.INVALID_INPUT, "equivalence needs two estimates, two ses and a margin.")
            out = evidence.equivalence(estimates[0], ses[0], estimates[1], ses[1], margin)
            summary = f"Difference {out['difference']:.4g}; {'equivalent' if out['equivalent'] else 'not shown equivalent'} within ±{margin}."
        elif kind == "power":
            if se is None:
                return _fail(errors.INVALID_INPUT, "power needs se.")
            out = evidence.power(se, effect, target_power)
            summary = f"Minimum detectable effect {out['minimum_detectable_effect']:.4g} at {target_power:.0%} power" + (
                f"; power for {effect} is {out['power']:.0%}" if effect is not None else "") + "."
        else:
            return _fail(errors.INVALID_INPUT, "kind must be 'pool', 'equivalence' or 'power'.")
    except _INPUT_ERRORS as exc:
        return _fail(errors.INVALID_INPUT, f"{type(exc).__name__}: {exc}", "check the inputs, then retry")
    from census.results import _jsonable
    return _ok(summary, "report the estimate with its interval and say whether it is validated", **_jsonable(out))


def estimate_effect(
    input_path: str,
    kind: str,
    outcome: str,
    treatment: Optional[str] = None,
    confounders: Optional[List[str]] = None,
    x: Optional[str] = None,
    instrument: Optional[str] = None,
    mediator: Optional[str] = None,
    controls: Optional[List[str]] = None,
    method: Optional[str] = None,
    replicates_path: Optional[str] = None,
    calibrate: bool = False,
) -> Dict[str, Any]:
    """Causal-style estimates for areas (state the assumptions; register designs for confirmatory claims).

    Args:
        kind: "treatment" (binary 0/1 treatment column, confounders; method aipw|ipw|ra),
            "iv" (error-prone x instrumented by an independent second measurement, controls) or
            "mediation" (x -> mediator -> outcome; method bootstrap|sobel).
        replicates_path: Lets the tool flag error-prone confounders or mediators.
        calibrate: Correct noisy confounders (treatment, AIPW) or a noisy mediator (mediation, no
            controls) using their _se/_moe columns (Round 47; validated).
    Validated (Round 41): treatment effects with precisely measured confounders; 2SLS with a second
    measurement; mediation with an exactly measured mediator. Round 47: calibrate=True for noisy
    confounders or mediators; iv also reports an Anderson-Rubin interval (valid for weak instruments;
    use it when first-stage F < 10).
    Example: estimate_effect("frame.parquet", "iv", "mortality", x="poverty", instrument="poverty_2017")
    """
    from census import causal

    needs = {"treatment": {"treatment": treatment, "confounders": confounders},
             "iv": {"x": x, "instrument": instrument}, "mediation": {"x": x, "mediator": mediator}}
    if kind not in needs:
        return _fail(errors.INVALID_INPUT, "kind must be 'treatment', 'iv' or 'mediation'.")
    missing = [k for k, v in needs[kind].items() if not v]
    if missing:
        return _fail(errors.INVALID_INPUT, f"kind={kind!r} needs {missing}.", f"pass {', '.join(missing)}, then retry")
    reps = _read_replicates(replicates_path) if replicates_path else None
    try:
        frame = _load_frame(input_path)
        if kind == "treatment":
            out = causal.estimate_effect(frame, outcome, treatment, confounders or [], method or "aipw", reps,
                                         calibrate=calibrate)
            e = out["ate"]; summary = f"Average treatment effect {e['estimate']:.4g} (90% CI {e['lower']:.4g} to {e['upper']:.4g})."
        elif kind == "iv":
            out = causal.iv_slope(frame, outcome, x, instrument, controls or [])
            e, ar = out["iv"], out["ar_interval"]
            ar_text = {"bounded": f"{ar['lower']:.4g} to {ar['upper']:.4g}", "real_line": "unbounded (whole line)",
                       "disjoint": f"outside ({ar['lower']:.4g}, {ar['upper']:.4g})", "empty": "empty"}[ar["kind"]]
            summary = (f"2SLS slope {e['estimate']:.4g} ({e['lower']:.4g} to {e['upper']:.4g}); Anderson-Rubin "
                       f"{ar_text}; first-stage F {out['first_stage_f']:.1f}; naive OLS {out['ols_naive']['estimate']:.4g}."
                       + (" Weak instrument: report the Anderson-Rubin interval." if out["first_stage_f"] < causal.IV_UNSTABLE_F else ""))
        elif kind == "mediation":
            out = causal.mediation(frame, x, mediator, outcome, controls or [], method or "bootstrap", reps,
                                   calibrate=calibrate)
            e = out["indirect"]; summary = f"Indirect effect {e['estimate']:.4g} ({e['lower']:.4g} to {e['upper']:.4g})."
        else:
            return _fail(errors.INVALID_INPUT, "kind must be 'treatment', 'iv' or 'mediation'.")
    except _INPUT_ERRORS as exc:
        return _fail(errors.INVALID_INPUT, f"{type(exc).__name__}: {exc}", "check the columns for this kind, then retry")
    from census.results import _jsonable
    return _ok(summary + (" Validated." if out["validated"] else " Exploratory: see notes."),
               "report the estimate with its interval and the assumptions in notes", **_jsonable(out))


def small_area_estimates(
    input_path: str,
    formula: str,
    se_col: str,
    method: str = "REML",
    output_path: Optional[str] = None,
    figure_dir: Optional[str] = None,
    transform: Optional[str] = None,
    n_col: Optional[str] = None,
    temporal: bool = False,
    release_column: str = "Year",
) -> Dict[str, Any]:
    """Sharpen noisy small-area estimates (tracts, small counties) with the
    Fay-Herriot model, which borrows strength from covariates.
    Round 80: transform="arcsine" for proportions near 0 or 1 (outcome a proportion or percent; n_col optional
    effective sample size, needed where the direct estimate is 0 or 1); temporal=True borrows strength across 2-3
    NON-overlapping releases (release_column) and estimates the latest release (Rao-Yu).

    Args:
        input_path: Analysis frame with the outcome, its SE column, and covariates.
        formula: e.g. "poverty_rate ~ unemployment_rate + median_rent".
        se_col: The outcome's standard error column, e.g. "poverty_rate_se".
        method: "REML" (default), "ML", or "FH".
        output_path: CSV of EBLUPs, MSEs, intervals, and shrinkage (gamma).
        figure_dir: Also write a shrinkage plot here.

    gamma near 0 means the area was pulled almost entirely to the model.
    """
    from census.sae import fay_herriot

    if transform not in (None, "arcsine") or (transform and temporal):
        return _fail(errors.INVALID_INPUT, "transform must be 'arcsine' (or omitted); it cannot be combined with temporal.")
    if transform or temporal:
        from census import sae_extensions as sx
        try:
            frame = _load_frame(input_path)
            est = (sx.arcsine_small_area(frame, formula, se_col, n_col=n_col) if transform
                   else sx.temporal_small_area(frame, formula, se_col, release_column=release_column))
        except _INPUT_ERRORS as exc:
            return _fail(errors.INVALID_INPUT, f"{type(exc).__name__}: {exc}",
                         "check the formula, columns and releases, then retry")
        path = _write_frame(est, output_path, "small_area_estimates.csv")
        kind = "arcsine Fay-Herriot" if transform else f"Rao-Yu temporal Fay-Herriot (latest release {est['release'].iloc[0]})"
        state = "validated" if est.attrs["validated"] else "exploratory (see the audit)"
        return _ok(f"{kind} estimates for {len(est)} areas; {state}.",
                   "report the estimates with their bootstrap-MSE intervals and the direct estimates",
                   output_path=path, preview=_records(est, 10),
                   **{k: v for k, v in est.attrs.items() if k in ("validated", "interval", "sigma2_u", "sigma2_v", "rho", "releases", "audit")})
    try:
        res = fay_herriot(formula, _load_frame(input_path), se_col, method=method)
    except _INPUT_ERRORS as exc:
        return _fail(errors.INVALID_INPUT, f"{type(exc).__name__}: {exc}",
                     "check the formula, column names, and input file, then retry")
    path = _write_frame(res.estimates, output_path, "small_area_estimates.csv")
    payload: Dict[str, Any] = {"output_path": path, "sigma2_u": res.sigma2_u,
                               "coefficients": res.coefficients, "notes": res.notes,
                               "preview": _records(res.estimates, 10)}
    if figure_dir:
        from census.figures import shrinkage_plot

        fig = shrinkage_plot(res, out_dir=_out_dir(figure_dir, "figures"))
        payload["figure_paths"] = [str(p) for p in (fig.paths.values() if isinstance(fig.paths, dict) else fig.paths)]
    return _ok(
        f"Fay-Herriot ({method}) estimates for {len(res.estimates)} areas; sigma2_u={res.sigma2_u:.4g}.",
        "make_table or make_figure; report EBLUPs with their MSE-based intervals",
        **payload,
    )


def correlation_matrix(
    input_path: str,
    variables: List[str],
    method: str = "pearson",
    replicates_path: Optional[str] = None,
    disattenuate: bool = False,
    figure_dir: Optional[str] = None,
    controls: Optional[List[str]] = None,
    spatial: bool = False,
) -> Dict[str, Any]:
    """Correlations among ACS variables with confidence intervals, corrected
    p-values, design-based SEs from replicates, and optional correction for the
    weakening caused by sampling error (reported next to, never instead of, r).

    Args:
        input_path: Analysis frame.
        variables: Two or more variable names.
        method: "pearson", "spearman", "kendall", or "partial" (Pearson given controls).
        replicates_path: From build_analysis_frame, for replicate SEs (Pearson and partial
            intervals are validated only with replicates).
        controls: Variables held constant (method="partial").
        disattenuate: Also report correlations corrected for sampling error.
        figure_dir: Also write a heatmap here.
        spatial: Neighbouring areas are alike (spatial dependence): widen the validated
            intervals with the effective sample size (Round 48; county or tract GEOIDs).
    """
    from census.correlation import correlation_matrix as _corr, validated_correlations

    if len(variables or []) < 2:
        return _fail(errors.INVALID_INPUT, "Pass at least two variables.")
    try:
        frame = _load_frame(input_path)
        reps = _read_replicates(replicates_path)
        coords = None
        if spatial:
            from census.small_spatial import frame_coordinates
            coords = frame_coordinates(frame)
        table = validated_correlations(frame, variables, method, reps, controls or (), coords=coords)
        if method in ("kendall", "partial"):
            n_ok = int(table["validated"].sum())
            return _ok(f"{method.title()} correlations among {len(variables)} variables; {n_ok} of {len(table)} "
                       "intervals validated.", "report r with its interval" + ("" if spatial else "; areas are assumed independent"),
                       validated_intervals=table.to_dict("records"))
        res = _corr(frame, variables, method=method, replicates=reps, disattenuate=disattenuate)
    except _INPUT_ERRORS as exc:
        return _fail(errors.INVALID_INPUT, f"{type(exc).__name__}: {exc}",
                     "check the formula, column names, and input file, then retry")
    payload = res.to_dict()
    payload["validated_intervals"] = table.to_dict("records")
    if figure_dir:
        from census.figures import correlation_heatmap

        fig = correlation_heatmap(res, out_dir=_out_dir(figure_dir, "figures"))
        payload["figure_paths"] = [str(p) for p in (fig.paths.values() if isinstance(fig.paths, dict) else fig.paths)]
    return _ok(f"{method.title()} correlations among {len(variables)} variables.",
               "make_table (correlation) or report r with its interval", **payload)


def minimum_detectable_difference(
    moe1: float,
    moe2: Optional[float] = None,
    confidence: float = 0.90,
    power: float = 0.80,
    year1: Optional[int] = None,
    year2: Optional[int] = None,
) -> Dict[str, Any]:
    """Smallest difference between two estimates these margins of error can detect.

    Args:
        moe1, moe2: Published 90% MOEs (moe2 defaults to moe1).
        confidence: Test confidence level. power: Desired power.
        year1, year2: Releases, to account for overlapping 5-year periods.

    Example: minimum_detectable_difference(2.1, 2.4) -> about 4.8 points (90% confidence, 80% power).
    """
    from census.planning import minimum_detectable_difference as _mdd

    res = _mdd(moe1, moe2, confidence=confidence, power=power, year1=year1, year2=year2)
    value = res.get("mdd") if isinstance(res, dict) else None
    return _ok(f"Minimum detectable difference: {value}.",
               "if too large, aggregate geographies (aggregate_geographies) or use non-overlapping years",
               **res)


def reliability_profile(input_path: str, variables: Optional[List[str]] = None,
                        allocation_tables: Optional[List[str]] = None, year: Optional[int] = None) -> Dict[str, Any]:
    """Distribution of coefficients of variation for each variable in a file:
    how many estimates are high (CV<=12%), moderate, or low (CV>30%) reliability.
    Use before choosing a geography level or model.
    allocation_tables (Round 82): ACS table or variable codes (e.g. ["B27010", "B18101"]); adds the share of
    answers the Census Bureau allocated (imputed) per area from the matching B99 tables for `year`, flagged above
    5% (item nonresponse worth discussing)."""
    from census.planning import reliability_profile as _profile

    try:
        frame = _load_frame(input_path)
        res = _profile(frame, variables)
        extra: Dict[str, Any] = {}
        if allocation_tables:
            from census import epi_reporting as er
            b99 = [b for t in allocation_tables for b in (er.allocation_tables_for(t) or ([t] if str(t).upper().startswith("B99") else []))]
            if not b99:
                return _fail(errors.INVALID_INPUT, "no B99 allocation table is mapped for those codes.")
            geo = frame["GEOID"].astype(str)
            level = {2: "state", 5: "county", 11: "tract"}.get(int(geo.str.len().max()))
            if level is None or year is None:
                return _fail(errors.INVALID_INPUT, "allocation needs state, county or tract GEOIDs and year.")
            shares = er.fetch_allocation(b99, int(year), level, sorted(geo.str[:2].unique()))
            summary = er.allocation_summary(shares, geo)
            extra = {"allocation": summary, "allocation_notes": er.allocation_note(summary)}
    except _INPUT_ERRORS as exc:
        return _fail(errors.INVALID_INPUT, f"{type(exc).__name__}: {exc}",
                     "check the formula, column names, and input file, then retry")
    return _ok(f"Reliability profile for {len(res)} variable(s)."
               + (f" Allocation above 5% for {sum(r['above_limit'] for r in extra['allocation'])} table(s)."
                  if extra else ""),
               "build_analysis_frame with the reliable variables"
               + ("; report allocation shares above 5% as a limitation" if extra.get("allocation_notes") else ""),
               profile=_records(res), **extra)


def trend_test(years: List[int], estimates: List[float], moes: List[float],
               confidence_level: float = 0.90) -> Dict[str, Any]:
    """Test for a linear trend across three or more NON-overlapping ACS 5-year
    releases (e.g. 2013, 2018, 2023). Overlapping releases are refused with a
    suggested non-overlapping set.

    Example: trend_test([2013, 2018, 2023], [14.1, 13.0, 11.8], [0.4, 0.4, 0.3])
    """
    from census.trends import linear_trend_test

    from census.trends import overlap_design_check

    try:
        design = overlap_design_check(years)
    except ValueError as exc:
        return _fail(errors.INVALID_INPUT, str(exc))
    if design.get("overlapping"):
        latest = max(int(y) for y in years)
        example = [latest - 10, latest - 5, latest]
        return _fail(
            errors.INVALID_INPUT,
            f"Releases {sorted(years)} overlap: 5-year releases less than 5 years apart share sample "
            f"years, so a trend test across them overstates precision. Use releases at least 5 years "
            f"apart, e.g. {example}.",
            f"download releases {example} and call trend_test again",
        )
    try:
        res = linear_trend_test(years, estimates, moes=moes, confidence_level=confidence_level)
    except ValueError as exc:
        return _fail(errors.INVALID_INPUT, str(exc))
    sig = res.get("significant")
    return _ok(f"Trend slope {res.get('slope')} per year; significant: {sig}.",
               "make_figure(kind='trend') to plot it", **res)


def make_figure(
    kind: str,
    input_path: str,
    output_dir: Optional[str] = None,
    label_col: Optional[str] = None,
    estimate_col: Optional[str] = None,
    moe_col: Optional[str] = None,
    se_col: Optional[str] = None,
    period_col: Optional[str] = None,
    width: str = "one",
    data_source: str = "",
) -> Dict[str, Any]:
    """Journal-ready figure (PDF, SVG, EPS, PNG) with a values CSV, draft caption,
    and provenance file.

    Args:
        kind: "estimates" (estimates with 90% intervals; needs label_col,
            estimate_col, moe_col or se_col), "forest" (input is a
            batch_significance output), or "trend" (needs period_col, estimate_col,
            moe_col or se_col).
        input_path: CSV/Parquet with the values.
        output_dir: Folder for the files (default downloads/figures).
        width: "one" or "two" journal columns.
        data_source: Text for the caption, e.g. "ACS 5-year 2019-2023, table B17001".

    Model, correlation, and small-area figures come from fit_model,
    correlation_matrix, and small_area_estimates via their figure_dir argument.
    """
    from census import figures

    if kind not in _FIGURE_KINDS:
        return _fail(errors.INVALID_INPUT, f"kind must be one of {_FIGURE_KINDS}.")
    folder = _out_dir(output_dir, "figures")
    try:
        df = _load_frame(input_path)
        common = {"out_dir": folder, "width": width, "data_source": data_source}
        if kind == "estimates":
            fig = figures.estimates_with_intervals(df, label_col, estimate_col, se_col=se_col, moe_col=moe_col, **common)
        elif kind == "forest":
            fig = figures.forest_plot(df, label_col=label_col, **common)
        else:
            fig = figures.trend_plot(df, period_col, estimate_col, se_col=se_col, moe_col=moe_col, **common)
    except (FileNotFoundError, OSError, KeyError, ValueError, TypeError) as exc:
        return _fail(errors.INVALID_INPUT, str(exc))
    paths = fig.paths.values() if isinstance(fig.paths, dict) else fig.paths
    return _ok(f"Wrote {kind} figure '{fig.name}'.", "make_table, or include the PDF/SVG and caption in your write-up",
               figure_paths=[str(p) for p in paths], caption=fig.caption)


def make_table(kind: str, input_path: str, output_dir: Optional[str] = None,
               variables: Optional[List[str]] = None, name: str = "table", exposure: Optional[str] = None,
               population: Optional[str] = None, confidence_level: Optional[float] = None) -> Dict[str, Any]:
    """Publication table as LaTeX (booktabs), Markdown, and CSV.

    Args:
        kind: "descriptive" (variables from an analysis frame), "comparison" (a batch_significance output file) or
            "table1" (Round 82: the study areas described by tertiles of `exposure`, with `variables` and optional
            `population`; the "Table 1" of an epidemiologic report).
        input_path: The file. variables: For descriptive and table1 tables.
        confidence_level: comparison tables only: re-express the intervals at this level (e.g. 0.95 for health
            journals); tests and p-values are unchanged.
        output_dir: Folder (default downloads/tables).
    """
    from census import report_tables

    folder = _out_dir(output_dir, "tables")
    try:
        df = _load_frame(input_path)
        if kind == "descriptive":
            table = report_tables.descriptive_table(df, variables or [c for c in df.columns if f"{c}_se" in df.columns])
        elif kind == "comparison":
            table = report_tables.comparison_table(df, confidence_level=confidence_level)
        elif kind == "table1":
            if not exposure or not variables:
                return _fail(errors.INVALID_INPUT, "kind='table1' needs exposure and variables.")
            table = report_tables.table_one_table(df, exposure, variables, population=population)
        else:
            return _fail(errors.INVALID_INPUT, "kind must be 'descriptive', 'comparison' or 'table1'.")
        written = table.write(folder, name)
    except _INPUT_ERRORS as exc:
        return _fail(errors.INVALID_INPUT, f"{type(exc).__name__}: {exc}",
                     "check the formula, column names, and input file, then retry")
    files = list(written.values()) if isinstance(written, dict) else written
    return _ok(f"Wrote {kind} table '{name}'.", "include the .tex or .md table in your write-up",
               table_paths=[str(p) for p in files], markdown=table.to_markdown())


def _extraction_record(meta: Dict[str, Any]) -> Dict[str, Any]:
    """Provenance fields of an extraction metadata JSON."""
    return {"table": meta.get("table_code"), "dataset": meta.get("dataset"), "years": meta.get("years"),
            "geo_level": meta.get("geo_level"), "endpoint": meta.get("endpoint"),
            "states": sorted({e.get("state_code") for e in meta.get("entities") or [] if e.get("state_code")}),
            "variables": meta.get("variables"), "generated_at": meta.get("generated_at"),
            "package_version": meta.get("package_version"), "git_commit": meta.get("git_commit"),
            "failed_calls": len(meta.get("failed_calls") or []), "data_source": meta.get("data_source")}


def _recorded_source(doc: Any) -> Optional[Dict[str, Any]]:
    """The data source a saved JSON (extraction metadata, tool result, manifest run or bundle)
    recorded when its data were read: {"synthetic": bool, ...}, or None when it records none."""
    if not isinstance(doc, dict):
        return None
    for source in (doc.get("data_source"), (doc.get("provenance") or {}).get("data_source")):
        if isinstance(source, dict) and isinstance(source.get("synthetic"), bool):
            return source
    return None


def _input_names(paths: List[str]) -> List[str]:
    """Input paths relative to their common folder ('/'-separated), so same-named files from
    different folders (extract/26/B19013/..., extract/36/B19013/...) stay distinguishable."""
    full = [os.path.abspath(p) for p in paths]
    if not full:
        return []
    try:
        common = os.path.commonpath([os.path.dirname(p) for p in full])
    except ValueError:  # different drives (Windows): keep the parent folder name
        return [f"{os.path.basename(os.path.dirname(p))}/{os.path.basename(p)}" for p in full]
    return [os.path.relpath(p, common).replace(os.sep, "/") for p in full]


def _bundle_source(recorded: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Bundle data source from the inputs' recorded sources (each {path, synthetic, ...})."""
    if not recorded:
        return {"kind": "unknown", "synthetic": None}
    synthetic = [r for r in recorded if r["synthetic"]]
    if not synthetic:
        return {"kind": "census_api", "synthetic": False}
    marker = {k: synthetic[0][k] for k in ("description", "generator") if synthetic[0].get(k)}
    return {"kind": "synthetic" if len(synthetic) == len(recorded) else "mixed", "synthetic": True, **marker}


def make_results_bundle(
    output_dir: str,
    results: Dict[str, str],
    figure_paths: Optional[List[str]] = None,
    inputs: Optional[List[str]] = None,
    title: str = "",
    notes: Optional[List[str]] = None,
    allow_failed_results: bool = False,
    design: str = "area",
) -> Dict[str, Any]:
    """Collect an exploratory (not pre-registered) analysis into one results bundle:
    results JSON, figures, methods.md, and bundle.json with every file's SHA-256,
    the data citation and provenance (data source, input hashes, extractions).

    Args:
        output_dir: Fresh or empty bundle folder; existing artifacts are preserved and refused.
        results: {name: path} of tool results saved with `python -m census tool ... --save PATH`.
            Names must be portable filename components, not paths; case-insensitive
            collisions within a bundle category are refused before bundle writes.
            A saved failure (success false) is refused unless allow_failed_results=True,
            which lists it under "Failed steps" in methods.md, never as a result.
        figure_paths: Figure files to copy (e.g. make_map figure_paths).
        inputs: Files the analysis used (extraction metadata JSON, frames, replicate
            files); their SHA-256 (keyed by the path relative to the inputs' common
            folder) and, for extraction metadata, table, years, states, endpoint,
            call failures and data source are recorded.
        title, notes: Methods heading and extra methods/limitations lines.
        design: "area" (default; adds the ecologic and cross-sectional limitations, Round 82), "individual"
            (PUMS person records: cross-sectional only) or "none" (annual series, trials: no design lines).
    The data source comes from what the inputs and results recorded when their data
    were read (extraction metadata records the cache marker at extraction time): all
    synthetic -> "synthetic", none synthetic -> "census_api", both -> "mixed" (with a
    warning), nothing recorded -> "unknown". It is never taken from the cache present
    at bundle time. Pre-registered analyses use run_manifest instead (status "confirmatory").
    """
    from census.figures import FigureOutput
    from census.manifest import STATUS_EXPLORATORY
    from census.pipeline import file_sha256
    from census.report_tables import _require_empty_bundle, data_citation, results_bundle

    try:
        _require_empty_bundle(output_dir)
        loaded, failed, recorded = {}, [], []
        for name, path in (results or {}).items():
            with open(path, encoding="utf-8") as f:
                res = json.load(f)
            if isinstance(res, dict) and res.get("success") is False:
                failed.append({"name": name, "path": os.path.basename(path), "error_code": res.get("error_code"),
                               "error": res.get("error") or res.get("summary")})
                if not allow_failed_results:
                    return _fail(errors.INVALID_INPUT,
                                 f"Saved result '{name}' ({path}) is a failure (success false: "
                                 f"{failed[-1]['error']}); a failed step is not a result.",
                                 "fix and re-run that step, or drop it from results (allow_failed_results=True "
                                 "lists it under Failed steps, not as a result)")
                continue
            loaded[name] = res
            source = _recorded_source(res)
            if source:
                recorded.append({"path": f"results/{name}.json", **source})
        input_records, extractions = [], []
        for path, rel in zip(inputs or [], _input_names(list(inputs or []))):
            input_records.append({"path": rel, "sha256": file_sha256(path)})
            if path.lower().endswith(".json"):
                with open(path, encoding="utf-8") as f:
                    doc = json.load(f)
                if path.endswith("_extraction_metadata.json") and isinstance(doc, dict):
                    extractions.append(_extraction_record(doc))
                source = _recorded_source(doc)
                if source:
                    recorded.append({"path": rel, **source})
        figs = list(figure_paths or [])
        base = [os.path.basename(p) for p in figs]
        # same file name from different folders (e.g. maps/26/choropleth.pdf, maps/36/...): prefix the folder
        names = [b if base.count(b) == 1 else f"{os.path.basename(os.path.dirname(os.path.abspath(p)))}_{b}"
                 for p, b in zip(figs, base)]
        if len(set(names)) != len(names):
            raise ValueError("figure_paths contain the same file name twice in the same folder name")
        # Let results_bundle own all writes after its empty-destination check.
        # Each supplied path is already a rendered file, with no new caption.
        figure_specs = {name: FigureOutput(name=os.path.basename(path), paths={"file": path},
                                          values=pd.DataFrame(), caption="", provenance={})
                        for path, name in zip(figs, names)}
    except (OSError, ValueError, TypeError) as exc:
        return _fail(errors.INVALID_INPUT, f"{type(exc).__name__}: {exc}")
    source = _bundle_source(recorded)
    warnings: List[str] = []
    if source["kind"] == "mixed":
        synth = [r["path"] for r in recorded if r["synthetic"]]
        real = [r["path"] for r in recorded if not r["synthetic"]]
        warnings.append(f"MIXED DATA SOURCES: SYNTHETIC inputs ({', '.join(synth)}) are combined with Census "
                        f"Data API inputs ({', '.join(real)}). These are not Census results and must not be "
                        "reported as such; re-extract every input from one source.")
    elif source["kind"] == "unknown":
        warnings.append("DATA SOURCE UNKNOWN: no input records where its data came from; pass the extraction "
                        "metadata JSON files as inputs (they record the source observed at extraction time).")
    releases = sorted({int(y) for e in extractions for y in e.get("years") or []})
    tables = sorted({e["table"] for e in extractions if e.get("table")})
    citation = data_citation(releases, tables, synthetic=bool(source["synthetic"]),
                             description=source.get("description"), retrieved=source["kind"] != "unknown")
    if source["kind"] == "mixed":
        citation = "MIXED DATA SOURCES (some inputs synthetic): " + citation
    lines = [f"# {title or 'Results'}", "",
             f"**Analysis status:** {STATUS_EXPLORATORY} (not a pre-registered manifest run).", "",
             f"**Data:** {citation}", ""]
    for w in warnings:
        lines += [f"**WARNING:** {w}", ""]
    for name, res in loaded.items():
        lines.append(f"## {name}")
        lines.append("")
        if res.get("summary"):
            lines.append(str(res["summary"]))
            lines.append("")
        interval = res.get("interval")
        if isinstance(interval, dict) and interval.get("text"):
            lines += [f"Intervals: {interval['text']}", ""]
        for note in res.get("notes") or []:
            lines.append(f"- {note}")
        lines.append("")
    if failed:
        lines += ["## Failed steps (FAILED: not results)", ""]
        lines += [f"- {f['name']}: FAILED ({f['error_code']}): {f['error']}" for f in failed] + [""]
    from census.epi_reporting import design_labels
    design_notes = [] if design == "none" else design_labels(None, individual=design == "individual")["notes"]
    if notes or design_notes:
        lines += ["## Notes and limitations", ""] + [f"- {n}" for n in list(notes or [])+design_notes] + [""]
    provenance = {"analysis_status": STATUS_EXPLORATORY, "data_source": source, "inputs": input_records,
                  "recorded_data_sources": recorded, "extractions": extractions, "title": title}
    if warnings:
        provenance["warnings"] = warnings
    if failed:
        provenance["failed_results"] = failed
    if design != "none":
        provenance["design"] = design_labels(None, individual=design == "individual")["design"]
    try:
        bundle = results_bundle(output_dir, figures=figure_specs, methods="\n".join(lines), results=loaded,
                                provenance=provenance, citation=citation)
    except (OSError, ValueError, TypeError) as exc:
        return _fail(errors.INVALID_INPUT, f"{type(exc).__name__}: {exc}")
    return _ok(f"Results bundle with {len(loaded)} result(s), {len(figure_paths or [])} figure file(s) and "
               f"{len(input_records)} input hash(es) written; data source {source['kind']}."
               + (f" WARNING: {' '.join(warnings)}" if warnings else ""),
               "cite bundle.json (file hashes and provenance) and methods.md with the results"
               + ("; resolve the data source warning before reporting" if warnings else ""),
               output_dir=output_dir, data_source=source, citation=citation, warnings=warnings,
               results=list(loaded), files=len(bundle.get("files", {})), extractions=extractions)


def save_json(result: Dict[str, Any], path: str) -> str:
    """Write a tool result as the JSON ``--json`` prints (``python -m census tool ... --save PATH``)."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(result, indent=2, default=str) + "\n")
    return path


def list_health_sources(source: Optional[str] = None, kind: str = "outcome") -> Dict[str, Any]:
    """List external health data sources a manifest can use as an outcome, with the
    circularity rule. Read each measure's kind and acs_equivalent before designing a study.

    The rule: determinant studies keep using the ACS's own measure as the outcome (for
    disability: B18101), and use external sources such as CDC PLACES for measures the ACS
    lacks, such as diabetes. A model-based outcome (PLACES, PLACES-based County Health
    Rankings measures, USALEEP) must not be tested against its model's inputs (PLACES:
    age, sex, race/ethnicity, education, poverty). Direct vital records (County Health
    Rankings mortality, WONDER exports) have no model inputs.

    Args:
        source: places, usaleep, chr or wonder; omit for all.
        kind: "outcome" (default) or "context" (Round 72: county covariate sources such as CBP, ERS
            typology and rural-urban codes, CHR additional measures; never outcomes).

    Example: list_health_sources(source="places")
    """
    from census.health_sources import registry_summary

    if kind == "context":
        from census.context_sources import list_context_sources
        ctx = list_context_sources()
        return _ok(f"Context covariate sources: {', '.join(ctx)} (covariates only, never outcomes)",
                   "add a context entry to build_analysis_frame(context=[...]) or a manifest 'context' block",
                   sources=ctx)
    if kind != "outcome":
        return _fail(errors.INVALID_INPUT, "kind must be 'outcome' or 'context'")
    try:
        reg = registry_summary(source)
    except ValueError as exc:
        return _fail(errors.INVALID_INPUT, str(exc), "list_health_sources() to list all sources")
    names = ", ".join(reg["sources"])
    return _ok(f"External health sources: {names}. Rule: {reg['rule']}",
               "get_recipe(name='external_health_outcome'), then add an 'external' entry to a manifest",
               **reg)


def run_variant(
    run_dir: str,
    analysis: str,
    formula: Optional[str] = None,
    keep_prefixes: Optional[List[str]] = None,
    drop_prefixes: Optional[List[str]] = None,
    args: Optional[Dict[str, Any]] = None,
    output_dir: Optional[str] = None,
    label: Optional[str] = None,
) -> Dict[str, Any]:
    """Exploratory refit of one analysis of a finished run_manifest run, on the same
    hash-checked analysed data, without writing Python. The output is labelled
    exploratory with the manifest hash; confirmatory results are never changed.

    Spatial_se={"cutoff_km":150} is exploratory only (failed spatial HAC validation).
    Binomial count proportions use trials=<name>_denominator, scale:"X2".

    Args:
        run_dir: The run_manifest output folder (holds manifest.json and bundle/).
        analysis: Analysis id in the manifest, e.g. "m2".
        formula: Replacement formula (frame columns only), e.g. "y ~ x + C(GEOID.str[:5])".
        keep_prefixes / drop_prefixes: GEOID prefixes to keep or drop, e.g. ["36"].
        args: Merged over the analysis args, e.g. {"cluster": "GEOID.str[:5]",
            "cluster_se": "jackknife"}.
        label: Short name for the output file.
    Example: run_variant("studies_output/r21/confirmatory", "m1", drop_prefixes=["36005", "36047"])
    """
    from census.manifest import run_variant as _variant

    try:
        out = _variant(run_dir, analysis, formula=formula, keep_prefixes=keep_prefixes, drop_prefixes=drop_prefixes,
                       args=args, out_dir=output_dir, label=label)
    except (FileNotFoundError, OSError, ValueError, KeyError, TypeError) as exc:
        return _fail(errors.INVALID_INPUT, f"{type(exc).__name__}: {exc}",
                     "check run_dir (a run_manifest output folder) and the analysis id")
    coefs = (out.get("result") or {}).get("coefficients") or []
    head = "; ".join(f"{c['term']} {c['estimate']:.4g} (SE {c.get('se_total', c.get('se', float('nan'))):.3g})"
                     for c in coefs[:4] if isinstance(c, dict) and "estimate" in c)
    return _ok(f"Exploratory variant of {analysis} on {out['units']} units: {head}",
               "report it labelled exploratory, with related_manifest_hash", **_jsonable(out))


def create_manifest(manifest_path: str) -> Dict[str, Any]:
    """Validate a pre-registration manifest (JSON) and return its SHA-256 hash.
    Commit the manifest and hash BEFORE pulling data; then call run_manifest.
    exploratory:true labels the run exploratory. Spatial_se failed validation: exploratory only.
    Binomial external outcomes need trials=<name>_denominator and scale:"X2".
    Several states: geography {"level": "county", "states": ["26", "36"]}; a price
    adjustment: "adjustments": [{"type": "rpp", "variables": ["income"], "rpp_year": 2024}]
    (rpp_year is required; when omitted, the latest RPP year is filled in before
    hashing and the completed manifest is written to <name>.completed.json, never
    over the input; commit and run that file, as the result's notes say).
    Several releases: the adjustment also needs "dollar_year", "price_index"
    and "rpp_years" ({"2019": 2019, "2024": 2024}); omitted ones are filled the same
    way. "replicates": {"source": "census_vre"} makes run_manifest fetch Census
    replicates; the notes list variables that have none. External health outcomes
    (list_health_sources; no key): "external": [{"name": "diab", "source": "places",
    "release": 2025, "measure": "DIABETES"}], usable only as the outcome of fit_eiv/
    fit_replicate/fh_regression. Circularity rule (errors): determinant studies use the
    ACS's own measure (disability: B18101), and external sources for measures the ACS
    lacks, such as diabetes; never test a term built from the outcome model's inputs.
    fit_eiv "args": {"cluster": "GEOID.str[:5]"} clusters SEs by county.

    The schema is documented in census/manifest.py and examples/manifests/.
    Example: create_manifest("examples/manifests/income_population_tracts.json")
    """
    from census.manifest import create_manifest as _create

    try:
        res = _create(manifest_path)
    except (FileNotFoundError, OSError, ValueError, TypeError) as exc:
        return _fail(errors.INVALID_INPUT, str(exc))
    if res.get("error_code") == errors.BUNDLED_DATA_INTEGRITY:
        return res
    if res.get("errors"):
        return _fail(errors.INVALID_INPUT, "Manifest invalid: " + "; ".join(map(str, res["errors"])),
                     "fix the listed problems and call create_manifest again")
    return _ok(f"Manifest valid; SHA-256 {res['hash']}." + "".join(f" {n}." for n in res.get("notes") or []),
               "commit the manifest, then run_manifest with the same path", **res)


def run_manifest(manifest_path: str, output_dir: Optional[str] = None,
                 replicates_path: Optional[str] = None, replicates_synthetic: Optional[bool] = None,
                 checkpoint: bool = False) -> Dict[str, Any]:
    """Run a pre-registered analysis exactly as written and write a results bundle
    (tables, figures, methods.md); anything that could not run is a deviation.

    Args:
        manifest_path: the manifest JSON.
        replicates_path: optional CSV/Parquet of replicates (long: GEOID, Year,
            variable, rep_1..rep_80) for "replicates": "required"; not with census_vre.
        replicates_synthetic: mark supplied replicates synthetic.
        checkpoint: true = resumable long run (reuse output_dir).

    Returns analysis_status, data_source, replicates, deviations, hypotheses;
    success is False when analysis_status is "confirmatory_incomplete".

    Example: run_manifest("examples/manifests/income_population_tracts.json")
    """
    from census.manifest import run_manifest as _run

    folder = _out_dir(output_dir, "manifest_run")
    try:
        reps = _read_replicates(replicates_path)
    except (FileNotFoundError, OSError, ValueError, ImportError) as exc:
        return _fail(errors.INVALID_INPUT, f"replicates_path unreadable: {type(exc).__name__}: {exc}",
                     "pass a CSV or Parquet file in the analysis replicate long format")
    try:
        res = _run(manifest_path, folder, replicates=reps, replicates_synthetic=replicates_synthetic,
                   checkpoint=bool(checkpoint))
    except (FileNotFoundError, OSError, ValueError, KeyError) as exc:
        return _fail(errors.INVALID_INPUT, f"{type(exc).__name__}: {exc}" if isinstance(exc, KeyError) else str(exc))
    if res.get("error_code") == errors.BUNDLED_DATA_INTEGRITY:
        return res
    if res.get("output_error"):
        return _fail(errors.INVALID_INPUT, f"output_dir unusable: {res['output_error']}",
                     "call run_manifest again with a new or empty output_dir; the manifest is fine")
    if res.get("errors"):
        return _fail(errors.INVALID_INPUT, "Manifest invalid: " + "; ".join(map(str, res["errors"])),
                     "fix the manifest with create_manifest")
    hyp = res.get("hypotheses")
    devs = res.get("deviations") or []
    status = res.get("analysis_status")
    out = {
        "manifest_hash": res.get("manifest_hash"), "output_dir": res.get("output_dir"),
        "analysis_status": status, "data_source": res.get("data_source"), "replicates": res.get("replicates"),
        "deviations": devs, "hypotheses": hyp, "bundle": res.get("bundle"),
    }
    if "adjustments" in res:
        out["adjustments"] = res["adjustments"]
    if "checkpoint" in res:
        out["checkpoint"] = res["checkpoint"]
    if "external" in res:
        out["external"] = res["external"]
    payload = _jsonable(out)
    if not res.get("success"):
        kinds = sorted({str(d.get("kind")) for d in devs})
        payload.update({"success": False, "error_code": errors.INVALID_INPUT if "data_source_mismatch" in kinds
                        else errors.NO_DATA,
                        "error": f"Manifest ran with {len(devs)} deviation(s) that block confirmatory results "
                                 f"({', '.join(kinds)}); analysis_status {status}.",
                        "summary": f"Run incomplete ({status}): {len(devs)} deviation(s); see deviations.",
                        "next_step": "report the run as confirmatory_incomplete with its deviations; do not "
                                     "substitute variables, releases or data sources"
                                     + ("; supply replicates_path" if "replicates_unavailable" in kinds else "")})
        return payload
    return _ok(f"Manifest run complete ({status}); {len(devs)} deviation(s); results in {res.get('output_dir')}.",
               "read methods.md and the tables in the output folder; report deviations if any",
               **out)


def interrupted_series(
    values: Optional[List[float]] = None,
    interruption_index: Optional[int] = None,
    interruption_year: Optional[int] = None,
    input_path: Optional[str] = None,
    column: Optional[str] = None,
    year_column: str = "year",
    years: Optional[List[int]] = None,
    method: str = "bootstrap_t_cons",
) -> Dict[str, Any]:
    """Level and slope change after a break in an ANNUAL series (interrupted time series; AR(1) errors).

    Give the series as values (plus years, optional) or as input_path + column (sorted by year_column), and the
    break as interruption_year or interruption_index (0-based position of the first post-break year).
    method: "bootstrap_t_cons" (default; validated for 17+ points, Round 63), "bootstrap_t_bb" (19+),
    "bootstrap_t_bc" (20+), "bootstrap_t" (30+), "reml" or "ar1" (not validated). Below 17 points no method is
    validated: results are exploratory.
    Not for ACS five-year releases: consecutive releases overlap (4 of 5 years shared), so they are not annual
    observations; use trend_test with non-overlapping releases. Years must be consecutive.
    Example: interrupted_series(values=[...18 annual rates...], years=[2005, ..., 2022], interruption_year=2014)
    """
    from census.missing_censored_its import interrupted_series as _its

    try:
        if input_path is not None:
            if values is not None or not column:
                return _fail(errors.INVALID_INPUT, "give either values, or input_path with column.")
            frame = _load_frame(input_path)
            if year_column not in frame or column not in frame:
                return _fail(errors.INVALID_INPUT, f"input needs columns {year_column!r} and {column!r}.")
            frame = frame[[year_column, column]].dropna().sort_values(year_column)
            years, values = [int(y) for y in frame[year_column]], [float(v) for v in frame[column]]
        if not values:
            return _fail(errors.INVALID_INPUT, "values (or input_path with column) are required.")
        if years is not None:
            if len(years) != len(values):
                return _fail(errors.INVALID_INPUT, "years and values must have the same length.")
            if any(b - a != 1 for a, b in zip(years, years[1:])):
                return _fail(errors.INVALID_INPUT,
                             "years must be consecutive annual years. Overlapping ACS five-year releases are not "
                             "annual observations; compare non-overlapping releases with trend_test.",
                             "use an annual source, or trend_test for ACS five-year releases")
        if interruption_year is not None:
            if years is None or interruption_year not in years:
                return _fail(errors.INVALID_INPUT, "interruption_year needs years containing it.")
            interruption_index = years.index(interruption_year)
        if interruption_index is None or not 2 <= interruption_index <= len(values) - 2:
            return _fail(errors.INVALID_INPUT, "give interruption_year or interruption_index, with at least two "
                         "points on each side.")
        res = _its(values, interruption_index, method=method)
    except (ValueError, KeyError, TypeError) as exc:
        return _fail(errors.INVALID_INPUT, str(exc))
    lc, sc = res["level_change"], res["slope_change"]
    state = "validated" if res["validated"] else "exploratory (not validated for this method and length)"
    return _ok(f"{len(values)}-point series, {method}: level change {lc['estimate']:.4g} "
               f"({lc['lower']:.4g} to {lc['upper']:.4g}), slope change {sc['estimate']:.4g} "
               f"({sc['lower']:.4g} to {sc['upper']:.4g}); {state}.",
               "report both changes with their intervals and the AR(1) and linear-trend assumptions"
               if res["validated"] else "label the result exploratory; validated methods need 17+ annual points",
               **res)


def disparity_measures(
    input_path: str,
    groups: List[str],
    populations: List[str],
    reference: Optional[str] = None,
    replicates_path: Optional[str] = None,
    counts: bool = False,
    omitted_groups: Optional[List[str]] = None,
    decompose_areas: Optional[List[str]] = None,
    confidence_level: float = 0.90,
) -> Dict[str, Any]:
    """Disparities BETWEEN POPULATION GROUPS within each area (race/ethnicity, sex, income groups), Round 76.

    Gives the rate difference and log rate ratio of each group against a reference group, the Index of
    Disparity, the between-group variance, and Theil and mean log deviation over the groups.
    groups: one rate column per mutually exclusive group (with replicates_path), or one event-count column per group
    with counts=True (Poisson; populations are the denominators). populations: the matching group population
    columns. reference: the comparison group, chosen before looking at the data. omitted_groups: names of
    groups left out of the universe (reported).
    Validated: ACS differences and Index of Disparity up to group-rate CV .50; ratios and indices up to .30;
    counts: difference and ratio with 20+ events per group (count indices are exploratory); 2-6 groups.
    decompose_areas=[area, comparison]: instead runs a Kitagawa decomposition of the crude-rate difference into
    rate and composition effects; then groups are stratum (e.g. age band) rates or counts and populations the
    stratum populations.
    For differences ACROSS AREAS along a deprivation gradient use the health_inequality recipe instead.
    Example: disparity_measures("frame.csv", ["pov_white", "pov_black", "pov_hisp"], ["pop_white", "pop_black",
    "pop_hisp"], reference="pov_white", replicates_path="reps.parquet")
    """
    from census.disparity import disparity_measures as _dm, kitagawa_decomposition as _kd
    try:
        frame = _load_frames(input_path)
        reps = _read_replicates(replicates_path)
        if decompose_areas is not None:
            if len(decompose_areas) != 2:
                return _fail(errors.INVALID_INPUT, "decompose_areas must be [area, comparison area].")
            out = _kd(frame, decompose_areas[0], decompose_areas[1], groups, populations, replicates=reps,
                      counts=counts, level=confidence_level)
            rows = out.set_index("component")
            ok = bool(out["validated"].all())
            return _ok(f"Kitagawa {decompose_areas[0]} minus {decompose_areas[1]}: crude difference "
                       f"{rows.loc['crude_difference', 'estimate']:.4g} = rate effect "
                       f"{rows.loc['rate_effect', 'estimate']:.4g} + composition effect "
                       f"{rows.loc['composition_effect', 'estimate']:.4g}; "
                       + ("validated." if ok else "exploratory (outside the validated range; see notes)."),
                       "report both components with their intervals" if ok else "label the result exploratory",
                       rows=_records(out))
        if reference is None:
            return _fail(errors.INVALID_INPUT, "reference is required: the comparison group, declared in advance.")
        out = _dm(frame, groups, reference, populations, replicates=reps, counts=counts, level=confidence_level,
                  omitted_groups=omitted_groups)
    except (ValueError, KeyError, TypeError, FileNotFoundError) as exc:
        return _fail(errors.INVALID_INPUT, str(exc))
    n_val = int(out["validated"].sum())
    return _ok(f"{out['GEOID'].nunique()} area(s), {len(groups)} groups vs {reference}: {len(out)} measure rows, "
               f"{n_val} validated, {len(out) - n_val} exploratory.",
               "report absolute (rd, bgv) and relative (log_rr, idisp, theil, mld) measures together, with intervals; "
               "label rows with validated=False exploratory",
               audit=out.attrs["audit"], rows=_records(out))
def joinpoint(
    years: Optional[List[int]] = None,
    counts: Optional[List[float]] = None,
    population: Optional[List[float]] = None,
    rates: Optional[List[float]] = None,
    se: Optional[List[float]] = None,
    input_path: Optional[str] = None,
    year_column: str = "year",
    max_joinpoints: int = 3,
    product: str = "annual",
    rate_ratio: Optional[Dict[str, List[float]]] = None,
) -> Dict[str, Any]:
    """Joinpoint regression of an ANNUAL rate series (Round 77): where did the trend change, and the annual percent
    change (APC) of each segment plus the average APC (AAPC), as NCI Joinpoint reports them.

    Give years with counts + population (e.g. deaths and population per year), or rates + se; or input_path with
    those column names. Complete years only (suppressed years are refused). Not for overlapping ACS five-year
    releases. For a known policy date use interrupted_series instead.
    rate_ratio={"cases1": [...], "population1": [...], "cases2": [...], "population2": [...], "standard": [...]}
    instead returns the ratio of two directly age-adjusted rates with the Tiwari interval.
    Example: joinpoint(years=[1999, ..., 2022], counts=[...], population=[...])
    """
    from census import joinpoint as jp
    try:
        if rate_ratio is not None:
            r = jp.age_adjusted_rate_ratio(**rate_ratio)
            return _ok(f"Age-adjusted rate ratio {r['ratio']:.4g} ({r['ci_lower']:.4g} to {r['ci_upper']:.4g}; "
                       f"{r['method']}); {'validated' if r['validated'] else 'exploratory'}.",
                       "report the ratio with its interval and both age-adjusted rates", **r)
        if input_path is not None:
            f = _load_frame(input_path).sort_values(year_column)
            years = [int(v) for v in f[year_column]]
            pick = lambda c: [float(v) for v in f[c]] if c in f else None  # noqa: E731
            counts, population, rates, se = pick("counts"), pick("population"), pick("rates"), pick("se")
        if not years:
            return _fail(errors.INVALID_INPUT, "years (or input_path with a year column) are required.")
        r = jp.joinpoint(years, counts=counts, population=population, rates=rates, se=se,
                         max_joinpoints=max_joinpoints, product=product)
    except (ValueError, KeyError, TypeError, FileNotFoundError) as exc:
        return _fail(errors.INVALID_INPUT, str(exc))
    seg = r["segments"]
    parts = "; ".join(f"{s.start}-{s.end}: APC {s.apc:.2f}% ({s.ci_lower:.2f} to {s.ci_upper:.2f})" for s in seg.itertuples())
    ok = all(r["validated"].values())
    return _ok(f"{r['n_joinpoints']} joinpoint(s) {r['joinpoints']}; {parts}; AAPC {r['aapc']['aapc']:.2f}%; "
               + ("validated." if ok else "partly exploratory (see validated and notes)."),
               "report each segment's APC and the AAPC with intervals; say that joinpoint locations are estimated",
               **{**r, "segments": seg.to_dict("records")})


def spatial_scan(
    input_path: str,
    cases: str,
    population: Optional[str] = None,
    expected: Optional[str] = None,
    year: Optional[int] = None,
    max_share: float = 0.5,
    exclude: Optional[List[str]] = None,
    exclude_rule: Optional[str] = None,
    prespecified: bool = False,
) -> Dict[str, Any]:
    """Find clusters of COUNTIES with unusually high counts (Kulldorff Poisson spatial scan, Round 81).

    input_path: county frame (GEOID) with a count column (cases) and population, or expected counts (e.g. from
    indirect standardisation). Circular windows up to max_share of the expected total (0.5 is validated); Monte
    Carlo p-values (999 data sets). Missing (suppressed) counts are refused: list those counties in exclude with an
    exclude_rule. Exploratory unless prespecified=True (window and alpha declared in advance). For a map of local
    autocorrelation use spatial_autocorrelation instead.
    Example: spatial_scan("counties.csv", cases="lbw_births", population="births")
    """
    from census.scan import spatial_scan as _scan
    try:
        r = _scan(_load_frame(input_path), cases, population=population, expected=expected, year=year,
                  max_share=max_share, exclude=exclude, exclude_rule=exclude_rule, prespecified=prespecified)
    except (ValueError, KeyError, TypeError, FileNotFoundError) as exc:
        return _fail(errors.INVALID_INPUT, str(exc))
    p = r["primary"]
    if p is None:
        return _ok("No window has more cases than expected.", "report that no high-rate cluster was found", **r)
    return _ok(f"Primary cluster: {len(p['counties'])} counties around {p['center']}, RR {p['relative_risk']:.2f}, "
               f"p = {p['p_value']:.3g}; {len(r['secondary'])} secondary cluster(s). "
               + ("Confirmatory (pre-specified)." if r["confirmatory"] else "Exploratory."),
               "report the cluster counties, RR and p-value; describe it as exploratory unless pre-specified", **r)


def designation_accuracy(
    input_path: str,
    column: str,
    threshold: float,
    se_col: Optional[str] = None,
    n_col: Optional[str] = None,
    covariates: Optional[List[str]] = None,
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """How accurate is designating areas by a threshold on a noisy ACS rate (Round 85)? E.g. "tracts with poverty
    at least 20%".

    Returns each area's probability of truly exceeding the threshold (Fay-Herriot posterior with optional
    covariates; validated) and, for the rules point (estimate >= threshold), lower (lower 90% bound >= threshold),
    prob50 and prob80 (probability >= .5 / .8), the number designated and the expected sensitivity, specificity, PPV
    and NPV (exploratory). column: a proportion or percent; se_col its SE (or n_col effective sample sizes).
    Example: designation_accuracy("tracts.csv", "poverty", 20, se_col="poverty_se", covariates=["unemployment"])
    """
    from census.designation import designation_accuracy as _da
    try:
        r = _da(_load_frame(input_path), column, threshold, se_col=se_col, n_col=n_col, covariates=covariates or [])
    except (ValueError, KeyError, TypeError, FileNotFoundError, np.linalg.LinAlgError) as exc:
        return _fail(errors.INVALID_INPUT, str(exc))
    path = _write_frame(r["areas"], output_path, "designation_accuracy.csv")
    rules = r["rules"]
    txt = "; ".join(f"{x.rule}: {x.designated} areas, PPV {x.ppv:.2f}, sensitivity {x.sensitivity:.2f}"
                    for x in rules.itertuples())
    return _ok(f"Expected {r['expected_qualifying']:.0f} areas truly above {threshold}; {txt} (expected accuracy "
               "exploratory).", "report the designated list with the rule's expected PPV and sensitivity",
               output_path=path, rules=_records(rules), threshold=r["threshold"], validated=r["validated"],
               notes=r["notes"], audit=r["audit"], preview=_records(r["areas"], 10))
