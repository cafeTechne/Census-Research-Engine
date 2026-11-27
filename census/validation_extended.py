# SPDX-License-Identifier: AGPL-3.0-or-later
"""Extended validation checks (F6-F8, F10-F11) extracted from census/validation.py (Round 151)."""
from census.validation import (  # noqa: F401
    APPORTIONMENT_TABLE2_URL,
    Any,
    BASE_URL,
    Battery,
    CPI_GUIDANCE,
    CP_USER_NOTES,
    CensusSource,
    DATASETS,
    DEFAULT_BATTERY,
    Dict,
    List,
    MAX_FAILURE_SAMPLES,
    Mapping,
    Optional,
    SUMMARY_FILE_DOC,
    SUMMARY_FILE_URL,
    Sequence,
    Tuple,
    ValidationResult,
    _aggregate,
    _dec,
    _distribution,
    _inflation,
    _max,
    _md,
    _norm_label,
    _numeric,
    _raw_float,
    acs5_overlap_years,
    io,
    math,
    np,
    pd,
    re,
    z_test,
)



# ---------------------------------------------------------------------------
# F6 / F7: Comparison Profile
# ---------------------------------------------------------------------------


def _cp_items(source: CensusSource, b: Battery, late: int, early: int) -> Dict[str, Any]:
    """Pair every CP03 item with its DP03 item in the early and late release."""
    geo = {"for": f"state:{b.state_list()}"}
    cp = source.api_group(late, "cprofile", "CP03", geo).set_index("GEOID")
    dp_late = source.api_group(late, "profile", "DP03", geo).set_index("GEOID")
    dp_early = source.api_group(early, "profile", "DP03", geo).set_index("GEOID")
    cp_meta, _ = _md.table_variables("CP03", "cprofile", late)
    meta_late, _ = _md.table_variables("DP03", "profile", late)
    meta_early, _ = _md.table_variables("DP03", "profile", early)

    def index(meta: Mapping[str, Any]) -> Dict[str, List[str]]:
        out: Dict[str, List[str]] = {}
        for code, m in meta.items():
            if re.match(r"^DP03_\d{4}(E|PE)$", code):
                out.setdefault(_norm_label(m["label"]), []).append(code)
        return out

    idx_late, idx_early = index(meta_late), index(meta_early)
    items: List[Dict[str, Any]] = []
    unmatched: List[str] = []
    for code in sorted(cp_meta):
        m = re.match(rf"^CP03_{early}_(\d{{3}})E$", code)
        if not m:
            continue
        num = m.group(1)
        late_code = f"CP03_{late}_{num}E"
        ss_code = f"CP03_{late}to{early}_{num}SS"
        label = _norm_label(cp_meta[code]["label"])
        if late_code not in cp_meta or late_code not in cp.columns or code not in cp.columns:
            unmatched.append(code)
            continue

        def base(idx: Dict[str, List[str]]) -> Optional[str]:
            cands = sorted({re.sub(r"P?E$", "", c) for c in idx.get(label, [])})
            if len(cands) == 1:
                return cands[0]
            same = f"DP03_0{num}"
            return same if same in cands else None

        b_late, b_early = base(idx_late), base(idx_early)
        if b_late is None or b_early is None:
            unmatched.append(code)
            continue
        # Which DP value does the CP show? Decide from the later period, where CP == DP.
        cp_late = _numeric(cp[late_code])
        suffix = None
        for e_suf in ("PE", "E"):
            col = b_late + e_suf
            if col in dp_late.columns:
                dv = _numeric(dp_late.loc[cp.index, col])
                both = np.isfinite(cp_late) & np.isfinite(dv)
                if both.any() and np.allclose(cp_late[both], dv[both], rtol=0, atol=1e-9) and (
                    np.isfinite(cp_late) == np.isfinite(dv)
                ).all():
                    suffix = e_suf
                    break
        if suffix is None:
            unmatched.append(code)
            continue
        items.append({
            "cp_early": code, "cp_late": late_code, "ss": ss_code, "label": cp_meta[code]["label"],
            "dp_early": b_early, "dp_late": b_late, "suffix": suffix,
            "dollar": "INFLATION-ADJUSTED DOLLARS" in label and "(DOLLARS)" in label.split("!!")[-1],
        })
    return {"items": items, "unmatched": unmatched, "cp": cp, "dp_late": dp_late, "dp_early": dp_early}


