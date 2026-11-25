# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 80: arcsine Fay-Herriot for proportions and Rao-Yu temporal Fay-Herriot."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from census import sae_extensions as sx, sae_extensions_core as core

ROOT = Path(__file__).resolve().parents[1]
AUDIT = json.loads((ROOT/"docs/audits/sae_extensions_validation.json").read_text(encoding="utf-8"))


def _cross(m=120, seed=0):
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(m); n = rng.uniform(50, 500, m)
    p = np.sin(np.clip(.32+.1*x+rng.normal(0, .08, m), 0, np.pi/2))**2
    ph = rng.binomial(n.round().astype(int), p)/n.round()
    se = np.sqrt(np.clip(ph*(1-ph), 1e-6, None)/n)
    return pd.DataFrame(dict(GEOID=[f"{i:05d}" for i in range(m)], rate=ph, rate_se=se, x=x, n=n)), p


def _panel(m=80, T=2, seed=1):
    rng = np.random.default_rng(seed); rows = []
    v = rng.normal(0, .05, m)
    for t, yr in enumerate([2018, 2023][:T]):
        x = rng.standard_normal(m)
        y = .3+.1*x+v+rng.normal(0, .05, m)+rng.normal(0, .03, m)
        rows += [dict(GEOID=f"{i:05d}", Year=yr, y=y[i], y_se=.03, x=x[i]) for i in range(m)]
    return pd.DataFrame(rows)


def test_flags_equal_the_audit():
    assert sx.VALIDATED == AUDIT["passed"] == {"P1": True, "P1q": True, "T1": True}
    assert AUDIT["draws"] == 500
    assert "Committed before the full run" in (ROOT/"docs/audits/sae_extensions_validation_criterion.md").read_text(encoding="utf-8")


def test_bias_corrected_backtransform():
    f = dict(theta=np.array([.3]), post_var=np.array([.01]))
    bc, nv = core._backtransform(f)
    t = np.random.default_rng(0).normal(.3, .1, 400000)
    assert bc[0] == pytest.approx(np.mean(np.sin(t)**2), abs=2e-4) and nv[0] == pytest.approx(np.sin(.3)**2)


def test_arcsine_small_area():
    f, p = _cross()
    out = sx.arcsine_small_area(f, "rate ~ x", "rate_se", n_col="n", bootstrap=50)
    assert out.attrs["validated"] and len(out) == len(f)
    assert ((out.ci_lower >= 0) & (out.ci_upper <= 1) & (out.ci_lower <= out.estimate)).all()
    pct = sx.arcsine_small_area(f.assign(rate=f.rate*100, rate_se=f.rate_se*100), "rate ~ x", "rate_se", n_col="n",
                                bootstrap=50)
    assert pct.estimate.to_numpy() == pytest.approx(100*out.estimate.to_numpy())
    zero = f.copy(); zero.loc[0, "rate"] = 0.0
    with pytest.raises(ValueError, match="n_col"):
        sx.arcsine_small_area(zero, "rate ~ x", "rate_se", bootstrap=20)
    assert np.isfinite(sx.arcsine_small_area(zero, "rate ~ x", "rate_se", n_col="n", bootstrap=20).estimate).all()


def test_temporal_small_area():
    out = sx.temporal_small_area(_panel(), "y ~ x", "y_se", bootstrap=20)
    assert out.attrs["validated"] and (out.release == 2023).all() and len(out) == 80
    with pytest.raises(ValueError, match="overlap"):
        sx.temporal_small_area(_panel().replace({"Year": {2018: 2021}}), "y ~ x", "y_se")
    with pytest.raises(ValueError, match="balanced"):
        sx.temporal_small_area(_panel().iloc[1:], "y ~ x", "y_se")


def test_tool(tmp_path):
    from census import workflows_inference as wi
    f, _ = _cross(); p = tmp_path/"f.csv"; f.to_csv(p, index=False)
    out = wi.small_area_estimates(str(p), "rate ~ x", "rate_se", transform="arcsine", n_col="n",
                                  output_path=str(tmp_path/"o.csv"))
    assert out["success"] and "arcsine" in out["summary"] and out["validated"]
    q = tmp_path/"panel.csv"; _panel().to_csv(q, index=False)
    out = wi.small_area_estimates(str(q), "y ~ x", "y_se", temporal=True, output_path=str(tmp_path/"t.csv"))
    assert out["success"] and "Rao-Yu" in out["summary"]
    assert not wi.small_area_estimates(str(p), "rate ~ x", "rate_se", transform="logit")["success"]
