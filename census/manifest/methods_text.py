# SPDX-License-Identifier: AGPL-3.0-or-later
"""Manifest methods text definitions."""

from typing import Any, List, Mapping, Optional
import pandas as pd
from ..results import ModelResult, interval_description
from .datasource import (
    effective_data_source,
)
from .external import (
    _ext_source_text,
    external_circularity,
    external_names,
)
from .replicates import (
    census_vre_source,
)
from .schema import (
    INCOMPLETE_STATUS_TEXT,
    REFERENCES,
    STATUS_CONFIRMATORY,
    STATUS_CONFIRMATORY_INCOMPLETE,
    _formula_names,
    _normalize_analysis,
    manifest_hash,
    manifest_releases,
    release_overlap_message,
    tables_and_refs,
)



# ---------------------------------------------------------------------------
# Methods text
# ---------------------------------------------------------------------------

from .methods import METHODS

# Retain the legacy introspection order while deriving every value from its spec.
_LEGACY_TEXT_ORDER = ("fit_replicate", "regression_calibration", "fit_eiv", "simex", "fh_regression",
                      "fay_herriot", "correlation_matrix", "linear_trend_test", "batch_z_test")
_METHOD_TEXT = {
    name: METHODS[name].text for name in dict.fromkeys((*_LEGACY_TEXT_ORDER, *METHODS))
    if METHODS[name].text is not None
}


def _age_standardized_text(d: Mapping[str, Any]) -> str:
    """Methods sentence for an ``age_standardized`` derivation: standard, bands, weights and the
    standard table's checksum."""
    from ..derived import standardization_weights
    w = standardization_weights(d)
    bands = d.get("bands") or []
    band_txt = ", ".join(f"{lo}-{hi}" if hi is not None else f"{lo}+" for lo, hi in bands) if bands else \
        f"{len(w)} groups"
    if d.get("standard") == "custom":
        std = "custom weights"
    else:
        from ..standardize import standard_info
        info = standard_info(str(d["standard"]))
        std = (f"the {info.get('description', d['standard'])} ({info.get('reference', '')}; bundled table "
               f"SHA-256 {info.get('csv_sha256')})")
    return (f"- `{d['name']}`: directly age-standardized rate{' (percent)' if d.get('as_percent') else ''}, "
            f"sum over age bands ({band_txt}) of weight x band numerator / band denominator, with weights "
            f"{[round(x, 6) for x in w]} from {std}. A unit with an empty age band has no standardized rate "
            "(complete case)")


def _multi_release_adjustment_text(m: Mapping[str, Any], adj: Mapping[str, Any],
                                   done: Optional[Mapping[str, Any]]) -> str:
    """Methods text of an adjustment with a declared dollar year (CPI, then RPP; D15-2)."""
    from ..inflation import INDEX_DISPLAY
    index = INDEX_DISPLAY.get(str(adj.get("price_index")), str(adj.get("price_index")))
    rpp_years = adj.get("rpp_years") or {str(m.get("releases", [None])[0]): adj.get("rpp_year")}
    areas = (done or {}).get("areas") or adj.get("areas") or "default"
    text = (f"- Price adjustment{' (after the exclusions)' if m.get('exclusions') else ''}, in this order: "
            f"(1) the values of {', '.join(adj.get('variables', []))} from each release were converted from the release's "
            f"end-year dollars to {adj['dollar_year']} dollars with the {index} (annual averages; factor "
            f"{index}({adj['dollar_year']}) / {index}(release end year)); (2) the converted values were divided by "
            "the BEA Regional Price Parity (U.S. = 100) / 100 of each unit's area for the release's own RPP year ("
            + ", ".join(f"release {k}: RPP {v}" for k, v in sorted(rpp_years.items())) + ")"
            + (" (the county's metropolitan statistical area, else the state's nonmetropolitan portion; CBSA "
               "membership from Census boundaries of the OMB 23-01 delineation)" if areas == "county_metro"
               else " (its state)" if areas == "state" else "")
            + ". Estimates, SEs and any replicates are scaled by the same factors and CVs are unchanged. Both "
            "factors are multiplicative, so the order does not change the values; it is stated so the price "
            "concepts are clear (national inflation first, then place). The price index and RPPs are treated "
            "as fixed: their own estimation error is not in any SE or interval.")
    if done:
        for r in done.get("releases") or []:
            cpi = r.get("cpi") or {}
            if cpi:
                text += (f"\n  Release {r['release']}: {index} {cpi['index_from']} -> {cpi['index_to']} (factor "
                         f"{cpi['factor']:.6f}); RPP year {r['rpp_year']}.")
        pidx = done.get("price_index") or {}
        text += (f"\n  {len(done.get('rpp_areas') or [])} release-by-RPP-area entries were used; RPP table "
                 + (f"custom {done['rpp_table'].get('path')} (SHA-256 {done['rpp_table'].get('sha256')}, not verified)"
                    if done["rpp_table"].get("source") == "custom"
                    else f"bundled (SHA-256 {done['rpp_table'].get('sha256')})")
                 + f"; price index table {pidx.get('source', 'bundled')} (SHA-256 {pidx.get('sha256')}).")
    return text