def _cp_data(source: CensusSource, b: Battery, ctx: Dict[str, Any], late: int, early: int) -> Dict[str, Any]:
    key = f"cp_{late}_{early}"
    if key not in ctx:
        ctx[key] = _cp_items(source, b, late, early)
    return ctx[key]


def check_f6_cp_inflation(
    source: CensusSource, battery: Battery = DEFAULT_BATTERY, ctx: Optional[Dict[str, Any]] = None
) -> ValidationResult:
    ctx = ctx if ctx is not None else {}
    b = battery
    res = ValidationResult(
        "F6",
        "Comparison Profile (CP03) earlier-period dollar values, which Census publishes in current-period "
        "dollars, vs the earlier release's DP03 value adjusted with inflation.adjust_inflation "
        f"(R-CPI-U-RS, the default), states {b.state_list()}, CP releases "
        + ", ".join(f"{late} (vs {early})" for late, early in b.cp_releases) + ".",
        tolerance="|ours - CP| <= max($1, 0.5% of CP), asserted for every item Census converts with a single "
        "factor (means, aggregates, per-capita); medians reported (see notes)",
    )
    res.census_source += [CPI_GUIDANCE, f"{BASE_URL}/<year>/acs/acs5/cprofile", f"{BASE_URL}/<year>/acs/acs5/profile"]
    failures: List[Dict[str, Any]] = []
    abs_e: List[float] = []
    rel_e: List[float] = []
    n = n_failed = 0
    factors: Dict[str, Any] = {}
    median_misses: List[Dict[str, Any]] = []
    for late, early in b.cp_releases:
        data = _cp_data(source, b, ctx, late, early)
        ours_factor = _inflation.inflation_factor(early, late)
        implied_median: List[float] = []
        implied_all: List[float] = []
        implied_agg: List[float] = []
        identity_bad = 0
        n_items = 0
        for it in data["items"]:
            if not it["dollar"] or it["suffix"] != "E":
                continue
            n_items += 1
            for g in data["cp"].index:
                cp_v = _numeric([data["cp"].at[g, it["cp_early"]]])[0]
                dp_col = it["dp_early"] + "E"
                dp_v = _numeric([data["dp_early"].at[g, dp_col]])[0] if dp_col in data["dp_early"].columns else math.nan
                if not (np.isfinite(cp_v) and np.isfinite(dp_v)) or dp_v == 0:
                    continue
                ours = _inflation.adjust_inflation(dp_v, early, late)
                err = ours - cp_v
                n += 1
                abs_e.append(abs(err))
                rel_e.append(abs(err) / abs(cp_v))
                implied = cp_v / dp_v
                implied_all.append(implied)
                if not re.search(r"MEDIAN", it["label"], re.I):
                    implied_agg.append(implied)
                else:
                    implied_median.append(implied)
                is_median = bool(re.search(r"MEDIAN", it["label"], re.I))
                if abs(err) > max(1.0, 0.005 * abs(cp_v)) + 1e-9:
                    row = {"cp_release": late, "GEOID": g, "item": it["cp_early"], "label": it["label"],
                           "dp_value": dp_v, "ours": round(ours, 2), "published": cp_v,
                           "implied_factor": round(implied, 6)}
                    if is_median:
                        median_misses.append(row)
                    else:
                        n_failed += 1
                        failures.append(row)
                # sanity: CP current-period value == DP current release value
                lv = _numeric([data["cp"].at[g, it["cp_late"]]])[0]
                dl = _numeric([data["dp_late"].at[g, it["dp_late"] + "E"]])[0]
                if np.isfinite(lv) and np.isfinite(dl) and lv != dl:
                    identity_bad += 1
        factors[f"{late} vs {early}"] = {
            "dollar_items": n_items,
            "ours_r_cpi_u_rs_factor": ours_factor,
            "ours_index_values": {str(early): _inflation.get_cpi(early), str(late): _inflation.get_cpi(late)},
            "census_implied_factor_all_items": _distribution(implied_all),
            "census_implied_factor_means_and_per_capita": _distribution(implied_agg),
            "census_implied_factor_medians": _distribution(implied_median),
            "implied_minus_ours_percent": (
                (float(np.median(implied_agg)) / ours_factor - 1) * 100 if implied_agg else None
            ),
            "current_period_cp_ne_dp": identity_bad,
            "unmatched_cp_items": len(data["unmatched"]),
        }
    res.n_compared = n
    res.n_failed = n_failed
    res.max_abs_error = _max(abs_e)
    res.max_rel_error = _max(rel_e)
    res.failures = failures[:MAX_FAILURE_SAMPLES] + [dict(r, asserted=False) for r in median_misses][:10]
    res.details = {"factors": factors, "median_items_outside_tolerance_not_asserted": len(median_misses)}
    res.notes += [
        "Asserted: means, aggregates and per-capita values, which Census converts with a single factor "
        "(implied factor constant to 5 digits across items and states). Median items are compared and "
        "reported but not asserted: in the 2019 Comparison Profile their implied factors scatter "
        "(1.0747-1.0838 against 1.08097 for means), showing that Census re-derived those medians from "
        "inflation-adjusted distributions rather than scaling the published median, which no deflator can "
        "reproduce from published data; in the 2023 CP medians scale with the same constant factor and all "
        "pass. Median misses are listed with asserted=false.",
        "Round 6 acceptance criterion 6: the Census-implied factor (median over mean/aggregate/per-capita "
        "items) is compared with our R-CPI-U-RS factor in details.factors.*.implied_minus_ours_percent.",
    ]
    return res.finish(n_failed == 0 and n > 0)


