# SPDX-License-Identifier: AGPL-3.0-or-later
"""Spatial error/lag regression and known-variance correction helpers (extracted from census/spatial.py in Round 177)."""
from census.spatial import (  # noqa: F401
    Any,
    CONTROLLED_TOTAL_CAVEAT,
    CORRECTION_COST_NOTE,
    CORRECTION_LAMBDA_BOUNDARY,
    CORRECTION_MAX_N,
    CORRECTION_METHODS,
    CORRELATED_ERROR_CAVEAT,
    DEFAULT_METHODS,
    Dict,
    EFFECTS_MAX_N,
    ERROR_CAVEAT,
    LAG_EFFECTS_CAVEAT,
    LAG_EFFECTS_NOTE,
    LAG_GM_NOTE,
    LAG_ML_CAVEAT,
    LAMBDA_MEANING_NOTE,
    List,
    ModelResult,
    NOISY_COVARIATE_CAVEAT,
    OUTCOME_ERROR_CORRECTION_NOTE,
    Optional,
    REPLICATE_COUNT,
    REPLICATE_FACTOR,
    SIGMA2_ZERO_REL,
    SOURCE_MODEL,
    SOURCE_SAMPLING_MODEL,
    SOURCE_SAMPLING_REPLICATE,
    SPATIAL_METHODS,
    SPATIAL_MODELS,
    SPATIAL_PARAMETER_TEST_NOTE,
    _aligned,
    _design,
    _lag_effect_values,
    _release_year,
    _replicate_matrix,
    _spreg_fit,
    check_refit_count,
    check_replicate_policy,
    controlled_total_reason,
    effect_multipliers,
    lag_effects,
    lm_diagnostics,
    math,
    np,
    pd,
    precheck_replicates,
    replicate_completeness,
    stochastic_variables,
    warnings,
    weights_eigenvalues,
    weights_report,
)



def error_model_known_variances(y: np.ndarray, X: np.ndarray, W: np.ndarray, D: np.ndarray,
                                method: str = "reml") -> Dict[str, Any]:
    """Spatial error model with known independent outcome sampling variances ``D`` (census.sae_spatial).

    y = X beta + u + e, u = lambda W u + eps, eps ~ N(0, sigma^2 I), e ~ N(0, diag(D)):
    V = sigma^2 [(I - lambda W)'(I - lambda W)]^-1 + diag(D), the spatial
    Fay-Herriot likelihood with rho = lambda (Petrucci & Salvati 2006;
    Molina & Marhuenda 2015 eq. (6)). (sigma^2, lambda) by REML or ML
    (census.sae_spatial.estimate_variance_rho), beta by GLS with covariance
    (X'V^-1X)^-1, SEs of (sigma^2, lambda) from the inverse expected
    information 0.5 tr(M V_k M V_l), M = P (REML) or V^-1 (ML).

    The ONE estimator behind ``spatial_regression(correct_outcome_error=True)``
    and the A1 studies' diagonal-Sigma rows (census.simulation_spreg
    'spatial_error_attenuation' and '_correlated' call this function), so the
    validated coverage describes the shipped path. ``X`` includes the
    constant; ``W`` is dense. Returns ``boundary`` (|lambda| >=
    CORRECTION_LAMBDA_BOUNDARY or sigma^2 at 0) with ``sigma2_zero``. Raises
    RuntimeError when the optimizer does not converge or V is singular at the
    optimum (no fallback to the uncorrected estimate).
    """
    from scipy import linalg as sla
    from .sae_spatial import _fisher, _fit, _loglik

    meth = method.upper()
    try:
        fit = _fit(y, X, D, W, meth)
    except (np.linalg.LinAlgError, sla.LinAlgError) as exc:
        raise RuntimeError(
            f"correct_outcome_error: the {meth} fit is singular at the optimum (V = sigma^2 C(lambda) + "
            f"diag(SE^2) cannot be factorized: {exc}); no corrected estimate is reported and the uncorrected fit "
            "is not substituted. This happens when sigma^2 is estimated at 0 and some SEs are 0 or tiny; check "
            "the SE column (units must match the outcome)") from exc
    if not fit["converged"]:
        raise RuntimeError(
            f"correct_outcome_error: the {meth} optimizer for (sigma^2, lambda) did not converge "
            f"(stopped at lambda={fit['rho']:.4f}, sigma^2={fit['A']:.4g}); no corrected estimate is reported and "
            "the uncorrected fit is not substituted. Check the SE column (units must match the outcome), the "
            "weights, and whether the sampling variances exceed the outcome's variance")
    s = fit["state"]
    A, lam = float(fit["A"]), float(fit["rho"])
    Fi = np.full((2, 2), np.nan)
    # at the sigma^2 = 0 boundary (relative to the outcome's variance) lambda is not identified: no SE
    sigma2_zero = A <= SIGMA2_ZERO_REL * max(float(np.var(y, ddof=1)), 1e-300)
    if not sigma2_zero:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", sla.LinAlgWarning)
                Fi = sla.inv(_fisher(s, meth))
        except (np.linalg.LinAlgError, sla.LinAlgError, ValueError):
            pass
    ll, _ = _loglik(np.array([A, lam]), y, X, D, W, "ML")
    return {"A": A, "lambda": lam, "beta": np.asarray(fit["beta"], float), "vcov_beta": np.asarray(fit["Q"], float),
            "se_A": float(math.sqrt(Fi[0, 0])) if np.isfinite(Fi[0, 0]) and Fi[0, 0] > 0 else float("nan"),
            "se_lambda": float(math.sqrt(Fi[1, 1])) if np.isfinite(Fi[1, 1]) and Fi[1, 1] > 0 else float("nan"),
            "loglik": float(ll), "converged": True, "sigma2_zero": bool(sigma2_zero),
            "boundary": bool(sigma2_zero or abs(lam) >= CORRECTION_LAMBDA_BOUNDARY)}