def _methods_replicate_source(m, results, rep_info):
    if rep_info and rep_info.get("source") == "census_vre":
        files = rep_info.get("files") or []
        tabs = sorted({f["table"] for f in files})
        rep_source = ("the 80 replicate estimates of the Census Bureau's variance replicate estimate (VRE) files "
                      f"fetched by the toolkit ({len(files)} file(s): tables {', '.join(tabs) or 'none'}; URLs and "
                      "SHA-256 of each file in run.json"
                      + (f"; canonical SHA-256 of the replicates used `{rep_info['sha256']}`" if rep_info.get("sha256")
                         else "") + ")")
        subs = [f["substitution"] for f in files if f.get("substitution")]
        if subs:
            rep_source += "; " + "; ".join(
                f"{', '.join(s['lines'])} read from {', '.join(s['lines'].values())} of `{s['source_url']}` because "
                f"`{s['requested_url']}` was unavailable ({s['reason']}); {s['verification']}" for s in subs)
        rep_short = " and replicate-based standard errors from Census VRE files"
    elif results is None and census_vre_source(m):
        rep_source = "the 80 replicate estimates of the Census VRE files fetched for the manifest's tables"
        rep_short = " and replicate-based standard errors from Census VRE files"
    elif rep_info:
        kind = "synthetic caller-supplied" if rep_info.get("synthetic") else "caller-supplied"
        rep_source = (f"the {kind} replicate estimates (not fetched from Census variance replicate files by "
                      + (f"the toolkit; canonical SHA-256 `{rep_info['sha256']}`)" if rep_info.get("sha256")
                         else f"the toolkit; SHA-256 unavailable: {rep_info.get('sha256_unavailable')})"))
        rep_short = f" and replicate-based standard errors from {kind} replicate estimates"
    elif results is not None:
        rep_source = "replicate estimates when supplied (none were supplied to this run)"
        rep_short = " and replicate-based standard errors"
    else:
        rep_source = "the 80 ACS replicate estimates"
        rep_short = " and replicate-based standard errors"
    return rep_source, rep_short


