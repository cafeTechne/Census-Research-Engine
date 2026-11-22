# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 91: IP-weighted marginal structural models for annual policy panels (backlog N67).

Hernán and Robins, *What If*, chapters 19-21: when a time-varying confounder (for example state unemployment) is
affected by earlier policy and affects later policy and the outcome (treatment-confounder feedback), regression
adjustment for it is biased and omitting it is confounded; IP weighting of a marginal structural model is not.

Validation: ``docs/audits/msm_validation.md`` (criterion tag ``criterion-r91``). Design: 51 units, 12 or 18 annual
periods, time zero at the first period (no unit treated), "start and stay on" treatment. **Failed** (exploratory):
stabilized weights covered .805-.881 and truncated weights .799-.885 (criterion .86), with a small positive bias
(about +0.1) in the first treated year. Regression on the current confounder covered only .00-.11 for later years
under feedback (bias up to -1.6), and no adjustment .05-.68: the MSM is far less wrong, but its intervals are
somewhat too narrow with 51 units.
"""
from typing import Any, Dict, Optional, Sequence

import numpy as np
import pandas as pd

from . import msm_core as mc

AUDIT = "docs/audits/msm_validation.md"
VALIDATED = {"stabilized": False, "truncated": False}   # docs/audits/msm_validation.md: .805-.881 and .799-.885
MIN_UNITS = 30


def marginal_structural_model(frame: pd.DataFrame, outcome: str, first_treated: str,
                              time_varying_confounders: Sequence[str], period: str = "Year", unit: str = "GEOID",
                              truncate: bool = False, product: str = "1-year", bootstrap: int = 200,
                              seed: int = 20282991, report: int = 3) -> Dict[str, Any]:
    """Effects of the 1st, 2nd, ... treated year versus never treated, with IP weights for the time-varying
    confounders (stabilized; ``truncate=True`` clips them at the 1st/99th percentiles) and a cluster bootstrap."""
    if str(product).lower().replace("_", "-") not in ("1-year", "annual"):
        raise ValueError("marginal structural models need annual, non-overlapping periods (ACS 1-year or another "
                         "annual source); overlapping five-year releases are refused")
    conf = list(time_varying_confounders or [])
    if not conf:
        raise ValueError("time_varying_confounders is required (without them use design='staggered')")
    cols = [unit, period, outcome, first_treated]+conf
    miss = [c for c in cols if c not in frame]
    if miss:
        raise ValueError(f"columns not in the frame: {miss}")
    f = frame[cols].copy()
    f[period] = pd.to_numeric(f[period], errors="raise").astype(int)
    if str(product) == "1-year" and 2020 in set(f[period]):
        raise ValueError("ACS 1-year 2020 values are refused: there is no standard 2020 1-year release")
    f = f.dropna(subset=[outcome]+conf)
    periods = sorted(f[period].unique())
    pos = {p: i+1 for i, p in enumerate(periods)}
    K = len(periods)
    counts = f.groupby(unit)[period].nunique()
    if (counts != K).any():
        raise ValueError("the panel must be balanced (every unit observed in every period)")
    if f[unit].nunique() < MIN_UNITS:
        raise ValueError(f"at least {MIN_UNITS} units are needed (validated with 51)")
    first = pd.to_numeric(f[first_treated], errors="coerce")
    if (first <= periods[0]).any():
        raise ValueError(f"units treated in the first period ({periods[0]}) are refused: time zero must precede "
                         "treatment (drop them or start the panel earlier; Hernán and Robins chapter 22)")
    A = (first.notna() & (f[period] >= first)).astype(float).to_numpy()
    codes, uniq = pd.factorize(f[unit])
    year = f[period].map(pos).to_numpy()
    Y = pd.to_numeric(f[outcome]).to_numpy(float)
    L = f[conf].apply(pd.to_numeric).to_numpy(float)
    L = L[:, 0] if L.shape[1] == 1 else L
    res = mc.msm(Y, A, L, codes, year, K, truncate=truncate, B=bootstrap, rng=np.random.default_rng(seed),
                 report=report)
    naive = mc.msm(Y, A, L, codes, year, K, adjust_L=True, B=bootstrap, rng=np.random.default_rng(seed), report=report)
    kind = "truncated" if truncate else "stabilized"
    notes = [f"Time zero: {periods[0]} (no unit treated); strategy 'start and stay on'; effects are for the d-th "
             "treated year versus never treated (Hernán and Robins chapters 19-22).",
             "Assumes no unmeasured time-varying confounding given the listed confounders and correct pooled-logistic "
             "treatment models; areas independent across units (cluster bootstrap over units).",
             "naive_adjusted is ordinary regression on current confounders: biased when they are affected by past "
             "treatment; shown for comparison only."]
    if VALIDATED.get(kind) is False:
        notes.append(f"Exploratory: the {kind} IP-weighted MSM failed validation ({AUDIT}).")
    effects = [dict(duration=int(d), estimate=e, lower=lo, upper=hi, se=s)
               for d, e, lo, hi, s in zip(res["durations"], res["estimate"], res["lower"], res["upper"], res["se"])]
    return dict(method=f"msm_{kind}", effects=effects, periods=[int(p) for p in periods], units=int(len(uniq)),
                treated_units=int(f.loc[first.notna(), unit].nunique()), max_weight=res["max_weight"],
                naive_adjusted=[dict(duration=int(d), estimate=e) for d, e in zip(naive["durations"], naive["estimate"])],
                bootstrap=res["resamples"], validated=bool(VALIDATED.get(kind)), notes=notes, audit=AUDIT)
