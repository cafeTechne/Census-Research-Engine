# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 86 exploratory example: bias analysis of the Michigan uninsured comparison, Black vs White non-Hispanic
adults 19-64 (PUMS 2019-2023; Round 79's population).

Exploratory; author self-review, not independent. Crude risk ratio with SDR 90% interval; its E-value; and an outcome
misclassification analysis with ILLUSTRATIVE (not literature-derived) values for self-reported uninsurance:
sensitivity .85, specificity .97, nondifferential (simple) and with SD .03 priors (probabilistic, exploratory).
Writes docs/audits/r86_bias_example.md.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402

from census import pums  # noqa: E402
from census.bias_analysis import e_value, misclassification  # noqa: E402


def main():
    df = pums.fetch_pums("26", 2023, product="5-year", record="person", columns=["RAC1P", "HISP", "AGEP", "HICOV"])
    sub = df[(df.AGEP >= 19) & (df.AGEP <= 64) & (df.HISP == 1) & df.RAC1P.isin([1, 2])]
    _, W = pums._weight_matrix(sub, "person")
    y = (sub.HICOV == 2).to_numpy(); e = (sub.RAC1P == 2).to_numpy()
    risk = lambda g: (W[g & y].sum(0))/W[g].sum(0)  # noqa: E731
    lrr = np.log(risk(e)/risk(~e))
    se = np.sqrt(4/80*((lrr[1:]-lrr[0])**2).sum())
    rr, lo, hi = np.exp(lrr[0]), np.exp(lrr[0]-1.645*se), np.exp(lrr[0]+1.645*se)
    ev = e_value(rr, lo, hi)
    w0 = W[:, 0]
    a, b = float(w0[e & y].sum()), float(w0[e & ~y].sum()); c, d = float(w0[~e & y].sum()), float(w0[~e & ~y].sum())
    scale = len(sub)/w0.sum()  # express the weighted table in record units for the probabilistic step
    m = misclassification(a*scale, b*scale, c*scale, d*scale, .85, .97, sd=.03)
    L = ["# Round 86 example: bias analysis of the Michigan uninsured comparison (PUMS 2019-2023, adults 19-64)", "",
         "Exploratory; author self-review, not independent.", "",
         f"Crude risk ratio of uninsurance, Black vs White non-Hispanic adults: {rr:.2f} (90% CI {lo:.2f} to {hi:.2f}).",
         "", f"E-value: {ev['e_value']:.2f} (interval limit {ev['e_value_limit']:.2f}): an unmeasured confounder would need "
         f"risk-ratio associations of at least {ev['e_value']:.2f} with both race and uninsurance to explain the crude "
         "ratio away. (Round 79 found the gap is explained by measured composition, so this crude ratio is not a "
         "causal effect of race in any case.)", "",
         "Outcome misclassification with ILLUSTRATIVE values (sensitivity .85, specificity .97 for reporting "
         f"uninsurance; not taken from a validation study): corrected RR {m['corrected']['rr']:.2f} (observed "
         f"{m['observed']['rr']:.2f}); probabilistic analysis (exploratory; failed validation) median "
         f"{m['probabilistic']['rr']['median']:.2f}, 90% simulation interval {m['probabilistic']['rr']['lower']:.2f} to "
         f"{m['probabilistic']['rr']['upper']:.2f}.", ""]
    (ROOT/"docs/audits/r86_bias_example.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