def check_f7_cp_significance(
    source: CensusSource, battery: Battery = DEFAULT_BATTERY, ctx: Optional[Dict[str, Any]] = None
) -> ValidationResult:
    ctx = ctx if ctx is not None else {}
    b = battery
    res = ValidationResult(
        "F7",
        "Comparison Profile significance flags (CP03 '..._SS' variables: '*' = the two periods differ at "
        "the 90% level, empty = not significant) vs stats.z_test on the CP estimates with the Data Profile "
        f"MOEs of each release, states {b.state_list()}, CP releases "
        + ", ".join(f"{late} (vs {early})" for late, early in b.cp_releases) + ".",
        tolerance="agreement on >= 98% of tests that are decidable from the published (rounded) values; "
        "every disagreement listed with its z statistic and its z range under rounding",
    )
    res.census_source += [CP_USER_NOTES, f"{BASE_URL}/<year>/acs/acs5/cprofile", f"{BASE_URL}/<year>/acs/acs5/profile"]
    rows: List[Dict[str, Any]] = []
    per: Dict[str, Any] = {}
    for late, early in b.cp_releases:
        data = _cp_data(source, b, ctx, late, early)
        factor = _inflation.inflation_factor(early, late)
        overlap = acs5_overlap_years(late, early)
        skipped = Counter()
        agree = total = 0
        for it in data["items"]:
            moe_suf = "PM" if it["suffix"] == "PE" else "M"
            for g in data["cp"].index:
                if it["ss"] not in data["cp"].columns:
                    skipped["no SS variable"] += 1
                    continue
                e_late = _numeric([data["cp"].at[g, it["cp_late"]]])[0]
                e_early = _numeric([data["cp"].at[g, it["cp_early"]]])[0]
                m_late_col = it["dp_late"] + moe_suf
                m_early_col = it["dp_early"] + moe_suf
                if m_late_col not in data["dp_late"].columns or m_early_col not in data["dp_early"].columns:
                    skipped["no DP MOE"] += 1
                    continue
                m_late = _numeric([data["dp_late"].at[g, m_late_col]])[0]
                m_early = _numeric([data["dp_early"].at[g, m_early_col]])[0]
                if not all(np.isfinite(v) for v in (e_late, e_early, m_late, m_early)):
                    skipped["estimate or MOE not published"] += 1
                    continue
                if not it["dollar"]:
                    dp_e = _numeric([data["dp_early"].at[g, it["dp_early"] + it["suffix"]]])[0]
                    if dp_e != e_early:
                        if "INFLATION-ADJUSTED DOLLARS" in _norm_label(it["label"]):
                            skipped["income-bracket share re-tabulated by Census after inflation adjustment"] += 1
                        else:
                            skipped["earlier CP value differs from earlier DP value"] += 1
                        continue
                else:
                    m_early = m_early * factor  # constant scaling: MOE(kX) = k MOE(X)
                ss = data["cp"].at[g, it["ss"]]
                census_sig = str(ss).strip() == "*"
                t = z_test(e_late, m_late, e_early, m_early, confidence_level=0.90, overlap_years=overlap)
                lo_z, hi_z = _z_rounding_range(e_late, m_late, e_early, m_early, it["suffix"] == "PE",
                                               factor if it["dollar"] else 1.0)
                decidable = hi_z < 1.645 or lo_z >= 1.645
                total += 1
                same = bool(t["significant"]) == census_sig
                agree += int(same)
                rows.append({
                    "cp_release": late, "GEOID": g, "item": it["cp_late"][:-1], "label": it["label"],
                    "estimate_late": e_late, "moe_late": m_late, "estimate_early": e_early,
                    "moe_early": round(m_early, 3), "z": round(float(t["z_statistic"]), 4),
                    "ours_significant": bool(t["significant"]), "census_significant": census_sig,
                    "agree": same, "z_range_under_rounding": [round(lo_z, 3), round(hi_z, 3)],
                    "decidable": decidable,
                })
        per[f"{late} vs {early}"] = {
            "items": len(data["items"]), "tests": total, "agree": agree,
            "agreement_rate": agree / total if total else None, "overlap_years": overlap,
            "skipped": dict(skipped), "unmatched_cp_items": len(data["unmatched"]),
        }
    for key, rel in per.items():
        sub = [r for r in rows if f"{r['cp_release']} vs" in key]
        dec = [r for r in sub if r["decidable"]]
        rel["decidable_tests"] = len(dec)
        rel["decidable_agree"] = sum(r["agree"] for r in dec)
    total = len(rows)
    decidable = [r for r in rows if r["decidable"]]
    undecidable = [r for r in rows if not r["decidable"]]
    disagree = [r for r in decidable if not r["agree"]]
    rate = (len(decidable) - len(disagree)) / len(decidable) if decidable else math.nan
    raw_rate = sum(r["agree"] for r in rows) / total if total else math.nan
    res.n_compared = len(decidable)
    res.n_failed = len(disagree)
    zs = [abs(r["z"] - 1.645) for r in disagree]
    res.max_abs_error = _max(zs)
    res.failures = sorted(disagree, key=lambda r: abs(r["z"] - 1.645)) + sorted(
        [r for r in undecidable if not r["agree"]], key=lambda r: abs(r["z"] - 1.645))[: max(0, MAX_FAILURE_SAMPLES - len(disagree))]
    res.details = {
        "per_release": per,
        "tests_total": total,
        "decidable_tests": len(decidable),
        "undecidable_tests": len(undecidable),
        "agreement_rate_decidable": rate,
        "agreement_rate_all_tests": raw_rate,
        "agreement_rate_undecidable": (sum(r["agree"] for r in undecidable) / len(undecidable)) if undecidable else None,
        "disagreements_abs_z_minus_1645": _distribution(zs),
        "census_flag_encoding": "'*' = statistically significant at 90%; null/empty = not significant "
        "(variable label 'Statistical Significance!!...', predicateType string)",
    }
    res.notes += [
        "The API's cprofile endpoint publishes estimates (E), annotations (EA) and significance (SS) only, "
        "no MOEs; MOEs come from each release's Data Profile (PM for percent items, M for others). For "
        "dollar items the earlier MOE is scaled by the same R-CPI-U-RS factor as the estimate.",
        "Census tests unrounded estimates and standard errors; we test the published (rounded) values, "
        "so disagreements are expected only for z close to the 1.645 critical value.",
        "A test is 'decidable' when every combination of unrounded values consistent with the published "
        "rounding (estimates and MOEs +/- half a unit; a published percent MOE of 0.1 may be any value in "
        "(0, 0.15)) gives z on the same side of 1.645. Only decidable tests can disagree with Census because "
        "of a calculation error; agreement is asserted on them and reported for all tests. Failures list "
        "decidable disagreements first, then undecidable ones.",
        "max_abs_error for this check is the largest |z - 1.645| among decidable disagreements.",
        "Excluded: earlier-period income-bracket shares (Census re-tabulates households into current-dollar "
        "brackets, so the earlier Data Profile shares and MOEs do not apply) and items without a published "
        "estimate or MOE (e.g. 2010-2014 occupation, '-888888888', not comparable after the occupation "
        "code change).",
        "n_compared counts decidable tests.",
    ]
    return res.finish(len(decidable) > 0 and rate >= 0.98)


