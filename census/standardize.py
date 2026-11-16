# SPDX-License-Identifier: AGPL-3.0-or-later
"""Direct age standardization (PLAN_ROUND_20 A1).

A directly age-standardized rate is the weighted mean of age-specific rates,

    R = sum_a w_a * cases_a / pop_a,    sum_a w_a = 1,

with the weights w_a taken from a standard population (Klein & Schoenborn
2001, Healthy People 2010 Statistical Notes 20). It answers "what would the
rate be if this area had the standard age structure", so areas with different
age structures can be compared.

Bundled standard: ``us2000``, the 2000 U.S. standard population (Census
P25-1130) by single year of age 0-84 and 85+, built from the SEER table by
``scripts/update_standard_populations.py`` and checked against the SHA-256 in
its sidecar on every load (as the price tables are; census.data_integrity).

* :func:`standard_weights`: weights for any set of contiguous age bands.
* :func:`direct_standardize`: rates for many areas at once (arrays of shape
  (bands, areas)); undefined (NaN) where a band has no population.
* :func:`age_adjusted_interval`: Fay & Feuer (1997) gamma interval for an
  age-adjusted rate from registry counts (Statistics in Medicine 16:791-801),
  for count data without replicates (PLAN_ROUND_20 section 8).

For ACS estimates the replicate route is exact: evaluate the standardized
rate on each of the 80 replicates (the manifest derivation ``age_standardized``
does this through census.analysis.attach_replicates).
"""

import csv
import io
import os
from functools import lru_cache
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from .data_integrity import read_sidecar, read_table_bytes
from .geo import get_resource_path

STANDARDS = ("us2000",)
UPDATE_SCRIPT = "scripts/update_standard_populations.py"

Band = Tuple[int, Optional[int]]  # (lowest age, highest age or None for open-ended)


def standard_dir() -> str:
    return get_resource_path(os.path.join("data", "standard_populations"))


@lru_cache(maxsize=None)
def _load(standard: str) -> Tuple[Tuple[Tuple[int, Optional[int], int], ...], str]:
    if standard not in STANDARDS:
        raise ValueError(f"unknown standard population {standard!r}; expected one of {STANDARDS}")
    d = standard_dir()
    path, sidecar = os.path.join(d, f"{standard}.csv"), os.path.join(d, f"{standard}.json")
    expected = read_sidecar(sidecar).get("csv_sha256")
    raw, _ = read_table_bytes(path, True, expected, sidecar, UPDATE_SCRIPT)
    rows = []
    for r in csv.DictReader(io.StringIO(raw.decode("utf-8"), newline="")):
        hi = r["age_hi"].strip()
        rows.append((int(r["age_lo"]), int(hi) if hi else None, int(r["population"])))
    return tuple(rows), str(expected)


def standard_population(standard: str = "us2000") -> List[Tuple[int, Optional[int], int]]:
    """Rows (age_lo, age_hi or None, population) of a bundled standard."""
    return list(_load(standard)[0])


def standard_info(standard: str = "us2000") -> Dict[str, Any]:
    """Sidecar metadata (source, reference, SHA-256s) of a bundled standard."""
    _load(standard)  # integrity check
    return read_sidecar(os.path.join(standard_dir(), f"{standard}.json"))


def normalize_bands(bands: Sequence[Sequence[Any]]) -> List[Band]:
    """Validate age bands: [[lo, hi], ...] ascending, contiguous, integer; only the last
    may be open-ended (hi None). Raises ValueError with the reason."""
    if not isinstance(bands, (list, tuple)) or not bands:
        raise ValueError("bands must be a non-empty list of [lo, hi] pairs (hi null for the open last band)")
    out: List[Band] = []
    for i, b in enumerate(bands):
        if not isinstance(b, (list, tuple)) or len(b) != 2:
            raise ValueError(f"bands[{i}] must be [lo, hi]")
        lo, hi = b
        if isinstance(lo, bool) or not isinstance(lo, int) or lo < 0:
            raise ValueError(f"bands[{i}]: lo must be a non-negative integer")
        if hi is not None and (isinstance(hi, bool) or not isinstance(hi, int) or hi < lo):
            raise ValueError(f"bands[{i}]: hi must be an integer >= lo, or null for an open last band")
        if hi is None and i != len(bands) - 1:
            raise ValueError(f"bands[{i}]: only the last band may be open-ended")
        if out and lo != (out[-1][1] or 0) + 1:
            raise ValueError(f"bands[{i}] starts at {lo}; bands must be contiguous (previous band ends at "
                             f"{out[-1][1]})")
        out.append((lo, hi))
    return out


