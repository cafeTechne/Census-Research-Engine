# SPDX-License-Identifier: AGPL-3.0-or-later
"""Manifest run definitions."""

from census.data_integrity import integrity_errors
from dataclasses import dataclass, field
import hashlib
import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple, Union
import numpy as np
import pandas as pd
if TYPE_CHECKING:
    from ..pipeline import ResearchOptions

from ..results import IncompleteReplicatesError, ModelResult
from .adjustments import (
    _apply_adjustments as _apply_adjustment_values,
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
    _derive_replicates as _derive_replicate_values,
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
                               {"held_external": held_external, "coords": coords, "external": external,
                                "wonder_names": frame.attrs.get("wonder_columns",())})


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
    wonder_names = [str(e["name"]) for e in m.get("external",[]) if e.get("source")=="wonder"]
    if wonder_names:
        from ..wonder_outputs import restore_snapshot
        frame = restore_snapshot(frame,wonder_names)
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


@dataclass
class RunState:
    """Values shared by the ordered stages; temporary variables stay stage-local.

    Only _prepare returns early (validation/output errors). Other stages record
    deviations and finish; no unused result sentinel is needed in the driver.
    """
    m: Dict[str, Any]
    h: str
    out: Path
    client: Any
    use_cache: bool
    replicates: Any
    external_fetch: Optional[Callable[[str], bytes]]
    replicates_synthetic: Optional[bool]
    level: float
    corr: Dict[str, Any]
    corr_method: str
    releases: List[int]
    geo: Dict[str, Any]
    entities: List[Any]
    opts: "ResearchOptions"
    source: Dict[str, Any]
    deviations: List[Dict[str, Any]] = field(default_factory=list)
    checkpoint: bool = False
    checkpoint_log: Dict[str, Any] = field(default_factory=dict)
    columns: Dict[str, Tuple[str, str, str]] = field(default_factory=dict)
    panels: List[pd.DataFrame] = field(default_factory=list)
    extraction: Dict[str, Any] = field(default_factory=dict)
    codes_by_year: Dict[str, Dict[int, str]] = field(default_factory=dict)
    frame: Optional[pd.DataFrame] = None
    harmonization: Optional[Dict[str, Any]] = None
    crosswalk_by_name: Dict[str, pd.DataFrame] = field(default_factory=dict)
    vre_info: Optional[Dict[str, Any]] = None
    work_reps: Any = None
    derived_on_replicates: Dict[str, Dict[str, int]] = field(default_factory=dict)
    external_info: Optional[Dict[str, Any]] = None
    joined_external: List[str] = field(default_factory=list)
    joined_context: List[str] = field(default_factory=list)
    exclusion_log: List[Dict[str, Any]] = field(default_factory=list)
    adjustment_log: List[Dict[str, Any]] = field(default_factory=list)
    coords: Optional[pd.DataFrame] = None
    spatial_info: Optional[Dict[str, Any]] = None
    results: Dict[str, Any] = field(default_factory=dict)
    declared_fixed: Dict[str, List[str]] = field(default_factory=dict)
    fixed_had_replicates: Dict[str, List[str]] = field(default_factory=dict)
    analysed_data: Dict[str, Any] = field(default_factory=dict)
    hyp_df: Optional[pd.DataFrame] = None


def _prepare(manifest: Union[str, Path, Mapping[str, Any]], output_dir: Union[str, Path],
             client: Any, replicates: Any, use_cache: bool, replicates_synthetic: Optional[bool],
             external_fetch: Optional[Callable[[str], bytes]]) -> Union[RunState, Dict[str, Any]]:
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

    return RunState(
        m=m,
        h=h,
        out=out,
        client=client,
        use_cache=use_cache,
        replicates=replicates,
        external_fetch=external_fetch,
        replicates_synthetic=replicates_synthetic,
        level=level,
        corr=corr,
        corr_method=corr_method,
        releases=releases,
        geo=geo,
        entities=entities,
        opts=opts,
        source=source,
        deviations=deviations,
    )


