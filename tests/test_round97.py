# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 97: spatial block cross-validation and MAUP sensitivity."""
import json
from pathlib import Path

import numpy as np
import pytest

from census import model_assessment as ma
from census import model_assessment_core as mc

ROOT = Path(__file__).resolve().parents[1]


def test_scores_crps_closed_form():
    s = mc.scores([0.0], [0.0], [1.0])
    assert s["crps"] == pytest.approx(2*0.3989422804014327-1/np.sqrt(np.pi)) and s["coverage"] == 1.0
    s = mc.scores([0, 1, 2], [0, 1, 2.5], [1, 1, 1])
    assert s["mae"] == pytest.approx(1/6) and s["rmse"] == pytest.approx(np.sqrt(.25/3))


def test_folds():
    rng = np.random.default_rng(1)
    xy = np.r_[rng.normal(0, 1, (50, 2)), rng.normal(20, 1, (50, 2))]
    lab = mc.block_folds(xy, 2, rng)
    assert len(set(lab[:50])) == 1 and len(set(lab[50:])) == 1 and lab[0] != lab[-1]
    f = mc.random_folds(103, 10, rng)
    assert np.bincount(f).max()-np.bincount(f).min() <= 1


def test_random_zoning_sizes_and_contiguity():
    k = 10; n = k*k
    E = [(i, i+1) for i in range(n) if (i+1) % k] + [(i, i+k) for i in range(n-k)]
    lab = mc.random_zoning(n, E, 10, np.random.default_rng(2))
    sz = np.bincount(lab)
    assert sz.sum() == n and np.median(sz) >= 8 and len(sz) <= n//5
    path = mc.random_zoning(30, [(i, i+1) for i in range(29)], 10, np.random.default_rng(0))
    assert np.bincount(path).tolist() == [10, 10, 10]


def test_maup_slope_identity():
    rng = np.random.default_rng(3); x = rng.normal(size=60); y = 2*x+rng.normal(size=60)
    assert mc.maup_slope(y, x, np.ones(60), np.arange(60)) == pytest.approx(np.polyfit(x, y, 1)[0])


def test_cross_validate_spatial_leakage():
    """With spatially correlated residuals, random folds flatter the neighbour-smoothing model."""
    rng = np.random.default_rng(4)
    g = np.array([(i, j) for i in range(20) for j in range(20)], float)
    D = np.hypot(g[:, :1]-g[:, 0], g[:, 1:]-g[:, 1])
    e = np.linalg.cholesky(np.exp(-D/5)+1e-8*np.eye(400)) @ rng.standard_normal(400)
    x = rng.normal(size=400); y = x+e
    sp = mc.cross_validate(y, x[:, None], g, mc.block_folds(g, 5, rng))
    rd = mc.cross_validate(y, x[:, None], g, mc.random_folds(400, 10, rng))
    assert rd["rmse"] < sp["rmse"]


def test_validated_flag_matches_audit():
    out = json.loads((ROOT/"docs/audits/model_assessment_validation.json").read_text())["outcome"]
    assert ma.VALIDATED["spatial_cv"] is out["V1"]["passed"]
