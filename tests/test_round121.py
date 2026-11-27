# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 121 regression tests: large-sample discrete RDD bandwidth fallback."""
import numpy as np
import pandas as pd

from census.rdd import regression_discontinuity


def test_discrete_rdd_large_sample_integer_grid_does_not_fail_pilot_bandwidth():
    rng = np.random.default_rng(12101)
    n = 160_000
    ages = rng.integers(55, 76, size=n)
    y = (0.05 - 0.04 * (ages >= 65) + rng.normal(0, 0.02, size=n))
    df = pd.DataFrame({"AGEP": ages, "y": y})
    res = regression_discontinuity(df, "y", "AGEP", 65.0, level=0.90)
    assert res["bandwidth"] >= 4.0
    assert abs(res["estimate"] - (-0.04)) < 0.01
