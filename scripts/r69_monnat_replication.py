# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 69: replication D, Monnat (2018) Appendix Table D.2 Model 4 analogue (frozen with the criterion,
docs/audits/r69_replication_criterion.md).

ln(age-adjusted drug-related mortality 2006-2015, WONDER multiple cause, Appendix Table A.1 codes) on ACS 2010-2014
county covariates (economic distress index with the paper's CFA loadings, housing, family distress, population),
ERS 2015 economic types, 2013 metro status, CBP 2012 social capital quartiles and state fixed effects; spatial error
ML with queen contiguity; complete cases (unsuppressed counties). Coefficients are 100 x beta per SD.

Primary outcome: 100 x ln(deaths / expected), an indirectly age-sex standardized rate, for every unsuppressed county
(>= 10 deaths, the paper's Model 4 sample). WONDER now withholds rates when deaths <= 20 ("Unreliable"), so the
published age-adjusted rate exists only for counties with > 20 deaths; 100 x ln(AAMR) on those is secondary.
Expected deaths = sum over age x sex of the national 2006-2015 rate x the county's ACS 2014 age x sex share x the
county's WONDER 2006-2015 person-years.

Secondary (descriptive): all counties with interval-censored NB2 (hidden counts 1-9), exposure = expected deaths
from national age x sex rates and ACS 2014 county age x sex counts.

Usage: scripts/r69_monnat_replication.py --criterion-commit SHA      (--build-only: counts only)
"""
import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from census import boundaries, spatial  # noqa: E402
from census.metadata import table_variables  # noqa: E402
from census.missing_censored_its import fit_censored_negbin  # noqa: E402
from census.workflows import _client  # noqa: E402

WONDER = ROOT/"external_data/wonder/mcd/2006-2015"
REPL = Path(os.getenv("CENSUS_REPLICATION_DIR", ROOT/".cache/replication"))
ERS_SHA = "58a4192775fbb724cee872303e9fe0e22bd33378cd4e2ab9208ccf96d51bdeef"
EXCLUDE_STATES = {"02", "15"}
EXCLUDE_COUNTIES = {"48301", "08014", "51515"}          # Loving TX, Broomfield CO, Bedford City VA
LOADINGS = {"pov2554": .9045, "ssi": .8753, "pubassist": .7125, "unemp_nilf2554": .8187, "disab1864": .7410,
            "lt4yr": .5134, "unins1864": .6098, "gini": .5848}
FAMILY = {"sepdiv": .728, "singleparent": .728}
PUBLISHED = {"econ_index": (9.62, 1.47), "family_index": (8.73, 1.22), "rent30": (3.31, 1.08), "vacant": (2.79, 1.11),
             "type_mining": (12.77, 3.69), "type_government": (-7.37, 2.29)}
RATIO = (.67, 1.5)
FROZEN = ["scripts/r69_monnat_replication.py", "docs/audits/r69_replication_criterion.md", "census/spatial.py",
          "census/missing_censored_its.py", "census/count_repairs_core.py"]
OUT = ROOT/"docs/audits/r69_monnat_replication"


def acs(c, table):
    rows = c.fetch(2014, "*", table, geo_level="county")
    d = pd.DataFrame(rows[1:], columns=rows[0]); d["GEOID"] = d.state+d.county
    return d.set_index("GEOID")


def lines(table, *must, exclude=()):
    meta, _ = table_variables(table, "acs5", 2014)
    out = []
    for code, m in meta.items():
        if not code.endswith("E"):
            continue
        lab = m["label"]
        if all(re.search(p, lab) for p in must) and not any(re.search(p, lab) for p in exclude):
            out.append(code)
    if not out:
        raise SystemExit(f"no {table} line matches {must}")
    return sorted(out)


def total(d, codes):
    return sum(pd.to_numeric(d[c], errors="coerce") for c in codes)


def build_covariates(c):
    T = {t: acs(c, t) for t in ("B17001", "B23001", "B18101", "B15002", "B19056", "B19057", "B19083", "B27001",
                                "B25002", "B25070", "B12001", "B11003", "B07003", "B01001", "B21001", "B03002", "B01003")}
    f = pd.DataFrame(index=T["B01003"].index)
    age = r"(25 to 34|35 to 44|45 to 54) years$"
    f["pov2554"] = total(T["B17001"], lines("B17001", "below poverty", age)) / \
        total(T["B17001"], lines("B17001", r"(below|at or above) poverty", age))
    a23 = r"!!(25 to 29|30 to 34|35 to 44|45 to 54) years"
    unem = lines("B23001", a23, r"Civilian!!Unemployed$") + lines("B23001", a23, r"Not in labor force$")
    civ = lines("B23001", a23+r"$")
    armed = lines("B23001", a23, r"In Armed Forces$")
    f["unemp_nilf2554"] = total(T["B23001"], unem) / (total(T["B23001"], civ)-total(T["B23001"], armed))
    a18 = r"(18 to 34|35 to 64) years"
    f["disab1864"] = total(T["B18101"], lines("B18101", a18, r"With a disability$")) / \
        total(T["B18101"], lines("B18101", a18+r"$"))
    ba = lines("B15002", r"(Bachelor's degree|Master's degree|Professional school degree|Doctorate degree)$")
    f["lt4yr"] = 1-total(T["B15002"], ba)/pd.to_numeric(T["B15002"]["B15002_001E"])
    f["ssi"] = pd.to_numeric(T["B19056"]["B19056_002E"])/pd.to_numeric(T["B19056"]["B19056_001E"])
    f["pubassist"] = pd.to_numeric(T["B19057"]["B19057_002E"])/pd.to_numeric(T["B19057"]["B19057_001E"])
    f["gini"] = pd.to_numeric(T["B19083"]["B19083_001E"])
    a27 = r"(18 to 24|25 to 34|35 to 44|45 to 54|55 to 64) years"
    f["unins1864"] = total(T["B27001"], lines("B27001", a27, r"No health insurance coverage$")) / \
        total(T["B27001"], lines("B27001", a27+r"$"))
    f["vacant"] = pd.to_numeric(T["B25002"]["B25002_003E"])/pd.to_numeric(T["B25002"]["B25002_001E"])
    r30 = lines("B25070", r"(30.0 to 34.9|35.0 to 39.9|40.0 to 49.9|50.0 percent or more)")
    f["rent30"] = total(T["B25070"], r30)/(pd.to_numeric(T["B25070"]["B25070_001E"])-total(T["B25070"], lines("B25070", "Not computed")))
    f["sepdiv"] = total(T["B12001"], lines("B12001", r"(Separated|Divorced)$")) / pd.to_numeric(T["B12001"]["B12001_001E"])
    own = r"With own children (of the householder )?under 18 years$"
    sp = lines("B11003", r"Other family", own)
    f["singleparent"] = total(T["B11003"], sp)/total(T["B11003"], lines("B11003", own))
    f["moved"] = total(T["B07003"], lines("B07003", r"(Moved from different county within same state|Moved from different state|Moved from abroad)$")) / \
        pd.to_numeric(T["B07003"]["B07003_001E"])
    f["age65"] = total(T["B01001"], lines("B01001", r"(65 and 66|67 to 69|70 to 74|75 to 79|80 to 84|85 years and over)")) / \
        pd.to_numeric(T["B01001"]["B01001_001E"])
    f["veteran"] = pd.to_numeric(T["B21001"]["B21001_002E"])/pd.to_numeric(T["B21001"]["B21001_001E"])
    b = T["B03002"]; tot = pd.to_numeric(b.B03002_001E)
    f["black"] = pd.to_numeric(b.B03002_004E)/tot; f["hisp"] = pd.to_numeric(b.B03002_012E)/tot
    f["aian"] = pd.to_numeric(b.B03002_005E)/tot
    f["pop"] = pd.to_numeric(T["B01003"]["B01003_001E"])
    # CBP 2012 social capital per 10,000
    ep = "https://api.census.gov/data/2012/cbp"
    for name, codes in (("religious", ["813110"]), ("membership", ["8134", "8139"]),
                        ("sports", ["713910", "713940", "713950"])):
        s = pd.Series(0., index=f.index)
        for n in codes:
            rows = c._get_json(ep, {"get": "ESTAB,NAICS2012", "for": "county:*", "in": "state:*", "NAICS2012": n,
                                    "key": c.api_key})
            d = pd.DataFrame(rows[1:], columns=rows[0]); d.index = d.state+d.county
            s = s.add(pd.to_numeric(d.ESTAB).groupby(level=0).sum(), fill_value=0)
        f[name] = s.reindex(f.index).fillna(0)/f["pop"]*1e4
    raw = (REPL/"ers_county_types_2015.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != ERS_SHA:
        raise SystemExit("ERS file hash differs from the pinned value")
    ers = pd.DataFrame(json.loads(raw)); ers.index = ers.FIPSTXT.astype(str).str.zfill(5)
    f["ers_type"] = ers.Type_2015_Update.reindex(f.index)
    f["nonmetro"] = (ers.Metro2013.reindex(f.index) == 0).astype(float)
    return f, T["B01001"]


def wonder(kind):
    t = (WONDER/kind/"drug_related.tsv").read_text(encoding="utf-8", errors="replace")
    return pd.read_csv(io.StringIO(t[:t.index('"---"')]), sep="\t", dtype=str)


def frame():
    c = _client()
    f, b01 = build_covariates(c)
    w = wonder("county"); w = w[w["County Code"].notna()].copy()
    w["GEOID"] = w["County Code"].str.zfill(5)
    w["suppressed"] = w.Deaths == "Suppressed"
    w["deaths"] = pd.to_numeric(w.Deaths, errors="coerce")
    w["aamr"] = pd.to_numeric(w["Age Adjusted Rate"].str.replace(r"\s*\(Unreliable\)", "", regex=True), errors="coerce")
    w["person_years"] = pd.to_numeric(w.Population, errors="coerce")
    d = f.join(w.set_index("GEOID")[["suppressed", "deaths", "aamr", "person_years"]], how="inner")
    d = d[~d.index.str[:2].isin(EXCLUDE_STATES) & ~d.index.isin(EXCLUDE_COUNTIES)].copy()
    # expected deaths (secondary): national age x sex rates x ACS 2014 county age x sex counts x 10 years
    nat = wonder("national_age_sex"); nat = nat[nat["Ten-Year Age Groups Code"].notna() & (nat["Ten-Year Age Groups"] != "Not Stated")]
    rate = {(r["Ten-Year Age Groups"], r.Sex): float(r.Deaths)/float(r.Population) for _, r in nat.iterrows()}
    bands = {"< 1 year": ["Under 5"], "1-4 years": [], "5-14 years": ["5 to 9", "10 to 14"],
             "15-24 years": ["15 to 17", "18 and 19", "20 years", "21 years", "22 to 24"],
             "25-34 years": ["25 to 29", "30 to 34"], "35-44 years": ["35 to 39", "40 to 44"],
             "45-54 years": ["45 to 49", "50 to 54"], "55-64 years": ["55 to 59", "60 and 61", "62 to 64"],
             "65-74 years": ["65 and 66", "67 to 69", "70 to 74"], "75-84 years": ["75 to 79", "80 to 84"],
             "85+ years": ["85 years and over"]}
    # ACS "Under 5" spans WONDER's "< 1" and "1-4": use the population-weighted combined national rate
    exp = pd.Series(0., index=d.index)
    for sex, lab in (("Male", "Male"), ("Female", "Female")):
        r04 = (rate[("< 1 year", sex)]*float(nat[(nat["Ten-Year Age Groups"] == "< 1 year") & (nat.Sex == sex)].Population.iloc[0])
               + rate[("1-4 years", sex)]*float(nat[(nat["Ten-Year Age Groups"] == "1-4 years") & (nat.Sex == sex)].Population.iloc[0])) / \
            (float(nat[(nat["Ten-Year Age Groups"] == "< 1 year") & (nat.Sex == sex)].Population.iloc[0])
             + float(nat[(nat["Ten-Year Age Groups"] == "1-4 years") & (nat.Sex == sex)].Population.iloc[0]))
        for band, parts in bands.items():
            if not parts:
                continue
            codes = [x for p in parts for x in lines("B01001", rf"!!{lab}!!{p}")]
            r = r04 if band == "< 1 year" else rate[(band, sex)]
            exp = exp.add(total(b01.reindex(d.index), codes)*r, fill_value=0)
    acs_total = pd.to_numeric(b01.reindex(d.index)["B01001_001E"])
    d["expected"] = exp/acs_total*d.person_years           # age x sex mix from ACS, person-years from WONDER
    return d


def design(d):
    z = lambda s: (s-s.mean())/s.std(ddof=1)  # noqa: E731
    X = pd.DataFrame(index=d.index)
    X["econ_index"] = z(sum(w*z(d[k]) for k, w in LOADINGS.items()))
    X["family_index"] = z(sum(w*z(d[k]) for k, w in FAMILY.items()))
    for k in ("vacant", "rent30", "moved", "age65", "veteran"):
        X[k] = z(d[k])
    for k in ("religious", "membership", "sports", "black", "hisp", "aian"):
        q = pd.qcut(d[k].rank(method="first"), 4, labels=False)
        for j in (1, 2, 3):
            X[f"{k}_q{j+1}"] = (q == j).astype(float)
    types = {1: "farming", 2: "mining", 3: "manufacturing", 4: "government", 5: "recreation"}
    for code, name in types.items():
        X[f"type_{name}"] = (d.ers_type == code).astype(float)
    X["nonmetro"] = d.nonmetro
    for s in sorted(d.index.str[:2].unique())[1:]:
        X[f"st{s}"] = (d.index.str[:2] == s).astype(float)
    return X


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--criterion-commit"); ap.add_argument("--build-only", action="store_true")
    a = ap.parse_args()
    d = frame()
    cov = list(LOADINGS)+list(FAMILY)+["vacant", "rent30", "moved", "age65", "veteran", "religious", "membership",
                                        "sports", "black", "hisp", "aian", "ers_type", "nonmetro"]
    miss = d[cov].isna().any(axis=1)
    if a.build_only:
        print(dict(counties=len(d), suppressed=int(d.suppressed.sum()), unsuppressed=int((~d.suppressed).sum()),
                   missing_covariates=int(miss.sum()), missing_ers=int(d.ers_type.isna().sum()),
                   aamr_missing_unsuppressed=int((~d.suppressed & d.aamr.isna()).sum()),
                   ten_plus=int((~d.suppressed & (d.deaths >= 10)).sum()), expected_ok=int((d.expected > 0).sum())))
        return
    subprocess.run(["git", "merge-base", "--is-ancestor", a.criterion_commit, "HEAD"], cwd=ROOT, check=True)
    for rel in FROZEN:
        if subprocess.check_output(["git", "show", a.criterion_commit+":"+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
            raise SystemExit("differs from criterion commit: "+rel)
    d = d[~miss].copy()
    out = dict(criterion_commit=a.criterion_commit, counties_all=int(len(d)))
    # primary: complete cases, spatial error ML
    cc = d[~d.suppressed & (d.deaths >= 10) & (d.expected > 0)].copy()
    X = design(cc)
    data = X.assign(y=100*np.log(cc.deaths/cc.expected), GEOID=cc.index)
    gdf = boundaries.get_boundaries("county", 2014)
    gdf = gdf[gdf.GEOID.astype(str).isin(set(cc.index))]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        w = spatial.spatial_weights(gdf, "queen")
        islands = sorted(str(i) for i in getattr(w, "islands", []))
        keep = data[~data.GEOID.isin(islands)]
        w = spatial.spatial_weights(gdf[gdf.GEOID.isin(set(keep.GEOID))], "queen")
        cols = [c for c in X.columns if keep[c].std() > 0]
        res = spatial.spatial_regression("y ~ "+" + ".join(cols), keep, w, model="error")
    t = res.coefficients.set_index("term")
    rows = {}
    for k, (p, pse) in PUBLISHED.items():
        e, lo, hi = (float(t.loc[k, c]) for c in ("estimate", "ci_lower", "ci_upper"))
        rows[k] = dict(published=p, published_se=pse, estimate=e, lower=lo, upper=hi, se=float(t.loc[k, "se_model"])
                       if "se_model" in t else None, ratio=e/p)
    e = rows["econ_index"]
    rep = bool(np.sign(e["estimate"]) == 1 and e["lower"] <= 9.62 <= e["upper"] and RATIO[0] <= e["ratio"] <= RATIO[1])
    out.update(primary=dict(n=int(len(keep)), islands=islands, lam=float(t.loc["lambda", "estimate"]), slopes=rows),
               outcome="replicated" if rep else ("partly replicated" if e["estimate"] > 0 else "not replicated"))
    # secondary A: published AAMR where WONDER reports it (> 20 deaths), same model
    ca = cc[cc.aamr.notna() & (cc.aamr > 0) & ~cc.index.isin(islands)]
    Xs = design(ca); ds = Xs.assign(y=100*np.log(ca.aamr), GEOID=ca.index)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        gs = gdf[gdf.GEOID.isin(set(ca.index))]; ws = spatial.spatial_weights(gs, "queen")
        isl2 = set(str(i) for i in getattr(ws, "islands", []))
        ds = ds[~ds.GEOID.isin(isl2)]; ws = spatial.spatial_weights(gs[gs.GEOID.isin(set(ds.GEOID))], "queen")
        c2 = [c for c in Xs.columns if ds[c].std() > 0]
        t2 = spatial.spatial_regression("y ~ "+" + ".join(c2), ds, ws, model="error").coefficients.set_index("term")
    out["secondary_aamr"] = dict(n=int(len(ds)), econ_index={k: float(t2.loc["econ_index", c]) for k, c in
                                                            (("estimate", "estimate"), ("lower", "ci_lower"), ("upper", "ci_upper"))})
    # secondary B: all counties, censored NB2 with expected deaths (state FE included)
    Xa = design(d)
    fa = Xa.assign(deaths=d.deaths.where(~d.suppressed), hidden=d.suppressed, expected=d.expected)
    try:
        r2 = fit_censored_negbin(fa, "deaths", "hidden", "expected", list(Xa.columns))
        tb = r2["table"].set_index("term")
        out["secondary_censored_nb2"] = dict(n=int(r2["n"]), hidden=int(r2["n_censored"]),
                                            econ_index={k: 100*float(tb.loc["econ_index", k]) for k in ("estimate", "lower", "upper")},
                                            published_model3=12.55)
    except Exception as exc:  # noqa: BLE001 - descriptive only
        out["secondary_censored_nb2"] = dict(error=f"{type(exc).__name__}: {exc}")
    OUT.with_suffix(".json").write_text(json.dumps(out, indent=1, default=float)+"\n")
    L = ["# Round 69 replication D: Monnat 2018, Model 4 analogue", "", f"Criterion commit: `{a.criterion_commit}`. "
         f"Complete-case counties: {out['primary']['n']:,} (paper: 2,484); islands dropped: {len(islands)}; "
         f"lambda {out['primary']['lam']:.3f}.", "",
         "| Covariate | Published (SE) | Ours (90% CI) | Ratio |", "| :--- | :--- | :--- | ---: |"]
    for k, r in rows.items():
        L.append(f"| {k} | {r['published']:.2f} ({r['published_se']:.2f}) | {r['estimate']:.2f} ({r['lower']:.2f} to "
                 f"{r['upper']:.2f}) | {r['ratio']:.2f} |")
    s2 = out["secondary_censored_nb2"]
    sa = out["secondary_aamr"]["econ_index"]
    L += ["", f"**Outcome (economic distress): {out['outcome']}.**", "",
          f"Secondary (published AAMR, counties with > 20 deaths, n {out['secondary_aamr']['n']:,}): economic distress "
          f"{sa['estimate']:.2f} ({sa['lower']:.2f} to {sa['upper']:.2f}).", "",
          "Secondary (descriptive, all counties, interval-censored NB2): "+
          (f"economic distress {s2['econ_index']['estimate']:.2f} ({s2['econ_index']['lower']:.2f} to "
           f"{s2['econ_index']['upper']:.2f}); n {s2['n']:,}, hidden {s2['hidden']}; paper's Model 3 12.55."
           if "econ_index" in s2 else s2.get("error", "")), ""]
    OUT.with_suffix(".md").write_text("\n".join(L))
    print(out["outcome"])


if __name__ == "__main__":
    main()
