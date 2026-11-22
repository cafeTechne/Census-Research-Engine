# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 79 exploratory example: the Michigan uninsured gap between Black and White adults aged 19-64.

Exploratory; author self-review, not independent. PUMS 2019-2023 (five-year), persons aged 19-64; groups Black alone
not Hispanic (RAC1P 2, HISP 1) and White alone not Hispanic (RAC1P 1, HISP 1); outcome uninsured (HICOV == 2).
Fairlie (logit) with age and income-to-poverty ratio (numeric) and employment status (ESR) and education (SCHL)
as categorical blocks; 100 orderings; SDR replicate-weight intervals. Oaxaca-Blinder (linear probability) for
comparison. Writes docs/audits/r79_decomposition_example.md.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from census import pums  # noqa: E402
from census.decomposition import pums_decomposition  # noqa: E402

A, B = "RAC1P == 2 and HISP == 1", "RAC1P == 1 and HISP == 1"
WHERE = "AGEP >= 19 and AGEP <= 64"


def main():
    df = pums.fetch_pums("26", 2023, product="5-year", record="person",
                         columns=["RAC1P", "HISP", "AGEP", "POVPIP", "ESR", "SCHL", "HICOV"])
    L = ["# Round 79 example: Michigan uninsured gap, Black vs White non-Hispanic adults 19-64 (PUMS 2019-2023)", "",
         "Exploratory; author self-review, not independent. 'Explained' is composition (age, income-to-poverty, "
         "employment, education), not a causal effect. Percentage points; 90% SDR intervals.", ""]
    for model, label in (("logit", "Fairlie (logit)"), ("linear", "Oaxaca-Blinder (linear probability)")):
        r = pums_decomposition(df, "HICOV == 2", A, B, ["AGEP", "POVPIP"], ["ESR", "SCHL"], model=model, where=WHERE)
        t = r["table"]
        L += [f"## {label}", "", f"Records: Black {r['records']['group_a']}, White {r['records']['group_b']}.", "",
              "| Component | Estimate | 90% CI | Validated |", "| :--- | ---: | :--- | :--- |"]
        for row in t.itertuples():
            if row.component in ("endowments", "coefficients", "interaction"):
                continue
            L.append(f"| {row.component} | {100*row.estimate:.2f} | {100*row.ci_lower:.2f} to {100*row.ci_upper:.2f} | "
                     f"{'yes' if row.validated else 'no'} |")
        L.append("")
    (ROOT/"docs/audits/r79_decomposition_example.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
