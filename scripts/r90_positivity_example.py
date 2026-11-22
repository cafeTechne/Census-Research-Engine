# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 90 exploratory example: positivity diagnostics for metro status and county uninsured rates.

Exploratory; author self-review, not independent; not a registered study. MI, NY, OH and PA counties, ACS 2019-2023:
outcome S2701 percent uninsured (C05_001); treatment ERS 2013 metro status; confounders S1701 percent below poverty
and DP05 percent aged 65+. Reports the propensity diagnostics, plain IPW and AIPW, the three weighting options and
the g-formula. Writes docs/audits/r90_positivity_example.md (summary only).

Usage: scripts/r90_positivity_example.py
"""
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pandas as pd  # noqa: E402

from census import causal  # noqa: E402
from census.api import CensusAPIClient  # noqa: E402
from census.context_sources import fetch_ers  # noqa: E402

C = CensusAPIClient()
STATES = {"26": "MI", "36": "NY", "39": "OH", "42": "PA"}


def get(st, table, cols, dataset):
    d = C.fetch(2023, st, table, geo_level="county", dataset=dataset)
    if d is None:
        raise SystemExit(f"{table} {st}: {C.last_error}")
    f = pd.DataFrame(d[1:], columns=d[0]).loc[:, lambda x: ~x.columns.duplicated()]
    f["GEOID"] = f.state+f.county
    return f.set_index("GEOID")[cols].apply(pd.to_numeric, errors="coerce")


def main():
    warnings.simplefilter("ignore")
    parts = []
    for st in STATES:
        u = get(st, "S2701", ["S2701_C05_001E"], "subject"); p = get(st, "S1701", ["S1701_C03_001E"], "subject")
        a = get(st, "DP05", ["DP05_0024PE"], "profile")
        parts.append(u.join(p).join(a))
    f = pd.concat(parts).rename(columns={"S2701_C05_001E": "unins", "S1701_C03_001E": "pov", "DP05_0024PE": "age65"})
    assert f.unins.median() < 20 and 5 < f.age65.median() < 35, "column checks"
    ers, _ = fetch_ers()
    f = f.join(ers["Metro2013"].rename("metro"), how="inner").dropna().reset_index()
    f["metro"] = pd.to_numeric(f.metro).astype(int)
    conf = ["pov", "age65"]
    res = {m: causal.estimate_effect(f, "unins", "metro", conf, method=m) for m in ("ipw", "aipw", "ra")}
    res.update({f"w_{w}": causal.estimate_effect(f, "unins", "metro", conf, weights=w)
                for w in ("stabilized", "truncated", "overlap")})
    d = res["aipw"]["positivity"]
    L = ["# Round 90 example: positivity diagnostics, metro status and county uninsured rates (exploratory)", "",
         "Author self-review, not independent; not a registered study. ACS 2019-2023, MI/NY/OH/PA counties "
         f"(n = {len(f)}, {int(f.metro.sum())} metro). Outcome: percent uninsured (S2701); treatment: ERS 2013 metro "
         "status; confounders: percent below poverty (S1701) and percent aged 65+ (DP05). There is no target trial "
         "here (metro status is not an intervention), so every estimate is associational.", "",
         f"**Positivity:** {d['share_outside']:.1%} of propensities lie outside [.05, .95]; overlap coefficient "
         f"{d['overlap_coefficient']:.2f}; propensity median {d['propensity_quantiles']['treated']['q50']:.2f} "
         f"(metro) and {d['propensity_quantiles']['untreated']['q50']:.2f} (non-metro); effective n "
         f"{d['effective_n']['treated']:.0f} of {d['n']['treated']} (metro) and {d['effective_n']['untreated']:.0f} of "
         f"{d['n']['untreated']} (non-metro); limited overlap: {'yes' if d['limited_overlap'] else 'no'}.", "",
         "| Estimator | Estimand | Estimate (points) | 90% CI | Validated |", "| :--- | :--- | ---: | :--- | :--- |"]
    names = {"ipw": "Plain IPW", "aipw": "AIPW", "ra": "g-formula (regression adjustment)",
             "w_stabilized": "Stabilized weights", "w_truncated": "Truncated weights", "w_overlap": "Overlap weights"}
    for k, r in res.items():
        e = r["ate"]
        L.append(f"| {names[k]} | {e.get('estimand', 'average treatment effect')} | {e['estimate']:.2f} | "
                 f"{e['lower']:.2f} to {e['upper']:.2f} | {'yes' if r['validated'] else 'no'} |")
    ag = res["w_stabilized"]["agreement"]
    L += ["", f"IPW versus g-formula: difference {ag['difference']:.2f}, threshold {ag['threshold']:.2f}, "
          f"{'flagged' if ag['flagged'] else 'not flagged'}.", ""]
    (ROOT/"docs/audits/r90_positivity_example.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
