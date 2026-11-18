# SPDX-License-Identifier: AGPL-3.0-or-later
"""Vital-records counts and rates from CDC WONDER exports (PLAN_ROUND_21 Part 2, C4; Step 3).

County mortality from CDC WONDER is available only through its web form (the WONDER API serves
national data only, per the NCHS data-sharing policy), so the engine reads the tab-delimited files
that the user exports from WONDER ("Export Results"). It does not automate the form.

* The export's footer (``"---"`` then ``Dataset:``, ``Query Parameters:`` and the parameter lines)
  is required: a file without it is refused as edited or partial. The parameters are recorded.
* WONDER suppresses counts of 1-9 (``Suppressed``): they are kept as censored, bounds [1, 9], never
  zero-filled; their rates are missing. Rates from fewer than 20 deaths carry ``(Unreliable)``.
* Crude rates get exact Poisson (Garwood) 95% intervals from the count (or WONDER's exported
  interval when present), SE = sqrt(deaths) / population (sqrt(1) for zero deaths). Age-adjusted rates need WONDER's exported
  standard error column: without age-specific counts the Fay-Feuer interval cannot be computed.
* A manifest pins the export by SHA-256; a different file is refused at registration (create_manifest) and at run time.
"""

import hashlib
import io
import os
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

SUPPRESSED_BOUNDS = (1, 9)
MEASURES = ("deaths", "crude_rate", "age_adjusted_rate")
_GEO_COLUMNS = {"county": ("County Code", 5), "state": ("State Code", 2)}


class WonderExportError(ValueError):
    """A WONDER export could not be read, or does not match its pinned hash."""


def _unquote(s: str) -> str:
    s = s.strip()
    return s[1:-1] if len(s) >= 2 and s[0] == s[-1] == '"' else s


def _split_footer(text: str) -> Tuple[List[str], List[str]]:
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if _unquote(line) == "---":
            return lines[:i], [_unquote(x) for x in lines[i:] if _unquote(x) not in ("", "---")]
    raise WonderExportError("no WONDER footer ('---' then Dataset: and Query Parameters:); the file is "
                            "edited or partial. Export again with 'Show Zero Values' and the footer kept")


def parse_footer(footer: List[str]) -> Dict[str, Any]:
    """Dataset name, query parameters ({name: value}) and other footer lines."""
    out: Dict[str, Any] = {"dataset": None, "parameters": {}, "other": []}
    in_params = False
    last_key = None
    for line in footer:
        if line.startswith("Dataset:"):
            out["dataset"] = line.split(":", 1)[1].strip()
            in_params = False
        elif line.startswith("Query Parameters:"):
            in_params = True
        elif in_params and ":" in line and not line.startswith(("Help:", "Query Date:", "Suggested Citation:")):
            k, v = line.split(":", 1)
            last_key = k.strip()
            out["parameters"][last_key] = v.strip()
        elif in_params and last_key and not line.startswith(("Help:", "Query Date:", "Suggested Citation:", "Notes:")):
            out["parameters"][last_key] += " " + line.strip()
        else:
            in_params = False
            last_key = None
            if line.startswith("Query Date:"):
                out["query_date"] = line.split(":", 1)[1].strip()
            out["other"].append(line)
    if not out["dataset"] or not out["parameters"]:
        raise WonderExportError("WONDER footer lacks 'Dataset:' or the query parameters; the file is edited or "
                                "partial")
    return out


def _num(series: pd.Series) -> "Tuple[np.ndarray, np.ndarray, np.ndarray]":
    """(values, suppressed, unreliable) from a WONDER column."""
    s = series.fillna("").astype(str).str.strip()
    unreliable = (s.str.contains(r"\(Unreliable\)", regex=True) | s.eq("Unreliable")).to_numpy()
    suppressed = s.str.fullmatch(r"Suppressed").to_numpy()
    clean = s.str.replace(r"\s*\(Unreliable\)", "", regex=True).str.replace(",", "", regex=False)
    val = pd.to_numeric(clean, errors="coerce").to_numpy(float)
    bad = (clean != "") & np.isnan(val) & ~clean.isin(["Suppressed", "Not Applicable", "Not Available", "Missing", "Unreliable"]).to_numpy()
    if bad.any():
        raise WonderExportError(f"unexpected values in {series.name!r}: {sorted(set(clean[bad]))[:5]}")
    return val, suppressed, unreliable


