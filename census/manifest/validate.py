# SPDX-License-Identifier: AGPL-3.0-or-later
"""Manifest validate definitions."""

from census.data_integrity import BundledDataIntegrityError
from datetime import datetime
from typing import Any, Dict, List, Mapping
import numpy as np
from .adjustments import (
    _check_adjustments,
)
from .derivations import (
    _age_standardized_errors,
)
from .external import (
    circularity_errors,
    external_names,
)
from .replicates import (
    _check_replicates,
    census_vre_source,
)
from .schema import (
    ANALYSIS_METHODS,
    AUTHOR_RE,
    CONCEPT_RE,
    DATA_SOURCE_KEYS,
    DIRECTIONS,
    EXCLUSION_RULES,
    FIPS2_RE,
    FORMULA_ID_COLUMNS,
    LEGACY_X2_MANIFESTS,
    NAME_RE,
    REPLICATE_METHODS,
    REPLICATE_SCOPES,
    SCHEMA_VERSION,
    YEAR_CODE_RE,
    _STATE_PREFIXED_LEVELS,
    _dataset_for,
    _derivation_refs,
    _duplicate_spec_keys,
    _formula_names,
    _is_int,
    _normalize_analysis,
    _table_of,
    manifest_entities,
    manifest_hash,
    manifest_releases,
    release_overlap_message,
)



def _check_geography(geo: Mapping[str, Any], errors: List[str]) -> None:
    from ..pipeline import expand_states, is_nationwide, normalize_geo_level
    if not isinstance(geo, Mapping) or not geo.get("level"):
        errors.append("geography.level is required")
        return
    state = geo.get("state")
    if isinstance(state, str) and not is_nationwide(state):
        bad = [p for p in state.split(",") if not FIPS2_RE.match(p.strip())]
        if bad:
            errors.append(f"geography.state: {bad[0]!r} must be a state FIPS code of exactly 2 digits "
                          "(e.g. \"06\", not \"6\"), or \"all\"")
            return
    states = geo.get("states")
    if states is not None:
        if "state" in geo:
            errors.append("geography: give either 'state' or 'states', not both")
            return
        if not isinstance(states, list) or not states or not all(isinstance(s, str) for s in states):
            errors.append("geography.states must be a non-empty list of 2-digit state FIPS strings, "
                          "e.g. [\"26\", \"36\"]")
            return
        for s in states:
            if is_nationwide(s) or "," in s:
                errors.append(f"geography.states: {s!r} must be one 2-digit state FIPS code (for every "
                              "state use \"state\": \"all\")")
                return
            if not FIPS2_RE.match(s):
                errors.append(f"geography.states: {s!r} must be a state FIPS code of exactly 2 digits "
                              "(e.g. \"06\", not \"6\")")
                return
            try:
                expand_states(s)
            except ValueError as exc:
                errors.append(f"geography.states: {exc}")
                return
        if len(set(states)) != len(states):
            errors.append("geography.states lists a state more than once")
            return
        if geo.get("codes"):
            errors.append("geography: 'codes' cannot be combined with 'states' (codes are per state); "
                          "list GEOIDs in a geoid_exclude exclusion or use one state per manifest")
            return
        try:
            level = normalize_geo_level(geo["level"])
        except Exception:  # noqa: BLE001 - reported by build_entities below
            level = geo["level"]
        if level == "zcta":
            errors.append("geography.states does not apply to level 'zcta': ZCTA GEOIDs are not state-prefixed "
                          "and ZCTAs can cross state lines, so they cannot be extracted per state and stacked")
            return
        if level not in _STATE_PREFIXED_LEVELS:
            errors.append(f"geography.states does not apply to level {geo['level']!r} (national geography)")
            return
    try:
        manifest_entities(geo)
    except Exception as exc:
        errors.append(f"geography: {exc}")


