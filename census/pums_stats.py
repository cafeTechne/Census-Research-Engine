# SPDX-License-Identifier: AGPL-3.0-or-later
"""PUMS regression and PUMA geography helpers (extracted from census/pums.py in Round 181)."""
from census.pums import (  # noqa: F401
    Any,
    Dict,
    List,
    ModelResult,
    Optional,
    PUMS_DOCS_BASE,
    PUMS_MODELS,
    REPLICATE_COUNT,
    REPLICATE_FACTOR,
    SOURCE_MODEL,
    SOURCE_SAMPLING_REPLICATE,
    Union,
    _mask,
    _product,
    _weight_matrix,
    cached_download,
    check_refit_count,
    check_replicate_policy,
    np,
    pd,
    re,
    replicate_completeness,
    state_fips,
)



def _irls(X: np.ndarray, y: np.ndarray, w: np.ndarray, model: str, start: Optional[np.ndarray] = None,
          max_iter: int = 100, tol: float = 1e-10) -> np.ndarray:
    """Weighted ML by Newton/IRLS; weights may be negative (some replicate weights are)."""
    if model == "ols":
        A = X.T @ (X * w[:, None])
        return np.linalg.solve(A, X.T @ (w * y))
    b = np.zeros(X.shape[1]) if start is None else start.copy()
    for _ in range(max_iter):
        eta = np.clip(X @ b, -30, 30)
        if model == "logit":
            mu = 1.0 / (1.0 + np.exp(-eta))
            v = mu * (1 - mu)
        else:
            mu = np.exp(eta)
            v = mu
        grad = X.T @ (w * (y - mu))
        H = X.T @ (X * (w * v)[:, None])
        step = np.linalg.solve(H, grad)
        b = b + step
        if np.max(np.abs(step)) < tol * (1 + np.max(np.abs(b))):
            return b
    raise RuntimeError("IRLS did not converge")


def _sandwich(X: np.ndarray, y: np.ndarray, w: np.ndarray, b: np.ndarray, model: str) -> np.ndarray:
    eta = X @ b
    if model == "ols":
        mu, v = eta, np.ones_like(eta)
    elif model == "logit":
        mu = 1.0 / (1.0 + np.exp(-eta))
        v = mu * (1 - mu)
    else:
        mu = np.exp(eta)
        v = mu
    bread = np.linalg.inv(X.T @ (X * (w * v)[:, None]))
    s = X * (w * (y - mu))[:, None]
    n, k = X.shape
    meat = s.T @ s * (n / max(n - k, 1))
    return np.sqrt(np.diag(bread @ meat @ bread))