def _z_rounding_range(
    e1: float, m1: float, e2: float, m2: float, percent: bool, factor2: float = 1.0
) -> Tuple[float, float]:
    """Range of |z| over unrounded values consistent with the published rounding.

    Percent items are published to 0.1 (half unit 0.05); other items to 1
    (half unit 0.5). ``factor2`` scales the second MOE's rounding (an earlier
    MOE converted to current dollars). A percent MOE published as 0.1 is
    treated as possibly anywhere in (0, 0.15).
    """
    h = 0.05 if percent else 0.5

    def bounds(m: float, k: float) -> Tuple[float, float]:
        lo = 0.0 if (percent and m <= 0.1 + 1e-12) else max(0.0, m - h * k)
        return lo, m + h * k

    l1, u1 = bounds(m1, 1.0)
    l2, u2 = bounds(m2, factor2)
    d = abs(e1 - e2)
    dmin, dmax = max(0.0, d - 2 * h), d + 2 * h
    se_max = math.sqrt(u1**2 + u2**2) / 1.645
    se_min = math.sqrt(l1**2 + l2**2) / 1.645
    z_lo = dmin / se_max if se_max > 0 else math.inf
    z_hi = dmax / se_min if se_min > 0 else math.inf
    return z_lo, z_hi


class Counter(dict):
    def __missing__(self, key: str) -> int:
        return 0