def _corrected_error_regression(formula: str, d: pd.DataFrame, weights, *, outcome: str, se_col: Optional[str],
                                method: Optional[str], target: str, level: float, controlled_total: Optional[bool],
                                ml_method: str, spreg_kwargs: Dict[str, Any]) -> ModelResult:
    """spatial_regression(model='error', correct_outcome_error=True): see :func:`spatial_regression`."""
    from .models import _table

    if se_col is None:
        raise ValueError("correct_outcome_error=True needs se_col: the column of the outcome's sampling SEs")
    if outcome not in d.columns:
        raise ValueError(f"correct_outcome_error=True needs a plain outcome column on the left of the formula "
                         f"(got {outcome!r}); se_col must be that column's SE")
    if se_col not in d.columns:
        raise KeyError(f"se_col {se_col!r} not in frame")
    corr_method = "reml" if method is None else method.lower()
    if corr_method not in CORRECTION_METHODS:
        raise ValueError(f"with correct_outcome_error=True, method must be one of {CORRECTION_METHODS} "
                         f"(variance-component estimator; REML is the validated default), not {method!r}")
    import census.spatial as _sp
    max_n = _sp.CORRECTION_MAX_N
    if len(d) > max_n:
        raise ValueError(
            f"correct_outcome_error=True is limited to {max_n} areas (got {len(d)}): the known-variance "
            f"fit works on dense n x n matrices (O(n^3) time per likelihood evaluation, O(n^2) memory; "
            f"{CORRECTION_COST_NOTE}). Fit at county level, or subset the frame to a region (e.g. one or a few "
            "states or metro areas) and rebuild the weights for it")
    se = pd.to_numeric(d[se_col], errors="coerce").to_numpy(float)
    if not np.isfinite(se).all() or (se < 0).any():
        bad = list(np.asarray(d.index)[~(np.isfinite(se) & (se >= 0))][:20])
        raise ValueError(f"se_col {se_col!r} must be finite and >= 0 in every area: {bad}")
    if (se == 0).any():
        zero = list(np.asarray(d.index)[se == 0][:20])
        raise ValueError(
            f"se_col {se_col!r} is 0 in {int((se == 0).sum())} area(s): {zero}. The known-variance model would treat "
            "those estimates as exact (V is singular when sigma^2 is estimated at 0, and an exact area can force a "
            "degenerate boundary fit). An ACS SE of 0 usually marks a controlled or suppressed cell: drop those "
            "areas (subset the frame and rebuild the weights) or give them their published nonzero SE")
    y2, X, names, yname = _design(formula, d)
    y = y2[:, 0]
    n = len(y)
    if n <= X.shape[1] + 3:
        raise ValueError(f"need more areas ({n}) than parameters ({X.shape[1] + 3})")
    W = np.asarray(weights.full()[0], float)  # row-standardized, in w.id_order (= d's row order)
    D = se ** 2
    Xc = np.column_stack([np.ones(n), X])
    fit = _sp.error_model_known_variances(y, Xc, W, D, corr_method)
    terms = ["Intercept"] + names + ["lambda"]
    params = pd.Series(list(fit["beta"]) + [fit["lambda"]], index=terms)
    se_model = pd.Series(list(np.sqrt(np.diag(fit["vcov_beta"]))) + [fit["se_lambda"]], index=terms)
    table = _table(params, se_model, pd.Series(np.nan, index=terms), level, target)

    reason = controlled_total_reason(outcome) if controlled_total is None else (
        "flagged by the caller (controlled_total=True)" if controlled_total else None)
    boundary = []
    if abs(fit["lambda"]) >= CORRECTION_LAMBDA_BOUNDARY:
        boundary.append(f"|lambda| >= {CORRECTION_LAMBDA_BOUNDARY:g} (near the unit bound; the SAR process is "
                        "near-singular)")
    var_y = float(np.var(y, ddof=1))
    if fit["sigma2_zero"]:
        boundary.append("sigma^2 estimated at 0: the sampling variances absorb all residual variation, lambda is "
                        "not identified and has no interval")
    try:
        _, _, _, lam_naive = _sp._spreg_fit(y2, X, weights, "error", "ml", names, yname, ml_method, spreg_kwargs)
    except Exception:  # noqa: BLE001 - comparison only; reported as unavailable
        lam_naive = None
    k = Xc.shape[1] + 2
    diagnostics: Dict[str, Any] = {
        "lm_tests": lm_diagnostics(y2, X, weights), "interval_target": target,
        "converged": True, "boundary": bool(boundary), "controlled_total_warning": reason is not None,
        "logll": fit["loglik"], "aic": -2 * fit["loglik"] + 2 * k, "schwarz": -2 * fit["loglik"] + k * math.log(n),
        "outcome_error_correction": {
            "se_col": se_col, "variance_method": corr_method.upper(), "sigma2": fit["A"],
            "sigma2_se": fit["se_A"], "lambda": fit["lambda"], "lambda_se": fit["se_lambda"],
            "lambda_uncorrected": lam_naive,
            "lambda_uncorrected_method": "spreg ML_Error (the default error model, no correction)",
            "mean_sampling_variance_share": float(np.mean(D) / var_y) if var_y > 0 else None,
            "assumption": "sampling errors independent across areas; variances known (SE^2)",
            "boundary_reasons": boundary, "controlled_total_reason": reason,
            "evidence": ["docs/audits/spatial_regression_validation.md (A1)",
                         "docs/audits/acs_sampling_covariance.md (C)"],
        },
    }
    notes: List[str] = []
    if reason is not None:
        notes.append(f"{CONTROLLED_TOTAL_CAVEAT} ({reason}; pass controlled_total=False if it is not)")
    notes += [OUTCOME_ERROR_CORRECTION_NOTE, LAMBDA_MEANING_NOTE, CORRELATED_ERROR_CAVEAT]
    if lam_naive is not None:
        notes.append(f"uncorrected lambda (spreg ML_Error) = {lam_naive:.4f}; corrected = {fit['lambda']:.4f}")
    notes += [f"boundary fit: {b}" for b in boundary]
    if not np.isfinite(fit["se_lambda"]):
        notes.append("lambda has no SE (sigma^2 at 0, or singular information at the fitted values): no interval "
                     "is reported")
    if weights.islands:
        notes.append(f"{len(weights.islands)} island(s) in the weights (zero spatial lag)")
    if d.attrs.get("extra_rows_dropped"):
        notes.append(f"{len(d.attrs['extra_rows_dropped'])} frame row(s) not in the weights were ignored")
    notes.append(f"intervals and p-values use the '{target}' target (normal, from se_model: GLS for beta, the "
                 f"{corr_method.upper()} information for lambda)")
    notes.append(SPATIAL_PARAMETER_TEST_NOTE.format(sp="lambda"))
    notes.append(NOISY_COVARIATE_CAVEAT)
    return ModelResult(
        model_type="spatial_error", formula=formula, n_obs=int(n), coefficients=table,
        method=f"spatial error model with known outcome sampling variances (spatial Fay-Herriot likelihood, "
               f"{corr_method.upper()})",
        uncertainty_sources=[SOURCE_MODEL, SOURCE_SAMPLING_MODEL], confidence_level=level, notes=notes,
        diagnostics=diagnostics,
        provenance={"library": "census.sae_spatial", "spatial_parameter": "lambda", "ml_method": None,
                    "outcome_error_correction": True, "se_col": se_col,
                    "weights": getattr(weights, "census_report", None) or weights_report(weights)},
    )


