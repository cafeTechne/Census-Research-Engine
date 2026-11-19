# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 34 exploratory example: Michigan counties ranked by poverty rate, ACS 2018-2022.

Exploratory; author self-review, not independent. Input: the v0.26.0 attachment
``r29_study_outputs.tar.gz`` (ACS columns only; checksums verified). No network.

Usage: scripts/r34_ranking_example.py R29_ARCHIVE OUT_DIR
"""
import hashlib
import json
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pandas as pd

from census.ranking import compare_to_reference, rank_intervals
from census.results import _jsonable


def main(archive, out_dir):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=False)
    base = "r29/mi_ny/confirmatory/"
    names = [base+"bundle/results/run.json", base+"analysed/analysis_frame.parquet", base+"analysed/replicates.parquet"]
    with tempfile.TemporaryDirectory() as tmp, tarfile.open(archive) as tar:
        tar.extractall(tmp, members=[tar.getmember(n) for n in names], filter="data")
        run = json.loads((Path(tmp)/names[0]).read_text())
        for key, name in (("analysis_frame", names[1]), ("replicates", names[2])):
            if hashlib.sha256((Path(tmp)/name).read_bytes()).hexdigest() != run["analysed_data"][key]["sha256"]:
                raise ValueError(f"checksum mismatch for {key}")
        frame = pd.read_parquet(Path(tmp)/names[1])[["GEOID", "Year", "poverty", "pov_total"]]
        reps = pd.read_parquet(Path(tmp)/names[2])
    frame = frame[frame.GEOID.str.startswith("26")].reset_index(drop=True)
    for c in ("poverty", "pov_total"):
        frame[c] = pd.to_numeric(frame[c])
    reps = reps[(reps.variable == "poverty") & reps.GEOID.str.startswith("26")]
    ind = rank_intervals(frame, "poverty", replicates=reps)
    joint = rank_intervals(frame, "poverty", replicates=reps, joint=True)
    holm = compare_to_reference(frame, "poverty", replicates=reps, weights="pov_total", method="holm")
    sim = compare_to_reference(frame, "poverty", replicates=reps, weights="pov_total", method="simultaneous")
    res = dict(individual=ind, joint=joint, versus_state_holm=holm, versus_state_simultaneous=sim)
    (out/"results.json").write_text(json.dumps(_jsonable(res), indent=2, default=str)+"\n")
    t = ind["table"]; tj = joint["table"].set_index("area")
    print("K", ind["K"], "median width", ind["median_interval_width"], "joint", joint["median_interval_width"])
    print("surely top decile", ind["surely_top_decile"], joint["surely_top_decile"])
    print(t.head(8).assign(joint_lower=lambda d: d.area.map(tj.rank_lower), joint_upper=lambda d: d.area.map(tj.rank_upper)).to_string())
    print(t.tail(3).to_string())
    print("state", holm["reference_value"], "differ holm", holm["n_differ"], "differ sim", sim["n_differ"])
    print(holm["table"].query("differs").assign(dir=lambda d: d.difference > 0).dir.value_counts().to_dict())


if __name__ == "__main__":
    main(*sys.argv[1:3])
