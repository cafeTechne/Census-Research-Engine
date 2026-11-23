# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 97 exploratory example: spatial vs random cross-validation and MAUP sensitivity, Wayne County tracts.

Exploratory; author self-review, not independent; not a registered study. The Round 93 frame (ACS 2019-2023 tracts:
percent below poverty, unemployment rate, percent with a bachelor's degree; scripts/r93_spatial_models_example.py).
(a) 5-fold spatial-block and random cross-validation of poverty ~ unemployment + education (OLS, and OLS with
neighbour residual smoothing). (b) MAUP: the poverty-on-unemployment slope over 100 random contiguous zonings of
about 10 tracts. Writes docs/audits/r97_model_assessment_example.md.

Usage: scripts/r97_model_assessment_example.py OUT_DIR
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/"scripts"))

from census.workflows_geo import spatial_model  # noqa: E402
from r93_spatial_models_example import frame  # noqa: E402


def main(out):
    od = Path(out); od.mkdir(parents=True, exist_ok=False)
    p = od/"wayne.csv"; frame().to_csv(p, index=False)
    cv = spatial_model(str(p), "cv", "tract", 2023, outcome="pov", predictors=["unemp", "ba"], output_path=str(od/"cv.csv"))
    mp = spatial_model(str(p), "maup", "tract", 2023, outcome="pov", predictors=["unemp"], output_path=str(od/"maup.csv"))
    for r in (cv, mp):
        if not r["success"]:
            raise SystemExit(r["error"])
    o, k = cv, cv["ols_knn"]
    row = lambda name, r: (f"| {name} | {r['spatial_block']['rmse']:.2f} | {r['random']['rmse']:.2f} | "  # noqa: E731
                           f"{r['spatial_block']['coverage']:.2f} | {r['random']['coverage']:.2f} | "
                           f"{r['spatial_block']['crps']:.2f} | {r['random']['crps']:.2f} |")
    L = ["# Round 97 example: spatial vs random cross-validation and MAUP, Wayne County tracts (exploratory)", "",
         f"Author self-review, not independent; not a registered study. ACS 2019-2023, {o['n']} Wayne County tracts; "
         "poverty (%) ~ unemployment (%) + bachelor's degree (%).", "",
         "| Model | RMSE, spatial blocks | RMSE, random folds | 90% coverage, blocks | Coverage, random | CRPS, blocks | CRPS, random |",
         "| :--- | ---: | ---: | ---: | ---: | ---: | ---: |", row("OLS", o), row("OLS + neighbour residuals", k), "",
         "Random folds look better for the model that borrows from neighbours; spatial blocks are the more honest "
         "(and still optimistic) guide to error in areas without nearby data.", "",
         f"**MAUP:** tract-level slope of poverty on unemployment {mp['area_slope']:.2f}; over 100 random contiguous "
         f"zonings of about 10 tracts the zone-level slope ranged {mp['zone_slopes']['p05']:.2f} to "
         f"{mp['zone_slopes']['p95']:.2f} (5th-95th percentile; mean {mp['zone_slopes']['mean']:.2f}).", ""]
    (ROOT/"docs/audits/r97_model_assessment_example.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main(sys.argv[1])