def _extract(state: RunState) -> None:
    from ..pipeline import plan_extraction, run_batch
    # 1-2. plan and extraction, one table at a time
    state.columns: Dict[str, Tuple[str, str, str]] = {}
    state.panels: List[pd.DataFrame] = []
    state.extraction: Dict[str, Any] = {}
    name_of = {str(v["ref"]): str(v["name"]) for v in state.m["variables"]}
    state.codes_by_year: Dict[str, Dict[int, str]] = {}  # manifest name -> {release: ACS base code} (VRE rows)
    for table, refs in tables_and_refs(state.m).items():
        plan = plan_extraction(table, state.entities, state.releases, "panel", state.opts, variables=refs, client=state.client)
        plan_pub = {k: v for k, v in plan.items() if not k.startswith("_")}
        state.extraction[table] = {"plan": plan_pub}
        if state.geo.get("states") is not None:  # one request set per state, stacked into one panel
            state.extraction[table]["states"] = manifest_states(state.geo)
        if not plan.get("success"):
            state.deviations.append({"kind": "blocked_variable", "table": table, "variables": refs,
                               "detail": plan.get("message") or plan.get("error_code")})
            continue
        res = run_batch(table, state.entities, state.releases, str(state.out / "extraction" / table), "panel", state.opts,
                        client=state.client, variables=refs)
        state.extraction[table]["run"] = {k: res.get(k) for k in ("success", "failed_calls", "successful_calls",
                                                             "metadata_path", "panel_path", "advisories")}
        if not res.get("success"):
            state.deviations.append({"kind": "extraction_failed", "table": table, "variables": refs,
                               "detail": res.get("message") or res.get("error_code")})
            continue
        if res.get("failed_calls"):
            state.deviations.append({"kind": "failed_calls", "table": table, "detail": res["failed_calls"]})
        if not res.get("panel_path") or not res.get("codebook_path"):
            state.deviations.append({"kind": "extraction_failed", "table": table, "variables": refs,
                               "detail": "no data returned (every call failed)"})
            continue
        codebook = pd.read_csv(res["codebook_path"], dtype=str)
        cid_of = {s["input"]: s["concept_id"] for s in plan.get("selection", [])}
        conc = plan.get("_concordance")
        for ref in refs:
            concept = getattr(conc, "concepts", {}).get(cid_of.get(ref, ref))
            if concept is not None:
                state.codes_by_year[name_of[ref]] = {int(y): str(c) for y, c in concept.codes.items()}
        tcols = {}
        for ref in refs:
            cols = _codebook_columns(codebook, cid_of.get(ref, ref))
            if cols is None:
                state.deviations.append({"kind": "variable_missing_from_extraction", "table": table, "variable": ref})
            else:
                tcols[name_of[ref]] = cols
        panel = pd.read_csv(res["panel_path"], dtype={"geoid": str}) if str(res["panel_path"]).endswith(".csv") \
            else pd.read_parquet(res["panel_path"])
        state.panels.append(_wide_from_panel(panel, tcols))
        state.columns.update(tcols)


def _build_frame(state: RunState) -> None:
    from ..analysis import analysis_frame
    # 3. analysis frame (tract harmonization, or optional aggregation, first)
    state.frame = None
    state.harmonization: Optional[Dict[str, Any]] = None
    state.crosswalk_by_name: Dict[str, pd.DataFrame] = {}
    if state.panels:
        wide = state.panels[0]
        for p in state.panels[1:]:
            wide = wide.merge(p.drop(columns=[c for c in ("NAME",) if c in p.columns]), on=["GEOID", "Year"],
                              how="outer")
        refs_by_name = {}
        for name, (_, _, code) in state.columns.items():
            refs_by_name[name] = code
        if state.geo.get("harmonize_tracts_to") is not None:
            from .. import tract_harmonization as th
            from ..pipeline import expand_states
            from ..stats import parse_variable_code
            target = int(state.geo["harmonize_tracts_to"])
            try:
                h_states = sorted({s for st in manifest_states(state.geo) if st for s in expand_states(st)})
                bases = {n: (parse_variable_code(c) or (c.rstrip("E"), "E"))[0] for n, c in refs_by_name.items()}
                tract_crosswalks = th.crosswalks(target, h_states, [th.weight_kind(c) for c in bases.values()],
                                                 releases=state.releases) \
                    if th.releases_to_apportion(state.releases, target) else {}  # nothing to apportion: no downloads
                state.crosswalk_by_name = {n: tract_crosswalks[th.weight_kind(c)] for n, c in bases.items()
                                     if th.weight_kind(c) in tract_crosswalks}
                wide, state.harmonization = th.harmonize_wide(wide, bases, target, tract_crosswalks)
                if state.harmonization.get("unmatched_source_tracts"):
                    state.deviations.append({"kind": "harmonization_incomplete", "detail": (
                        f"{len(state.harmonization['unmatched_source_tracts'])} source tract(s) are not in the tract "
                        "relationship file, so their values were not apportioned: "
                        + ", ".join(state.harmonization["unmatched_source_tracts"][:20]))})
            except Exception as exc:  # noqa: BLE001 - recorded as a blocking deviation, never substituted
                state.deviations.append({"kind": "harmonization_failed", "detail": f"{type(exc).__name__}: {exc}"})
                state.harmonization = {"target_vintage": target, "error": f"{type(exc).__name__}: {exc}"}
                wide = None
        if wide is not None and state.m.get("aggregation"):
            from ..aggregate import aggregate_geographies
            try:
                parts = []
                for year, sub in wide.groupby("Year"):
                    agg = aggregate_geographies(sub.drop(columns=["Year"]), state.m["aggregation"]["mapping"],
                                                estimate_cols=list(refs_by_name.values()))
                    agg["Year"] = year
                    parts.append(agg)
                wide = pd.concat(parts, ignore_index=True)
            except Exception as exc:
                state.deviations.append({"kind": "aggregation_failed", "detail": str(exc)})
                wide = None
        if wide is not None:
            try:
                state.frame = analysis_frame(wide, variables=refs_by_name, derive=state.m.get("derivations") or None)
            except Exception as exc:
                state.deviations.append({"kind": "analysis_frame_failed", "detail": str(exc)})


