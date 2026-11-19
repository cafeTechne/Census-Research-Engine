# SPDX-License-Identifier: AGPL-3.0-or-later
"""Descriptive model diagnostics for OLS fits (Round 33). Information only, never a gate."""
from typing import Any, Dict

import numpy as np
from scipy import stats


def model_diagnostics(fit, geoids=None) -> Dict[str, Any]:
    """VIFs, Cook's distance (five largest), Breusch-Pagan and RESET p-values, residual skewness.

    ``fit`` is a census.models.fit_replicate OLS result (uses its ``joint_inputs``).
    """
    import statsmodels.api as sm
    from statsmodels.stats.diagnostic import het_breuschpagan, linear_reset
    from statsmodels.stats.outliers_influence import OLSInfluence, variance_inflation_factor
    inputs = getattr(fit, "joint_inputs", None)
    if inputs is None or fit.model_type != "ols":
        return {"note": "diagnostics are computed for OLS fits from census.models.fit_replicate"}
    X, y, names = inputs["X"], inputs["y"], inputs["column_names"]
    ols = sm.OLS(y, X).fit()
    out: Dict[str, Any] = {"note": "information only, never a gate; they describe the model on the observed estimates"}
    if X.shape[1] > 2:
        out["vif"] = {names[j]: float(variance_inflation_factor(X, j)) for j in range(X.shape[1]) if names[j] != "Intercept"}
    cooks = OLSInfluence(ols).cooks_distance[0]
    top = np.argsort(cooks)[::-1][:5]
    geoids = geoids if geoids is not None else inputs.get("geoids")
    labels = list(geoids) if geoids is not None and len(geoids) == len(y) else list(range(len(y)))
    out["cooks_distance_top5"] = [{"unit": str(labels[i]), "cooks_d": float(cooks[i])} for i in top]
    out["breusch_pagan_p"] = float(het_breuschpagan(ols.resid, X)[1])
    try:
        out["reset_p"] = float(linear_reset(ols, power=2, use_f=True).pvalue)
    except (ValueError, np.linalg.LinAlgError):
        out["reset_p"] = None
    out["residual_skewness"] = float(stats.skew(ols.resid))
    return out