# ---------------------------------------------------------------------------
# F8: sums of counties
# ---------------------------------------------------------------------------


def check_f8_county_sums(
    source: CensusSource, battery: Battery = DEFAULT_BATTERY, ctx: Optional[Dict[str, Any]] = None
) -> ValidationResult:
    b = battery
    res = ValidationResult(
        "F8",
        "Sum of all counties (aggregate.aggregate_geographies, approximate MOE) vs the published state "
        f"estimate for additive counts ({', '.join(b.f8_variables)}), states {b.state_list()}, releases "
        f"{', '.join(map(str, b.releases))}.",
        tolerance="estimate exact; MOE ratio (approximate sum MOE / published state MOE) reported, not asserted",
    )
    res.census_source.append(f"{BASE_URL}/<year>/acs/acs5")
    failures: List[Dict[str, Any]] = []
    n = n_failed = 0
    abs_e: List[float] = []
    ratios: Dict[str, List[float]] = {}
    for year in b.releases:
        variables = [v + s for v in b.f8_variables for s in ("E", "M")]
        counties = source.api_frame(year, "acs5", variables, {"for": "county:*", "in": f"state:{b.state_list()}"})
        states = source.api_frame(year, "acs5", variables, {"for": f"state:{b.state_list()}"}).set_index("GEOID")
        for v in variables:
            counties[v] = pd.to_numeric(counties[v], errors="coerce")
        mapping = {g: g[:2] for g in counties["GEOID"]}
        meta, _ = _md.vintage_variables("acs5", year)
        agg = _aggregate.aggregate_geographies(
            counties, mapping, estimate_cols=list(b.f8_variables), method="approximate", metadata=meta
        ).set_index("group_id")
        for st in b.states:
            members = int(agg.at[st, "member_count"])
            expected_members = int((counties["GEOID"].str[:2] == st).sum())
            if members != expected_members:
                n_failed += 1
                failures.append({"year": year, "state": st, "problem": "member_count", "ours": members,
                                 "expected": expected_members})
            for v in b.f8_variables:
                ours = float(agg.at[st, v + "E"])
                pub = _raw_float(states.at[st, v + "E"])
                n += 1
                abs_e.append(abs(ours - pub))
                if ours != pub:
                    n_failed += 1
                    failures.append({"year": year, "state": st, "variable": v, "sum_of_counties": ours,
                                     "state_estimate": pub})
                pm = _raw_float(states.at[st, v + "M"])
                om = float(agg.at[st, v + "M"])
                if pm > 0 and np.isfinite(om):
                    ratios.setdefault(v, []).append(om / pm)
    res.n_compared = n
    res.n_failed = n_failed
    res.max_abs_error = _max(abs_e)
    res.failures = failures[:MAX_FAILURE_SAMPLES]
    res.details = {"moe_ratio_sum_approx_over_state_published": {k: _distribution(v) for k, v in ratios.items()}}
    res.notes.append(
        "B01003_001 is controlled (published MOE '*****') at county and state level, so no MOE ratio is "
        "formed for it. The approximate sum MOE ignores covariance between counties (Handbook 2020 ch. 8), "
        "so the ratio scatters around 1; it is reported, not asserted, as the plan specifies."
    )
    return res.finish(n_failed == 0 and n > 0)


