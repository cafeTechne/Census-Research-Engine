# SPDX-License-Identifier: AGPL-3.0-or-later
"""Manifest adjustments definitions."""

import json
from typing import Any, Dict, List, Mapping, Optional, Tuple
import numpy as np
import pandas as pd
from .schema import (
    ADJUSTMENT_TYPES,
    RPP_ADJUSTMENT_KEYS,
    _STATE_PREFIXED_LEVELS,
    _is_int,
    manifest_releases,
)



def default_rpp_areas(level: Optional[str]) -> str:
    """Default RPP ``areas`` of an adjustment for a (normalized) geography level: the
    county's metro/nonmetro area for counties, else the state (validation and runs)."""
    return "county_metro" if level == "county" else "state"


def latest_rpp_year() -> Optional[int]:
    """Latest year in the active RPP table (filled in by create_manifest when ``rpp_year`` is omitted), or None."""
    from .. import rpp
    years = rpp._years()
    return years[-1] if years else None


def _check_adjustments(manifest: Mapping[str, Any], names: List[str], errors: List[str]) -> None:
    adjustments = manifest.get("adjustments")
    if adjustments is None:
        return
    if not isinstance(adjustments, list):
        errors.append("adjustments must be a list of adjustment steps")
        return
    from ..pipeline import normalize_geo_level
    geo = manifest.get("geography") or {}
    try:
        level = normalize_geo_level(geo.get("level", ""))
    except Exception:  # noqa: BLE001 - geography errors are reported by _check_geography
        level = geo.get("level")
    releases = manifest_releases(manifest)
    if adjustments and manifest.get("aggregation") is not None:
        errors.append("adjustments cannot be combined with aggregation (RPP areas are assigned per GEOID)")
    adjusted: List[str] = []
    for i, adj in enumerate(adjustments):
        if not isinstance(adj, Mapping):
            errors.append(f"adjustments[{i}] must be an object")
            continue
        if adj.get("type") not in ADJUSTMENT_TYPES:
            errors.append(f"adjustments[{i}]: type must be one of {ADJUSTMENT_TYPES}")
            continue
        for k in sorted(set(adj) - set(RPP_ADJUSTMENT_KEYS)):
            errors.append(f"adjustments[{i}]: unknown key {k!r}; allowed {RPP_ADJUSTMENT_KEYS}")
        vars_ = adj.get("variables")
        if not isinstance(vars_, list) or not vars_:
            errors.append(f"adjustments[{i}]: variables must be a non-empty list of manifest variable names")
            vars_ = []
        for v in vars_:
            if str(v) not in names:
                errors.append(f"adjustments[{i}]: unknown variable {v!r}")
            elif str(v) in adjusted:
                errors.append(f"adjustments[{i}]: {v!r} is adjusted twice")
            adjusted.append(str(v))
        areas = adj.get("areas", default_rpp_areas(level))
        if areas not in ("county_metro", "state"):
            errors.append(f"adjustments[{i}]: areas must be 'county_metro' or 'state'")
        elif areas == "county_metro" and level not in ("county", "tract"):
            errors.append(f"adjustments[{i}]: areas 'county_metro' needs geography level 'county' or 'tract' "
                          "(a tract takes its county's RPP area)")
        elif areas == "state" and level not in _STATE_PREFIXED_LEVELS:
            errors.append(f"adjustments[{i}]: areas 'state' needs a state-based geography level "
                          f"{_STATE_PREFIXED_LEVELS}")
        try:
            from .. import rpp
            years = rpp._years()
        except Exception as exc:  # noqa: BLE001 - e.g. a bundled-data integrity failure
            errors.append(f"adjustments[{i}]: RPP table unreadable ({type(exc).__name__}: {exc})")
            continue
        if not years:
            errors.append(f"adjustments[{i}]: no RPP data available")
            continue
        _check_dollar_year(adj, i, releases, errors)
        if len(releases) > 1 or "rpp_years" in adj:
            _check_rpp_years(adj, i, releases, years, errors)
            continue
        year = adj.get("rpp_year")
        if year is None:
            errors.append(f"adjustments[{i}]: rpp_year is required (it fixes the price level in the "
                          f"pre-registration); the latest year in the RPP table is {years[-1]}. "
                          "create_manifest fills it in when omitted")
        elif not _is_int(year) or year not in years:
            errors.append(f"adjustments[{i}]: rpp_year must be an integer year in the RPP table "
                          f"({years[0]}-{years[-1]})")


