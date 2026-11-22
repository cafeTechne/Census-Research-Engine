# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 92: Population Estimates, LEHD LODES jobs and ACS county-to-county migration flows (backlog N68).

Walker, *Analyzing US Census Data* (2023), chapters 4 and 11; mapping in
``docs/literature/walker_analyzing_us_census_data.md``.

- **Population Estimates Program (PEP)**, U.S. Census Bureau: July 1 county and state populations by vintage, and
  county population by age group and sex. Each vintage revises earlier years, so every value carries its vintage and
  vintages are never mixed. Files: ``www2.census.gov/programs-surveys/popest/datasets`` (vintages 2019 and 2024).
  Estimates are not sample-based: there is no MOE. They are the denominators for annual rates (joinpoint, MSMs,
  interrupted series), never outcomes.
- **LEHD Origin-Destination Employment Statistics (LODES8)**: jobs by workplace (WAC) and residence (RAC) block, and
  origin-destination pairs (OD), aggregated here to tracts or counties. LODES protects confidentiality by noise
  infusion and synthetic data, not by sampling: there is no MOE, and small-area values are perturbed.
- **ACS county-to-county migration flows** (Census API ``acs/flows``): movers in, out and net between county pairs
  over a five-year release, with MOEs. County-to-county detail exists for releases up to 2016-2020; later releases
  publish state-level partners only, so they are refused here.

All downloads are cached with a SHA-256 sidecar (``context_sources._cached``) and use a generic User-Agent.
"""
import gzip
import io
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

from .context_sources import USER_AGENT, _cached, context_cache_dir

POPEST = "https://www2.census.gov/programs-surveys/popest/datasets"
PEP_VINTAGES = {2019: {"span": "2010-2019", "years": tuple(range(2010, 2020)), "encoding": "latin-1",
                       "agesex_year_code": {y: y-2007 for y in range(2010, 2020)}},   # 3 = 7/1/2010 ... 12 = 2019
                2024: {"span": "2020-2024", "years": tuple(range(2020, 2025)), "encoding": "latin-1",
                       "agesex_year_code": {y: y-2018 for y in range(2020, 2025)}}}   # 2 = 7/1/2020 ... 6 = 2024
LODES_BASE = "https://lehd.ces.census.gov/data/lodes/LODES8"
LODES_YEARS = tuple(range(2002, 2023))
LODES_KINDS = ("wac", "rac", "od")
LODES_JOB_TYPES = {"JT00": "all jobs", "JT01": "primary jobs", "JT02": "all private jobs",
                   "JT03": "private primary jobs", "JT04": "all federal jobs", "JT05": "federal primary jobs"}
STATE_ABBR = {"01": "al", "02": "ak", "04": "az", "05": "ar", "06": "ca", "08": "co", "09": "ct", "10": "de",
              "11": "dc", "12": "fl", "13": "ga", "15": "hi", "16": "id", "17": "il", "18": "in", "19": "ia",
              "20": "ks", "21": "ky", "22": "la", "23": "me", "24": "md", "25": "ma", "26": "mi", "27": "mn",
              "28": "ms", "29": "mo", "30": "mt", "31": "ne", "32": "nv", "33": "nh", "34": "nj", "35": "nm",
              "36": "ny", "37": "nc", "38": "nd", "39": "oh", "40": "ok", "41": "or", "42": "pa", "44": "ri",
              "45": "sc", "46": "sd", "47": "tn", "48": "tx", "49": "ut", "50": "vt", "51": "va", "53": "wa",
              "54": "wv", "55": "wi", "56": "wy"}
FLOWS_LAST_COUNTY_YEAR = 2020
NOTE_PEP = ("Census Population Estimates, vintage {v}: modelled from the decennial base with births, deaths and "
            "migration; no MOE (not a sample). Later vintages revise these values; do not mix vintages.")
NOTE_LODES = ("LEHD LODES8 ({kind}, {jt}, {year}): administrative records with noise infusion; no MOE, and "
              "small-area values are perturbed for confidentiality.")


def _get(url: str) -> bytes:
    import requests
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=300)
    r.raise_for_status()
    return r.content


def _vintage(v: int) -> Dict[str, Any]:
    if v not in PEP_VINTAGES:
        raise ValueError(f"PEP vintage must be one of {sorted(PEP_VINTAGES)}")
    return PEP_VINTAGES[v]


def pep_totals(vintage: int = 2024, fetch=None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """State and county July 1 populations (long: GEOID, level, year, population, vintage)."""
    info = _vintage(vintage)
    url = f"{POPEST}/{info['span']}/counties/totals/co-est{vintage}-alldata.csv"
    raw, rec = _cached(context_cache_dir()/"pep"/f"co-est{vintage}-alldata.csv", url, lambda: (fetch or _get)(url))
    d = pd.read_csv(io.BytesIO(raw), dtype={"SUMLEV": str, "STATE": str, "COUNTY": str}, encoding=info["encoding"])
    d["GEOID"] = np.where(d.SUMLEV == "040", d.STATE.str.zfill(2), d.STATE.str.zfill(2)+d.COUNTY.str.zfill(3))
    d["level"] = np.where(d.SUMLEV == "040", "state", "county")
    long = d.melt(id_vars=["GEOID", "level"], value_vars=[f"POPESTIMATE{y}" for y in info["years"]],
                  var_name="year", value_name="population")
    long["year"] = long.year.str[-4:].astype(int); long["vintage"] = vintage
    return long.sort_values(["GEOID", "year"]).reset_index(drop=True), dict(rec, note=NOTE_PEP.format(v=vintage))


def pep_age_sex(state: str, vintage: int = 2024, fetch=None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """County population by age group and sex for one state (wide columns as published: POPESTIMATE, UNDER5_TOT,
    AGE65PLUS_FEM, ...), with ``year`` decoded from the file's YEAR code."""
    info = _vintage(vintage)
    st = str(state).zfill(2)
    url = f"{POPEST}/{info['span']}/counties/asrh/cc-est{vintage}-agesex-{st}.csv"
    raw, rec = _cached(context_cache_dir()/"pep"/f"cc-est{vintage}-agesex-{st}.csv", url, lambda: (fetch or _get)(url))
    d = pd.read_csv(io.BytesIO(raw), dtype={"STATE": str, "COUNTY": str, "SUMLEV": str}, encoding=info["encoding"])
    code = {c: y for y, c in info["agesex_year_code"].items()}
    d = d[d.YEAR.isin(list(code))].copy()
    d["year"] = d.YEAR.map(code); d["GEOID"] = d.STATE.str.zfill(2)+d.COUNTY.str.zfill(3); d["vintage"] = vintage
    return d.drop(columns=["YEAR"]).reset_index(drop=True), dict(rec, note=NOTE_PEP.format(v=vintage))


