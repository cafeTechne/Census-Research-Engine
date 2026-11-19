# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 40 exploratory example: county poverty by share aged 65+ and metro class, as a share (beta)
and a median model, MI/NY (Round 31 example frame). Usage: scripts/r40_beta_median_example.py R31_ARCHIVE OUT_DIR"""
import json
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd

from census.models import fit_replicate
from census.regression_families import fit_beta, fit_median
from census.results import _jsonable

FORMULA = "C(metro_class, Treatment(reference='nonmetro')) + share65"


def main(archive, out_dir):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory() as tmp, tarfile.open(archive) as tar:
        tar.extractall(tmp, filter="data")
        f = pd.read_parquet(Path(tmp)/"r31ex/frame.parquet")
    f["poverty_share"] = f.poverty/100
    res = dict(beta=fit_beta("poverty_share ~ "+FORMULA, f), median=fit_median("poverty ~ "+FORMULA, f))
    ols = fit_replicate("poverty ~ "+FORMULA, f).coefficients[["term", "estimate", "ci_lower", "ci_upper"]]
    res["ols"] = ols
    (out/"results.json").write_text(json.dumps(_jsonable(res), indent=2, default=str)+"\n")
    for k in ("beta", "median"):
        print(k); print(res[k]["table"][["term", "estimate", "ci_lower", "ci_upper"]].round(4).to_string())
    print("ols"); print(ols.round(4).to_string())


if __name__ == "__main__":
    main(*sys.argv[1:3])
