# SPDX-License-Identifier: AGPL-3.0-or-later
"""Panel harmonization and wide-row apportionment helpers (extracted from census/geo_crosswalk.py in Round 176)."""
from census.geo_crosswalk import (  # noqa: F401
    ACS_2010_BOUNDARY_CHANGES,
    Any,
    BLOCK_WEIGHT_TYPES,
    DEFAULT_MIN_COVERAGE,
    Dict,
    FIRST_RELEASE_CT_PLANNING_REGIONS,
    LIMITATIONS,
    List,
    METHOD_APPORTIONED,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Union,
    WEIGHT_AUTO,
    WEIGHT_HOUSING,
    WEIGHT_POPULATION,
    _DERIVED_SUFFIX_RE,
    _recompute_reliability,
    apportion,
    apportion_long,
    crosswalk_targets_to_output_codes,
    native_tracts_to_output_codes,
    normalize_tract_geoids,
    np,
    os,
    parse_variable_code,
    pd,
    relationship_source,
    source_tracts_to_crosswalk_codes,
    tract_crosswalk,
    tract_vintage,
)



def harmonize_panel(
    df: pd.DataFrame,
    target_vintage: int = 2020,
    weight: str = WEIGHT_AUTO,
    weights_file: Optional[str] = None,
    crosswalk: Optional[pd.DataFrame] = None,
    geoid_col: str = "GEOID",
    year_col: str = "Year",
    metadata: Optional[Mapping[str, Mapping[str, str]]] = None,
    assume_additive: Union[bool, Sequence[str]] = False,
    non_additive: str = "raise",
    min_coverage: float = DEFAULT_MIN_COVERAGE,
    zero_estimate_rule: str = "all",
    ct_coding: str = "auto",
    return_record: bool = False,
) -> Union[pd.DataFrame, Tuple[pd.DataFrame, Dict[str, Any]]]:
    """Put a multi-release tract panel on one tract vintage.

    Rows from releases already on ``target_vintage`` tracts are kept (GEOIDs
    recoded to one consistent coding); rows from releases on the other vintage
    are apportioned with :func:`apportion`, one release at a time. Accepts the
    wide (GEOID, Year) panel from ``census.panel.build_tidy_panel`` (raw code
    columns) or a long frame with ``variable, estimate, moe`` columns.

    Wide panels: ``_SE``/``_CV``/``_RELIABILITY`` columns are recomputed for
    apportioned rows; ``_NOTE`` and annotation columns are blanked there. With
    ``non_additive="drop"``, non-additive columns (``PE``/``PM``, medians, ...)
    are kept for native rows and set to NaN for apportioned rows.

    GEOID coding: target 2010 uses the codes of the latest 2010-vintage ACS
    release (e.g. Oglala Lakota 46102); target 2020 uses Connecticut planning-
    region codes when ``ct_coding`` is ``"2022"`` (``"auto"``: when the panel
    has a 2022+ release) and the former county codes when ``"2020"``.

    Weights (``weight``): ``"auto"`` (default) uses block housing-unit weights
    for household and housing tables (``census.block_weights.weight_for_variable``)
    and block population weights otherwise, built only for the panel's states;
    ``"population"``, ``"housing_units"``, ``"land_area"`` or ``"total_area"``
    apply one weight to every column. States without block data fall back to
    land-area weights (noted in the record).

    The returned frame's ``attrs["harmonization"]`` (and the second element
    when ``return_record=True``) is a JSON-ready record for run metadata.
    """
    if target_vintage not in (2010, 2020):
        raise ValueError("target_vintage must be 2010 or 2020")
    for col in (geoid_col, year_col):
        if col not in df.columns:
            raise KeyError(f"panel needs a {col!r} column")
    long_format = {"variable", "estimate", "moe"}.issubset(df.columns)
    direction = "2010_to_2020" if target_vintage == 2020 else "2020_to_2010"
    years = sorted(int(y) for y in pd.unique(df[year_col]))
    vintages = {y: tract_vintage(y) for y in years}
    if ct_coding == "auto":
        ct_coding = "2022" if any(y >= FIRST_RELEASE_CT_PLANNING_REGIONS for y in years) else "2020"
    if ct_coding not in ("2020", "2022"):
        raise ValueError("ct_coding must be 'auto', '2020', or '2022'")

    if crosswalk is None and weights_file is None and weight == WEIGHT_AUTO:
        split = _split_by_weight(df, geoid_col, year_col, long_format)
        if len(split) > 1:
            return _harmonize_split(split, df, geoid_col, year_col, long_format, return_record, dict(
                target_vintage=target_vintage, geoid_col=geoid_col, year_col=year_col, metadata=metadata,
                assume_additive=assume_additive, non_additive=non_additive, min_coverage=min_coverage,
                zero_estimate_rule=zero_estimate_rule, ct_coding=ct_coding,
            ))
        weight = next(iter(split)) if split else WEIGHT_POPULATION
    if crosswalk is None:
        states = sorted({g[:2] for g in normalize_tract_geoids(df[geoid_col]).astype(str)})
        crosswalk = tract_crosswalk(
            direction, weight=weight, weights_file=weights_file,
            states=(states or None) if weight in BLOCK_WEIGHT_TYPES else None,
        )
    cw = crosswalk.copy()
    cw.attrs = dict(crosswalk.attrs)

    panel = df.copy()
    panel[geoid_col] = normalize_tract_geoids(panel[geoid_col]).values
    panel[year_col] = pd.to_numeric(panel[year_col]).astype("int64")
    recodes: Dict[str, int] = {}

    def _count(label: str, before: pd.Series, after: pd.Series) -> None:
        n = int((before.values != after.values).sum())
        if n:
            recodes[label] = recodes.get(label, 0) + n

    # 1. Bring source rows onto the crosswalk's (decennial Census) codes.
    src_years = [y for y in years if vintages[y] != target_vintage]
    native_years = [y for y in years if vintages[y] == target_vintage]
    src_mask = panel[year_col].isin(src_years)
    before = panel.loc[src_mask, geoid_col]
    after = source_tracts_to_crosswalk_codes(before, target_vintage)
    _count("acs_2010_codes_to_census_2010" if target_vintage == 2020 else "ct_planning_region_to_2020_county",
           before, after)
    panel.loc[src_mask, geoid_col] = after.values

    # 2. Bring native rows and crosswalk targets onto one output coding.
    nat_mask = panel[year_col].isin(native_years)
    before = panel.loc[nat_mask, geoid_col]
    after = native_tracts_to_output_codes(before, target_vintage, ct_coding)
    cw["target_geoid"] = crosswalk_targets_to_output_codes(cw["target_geoid"], target_vintage, ct_coding).values
    _count("acs_2010_codes_to_latest" if target_vintage == 2010 else f"ct_to_{ct_coding}_coding", before, after)
    panel.loc[nat_mask, geoid_col] = after.values

    # Compare normalized GEOIDs: a panel read without dtype=str loses leading zeros.
    boundary_hits = sorted(
        set(normalize_tract_geoids(df[geoid_col]).astype(str)) & set(ACS_2010_BOUNDARY_CHANGES)
    )
    record: Dict[str, Any] = {
        "method": METHOD_APPORTIONED,
        "target_vintage": target_vintage,
        "direction": direction,
        "weight_type": cw.attrs.get("weight_type", "user-supplied"),
        "requested_weight": cw.attrs.get("requested_weight", cw.attrs.get("weight_type", "user-supplied")),
        "block_data_unavailable": list(cw.attrs.get("fallbacks", {}).get("block_data_unavailable", [])),
        "weights_file": os.path.basename(weights_file) if weights_file else None,
        "relationship_file": relationship_source() if weights_file is None else None,
        "block_source": cw.attrs.get("source") if cw.attrs.get("requested_weight") in BLOCK_WEIGHT_TYPES else None,
        "years_native": native_years,
        "years_apportioned": src_years,
        "connecticut_coding": ct_coding if target_vintage == 2020 else "2020 county-based",
        "geoid_recodes": recodes,
        "min_coverage": min_coverage,
        "zero_estimate_rule": zero_estimate_rule,
        "rows_in": int(len(df)),
        "unmatched_geoids": {},
        "incomplete_targets": {},
        "dropped_columns": {},
        "notes": list(cw.attrs.get("notes", [])),
        "limitations": list(LIMITATIONS),
    }
    if boundary_hits:
        record["notes"].append(
            "GEOIDs with post-2010 boundary changes cannot be matched exactly: "
            + "; ".join(f"{g} ({ACS_2010_BOUNDARY_CHANGES[g]})" for g in boundary_hits)
        )

    if not src_years:
        out = panel
    else:
        native = panel.loc[nat_mask]
        parts: List[pd.DataFrame] = [native]
        kwargs = dict(
            metadata=metadata, assume_additive=assume_additive, non_additive=non_additive,
            min_coverage=min_coverage, zero_estimate_rule=zero_estimate_rule,
            geoid_col=geoid_col,
        )
        for year in src_years:
            rows = panel.loc[panel[year_col] == year]
            if long_format:
                res = apportion_long(rows, cw, group_cols=[year_col], **kwargs)
            else:
                res = _apportion_wide_panel_rows(rows, cw, year_col, kwargs)
            record["unmatched_geoids"][str(year)] = res.attrs.get("unmatched_geoids", [])
            record["incomplete_targets"][str(year)] = len(res.attrs.get("incomplete_targets", []))
            record["dropped_columns"].update(res.attrs.get("dropped_columns", {}))
            parts.append(res)
        out = pd.concat(parts, ignore_index=True, sort=False)
        if not long_format:
            out = out[[c for c in panel.columns if c in out.columns]]
            apportioned = out.index[out[year_col].isin(src_years)]
            _recompute_reliability(out, apportioned)
        sort_cols = [geoid_col, year_col] + (["variable"] if long_format else [])
        out = out.sort_values(sort_cols).reset_index(drop=True)
        if not long_format:
            out = _restore_dtypes(out, panel)
    record["rows_out"] = int(len(out))
    record["unmatched_geoids"] = {k: v for k, v in record["unmatched_geoids"].items() if v}
    out.attrs["harmonization"] = record
    return (out, record) if return_record else out


