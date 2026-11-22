# SPDX-License-Identifier: AGPL-3.0-or-later
"""Context covariate sources (Round 72, backlog N50).

County-level covariates the replications fetched by hand: County Business Patterns establishment counts, ERS county
economic types, ERS rural-urban codes and metro status, and County Health Rankings additional measures. These are
**covariates**, never health outcomes (the circularity rule governs outcomes only); an ACS-derived CHR measure is
refused as an outcome by the existing CHR rule and allowed here as a covariate or a replication comparison.

Every downloaded file is cached with a JSON sidecar (URL, SHA-256, size, time); results carry that provenance.

Entry format (``build_analysis_frame(context=[...])`` and manifest ``"context": [...]``)::

    {"source": "cbp", "name": "religious", "year": 2012, "naics": ["813110"], "per": 10000, "per_column": "pop"}
    {"source": "ers_typology", "name": "econ_type", "field": "Type_2015_Update"}
    {"source": "ers_rucc", "name": "rucc", "field": "RuralUrbanContinuumCode2013"}   # or "Metro2013"
    {"source": "chr_additional", "name": "segregation_bw", "measure": "v141", "release": 2025}
"""
import hashlib
import io
import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

import pandas as pd

ERS_URL = "https://gisportal.ers.usda.gov/server/rest/services/Rural_Atlas_Data/County_Classifications/MapServer/5/query"
ERS_FIELDS = ("FIPSTXT", "Type_2015_Update", "Type_2015_Farming_NO", "Type_2015_Manufacturing_NO", "Type_2015_Mining_NO",
              "Type_2015_Government_NO", "Type_2015_Recreation_NO", "Low_Education_2015_update",
              "Low_Employment_2015_update", "Population_loss_2015_update", "Retirement_Destination_2015_Update",
              "RuralUrbanContinuumCode2013", "UrbanInfluenceCode2013", "Metro2013", "Nonmetro2013", "Micropolitan2013")
CHR_REPO = "https://raw.githubusercontent.com/countyhealthrankings/county_health_measure_calculations"
CHR_COMMITS = {2025: "a516395d02b1aa6ff10da092267525a215cc3ff4"}   # pinned in Round 66
CBP_YEARS = tuple(range(2012, 2023))
USER_AGENT = "census-research-engine"

CONTEXT_SOURCES: Dict[str, Dict[str, Any]] = {
    "cbp": {"title": "County Business Patterns (establishment counts by NAICS)", "publisher": "U.S. Census Bureau",
            "licence": "Public domain (U.S. Government work)", "access": "Census API (cbp dataset; your API key)",
            "years": list(CBP_YEARS), "level": "county", "required": ("name", "year", "naics"),
            "derived_from": "business register (not the ACS)"},
    "ers_typology": {"title": "ERS county typology codes, 2015 edition (economic types)",
                     "publisher": "USDA Economic Research Service", "licence": "CC0 (data.gov)",
                     "access": "ERS GIS portal (County_Classifications MapServer)", "years": [2015], "level": "county",
                     "required": ("name", "field"), "derived_from": "BEA/BLS earnings and employment, 2010-12",
                     "fields": [f for f in ERS_FIELDS if f.startswith("Type_2015") or f.endswith(("_2015_update", "_2015_Update"))],
                     "codes": {0: "nonspecialized", 1: "farming", 2: "mining", 3: "manufacturing",
                               4: "federal/state government", 5: "recreation"}},
    "ers_rucc": {"title": "ERS rural-urban continuum and urban influence codes; 2013 metro status",
                 "publisher": "USDA Economic Research Service", "licence": "CC0 (data.gov)",
                 "access": "ERS GIS portal (County_Classifications MapServer)", "years": [2013], "level": "county",
                 "required": ("name", "field"), "derived_from": "OMB 2013 delineation and 2010 Census population",
                 "fields": ["RuralUrbanContinuumCode2013", "UrbanInfluenceCode2013", "Metro2013", "Nonmetro2013",
                            "Micropolitan2013"]},
    "chr_additional": {"title": "County Health Rankings additional measures (CHR calculation repository)",
                       "publisher": "University of Wisconsin Population Health Institute",
                       "licence": "Non-commercial research use", "access": "GitHub raw file at a pinned commit",
                       "years": sorted(CHR_COMMITS), "level": "county", "required": ("name", "measure", "release"),
                       "derived_from": "measure-specific (v141: ACS 2019-2023 B11002 tracts)"},
}