def _fetch_vre(state: RunState) -> None:
    # 3a. Census VRE replicates fetched for the manifest (replicates.source census_vre)
    state.vre_info: Optional[Dict[str, Any]] = None
    if census_vre_source(state.m) and state.frame is not None:
        try:
            state.replicates, state.vre_info = _census_vre_replicates(state.m, state.frame, state.codes_by_year, state.client,
                                                          crosswalk_by_name=state.crosswalk_by_name)
        except Exception as exc:  # noqa: BLE001 - recorded as a blocking deviation, never substituted
            state.deviations.append({"kind": "replicates_unavailable",
                               "detail": f"Census VRE replicates could not be fetched: {type(exc).__name__}: {exc}"})
            state.vre_info = {"source": "census_vre", "error": f"{type(exc).__name__}: {exc}"}
            state.replicates = None

    check = (state.vre_info or {}).get("apportioned_estimate_check") or {}
    bad = {n: c for n, c in check.items() if c.get("max_rel_diff") is not None and c["max_rel_diff"] > 1e-6}
    if bad:
        state.deviations.append({"kind": "harmonization_mismatch", "detail": (
            "apportioned Census VRE estimates differ from the apportioned published estimates for "
            + ", ".join(f"{n} (max relative difference {c['max_rel_diff']:.3g})" for n, c in sorted(bad.items()))
            + "; the replicate SEs may not belong to the analysed values")})


def _derive_replicates(state: RunState) -> None:
    # 3b. derivations on supplied replicates
    state.work_reps = state.replicates
    state.derived_on_replicates: Dict[str, Dict[str, int]] = {}
    if state.frame is not None and state.replicates is not None and state.m.get("derivations"):
        try:
            state.frame, state.work_reps, state.derived_on_replicates = _derive_replicate_values(state.frame, state.replicates, state.m)
        except Exception as exc:  # noqa: BLE001 - data problems are deviations; run_manifest never raises on them
            # replicate SEs of the derivations are unavailable: blocking, as when a strict replicate
            # analysis meets them; the analyses run on the published SEs and record their own outcome
            state.deviations.append({"kind": "replicates_incomplete", "detail": "derivations on replicates failed: "
                               f"{type(exc).__name__}: {exc}"})


def _join_external(state: RunState) -> None:
    # 3c. external variables (PLAN_ROUND_21 B3), joined on GEOID after the ACS frame
    state.external_info: Optional[Dict[str, Any]] = None
    state.joined_external: List[str] = []
    if state.frame is not None and state.m.get("external"):
        from .. import health_sources as hs
        ext_names = external_names(state.m)
        ext_columns = set(ext_names) | {n + "_numerator" for n in ext_names}
        required = sorted({v for a in state.m["analyses"] for v in _formula_names(str(_normalize_analysis(a).get("formula", "")))
                           if set(_formula_names(str(_normalize_analysis(a).get("formula", "")))) & ext_columns}
                          - ext_columns)
        try:
            ext_wide, ext_prov = hs.load_external(state.m["external"], str(state.geo["level"]),
                                                  [s for s in manifest_states(state.geo) if s], fetch=state.external_fetch)
            state.frame, join = hs.join_external(state.frame, ext_wide, ext_names, required=required)
            for name in ext_names:
                if name + "_numerator" in state.frame:
                    state.frame.loc[state.frame[name].isna(), name + "_numerator"] = np.nan
            state.joined_external = ext_names
            state.external_info = {"variables": state.m["external"], "sources": ext_prov, "join": join,
                             "required_acs_variables": required}
            limits = hs.join_limit(state.m["external"])
            join["missing_limit"] = limits
            over = {n: s for n, s in join["missing_share_by_variable"].items()
                    if not s <= limits.get(n, hs.JOIN_MISSING_LIMIT)}
            if over:
                state.deviations.append({"kind": "external_join_failed", "detail": (
                    "; ".join(f"{n}: {s:.1%} of {join['complete_acs_units']} units with complete ACS data have no "
                              f"value (> {limits.get(n, hs.JOIN_MISSING_LIMIT):.0%})" for n, s in over.items())
                    + ("; matched rows have unsuppressed missing outcomes. Examples: "
                       if join.get("wonder") and not any(join.get("unmatched_share_by_variable",{}).get(n,0)>limits.get(n,hs.JOIN_MISSING_LIMIT) for n in over)
                       else "; a geography-vintage mismatch is likely. Examples: ")
                    + ", ".join(join["examples_without_external"][:5]))})
        except Exception as exc:  # noqa: BLE001 - recorded as a blocking deviation, never substituted
            state.deviations.append({"kind": "external_unavailable", "detail": f"{type(exc).__name__}: {exc}"})
            state.external_info = {"variables": state.m["external"], "error": f"{type(exc).__name__}: {exc}"}