def _methods_data(m, run, source, lines, cites, data_citation):
    lines += ["### Data", ""]
    tables = sorted(tables_and_refs(m))
    geo = m.get("geography", {})
    cite = data_citation(m.get("releases", []), tables, synthetic=source["synthetic"],
                         description=source.get("description"))
    lines.append(f"Data are {cite} Geography: {geo.get('level')}"
                 + (f" (state {geo.get('state')})" if geo.get("state") else "")
                 + (f" (states {', '.join(map(str, geo['states']))}, extracted per state and stacked; no "
                    "automatic state effects, a state term enters only where a formula names one)"
                    if geo.get("states") else "")
                 + (f", codes {', '.join(map(str, geo['codes']))}" if geo.get("codes") else "") + ".")
    if source["synthetic"] and source.get("generator"):
        lines.append(f"Synthetic data generator: {source['generator']}.")
    lines.append("Variables (YEAR:CODE references resolve to that vintage's concept; concept IDs follow the "
                 "toolkit's cross-vintage concordance, with blocking concordance issues stopping extraction "
                 "rather than being substituted):")
    lines += [f"- `{v['name']}`: {v['ref']}" + (f" (table {v['table']})" if v.get("table") else "")
              for v in m.get("variables", [])]
    if len(manifest_releases(m)) > 1:
        if release_overlap_message(manifest_releases(m), "releases") is not None:
            lines.append("Multiple releases were linked through the concordance; overlapping 5-year periods "
                         "share sample years and are not independent.")
        else:
            lines.append("Multiple releases were linked through the concordance; the 5-year periods do not "
                         "overlap (no shared sample years), so their estimates come from independent samples.")
    if geo.get("harmonize_tracts_to") is not None:
        from ..tract_harmonization import methods_text as _harmonization_text
        lines.append(_harmonization_text(run.get("harmonization")) or (
            f"Tract harmonization (pre-registered): releases on another tract vintage are apportioned to "
            f"{geo['harmonize_tracts_to']} Census tracts with block weights; their Census VRE replicates are "
            "apportioned with the same weights."))
    if m.get("external"):
        from ..health_sources import SOURCES
        ext_run = run.get("external") or {}
        from ..health_sources import measure_info
        for e in m["external"]:
            info = SOURCES.get(e.get("source"), {})
            try:
                unit = measure_info(e["source"], e["measure"]).get("unit") or info.get("unit", "")
            except (KeyError, ValueError):
                unit = info.get("unit", "")
            rel = f" {e.get('release')} release," if e.get("release") is not None else ""
            lines.append(f"- External variable `{e['name']}`: {info.get('title', e.get('source'))}{rel} measure "
                         f"{e.get('measure')} ({unit}), joined on GEOID. Source: "
                         f"{_ext_source_text(e)}. Uncertainty: {info.get('uncertainty_text', '')}. Its error is "
                         "independent of the ACS sampling error (a different data system); how each analysis uses "
                         "it is stated under Analyses.")
            src_run = next((p for p in ext_run.get("sources") or [] if e["name"] in (p.get("measures") or {}).values()),
                           {})
            if src_run.get("predicted"):
                pr = src_run["predicted"]
                lines.append(f"  USALEEP flag counts {pr.get('flag_counts')}; "
                             + ("tracts with fully predicted death rates (flag 2) kept" if pr.get("include_predicted")
                                else f"{pr.get('dropped_fully_predicted')} tracts with fully predicted death rates "
                                     "(flag 2) dropped (pre-registered default)") + ".")
            if src_run.get("apportionment"):
                ap = src_run["apportionment"]
                lines.append(f"  Apportioned from 2010 to 2020 tracts: {ap['method']}; targets below "
                             f"{ap['min_coverage']:.0%} population coverage left missing ({ap['targets_below_coverage']}); "
                             + (f"{ap['split_targets_left_missing']} split tracts left missing (inheriting the parent's "
                                "value failed validation, docs/audits/rate_apportionment_validation.md)."
                                if ap.get("split_policy", "missing") == "missing" else
                                f"Dominant split policy: parent share >=0.95, validated on held-out OH/PA "
                                "(docs/audits/rate_apportionment_retest.md); other split targets left missing."
                                if ap.get("split_policy") == "dominant" else
                                f"{ap.get('split_targets', 0)} split tracts inherit their parent's value (NOT validated: "
                                "docs/audits/rate_apportionment_validation.md)."))
            if src_run.get("export"):
                ex = src_run["export"]
                lines.append(f"  WONDER export {ex['dataset']} (SHA-256 {ex['file']['sha256'][:12]}...; query date "
                             f"{ex.get('query_date')}); {ex['suppressed_units']} suppressed units kept as censored "
                             f"(1-9 deaths, missing rates), {ex['unreliable_units']} unreliable (fewer than 20).")
        join = ext_run.get("join")
        if join:
            lines.append(f"  {join['matched_units']} of {join['complete_acs_units']} units with complete ACS data had "
                         f"an external value; files and SHA-256 in run.json (external).")
        for name, count in ext_run.get("low_count_kept", {}).items():
            lines.append(f"{count} counties had fewer than 20 low-weight births (flagged unreliable by CHR&R); "
                         "they were kept, weighted by their births.")
        for c in external_circularity(m):
            if c["overlap"] and c["kind"] != "direct":
                lines.append(f"  Circularity: in {c['analysis']}, covariates {sorted(c['overlap'])} measure inputs of "
                             f"the {c['source']} model; their coefficients partly recover that model.")
            if c["equivalent"]:
                lines.append(f"  Measurement comparison: in {c['analysis']}, {c['outcome']} is compared with its "
                             f"direct ACS equivalent {sorted(c['equivalent'])}.")
    if m.get("aggregation"):
        lines.append(f"Geographies were aggregated into {len(set(m['aggregation']['mapping'].values()))} groups; "
                     "aggregate MOEs use replicate variance where available, else the ACS approximation "
                     "sqrt(sum MOE^2).")
        cites.append("vre")