def _check_variables(manifest: Mapping[str, Any], errors: List[str], resolve: bool, client: Any) -> None:
    from ..metadata import archived_vintages, vintage_variables
    releases = [int(r) for r in manifest.get("releases", []) if str(r).isdigit()]
    variables = manifest.get("variables") or []
    if not variables:
        errors.append("variables: at least one variable is required")
        return
    if not isinstance(variables, list):
        errors.append("variables must be a list of {name, ref} objects")
        return
    by_table: Dict[str, List[str]] = {}
    for i, v in enumerate(variables):
        if not isinstance(v, Mapping) or "name" not in v or "ref" not in v:
            errors.append(f"variables[{i}]: needs 'name' and 'ref'")
            continue
        ref = str(v["ref"])
        m = YEAR_CODE_RE.match(ref)
        if not m and not CONCEPT_RE.match(ref):
            errors.append(f"variables[{i}] {ref!r}: ref must be YEAR:CODE or a concept ID (c_ + 12 hex)")
            continue
        table = _table_of(v)
        if table is None:
            errors.append(f"variables[{i}] {ref!r}: a concept ID needs 'table'")
            continue
        dataset = _dataset_for(table)
        if m:
            year, code = int(m.group(1)), m.group(2)
            if year not in releases:
                errors.append(f"variables[{i}] {ref!r}: year {year} is not among releases {releases}")
            if resolve:
                if year not in archived_vintages(dataset):
                    errors.append(f"variables[{i}] {ref!r}: {dataset} {year} not in the offline metadata archive")
                    continue
                known, _ = vintage_variables(dataset, year)
                if not any(k == code or k.startswith(code) and k[len(code):] in ("E", "PE") for k in known):
                    errors.append(f"variables[{i}] {ref!r}: {code} does not exist in {dataset} {year}")
                    continue
        by_table.setdefault(table, []).append(ref)
    if not resolve:
        return
    from ..concordance import build_concordance
    for table, refs in by_table.items():
        dataset = _dataset_for(table)
        missing = [y for y in releases if y not in archived_vintages(dataset)]
        if missing:
            errors.append(f"{table}: releases {missing} not in the offline metadata archive for {dataset}")
            continue
        try:
            conc = build_concordance(table, dataset, releases, client=client)
            _, unknown = conc.resolve_selection(refs)
        except BundledDataIntegrityError:
            raise
        except Exception as exc:  # concordance build failures are validation errors
            errors.append(f"{table}: concordance could not be built ({exc})")
            continue
        for ref in unknown:
            errors.append(f"variable {ref!r} does not resolve in the {table} concordance for {releases}")


