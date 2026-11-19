# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 31 exploratory example: county poverty by metro class, MI/NY, ACS 2018-2022.

Exploratory; author self-review, not independent; no registration. Inputs (no network):
- ACS county estimates and 80 VRE replicates from the v0.26.0 release attachment
  ``r29_study_outputs.tar.gz`` (only ACS columns are read; checksums verified);
- CBSA membership from the committed fixture ``tests/fixtures/mi_ny_manifest/cbsa_membership.csv``
  (2024 CBSA file, OMB 2023 delineation);
- county coordinates and the fixed k = 8 assignment from ``docs/audits/im_acs_beta_star.json``.

Usage: scripts/r31_group_comparison_example.py ARCHIVE OUT_DIR
"""
import hashlib
import json
import sys
import tarfile
import tempfile
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd

from census.group_compare import compare_groups
from census.variance import REPLICATE_COLUMNS

AGE65 = [f"age_{s}_{b}" for s in ("m", "f") for b in ("65_74", "75_84", "85_plus")]


def load(archive):
    with tempfile.TemporaryDirectory() as tmp, tarfile.open(archive) as tar:
        base = "r29/mi_ny/confirmatory/"
        names = [base+"bundle/results/run.json", base+"analysed/analysis_frame.parquet", base+"analysed/replicates.parquet"]
        tar.extractall(tmp, members=[tar.getmember(n) for n in names], filter="data")
        run = json.loads((Path(tmp)/names[0]).read_text())
        for key, name in (("analysis_frame", names[1]), ("replicates", names[2])):
            if hashlib.sha256((Path(tmp)/name).read_bytes()).hexdigest() != run["analysed_data"][key]["sha256"]:
                raise ValueError(f"checksum mismatch for {key}")
        frame = pd.read_parquet(Path(tmp)/names[1])
        reps = pd.read_parquet(Path(tmp)/names[2])
    keep = ["GEOID", "Year", "poverty", "acs_population"] + AGE65
    frame = frame[keep].copy()
    for c in keep[2:]:
        frame[c] = pd.to_numeric(frame[c])
    reps = reps[reps.variable.isin(["poverty", "acs_population"] + AGE65)].copy()
    return frame, reps, run["manifest_hash"]


def add_share65(frame, reps):
    frame["share65"] = 100*frame[AGE65].sum(axis=1)/frame.acs_population
    wide = {v: reps[reps.variable == v].set_index("GEOID").loc[frame.GEOID, REPLICATE_COLUMNS].to_numpy(float)
            for v in AGE65+["acs_population"]}
    share = 100*sum(wide[v] for v in AGE65)/wide["acs_population"]
    rows = pd.DataFrame(share, columns=REPLICATE_COLUMNS)
    rows.insert(0, "estimate", frame.share65.to_numpy()); rows.insert(0, "variable", "share65")
    rows.insert(0, "Year", frame.Year.to_numpy()); rows.insert(0, "GEOID", frame.GEOID.to_numpy())
    return pd.concat([reps[reps.variable == "poverty"], rows], ignore_index=True)


def metro_class(frame):
    cbsa = pd.read_csv(ROOT/"tests/fixtures/mi_ny_manifest/cbsa_membership.csv", dtype=str)
    f = frame.merge(cbsa[["GEOID", "CBSA", "LSAD"]], on="GEOID", how="left", validate="one_to_one")
    metro = f.LSAD.eq("M1")
    pop = f[metro].groupby("CBSA").acs_population.sum()
    large = f.CBSA.isin(pop[pop >= 1e6].index) & metro
    return np.where(large, "large_metro", np.where(metro, "other_metro", "nonmetro"))


def main(archive, out_dir):
    warnings.simplefilter("ignore")
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=False)
    frame, reps, manifest_hash = load(archive)
    reps = add_share65(frame, reps)
    frame["metro_class"] = metro_class(frame)
    geo = json.loads((ROOT/"docs/audits/im_acs_beta_star.json").read_text())["coordinates"]
    coords = pd.DataFrame({"GEOID": geo["GEOID"], "lon": geo["lon"], "lat": geo["lat"]})
    results = {}
    runs = {
        "oneway_holm": dict(design="oneway", posthoc="holm"),
        "oneway_simultaneous": dict(design="oneway", posthoc="simultaneous"),
        "ancova_share65": dict(design="ancova", covariates=["share65"], posthoc="holm"),
        "oneway_im8": dict(design="oneway", posthoc="holm", spatial_clusters={"k": 8, "method": "im"}, coords=coords),
    }
    for name, kw in runs.items():
        try:
            r = compare_groups(frame, "poverty", "metro_class", replicates=reps, reference_group="nonmetro", **kw)
            results[name] = dict(summary=r.summary(), result=r.to_dict())
        except ValueError as exc:
            results[name] = dict(summary=f"unavailable: {exc}", result=None)
        print(name, "->", results[name]["summary"], flush=True)
    frame.to_parquet(out/"frame.parquet", index=False); reps.to_parquet(out/"replicates.parquet", index=False)
    from census.workflows_inference import compare_groups as tool
    guided = tool(str(out/"frame.parquet"), "poverty", "metro_class", replicates_path=str(out/"replicates.parquet"),
                  reference_group="nonmetro")
    results["mcp_guided"] = {k: guided[k] for k in ("success", "summary", "next_step")}
    meta = dict(source_archive=Path(archive).name, source_manifest_hash=manifest_hash,
                group_sizes=pd.Series(frame.metro_class).value_counts().to_dict(),
                note="Exploratory; author self-review, not independent; ACS columns only")
    (out/"results.json").write_text(json.dumps(dict(meta=meta, results=results), indent=2, default=str)+"\n")
    print(json.dumps(results["mcp_guided"], indent=2))


if __name__ == "__main__":
    main(*sys.argv[1:3])
