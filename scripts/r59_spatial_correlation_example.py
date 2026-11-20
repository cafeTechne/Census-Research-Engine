# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 59 exploratory example: OH/PA county correlations with and without the spatial (effective-n) correction.

Exploratory; author self-review, not independent; no registration. Round 54's frame (cached 2024 county
B17001/B19013/B23025 for OH and PA; ACS only) and the Round 44 OH/PA representative points. Spearman correlations
of child poverty, unemployment and log median income (validated with and without coords; with coords replicated on
OH/PA in Round 59), and the partial correlation of child poverty and unemployment given log income (no county
replicates are cached for OH/PA, so it is exploratory here: the validated partial interval needs replicates).

Usage: scripts/r59_spatial_correlation_example.py CACHE_DB OUT_DIR
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/"scripts"))
import pandas as pd  # noqa: E402

import r54_ohpa_im_example as r54  # noqa: E402
from census.correlation import validated_correlations  # noqa: E402


def main(cache_db, out_dir):
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=False)
    f = r54.frame(cache_db)
    g = json.loads((ROOT/"docs/audits/ohpa_geometry.json").read_text())["coordinates"]
    coords = pd.DataFrame(dict(GEOID=g["GEOID"], lon=g["lon"], lat=g["lat"]))
    vars_ = ["child_poverty", "unemployment", "log_income"]
    rows = []
    for label, kw in (("independent areas", {}), ("effective n (spatial)", {"coords": coords})):
        s = validated_correlations(f, vars_, "spearman", **kw).assign(method="spearman", analysis=label)
        p = validated_correlations(f, ["child_poverty", "unemployment"], "partial", controls=["log_income"], **kw)
        rows += [s, p.assign(method="partial | log_income", analysis=label)]
    out = pd.concat(rows, ignore_index=True)
    out.to_csv(out_dir/"correlations.csv", index=False)
    cols = ["analysis", "method", "var_a", "var_b", "estimate", "ci_lower", "ci_upper", "validated"]+(["n_eff"] if "n_eff" in out else [])
    print(out[cols].round(3).to_string(index=False))
    (out_dir/"summary.json").write_text(json.dumps(dict(counties=int(len(f))), indent=1)+"\n")


if __name__ == "__main__":
    main(*sys.argv[1:3])