def standard_weights(bands: Sequence[Sequence[Any]], standard: str = "us2000") -> List[float]:
    """Weights (summing to 1) of a standard population over ``bands``.

    Bands need not start at 0 or reach the oldest age (e.g. adults 18-64); weights are
    then normalized over the ages covered. A closed band must end at or below the
    standard's last single age (84 for us2000), whose oldest row is open-ended (85+)."""
    nb = normalize_bands(bands)
    rows = standard_population(standard)
    last_single = max(lo for lo, hi, _ in rows if hi is not None)
    open_lo = next(lo for lo, hi, _ in rows if hi is None)
    totals = []
    for lo, hi in nb:
        if hi is not None and hi > last_single:
            raise ValueError(f"band [{lo}, {hi}] ends above {last_single}; the {standard} standard has "
                             f"{open_lo}+ as one open group, so use an open last band [{lo}, null]")
        if hi is None and lo > open_lo:
            raise ValueError(f"open band [{lo}, null] starts above {open_lo}, the standard's open group")
        t = 0
        for rlo, rhi, p in rows:
            if rhi is None:
                if hi is None:
                    t += p
            elif rlo >= lo and (hi is None or rhi <= hi):
                t += p
        totals.append(t)
    s = float(sum(totals))
    return [t / s for t in totals]


def direct_standardize(cases: Any, populations: Any, weights: Sequence[float]) -> np.ndarray:
    """Standardized rates sum_a w_a cases_a / pop_a for arrays of shape (bands, areas)
    (or (bands,) for one area). NaN where any band's population is zero or missing.
    ``weights`` must sum to 1 (within 1e-9)."""
    c = np.asarray(cases, dtype=float)
    p = np.asarray(populations, dtype=float)
    w = np.asarray(weights, dtype=float)
    if c.shape != p.shape or c.shape[0] != len(w):
        raise ValueError(f"shapes differ: cases {c.shape}, populations {p.shape}, {len(w)} weights")
    if abs(w.sum() - 1.0) > 1e-9:
        raise ValueError(f"weights sum to {w.sum()}, not 1")
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.where(p > 0, c / p, np.nan)
    w = w.reshape((-1,) + (1,) * (r.ndim - 1))
    return np.sum(w * r, axis=0)  # NaN propagates: an empty band leaves the rate undefined


def age_adjusted_interval(cases: Sequence[float], populations: Sequence[float], weights: Sequence[float],
                          confidence_level: float = 0.95) -> Dict[str, float]:
    """Fay-Feuer (1997) gamma interval for a directly age-adjusted rate from Poisson counts.

    y = sum w_i x_i / n_i, v = sum w_i^2 x_i / n_i^2, wm = max_i w_i / n_i;
    lower = v / (2y) * chi2_{a/2}(2y^2 / v) (0 when y = 0);
    upper = (v + wm^2) / (2(y + wm)) * chi2_{1-a/2}(2(y + wm)^2 / (v + wm^2)).
    Returns rate, lower, upper (per unit population; scale as needed)."""
    from scipy.stats import chi2

    x = np.asarray(cases, dtype=float)
    n = np.asarray(populations, dtype=float)
    w = np.asarray(weights, dtype=float)
    if (n <= 0).any():
        raise ValueError("every band needs a positive population")
    alpha = 1.0 - confidence_level
    y = float(np.sum(w * x / n))
    v = float(np.sum(w**2 * x / n**2))
    wm = float(np.max(w / n))
    lower = 0.0 if y == 0 or v == 0 else v / (2 * y) * float(chi2.ppf(alpha / 2, 2 * y**2 / v))
    vu, yu = v + wm**2, y + wm
    upper = vu / (2 * yu) * float(chi2.ppf(1 - alpha / 2, 2 * yu**2 / vu))
    return {"rate": y, "lower": lower, "upper": upper, "confidence_level": confidence_level}


# Set only from the pre-specified simulation report.
SMR_VALIDATED = True  # docs/audits/smr_validation.md (680707e criterion)


