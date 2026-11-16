# SPDX-License-Identifier: AGPL-3.0-or-later
"""Manifest run definitions."""

from census.data_integrity import integrity_errors
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple, Union
import numpy as np
import pandas as pd
from ..results import IncompleteReplicatesError, ModelResult
from .adjustments import (
    _apply_adjustments,
)
from .datasource import (
    resolve_data_source,
)
from .external import (
    external_names,
)
from .methods_text import (
    methods_section,
)
from .replicates import (
    _census_vre_replicates,
    _declared_covariates_only,
    _derive_replicates,
    _has_replicate_rows,
    _replicate_overlap,
    _replicate_rows,
    census_vre_source,
    replicates_digest,
)
from .schema import (
    BLOCKING_DEVIATIONS,
    CONFIRMATORY_REPLICATE_POLICY,
    INCOMPLETE_STATUS_TEXT,
    REPLICATE_METHODS,
    STATUS_CONFIRMATORY,
    STATUS_CONFIRMATORY_INCOMPLETE,
    STATUS_EXPLORATORY,
    _formula_names,
    _normalize_analysis,
    load_manifest,
    manifest_entities,
    manifest_hash,
    manifest_states,
    tables_and_refs,
)
from .validate import (
    validate_manifest,
)



# ---------------------------------------------------------------------------
# Exploratory labelling
# ---------------------------------------------------------------------------


def label_exploratory(result: Any, reason: str = "not in a pre-registered manifest",
                      manifest_hash_value: Optional[str] = None) -> Any:
    """Tag a result (result object with ``provenance`` or a dict) as exploratory.

    Use for any analysis run outside a manifest, including on the same data
    as a manifest run (pass its hash in ``manifest_hash_value``).
    """
    tag = {"analysis_status": STATUS_EXPLORATORY, "exploratory_reason": reason,
           "related_manifest_hash": manifest_hash_value}
    if hasattr(result, "provenance") and isinstance(result.provenance, dict):
        result.provenance.update(tag)
        if hasattr(result, "notes") and isinstance(result.notes, list):
            result.notes.append(f"EXPLORATORY: {reason}")
        return result
    if isinstance(result, dict):
        result.update(tag)
        return result
    raise TypeError("label_exploratory needs a result object with .provenance or a dict")


def analysis_status(result: Any) -> str:
    prov = getattr(result, "provenance", result if isinstance(result, dict) else {})
    return prov.get("analysis_status", STATUS_EXPLORATORY) if isinstance(prov, dict) else STATUS_EXPLORATORY


# ---------------------------------------------------------------------------
# Running
# ---------------------------------------------------------------------------


def _codebook_columns(codebook: pd.DataFrame, concept_id: str) -> Optional[Tuple[str, str, str]]:
    """(estimate slug, moe slug, estimate code) for a concept in a run_batch codebook."""
    rows = codebook[codebook["Concept_ID"].astype(str) == concept_id]
    est = rows[rows["Variable_Slug"].str.endswith(("_est", "_pct")) & ~rows["Variable_Slug"].str.endswith("_moe")]
    if est.empty:
        return None
    e = est.iloc[0]
    slug = str(e["Variable_Slug"])
    moe = f"{slug}_moe" if slug.endswith("_pct") else slug[: -len("_est")] + "_moe"
    return slug, moe, str(e["Variable_Code"])


def _wide_from_panel(panel: pd.DataFrame, columns: Mapping[str, Tuple[str, str, str]]) -> pd.DataFrame:
    """Panel (slugged) -> wide frame keyed by ACS codes (``<base>E``/``<base>M``)."""
    from ..stats import parse_variable_code
    out = pd.DataFrame({"GEOID": panel["geoid"].astype(str), "Year": panel["year"].astype("int64")})
    if "name" in panel.columns:
        out["NAME"] = panel["name"]
    for _, (est, moe, code) in columns.items():
        base, suffix = parse_variable_code(code) or (code.rstrip("E"), "E")
        out[f"{base}{suffix}"] = pd.to_numeric(panel[est], errors="coerce").to_numpy()
        out[f"{base}{'PM' if suffix == 'PE' else 'M'}"] = pd.to_numeric(panel[moe], errors="coerce").to_numpy()
    return out


def _one_sided(p: float, estimate: float, direction: str) -> float:
    if direction == "two-sided" or p is None or not np.isfinite(p):
        return p
    agrees = (estimate > 0) if direction == "greater" else (estimate < 0)
    return p / 2 if agrees else 1 - p / 2


def _run_analysis(a: Mapping[str, Any], frame: pd.DataFrame, level: float, replicates: Any,
                  correction: str, external: Sequence[str] = (), coords=None) -> Any:
    from .. import correlation, models, multitest, sae, trends
    a = _normalize_analysis(a)
    method, args = a["method"], dict(a.get("args") or {})
    for k in ("error_covariates", "variables", "variable", "geoid", "variable_1", "variable_2"):
        if k in a:
            args.setdefault(k, a[k])
    if method in REPLICATE_METHODS:
        # Confirmatory runs refuse incomplete replicates (PLAN_ROUND_11 Q2/D7);
        # the failure is recorded as a "replicates_incomplete" deviation.
        args["replicate_policy"] = CONFIRMATORY_REPLICATE_POLICY
    if args.get("spatial_se") is not None:
        args["coords"] = coords
    held_external = [v for v in _formula_names(str(a.get("formula", "")).split("~")[0]) if v in set(external) or (v.endswith("_numerator") and v[:-10] in set(external))]
    from .methods import METHODS
    if method not in METHODS:
        raise ValueError(f"unsupported method {method}")
    return METHODS[method].run(a, args, frame, level, replicates, correction,
                               {"held_external": held_external, "coords": coords})


