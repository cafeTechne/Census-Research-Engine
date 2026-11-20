# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 67: replication C, Mitchell et al. (2022) NC tract life expectancy and ICE (frozen with the criterion).

Data: USALEEP 2010-2015 NC e(0) (all tracts with a value) and ACS 2014-2018 tract tables (engine caches filled by
scripts/r67_fetch.py). ICE Income = (B19001 014-017 - 002-005) / 001; ICE Race = (B03002 003 - 004) / 001;
ICE Income + Race = (B19001H 014-017 - B19001B 002-005) / B19001 001. Tracts with zero population, zero
households or no e(0) are excluded. Outcome ln(e0).

Models per ICE: OLS (interval: SCPC rho_bar .05 if docs/audits/r67_nc_tract_validation.json passed it, else HC3)
and the engine's spatial error model (queen contiguity on 2018 cartographic tracts, ML). Rule per slope: same sign,
interval overlaps the published value +/- half a unit of its last digit, ratio in [0.67, 1.5]. Secondary
(descriptive): EIV-corrected slopes for ICE Income and ICE Race from the 2018 VRE files.

Usage: scripts/r67_nc_ice_replication.py --criterion-commit SHA
"""
import argparse
import json
import subprocess
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import statsmodels.api as sm  # noqa: E402

from census import boundaries, health_sources, models, replicate, scpc, spatial  # noqa: E402
from census.workflows import _client  # noqa: E402

PUBLISHED = {  # Table 3: (OLS estimate, adjusted R2 %, spatial-error estimate)
    "ice_race": ("0.045", 19.60, "0.054"),
    "ice_income": ("0.13", 48.19, "0.12"),
    "ice_income_race": ("0.13", 45.07, "0.13"),
}
RATIO = (.67, 1.5)
FROZEN = ["scripts/r67_nc_ice_replication.py", "docs/audits/r67_replication_criterion.md", "census/scpc.py",
          "census/scpc_core.py", "census/spatial.py", "census/models.py"]
OUT = ROOT/"docs/audits/r67_nc_ice_replication"
HI, LO = range(14, 18), range(2, 6)


def acs(client, table):
    rows = client.fetch(2018, "37", table, geo_level="tract")
    d = pd.DataFrame(rows[1:], columns=rows[0]); d["GEOID"] = d.state+d.county+d.tract
    return d.set_index("GEOID")


def num(d, table, lines):
    return sum(pd.to_numeric(d[f"{table}_{i:03d}E"]) for i in lines)


def build():
    c = _client()
    inc, b, h, race = (acs(c, t) for t in ("B19001", "B19001B", "B19001H", "B03002"))
    f = pd.DataFrame(index=inc.index)
    f["hh"] = pd.to_numeric(inc.B19001_001E); f["pop"] = pd.to_numeric(race.B03002_001E)
    f["ice_income"] = (num(inc, "B19001", HI)-num(inc, "B19001", LO))/f.hh
    f["ice_race"] = (pd.to_numeric(race.B03002_003E)-pd.to_numeric(race.B03002_004E))/f["pop"]
    f["ice_income_race"] = (num(h, "B19001H", HI)-num(b, "B19001B", LO))/f.hh
    le, rec = health_sources.parse_usaleep(health_sources.fetch_usaleep(["37"])["rows"], "le", include_predicted=True)
    f = f.join(le.set_index("GEOID")[["le", "le_se"]], how="inner")
    n_all = int(len(f))
    f = f[(f["pop"] > 0) & (f.hh > 0) & f["le"].notna()].copy()
    f["lnle"] = np.log(f["le"].astype(float))
    return f.reset_index().rename(columns={"index": "GEOID"}), n_all


def unit(s):
    return 10.0**-(len(s.split(".")[1]))


def judge(est, lo, hi, pub):
    p, u = float(pub), unit(pub)
    return dict(published=p, estimate=est, lower=lo, upper=hi, ratio=est/p, same_sign=bool(np.sign(est) == np.sign(p)),
                overlaps=bool(lo <= p+u/2 and hi >= p-u/2), ratio_ok=bool(RATIO[0] <= est/p <= RATIO[1]),
                replicated=bool(np.sign(est) == np.sign(p) and lo <= p+u/2 and hi >= p-u/2
                                and RATIO[0] <= est/p <= RATIO[1]))


def ice_replicates(var):
    """Per-tract replicate ICE values (ICE Income or ICE Race) from the 2018 VRE files."""
    if var == "ice_income":
        v = replicate.fetch_vre("B19001", 2018, "tract", state_code="37", lines=[1, *HI, *LO])
        tab, tot, hi, lo = "B19001", [1], list(HI), list(LO)
    else:
        v = replicate.fetch_vre("B03002", 2018, "tract", state_code="37", lines=[1, 3, 4])
        tab, tot, hi, lo = "B03002", [1], [3], [4]
    cols = ["estimate", *replicate.REPLICATE_COLUMNS]
    g = lambda ls: v[v.variable.isin([f"{tab}_{i:03d}" for i in ls])].groupby("GEOID")[cols].sum()  # noqa: E731
    r = (g(hi)-g(lo))/g(tot)
    return r.reset_index().assign(variable=var, Year=2018)


def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument("--criterion-commit", required=True)
    a = ap.parse_args()
    subprocess.run(["git", "merge-base", "--is-ancestor", a.criterion_commit, "HEAD"], cwd=ROOT, check=True)
    for rel in FROZEN:
        if subprocess.check_output(["git", "show", a.criterion_commit+":"+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
            raise SystemExit("differs from criterion commit: "+rel)
    sim = json.loads((ROOT/"docs/audits/r67_nc_tract_validation.json").read_text())
    use_scpc = bool(sim["passed"]["SCPC05"])
    f, n_joined = build()
    geo = json.loads((ROOT/"docs/audits/nc_tract_geometry.json").read_text())
    coords = pd.DataFrame(dict(GEOID=geo["GEOID"], lon=geo["lon"], lat=geo["lat"]))
    gdf = boundaries.get_boundaries("tract", 2018, state="37")
    gdf = gdf[gdf.GEOID.astype(str).isin(set(f.GEOID))].copy()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        w = spatial.spatial_weights(gdf, "queen")
    islands = sorted(str(i) for i in getattr(w, "islands", []))
    out = dict(criterion_commit=a.criterion_commit, n_tracts=int(len(f)), n_joined=n_joined, islands=islands,
               interval="SCPC rho_bar .05" if use_scpc else "HC3", slopes={})
    for var, (p_ols, p_r2, p_sem) in PUBLISHED.items():
        d = f[["GEOID", "lnle", var]].dropna()
        X = sm.add_constant(d[var]); fit = sm.OLS(d.lnle, X).fit(cov_type="HC3")
        if use_scpc:
            s = scpc.fit_scpc(f"lnle ~ {var}", d, coords=coords, rho_bar=.05)
            row = s["table"].set_index("term").loc[var]; lo, hi = float(row.lower), float(row.upper)
        else:
            lo, hi = (float(x) for x in fit.conf_int(alpha=.10).loc[var])
        ols = judge(float(fit.params[var]), lo, hi, p_ols)
        ols.update(adj_r2=float(fit.rsquared_adj)*100, published_adj_r2=p_r2, hc3=[float(x) for x in fit.conf_int(alpha=.10).loc[var]])
        dd = d[~d.GEOID.isin(islands)]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            wi = spatial.spatial_weights(gdf[gdf.GEOID.isin(set(dd.GEOID))], "queen")
            sr = spatial.spatial_regression(f"lnle ~ {var}", dd, wi, model="error")
        t = sr.coefficients.set_index("term")
        sem = judge(float(t.loc[var, "estimate"]), float(t.loc[var, "ci_lower"]), float(t.loc[var, "ci_upper"]), p_sem)
        sem.update(lam=float(t.loc["lambda", "estimate"]), n=int(len(dd)))
        eiv = None
        if var in ("ice_income", "ice_race"):
            try:
                rep = ice_replicates(var)
                e = models.fit_eiv(f"lnle ~ {var}", d.assign(Year=2018), rep, model="ols")
                ct = e.coefficients.set_index("term").loc[var]
                eiv = dict(estimate=float(ct.estimate), lower=float(ct.ci_lower), upper=float(ct.ci_upper))
            except Exception as exc:  # noqa: BLE001 - descriptive only
                eiv = dict(error=f"{type(exc).__name__}: {exc}")
        out["slopes"][var] = dict(ols=ols, spatial_error=sem, eiv=eiv)
    allrep = all(v[m]["replicated"] for v in out["slopes"].values() for m in ("ols", "spatial_error"))
    signs = all(v[m]["same_sign"] for v in out["slopes"].values() for m in ("ols", "spatial_error"))
    out["outcome"] = "replicated" if allrep else ("partly replicated" if signs else "not replicated")
    OUT.with_suffix(".json").write_text(json.dumps(out, indent=1, default=float)+"\n")
    L = ["# Round 67 replication C: NC tract life expectancy and ICE", "",
         f"Criterion commit: `{a.criterion_commit}`. Tracts: {out['n_tracts']:,} (paper: 1,970). OLS interval: "
         f"{out['interval']}. Islands dropped from the spatial error model: {len(islands)}.", "",
         "| ICE | Model | Published | Ours (90% CI) | Ratio | Replicated |", "| :--- | :--- | ---: | :--- | ---: | :--- |"]
    for var, r in out["slopes"].items():
        for m in ("ols", "spatial_error"):
            j = r[m]
            L.append(f"| {var} | {m} | {j['published']:g} | {j['estimate']:.4f} ({j['lower']:.4f} to {j['upper']:.4f}) | "
                     f"{j['ratio']:.2f} | {j['replicated']} |")
    L += ["", "| ICE | Adjusted R2 ours | Published |", "| :--- | ---: | ---: |"]
    for var, r in out["slopes"].items():
        L.append(f"| {var} | {r['ols']['adj_r2']:.2f}% | {r['ols']['published_adj_r2']:.2f}% |")
    L += ["", f"**Outcome: {out['outcome']}.**", ""]
    OUT.with_suffix(".md").write_text("\n".join(L))
    print(out["outcome"])


if __name__ == "__main__":
    main()
