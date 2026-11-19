# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 36 exploratory example: an MI/NY county deprivation index from Round 21b's ACS measures.

Exploratory; author self-review, not independent. Cached, checksum-verified R21b inputs (ACS
columns only; the outcome is never an indicator). Usage: scripts/r36_index_example.py STUDIES_ROOT OUT_DIR
"""
import json
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'scripts'))
from census.composite_index import build_index
from census.results import _jsonable
from r30_posthoc_im_acs import load_verified

INDICATORS = ["pov_rate", "no_vehicle", "cost_burden", "pct_bachelors"]


def main(studies_root, out_dir):
    warnings.simplefilter("ignore")
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=False)
    _, _, data, _ = load_verified(Path(studies_root)/'r21b/confirmatory', 'r21b_mi_ny_county_premature_mortality.json')
    frame, reps = data['analysis_frame'], data['replicates']
    frame['GEOID'] = frame['GEOID'].astype(str)
    res = {}
    for method in ("pca", "equal"):
        res[method] = build_index(frame, INDICATORS, replicates=reps, method=method, reverse=["pct_bachelors"],
                                  outcome="prem_mort", typology_k=4 if method == "pca" else None)
    (out/"results.json").write_text(json.dumps(_jsonable(res), indent=2, default=str)+"\n")
    p = res["pca"]; t = p["table"]
    print("loadings", p["loadings"], "explained", p["explained_variance"], "alpha", p["cronbach_alpha"])
    print(t.head(6).to_string()); print(t.tail(3).to_string())
    print("median se", t.se.median(), "stability median", t.quintile_stability.median(), "share stable >= .8", (t.quintile_stability >= .8).mean())
    print("typology", p["typology"])
    import numpy as np
    eq = res["equal"]["table"].set_index("area").score
    print("pca-equal score correlation", np.corrcoef(t.set_index("area").score.loc[eq.index], eq)[0, 1])


if __name__ == "__main__":
    main(*sys.argv[1:3])
