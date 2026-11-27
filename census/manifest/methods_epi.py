# SPDX-License-Identifier: AGPL-3.0-or-later
"""Causal, disparity, joinpoint, meta-analysis, and QBA manifest methods (extracted from census/manifest/methods.py in Round 157)."""
from census.manifest.methods import (  # noqa: F401
    np,
    stats,
)

def _run_estimate_effect(a, args, frame, level, replicates, correction, ctx):
    kind = a["kind"]
    if kind == "treatment":
        from ..causal import estimate_effect
        r = estimate_effect(frame, a["outcome"], a["treatment"], a["confounders"],
                            method=args.get("method", "aipw"), replicates=replicates,
                            calibrate=bool(args.get("calibrate", False)), weights=args.get("weights"))
        eff = r.get("ate") or r.get("effect") or r
        return dict(kind=kind, estimate=float(eff["estimate"]), se=float(eff["se"]),
                    ci_lower=float(eff["lower"]), ci_upper=float(eff["upper"]),
                    validated=bool(r["validated"]), se_basis=f"causal treatment ({args.get('method', 'aipw')})",
                    notes=list(r.get("notes", [])), audit=r.get("audit", ""), raw=r)
    if kind == "matching":
        from ..matching import matching_effect
        m = args.get("method", "nn")
        est_arg = args.get("estimand", "ATT" if m in ("cem", "ps") else "ATE")
        r = matching_effect(frame, a["outcome"], a["treatment"], a["confounders"], method=m, estimand=est_arg)
        eff = r["effect"]
        return dict(kind=kind, estimate=float(eff["estimate"]), se=float(eff["se"]),
                    ci_lower=float(eff["lower"]), ci_upper=float(eff["upper"]),
                    validated=bool(r["validated"]), se_basis=f"matching ({m}, {est_arg})",
                    notes=list(r.get("notes", [])), audit=r.get("audit", ""), raw=r)
    if kind == "iv":
        from ..causal import iv_slope
        r = iv_slope(frame, a["outcome"], a["x"], a["instrument"], controls=args.get("controls", ()))
        ar = r.get("anderson_rubin", {})
        lo = float(ar.get("lower", r["lower"])); hi = float(ar.get("upper", r["upper"]))
        return dict(kind=kind, estimate=float(r["estimate"]), se=float(r["se"]),
                    ci_lower=lo, ci_upper=hi, validated=bool(r["validated"]),
                    se_basis="2SLS (Anderson-Rubin interval)", notes=list(r.get("notes", [])),
                    audit=r.get("audit", ""), raw=r)
    if kind == "mediation":
        from ..causal import mediation
        r = mediation(frame, a["x"], a["mediator"], a["outcome"], controls=args.get("controls", ()),
                      replicates=replicates, calibrate=bool(args.get("calibrate", False)))
        part = r["indirect"]
        return dict(kind=kind, estimate=float(part["estimate"]), se=float(part["se"]),
                    ci_lower=float(part["lower"]), ci_upper=float(part["upper"]),
                    validated=bool(r["validated"]), se_basis="mediation indirect effect",
                    notes=list(r.get("notes", [])), audit=r.get("audit", ""), raw=r)
    raise ValueError(f"unsupported estimate_effect kind {kind!r}")


def _stat_estimate_effect(h, res):
    est = float(res["estimate"]); se = float(res["se"])
    null_v = float(h.get("null_value", 0.0))
    z = abs(est - null_v) / se if np.isfinite(se) and se > 0 else np.inf
    out = {"estimate": est, "se": se, "se_basis": res["se_basis"],
           "ci_lower": float(res["ci_lower"]), "ci_upper": float(res["ci_upper"]),
           "p_two_sided": float(2.0 * stats.norm.sf(z))}
    if not res.get("validated", False):
        out["confirmatory_refusal"] = f"estimate_effect ({res['kind']}) was not validated ({res.get('audit', '')})"
    return out


