# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 20 pre-specified EXPLORATORY analyses (PLAN_ROUND_20 section 3, E1-E6; E5b county-clustered SEs added after E5 showed
residual autocorrelation, labelled as such).

Runs on the data the confirmatory models analysed (``<run>/analysed/``, hashes
checked against ``run.json``), with the engine's own tools. Every output is
labelled exploratory with the manifest hash. Not confirmatory evidence.

    python scripts/r20_exploratory.py studies_output/r20/confirmatory studies_output/r20/exploratory
"""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from census import models, workflows_geo  # noqa: E402
from census.analysis import REPLICATE_COLUMNS  # noqa: E402

LEVEL = 0.90
ST = "C(GEOID.str[:2])"
M1 = f"asdp ~ pov_rate + {ST}"
M2 = f"asdp ~ pov_rate + pct_bachelors + no_vehicle + cost_burden + {ST}"
TERMS = {"H1": ("m1", "pov_rate"), "H2": ("m2", "no_vehicle"), "H3": ("m2", "cost_burden")}
NYC = ("36005", "36047", "36061", "36081", "36085")
STATES = {"26": "Michigan", "36": "New York"}
BANDS = {  # band -> (population names, with-disability names), as in the manifest
    "b0": (["dis_pop_003", "dis_pop_006", "dis_pop_022", "dis_pop_025"],
           ["dis_with_004", "dis_with_007", "dis_with_023", "dis_with_026"]),
    "b1": (["dis_pop_009", "dis_pop_028"], ["dis_with_010", "dis_with_029"]),
    "b2": (["dis_pop_012", "dis_pop_031"], ["dis_with_013", "dis_with_032"]),
    "b3": (["dis_pop_015", "dis_pop_034"], ["dis_with_016", "dis_with_035"]),
    "b4": (["dis_pop_018", "dis_pop_037"], ["dis_with_019", "dis_with_038"]),
}


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
    return run, data["analysis_frame"], data["replicates"]


def coef(result, term, basis):
    row = result.coefficients.set_index("term").loc[term]
    out = {"estimate": float(row["estimate"]), "se": float(row[basis]), "ci_lower": float(row["ci_lower"]),
           "ci_upper": float(row["ci_upper"]), "n": int(result.n_obs)}
    if "naive_estimate" in row:
        out["naive_estimate"] = float(row["naive_estimate"])
    return out


def eiv(formula, frame, reps, **kw):
    return models.fit_eiv(formula, frame, reps, confidence_level=LEVEL, replicate_policy="strict", **kw)


def hyp_table(fit_fn, frame, reps, basis="se_total", **kw):
    out = {}
    fits = {"m1": fit_fn(M1, frame, reps, **kw), "m2": fit_fn(M2, frame, reps, **kw)}
    for h, (m, term) in TERMS.items():
        out[h] = coef(fits[m], term, basis)
    return out, fits


def subset(frame, reps, mask):
    keep = set(frame.loc[mask, "GEOID"].astype(str))
    return frame[mask].reset_index(drop=True), reps[reps["GEOID"].astype(str).isin(keep)].reset_index(drop=True)


def crude(frame, reps):
    """Crude disability prevalence (all ages, %) with its replicate rows, from the band counts."""
    pops = [p for b in BANDS.values() for p in b[0]]
    withs = [w for b in BANDS.values() for w in b[1]]
    frame = frame.copy()
    frame["crude"] = 100 * frame[withs].sum(axis=1) / frame[pops].sum(axis=1)
    keys = ["GEOID"] + (["Year"] if "Year" in reps.columns else [])
    cols = ["estimate"] + REPLICATE_COLUMNS
    piv = {v: reps[reps["variable"] == v].set_index(keys)[cols] for v in pops + withs}
    num = sum(piv[v] for v in withs)
    den = sum(piv[v] for v in pops)
    cr = (100 * num / den.where(den != 0)).reset_index()
    cr["variable"] = "crude"
    reps = pd.concat([reps, cr], ignore_index=True)
    sub = cr.set_index("GEOID")
    se = np.sqrt(4 / 80 * ((sub[REPLICATE_COLUMNS].to_numpy(float) - sub[["estimate"]].to_numpy(float)) ** 2)
                 .sum(axis=1))
    frame["crude_se"] = frame["GEOID"].map(dict(zip(sub.index.astype(str), se)))
    return frame, reps


def main(run_dir, out_dir):
    run_dir, out_dir = Path(run_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    run, frame, reps = load(run_dir)
    h = run["manifest_hash"]
    frame["GEOID"] = frame["GEOID"].astype(str)
    reps["GEOID"] = reps["GEOID"].astype(str)
    summary = {"analysis_status": "exploratory", "related_manifest_hash": h,
               "analysed_data": {k: v["sha256"] for k, v in run["analysed_data"].items()}}
    need = ["asdp", "pov_rate", "pct_bachelors", "no_vehicle", "cost_burden"]
    cc = frame[np.isfinite(frame[need].to_numpy(float)).all(axis=1)].reset_index(drop=True)
    summary["descriptives"] = {
        v: {"mean": float(cc[v].mean()), "sd": float(cc[v].std()), "median_cv": float(np.nanmedian(cc[f"{v}_cv"]))}
        for v in need}
    summary["descriptives"]["n_tracts"] = int(len(cc))
    summary["descriptives"]["by_state"] = {
        STATES[s]: {v: float(cc.loc[cc.GEOID.str[:2] == s, v].mean()) for v in need} | {
            "n": int((cc.GEOID.str[:2] == s).sum())} for s in STATES}

    # registered (re-fit, as a check against the bundle)
    reg, fits = hyp_table(eiv, frame, reps)
    summary["registered_refit"] = reg
    summary["reliability"] = {m: f.diagnostics.get("reliability") for m, f in fits.items()}
    summary["outcome_error_correlation"] = {m: f.diagnostics.get("outcome_error_correlation") for m, f in fits.items()}

    # E1: naive replicate fits and regression calibration
    naive, _ = hyp_table(lambda f, d, r: models.fit_replicate(f, d, replicates=r, confidence_level=LEVEL,
                                                              target="conservative", replicate_policy="strict"),
                         frame, reps)
    rc = {}
    for hid, (m, term) in TERMS.items():
        formula = M1 if m == "m1" else M2
        covs = ["pov_rate"] if m == "m1" else ["pov_rate", "pct_bachelors", "no_vehicle", "cost_burden"]
        res = models.regression_calibration(formula, frame, covs, confidence_level=LEVEL, n_boot=200, seed=20)
        rc[hid] = coef(res, term, "se_total")
    summary["E1"] = {"naive_fit_replicate_conservative": naive, "regression_calibration": rc}

    # E2: without New York City; per state
    nyc = frame["GEOID"].str[:5].isin(NYC)
    e2 = {"without_nyc": hyp_table(eiv, *subset(frame, reps, ~nyc))[0]}
    for s, name in STATES.items():
        f_s, r_s = subset(frame, reps, frame["GEOID"].str[:2] == s)
        e2[name] = {hid: coef(eiv(M1.replace(f" + {ST}", "") if m == "m1" else M2.replace(f" + {ST}", ""),
                                  f_s, r_s), term, "se_total")
                    for hid, (m, term) in TERMS.items()}
    summary["E2"] = e2

    # E3: crude prevalence instead of age-standardized
    fc, rcr = crude(frame, reps)
    summary["E3_crude"] = {hid: coef(eiv((M1 if m == "m1" else M2).replace("asdp ~", "crude ~"), fc, rcr), term,
                                     "se_total") for hid, (m, term) in TERMS.items()}

    # E4: drop CV-flagged outcome rows; household-weighted
    flagged = frame["asdp_cv"] > 30
    summary["E4"] = {"drop_cv_flagged": hyp_table(eiv, *subset(frame, reps, ~flagged))[0],
                     "n_flagged": int(flagged.sum())}
    fw = frame.copy()
    fw["hh_weight"] = fw["hh_total"] / fw["hh_total"].mean()
    summary["E4"]["household_weighted"] = hyp_table(eiv, fw, reps, model="wls", weights="hh_weight")[0]

    # E5: Moran's I of m2 residuals, per state
    m2 = fits["m2"]
    res_frame = frame.copy()
    used = res_frame[np.isfinite(res_frame[need].to_numpy(float)).all(axis=1)].reset_index(drop=True)
    b = m2.coefficients.set_index("term")["estimate"]
    import patsy
    X = patsy.dmatrix(M2.split("~")[1], used, return_type="dataframe")
    used["resid_m2"] = used["asdp"].to_numpy(float) - X.to_numpy(float) @ b.reindex(X.columns).to_numpy(float)
    summary["E5"] = {}
    figs = out_dir / "figures"
    for s, name in STATES.items():
        part = out_dir / f"resid_{s}.csv"
        used.loc[used.GEOID.str[:2] == s, ["GEOID", "resid_m2"]].to_csv(part, index=False)
        r = workflows_geo.spatial_autocorrelation(str(part), "resid_m2", "tract", 2024)
        summary["E5"][name] = {"global": r.get("global"), "error": r.get("error")}

    # E5b: registered models with county-clustered sandwich SEs (residuals are spatially autocorrelated)
    fcl = frame.copy()
    fcl["county"] = fcl["GEOID"].str[:5]
    summary["E5_county_clustered"] = hyp_table(eiv, fcl, reps, cluster="county")[0]

    # E6: maps
    summary["E6"] = {}
    labels = {"asdp": "Age-standardized disability prevalence, % (2000 U.S. standard)",
              "no_vehicle": "Households with no vehicle, %",
              "cost_burden": "Households paying 30%+ of income for housing, %"}
    for s, name in STATES.items():
        part = out_dir / f"tracts_{s}.csv"
        frame[frame.GEOID.str[:2] == s].to_csv(part, index=False)
        for v, lab in labels.items():
            m = workflows_geo.make_map(str(part), v, "tract", 2024, se_col=f"{v}_se",
                                       output_dir=str(figs / f"{v}_{s}"), label=lab,
                                       data_source=f"ACS 5-year 2020-2024; exploratory; manifest {h[:12]}")
            summary["E6"][f"{v} {name}"] = {k: m.get(k) for k in ("success", "paths", "error")}

    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    print(json.dumps({k: summary[k] for k in ("registered_refit", "E1", "E2", "E3_crude", "E4",
                                              "E5_county_clustered")}, indent=1,
                     default=str))


if __name__ == "__main__":
    main(*sys.argv[1:3])