TRACT_ERROR_NOTE = ("EXPLORATORY on tracts: the spatial error ML slope interval under-covered on NC and MI tract "
                    "geometries when fields correlate over 20-100 km (.63-.76; Round 71, "
                    "docs/audits/tract_spatial_validation.md). For tract slopes use fit_model(spatial=\"scpc\") (OLS, "
                    "validated with rho_bar .20/.30).")


def spatial_regression(
    formula: str,
    data: pd.DataFrame,
    weights,
    *,
    model: str = "lag",
    method: Optional[str] = None,
    replicates: Optional[pd.DataFrame] = None,
    target: str = "population",
    confidence_level: float = 0.90,
    geoid_col: str = "GEOID",
    ml_method: str = "full",
    max_failed_replicates: int = 0,
    replicate_policy: str = "flag",
    correct_outcome_error: bool = False,
    se_col: Optional[str] = None,
    controlled_total: Optional[bool] = None,
    **spreg_kwargs: Any,
) -> ModelResult:
    """Spatial lag or spatial error regression (spreg) as a ModelResult.

    ``model``: ``lag`` (y = rho W y + X b + e) or ``error`` (u = lambda W u + e).
    ``method``: ``ml`` (ML_Lag / ML_Error, ``ml_method`` full/ord/LU) or ``gm``
    (GM_Lag: spatial 2SLS with W X, W^2 X instruments; GM_Error_Het:
    Kelejian-Prucha GMM robust to heteroskedasticity). Default
    (:data:`DEFAULT_METHODS`): ``gm`` for the lag model, ``ml`` for the error
    model. Coefficients include
    the spatial parameter as term ``rho`` or ``lambda``. ``diagnostics`` carries
    the OLS LM tests (``lm_tests``) with a suggested model.

    With ``replicates`` every formula variable that has replicates is replaced
    by its r-th replicate and the model refit 80 times; ``se_sampling`` =
    sqrt(4/80 sum (b_r - b)^2) as in census.models.fit_replicate, and
    ``target`` (population / these_areas / conservative) picks the SE for
    intervals. ML refits cost O(n^3) each with ml_method='full'; use
    ml_method='LU' or method='gm' for large n.

    Measured behavior (census.simulation 'spatial_regression_coverage', added
    to the notes): with ACS sampling error in the outcome the ML lag
    estimator's rho is biased toward 0 and its intervals under-cover badly
    (0.48 at rho 0.3, 0.003 at 0.6); GMM lag, the default since Round 15,
    covers rho near nominal (0.89-0.90). In the error model lambda is
    attenuated by either estimator (ML, the default, is not worse), while
    beta intervals stay near nominal. ``replicate_policy``: "flag"
    (default) records failed refits or stochastic variables without
    replicates in diagnostics["replicates_incomplete"]; "strict" raises
    ValueError (census.results.replicate_completeness, PLAN_ROUND_11 Q2/D7).

    ``correct_outcome_error=True`` (model='error' only; PLAN_ROUND_16 A1,
    owner-approved option, off by default) needs ``se_col``, the outcome's
    sampling SEs, and fits the spatial error model with those known
    variances: V = sigma^2 [(I - lambda W)'(I - lambda W)]^-1 + diag(SE^2),
    the spatial Fay-Herriot likelihood of census.sae_spatial. ``method`` is
    then the variance-component estimator, ``reml`` (default, validated) or
    ``ml``. lambda (corrected) has a Wald interval from the information
    matrix and beta GLS Wald intervals, the interval methods validated by the
    'spatial_error_attenuation' study (REML lambda coverage 0.86-0.93 at
    lambda 0.3-0.6 vs 0.003-0.85 uncorrected). It assumes sampling errors
    independent across areas (docs/audits/acs_sampling_covariance.md: about 0
    for rates, shares, medians and most counts); positively correlated errors
    bias it upward (notes). Controlled totals (population, households,
    housing units: :data:`CONTROLLED_TOTAL_CELLS`, or ``controlled_total=True``)
    have negatively correlated errors within counties and get a warning note
    and ``diagnostics['controlled_total_warning']``. Non-convergence, or a
    singular V at the optimum, raises RuntimeError; SEs of 0 and frames above
    :data:`CORRECTION_MAX_N` areas (dense O(n^3) fit) are refused with
    ValueError. Replicates are not used with this option.
    """
    from .analysis import formula_variables
    from .models import INTERVAL_TARGETS, _table

    check_replicate_policy(replicate_policy)

    from .splines import has_spline
    if has_spline(formula):
        raise ValueError("cr splines are supported only by non-spatial fit_replicate")
    model = model.lower()
    if model not in SPATIAL_MODELS:
        raise ValueError(f"model must be one of {SPATIAL_MODELS}")
    if correct_outcome_error:
        if model != "error":
            raise ValueError("correct_outcome_error=True applies to model='error' only (the lag model's default "
                             "GMM estimator already holds its rho intervals under outcome error)")
        if replicates is not None and len(replicates):
            raise ValueError("correct_outcome_error=True does not use replicates: the outcome's sampling variance "
                             "enters the model through se_col; fit without replicates")
        if target != "population":
            raise ValueError("correct_outcome_error=True supports target='population' only (intervals from the "
                             "model, which includes the known sampling variances)")
        outcome = formula.split("~")[0].strip()
        d = _aligned(data, outcome if outcome in data.columns else None, weights, geoid_col)
        weights.transform = "r"
        return _corrected_error_regression(
            formula, d, weights, outcome=outcome, se_col=se_col, method=method, target=target,
            level=confidence_level if confidence_level <= 1 else confidence_level / 100,
            controlled_total=controlled_total, ml_method=ml_method, spreg_kwargs=spreg_kwargs)
    if se_col is not None or controlled_total is not None:
        raise ValueError("se_col and controlled_total apply only with correct_outcome_error=True")
    method = DEFAULT_METHODS[model] if method is None else method.lower()
    if method not in SPATIAL_METHODS:
        raise ValueError(f"method must be one of {SPATIAL_METHODS}")
    if target not in INTERVAL_TARGETS:
        raise ValueError(f"target must be one of {INTERVAL_TARGETS}")
    if target == "these_areas" and (replicates is None or not len(replicates)):
        raise ValueError("target='these_areas' needs replicates (se_sampling)")
    outcome = formula.split("~")[0].strip()
    d = _aligned(data, outcome if outcome in data.columns else None, weights, geoid_col)
    weights.transform = "r"
    y, X, names, yname = _design(formula, d)
    if len(y) != weights.n:
        raise ValueError("rows were dropped by the formula; weights must match the modelled areas")
    import census.spatial as _sp
    r, betas, se, spatial = _sp._spreg_fit(y, X, weights, model, method, names, yname, ml_method, spreg_kwargs)
    sp_name = "rho" if model == "lag" else "lambda"
    terms = ["Intercept"] + names + [sp_name]
    params = pd.Series(betas, index=terms)
    se_model = pd.Series(se, index=terms)
    se_sampling = pd.Series(np.nan, index=terms)
    notes: List[str] = []
    sources = [SOURCE_MODEL]
    est_method = f"spreg {'ML' if method == 'ml' else 'GMM'} spatial {model}"
    diagnostics: Dict[str, Any] = {"lm_tests": lm_diagnostics(y, X, weights), "interval_target": target}
    for attr in ("logll", "aic", "schwarz", "pr2", "pr2_e", "sig2"):
        if hasattr(r, attr):
            try:
                diagnostics[attr] = float(np.asarray(getattr(r, attr)).ravel()[0])
            except (TypeError, ValueError):
                pass
    if model == "error" and method == "gm":
        notes.append("GM_Error_Het: Kelejian-Prucha (2010) GMM, heteroskedasticity-robust; spatial parameter "
                     "is 'lambda'")
    if weights.islands:
        notes.append(f"{len(weights.islands)} island(s) in the weights (zero spatial lag)")
    eig = weights_eigenvalues(weights) if model == "lag" else None
    share = 1.0 - len(weights.islands) / weights.n
    eff = None
    if eig is not None:
        k = len(terms)
        vm_k = np.asarray(r.vm, float)[:k, :k]
        eff = lag_effects(betas, vm_k, names, eig, share)
        # for simulated (LeSage & Pace 2009) effect intervals: draws from N(estimates, vcov)
        diagnostics["coefficient_vcov"] = {"terms": terms, "matrix": vm_k.tolist()}
    B = None
    if replicates is not None and len(replicates):
        all_used = formula_variables(formula, d)
        used = [v for v in all_used if v in set(replicates["variable"])]
        if not used:
            raise ValueError("no formula variable has replicates in the replicate frame")
        yr = _release_year(data)
        mats = {v: _replicate_matrix(replicates, v, list(d.index), geoid_col, yr) for v in used}
        # rows without replicates are refused by _replicate_matrix, so only
        # failed refits and variables without replicates can be incomplete
        stoch = stochastic_variables(data, [v for v in all_used if v not in used])
        precheck_replicates(replicate_policy, variables_without_replicates=stoch, context="spatial_regression")
        B, failed, explosive = [], 0, 0
        for k in range(REPLICATE_COUNT):
            dd = d.copy()
            for v, m in mats.items():
                dd[v] = m[:, k]
            try:
                yr, Xr, _, _ = _design(formula, dd)
                _, b, _, _ = _sp._spreg_fit(yr, Xr, weights, model, method, names, yname, ml_method, spreg_kwargs)
                if not np.isfinite(b).all():
                    raise ValueError("non-finite")
                if model == "lag" and not abs(float(b[-1])) < 1:
                    # (I - rho W)^-1 is not a stationary multiplier: effects undefined, not a usable refit
                    explosive += 1
                    raise ValueError("|rho| >= 1")
                B.append(b)
            except Exception:  # noqa: BLE001 - counted and reported
                failed += 1
        context = "spatial_regression"
        if explosive:
            context += (f" ({explosive} replicate refit(s) estimated |rho| >= 1, where the spatial multiplier and "
                        "the effects are undefined; counted as failed refits)")
            diagnostics["replicate_refits_rho_out_of_bounds"] = explosive
        replicate_completeness(replicate_policy, failed_refits=failed, variables_without_replicates=stoch,
                               context=context, diagnostics=diagnostics, notes=notes)
        if explosive:
            notes.append(f"{explosive} of {REPLICATE_COUNT} replicate refits estimated |rho| >= 1 and were counted "
                         "as failed refits (not dropped silently); se_sampling uses the remaining refits")
        check_refit_count(failed, len(B), max_failed_replicates, context)
        B = np.vstack(B)
        se_sampling = pd.Series(np.sqrt(REPLICATE_FACTOR * ((B - betas) ** 2).sum(axis=0)), index=terms)
        sources.append(SOURCE_SAMPLING_REPLICATE)
        est_method += ", replicate refits"
        diagnostics["replicate_failures"] = failed
        diagnostics["replicate_variables"] = used
        notes.append("se_sampling from 80 replicate refits; se_total is conservative (the model residual already "
                     "absorbs outcome sampling error), as for census.models.fit_replicate")
    level = confidence_level if confidence_level <= 1 else confidence_level / 100
    table = _table(params, se_model, se_sampling, level, target)
    effects = None
    if model == "lag":
        table["interpretation"] = ["intercept"] + [
            "coefficient on X in y = rho W y + X beta + e: NOT the marginal effect (see effects)"] * len(names) + [
            "spatial lag parameter rho (spillover strength); its p-value tests rho = 0, not the model "
            "specification"]
        if eff is None:
            notes.insert(0, f"{LAG_EFFECTS_NOTE}. Effects were NOT computed: {weights.n} areas exceed "
                            f"EFFECTS_MAX_N={EFFECTS_MAX_N} (dense eigenvalues of W)")
        else:
            eff_sampling = pd.Series(np.nan, index=eff["terms"])
            if B is not None:
                E = np.vstack([_lag_effect_values(b, eig, len(names), np.asarray(share)) for b in B])
                eff_sampling[:] = np.sqrt(REPLICATE_FACTOR * ((E - eff["estimate"]) ** 2).sum(axis=0))
            effects = _table(pd.Series(eff["estimate"], index=eff["terms"]), pd.Series(eff["se"], index=eff["terms"]),
                             eff_sampling, level, target)
            effects.insert(1, "variable", [v for v in names for _ in range(3)])
            effects.insert(2, "effect", ["direct", "indirect", "total"] * len(names))
            notes[0:0] = [LAG_EFFECTS_NOTE, LAG_EFFECTS_CAVEAT]
            if not abs(spatial) < 1:
                notes.insert(0, f"rho = {spatial:.4f} is outside (-1, 1): (I - rho W)^-1 is not a stationary spatial "
                                "multiplier, so the direct, indirect and total effects are undefined (reported as "
                                "NaN, no intervals). Do not interpret beta or rho as effects; check the "
                                "specification (a spatial Durbin process or W X instruments correlated with the "
                                "error push GMM rho toward or past 1), or try method='ml'")
                diagnostics["effects_undefined"] = True
            diagnostics["effects_multipliers"] = {k: v for k, v in effect_multipliers(eig, spatial, share).items()
                                                  if not k.startswith("d_")}
    notes.append(f"intervals and p-values use the '{target}' target")
    notes.append(SPATIAL_PARAMETER_TEST_NOTE.format(sp=sp_name))
    notes.append(ERROR_CAVEAT if model == "error" else LAG_ML_CAVEAT if method == "ml" else LAG_GM_NOTE)
    if model == "error" and geoid_col in data and data[geoid_col].astype(str).str.len().ge(11).all():
        notes.append(TRACT_ERROR_NOTE)
    notes.append(NOISY_COVARIATE_CAVEAT)
    return ModelResult(
        model_type=f"spatial_{model}", formula=formula, n_obs=int(len(y)), coefficients=table,
        method=est_method, uncertainty_sources=sources, confidence_level=level, notes=notes,
        diagnostics=diagnostics,
        provenance={"library": "spreg", "spatial_parameter": sp_name, "ml_method": ml_method if method == "ml" else None,
                    "weights": getattr(weights, "census_report", None) or weights_report(weights),
                    **({"coefficient_meaning": "beta is the coefficient on X in y = rho W y + X beta + e, not a "
                                               "marginal effect; see effects"} if model == "lag" else {})},
        effects=effects,
    )
