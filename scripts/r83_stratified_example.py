# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 83 exploratory example: uninsurance by disability, stratified by age band (Michigan PUMS 2019-2023).

Exploratory; author self-review, not independent. Adults 19-64; exposure: any disability (DIS == 1); outcome:
uninsured (HICOV == 2); strata: age 19-34, 35-49, 50-64. Crude, stratum and Mantel-Haenszel measures with SDR
intervals; classification by the book's Table 8-5; RERI for disability x male sex. Writes
docs/audits/r83_stratified_example.md. (The planned WONDER county-by-age example needs county x age deaths, which the
owner's exports do not contain.)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402

from census import pums  # noqa: E402
from census.stratified import additive_interaction, stratified_pums  # noqa: E402


def main():
    df = pums.fetch_pums("26", 2023, product="5-year", record="person", columns=["AGEP", "DIS", "HICOV", "SEX"])
    sub = df[(df.AGEP >= 19) & (df.AGEP <= 64)]
    y = (sub.HICOV == 2).to_numpy(int); e = (sub.DIS == 1).to_numpy(int)
    band = np.digitize(sub.AGEP.to_numpy(), [35, 50])
    _, W = pums._weight_matrix(sub, "person")
    r = stratified_pums(y, e, band, W, [0, 1, 2])
    male = (sub.SEX == 1).to_numpy(int)
    cells = e+2*male
    risks = np.stack([(W[cells == k]*y[cells == k, None]).sum(0)/W[cells == k].sum(0) for k in range(4)], axis=1)
    ai = additive_interaction(risks=risks)
    names = {"0": "19-34", "1": "35-49", "2": "50-64"}
    L = ["# Round 83 example: uninsurance by disability, stratified by age (Michigan PUMS 2019-2023, adults 19-64)", "",
         "Exploratory; author self-review, not independent. Outcome uninsured; exposure any disability; SDR 90% "
         f"intervals. Records per stratum: {', '.join(f'{names[k]}: {v:,}' for k, v in r['records'].items())}.", "",
         "| Measure | Crude | " + " | ".join(f"Age {v}" for v in names.values()) + " | MH pooled (90% CI) | Label |",
         "| :--- | ---: | ---: | ---: | ---: | :--- | :--- |"]
    for m in ("rr", "or", "rd"):
        p = r["pooled"][m]
        L.append(f"| {m.upper()} | {r['crude'][m]:.3f} | " + " | ".join(f"{r['strata'][m][k]:.3f}" for k in names)
                 + f" | {p['estimate']:.3f} ({p['lower']:.3f} to {p['upper']:.3f}) | {r['classification'][m]} |")
    L += ["", "Homogeneity (replicate Wald, exploratory): " + ", ".join(
        f"{m.upper()} p = {h['p']:.3f}" for m, h in r["homogeneity"].items()) + ".", "",
        f"Additive interaction of disability and male sex: RERI {ai['reri']:.3f} (90% CI {ai['lower']:.3f} to "
        f"{ai['upper']:.3f}); AP {ai['ap']:.3f}; S {ai['s']:.3f}.", ""]
    (ROOT/"docs/audits/r83_stratified_example.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
