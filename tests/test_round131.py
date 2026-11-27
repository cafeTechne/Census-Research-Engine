# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 131 tests: segregation index mathematical bounds [0, 1]."""
import numpy as np

from census.segregation import segregation_indices


def test_segregation_indices_bounded_zero_to_one():
    even = np.array([[50, 50], [50, 50], [50, 50]], dtype=float)
    idx_even = segregation_indices(even)
    assert abs(idx_even["dissimilarity"]) < 1e-12
    assert abs(idx_even["theil_h"]) < 1e-12

    complete = np.array([[100, 0], [0, 100]], dtype=float)
    idx_comp = segregation_indices(complete)
    assert abs(idx_comp["dissimilarity"] - 1.0) < 1e-12
    assert abs(idx_comp["theil_h"] - 1.0) < 1e-12
