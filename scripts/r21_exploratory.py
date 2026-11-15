# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 21 pre-specified EXPLORATORY analyses (PLAN_ROUND_21 section 4, E1-E6).

Runs on the data the confirmatory models analysed (``<run>/analysed/``, hashes checked
against ``run.json``) and, for E2, on Round 20's analysed data (hashes checked against its
run.json). Every output is labelled exploratory with the manifest hash. Not confirmatory.

    python scripts/r21_exploratory.py studies_output/r21/confirmatory studies_output/r20/confirmatory \
        studies_output/r21/exploratory
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

LEVEL = 0.90
CL = "GEOID.str[:5]"
ST = "C(GEOID.str[:2])"
CO = "C(GEOID.str[:5])"
FORMULAS = {"H1": f"places_dis ~ acs_dis + {ST}", "H2": f"places_dis ~ acs_dis + {CO}",
            "H3": f"places_dis ~ acs_dis + pct65 + {CO}"}
NYC = ("36005", "36047", "36061", "36081", "36085")
STATES = {"26": "Michigan", "36": "New York"}


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
    for d in data.values():
        d["GEOID"] = d["GEOID"].astype(str)
    return run, data["analysis_frame"], data["replicates"]


def eiv(formula, frame, reps, fixed=("places_dis",), cluster=CL, **kw):
    return models.fit_eiv(formula, frame, reps, confidence_level=LEVEL, replicate_policy="strict",
                          fixed_variables=[f for f in fixed if f in formula.split("~")[0]], cluster=cluster, **kw)


def coef(res, term):
    row = res.coefficients.set_index("term").loc[term]
    out = {"estimate": float(row["estimate"]), "se_total": float(row["se_total"]),
           "ci_lower": float(row["ci_lower"]), "ci_upper": float(row["ci_upper"]), "n": int(res.n_obs)}
    if "naive_estimate" in row:
        out["naive_estimate"] = float(row["naive_estimate"])
    ind = (res.diagnostics or {}).get("se_total_independent")
    if ind:
        out["se_independent"] = float(ind[term])
    return out


def subset(frame, reps, mask):
    keep = set(frame.loc[mask, "GEOID"])
    return frame[mask].reset_index(drop=True), reps[reps["GEOID"].isin(keep)].reset_index(drop=True)


def residuals(res, formula, frame):
    import patsy
    need = [c for c in ("places_dis", "acs_dis", "pct65") if c in formula]
    used = frame[np.isfinite(frame[need].to_numpy(float)).all(axis=1)].reset_index(drop=True)
    X = patsy.dmatrix(formula.split("~")[1], used, return_type="dataframe")
    b = res.coefficients.set_index("term")["estimate"].reindex(X.columns).to_numpy(float)
    used = used.copy()
    used["resid"] = used["places_dis"].to_numpy(float) - X.to_numpy(float) @ b
    return used