def read_wonder_export(path: str, level: str = "county") -> Dict[str, Any]:
    """Parse a WONDER export: {"rows": DataFrame, "footer": {...}, "sha256", "path"}.

    Rows: GEOID, deaths, deaths_suppressed, deaths_lower_bound, deaths_upper_bound, population,
    crude_rate (+ _ci_lower/_ci_upper/_se), age_adjusted_rate (+ _se, _ci_lower, _ci_upper when
    exported), unreliable. The Total row and blank lines are dropped.
    """
    if level not in _GEO_COLUMNS:
        raise WonderExportError(f"level must be one of {sorted(_GEO_COLUMNS)}")
    with open(path, "rb") as f:
        raw = f.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    body, footer_lines = _split_footer(text)
    footer = parse_footer(footer_lines)
    df = pd.read_csv(io.StringIO("\n".join(body)), sep="\t", dtype=str, keep_default_na=False)
    geo_col, width = _GEO_COLUMNS[level]
    if geo_col not in df.columns or "Deaths" not in df.columns:
        raise WonderExportError(f"export lacks {geo_col!r} or 'Deaths' columns (group by {level} and keep the "
                                f"default measures); columns: {list(df.columns)[:12]}")
    notes = df["Notes"].astype(str).str.strip() if "Notes" in df.columns else pd.Series("", index=df.index)
    df = df[(notes != "Total") & (df[geo_col].astype(str).str.strip() != "")].copy()
    geo = df[geo_col].astype(str).str.strip().str.zfill(width)
    if (~geo.str.fullmatch(rf"\d{{{width}}}")).any():
        raise WonderExportError(f"malformed {geo_col} values: {sorted(geo[~geo.str.fullmatch(r'[0-9]+')])[:5]}")
    if geo.duplicated().any():
        raise WonderExportError(f"duplicated {level} rows (group by {level} only): {sorted(geo[geo.duplicated()])[:5]}")
    out = pd.DataFrame({"GEOID": geo.to_numpy()})
    deaths, supp, _ = _num(df["Deaths"])
    supp = supp | ((deaths >= 1) & (deaths <= 9))
    out["deaths"] = np.where(supp, np.nan, deaths)
    out["deaths_suppressed"] = supp
    out["deaths_lower_bound"] = np.where(supp, SUPPRESSED_BOUNDS[0], deaths)
    out["deaths_upper_bound"] = np.where(supp, SUPPRESSED_BOUNDS[1], deaths)
    pop = _num(df["Population"])[0] if "Population" in df.columns else np.full(len(df), np.nan)
    out["population"] = pop
    unrel = np.zeros(len(df), bool)
    if "Crude Rate" in df.columns:
        rate, rs, ru = _num(df["Crude Rate"])
        unrel |= ru
        out["crude_rate"] = np.where(rs, np.nan, rate)
    else:
        with np.errstate(divide="ignore", invalid="ignore"):
            out["crude_rate"] = out["deaths"] / pop * 1e5
    lo_c = [c for c in df.columns if c.startswith("Crude Rate Lower 95%")]
    hi_c = [c for c in df.columns if c.startswith("Crude Rate Upper 95%")]
    if lo_c and hi_c:
        out["crude_rate_ci_lower"] = _num(df[lo_c[0]])[0]
        out["crude_rate_ci_upper"] = _num(df[hi_c[0]])[0]
    else:
        lo, hi = garwood_interval(out["deaths"].to_numpy(float))
        with np.errstate(divide="ignore", invalid="ignore"):
            out["crude_rate_ci_lower"] = lo / pop * 1e5
            out["crude_rate_ci_upper"] = hi / pop * 1e5
    with np.errstate(divide="ignore", invalid="ignore"):
        # Poisson SE sqrt(D)/P; a county with zero deaths gets sqrt(1)/P (one death's worth) so it keeps a
        # finite, conservative SE instead of 0 or 0/0 (dropping it would remove the lowest-mortality counties)
        out["crude_rate_se"] = np.sqrt(np.maximum(out["deaths"], 1.0)) / pop * 1e5
        out.loc[~np.isfinite(out["crude_rate"]), "crude_rate_se"] = np.nan
    if "Age Adjusted Rate" in df.columns:
        aa, aas, aau = _num(df["Age Adjusted Rate"])
        unrel |= aau
        out["age_adjusted_rate"] = np.where(aas, np.nan, aa)
        se_c = [c for c in df.columns if c.startswith("Age Adjusted Rate Standard Error")]
        out["age_adjusted_rate_se"] = _num(df[se_c[0]])[0] if se_c else np.nan
        for suf, pre in (("_ci_lower", "Age Adjusted Rate Lower 95%"), ("_ci_upper", "Age Adjusted Rate Upper 95%")):
            cols = [c for c in df.columns if c.startswith(pre)]
            out["age_adjusted_rate" + suf] = _num(df[cols[0]])[0] if cols else np.nan
    out["unreliable"] = unrel | ((out["deaths"] < 20) & ~out["deaths_suppressed"]).to_numpy()
    notes = []
    if "Population" not in df:
        notes.append("Deaths-only export: population/rate columns absent; study expected counts require separate ACS populations.")
    elif not np.isfinite(pop).all():
        notes.append(f"Population unavailable for {int((~np.isfinite(pop)).sum())} row(s); retained as missing, not zero.")
    return {"rows": out, "footer": footer, "sha256": hashlib.sha256(raw).hexdigest(), "path": os.path.abspath(path),
            "size_bytes": len(raw), "notes": notes, "columns": list(df.columns)}


