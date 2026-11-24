# SPDX-License-Identifier: AGPL-3.0-or-later
"""Area designations as screening tests (Round 85; backlog N62; Foundations of Epidemiology chapter 11).

Validation: ``docs/audits/designation_validation.md`` (criterion ``designation_validation_criterion.md``):
- **Validated**: the Fay-Herriot posterior probability that an area truly exceeds the threshold (Q1b; calibration
  within .031 in every bin on MI/NY tracts and counties).
- **Exploratory**: the flat-prior probability from the direct estimate (Q1a; off by up to .17 when few areas truly
  qualify, because it ignores regression to the mean) and the expected accuracy of a rule (Q2). Expected sensitivity,
  specificity, PPV and NPV from Q1b agreed with the realized values within about .01 on average, but the predictive
  interval for the realized PPV under-covered on tracts (.54-.85), so Q2 failed its pre-set criterion; the expected
  values are reported without an interval and labelled exploratory.
"""
from typing import Any, Dict, Optional, Sequence

import numpy as np
import pandas as pd

from . import designation_core as dc

AUDIT = "docs/audits/designation_validation.md"
REPAIRS_AUDIT = "docs/audits/repairs107_validation.md"
REPAIRS_AUDIT_112 = "docs/audits/repairs112_validation.md"
VALIDATED = {"q1_direct": False, "q1_fh": True, "q2": False}
PPV_INTERVAL_VALIDATED = {"prob80": True, "point": True, "lower": True, "prob50": False}
RULES = ("point", "lower", "prob50", "prob80")


def designation_accuracy(frame: pd.DataFrame, column: str, threshold: float, se_col: Optional[str] = None,
                         n_col: Optional[str] = None, covariates: Sequence[str] = (), percent: Optional[bool] = None,
                         rules: Sequence[str] = RULES, ppv_intervals: bool = False,
                         ppv_bootstrap: int = 150, seed: int = 20287071) -> Dict[str, Any]:
    """Per-area probability of truly exceeding ``threshold`` (Fay-Herriot posterior, validated; direct, exploratory)
    and the expected accuracy of each designation rule. Pass ``ppv_intervals=True`` for Round 107 FH parametric
    bootstrap PPV predictive intervals (validated for ``'prob80'`` and ``'point'``; ``docs/audits/repairs107_validation.md``)."""
    f = frame.dropna(subset=[column]+([se_col] if se_col else [])+([n_col] if n_col else [])+list(covariates)).copy()
    p = f[column].to_numpy(float); t = float(threshold)
    if percent is None:
        percent = bool(np.nanmax(p) > 1)
    if percent:
        p, t = p/100, t/100
    if n_col:
        n = f[n_col].to_numpy(float)
    else:
        if not se_col:
            raise ValueError("give se_col (the estimate's standard error) or n_col (effective sample size)")
        se = f[se_col].to_numpy(float)/(100 if percent else 1)
        with np.errstate(divide="ignore", invalid="ignore"):
            n = p*(1-p)/se**2
        bad = ~np.isfinite(n) | (n <= 0)
        if bad.any():
            raise ValueError(f"{int(bad.sum())} area(s) have an estimate of 0 or 100% or a zero SE; give n_col")
    X = np.column_stack([np.ones(len(p))]+[f[c].to_numpy(float) for c in covariates])
    Pb, theta, mse = dc.q1_fh(p, n, X, t)
    Pa = dc.q1_direct(p, n, t)
    table = []
    rng = np.random.default_rng(seed) if ppv_intervals else None
    if ppv_intervals:
        from . import repairs107_core as r107
        from . import repairs112_core as r112
    for rule in rules:
        S = dc.designate(rule, p, n, t, Pb)
        e = dc.expected_accuracy(S, Pb)
        row = {k: e[k] for k in ("designated", "sensitivity", "specificity", "ppv", "npv")} | {"rule": rule}
        if ppv_intervals:
            if rule == "prob80":
                iv = r107.ppv_interval_prob80("prob80", S, p, n, X, t, B=int(ppv_bootstrap), rng=rng)
                row.update(ppv_lower=iv["ppv_lower"], ppv_upper=iv["ppv_upper"], ppv_validated=True)
            elif rule == "point":
                iv = r107.ppv_interval_point_ll(S, p, n, X, t, B=int(ppv_bootstrap), rng=rng)
                row.update(ppv_lower=iv["ppv_lower"], ppv_upper=iv["ppv_upper"], ppv_validated=True)
            elif rule == "lower":
                iv = r112.ppv_interval_ll("lower", S, p, n, X, t, B=int(ppv_bootstrap), rng=rng)
                row.update(ppv_lower=iv["ppv_lower"], ppv_upper=iv["ppv_upper"], ppv_validated=True)
            else:
                row.update(ppv_lower=float("nan"), ppv_upper=float("nan"), ppv_validated=False)
        table.append(row)
    scale = 100 if percent else 1
    areas = pd.DataFrame({"GEOID": f["GEOID"].astype(str).to_numpy() if "GEOID" in f else np.arange(len(p)),
                          "estimate": p*scale, "probability_above": Pb, "probability_above_direct": Pa,
                          **{f"designated_{r}": dc.designate(r, p, n, t, Pb) for r in rules}})
    notes = ["probability_above (Fay-Herriot posterior) is validated; probability_above_direct ignores "
             "regression to the mean and is exploratory.",
             "Expected sensitivity, specificity, PPV and NPV point summaries are exploratory; Round 107 "
             f"validated FH parametric bootstrap PPV predictive intervals for 'prob80' and 'point' ({REPAIRS_AUDIT}; "
             "pass ppv_intervals=True).",
             "Choose the rule by the cost of false positives versus false negatives: 'lower' and 'prob80' "
             "trade sensitivity for PPV."]
    return dict(threshold=float(threshold), areas=areas, rules=pd.DataFrame(table),
                expected_qualifying=float(Pb.sum()), validated=dict(VALIDATED), audit=AUDIT,
                repairs_audit=REPAIRS_AUDIT, notes=notes)