def _check_rpp_years(adj: Mapping[str, Any], i: int, releases: List[int], years: List[int],
                     errors: List[str]) -> None:
    """``rpp_years`` ({release: RPP year}, one entry per release) replaces ``rpp_year`` when a
    manifest has several releases (each release's dollars get their own year's RPP, D15-2)."""
    if "rpp_year" in adj:
        errors.append(f"adjustments[{i}]: give rpp_years (one RPP year per release), not rpp_year, "
                      "when the manifest has several releases" if len(releases) > 1
                      else f"adjustments[{i}]: give either rpp_year or rpp_years, not both")
        return
    ry = adj.get("rpp_years")
    if ry is None:
        errors.append(f"adjustments[{i}]: rpp_years is required with several releases, e.g. "
                      + json.dumps({str(r): r for r in releases})
                      + " (each release's own year, D15-2; it fixes the price levels in the pre-registration). "
                      "create_manifest fills it in when omitted")
        return
    if not isinstance(ry, Mapping) or sorted(str(k) for k in ry) != sorted(str(r) for r in releases):
        errors.append(f"adjustments[{i}]: rpp_years must map every release (as a string key) to an RPP year, "
                      "e.g. " + json.dumps({str(r): r for r in releases}))
        return
    for k, v in ry.items():
        if not _is_int(v) or v not in years:
            errors.append(f"adjustments[{i}]: rpp_years[{k!r}] must be an integer year in the RPP table "
                          f"({years[0]}-{years[-1]})")


def _check_dollar_year(adj: Mapping[str, Any], i: int, releases: List[int], errors: List[str]) -> None:
    """``dollar_year`` + ``price_index``: every release's dollars are converted to the dollar year
    with the price index (CPI first, then the RPP; D15-2). Required with several releases."""
    from ..inflation import PRICE_INDEXES, load_price_index
    dy, index = adj.get("dollar_year"), adj.get("price_index")
    if dy is None:
        if len(releases) > 1:
            errors.append(f"adjustments[{i}]: dollar_year is required with several releases (dollars of "
                          f"different years are converted to one year with the price index before the RPP); "
                          "create_manifest fills in the latest release")
        if index is not None:
            errors.append(f"adjustments[{i}]: price_index needs dollar_year")
        return
    if not _is_int(dy):
        errors.append(f"adjustments[{i}]: dollar_year must be an integer year")
        return
    if index is None:
        errors.append(f"adjustments[{i}]: price_index is required with dollar_year (one of {PRICE_INDEXES}; "
                      "create_manifest fills in the default r-cpi-u-rs)")
        return
    if index not in PRICE_INDEXES:
        errors.append(f"adjustments[{i}]: price_index must be one of {PRICE_INDEXES}")
        return
    try:
        table = load_price_index(index)
    except Exception as exc:  # noqa: BLE001 - e.g. a bundled-data integrity failure
        errors.append(f"adjustments[{i}]: price index table unreadable ({type(exc).__name__}: {exc})")
        return
    missing = sorted({int(dy), *releases} - set(table))
    if missing:
        errors.append(f"adjustments[{i}]: no complete {index} value for {missing} (available "
                      f"{min(table) if table else '-'}-{max(table) if table else '-'})")


_FILL_REASONS = {
    "rpp_year": "the latest year in the RPP table",
    "dollar_year": "the latest release",
    "price_index": "the default index (R-CPI-U-RS, the index the Census Bureau uses for ACS dollars)",
    "rpp_years": "each release's own year (D15-2)",
}