def _methods_derivations(m, rep_info, lines, cites):
    lines += ["", "### Measures and uncertainty", "",
              "Standard errors of published estimates are MOE/1.645 (ACS MOEs are 90% margins)."]
    rep_rows = (rep_info or {}).get("derived_on_replicates_rows") or {}
    for d in m.get("derivations") or []:
        c = rep_rows.get(d["name"])
        if c and c["rows_replicate"] >= c["rows"]:
            se_text = f"; SE from the derivation evaluated on each replicate (all {c['rows']} units)"
        elif c:
            se_text = (f"; replicate SE for {c['rows_replicate']} of {c['rows']} units; approximate SE (ACS "
                       "formulas, Handbook ch. 8) elsewhere")
        else:
            se_text = "; MOE by the ACS approximation formulas (Handbook ch. 8)"
        if d.get("op") == "expected_count":
            lines.append(f"- `{d['name']}` = {d.get('period_years',1)} times age/sex populations times annual national reference rates from the pinned export, evaluated on every ACS replicate"+se_text+". Poisson exposures hold this offset fixed; reference-aware SMR intervals assess expected-count uncertainty.")
            continue
        if d.get("op") == "age_standardized":
            lines.append(_age_standardized_text(d) + se_text + ".")
            if d.get("standard") == "us2000" and "standard_pop" not in cites:
                cites.append("standard_pop")
            continue
        lines.append(f"- `{d['name']}` = {d.get('op', 'auto')} of {d.get('num')}"
                     + (f" over {d['den']}" if d.get("den") is not None else "") + se_text + ".")
    for ex in m.get("exclusions") or []:
        if ex["rule"] == "cv_screen":
            lines.append(f"Observations with CV > {ex.get('threshold', 30)}% on {', '.join(ex.get('variables', []))} "
                         f"were {'excluded' if ex.get('action') == 'exclude' else 'kept and flagged'}.")
        else:
            lines.append(f"{len(ex.get('geoids', []))} pre-specified GEOIDs were excluded.")


