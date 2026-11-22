# SPDX-License-Identifier: AGPL-3.0-or-later
"""Replication suite (Round 74, backlog N52): the published replications of Rounds 66-69 rerun through the engine's
own routes, compared with their original audits.

Specs live in ``docs/replications/<id>.json``. Each records the published target, the pre-set rule copied from its
Round 66-69 criterion, the original audit's result (``original``) and the tolerance fixed in PLAN_ROUND_74. They
are **replication reruns**, not new registered studies: the registered results stay those of Rounds 66-69. A rerun
that differs beyond tolerance does not change them; the difference is reported with its cause.

``run(id)`` returns ``{"id", "status", ...}`` with status ``agrees``, ``differs`` or ``skipped`` (data absent:
the owner's WONDER exports, a missing CHR file offline). WONDER data are never fetched automatically.
"""
import json
import os
import tempfile
import warnings
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SPEC_DIR = ROOT/"docs"/"replications"
IDS = ("chr_segregation", "state_gini", "nc_ice", "le_variance", "monnat_d")
SPEC_KEYS = {"id", "label", "replication", "study", "target", "published", "rule", "original", "engine_route",
             "data", "tolerance"}
TOLERANCE_KINDS = ("max_abs_vs_published", "each_within_original")


class Unavailable(RuntimeError):
    """Input data are absent (reported as skipped, never as a failure)."""


def load_spec(rid: str) -> Dict[str, Any]:
    if rid not in IDS:
        raise ValueError(f"unknown replication {rid!r}; one of {IDS}")
    return json.loads((SPEC_DIR/f"{rid}.json").read_text())


def validate_spec(spec: Dict[str, Any]) -> List[str]:
    errs = []
    missing = SPEC_KEYS-set(spec)
    if missing:
        errs.append(f"missing keys {sorted(missing)}")
    if spec.get("id") not in IDS:
        errs.append("id must be one of "+", ".join(IDS))
    if spec.get("label") != "replication rerun":
        errs.append('label must be "replication rerun" (not a new registered study)')
    tol = spec.get("tolerance") or {}
    if tol.get("kind") not in TOLERANCE_KINDS or not isinstance(tol.get("value"), (int, float)) or tol["value"] <= 0:
        errs.append(f"tolerance must be {{kind: one of {TOLERANCE_KINDS}, value > 0}}")
    if spec.get("data") not in ("public", "owner_wonder_exports"):
        errs.append("data must be public or owner_wonder_exports")
    orig = spec.get("original") or {}
    if not isinstance(orig.get("headline"), dict) or not orig.get("audit") or not orig.get("criterion_commit"):
        errs.append("original needs audit, criterion_commit and a headline dict")
    if not isinstance(spec.get("engine_route"), list) or not spec["engine_route"]:
        errs.append("engine_route must list the MCP calls")
    return errs


def compare(spec: Dict[str, Any], headline: Dict[str, float], published: Optional[Dict[str, float]] = None
            ) -> Dict[str, Any]:
    """Compare a rerun headline with the original audit (or, for max_abs_vs_published, with the published values)."""
    tol = spec["tolerance"]
    ref = (published if tol["kind"] == "max_abs_vs_published" else spec["original"]["headline"])
    if ref is None:
        raise ValueError("max_abs_vs_published needs the published values")
    keys = sorted(set(ref) | set(headline))
    absent = [k for k in keys if k not in headline or k not in ref]
    diffs = {k: float(headline[k]-ref[k]) for k in keys if k in headline and k in ref}
    worst = max((abs(v) for v in diffs.values()), default=float("nan"))
    agrees = not absent and bool(diffs) and all(abs(v) <= tol["value"] for v in diffs.values())
    out = dict(status="agrees" if agrees else "differs", max_abs_difference=worst, compared=len(diffs),
               tolerance=tol, missing=absent[:20], n_missing=len(absent))
    if not agrees:
        out["beyond_tolerance"] = {k: v for k, v in sorted(diffs.items(), key=lambda kv: -abs(kv[1]))
                                   if abs(v) > tol["value"]}
        out["beyond_tolerance"] = dict(list(out["beyond_tolerance"].items())[:20])
    return out