def lodes(state: str, year: int, kind: str = "wac", level: str = "county", job_type: str = "JT00",
          segment: str = "S000", fetch=None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """LODES8 jobs aggregated to ``level`` ("block", "tract" or "county").

    wac/rac: one row per area with C000 (total jobs) and the published breakdowns (CA01-03 age, CE01-03 earnings,
    CNS01-20 sectors, ...). od: workplace-residence pairs with S000 (jobs) and breakdowns, aggregated at both ends
    (main file: both ends in the state)."""
    st = str(state).zfill(2)
    if st not in STATE_ABBR:
        raise ValueError(f"unknown state FIPS {state!r}")
    if kind not in LODES_KINDS:
        raise ValueError(f"kind must be one of {LODES_KINDS}")
    if job_type not in LODES_JOB_TYPES:
        raise ValueError(f"job_type must be one of {sorted(LODES_JOB_TYPES)}")
    if int(year) not in LODES_YEARS:
        raise ValueError(f"LODES8 years are {LODES_YEARS[0]}-{LODES_YEARS[-1]} (coverage varies by state)")
    if level not in ("block", "tract", "county"):
        raise ValueError("level must be 'block', 'tract' or 'county'")
    ab = STATE_ABBR[st]
    name = (f"{ab}_od_main_{job_type}_{year}.csv.gz" if kind == "od" else f"{ab}_{kind}_{segment}_{job_type}_{year}.csv.gz")
    url = f"{LODES_BASE}/{ab}/{kind}/{name}"
    raw, rec = _cached(context_cache_dir()/"lodes"/name, url, lambda: (fetch or _get)(url))
    geo = {"wac": ["w_geocode"], "rac": ["h_geocode"], "od": ["w_geocode", "h_geocode"]}[kind]
    d = pd.read_csv(io.BytesIO(gzip.decompress(raw)), dtype={g: str for g in geo})
    d = d.drop(columns=[c for c in ("createdate",) if c in d])
    n = {"block": 15, "tract": 11, "county": 5}[level]
    keys = []
    for g in geo:
        k = g.replace("_geocode", "_"+level)
        d[k] = d[g].str.zfill(15).str[:n]; keys.append(k)
    out = d.drop(columns=geo).groupby(keys, as_index=False).sum(numeric_only=True)
    note = NOTE_LODES.format(kind=kind.upper(), jt=LODES_JOB_TYPES[job_type], year=year)
    return out, dict(rec, note=note, level=level, job_type=job_type, segment=segment, version="LODES8")


def migration_flows(state: str, year: int = 2020, county: str = "*", client: Any = None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """ACS county-to-county flows for counties of ``state`` (``year`` = last year of the five-year release, 2010-2020):
    movers in, out and net with 90% MOEs; partner rows abroad have no out-flow (not measured)."""
    year = int(year)
    if year > FLOWS_LAST_COUNTY_YEAR:
        raise ValueError(f"ACS flows after the {FLOWS_LAST_COUNTY_YEAR-4}-{FLOWS_LAST_COUNTY_YEAR} release give state-level "
                         "partners only; use year <= 2020 for county-to-county flows")
    if year < 2010:
        raise ValueError("ACS county-to-county flows start with the 2006-2010 release (year=2010)")
    from .workflows import _client
    c = client or _client()
    ep = f"https://api.census.gov/data/{year}/acs/flows"
    rows = c._get_json(ep, {"get": "MOVEDIN,MOVEDIN_M,MOVEDOUT,MOVEDOUT_M,MOVEDNET,MOVEDNET_M,GEOID1,GEOID2,FULL2_NAME",
                            "for": f"county:{county}", "in": f"state:{str(state).zfill(2)}", "key": c.api_key})
    if rows is None:
        raise ValueError(f"ACS flows {year}: {c.last_error}")
    d = pd.DataFrame(rows[1:], columns=rows[0]).drop(columns=["state", "county"])
    for col in ("MOVEDIN", "MOVEDIN_M", "MOVEDOUT", "MOVEDOUT_M", "MOVEDNET", "MOVEDNET_M"):
        d[col] = pd.to_numeric(d[col], errors="coerce")
    d = d.rename(columns={"GEOID1": "GEOID", "GEOID2": "partner", "FULL2_NAME": "partner_name"})
    rec = {"source_url": ep, "year": year, "release": f"{year-4}-{year}", "query_cache": True,
           "note": "ACS county-to-county migration flows (five-year): MOEs are 90%; partner rows abroad have no "
                   "out-flow."}
    return d, rec


def net_migration(flows: pd.DataFrame) -> pd.DataFrame:
    """County totals of domestic and total in-, out- and net-flows with MOEs (root sum of squares, the ACS
    approximation for sums; out-flows abroad are not measured, so totals cover domestic out-flows only)."""
    dom = flows[flows.partner.notna() & (flows.partner.str.len() == 5)]
    g = flows.groupby("GEOID"); gd = dom.groupby("GEOID")
    rss = lambda s: float(np.sqrt(np.nansum(np.square(s))))  # noqa: E731
    return pd.DataFrame({
        "moved_in": g.MOVEDIN.sum(), "moved_in_moe": g.MOVEDIN_M.agg(rss),
        "moved_in_domestic": gd.MOVEDIN.sum(), "moved_in_domestic_moe": gd.MOVEDIN_M.agg(rss),
        "moved_out_domestic": gd.MOVEDOUT.sum(), "moved_out_domestic_moe": gd.MOVEDOUT_M.agg(rss),
        "net_domestic": gd.MOVEDNET.sum(), "net_domestic_moe": gd.MOVEDNET_M.agg(rss)}).reset_index()
