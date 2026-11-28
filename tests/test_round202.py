# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 202 tests: reusable confounding_adjustment_screen, 100 routing rows (R98-R100), and v0.198.0 hygiene."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from census.standardize import confounding_adjustment_screen

ROOT = Path(__file__).resolve().parents[1]


def test_confounding_adjustment_screen_detects_simpsons_paradox():
    # Construct a synthetic county dataset where older rural counties have lower poverty but higher mortality,
    # creating a classic Simpson's paradox (crude RR < 1, age-adjusted RR > 1).
    rng = np.random.default_rng(202)
    n = 120
    pct_65 = rng.uniform(10.0, 28.0, n)
    poverty = 28.0 - 0.65 * pct_65 + rng.normal(0.0, 2.5, n)
    pop = rng.uniform(20_000, 300_000, n)
    log_rate = -7.2 + 0.03 * poverty + 0.11 * pct_65
    deaths = rng.poisson(pop * np.exp(log_rate))
    df = pd.DataFrame({"deaths": deaths, "pop": pop, "poverty": poverty, "pct_65": pct_65})

    res = confounding_adjustment_screen(
        df, "deaths", "pop", "poverty", confounders=["pct_65"], exposure_scale=10.0
    )
    assert res["n_obs"] == n
    assert res["crude"]["rr"] < 1.0
    assert res["adjusted"]["rr"] > 1.0
    assert res["sign_flipped"] is True
    assert abs(res["cie_pct"]) > 10.0


def test_r202_routing_100_rows_and_hygiene_v0198():
    rt = (ROOT / "docs/agent_routing.md").read_text(encoding="utf-8")
    for row_id in ("| R98 |", "| R99 |", "| R100 |"):
        assert row_id in rt

    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/release_hygiene_check.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rep = json.loads(proc.stdout)
    assert rep["ok"] is True and rep["version"] >= "0.198.0"