def garwood_interval(deaths: np.ndarray, level: float = 0.95) -> "Tuple[np.ndarray, np.ndarray]":
    """Exact Poisson interval for counts (Garwood 1936): chi2 quantiles / 2."""
    from scipy.stats import chi2
    d = np.asarray(deaths, float)
    a = (1 - level) / 2
    with np.errstate(invalid="ignore"):
        lo = np.where(d > 0, chi2.ppf(a, 2 * d) / 2, 0.0)
        hi = chi2.ppf(1 - a, 2 * d + 2) / 2
    lo = np.where(np.isnan(d), np.nan, lo)
    hi = np.where(np.isnan(d), np.nan, hi)
    return lo, hi


def load_wonder_measure(path: str, sha256: str, measure: str, name: str,
                        level: str = "county") -> "Tuple[pd.DataFrame, Dict[str, Any]]":
    """One measure of a pinned WONDER export as an external frame: GEOID, <name>, <name>_se,
    <name>_ci_lower, <name>_ci_upper, <name>_numerator (deaths), <name>_denominator (population),
    <name>_flag (0 ok, 1 unreliable, 2 suppressed), plus <name>_lower_bound/_upper_bound for deaths."""
    measure = str(measure).lower()
    if measure not in MEASURES:
        raise WonderExportError(f"measure must be one of {MEASURES}")
    if not os.path.exists(path):
        raise WonderExportError(f"WONDER export {path} not found")
    exp = read_wonder_export(path, level)  # hashes the bytes it parses (one read)
    if exp["sha256"] != str(sha256).lower():
        raise WonderExportError(f"{path} has SHA-256 {exp['sha256']}, not the pinned {sha256}: a different or "
                                "edited file")
    r = exp["rows"]
    flag = np.where(r["deaths_suppressed"], 2, np.where(r["unreliable"], 1, 0))
    out = pd.DataFrame({"GEOID": r["GEOID"]})
    if measure == "deaths":
        out[name] = r["deaths"]
        out[f"{name}_se"] = np.sqrt(np.maximum(r["deaths"], 1.0))  # NaN stays NaN (suppressed)
        lo, hi = garwood_interval(r["deaths"].to_numpy(float))
        out[f"{name}_ci_lower"], out[f"{name}_ci_upper"] = lo, hi
        out[f"{name}_lower_bound"], out[f"{name}_upper_bound"] = r["deaths_lower_bound"], r["deaths_upper_bound"]
    else:
        if measure not in r.columns:
            raise WonderExportError(f"the export has no {measure.replace('_', ' ')} column")
        if measure == "age_adjusted_rate" and not np.isfinite(r["age_adjusted_rate_se"].to_numpy(float)).any():
            raise WonderExportError("age-adjusted rates need WONDER's 'Age Adjusted Rate Standard Error' column "
                                    "(tick it under Other Options and export again): without age-specific counts "
                                    "the Fay-Feuer interval cannot be computed")
        for suf in ("", "_se", "_ci_lower", "_ci_upper"):
            out[name + suf] = r[measure + suf]
    out[f"{name}_numerator"] = r["deaths"]
    out[f"{name}_denominator"] = r["population"]
    out[f"{name}_flag"] = flag
    rec = {"dataset": exp["footer"]["dataset"], "parameters": exp["footer"]["parameters"],
           "query_date": exp["footer"].get("query_date"), "measure": measure,
           "suppressed_units": int(r["deaths_suppressed"].sum()), "unreliable_units": int((flag == 1).sum()),
           "file": {"path": exp["path"], "sha256": exp["sha256"], "size_bytes": exp["size_bytes"],
                    "source_url": "user-supplied CDC WONDER export"}}
    if exp.get("notes"):
        rec["notes"] = exp["notes"]
    return out, rec