def _methods_adjustments(m, run, lines, cites):
    run_adj = {i: a for i, a in enumerate(run.get("adjustments") or [])}
    for i, adj in enumerate(m.get("adjustments") or []):
        done = run_adj.get(i)
        if adj.get("dollar_year") is not None:
            lines.append(_multi_release_adjustment_text(m, adj, done))
            continue
        year = (done or {}).get("rpp_year") or adj.get("rpp_year")
        areas = (done or {}).get("areas") or adj.get("areas") or "default"
        lines.append(f"- Price adjustment{' (after the exclusions)' if m.get('exclusions') else ''}: "
                     f"{', '.join(adj.get('variables', []))} divided by the BEA Regional "
                     f"Price Parity ({year}, U.S. = 100) / 100 of each "
                     "unit's area"
                     + (" (the county's metropolitan statistical area, else the state's nonmetropolitan portion; "
                        "CBSA membership from Census boundaries of the OMB 23-01 delineation)"
                        if areas == "county_metro" else " (its state)" if areas == "state" else "")
                     + "; estimates, SEs and any supplied replicates are scaled by the same factor and CVs are "
                     "unchanged. "
                     "RPPs are treated as fixed: their own estimation error is not in any SE or interval.")
        if done:
            if not done.get("rpp_year_matches_release"):
                lines.append(f"  Note: the {done['rpp_year']} RPP was applied to dollars of {done['dollar_year']} "
                             "(the release end year).")
            lines.append(f"  {len(done.get('rpp_areas') or [])} RPP area(s) were used; RPP table "
                         + (f"custom {done['rpp_table'].get('path')} (SHA-256 {done['rpp_table'].get('sha256')}, "
                            "not verified)" if done["rpp_table"].get("source") == "custom"
                            else f"bundled (SHA-256 {done['rpp_table'].get('sha256')})") + ".")


def _methods_replicates(rep_info, lines):
    if rep_info and rep_info.get("source") == "census_vre" and rep_info.get("unavailable"):
        miss = sorted({f"{u['variable']} ({u['table']})" for u in rep_info["unavailable"]})
        lines.append(f"No Census VRE replicates are published for {', '.join(miss)}; replicate analyses using "
                     "them as variables with sampling error stop under the strict confirmatory policy unless "
                     "the manifest declares otherwise (below).")
    lines.append("Rows with missing or undefined estimates were dropped analysis by analysis (complete cases).")