def _build_indices(state: RunState) -> None:
    # 3b'. composite indices built in the manifest (Round 75; Round 36/73 construction, weights fixed in replicates)
    state.indices_info = None
    if state.frame is not None and state.m.get("indices"):
        from .round75 import build_indices
        try:
            state.frame, state.work_reps, state.indices_info = build_indices(state.frame, state.work_reps,
                                                                              state.m["indices"])
        except Exception as exc:  # noqa: BLE001 - recorded; analyses using the index then do not run
            state.deviations.append({"kind": "analysis_frame_failed", "detail": f"indices: {type(exc).__name__}: {exc}"})


def _apply_person_years(state: RunState) -> None:
    # 3c'. expected counts scaled by external person-years (Round 75; census.wonder_reference.expected_counts rule)
    state.person_years_info = None
    if state.frame is not None and any("person_years" in d for d in state.m.get("derivations") or []):
        from .round75 import apply_person_years
        try:
            state.frame, state.work_reps, state.person_years_info = apply_person_years(
                state.frame, state.work_reps, state.m["derivations"])
        except Exception as exc:  # noqa: BLE001
            state.deviations.append({"kind": "analysis_frame_failed",
                                     "detail": f"person-years expected counts: {type(exc).__name__}: {exc}"})


def _join_context(state: RunState) -> None:
    # 3d. context covariates (Round 72), county values joined on GEOID (tracts take their county's value)
    state.context_info = None
    if state.frame is not None and state.m.get("context"):
        from ..context_sources import context_frame, join_context
        try:
            ctx, prov = context_frame(state.m["context"], state.frame, client=state.client)
            state.frame, join = join_context(state.frame, ctx)
            state.joined_context = list(ctx.columns)
            state.context_info = {"entries": state.m["context"], "provenance": prov, "join": join}
        except Exception as exc:  # noqa: BLE001 - recorded, analyses that need it do not run
            state.deviations.append({"kind": "context_join_failed", "detail": f"{type(exc).__name__}: {exc}"})


def _apply_exclusions(state: RunState) -> None:
    # 4. exclusions (before adjustments: a pre-registered exclusion can remove a unit without an
    # RPP area; the CV screen gives the same rows either way, since the RPP factor leaves CVs unchanged)
    state.exclusion_log: List[Dict[str, Any]] = []
    if state.frame is not None:
        from ..models import reliability_screen
        for ex in state.m.get("exclusions") or []:
            if ex["rule"] == "geoid_exclude":
                drop = state.frame["GEOID"].isin([str(g) for g in ex.get("geoids", [])])
                state.frame = state.frame[~drop].reset_index(drop=True)
                state.exclusion_log.append({"rule": "geoid_exclude", "rows_excluded": int(drop.sum())})
            else:
                thr = float(ex.get("threshold", 30.0))
                vars_ = [v for v in ex.get("variables") or [] if f"{v}_cv" in state.frame.columns]
                flagged = reliability_screen(state.frame, vars_, threshold=thr)
                entry = {"rule": "cv_screen", "threshold": thr, "variables": vars_,
                         "action": ex.get("action", "flag"), "rows_flagged": int(flagged["GEOID"].nunique())
                         if len(flagged) else 0}
                if entry["action"] == "exclude" and len(flagged):
                    keys = [k for k in ("GEOID", "Year") if k in flagged.columns]
                    bad = state.frame[keys].merge(flagged[keys].drop_duplicates(), how="left", indicator=True)
                    keep = (bad["_merge"] == "left_only").to_numpy()
                    entry["rows_excluded"] = int((~keep).sum())
                    state.frame = state.frame[keep].reset_index(drop=True)
                state.exclusion_log.append(entry)


def _apply_adjustments(state: RunState) -> None:
    # 4b. pre-registered adjustments (a unit still without an RPP area blocks: adjustment_failed)
    state.adjustment_log: List[Dict[str, Any]] = []
    if state.frame is not None and state.m.get("adjustments"):
        state.frame, state.work_reps, state.adjustment_log, failure = _apply_adjustment_values(state.frame, state.work_reps, state.m, state.releases)
        if failure:
            state.deviations.append({"kind": "adjustment_failed", "detail": failure})
            state.frame = None
    if state.frame is not None:  # replicate-SE coverage of the units analysed
        counts = {name: _replicate_rows(state.frame, name) for name in state.derived_on_replicates}
        state.derived_on_replicates = {k: v for k, v in counts.items() if v["rows_replicate"]}

    if state.frame is not None and state.external_info is not None:
        state.external_info["low_count_kept"] = {
            e["name"]: int((state.frame[e["name"] + "_numerator"] < 20).sum())
            for e in state.m.get("external", []) if e.get("source") == "chr" and e.get("measure") == "v037"
            and e["name"] + "_numerator" in state.frame
        }
    state.coords, state.spatial_info = None, None
    if state.frame is not None and any((_normalize_analysis(a).get("args") or {}).get("spatial_se") is not None
                                 for a in state.m["analyses"]):
        from ..spatial_hac import unit_coordinates
        state.coords, state.spatial_info = unit_coordinates(state.frame["GEOID"], state.geo["level"], max(state.releases))


