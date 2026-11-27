# SPDX-License-Identifier: AGPL-3.0-or-later
"""Errors-in-variables (fit_eiv), SIMEX, and cluster jackknife helpers (extracted from census/models.py in Round 158)."""
from census.models import (  # noqa: F401
    Any,
    DEFAULT_CV_THRESHOLD,
    Dict,
    EIV_LOW_RELIABILITY,
    EIV_MODELS,
    FH_POINTER,
    Mapping,
    ModelResult,
    Optional,
    REPLICATE_COUNT,
    REPLICATE_FACTOR,
    SOURCE_MODEL,
    SOURCE_SAMPLING_REPLICATE,
    Sequence,
    Union,
    _corrected_result,
    _fit,
    _prepare,
    _replicate_matrices,
    _screen_summary,
    _setup,
    check_replicate_policy,
    formula_variables,
    math,
    np,
    pd,
    precheck_replicates,
    re,
    replicate_completeness,
    stochastic_variables,
)



def _design_deviations(formula: str, data: pd.DataFrame, mats: Mapping[str, np.ndarray]):
    """Design matrices of the estimates and the per-replicate deviations of every design column.

    Returns (y (n,), X (n, k) DataFrame, D (R, n, k), e (R, n), kept row positions). Replicate
    design rows reuse the estimates' patsy design information, so factor coding is identical and
    error-free columns (constant, factors) have zero deviation."""
    import patsy
    y_df, X_df = patsy.dmatrices(formula, data, return_type="dataframe", NA_action="drop")
    rows = np.asarray(X_df.index)
    cols = list(dict.fromkeys([c for c in ("GEOID", "Year") if c in data.columns] + formula_variables(formula, data)))
    sub = data.loc[rows, cols].reset_index(drop=True)
    keep_nan = patsy.NAAction(NA_types=[])  # undefined replicate values stay NaN (handled by the caller)
    y = y_df.iloc[:, 0].to_numpy(float)
    X = X_df.to_numpy(float)
    R = REPLICATE_COUNT
    D = np.zeros((R, len(sub), X.shape[1]))
    e = np.zeros((R, len(sub)))
    pos = data.index.get_indexer(rows)
    for r in range(R):
        d = sub.copy()
        for v, m in mats.items():
            d[v] = m[pos, r]
        Xr = np.asarray(patsy.build_design_matrices([X_df.design_info], d, NA_action=keep_nan)[0], float)
        yr = np.asarray(patsy.build_design_matrices([y_df.design_info], d, NA_action=keep_nan)[0], float)[:, 0]
        D[r] = Xr - X
        e[r] = yr - y
    return y, X_df, D, e, rows


CLUSTER_PREFIX_RE = re.compile(r"^GEOID\.str\[:(\d+)\]$")


def _cluster_jackknife(X: np.ndarray, y: np.ndarray, w: np.ndarray, D: np.ndarray, e: np.ndarray,
                       inv: np.ndarray, G: int, f: float) -> np.ndarray:
    """Delete-one-cluster jackknife covariance of the fit_eiv moment estimator (CR3)."""
    k = X.shape[1]
    M_g = np.zeros((G, k, k))
    XX_g = np.zeros((G, k, k))
    r_g = np.zeros((G, k))
    for g in range(G):
        idx = np.flatnonzero(inv == g)
        Xg, wg = X[idx], w[idx]
        Dg, eg = D[:, idx], e[:, idx]
        XX_g[g] = Xg.T @ (wg[:, None] * Xg)
        M_g[g] = XX_g[g] - f * np.einsum("rnj,n,rnl->jl", Dg, wg, Dg)
        r_g[g] = Xg.T @ (wg * y[idx]) - f * np.einsum("rnj,n,rn->j", Dg, wg, eg)
    M, r, XX = M_g.sum(axis=0), r_g.sum(axis=0), XX_g.sum(axis=0)
    present = np.zeros((G, k))
    np.add.at(present, inv, (X != 0).astype(float))
    total_nz = present.sum(axis=0)
    const = np.all(X == 1, axis=0)
    indicator = np.all((X == 0) | (X == 1), axis=0) & ~const

    def full_rank(cols: np.ndarray, g: int) -> bool:
        A = (XX - XX_g[g])[np.ix_(cols, cols)]
        d = np.sqrt(np.clip(np.diag(A), 1e-300, None))
        return float(np.linalg.eigvalsh(A / np.outer(d, d))[0]) > 1e-10

    B = np.full((G, k), np.nan)
    for g in range(G):
        keep = (total_nz - present[g]) > 0
        report = keep.copy()
        if not full_rank(np.flatnonzero(keep), g) and const.any():
            # deleting the reference cluster of cluster fixed effects leaves the intercept collinear with the
            # remaining dummies: drop the intercept; the dummies then measure levels, not contrasts, so neither
            # they nor the intercept enter this refit's jackknife (the other terms are unaffected)
            keep &= ~const
            report = keep & ~indicator
        if not full_rank(np.flatnonzero(keep), g):
            continue  # not identified without this cluster: the refit is left out
        Mk = (M - M_g[g])[np.ix_(keep, keep)]
        try:
            sol = np.linalg.solve(Mk, (r - r_g[g])[keep])
        except np.linalg.LinAlgError:
            continue
        row = np.full(k, np.nan)
        row[keep] = sol
        B[g, report] = row[report]
    ok = np.isfinite(B)
    if not ok.any(axis=0).all():
        raise ValueError("fit_eiv jackknife: some term is not estimable in any delete-one-cluster refit")
    mean = np.nanmean(B, axis=0)
    dev = np.where(ok, B - mean, 0.0)
    cnt = ok.sum(axis=0).astype(float)
    V = dev.T @ dev
    scale = np.sqrt((cnt - 1) / cnt)
    return V * np.outer(scale, scale)


