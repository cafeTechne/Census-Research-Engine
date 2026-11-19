# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 33 exploratory example: rank methods on MI/NY county poverty (ACS 2018-2022).

Exploratory; author self-review, not independent. Input: the Round 31 example archive
``r31_example_outputs.tar.gz`` (ACS-only county frame and replicates). No network.

Usage: scripts/r33_rank_methods_example.py R31_ARCHIVE OUT_DIR
"""
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

from census.correlation import validated_correlations
from census.group_compare import compare_groups
from census.results import _jsonable


def main(archive, out_dir):
    warnings.simplefilter("ignore")
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory() as tmp, tarfile.open(archive) as tar:
        tar.extractall(tmp, filter="data")
        frame = pd.read_parquet(Path(tmp)/"r31ex/frame.parquet")
        reps = pd.read_parquet(Path(tmp)/"r31ex/replicates.parquet")
    frame["log_population"] = np.log(frame.acs_population)
    res = {
        "spearman_poverty_population": validated_correlations(frame, ["poverty", "log_population"], "spearman"),
        "kendall_poverty_population": validated_correlations(frame, ["poverty", "log_population"], "kendall"),
        "pearson_poverty_share65_replicates": validated_correlations(frame, ["poverty", "share65"], "pearson", reps),
        "pearson_poverty_share65_no_replicates": validated_correlations(frame, ["poverty", "share65"], "pearson"),
    }
    two = frame[frame.metro_class.isin(["nonmetro", "large_metro"])]
    sup = compare_groups(two, "poverty", "metro_class", design="two_group", method="rank", reference_group="large_metro")
    kw = compare_groups(frame, "poverty", "metro_class", method="rank", reference_group="nonmetro")
    anc = compare_groups(frame, "poverty", "metro_class", design="ancova", covariates=["share65"], replicates=reps,
                         reference_group="nonmetro")
    res["superiority_nonmetro_vs_large_metro"] = dict(summary=sup.summary(), effect=sup.effect_sizes, omnibus=sup.omnibus)
    res["kruskal_wallis_metro_class"] = dict(summary=kw.summary(), effect=kw.effect_sizes, omnibus=kw.omnibus)
    res["ancova_diagnostics"] = anc.diagnostics.get("model")
    (out/"results.json").write_text(json.dumps(_jsonable(res), indent=2, default=str)+"\n")
    for k, v in res.items():
        print(k, v if not isinstance(v, pd.DataFrame) else v[["estimate", "ci_lower", "ci_upper", "variant", "validated"]].to_dict("records"))


if __name__ == "__main__":
    main(*sys.argv[1:3])
