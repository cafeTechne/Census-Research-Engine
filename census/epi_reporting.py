# SPDX-License-Identifier: AGPL-3.0-or-later
"""Epidemiologic reporting conventions (Round 82; backlog N59).

Implements the reporting guidance of Bovbjerg, *Foundations of Epidemiology* (2020; mapping in
``docs/literature/foundations_of_epidemiology.md``):
- measure types (chapter 2): counts, prevalence, incidence proportion, incidence rate, levels;
- design labels for area analyses: ecologic and cross-sectional (chapters 1 and 9);
- interpretation sentences for ratios and differences (chapters 4 and 5);
- item nonresponse: ACS allocation (imputation) shares from the B99 tables (chapter 6);
- a "Table 1" of the study areas by exposure tertile and a generated limitations list (Appendix 1).
No new inferential statistics.
"""
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

import numpy as np
import pandas as pd
from scipy import stats

MEASURE_TYPES = ("count", "prevalence", "incidence_proportion", "incidence_rate", "level", "ratio", "index",
                 "expected_count", "unspecified")
MEASURE_TEXT = {
    "count": "a count",
    "prevalence": "a prevalence (share of the universe with the characteristic during the survey period; existing, "
                  "not new, cases)",
    "incidence_proportion": "an incidence proportion (new events per person at risk over the period)",
    "incidence_rate": "an incidence rate (new events per person-time over the period)",
    "level": "a level (median, dollar amount, life expectancy or similar)",
    "ratio": "a ratio of two estimates",
    "index": "a composite index",
    "expected_count": "an expected count from reference rates",
    "unspecified": "a measure of unspecified type",
}
ECOLOGIC_NOTE = ("Ecologic design: units are areas, so associations describe areas, not individuals; applying them "
                 "to individuals is the ecologic fallacy.")
CROSS_SECTIONAL_NOTE = ("Cross-sectional design: exposure and outcome are measured over the same survey window, so "
                        "their temporal order is not established; results are associations suited to hypothesis "
                        "generation, not evidence that one causes the other.")
PREVALENCE_NOTE = ("Survey-based measures (ACS, PLACES) are prevalences: they count existing cases, which depend on "
                   "both the rate of new cases and how long the condition lasts.")
ALLOCATION_LIMIT = .05
ASSOCIATION_WORDS = ("is associated with", "was associated with", "compared with")
CAUSAL_WORDS = ("causes", "caused by", "leads to", "led to", "effect of", "impact of", "results in", "drives")

_DERIVATION_TYPES = {"proportion": "prevalence", "age_standardized": "prevalence", "sum": "count",
                     "difference": "count", "ratio": "ratio", "expected_count": "expected_count",
                     "median": "level", "mean": "level", "log": "level"}
_EXTERNAL_TYPES = {"wonder": "incidence_rate", "places": "prevalence", "usaleep": "level"}
_CHR_TYPES = {"v037": "incidence_proportion", "v001": "incidence_rate", "v127": "incidence_rate", "v147": "level"}


def external_measure_type(spec: Mapping[str, Any]) -> str:
    """Measure type of a manifest external variable: declared ``measure_type`` wins; else inferred by source."""
    declared = spec.get("measure_type")
    if declared in MEASURE_TYPES:
        return declared
    src = str(spec.get("source", "")).lower()
    if src == "wonder":
        return "count" if str(spec.get("measure", "")).lower() == "deaths" else "incidence_rate"
    if src == "chr":
        return _CHR_TYPES.get(str(spec.get("measure")), "unspecified")
    return _EXTERNAL_TYPES.get(src, "unspecified")


def manifest_measure_types(m: Mapping[str, Any]) -> Dict[str, str]:
    """Measure type of every manifest name (variables, derivations, indices, external variables)."""
    out: Dict[str, str] = {}
    for v in m.get("variables") or []:
        out[v["name"]] = "level" if any(t in str(v.get("ref", "")) for t in ("B19013", "B19113", "B25064", "B25077",
                                                                                 "B19301", "B01002")) else "count"
    for d in m.get("derivations") or []:
        if "person_years" in d:
            out[d.get("name")] = "expected_count"
        else:
            out[d.get("name")] = _DERIVATION_TYPES.get(str(d.get("op")), "unspecified")
    for ix in m.get("indices") or []:
        out[ix.get("name")] = "index"
    for e in m.get("external") or []:
        t = external_measure_type(e)
        out[e.get("name")] = "incidence_rate" if t == "count" else t  # a WONDER deaths export's rate column
        out[f"{e.get('name')}_numerator"] = "count"
        out[f"{e.get('name')}_denominator"] = "count"
    return out


