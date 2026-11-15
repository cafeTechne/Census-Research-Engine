# SPDX-License-Identifier: AGPL-3.0-or-later
"""Multi-start selection and score-based convergence (census.optim).

Regression for the Python 3.10 / SciPy 1.15 failure of
test_spatial_lambda_correction: two L-BFGS-B starts reached the same optimum,
one ended with an ABNORMAL line-search exit and an objective 2e-13 lower, and
the fit was reported unconverged. The tests below reproduce that on any SciPy
by forcing the exit status, so they do not depend on the installed version.
"""

import os
import re
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from census.optim import best_start, projected_score_ok

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _r(fun, success, x=(0.0,)):
    return SimpleNamespace(fun=fun, success=success, x=np.array(x), message="ok" if success else "ABNORMAL")


class TestBestStart(unittest.TestCase):
    def test_tied_converged_run_preferred(self):
        a, b = _r(554.3449970352636, False), _r(554.3449970352638, True)
        self.assertIs(best_start([a, b]), b)

    def test_strictly_better_unconverged_kept(self):
        a, b = _r(500.0, False), _r(554.0, True)
        self.assertIs(best_start([a, b]), a)

    def test_lowest_converged(self):
        a, b = _r(10.0, True), _r(9.0, True)
        self.assertIs(best_start([a, b]), b)

    def test_nonfinite_ignored(self):
        a, b = _r(float("nan"), True), _r(3.0, False)
        self.assertIs(best_start([a, b]), b)


class TestProjectedScore(unittest.TestCase):
    def test_interior_small_gradient(self):
        self.assertTrue(projected_score_ok([0.2, 0.3], [1e-5, -2e-4], [(None, None), (-1, 1)]))

    def test_interior_large_gradient(self):
        self.assertFalse(projected_score_ok([0.2, 0.3], [1e-5, 0.5], [(None, None), (-1, 1)]))

    def test_bound_pointing_out(self):
        # minimum at the upper bound: gradient negative (descent direction is outside the box)
        self.assertTrue(projected_score_ok([0.99], [-3.0], [(-0.99, 0.99)]))
        self.assertFalse(projected_score_ok([0.99], [3.0], [(-0.99, 0.99)]))

    def test_nonfinite(self):
        self.assertFalse(projected_score_ok([0.0], [float("nan")], [(None, None)]))


class TestMeSemFitAbnormalExit(unittest.TestCase):
    def test_abnormal_exit_at_optimum_is_converged(self):
        """Every L-BFGS-B run is forced to report ABNORMAL; the fit is still converged (score ~ 0)."""
        import census.simulation  # noqa: F401  (registers simulation_spreg)
        from census import simulation_spreg as ss
        rng = np.random.default_rng(7)
        side = 6
        n = side * side
        W = np.zeros((n, n))
        for i in range(side):
            for j in range(side):
                k = i * side + j
                for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    a, b = i + di, j + dj
                    if 0 <= a < side and 0 <= b < side:
                        W[k, a * side + b] = 1.0
        W = W / W.sum(1, keepdims=True)
        x = rng.standard_normal(n)
        u = np.linalg.solve(np.eye(n) - 0.5 * W, rng.standard_normal(n))
        s = np.full(n, 0.3)
        y = 1.0 + 2.0 * x + u + s * rng.standard_normal(n)
        ref = ss.me_sem_fit(y, x[:, None], W, np.diag(s ** 2))
        self.assertTrue(ref["converged"])
        real = ss.optimize.minimize

        def abnormal(*a, **k):
            res = real(*a, **k)
            res.success = False
            res.message = "ABNORMAL: "
            return res

        with patch.object(ss.optimize, "minimize", side_effect=abnormal):
            f = ss.me_sem_fit(y, x[:, None], W, np.diag(s ** 2))
        self.assertTrue(f["converged"])
        self.assertIn("ABNORMAL", f["message"])
        self.assertAlmostEqual(f["lambda"], ref["lambda"], places=8)

    def test_far_from_optimum_not_converged(self):
        """A run stopped early (maxiter 1) away from the optimum is still reported unconverged."""
        import census.simulation  # noqa: F401
        from census import simulation_spreg as ss
        rng = np.random.default_rng(3)
        n = 25
        W = np.zeros((n, n))
        for k in range(n - 1):
            W[k, k + 1] = W[k + 1, k] = 1.0
        W = W / W.sum(1, keepdims=True)
        x = rng.standard_normal(n)
        y = 1.0 + x + np.linalg.solve(np.eye(n) - 0.7 * W, rng.standard_normal(n))
        real = ss.optimize.minimize

        def short(fun, x0, **k):
            k["options"] = dict(k.get("options", {}), maxiter=1)
            res = real(fun, x0, **k)
            res.success = False
            return res

        with patch.object(ss.optimize, "minimize", side_effect=short):
            f = ss.me_sem_fit(y, x[:, None], W, np.diag(np.full(n, 0.04)))
        self.assertFalse(f["converged"])


class TestSupportedVersions(unittest.TestCase):
    def test_python_and_scipy_floors(self):
        with open(os.path.join(ROOT, "pyproject.toml"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn('requires-python = ">=3.11"', text)
        self.assertIn('"scipy>=1.16"', text)
        with open(os.path.join(ROOT, ".github", "workflows", "ci.yml"), encoding="utf-8") as f:
            ci = f.read()
        self.assertNotRegex(ci, re.compile(r'"3\.10"'))


if __name__ == "__main__":
    unittest.main()
