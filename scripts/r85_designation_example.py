# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 85 exploratory example: designating Michigan tracts with poverty at least 20% (2019-2023 ACS, S1701).

Exploratory; author self-review, not independent. Tracts with a published 0% or 100% or a zero MOE are left out
(their effective sample size is undefined). Fay-Herriot posterior probabilities (no covariates); expected accuracy
of the four rules (exploratory). Writes docs/audits/r85_designation_example.md.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pandas as pd  # noqa: E402

from census.api import CensusAPIClient  # noqa: E402
from census.designation import designation_accuracy  # noqa: E402


def main():
    d = CensusAPIClient().fetch(2023, "26", "S1701", geo_level="tract", dataset="subject")
    f = pd.DataFrame(d[1:], columns=d[0]).loc[:, lambda x: ~x.columns.duplicated()]
    f = pd.DataFrame({"GEOID": f.state+f.county+f.tract, "pov": pd.to_numeric(f["S1701_C03_001E"], errors="coerce"),
                      "pov_se": pd.to_numeric(f["S1701_C03_001M"], errors="coerce")/1.645}).dropna()
    f = f[(f.pov > 0) & (f.pov < 100) & (f.pov_se > 0)]
    r = designation_accuracy(f, "pov", 20, se_col="pov_se")
    a = r["areas"]
    L = ["# Round 85 example: designating Michigan tracts with poverty of at least 20% (2019-2023 ACS)", "",
         f"Exploratory; author self-review, not independent. {len(f)} tracts; expected number truly at or above 20%: "
         f"{r['expected_qualifying']:.0f}. Probabilities are Fay-Herriot posteriors (validated); expected accuracy is "
         "exploratory.", "", "| Rule | Designated | Expected sensitivity | Expected specificity | Expected PPV | Expected NPV |",
         "| :--- | ---: | ---: | ---: | ---: | ---: |"]
    for x in r["rules"].itertuples():
        L.append(f"| {x.rule} | {x.designated} | {x.sensitivity:.3f} | {x.specificity:.3f} | {x.ppv:.3f} | {x.npv:.3f} |")
    changed = int((a.designated_point != a.designated_prob80).sum())
    L += ["", f"Tracts whose status differs between the point rule and the probability-.8 rule: {changed}. Tracts with "
          f"a point estimate at or above 20% but a probability below .5 of truly being there: "
          f"{int(((a.estimate >= 20) & (a.probability_above < .5)).sum())}.", ""]
    (ROOT/"docs/audits/r85_designation_example.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