def _run_analyses(state: RunState) -> None:
    # 5. analyses
    available = set(state.columns) | {str(d["name"]) for d in state.m.get("derivations") or []} | set(state.joined_external)
    available |= {n + "_numerator" for n in state.joined_external}
    available |= set(state.joined_context)
    from .round75 import GEO_GROUP_COLUMNS, index_names, with_geo_groups
    available |= set(index_names(state.m)) | (set(GEO_GROUP_COLUMNS) if state.frame is not None and "GEOID" in state.frame else set())
    state.results: Dict[str, Any] = {}
    # caller-supplied replicates of overlapping releases: refused (census_vre is refused at validation)
    rep_overlap = _replicate_overlap(state.replicates) if state.replicates is not None and not census_vre_source(state.m) else None
    state.declared_fixed = _declared_covariates_only(state.m)
    state.fixed_had_replicates: Dict[str, List[str]] = {}
    from .. import progress
    ck = _Checkpoint(state) if state.checkpoint else None
    total = len(state.m["analyses"])
    for i, a in enumerate(state.m["analyses"], 1):
        a = _normalize_analysis(a)
        aid = a["id"]
        progress.report(f"run_manifest: analysis {aid}", i, total)
        needed = set(_formula_names(a.get("formula", "")))
        for k in ("variables", "error_covariates", "groups"):
            v = a.get(k) or []
            needed |= {v} if isinstance(v, str) else set(v)
        needed |= {a[k] for k in ("variable", "variable_1", "variable_2") if a.get(k)}
        if state.frame is None or not needed <= available:
            state.deviations.append({"kind": "analysis_not_run", "analysis": aid,
                               "detail": f"unavailable variables: {sorted(needed - available)}"
                               if state.frame is not None else "no analysis frame"})
            continue
        if a.get("replicates") == "required" and state.replicates is None and a["method"] in REPLICATE_METHODS:
            state.deviations.append({"kind": "replicates_unavailable", "analysis": aid,
                               "detail": "manifest requires replicate SEs; none supplied, analysis not run"})
            continue
        if census_vre_source(state.m) and state.replicates is None and a["method"] in REPLICATE_METHODS:
            state.deviations.append({"kind": "replicates_unavailable", "analysis": aid,
                               "detail": "manifest declares Census VRE replicates; none were fetched or published "
                                         "for its variables (see replicates.unavailable), analysis not run"})
            continue
        if rep_overlap and a["method"] in REPLICATE_METHODS:
            state.deviations.append({"kind": "replicates_overlapping_releases", "analysis": aid,
                               "detail": rep_overlap + "; analysis not run"})
            continue
        if aid in state.declared_fixed and state.work_reps is not None:
            had = [v for v in state.declared_fixed[aid] if _has_replicate_rows(state.work_reps, v)]
            if had:
                state.fixed_had_replicates[aid] = had
        saved = ck.load(a) if ck is not None else None
        if saved is not None:
            state.results[aid], extra = saved
            state.deviations.extend(dict(d,analysis=aid) for d in extra)
            continue
        try:
            state.results[aid] = _run_analysis(a, with_geo_groups(state.frame, needed), state.level, state.work_reps, state.corr_method, external=state.joined_external, coords=state.coords)
            result = state.results[aid]
            extra = getattr(result,"attrs",{}).get("deviations",getattr(result,"diagnostics",{}).get("deviations",[]))
            state.deviations.extend(dict(d,analysis=aid) for d in extra)
            if ck is not None:
                ck.save(a, result, list(extra))
        except Exception as exc:
            kind = "replicates_incomplete" if isinstance(exc, IncompleteReplicatesError) else "analysis_failed"
            state.deviations.append({"kind": kind, "analysis": aid, "detail": f"{type(exc).__name__}: {exc}"})

    # 5a. the analysed data, for follow-up (exploratory) work on exactly what the models saw
    try:
        state.analysed_data = _write_analysed_data(state.out, state.frame, state.work_reps)
    except Exception as exc:  # noqa: BLE001 - a convenience copy must never cost the confirmatory run
        state.analysed_data = {"error": f"analysed data not written: {type(exc).__name__}: {exc}"}


