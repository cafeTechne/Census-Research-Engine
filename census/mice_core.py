# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 100 frozen core: multiple imputation by fully conditional specification (backlog N77; van Buuren, *Flexible
Imputation of Missing Data*, 2012, chapters 2-7; Rubin 1987; Barnard and Rubin 1999; Little 1988).

Data: a numeric matrix with NaN for missing values. Each incomplete column is imputed in turn (visit sequence: from
least to most missing) from all other columns, for ``cycles`` iterations, in each of ``m`` independent chains.
- "norm": Bayesian linear regression - sigma*^2 = RSS / chi^2_(n_obs - p), beta* ~ N(beta_hat, sigma*^2 (X'X)^-1),
  imputations X_mis beta* + N(0, sigma*^2).
- "pmm": predictive mean matching (type 1): predictions X_obs beta_hat for observed rows and X_mis beta* for missing
  rows; each missing value takes the observed value of one of the 5 closest donors at random. Imputed values are
  always observed values (bounds and skew kept).
- Start: missing entries filled with random draws of the column's observed values.
- Passive variables: functions recomputing derived columns from the current data after every update.
- delta adjustment (MNAR sensitivity): a constant added to a declared column's imputations at every step.
Pooling (Rubin's rules): Qbar, Ubar, B, T = Ubar + (1 + 1/m) B; lambda = (1 + 1/m) B / T; Barnard-Rubin
df nu = nu_old nu_obs / (nu_old + nu_obs), nu_old = (m - 1) / lambda^2, nu_obs = (nu_com + 1)/(nu_com + 3) nu_com
(1 - lambda); FMI = (r + 2/(nu + 3)) / (r + 1), r = (1 + 1/m) B / Ubar.
"""
from typing import Callable, Dict, List, Mapping, Optional, Sequence

import numpy as np
from scipy import stats

DONORS = 5


def _impute_column(Z, j, miss, method, rng, delta=0.0):
    obs = ~miss
    X = np.column_stack([np.ones(len(Z)), np.delete(Z, j, axis=1)])
    Xo, yo = X[obs], Z[obs, j]
    XtX = Xo.T @ Xo
    XtXi = np.linalg.pinv(XtX)
    bhat = XtXi @ Xo.T @ yo
    rss = float(np.sum((yo-Xo @ bhat)**2))
    df = max(int(obs.sum())-X.shape[1], 1)
    s2 = rss/rng.chisquare(df)
    L = np.linalg.cholesky(XtXi*s2+1e-12*np.eye(len(bhat)))
    bstar = bhat+L @ rng.standard_normal(len(bhat))
    if method == "norm":
        vals = X[miss] @ bstar+rng.normal(0, np.sqrt(s2), miss.sum())
    elif method == "pmm":
        po = Xo @ bhat; pm = X[miss] @ bstar
        d = np.abs(pm[:, None]-po[None, :])
        k = min(DONORS, len(po))
        near = np.argpartition(d, k-1, axis=1)[:, :k]
        pick = near[np.arange(len(pm)), rng.integers(0, k, len(pm))]
        vals = yo[pick]
    else:
        raise ValueError("method must be 'pmm' or 'norm'")
    Z[miss, j] = vals+delta


def mice(data, methods: Mapping[int, str], m: int = 20, cycles: int = 10, rng=None,
         passive: Optional[Mapping[int, Callable[[np.ndarray], np.ndarray]]] = None,
         delta: Optional[Mapping[int, float]] = None) -> List[np.ndarray]:
    """``methods``: {column: "pmm" | "norm"} for every incomplete, non-passive column. Returns m completed copies."""
    D = np.asarray(data, float)
    rng = rng or np.random.default_rng(0)
    passive = dict(passive or {}); delta = dict(delta or {})
    M = np.isnan(D)
    cols = [j for j in np.argsort(M.sum(0)) if M[:, j].any() and j not in passive]
    missing = [j for j in cols if j not in methods]
    if missing:
        raise ValueError(f"no imputation method for incomplete columns {missing}")
    out = []
    for _ in range(m):
        Z = D.copy()
        for j in cols:
            obs = Z[~M[:, j], j]
            Z[M[:, j], j] = rng.choice(obs, M[:, j].sum())
        for j, f in passive.items():
            Z[:, j] = f(Z)
        for _ in range(cycles):
            for j in cols:
                _impute_column(Z, j, M[:, j], methods[j], rng, delta.get(j, 0.0))
                for k, f in passive.items():
                    Z[:, k] = f(Z)
        out.append(Z)
    return out


def pool(estimates: Sequence[np.ndarray], variances: Sequence[np.ndarray], df_complete: float, level: float = .90
         ) -> Dict[str, np.ndarray]:
    Q = np.asarray(estimates, float); U = np.asarray(variances, float); m = len(Q)
    qbar = Q.mean(0); ubar = U.mean(0); B = Q.var(0, ddof=1)
    T = ubar+(1+1/m)*B
    lam = np.clip((1+1/m)*B/T, 1e-12, 1-1e-12)
    nu_old = (m-1)/lam**2
    nu_obs = (df_complete+1)/(df_complete+3)*df_complete*(1-lam)
    nu = nu_old*nu_obs/(nu_old+nu_obs)
    r = (1+1/m)*B/ubar
    fmi = (r+2/(nu+3))/(r+1)
    se = np.sqrt(T); t = stats.t.ppf(.5+level/2, nu)
    return dict(estimate=qbar, se=se, lower=qbar-t*se, upper=qbar+t*se, df=nu, lambda_=lam, fmi=fmi, m=m)


def ols(Z, y_col: int, x_cols: Sequence[int]):
    X = np.column_stack([np.ones(len(Z)), Z[:, list(x_cols)]]); y = Z[:, y_col]
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y-X @ b; n, p = X.shape
    V = np.linalg.inv(X.T @ X)*float(r @ r)/(n-p)
    return b, np.diag(V), n-p
