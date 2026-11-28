# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 200 tests: Multi-component and island-aware BYM2 spatial disease mapping (N132)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from census.disease_mapping import disease_map
from census.disease_mapping_core import graph_components, scaled_icar_eigen


def test_single_component_matches_strict_default_and_default_rejects_disconnected():
    edges = [(0, 1), (1, 2), (2, 3), (3, 0)]
    v1, l1 = scaled_icar_eigen(4, edges, allow_disconnected=False)
    v2, l2 = scaled_icar_eigen(4, edges, allow_disconnected=True)
    np.testing.assert_allclose(v1, v2)
    np.testing.assert_allclose(l1, l2)

    disc_edges = [(0, 1), (1, 2), (3, 4)]  # 2 components + island 5
    with pytest.raises(ValueError, match="connected"):
        scaled_icar_eigen(6, disc_edges, allow_disconnected=False)


def test_multi_component_and_island_bym2_disease_map():
    # Two disconnected 4-node rings + 1 isolated island (9 areas total)
    edges = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4)]
    comps = graph_components(9, edges)
    assert len(comps) == 3
    assert sum(1 for c in comps if len(c) == 1) == 1

    rng = np.random.default_rng(200)
    E = np.full(9, 45.0)
    y = rng.poisson(E * np.array([1.3, 1.2, 1.1, 1.0, 0.8, 0.9, 0.85, 0.95, 1.5]))
    df = pd.DataFrame({"GEOID": [f"9900{i}" for i in range(9)], "deaths": y, "expected": E})
    res = disease_map(df, "deaths", "expected", edges, method="B3", allow_disconnected=True)
    assert res["n_components"] == 3
    assert res["n_islands"] == 1
    assert res["validated"] is False  # multi-component stays explicitly exploratory
    assert np.isfinite(res["table"]["relative_risk"]).all()
    assert (res["table"]["ci_lower"] < res["table"]["ci_upper"]).all()
    assert any("Freni-Sterrantino" in n for n in res["notes"])