def _weight_kind(item: str) -> str:
    from .block_weights import weight_for_variable

    base = _DERIVED_SUFFIX_RE.sub(r"\g<key>", item)
    base = base[: -len("_NOTE")] if base.endswith("_NOTE") else base
    return weight_for_variable(base) if parse_variable_code(base) else WEIGHT_POPULATION


def _split_by_weight(df: pd.DataFrame, geoid_col: str, year_col: str, long_format: bool) -> Dict[str, List[str]]:
    """weight type -> variables (long) or columns (wide) for ``weight="auto"``."""
    items = [str(v) for v in pd.unique(df["variable"])] if long_format else [
        str(c) for c in df.columns if c not in (geoid_col, year_col)
    ]
    groups: Dict[str, List[str]] = {}
    for item in items:
        groups.setdefault(_weight_kind(item), []).append(item)
    if not long_format and len(groups) > 1:
        pop_values = [c for c in groups[WEIGHT_POPULATION] if parse_variable_code(_DERIVED_SUFFIX_RE.sub(r"\g<key>", c))]
        if not pop_values:  # only NAME-like columns besides housing variables
            return {WEIGHT_HOUSING: groups[WEIGHT_HOUSING] + groups[WEIGHT_POPULATION]}
    return groups


def _harmonize_split(
    split: Dict[str, List[str]],
    df: pd.DataFrame,
    geoid_col: str,
    year_col: str,
    long_format: bool,
    return_record: bool,
    kwargs: Dict[str, Any],
) -> Union[pd.DataFrame, Tuple[pd.DataFrame, Dict[str, Any]]]:
    """Harmonize each weight group separately and recombine (``weight="auto"``)."""
    results: List[pd.DataFrame] = []
    records: Dict[str, Dict[str, Any]] = {}
    for kind, items in split.items():
        if long_format:
            part = df.loc[df["variable"].astype(str).isin(items)]
        else:
            part = df[[geoid_col, year_col] + items]
        res, rec = harmonize_panel(part, weight=kind, return_record=True, **kwargs)  # type: ignore[misc]
        results.append(res)
        records[kind] = rec
    if long_format:
        out = pd.concat(results, ignore_index=True, sort=False)
        out = out.sort_values([geoid_col, year_col, "variable"]).reset_index(drop=True)
    else:
        out = results[0]
        for res in results[1:]:
            out = out.merge(res, on=[geoid_col, year_col], how="outer")
        out = out[[c for c in df.columns if c in out.columns]]
        out = out.sort_values([geoid_col, year_col]).reset_index(drop=True)
    record = dict(next(iter(records.values())))
    merged: Dict[str, Dict[str, Any]] = {"unmatched_geoids": {}, "dropped_columns": {}, "incomplete_targets": {}}
    for r in records.values():
        for key, acc in merged.items():
            for k, v in r.get(key, {}).items():
                if isinstance(v, list):
                    acc[k] = sorted(set(acc.get(k, [])) | set(v))
                elif isinstance(v, (int, float)):
                    acc[k] = max(acc.get(k, 0), v)
                else:
                    acc[k] = v
    record.update(merged)
    record.update(
        weight_type=WEIGHT_AUTO,
        requested_weight=WEIGHT_AUTO,
        weights_by_variable={k: list(v) for k, v in split.items()},
        block_data_unavailable=sorted({s for r in records.values() for s in r.get("block_data_unavailable", [])}),
        weight_records={k: {"weight_type": r["weight_type"], "notes": r["notes"]} for k, r in records.items()},
        notes=list(dict.fromkeys(n for r in records.values() for n in r["notes"])),
        rows_in=int(len(df)),
        rows_out=int(len(out)),
    )
    out.attrs["harmonization"] = record
    return (out, record) if return_record else out


