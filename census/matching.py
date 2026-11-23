# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 99: matching estimators and triple differences (backlog N76; Cunningham, *Mixtape*; Abadie and Imbens 2006,
2011; Iacus, King and Porro 2012; Gruber 1994).

Validation (``docs/audits/matching_validation.md``; criterion tag ``criterion-r99``), Round 90 confounding designs
(145 and 600 areas) and 51-unit panels:
- passed: nearest-neighbour matching (4 matches, bias-corrected, Abadie-Imbens variance) for the ATE (.861-.903);
  coarsened exact matching for the ATT among matched treated units (.951-.974, conservative); propensity-score
  caliper matching with a bootstrap (.962-.993, conservative - unexpectedly, against the literature); triple
  differences (.980-.986, conservative). Simple DiD with a treated-unit trend covered 0 (bias 1.5).
- failed: nearest-neighbour ATT (.852 with 145 areas and limited overlap; .858-.914 otherwise): exploratory.
"""
from typing import Any, Dict, Sequence

import numpy as np
import pandas as pd

from . import matching_core as mc

AUDIT = "docs/audits/matching_validation.md"
VALIDATED = {"nn_ATE": True, "nn_ATT": False, "cem": True, "ps": True, "triple": True}


def matching_effect(frame: pd.DataFrame, outcome: str, treatment: str, covariates: Sequence[str], method: str = "nn",
                    estimand: str = "ATE", matches: int = 4, seed: int = 20282991) -> Dict[str, Any]:
    d = frame.dropna(subset=[outcome, treatment, *covariates]).reset_index(drop=True)
    y = d[outcome].astype(float).to_numpy(); T = d[treatment].astype(int).to_numpy()
    if set(np.unique(T)) - {0, 1}:
        raise ValueError("treatment must be coded 0/1")
    if min(T.sum(), (1-T).sum()) < 10:
        raise ValueError("each treatment group needs at least 10 areas")
    X = d[list(covariates)].astype(float).to_numpy()
    if method == "nn":
        if estimand not in ("ATE", "ATT"):
            raise ValueError("estimand must be 'ATE' or 'ATT'")
        r = mc.nn_match(y, T, X, matches, estimand); key = f"nn_{estimand}"
    elif method == "cem":
        r = mc.cem(y, T, X); key = "cem"; r.pop("matched")
    elif method == "ps":
        r = mc.ps_match(y, T, X, np.random.default_rng(seed)); key = "ps"
    else:
        raise ValueError("method must be 'nn', 'cem' or 'ps'")
    balance = {c: dict(smd=float((X[T == 1, j].mean()-X[T == 0, j].mean())/np.sqrt((X[T == 1, j].var(ddof=1)+X[T == 0, j].var(ddof=1))/2)))
               for j, c in enumerate(covariates)}
    validated = bool(VALIDATED[key]) and (method != "nn" or matches == 4)
    notes = ["Assumes no unmeasured confounding; areas independent. Balance before matching is in 'balance'."]
    if method == "cem":
        notes.append(f"Estimand: the effect among the {r['share_treated_matched']:.0%} of treated areas matched in a "
                     "coarsened stratum (quintiles); unmatched treated areas are dropped.")
    if key == "nn_ATT":
        notes.append("Nearest-neighbour ATT intervals under-covered (.852) with 145 areas and limited overlap: exploratory.")
    return dict(method=method, n=len(y), n_treated=int(T.sum()), effect=r, balance_before=balance,
                validated=validated, notes=notes, audit=AUDIT)


def triple_difference(frame: pd.DataFrame, outcome: str, unit: str, group: str, affected_group: Any, period: str,
                      treated: str, first_treated_period: int) -> Dict[str, Any]:
    d = frame.dropna(subset=[outcome, unit, group, period, treated]).reset_index(drop=True)
    ga = (d[group] == affected_group).astype(int).to_numpy()
    if ga.all() or not ga.any():
        raise ValueError("the group column needs both the affected group and at least one comparison group")
    post = (d[period].astype(int) >= int(first_treated_period)).astype(int).to_numpy()
    r = mc.triple_difference(d[outcome].astype(float).to_numpy(), d[unit].astype(str).to_numpy(), ga,
                             d[period].astype(int).to_numpy(), d[treated].astype(int).to_numpy(), post)
    if r["clusters"] < 30:
        note = f"{r['clusters']} units: validation used 51; fewer clusters are outside the validated range."
    else:
        note = "Triple difference: identified if group-specific shocks do not differ between treated and comparison units."
    return dict(design="triple", effect=r, validated=r["clusters"] >= 30, notes=[note], audit=AUDIT)
