# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 21 Part 2 pre-specified EXPLORATORY analyses (PLAN_ROUND_21 section 12, X1-X5).

Runs on hash-checked analysed data of the confirmatory runs. Every output is labelled exploratory
with the related manifest hash. Not confirmatory.

    python scripts/r21b_exploratory.py studies_output/r21b/confirmatory studies_output/r21/confirmatory \
        studies_output/r20/confirmatory studies_output/r21b/x4 studies_output/r21b/exploratory
"""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from census import health_sources as hs, models, workflows_geo  # noqa: E402
from census.manifest import run_variant  # noqa: E402

LEVEL = 0.90
ST = "C(GEOID.str[:2])"
STATES = {"26": "Michigan", "36": "New York"}
NYC = ("36005", "36047", "36061", "36081", "36085")
FORMULAS = {"m1": "{y} ~ pov_rate + " + ST,
            "m2": "{y} ~ pov_rate + pct_bachelors + no_vehicle + cost_burden + " + ST,
            "m3": "{y} ~ asdp + " + ST}
TERMS = {"m1": ["pov_rate"], "m2": ["no_vehicle", "cost_burden", "pov_rate", "pct_bachelors"], "m3": ["asdp"]}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(run_dir):
    run = json.loads((run_dir / "bundle" / "results" / "run.json").read_text())
    data = {}
    for name, info in run["analysed_data"].items():
        path = run_dir / info["path"]
        if sha256(path) != info["sha256"]:
            raise SystemExit(f"{path} does not match run.json; refusing to analyse different data")
        data[name] = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path, dtype={"GEOID": str})
        data[name]["GEOID"] = data[name]["GEOID"].astype(str)
    return run, data["analysis_frame"], data.get("replicates")


def eiv(formula, frame, reps, fixed=(), **kw):
    y = formula.split("~")[0].strip()
    return models.fit_eiv(formula, frame, reps, confidence_level=LEVEL, replicate_policy="strict",
                          fixed_variables=[y] if y in fixed else [], **kw)


def coef(res, term):
    row = res.coefficients.set_index("term").loc[term]
    out = {k: float(row[k]) for k in ("estimate", "se_total", "ci_lower", "ci_upper")}
    out["n"] = int(res.n_obs)
    if "naive_estimate" in row:
        out["naive_estimate"] = float(row["naive_estimate"])
    for key in ("se_total_cr1", "se_total_independent"):
        d = (res.diagnostics or {}).get(key)
        if d:
            out[key] = float(d[term])
    return out


def subset(frame, reps, mask):
    keep = set(frame.loc[mask, "GEOID"])
    return frame[mask].reset_index(drop=True), reps[reps["GEOID"].isin(keep)].reset_index(drop=True)


def main(run_dir, r21_dir, r20_dir, x4_dir, out_dir):
    run_dir, r21_dir, r20_dir, x4_dir, out_dir = map(Path, (run_dir, r21_dir, r20_dir, x4_dir, out_dir))
    out_dir.mkdir(parents=True, exist_ok=True)
    run, frame, reps = load(run_dir)
    h = run["manifest_hash"]
    S = {"analysis_status": "exploratory", "related_manifest_hash": h,
         "analysed_data": {k: v["sha256"] for k, v in run["analysed_data"].items()}}
    need = ["prem_mort", "pov_rate", "pct_bachelors", "no_vehicle", "cost_burden", "asdp"]
    cc = frame[np.isfinite(frame[need].to_numpy(float)).all(axis=1)]
    S["descriptives"] = {
        "n_counties": int(len(cc)),
        **{v: {"mean": float(cc[v].mean()), "sd": float(cc[v].std()), "min": float(cc[v].min()),
               "max": float(cc[v].max())} for v in need},
        "by_state": {STATES[s]: {"n": int((cc.GEOID.str[:2] == s).sum()),
                                 "prem_mort": float(cc.loc[cc.GEOID.str[:2] == s, "prem_mort"].mean())}
                     for s in STATES},
        "nyc_prem_mort": {g: float(cc.loc[cc.GEOID == g, "prem_mort"].iloc[0]) for g in NYC if (cc.GEOID == g).any()},
        "correlations_with_prem_mort": {v: float(np.corrcoef(cc["prem_mort"], cc[v])[0, 1]) for v in need[1:]},
    }

    # X1: the same models with premature death (YPLL, v001) and life expectancy (v147)
    states = sorted({g[:2] for g in frame["GEOID"]})
    ext, prov = hs.load_external([{"name": "ypll", "source": "chr", "release": 2025, "measure": "v001"},
                                  {"name": "chr_le", "source": "chr", "release": 2025, "measure": "v147"}],
                                 "county", states)
    f1 = frame.merge(ext[["GEOID", "ypll", "ypll_se", "chr_le", "chr_le_se"]], on="GEOID", how="left")
    S["X1_other_mortality_outcomes"] = {"sources": [{k: p[k] for k in ("dataset", "files")} for p in prov]}
    for y in ("ypll", "chr_le"):
        ok = np.isfinite(f1[[y] + need[1:]].to_numpy(float)).all(axis=1)
        fy, ry = subset(f1, reps, ok)
        S["X1_other_mortality_outcomes"][y] = {
            mid: {t: coef(eiv(f.format(y=y), fy, ry, fixed=(y,)), t) for t in TERMS[mid]}
            for mid, f in FORMULAS.items()}

    # X1b: without New York City (5 counties)
    fo, ro = subset(frame, reps, ~frame["GEOID"].isin(NYC))
    S["X1b_without_nyc"] = {mid: {t: coef(eiv(f.format(y="prem_mort"), fo, ro, fixed=("prem_mort",)), t)
                                  for t in TERMS[mid]} for mid, f in FORMULAS.items()}

    # X2: Part 1 H1-H3 with the delete-one-cluster jackknife (run_variant)
    S["X2_part1_jackknife"] = {}
    for mid in ("m1", "m2", "m3"):
        v = run_variant(r21_dir, mid, args={"cluster_se": "jackknife"}, out_dir=out_dir / "variants",
                        label="jackknife")
        c = next(c for c in v["result"]["coefficients"] if c["term"] == "acs_dis")
        S["X2_part1_jackknife"][mid] = {"estimate": c["estimate"], "se_jackknife": c["se_total"],
                                        "se_cr1": v["result"]["diagnostics"]["se_total_cr1"]["acs_dis"],
                                        "ci_lower": c["ci_lower"], "ci_upper": c["ci_upper"],
                                        "related_manifest_hash": v["related_manifest_hash"]}

    # X3: Part 1 E2 with the crude adult ACS disability measure (acs_dis) instead of asdp
    _, f21, r21 = load(r21_dir)
    _, f20, r20 = load(r20_dir)
    f3 = f20.merge(f21[["GEOID", "acs_dis", "acs_dis_se", "places_dis", "places_dis_se"]], on="GEOID", how="inner")
    r3 = pd.concat([r20, r21[r21["variable"] == "acs_dis"]], ignore_index=True)
    ok = np.isfinite(f3[["acs_dis", "places_dis", "pov_rate", "pct_bachelors", "no_vehicle",
                         "cost_burden"]].to_numpy(float)).all(axis=1)
    f3, r3 = subset(f3, r3, ok)
    cl = {"cluster": "GEOID.str[:5]"}
    S["X3_crude_adult_e2"] = {"n_tracts": int(len(f3))}
    for y in ("acs_dis", "places_dis", "asdp"):
        S["X3_crude_adult_e2"][y] = {
            "m1_pov_rate": coef(eiv(FORMULAS["m1"].format(y=y), f3, r3, fixed=("places_dis",), **cl), "pov_rate"),
            **{f"m2_{t}": coef(eiv(FORMULAS["m2"].format(y=y), f3, r3, fixed=("places_dis",), **cl), t)
               for t in TERMS["m2"]}}

    # X4: USALEEP (exploratory manifest run), summarised from its bundle
    try:
        x4 = json.loads((x4_dir / "bundle" / "results" / "hypotheses.json").read_text())
        x4run = json.loads((x4_dir / "bundle" / "results" / "run.json").read_text())
        S["X4_usaleep"] = {"note": "exploratory manifest (not pre-registered); R2: pct_bachelors is a USALEEP "
                                   "model input, used as a control only",
                           "manifest_hash": x4run["manifest_hash"], "hypotheses": x4,
                           "external": {k: x4run.get("external", {}).get(k) for k in ("join",)},
                           "predicted": [p.get("predicted") for p in x4run.get("external", {}).get("sources", [])],
                           "deviations": x4run.get("deviations")}
    except FileNotFoundError as exc:
        S["X4_usaleep"] = {"error": str(exc)}

    # X5: m2 residual map (diverging) and Moran's I
    import patsy
    res2 = eiv(FORMULAS["m2"].format(y="prem_mort"), cc.reset_index(drop=True),
               reps[reps.GEOID.isin(set(cc.GEOID))].reset_index(drop=True), fixed=("prem_mort",))
    X = patsy.dmatrix(FORMULAS["m2"].split("~")[1], cc, return_type="dataframe")
    b = res2.coefficients.set_index("term")["estimate"].reindex(X.columns).to_numpy(float)
    rr = cc[["GEOID"]].copy()
    rr["resid_m2"] = cc["prem_mort"].to_numpy(float) - X.to_numpy(float) @ b
    rp = out_dir / "resid_m2.csv"
    rr.to_csv(rp, index=False)
    mp = workflows_geo.make_map(str(rp), "resid_m2", "county", 2022, scheme="diverging", k=6,
                                output_dir=str(out_dir / "figures" / "resid_m2"),
                                label="Premature mortality minus fitted (m2), deaths per 100,000",
                                data_source=f"CHR&R 2025 (NCHS 2020-2022); ACS 2018-2022; exploratory; manifest {h[:12]}")
    S["X5_map"] = {k: mp.get(k) for k in ("success", "paths", "error")}
    sa = workflows_geo.spatial_autocorrelation(str(rp), "resid_m2", "county", 2022)
    S["X5_moran"] = {"global": sa.get("global"), "error": sa.get("error")}
    for s in STATES:
        part = out_dir / f"prem_mort_{s}.csv"
        frame[frame.GEOID.str[:2] == s].to_csv(part, index=False)
        m = workflows_geo.make_map(str(part), "prem_mort", "county", 2022, se_col="prem_mort_se",
                                   output_dir=str(out_dir / "figures" / f"prem_mort_{s}"),
                                   label="Premature age-adjusted mortality, deaths under 75 per 100,000",
                                   data_source=f"CHR&R 2025 (NCHS 2020-2022); exploratory; manifest {h[:12]}")
        S["X5_map"][f"prem_mort {STATES[s]}"] = {k: m.get(k) for k in ("success", "paths", "error")}

    (out_dir / "summary.json").write_text(json.dumps(S, indent=2, default=str) + "\n")
    print(json.dumps({k: v for k, v in S.items() if k not in ("X5_map", "analysed_data")}, indent=1, default=str))


if __name__ == "__main__":
    main(*sys.argv[1:6])