def context_cache_dir() -> Path:
    from .health_sources import health_cache_dir
    return Path(os.getenv("CENSUS_CONTEXT_DIR", os.path.join(health_cache_dir(), "context")))


def list_context_sources() -> Dict[str, Any]:
    return {k: {kk: v for kk, v in s.items() if kk != "required"} for k, s in CONTEXT_SOURCES.items()}


def validate_context(entries: Any, names: Sequence[str] = ()) -> List[str]:
    """Errors for a manifest/frame ``context`` list (empty when valid)."""
    if entries is None:
        return []
    if not isinstance(entries, list):
        return ["context must be a list of objects"]
    errors, seen = [], set(names)
    for i, e in enumerate(entries):
        p = f"context[{i}]: "
        if not isinstance(e, Mapping) or e.get("source") not in CONTEXT_SOURCES:
            errors.append(p+f"source must be one of {sorted(CONTEXT_SOURCES)}"); continue
        info = CONTEXT_SOURCES[e["source"]]
        miss = [k for k in info["required"] if e.get(k) in (None, "", [])]
        if miss:
            errors.append(p+f"needs {miss}")
        n = e.get("name")
        if not isinstance(n, str) or not n.isidentifier():
            errors.append(p+"name must be a Python identifier")
        elif n in seen:
            errors.append(p+f"name {n!r} duplicates another variable")
        seen.add(n)
        if e["source"] == "cbp":
            if e.get("year") not in CBP_YEARS:
                errors.append(p+f"cbp year must be in {CBP_YEARS[0]}-{CBP_YEARS[-1]}")
            if not isinstance(e.get("naics"), list) or not all(isinstance(x, str) and x.isdigit() for x in e.get("naics") or []):
                errors.append(p+"naics must be a list of NAICS code strings")
            if e.get("per") is not None and not e.get("per_column"):
                errors.append(p+"per needs per_column (the population column of the frame)")
        if e["source"] in ("ers_typology", "ers_rucc") and e.get("field") not in info["fields"]:
            errors.append(p+f"field must be one of {info['fields']}")
        if e["source"] == "chr_additional" and e.get("release") not in CHR_COMMITS:
            errors.append(p+f"chr_additional release must be one of {sorted(CHR_COMMITS)}")
    return errors