def _check_estimate_effect(stage, ctx):
    if stage != "before_spatial":
        return
    a, manifest, names, ext_names, errors = ctx["a"], ctx["manifest"], ctx["names"], ctx.get("ext_names") or (), ctx["errors"]
    label = f"analyses ({a.get('id')}) estimate_effect"
    kind = a.get("kind")
    if kind not in ("treatment", "matching", "iv", "mediation"):
        errors.append(f"{label}: kind must be 'treatment', 'matching', 'iv' or 'mediation'")
        return
    out_v = a.get("outcome")
    out_ok = isinstance(out_v, str) and (
        out_v in names or out_v in ext_names or (out_v.endswith("_numerator") and out_v[:-10] in ext_names)
    )
    if not out_ok:
        errors.append(f"{label}: outcome {out_v!r} is not a manifest variable")
    if not manifest.get("exploratory", False) and not manifest.get("causal_question"):
        errors.append(f"{label}: confirmatory causal analyses require a manifest-level causal_question block (Round 89)")
    args = a.get("args") or {}
    adj = []
    trt = None
    if kind in ("treatment", "matching"):
        trt = a.get("treatment")
        if trt not in names:
            errors.append(f"{label}: treatment {trt!r} is not a manifest variable")
        confs = a.get("confounders")
        if not isinstance(confs, list) or not confs or not all(isinstance(c, str) and c in names for c in confs):
            errors.append(f"{label}: confounders must be a non-empty list of manifest variables")
        else:
            adj = list(confs)
            if a.get("outcome") in confs:
                errors.append(f"{label}: circularity (R1/R2): outcome cannot appear in confounders")
        if kind == "treatment":
            bad = set(args) - {"method", "weights", "calibrate"}
            if bad:
                errors.append(f"{label}: treatment takes args method, weights, calibrate only, not {sorted(bad)}")
            if args.get("method", "aipw") not in ("aipw", "ipw", "ra"):
                errors.append(f"{label}: treatment method must be 'aipw', 'ipw' or 'ra'")
            if args.get("weights") not in (None, "stabilized", "truncated", "overlap"):
                errors.append(f"{label}: weights must be 'stabilized', 'truncated' or 'overlap'")
        else:
            bad = set(args) - {"method", "estimand"}
            if bad:
                errors.append(f"{label}: matching takes args method, estimand only, not {sorted(bad)}")
            if args.get("method", "nn") not in ("nn", "cem", "ps"):
                errors.append(f"{label}: matching method must be 'nn', 'cem' or 'ps'")
            if args.get("estimand") not in (None, "ATE", "ATT"):
                errors.append(f"{label}: estimand must be 'ATE' or 'ATT'")
    elif kind == "iv":
        trt = a.get("x")
        if trt not in names or a.get("instrument") not in names:
            errors.append(f"{label}: iv requires manifest variables x and instrument")
        bad = set(args) - {"controls"}
        if bad:
            errors.append(f"{label}: iv takes args controls only, not {sorted(bad)}")
        adj = list(args.get("controls") or [])
    elif kind == "mediation":
        trt = a.get("x")
        if trt not in names or a.get("mediator") not in names:
            errors.append(f"{label}: mediation requires manifest variables x and mediator")
        if a.get("mediator") == a.get("outcome"):
            errors.append(f"{label}: circularity (R1/R2): mediator cannot equal outcome")
        bad = set(args) - {"controls", "calibrate"}
        if bad:
            errors.append(f"{label}: mediation takes args controls, calibrate only, not {sorted(bad)}")
        adj = list(args.get("controls") or [])
    if manifest.get("dag") and trt and adj and not manifest.get("exploratory", False):
        from ..causal_spec import DagError, dag_report
        dag_cfg = {**manifest["dag"], "treatment": trt, "outcome": a.get("outcome")}
        try:
            chk = dag_report(dag_cfg, adj)["check"]
        except DagError as exc:
            errors.append(f"{label}: DAG error: {exc}")
        else:
            if not chk.get("sufficient", True):
                reasons = chk.get("reasons") or [k for k in ("colliders_opened", "mediators", "treatment_descendants",
                                                             "open_backdoor_paths") if chk.get(k)]
                errors.append(f"{label}: DAG backdoor check failed: {'; '.join(map(str, reasons))}")


def _run_spatial_scan(a, args, frame, level, replicates, correction, ctx):
    from ..scan import spatial_scan
    return spatial_scan(frame, a["cases"], population=a.get("population"), expected=a.get("expected"),
                        year=args.get("year"), max_share=float(args.get("max_share", 0.5)),
                        exclude=args.get("exclude"), exclude_rule=args.get("exclude_rule"), prespecified=True)


def _stat_spatial_scan(h, res):
    p = res.get("primary")
    if p is None:
        return {"estimate": 1.0, "se": float("nan"), "se_basis": "Kulldorff Poisson Monte Carlo",
                "ci_lower": float("nan"), "ci_upper": float("nan"), "p_two_sided": 1.0,
                "confirmatory_refusal": "spatial_scan found no high-rate window"}
    out = {"estimate": float(p["relative_risk"]), "se": float("nan"),
           "se_basis": "Kulldorff Poisson Monte Carlo (999 replicates)",
           "ci_lower": float("nan"), "ci_upper": float("nan"), "p_two_sided": float(p["p_value"])}
    if not (res.get("confirmatory") if "confirmatory" in res else res.get("validated_p", res.get("validated", False))):
        out["confirmatory_refusal"] = f"spatial_scan was not validated ({res.get('audit', '')})"
    return out