def _client():
    from .workflows import _client as c
    return c()


def _acs(client, year, state, table, geo="tract"):
    rows = client.fetch(year, state, table, geo_level=geo)
    if rows is None:
        raise Unavailable(f"{table} {state} {year}: {client.last_error}")
    d = pd.DataFrame(rows[1:], columns=rows[0])
    d["GEOID"] = d.state+d.county+d.tract if geo == "tract" else d.state+(d.county if geo == "county" else "")
    return d


# ---- A: CHR 2025 county Black/White dissimilarity ---------------------------------------------------------------

def run_chr_segregation(spec, client=None) -> Dict[str, Any]:
    from .context_sources import fetch_chr_additional
    from .segregation import segregation_indices
    p = spec["frame"]
    c = client or _client()
    try:
        pub, rec = fetch_chr_additional("v141", 2025)
    except Exception as exc:  # noqa: BLE001 - offline / missing file
        raise Unavailable(f"CHR v141 file: {type(exc).__name__}: {exc}")
    tr = []
    for s in p["states"]:
        a, w = (_acs(c, p["year"], s, t) for t in ("B11002A", "B11002B"))
        m = a[["GEOID", "B11002A_001E"]].merge(w[["GEOID", "B11002B_001E"]], on="GEOID")
        tr.append(m.rename(columns={"B11002A_001E": "white", "B11002B_001E": "black"}))
    tr = pd.concat(tr)
    tr[["white", "black"]] = tr[["white", "black"]].apply(pd.to_numeric, errors="coerce")
    tr["county"] = tr.GEOID.str[:5]
    skip = set(p["excluded_counties"])
    ours = {}
    for cty, g in tr.groupby("county"):
        if cty[:2] in p["excluded_states"] or cty in skip or g.black.sum() < p["min_black"]:
            continue
        if g[["white", "black"]].isna().any().any():
            continue                                    # CHR: a missing tract makes the county missing
        d = segregation_indices(g[["black", "white"]].to_numpy(float))["dissimilarity"]*100
        if d > 0:
            ours[cty] = d
    pub = pub.dropna()
    pub = pub[(~pub.index.str[:2].isin(p["excluded_states"])) & ~pub.index.isin(skip)]
    out = compare(spec, ours, published=pub.to_dict())
    out.update(counties=len(ours), chr_counties=int(len(pub)), chr_file_sha256=rec.get("sha256"))
    orig = spec["original"]["headline_counts"]
    out["counts_match_original"] = bool(out["compared"] == orig["counties_compared"] and out["n_missing"] == 0)
    if not out["counts_match_original"] and out["status"] == "agrees":
        out["status"] = "differs"
    return out


# ---- B: Census state Gini (B19083) from PUMS --------------------------------------------------------------------

def run_state_gini(spec, client=None) -> Dict[str, Any]:
    from . import workflows_microdata as wm
    p = spec["frame"]
    head, rows = {}, []
    for s in p["states"]:
        r = wm.test_association(s, p["year"], "inequality", var=p["var"], where=p["where"], weight="housing")
        if not r.get("success"):
            raise Unavailable(f"PUMS {s}: {r.get('error') or r.get('summary')}")
        g = next(t for t in r["table"] if t["measure"] == "gini")
        head[s] = float(g["estimate"])
        rows.append(dict(state=s, gini=head[s], lower=float(g["lower"]), upper=float(g["upper"]),
                         validated=bool(g["validated"])))
    out = compare(spec, head)
    out["states"] = rows
    return out


# ---- C: NC tract life expectancy and ICE (Mitchell et al. 2022) -------------------------------------------------

