# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 134 tests: WHO PAR non-negativity and priority quadrants classification."""
import pandas as pd

from census.inequality_monitoring import priority_quadrants


def test_priority_quadrants_assigns_expected_sides():
    df = pd.DataFrame({
        "GEOID": ["A", "B", "C", "D"],
        "level": [10.0, 20.0, 10.0, 20.0],
        "level_lower": [9.5, 19.5, 9.5, 19.5],
        "level_upper": [10.5, 20.5, 10.5, 20.5],
        "par": [0.1, 0.1, 2.0, 2.0],
        "par_lower": [0.05, 0.05, 1.8, 1.8],
        "par_upper": [0.15, 0.15, 2.2, 2.2],
    })
    out = priority_quadrants(df, level="level", inequality="par").set_index("GEOID")
    assert out.loc["D", "level_side"] == "worse" and out.loc["D", "inequality_side"] == "worse"
    assert out.loc["A", "level_side"] == "better" and out.loc["A", "inequality_side"] == "better"
