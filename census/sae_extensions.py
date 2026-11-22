# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fay-Herriot for proportions (arcsine) and across releases (Rao-Yu) (Round 80; backlog N57).

Validation: ``docs/audits/sae_extensions_validation.md`` (criterion ``sae_extensions_validation_criterion.md``);
computation is the frozen core :mod:`census.sae_extensions_core`.
"""
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from . import sae_extensions_core as sx

AUDIT = "docs/audits/sae_extensions_validation.md"
VALIDATED = {"P1": True, "P1q": True, "T1": True}  # docs/audits/sae_extensions_validation.json "passed"
SEED = 20282080


def _design(formula, frame):
    import patsy
    lhs, rhs = formula.split("~", 1)
    X = patsy.dmatrix(rhs, frame, return_type="dataframe", NA_action="raise")
    return lhs.strip(), X


def arcsine_small_area(frame: pd.DataFrame, formula: str, se_col: str, n_col: Optional[str] = None,
                       percent: Optional[bool] = None, bootstrap: int = 200, level: float = .90,
                       seed: int = SEED) -> pd.DataFrame:
    """P1: arcsine Fay-Herriot for direct proportions (outcome in [0, 1], or percent with ``percent=True``).

    The effective sample size is p(1 - p) / se^2 from the direct estimate, or ``n_col`` when given (needed for
    areas whose direct estimate is 0 or 1; without it those areas are refused). Returns one row per area with the
    bias-corrected estimate, bootstrap MSE, interval, the naive back-transform and the shrinkage factor."""
    y_name, X = _design(formula, frame)
    p = frame[y_name].to_numpy(float); se = frame[se_col].to_numpy(float)
    if percent is None:
        percent = bool(np.nanmax(p) > 1)
    if percent:
        p, se = p/100, se/100
    if ((p < 0) | (p > 1)).any() or np.isnan(p).any():
        raise ValueError("the outcome must be a proportion in [0, 1] (or a percentage)")
    if n_col:
        n = frame[n_col].to_numpy(float)
    else:
        with np.errstate(divide="ignore", invalid="ignore"):
            n = p*(1-p)/se**2
        bad = ~np.isfinite(n) | (n <= 0)
        if bad.any():
            ids = frame.loc[bad, "GEOID"].astype(str).tolist() if "GEOID" in frame else np.flatnonzero(bad).tolist()
            raise ValueError(f"{int(bad.sum())} area(s) have a direct estimate of 0 or 1 or a zero SE, so the effective "
                             f"sample size is undefined; give n_col or drop them: {ids[:10]}")
    r = sx.arcsine_fh(p, n, X.to_numpy(float), B=bootstrap, level=level, rng=np.random.default_rng(seed))
    use_q = not VALIDATED["P1"] and bool(VALIDATED["P1q"])
    lo, hi = (r["q_lower"], r["q_upper"]) if use_q else (r["lower"], r["upper"])
    scale = 100 if percent else 1
    out = pd.DataFrame({"GEOID": frame["GEOID"].astype(str).to_numpy() if "GEOID" in frame else np.arange(len(p)),
                        "direct": p*scale, "estimate": r["estimate"]*scale, "mse": r["mse"]*scale**2,
                        "ci_lower": lo*scale, "ci_upper": hi*scale, "naive_estimate": r["naive"]*scale,
                        "n_eff": n, "transformed_variance": r["direct_var_transformed"]})
    out.attrs.update(validated=bool(VALIDATED["P1"] or VALIDATED["P1q"]), interval="bootstrap quantile" if use_q else
                     "bootstrap MSE, normal", sigma2_u=r["A"], audit=AUDIT)
    return out


def temporal_small_area(frame: pd.DataFrame, formula: str, se_col: str, release_column: str = "Year",
                        period_years: int = 5, bootstrap: int = 100, level: float = .90,
                        seed: int = SEED) -> pd.DataFrame:
    """T1: Rao-Yu temporal Fay-Herriot over 2-3 non-overlapping releases; estimates for the latest release.

    Every area needs every release (balanced). Releases closer than ``period_years`` apart (overlapping five-year
    windows) are refused."""
    rel = sorted(frame[release_column].astype(int).unique())
    if len(rel) < 2:
        raise ValueError("temporal estimation needs at least two releases")
    if any(b-a < period_years for a, b in zip(rel, rel[1:])):
        raise ValueError(f"releases {rel} overlap (closer than {period_years} years): sampling errors would share years")
    f = frame.assign(GEOID=frame["GEOID"].astype(str)).sort_values(["GEOID", release_column])
    counts = f.groupby("GEOID")[release_column].nunique()
    if (counts != len(rel)).any():
        raise ValueError("every area needs every release (balanced panel)")
    y_name, X = _design(formula, f)
    m, T = counts.size, len(rel)
    y = f[y_name].to_numpy(float).reshape(m, T)
    D = (f[se_col].to_numpy(float)**2).reshape(m, T)
    if (D <= 0).any():
        raise ValueError("every area-release needs a positive SE")
    Xa = X.to_numpy(float).reshape(m, T, -1)
    r = sx.rao_yu(y, Xa, D, B=bootstrap, level=level, rng=np.random.default_rng(seed))
    out = pd.DataFrame({"GEOID": counts.index.to_numpy(), "release": rel[-1], "direct": y[:, -1],
                        "estimate": r["estimate"], "mse": r["mse"], "ci_lower": r["lower"], "ci_upper": r["upper"]})
    sv, su, rho = r["par"]
    out.attrs.update(validated=bool(VALIDATED["T1"]) and T <= 3, sigma2_v=sv, sigma2_u=su, rho=rho, releases=rel,
                     audit=AUDIT)
    return out