def _check_spatial_scan(stage, ctx):
    if stage != "before_spatial":
        return
    a, manifest, names, ext_names, errors = ctx["a"], ctx["manifest"], ctx["names"], ctx.get("ext_names") or (), ctx["errors"]
    label = f"analyses ({a.get('id')}) spatial_scan"
    if manifest.get("geography", {}).get("level") not in (None, "county"):
        errors.append(f"{label}: spatial_scan is validated at county level only (Round 81)")
    cases = a.get("cases")
    allowed_cases = isinstance(cases, str) and (
        cases in names or cases in ext_names or (cases.endswith("_numerator") and cases[:-10] in ext_names)
    )
    if not allowed_cases:
        errors.append(f"{label}: cases {cases!r} is not a manifest variable")
    if a.get("population") is None and a.get("expected") is None:
        errors.append(f"{label}: requires population or expected")
    for col in ("population", "expected"):
        if a.get(col) is not None and a[col] not in names:
            errors.append(f"{label}: {col} {a[col]!r} is not a manifest variable")
    args = a.get("args") or {}
    bad = set(args) - {"max_share", "exclude", "exclude_rule", "year"}
    if bad:
        errors.append(f"{label}: takes args max_share, exclude, exclude_rule, year only, not {sorted(bad)}")
    if not manifest.get("exploratory", False) and float(args.get("max_share", 0.5)) != 0.5:
        errors.append(f"{label}: confirmatory spatial_scan requires max_share=0.5 (Round 81)")


def _run_stratified(a, args, frame, level, replicates, correction, ctx):
    from ..stratified import stratified_counts
    return stratified_counts(frame, a["stratum"], a["cases_exposed"], a["total_exposed"],
                             a["cases_unexposed"], a["total_unexposed"],
                             person_time=bool(args.get("person_time", False)), level=level)


def _stat_stratified(h, res):
    stat = h["statistic"]
    if stat == "homogeneity":
        hom = res.get("homogeneity") or {}
        bd = hom.get("or") or hom.get("breslow_day_tarone") or hom.get("breslow_day")
        if not bd:
            raise KeyError("stratified: homogeneity test not present in result")
        p_val = bd.get("p", bd.get("p_value", float("nan")))
        out = {"estimate": float(bd["statistic"]), "se": float("nan"),
               "se_basis": str(bd.get("test", "Breslow-Day-Tarone")),
               "ci_lower": float("nan"), "ci_upper": float("nan"), "p_two_sided": float(p_val)}
        if not bool(bd.get("validated", True)):
            out["confirmatory_refusal"] = "stratified homogeneity test is exploratory"
        return out
    if stat == "reri":
        r = res.get("additive_interaction")
        if not r:
            raise KeyError("stratified: additive_interaction (RERI) requires a binary (2-level) stratum")
        est = float(r["reri"]); lo = float(r["lower"]); hi = float(r["upper"])
        se = float(r.get("se", (hi - lo) / (2.0 * stats.norm.ppf(0.95))))
        z = abs(est - float(h.get("null_value", 0.0))) / se if se > 0 else np.inf
        return {"estimate": est, "se": se, "se_basis": "RERI delta/bootstrap", "ci_lower": lo, "ci_upper": hi,
                "p_two_sided": float(2.0 * stats.norm.sf(z))}
    key = stat[3:]  # rr, or, rd, irr
    m = res["pooled"][key]
    est = float(m["estimate"]); lo = float(m["lower"]); hi = float(m["upper"])
    se = float(m.get("se", (hi - lo) / (2.0 * stats.norm.ppf(0.95))))
    null_v = float(h.get("null_value", 0.0 if key == "rd" else 1.0))
    if key == "rd":
        z = abs(est - null_v) / se if se > 0 else np.inf
    else:
        se_log = (np.log(hi) - np.log(lo)) / (2.0 * stats.norm.ppf(0.95)) if lo > 0 and hi > 0 else np.nan
        z = abs(np.log(est) - np.log(null_v)) / se_log if np.isfinite(se_log) and se_log > 0 else np.inf
    out = {"estimate": est, "se": se, "se_basis": f"Mantel-Haenszel ({key})", "ci_lower": lo, "ci_upper": hi,
           "p_two_sided": float(2.0 * stats.norm.sf(z))}
    if not res.get("validated", True):
        out["confirmatory_refusal"] = f"stratified {stat} was not validated"
    return out


def _check_stratified(stage, ctx):
    a, errors = ctx["a"], ctx["errors"]
    label = f"analyses ({a.get('id')}) stratified"
    if stage == "before_spatial":
        names = ctx["names"]
        for k in ("stratum", "cases_exposed", "total_exposed", "cases_unexposed", "total_unexposed"):
            if a.get(k) not in names:
                errors.append(f"{label}: {k} {a.get(k)!r} is not a manifest variable")
        args = a.get("args") or {}
        bad = set(args) - {"person_time"}
        if bad:
            errors.append(f"{label}: takes args person_time only, not {sorted(bad)}")
        return
    if stage == "hypothesis":
        if ctx["h"].get("statistic") == "mh_irr" and not (a.get("args") or {}).get("person_time"):
            errors.append(f"{label}: mh_irr requires args.person_time=true")


