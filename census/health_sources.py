# SPDX-License-Identifier: AGPL-3.0-or-later
"""External health-outcome data sources (PLAN_ROUND_21 B2).

A registry of public, keyless bulk sources whose estimates a manifest can join to
an ACS analysis frame (manifest ``external`` variables). Each source records what
it is, where it comes from, its licence, its geography vintage, the kind of
uncertainty its estimates carry, and the covariates of the model that produced
it, so that analyses can be checked for circularity (regressing a model-based
outcome on the model's own inputs partly recovers the model, not the world).

The first connector is CDC PLACES (model-based adult crude prevalences for
tracts and counties). Downloads are plain HTTPS CSV exports from the
data.cdc.gov Socrata portal, filtered to the requested states and measures; no
key and no app token. Every page is cached with a sidecar recording its URL,
SHA-256 and retrieval time (the same convention as the Census VRE files), and
the dataset's ``rowsUpdatedAt`` is recorded because Socrata datasets can be
revised in place. ``CENSUS_HEALTH_OFFLINE`` refuses downloads (cache only).
"""

import io
import json
import os
import re
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence
from urllib.parse import urlencode

import numpy as np
import pandas as pd

from .block_weights import STATE_ABBR
from .geo import get_resource_path
from .replicate import _read_cached, _sha256, _sidecar_path, _write_cached

USER_AGENT = "census-research-engine/health-sources (research toolkit; python-requests)"
Z95 = 1.959963984540054
PAGE_SIZE = 50000
EXTERNAL_KEYS = ("name", "source", "release", "measure")
# where an external variable may appear: only as the outcome of these methods (its model-based
# error is independent of the ACS sampling error, so it enters the residual; as a covariate it
# would go uncorrected)
EXTERNAL_OUTCOME_METHODS = ("fit_eiv", "fit_replicate", "fh_regression")
JOIN_MISSING_LIMIT = 0.05

_PLACES_MEASURES = (
    "ACCESS2", "ARTHRITIS", "BINGE", "BPHIGH", "BPMED", "CANCER", "CASTHMA", "CHD", "CHECKUP", "CHOLSCREEN",
    "COGNITION", "COLON_SCREEN", "COPD", "CSMOKING", "DENTAL", "DEPRESSION", "DIABETES", "DISABILITY",
    "EMOTIONSPT", "FOODINSECU", "FOODSTAMP", "GHLTH", "HEARING", "HIGHCHOL", "HOUSINSECU", "INDEPLIVE",
    "LACKTRPT", "LONELINESS", "LPA", "MAMMOUSE", "MHLTH", "MOBILITY", "OBESITY", "PHLTH", "SELFCARE",
    "SHUTUTILITY", "SLEEP", "STROKE", "TEETHLOST", "VISION",
)

SOURCES: Dict[str, Dict[str, Any]] = {
    "places": {
        "title": "CDC PLACES: Local Data for Better Health",
        "publisher": "Centers for Disease Control and Prevention, National Center for Chronic Disease Prevention "
                     "and Health Promotion, Division of Population Health",
        "licence": "Public Domain",
        "portal": "https://data.cdc.gov",
        "methodology_url": "https://www.cdc.gov/places/methodology/index.html",
        "releases": {
            2025: {
                "datasets": {"tract": "cwsq-ngmh", "county": "swc5-untb"},
                "data_years": "BRFSS 2023 (2022 for DENTAL, TEETHLOST, MAMMOUSE, COLON_SCREEN, SLEEP)",
                "tract_vintage": 2020,
                "poststratification": "decennial 2020 census block population counts",
            },
        },
        "measures": _PLACES_MEASURES,
        "value_type": {"tract": "Crude prevalence", "county": "Crude prevalence"},
        "unit": "percent of adults aged 18 and over",
        "uncertainty": "model_based",
        "uncertainty_text": "model-based 95% interval (2.5th and 97.5th percentiles of 1,000 Monte Carlo draws); the "
                            "SE used here is (upper - lower) / (2 x 1.96), an approximation since percentile "
                            "intervals need not be symmetric",
        "model_text": "multilevel logistic regression and post-stratification (MRP) of BRFSS responses: individual "
                      "age, sex, race/ethnicity and education; county share of adults below 150% of the poverty "
                      "line (ACS 5-year); state and county random effects; applied to census block population "
                      "counts and aggregated to tracts. Within a county a tract's estimate varies only with its "
                      "age, sex, race/ethnicity and education composition: the model has no tract-level health "
                      "information",
        # ACS table families whose purpose is measuring the model's covariates (age-sex, race/ethnicity,
        # education; poverty enters at county level). A table-level heuristic: a composition share built
        # from another table's age cells (e.g. B18101) is not caught, so reports still state the caveat
        "model_covariate_tables": {
            "age and sex": ("B01001", "B01002"),
            "race/ethnicity": ("B02001", "B03002", "B01001A", "B01001B", "B01001D", "B01001H", "B01001I"),
            "education": ("B15002", "B15003", "C15002", "B15001"),
            "poverty (county level in the model)": ("B17001", "C17002", "B17024", "B17020", "S1701"),
        },
        "citation": "Centers for Disease Control and Prevention. PLACES: Local Data for Better Health, {release} "
                    "release. https://www.cdc.gov/places (data: data.cdc.gov dataset {dataset}).",
    },
}