def pums_regression(
    formula: str,
    df: pd.DataFrame,
    weight: str = "person",
    model: str = "ols",
    where: Any = None,
    target: str = "these_areas",
    confidence_level: float = 0.90,
    replicate_policy: str = "flag",
    max_failed_replicates: int = 0,
) -> ModelResult:
    """Survey-weighted regression on PUMS with replicate-weight SEs.

    The model (``ols`` = weighted least squares, ``logit``, ``poisson``) is
    fit with the full weight and refit with each of the 80 replicate weights;
    ``se_sampling = sqrt(4/80 * sum_r (b_r - b)^2)`` (the PUMS replicate
    formula). ``se_model`` is the weighted sandwich (HC1) SE, which treats
    records as independent and ignores the PUMS design (household clustering,
    replicate structure); it is reported for comparison.

    Interval targets (census.models.INTERVAL_TARGETS): the default
    ``"these_areas"`` uses se_sampling, the design-based SE for the population
    the PUMS represents (Census's documented method for PUMS); ``"population"``
    uses se_model; ``"conservative"`` uses sqrt(se_model^2 + se_sampling^2).

    ``replicate_policy`` (census.results.replicate_completeness, PLAN_ROUND_11
    Q2/D7): a replicate refit fails when IRLS does not converge, the system is
    singular, or a replicate weight is missing (non-finite) for a modelled
    record. "flag" (default) omits up to ``max_failed_replicates`` (default
    0, as in census.models.fit_replicate) failed refits from se_sampling and
    records diagnostics["replicates_incomplete"]; more failures raise
    RuntimeError. "strict" raises IncompleteReplicatesError (a ValueError) on
    any failure. If every refit fails, RuntimeError (flag) or
    IncompleteReplicatesError (strict) is raised.
    """
    import patsy

    from .models import INTERVAL_TARGETS, _table

    model = model.lower()
    check_replicate_policy(replicate_policy)
    if model not in PUMS_MODELS:
        raise ValueError(f"model must be one of {PUMS_MODELS}")
    if target not in INTERVAL_TARGETS:
        raise ValueError(f"target must be one of {INTERVAL_TARGETS}")
    # Positional index: concatenated multi-state frames repeat row labels,
    # which would make the label lookup below ambiguous.
    sub = df.loc[_mask(df, where)].reset_index(drop=True)
    base, W = _weight_matrix(sub, weight)
    y_df, X_df = patsy.dmatrices(formula, sub, return_type="dataframe", NA_action="drop")
    pos = sub.index.get_indexer(X_df.index)
    W = W[pos]
    X, y = X_df.to_numpy(float), y_df.iloc[:, 0].to_numpy(float)
    if model == "logit" and not np.isin(y, (0.0, 1.0)).all():
        raise ValueError("logit outcome must be 0/1")
    b0 = _irls(X, y, W[:, 0], model)
    coefs, failed = [], 0
    for r in range(1, REPLICATE_COUNT + 1):
        try:
            if not np.isfinite(W[:, r]).all():
                raise ValueError("non-finite replicate weight")
            b = _irls(X, y, W[:, r], model, start=b0)
            if not np.isfinite(b).all():
                raise ValueError("non-finite coefficients")
            coefs.append(b)
        except (np.linalg.LinAlgError, RuntimeError, ValueError):
            failed += 1
    notes: List[str] = []
    diagnostics: Dict[str, Any] = {}
    replicate_completeness(replicate_policy, failed_refits=failed, context="pums_regression",
                           diagnostics=diagnostics, notes=notes)
    check_refit_count(failed, len(coefs), max_failed_replicates, "pums_regression")
    B = np.vstack(coefs)
    se_samp = np.sqrt(REPLICATE_FACTOR * ((B - b0) ** 2).sum(axis=0))
    se_mod = _sandwich(X, y, W[:, 0], b0, model)
    terms = list(X_df.columns)
    table = _table(pd.Series(b0, index=terms), pd.Series(se_mod, index=terms),
                   pd.Series(se_samp, index=terms), confidence_level, target)
    notes = notes + [
        "se_sampling: refit with each of the 80 replicate weights, Var = 4/80 * sum_r (b_r - b)^2",
        "se_model: weighted sandwich (HC1) SE ignoring the PUMS design; for comparison only",
        f"intervals and p-values use the '{target}' target",
    ]
    dropped = len(sub) - len(X_df)
    if dropped:
        notes.append(f"{dropped} record(s) dropped for missing formula variables")
    diagnostics.update({
        "interval_target": target, "weight": base, "n_unweighted": int(len(X_df)),
        "weighted_n": float(W[:, 0].sum()),
        "replicate_stability": {t: {"sd": float(B[:, j].std(ddof=1)),
                                    "share_same_sign": float(np.mean(np.sign(B[:, j]) == np.sign(b0[j])))}
                                for j, t in enumerate(terms)},
    })
    provenance = {k: v for k, v in df.attrs.items() if isinstance(v, (str, int, float, bool))}
    provenance["model_library"] = "numpy IRLS (census.pums)"
    return ModelResult(model_type=f"pums_{model}", formula=formula, n_obs=int(len(X_df)), coefficients=table,
                       method="pums_replicate_weight_refit",
                       uncertainty_sources=[SOURCE_MODEL, SOURCE_SAMPLING_REPLICATE],
                       confidence_level=confidence_level, notes=notes, diagnostics=diagnostics,
                       provenance=provenance)


# --------------------------------------------------------------------------- PUMA geography

PUMA_TRACT_RELATIONSHIP_URLS = {
    2010: "https://www2.census.gov/geo/docs/maps-data/data/rel/2010_Census_Tract_to_2010_PUMA.txt",
    2020: "https://www2.census.gov/geo/docs/maps-data/data/rel2020/2020_Census_Tract_to_2020_PUMA.txt",
}


PUMS_DATA_DICTIONARY_PUMA_SOURCES = (
    # Verified 2026-11: PUMA columns in the official CSV data dictionaries.
    f"{PUMS_DOCS_BASE}/data_dict/PUMS_Data_Dictionary_2017-2021.csv",  # PUMA, 2010 definition
    f"{PUMS_DOCS_BASE}/data_dict/PUMS_Data_Dictionary_2018-2022.csv",  # PUMA10 + PUMA20, -0009 = N/A
    f"{PUMS_DOCS_BASE}/data_dict/PUMS_Data_Dictionary_2019-2023.csv",  # PUMA, 2020 definition
    f"{PUMS_DOCS_BASE}/data_dict/PUMS_Data_Dictionary_2020-2024.csv",  # PUMA, 2020 definition
    f"{PUMS_DOCS_BASE}/data_dict/PUMS_Data_Dictionary_2021.csv",       # 1-year: PUMA, 2010
    f"{PUMS_DOCS_BASE}/data_dict/PUMS_Data_Dictionary_2022.csv",       # 1-year: PUMA, 2020
)
PUMA_NOT_APPLICABLE = "-0009"