def read_wonder_reference(path, *, expected_sha256=None, state=None, validate_only=False):
    """Read national age/sex manual TSV/TXT, with one common schema.

    Rates are deaths/summed annual populations (per person-year). Under-one and
    ages 1–4 combine before division. Not Stated ages are excluded and counted.
    State references require an explicit state selector; a suppressed state cell
    can pass registration validation but is refused at runtime. National
    suppressed reference cells are always refused. No network access occurs.
    """
    from pathlib import Path
    import re
    from .wonder_reference import BANDS,band_order
    file=Path(path);raw=file.read_bytes();sha=hashlib.sha256(raw).hexdigest()
    if expected_sha256 is not None and sha!=str(expected_sha256).lower():raise WonderExportError('reference export SHA-256 differs from its registered bytes')
    notes=[]
    if file.suffix.lower() in ('.tsv','.txt'):
        text=raw.decode('utf-8-sig');body,lines=_split_footer(text);footer=parse_footer(lines)
        from .wonder_inventory import years_from_parameters
        years=years_from_parameters(footer['parameters'])
        source=pd.read_csv(io.StringIO('\n'.join(body)),sep='\t',dtype=str,keep_default_na=False)
        is_state='State Code' in source
        group=footer['parameters'].get('Group By','').lower().replace('gender','sex')
        group_parts={x.strip() for x in group.split(';') if x.strip()}
        wanted={'ten-year age groups','sex'}|({'state'} if is_state else set())
        if group_parts!=wanted or 'County Code' in source:
            raise WonderExportError('reference grouping must be national age/sex or preregistered state/age/sex')
        if not is_state:
            for key,value in footer['parameters'].items():
                if any(word in key.lower() for word in ('location','county','state','region','division','urbanization')) and '*All*' not in value and value.strip() not in ('All','The United States'):
                    raise WonderExportError('national reference file has a location filter')
        if is_state:
            if not isinstance(state,str) or not re.fullmatch(r'[0-9]{2}',state):raise WonderExportError('state reference rates require an explicitly preregistered two-digit state')
            source=source[source['State Code'].str.zfill(2)==state]
            if source.empty:raise WonderExportError('selected reference state is absent')
        age=next((c for c in ('Ten-Year Age Groups','Ten-Year Age Group') if c in source),None)
        sex=next((c for c in ('Sex','Gender') if c in source),None)
        if not age or not sex or not {'Deaths','Population'}<=set(source):raise WonderExportError('age/sex reference requires Ten-Year Age Groups, Sex/Gender, Deaths and Population columns')
        if 'Notes' in source:source=source[source.Notes.str.strip()!='Total']
        rows=source.rename(columns={age:'age',sex:'sex','Deaths':'deaths','Population':'population'})[['age','sex','deaths','population']].copy()
    else:raise WonderExportError('reference format must be TSV or TXT')
    if state is not None and not is_state:raise WonderExportError('state selector requires a state-grouped reference file')
    if not years or years!=list(range(min(years),max(years)+1)):raise WonderExportError('reference years must be explicit and contiguous')
    unstated=rows.age.str.strip().str.lower().isin(('not stated','unknown','ns'))
    dropped=int(unstated.sum())
    if dropped:
        values=[]
        for value in rows.loc[unstated,'deaths']:
            number=pd.to_numeric(str(value).replace(',',''),errors='coerce')
            values.append('suppressed/unavailable' if not np.isfinite(number) or 1<=number<=9 else int(number))
        notes.append(f'Dropped {dropped} Not Stated age row(s); deaths by excluded row: {values}.')
    rows=rows[~unstated].copy()
    rows['sex']=rows.sex.str.strip().map({'Male':'M','Female':'F','M':'M','F':'F'})
    if rows.sex.isna().any():raise WonderExportError('unexpected reference sex category')
    deaths,supp,_=_num(rows.deaths);pop,_,_=_num(rows.population)
    rows['deaths']=deaths;rows['population']=pop;rows['suppressed']=supp|((deaths>=1)&(deaths<=9))
    # National numeric counts are public; labelled suppressed cells are refused.
    if rows.suppressed.any() and (not is_state or not validate_only):raise WonderExportError('suppressed reference cell refused; reference rates unavailable')
    if not np.isfinite(pop).all() or (pop<=0).any():raise WonderExportError('reference populations/person-years must be present and positive')
    if ((~rows.suppressed)&(~np.isfinite(deaths)|(deaths<0)|(deaths!=np.floor(deaths)))).any():raise WonderExportError('reference deaths must be nonnegative integer counts')
    def age_code(label):
        label=' '.join(str(label).strip().replace('–','-').split())
        if label in ('< 1 year','Under 1 year','<1 year','1'):return '<1'
        label=re.sub(r'\s+years?$','',label)
        if label=='1-4':return '1-4'
        if label in BANDS[1:]:return label
        raise WonderExportError(f'unexpected ten-year reference age group {label!r}')
    rows['source_age']=rows.age.map(age_code)
    if rows.duplicated(['sex','source_age']).any():raise WonderExportError('duplicate reference age/sex rows')
    expected={(s,a) for s in ('M','F') for a in ('<1','1-4',*BANDS[1:])}
    if set(zip(rows.sex,rows.source_age))!=expected:raise WonderExportError('reference lacks complete ten-year age/sex coverage')
    rows['band']=rows.source_age.replace({'<1':'0-4','1-4':'0-4'})
    grouped=rows.groupby(['sex','band'],sort=False).agg(deaths=('deaths',lambda x:x.sum(min_count=len(x))),population=('population','sum'),suppressed=('suppressed','any'))
    grouped=grouped.loc[band_order()].reset_index();grouped['rate']=grouped.deaths/grouped.population
    return dict(rows=grouped,years=years,footer=footer,notes=notes,sha256=sha,path=str(file.resolve()),state=state)
