# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 132 tests: arcsine Fay-Herriot MSE strictly reduces or matches direct variance."""
import numpy as np
import pandas as pd

from census.sae_extensions import arcsine_small_area


def test_arcsine_fay_herriot_reduces_median_mse():
    rng = np.random.default_rng(13201)
    n = 60
    x = rng.normal(0, 1, n)
    p_true = 1.0 / (1.0 + np.exp(-(-1.8 + 0.4 * x)))
    se = rng.uniform(0.015, 0.035, n)
    p_obs = np.clip(p_true + rng.normal(0, se), 0.01, 0.99)
    df = pd.DataFrame({"GEOID": [f"26{i:03d}" for i in range(n)], "p": p_obs, "se": se, "x": x})
    out = arcsine_small_area(df, "p ~ x", se_col="se", percent=False, bootstrap=60, level=0.90)
    assert out.attrs["validated"] is True
    assert float(np.median(out["mse"] / (se ** 2))) < 1.0