class _Checkpoint:
    """Per-analysis checkpoints for ``run_manifest(checkpoint=True)`` (Round 70, backlog N48).

    Each completed analysis is pickled to ``<output_dir>/.checkpoint/<id>.pkl``, keyed by the manifest hash, the
    analysis spec and a hash of the exact data it saw (analysis frame and replicates). A rerun reuses a checkpoint
    only when all three match; anything else is ignored with a note. Checkpoints are local files the engine wrote
    itself: never resume from a folder you did not create. The folder is removed after a successful bundle.
    """

    def __init__(self, state: "RunState") -> None:
        import hashlib
        self.state = state
        self.folder = state.out / ".checkpoint"
        self.folder.mkdir(parents=True, exist_ok=True)
        h = hashlib.sha256()
        for df in (state.frame, state.work_reps):
            if isinstance(df, pd.DataFrame) and not df.empty:
                h.update(pd.util.hash_pandas_object(df.reset_index(drop=True), index=False).values.tobytes())
                h.update(",".join(map(str, df.columns)).encode())
        self.data_hash = h.hexdigest()
        state.checkpoint_log = {"folder": str(self.folder), "reused": [], "ignored": [], "saved": []}

    def _key(self, a: Dict[str, Any]) -> str:
        import hashlib
        spec = json.dumps(a, sort_keys=True, default=str)
        return hashlib.sha256(f"{self.state.h}|{self.data_hash}|{spec}".encode()).hexdigest()

    def load(self, a: Dict[str, Any]):
        import pickle
        path = self.folder / f"{a['id']}.pkl"
        if not path.exists():
            return None
        try:
            with open(path, "rb") as fh:
                saved = pickle.load(fh)
        except Exception as exc:  # noqa: BLE001 - an unreadable checkpoint is ignored, never fatal
            self.state.checkpoint_log["ignored"].append({"analysis": a["id"], "reason": f"unreadable: {type(exc).__name__}"})
            return None
        if saved.get("key") != self._key(a):
            self.state.checkpoint_log["ignored"].append({"analysis": a["id"],
                                                         "reason": "manifest, analysis or data changed"})
            return None
        self.state.checkpoint_log["reused"].append(a["id"])
        return saved["result"], saved["deviations"]

    def save(self, a: Dict[str, Any], result: Any, deviations: List[Dict[str, Any]]) -> None:
        import pickle
        try:
            tmp = self.folder / f"{a['id']}.pkl.tmp"
            with open(tmp, "wb") as fh:
                pickle.dump({"key": self._key(a), "result": result, "deviations": deviations}, fh)
            tmp.replace(self.folder / f"{a['id']}.pkl")
            self.state.checkpoint_log["saved"].append(a["id"])
        except Exception as exc:  # noqa: BLE001 - a checkpoint must never cost the run
            self.state.checkpoint_log["ignored"].append({"analysis": a["id"], "reason": f"not saved: {type(exc).__name__}"})


def _test_hypotheses(state: RunState) -> None:
    from ..multitest import adjust_pvalues
    # 6. hypotheses with the pre-registered correction
    rows = []
    for hyp in state.m["hypotheses"]:
        row = {"id": hyp["id"], "analysis": hyp["analysis"], "statistic": hyp["statistic"],
               "direction": hyp.get("direction", "two-sided"), "family": hyp.get("family", "primary"),
               "statement": hyp.get("statement", "")}
        res = state.results.get(hyp["analysis"])
        if res is None:
            row.update(status="not_tested", estimate=None, p_value=None)
            state.deviations.append({"kind": "hypothesis_not_tested", "hypothesis": hyp["id"],
                               "detail": f"analysis {hyp['analysis']} did not run"})
        else:
            try:
                s = _statistic(hyp, res)
                refusal = s.pop("confirmatory_refusal", None)
                if refusal and not state.m.get("exploratory", False):
                    raise ValueError(refusal)
                row.update(s, status="tested",
                           p_value=s["p_two_sided"] if hyp["statistic"] in ("joint_wald", "joint_test") else _one_sided(s["p_two_sided"], s.get("test_estimate", s["estimate"]), row["direction"]))
            except Exception as exc:
                row.update(status="not_tested", estimate=None, p_value=None)
                state.deviations.append({"kind": "hypothesis_not_tested", "hypothesis": hyp["id"], "detail": str(exc)})
        spec = next(_normalize_analysis(a) for a in state.m["analyses"] if a["id"] == hyp["analysis"])
        if hyp["statistic"] == "coefficient" and spec["method"] == "fit_replicate" and (spec.get("args") or {}).get("model") == "binomial":
            for source_key, target in (("estimate", "odds_ratio"), ("ci_lower", "odds_ratio_lower"),
                                   ("ci_upper", "odds_ratio_upper")):
                row[target] = float(np.exp(row[source_key])) if row.get(source_key) is not None else None
        if hyp["statistic"] in ("log_rii", "log_smr"):
            for source_key, target in (("estimate", "ratio"), ("ci_lower", "ratio_lower"), ("ci_upper", "ratio_upper")):
                row[target] = float(np.exp(row[source_key])) if row.get(source_key) is not None else None
        rows.append(row)
    state.hyp_df = pd.DataFrame(rows)
    state.hyp_df["p_adjusted"] = np.nan
    groups = [state.hyp_df.index] if state.corr.get("family", "all") == "all" else \
        [g.index for _, g in state.hyp_df.groupby("family")]
    for idx in groups:
        p = pd.to_numeric(state.hyp_df.loc[idx, "p_value"], errors="coerce")
        state.hyp_df.loc[idx, "p_adjusted"] = np.asarray(adjust_pvalues(p.to_numpy(float), state.corr_method))
    state.hyp_df["significant"] = state.hyp_df["p_adjusted"] < (1 - state.level)
    state.hyp_df["manifest_hash"] = state.h