class HealthSourceError(RuntimeError):
    """An external health source could not be fetched, parsed or joined."""


def health_cache_dir() -> str:
    """$CENSUS_HEALTH_DIR or <repo>/.cache/health."""
    return os.getenv("CENSUS_HEALTH_DIR") or get_resource_path(os.path.join(".cache", "health"))


def _offline() -> bool:
    return os.getenv("CENSUS_HEALTH_OFFLINE", "").strip() not in ("", "0", "false", "False")


def source_info(source: str) -> Dict[str, Any]:
    if source not in SOURCES:
        raise ValueError(f"unknown external source {source!r}; known: {sorted(SOURCES)}")
    return SOURCES[source]


def dataset_id(source: str, release: int, level: str) -> str:
    info = source_info(source)
    rel = info["releases"].get(int(release))
    if rel is None:
        raise ValueError(f"{source}: release {release} not registered (known: {sorted(info['releases'])})")
    ds = rel["datasets"].get(level)
    if ds is None:
        raise ValueError(f"{source} {release}: no dataset for geography level {level!r} "
                         f"(available: {sorted(rel['datasets'])})")
    return ds


def validate_external(entries: Any, geography: Mapping[str, Any], releases: Sequence[int],
                      taken_names: Iterable[str]) -> List[str]:
    """Errors for a manifest's ``external`` list (empty when valid). Offline: checks the registry only."""
    errors: List[str] = []
    if not isinstance(entries, list) or not entries:
        return ["external must be a non-empty list of {name, source, release, measure} objects"]
    taken = set(taken_names)
    seen: Dict[tuple, str] = {}
    level = str(geography.get("level", ""))
    if len(list(releases)) > 1:
        errors.append("external variables need a single ACS release (one row per unit to join on GEOID; external "
                      "values are not release-specific)")
    for i, e in enumerate(entries):
        if not isinstance(e, Mapping):
            errors.append(f"external[{i}]: must be an object")
            continue
        extra = sorted(set(e) - set(EXTERNAL_KEYS))
        missing = [k for k in EXTERNAL_KEYS if k not in e]
        if extra:
            errors.append(f"external[{i}]: unknown keys {extra} (allowed: {list(EXTERNAL_KEYS)})")
        if missing:
            errors.append(f"external[{i}]: needs {missing}")
            continue
        name = str(e["name"])
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
            errors.append(f"external[{i}]: name {name!r} must be an identifier")
        if name in taken:
            errors.append(f"external[{i}]: name {name!r} is already a variable, derivation or external name")
        taken.add(name)
        try:
            info = source_info(str(e["source"]))
            if not isinstance(e["release"], int) or isinstance(e["release"], bool):
                raise ValueError(f"release must be an integer year, got {e['release']!r}")
            dataset_id(str(e["source"]), e["release"], level)
        except ValueError as exc:
            errors.append(f"external[{i}]: {exc}")
            continue
        if str(e["measure"]) not in info["measures"]:
            errors.append(f"external[{i}]: measure {e['measure']!r} is not a {e['source']} measure")
        key = (str(e["source"]), e["release"], str(e["measure"]).upper())
        if key in seen:
            errors.append(f"external[{i}]: {key[0]} {key[1]} {key[2]} is already external {seen[key]!r}; name each "
                          "measure once")
        seen.setdefault(key, name)
        if level == "tract":
            from .geo_crosswalk import tract_vintage
            vintage = info["releases"][e["release"]].get("tract_vintage")
            target = geography.get("harmonize_tracts_to")
            if target is not None:
                if target != vintage:
                    errors.append(f"external[{i}]: {e['source']} {e['release']} uses {vintage} tracts; "
                                  f"harmonize_tracts_to is {target}")
            else:
                other = []
                try:
                    other = [r for r in releases if tract_vintage(int(r)) != vintage]
                except ValueError as exc:  # pre-2010 tracts
                    errors.append(f"external[{i}]: {exc}")
                if other:
                    errors.append(f"external[{i}]: {e['source']} {e['release']} uses {vintage} tracts; ACS releases "
                                  f"{other} use the other tract vintage (set geography.harmonize_tracts_to to "
                                  f"{vintage})")
    if geography.get("states") is None and geography.get("state") in (None, "all"):
        errors.append("external: needs geography.state or geography.states (downloads are filtered by state)")
    return errors


