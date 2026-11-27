# SPDX-License-Identifier: AGPL-3.0-or-later
"""CHR parsing and external health source loading/joining helpers (extracted from census/health_sources.py in Round 182)."""
from census.health_sources import (  # noqa: F401
    Any,
    Callable,
    Dict,
    HealthSourceError,
    List,
    Mapping,
    Optional,
    SOURCES,
    Sequence,
    Z95,
    _cached_file,
    _http_get,
    _measure_key,
    apportion_rates,
    fetch_places,
    fetch_usaleep,
    health_cache_dir,
    io,
    measure_kind,
    np,
    os,
    parse_places,
    parse_usaleep,
    pd,
    resolve_external_file,
)



# ---------------------------------------------------------------------------
# County Health Rankings & Roadmaps (county analytic data)
# ---------------------------------------------------------------------------


def fetch_chr(release: int, fetch: Optional[Callable[[str], bytes]] = None, cache_dir: Optional[str] = None,
              session: Any = None) -> Dict[str, Any]:
    """The CHR&R analytic data file of ``release`` (cached), with provenance."""
    rel = SOURCES["chr"]["releases"].get(int(release))
    if rel is None:
        raise ValueError(f"chr: release {release} not registered")
    get = fetch or (lambda u: _http_get(u, session=session))
    path = os.path.join(cache_dir or health_cache_dir(), "chr", str(release), rel["datasets"]["county"])
    raw, rec, _ = _cached_file(path, rel["url"], get, "text/csv")
    return {"raw": raw, "files": [rec], "dataset": rel["datasets"]["county"], "rows_updated_at": None}