def main(run_dir, r20_dir, out_dir):
    run_dir, r20_dir, out_dir = Path(run_dir), Path(r20_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    run, frame, reps = load(run_dir)
    h = run["manifest_hash"]
    summary = {"analysis_status": "exploratory", "related_manifest_hash": h,
               "analysed_data": {k: v["sha256"] for k, v in run["analysed_data"].items()}}
    cc = frame[np.isfinite(frame[["places_dis", "acs_dis", "pct65"]].to_numpy(float)).all(axis=1)]
    summary["descriptives"] = {
        "n_tracts": int(len(cc)),
        **{v: {"mean": float(cc[v].mean()), "sd": float(cc[v].std()), "median_se": float(np.nanmedian(cc[f"{v}_se"]))}
           for v in ("places_dis", "acs_dis", "pct65")},
        "pearson_places_acs": float(np.corrcoef(cc["places_dis"], cc["acs_dis"])[0, 1]),
        "share_of_places_variance_between_counties": float(
            cc.groupby(cc.GEOID.str[:5])["places_dis"].transform("mean").var() / cc["places_dis"].var()),
        "share_of_acs_variance_between_counties": float(
            cc.groupby(cc.GEOID.str[:5])["acs_dis"].transform("mean").var() / cc["acs_dis"].var()),
        "by_state": {STATES[s]: {"n": int((cc.GEOID.str[:2] == s).sum()),
                                 "places_dis": float(cc.loc[cc.GEOID.str[:2] == s, "places_dis"].mean()),
                                 "acs_dis": float(cc.loc[cc.GEOID.str[:2] == s, "acs_dis"].mean())} for s in STATES},
    }

    # E1: registered refit (check), independence vs clustered SE, naive vs corrected
    fits = {hid: eiv(f, frame, reps) for hid, f in FORMULAS.items()}
    summary["E1_registered_refit"] = {hid: coef(r, "acs_dis") for hid, r in fits.items()}
    summary["E1_registered_refit"]["H3_pct65"] = coef(fits["H3"], "pct65")
    summary["reliability"] = {hid: r.diagnostics.get("reliability") for hid, r in fits.items()}

    # E2: Round 20 determinant models with the PLACES outcome, on Round 20's analysed frame
    r20, f20, rep20 = load(r20_dir)
    f20 = f20.merge(frame[["GEOID", "places_dis", "places_dis_se"]], on="GEOID", how="left")
    m1 = "{y} ~ pov_rate + C(GEOID.str[:2])"
    m2 = "{y} ~ pov_rate + pct_bachelors + no_vehicle + cost_burden + C(GEOID.str[:2])"
    e2 = {"related_round20_manifest_hash": r20["manifest_hash"]}
    both = np.isfinite(f20[["places_dis", "asdp"]].to_numpy(float)).all(axis=1)
    fb, rb = subset(f20, rep20, both)
    for y in ("asdp", "places_dis"):
        r_1, r_2 = eiv(m1.format(y=y), fb, rb), eiv(m2.format(y=y), fb, rb)
        e2[y] = {"m1_pov_rate": coef(r_1, "pov_rate"),
                 **{f"m2_{t}": coef(r_2, t) for t in ("pov_rate", "pct_bachelors", "no_vehicle", "cost_burden")}}
    summary["E2_round20_models_places_outcome"] = e2

    # E3: PLACES lack of reliable transportation against ACS no_vehicle (Round 20 frame)
    try:
        states = sorted({g[:2] for g in f20["GEOID"]})
        lt, prov = hs.load_external([{"name": "lacktrpt", "source": "places", "release": 2025,
                                      "measure": "LACKTRPT"}], "tract", states)
        f3 = f20.merge(lt[["GEOID", "lacktrpt", "lacktrpt_se"]], on="GEOID", how="left")
        ok = np.isfinite(f3[["lacktrpt", "no_vehicle"]].to_numpy(float)).all(axis=1)
        f3, r3 = subset(f3, rep20, ok)
        r = eiv("lacktrpt ~ no_vehicle + C(GEOID.str[:2])", f3, r3, fixed=("lacktrpt",))
        nyc = f3["GEOID"].str[:5].isin(NYC)
        fo, ro = subset(f3, r3, ~nyc)
        r_o = eiv("lacktrpt ~ no_vehicle + C(GEOID.str[:2])", fo, ro, fixed=("lacktrpt",))
        summary["E3_lacktrpt"] = {"all": coef(r, "no_vehicle"), "without_nyc": coef(r_o, "no_vehicle"),
                                  "pearson": float(np.corrcoef(f3["lacktrpt"], f3["no_vehicle"])[0, 1]),
                                  "sources": [{k: p[k] for k in ("dataset", "rows_updated_at", "files")}
                                              for p in prov]}
    except Exception as exc:  # noqa: BLE001 - exploratory; recorded
        summary["E3_lacktrpt"] = {"error": f"{type(exc).__name__}: {exc}"}

    # E4: without NYC; per state
    nyc = frame["GEOID"].str[:5].isin(NYC)
    fo, ro = subset(frame, reps, ~nyc)
    summary["E4_without_nyc"] = {hid: coef(eiv(f, fo, ro), "acs_dis") for hid, f in FORMULAS.items()}
    summary["E4_by_state"] = {}
    for s, name in STATES.items():
        fs, rs = subset(frame, reps, frame["GEOID"].str[:2] == s)
        summary["E4_by_state"][name] = {hid: coef(eiv(f.replace(f" + {ST}", ""), fs, rs), "acs_dis")
                                        for hid, f in FORMULAS.items()}

    # E5: maps; E6: Moran's I of m3 residuals
    res3 = residuals(fits["H3"], FORMULAS["H3"], frame)
    res1 = residuals(fits["H1"], FORMULAS["H1"], frame)
    figs = out_dir / "figures"
    summary["E5"], summary["E6"] = {}, {}
    labels = {"places_dis": "PLACES 2025 adult disability, % (model-based, BRFSS 2023)",
              "acs_dis": "ACS 2020-2024 adult disability, % (direct survey estimate)",
              "resid_m1": "PLACES minus fitted from ACS (m1 residual), percentage points"}
    for s, name in STATES.items():
        part = out_dir / f"tracts_{s}.csv"
        sub = frame[frame.GEOID.str[:2] == s].merge(res1[["GEOID", "resid"]].rename(columns={"resid": "resid_m1"}),
                                                     on="GEOID", how="left")
        sub.to_csv(part, index=False)
        for v, lab in labels.items():
            m = workflows_geo.make_map(str(part), v, "tract", 2024,
                                       se_col=f"{v}_se" if f"{v}_se" in sub.columns else None,
                                       output_dir=str(figs / f"{v}_{s}"), label=lab,
                                       data_source=f"CDC PLACES 2025; ACS 5-year 2020-2024; exploratory; manifest {h[:12]}")
            summary["E5"][f"{v} {name}"] = {k: m.get(k) for k in ("success", "paths", "error")}
        rp = out_dir / f"resid_m3_{s}.csv"
        res3.loc[res3.GEOID.str[:2] == s, ["GEOID", "resid"]].to_csv(rp, index=False)
        r = workflows_geo.spatial_autocorrelation(str(rp), "resid", "tract", 2024)
        summary["E6"][name] = {"global": r.get("global"), "error": r.get("error")}

    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("E5", "analysed_data")}, indent=1, default=str))


if __name__ == "__main__":
    main(*sys.argv[1:4])