def circularity_overlap(source: str, tables: Iterable[str]) -> Dict[str, List[str]]:
    """Model-covariate families of ``source`` that ``tables`` (ACS table ids) belong to."""
    fam = source_info(source).get("model_covariate_tables") or {}
    tables = {str(t).upper() for t in tables}
    out: Dict[str, List[str]] = {}
    for label, ids in fam.items():
        hit = sorted(t for t in tables if any(t == x or t.startswith(x + "_") for x in ids))
        if hit:
            out[label] = hit
    return out


# ---------------------------------------------------------------------------
# Download and cache
# ---------------------------------------------------------------------------


def _http_get(url: str, session: Any = None, timeout: float = 300.0) -> bytes:
    from .http import polite_get
    resp = polite_get(url, user_agent=USER_AGENT, error=HealthSourceError, session=session, timeout=timeout)
    if resp.status_code != 200:
        raise HealthSourceError(f"HTTP {resp.status_code} for {url}")
    return resp.content or b""


def _side(path: str) -> Dict[str, Any]:
    with open(_sidecar_path(path), encoding="utf-8") as f:
        return json.load(f)


def _states_abbr(states: Sequence[str]) -> List[str]:
    out = []
    for s in states:
        code = str(s).zfill(2)
        if code not in STATE_ABBR:
            raise ValueError(f"unknown state FIPS {s!r}")
        out.append(STATE_ABBR[code])
    return out


def places_query_url(ds: str, states: Sequence[str], measures: Sequence[str], offset: int, limit: int) -> str:
    """Socrata CSV export of crude prevalences (datavaluetypeid CrdPrv) for ``states`` and ``measures``;
    (locationid, measureid) is unique among them, so offset paging is deterministic."""
    sts = ",".join(f"'{a}'" for a in _states_abbr(states))
    ms = ",".join(f"'{m}'" for m in measures)
    params = {"$where": f"stateabbr in({sts}) AND measureid in({ms}) AND datavaluetypeid='CrdPrv'",
              "$order": "locationid,measureid",
              "$limit": str(limit), "$offset": str(offset)}
    return f"https://data.cdc.gov/resource/{ds}.csv?" + urlencode(params)


