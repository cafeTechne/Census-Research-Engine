# SPDX-License-Identifier: AGPL-3.0-or-later
"""Manifest replicates definitions."""

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union
import numpy as np
import pandas as pd
from .schema import (
    REPLICATES_KEYS,
    REPLICATE_SOURCES,
    YEAR_CODE_RE,
    _derivation_refs,
    _formula_names,
    _normalize_analysis,
    _table_of,
    _variable_tables,
    manifest_releases,
    manifest_states,
    release_overlap_message,
)



def _vre_level(level: Any) -> str:
    """A manifest geography level as census.replicate names it (``block group`` -> ``block_group``)."""
    from ..pipeline import normalize_geo_level
    return normalize_geo_level(str(level)).replace(" ", "_")


def census_vre_source(manifest: Mapping[str, Any]) -> bool:
    """True when the manifest declares ``"replicates": {"source": "census_vre"}``."""
    reps = manifest.get("replicates")
    return isinstance(reps, Mapping) and reps.get("source") == "census_vre"


def _check_replicates(manifest: Mapping[str, Any], errors: List[str]) -> None:
    """``replicates`` (optional): ``{"source": "census_vre"}`` makes run_manifest fetch the Census
    VRE files for the manifest's tables, geography and releases (census.replicate and its cache)."""
    reps = manifest.get("replicates")
    if reps is None:
        return
    if not isinstance(reps, Mapping):
        errors.append("replicates must be an object, e.g. {\"source\": \"census_vre\"}")
        return
    for k in sorted(set(reps) - set(REPLICATES_KEYS)):
        errors.append(f"replicates: unknown key {k!r}; allowed {REPLICATES_KEYS}")
    if reps.get("source") not in REPLICATE_SOURCES:
        errors.append(f"replicates.source must be one of {REPLICATE_SOURCES}")
        return
    from .. import replicate as vre
    geo = manifest.get("geography") if isinstance(manifest.get("geography"), Mapping) else {}
    try:
        sumlev = vre.sumlev_for(_vre_level(geo.get("level", "")))
    except Exception as exc:  # noqa: BLE001 - unsupported level for VRE files
        errors.append(f"replicates.source census_vre: {exc}")
        sumlev = None
    if sumlev in vre.PER_STATE_SUMLEVS and not geo.get("state") and not geo.get("states"):
        errors.append(f"replicates.source census_vre at level {geo.get('level')!r}: Census VRE files of summary "
                      f"level {sumlev} are published per state; give geography.state or geography.states")
    releases = manifest_releases(manifest)
    bad = [r for r in releases if r not in vre.VRE_LAYOUTS]
    if bad:
        errors.append(f"replicates.source census_vre: no Census VRE release for {bad} (5-year releases "
                      f"{vre.FIRST_VRE_YEAR}-{vre.LAST_KNOWN_VRE_YEAR})")
    if manifest.get("aggregation") is not None:
        errors.append("replicates.source census_vre cannot be combined with aggregation (VRE replicates are "
                      "per GEOID and are not aggregated by run_manifest)")
    overlap = release_overlap_message(releases, "replicates.source census_vre")
    if overlap:
        errors.append(overlap)