def analysis_outcomes(m: Mapping[str, Any]) -> List[str]:
    """Names used as outcomes by the manifest's analyses (formula left-hand side, outcome, observed, groups)."""
    names: List[str] = []
    for a in m.get("analyses") or []:
        f = str(a.get("formula", ""))
        if "~" in f:
            names.append(f.split("~")[0].strip())
        for k in ("outcome", "observed", "variable"):
            if isinstance(a.get(k), str):
                names.append(a[k])
        for k in ("groups", "rates"):
            if isinstance(a.get(k), list) and a.get("method") in ("disparity", "kitagawa"):
                names += [x for x in a[k] if isinstance(x, str)]
    return list(dict.fromkeys(n for n in names if n))


def design_labels(level: Optional[str], individual: bool = False) -> Dict[str, Any]:
    """Design labels: area analyses are ecologic and cross-sectional; PUMS person-level analyses are
    cross-sectional only."""
    if individual:
        return {"design": ["cross-sectional"], "notes": [CROSS_SECTIONAL_NOTE]}
    return {"design": ["ecologic", "cross-sectional"], "unit": level or "area",
            "notes": [ECOLOGIC_NOTE, CROSS_SECTIONAL_NOTE]}


def causal_terms(text: str) -> List[str]:
    """Causal phrases present in ``text`` (generated text for ecologic, cross-sectional designs must avoid them)."""
    low = f" {str(text).lower()} "
    return [w for w in CAUSAL_WORDS if f" {w} " in low]


# ------------------------------------------------------------------ interpretation templates
def rescale_interval(estimate: float, lower: float, upper: float, from_level: float = .90, to_level: float = .95,
                     log_scale: bool = False) -> Dict[str, float]:
    """Re-express a symmetric normal interval at another confidence level (on the log scale for ratios)."""
    f = (lambda x: np.log(x)) if log_scale else (lambda x: x)  # noqa: E731
    g = (lambda x: float(np.exp(x))) if log_scale else float  # noqa: E731
    z0, z1 = stats.norm.ppf(.5+from_level/2), stats.norm.ppf(.5+to_level/2)
    e, lo, hi = f(estimate), f(lower), f(upper)
    half = (hi-lo)/2*z1/z0
    return {"estimate": g(e), "lower": g(e-half), "upper": g(e+half), "level": to_level}


def interpret_ratio(kind: str, ratio: float, lower: float, upper: float, outcome: str, exposed: str,
                    unexposed: str, period: Optional[str] = None, level: float = .90) -> str:
    """Bovbjerg's template: "The [kind] of [outcome] was [ratio] times as high in [exposed] compared with
    [unexposed] [over period] (90% CI ...)." ``kind``: risk, rate, odds or prevalence."""
    over = f" over {period}" if period else ""
    sig = lower > 1 or upper < 1
    base = (f"The {kind} of {outcome} was {ratio:.2f} times as high in {exposed} compared with {unexposed}{over} "
            f"({level:.0%} CI {lower:.2f} to {upper:.2f})")
    if not sig:
        base += "; the interval includes 1, so these data give no evidence of a difference (not evidence of no difference)"
    return base+"."


def interpret_difference(kind: str, diff: float, lower: float, upper: float, outcome: str, exposed: str,
                         unexposed: str, unit: str = "percentage points", period: Optional[str] = None,
                         level: float = .90) -> str:
    """Absolute-measure template: "[outcome] [kind] was [diff] [unit] higher/lower in [exposed] than [unexposed]"."""
    over = f" over {period}" if period else ""
    word = "higher" if diff >= 0 else "lower"
    base = (f"The {kind} of {outcome} was {abs(diff):.2f} {unit} {word} in {exposed} than in {unexposed}{over} "
            f"({level:.0%} CI {lower:.2f} to {upper:.2f})")
    if lower <= 0 <= upper:
        base += "; the interval includes 0, so these data give no evidence of a difference (not evidence of no difference)"
    return base+"."