def cluster_labels(data: pd.DataFrame, cluster: str) -> np.ndarray:
    """Cluster labels from a column, or from a GEOID prefix written ``GEOID.str[:N]``."""
    m = CLUSTER_PREFIX_RE.match(str(cluster))
    if m:
        return data["GEOID"].astype(str).str[: int(m.group(1))].to_numpy()
    if cluster not in data.columns:
        raise ValueError(f"cluster {cluster!r} is neither a frame column nor GEOID.str[:N]")
    return data[cluster].astype(str).to_numpy()


def fit_eiv(
    formula: str,
    frame: pd.DataFrame,
    replicates: Optional[pd.DataFrame] = None,
    model: str = "ols",
    weights: Optional[str] = None,
    confidence_level: float = 0.90,
    cv_threshold: float = DEFAULT_CV_THRESHOLD,
    replicate_policy: str = "flag",
    cluster: Optional[str] = None,
    fixed_variables: Sequence[str] = (),
    cluster_se: str = "cr1",
    spatial_se: Optional[Mapping] = None,
    coords: Optional[pd.DataFrame] = None,
    spatial_clusters: Optional[Mapping] = None,
) -> ModelResult:
    """Least squares corrected for ACS sampling error in covariates and outcome (PLAN_ROUND_20 A2).

    With x_i the design row of unit i from the estimates, x_i^(r) the same row from replicate r
    and y likewise, the per-unit error covariances are estimated from the replicates (the VRE
    successive-difference formula):

        S_i = 4/80 sum_r (x_i^(r) - x_i)(x_i^(r) - x_i)',   s_i = 4/80 sum_r (x_i^(r) - x_i)(y_i^(r) - y_i)

    and the coefficients are Fuller's moment estimator with known heteroscedastic error
    covariance (Fuller 1987, Measurement Error Models, sections 2.2 and 3.1):

        b = (sum w_i x_i x_i' - sum w_i S_i)^-1 (sum w_i x_i y_i - sum w_i s_i).

    Unlike regression_calibration, it removes the bias from the correlation between the
    outcome's and the covariates' sampling errors (s_i), which arises when both are estimated
    from the same ACS sample, and it handles transformed and interaction columns (their error
    comes from their own replicate design rows). Error-free columns (constant, factors) have
    S_i = 0.

    Variance: sandwich M^-1 (sum psi_i psi_i') M^-1 * n/(n-k), psi_i = w_i [x_i (y_i - x_i'b) -
    (s_i - S_i b)], M = sum w_i x_i x_i' - sum w_i S_i, units independent (tract sampling errors
    are nearly uncorrelated between neighbours, Round 16). It covers model and sampling error:
    reported as se_total, the basis of intervals and p-values; se_model is the naive fit's
    model SE and the naive (uncorrected) coefficients are reported alongside.

    ``model``: "ols", or "wls" with an error-free ``weights`` column. Needs ``replicates`` (the
    long frame of census.analysis.attach_replicates) for every stochastic formula variable;
    ``replicate_policy`` as in fit_replicate ("strict" refuses rows or variables without them).
    Refuses a fit whose corrected moment matrix is not positive definite; notes covariates whose
    reliability is below 0.5, where moment corrections become unstable.

    ``cluster``: a column naming groups (e.g. county) whose units may be correlated (spatially
    autocorrelated model errors); the sandwich then sums psi within clusters, with the
    G/(G-1) * (n-1)/(n-k) small-sample factor. Needs at least 20 clusters. ``GEOID.str[:N]``
    (e.g. ``GEOID.str[:5]``, counties of tracts) clusters by a GEOID prefix without a column.
    Validated by simulation in docs/audits/eiv_cluster_validation.md (PLAN_ROUND_21 B1).
    ``cluster_se="jackknife"`` uses the delete-one-cluster jackknife (CR3) instead:
    V = (G-1)/G sum_g (b_(g) - mean b_(g))(...)', each b_(g) the moment estimator from the
    other clusters' sums (exact; the error covariances are not re-estimated). A term whose
    column is all zero without cluster g (that cluster's own fixed effect) is left out of
    that refit, and its variance uses the other refits. Less anti-conservative than CR1 with
    few or unequal clusters (PLAN_ROUND_21 Part 2, C5).

    ``fixed_variables``: variables whose error is independent of the ACS sampling error and
    which have no replicates (external outcomes, e.g. CDC PLACES; PLAN_ROUND_21 B3). They are
    held at their estimates in every replicate design row (zero deviation, so s_i has no term
    from them) and are not counted as missing replicates; as an outcome their error enters the
    residual, which the sandwich covers. Only the outcome may be fixed: a fixed covariate's
    error would go uncorrected.
    """
    if spatial_clusters is not None:
        from .spatial_clusters import check_config
        check_config(spatial_clusters)
        if (spatial_clusters != {'k':8,'method':'im'} or model.lower()!='ols' or weights is not None
                or cluster is not None or spatial_se is not None or cluster_se != 'cr1'):
            raise ValueError("IM EIV requires unweighted OLS, k=8/method=im, and refuses cluster, cluster_se and spatial_se")
        raise ValueError("IM EIV C2 failed validation and is refused; docs/audits/im_acs_validation.md")
    from .splines import has_spline
    if has_spline(formula):
        raise ValueError("cr splines are supported only by non-spatial fit_replicate")
    import scipy.linalg as sla

    if spatial_se is not None and cluster:
        raise ValueError("spatial_se and cluster are mutually exclusive")
    if spatial_se is not None and coords is None:
        raise ValueError("spatial_se requires coords")
    model = model.lower()
    check_replicate_policy(replicate_policy)
    if cluster_se not in ("cr1", "jackknife"):
        raise ValueError("cluster_se must be 'cr1' or 'jackknife'")
    if cluster_se == "jackknife" and not cluster:
        raise ValueError("cluster_se='jackknife' needs cluster")
    if model not in EIV_MODELS:
        raise ValueError(f"fit_eiv supports models {EIV_MODELS}; got {model!r}")
    if model == "wls" and not weights:
        raise ValueError("model='wls' needs weights=<column>")
    if replicates is None or not len(replicates):
        raise ValueError("fit_eiv needs replicates (the error covariances come from them)")
    data, _, notes = _prepare(frame, formula, model, weights if model == "wls" else None, None, None)
    used = formula_variables(formula, data)
    if weights and model == "wls":
        if weights in set(replicates["variable"].astype(str)) or weights in used:
            raise ValueError(f"weights column {weights!r} must be error-free (not a replicated or formula variable)")
    declared = [v for v in used if v in set(fixed_variables)]
    if declared:
        outcome_vars = set(formula_variables(formula.split("~")[0] + "~ 1", data))
        bad_fixed = [v for v in declared if v not in outcome_vars]
        if bad_fixed:
            raise ValueError(f"fixed_variables {bad_fixed} are covariates; only the outcome may be held fixed (a "
                             "covariate's error would go uncorrected)")
    mats, fixed = _replicate_matrices(data, replicates, [v for v in used if v not in declared])
    if not mats:
        raise ValueError("no formula variable has replicates in the replicate frame")
    missing = [v for v in used if v not in mats and v not in declared]
    stoch_missing = stochastic_variables(frame, missing)
    precheck_replicates(replicate_policy, rows_held_fixed=fixed, variables_without_replicates=stoch_missing,
                        context="fit_eiv")
    diagnostics: Dict[str, Any] = {"reliability_screen": _screen_summary(data, formula, cv_threshold)}
    replicate_completeness(replicate_policy, rows_held_fixed=fixed, variables_without_replicates=stoch_missing,
                           context="fit_eiv", diagnostics=diagnostics, notes=notes)

    y, X_df, D, e, rows = _design_deviations(formula, data, mats)
    used_data = data.loc[rows].reset_index(drop=True)
    with np.errstate(invalid="ignore"):
        bad = ~(np.isfinite(D).all(axis=(0, 2)) & np.isfinite(e).all(axis=0))
    if bad.any():
        # a transform undefined on some replicate (e.g. log of a replicate 0): those units' error
        # covariance is undefined; strict refuses, flag drops them and records it
        replicate_completeness(replicate_policy, rows_held_fixed={"undefined transformed replicate": int(bad.sum())},
                               context="fit_eiv", diagnostics=diagnostics, notes=notes,
                               rows_label="units dropped (a formula term is undefined on some replicate)")
        keep = ~bad
        y, D, e = y[keep], D[:, keep], e[:, keep]
        X_df = X_df.iloc[np.flatnonzero(keep)]
        used_data = used_data.loc[keep].reset_index(drop=True)
    n, k = X_df.shape
    if n <= k:
        raise ValueError(f"fit_eiv: {n} rows for {k} coefficients")
    w = used_data[weights].to_numpy(float) if model == "wls" else np.ones(n)
    if not (np.isfinite(w).all() and (w >= 0).all()):
        raise ValueError("weights must be non-negative and finite")
    if (w == 0).any():  # zero weight = the unit does not enter the weighted fit (as in WLS)
        keep = w > 0
        notes.append(f"{int((~keep).sum())} unit(s) with weight 0 left out of the weighted fit")
        y, D, e, w = y[keep], D[:, keep], e[:, keep], w[keep]
        X_df = X_df.iloc[np.flatnonzero(keep)]
        used_data = used_data.loc[keep].reset_index(drop=True)
        n = len(y)
        if n <= k:
            raise ValueError(f"fit_eiv: {n} rows with positive weight for {k} coefficients")
    X = X_df.to_numpy(float)
    terms = list(X_df.columns)
    f = REPLICATE_FACTOR
    S_sum = f * np.einsum("rnj,n,rnl->jl", D, w, D)        # sum_i w_i S_i
    s_sum = f * np.einsum("rnj,n,rn->j", D, w, e)          # sum_i w_i s_i
    XtWX = X.T @ (w[:, None] * X)
    M = XtWX - S_sum
    try:
        rel_eig = float(sla.eigh(M, XtWX, eigvals_only=True)[0])
    except (np.linalg.LinAlgError, ValueError) as exc:
        raise ValueError(f"fit_eiv: design matrix is singular ({exc})") from exc
    if not rel_eig > 0:
        raise ValueError("fit_eiv: the corrected moment matrix X'WX - sum S_i is not positive definite "
                         f"(smallest relative eigenvalue {rel_eig:.3g}): the covariates' sampling error is as large as "
                         "their spread; the correction is not identified for this model")
    b = np.linalg.solve(M, X.T @ (w * y) - s_sum)
    resid = y - X @ b
    s_i = f * np.einsum("rnj,rn->nj", D, e)                 # (n, k)
    Sb_i = f * np.einsum("rnj,rn->nj", D, D @ b)            # (n, k): S_i b
    psi = w[:, None] * (X * resid[:, None] - (s_i - Sb_i))
    Minv = np.linalg.inv(M)
    if cluster:
        groups = cluster_labels(used_data, cluster)
        codes, inv = np.unique(groups, return_inverse=True)
        G = len(codes)
        if G < 20:
            raise ValueError(f"cluster {cluster!r} has {G} groups; the clustered sandwich needs at least 20")
        psi_g = np.zeros((G, k))
        np.add.at(psi_g, inv, psi)
        V = Minv @ (psi_g.T @ psi_g) @ Minv * (G / (G - 1)) * ((n - 1) / (n - k))
        V_ind = Minv @ (psi.T @ psi) @ Minv * n / (n - k)
        diagnostics["clusters"] = {"column": cluster, "groups": int(G), "se": cluster_se}
        if cluster_se == "jackknife":
            diagnostics["se_total_cr1"] = dict(zip(map(str, X_df.columns),
                                                   map(float, np.sqrt(np.maximum(np.diag(V), 0.0)))))
            V = _cluster_jackknife(X, y, w, D, e, inv, G, f)
        diagnostics["se_total_independent"] = dict(zip(map(str, X_df.columns),
                                                       map(float, np.sqrt(np.maximum(np.diag(V_ind), 0.0)))))
        notes.append(f"se_total clustered by {cluster!r} ({G} clusters, "
                     + ("delete-one-cluster jackknife" if cluster_se == "jackknife" else "CR1") + ")")
    else:
        V = Minv @ (psi.T @ psi) @ Minv * n / (n - k)
    if spatial_se is not None:
        from .spatial_hac import conley_covariance, coordinate_distances
        diagnostics["se_independent"] = dict(zip(terms, map(float, np.sqrt(np.diag(V)))))
        V, info = conley_covariance(psi, Minv, coordinate_distances(used_data, coords), spatial_se["cutoff_km"])
        diagnostics["spatial_se"] = info
        notes.append(f"Spatial HAC (Conley) SEs, Bartlett kernel, cutoff {spatial_se['cutoff_km']} km")
    se_total = pd.Series(np.sqrt(np.maximum(np.diag(V), 0.0)), index=terms)

    naive = _fit(formula, used_data, model, weights if model == "wls" else None, None, None)
    noisy = [j for j in range(k) if np.any(D[:, :, j] != 0)]
    clean = [j for j in range(k) if j not in noisy]
    reliability: Dict[str, float] = {}
    for j in noisy:
        xj = X[:, j]
        if clean:
            Z = X[:, clean]
            coef, *_ = np.linalg.lstsq(Z * np.sqrt(w)[:, None], xj * np.sqrt(w), rcond=None)
            xj = xj - Z @ coef
        var_obs = float(np.sum(w * xj**2) / np.sum(w))
        err = float(f * np.einsum("rn,n,rn->", D[:, :, j], w, D[:, :, j]) / np.sum(w))
        reliability[terms[j]] = 1.0 - err / var_obs if var_obs > 0 else float("nan")
    err_corr: Dict[str, float] = {}
    var_y = f * np.einsum("rn,rn->n", e, e)
    for j in noisy:
        var_x = f * np.einsum("rn,rn->n", D[:, :, j], D[:, :, j])
        den = np.sqrt(np.mean(var_x) * np.mean(var_y))
        err_corr[terms[j]] = float(np.mean(s_i[:, j]) / den) if den > 0 else float("nan")
    diagnostics.update({
        "reliability": reliability,
        "outcome_error_correlation": err_corr,
        "smallest_relative_eigenvalue": rel_eig,
        "error_covariance_from": "replicates (4/80 sum over 80 replicates)",
        "noisy_terms": [terms[j] for j in noisy],
    })
    low = [t for t, r in reliability.items() if np.isfinite(r) and r < EIV_LOW_RELIABILITY]
    if low:
        notes.append(f"LOW RELIABILITY: {low} have reliability below {EIV_LOW_RELIABILITY}; moment corrections are "
                     "unstable there (large variance, possible sign changes)")
    if declared:
        diagnostics["replicates_declared_fixed"] = declared
        notes.append(f"{declared} held fixed in the replicate design rows (declared: error independent of the ACS "
                     "sampling error, no replicates); their error enters the residual and the sandwich")
    notes.append("fit_eiv: moment-corrected least squares (Fuller 1987) with per-unit error covariances, including "
                 "the outcome-covariate error covariance, from the ACS replicates; sandwich se_total ("
                 + (f"clustered by {cluster!r}" if cluster else "units independent")
                 + ") is the basis of intervals and p-values")
    res = _corrected_result(formula, model, naive, pd.Series(b, index=terms), se_total, confidence_level,
                            "fit_eiv", notes, diagnostics, int(n))
    res.uncertainty_sources = [SOURCE_MODEL, SOURCE_SAMPLING_REPLICATE]
    res.provenance = {**(res.provenance or {}), "replicate_variables": sorted(mats), "rows_used": int(n)}
    return res


