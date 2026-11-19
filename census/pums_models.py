# SPDX-License-Identifier: AGPL-3.0-or-later
"""Survey-weighted PUMS models with the SDR replicate variance (Round 49).

Wraps the frozen solvers in :mod:`census.pums_models_core`: the model is fitted with the full PUMS
weight and refitted with each of the 80 replicate weights (warm-started), and
Var = 4/80 * sum_r (theta_r - theta)^2. Validation: ``docs/audits/pums_models_validation.md``
(Round 32 superpopulation with household clustering, unequal weights and ACS-style SDR weights).
"""
from typing import Any, Dict

import numpy as np
import pandas as pd

from . import pums
from . import pums_models_core as pm

AUDIT = "docs/audits/pums_models_validation.md"
MODELS = ("ordered_logit", "ordered_probit", "mnlogit", "median", "probit")
# Round 49 outcomes per model (tests/test_round49.py checks these against the audit JSON)
VALIDATED = {"ordered_logit": True, "ordered_probit": True, "mnlogit": True, "median": True, "probit": True}
AUDIT_KEY = {"ordered_logit": "O", "ordered_probit": "P", "mnlogit": "M", "median": "Q", "probit": "G"}


def fit_pums_model(formula: str, df: pd.DataFrame, model: str = "ordered_logit", weight: str = "person",
                   where: Any = None, confidence_level: float = 0.90,
                   min_n: int = pums.MIN_UNWEIGHTED_N) -> Dict[str, Any]:
    """Fit ``formula`` (patsy, PUMS codes) on PUMS records with SDR replicate-weight intervals.

    ``model``: "ordered_logit" / "ordered_probit" (ordered categories of the outcome, sorted by code;
    thresholds reported separately), "mnlogit" (unordered categories; the lowest code is the
    baseline), "median" (weighted median regression) or "probit" (0/1 outcome)."""
    import patsy
    if model not in MODELS:
        raise ValueError(f"model must be one of {MODELS}")
    sub = df.loc[pums._mask(df, where)].reset_index(drop=True)
    base, W = pums._weight_matrix(sub, weight)
    y_df, X_df = patsy.dmatrices(formula, sub, return_type="dataframe", NA_action="drop")
    W = W[sub.index.get_indexer(X_df.index)]
    if not np.isfinite(W).all():
        raise ValueError("non-finite weights among modelled records")
    y = y_df.iloc[:, 0].to_numpy(float)
    terms = list(X_df.columns)
    levels = None
    if model in ("ordered_logit", "ordered_probit", "mnlogit"):
        levels = np.unique(y)
        if (len(levels) < 3 and model != "mnlogit") or len(levels) < 2:
            raise ValueError("the outcome needs at least three categories (ordered) or two (mnlogit)")
        y = np.searchsorted(levels, y)
    if model == "probit" and not np.isin(y, (0., 1.)).all():
        raise ValueError("probit outcome must be 0/1")
    if model in ("ordered_logit", "ordered_probit"):
        keep = [j for j, t in enumerate(terms) if t != "Intercept"]
        X = X_df.to_numpy(float)[:, keep]; terms = [terms[j] for j in keep]
    else:
        X = X_df.to_numpy(float)
    r = pm.sdr_fit(model, y, X, W, confidence_level)
    rows = []
    if model == "mnlogit":
        p = X.shape[1]
        for a in range(len(levels)-1):
            for j, t in enumerate(terms):
                k = a*p+j
                rows.append(dict(term=f"{t} [{pums_label(levels[a+1])} vs {pums_label(levels[0])}]",
                                 estimate=r["estimate"][k], se=r["se"][k], lower=r["lower"][k], upper=r["upper"][k]))
    else:
        names = terms+([f"threshold {pums_label(levels[j])}|{pums_label(levels[j+1])}" for j in range(len(levels)-1)]
                       if model in ("ordered_logit", "ordered_probit") else [])
        rows = [dict(term=t, estimate=r["estimate"][k], se=r["se"][k], lower=r["lower"][k], upper=r["upper"][k])
                for k, t in enumerate(names)]
    validated = bool(VALIDATED[model])
    notes = ["SE from the 80 replicate-weight refits: Var = 4/80 * sum_r (theta_r - theta)^2 (Round 49)."]
    if len(y) < min_n:
        notes.append(f"fewer than {min_n} records ({len(y)}): estimates are unreliable")
    if not validated:
        notes.append(f"EXPLORATORY: {model} intervals did not pass the Round 49 validation ({AUDIT}).")
    if model == "mnlogit":
        notes.append(f"Baseline category: {pums_label(levels[0])}.")
    return dict(model=model, formula=formula, table=pd.DataFrame(rows), n=int(len(y)),
                weighted_n=float(W[:, 0].sum()), weight=base, validated=validated, notes=notes, audit=AUDIT,
                levels=None if levels is None else [pums_label(v) for v in levels])


def pums_label(v):
    return str(int(v)) if float(v).is_integer() else str(v)