def _methods_analyses(m, rep_info, level, rep_short, rep_source, lines, cites):
    lines += ["", "### Analyses", ""]
    for a in m.get("analyses", []):
        a = _normalize_analysis(a)
        text, refs = _METHOD_TEXT[a["method"]]
        args = a.get("args") or {}
        tgt = args.get("target", METHODS[a["method"]].default_target)
        # the same interpretation contract as the fitted result (census.results.interval_description)
        probe = ModelResult(model_type="", formula=str(a.get("formula") or ""), n_obs=0,
                            coefficients=pd.DataFrame(columns=["term"]), method=a["method"], uncertainty_sources=[],
                            confidence_level=level,
                            diagnostics={"interval_target": tgt} if a["method"] in ("fit_replicate", "inequality") else {})
        info = interval_description(probe)
        text = text.format(reference_source=a.get("reference_source", ""),
                           rank_direction=("higher rank values mean more deprived" if args.get("higher_is_more_deprived")
                                           else "lower rank values mean more deprived"), model=args.get("model", "ols").upper(), target=tgt, estimand=info["estimand"],
                           target_se={"se_model": "model SE (se_model)", "se_sampling": "replicate sampling SE "
                                      "(se_sampling)", "se_total": "combined SE (se_total)"}[info["basis_column"]],
                           cov=", ".join(a.get("error_covariates") or args.get("error_covariates") or []),
                           rep=rep_short if (a.get("replicates") or rep_info) else "", rep_source=rep_source,
                           se_basis=(f"delete-one-cluster jackknife (CR3) SEs over groups of `{args['cluster']}` "
                                     "(validated by simulation, docs/audits/eiv_cluster_validation.md)"
                                     if args.get("cluster") and args.get("cluster_se") == "jackknife" else
                                     f"cluster-robust sandwich SEs with units correlated within groups of "
                                     f"`{args['cluster']}` (G/(G-1) small-sample factor; validated by simulation, "
                                     "docs/audits/eiv_cluster_validation.md)" if args.get("cluster")
                                     else "sandwich SEs treating units as independent"))
        formatter = METHODS[a["method"]].format_text
        if formatter is not None:
            text = formatter(a, text)
        clusters = args.get("spatial_clusters")
        if clusters is not None:
            from scipy.stats import t as student_t
            from ..spatial_clusters import SPATIAL_CLUSTERS_VALIDATED, VALIDATED_CLUSTER_COUNTS
            k, cm = clusters["k"], clusters["method"]
            critical = student_t.ppf((1+level)/2, k-1)
            text = (f"Counties/tracts were assigned before outcome filtering to {k} geographic clusters "
                    "using 50 seeded EPSG:5070 k-means restarts (seed 20261126), minimum five units per cluster; "
                    "the bundle records GEOID-to-label assignments. ")
            if cm == "cr1_t":
                text += (f"Grouped-score CR1 covariance uses G/(G-1)*(n-1)/(n-k); target {tgt} "
                         f"combines model/sampling SEs by the registered rule. Intervals and p-values use "
                         f"t({k-1}), critical value {critical:.8g}. ")
                refs = ["cluster_bch", "vre"]
            elif cm == "im":
                from ..spatial_clusters import supports_im_acs
                text += (f"Ibragimov-Müller inference averages coefficients from separately fitted, full-rank "
                         f"cluster regressions; a one-sample t({k-1}) test uses between-cluster sd/sqrt(G), "
                         f"critical value {critical:.8g}. Only population target is supported. "
                         "No additive full-sample model SE is available. ")
                if supports_im_acs(clusters,args.get('model','ols')) and a['method']=='fit_replicate':
                    text += ("Round 30 C1 targets coefficients on ACS estimates as observed, not true measurement-error-corrected slopes. "
                             "Independent ACS error enters between-cluster spread; no additive ACS replicate variance is used. "
                             "Terms constant within every cluster are absorbed by cluster intercepts and reported not estimable; "
                             "partial constancy is refused. Poisson expected-death offsets stay fixed. "
                             "C2 EIV failed and remains refused (docs/audits/im_acs_validation.md). ")
                else:
                    text += "ACS sampling error is not included; analysed variables with ACS replicates are refused. "
                refs = ["cluster_im"]
            else:
                text += ("Restricted wild cluster inference uses 999 Webb six-point weight draws: residual "
                         "WCR for OLS, Kline-Santos Score2-Wald for binomial. Intervals invert the two-sided "
                         "bootstrap test at the registered level; no single t critical value or scalar SE is "
                         "reported. Only population target; ACS replicates are refused and their sampling "
                         "error is not included. ")
                refs = ["cluster_wcr"]
            if not SPATIAL_CLUSTERS_VALIDATED[cm] or k not in VALIDATED_CLUSTER_COUNTS[cm]:
                text += "EXPLORATORY ONLY: this method/count failed or was outside the fixed validation. "
        ext_out = [v for v in _formula_names(str(a.get("formula", "")).split("~")[0]) if v in external_names(m)]
        ext_kind = "an external model-based estimate"
        if ext_out:
            from ..health_sources import kind_phrase
            ent = next((e for e in m["external"] if e.get("name") == ext_out[0]), {})
            try:
                ext_kind = kind_phrase(ent["source"], ent["measure"])
            except (KeyError, ValueError):
                pass
        if ext_out and a["method"] == "fit_eiv":
            text += (f" The outcome ({', '.join(ext_out)}) is {ext_kind} with no ACS "
                     "replicates: it was held fixed in the replicate design rows, so the outcome-covariate error "
                     "covariance is zero by construction (independent surveys) and only the covariates' error was "
                     "corrected; the outcome's own error enters the residual and the sandwich.")
        elif ext_out and a["method"] == "fit_replicate" and (clusters is None or clusters["method"] == "cr1_t"):
            text += (f" The outcome ({', '.join(ext_out)}) is {ext_kind} held fixed in every "
                     "refit; se_sampling covers the covariates' ACS sampling error only.")
        elif ext_out and a["method"] == "fh_regression":
            text += (f" The outcome ({', '.join(ext_out)}) is {ext_kind}; its published "
                     "interval-derived SE was used as the known sampling variance of the Fay-Herriot model.")
        if a["method"] == "fit_replicate" and clusters is None and args.get("model") in ("binomial", "poisson"):
            if args["model"] == "binomial" and args.get("scale") == "X2" and ext_out:
                text += (" Coefficients were estimated by quasi-binomial regression (logit link, statsmodels GLM, "
                         "dispersion from Pearson χ²) of the low birth weight proportion with live births as trials. "
                         "Coefficients and intervals are on the logit scale; odds ratios exponentiate them.")
            elif args["model"] == "poisson" and args.get("scale") == "X2":
                text += " Coefficients were estimated by quasi-Poisson regression of counts with the denominator as exposure."
            elif args.get("scale") == "robust":
                text += (" Coefficients were estimated by " + ("binomial regression (logit link) with the denominator "
                         "as trials" if args["model"] == "binomial" else "Poisson regression (log link) with the "
                         "denominator as exposure") + "; standard errors are HC3 sandwich estimates, robust to "
                         "between-area overdispersion (validated coverage 0.879-0.897 at nominal 0.90, "
                         "docs/audits/robust_se_validation.md) but treating areas as independent.")
        if a.get("replicate_scope") == "covariates_only":
            held = _formula_names(str(a.get("formula", "")).split("~")[0])
            had = ((rep_info or {}).get("covariates_only_outcome_had_replicates") or {}).get(a["id"])
            text += (f" Pre-registered replicate scope `covariates_only`: the outcome ({', '.join(held)}) was held "
                     "at its estimate in every refit"
                     + (" as declared, although replicates were available for it in this run" if had
                        else " (declared because it has no published replicates)")
                     + ", so se_sampling covers the covariates' sampling error only; the stated interval does not "
                     "use se_sampling alone.")
        if a.get("formula") and "C(Year)" in str(a["formula"]) and len(manifest_releases(m)) > 1:
            if release_overlap_message(manifest_releases(m), "releases") is None:
                text += (" `C(Year)` contrasts the releases; replicate r of each release enters refit r together. "
                         "The ACS 5-year periods of these releases share no sample years, so their replicates come "
                         "from independent samples: the cross-release products have expectation zero and the "
                         "replicate variance of the contrast estimates the sum of the releases' sampling variances.")
            else:
                text += (" `C(Year)` contrasts releases whose ACS 5-year periods overlap (shared sample years): "
                         "their estimates are not independent, and no standard error reported here accounts for "
                         "that covariance (replicate SEs across overlapping releases are refused).")
        target = a.get("formula") or a.get("variables") or a.get("variable")
        lines.append(f"- **{a['id']}** (`{target}`): {text}")
        cites += refs
        if args.get("spatial_se") is not None:
            from ..boundaries import boundary_vintage
            lines.append("Standard errors are spatial HAC (Conley 1999) with a Bartlett kernel and a "
                         f"{args['spatial_se']['cutoff_km']} km cutoff, using great-circle distances between unit "
                         f"representative points (TIGER/Line cartographic boundaries, year "
                         f"{boundary_vintage(max(m['releases']), m['geography']['level'])}); validated in "
                         "docs/audits/spatial_hac_validation.md. Conley, T. G. (1999). GMM estimation with cross "
                         "sectional dependence. Journal of Econometrics, 92(1), 1–45.")
            from ..spatial_hac import SPATIAL_HAC_VALIDATED
            if not SPATIAL_HAC_VALIDATED:
                lines.append("The pre-set spatial HAC coverage validation FAILED; these standard errors are "
                             "exploratory and not validated for confirmatory use.")
        if a["method"] == "fit_eiv" and args.get("cluster"):
            cites.append("cluster")