# ---------------------------------------------------------------------------
# F10: Summary File
# ---------------------------------------------------------------------------


def check_f10_summary_file(
    source: CensusSource, battery: Battery = DEFAULT_BATTERY, ctx: Optional[Dict[str, Any]] = None
) -> ValidationResult:
    b = battery
    year = b.sf_release
    res = ValidationResult(
        "F10",
        f"ACS {year - 4}-{year} table-based Summary File cells (bulk delivery on www2.census.gov) vs API "
        f"cells for tables {', '.join(b.sf_tables)}, the nation and states {b.state_list()}.",
        tolerance="exact (numeric equality of every estimate and MOE cell)",
    )
    res.census_source.append(SUMMARY_FILE_DOC)
    res.notes.append(
        "Only the first bytes of each national per-table file are requested (HTTP Range); its rows are "
        "sorted by GEO_ID, so the nation and state rows precede the county, tract and block-group rows. "
        "The table-based Summary File exists from the 2021 releases on (summary_file/2021/table-based-SF/); "
        "summary_file/2019/ holds only data/ (the sequence-based files, one archive per state holding every "
        "table), documentation/ and prototype/ (checked 2026-11-02), so "
        f"{', '.join(str(y) for y in b.releases if y < 2021) or 'no release'} is not compared here."
    )
    geo_ids = ["0100000US"] + [f"0400000US{s}" for s in b.states]
    failures: List[Dict[str, Any]] = []
    n = n_failed = 0
    per: Dict[str, Any] = {}
    for table in b.sf_tables:
        sf = source.summary_file_rows(year, table, geo_ids)
        url = SUMMARY_FILE_URL.format(year=year, table=table.lower())
        res.census_source.append(url)
        api_states = source.api_group(year, "acs5", table, {"for": f"state:{b.state_list()}"}).set_index("GEOID")
        api_us = source.api_group(year, "acs5", table, {"for": "us:1"}).set_index("GEOID")
        t_n = t_bad = 0
        missing_rows = [g for g in geo_ids if g not in sf["rows"]]
        for g in missing_rows:
            failures.append({"table": table, "GEO_ID": g, "problem": "row not found in the fetched byte range"})
        t_bad += len(missing_rows)
        for g, row in sf["rows"].items():
            api = api_us if g == "0100000US" else api_states
            key = "US" if g == "0100000US" else g[-2:]
            for col, val in row.items():
                m = re.match(rf"^{table}_([EM])(\d{{3}})$", col)
                if not m:
                    continue
                api_col = f"{table}_{m.group(2)}{m.group(1)}"
                t_n += 1
                a = _raw_float(api.at[key, api_col]) if api_col in api.columns else math.nan
                s = _raw_float(val)
                if not ((math.isnan(a) and math.isnan(s)) or a == s):
                    t_bad += 1
                    if len(failures) < MAX_FAILURE_SAMPLES:
                        failures.append({"table": table, "GEO_ID": g, "cell": api_col, "summary_file": val,
                                         "api": api.at[key, api_col] if api_col in api.columns else None})
        n += t_n
        n_failed += t_bad
        per[table] = {"cells": t_n, "mismatches": t_bad, "rows": len(sf["rows"]), "byte_range": sf.get("byte_range")}
    res.n_compared = n
    res.n_failed = n_failed
    res.max_abs_error = 0.0 if n_failed == 0 else math.nan
    res.failures = failures
    res.details = {"tables": per}
    return res.finish(n_failed == 0 and n > 0)


# ---------------------------------------------------------------------------
# F11: 2020 Census invariants and hierarchy
# ---------------------------------------------------------------------------

# Items both 2020 Census files publish: (P.L. 94-171 variable, DHC variable, item).
F11_SHARED_ITEMS: Tuple[Tuple[str, str, str], ...] = (
    ("P1_001N", "P1_001N", "total population"),
    ("H1_001N", "H1_001N", "housing units (block invariant)"),
    ("H1_001N", "H3_001N", "housing units, DHC occupancy-status table"),
    ("H1_002N", "H3_002N", "occupied housing units"),
    ("H1_003N", "H3_003N", "vacant housing units"),
)