def indirect_standardize(observed, band_populations, reference_rates, band_replicates=None, level=0.90):
    """Indirect SMR and fixed-expected Garwood / combined log-Wald intervals.

    ``observed`` is a GEOID-indexed Series of nonnegative integer counts;
    ``band_populations`` a DataFrame with exactly the same ordered index and
    columns in reference-rate order (areas x bands). No implicit joins/drops.
    Replicates are an array (areas, bands, 80) in that order. Positive finite
    expected counts are required in every refit. The returned final GEOID
    ``all`` pools counts and expected counts BEFORE computing uncertainty.
    Rates are fixed; their uncertainty and between-area dependence are not
    covered. At O=0 only the exact fixed-E interval is defined.
    """
    import pandas as pd
    from scipy.stats import chi2, norm
    if not isinstance(observed, pd.Series) or not isinstance(band_populations, pd.DataFrame):
        raise ValueError("observed must be a GEOID-indexed Series; band_populations a DataFrame")
    if (not observed.index.equals(band_populations.index) or observed.index.has_duplicates
            or not len(observed) or observed.index.isna().any()
            or "all" in observed.index.astype(str)):
        raise ValueError("area indexes must match exactly, be unique/nonmissing, and exclude reserved GEOID 'all'")
    if observed.index.astype(str).has_duplicates:
        raise ValueError("GEOIDs collide after string conversion")
    if not 0 < level < 1:
        raise ValueError("level must be between zero and one")
    o, pop, rates = observed.to_numpy(float), band_populations.to_numpy(float), np.asarray(reference_rates, float)
    if rates.ndim != 1 or rates.size != pop.shape[1] or not rates.size or not np.isfinite(rates).all() or (rates <= 0).any():
        raise ValueError("reference_rates must be finite positive numbers, one per population band")
    if not np.isfinite(o).all() or (o < 0).any() or (o != np.floor(o)).any():
        raise ValueError("observed counts must be finite nonnegative integers")
    if not np.isfinite(pop).all() or (pop < 0).any():
        raise ValueError("band populations must be finite and nonnegative")
    e = pop@rates
    if (e <= 0).any():
        raise ValueError("expected counts must be positive")
    notes = ["Reference rates fixed; exact Garwood interval conditions on expected counts."]
    o, e = np.r_[o, o.sum()], np.r_[e, e.sum()]
    ve = np.zeros(len(o))
    if band_replicates is not None:
        rep = np.asarray(band_replicates, float)
        if rep.shape != (*pop.shape, 80) or not np.isfinite(rep).all() or (rep < 0).any():
            raise ValueError("band_replicates must be finite nonnegative (areas, bands, 80)")
        er = np.einsum("abr,b->ar", rep, rates)
        er = np.vstack((er, er.sum(axis=0)))
        if (er <= 0).any():
            raise ValueError("replicate expected counts must be positive")
        ve = .05*np.sum((np.log(er)-np.log(e[:, None]))**2, axis=1)
    else:
        notes.append("No band replicates: expected-count uncertainty set to zero.")
    alpha = 1-level
    lower = np.zeros(len(o)); positive = o > 0
    lower[positive] = chi2.ppf(alpha/2, 2*o[positive])/(2*e[positive])
    upper = chi2.ppf(1-alpha/2, 2*o+2)/(2*e)
    smr = o/e
    log, se, lo, hi, p = (np.full(len(o), np.nan) for _ in range(5))
    log[positive] = np.log(smr[positive])
    se[positive] = np.sqrt(1/o[positive]+ve[positive])
    z = norm.ppf(1-alpha/2)
    lo[positive], hi[positive] = np.exp(log[positive]-z*se[positive]), np.exp(log[positive]+z*se[positive])
    p[positive] = 2*norm.sf(np.abs(log[positive]/se[positive]))
    rownotes = [notes+([] if pos else ["O=0: combined log interval and Wald test undefined."]) for pos in positive]
    return pd.DataFrame(dict(GEOID=list(observed.index.astype(str))+["all"], observed=o, expected=e,
                             smr=smr, log_smr=log, se_log_smr=se, smr_lower=lo, smr_upper=hi,
                             smr_exact_lower=lower, smr_exact_upper=upper, p_value=p, notes=rownotes))