def _fill_adjustment_defaults(manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fill omitted required adjustment fields (in place) so the hash fixes them; returns
    one ``{"adjustment": i, <field>: value}`` entry per filled field.

    One release: ``rpp_year`` (the latest RPP year; Round 14). Several releases (or a declared
    ``dollar_year``): ``dollar_year`` (the latest release), ``price_index`` (R-CPI-U-RS) and
    ``rpp_years`` (each release's own year, when the RPP table has it; otherwise left out and
    validation asks for it)."""
    filled: List[Dict[str, Any]] = []
    adjustments = manifest.get("adjustments")
    if not isinstance(adjustments, list):
        return filled
    releases = manifest_releases(manifest)
    multi = len(releases) > 1
    try:
        from .. import rpp
        rpp_years, latest = rpp._years(), latest_rpp_year()
    except Exception:  # noqa: BLE001 - an unreadable RPP table is reported by validation
        rpp_years = latest = None
    for i, adj in enumerate(adjustments):
        if not (isinstance(adj, dict) and adj.get("type") == "rpp"):
            continue
        if multi and adj.get("dollar_year") is None and releases:
            adj["dollar_year"] = max(releases)
            filled.append({"adjustment": i, "dollar_year": max(releases)})
        if adj.get("dollar_year") is not None and adj.get("price_index") is None:
            from ..inflation import DEFAULT_PRICE_INDEX
            adj["price_index"] = DEFAULT_PRICE_INDEX
            filled.append({"adjustment": i, "price_index": DEFAULT_PRICE_INDEX})
        if multi or "rpp_years" in adj:
            if adj.get("rpp_years") is None and "rpp_year" not in adj and rpp_years \
                    and all(r in rpp_years for r in releases):
                adj["rpp_years"] = {str(r): int(r) for r in releases}
                filled.append({"adjustment": i, "rpp_years": dict(adj["rpp_years"])})
        elif adj.get("rpp_year") is None and latest is not None:
            adj["rpp_year"] = int(latest)
            filled.append({"adjustment": i, "rpp_year": int(latest)})
    return filled


def _scale_rows(frame: pd.DataFrame, replicates: Any, variables: List[str], rows: np.ndarray, factor: float,
                year: Optional[int]) -> Tuple[pd.DataFrame, Any]:
    """Multiply estimates and SEs of ``variables`` on ``rows`` (and their replicates of release
    ``year``) by ``factor`` (the CPI conversion to the dollar year)."""
    from ..analysis import REPLICATE_COLUMNS
    frame = frame.copy()
    for v in variables:
        for col in (v, f"{v}_se"):
            vals = pd.to_numeric(frame[col], errors="coerce").to_numpy(float).copy()
            vals[rows] = vals[rows] * factor
            frame[col] = vals
    if replicates is not None:
        reps = replicates.copy()
        sel = reps["variable"].isin(variables).to_numpy(copy=True)
        if year is not None:
            sel = sel & (pd.to_numeric(reps["Year"]).astype(int) == int(year)).to_numpy()
        cols = ["estimate"] + [c for c in REPLICATE_COLUMNS if c in reps.columns]
        reps[cols] = reps[cols].astype(float)
        reps.loc[sel, cols] = reps.loc[sel, cols].to_numpy(float) * factor
        replicates = reps
    return frame, replicates


def _apply_adjustments(frame: pd.DataFrame, replicates: Any, m: Mapping[str, Any],
                       releases: List[int]) -> Tuple[Optional[pd.DataFrame], Any, List[Dict[str, Any]], Optional[str]]:
    """Run the manifest's ``adjustments`` in order with the place_adjust_frame core.

    Per release (D15-2): with a declared ``dollar_year``, estimates, SEs and replicates of the
    release are first converted to dollars of that year with the declared price index
    (CPI(dollar_year) / CPI(release); R-CPI-U-RS by default, the index the Census Bureau uses for
    ACS dollars), then divided by the RPP / 100 of the release's own ``rpp_years`` entry (one
    release: ``rpp_year``). Returns (frame, replicates, log, failure message or None)."""
    from .. import rpp
    from ..inflation import INDEX_DISPLAY, get_cpi, price_index_info
    from ..pipeline import normalize_geo_level
    from ..workflows_microdata import place_adjust
    level = normalize_geo_level(m["geography"]["level"])
    log: List[Dict[str, Any]] = []
    multi = len(releases) > 1
    if frame.empty:  # e.g. exclusions removed every unit: nothing to scale; the analyses report the outcome
        return frame, replicates, log, None
    for i, adj in enumerate(m.get("adjustments") or []):
        variables = [str(v) for v in adj["variables"]]
        areas = adj.get("areas", default_rpp_areas(level))
        dollar_year = adj.get("dollar_year")
        index = adj.get("price_index")
        rpp_years = {int(k): int(v) for k, v in (adj.get("rpp_years") or {}).items()} \
            or {int(releases[0]): int(adj["rpp_year"])}  # required by validation, so the hash fixes them
        per_release: List[Dict[str, Any]] = []
        parts: List[pd.DataFrame] = []
        rep_parts: List[pd.DataFrame] = []
        try:
            if multi and replicates is not None and "Year" not in replicates.columns:
                raise ValueError("replicates need a Year column when the manifest has several releases")
            # one release: the whole frame (as in Round 14); several: the rows of each release
            years_col = pd.to_numeric(frame["Year"]).astype(int).to_numpy() if multi \
                else np.full(len(frame), int(releases[0]))
            work, wreps = frame, replicates
            cpis: Dict[int, Optional[Dict[str, Any]]] = {}
            for release in releases:  # 1. price index: release dollars -> dollar_year dollars
                cpis[release] = None
                if dollar_year is not None:
                    c_from, c_to = get_cpi(int(release), index=index), get_cpi(int(dollar_year), index=index)
                    cpis[release] = {"index": index, "from_year": int(release), "to_year": int(dollar_year),
                                     "index_from": c_from, "index_to": c_to, "factor": c_to / c_from}
                    work, wreps = _scale_rows(work, wreps, variables, years_col == int(release), c_to / c_from,
                                              int(release) if multi else None)
            done: List[int] = []
            for release in releases:  # 2. RPP of the release's own rpp_years entry
                rows = years_col == int(release)
                if not rows.any():
                    continue
                sub_reps = wreps
                if wreps is not None and multi:
                    sub_reps = wreps[pd.to_numeric(wreps["Year"]).astype(int).to_numpy() == int(release)]
                res = place_adjust(work[rows], variables, int(release), areas=areas, replicates=sub_reps,
                                   rpp_year=rpp_years[int(release)])
                parts.append(res["frame"])
                if sub_reps is not None:
                    rep_parts.append(res["replicates"])
                done.append(int(release))
                cpi = cpis[release]
                notes = ([f"PRICE INDEX: release {release} dollars converted to {cpi['to_year']} dollars with "
                          f"{INDEX_DISPLAY.get(index, index)} (factor {cpi['factor']:.6f}) before the RPP division "
                          "below."] if cpi else []) + list(res["notes"])
                per_release.append({"release": int(release), "rpp_year": res["rpp_year"], "cpi": cpi,
                                    "rpp_year_matches_release": res["rpp_year"] == int(release),
                                    "rpp_areas": res["rpp_areas"], "boundary_source": res["boundary_source"],
                                    "rows": int(len(res["frame"])), "notes": notes,
                                    "advisories": res["advisories"], "custom_table": res["custom_table"]})
            if not per_release:
                raise ValueError("no rows to adjust")
        except Exception as exc:  # noqa: BLE001 - recorded as a blocking deviation, never substituted
            return None, replicates, log, f"adjustments[{i}] ({adj.get('type')}): {type(exc).__name__}: {exc}"
        if multi:
            frame = pd.concat(parts).loc[frame.index[np.isin(years_col, done)]]
            if wreps is not None:
                rest = wreps[~np.isin(pd.to_numeric(wreps["Year"]).astype(int).to_numpy(), done)]
                replicates = pd.concat([rest] + rep_parts, ignore_index=True)
        else:
            frame = parts[0]
            if wreps is not None:
                replicates = rep_parts[0]
        info = rpp.price_parity_info()
        custom = next((r["custom_table"] for r in per_release if r["custom_table"]), None)
        table: Dict[str, Any] = {"source": "custom" if custom else "bundled"}
        if custom:
            table.update(custom)
        else:
            table["sha256"] = (info.get("csv_sha256") or {}).get("rpp.csv")
        first = per_release[0]
        entry: Dict[str, Any] = {
            "type": adj["type"], "variables": variables, "areas": areas,
            "dollar_year": int(dollar_year) if dollar_year is not None else int(releases[0]),
            "rpp_year": first["rpp_year"] if not multi else None, "rpp_year_source": "manifest",
            "rpp_year_matches_release": all(r["rpp_year_matches_release"] for r in per_release),
            "rpp_areas": first["rpp_areas"] if not multi else
            [dict(a, release=r["release"]) for r in per_release for a in r["rpp_areas"]],
            "boundary_source": first["boundary_source"], "rpp_table": table,
            "rows": int(len(frame)), "notes": [n for r in per_release for n in r["notes"]],
            "advisories": sorted({a for r in per_release for a in r["advisories"]}), "applied_by_default": False}
        if dollar_year is not None:
            pinfo = price_index_info(index)
            entry["price_index"] = {"index": index, "name": INDEX_DISPLAY.get(index, index),
                                    "sha256": pinfo.get("custom_table", {}).get("sha256") or pinfo.get("csv_sha256"),
                                    "source": "custom" if pinfo.get("custom_table") else "bundled"}
            entry["order"] = "price index to dollar_year first, then the RPP of each release's rpp_year"
        if multi or adj.get("rpp_years") is not None:
            entry["rpp_years"] = {str(r["release"]): r["rpp_year"] for r in per_release}
            entry["releases"] = [{k: r[k] for k in ("release", "rpp_year", "cpi", "rpp_year_matches_release",
                                                    "boundary_source", "rows")} for r in per_release]
        elif dollar_year is not None:
            entry["releases"] = [{k: r[k] for k in ("release", "rpp_year", "cpi")} for r in per_release]
        log.append(entry)
    return frame, replicates, log, None