def _apportionment_state_totals(raw: bytes) -> Dict[str, int]:
    """State FIPS -> resident population from 2020 Apportionment Results Table 2 (xlsx)."""
    from census.geo import STATE_MAPPING

    by_name = {v.lower(): k for k, v in STATE_MAPPING.items()}
    table = pd.read_excel(io.BytesIO(raw), header=None, dtype=object)
    out: Dict[str, int] = {}
    for _, row in table.iterrows():
        name, value = str(row.iloc[0]).strip().lower(), row.iloc[1]
        if name in by_name and isinstance(value, (int, float, np.integer)) and not pd.isna(value):
            out[by_name[name]] = int(value)
    return out


def _f11_frame(source: CensusSource, dataset: str, variables: Sequence[str], geo: Mapping[str, str]) -> pd.DataFrame:
    frame = source.api_frame(_dec.DECENNIAL_YEAR, dataset, variables, geo)
    for v in variables:
        frame[v] = pd.to_numeric(frame[v], errors="coerce")
    return frame.set_index("GEOID")


def _f11_blocks(source: CensusSource, dataset: str, state: str, county: str) -> pd.DataFrame:
    """Block housing units (``get=H1_001N`` only, no NAME: the smallest response)."""
    endpoint = f"{BASE_URL}/{_dec.DECENNIAL_YEAR}/{DATASETS[dataset]}"
    payload = source.get_json(endpoint, {"get": "H1_001N", "for": "block:*", "in": f"state:{state} county:{county}"})
    df = pd.DataFrame(payload[1:], columns=payload[0])
    df["H1_001N"] = pd.to_numeric(df["H1_001N"], errors="coerce")
    df["tract_geoid"] = df["state"] + df["county"] + df["tract"]
    df["GEOID"] = df["tract_geoid"] + df["block"]
    return df


