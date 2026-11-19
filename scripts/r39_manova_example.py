# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 39 exploratory example: poverty and share aged 65+ by metro class (MANOVA), MI/NY counties.

Input: the Round 31 example archive (ACS-only county frame and replicates). Exploratory.
Usage: scripts/r39_manova_example.py R31_ARCHIVE OUT_DIR
"""
import json
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pandas as pd

from census.count_models import compare_groups_multivariate
from census.group_compare import compare_groups
from census.results import _jsonable


def main(archive, out_dir):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory() as tmp, tarfile.open(archive) as tar:
        tar.extractall(tmp, filter="data")
        frame = pd.read_parquet(Path(tmp)/"r31ex/frame.parquet"); reps = pd.read_parquet(Path(tmp)/"r31ex/replicates.parquet")
    mv = compare_groups_multivariate(frame, ["poverty", "share65"], "metro_class", replicates=reps)
    per = {o: compare_groups(frame, o, "metro_class", replicates=reps, reference_group="nonmetro").summary()
           for o in ("poverty", "share65")}
    means = frame.groupby("metro_class")[["poverty", "share65"]].mean().round(2).to_dict()
    res = dict(multivariate=mv, per_outcome=per, group_means=means)
    (out/"results.json").write_text(json.dumps(_jsonable(res), indent=2, default=str)+"\n")
    print("joint p", mv["p_value"], "pillai", mv["pillai"]["statistic"], mv["pillai"]["p"]); print(per); print(means)


if __name__ == "__main__":
    main(*sys.argv[1:3])
