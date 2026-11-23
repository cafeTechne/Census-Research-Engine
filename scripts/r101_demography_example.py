# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 101 exploratory example: US life expectancy change by age and cause, and age-data quality in Michigan.

Exploratory; author self-review, not independent; not a registered study.
(a) Life expectancy at birth, US, 2013-2017 and 2018-2022, from the owner's national WONDER all-cause exports
    (abridged life tables, Chiang II intervals); Arriaga decomposition of the change by age band and by the
    underlying causes on file (heart disease, cancer, unintentional injury, suicide, liver disease, diabetes,
    stroke, CLRD, kidney disease; overdose, firearm and alcohol-induced overlap other categories and are reported
    separately as a share of the change).
(b) Whipple, Myers and UN age-sex accuracy indices for Michigan: 2020 Census single-year ages (DHC PCT12, exact) and
    the 2019-2023 PUMS (weighted, replicate SEs).
Writes docs/audits/r101_demography_example.md.

Usage: scripts/r101_demography_example.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from census.api import CensusAPIClient  # noqa: E402
from census.demography import age_quality, age_quality_pums, arriaga_from_wonder  # noqa: E402
from census.pums import fetch_pums  # noqa: E402

W = ROOT/"external_data/wonder/ucd"
EXCLUSIVE = ["heart_disease", "cancer", "unintentional_injury", "suicide", "liver_disease", "diabetes", "stroke", "clrd",
             "kidney_disease"]


def dhc_ages():
    c = CensusAPIClient()
    d = c._get_json("https://api.census.gov/data/2020/dec/dhc", {"get": "group(PCT12)", "for": "state:26", "key": c.api_key})
    if d is None:
        raise SystemExit(c.last_error)
    row = dict(zip(d[0], d[1]))
    m = {a: int(row[f"PCT12_{3+a:03}N"]) for a in range(100)}; f = {a: int(row[f"PCT12_{107+a:03}N"]) for a in range(100)}
    tot = {a: m[a]+f[a] for a in range(100)}
    five = lambda s: [sum(s[a+i] for i in range(5)) for a in range(0, 75, 5)]  # noqa: E731
    return tot, five(m), five(f)


def main():
    p = lambda per, c: str(W/per/"national_age_sex"/f"{c}.tsv")  # noqa: E731
    r = arriaga_from_wonder(p("2013-2017", "all_causes"), p("2018-2022", "all_causes"),
                            {c: p("2013-2017", c) for c in EXCLUSIVE}, {c: p("2018-2022", c) for c in EXCLUSIVE})
    tot = r["by_age_cause"].sum(0).sort_values()
    L = ["# Round 101 example: US life expectancy change and Michigan age-data quality (exploratory)", "",
         "Author self-review, not independent; not a registered study.", "",
         f"## Life expectancy at birth, United States (owner's national WONDER exports)", "",
         f"e0 2013-2017: {r['e0_1']:.2f} years; 2018-2022: {r['e0_2']:.2f} years; change {r['difference']:+.2f} years "
         "(Chiang II 90% intervals are about +/-0.01 at national scale).", "",
         "Arriaga decomposition by age band (years of e0):", "", "| Age | Contribution |", "| :--- | ---: |"]
    L += [f"| {a} | {v:+.3f} |" for a, v in r["by_age"].items()]
    L += ["", "By underlying cause (mutually exclusive ICD-10 chapters on file; 'other' is the remainder):", "",
          "| Cause | Contribution |", "| :--- | ---: |"] + [f"| {k.replace('_', ' ')} | {v:+.3f} |" for k, v in tot.items()]
    L += ["", "'Other' includes COVID-19 (U07.1, 2020-2022), which has no export of its own here and accounts for most "
          "of it. Notes: "+" ".join(r["notes"]), ""]
    t, m5, f5 = dhc_ages()
    q1 = age_quality(t, m5, f5)
    df = fetch_pums("26", 2023, columns=["AGEP", "SEX"])
    q2 = age_quality_pums(df)
    L += ["## Age-data quality, Michigan", "", "| Source | Whipple | Myers | UN age-sex accuracy |", "| :--- | ---: | ---: | ---: |",
          f"| 2020 Census (DHC PCT12) | {q1['whipple']:.1f} | {q1['myers']:.2f} | {q1['un_age_sex_accuracy']['index']:.1f} |",
          f"| PUMS 2019-2023 (weighted; SE) | {q2['whipple']:.1f} ({q2['whipple_se']:.1f}) | {q2['myers']:.2f} ({q2['myers_se']:.2f}) | "
          f"{q2['un_age_sex_accuracy']:.1f} ({q2['un_se']:.1f}) |", "",
          "Whipple near 100 and Myers near 0 mean no detectable age heaping; the UN index mixes real cohort-size "
          "variation (baby boom, migration) with error, so values above 20 do not by themselves indicate bad data in "
          "a population with uneven birth cohorts.", ""]
    (ROOT/"docs/audits/r101_demography_example.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
