# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 58 exploratory example: OH/PA county child poverty with SCPC spatial intervals.

Exploratory; author self-review, not independent; no registration. Same frame as Round 54
(scripts/r54_ohpa_im_example.py: cached 2024 county B17001/B19013/B23025 for OH and PA). OLS of the child poverty
rate on log median income and the unemployment rate: HC3, IM-8 (not validated outside MI/NY) and SCPC (validated
for OLS on MI/NY and OH/PA, Round 58; rho_bar .05 and the more conservative .10). Coordinates are the Round 44
OH/PA representative points. ACS only.

Usage: scripts/r58_scpc_example.py CACHE_DB OUT_DIR
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/"scripts"))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import r54_ohpa_im_example as r54  # noqa: E402
from census.scpc import fit_scpc  # noqa: E402


def main(cache_db, out_dir):
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=False)
    f = r54.frame(cache_db)
    g = json.loads((ROOT/"docs/audits/ohpa_geometry.json").read_text())["coordinates"]
    coords = pd.DataFrame(dict(GEOID=g["GEOID"], lon=g["lon"], lat=g["lat"]))
    rows = []
    for rho in (.05, .10):
        r = fit_scpc("child_poverty ~ log_income + unemployment", f, coords=coords, rho_bar=rho)
        for _, t in r["table"].iterrows():
            rows.append(dict(method=f"SCPC rho_bar {rho} (q {t.q}, cv {t.cv:.2f})", term=t.term, estimate=t.estimate,
                             lower=t.lower, upper=t.upper, validated=r["validated"]))
    prev = pd.read_csv(Path(out_dir).parent/"r54_example"/"slopes.csv") if (Path(out_dir).parent/"r54_example"/"slopes.csv").exists() else None
    out = pd.DataFrame(rows); out.to_csv(out_dir/"scpc_slopes.csv", index=False)
    print(out.round(3).to_string(index=False))
    if prev is not None:
        print(prev.round(3).to_string(index=False))
    (out_dir/"summary.json").write_text(json.dumps(dict(counties=int(len(f))), indent=1)+"\n")


if __name__ == "__main__":
    main(*sys.argv[1:3])
