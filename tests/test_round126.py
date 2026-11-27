# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 126 tests: Chiang II life table + exact Arriaga additivity identity."""
import numpy as np

from census import demography_core as dc


def test_chiang_life_table_and_arriaga_exact_additivity():
    ages = np.array([0, 1, 5, 15, 25, 35, 45, 55, 65, 75, 85], dtype=float)
    pop = np.array([1e6, 4e6, 1e7, 1e7, 1e7, 1e7, 1e7, 9e6, 7e6, 4e6, 1.5e6], dtype=float)
    d_m = np.array([6000, 1200, 1800, 12000, 20000, 25000, 45000, 100000, 180000, 260000, 240000], dtype=float)
    d_f = d_m * 0.65
    lt_m = dc.life_table(ages, d_m, pop, level=0.90)
    lt_f = dc.life_table(ages, d_f, pop, level=0.90)
    arr = dc.arriaga(lt_m, lt_f)
    by_age = np.asarray(arr, float)
    assert abs(float(np.sum(by_age)) - float(lt_f["e"][0] - lt_m["e"][0])) < 1e-10
    assert lt_f["e"][0] > lt_m["e"][0]
