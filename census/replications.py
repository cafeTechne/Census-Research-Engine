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


# ---- E: shares of US life-expectancy variation (Boing et al. 2020) ----------------------------------------------

def run_le_variance(spec, client=None) -> Dict[str, Any]:
    from . import health_sources
    from . import workflows_microdata as wm
    p = spec["frame"]
    try:
        rows = health_sources.fetch_usaleep(p["states"])["rows"]
    except Exception as exc:  # noqa: BLE001
        raise Unavailable(f"USALEEP: {type(exc).__name__}: {exc}")
    le, _ = health_sources.parse_usaleep(rows, "le", include_predicted=True)
    d = le[le["le"].notna()].copy()
    d["e0"] = d["le"].astype(float); d["state"] = d.GEOID.str[:2]; d["county"] = d.GEOID.str[:5]
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "e0.parquet"); d[["GEOID", "e0", "state", "county"]].to_parquet(path, index=False)
        out = wm.multilevel_model(path, "e0 ~ 1", ["state", "county"], share_intervals=False)
    if not out.get("success"):
        raise RuntimeError(f"multilevel_model: {out}")
    s = out["shares"]
    head = {"tract": 100*s["bottom"], "county": 100*s["middle"], "state": 100*s["top"]}
    res = compare(spec, head)
    res.update(shares=head, tracts=out["n"], counties=out["n_middle"], top_units=out["n_top"])
    return res


# ---- D: Monnat 2018 Model 4 (county drug-related mortality; the owner's WONDER exports) ------------------------

def _label_lines(table, year, *must, exclude=()):
    import re
    from .metadata import table_variables
    meta, _ = table_variables(table, "acs5", year)
    out = sorted(code for code, m in meta.items() if code.endswith("E")
                 and all(re.search(x, m["label"]) for x in must) and not any(re.search(x, m["label"]) for x in exclude))
    if not out:
        raise ValueError(f"no {table} line matches {must}")
    return out


def monnat_frame(spec, client=None) -> pd.DataFrame:
    """ACS 2014 county covariates (Round 69's definitions), CBP and ERS context, WONDER deaths and expected deaths."""
    from .context_sources import context_frame
    from .vital_records import read_wonder_export
    from .wonder_reference import acs_band_populations, expected_counts
    p = spec["frame"]
    wdir = ROOT/p["wonder_dir"]
    county_tsv, nat_tsv = wdir/"county"/"drug_related.tsv", wdir/"national_age_sex"/"drug_related.tsv"
    if not (county_tsv.exists() and nat_tsv.exists()):
        raise Unavailable(f"the owner's WONDER exports are absent ({p['wonder_dir']}; docs/data/wonder_exports.md "
                          "Part G). WONDER is never fetched automatically.")
    c = client or _client()
    yr = p["acs_year"]
    T = {}
    for t in ("B17001", "B23001", "B18101", "B15002", "B19056", "B19057", "B19083", "B27001", "B25002", "B25070",
              "B12001", "B11003", "B07003", "B01001", "B21001", "B03002", "B01003"):
        T[t] = _acs(c, yr, "*", t, geo="county").set_index("GEOID")
    L = lambda t, *m, exclude=(): _label_lines(t, yr, *m, exclude=exclude)  # noqa: E731
    tot = lambda t, codes: sum(pd.to_numeric(T[t][k], errors="coerce") for k in codes)  # noqa: E731
    col = lambda t, k: pd.to_numeric(T[t][k], errors="coerce")  # noqa: E731
    f = pd.DataFrame(index=T["B01003"].index)
    age = r"(25 to 34|35 to 44|45 to 54) years$"
    f["pov2554"] = tot("B17001", L("B17001", "below poverty", age))/tot("B17001", L("B17001", r"(below|at or above) poverty", age))
    a23 = r"!!(25 to 29|30 to 34|35 to 44|45 to 54) years"
    unem = L("B23001", a23, r"Civilian!!Unemployed$")+L("B23001", a23, r"Not in labor force$")
    f["unemp_nilf2554"] = tot("B23001", unem)/(tot("B23001", L("B23001", a23+r"$"))-tot("B23001", L("B23001", a23, r"In Armed Forces$")))
    a18 = r"(18 to 34|35 to 64) years"
    f["disab1864"] = tot("B18101", L("B18101", a18, r"With a disability$"))/tot("B18101", L("B18101", a18+r"$"))
    ba = L("B15002", r"(Bachelor's degree|Master's degree|Professional school degree|Doctorate degree)$")
    f["lt4yr"] = 1-tot("B15002", ba)/col("B15002", "B15002_001E")
    f["ssi"] = col("B19056", "B19056_002E")/col("B19056", "B19056_001E")
    f["pubassist"] = col("B19057", "B19057_002E")/col("B19057", "B19057_001E")
    f["gini"] = col("B19083", "B19083_001E")
    a27 = r"(18 to 24|25 to 34|35 to 44|45 to 54|55 to 64) years"
    f["unins1864"] = tot("B27001", L("B27001", a27, r"No health insurance coverage$"))/tot("B27001", L("B27001", a27+r"$"))
    f["vacant"] = col("B25002", "B25002_003E")/col("B25002", "B25002_001E")
    r30 = L("B25070", r"(30.0 to 34.9|35.0 to 39.9|40.0 to 49.9|50.0 percent or more)")
    f["rent30"] = tot("B25070", r30)/(col("B25070", "B25070_001E")-tot("B25070", L("B25070", "Not computed")))
    f["sepdiv"] = tot("B12001", L("B12001", r"(Separated|Divorced)$"))/col("B12001", "B12001_001E")
    own = r"With own children (of the householder )?under 18 years$"
    f["singleparent"] = tot("B11003", L("B11003", r"Other family", own))/tot("B11003", L("B11003", own))
    f["moved"] = tot("B07003", L("B07003", r"(Moved from different county within same state|Moved from different state|"
                                 r"Moved from abroad)$"))/col("B07003", "B07003_001E")
    f["age65"] = tot("B01001", L("B01001", r"(65 and 66|67 to 69|70 to 74|75 to 79|80 to 84|85 years and over)"))/col("B01001", "B01001_001E")
    f["veteran"] = col("B21001", "B21001_002E")/col("B21001", "B21001_001E")
    b = col("B03002", "B03002_001E")
    f["black"] = col("B03002", "B03002_004E")/b; f["hisp"] = col("B03002", "B03002_012E")/b
    f["aian"] = col("B03002", "B03002_005E")/b
    f["pop"] = col("B01003", "B01003_001E")
    f.index.name = "GEOID"
    ctx, _ = context_frame(p["context"], f.reset_index(), client=c)
    f = f.join(ctx.reindex(f.index))
    for e in p["context"]:
        if e["source"] == "cbp":
            f[e["name"]] = f[e["name"]].fillna(0)        # a county without establishments has zero
    f["nonmetro"] = (f.metro2013 == 0).astype(float)
    w = read_wonder_export(str(county_tsv), "county")["rows"].set_index("GEOID")
    d = f.join(w[["deaths", "deaths_suppressed", "population"]], how="inner")
    d = d[~d.index.str[:2].isin(p["excluded_states"]) & ~d.index.isin(p["excluded_counties"])].copy()
    pops = acs_band_populations(T["B01001"].reindex(d.index))
    d["expected"] = expected_counts(pops, str(nat_tsv), person_years=d.population)
    return d