# ------------------------------------------------------------------ allocation (item imputation)
# Analysis-table family -> B99 allocation tables (Census "Allocation of ..." tables; detailed-table universes).
ALLOCATION_TABLES = {
    "B27": ["B992701"], "C27": ["B992701"], "S2701": ["B992701"],
    "B18": ["B99181"], "C18": ["B99181"], "S1810": ["B99181"],
    "B17": ["B99172", "B99171"], "C17": ["B99172", "B99171"], "S1701": ["B99172", "B99171"],
    "B19": ["B99192"], "S1901": ["B99192"], "B20": ["B99201"],
    "B23": ["B99231"], "C23": ["B99231"], "S2301": ["B99231"],
    "B15": ["B99151"], "C15": ["B99151"], "S1501": ["B99151"],
    "B16": ["B99161"], "C16": ["B99161"], "B05": ["B99051"], "B21": ["B99211"], "B14": ["B99141"],
    "B07": ["B99071"], "B02": ["B99021"], "B03": ["B99031"],
    "B25003": ["B99252"], "B25044": ["B992512"], "B25064": ["B992518"], "B25070": ["B992518"],
}


def allocation_tables_for(code: str) -> List[str]:
    """B99 allocation tables for an ACS table or variable code (longest matching prefix)."""
    c = str(code).upper().split(":")[-1]
    for k in sorted(ALLOCATION_TABLES, key=len, reverse=True):
        if c.startswith(k):
            return list(ALLOCATION_TABLES[k])
    return []


def allocation_lines(labels: Mapping[str, str]) -> Dict[str, List[str]]:
    """Split a B99 table's leaf lines into allocated and not-allocated sets from their labels.

    ``labels``: {variable code: label}. Allocated leaves end "Allocated", start "One or more" or record a positive or
    zero-dollar allocation ("More than 0 ...", "10 to ...", "100 percent ...", "Dollar value of zero allocated");
    not-allocated leaves end "Not allocated" or start "No ". Returns {"allocated": [...], "not_allocated": [...]}."""
    clean = {k: str(v).replace("Estimate!!", "").rstrip(":") for k, v in labels.items()}
    leaves = [k for k, v in clean.items() if not any(o != k and w.startswith(v+"!!") for o, w in clean.items())]
    out = {"allocated": [], "not_allocated": []}
    for k in sorted(leaves):
        last = clean[k].split("!!")[-1].strip()
        lo = last.lower()
        if lo.startswith("not allocated") or lo.startswith("no "):
            out["not_allocated"].append(k)
        elif "allocat" in lo:
            out["allocated"].append(k)
    return out


def allocation_shares(values: pd.DataFrame, labels: Mapping[str, str]) -> pd.Series:
    """Allocated share per row: allocated / (allocated + not allocated) leaf totals of one B99 table."""
    parts = allocation_lines(labels)
    if not parts["allocated"] or not parts["not_allocated"]:
        raise ValueError("could not identify allocated and not-allocated lines in the B99 table")
    a = values[parts["allocated"]].apply(pd.to_numeric, errors="coerce").sum(axis=1)
    n = values[parts["not_allocated"]].apply(pd.to_numeric, errors="coerce").sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        return a/(a+n)


def fetch_allocation(tables: Iterable[str], year: int, geo_level: str, states: Sequence[str],
                     client: Any = None) -> pd.DataFrame:
    """Allocated shares (GEOID, table, allocated_share) for B99 tables from the Census API (cached)."""
    from .api import CensusAPIClient
    from .metadata import table_variables
    client = client or CensusAPIClient()
    rows = []
    for t in dict.fromkeys(tables):
        meta, _ = table_variables(t, "acs5", year)
        labels = {k[:-1]: v["label"] for k, v in meta.items() if k.endswith("E")}
        for st in states:
            d = client.fetch(year, st, t, geo_level=geo_level)
            if d is None:
                raise ValueError(f"{t} {year} {geo_level} {st}: {client.last_error}")
            f = pd.DataFrame(d[1:], columns=d[0]).loc[:, lambda x: ~x.columns.duplicated()]
            geo = f["state"]+(f["county"] if "county" in f else "")+(f["tract"] if "tract" in f else "")
            vals = pd.DataFrame({k: f.get(k+"E") for k in labels if k+"E" in f.columns})
            share = allocation_shares(vals, {k: labels[k] for k in vals.columns})
            rows.append(pd.DataFrame({"GEOID": geo.to_numpy(), "table": t, "allocated_share": share.to_numpy()}))
    return pd.concat(rows, ignore_index=True)


