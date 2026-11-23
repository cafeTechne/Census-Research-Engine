# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 100 exploratory example: Michigan tract median household income with withheld values, imputed by FCS.

Exploratory; author self-review, not independent; not a registered study. ACS 2019-2023 Michigan tracts: median
household income (B19013, withheld "jam" values such as -666666666 treated as missing), percent below poverty
(S1701_C03_001) and percent with a bachelor's degree (S1501_C02_015); tracts with no population dropped. Regression of
log median income on poverty and education with all three variables imputed by predictive mean matching (m = 20),
the fraction of missing information, and a delta sensitivity for log income (missing incomes 10% or 20% lower).
Writes docs/audits/r100_mice_example.md.

Usage: scripts/r100_mice_example.py OUT_DIR
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from census.api import CensusAPIClient  # noqa: E402
from census.workflows_inference import fit_model  # noqa: E402


def get(table, col, dataset):
    c = CensusAPIClient()
    d = c.fetch(2023, "26", table, geo_level="tract", dataset=dataset)
    if d is None:
        raise SystemExit(c.last_error)
    f = pd.DataFrame(d[1:], columns=d[0]).loc[:, lambda x: ~x.columns.duplicated()]
    f["GEOID"] = f.state+f.county+f.tract
    v = pd.to_numeric(f[col], errors="coerce")
    return pd.Series(np.where(v < 0, np.nan, v), index=f.GEOID)


def main(out):
    od = Path(out); od.mkdir(parents=True, exist_ok=False)
    pop = get("B01003", "B01003_001E", "acs5")
    f = pd.DataFrame({"income": get("B19013", "B19013_001E", "acs5"), "pov": get("S1701", "S1701_C03_001E", "subject"),
                      "ba": get("S1501", "S1501_C02_015E", "subject")})
    f = f[pop.reindex(f.index) > 0].copy()
    f["log_income"] = np.log(f.income)
    f = f.drop(columns="income").reset_index()
    p = od/"tracts.csv"; f.to_csv(p, index=False)
    miss = f[["log_income", "pov", "ba"]].isna().sum().to_dict()
    r = fit_model(str(p), "log_income ~ pov + ba", method="replicate", impute=["log_income", "pov", "ba"],
                  impute_method="pmm", impute_delta_variable="log_income",
                  impute_delta_shifts=[np.log(.8), np.log(.9), 0.0])
    if not r["success"]:
        raise SystemExit(r["error"])
    cc = pd.read_csv(p).dropna()
    b = np.linalg.lstsq(np.column_stack([np.ones(len(cc)), cc.pov, cc.ba]), cc.log_income, rcond=None)[0]
    t = pd.DataFrame(r["table"])
    L = ["# Round 100 example: Michigan tract median income with withheld values (exploratory)", "",
         f"Author self-review, not independent; not a registered study. ACS 2019-2023, {len(f)} populated Michigan tracts; "
         f"missing values: log income {miss['log_income']}, poverty {miss['pov']}, bachelor's {miss['ba']}.", "",
         "| Term | FCS (PMM) estimate | 90% CI | FMI | Complete cases |", "| :--- | ---: | :--- | ---: | ---: |"]
    for (_, row), cb in zip(t.iterrows(), b):
        L.append(f"| {row['term']} | {row['estimate']:.4f} | {row['ci_lower']:.4f} to {row['ci_upper']:.4f} | {row['fmi']:.2f} | {cb:.4f} |")
    L += ["", "Delta sensitivity (missing incomes assumed lower by the stated factor):", "",
          "| Missing incomes | Poverty coefficient | Bachelor's coefficient |", "| :--- | ---: | ---: |"]
    for d in r["delta_sensitivity"]:
        L.append(f"| x {np.exp(d['delta']):.1f} | {d['estimate[pov]']:.4f} | {d['estimate[ba]']:.4f} |")
    L += ["", "Withheld medians cluster in small or unusual tracts, so missing-at-random is doubtful; the delta rows show "
          "how far conclusions move if those incomes are systematically lower.", ""]
    (ROOT/"docs/audits/r100_mice_example.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main(sys.argv[1])