def _methods_hypotheses(m, corr, level, lines, cites):
    from ..splines import has_spline
    if any(h.get("statistic") == "joint_wald" for h in m.get("hypotheses", [])):
        lines.append("Joint Wald tests jointly tested the standalone design columns for the named variable: W=b'V^-1 b against chi-squared(q), using HC3, ACS sampling covariance, or their conservative sum according to target; singular covariance was not tested. No coefficient confidence interval or odds ratio is attached to W.")
    if any(has_spline(a.get("formula", "")) for a in m.get("analyses", [])):
        lines.append("Natural cubic splines used explicit df=3/4/5, centered constraints and full-sample quantile knots frozen in every replicate; spline coefficient model covariance was HC3.")

    lines += ["", "### Hypotheses and multiple comparisons", ""]
    for hyp in m.get("hypotheses", []):
        lines.append(f"- **{hyp['id']}** ({hyp.get('direction', 'two-sided')}, {hyp['statistic']}"
                     + (f" of `{hyp['term']}`" if hyp.get("term") else "") + f"): {hyp.get('statement', '')}")
        if hyp.get("circularity_justification"):
            lines.append(f"  Circularity justification (pre-registered): {hyp['circularity_justification']}")
    cm = str(corr.get("method", "holm")).lower()
    lines.append(f"Intervals are {level:.0%}. p-values were adjusted with the {cm} procedure across "
                 f"{'all hypotheses' if corr.get('family', 'all') == 'all' else 'each hypothesis family'}; "
                 f"one-sided p-values are half the two-sided value in the hypothesized direction.")
    cites.append({"benjamini-hochberg": "bh", "fdr_bh": "bh", "fdr_by": "by"}.get(cm, cm))


