# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 10 workflows (PUMS microdata, research designs, place price levels,
interactive maps) shared by the MCP server and the CLI. Same conventions as
census.workflows_inference: plain arguments in, JSON-safe dicts out, with
``summary`` and ``next_step``; failures carry ``error_code``.
"""

import os
import re
from typing import Any, Dict, List, Optional, Union
import pandas as pd
import numpy as np

from census import errors
from census.data_integrity import BundledDataIntegrityError, integrity_error_result
from census.workflows import _load_frame, _records, _write_frame
from census.results import interval_description
from census.workflows_inference import _fail, _ok, _out_dir, _read_replicates, interval_next_step, result_summary

_ERRORS = (FileNotFoundError, OSError, KeyError, ValueError, TypeError, RuntimeError, ZeroDivisionError)
_PUMS_NAME = re.compile(r"\b[A-Z][A-Z0-9_]{1,15}\b")


def _pums_columns(*texts: Optional[str]) -> List[str]:
    """PUMS variable names mentioned in var/by/where/formula text (upper-case codes)."""
    names: List[str] = []
    for text in texts:
        for name in _PUMS_NAME.findall(text or ""):
            if name not in names and name not in ("AND", "OR", "NOT", "IN"):
                names.append(name)
    return names


def _memory_warnings(df: Any) -> List[str]:
    """attrs["memory_note"] from census.pums.read_pums_csv (columns=None on a large file), as a list."""
    note = (getattr(df, "attrs", None) or {}).get("memory_note")
    return [f"MEMORY: {note}"] if note else []


def _warning_suffix(warns: List[str]) -> str:
    return f" WARNING: {' '.join(warns)}" if warns else ""


def pums_tabulate(
    state: str,
    year: int,
    statistic: str = "count",
    var: Optional[str] = None,
    by: Optional[str] = None,
    where: Optional[str] = None,
    weight: str = "person",
    product: str = "5-year",
    output_path: Optional[str] = None,
    denominator: Optional[str] = None,
) -> Dict[str, Any]:
    """Custom tabulation from ACS PUMS microdata with replicate-weight standard
    errors (Census successive-difference replication, 80 replicate weights).

    Use it when no published table crosses the variables you need.

    Args:
        state: 2-digit FIPS. year: release end year. product: "5-year" or "1-year".
        statistic: "count", "mean", "proportion", "median", or "ratio".
        var: PUMS variable (e.g. "PINCP"); by: grouping variable (e.g. "PUMA" or "DIS").
        where: pandas query on PUMS codes, e.g. "AGEP >= 25 and AGEP < 65".
        weight: "person" (PWGTP) or "housing" (WGTP).
        denominator: required for statistic="ratio": sum(w*var) / sum(w*denominator),
            e.g. var="WAGP", denominator="PINCP" (records with both defined).
    Estimates from fewer than 30 records or with CV above 30% are flagged, not
    suppressed. Results reproduce Census PUMS verification estimates.
    Example: pums_tabulate("56", 2024, "median", var="PINCP", where="AGEP >= 15")
    """
    from census import pums

    record = "housing" if weight == "housing" else "person"
    try:
        columns = _pums_columns(var, by, where, denominator)
        df = pums.fetch_pums(state, year, product=product, record=record, columns=columns or None)
        out = pums.tabulate(df, statistic, var, by=by, where=where, weight=weight, denominator=denominator)
    except _ERRORS as exc:
        return _fail(errors.INVALID_INPUT, str(exc))
    path = _write_frame(out, output_path, "pums_tabulation.csv")
    flags = [c for c in ("flag_small_n", "flag_high_cv", "flag_se_undefined") if c in out.columns]
    flagged = int(out[flags].astype(bool).any(axis=1).sum()) if flags else 0
    warns = _memory_warnings(df)
    return _ok(f"PUMS {statistic} for {len(out)} cell(s); {flagged} flagged (fewer than 30 records, "
               "CV over 30%, or undefined uncertainty)." + _warning_suffix(warns),
               "report estimates with their MOE; treat flagged cells with caution",
               output_path=path, preview=_records(out, 20), warnings=warns)


_ASSOCIATION_KINDS = ("independence", "two_by_two", "means", "medians", "proportion", "inequality")


def test_association(
    state: str,
    year: int,
    kind: str,
    row: Optional[str] = None,
    col: Optional[str] = None,
    var: Optional[str] = None,
    by: Optional[str] = None,
    exposure: Optional[str] = None,
    outcome: Optional[str] = None,
    where: Optional[str] = None,
    weight: str = "person",
    product: str = "5-year",
    method: str = "korn_graubard",
) -> Dict[str, Any]:
    """Survey-correct tests and intervals on ACS PUMS microdata (replicate weights).

    Args:
        state: 2-digit FIPS. year: release end year. product: "5-year" or "1-year".
        kind: "independence" (row x col table; Rao-Scott test), "two_by_two"
            (exposure and outcome conditions; difference, odds ratio, relative risk),
            "means" (var by groups; difference and test), "medians" (var by two groups),
            "proportion" (share with var true; Korn-Graubard interval), or "inequality" (var: a
            nonnegative income, e.g. "HINCP" with weight="housing"; Gini, log P90/P10 and P80/P20
            validated, Round 56; Atkinson validated with transformed intervals, top share and
            Atkinson .5 from 7,000 records, Round 60; Theil exploratory; optional by with two
            groups adds the Gini difference).
        row/col, var/by, exposure/outcome: PUMS variables or conditions, e.g. "DIS",
            "HICOV == 2", "POVPIP < 100".
        where: pandas query on PUMS codes, e.g. "AGEP >= 19 and AGEP <= 64".
        weight: "person" (PWGTP) or "housing" (WGTP).
    Results say whether the procedure was validated; small groups are flagged.
    Example: test_association("26", 2022, "two_by_two", exposure="DIS == 1", outcome="POVPIP < 100")
    """
    from census import pums, pums_inference as pi

    if kind not in _ASSOCIATION_KINDS:
        return _fail(errors.INVALID_INPUT, f"kind must be one of {_ASSOCIATION_KINDS}.")
    need = {"independence": ("row", "col"), "two_by_two": ("exposure", "outcome"), "means": ("var", "by"),
            "medians": ("var", "by"), "proportion": ("var",), "inequality": ("var",)}[kind]
    given = dict(row=row, col=col, var=var, by=by, exposure=exposure, outcome=outcome)
    missing = [k for k in need if not given[k]]
    if missing:
        return _fail(errors.INVALID_INPUT, f"kind={kind!r} needs {', '.join(missing)}.",
                     f"call test_association again with {', '.join(missing)}")
    record = "housing" if weight == "housing" else "person"
    try:
        columns = _pums_columns(row, col, var, by, exposure, outcome, where)
        df = pums.fetch_pums(state, year, product=product, record=record, columns=columns or None)
        if kind == "independence":
            out = pi.independence_test(df, row, col, weight=weight, where=where)
            summary = (f"{row} and {col}: Rao-Scott p = {out['p_value']:.3g} "
                       f"(design effect {out['design_effect_mean']:.2f}; {'validated' if out['validated'] else 'exploratory'})")
        elif kind == "two_by_two":
            out = pi.two_by_two(df, exposure, outcome, weight=weight, where=where)
            o, d = out["odds_ratio"], out["difference_of_proportions"]
            summary = (f"Odds ratio {o['estimate']:.3g} (90% CI {o['lower']:.3g}-{o['upper']:.3g}); "
                       f"difference {d['estimate']:.3g} ({d['lower']:.3g} to {d['upper']:.3g})")
        elif kind == "means":
            out = pi.compare_means(df, var, by, weight=weight, where=where)
            summary = f"Means of {var} by {by}: {out['test']} p = {out['p_value']:.3g}"
        elif kind == "medians":
            out = pi.compare_medians(df, var, by, weight=weight, where=where)
            d = out["difference"]
            summary = f"Median difference {d['estimate']:.4g} (90% CI {d['lower']:.4g} to {d['upper']:.4g})"
        elif kind == "inequality":
            from census.pums_inequality import pums_inequality
            out = pums_inequality(df, var, weight=weight, where=where, by=by)
            g = out["table"].set_index("measure").loc["gini"]
            summary = f"Gini of {var} {g['estimate']:.3f} (90% CI {g['lower']:.3f}-{g['upper']:.3f})"
            if "gini_difference" in out:
                d = out["gini_difference"]
                summary += f"; Gini difference {d['estimate']:.3f} ({d['lower']:.3f} to {d['upper']:.3f})"
            out["table"] = out["table"].to_dict("records")
            for grp in out.get("groups", {}).values():
                grp["table"] = grp["table"].to_dict("records")
            out["validated"] = bool(g["validated"])
        else:
            out = pi.proportion_interval(df, var, weight=weight, where=where, method=method)
            summary = f"Proportion {out['estimate']:.4g} (90% CI {out['lower']:.4g}-{out['upper']:.4g}; {out['method']})"
    except _ERRORS as exc:
        return _fail(errors.INVALID_INPUT, f"{type(exc).__name__}: {exc}",
                     "check the variable names, conditions and universe, then retry")
    from census.results import _jsonable
    next_step = ("report the estimate with its interval" if out.get("validated", True) else
                 "treat as exploratory; see notes")
    return _ok(summary, next_step, **_jsonable(out))


def pums_regression(
    state: str,
    year: int,
    formula: str,
    weight: str = "person",
    model: str = "ols",
    where: Optional[str] = None,
    product: str = "5-year",
    target: str = "these_areas",
    marginal: Optional[str] = None,
    ecologic_check: Optional[str] = None,
) -> Dict[str, Any]:
    """Survey-weighted regression on PUMS microdata with replicate-weight SEs
    (the design-based inference Census recommends for PUMS).
    Round 84: model="logit" with marginal="<binary exposure column of the design>" adds the standardized
    (marginal) risk ratio and risk difference, the attributable fraction and the modified-Poisson prevalence ratio,
    all with replicate-weight intervals (validated). Use it whenever the outcome is common (odds ratios overstate).
    Round 87: ecologic_check="<exposure column>" adds the within-PUMA (individual), between-PUMA, contextual and
    ecologic (area-level) associations of that exposure with the formula's outcome, and the ecologic gap: how far an
    area-level analysis would be from the individual-level association (the ecologic fallacy, measured).

    Args:
        formula: e.g. "np.log(WAGP) ~ AGEP + C(SCHL)" (PUMS codes).
        model: "ols", "logit", or "poisson"; Round 49: "ordered_logit", "ordered_probit"
            (ordered categories), "mnlogit" (unordered), "median" (median regression) or
            "probit" (0/1), always with replicate-weight intervals. where: pandas query.
        target: "these_areas" (default; the coefficient in the surveyed population,
            replicate-weight SE) or "population" (model SE).
    Example: pums_regression("56", 2024, "WAGP ~ AGEP", where="WAGP > 0")
    """
    from census import pums

    record = "housing" if weight == "housing" else "person"
    try:
        df = pums.fetch_pums(state, year, product=product, record=record,
                             columns=_pums_columns(formula, where) or None)
        from census import pums_models
        if model in pums_models.MODELS:
            out = pums_models.fit_pums_model(formula, df, model=model, weight=weight, where=where)
            from census.results import _jsonable
            out["table"] = out["table"].to_dict("records")
            return _ok(f"{model} on {out['n']} PUMS records with replicate-weight intervals; "
                       + ("validated (Round 49)." if out["validated"] else "exploratory: see notes."),
                       "report coefficients with their replicate-weight intervals", **_jsonable(out))
        res = pums.pums_regression(formula, df, weight=weight, model=model, where=where, target=target)
        extra = {}
        if marginal:
            if model != "logit":
                return _fail(errors.INVALID_INPUT, "marginal measures need model='logit' with a 0/1 outcome.")
            import patsy
            from census.epi_measures import pums_marginal_measures
            sub = df.loc[pums._mask(df, where)]
            yd, Xd = patsy.dmatrices(formula, sub, return_type="dataframe", NA_action="drop")
            if marginal not in Xd.columns:
                return _fail(errors.INVALID_INPUT, f"marginal must be a design column; columns: {list(Xd.columns)}")
            if not set(np.unique(Xd[marginal])) <= {0.0, 1.0}:
                return _fail(errors.INVALID_INPUT, "marginal measures need a binary (0/1) exposure column.")
            _, W = pums._weight_matrix(sub.loc[Xd.index], weight)
            extra["marginal"] = pums_marginal_measures(yd.iloc[:, 0].to_numpy(float), Xd.to_numpy(float), W,
                                                       list(Xd.columns).index(marginal))
        eco = None
        if ecologic_check:
            from census.ecologic import ecologic_check as _eco
            if "PUMA" not in df.columns:
                df = pums.fetch_pums(state, year, product=product, record=record,
                                     columns=list(dict.fromkeys(_pums_columns(formula, where)+["PUMA"])))
            sub = df.loc[pums._mask(df, where)]
            outcome = formula.split("~")[0].strip()
            y = np.asarray(pums._values(sub, outcome), float); x = np.asarray(pums._values(sub, ecologic_check), float)
            okr = np.isfinite(y) & np.isfinite(x) & sub["PUMA"].notna().to_numpy()
            _, W = pums._weight_matrix(sub, weight)
            eco = _eco(y[okr], x[okr], sub["PUMA"].to_numpy()[okr], W[okr], binary=set(np.unique(y[okr])) <= {0.0, 1.0})
    except _ERRORS as exc:
        return _fail(errors.INVALID_INPUT, str(exc))
    out = res.to_dict()
    out.update(extra)
    if eco is not None:
        from census.results import _jsonable
        out["ecologic"] = _jsonable(eco)
    warns = _memory_warnings(df)
    return _ok(result_summary(res) + _warning_suffix(warns),
               "report coefficients with the SE named in uncertainty_sources",
               **{k: v for k, v in out.items() if k not in ("summary", "warnings")}, warnings=warns)


def multilevel_model(
    input_path: str,
    formula: str,
    groups: Union[str, List[str]],
    re_formula: Optional[str] = None,
    sampling_se: Optional[str] = None,
    replicates_path: Optional[str] = None,
    target: str = "population",
    share_intervals: bool = True,
) -> Dict[str, Any]:
    """Multilevel (mixed) model, e.g. tracts within counties, with Kenward-Roger
    small-sample intervals; ACS sampling error enters through a known level-1
    variance (sampling_se) or replicate refits.

    Args:
        groups: grouping column, e.g. "county"; or [top, middle], e.g. ["state", "county"], for a three-level
            model (Round 73: fixed-effect intervals and variance shares; no sampling_se/replicates/re_formula).
            re_formula: random slopes, e.g. "~x".
        share_intervals: three-level only; False skips the jackknife share intervals (one refit per top unit).
        sampling_se: outcome SE column (known level-1 variance).
    Validated: 90% intervals cover 0.89 in simulation.
    Example: multilevel_model("frame.parquet", "poverty_rate ~ unemployment_rate", "county", sampling_se="poverty_rate_se")
    """
    from census.multilevel import fit_multilevel

    if isinstance(groups, (list, tuple)):
        if re_formula or sampling_se or replicates_path or target != "population":
            return _fail(errors.INVALID_INPUT, "a three-level model takes no re_formula, sampling_se, replicates_path "
                         "or target")
        from census.multilevel3 import fit_three_level
        from census.results import _jsonable
        try:
            res = fit_three_level(formula, _load_frame(input_path), groups, share_intervals=share_intervals)
        except _ERRORS as exc:
            return _fail(errors.INVALID_INPUT, str(exc))
        res["table"] = res["table"].to_dict("records")
        s = res["shares"]
        return _ok(f"Three-level model: variance shares bottom {s['bottom']:.1%}, middle {s['middle']:.1%}, "
                   f"top {s['top']:.1%}; fixed effects {'validated' if res['validated'] else 'exploratory'}.",
                   "report fixed effects with intervals; share intervals are exploratory", **_jsonable(res))
    try:
        frame = _load_frame(input_path)
        res = fit_multilevel(formula, frame, groups, re_formula=re_formula, sampling_se=sampling_se,
                             replicates=_read_replicates(replicates_path), target=target)
    except _ERRORS as exc:
        return _fail(errors.INVALID_INPUT, str(exc))
    out = res.to_dict()
    return _ok(result_summary(res), interval_next_step(interval_description(res)),
               **{k: v for k, v in out.items() if k != "summary"})


def difference_in_differences(
    input_path: str,
    outcome: str,
    treated: str,
    treatment_period: Optional[int] = None,
    period: str = "Year",
    se: Optional[str] = None,
    design: str = "two_group",
    reference: Optional[int] = None,
    replicates_path: Optional[str] = None,
    target: str = "population",
    product: str = "5-year",
    period_years: Optional[int] = None,
    first_treated: Optional[str] = None,
    method: str = "sun_abraham",
    unit: str = "GEOID",
    causal_question: Optional[Dict[str, Any]] = None,
    time_varying_confounders: Optional[List[str]] = None,
    truncate_weights: bool = False,
    group: Optional[str] = None,
    affected_group: Optional[str] = None,
) -> Dict[str, Any]:
    """Difference-in-differences on area-level ACS estimates across NON-overlapping
    periods (e.g. 2013, 2018, 2023 releases); overlapping releases are refused.
    design="staggered" (Round 78): policies starting in different years in an ANNUAL panel (ACS 1-year with
    product="1-year", or another annual source; 2020 1-year refused). first_treated: column with each unit's first
    treated year (blank = never treated); treated and treatment_period are then not used. method "sun_abraham"
    (default, validated) or "callaway_santanna" (validated with se). Returns the overall ATT and an event study.

    Args:
        treated: 0/1 column marking treated areas. treatment_period: first treated release.
        se: outcome SE column (known sampling variance). design: "two_group" or "event".
        reference: pre-treatment release used as the baseline.
        product: "5-year" (default) or "1-year"; sets the period length used for
            the overlap check (5 or 1) unless period_years is given.
    With 3+ pre-periods a parallel-trends test is reported. Validated: coverage 0.90-0.91.
    Round 89: causal_question (target trial: eligibility, intervention, comparator, time_zero, outcome, follow_up,
    contrast, target) is checked; without it the result is labelled associational.
    design="triple" (Round 99): triple differences with group (e.g. age group column) and affected_group: the
    affected group's DiD minus the comparison groups' DiD within units (validated with 51 units).
    design="msm" (Round 91 / Round 106): annual panel with time_varying_confounders (e.g. unemployment) that past
    policy may affect (first_treated column; effects of the 1st, 2nd, 3rd treated year vs never). Pass
    method="gformula" (Round 106, validated .883-.920 for one time-varying confounder via Hernán & Robins ch. 21
    parametric g-formula + delete-one-unit cluster jackknife) or leave default for the exploratory IP-weighted MSM
    (truncate_weights clips weights at the 1st/99th percentiles). Units treated in the first period refused.
    Example: difference_in_differences("panel.csv", "poverty_rate", "treated", 2023, se="poverty_rate_se")
    """
    from census.api import PRODUCT_PERIOD_YEARS, normalize_product
    from census.did import difference_in_differences as _did

    if design == "staggered":
        from census.staggered import staggered_did
        try:
            if not first_treated:
                return _fail(errors.INVALID_INPUT, "design='staggered' needs first_treated (each unit's first treated year).")
            r = staggered_did(_load_frame(input_path), outcome, first_treated, period=period, unit=unit, se=se,
                              method=method, product=product)
        except _ERRORS as exc:
            return _fail(errors.INVALID_INPUT, str(exc))
        o = r["overall"]
        state = "validated" if r["validated"] else "exploratory (see notes)"
        return _with_trial(_ok(f"Staggered DiD ({r['method']}), {r['units']} units: overall ATT {o['estimate']:.4g} "
                   f"({o['ci_lower']:.4g} to {o['ci_upper']:.4g}); {state}.",
                   "report the overall ATT and the event study with intervals; check the pre-trend result",
                   **{k: (v.to_dict("records") if isinstance(v, pd.DataFrame) else v) for k, v in r.items()}),
                   causal_question, first_treated)
    if design == "triple":   # Round 99
        from census.matching import triple_difference
        if not group or affected_group is None or treatment_period is None:
            return _fail(errors.INVALID_INPUT, "design='triple' needs group, affected_group and treatment_period.")
        try:
            frame = _load_frame(input_path)
            ag = type(frame[group].dropna().iloc[0])(affected_group) if len(frame) else affected_group
            r = triple_difference(frame, outcome, unit, group, ag, period, treated, int(treatment_period))
        except _ERRORS as exc:
            return _fail(errors.INVALID_INPUT, str(exc))
        e = r["effect"]
        return _with_trial(_ok(f"Triple difference ({group} = {affected_group} vs other groups): {e['estimate']:.4g} "
                               f"(90% CI {e['lower']:.4g} to {e['upper']:.4g}; {e['clusters']} units clustered); "
                               + ("validated." if r["validated"] else "exploratory (see notes)."),
                               "report the estimate with the triple-difference assumption", **r), causal_question, treated)
    if design == "msm":
        from census.msm import marginal_structural_model
        try:
            if not first_treated:
                return _fail(errors.INVALID_INPUT, "design='msm' needs first_treated (each unit's first treated year).")
            msm_method = "gformula" if method in ("gformula", "gformula_jackknife") else "ipw"
            r = marginal_structural_model(_load_frame(input_path), outcome, first_treated, time_varying_confounders or [],
                                          period=period, unit=unit, truncate=truncate_weights, product=product,
                                          method=msm_method)
        except _ERRORS as exc:
            return _fail(errors.INVALID_INPUT, str(exc))
        e = r["effects"]
        txt = "; ".join(f"year {x['duration']}: {x['estimate']:.4g} ({x['lower']:.4g} to {x['upper']:.4g})" for x in e)
        state = "validated" if r["validated"] else "exploratory (see notes)"
        return _with_trial(_ok(f"Marginal structural model ({r['method']}), {r['units']} units, {r['treated_units']} "
                               f"treated: effect of the treated year vs never: {txt}; {state}.",
                               "report the effects by treated year with intervals; state the time-varying confounders "
                               "and the no-unmeasured-confounding assumption", **r), causal_question, first_treated)
    if treatment_period is None:
        return _fail(errors.INVALID_INPUT, "treatment_period is required for two_group and event designs.")
    try:
        years = int(period_years) if period_years is not None else PRODUCT_PERIOD_YEARS[normalize_product(product)]
        frame = _load_frame(input_path)
        res = _did(frame, outcome, treated, treatment_period, period=period, se=se, design=design,
                   reference=reference, replicates=_read_replicates(replicates_path), target=target,
                   period_years=years)
    except _ERRORS as exc:
        return _fail(errors.INVALID_INPUT, str(exc))
    out = res.to_dict()
    return _with_trial(_ok(result_summary(res), "report the DiD estimate with its interval and the parallel-trends "
                           "result", **{k: v for k, v in out.items() if k != "summary"}), causal_question, treated)


def _with_trial(result, causal_question, treatment):
    """Round 89: target-trial assessment on a successful DiD result (the design, not a diagram, handles
    confounding: parallel trends replaces adjustment)."""
    from census import causal_spec as cs
    a = cs.assess(causal_question=causal_question, treatment=treatment)
    result["causal_assessment"] = a
    if a["problems"]:
        result["summary"] += " CAUSAL SPECIFICATION PROBLEMS: " + "; ".join(a["problems"]) + "."
    elif not causal_question:
        result["summary"] += " Label: associational (no causal question specified)."
    return result


def regression_discontinuity(
    input_path: str,
    outcome: str,
    running: str,
    cutoff: float,
    treatment: Optional[str] = None,
    weight: Optional[str] = None,
    replicate_prefix: Optional[str] = None,
    bandwidth: Optional[float] = None,
    covariates: Optional[List[str]] = None,
    placebo_cutoffs: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """Regression discontinuity at a cutoff of a running variable (Round 98 / Round 105; e.g. PUMS age 65 for Medicare).
    Sharp (outcome jump) or fuzzy (treatment= column: outcome jump / treatment jump). Robust bias-corrected
    interval: discrete running variables with survey weights/replicates (weight="PWGTP", replicate_prefix="PWGTP")
    and continuous running variables (Round 105 CCT CER bandwidth h_ik * n^(-1/20)) are both validated; the density
    (manipulation) test stays exploratory. covariates: jumps that should be zero; placebo_cutoffs: fake cutoffs that
    should show none.
    Example: regression_discontinuity("pums.parquet", "HICOV", "AGEP", 65, treatment="HINS3", weight="PWGTP",
    replicate_prefix="PWGTP")
    """
    from census.rdd import regression_discontinuity as _rdd
    try:
        r = _rdd(_load_frame(input_path), outcome, running, float(cutoff), treatment=treatment, weight=weight,
                 replicate_prefix=replicate_prefix, bandwidth=bandwidth, covariates=covariates or (),
                 placebo_cutoffs=placebo_cutoffs or ())
    except _ERRORS as exc:
        return _fail(errors.INVALID_INPUT, str(exc))
    return _ok(f"{r['design'].capitalize()} RDD at {running} = {cutoff:g}: jump in {outcome} {r['estimate']:.4g} "
               f"(90% robust CI {r['lower']:.4g} to {r['upper']:.4g}); bandwidth {r['bandwidth']:.3g}; "
               + ("validated." if r["validated"] else "exploratory (see notes)."),
               "report the robust estimate and interval with the density test, covariate jumps and placebo cutoffs",
               **r)


def adjust_for_place(
    value: float,
    geography: str,
    year: int,
    state: Optional[str] = None,
    base_year: Optional[int] = None,
    product: str = "5-year",
) -> Dict[str, Any]:
    """Convert dollars to national-average purchasing power with BEA Regional
    Price Parities (state, metro area, or nonmetro portion); with base_year also
    convert to that year's dollars with R-CPI-U-RS. Never applied automatically.

    Args:
        geography: state FIPS, CBSA code, or "US". year: the dollars' year.
        product: "5-year" (default) or "1-year": the ACS product the dollars come from.
    RPPs carry their own estimation error, which is not in ACS MOEs.
    Example: adjust_for_place(75000, "06", 2023)
    """
    from census import rpp
    from census.api import PRODUCT_PERIOD_YEARS, normalize_product

    try:
        period_years = PRODUCT_PERIOD_YEARS[normalize_product(product)]
        if base_year is None:
            adjusted = rpp.adjust_for_place(value, geography, year, state=state)
        else:
            adjusted = rpp.adjust_for_place_and_time(value, geography, year, base_year, state=state)
        described = rpp.describe_place_adjustment(geography, year, state=state, base_year=base_year,
                                                  acs_period_years=period_years)
    except BundledDataIntegrityError as exc:
        return integrity_error_result(exc)
    except _ERRORS as exc:
        return _fail(errors.INVALID_INPUT, str(exc))
    return _ok(f"{value:,.0f} in {geography} ({year}) = {adjusted:,.0f} at national-average prices"
               + (f" in {base_year} dollars" if base_year else "") + ".",
               "state in results that a regional price parity adjustment was applied",
               value=value, adjusted_value=adjusted, geography=geography, year=year, base_year=base_year,
               adjustment=described)


_RPP_AREAS = ("county_metro", "state")


def _county_rpp_areas(geoids: List[str], year: int) -> Any:
    """GEOID -> CBSA membership (CBSA, CBSA_NAME, LSAD) from Census boundaries: the
    ACS release's county file and the CBSA file of BEA's delineation."""
    from census import rpp
    from census.boundaries import county_cbsa_membership, get_boundaries
    from census.workflows_geo import _fetch_boundaries

    counties = _fetch_boundaries("county", year, sorted({g[:2] for g in geoids}))
    counties = counties[counties["GEOID"].astype(str).isin(set(geoids))]
    missing = sorted(set(geoids) - set(counties["GEOID"].astype(str)))
    if missing:
        raise ValueError(f"no {year} county boundaries for {missing[:5]}")
    cbsas = get_boundaries("cbsa", rpp.RPP_CBSA_BOUNDARY_YEAR)
    return county_cbsa_membership(counties, cbsas).set_index("GEOID"), cbsas.attrs.get("source_url")


def place_adjust(frame: Any, variables: List[str], year: int, areas: str = "county_metro",
                 replicates: Any = None, rpp_year: Optional[int] = None) -> Dict[str, Any]:
    """Core of :func:`place_adjust_frame` and of the manifest ``adjustments`` step
    (census.manifest): the one implementation of the RPP adjustment of a frame.

    ``frame``: analysis frame (DataFrame, GEOID per row; a modified copy is returned).
    ``variables``: dollar variables; ``<v>`` and ``<v>_se`` are divided by RPP/100.
    ``year``: the dollars' year (ACS: release end year; also the county boundary year).
    ``rpp_year``: the RPP year (default ``year``). ``replicates``: optional replicate
    long frame; rows of ``variables`` are scaled by the same factor, and their rows
    whose GEOID is not in the frame are dropped.
    Returns {"frame", "replicates", "rpp_year", "parity", "rpp_areas", "boundary_source",
    "notes", "advisories", "custom_table"}. Raises on bad input or a missing RPP.
    """
    import pandas as pd

    from census import rpp
    from census.analysis import REPLICATE_COLUMNS

    if areas not in _RPP_AREAS:
        raise ValueError(f"areas must be one of {_RPP_AREAS}.")
    if isinstance(variables, str):
        variables = [variables]
    variables = list(variables)
    rpp_year = int(year if rpp_year is None else rpp_year)
    frame = frame.copy()
    missing = [v for v in variables if v not in frame.columns or f"{v}_se" not in frame.columns]
    if missing:
        raise KeyError(f"frame lacks {missing} (or their _se columns); use analysis variable names")
    if "Year" in frame.columns and set(pd.to_numeric(frame["Year"]).astype(int)) - {int(year)}:
        raise ValueError(f"frame has releases other than {int(year)}; adjust one release at a time")
    geoids = [str(g) for g in frame["GEOID"]]
    boundary_source = None
    if areas == "county_metro":
        # Counties (5 digits) or tracts (11 digits; a tract lies in one county, GEOID[:5]).
        if any(len(g) not in (5, 11) for g in geoids) or len({len(g) for g in geoids}) > 1:
            raise ValueError("areas='county_metro' needs county (5-digit) or tract (11-digit) GEOIDs; "
                             "use areas='state'")
        county_of = {g: g[:5] for g in set(geoids)}
        membership, boundary_source = _county_rpp_areas(sorted(set(county_of.values())), int(year))
        member = {g: membership.loc[c] for g, c in county_of.items()}
        keys = [rpp.county_rpp_area(county_of[g], member[g]["CBSA"] if pd.notna(member[g]["CBSA"]) else None,
                                    member[g]["LSAD"] if pd.notna(member[g]["LSAD"]) else None)
                for g in geoids]
        frame["cbsa"] = [member[g]["CBSA"] if pd.notna(member[g]["CBSA"]) else "" for g in geoids]
        frame["cbsa_type"] = [{"M1": "metropolitan", "M2": "micropolitan"}.get(member[g]["LSAD"], "none")
                              if pd.notna(member[g]["LSAD"]) else "none" for g in geoids]
    else:
        keys = [g[:2] for g in geoids]
    parity = {k: rpp.place_parity(k, rpp_year) for k in sorted(set(keys))}
    frame["rpp_area"] = [parity[k]["geo_fips"] for k in keys]
    frame["rpp_area_name"] = [parity[k]["geo_name"] for k in keys]
    frame["rpp"] = [parity[k]["rpp"] for k in keys]
    factor = 100.0 / frame["rpp"].to_numpy(float)
    for v in variables:
        frame[v] = pd.to_numeric(frame[v], errors="coerce").to_numpy(float) * factor
        frame[f"{v}_se"] = pd.to_numeric(frame[f"{v}_se"], errors="coerce").to_numpy(float) * factor
    reps = None
    if replicates is not None:
        reps = replicates.copy()
        by_geoid = dict(zip(geoids, factor))
        sel = reps["variable"].isin(variables)
        unmatched = sorted(set(reps.loc[sel, "GEOID"].astype(str)) - set(by_geoid))
        f = reps.loc[sel, "GEOID"].astype(str).map(by_geoid).to_numpy(float)
        cols = ["estimate"] + [c for c in REPLICATE_COLUMNS if c in reps.columns]
        # whole-number replicate files read as int64; pandas 3 refuses float values in int columns
        reps[cols] = reps[cols].astype(float)
        reps.loc[sel, cols] = reps.loc[sel, cols].to_numpy(float) * f[:, None]
        if unmatched:
            reps = reps[~(sel & reps["GEOID"].astype(str).isin(unmatched))]
    counts = frame.groupby(["rpp_area", "rpp_area_name"]).agg(rpp=("rpp", "first"), rows=("rpp", "size")).reset_index()
    notes = [f"PLACE ADJUSTMENT: {', '.join(variables)} divided by the BEA Regional Price Parity ({rpp_year}, "
             "U.S.=100) of each row's area, i.e. expressed in national-average purchasing power; _se scaled by "
             "the same factor."]
    if rpp_year == int(year):
        notes.append(f"ACS 5-year dollars are in end-year ({int(year)}) dollars; the {int(year)} RPP is applied to "
                     "the whole period.")
    else:
        notes.append(f"RPP YEAR: the {rpp_year} RPP is applied to ACS dollars of {int(year)} (the release end "
                     f"year); price-level differences between places are assumed unchanged between {rpp_year} "
                     f"and {int(year)}.")
    if areas == "county_metro":
        notes.append("RPP AREA: " + ("tracts take the RPP area of their county; " if geoids and len(geoids[0]) == 11
                                     else "") + "counties in a metropolitan CBSA use that MSA's RPP; micropolitan and rural "
                     "counties use the state nonmetropolitan-portion RPP (BEA nonmetro portions include "
                     f"micropolitan counties). CBSA membership from {boundary_source} (OMB bulletin 23-01 "
                     "delineation, as in BEA's RPPs).")
    # provenance as in rpp.describe_place_adjustment: advisories and an unverified custom RPP table
    advisories = sorted({a for p in parity.values() for a in p["advisories"]})
    custom = next((p["custom_table"] for p in parity.values() if p.get("custom_table")), None)
    notes += advisories
    if custom:
        notes.append(rpp.custom_table_note(custom))
    notes.append(rpp.RPP_ESTIMATION_ERROR_NOTE)
    return {"frame": frame, "replicates": reps, "rpp_year": rpp_year, "parity": parity,
            "rpp_areas": _records(counts), "boundary_source": boundary_source, "notes": notes,
            "advisories": advisories, "custom_table": custom}


def place_adjust_frame(
    input_path: str,
    variables: List[str],
    year: int,
    areas: str = "county_metro",
    replicates_path: Optional[str] = None,
    output_path: Optional[str] = None,
    replicates_output_path: Optional[str] = None,
    rpp_year: Optional[int] = None,
) -> Dict[str, Any]:
    """Express dollar variables of an analysis frame in national-average purchasing
    power with BEA Regional Price Parities, row by row (value * 100 / RPP).

    Args:
        input_path: Analysis frame from build_analysis_frame (GEOID per row).
        variables: Dollar variables to adjust, e.g. ["income"]; their _se is
            scaled by the same factor (_cv is unchanged).
        year: The dollars' year (ACS 5-year: the release end year) and RPP year.
        areas: "county_metro" (counties: the MSA RPP for counties in a
            metropolitan CBSA, else the state's nonmetropolitan-portion RPP;
            membership from Census CBSA boundaries of BEA's delineation) or
            "state" (the state RPP for every row).
        replicates_path: Replicate file from build_analysis_frame; the rows of
            the adjusted variables are scaled too (written to replicates_output_path).
        rpp_year: RPP year when it differs from year (default: year); noted in the result.
    The RPP is treated as fixed: its own estimation error is not in the adjusted
    SEs, MOEs or replicates. Never applied automatically. A manifest can declare the
    same adjustment as an "adjustments" step (run_manifest).
    Example: place_adjust_frame("frame.parquet", ["income"], 2024)
    """
    from census import rpp

    if isinstance(variables, str):
        variables = [variables]
    try:  # place_adjust validates areas (ValueError, reported as invalid input below)
        reps = _read_replicates(replicates_path) if replicates_path else None
        res = place_adjust(_load_frame(input_path), variables, year, areas=areas, replicates=reps,
                           rpp_year=rpp_year)
        rep_out = None
        if replicates_path:
            rep_out = _write_frame(res["replicates"], replicates_output_path
                                   or os.path.splitext(replicates_path)[0] + "_rpp.parquet", "replicates_rpp.parquet")
    except BundledDataIntegrityError as exc:
        return integrity_error_result(exc)
    except (*_ERRORS, rpp.RPPUnavailable) as exc:
        return _fail(errors.INVALID_INPUT, f"{type(exc).__name__}: {exc}")
    frame = res["frame"]
    path = _write_frame(frame, output_path or os.path.splitext(input_path)[0] + "_rpp.parquet", "frame_rpp.parquet")
    return _ok(f"Adjusted {', '.join(variables)} for {len(frame)} rows with {len(res['parity'])} RPP area(s).",
               "fit_model or make_map with input_path=output_path"
               + (" and replicates_path=replicates_output_path" if rep_out else "")
               + "; state in results that a regional price parity adjustment was applied",
               output_path=path, replicates_output_path=rep_out, areas=areas, year=int(year),
               rpp_year=res["rpp_year"], rpp_areas=res["rpp_areas"], notes=res["notes"],
               advisories=res["advisories"], custom_table=res["custom_table"], applied_by_default=False)


def make_web_map(
    input_path: str,
    column: str,
    level: str,
    year: int,
    se_col: Optional[str] = None,
    moe_col: Optional[str] = None,
    scheme: str = "quantiles",
    output_path: Optional[str] = None,
    product: str = "5-year",
) -> Dict[str, Any]:
    """Self-contained interactive HTML map (no external servers or tiles): hover
    for each area's estimate, MOE, CV, and reliability; legend reports class
    separability like the journal maps.

    product: "5-year" (default) or "1-year"; named in the map's data citation.
    Example: make_web_map("frame.parquet", "poverty_rate", "county", 2023, se_col="poverty_rate_se")
    """
    from census.web_maps import web_choropleth
    from census.workflows_geo import _with_boundaries

    try:
        gdf = _with_boundaries(_load_frame(input_path), level, year)
        path = output_path or f"{_out_dir(None, 'maps')}/{column}_{level}_{year}.html"
        res = web_choropleth(gdf, column, se_col=se_col, moe_col=moe_col, scheme=scheme, out_path=path,
                             product=product)
    except _ERRORS as exc:
        return _fail(errors.INVALID_INPUT, str(exc))
    return _ok(f"Interactive map of {column} written ({res.get('n_features')} areas, {res.get('bytes')} bytes).",
               "open the HTML file in a browser; it makes no network requests",
               **{k: (str(v) if k == "path" else v) for k, v in dict(res).items()})


def decompose_gap(
    state: str,
    year: int,
    outcome: str,
    group_a: str,
    group_b: str,
    covariates: Optional[List[str]] = None,
    categorical: Optional[List[str]] = None,
    model: str = "linear",
    where: Optional[str] = None,
    product: str = "5-year",
) -> Dict[str, Any]:
    """How much of a gap between two groups is explained by composition (Round 79; PUMS microdata).

    Oaxaca-Blinder (model="linear", numeric outcome such as "WAGP") or Fairlie (model="logit", a 0/1 condition such
    as "HICOV == 2" = uninsured). group_a / group_b: mutually exclusive PUMS conditions, e.g. "RAC1P == 2 and
    HISP == 1" and "RAC1P == 1 and HISP == 1". covariates: numeric columns ("AGEP", "POVPIP"); categorical: code
    columns ("SCHL", "ESR"). where: universe, e.g. "AGEP >= 19 and AGEP <= 64". Replicate-weight intervals.
    'Explained' is statistical composition, not a causal effect.
    Example: decompose_gap("26", 2023, "HICOV == 2", "RAC1P == 2 and HISP == 1", "RAC1P == 1 and HISP == 1",
    covariates=["AGEP"], categorical=["SCHL", "ESR"], model="logit", where="AGEP >= 19 and AGEP <= 64")
    """
    from census import pums
    from census.decomposition import pums_decomposition
    covariates, categorical = list(covariates or []), list(categorical or [])
    try:
        cols = _pums_columns(outcome, group_a, group_b, where, *covariates, *categorical)
        df = pums.fetch_pums(state, year, product=product, record="person", columns=cols or None)
        r = pums_decomposition(df, outcome, group_a, group_b, covariates, categorical, model=model, where=where)
    except _ERRORS as exc:
        return _fail(errors.INVALID_INPUT, f"{type(exc).__name__}: {exc}",
                     "check the conditions, covariates and universe, then retry")
    t = r["table"].set_index("component")
    summary = (f"{r['method']}: gap {t.loc['gap', 'estimate']:.4g}; explained {t.loc['explained', 'estimate']:.4g} "
               f"({t.loc['explained', 'ci_lower']:.4g} to {t.loc['explained', 'ci_upper']:.4g}); unexplained "
               f"{t.loc['unexplained', 'estimate']:.4g}.")
    from census.results import _jsonable
    return _ok(summary, "report explained and unexplained parts with intervals; explained is composition, not causation",
               **_jsonable({**r, "table": r["table"].to_dict("records")}))


def stratified_analysis(
    input_path: Optional[str] = None,
    stratum: Optional[str] = None,
    cases_exposed: Optional[str] = None,
    total_exposed: Optional[str] = None,
    cases_unexposed: Optional[str] = None,
    total_unexposed: Optional[str] = None,
    person_time: bool = False,
    state: Optional[str] = None,
    year: Optional[int] = None,
    exposure: Optional[str] = None,
    outcome: Optional[str] = None,
    strata: Optional[str] = None,
    where: Optional[str] = None,
    interaction: Optional[str] = None,
    product: str = "5-year",
) -> Dict[str, Any]:
    """Stratified analysis (Round 83): is a third variable a confounder or an effect modifier?

    Gives the crude measure, stratum-specific measures, the Mantel-Haenszel pooled (adjusted) RR, OR and RD,
    homogeneity tests and a descriptive label (confounder / effect_modifier / neither, 10% change rule).
    Counts: input_path with one row per stratum (stratum, cases_exposed, total_exposed, cases_unexposed,
    total_unexposed; person_time=True when totals are person-years, giving the MH rate ratio).
    PUMS: state, year, exposure and outcome as conditions (e.g. "DIS == 1", "HICOV == 2"), strata a code column
    (e.g. "AGEP_BAND" or "SEX"); interaction="<second condition>" adds RERI (additive interaction).
    Example: stratified_analysis(state="26", year=2023, exposure="DIS == 1", outcome="HICOV == 2", strata="SEX",
    where="AGEP >= 19 and AGEP <= 64")
    """
    from census import stratified as st
    try:
        if input_path is not None:
            need = [stratum, cases_exposed, total_exposed, cases_unexposed, total_unexposed]
            if not all(need):
                return _fail(errors.INVALID_INPUT, "counts mode needs stratum, cases_exposed, total_exposed, "
                             "cases_unexposed and total_unexposed columns.")
            r = st.stratified_counts(_load_frame(input_path), stratum, cases_exposed, total_exposed,
                                     cases_unexposed, total_unexposed, person_time=person_time)
        else:
            if not (state and year and exposure and outcome and (strata or interaction)):
                return _fail(errors.INVALID_INPUT, "PUMS mode needs state, year, exposure, outcome and strata "
                             "(or interaction).")
            from census import pums
            cols = _pums_columns(exposure, outcome, strata, where, interaction)
            df = pums.fetch_pums(state, year, product=product, record="person", columns=cols or None)
            sub = df.loc[pums._mask(df, where)]
            y = np.asarray(pums._values(sub, outcome), float); e = np.asarray(pums._values(sub, exposure), float)
            _, W = pums._weight_matrix(sub, "person")
            if interaction:
                f2 = np.asarray(pums._values(sub, interaction), float)
                cells = (e > 0).astype(int)+2*(f2 > 0).astype(int)
                risks = np.stack([(W[cells == k]*y[cells == k, None]).sum(0)/W[cells == k].sum(0) for k in range(4)], axis=1)
                r = {"additive_interaction": st.additive_interaction(risks=risks)}
                if strata:
                    s = sub[strata].to_numpy()
                    r.update(st.stratified_pums(y, e, s, W, sorted(pd.unique(s[pd.notna(s)]))))
            else:
                s = sub[strata].to_numpy()
                r = st.stratified_pums(y, e, s, W, sorted(pd.unique(s[pd.notna(s)])))
    except _ERRORS as exc:
        return _fail(errors.INVALID_INPUT, f"{type(exc).__name__}: {exc}")
    from census.results import _jsonable
    lab = r.get("classification", {})
    pooled = r.get("pooled", {})
    summary = "Stratified analysis: " + ", ".join(
        f"MH {m.upper()} {v['estimate']:.3g} ({v['lower']:.3g} to {v['upper']:.3g})" for m, v in pooled.items()
        if isinstance(v, dict) and "estimate" in v)
    if lab:
        summary += "; label " + ", ".join(f"{m}: {v}" for m, v in lab.items())
    if "additive_interaction" in r:
        ai = r["additive_interaction"]
        summary += f"; RERI {ai['reri']:.3g} ({ai['lower']:.3g} to {ai['upper']:.3g})"
    return _ok(summary + ".", "report the adjusted (MH) measure for a confounder or each stratum for an effect "
               "modifier, with crude and stratum measures", **_jsonable(r))
