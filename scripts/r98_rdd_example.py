# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 98 exploratory example: health insurance at age 65 in the Michigan PUMS (after Card, Dobkin and Maestas 2008).

Exploratory; author self-review, not independent; not a registered study. ACS PUMS 2019-2023, Michigan persons aged
45-84; person weights PWGTP with the 80 SDR replicates. Running variable AGEP (cutoff 65).
(a) Sharp RDD of Medicare coverage (HINS3 = 1): the first stage.
(b) Sharp RDD of any coverage (HICOV = 1).
(c) Fuzzy RDD: any coverage on Medicare at 65.
Checks: sex (female share) at the cutoff; placebo cutoffs 60 and 70. Writes docs/audits/r98_rdd_example.md.

Usage: scripts/r98_rdd_example.py OUT_DIR
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from census.pums import fetch_pums  # noqa: E402
from census.workflows_microdata import regression_discontinuity  # noqa: E402


def main(out):
    od = Path(out); od.mkdir(parents=True, exist_ok=False)
    df = fetch_pums("26", 2023, columns=["AGEP", "HICOV", "HINS3", "SEX"])
    df = df[(df.AGEP >= 45) & (df.AGEP <= 84)].copy()
    df["covered"] = (df.HICOV == 1).astype(float); df["medicare"] = (df.HINS3 == 1).astype(float)
    df["female"] = (df.SEX == 2).astype(float)
    p = od/"mi_pums_45_84.parquet"; df.to_parquet(p, index=False)
    kw = dict(running="AGEP", cutoff=65, weight="PWGTP", replicate_prefix="PWGTP")
    a = regression_discontinuity(str(p), "medicare", covariates=["female"], placebo_cutoffs=[60, 70], **kw)
    b = regression_discontinuity(str(p), "covered", placebo_cutoffs=[60, 70], **kw)
    c = regression_discontinuity(str(p), "covered", treatment="medicare", **kw)
    for r in (a, b, c):
        if not r["success"]:
            raise SystemExit(r["error"])
    pc = lambda v: f"{100*v:+.1f}"  # noqa: E731
    row = lambda name, r: f"| {name} | {pc(r['estimate'])} | {pc(r['lower'])} to {pc(r['upper'])} | {r['bandwidth']:.1f} | {'yes' if r['validated'] else 'no'} |"  # noqa: E731
    L = ["# Round 98 example: health insurance at age 65, Michigan PUMS 2019-2023 (exploratory)", "",
         f"Author self-review, not independent; not a registered study. {a['n']:,} persons aged 45-84; weights and SDR "
         "replicates; robust bias-corrected local quadratic jumps (percentage points; fuzzy: points of coverage per "
         "point of Medicare).", "", "| Estimate | Jump | 90% CI | Bandwidth (years) | Validated |", "| :--- | ---: | :--- | ---: | :--- |",
         row("Medicare coverage (first stage)", a), row("Any coverage", b),
         f"| Any coverage per Medicare (fuzzy) | {c['estimate']:.3f} | {c['lower']:.3f} to {c['upper']:.3f} | {c['bandwidth']:.1f} | "
         f"{'yes' if c['validated'] else 'no'} |", "",
         f"Checks: female share jump {pc(a['covariate_jumps']['female']['estimate'])} points "
         f"({pc(a['covariate_jumps']['female']['lower'])} to {pc(a['covariate_jumps']['female']['upper'])}); placebo cutoffs for "
         "any coverage: " + "; ".join(f"age {k}: {pc(v['estimate'])} ({pc(v['lower'])} to {pc(v['upper'])})" for k, v in b["placebo"].items())
         + f". Density test (exploratory): p = {a['density_test']['p']:.2f}.", "",
         "Card, Dobkin and Maestas (2008) found coverage rising by about 7-10 points at 65 in the NHIS and CPS; ACS "
         "coverage before 65 is higher today (post-ACA), so a smaller jump is expected.", ""]
    (ROOT/"docs/audits/r98_rdd_example.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main(sys.argv[1])
