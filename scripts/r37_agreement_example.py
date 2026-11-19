# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 37 exploratory example: ACS 2018-2022 county population vs Census population estimates (MI/NY).

ACS: the v0.26.0 attachment (acs_population with replicates; checksums verified). Population estimates:
the 'Population' column of the owner's WONDER all-cause county export (summed annual estimates over
2018-2022, divided by 5). Population figures only; no death counts are read or written.
Usage: scripts/r37_agreement_example.py R29_ARCHIVE WONDER_COUNTY_TSV OUT_DIR
"""
import hashlib
import io
import json
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd

from census.agreement import check_agreement
from census.results import _jsonable


def main(archive, wonder_tsv, out_dir):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=False)
    base = "r29/mi_ny/confirmatory/"
    names = [base+"bundle/results/run.json", base+"analysed/analysis_frame.parquet", base+"analysed/replicates.parquet"]
    with tempfile.TemporaryDirectory() as tmp, tarfile.open(archive) as tar:
        tar.extractall(tmp, members=[tar.getmember(n) for n in names], filter="data")
        run = json.loads((Path(tmp)/names[0]).read_text())
        for key, name in (("analysis_frame", names[1]), ("replicates", names[2])):
            if hashlib.sha256((Path(tmp)/name).read_bytes()).hexdigest() != run["analysed_data"][key]["sha256"]:
                raise ValueError("checksum mismatch")
        acs = pd.read_parquet(Path(tmp)/names[1])[["GEOID", "Year", "acs_population"]]
        reps = pd.read_parquet(Path(tmp)/names[2])
    reps = reps[reps.variable == "acs_population"]
    body = open(wonder_tsv).read().partition('\n"---"\n')[0]
    w = pd.read_csv(io.StringIO(body), sep="\t", dtype=str, keep_default_na=False)
    w = w[w["County Code"].str[:2].isin(["26", "36"])][["County Code", "Population"]]
    w = w[w.Population.str.strip() != "Not Available"]
    w["pep_population"] = pd.to_numeric(w.Population)/5
    f = acs.merge(w.rename(columns={"County Code": "GEOID"})[["GEOID", "pep_population"]], on="GEOID", how="inner")
    f["acs_population"] = pd.to_numeric(f.acs_population)
    for c in ("acs_population", "pep_population"):
        f["log_"+c] = np.log(f[c])
    rl = reps.copy(); rl["variable"] = "log_acs_population"
    rl[[f"rep_{k}" for k in range(1, 81)]] = np.log(rl[[f"rep_{k}" for k in range(1, 81)]].astype(float))
    rl["estimate"] = np.log(rl.estimate.astype(float))
    res = check_agreement(f, "log_acs_population", "log_pep_population", replicates=rl)
    (out/"results.json").write_text(json.dumps(_jsonable(res), indent=2, default=str)+"\n")
    print("n", res["n"], "bias (log)", res["bias"], "kappa", res["kappa_quintiles"])
    print("limits observed", res["limits_observed"]); print("error-free", res.get("limits_error_free")); print("ccc", res["ccc"])
    d = f.log_pep_population-f.log_acs_population
    print("largest relative differences", f.assign(d=d).reindex(d.abs().sort_values(ascending=False).index).head(5)[["GEOID", "acs_population", "pep_population", "d"]].to_string())


if __name__ == "__main__":
    main(*sys.argv[1:4])