def _sidecar(path: Path, url: str, raw: bytes) -> Dict[str, Any]:
    rec = {"source_url": url, "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw),
           "downloaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    path.with_name(path.name+".json").write_text(json.dumps(rec, indent=1)+"\n")
    return rec


def _cached(path: Path, url: str, getter: Callable[[], bytes]) -> Tuple[bytes, Dict[str, Any]]:
    side = path.with_name(path.name+".json")
    if path.exists() and side.exists():
        raw = path.read_bytes(); rec = json.loads(side.read_text())
        if hashlib.sha256(raw).hexdigest() == rec.get("sha256"):
            return raw, rec
    from .health_sources import _offline
    if _offline():
        raise FileNotFoundError(f"{path} not cached and CENSUS_HEALTH_OFFLINE is set")
    raw = getter()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return raw, _sidecar(path, url, raw)


def fetch_ers(session: Any = None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """All ERS county classification fields (one cached JSON); GEOID-indexed."""
    import requests
    get = (session or requests).get

    def pull() -> bytes:
        rows, off = [], 0
        while True:
            r = get(ERS_URL, params={"where": "1=1", "outFields": ",".join(ERS_FIELDS), "returnGeometry": "false",
                                     "f": "json", "resultOffset": off, "resultRecordCount": 1000},
                    headers={"User-Agent": USER_AGENT}, timeout=120).json()
            feats = r.get("features", [])
            rows += [f["attributes"] for f in feats]
            if not feats or not r.get("exceededTransferLimit"):
                break
            off += len(feats)
        if not rows:
            raise ValueError(f"ERS service returned no rows ({str(r.get('error', ''))[:200]})")
        return json.dumps(sorted(rows, key=lambda x: str(x["FIPSTXT"])), sort_keys=True).encode()

    raw, rec = _cached(context_cache_dir()/"ers"/"county_classifications.json", ERS_URL, pull)
    d = pd.DataFrame(json.loads(raw))
    d.index = d.FIPSTXT.astype(str).str.zfill(5)
    return d, rec


def fetch_chr_additional(measure: str, release: int, fetch: Optional[Callable[[str], bytes]] = None
                         ) -> Tuple[pd.Series, Dict[str, Any]]:
    import requests
    url = f"{CHR_REPO}/{CHR_COMMITS[release]}/measure_datasets/{measure}_r{release}.csv"
    get = fetch or (lambda u: requests.get(u, headers={"User-Agent": USER_AGENT}, timeout=120).content)
    raw, rec = _cached(context_cache_dir()/"chr"/f"{measure}_r{release}.csv", url, lambda: get(url))
    d = pd.read_csv(io.BytesIO(raw), dtype={"statecode": str, "countycode": str, "fipscode": str})
    col = f"{measure}_rawvalue"
    if col not in d:
        raise ValueError(f"{url}: no column {col}")
    d = d[d.countycode != "000"]
    return pd.to_numeric(d.set_index(d.fipscode.str.zfill(5))[col], errors="coerce"), rec


def fetch_cbp(year: int, naics: Sequence[str], client: Any = None) -> Tuple[pd.Series, Dict[str, Any]]:
    """County establishment counts summed over ``naics`` (Census API, cached by the engine's query cache)."""
    from .workflows import _client
    c = client or _client()
    ep = f"https://api.census.gov/data/{year}/cbp"
    code_var = "NAICS2012" if year < 2017 else "NAICS2017"
    total: Optional[pd.Series] = None
    for n in naics:
        rows = c._get_json(ep, {"get": f"ESTAB,{code_var}", "for": "county:*", "in": "state:*", code_var: n,
                                "key": c.api_key})
        if rows is None:
            raise ValueError(f"CBP {year} {n}: {c.last_error}")
        d = pd.DataFrame(rows[1:], columns=rows[0])
        s = pd.to_numeric(d.ESTAB).groupby((d.state+d.county).values).sum()
        total = s if total is None else total.add(s, fill_value=0)
    rec = {"source_url": ep, "naics": list(naics), "year": year, "query_cache": True}
    return total, rec


def context_frame(entries: Sequence[Mapping[str, Any]], frame: Optional[pd.DataFrame] = None, client: Any = None,
                  fetch: Optional[Callable[[str], bytes]] = None) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    """County-indexed frame (index = 5-digit GEOID) with one column per entry, and provenance records.

    ``per``/``per_column`` (CBP) divide by a population column of ``frame`` (county rows) and multiply by ``per``.
    """
    out = pd.DataFrame()
    prov: List[Dict[str, Any]] = []
    ers = None
    for e in entries:
        src = e["source"]
        if src == "cbp":
            s, rec = fetch_cbp(int(e["year"]), e["naics"], client)
            if e.get("per") is not None:
                pop = _county_values(frame, e["per_column"])
                s = s.reindex(pop.index).fillna(0)/pop*float(e["per"])
        elif src in ("ers_typology", "ers_rucc"):
            if ers is None:
                ers = fetch_ers()
            s, rec = pd.to_numeric(ers[0][e["field"]], errors="coerce"), ers[1]
        else:
            s, rec = fetch_chr_additional(e["measure"], int(e["release"]), fetch)
        out = out.join(s.rename(e["name"]), how="outer") if not out.empty else s.rename(e["name"]).to_frame()
        prov.append({"entry": dict(e), "source": CONTEXT_SOURCES[src]["title"], **rec})
    return out, prov


def _county_values(frame: Optional[pd.DataFrame], column: str) -> pd.Series:
    if frame is None or column not in frame:
        raise ValueError(f"per_column {column!r} is not a column of the frame")
    f = frame.assign(_c=frame.GEOID.astype(str).str[:5])
    if f.GEOID.astype(str).str.len().eq(5).all():
        return pd.to_numeric(f.set_index("_c")[column])
    return pd.to_numeric(f.groupby("_c")[column].sum())     # tract frames: county population from its tracts


def join_context(frame: pd.DataFrame, ctx: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Join county context onto a county or tract frame (tracts take their county's value)."""
    key = frame.GEOID.astype(str).str[:5]
    joined = frame.copy()
    for c in ctx.columns:
        joined[c] = key.map(ctx[c]).to_numpy()
    level = "county" if frame.GEOID.astype(str).str.len().eq(5).all() else "tract (county values)"
    missing = {c: float(joined[c].isna().mean()) for c in ctx.columns}
    return joined, {"level": level, "missing_share": missing}