def puma_vintage(year: int, product: str = "5-year") -> int:
    """Census PUMA set (2000, 2010 or 2020) coded in a PUMS release.

    Per the official PUMS data dictionaries (``PUMS_DATA_DICTIONARY_PUMA_SOURCES``):

    * 1-year: 2010 PUMAs from 2012 through 2021, 2020 PUMAs from 2022.
    * 5-year: 2010 PUMAs for 2012-2016 through 2017-2021; one ``PUMA`` column
      on the 2020 definition for 2019-2023 and 2020-2024 (the 2019-2021 sample
      years are recoded to 2020 PUMAs).
    * Mixed releases raise ValueError: 2008-2012 through 2011-2015 carry
      PUMA00/PUMA10, and 2018-2022 carries PUMA10 (data years 2018-2021) and
      PUMA20 (data year 2022) with ``-0009`` (not applicable) in the other
      column, so no single PUMA vintage covers every record.
    """
    p, year = _product(product), int(year)
    if p == "1-year":
        if year >= 2022:
            return 2020
        return 2010 if year >= 2012 else 2000
    if year == 2022:
        raise ValueError("the 2018-2022 5-year PUMS mixes 2010 and 2020 PUMAs (PUMA10 for data years "
                         "2018-2021, PUMA20 for 2022; -0009 = not applicable): pick one column explicitly")
    if year >= 2023:
        return 2020
    if year >= 2016:
        return 2010
    if year <= 2011:
        return 2000
    raise ValueError(f"the {year - 4}-{year} 5-year PUMS mixes 2000 and 2010 PUMAs (PUMA00/PUMA10 columns)")


def puma_geoid(df: pd.DataFrame, puma: str = "PUMA", state: str = "STATE") -> pd.Series:
    """7-character PUMA GEOID (state FIPS + 5-digit PUMA), matching boundary files.

    Mixed-vintage files (2018-2022 5-year: PUMA10/PUMA20; 2008-2012 to 2011-2015:
    PUMA00/PUMA10) have no ``PUMA`` column: pass ``puma="PUMA20"`` (or another
    vintage column) explicitly. Records coded ``-0009`` (not applicable: the
    record's data year is outside that column's vintage) get a missing GEOID.
    """
    if puma not in df.columns:
        alts = [c for c in df.columns if re.fullmatch(r"PUMA\d\d", str(c))]
        if alts:
            raise ValueError(f"no {puma!r} column: this release mixes PUMA vintages ({', '.join(alts)}); "
                             "pass puma=<one of them>; records outside its vintage get a missing GEOID")
        raise KeyError(puma)
    st = df[state].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(2)
    raw = df[puma].astype(str).str.replace(r"\.0$", "", regex=True)
    pu = raw.str.zfill(5)
    na = df[puma].isna() | raw.str.startswith("-")
    return (st + pu).mask(na).rename("GEOID")


def add_puma_geoid(df: pd.DataFrame, puma: str = "PUMA", state: str = "STATE") -> pd.DataFrame:
    out = df.copy()
    out["GEOID"] = puma_geoid(df, puma, state)
    out.attrs.update(df.attrs)
    return out


def puma_boundaries(year: int, state: Optional[Union[str, int]] = None, product: str = "5-year",
                    detail: str = "cb", **kwargs: Any):
    """PUMA polygons matching a PUMS release (census.boundaries level 'puma')."""
    from .boundaries import boundary_vintage, get_boundaries

    _product(product)
    vintage = boundary_vintage(int(year), "puma", detail)
    return get_boundaries("puma", vintage, state_fips(state) if state is not None else None, detail, **kwargs)


def puma_tract_relationship(vintage: int, state: Optional[Union[str, int]] = None, *,
                            cache_dir: Optional[str] = None, refresh: bool = False,
                            session: Any = None) -> pd.DataFrame:
    """Census tract-to-PUMA relationship file (2010 or 2020) with tract and PUMA GEOIDs."""
    if int(vintage) not in PUMA_TRACT_RELATIONSHIP_URLS:
        raise ValueError(f"vintage must be one of {sorted(PUMA_TRACT_RELATIONSHIP_URLS)}")
    url = PUMA_TRACT_RELATIONSHIP_URLS[int(vintage)]
    path, meta = cached_download(url, "relationship", cache_dir=cache_dir, refresh=refresh, session=session)
    rel = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    rel.columns = [c.strip().upper() for c in rel.columns]
    pcol = next(c for c in rel.columns if c.startswith("PUMA"))
    rel["TRACT_GEOID"] = rel["STATEFP"] + rel["COUNTYFP"] + rel["TRACTCE"]
    rel["PUMA_GEOID"] = rel["STATEFP"] + rel[pcol]
    if state is not None:
        rel = rel[rel["STATEFP"] == state_fips(state)]
    rel = rel.reset_index(drop=True)
    rel.attrs.update(source_url=url, sha256=meta.get("sha256"), vintage=int(vintage))
    return rel
