# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 68: replication E, Boing et al. (2020) headline shares of life-expectancy variation (frozen with the
criterion, docs/audits/r68_replication_criterion.md).

USALEEP 2010-2015 A files for every covered state (all FIPS except Maine 23 and Wisconsin 55, plus NYC), every tract
with e(0). Three-level REML null model e0 = mu + u_state + v_county + e_tract (statsmodels MixedLM: groups = state,
variance component = county). Shares = variance / sum. Rule: each share within 5 points of the published 70.4
(tract), 10.7 (county), 19.0 (state) and order tract > state > county.

Usage: scripts/r68_le_variance_replication.py --criterion-commit SHA    (or --fetch-only)
"""
import argparse
import json
import subprocess
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import statsmodels.formula.api as smf  # noqa: E402

from census import health_sources  # noqa: E402

STATES = ["01", "02", "04", "05", "06", "08", "09", "10", "11", "12", "13", "15", "16", "17", "18", "19", "20", "21",
          "22", "24", "25", "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37", "38", "39",
          "40", "41", "42", "44", "45", "46", "47", "48", "49", "50", "51", "53", "54", "56"]
PUBLISHED = {"tract": 70.4, "county": 10.7, "state": 19.0}
TOL = 5.0
FROZEN = ["scripts/r68_le_variance_replication.py", "docs/audits/r68_replication_criterion.md"]
OUT = ROOT/"docs/audits/r68_le_variance_replication"


def data():
    rows = health_sources.fetch_usaleep(STATES)["rows"]
    le, _ = health_sources.parse_usaleep(rows, "le", include_predicted=True)
    d = le[le["le"].notna()].copy()
    d["e0"] = d["le"].astype(float); d["state"] = d.GEOID.str[:2]; d["county"] = d.GEOID.str[:5]
    return d


def three_level(d, y):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = smf.mixedlm(f"{y} ~ 1", d, groups="state", vc_formula={"county": "0 + C(county)"},
                        re_formula="1").fit(reml=True, method=["lbfgs", "powell"])
    v = dict(state=float(m.cov_re.iloc[0, 0]), county=float(m.vcomp[0]), tract=float(m.scale))
    tot = sum(v.values())
    return dict(variances=v, shares={k: 100*x/tot for k, x in v.items()}, converged=bool(m.converged))


def two_level(d, y, g):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = smf.mixedlm(f"{y} ~ 1", d, groups=g).fit(reml=True)
    a, b = float(m.cov_re.iloc[0, 0]), float(m.scale)
    return {g: 100*a/(a+b), "tract": 100*b/(a+b)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--criterion-commit"); ap.add_argument("--fetch-only", action="store_true")
    a = ap.parse_args()
    if a.fetch_only:
        d = data(); print(len(d), "tracts,", d.county.nunique(), "counties,", d.state.nunique(), "states"); return
    subprocess.run(["git", "merge-base", "--is-ancestor", a.criterion_commit, "HEAD"], cwd=ROOT, check=True)
    for rel in FROZEN:
        if subprocess.check_output(["git", "show", a.criterion_commit+":"+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
            raise SystemExit("differs from criterion commit: "+rel)
    d = data(); d["ln_e0"] = np.log(d.e0)
    main_fit = three_level(d, "e0")
    s = main_fit["shares"]
    order = s["tract"] > s["state"] > s["county"]
    within = all(abs(s[k]-PUBLISHED[k]) <= TOL for k in PUBLISHED)
    outcome = "replicated" if (order and within) else ("partly replicated" if order else "not replicated")
    res = dict(criterion_commit=a.criterion_commit, tracts=int(len(d)), counties=int(d.county.nunique()),
               states=int(d.state.nunique()), primary=main_fit, published=PUBLISHED, outcome=outcome,
               secondary=dict(log_e0=three_level(d, "ln_e0"), tract_in_county=two_level(d, "e0", "county"),
                              tract_in_state=two_level(d, "e0", "state")))
    OUT.with_suffix(".json").write_text(json.dumps(res, indent=1)+"\n")
    L = ["# Round 68 replication E: shares of life-expectancy variation", "",
         f"Criterion commit: `{a.criterion_commit}`. {res['tracts']:,} tracts, {res['counties']:,} counties, "
         f"{res['states']} states and DC (paper: 65,662; 3,020; 48 + DC).", "",
         "| Level | Published share | Ours (e0) | Ours (ln e0) |", "| :--- | ---: | ---: | ---: |"]
    for k in ("tract", "county", "state"):
        L.append(f"| {k} | {PUBLISHED[k]:.1f}% | {s[k]:.1f}% | {res['secondary']['log_e0']['shares'][k]:.1f}% |")
    L += ["", f"Converged: {main_fit['converged']}. **Outcome: {outcome}** (each share within {TOL:g} points and "
          "order tract > state > county).", ""]
    OUT.with_suffix(".md").write_text("\n".join(L))
    print(outcome, {k: round(v, 1) for k, v in s.items()})


if __name__ == "__main__":
    main()