def validate_manifest(manifest: Mapping[str, Any], resolve: bool = True, client: Any = None) -> List[str]:
    """Return a list of errors (empty when the manifest is valid).

    ``resolve``: check every variable against the offline metadata archive
    and the concordance (no network when the archive covers the releases).
    """
    errors: List[str] = []
    if "exploratory" in manifest and type(manifest["exploratory"]) is not bool:
        errors.append("exploratory must be true or false")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if not str(manifest.get("title", "")).strip():
        errors.append("title is required")
    authors = manifest.get("authors") or []
    if not authors:
        errors.append("authors: at least one author ('human:<id>' or 'agent:<id>') is required")
    for a in authors:
        if not AUTHOR_RE.match(str(a)):
            errors.append(f"author {a!r} must look like 'human:<id>' or 'agent:<id>'")
    try:
        datetime.fromisoformat(str(manifest.get("created", "")).replace("Z", "+00:00"))
    except ValueError:
        errors.append("created must be an ISO 8601 timestamp")
    releases = manifest.get("releases") or []
    if not isinstance(releases, list) or not releases or not all(_is_int(r) for r in releases):
        errors.append("releases must be a non-empty list of ACS 5-year end years (integers)")
    # Present archive corruption must win over geography probes or API fallback.
    variables = manifest.get("variables")
    if resolve and isinstance(releases, list) and all(_is_int(r) for r in releases) and isinstance(variables, list):
        from ..metadata import preflight_archives
        for variable in variables:
            if isinstance(variable, Mapping) and "ref" in variable:
                table = _table_of(variable)
                if table:
                    preflight_archives(_dataset_for(table), releases)
    _check_geography(manifest.get("geography") or {}, errors)
    from ..tract_harmonization import validation_errors as _harmonization_errors
    errors.extend(_harmonization_errors(manifest.get("geography") or {}, manifest))
    level = manifest.get("confidence_level", 0.90)
    if not isinstance(level, (int, float)) or not 0 < float(level) < 1:
        errors.append("confidence_level must be in (0, 1), e.g. 0.90")
    corr = manifest.get("correction") or {}
    try:
        from ..multitest import _method
        _method(corr.get("method", "holm"))
    except ValueError as exc:
        errors.append(f"correction: {exc}")
    if corr.get("family", "all") not in ("all", "by_family"):
        errors.append("correction.family must be 'all' or 'by_family'")
    ds = manifest.get("data_source")
    if ds is not None:
        if not isinstance(ds, Mapping):
            errors.append("data_source must be an object {synthetic, description, generator}")
        else:
            if not isinstance(ds.get("synthetic"), bool):
                errors.append("data_source.synthetic is required and must be true or false")
            for k in ("description", "generator"):
                if k in ds and not isinstance(ds[k], str):
                    errors.append(f"data_source.{k} must be a string")
            for k in sorted(set(ds) - set(DATA_SOURCE_KEYS)):
                errors.append(f"data_source: unknown key {k!r}; allowed {DATA_SOURCE_KEYS}")
    if manifest.get("missing", "complete_case") != "complete_case":
        errors.append("missing: only 'complete_case' is supported")

    _check_variables(manifest, errors, resolve, client)
    variables = manifest.get("variables")
    names = [str(v.get("name")) for v in (variables if isinstance(variables, list) else []) if isinstance(v, Mapping)]
    derivations = manifest.get("derivations") or []
    for i, d in enumerate(derivations if isinstance(derivations, list) else [derivations]):
        if not isinstance(d, Mapping):
            errors.append(f"derivations[{i}] must be an object {{name, op, num, den}}")
            continue
        if d.get("op") == "age_standardized":
            _age_standardized_errors(d, errors)
        for r in _derivation_refs(d):
            if r not in names:
                errors.append(f"derivation {d.get('name')!r}: input {r!r} is not an earlier variable name")
        names.append(str(d.get("name")))
    for n in names:
        if not NAME_RE.match(n):
            errors.append(f"name {n!r} must be a Python identifier (used in formulas)")
    if len(set(names)) != len(names):
        errors.append("variable/derivation names must be unique")
    agg = manifest.get("aggregation")
    if agg is not None and not isinstance(agg.get("mapping"), Mapping):
        errors.append("aggregation.mapping must be an object GEOID -> group id")
    ext_names = external_names(manifest)
    if manifest.get("external") is not None:
        from ..health_sources import validate_external
        errors.extend(validate_external(manifest.get("external"), manifest.get("geography") or {},
                                        [int(r) for r in releases if _is_int(r)] if isinstance(releases, list)
                                        else [], names))
        if agg is not None:
            errors.append("external variables cannot be combined with aggregation (external values are per unit)")
    _check_adjustments(manifest, names, errors)
    _check_replicates(manifest, errors)

    for i, ex in enumerate(manifest.get("exclusions") or []):
        if ex.get("rule") not in EXCLUSION_RULES:
            errors.append(f"exclusions[{i}]: rule must be one of {EXCLUSION_RULES}")
        if ex.get("rule") == "cv_screen" and ex.get("action", "flag") not in ("flag", "exclude"):
            errors.append(f"exclusions[{i}]: action must be 'flag' or 'exclude'")
        for v in ex.get("variables") or []:
            if v not in names:
                errors.append(f"exclusions[{i}]: unknown variable {v!r}")

    analyses = manifest.get("analyses") or []
    if not analyses:
        errors.append("analyses: at least one analysis is required")
    from ..report_tables import _artifact_name
    ids = {}
    folded_ids: Dict[str, Any] = {}
    needs_replicates: List[str] = []  # replicate analyses declaring "replicates": "required"
    for i, a in enumerate(analyses):
        for k in _duplicate_spec_keys(a):
            errors.append(f"analyses[{i}]: {k!r} given both at the top level and in args; give it once")
        a = _normalize_analysis(a)
        method = a.get("method")
        if method not in ANALYSIS_METHODS:
            errors.append(f"analyses[{i}]: unsupported method {method!r}; supported {sorted(ANALYSIS_METHODS)}")
            continue
        aid = a.get("id")
        if aid in ids or not aid:
            errors.append(f"analyses[{i}]: id must be present and unique")
        elif str(aid).casefold() in folded_ids:
            # results-bundle artifacts are named after ids; reject now, not after every model has run
            errors.append(f"analyses[{i}]: id {aid!r} collides with {folded_ids[str(aid).casefold()]!r} on a "
                          "case-insensitive filesystem; ids must differ in more than letter case")
        else:
            try:
                _artifact_name(str(aid))
            except ValueError:
                errors.append(f"analyses[{i}]: id {aid!r} must be usable as a filename (letters, digits, '_', "
                              "'-', '.'; no path separators, ':', spaces at the end or reserved device names)")
        if aid:
            folded_ids.setdefault(str(aid).casefold(), aid)
        ids[aid] = method
        if method in REPLICATE_METHODS and a.get("replicates") == "required":
            needs_replicates.append(str(a.get("id")))
        for req in ANALYSIS_METHODS[method][0]:
            if req not in a:
                errors.append(f"analyses[{i}] ({method}): {req!r} is required")
        used = _formula_names(a["formula"]) if a.get("formula") else []
        for key in ("variables", "error_covariates"):
            used += list(a.get(key) or [])
        for key in ("variable", "variable_1", "variable_2"):
            if a.get(key):
                used.append(a[key])
        aargs = a.get("args") or {}
        outcome_name = str(a.get("formula", "")).split("~")[0].strip()
        count_outcome = (outcome_name if method == "fit_replicate" and aargs.get("model") == "poisson"
                         and outcome_name.endswith("_numerator") and outcome_name[:-10] in ext_names else None)
        if count_outcome and count_outcome in _formula_names(str(a.get("formula", "")).split("~", 1)[1]):
            errors.append("external count columns are allowed as the Poisson outcome only")
        for u in used:
            if u not in names and u not in ext_names and u != count_outcome:
                errors.append(f"analyses[{i}] ({a.get('id')}): {u!r} is not a manifest variable")
        ext_used = [u for u in used if u in ext_names or u == count_outcome]
        if ext_used:
            from ..health_sources import EXTERNAL_OUTCOME_METHODS
            outcome = _formula_names(str(a.get("formula", "")).split("~")[0]) if "~" in str(a.get("formula", "")) \
                else []
            if method not in EXTERNAL_OUTCOME_METHODS:
                errors.append(f"analyses[{i}] ({a.get('id')}): external variables {ext_used} can only be the outcome "
                              f"of {list(EXTERNAL_OUTCOME_METHODS)}")
            elif [u for u in ext_used if u not in outcome] or len(outcome) != 1:
                errors.append(f"analyses[{i}] ({a.get('id')}): external variables {ext_used} may only be the outcome "
                              "(alone): as covariates their model-based error would go uncorrected")
            elif method == "fit_replicate" and (a.get("args") or {}).get("target", "population") == "these_areas":
                errors.append(f"analyses[{i}] ({a.get('id')}): an external outcome is held fixed in the refits, so "
                              "target 'these_areas' (replicate SE alone) is refused; use 'population' or "
                              "'conservative'")
        if method == "fit_replicate":
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
        if method == "fit_eiv":
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
        scope = a.get("replicate_scope", "all")
        if scope not in REPLICATE_SCOPES:
            errors.append(f"analyses[{i}] ({a.get('id')}): replicate_scope must be one of {REPLICATE_SCOPES}")
        elif scope == "covariates_only":
            outcome = _formula_names(a["formula"].split("~")[0]) if "~" in str(a.get("formula", "")) else []
            if method != "fit_replicate":
                errors.append(f"analyses[{i}] ({a.get('id')}): replicate_scope 'covariates_only' applies to "
                              "fit_replicate only")
            elif (a.get("args") or {}).get("target", "population") == "these_areas":
                errors.append(f"analyses[{i}] ({a.get('id')}): replicate_scope 'covariates_only' cannot use "
                              "target 'these_areas' (its interval would rest on a sampling SE without the "
                              "outcome's sampling error); use 'population' or 'conservative'")
            elif len(outcome) != 1:
                errors.append(f"analyses[{i}] ({a.get('id')}): replicate_scope 'covariates_only' needs a formula "
                              "whose outcome is one manifest variable")
            # An outcome the VRE registry lists may still lack replicates for the analysed units (a line
            # missing from the file), so the declaration is allowed; create_manifest notes it and the run
            # records whether the outcome had replicates (it is held fixed either way: the hash governs).
    if needs_replicates and not census_vre_source(manifest):  # census_vre: _check_replicates
        overlap = release_overlap_message(manifest_releases(manifest),
                                          f"analyses {needs_replicates} require replicates")
        if overlap:
            errors.append(overlap)
    hyps = manifest.get("hypotheses") or []
    if not hyps:
        errors.append("hypotheses: at least one pre-registered hypothesis is required")
    hids = set()
    for i, h in enumerate(hyps):
        if not h.get("id") or h["id"] in hids:
            errors.append(f"hypotheses[{i}]: id must be present and unique")
        hids.add(h.get("id"))
        if h.get("direction", "two-sided") not in DIRECTIONS:
            errors.append(f"hypotheses[{i}]: direction must be one of {DIRECTIONS}")
        method = ids.get(h.get("analysis"))
        if method is None:
            errors.append(f"hypotheses[{i}]: analysis {h.get('analysis')!r} is not defined")
            continue
        if h.get("statistic") not in ANALYSIS_METHODS[method][1]:
            errors.append(f"hypotheses[{i}]: statistic {h.get('statistic')!r} not available from {method} "
                          f"(supported: {ANALYSIS_METHODS[method][1]})")
        need = {"coefficient": ("term",), "correlation": ("variables",), "trend_slope": (),
                "z_difference": ("geoid",)}.get(h.get("statistic"), ())
        for k in need:
            if k not in h:
                errors.append(f"hypotheses[{i}]: {k!r} is required for statistic {h.get('statistic')!r}")
        just = h.get("circularity_justification")
        if just is not None and not isinstance(just, str):
            errors.append(f"hypotheses[{i}]: circularity_justification must be text")
    if ext_names:
        errors.extend(circularity_errors(manifest))
    return errors
