# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 100: multiple imputation by fully conditional specification (backlog N77; van Buuren, *Flexible Imputation of
Missing Data*, 2012).

Validation (``docs/audits/mice_validation.md``; criterion tag ``criterion-r100``): 145 and 600 areas, three incomplete
variables including the outcome (10% and 40% MAR missingness), m = 20, 10 cycles: predictive mean matching covered
.885-.912 and Bayesian linear imputation .887-.915 (both validated). The delta adjustment is a descriptive MNAR
sensitivity analysis (exact at delta = 0).
"""
from typing import Any, Dict, Mapping, Optional, Sequence

import numpy as np
import pandas as pd
import patsy

from . import mice_core as mc

AUDIT = "docs/audits/mice_validation.md"
VALIDATED = {"pmm": True, "norm": True}


def impute_fcs(formula: str, frame: pd.DataFrame, incomplete: Sequence[str], method: str = "pmm", m: int = 20,
               cycles: int = 10, delta: Optional[Mapping[str, Sequence[float]]] = None, auxiliary: Sequence[str] = (),
               seed: int = 20283001, level: float = .90) -> Dict[str, Any]:
    """OLS of ``formula`` with ``incomplete`` variables (outcome allowed) imputed by FCS. ``delta``: {variable:
    [shifts]} reports the pooled coefficients for each shift added to that variable's imputations (MNAR sensitivity)."""
    if method not in ("pmm", "norm"):
        raise ValueError("method must be 'pmm' or 'norm'")
    outcome = formula.split("~", 1)[0].strip()
    rhs_vars = sorted({f.name() for t in patsy.ModelDesc.from_formula(formula).rhs_termlist for f in t.factors})
    cols = list(dict.fromkeys([outcome, *rhs_vars, *auxiliary]))
    for c in cols:
        if not all(ch.isalnum() or ch == "_" for ch in c):
            raise ValueError(f"impute with method= needs plain column terms; {c!r} is an expression")
    miss_cols = [c for c in incomplete if c not in cols]
    if miss_cols:
        raise ValueError(f"incomplete variables {miss_cols} are not in the formula or auxiliary")
    D = frame[cols].apply(pd.to_numeric, errors="coerce").to_numpy(float)
    M = np.isnan(D)
    extra = [cols[j] for j in range(len(cols)) if M[:, j].any() and cols[j] not in incomplete]
    if extra:
        raise ValueError(f"columns {extra} have missing values but are not listed in impute")
    methods = {cols.index(c): method for c in incomplete}

    def run(dlt):
        imps = mc.mice(D, methods, m=m, cycles=cycles, rng=np.random.default_rng(seed), delta=dlt)
        est, var = [], []
        for Z in imps:
            f = pd.DataFrame(Z, columns=cols)
            y, X = patsy.dmatrices(formula, f, return_type="dataframe")
            b, *_ = np.linalg.lstsq(X.to_numpy(), y.to_numpy()[:, 0], rcond=None)
            r = y.to_numpy()[:, 0]-X.to_numpy() @ b; n, p = X.shape
            V = np.linalg.inv(X.T.to_numpy() @ X.to_numpy())*float(r @ r)/(n-p)
            est.append(b); var.append(np.diag(V)); names = list(X.columns); dfc = n-p
        return mc.pool(est, var, dfc, level), names
    pooled, names = run(None)
    table = pd.DataFrame({"term": names, "estimate": pooled["estimate"], "se": pooled["se"], "ci_lower": pooled["lower"],
                          "ci_upper": pooled["upper"], "df": pooled["df"], "fmi": pooled["fmi"], "lambda": pooled["lambda_"]})
    sens = []
    for var_name, shifts in (delta or {}).items():
        if var_name not in incomplete:
            raise ValueError(f"delta variable {var_name!r} is not imputed")
        for s in shifts:
            p, _ = run({cols.index(var_name): float(s)})
            sens.append({"variable": var_name, "delta": float(s), **{f"estimate[{t}]": float(v) for t, v in zip(names, p["estimate"])}})
    pattern = {c: int(M[:, cols.index(c)].sum()) for c in incomplete}
    return dict(table=table, n=len(D), missing=pattern, method=method, imputations=m, cycles=cycles,
                delta_sensitivity=sens, validated=VALIDATED[method], audit=AUDIT,
                notes=[f"Fully conditional specification ({method}; m = {m}; {cycles} cycles); Rubin's rules with "
                       "Barnard-Rubin df; fmi = fraction of missing information per coefficient. Assumes missing at "
                       "random given the imputation model" + ("; delta_sensitivity shows how coefficients move if the "
                       "missing values are systematically different (MNAR)." if sens else ".")])