def _apportion_wide_panel_rows(
    rows: pd.DataFrame, cw: pd.DataFrame, year_col: str, kwargs: Dict[str, Any]
) -> pd.DataFrame:
    res = apportion(rows, cw, group_cols=[year_col], **kwargs)
    # Non-value columns (NAME, notes, annotations, derived) are blank for apportioned rows.
    for col in rows.columns:
        if col in res.columns:
            continue
        info = parse_variable_code(str(col))
        if info is not None and info[1] in ("E", "M", "PE", "PM"):
            res[col] = np.nan
        elif _DERIVED_SUFFIX_RE.match(str(col)) and not str(col).endswith("_RELIABILITY"):
            res[col] = np.nan
        else:
            res[col] = ""
    return res


def _restore_dtypes(out: pd.DataFrame, like: pd.DataFrame) -> pd.DataFrame:
    for col in out.columns:
        if col in like.columns and pd.api.types.is_numeric_dtype(like[col]) and not pd.api.types.is_numeric_dtype(out[col]):
            out[col] = pd.to_numeric(out[col], errors="coerce")
        elif col in like.columns and (pd.api.types.is_object_dtype(like[col]) or pd.api.types.is_string_dtype(like[col])):
            out[col] = out[col].fillna("") if not pd.api.types.is_numeric_dtype(out[col]) else out[col]
    return out


__all__ = [
    "ACS_2010_BOUNDARY_CHANGES",
    "ACS_2010_COUNTY_RECODES",
    "ACS_2010_TRACT_RENUMBERING",
    "acs_to_census2010_geoid",
    "source_tracts_to_crosswalk_codes",
    "native_tracts_to_output_codes",
    "crosswalk_targets_to_output_codes",
    "apportion",
    "apportion_long",
    "census2010_to_acs_geoid",
    "check_additive",
    "harmonize_panel",
    "load_ct_tract_recode",
    "load_tract_relationships",
    "load_weight_file",
    "normalize_tract_geoid",
    "normalize_tract_geoids",
    "recode_ct_tracts",
    "relationship_source",
    "tract_crosswalk",
    "tract_vintage",
    "BLOCK_WEIGHT_TYPES",
    "WEIGHT_AUTO",
    "WEIGHT_HOUSING",
]