def simex(
    formula: str,
    frame: pd.DataFrame,
    error_covariates: Union[Sequence[str], Mapping[str, str]],
    model: str = "ols",
    weights: Optional[str] = None,
    exposure: Optional[str] = None,
    trials: Optional[str] = None,
    confidence_level: float = 0.90,
    lambdas: Sequence[float] = (0.5, 1.0, 1.5, 2.0),
    n_sim: int = 100,
    extrapolation: str = "quadratic",
    seed: Optional[int] = 0,
    cv_threshold: float = DEFAULT_CV_THRESHOLD,
) -> ModelResult:
    """SIMEX for covariates with known (heteroscedastic) sampling SEs.

    NOT VALIDATED as a default: in docs/audits/inference_validation.md, quadratic
    SIMEX under-corrects attenuation and its 90% intervals covered 0.81 at
    covariate reliability 0.71 (0.29 at reliability 0.38). Prefer
    :func:`regression_calibration` (coverage 0.89, bias removed). Results
    carry a note saying so.

    For each lambda, ``n_sim`` data sets W + sqrt(lambda) * s_i * Z (Z ~ N(0,1))
    are refit; mean coefficients are extrapolated (``quadratic`` or
    ``linear`` in lambda, through lambda = 0, the naive fit) to lambda = -1
    (Cook & Stefanski 1994; heteroscedastic form Devanarayan & Stefanski
    2002). Variance: tau^2(lambda) = mean model variance - between-simulation
    variance, extrapolated to -1 (Stefanski & Cook 1995). Quadratic
    extrapolation is approximate and typically leaves some residual
    attenuation when reliability is low.
    """
    model, spec, data, n_trials, notes, _ = _setup(formula, frame, error_covariates, model, weights, exposure, trials)
    if extrapolation not in ("quadratic", "linear"):
        raise ValueError("extrapolation must be 'quadratic' or 'linear'")
    naive = _fit(formula, data, model, weights, exposure, n_trials)
    terms = naive.params.index
    rng = np.random.default_rng(seed)
    lam = [0.0] + [float(x) for x in lambdas]
    means = [naive.params.to_numpy(float)]
    taus = [naive.bse.to_numpy(float) ** 2]
    failed = 0
    for lv in lambdas:
        bs, vs = [], []
        for _ in range(n_sim):
            d = data.copy()
            for w, s in spec.items():
                d[w] = d[w].to_numpy(float) + math.sqrt(lv) * d[s].to_numpy(float) * rng.standard_normal(len(d))
            try:
                res = _fit(formula, d, model, weights, exposure, n_trials)
                bs.append(res.params.reindex(terms).to_numpy(float))
                vs.append(res.bse.reindex(terms).to_numpy(float) ** 2)
            except Exception:  # noqa: BLE001
                failed += 1
        bs_arr = np.vstack(bs)
        means.append(bs_arr.mean(axis=0))
        taus.append(np.vstack(vs).mean(axis=0) - bs_arr.var(axis=0, ddof=1))
    deg = 2 if extrapolation == "quadratic" else 1
    lam_a = np.asarray(lam)
    M, T = np.vstack(means), np.vstack(taus)
    est = np.array([np.polyval(np.polyfit(lam_a, M[:, j], deg), -1.0) for j in range(M.shape[1])])
    var = np.array([np.polyval(np.polyfit(lam_a, T[:, j], deg), -1.0) for j in range(T.shape[1])])
    if (var <= 0).any():
        notes.append("extrapolated SIMEX variance non-positive for some terms; se_total set to NaN there")
    se_total = pd.Series(np.sqrt(np.where(var > 0, var, np.nan)), index=terms)
    diagnostics = {"reliability_screen": _screen_summary(data, formula, cv_threshold),
                   "simex_path": pd.DataFrame(M, columns=list(terms)).assign(**{"lambda": lam_a}),
                   "failed_simulations": failed}
    notes = notes + [f"SIMEX ({extrapolation} extrapolation, lambdas {lam}, {n_sim} simulations each) for "
                     f"{list(spec)}", FH_POINTER,
                     "SIMEX is not validated for confirmatory use: simulated 90% interval coverage was 0.81 "
                     "(docs/audits/inference_validation.md); prefer regression_calibration"]
    return _corrected_result(formula, model, naive, pd.Series(est, index=terms), se_total, confidence_level,
                             "simex", notes, diagnostics, int(naive.nobs))
