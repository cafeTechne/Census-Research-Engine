# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fixed validation of robust (HC3) GLM standard errors: four cells, 2,000 draws each, seed 20261115+cell.

Pre-set before any run (committed with this script): the shipped census.models.glm_robust_covariance
HC3 interval must cover >= 0.86 of nominal 90% Wald intervals in all four cells. Comparators (reported,
not judged): HC0 x sqrt(n/(n-k)) and Pearson X2 (quasi-likelihood). Design follows the Round 22 A2
binomial cell at range 0 (n=145, independent units, lognormal denominators drawn once per cell: median
3900, log-SD 1, minimum 50; logit or log mean -2.6 + 0.3 x + u, x ~ N(0,1), u ~ N(0, sd_u^2)).
Cells: binomial sd_u 0 (no overdispersion), 0.15 (A2), 0.30; Poisson sd_u 0.15 with exposure.
Units are independent: spatial dependence is out of scope (the Conley test of A2 failed).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import statsmodels.api as sm

from census.models import glm_robust_covariance

SIMS = 2000
N = 145
MIN_COVERAGE = .86
Z90 = 1.6448536269514722
CELLS = (("binomial", 0.0), ("binomial", 0.15), ("binomial", 0.30), ("poisson", 0.15))
BETA = .3


def main():
    rows = []
    for index, (model, sd_u) in enumerate(CELLS):
        seed = 20261115 + index
        rng = np.random.default_rng(seed)
        denom = np.maximum(50, np.rint(rng.lognormal(np.log(3900), 1, N)))
        hits = {"HC3": 0, "HC0_nk": 0, "X2": 0}
        ses = {k: [] for k in hits}
        est, failed = [], 0
        for _ in range(SIMS):
            x = rng.standard_normal(N)
            eta = -2.6 + BETA * x + sd_u * rng.standard_normal(N)
            X = np.column_stack((np.ones(N), x))
            if model == "binomial":
                y = rng.binomial(denom.astype(int), 1 / (1 + np.exp(-eta))) / denom
                fit = sm.GLM(y, X, family=sm.families.Binomial(), var_weights=denom).fit()
                t = denom
            else:
                y = rng.poisson(denom * np.exp(eta)).astype(float)
                fit = sm.GLM(y, X, family=sm.families.Poisson(), exposure=denom).fit()
                t = None
            b = float(fit.params[1])
            est.append(b)
            mu = np.asarray(fit.fittedvalues, float)
            x2 = float(np.sqrt(fit.cov_params()[1, 1] * fit.pearson_chi2 / fit.df_resid))
            try:
                cov3, _ = glm_robust_covariance(X, y, mu, model, t)
                se3 = float(np.sqrt(cov3[1, 1]))
            except ValueError:
                se3 = float("nan")
                failed += 1  # counted as noncoverage
            w = denom * mu * (1 - mu) if model == "binomial" else mu
            r = denom * (y - mu) if model == "binomial" else y - mu
            bread = np.linalg.inv(X.T @ (w[:, None] * X))
            s = X * r[:, None]
            se0 = float(np.sqrt((bread @ (s.T @ s) @ bread)[1, 1] * N / (N - 2)))
            for k, se in (("HC3", se3), ("HC0_nk", se0), ("X2", x2)):
                ses[k].append(se)
                hits[k] += int(np.isfinite(se) and abs(b - BETA) <= Z90 * se)
        sd = float(np.std(est, ddof=1))
        for k in hits:
            cov = hits[k] / SIMS
            rows.append({"model": model, "sd_u": sd_u, "estimator": k, "sims": SIMS, "seed": seed,
                         "coverage": cov, "mc_se": float(np.sqrt(cov * (1 - cov) / SIMS)),
                         "mean_se_over_empirical_sd": float(np.nanmean(ses[k]) / sd),
                         "failed": failed if k == "HC3" else 0})
        print(model, sd_u, {k: hits[k] / SIMS for k in hits}, flush=True)
    passed = all(r["coverage"] >= MIN_COVERAGE for r in rows if r["estimator"] == "HC3")
    result = {"passed": passed, "criterion": "HC3 coverage >= 0.86 in all four cells", "rows": rows}
    folder = Path("docs/audits")
    (folder / "robust_se_validation.json").write_text(json.dumps(result, indent=2) + "\n")
    lines = ["# Robust GLM standard-error validation", "",
             "Fixed design (follows the Round 22 A2 binomial cell at range 0): n=145 independent units, 2,000 "
             "simulations per cell, seed 20261115 + cell index. Lognormal denominators drawn once per cell "
             "(median 3900, log-SD 1, minimum 50). Linear predictor -2.6 + 0.3x + u, x ~ N(0,1), "
             "u ~ N(0, sd_u^2) (between-area variation that does not shrink with the denominator). "
             "Binomial: logit link, denominators as trials. Poisson: log link, denominators as exposure. "
             "90% normal Wald intervals.", "",
             "Estimator under test: the shipped `census.models.glm_robust_covariance` (HC3), used by "
             "`fit_replicate(scale='robust')`. Comparators: HC0 with the n/(n-k) factor, Pearson X2.", "",
             "**Pre-set acceptance** (committed before the first run): HC3 coverage >= 0.86 in all four cells. "
             f"**{'PASSED' if passed else 'FAILED'}**.", "",
             "Scope: units independent. Spatial dependence is not covered (Round 22 A2 Conley test failed).", "",
             "| Model | sd_u | Estimator | Coverage | MC SE | Mean SE / empirical SD | Failed |",
             "| :--- | ---: | :--- | ---: | ---: | ---: | ---: |"]
    for r in rows:
        lines.append("| {model} | {sd_u} | {estimator} | {coverage:.4f} | {mc_se:.4f} | "
                     "{mean_se_over_empirical_sd:.4f} | {failed} |".format(**r))
    lines += ["", "Reproduce: `OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/robust_se_validation.py`.", ""]
    (folder / "robust_se_validation.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