def _bundle(state: RunState) -> Dict[str, Any]:
    from ..report_tables import data_citation
    # 7. bundle
    complete = not any(d["kind"] in BLOCKING_DEVIATIONS for d in state.deviations)
    status = (STATUS_EXPLORATORY if state.m.get("exploratory", False) else
              STATUS_CONFIRMATORY if complete else STATUS_CONFIRMATORY_INCOMPLETE)
    if state.m.get("exploratory"):
        state.hyp_df["analysis_status"] = status
    rep_info = None
    if state.vre_info is not None:
        rep_info = dict(state.vre_info)
        if state.replicates is not None:
            digest, reason = replicates_digest(state.replicates)
            rep_info.update(rows=int(len(state.replicates)), sha256=digest)
            if digest is None:
                rep_info["sha256_unavailable"] = reason
        if state.derived_on_replicates:
            rep_info["derived_on_replicates"] = list(state.derived_on_replicates)
            rep_info["derived_on_replicates_rows"] = state.derived_on_replicates
        scaled = [v for a in state.adjustment_log for v in a["variables"]]
        if scaled and state.replicates is not None:
            rep_info["scaled_by_adjustments"] = scaled
    elif state.replicates is not None:
        if state.replicates_synthetic is None:
            attrs = getattr(state.replicates, "attrs", {}) or {}
            state.replicates_synthetic = bool(attrs.get("synthetic", state.source["synthetic"]))
        digest, reason = replicates_digest(state.replicates)
        rep_info = {"source": "caller_supplied", "synthetic": bool(state.replicates_synthetic),
                    "rows": int(len(state.replicates)), "sha256": digest}
        if digest is None:
            rep_info["sha256_unavailable"] = reason
        if state.derived_on_replicates:
            rep_info["derived_on_replicates"] = list(state.derived_on_replicates)
            rep_info["derived_on_replicates_rows"] = state.derived_on_replicates
        scaled = [v for a in state.adjustment_log for v in a["variables"]]
        if scaled:
            rep_info["scaled_by_adjustments"] = scaled
    if rep_info is not None and state.declared_fixed:
        rep_info["declared_covariates_only"] = state.declared_fixed
        if state.fixed_had_replicates:
            # the hashed declaration governs: the outcome stays fixed although replicates were available
            rep_info["covariates_only_outcome_had_replicates"] = state.fixed_had_replicates
            rep_info.setdefault("notes", []).extend(
                f"analysis {aid}: replicate_scope 'covariates_only' was declared and the outcome {names} was held "
                "at its estimate in every refit as pre-registered, although replicates were available for it in "
                "this run; se_sampling excludes the outcome's sampling error"
                for aid, names in state.fixed_had_replicates.items())
    tagged = {aid: _tag(r, state.h, aid, status) for aid, r in state.results.items()}
    run_info = {"manifest_hash": state.h, "analysis_status": status, "deviations": state.deviations,
                "exclusions": state.exclusion_log, "extraction": state.extraction, "n_units": None if state.frame is None
                else int(len(state.frame)), "title": state.m.get("title"), "data_source": state.source, "replicates": rep_info}
    from ..epi_reporting import analysis_outcomes, design_labels, manifest_measure_types  # Round 82
    _types = manifest_measure_types(state.m)
    run_info["design"] = design_labels(state.m.get("geography", {}).get("level"))
    run_info["measure_types"] = {o: _types.get(o, "unspecified") for o in analysis_outcomes(state.m)}
    if state.spatial_info is not None:
        run_info["spatial_coordinates"] = state.spatial_info
    if state.m.get("adjustments"):
        run_info["adjustments"] = state.adjustment_log
    if state.harmonization is not None:
        run_info["harmonization"] = state.harmonization
    if state.external_info is not None:
        run_info["external"] = state.external_info
    if getattr(state, "context_info", None) is not None:
        run_info["context"] = state.context_info
    if getattr(state, "indices_info", None) is not None:
        run_info["indices"] = state.indices_info
    if getattr(state, "person_years_info", None) is not None:
        run_info["person_years"] = state.person_years_info
    if state.analysed_data:
        run_info["analysed_data"] = state.analysed_data
    if not complete:
        run_info["status_note"] = INCOMPLETE_STATUS_TEXT
    tables_used = sorted(tables_and_refs(state.m))
    citation = data_citation(state.releases, tables_used, synthetic=state.source["synthetic"],
                             description=state.source.get("description"))
    if state.external_info and state.external_info.get("sources"):
        citation = citation + " External data: " + " ".join(p["citation"] for p in state.external_info["sources"])
    if state.frame is not None:
        from ..wonder_outputs import policy_from_frame
        policy = policy_from_frame(state.frame,state.m)
        if policy:run_info["wonder_output_policy"] = policy
    bundle = _write_bundle(state.out / "bundle", state.m, state.h, tagged, state.hyp_df, run_info, citation)
    out_res = {"success": complete, "analysis_status": status, "data_source": state.source, "replicates": rep_info,
               "manifest_hash": state.h, "deviations": state.deviations, "hypotheses": state.hyp_df, "results": tagged,
               "frame": state.frame, "bundle": bundle, "output_dir": str(state.out), "errors": []}
    if run_info.get("wonder_output_policy"):
        from ..wonder_outputs import sanitize_frame
        out_res["frame"] = sanitize_frame(state.frame,run_info["wonder_output_policy"])
    if state.m.get("adjustments"):
        out_res["adjustments"] = state.adjustment_log
    if state.external_info is not None:
        out_res["external"] = state.external_info
    return out_res