def run_monnat_d(spec, client=None) -> Dict[str, Any]:
    from .composite_index import build_index
    from . import boundaries, spatial
    from . import workflows_geo as wg
    p = spec["frame"]
    d = monnat_frame(spec, client)
    cov = list(p["econ_loadings"])+list(p["family_loadings"])+p["other_covariates"]
    d = d[~d[cov].isna().any(axis=1)]
    cc = d[(d.deaths >= 10) & (d.expected > 0)].copy()
    cc.index.name = "GEOID"
    base = cc.reset_index()
    X = pd.DataFrame(index=cc.index)
    for name, key in (("econ_index", "econ_loadings"), ("family_index", "family_loadings")):
        r = build_index(base, list(p[key]), method="loadings", loadings=p[key], standardize=True)
        X[name] = r["table"].set_index("area").score.reindex(cc.index).to_numpy()
    z = lambda s: (s-s.mean())/s.std(ddof=1)  # noqa: E731
    for k in ("vacant", "rent30", "moved", "age65", "veteran"):
        X[k] = z(cc[k])
    for k in ("religious", "membership", "sports", "black", "hisp", "aian"):
        q = pd.qcut(cc[k].rank(method="first"), 4, labels=False)
        for j in (1, 2, 3):
            X[f"{k}_q{j+1}"] = (q == j).astype(float)
    for code, name in {1: "farming", 2: "mining", 3: "manufacturing", 4: "government", 5: "recreation"}.items():
        X[f"type_{name}"] = (cc.ers_type == code).astype(float)
    X["nonmetro"] = cc.nonmetro
    for s in sorted(cc.index.str[:2].unique())[1:]:
        X[f"st{s}"] = (cc.index.str[:2] == s).astype(float)
    data = X.assign(y=100*np.log(cc.deaths/cc.expected)).reset_index()
    gdf = boundaries.get_boundaries("county", p["acs_year"])
    gdf = gdf[gdf.GEOID.astype(str).isin(set(data.GEOID))]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        islands = {str(i) for i in getattr(spatial.spatial_weights(gdf, "queen"), "islands", [])}
    keep = data[~data.GEOID.isin(islands)]
    cols = [c for c in X.columns if keep[c].std() > 0]
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "monnat.parquet"); keep.to_parquet(path, index=False)
        sem = wg.spatial_regression(path, "y ~ "+" + ".join(cols), "county", p["acs_year"], model="error")
    if not sem.get("success"):
        raise RuntimeError(f"spatial_regression: {sem.get('error')}")
    t = {r["term"]: r for r in sem["coefficients"]}
    head = {"econ_index": float(t["econ_index"]["estimate"])}
    res = compare(spec, head)
    res.update(counties=int(len(keep)), islands=len(islands),
               slopes={k: dict(estimate=float(t[k]["estimate"]), lower=float(t[k]["ci_lower"]),
                               upper=float(t[k]["ci_upper"])) for k in spec["published"] if k in t})
    return res


RUNNERS: Dict[str, Callable[..., Dict[str, Any]]] = {
    "chr_segregation": run_chr_segregation, "state_gini": run_state_gini, "nc_ice": run_nc_ice,
    "le_variance": run_le_variance, "monnat_d": run_monnat_d,
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
