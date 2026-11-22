# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 87 exploratory example: income-to-poverty ratio and disability, within and between PUMAs (PUMS 2019-2023).

Exploratory; author self-review, not independent. Adults 19-64; outcome any disability (DIS == 1); exposure
income-to-poverty ratio in hundreds of percent (POVPIP / 100, capped at 5.01). Logit decomposition (validated) and
identity-scale decomposition with the ecologic gap (exploratory). Michigan, with Ohio as the replication state.
Writes docs/audits/r87_ecologic_example.md.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402

from census import pums  # noqa: E402
from census.ecologic import ecologic_check  # noqa: E402


def run(state):
    df = pums.fetch_pums(state, 2023, product="5-year", record="person", columns=["AGEP", "DIS", "POVPIP", "PUMA"])
    sub = df[(df.AGEP >= 19) & (df.AGEP <= 64) & df.POVPIP.notna() & df.PUMA.notna()]
    _, W = pums._weight_matrix(sub, "person")
    y = (sub.DIS == 1).to_numpy(float); x = sub.POVPIP.to_numpy(float)/100
    return ecologic_check(y, x, sub.PUMA.astype(str).to_numpy(), W, binary=True)


def main():
    L = ["# Round 87 example: income-to-poverty ratio and disability within and between PUMAs (PUMS 2019-2023)", "",
         "Exploratory; author self-review, not independent. Adults 19-64; exposure per 100 percentage points of the "
         "income-to-poverty ratio. Logit results are validated; identity-scale (risk-difference) results and the "
         "ecologic gap are exploratory.", "",
         "| State | PUMAs | Records | Logit within | Logit between | Logit contextual | Identity within | Ecologic (area-level) | Ecologic gap |",
         "| :--- | ---: | ---: | :--- | :--- | :--- | :--- | :--- | :--- |"]
    f = lambda d: f"{d['estimate']:.3f} ({d['lower']:.3f} to {d['upper']:.3f})"  # noqa: E731
    for st, name in (("26", "Michigan"), ("39", "Ohio")):
        r = run(st)
        lg, idn = r["logit"], r["identity"]
        L.append(f"| {name} | {r['areas']} | {r['records']:,} | {f(lg['within'])} | {f(lg['between'])} | "
                 f"{f(lg['contextual'])} | {f(idn['within'])} | {f(idn['ecologic'])} | {f(idn['ecologic_gap'])} |")
    L += ["", "Reading: the within-PUMA (individual) association is what applies to people; the area-level (ecologic) "
          "slope is what an ACS-only analysis would estimate, and the gap is its ecologic bias for this question.", ""]
    (ROOT/"docs/audits/r87_ecologic_example.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