def _statistic(h: Mapping[str, Any], res: Any) -> Dict[str, Any]:
    from .methods import STATISTIC_EXTRACTORS
    stat = h["statistic"]
    if stat not in STATISTIC_EXTRACTORS:
        raise ValueError(stat)
    return STATISTIC_EXTRACTORS[stat](h, res)


def _tag(result: Any, h: str, analysis_id: str, status: str = STATUS_CONFIRMATORY) -> Any:
    tag = {"analysis_status": status, "manifest_hash": h, "manifest_analysis_id": analysis_id}
    if hasattr(result, "provenance") and isinstance(result.provenance, dict):
        result.provenance.update(tag)
        return result
    if isinstance(result, pd.DataFrame):
        return {**tag, "rows": result}
    if isinstance(result, dict):
        return {**result, **tag}
    return result


def run_variant(
    run_dir: Union[str, Path],
    analysis: str,
    formula: Optional[str] = None,
    keep_prefixes: Optional[Sequence[str]] = None,
    drop_prefixes: Optional[Sequence[str]] = None,
    args: Optional[Mapping[str, Any]] = None,
    out_dir: Optional[Union[str, Path]] = None,
    label: Optional[str] = None,
) -> Dict[str, Any]:
    """Exploratory refit of one analysis of a completed run (PLAN_ROUND_21 Part 2, C7).

    Loads ``<run_dir>/manifest.json`` and the analysed data recorded in run.json (refusing files
    whose SHA-256 differs), applies the variant (``formula``; ``keep_prefixes``/``drop_prefixes``:
    GEOID prefixes, e.g. ["36"] or ["36005", "36047"]; ``args`` merged over the analysis args, e.g.
    {"cluster": "GEOID.str[:5]", "cluster_se": "jackknife"}), refits with the confirmatory code path
    and writes ``<out_dir>/variant_<analysis>_<label>.json`` labelled ``exploratory`` with the
    manifest hash. Never changes the confirmatory outputs.
    """
    import hashlib
    run_dir = Path(run_dir)
    run = json.loads((run_dir / "bundle" / "results" / "run.json").read_text(encoding="utf-8"))
    m = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest_hash(m) != run.get("manifest_hash"):
        raise ValueError("manifest.json does not match the run's manifest hash")
    data: Dict[str, pd.DataFrame] = {}
    for name, info in (run.get("analysed_data") or {}).items():
        if not isinstance(info, Mapping) or "path" not in info or "sha256" not in info:
            raise ValueError(f"run.json records no analysed {name} file ({info!r}); the run cannot be refitted")
        path = run_dir / info["path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != info["sha256"]:
            raise ValueError(f"{path} does not match run.json (SHA-256); refusing to analyse different data")
        df = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path, dtype={"GEOID": str})
        df["GEOID"] = df["GEOID"].astype(str)
        data[name] = df
    if "analysis_frame" not in data:
        raise ValueError("run.json lists no analysed analysis_frame")
    spec = next((a for a in m.get("analyses") or [] if a.get("id") == analysis), None)
    if spec is None:
        raise ValueError(f"analysis {analysis!r} is not in the manifest (ids: "
                         f"{[a.get('id') for a in m.get('analyses') or []]})")
    a = dict(_normalize_analysis(spec))
    if formula:
        a["formula"] = formula
    if args:
        a["args"] = {**(a.get("args") or {}), **dict(args)}
        if dict(args).get("spatial_se") is not None and a["args"].get("scale") == "robust" and "scale" not in args:
            a["args"].pop("scale")   # spatial (Conley) SEs replace the registered robust SEs in this variant
    frame, reps = data["analysis_frame"], data.get("replicates")
    mask = np.ones(len(frame), bool)
    if keep_prefixes:
        mask &= frame["GEOID"].str.startswith(tuple(str(p) for p in keep_prefixes)).to_numpy()
    if drop_prefixes:
        mask &= ~frame["GEOID"].str.startswith(tuple(str(p) for p in drop_prefixes)).to_numpy()
    frame = frame[mask].reset_index(drop=True)
    if reps is not None:
        reps = reps[reps["GEOID"].isin(set(frame["GEOID"]))].reset_index(drop=True)
    corr = (m.get("correction") or {}).get("method", "holm")
    coords, spatial_info = None, None
    if (a.get("args") or {}).get("spatial_se") is not None:
        from ..spatial_hac import unit_coordinates
        coords, spatial_info = unit_coordinates(frame["GEOID"], m["geography"]["level"], max(m["releases"]))
    res = _run_analysis(a, frame, float(m.get("confidence_level", 0.90)), reps, corr,
                        external=external_names(m), coords=coords)
    if spatial_info is not None:
        res.provenance["spatial_coordinates"] = spatial_info
    variant = {"analysis": analysis, "formula": a.get("formula"), "keep_prefixes": list(keep_prefixes or []),
               "drop_prefixes": list(drop_prefixes or []), "args": a.get("args") or {}}
    if label is not None and (not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", str(label)) or not str(label).strip(".")):
        raise ValueError("label must be 1-64 letters, digits, '_', '-' or '.' (it names the output file)")
    tag = label or hashlib.sha256(json.dumps(variant, sort_keys=True, default=str).encode()).hexdigest()[:10]
    out = {"analysis_status": "exploratory", "related_manifest_hash": run["manifest_hash"],
           "note": "exploratory variant of a pre-registered analysis; not confirmatory",
           "variant": variant, "units": int(len(frame)),
           "analysed_data": {k: v["sha256"] for k, v in run["analysed_data"].items()},
           "result": res.to_dict() if hasattr(res, "to_dict") else res}
    folder = Path(out_dir) if out_dir else run_dir / "exploratory"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"variant_{analysis}_{tag}.json"
    path.write_text(json.dumps(out, indent=2, default=str) + "\n", encoding="utf-8")
    out["path"] = str(path)
    return out


@integrity_errors
def run_manifest(
    manifest: Union[str, Path, Mapping[str, Any]], output_dir: Union[str, Path], client: Any = None,
    replicates: Any = None, use_cache: bool = True, replicates_synthetic: Optional[bool] = None,
    external_fetch: Optional[Callable[[str], bytes]] = None,
) -> Dict[str, Any]:
    """Execute a manifest exactly: plan -> extraction -> analysis frame ->
    derivations on replicates -> exclusions -> adjustments -> analyses -> hypothesis tests with the pre-registered
    correction -> results bundle (tables, figures, methods.md).

    ``replicates``: optional pre-fetched replicate long frame (from
    :func:`census.analysis.attach_replicates`) used by ``fit_replicate`` and
    ``correlation_matrix``; without it those report model-based SEs and a
    deviation is recorded when the analysis sets ``"replicates": "required"``.
    Replicate analyses run with ``replicate_policy="strict"`` (confirmatory):
    failed refits, rows held fixed, or stochastic variables without replicates
    stop the analysis and record a ``replicates_incomplete`` deviation.
    Supplied replicates are recorded as caller-supplied (not fetched from
    Census VRE files by this function) with the SHA-256 of their canonical form
    (:func:`replicates_sha256`); ``replicates_synthetic`` (default: the data
    source's synthetic flag, or ``replicates.attrs["synthetic"]``) marks them
    synthetic in the methods text.
    A manifest with ``"replicates": {"source": "census_vre"}`` fetches the
    Census VRE files itself (:func:`census.replicate.fetch_vre` and its cache)
    for its tables, geography and releases; the run records each file's URL and
    SHA-256 and the variables without published replicates
    (``replicates.unavailable``). Passing ``replicates`` as well is an error.
    ``analysis_status`` is ``"confirmatory"`` only without blocking deviations,
    else ``"confirmatory_incomplete"`` (see the module docstring).
    Never raises on data problems; returns ``success``, ``deviations``,
    ``hypotheses`` and the bundle manifest. The manifest hash is written into
    every output (results JSON, tables, figure sidecars, methods.md, bundle.json).
    ``external_fetch(url) -> bytes`` replaces the HTTP client of external sources (tests).
    """
    from ..analysis import analysis_frame
    from ..multitest import adjust_pvalues
    from ..pipeline import ResearchOptions, plan_extraction, run_batch
    from ..report_tables import _require_empty_bundle, data_citation

    m = load_manifest(manifest)
    errors = validate_manifest(m, resolve=True, client=client)
    if census_vre_source(m) and replicates is not None:
        errors.append("replicates: the manifest declares replicates.source 'census_vre' (fetched by run_manifest); "
                      "do not also supply replicates (replicates_path)")
    h = manifest_hash(m)
    out = Path(output_dir)
    if errors:
        return {"success": False, "manifest_hash": h, "errors": errors}
    try:
        _require_empty_bundle(out / "bundle")
    except (OSError, ValueError) as exc:  # the destination, not the manifest, is at fault
        return {"success": False, "manifest_hash": h, "errors": [], "output_error": str(exc)}
    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").write_text(json.dumps(m, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                                       encoding="utf-8", newline="\n")
    deviations: List[Dict[str, Any]] = []
    source, mismatch = resolve_data_source(m, client, use_cache)
    if mismatch:
        deviations.append({"kind": "data_source_mismatch", "detail": mismatch})
    level = float(m.get("confidence_level", 0.90))
    corr = m.get("correction") or {}
    corr_method = corr.get("method", "holm")
    releases = [int(r) for r in m["releases"]]
    geo = m["geography"]
    entities = manifest_entities(geo, years=releases)
    opts = ResearchOptions(use_cache=use_cache, include_codebook=True,
                           concordance_mode=m.get("concordance_mode", "fail"))

    # 1-2. plan and extraction, one table at a time
    columns: Dict[str, Tuple[str, str, str]] = {}
    panels: List[pd.DataFrame] = []
    extraction: Dict[str, Any] = {}
    name_of = {str(v["ref"]): str(v["name"]) for v in m["variables"]}
    codes_by_year: Dict[str, Dict[int, str]] = {}  # manifest name -> {release: ACS base code} (VRE rows)
    for table, refs in tables_and_refs(m).items():
        plan = plan_extraction(table, entities, releases, "panel", opts, variables=refs, client=client)
        plan_pub = {k: v for k, v in plan.items() if not k.startswith("_")}
        extraction[table] = {"plan": plan_pub}
        if geo.get("states") is not None:  # one request set per state, stacked into one panel
            extraction[table]["states"] = manifest_states(geo)
        if not plan.get("success"):
            deviations.append({"kind": "blocked_variable", "table": table, "variables": refs,
                               "detail": plan.get("message") or plan.get("error_code")})
            continue
        res = run_batch(table, entities, releases, str(out / "extraction" / table), "panel", opts,
                        client=client, variables=refs)
        extraction[table]["run"] = {k: res.get(k) for k in ("success", "failed_calls", "successful_calls",
                                                             "metadata_path", "panel_path", "advisories")}
        if not res.get("success"):
            deviations.append({"kind": "extraction_failed", "table": table, "variables": refs,
                               "detail": res.get("message") or res.get("error_code")})
            continue
        if res.get("failed_calls"):
            deviations.append({"kind": "failed_calls", "table": table, "detail": res["failed_calls"]})
        if not res.get("panel_path") or not res.get("codebook_path"):
            deviations.append({"kind": "extraction_failed", "table": table, "variables": refs,
                               "detail": "no data returned (every call failed)"})
            continue
        codebook = pd.read_csv(res["codebook_path"], dtype=str)
        cid_of = {s["input"]: s["concept_id"] for s in plan.get("selection", [])}
        conc = plan.get("_concordance")
        for ref in refs:
            concept = getattr(conc, "concepts", {}).get(cid_of.get(ref, ref))
            if concept is not None:
                codes_by_year[name_of[ref]] = {int(y): str(c) for y, c in concept.codes.items()}
        tcols = {}
        for ref in refs:
            cols = _codebook_columns(codebook, cid_of.get(ref, ref))
            if cols is None:
                deviations.append({"kind": "variable_missing_from_extraction", "table": table, "variable": ref})
            else:
                tcols[name_of[ref]] = cols
        panel = pd.read_csv(res["panel_path"], dtype={"geoid": str}) if str(res["panel_path"]).endswith(".csv") \
            else pd.read_parquet(res["panel_path"])
        panels.append(_wide_from_panel(panel, tcols))
        columns.update(tcols)

    # 3. analysis frame (tract harmonization, or optional aggregation, first)
    frame = None
    harmonization: Optional[Dict[str, Any]] = None
    crosswalk_by_name: Dict[str, pd.DataFrame] = {}
    if panels:
        wide = panels[0]
        for p in panels[1:]:
            wide = wide.merge(p.drop(columns=[c for c in ("NAME",) if c in p.columns]), on=["GEOID", "Year"],
                              how="outer")
        refs_by_name = {}
        for name, (_, _, code) in columns.items():
            refs_by_name[name] = code
        if geo.get("harmonize_tracts_to") is not None:
            from .. import tract_harmonization as th
            from ..pipeline import expand_states
            from ..stats import parse_variable_code
            target = int(geo["harmonize_tracts_to"])
            try:
                h_states = sorted({s for st in manifest_states(geo) if st for s in expand_states(st)})
                bases = {n: (parse_variable_code(c) or (c.rstrip("E"), "E"))[0] for n, c in refs_by_name.items()}
                tract_crosswalks = th.crosswalks(target, h_states, [th.weight_kind(c) for c in bases.values()],
                                                 releases=releases) \
                    if th.releases_to_apportion(releases, target) else {}  # nothing to apportion: no downloads
                crosswalk_by_name = {n: tract_crosswalks[th.weight_kind(c)] for n, c in bases.items()
                                     if th.weight_kind(c) in tract_crosswalks}
                wide, harmonization = th.harmonize_wide(wide, bases, target, tract_crosswalks)
                if harmonization.get("unmatched_source_tracts"):
                    deviations.append({"kind": "harmonization_incomplete", "detail": (
                        f"{len(harmonization['unmatched_source_tracts'])} source tract(s) are not in the tract "
                        "relationship file, so their values were not apportioned: "
                        + ", ".join(harmonization["unmatched_source_tracts"][:20]))})
            except Exception as exc:  # noqa: BLE001 - recorded as a blocking deviation, never substituted
                deviations.append({"kind": "harmonization_failed", "detail": f"{type(exc).__name__}: {exc}"})
                harmonization = {"target_vintage": target, "error": f"{type(exc).__name__}: {exc}"}
                wide = None
        if wide is not None and m.get("aggregation"):
            from ..aggregate import aggregate_geographies
            try:
                parts = []
                for year, sub in wide.groupby("Year"):
                    agg = aggregate_geographies(sub.drop(columns=["Year"]), m["aggregation"]["mapping"],
                                                estimate_cols=list(refs_by_name.values()))
                    agg["Year"] = year
                    parts.append(agg)
                wide = pd.concat(parts, ignore_index=True)
            except Exception as exc:
                deviations.append({"kind": "aggregation_failed", "detail": str(exc)})
                wide = None
        if wide is not None:
            try:
                frame = analysis_frame(wide, variables=refs_by_name, derive=m.get("derivations") or None)
            except Exception as exc:
                deviations.append({"kind": "analysis_frame_failed", "detail": str(exc)})

    # 3a. Census VRE replicates fetched for the manifest (replicates.source census_vre)
    vre_info: Optional[Dict[str, Any]] = None
    if census_vre_source(m) and frame is not None:
        try:
            replicates, vre_info = _census_vre_replicates(m, frame, codes_by_year, client,
                                                          crosswalk_by_name=crosswalk_by_name)
        except Exception as exc:  # noqa: BLE001 - recorded as a blocking deviation, never substituted
            deviations.append({"kind": "replicates_unavailable",
                               "detail": f"Census VRE replicates could not be fetched: {type(exc).__name__}: {exc}"})
            vre_info = {"source": "census_vre", "error": f"{type(exc).__name__}: {exc}"}
            replicates = None

    check = (vre_info or {}).get("apportioned_estimate_check") or {}
    bad = {n: c for n, c in check.items() if c.get("max_rel_diff") is not None and c["max_rel_diff"] > 1e-6}
    if bad:
        deviations.append({"kind": "harmonization_mismatch", "detail": (
            "apportioned Census VRE estimates differ from the apportioned published estimates for "
            + ", ".join(f"{n} (max relative difference {c['max_rel_diff']:.3g})" for n, c in sorted(bad.items()))
            + "; the replicate SEs may not belong to the analysed values")})

    # 3b. derivations on supplied replicates
    work_reps = replicates
    derived_on_replicates: Dict[str, Dict[str, int]] = {}
    if frame is not None and replicates is not None and m.get("derivations"):
        try:
            frame, work_reps, derived_on_replicates = _derive_replicates(frame, replicates, m)
        except Exception as exc:  # noqa: BLE001 - data problems are deviations; run_manifest never raises on them
            # replicate SEs of the derivations are unavailable: blocking, as when a strict replicate
            # analysis meets them; the analyses run on the published SEs and record their own outcome
            deviations.append({"kind": "replicates_incomplete", "detail": "derivations on replicates failed: "
                               f"{type(exc).__name__}: {exc}"})

    # 3c. external variables (PLAN_ROUND_21 B3), joined on GEOID after the ACS frame
    external_info: Optional[Dict[str, Any]] = None
    joined_external: List[str] = []
    if frame is not None and m.get("external"):
        from .. import health_sources as hs
        ext_names = external_names(m)
        ext_columns = set(ext_names) | {n + "_numerator" for n in ext_names}
        required = sorted({v for a in m["analyses"] for v in _formula_names(str(_normalize_analysis(a).get("formula", "")))
                           if set(_formula_names(str(_normalize_analysis(a).get("formula", "")))) & ext_columns}
                          - ext_columns)
        try:
            ext_wide, ext_prov = hs.load_external(m["external"], str(geo["level"]),
                                                  [s for s in manifest_states(geo) if s], fetch=external_fetch)
            frame, join = hs.join_external(frame, ext_wide, ext_names, required=required)
            for name in ext_names:
                if name + "_numerator" in frame:
                    frame.loc[frame[name].isna(), name + "_numerator"] = np.nan
            joined_external = ext_names
            external_info = {"variables": m["external"], "sources": ext_prov, "join": join,
                             "required_acs_variables": required}
            limits = hs.join_limit(m["external"])
            join["missing_limit"] = limits
            over = {n: s for n, s in join["missing_share_by_variable"].items()
                    if not s <= limits.get(n, hs.JOIN_MISSING_LIMIT)}
            if over:
                deviations.append({"kind": "external_join_failed", "detail": (
                    "; ".join(f"{n}: {s:.1%} of {join['complete_acs_units']} units with complete ACS data have no "
                              f"value (> {limits.get(n, hs.JOIN_MISSING_LIMIT):.0%})" for n, s in over.items())
                    + "; a geography-vintage mismatch is likely. Examples: "
                    + ", ".join(join["examples_without_external"][:5]))})
        except Exception as exc:  # noqa: BLE001 - recorded as a blocking deviation, never substituted
            deviations.append({"kind": "external_unavailable", "detail": f"{type(exc).__name__}: {exc}"})
            external_info = {"variables": m["external"], "error": f"{type(exc).__name__}: {exc}"}

    # 4. exclusions (before adjustments: a pre-registered exclusion can remove a unit without an
    # RPP area; the CV screen gives the same rows either way, since the RPP factor leaves CVs unchanged)
    exclusion_log: List[Dict[str, Any]] = []
    if frame is not None:
        from ..models import reliability_screen
        for ex in m.get("exclusions") or []:
            if ex["rule"] == "geoid_exclude":
                drop = frame["GEOID"].isin([str(g) for g in ex.get("geoids", [])])
                frame = frame[~drop].reset_index(drop=True)
                exclusion_log.append({"rule": "geoid_exclude", "rows_excluded": int(drop.sum())})
            else:
                thr = float(ex.get("threshold", 30.0))
                vars_ = [v for v in ex.get("variables") or [] if f"{v}_cv" in frame.columns]
                flagged = reliability_screen(frame, vars_, threshold=thr)
                entry = {"rule": "cv_screen", "threshold": thr, "variables": vars_,
                         "action": ex.get("action", "flag"), "rows_flagged": int(flagged["GEOID"].nunique())
                         if len(flagged) else 0}
                if entry["action"] == "exclude" and len(flagged):
                    keys = [k for k in ("GEOID", "Year") if k in flagged.columns]
                    bad = frame[keys].merge(flagged[keys].drop_duplicates(), how="left", indicator=True)
                    keep = (bad["_merge"] == "left_only").to_numpy()
                    entry["rows_excluded"] = int((~keep).sum())
                    frame = frame[keep].reset_index(drop=True)
                exclusion_log.append(entry)

    # 4b. pre-registered adjustments (a unit still without an RPP area blocks: adjustment_failed)
    adjustment_log: List[Dict[str, Any]] = []
    if frame is not None and m.get("adjustments"):
        frame, work_reps, adjustment_log, failure = _apply_adjustments(frame, work_reps, m, releases)
        if failure:
            deviations.append({"kind": "adjustment_failed", "detail": failure})
            frame = None
    if frame is not None:  # replicate-SE coverage of the units analysed
        counts = {name: _replicate_rows(frame, name) for name in derived_on_replicates}
        derived_on_replicates = {k: v for k, v in counts.items() if v["rows_replicate"]}

    if frame is not None and external_info is not None:
        external_info["low_count_kept"] = {
            e["name"]: int((frame[e["name"] + "_numerator"] < 20).sum())
            for e in m.get("external", []) if e.get("source") == "chr" and e.get("measure") == "v037"
            and e["name"] + "_numerator" in frame
        }
    coords, spatial_info = None, None
    if frame is not None and any((_normalize_analysis(a).get("args") or {}).get("spatial_se") is not None
                                 for a in m["analyses"]):
        from ..spatial_hac import unit_coordinates
        coords, spatial_info = unit_coordinates(frame["GEOID"], geo["level"], max(releases))

    # 5. analyses
    available = set(columns) | {str(d["name"]) for d in m.get("derivations") or []} | set(joined_external)
    available |= {n + "_numerator" for n in joined_external}
    results: Dict[str, Any] = {}
    # caller-supplied replicates of overlapping releases: refused (census_vre is refused at validation)
    rep_overlap = _replicate_overlap(replicates) if replicates is not None and not census_vre_source(m) else None
    declared_fixed = _declared_covariates_only(m)
    fixed_had_replicates: Dict[str, List[str]] = {}
    for a in m["analyses"]:
        a = _normalize_analysis(a)
        aid = a["id"]
        needed = set(_formula_names(a.get("formula", "")))
        for k in ("variables", "error_covariates"):
            needed |= set(a.get(k) or [])
        needed |= {a[k] for k in ("variable", "variable_1", "variable_2") if a.get(k)}
        if frame is None or not needed <= available:
            deviations.append({"kind": "analysis_not_run", "analysis": aid,
                               "detail": f"unavailable variables: {sorted(needed - available)}"
                               if frame is not None else "no analysis frame"})
            continue
        if a.get("replicates") == "required" and replicates is None and a["method"] in REPLICATE_METHODS:
            deviations.append({"kind": "replicates_unavailable", "analysis": aid,
                               "detail": "manifest requires replicate SEs; none supplied, analysis not run"})
            continue
        if census_vre_source(m) and replicates is None and a["method"] in REPLICATE_METHODS:
            deviations.append({"kind": "replicates_unavailable", "analysis": aid,
                               "detail": "manifest declares Census VRE replicates; none were fetched or published "
                                         "for its variables (see replicates.unavailable), analysis not run"})
            continue
        if rep_overlap and a["method"] in REPLICATE_METHODS:
            deviations.append({"kind": "replicates_overlapping_releases", "analysis": aid,
                               "detail": rep_overlap + "; analysis not run"})
            continue
        if aid in declared_fixed and work_reps is not None:
            had = [v for v in declared_fixed[aid] if _has_replicate_rows(work_reps, v)]
            if had:
                fixed_had_replicates[aid] = had
        try:
            results[aid] = _run_analysis(a, frame, level, work_reps, corr_method, external=joined_external, coords=coords)
        except Exception as exc:
            kind = "replicates_incomplete" if isinstance(exc, IncompleteReplicatesError) else "analysis_failed"
            deviations.append({"kind": kind, "analysis": aid, "detail": f"{type(exc).__name__}: {exc}"})

    # 5a. the analysed data, for follow-up (exploratory) work on exactly what the models saw
    try:
        analysed_data = _write_analysed_data(out, frame, work_reps)
    except Exception as exc:  # noqa: BLE001 - a convenience copy must never cost the confirmatory run
        analysed_data = {"error": f"analysed data not written: {type(exc).__name__}: {exc}"}

    # 6. hypotheses with the pre-registered correction
    rows = []
    for hyp in m["hypotheses"]:
        row = {"id": hyp["id"], "analysis": hyp["analysis"], "statistic": hyp["statistic"],
               "direction": hyp.get("direction", "two-sided"), "family": hyp.get("family", "primary"),
               "statement": hyp.get("statement", "")}
        res = results.get(hyp["analysis"])
        if res is None:
            row.update(status="not_tested", estimate=None, p_value=None)
            deviations.append({"kind": "hypothesis_not_tested", "hypothesis": hyp["id"],
                               "detail": f"analysis {hyp['analysis']} did not run"})
        else:
            try:
                s = _statistic(hyp, res)
                row.update(s, status="tested",
                           p_value=_one_sided(s["p_two_sided"], s["estimate"], row["direction"]))
            except Exception as exc:
                row.update(status="not_tested", estimate=None, p_value=None)
                deviations.append({"kind": "hypothesis_not_tested", "hypothesis": hyp["id"], "detail": str(exc)})
        spec = next(_normalize_analysis(a) for a in m["analyses"] if a["id"] == hyp["analysis"])
        if spec["method"] == "fit_replicate" and (spec.get("args") or {}).get("model") == "binomial":
            for source_key, target in (("estimate", "odds_ratio"), ("ci_lower", "odds_ratio_lower"),
                                   ("ci_upper", "odds_ratio_upper")):
                row[target] = float(np.exp(row[source_key])) if row.get(source_key) is not None else None
        rows.append(row)
    hyp_df = pd.DataFrame(rows)
    hyp_df["p_adjusted"] = np.nan
    groups = [hyp_df.index] if corr.get("family", "all") == "all" else \
        [g.index for _, g in hyp_df.groupby("family")]
    for idx in groups:
        p = pd.to_numeric(hyp_df.loc[idx, "p_value"], errors="coerce")
        hyp_df.loc[idx, "p_adjusted"] = np.asarray(adjust_pvalues(p.to_numpy(float), corr_method))
    hyp_df["significant"] = hyp_df["p_adjusted"] < (1 - level)
    hyp_df["manifest_hash"] = h

    # 7. bundle
    complete = not any(d["kind"] in BLOCKING_DEVIATIONS for d in deviations)
    status = (STATUS_EXPLORATORY if m.get("exploratory", False) else
              STATUS_CONFIRMATORY if complete else STATUS_CONFIRMATORY_INCOMPLETE)
    if m.get("exploratory"):
        hyp_df["analysis_status"] = status
    rep_info = None
    if vre_info is not None:
        rep_info = dict(vre_info)
        if replicates is not None:
            digest, reason = replicates_digest(replicates)
            rep_info.update(rows=int(len(replicates)), sha256=digest)
            if digest is None:
                rep_info["sha256_unavailable"] = reason
        if derived_on_replicates:
            rep_info["derived_on_replicates"] = list(derived_on_replicates)
            rep_info["derived_on_replicates_rows"] = derived_on_replicates
        scaled = [v for a in adjustment_log for v in a["variables"]]
        if scaled and replicates is not None:
            rep_info["scaled_by_adjustments"] = scaled
    elif replicates is not None:
        if replicates_synthetic is None:
            attrs = getattr(replicates, "attrs", {}) or {}
            replicates_synthetic = bool(attrs.get("synthetic", source["synthetic"]))
        digest, reason = replicates_digest(replicates)
        rep_info = {"source": "caller_supplied", "synthetic": bool(replicates_synthetic),
                    "rows": int(len(replicates)), "sha256": digest}
        if digest is None:
            rep_info["sha256_unavailable"] = reason
        if derived_on_replicates:
            rep_info["derived_on_replicates"] = list(derived_on_replicates)
            rep_info["derived_on_replicates_rows"] = derived_on_replicates
        scaled = [v for a in adjustment_log for v in a["variables"]]
        if scaled:
            rep_info["scaled_by_adjustments"] = scaled
    if rep_info is not None and declared_fixed:
        rep_info["declared_covariates_only"] = declared_fixed
        if fixed_had_replicates:
            # the hashed declaration governs: the outcome stays fixed although replicates were available
            rep_info["covariates_only_outcome_had_replicates"] = fixed_had_replicates
            rep_info.setdefault("notes", []).extend(
                f"analysis {aid}: replicate_scope 'covariates_only' was declared and the outcome {names} was held "
                "at its estimate in every refit as pre-registered, although replicates were available for it in "
                "this run; se_sampling excludes the outcome's sampling error"
                for aid, names in fixed_had_replicates.items())
    tagged = {aid: _tag(r, h, aid, status) for aid, r in results.items()}
    run_info = {"manifest_hash": h, "analysis_status": status, "deviations": deviations,
                "exclusions": exclusion_log, "extraction": extraction, "n_units": None if frame is None
                else int(len(frame)), "title": m.get("title"), "data_source": source, "replicates": rep_info}
    if spatial_info is not None:
        run_info["spatial_coordinates"] = spatial_info
    if m.get("adjustments"):
        run_info["adjustments"] = adjustment_log
    if harmonization is not None:
        run_info["harmonization"] = harmonization
    if external_info is not None:
        run_info["external"] = external_info
    if analysed_data:
        run_info["analysed_data"] = analysed_data
    if not complete:
        run_info["status_note"] = INCOMPLETE_STATUS_TEXT
    tables_used = sorted(tables_and_refs(m))
    citation = data_citation(releases, tables_used, synthetic=source["synthetic"],
                             description=source.get("description"))
    if external_info and external_info.get("sources"):
        citation = citation + " External data: " + " ".join(p["citation"] for p in external_info["sources"])
    bundle = _write_bundle(out / "bundle", m, h, tagged, hyp_df, run_info, citation)
    out_res = {"success": complete, "analysis_status": status, "data_source": source, "replicates": rep_info,
               "manifest_hash": h, "deviations": deviations, "hypotheses": hyp_df, "results": tagged,
               "frame": frame, "bundle": bundle, "output_dir": str(out), "errors": []}
    if m.get("adjustments"):
        out_res["adjustments"] = adjustment_log
    if external_info is not None:
        out_res["external"] = external_info
    return out_res


def _write_analysed_data(out: Path, frame: Optional[pd.DataFrame], replicates: Any) -> Dict[str, Any]:
    """Write the analysis frame and replicates as the analyses received them (after derivations,
    exclusions and adjustments) to ``out/analysed/``; returns {name: {path, sha256, rows}}.

    Parquet when pyarrow is available, else CSV. Outside the bundle (the replicates can be large);
    their hashes are in run.json so a follow-up analysis can show it used the same data."""
    import hashlib
    written: Dict[str, Any] = {}
    folder = out / "analysed"
    for name, df in (("analysis_frame", frame), ("replicates", replicates)):
        if not isinstance(df, pd.DataFrame) or df.empty:
            continue
        folder.mkdir(parents=True, exist_ok=True)
        for stale in (folder / f"{name}.parquet", folder / f"{name}.csv"):  # never mix with an earlier run's copy
            stale.unlink(missing_ok=True)
        data = df.reset_index(drop=True)
        try:
            path = folder / f"{name}.parquet"
            data.to_parquet(path, index=False)
        except Exception:  # noqa: BLE001 - no pyarrow, or a column pyarrow cannot store: CSV instead
            (folder / f"{name}.parquet").unlink(missing_ok=True)
            path = folder / f"{name}.csv"
            data.to_csv(path, index=False)
        written[name] = {"path": str(path.relative_to(out)), "rows": int(len(data)),
                         "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    return written


def _write_bundle(folder: Path, m, h, results, hyp_df, run_info, citation) -> Dict[str, Any]:
    from .. import figures as figs
    from ..report_tables import ReportTable, correlation_table, regression_table
    from ..results import CorrelationResult, ModelResult, SmallAreaResult
    note = f"Pre-registered analysis; manifest SHA-256 {h}."
    fig_source = f"{citation} {note}"
    tables, figures_ = {}, {}
    model_results = {aid: r for aid, r in results.items() if isinstance(r, ModelResult)}
    if model_results:
        t = regression_table(model_results, correction=(m.get("correction") or {}).get("method", "holm"))
        t.notes.append(note)
        t.data = t.data.assign(manifest_hash=h)
        tables["regression"] = t
        figures_["coefficients"] = (figs.coefficient_plot, {"results": model_results, "manifest_hash": h,
                                                            "data_source": fig_source})
    for aid, r in results.items():
        if isinstance(r, CorrelationResult):
            t = correlation_table(r)
            t.notes.append(note)
            t.data = t.data.assign(manifest_hash=h)
            tables[f"correlation_{aid}"] = t
            figures_[f"correlation_{aid}"] = (figs.correlation_heatmap, {"result": r, "manifest_hash": h,
                                                                         "data_source": fig_source})
        if isinstance(r, SmallAreaResult):
            figures_[f"shrinkage_{aid}"] = (figs.shrinkage_plot, {"result": r, "manifest_hash": h,
                                                                  "data_source": fig_source})
    cols = ["id", "statistic", "direction", "estimate", "p_value", "p_adjusted", "significant", "status"]
    cols += [c for c in ("odds_ratio", "odds_ratio_lower", "odds_ratio_upper") if c in hyp_df]
    if m.get("exploratory"):
        cols.append("analysis_status")
    show = hyp_df.reindex(columns=cols)
    tables["hypotheses"] = ReportTable(
        title="Exploratory hypotheses" if m.get("exploratory") else "Pre-registered hypotheses", display=show.astype(object).where(show.notna(), "").astype(str),
        data=hyp_df, notes=[note, f"p-values adjusted by {(m.get('correction') or {}).get('method', 'holm')} "
                                  f"(family: {(m.get('correction') or {}).get('family', 'all')})."])
    payload = dict(results)
    payload["hypotheses"] = {"manifest_hash": h, "rows": hyp_df}
    payload["run"] = run_info
    from ..report_tables import results_bundle
    provenance = {"manifest_hash": h, "analysis_status": run_info["analysis_status"],
                  "deviations": len(run_info["deviations"]), "data_source": run_info.get("data_source"),
                  "replicates": run_info.get("replicates")}
    if "adjustments" in run_info:  # RPP provenance: years, areas, table hash
        provenance["adjustments"] = [{k: a[k] for k in ("type", "variables", "areas", "dollar_year", "rpp_year",
                                                        "rpp_year_source", "rpp_areas", "boundary_source",
                                                        "rpp_table", "rpp_years", "price_index", "order",
                                                        "releases") if k in a}
                                     for a in run_info["adjustments"]]
    return results_bundle(folder, tables=tables, figures=figures_, methods=methods_section(m, run_info),
                          results=payload, provenance=provenance, citation=citation)
