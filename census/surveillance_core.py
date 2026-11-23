# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 95 frozen core: years of potential life lost and aberration detection (backlog N72; CDC, *Principles of
Epidemiology in Public Health Practice*, 3rd ed., lessons 3-5).

Y1 YPLL to an end point E (an age-band boundary, e.g. 65 or 75), from age-band death counts d_a with bands [lo_a,
hi_a] wholly below E: YPLL = sum_a d_a (E - m_a), m_a = (lo_a + hi_a + 1)/2 the band midpoint (CDC grouped-data
method). Crude YPLL rate = 100,000 YPLL / sum_a pop_a. Age-adjusted YPLL rate = 100,000 sum_a w_a (E - m_a) d_a /
pop_a with 2000 US standard weights over the bands below E; 90% Fay-Feuer gamma interval treating it as a weighted
sum of Poisson counts (census.standardize.age_adjusted_interval with weights w_a (E - m_a)).
Suppressed bands (counts 1-9) give bounds: YPLL with each suppressed count at 1 and at 9; nothing else is derived.

A1 historical limits (MMWR style, annual): baseline = the previous k rates (k declared, default 5); flag "high" when
the current rate exceeds mean_b + 2 sqrt(sd_b^2 + se_t^2), "low" when below mean_b - 2 sqrt(...) (se_t the current
rate's standard error; sd_b the baseline sample SD).
A2 EARS C2 (annual adaptation): baseline = rates at t-9..t-3 (7 years, 2-year guard band); z = (r_t - mean_b) /
sd_b; flag when z > 3.
"""
from typing import Any, Dict, Optional, Sequence, Tuple

import numpy as np

from .standardize import age_adjusted_interval, standard_weights


def _bands_below(bands: Sequence[Tuple[int, Optional[int]]], end: int):
    keep = []
    for lo, hi in bands:
        if hi is not None and hi < end:
            keep.append((lo, hi))
        elif lo < end:
            raise ValueError(f"end point {end} must fall on a band boundary; band [{lo}, {hi}] straddles it")
    if not keep:
        raise ValueError("no age band lies wholly below the end point")
    return keep


def ypll(deaths, populations, bands, end: int = 75, level: float = .90) -> Dict[str, Any]:
    """YPLL, crude and age-adjusted YPLL rates (per 100,000) with a Fay-Feuer interval for one area."""
    keep = _bands_below(bands, end)
    idx = [list(map(tuple, bands)).index(b) for b in keep]
    d = np.asarray(deaths, float)[idx]; n = np.asarray(populations, float)[idx]
    mid = np.array([(lo+hi+1)/2 for lo, hi in keep]); yl = end-mid
    w = np.array(standard_weights([[lo, hi] for lo, hi in keep]))
    total = float(np.sum(d*yl))
    iv = age_adjusted_interval(d, n, w*yl, confidence_level=level)
    return dict(ypll=total, crude_rate=1e5*total/float(n.sum()), adjusted_rate=1e5*iv["rate"],
                lower=1e5*iv["lower"], upper=1e5*iv["upper"], end=end, bands=keep)


def ypll_bounds(deaths, suppressed, populations, bands, end: int = 75) -> Dict[str, float]:
    """Bounds on YPLL and its age-adjusted rate when ``suppressed`` bands (boolean) hold counts in 1..9."""
    d = np.asarray(deaths, float).copy(); s = np.asarray(suppressed, bool)
    lo_d, hi_d = d.copy(), d.copy(); lo_d[s] = 1; hi_d[s] = 9
    a, b = ypll(lo_d, populations, bands, end), ypll(hi_d, populations, bands, end)
    return dict(ypll_lower=a["ypll"], ypll_upper=b["ypll"], adjusted_rate_lower=a["adjusted_rate"],
                adjusted_rate_upper=b["adjusted_rate"])


def historical_limits(rates: Sequence[float], se_current: float = 0.0, k: int = 5) -> Dict[str, Any]:
    r = np.asarray(rates, float)
    if len(r) < k+1:
        raise ValueError(f"need {k} baseline years before the current one")
    base, cur = r[-k-1:-1], r[-1]
    m, sd = float(base.mean()), float(base.std(ddof=1))
    half = 2*np.sqrt(sd**2+float(se_current)**2)
    flag = "high" if cur > m+half else ("low" if cur < m-half else "none")
    return dict(current=float(cur), baseline_mean=m, baseline_sd=sd, lower_limit=m-half, upper_limit=m+half,
                flag=flag, ratio=float(cur/m) if m else np.nan)


def ears_c2(rates: Sequence[float]) -> Dict[str, Any]:
    r = np.asarray(rates, float)
    if len(r) < 10:
        raise ValueError("EARS C2 needs 9 earlier years (7 baseline + 2 guard)")
    base, cur = r[-10:-3], r[-1]
    m, sd = float(base.mean()), float(base.std(ddof=1))
    z = (cur-m)/sd if sd > 0 else np.inf*np.sign(cur-m)
    return dict(current=float(cur), baseline_mean=m, baseline_sd=sd, z=float(z), flag="high" if z > 3 else "none")
