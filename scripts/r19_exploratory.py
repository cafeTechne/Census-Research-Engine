# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 19 pre-specified EXPLORATORY analyses (PLAN_ROUND_19 section 3, E1-E4).

Runs on the data the confirmatory models analysed (``<run>/analysed/``, hashes
checked against ``run.json``), with the engine's own tools. Every output is
labelled exploratory with the manifest hash. Not confirmatory evidence.

    python scripts/r19_exploratory.py studies_output/r19/reproduction studies_output/r19/exploratory
"""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from census import models, rpp  # noqa: E402
from census import tract_harmonization as th  # noqa: E402
from census import workflows_geo  # noqa: E402
from census.analysis import REPLICATE_COLUMNS  # noqa: E402
from census.multitest import batch_z_test  # noqa: E402

LEVEL = 0.90
OUTCOME = "mean_hh_income"
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
    return run, data["analysis_frame"], data["replicates"]


SE_FOR_TARGET = {"these_areas": "se_sampling", "conservative": "se_total", "population": "se_model"}


def coef(fitted, term):
    result, target = fitted
    row = result.coefficients.set_index("term").loc[term]
    return {"estimate": float(row["estimate"]), "se": float(row[SE_FOR_TARGET[target]]),
            "ci_lower": float(row["ci_lower"]), "ci_upper": float(row["ci_upper"]), "n": int(result.n_obs)}


def fit(formula, frame, reps, target, **kw):
    return models.fit_replicate(formula, frame, replicates=reps, confidence_level=LEVEL, target=target,
                                replicate_policy="strict", **kw), target


def rescale(frame, reps, factor):
    """Multiply the outcome, its SE and its replicate rows by ``factor`` (Series aligned to frame rows)."""
    frame = frame.copy()
    frame[OUTCOME] = frame[OUTCOME] * factor.to_numpy()
    frame[f"{OUTCOME}_se"] = frame[f"{OUTCOME}_se"] * factor.to_numpy()
    key = frame["GEOID"].astype(str) + "|" + frame["Year"].astype(str)
    by_key = dict(zip(key, factor.to_numpy()))
    reps = reps.copy()
    sel = (reps["variable"] == OUTCOME).to_numpy()
    rkey = reps.loc[sel, "GEOID"].astype(str) + "|" + reps.loc[sel, "Year"].astype(str)
    f = rkey.map(by_key).to_numpy(float)
    cols = ["estimate"] + REPLICATE_COLUMNS
    reps.loc[sel, cols] = reps.loc[sel, cols].to_numpy(float) * f[:, None]
    return frame, reps


def replicate_se(reps, variable):
    sub = reps[reps["variable"] == variable]
    dev = sub[REPLICATE_COLUMNS].to_numpy(float) - sub["estimate"].to_numpy(float)[:, None]
    return pd.DataFrame({"GEOID": sub["GEOID"].astype(str).values, "Year": sub["Year"].astype(int).values,
                         "se_rep": np.sqrt(4 / 80 * (dev ** 2).sum(axis=1))})


def main(run_dir, out_dir):
    run_dir, out_dir = Path(run_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    run, frame, reps = load(run_dir)
    h = run["manifest_hash"]
    frame = frame.dropna(subset=[OUTCOME]).copy()
    frame["state"] = frame["GEOID"].astype(str).str[:2]
    summary = {"analysis_status": "exploratory", "related_manifest_hash": h,
               "exploratory_reason": "pre-specified exploratory analyses (PLAN_ROUND_19 E1-E4); not confirmatory",
               "inputs": run["analysed_data"]}

    # ---- panel balance and the per-tract change ---------------------------------------------
    periods = frame.groupby("GEOID")["Year"].nunique()
    balanced_ids = set(periods[periods == 2].index)
    summary["panel"] = {"tracts": int(len(periods)), "both_periods": len(balanced_ids),
                        "one_period": int((periods == 1).sum())}
    wide = frame[frame["GEOID"].isin(balanced_ids)].pivot(index="GEOID", columns="Year",
                                                          values=[OUTCOME, f"{OUTCOME}_se", "pct_bachelors"])
    se_rep = replicate_se(reps, OUTCOME).set_index(["GEOID", "Year"])["se_rep"]
    change = pd.DataFrame({
        "GEOID": wide.index, "Year": 2024,
        "mean_2019": wide[(OUTCOME, 2019)].values, "mean_2024": wide[(OUTCOME, 2024)].values,
        "change": (wide[(OUTCOME, 2024)] - wide[(OUTCOME, 2019)]).values,
        "pct_bachelors_2019": wide[("pct_bachelors", 2019)].values,
    })
    # independent samples (non-overlapping periods): Var(change) = Var(2024) + Var(2019), replicate SEs
    s19 = se_rep.reindex(list(zip(change["GEOID"], [2019] * len(change)))).to_numpy()
    s24 = se_rep.reindex(list(zip(change["GEOID"], [2024] * len(change)))).to_numpy()
    change["change_se"] = np.sqrt(s19 ** 2 + s24 ** 2)
    change["change_cv"] = 100 * change["change_se"] / change["change"].abs().replace(0, np.nan)
    change["state"] = change["GEOID"].str[:2]
    change_path = out_dir / "tract_change.parquet"
    change.to_parquet(change_path, index=False)
    defined = change["change_se"].notna()
    sig = ((change["change"].abs() / change["change_se"]) > 1.645)[defined]
    up = change.loc[defined, "change"] > 0
    summary["change"] = {
        "tracts": int(len(change)), "tracts_with_change_se": int(defined.sum()),
        "median_change_cv": float(change["change_cv"].median()),
        "mean": float(change["change"].mean()),
        "median": float(change["change"].median()),
        "share_positive": float((change["change"] > 0).mean()),
        "share_distinguishable_from_zero_90": float(sig.mean()),
        "share_up_distinguishable": float((sig & up).mean()),
        "share_down_distinguishable": float((sig & ~up).mean()),
        "median_change_se": float(change["change_se"].median()),
        "by_state": {STATES[s]: {"tracts": int(len(g)), "mean": float(g["change"].mean()),
                                 "median": float(g["change"].median()),
                                 "share_positive": float((g["change"] > 0).mean())}
                     for s, g in change.groupby("state")},
        "path": str(change_path), "sha256": sha256(change_path),
    }

    # ---- E3 sensitivity of H1-H3 -------------------------------------------------------------
    flagged = set(frame.loc[frame[f"{OUTCOME}_cv"] > 30, "GEOID"])
    cpi = {int(r["release"]): float(r["cpi"]["factor"]) for r in run["adjustments"][0]["releases"]
           if isinstance(r.get("cpi"), dict)} or None
    state_rpp = {(s, y): float(rpp.place_parity(s, y)["rpp"]) for s in STATES for y in (2019, 2024)}
    variants = {
        "registered": (frame, reps, {}),
        "drop_cv_flagged_tracts": (frame[~frame["GEOID"].isin(flagged)], reps, {}),
        "balanced_panel": (frame[frame["GEOID"].isin(balanced_ids)], reps, {}),
        "household_weighted_wls": (frame, reps, {"model": "wls", "weights": "households"}),
        "state_rpp_areas": rescale(frame, reps, frame["rpp"] / [state_rpp[(s, y)] for s, y in
                                                               zip(frame["state"], frame["Year"].astype(int))]) + ({},),
    }
    if cpi:
        nominal = frame["rpp"] / 100 / frame["Year"].astype(int).map(cpi)
        variants["nominal_dollars"] = rescale(frame, reps, nominal) + ({},)
    else:
        summary["nominal_dollars_skipped"] = "CPI factors not found in run.json adjustments"
    specs = {"H1": ("mean_hh_income ~ C(Year)", "these_areas", "C(Year)[T.2024]"),
             "H2": ("mean_hh_income ~ C(Year) * pct_bachelors + C(GEOID.str[:2])", "conservative",
                    "C(Year)[T.2024]:pct_bachelors"),
             "H3": ("mean_hh_income ~ C(Year) * C(GEOID.str[:2])", "these_areas",
                    "C(Year)[T.2024]:C(GEOID.str[:2])[T.36]")}
    sens = {}
    for name, (f, r, kw) in variants.items():
        sens[name] = {}
        for hid, (formula, target, term) in specs.items():
            try:
                sens[name][hid] = coef(fit(formula, f, r, target, **kw), term)
            except Exception as exc:  # noqa: BLE001 - a failed variant is reported, not hidden
                sens[name][hid] = {"error": f"{type(exc).__name__}: {exc}"}
    summary["sensitivity"] = sens

    # ---- H2, described per period (the registered test is the interaction) --------------------
    summary["gradient_by_period"] = {
        str(y): coef(fit("mean_hh_income ~ pct_bachelors + C(GEOID.str[:2])", frame[frame["Year"] == y], reps,
                         "conservative"), "pct_bachelors") for y in (2019, 2024)}

    # ---- E4 replicate SE vs independence approximation for apportioned 2019 tracts -------------
    # Composition of each 2020 tract by 2010 source: share of the target's block mass from each source.
    # "Merged" needs a second source with at least 10% of the mass (slivers would dilute the comparison).
    cw = th.crosswalks(2020, list(STATES), ["housing_units"], releases=[2019, 2024])["housing_units"]
    mass = cw.assign(m=cw["part_area"]).groupby(["target_geoid", "source_geoid"])["m"].sum()
    share = mass / mass.groupby(level=0).transform("sum")
    second = share.groupby(level=0).apply(lambda x: x.nlargest(2).iloc[-1] if len(x) > 1 else 0.0)
    whole = cw.groupby("target_geoid")["weight"].max()
    kind = pd.Series(np.where(second >= 0.10, "merged (second source >= 10% of the tract)",
                              np.where(whole.reindex(second.index) >= 0.999, "same tract (weight 1)",
                                       "part of a split 2010 tract (or slivers < 10%)")),
                     index=second.index.astype(str))
    e4 = {}
    for var in ("agg_income", "households"):
        rep = replicate_se(reps, var)
        rep = rep[rep["Year"] == 2019].merge(frame.loc[frame["Year"] == 2019, ["GEOID", f"{var}_se"]], on="GEOID")
        rep["ratio"] = rep["se_rep"] / rep[f"{var}_se"]
        rep["kind"] = rep["GEOID"].map(kind)
        e4[var] = {k: {"tracts": int(len(g)), "median_ratio": float(g["ratio"].median()),
                       "p05": float(g["ratio"].quantile(0.05)), "p95": float(g["ratio"].quantile(0.95)),
                       "share_rep_se_larger_by_10pct": float((g["ratio"] > 1.10).mean())}
                   for k, g in rep.dropna(subset=["ratio"]).groupby("kind")}
    summary["replicate_vs_independence_se_2019"] = e4

    # ---- E1 maps and E2 local Moran's I, one state at a time (engine tools) --------------------
    figs = out_dir / "figures"
    summary["maps"], summary["lisa"] = {}, {}
    for st, name in STATES.items():
        part = out_dir / f"tract_change_{st}.csv"
        change[change["state"] == st].to_csv(part, index=False)
        m = workflows_geo.make_map(str(part), "change", "tract", 2024, se_col="change_se",
                                   output_dir=str(figs / f"change_{st}"), label="Change in real mean household "
                                   "income, 2015-2019 to 2020-2024 (2024 $, RPP-adjusted)",
                                   data_source=f"ACS 5-year 2019 and 2024; exploratory; manifest {h[:12]}")
        summary["maps"][name] = {k: m.get(k) for k in ("success", "summary", "paths", "error")}
        # E1b: per-tract change tests (independent periods; replicate SEs as 90% MOEs), BH across the state
        sub = change[change["state"] == st].copy()
        sub["se_2019"] = s19[(change["state"] == st).to_numpy()]
        sub["se_2024"] = s24[(change["state"] == st).to_numpy()]
        z = batch_z_test(sub.assign(moe_2024=1.645 * sub["se_2024"], moe_2019=1.645 * sub["se_2019"]),
                         "mean_2024", "moe_2024", "mean_2019", "moe_2019", year1=2024, year2=2019,
                         confidence_level=LEVEL, correction="bh")
        z["GEOID"] = sub["GEOID"].values
        zpath = out_dir / f"change_tests_{st}.csv"
        z.to_csv(zpath, index=False)
        sm = workflows_geo.make_map(str(zpath), "change", "tract", 2024, kind="significance",
                                    output_dir=str(figs / f"change_significance_{st}"),
                                    data_source=f"ACS 5-year 2019 and 2024; exploratory; manifest {h[:12]}")
        adj = z["significant_adjusted"].astype("boolean")
        diff = z["mean_2024"] - z["mean_2019"] if "mean_2024" in z else sub["change"].values
        summary["maps"][name + " significance"] = {
            "success": sm.get("success"), "error": sm.get("error"),
            "increase_bh": int((adj.fillna(False) & (pd.Series(diff).values > 0)).sum()),
            "decrease_bh": int((adj.fillna(False) & (pd.Series(diff).values < 0)).sum()),
            "tested": int(adj.notna().sum())}
        lisa_path = out_dir / f"lisa_change_{st}.csv"
        s = workflows_geo.spatial_autocorrelation(str(part), "change", "tract", 2024, local=True,
                                                  output_path=str(lisa_path))
        entry = {"global": s.get("global"), "notes": s.get("local_notes"), "error": s.get("error")}
        if lisa_path.exists():
            lisa = pd.read_csv(lisa_path, dtype={"GEOID": str})
            col = next((c for c in ("quadrant", "cluster", "label") if c in lisa.columns), None)
            sigcol = next((c for c in ("significant", "significant_adjusted") if c in lisa.columns), None)
            if col and sigcol:
                entry["significant_by_quadrant"] = lisa[lisa[sigcol].astype(bool)][col].value_counts().to_dict()
            entry["tracts"] = int(len(lisa))
        summary["lisa"][name] = entry

    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    print(json.dumps({k: summary[k] for k in ("panel", "change", "sensitivity", "gradient_by_period",
                                              "replicate_vs_independence_se_2019")}, indent=1, default=str))


if __name__ == "__main__":
    main(*sys.argv[1:3])
