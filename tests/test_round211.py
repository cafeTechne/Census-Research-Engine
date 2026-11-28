# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 211 tests: confounding_screen MCP/CLI tool (85 Layer A tools), routing R104-R109, and v0.207.0 hygiene."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def test_confounding_screen_cli_and_routing_r104_r109(tmp_path: Path):
    rng = np.random.default_rng(211)
    n = 80
    pct_65 = rng.uniform(10.0, 28.0, n)
    poverty = 28.0 - 0.65 * pct_65 + rng.normal(0.0, 2.5, n)
    pop = rng.uniform(25_000, 250_000, n)
    deaths = rng.poisson(pop * np.exp(-7.2 + 0.03 * poverty + 0.11 * pct_65))
    csv_p = tmp_path / "frame.csv"
    pd.DataFrame({"deaths": deaths, "pop": pop, "poverty": poverty, "pct_65": pct_65}).to_csv(csv_p, index=False)

    payload = json.dumps({
        "input_path": str(csv_p),
        "deaths_col": "deaths",
        "population_col": "pop",
        "exposure_col": "poverty",
        "confounders": ["pct_65"],
        "exposure_scale": 10.0,
    })
    proc = subprocess.run(
        [sys.executable, "-m", "census", "tool", "confounding_screen", payload, "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rep = json.loads(proc.stdout)
    assert rep["success"] is True
    assert rep["sign_flipped"] is True

    rt = (ROOT / "docs/agent_routing.md").read_text(encoding="utf-8")
    for row_id in ("| R104 |", "| R105 |", "| R106 |", "| R107 |", "| R108 |", "| R109 |"):
        assert row_id in rt


def test_r211_doctor_deep_and_release_hygiene_v0207():
    proc = subprocess.run(
        [sys.executable, "-m", "census", "doctor", "--deep", "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rep = json.loads(proc.stdout)
    assert rep["ok"] is True
    assert rep["deep_checks"]["mcp_tool_count"] == 85
    assert rep["deep_checks"]["tool_sources_count"] == 85
