# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 73 example (descriptive): replication E (Round 68) through the engine route multilevel_model(groups=["state",
"county"]) instead of the hand-written MixedLM call. Round 68's registered result does not change.

Writes docs/audits/r73_three_level_example.md. Usage: scripts/r73_three_level_example.py
"""
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/"scripts"))
import r68_le_variance_replication as r68  # noqa: E402

from census import workflows_microdata as wm  # noqa: E402


def main():
    d = r68.data()[["GEOID", "e0", "state", "county"]]
    orig = json.loads((ROOT/"docs/audits/r68_le_variance_replication.json").read_text())["primary"]["shares"]
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "e0.parquet"); d.to_parquet(p, index=False)
        out = wm.multilevel_model(p, "e0 ~ 1", ["state", "county"], share_intervals=False)
    if not out["success"]:
        raise SystemExit(out)
    s = out["shares"]
    L = ["# Round 73 example: replication E through `multilevel_model`", "",
         "Descriptive; Round 68's registered result is unchanged. `multilevel_model(input, \"e0 ~ 1\", "
         "[\"state\", \"county\"], share_intervals=False)` on the USALEEP tracts of Round 68.", "",
         f"{out['n']:,} tracts, {out['n_middle']:,} counties, {out['n_top']} top units (48 states and DC).", "",
         "| Level | Round 68 (hand script) | Engine route | Published |", "| :--- | ---: | ---: | ---: |"]
    for k, eng in (("tract", "bottom"), ("county", "middle"), ("state", "top")):
        L.append(f"| {k} | {orig[k]:.2f}% | {100*s[eng]:.2f}% | {r68.PUBLISHED[k]:.1f}% |")
    L += ["", f"Intercept {out['table'][0]['estimate']:.2f} years (90% CI {out['table'][0]['lower']:.2f} to "
          f"{out['table'][0]['upper']:.2f}).", ""]
    (ROOT/"docs/audits/r73_three_level_example.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