def fetch_places(
    release: int,
    level: str,
    states: Sequence[str],
    measures: Sequence[str],
    fetch: Optional[Callable[[str], bytes]] = None,
    cache_dir: Optional[str] = None,
    session: Any = None,
) -> Dict[str, Any]:
    """Raw PLACES rows for ``states`` and ``measures`` (cached), with provenance.

    Returns {"rows": DataFrame (the CSV columns), "files": [{url, path, sha256, size_bytes,
    downloaded_at}], "rows_updated_at": int or None, "dataset": id}. ``fetch(url) -> bytes`` replaces the
    HTTP client (tests). Pages of PAGE_SIZE rows are requested until a short page.
    """
    ds = dataset_id("places", release, level)
    measures = sorted({str(m).upper() for m in measures})
    unknown = [m for m in measures if m not in SOURCES["places"]["measures"]]
    if unknown:
        raise ValueError(f"unknown PLACES measures {unknown}")
    states = sorted({str(s).zfill(2) for s in states})
    get = fetch or (lambda u: _http_get(u, session=session))
    key = _sha256(json.dumps([states, measures]).encode())[:12]
    folder = os.path.join(cache_dir or health_cache_dir(), "places", str(release), level)
    meta_url = f"https://data.cdc.gov/api/views/{ds}.json"
    meta_path = os.path.join(folder, f"{ds}_{key}_metadata.json")
    files: List[Dict[str, Any]] = []
    frames: List[pd.DataFrame] = []
    fresh = False
    offset = 0
    while True:
        url = places_query_url(ds, states, measures, offset, PAGE_SIZE)
        path = os.path.join(folder, f"{ds}_{key}_{offset}.csv")
        raw = _read_cached(path)  # None when absent or not matching its sidecar SHA-256 (then fetched again)
        if raw is None:
            if _offline():
                raise HealthSourceError(f"{path} not cached and CENSUS_HEALTH_OFFLINE is set")
            raw = get(url)
            if raw[:200].lstrip().lower().startswith((b"<!doctype", b"<html")):
                raise HealthSourceError(f"{url} returned an HTML page, not CSV; nothing cached")
            _write_cached(path, raw, url, "text/csv")
            fresh = True
        side = _side(path)
        files.append({k: side.get(k) for k in ("source_url", "sha256", "size_bytes", "downloaded_at")} |
                     {"path": path})
        try:
            page = pd.read_csv(io.BytesIO(raw), dtype=str)
        except Exception as exc:  # noqa: BLE001
            raise HealthSourceError(f"{url}: not a CSV ({exc})") from exc
        frames.append(page)
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    rows = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    # the revision stamp belongs to this download: fetched with fresh pages, read from the cache only
    # when every page came from it (a stamp that cannot be fetched is recorded as unknown)
    raw_meta = None if fresh else _read_cached(meta_path)
    if raw_meta is None:
        for p in (meta_path, _sidecar_path(meta_path)):
            if os.path.exists(p):
                os.remove(p)
        if not _offline():
            try:
                raw_meta = get(meta_url)
                json.loads(raw_meta)
                _write_cached(meta_path, raw_meta, meta_url, "application/json")
            except Exception:  # noqa: BLE001 - the revision stamp is provenance only
                raw_meta = None
    updated = None
    if raw_meta is not None:
        try:
            updated = json.loads(raw_meta).get("rowsUpdatedAt")
        except ValueError:
            updated = None
    return {"rows": rows, "files": files, "rows_updated_at": updated, "dataset": ds}


def parse_places(rows: pd.DataFrame, level: str, measure_names: Mapping[str, str]) -> pd.DataFrame:
    """Wide frame GEOID, <name>, <name>_se, <name>_ci_lower, <name>_ci_upper for ``measure_names``
    ({measure id: frame name}). Raises on malformed or duplicated rows."""
    need = ("locationid", "measureid", "data_value", "low_confidence_limit", "high_confidence_limit",
            "data_value_type")
    missing = [c for c in need if c not in rows.columns]
    if missing:
        raise HealthSourceError(f"PLACES rows lack columns {missing}")
    width = {"tract": 11, "county": 5}[level]
    want = SOURCES["places"]["value_type"][level]
    sub = rows[rows["measureid"].str.upper().isin(list(measure_names))].copy()
    sub = sub[sub["data_value_type"] == want]
    geo = sub["locationid"].astype(str).str.strip()
    bad = ~geo.str.fullmatch(rf"\d{{{width}}}")
    if bad.any():
        raise HealthSourceError(f"PLACES rows with malformed {level} ids: {sorted(geo[bad].unique())[:5]}")
    sub["GEOID"] = geo
    dup = sub.duplicated(["GEOID", "measureid"])
    if dup.any():
        raise HealthSourceError(f"duplicated PLACES rows for {int(dup.sum())} GEOID-measure pairs")
    out = pd.DataFrame({"GEOID": sorted(sub["GEOID"].unique())})
    for mid, name in measure_names.items():
        part = sub[sub["measureid"].str.upper() == mid].set_index("GEOID")
        vals = {}
        for col, src in (("", "data_value"), ("_ci_lower", "low_confidence_limit"),
                         ("_ci_upper", "high_confidence_limit")):
            raw = part[src]
            num = pd.to_numeric(raw, errors="coerce")
            nonnum = raw.notna() & raw.astype(str).str.strip().ne("") & num.isna()
            if nonnum.any():
                raise HealthSourceError(f"PLACES {mid}: non-numeric {src} values")
            vals[col] = num
        df = pd.DataFrame({name: vals[""], f"{name}_ci_lower": vals["_ci_lower"],
                           f"{name}_ci_upper": vals["_ci_upper"]})
        df[f"{name}_se"] = (df[f"{name}_ci_upper"] - df[f"{name}_ci_lower"]) / (2 * Z95)
        out = out.merge(df.reset_index(), on="GEOID", how="left")
    return out