def nc_ice_frame(spec, client=None) -> pd.DataFrame:
    from . import health_sources
    p = spec["frame"]
    c = client or _client()
    t = {k: _acs(c, p["year"], p["state"], k).set_index("GEOID") for k in ("B19001", "B19001B", "B19001H", "B03002")}
    num = lambda d, tab, ls: sum(pd.to_numeric(d[f"{tab}_{i:03d}E"]) for i in ls)  # noqa: E731
    hi, lo = range(14, 18), range(2, 6)
    f = pd.DataFrame(index=t["B19001"].index)
    f["hh"] = pd.to_numeric(t["B19001"].B19001_001E); f["pop"] = pd.to_numeric(t["B03002"].B03002_001E)
    f["ice_income"] = (num(t["B19001"], "B19001", hi)-num(t["B19001"], "B19001", lo))/f.hh
    f["ice_race"] = (pd.to_numeric(t["B03002"].B03002_003E)-pd.to_numeric(t["B03002"].B03002_004E))/f["pop"]
    f["ice_income_race"] = (num(t["B19001H"], "B19001H", hi)-num(t["B19001B"], "B19001B", lo))/f.hh
    try:
        le, _ = health_sources.parse_usaleep(health_sources.fetch_usaleep([p["state"]])["rows"], "le",
                                             include_predicted=True)
    except Exception as exc:  # noqa: BLE001
        raise Unavailable(f"USALEEP: {type(exc).__name__}: {exc}")
    f = f.join(le.set_index("GEOID")[["le"]], how="inner")
    f = f[(f["pop"] > 0) & (f.hh > 0) & f["le"].notna()].copy()
    f["lnle"] = np.log(f["le"].astype(float))
    f["Year"] = p["year"]          # the release sets the boundary vintage for representative points
    f.index.name = "GEOID"
    return f.reset_index()


def run_nc_ice(spec, client=None) -> Dict[str, Any]:
    from . import boundaries, spatial
    from . import workflows_geo as wg, workflows_inference as wi
    p = spec["frame"]
    f = nc_ice_frame(spec, client)
    gdf = boundaries.get_boundaries("tract", p["year"], state=p["state"])
    gdf = gdf[gdf.GEOID.astype(str).isin(set(f.GEOID))]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        islands = {str(i) for i in getattr(spatial.spatial_weights(gdf, "queen"), "islands", [])}
    head, detail = {}, {}
    with tempfile.TemporaryDirectory() as tmp:
        for var in p["ice"]:
            d = f[["GEOID", "Year", "lnle", var]].dropna()
            path = os.path.join(tmp, f"{var}.csv"); d.to_csv(path, index=False)
            ols = wi.fit_model(path, f"lnle ~ {var}")
            if not ols.get("success"):
                raise RuntimeError(f"fit_model {var}: {ols}")
            row = next(r for r in ols["coefficients"] if r["term"] == var)
            sc = wi.fit_model(path, f"lnle ~ {var}", spatial="scpc")
            srow = next((r for r in sc.get("table", []) if r["term"] == var), {}) if sc.get("success") else {}
            dd = d[~d.GEOID.isin(islands)]
            spath = os.path.join(tmp, f"{var}_sem.csv"); dd.to_csv(spath, index=False)
            sem = wg.spatial_regression(spath, f"lnle ~ {var}", "tract", p["year"], model="error")
            if not sem.get("success"):
                raise RuntimeError(f"spatial_regression {var}: {sem}")
            srow2 = next(r for r in sem["coefficients"] if r["term"] == var)
            head[f"{var}/ols"] = float(row["estimate"]); head[f"{var}/spatial_error"] = float(srow2["estimate"])
            detail[var] = dict(ols=float(row["estimate"]), spatial_error=float(srow2["estimate"]),
                               scpc=dict(lower=srow.get("lower"), upper=srow.get("upper"),
                                         validated=sc.get("validated"), rho_bar=sc.get("rho_bar")))
    out = compare(spec, head)
    out.update(tracts=int(len(f)), islands=len(islands), slopes=detail)
    return out


# ---- E and D (need Round 73) -------------------------------------------------------------------------------------

RUNNERS: Dict[str, Callable[..., Dict[str, Any]]] = {
    "chr_segregation": run_chr_segregation, "state_gini": run_state_gini, "nc_ice": run_nc_ice,
}


def run(rid: str, client=None) -> Dict[str, Any]:
    spec = load_spec(rid)
    errs = validate_spec(spec)
    if errs:
        raise ValueError(f"{rid}: "+"; ".join(errs))
    try:
        out = RUNNERS[rid](spec, client)
    except Unavailable as exc:
        return dict(id=rid, status="skipped", reason=str(exc))
    return dict(id=rid, **out)