_STAGES = (
    _extract,
    _build_frame,
    _fetch_vre,
    _derive_replicates,
    _build_indices,
    _join_external,
    _apply_person_years,
    _join_context,
    _apply_exclusions,
    _apply_adjustments,
    _run_analyses,
    _test_hypotheses,
)


@integrity_errors
def run_manifest(
    manifest: Union[str, Path, Mapping[str, Any]], output_dir: Union[str, Path], client: Any = None,
    replicates: Any = None, use_cache: bool = True, replicates_synthetic: Optional[bool] = None,
    external_fetch: Optional[Callable[[str], bytes]] = None, checkpoint: bool = False,
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
    ``checkpoint=True`` (Round 70) saves each completed analysis under ``<output_dir>/.checkpoint`` and, on a rerun
    with the same manifest and data, reuses them (see :class:`_Checkpoint`); the folder is removed after a
    successful bundle. Results are identical with or without it.
    """
    state = _prepare(manifest, output_dir, client, replicates, use_cache,
                     replicates_synthetic, external_fetch)
    if not isinstance(state, RunState):
        return state
    state.checkpoint = bool(checkpoint)
    for stage in _STAGES:
        stage(state)
    out = _bundle(state)
    if state.checkpoint:
        out["checkpoint"] = state.checkpoint_log
        failed = any(d.get("kind") in ("analysis_failed", "replicates_incomplete") for d in state.deviations)
        if out.get("bundle") is not None and not failed:   # keep them when an analysis failed: a rerun reuses the rest
            import shutil
            shutil.rmtree(state.out / ".checkpoint", ignore_errors=True)
            out["checkpoint"]["removed"] = True
    return out


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
        if name == "analysis_frame":
            from ..wonder_outputs import policy_from_frame,sanitize_frame
            policy = policy_from_frame(df)
            if policy:
                data = sanitize_frame(data,policy,parquet=True)
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
    cols += [c for c in ("df", "null_value", "geoid", "release", "compare_geoid", "compare_release", "odds_ratio", "odds_ratio_lower", "odds_ratio_upper", "ratio", "ratio_lower", "ratio_upper") if c in hyp_df]
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
    wonder_policy = run_info.get("wonder_output_policy")
    provenance = {"manifest_hash": h, "analysis_status": run_info["analysis_status"],
                  "deviations": len(run_info["deviations"]), "data_source": run_info.get("data_source"),
                  "replicates": run_info.get("replicates")}
    if "adjustments" in run_info:  # RPP provenance: years, areas, table hash
        provenance["adjustments"] = [{k: a[k] for k in ("type", "variables", "areas", "dollar_year", "rpp_year",
                                                        "rpp_year_source", "rpp_areas", "boundary_source",
                                                        "rpp_table", "rpp_years", "price_index", "order",
                                                        "releases") if k in a}
                                     for a in run_info["adjustments"]]
    from .methods_text import manifest_bibtex
    bib_text = manifest_bibtex(m, run_info, only_if_registry=True)
    extra_kw = {}
    if wonder_policy:
        extra_kw["wonder_policy"] = wonder_policy
    if bib_text:
        extra_kw["references"] = {"references.bib": bib_text}
    return results_bundle(folder, tables=tables, figures=figures_, methods=methods_section(m, run_info),
                          results=payload, provenance=provenance, citation=citation, **extra_kw)