def parse_chr(raw: bytes, measure_names: Mapping[str, str], states: Optional[Sequence[str]] = None) -> pd.DataFrame:
    """County frame GEOID, <name>, <name>_se, <name>_ci_lower, <name>_ci_upper, <name>_numerator,
    <name>_denominator, <name>_flag for ``measure_names`` ({vNNN: name}). Suppressed values (flag 2) are
    missing. Row 2 of the file holds the column codes; state (county 000) and national rows are dropped."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    df = pd.read_csv(io.StringIO(text), dtype=str, header=None, low_memory=False)
    if len(df) < 2:
        raise HealthSourceError("CHR&R file has no code row")
    codes = df.iloc[1].astype(str).str.strip().tolist()
    if "fipscode" not in codes or "countycode" not in codes:
        raise HealthSourceError("CHR&R file: row 2 lacks the column codes (fipscode, countycode)")
    if len(set(codes)) != len(codes):
        raise HealthSourceError("CHR&R file: duplicated column codes")
    df = df.iloc[2:].copy()
    df.columns = codes
    df = df[df["countycode"].astype(str).str.zfill(3) != "000"]
    geo = df["fipscode"].astype(str).str.strip().str.zfill(5)
    if (~geo.str.fullmatch(r"\d{5}")).any():
        raise HealthSourceError("CHR&R file: malformed county FIPS codes")
    df["GEOID"] = geo
    if states:
        df = df[df["GEOID"].str[:2].isin({str(s).zfill(2) for s in states})]
    if df["GEOID"].duplicated().any():
        raise HealthSourceError("CHR&R file: duplicated counties")
    out = pd.DataFrame({"GEOID": df["GEOID"].to_numpy()})
    for code, name in measure_names.items():
        cols = {"": f"{code}_rawvalue", "_ci_lower": f"{code}_cilow", "_ci_upper": f"{code}_cihigh",
                "_numerator": f"{code}_numerator", "_denominator": f"{code}_denominator"}
        if cols[""] not in df.columns:
            raise HealthSourceError(f"CHR&R file has no column {cols['']}")
        for suf, col in cols.items():
            if col not in df.columns:
                out[name + suf] = np.nan
                continue
            rawcol = df[col]
            num = pd.to_numeric(rawcol, errors="coerce")
            if (rawcol.notna() & rawcol.astype(str).str.strip().ne("") & num.isna()).any():
                raise HealthSourceError(f"CHR&R {col}: non-numeric values")
            out[name + suf] = num.to_numpy()
        flag = pd.to_numeric(df[f"{code}_flag"], errors="coerce").to_numpy() if f"{code}_flag" in df.columns \
            else np.full(len(df), np.nan)
        out[f"{name}_flag"] = flag
        out.loc[flag == 2, [name, f"{name}_ci_lower", f"{name}_ci_upper"]] = np.nan
        out[f"{name}_se"] = (out[f"{name}_ci_upper"] - out[f"{name}_ci_lower"]) / (2 * Z95)
    return out


# ---------------------------------------------------------------------------
# Manifest entry point
# ---------------------------------------------------------------------------


def _provenance(source: str, release: Any, level: str, dataset: str, names: Mapping[str, str],
                files: List[Dict[str, Any]], units: int, rows_updated_at: Any = None,
                **extra: Any) -> Dict[str, Any]:
    info = SOURCES[source]
    return {"source": source, "release": release, "level": level, "dataset": dataset, "measures": dict(names),
            "kinds": {m: measure_kind(source, m) for m in names}, "files": files,
            "rows_updated_at": rows_updated_at, "units": int(units), "licence": info["licence"],
            "uncertainty": info["uncertainty_text"], "model": info["model_text"],
            "citation": info["citation"].format(release=release, dataset=dataset), **extra}


def load_external(
    entries: Sequence[Mapping[str, Any]],
    level: str,
    states: Sequence[str],
    fetch: Optional[Callable[[str], bytes]] = None,
    cache_dir: Optional[str] = None,
    crosswalk: Optional[pd.DataFrame] = None,
) -> "tuple[pd.DataFrame, List[Dict[str, Any]]]":
    """Fetch and parse a manifest's external entries; returns (wide frame on GEOID, provenance records).

    ``crosswalk``: 2010-to-2020 tract crosswalk with population masses for USALEEP entries with
    ``apportion_to`` (default: census.block_weights.tract_weights for ``states``)."""
    groups: Dict[tuple, Dict[str, str]] = {}
    for e in entries:
        if e["source"] in ("usaleep", "wonder"):
            continue
        groups.setdefault((e["source"], int(e["release"])), {})[_measure_key(e["source"], e["measure"])] = \
            str(e["name"])
    parts: List[pd.DataFrame] = []
    wonder_geoids = {}
    prov: List[Dict[str, Any]] = []
    for (source, release), names in groups.items():
        if source == "places":
            got = fetch_places(release, level, states, list(names), fetch=fetch, cache_dir=cache_dir)
            part = parse_places(got["rows"], level, {k.upper(): v for k, v in names.items()})
        elif source == "chr":
            got = fetch_chr(release, fetch=fetch, cache_dir=cache_dir)
            part = parse_chr(got["raw"], names, states)
        else:  # registry and validation keep this unreachable
            raise HealthSourceError(f"no connector for {source!r}")
        prov.append(_provenance(source, release, level, got["dataset"], names, got["files"], len(part),
                                got.get("rows_updated_at")))
        parts.append(part)
    for e in entries:
        name = str(e["name"])
        if e["source"] == "usaleep":
            got = fetch_usaleep(states, fetch=fetch, cache_dir=cache_dir)
            part, drop = parse_usaleep(got["rows"], name, bool(e.get("include_predicted", False)))
            extra: Dict[str, Any] = {"predicted": drop}
            if e.get("apportion_to") is not None:
                cw = crosswalk
                if cw is None:
                    from .block_weights import tract_weights
                    cw = tract_weights(states, "2010_to_2020", "population")
                part, rec = apportion_rates(part, name, cw, float(e.get("min_coverage", 0.9)),
                                            str(e.get("split", "missing")))
                extra["apportionment"] = rec
            else:
                from .geo_crosswalk import census2010_to_acs_geoid
                part["GEOID"] = part["GEOID"].map(census2010_to_acs_geoid)
            part = part.drop(columns=[c for c in part.columns if c == f"{name}_coverage"])
            prov.append(_provenance("usaleep", int(e["release"]), level, got["dataset"], {"E0": name},
                                    got["files"], len(part), **extra))
            parts.append(part)
        elif e["source"] == "wonder":
            from .vital_records import load_wonder_measure
            part, rec = load_wonder_measure(resolve_external_file(str(e["file"])), str(e["sha256"]),
                                            str(e["measure"]), name, level)
            prov.append(_provenance("wonder", None, level, rec["dataset"], {str(e["measure"]).lower(): name},
                                    [rec["file"]], len(part), export=rec))
            wonder_geoids[name] = part["GEOID"].astype(str).tolist()
            parts.append(part)
    wide: Optional[pd.DataFrame] = None
    for part in parts:
        wide = part if wide is None else wide.merge(part, on="GEOID", how="outer")
    if wide is not None and wonder_geoids:
        wide.attrs["wonder_source_geoids"] = wonder_geoids
        wide.attrs["wonder_columns"] = list(wonder_geoids)
    return (wide if wide is not None else pd.DataFrame({"GEOID": []})), prov


def join_external(frame: pd.DataFrame, ext: pd.DataFrame, names: Sequence[str],
                  required: Sequence[str]) -> "tuple[pd.DataFrame, Dict[str, Any]]":
    """Left-join external columns to ``frame`` on GEOID; returns (frame, join record).

    ``required``: frame variables that define a complete ACS unit; the record's ``missing_share``
    is the share of complete units without an external value (any of ``names``)."""
    if "Year" in frame.columns and frame["Year"].nunique() > 1:
        raise HealthSourceError("external variables need a single-release frame (one row per GEOID)")
    sufs = ("", "_se", "_ci_lower", "_ci_upper", "_flag", "_numerator", "_denominator", "_lower_bound",
            "_upper_bound")
    cols = ["GEOID"] + [n + s for n in names for s in sufs if n + s in ext.columns]
    clash = [c for c in cols[1:] if c in frame.columns]
    if clash:
        raise HealthSourceError(f"external columns already in the frame: {clash}")
    out = frame.merge(ext[cols], on="GEOID", how="left")
    req = [c for c in required if c in out.columns]
    complete = np.isfinite(out[req].to_numpy(float)).all(axis=1) if req else np.ones(len(out), bool)
    has = np.isfinite(out[list(names)].to_numpy(float)).all(axis=1)
    lacking = out.loc[complete & ~has, "GEOID"].astype(str).tolist()
    n_complete = int(complete.sum())
    per_name = {n: float((complete & ~np.isfinite(out[n].to_numpy(float))).sum() / n_complete) if n_complete
                else float("nan") for n in names}
    record = {"frame_units": int(len(out)), "complete_acs_units": int(complete.sum()),
              "matched_units": int((complete & has).sum()), "complete_units_without_external": len(lacking),
              "missing_share": float(len(lacking) / complete.sum()) if complete.sum() else float("nan"),
              "missing_share_by_variable": per_name,
              "examples_without_external": lacking[:20],
              "source_units_outside_frame": int((~ext["GEOID"].isin(frame["GEOID"].astype(str))).sum())}
    wonder_names = list(ext.attrs.get("wonder_columns", ()))
    if wonder_names:
        if frame["GEOID"].duplicated().any() or ext["GEOID"].duplicated().any():
            raise HealthSourceError("WONDER joins require unique county GEOIDs")
        matched_masks = []; missing_masks = []; all_supp = np.zeros(len(out),bool)
        per_variable = {}; unmatched_shares = {}; unsuppressed_missing = {}
        for name in names:
            finite = np.isfinite(out[name].to_numpy(float))
            if name not in wonder_names:
                matched_masks.append(finite); missing_masks.append(~finite)
                continue
            source_ids = ext.attrs.get("wonder_source_geoids", {}).get(name, ext["GEOID"].astype(str))
            matched = out["GEOID"].astype(str).isin(set(source_ids)).to_numpy()
            flag = out.get(name+"_flag",pd.Series(0,index=out.index)).fillna(0).to_numpy()
            count = out.get(name+"_numerator",out[name]).to_numpy(float)
            suppressed = matched & ((flag==2) | ((count>=1)&(count<=9)))
            for col in [name,name+"_numerator",name+"_se",name+"_ci_lower",name+"_ci_upper"]:
                if col in out:out.loc[suppressed,col]=np.nan
            if name+"_flag" in out:out.loc[suppressed,name+"_flag"]=2
            finite = np.isfinite(out[name].to_numpy(float))
            missing = ~finite & ~suppressed
            matched_masks.append(matched);missing_masks.append(missing);all_supp |= suppressed
            n_supp = int((complete & suppressed).sum())
            per_variable[name] = {"matched":int((complete & matched).sum()),"unmatched":int((complete & ~matched).sum()),
                "suppressed":n_supp,"analyzable":int((complete & finite & matched).sum()),
                "unsuppressed_missing":int((complete & matched & ~finite & ~suppressed).sum()),
                "suppressed_geoids":out.loc[complete & suppressed,"GEOID"].astype(str).tolist(),
                "excluded_deaths_bounds":[n_supp,9*n_supp]}
            per_name[name] = float((complete & missing).sum()/n_complete) if n_complete else float("nan")
            unmatched_shares[name] = float((complete & ~matched).sum()/n_complete) if n_complete else float("nan")
            unsuppressed_missing[name] = per_variable[name]["unsuppressed_missing"]
        any_missing = np.logical_or.reduce(missing_masks)
        ids_matched = np.logical_and.reduce(matched_masks)
        has = np.isfinite(out[list(names)].to_numpy(float)).all(axis=1)
        lacking = out.loc[complete & any_missing,"GEOID"].astype(str).tolist()
        record.update(matched_units=int((complete & ids_matched).sum()),unmatched_units=int((complete & ~ids_matched).sum()),
                      suppressed_units=int((complete & all_supp).sum()),analyzable_units=int((complete & has).sum()),
                      complete_units_without_external=len(lacking),missing_share=float(len(lacking)/n_complete) if n_complete else float("nan"),
                      missing_share_by_variable=per_name,examples_without_external=lacking[:20],
                      unmatched_share_by_variable=unmatched_shares,unsuppressed_missing_by_variable=unsuppressed_missing,
                      wonder=per_variable)
        out.attrs.update(frame.attrs)
        out.attrs["wonder_columns"] = wonder_names
    return out, record
