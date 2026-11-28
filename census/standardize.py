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
SMR_REFERENCE_VALIDATED = True  # criterion 134bf7f; docs/audits/smr_reference_validation.md
SMR_VALIDATED = True  # docs/audits/smr_validation.md (680707e criterion)
# Round 55 (criterion dd6d6b7; docs/audits/short_series_reference_validation.md): adding the sampling variance of
# survey-estimated reference person-years covered .892-.908 (reference population CV .02-.08); without it
# .863-.907 (smallest at CV .08 with 500 reference deaths and E = 100).
SMR_REFERENCE_POPULATION_VALIDATED = True
# Round 51 (criterion 2837bfb; docs/audits/negative_replicates_validation.md): negative band replicates used
# as published ("accept", .903-.922) or clipped at zero ("clip", .891-.917) both passed in all eight cells.
# The default is "accept": the expected count is linear in the bands, so no information is discarded.
SMR_NEGATIVE_REPLICATES_VALIDATED = {"accept": True, "clip": True}
DEFAULT_SMR_NEGATIVE_REPLICATES = "accept"


def indirect_standardize(observed, band_populations, reference_rates, band_replicates=None, level=0.90,
                         *, period_years=1, reference_counts=None, negative_replicates=None,
                         reference_population_se=None):
    """Indirect SMR and fixed-expected Garwood / combined log-Wald intervals.

    ``observed`` is a GEOID-indexed Series of nonnegative integer counts;
    ``band_populations`` a DataFrame with exactly the same ordered index and
    columns in reference-rate order (areas x bands). No implicit joins/drops.
    Replicates are an array (areas, bands, 80) in that order. Positive finite
    expected counts are required in every refit. This validated implementation
    handles negative band replicates by ``negative_replicates`` (Round 51): ``"accept"`` (the default,
    validated) uses them as published (the expected count is linear in the bands; every replicate
    expected count must still be positive); ``"clip"`` (validated) sets them to zero first; ``"refuse"``
    raises (the strict pre-Round 51 policy, kept by registered manifests). The returned final GEOID
    ``all`` pools counts and expected counts BEFORE computing uncertainty.
    Rates are per person-year; period_years multiplies expected counts and every
    replicate. Optional positive integer reference_counts adds independent-Poisson
    reference-rate uncertainty. Reference person-years must be treated as fixed.
    Shared reference uncertainty is pooled by band before squaring, not averaged
    as independent area uncertainty. ``reference_population_se`` (Round 55; needs reference_counts): per-band
    SEs of the reference person-years P_b = D_b / rate_b when they are survey estimates (e.g. ACS); adds
    sum_b (E_b/E)^2 (se_b/P_b)^2 to the log variance. For an internal reference, ignoring positive
    study/reference covariance makes intervals conservative (not refused).
    At O=0 only the exact fixed-E interval is defined. Fixed-E exact intervals do
    not incorporate population or reference-rate uncertainty.
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
    if isinstance(period_years, (bool, np.bool_)) or not isinstance(period_years, (int, np.integer)) or period_years <= 0:
        raise ValueError("period_years must be a positive integer")
    reference = None
    if reference_counts is not None:
        reference = np.asarray(reference_counts)
        if (reference.ndim != 1 or reference.size != rates.size or reference.dtype.kind not in "iuf"
                or any(isinstance(d,(bool,np.bool_)) for d in np.asarray(reference_counts,dtype=object).flat)
                or not np.isfinite(reference).all() or (reference <= 0).any()
                or (reference != np.floor(reference)).any()):
            raise ValueError("reference_counts must be positive integers, one per population band; zero reference deaths refused")
        reference = reference.astype(float)
    ref_cv2 = None
    if reference_population_se is not None:
        if reference is None:
            raise ValueError("reference_population_se requires reference_counts (reference rates are D_b / P_b)")
        rse = np.asarray(reference_population_se, float)
        if rse.ndim != 1 or rse.size != rates.size or not np.isfinite(rse).all() or (rse < 0).any():
            raise ValueError("reference_population_se must be finite nonnegative, one per population band")
        ref_cv2 = (rse*rates/reference)**2      # (se_b / P_b)^2 with P_b = D_b / rate_b
    e = period_years*(pop@rates)
    if not np.isfinite(e).all() or (e <= 0).any():
        raise ValueError("expected counts must be positive")
    notes = ["Reference rates fixed; exact Garwood interval conditions on expected counts."]
    if period_years != 1:
        notes.append(f"Reference rates are per person-year; expected counts multiply band populations by period_years={period_years}.")
    if reference is not None:
        notes[0] = "Combined log interval includes independent-Poisson reference-rate uncertainty; exact Garwood interval still conditions on expected counts."
        if ref_cv2 is None:
            notes.append("Reference person-years are treated as fixed. For internal standardization (study areas included in the reference population), ignoring positive study/reference covariance makes the combined interval conservative; no refusal.")
    o, e = np.r_[o, o.sum()], np.r_[e, e.sum()]
    ve = np.zeros(len(o))
    if band_replicates is not None:
        rep = np.asarray(band_replicates, float)
        if negative_replicates is None:
            negative_replicates = DEFAULT_SMR_NEGATIVE_REPLICATES
        if negative_replicates not in ("refuse", "accept", "clip"):
            raise ValueError("negative_replicates must be 'refuse', 'accept' or 'clip'")
        if rep.shape != (*pop.shape, 80) or not np.isfinite(rep).all():
            raise ValueError("band_replicates must be finite (areas, bands, 80)")
        negative = int((rep < 0).sum())
        if negative and negative_replicates == "refuse":
            raise ValueError("band_replicates must be finite nonnegative (areas, bands, 80)")
        if negative:
            if negative_replicates == "clip":
                rep = np.maximum(rep, 0.)
            notes.append(f"{negative} negative band replicate value(s) "
                         + ("set to zero before the expected-count refits." if negative_replicates == "clip"
                            else "used as published (expected counts are linear in the bands)."))
        er = period_years*np.einsum("abr,b->ar", rep, rates)
        er = np.vstack((er, er.sum(axis=0)))
        if (er <= 0).any():
            raise ValueError("replicate expected counts must be positive")
        ve = .05*np.sum((np.log(er)-np.log(e[:, None]))**2, axis=1)
    else:
        notes.append("No band replicates: expected-count uncertainty set to zero.")
    reference_variance = np.zeros(len(o))
    if reference is not None:
        components = period_years*pop*rates
        components = np.vstack((components, components.sum(axis=0)))
        reference_variance = np.sum((components/e[:,None])**2*(1/reference+(0 if ref_cv2 is None else ref_cv2)), axis=1)
        if ref_cv2 is not None:
            notes.append("Reference person-years are survey estimates: their sampling variance (se_b/P_b)^2 is added per band "
                         "(Round 55); covariance with study-area estimates is ignored (conservative for an internal reference).")
    alpha = 1-level
    lower = np.zeros(len(o)); positive = o > 0
    lower[positive] = chi2.ppf(alpha/2, 2*o[positive])/(2*e[positive])
    upper = chi2.ppf(1-alpha/2, 2*o+2)/(2*e)
    smr = o/e
    log, se, lo, hi, p = (np.full(len(o), np.nan) for _ in range(5))
    log[positive] = np.log(smr[positive])
    se[positive] = np.sqrt(1/o[positive]+ve[positive]+reference_variance[positive])
    z = norm.ppf(1-alpha/2)
    lo[positive], hi[positive] = np.exp(log[positive]-z*se[positive]), np.exp(log[positive]+z*se[positive])
    p[positive] = 2*norm.sf(np.abs(log[positive]/se[positive]))
    rownotes = [notes+([] if pos else ["O=0: combined log interval and Wald test undefined."]) for pos in positive]
    result = pd.DataFrame(dict(GEOID=list(observed.index.astype(str))+["all"], observed=o, expected=e,
                             smr=smr, log_smr=log, se_log_smr=se, smr_lower=lo, smr_upper=hi,
                             smr_exact_lower=lower, smr_exact_upper=upper, p_value=p, notes=rownotes))
    if reference is not None or period_years != 1:
        result["period_years"] = int(period_years)
        result["variance_log_reference"] = reference_variance
    return result


def confounding_adjustment_screen(
    frame,
    deaths_col: str,
    population_col: str,
    exposure_col: str,
    confounders,
    *,
    exposure_scale: float = 1.0,
    confidence_level: float = 0.90,
):
    """Compare crude vs. confounder-adjusted Poisson rate ratios (HC3 robust SEs) for ecologic/surveillance frames.

    Flags demographic/urban-rural confounding and Simpson's-paradox sign flips (Round 202 / N128).
    Returns ``crude``, ``adjusted``, ``cie_pct`` (percentage change-in-estimate on the RR scale),
    and ``sign_flipped`` (True when crude and adjusted RRs lie on opposite sides of 1.0).
    """
    import pandas as pd
    import statsmodels.api as sm
    from scipy.stats import norm

    conf_cols = [str(c) for c in confounders]
    if not conf_cols:
        raise ValueError("confounders must contain at least one column name")
    if exposure_scale <= 0 or not np.isfinite(exposure_scale):
        raise ValueError("exposure_scale must be finite and positive")
    if not 0 < confidence_level < 1:
        raise ValueError("confidence_level must be between 0 and 1")

    cols = [deaths_col, population_col, exposure_col, *conf_cols]
    df = frame[cols].apply(pd.to_numeric, errors="coerce").dropna().copy()
    df = df[(df[deaths_col] >= 0) & (df[population_col] > 0)].reset_index(drop=True)
    if len(df) <= len(conf_cols) + 2:
        raise ValueError(f"insufficient complete rows ({len(df)}) for {len(conf_cols)} confounders")

    exp_scaled = df[exposure_col].to_numpy(float) / float(exposure_scale)
    y = df[deaths_col].to_numpy(float)
    offset = np.log(df[population_col].to_numpy(float))
    z = float(norm.ppf(0.5 + confidence_level / 2.0))

    def _fit(X_df: pd.DataFrame):
        fit = sm.GLM(y, sm.add_constant(X_df), family=sm.families.Poisson(), offset=offset).fit(cov_type="HC3")
        b = float(fit.params["exposure"])
        se = float(fit.bse["exposure"])
        return {
            "log_rr": round(b, 6),
            "se": round(se, 6),
            "rr": round(float(np.exp(b)), 4),
            "ci_lower": round(float(np.exp(b - z * se)), 4),
            "ci_upper": round(float(np.exp(b + z * se)), 4),
        }

    crude = _fit(pd.DataFrame({"exposure": exp_scaled}))
    adj_df = pd.DataFrame({"exposure": exp_scaled})
    for c in conf_cols:
        adj_df[c] = df[c].to_numpy(float)
    adjusted = _fit(adj_df)

    cie_pct = round(100.0 * (adjusted["rr"] - crude["rr"]) / max(crude["rr"], 1e-12), 2)
    sign_flipped = bool((crude["rr"] - 1.0) * (adjusted["rr"] - 1.0) < 0.0)
    return {
        "n_obs": int(len(df)),
        "exposure": exposure_col,
        "exposure_scale": float(exposure_scale),
        "confounders": conf_cols,
        "confidence_level": float(confidence_level),
        "crude": crude,
        "adjusted": adjusted,
        "cie_pct": cie_pct,
        "sign_flipped": sign_flipped,
        "validated": False,
        "note": "Exploratory HC3 Poisson confounding screen; for confirmatory inference use a pre-registered manifest with spatial/replicate SEs.",
    }