def vre_unavailable(manifest: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Variables and derivations without published Census VRE replicates for some release
    (offline, from the census.replicate registry): [{"variable", "table", "release", "reason"}]."""
    from .. import replicate as vre
    level = _vre_level((manifest.get("geography") or {}).get("level", ""))
    out = []
    releases = manifest_releases(manifest)
    for name, tables in _variable_tables(manifest).items():
        for table in tables:
            for year in releases:
                info = vre.vre_availability(table, year, level)
                if not info["available"]:
                    out.append({"variable": name, "table": table, "release": year, "reason": info["reason"]})
    return out


def _declared_covariates_only(manifest: Mapping[str, Any]) -> Dict[str, List[str]]:
    """{analysis id: outcome names} of analyses declaring ``replicate_scope: "covariates_only"``."""
    out: Dict[str, List[str]] = {}
    for a in manifest.get("analyses") or []:
        if not isinstance(a, Mapping):
            continue
        a = _normalize_analysis(a)
        if a.get("replicate_scope") == "covariates_only" and "~" in str(a.get("formula", "")):
            out[str(a.get("id"))] = _formula_names(str(a["formula"]).split("~")[0])
    return out


def _replicate_overlap(replicates: Any) -> Optional[str]:
    """Why caller-supplied replicates cannot be used (their releases' 5-year periods overlap), or None."""
    if isinstance(replicates, Mapping):  # {release: frame}
        years = [int(y) for y in replicates if str(y).isdigit()]
    elif isinstance(replicates, pd.DataFrame) and "Year" in replicates.columns:
        years = sorted({int(y) for y in pd.to_numeric(replicates["Year"], errors="coerce").dropna()})
    else:
        return None
    return release_overlap_message(years, "caller-supplied replicates")


def _has_replicate_rows(replicates: Any, name: str) -> bool:
    """True when the replicate long frame has rows for manifest variable ``name``."""
    try:
        return bool((replicates["variable"].astype(str) == str(name)).any())
    except Exception:  # noqa: BLE001 - malformed replicates are reported by the analysis itself
        return False


def _replicate_rows(frame: pd.DataFrame, name: str) -> Dict[str, int]:
    """{"rows_replicate": rows whose ``name`` SE is a replicate SE, "rows": all rows}."""
    col = frame.get(f"{name}_method")
    k = 0 if col is None else int((col.astype(str) == "replicate").sum())
    return {"rows_replicate": k, "rows": int(len(frame))}


def _derive_replicates(frame: pd.DataFrame, replicates: Any,
                       m: Mapping[str, Any]) -> Tuple[pd.DataFrame, Any, Dict[str, Dict[str, int]]]:
    """Evaluate manifest derivations missing from the supplied replicate frame on the
    replicates of their inputs (:func:`census.analysis.attach_replicates`, the same
    evaluation as build_analysis_frame). Inputs are found by manifest variable name or
    by ACS code (``B15002_015``). The derived variables' SEs become exact replicate SEs;
    other variables keep theirs. Derivations whose inputs lack replicates are left
    out (a replicate analysis using them then stops as replicates_incomplete).
    Returns (frame, replicates, {derivation: _replicate_rows counts}) listing only
    derivations that received a replicate SE for at least one row. Raises on
    malformed replicates (run_manifest records that as a deviation)."""
    from ..analysis import _default_name, attach_replicates
    reps = replicates if isinstance(replicates, pd.DataFrame) else pd.DataFrame(replicates)
    if "variable" not in reps.columns:
        return frame, replicates, {}
    have = {_default_name(v) for v in reps["variable"].astype(str)}

    refs_of = _derivation_refs

    var_map: Dict[str, str] = {}  # manifest name -> replicate variable
    for v in m.get("variables") or []:
        name, mm = str(v["name"]), YEAR_CODE_RE.match(str(v.get("ref", "")))
        if name in have:
            var_map[name] = name
        elif mm and _default_name(mm.group(2)) in have:  # B19013_001E, DP04_0046PE as normalized
            var_map[name] = _default_name(mm.group(2))
    todo: List[Dict[str, Any]] = []
    for d in m.get("derivations") or []:
        name, refs = str(d["name"]), refs_of(d)
        if name in have:
            var_map[name] = name
        elif refs and all(r in var_map or r in {str(t["name"]) for t in todo} for r in refs):
            todo.append(dict(d))
    if not todo:
        return frame, replicates, {}
    new_frame, long = attach_replicates(frame, reps, variables=var_map, derive=todo, replace_se=True)
    counts = {str(d["name"]): _replicate_rows(new_frame, str(d["name"])) for d in todo}
    derived = [name for name, c in counts.items() if c["rows_replicate"]]
    if not derived:
        return frame, replicates, {}
    out = frame.copy()
    for name in derived:  # only the derived variables take replicate SEs
        for suffix in ("_se", "_cv", "_method"):
            if f"{name}{suffix}" in new_frame.columns:
                out[f"{name}{suffix}"] = new_frame[f"{name}{suffix}"].to_numpy()
    # derived rows, and rows of inputs found by ACS code renamed to their manifest name
    added = long[long["variable"].isin(derived + [n for n, c in var_map.items() if c != n])]
    combined = pd.concat([reps, added], ignore_index=True)
    combined.attrs = dict(getattr(reps, "attrs", {}) or {})
    return out, combined, {name: counts[name] for name in derived}


def _census_vre_replicates(m: Mapping[str, Any], frame: pd.DataFrame, codes_by_year: Mapping[str, Mapping[int, str]],
                           client: Any = None, crosswalk_by_name: Optional[Mapping[str, pd.DataFrame]] = None,
                           ) -> Tuple[Optional[pd.DataFrame], Dict[str, Any]]:
    """Fetch the Census VRE files for the manifest's variables, geography and releases with
    :func:`census.replicate.fetch_vre` (and its cache) and return (replicate long frame, record).

    The long frame has GEOID, Year, variable (the manifest variable name), estimate and the 80
    replicates, for the analysis frame's units only. The record lists every file (URL, SHA-256 of
    the file as downloaded, release, summary level, published-MOE self-check) and every variable
    without published replicates (``unavailable``: table not on the release's VRE list, or the
    line missing from the file). Raises when a published file cannot be fetched.

    With ``geography.harmonize_tracts_to`` the replicate rows of releases on the other tract
    vintage are apportioned with the estimates' crosswalk (``crosswalk_by_name``) before they
    are matched to the analysis units (census.tract_harmonization.apportion_replicates)."""
    from .. import replicate as vre
    from ..analysis import REPLICATE_COLUMNS
    from ..pipeline import expand_states
    geo = m["geography"]
    level = _vre_level(geo["level"])
    sumlev = vre.sumlev_for(level)
    states: List[Optional[str]] = []
    for st in manifest_states(geo):
        states += list(expand_states(st)) if st else []
    calls: List[Optional[str]] = sorted(set(states)) if sumlev in vre.PER_STATE_SUMLEVS else [None]
    if not calls:  # per-state files and no state: nothing could be fetched (validation requires a state)
        raise ValueError(f"Census VRE files of summary level {sumlev} ({geo['level']}) are published per state, "
                         "and the manifest geography names no state (geography.state or geography.states), so "
                         "no VRE file could be requested")
    units = frame[["GEOID", "Year"]].astype({"GEOID": str, "Year": "int64"})
    releases = [int(r) for r in m["releases"]]
    apportioned: List[int] = []
    if geo.get("harmonize_tracts_to") is not None:
        from .. import tract_harmonization as th
        apportioned = th.releases_to_apportion(releases, int(geo["harmonize_tracts_to"]))
    names_by_table: Dict[str, List[str]] = {}
    for v in m["variables"]:
        names_by_table.setdefault(str(_table_of(v)), []).append(str(v["name"]))
    files: List[Dict[str, Any]] = []
    unavailable: List[Dict[str, Any]] = []
    parts: List[pd.DataFrame] = []
    covered: Dict[str, List[int]] = {}
    for table, names in names_by_table.items():
        for year in releases:
            info = vre.vre_availability(table, year, level)
            if not info["available"]:
                unavailable += [{"variable": n, "table": table, "release": year, "reason": info["reason"]}
                                for n in names]
                continue
            want = set(units.loc[units["Year"] == year, "GEOID"])
            frames = []
            for st in calls:
                f = vre.fetch_vre(table, year, level, state_code=st, client=client)
                files.append({"table": table, "release": year, "summary_level": f.attrs.get("summary_level"),
                              "state_code": f.attrs.get("state_code"), "url": f.attrs.get("source_url"),
                              "sha256": f.attrs.get("sha256"), "moe_check": f.attrs.get("moe_check")})
                if f.attrs.get("substitution"):  # B01003 total read from B01001 (census.replicate.fetch_vre)
                    files[-1]["substitution"] = f.attrs["substitution"]
                # apportioned releases: keep every source tract; matched to the units after apportionment
                frames.append(f if year in apportioned else f[f["GEOID"].astype(str).isin(want)])
            rows = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
            for n in names:
                code = (codes_by_year.get(n) or {}).get(year)
                sub = rows[rows["variable"] == code] if code is not None and len(rows) else rows.iloc[0:0]
                if sub.empty:
                    unavailable.append({"variable": n, "table": table, "release": year,
                                        "reason": f"{code or 'no code'} has no rows in the {table} VRE file for "
                                                  "the analysed units"})
                    continue
                part = sub[["GEOID", "estimate"] + REPLICATE_COLUMNS].copy()
                if year in apportioned:
                    cw = (crosswalk_by_name or {}).get(n)
                    if cw is None:  # e.g. the variable is missing from the extraction
                        unavailable.append({"variable": n, "table": table, "release": year,
                                            "reason": "no tract crosswalk for this variable (not in the harmonized "
                                                      "frame)"})
                        continue
                    part = th.apportion_replicates(part, code, cw, int(geo["harmonize_tracts_to"]))
                    part = part[part["GEOID"].astype(str).isin(want)]
                part.insert(1, "Year", int(year))
                part.insert(2, "variable", n)
                parts.append(part)
                covered.setdefault(n, []).append(int(year))
    reps = pd.concat(parts, ignore_index=True) if parts else None
    if reps is not None:
        reps.attrs["synthetic"] = False
    record = {"source": "census_vre", "synthetic": False, "files": files, "variables": covered,
              "unavailable": unavailable, "documentation": vre.VRE_DOCUMENTATION}
    if apportioned and reps is not None:
        record["apportioned_releases"] = apportioned
        record["apportioned_estimate_check"] = th.replicate_estimate_check(frame, reps, list(covered), apportioned)
    return reps, record


def _canonical_column(col: pd.Series) -> List[str]:
    """String form of one column: numbers (int or float, not numeric strings) as repr(float)
    (shortest round-trip text, identical across pandas/numpy versions; 3 and 3.0 alike),
    NaN/None as "", everything else str(); identical across pandas/numpy versions."""
    out: List[str] = []
    numeric = pd.api.types.is_numeric_dtype(col.dtype) and not pd.api.types.is_bool_dtype(col.dtype)
    for v in col.tolist():
        if v is None or (isinstance(v, float) and math.isnan(v)) or v is pd.NA or v is pd.NaT:
            out.append("")
        elif numeric or (isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, (bool, np.bool_))):
            f = float(v)
            out.append("" if math.isnan(f) else repr(f))
        else:
            out.append(str(v))
    return out


def replicates_digest(replicates: Any) -> Tuple[Optional[str], Optional[str]]:
    """(sha256, None) of the canonical CSV of a replicate frame, or (None, reason). Never raises.

    Canonical form (JSON lines): column labels as strings (a collision after str() is an
    error), columns sorted by label, every value as a string (numbers as
    ``repr(float(x))`` so 3 and 3.0 hash alike; missing as ""), rows sorted
    by those strings (stable), no index, UTF-8, LF line endings.
    """
    try:
        df = replicates if isinstance(replicates, pd.DataFrame) else pd.DataFrame(replicates)
        labels = [str(c) for c in df.columns]
        dups = sorted({x for x in labels if labels.count(x) > 1})
        if dups:
            return None, f"column labels collide as strings: {dups}"
        cols = {lab: _canonical_column(df.iloc[:, i]) for i, lab in enumerate(labels)}
        order = sorted(labels)
        rows = sorted(zip(*(cols[c] for c in order))) if order else []
        lines = [json.dumps(order, ensure_ascii=False)] + [json.dumps(list(r), ensure_ascii=False) for r in rows]
        return hashlib.sha256(("\n".join(lines) + "\n").encode("utf-8")).hexdigest(), None
    except Exception as exc:  # noqa: BLE001 - provenance hashing must never stop a run
        return None, f"{type(exc).__name__}: {exc}"


def read_replicates(path: Union[str, Path]) -> pd.DataFrame:
    """Read a replicate long frame (CSV or Parquet) with GEOID as text and floats
    parsed exactly (round-trip) on every pandas version, so the same file gives the
    same values and :func:`replicates_sha256` everywhere."""
    path = str(path)
    if path.lower().endswith(".parquet"):
        return pd.read_parquet(path)
    kw: Dict[str, Any] = {"dtype": {"GEOID": str}}
    if int(pd.__version__.split(".")[0]) < 3:  # pandas 3 parses round-trip by default (option deprecated)
        kw["float_precision"] = "round_trip"
    return pd.read_csv(path, **kw)


def replicates_sha256(replicates: Any) -> Optional[str]:
    """SHA-256 of a replicate frame's canonical form (:func:`replicates_digest`); None if unavailable."""
    return replicates_digest(replicates)[0]
