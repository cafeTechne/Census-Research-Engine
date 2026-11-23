# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 96 exploratory example: BYM2 drug-overdose relative risks for Michigan counties, 2018-2022.

Exploratory; author self-review, not independent; not a registered study. Observed deaths: the owner's county
WONDER manual export (Underlying Cause, drug overdose X40-X44, X60-X64, X85, Y10-Y14, 2018-2022); suppressed counties
(1-9) enter as missing and are predicted from neighbours. Expected deaths: national age x sex rates (owner's national
export, same years) applied to each county's ACS 2018-2022 age x sex mix (B01001) and its WONDER person-years
(census.wonder_reference.expected_counts). Queen contiguity on 2020 county boundaries, with nearest bridge edges
joining separate parts. Only relative risks, intervals and exceedance probabilities are written; no counts.
Writes docs/audits/r96_disease_mapping_example.md.

Usage: scripts/r96_disease_mapping_example.py
"""
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pandas as pd  # noqa: E402

from census.api import CensusAPIClient  # noqa: E402
from census.vital_records import read_wonder_export  # noqa: E402
from census.wonder_reference import acs_band_populations, expected_counts  # noqa: E402
from census.workflows_geo import spatial_model  # noqa: E402

W = ROOT/"external_data/wonder/ucd/2018-2022"


def main(out_dir):
    warnings.simplefilter("ignore")
    ex = read_wonder_export(str(W/"county/drug_overdose.tsv"))["rows"]
    ex = ex[ex.GEOID.str.startswith("26")].set_index("GEOID")
    c = CensusAPIClient()
    d = c.fetch(2022, "26", "B01001", geo_level="county")
    if d is None:
        raise SystemExit(c.last_error)
    b = pd.DataFrame(d[1:], columns=d[0]).loc[:, lambda x: ~x.columns.duplicated()]
    b.index = b.state+b.county
    bands = acs_band_populations(b)
    E = expected_counts(bands, str(W/"national_age_sex/drug_overdose.tsv"), person_years=ex.population)
    f = pd.DataFrame({"GEOID": ex.index, "deaths": ex.deaths.to_numpy(), "expected": E.reindex(ex.index).to_numpy()})
    Path(out_dir).mkdir(parents=True, exist_ok=False)
    p = Path(out_dir)/"frame.csv"; f.to_csv(p, index=False)
    r = spatial_model(str(p), "disease_map", "county", 2020, outcome="deaths", expected="expected", threshold=1.2,
                      output_path=str(Path(out_dir)/"rr.csv"))
    if not r["success"]:
        raise SystemExit(r["error"])
    t = pd.read_csv(Path(out_dir)/"rr.csv", dtype={"GEOID": str})
    pc = "p_exceed"
    top = t.sort_values("relative_risk", ascending=False).head(8)
    L = ["# Round 96 example: BYM2 drug-overdose relative risks, Michigan counties, 2018-2022 (exploratory)", "",
         "Author self-review, not independent; not a registered study. Observed deaths from the owner's county WONDER "
         "export; expected deaths from national age x sex rates and each county's ACS age x sex mix and WONDER "
         "person-years. Only smoothed relative risks, intervals and probabilities are shown (no counts).", "",
         f"{len(t)} counties; {int((~t.count_used).sum())} with suppressed counts predicted from neighbours; "
         f"{int((t[pc] >= .8).sum())} with P(RR > 1.2) >= .8; {int((t[pc] <= .2).sum())} with P(RR > 1.2) <= .2.", "",
         "Highest smoothed relative risks:", "", "| County | RR | 90% interval | P(RR > 1.2) | Count used |",
         "| :--- | ---: | :--- | ---: | :--- |"]
    L += [f"| {x.GEOID} | {x.relative_risk:.2f} | {x.ci_lower:.2f}-{x.ci_upper:.2f} | {x[pc]:.2f} | "
          f"{'yes' if x.count_used else 'no (suppressed)'} |" for _, x in top.iterrows()]
    L += ["", "Notes: " + " ".join(r["notes"]), ""]
    (ROOT/"docs/audits/r96_disease_mapping_example.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main(sys.argv[1])