def allocation_summary(shares: pd.DataFrame, geoids: Optional[Iterable[str]] = None) -> List[Dict[str, Any]]:
    """Per table: median and maximum allocated share over the analysed areas, and the >5% flag."""
    s = shares if geoids is None else shares[shares["GEOID"].isin(set(map(str, geoids)))]
    out = []
    for t, g in s.groupby("table"):
        med = float(g["allocated_share"].median())
        out.append({"table": t, "areas": int(g["allocated_share"].notna().sum()), "median_allocated_share": med,
                    "max_allocated_share": float(g["allocated_share"].max()), "above_limit": med > ALLOCATION_LIMIT})
    return out


def allocation_note(summary: Sequence[Mapping[str, Any]]) -> List[str]:
    return [f"Item nonresponse: a median {r['median_allocated_share']:.1%} of answers behind {r['table']} were "
            f"allocated (imputed by the Census Bureau) in the analysed areas, above the {ALLOCATION_LIMIT:.0%} level at "
            "which missing data deserve discussion; imputed answers follow the Bureau's hot-deck model and may "
            "bias associations." for r in summary if r["above_limit"]]


# ------------------------------------------------------------------ Table 1 and limitations
def table_one(frame: pd.DataFrame, exposure: str, variables: Sequence[str], population: Optional[str] = None,
              groups: int = 3) -> pd.DataFrame:
    """Study areas described by exposure tertile (or ``groups`` quantile groups): areas, population, and the mean,
    median and median SE (from ``<v>_se``) of each variable. The last column block is all areas."""
    f = frame.dropna(subset=[exposure]).copy()
    if len(f) < groups:
        raise ValueError("too few areas for the exposure groups")
    f["_group"] = pd.qcut(f[exposure].rank(method="first"), groups, labels=[f"Q{i+1}" for i in range(groups)])
    cols = []
    for gname, g in list(f.groupby("_group", observed=True))+[("All", f)]:
        col = {"group": str(gname), "areas": int(len(g)),
               f"{exposure} range": f"{g[exposure].min():.4g} to {g[exposure].max():.4g}"}
        if population:
            col["population"] = float(g[population].sum())
        for v in variables:
            x = pd.to_numeric(g[v], errors="coerce")
            col[f"{v} mean"] = float(x.mean()); col[f"{v} median"] = float(x.median())
            if f"{v}_se" in g:
                col[f"{v} median SE"] = float(pd.to_numeric(g[f"{v}_se"], errors="coerce").median())
        cols.append(col)
    return pd.DataFrame(cols).set_index("group").T


def limitations(level: Optional[str] = None, individual: bool = False, measure_types: Optional[Mapping[str, str]] = None,
                outcomes: Sequence[str] = (), allocation: Sequence[Mapping[str, Any]] = (),
                deviations: Sequence[Mapping[str, Any]] = (), exploratory_methods: Sequence[str] = (),
                extra: Sequence[str] = ()) -> List[str]:
    """Generated limitations list (Appendix 1): design, measure types, item nonresponse, run deviations,
    exploratory methods, plus caller-supplied lines."""
    out = list(design_labels(level, individual)["notes"])
    types = {o: (measure_types or {}).get(o, "unspecified") for o in outcomes}
    if any(t == "prevalence" for t in types.values()):
        out.append(PREVALENCE_NOTE)
    unspecified = [o for o, t in types.items() if t == "unspecified"]
    if unspecified:
        out.append(f"Measure type not stated for {', '.join(unspecified)}; declare measure_type so rates are "
                   "compared in the same units and period.")
    out += allocation_note(allocation)
    kinds = sorted({d.get("kind") for d in deviations if d.get("kind")})
    if kinds:
        out.append("Deviations recorded during the run: "+", ".join(kinds)+" (see the deviations list).")
    if exploratory_methods:
        out.append("Exploratory (not validated) methods used: "+", ".join(exploratory_methods)+".")
    out += list(extra)
    return out
