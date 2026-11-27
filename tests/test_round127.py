# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 127 tests: Oaxaca-Blinder exact decomposition identity."""
import numpy as np

from census import decomposition_core as dc


def test_oaxaca_blinder_exact_additivity_identity():
    rng = np.random.default_rng(12701)
    n_a, n_b = 400, 500
    xa = rng.normal(0.0, 1.0, (n_a, 2))
    xb = rng.normal(0.8, 1.0, (n_b, 2))
    ya = 1.0 + 0.5 * xa[:, 0] - 0.3 * xa[:, 1] + rng.normal(0, 0.5, n_a)
    yb = 2.0 + 0.5 * xb[:, 0] - 0.3 * xb[:, 1] + rng.normal(0, 0.5, n_b)
    y = np.concatenate([ya, yb])
    X = np.column_stack([np.ones(n_a + n_b), np.vstack([xa, xb])])
    g = np.concatenate([np.ones(n_a), np.zeros(n_b)])
    w = np.ones(n_a + n_b)
    out = dc.oaxaca(y, X, g, w, {"x1": [1], "x2": [2]})
    assert abs((out["explained"] + out["unexplained"]) - out["gap"]) < 1e-10