def _methods_deviations(results, lines):
    if results is not None:
        devs = results.get("deviations", [])
        lines += ["", "### Deviations from the manifest", ""]
        lines += [f"- {d['kind']}: " + ", ".join(f"{k}={v}" for k, v in d.items() if k != "kind")
                  for d in devs] or ["None."]
        for e in results.get("exclusions", []):
            lines.append(f"- Exclusion {e['rule']}: " + ", ".join(f"{k}={v}" for k, v in e.items() if k != "rule"))


def _methods_references(cites, lines, FH_REFS):
    lines += ["", "### References", ""]
    seen = []
    for c in cites:
        if c in seen:
            continue
        seen.append(c)
        if c == "fh":
            lines += [f"- {r}" for r in FH_REFS]
        elif c in REFERENCES:
            lines.append(f"- {REFERENCES[c]}")


def methods_section(manifest: Mapping[str, Any], results: Optional[Mapping[str, Any]] = None) -> str:
    """Markdown methods text matching what the manifest specifies (and, with
    ``results`` = the run info of :func:`run_manifest`, what actually ran)."""
    from ..report_tables import data_citation
    from ..sae import REFERENCES as FH_REFS
    m = manifest
    h = manifest_hash(m)
    run = results or {}
    source = run.get("data_source") or effective_data_source(m)
    rep_info = run.get("replicates")
    rep_source, rep_short = _methods_replicate_source(m, results, rep_info)
    level = float(m.get("confidence_level", 0.90))
    corr = m.get("correction") or {}
    cites: List[str] = ["acs"]
    lines = [f"## Methods", "", f"*Pre-registered analysis \"{m.get('title', '')}\"; manifest SHA-256 `{h}`, "
             f"created {m.get('created')} by {', '.join(m.get('authors', []))}.*", ""]
    if m.get("exploratory"):
        lines.insert(0, "This analysis was registered as exploratory (manifest flag `exploratory: true`); its results are not confirmatory.")
    if results is not None:
        status = results.get("analysis_status", STATUS_CONFIRMATORY)
        lines += [f"**Analysis status: {status}**"
                  + (f": {INCOMPLETE_STATUS_TEXT}." if status == STATUS_CONFIRMATORY_INCOMPLETE else "."), ""]
    _methods_data(m, run, source, lines, cites, data_citation)
    _methods_derivations(m, rep_info, lines, cites)
    _methods_adjustments(m, run, lines, cites)
    _methods_replicates(rep_info, lines)
    _methods_analyses(m, rep_info, level, rep_short, rep_source, lines, cites)
    _methods_hypotheses(m, corr, level, lines, cites)
    _methods_deviations(results, lines)
    _methods_references(cites, lines, FH_REFS)
    return "\n".join(lines) + "\n"