def load_external(
    entries: Sequence[Mapping[str, Any]],
    level: str,
    states: Sequence[str],
    fetch: Optional[Callable[[str], bytes]] = None,
    cache_dir: Optional[str] = None,
) -> "tuple[pd.DataFrame, List[Dict[str, Any]]]":
    """Fetch and parse a manifest's external entries; returns (wide frame on GEOID, provenance records)."""
    groups: Dict[tuple, Dict[str, str]] = {}
    for e in entries:
        groups.setdefault((e["source"], int(e["release"])), {})[str(e["measure"]).upper()] = str(e["name"])
    wide: Optional[pd.DataFrame] = None
    prov: List[Dict[str, Any]] = []
    for (source, release), names in groups.items():
        if source != "places":  # registry and validation keep this unreachable
            raise HealthSourceError(f"no connector for {source!r}")
        got = fetch_places(release, level, states, list(names), fetch=fetch, cache_dir=cache_dir)
        part = parse_places(got["rows"], level, names)
        info = SOURCES[source]
        prov.append({"source": source, "release": release, "level": level, "dataset": got["dataset"],
                     "measures": names, "files": got["files"], "rows_updated_at": got["rows_updated_at"],
                     "units": int(len(part)), "licence": info["licence"],
                     "uncertainty": info["uncertainty_text"], "model": info["model_text"],
                     "citation": info["citation"].format(release=release, dataset=got["dataset"])})
        wide = part if wide is None else wide.merge(part, on="GEOID", how="outer")
    return (wide if wide is not None else pd.DataFrame({"GEOID": []})), prov


def join_external(frame: pd.DataFrame, ext: pd.DataFrame, names: Sequence[str],
                  required: Sequence[str]) -> "tuple[pd.DataFrame, Dict[str, Any]]":
    """Left-join external columns to ``frame`` on GEOID; returns (frame, join record).

    ``required``: frame variables that define a complete ACS unit; the record's ``missing_share``
    is the share of complete units without an external value (any of ``names``)."""
    if "Year" in frame.columns and frame["Year"].nunique() > 1:
        raise HealthSourceError("external variables need a single-release frame (one row per GEOID)")
    cols = ["GEOID"] + [c for n in names for c in (n, f"{n}_se", f"{n}_ci_lower", f"{n}_ci_upper")
                        if c in ext.columns]
    clash = [c for c in cols[1:] if c in frame.columns]
    if clash:
        raise HealthSourceError(f"external columns already in the frame: {clash}")
    out = frame.merge(ext[cols], on="GEOID", how="left")
    req = [c for c in required if c in out.columns]
    complete = np.isfinite(out[req].to_numpy(float)).all(axis=1) if req else np.ones(len(out), bool)
    has = np.isfinite(out[list(names)].to_numpy(float)).all(axis=1)
    lacking = out.loc[complete & ~has, "GEOID"].astype(str).tolist()
    record = {"frame_units": int(len(out)), "complete_acs_units": int(complete.sum()),
              "matched_units": int((complete & has).sum()), "complete_units_without_external": len(lacking),
              "missing_share": float(len(lacking) / complete.sum()) if complete.sum() else float("nan"),
              "examples_without_external": lacking[:20],
              "source_units_outside_frame": int((~ext["GEOID"].isin(frame["GEOID"].astype(str))).sum())}
    return out, record
