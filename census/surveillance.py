# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 95: years of potential life lost and aberration detection (backlog N72; CDC, *Principles of Epidemiology in
Public Health Practice*, 3rd ed., lessons 3-5).

Validation (``docs/audits/surveillance_validation.md``; criterion tag ``criterion-r95``):
- the age-adjusted YPLL-75 rate with its Fay-Feuer interval covered .888-.963 (populations 30,000 to 5 million,
  all-cause and overdose-like age patterns): validated;
- historical limits (A1) and EARS C2 (A2) flagged .005-.016 of null series (no trend, no overdispersion): validated.
  Both assume a flat baseline: with a 3% annual trend false alarms rose to .10 (A1) and .24 (A2) in large
  populations, and overdispersion raised A1 to .04. Check the trend first (joinpoint) and read a flag as a prompt to
  look, not as a finding.
All WONDER inputs are the owner's manual exports; the reader refuses suppressed cells (counts 1-9) in national
files, and sub-national YPLL uses bounds only (never an imputed count).
"""
import io
import re
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from . import surveillance_core as sc

AUDIT = "docs/audits/surveillance_validation.md"
VALIDATED = {"ypll": True, "historical_limits": True, "ears_c2": True}
TREND_NOTE = ("Aberration flags assume a flat baseline: under a 3% annual trend false alarms reached .10 "
              "(historical limits) and .24 (EARS C2) in validation. Check the trend (joinpoint) before reading a flag.")
WONDER_BANDS = [("<1", (0, 0)), ("1-4", (1, 4)), ("5-14", (5, 14)), ("15-24", (15, 24)), ("25-34", (25, 34)),
                ("35-44", (35, 44)), ("45-54", (45, 54)), ("55-64", (55, 64)), ("65-74", (65, 74)),
                ("75-84", (75, 84)), ("85+", (85, None))]


def _age_label(label: str) -> str:
    label = " ".join(str(label).strip().replace("–", "-").split())
    if label in ("< 1 year", "Under 1 year", "<1 year", "1"):
        return "<1"
    return re.sub(r"\s+years?$", "", label)


def ypll_from_wonder(path: str, end: int = 75, expected_sha256: Optional[str] = None, level: float = .90
                     ) -> Dict[str, Any]:
    """YPLL from a national WONDER export grouped by Ten-Year Age Groups and Sex (sexes summed; <1 and 1-4 kept
    apart). Deaths and populations are summed over the export's years, so rates are per person-year; ``ypll`` is
    the annual average."""
    from .vital_records import WonderExportError, _split_footer, read_wonder_reference
    try:
        ref = read_wonder_reference(path, expected_sha256=expected_sha256)   # integrity, grouping, suppression check
        suppressed_file = False
    except WonderExportError as exc:
        if "suppressed" not in str(exc):
            raise
        ref, suppressed_file = None, True
    text = open(path, "rb").read().decode("utf-8-sig")
    body, _ = _split_footer(text)
    src = pd.read_csv(io.StringIO("\n".join(body)), sep="\t", dtype=str, keep_default_na=False)
    if "Notes" in src:
        src = src[src.Notes.str.strip() != "Total"]
    age = next(c for c in ("Ten-Year Age Groups", "Ten-Year Age Group") if c in src)
    src = src.assign(a=src[age].map(_age_label))
    src = src[src.a.isin([b for b, _ in WONDER_BANDS])]
    num = lambda s: pd.to_numeric(s.str.replace(",", ""), errors="coerce")  # noqa: E731
    d = num(src.Deaths)
    supp = d.isna() | ((d >= 1) & (d <= 9))
    t = src.assign(d=d.where(~supp, 0), n=num(src.Population), k=supp.astype(int))
    g = t.groupby("a")[["d", "n", "k"]].sum()
    labels = [b for b, _ in WONDER_BANDS]; bands = [r for _, r in WONDER_BANDS]
    g = g.reindex(labels)
    if g[["d", "n"]].isna().any().any():
        raise ValueError("the export lacks an age band")
    from .wonder_inventory import years_from_parameters
    from .vital_records import parse_footer
    if ref is None:
        import hashlib
        raw = open(path, "rb").read()
        ref = dict(years=years_from_parameters(parse_footer(_split_footer(text)[1])["parameters"]),
                   sha256=hashlib.sha256(raw).hexdigest(), notes=[])
    years = len(ref["years"])
    if suppressed_file or g.k.sum():
        lo = sc.ypll((g.d+g.k).to_numpy(), g.n.to_numpy(), bands, end, level)
        hi = sc.ypll((g.d+9*g.k).to_numpy(), g.n.to_numpy(), bands, end, level)
        below = [lab for lab, (a, b) in WONDER_BANDS if b is not None and b < end and g.loc[lab, "k"] > 0]
        return dict(ypll_lower=lo["ypll"]/years, ypll_upper=hi["ypll"]/years, adjusted_rate_lower=lo["adjusted_rate"],
                    adjusted_rate_upper=hi["adjusted_rate"], end=end, years=ref["years"], sha256=ref["sha256"],
                    suppressed_cells=int(g.k.sum()), suppressed_bands_below_end=below, validated=False,
                    notes=["Suppressed cells (1-9 deaths) in this export: bounds only (each suppressed cell at 1 and "
                           "at 9); no point estimate."], audit=AUDIT)
    out = sc.ypll(g.d.to_numpy(), g.n.to_numpy(), bands, end, level)
    out.update(ypll=out["ypll"]/years, years=ref["years"], sha256=ref["sha256"], validated=VALIDATED["ypll"],
               notes=[f"YPLL to {end} by the CDC grouped-data method (band midpoints); age-adjusted to the 2000 US "
                      "standard over ages below the end point; rates per 100,000 person-years; Fay-Feuer interval.",
                      *ref["notes"]], audit=AUDIT)
    return out


def ypll_table(frame: pd.DataFrame, death_columns: Sequence[str], population_columns: Sequence[str],
               bands: Sequence[Sequence[Any]], end: int = 75, suppressed_columns: Optional[Sequence[str]] = None,
               level: float = .90) -> pd.DataFrame:
    """YPLL per row (area) from band death and population columns; rows with suppressed bands (boolean columns in
    ``suppressed_columns``) get bounds only."""
    rows = []
    bands = [tuple(b) for b in bands]
    for _, r in frame.iterrows():
        d = r[list(death_columns)].to_numpy(float); n = r[list(population_columns)].to_numpy(float)
        s = r[list(suppressed_columns)].to_numpy(bool) if suppressed_columns else np.zeros(len(d), bool)
        base = {"GEOID": r.get("GEOID")}
        if s.any():
            b = sc.ypll_bounds(np.where(s, 0, d), s, n, bands, end)
            rows.append({**base, **b, "suppressed_bands": int(s.sum()), "validated": False,
                         "notes": ["Suppressed bands (1-9 deaths): bounds only, no point estimate."]})
        else:
            y = sc.ypll(d, n, bands, end, level)
            rows.append({**base, "ypll": y["ypll"], "crude_rate": y["crude_rate"], "adjusted_rate": y["adjusted_rate"],
                         "ci_lower": y["lower"], "ci_upper": y["upper"], "suppressed_bands": 0, "validated": True,
                         "notes": []})
    return pd.DataFrame(rows)


def aberration(years: Sequence[int], rates: Sequence[float], se: Optional[Sequence[float]] = None,
               method: str = "historical_limits", baseline_years: int = 5) -> Dict[str, Any]:
    """Flag the latest year of an annual rate series against its own history."""
    y = np.asarray(years, int); r = np.asarray(rates, float)
    if len(y) != len(r) or np.any(np.diff(y) <= 0):
        raise ValueError("years must be increasing and match the rates")
    if method == "historical_limits":
        out = sc.historical_limits(r, float(se[-1]) if se is not None else 0.0, k=baseline_years)
    elif method == "ears_c2":
        out = sc.ears_c2(r)
    else:
        raise ValueError("method must be 'historical_limits' or 'ears_c2'")
    gaps = bool(np.any(np.diff(y) > 1))
    notes = [TREND_NOTE] + (["The series skips years (e.g. 2020); the baseline counts observed years."] if gaps else [])
    if method == "historical_limits" and baseline_years != 5:
        notes.append("Validated with a 5-year baseline.")
    return dict(method=method, year=int(y[-1]), validated=VALIDATED[method] and (method != "historical_limits" or
                baseline_years == 5), notes=notes, audit=AUDIT, **out)


def deviation_chart(names: Sequence[str], ratios: Sequence[float], lower: Sequence[float], upper: Sequence[float],
                    out_path: str, title: str = "") -> str:
    """CDC lesson 4 (Figure 4.25 style) deviation bar chart: current / historical mean on a log scale, with the
    historical limits as ratios; bars beyond the limits are highlighted."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    r = np.asarray(ratios, float); lo = np.asarray(lower, float); hi = np.asarray(upper, float)
    fig, ax = plt.subplots(figsize=(6, .4*len(r)+1))
    beyond = (r > hi) | (r < lo)
    ax.barh(range(len(r)), np.log2(r), color=np.where(beyond, "#b2182b", "#999999"))
    for i in range(len(r)):
        ax.plot([np.log2(lo[i]), np.log2(hi[i])], [i, i], color="black", lw=.8)
    ax.axvline(0, color="black", lw=.8)
    ax.set_yticks(range(len(r))); ax.set_yticklabels(names)
    ticks = [.25, .5, 1, 2, 4]; ax.set_xticks(np.log2(ticks)); ax.set_xticklabels([str(t) for t in ticks])
    ax.set_xlabel("Ratio of current to historical mean (log scale); lines: historical limits")
    if title:
        ax.set_title(title)
    fig.tight_layout(); fig.savefig(out_path, dpi=150); plt.close(fig)
    return out_path