def check_f11_decennial_invariants(
    source: CensusSource, battery: Battery = DEFAULT_BATTERY, ctx: Optional[Dict[str, Any]] = None
) -> ValidationResult:
    b = battery
    states = ",".join(b.f11_states)
    counties = ", ".join(f"{s}{c}" for s, c in b.f11_block_counties)
    res = ValidationResult(
        "F11",
        "2020 Census invariants and hierarchy (census.decennial; dec/pl and dec/dhc through the toolkit's "
        f"API layer), states {states}: (a) state total population in P.L. 94-171 and DHC vs the resident "
        "population published in the 2020 Apportionment Results (Table 2); (b) block housing units (H1_001N, "
        f"a block invariant) summed to tracts and counties vs published tract and county totals, counties "
        f"{counties}, and P.L. 94-171 vs DHC block by block; (c) DHC vs P.L. 94-171 for the items both "
        f"publish ({', '.join(i[2] for i in F11_SHARED_ITEMS)}) at every county of the states and every "
        "tract of those counties.",
        tolerance="exact (integer equality); these are published counts with no sampling error",
    )
    res.census_source += [_dec.APPORTIONMENT_URL, _dec.INVARIANTS_URL, _dec.PPMF_URL,
                          f"{BASE_URL}/2020/dec/pl", f"{BASE_URL}/2020/dec/dhc"]
    failures: List[Dict[str, Any]] = []
    parts: Dict[str, Dict[str, int]] = {}
    abs_e: List[float] = []

    def compare(part: str, ours: float, ref: float, **where: Any) -> None:
        stats = parts.setdefault(part, {"compared": 0, "failed": 0})
        stats["compared"] += 1
        diff = abs(float(ours) - float(ref)) if np.isfinite(ours) and np.isfinite(ref) else math.inf
        abs_e.append(diff)
        if diff != 0:
            stats["failed"] += 1
            if len(failures) < MAX_FAILURE_SAMPLES:
                failures.append({"part": part, **where, "value": ours, "reference": ref})

    # (a) state totals vs the apportionment release
    published = _apportionment_state_totals(
        source.www2_file("dec2020_apportionment_table02.xlsx", APPORTIONMENT_TABLE2_URL, "apportionment_table")
    )
    pl_vars = sorted({i[0] for i in F11_SHARED_ITEMS})
    dhc_vars = sorted({i[1] for i in F11_SHARED_ITEMS})
    pl_states = _f11_frame(source, _dec.DECENNIAL_PL, pl_vars, {"for": f"state:{states}"})
    dhc_states = _f11_frame(source, _dec.DECENNIAL_DHC, dhc_vars, {"for": f"state:{states}"})
    for st in b.f11_states:
        ref = float(published.get(st, math.nan))
        compare("a_state_population", float(pl_states.at[st, "P1_001N"]), ref, geography=st, dataset="dec/pl")
        compare("a_state_population", float(dhc_states.at[st, "P1_001N"]), ref, geography=st, dataset="dec/dhc")

    # (c) DHC vs P.L. 94-171, counties of the states and tracts of the block counties
    geos = [("county", {"for": "county:*", "in": f"state:{states}"})] + [
        ("tract", {"for": "tract:*", "in": f"state:{s} county:{c}"}) for s, c in b.f11_block_counties
    ]
    tract_totals: Dict[str, Tuple[pd.DataFrame, pd.DataFrame]] = {}
    county_totals: Optional[Tuple[pd.DataFrame, pd.DataFrame]] = None
    for level, geo in geos:
        pl = _f11_frame(source, _dec.DECENNIAL_PL, pl_vars, geo)
        dhc = _f11_frame(source, _dec.DECENNIAL_DHC, dhc_vars, geo)
        if sorted(pl.index) != sorted(dhc.index):
            compare(f"c_{level}_geographies", len(pl.index), len(dhc.index), geography=geo.get("in", ""))
        for g in pl.index.intersection(dhc.index):
            for pv, dv, item in F11_SHARED_ITEMS:
                compare(f"c_{level}_dhc_vs_pl", float(dhc.at[g, dv]), float(pl.at[g, pv]),
                        geography=g, item=f"{dv} vs {pv} ({item})")
        if level == "county":
            county_totals = (pl, dhc)
        else:
            tract_totals[geo["in"]] = (pl, dhc)

    # (b) block housing units -> tract and county totals; P.L. 94-171 vs DHC per block
    block_counts: Dict[str, int] = {}
    for st, co in b.f11_block_counties:
        pl_blocks = _f11_blocks(source, _dec.DECENNIAL_PL, st, co)
        dhc_blocks = _f11_blocks(source, _dec.DECENNIAL_DHC, st, co).set_index("GEOID")
        block_counts[st + co] = len(pl_blocks)
        for g, value in pl_blocks.set_index("GEOID")["H1_001N"].items():
            compare("b_block_pl_vs_dhc", float(dhc_blocks["H1_001N"].get(g, math.nan)), float(value), geography=g)
        sums = pl_blocks.groupby("tract_geoid")["H1_001N"].sum()
        pl_tracts, dhc_tracts = tract_totals[f"state:{st} county:{co}"]
        for frame, ds in ((pl_tracts, "dec/pl"), (dhc_tracts, "dec/dhc")):
            for g in frame.index.union(sums.index):
                compare("b_blocks_to_tracts", float(sums.get(g, math.nan)),
                        float(frame["H1_001N"].get(g, math.nan)), geography=g, dataset=ds)
        assert county_totals is not None
        for frame, ds in zip(county_totals, ("dec/pl", "dec/dhc")):
            compare("b_blocks_to_county", float(pl_blocks["H1_001N"].sum()),
                    float(frame.at[st + co, "H1_001N"]), geography=st + co, dataset=ds)

    res.n_compared = sum(p["compared"] for p in parts.values())
    res.n_failed = sum(p["failed"] for p in parts.values())
    res.max_abs_error = _max(abs_e)
    res.failures = failures
    res.details = {"parts": parts, "blocks_per_county": block_counts,
                   "published_state_population": {st: published.get(st) for st in b.f11_states}}
    res.notes += [
        "Invariants (published without disclosure-avoidance noise): state total population, block total "
        "housing units and occupied group-quarters facilities by type (Census DAS update 2020-11-25, "
        f"{_dec.INVARIANTS_URL}; fact sheet {_dec.DAS_FACT_SHEET_URL}). Part (a) compares against an "
        "independent publication (the April 2021 apportionment release), part (b) tests the block invariant "
        "and the tabulation hierarchy.",
        "Part (c) items other than housing units are not invariants: they agree because every 2020 product "
        "is tabulated from the same privacy-protected microdata (\"Tabulations from the PPMF are entirely "
        f"consistent with tables from these data products\", {_dec.PPMF_URL}). Agreement shows the toolkit "
        "reads both files consistently; it does not show the counts are free of disclosure-avoidance noise.",
        "There is no sampling error to compare: decennial counts have no MOE, so the check asserts exact "
        "equality only.",
    ]
    return res.finish(res.n_failed == 0 and res.n_compared > 0)


# ---------------------------------------------------------------------------
# Battery and reports
# ---------------------------------------------------------------------------
