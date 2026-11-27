# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 130 tests: closed-form mathematical benchmarks, Layer B isolation, and v0.125.0 hygiene."""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

from census import decomposition_core as dec
from census import demography_core as dem

ROOT = Path(__file__).resolve().parents[1]


def test_r130_arriaga_and_oaxaca_exact_identities():
    ages = np.array([0, 1, 5, 15, 25, 35, 45, 55, 65, 75, 85], dtype=float)
    pop = np.array([5e5, 2e6, 5e6, 5e6, 5e6, 5e6, 5e6, 4.5e6, 3.5e6, 2e6, 7.5e5], dtype=float)
    d1 = np.array([3000, 600, 900, 6000, 10000, 12500, 22500, 50000, 90000, 130000, 120000], dtype=float)
    lt1 = dem.life_table(ages, d1, pop)
    lt2 = dem.life_table(ages, d1 * 0.8, pop)
    arr = np.asarray(dem.arriaga(lt1, lt2), float)
    assert abs(float(arr.sum()) - float(lt2["e"][0] - lt1["e"][0])) < 1e-10

    rng = np.random.default_rng(13001)
    xa, xb = rng.normal(0, 1, (300, 2)), rng.normal(0.5, 1, (300, 2))
    ya = 1.0 + 0.6 * xa[:, 0] + rng.normal(0, 0.3, 300)
    yb = 1.8 + 0.6 * xb[:, 0] + rng.normal(0, 0.3, 300)
    y = np.concatenate([ya, yb])
    X = np.column_stack([np.ones(600), np.vstack([xa, xb])])
    g = np.concatenate([np.ones(300), np.zeros(300)])
    ob = dec.oaxaca(y, X, g, np.ones(600), {"x1": [1], "x2": [2]})
    assert abs((ob["explained"] + ob["unexplained"]) - ob["gap"]) < 1e-10


def test_r130_layer_b_isolation_and_release_hygiene():
    imp_pat = re.compile(r"^\s*(from\s+census\b|import\s+census\b)", re.M)
    for pyf in (ROOT / "layer_b_openscholar").rglob("*.py"):
        assert not imp_pat.search(pyf.read_text(encoding="utf-8")), f"census import in {pyf}"
    proc = subprocess.run([sys.executable, str(ROOT / "scripts/release_hygiene_check.py")],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rep = json.loads(proc.stdout)
    assert rep["ok"] is True and rep["version"] >= "0.125.0"
