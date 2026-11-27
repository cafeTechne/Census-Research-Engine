# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 63: interrupted series at 17-19 points; spatial EIV with six to eight covariates under the gate."""
import json
from pathlib import Path

import numpy as np
import pytest
from scipy import stats

from census import its_small_core as isc, mci_core as mi, small_spatial as ss, spatial_eiv
from census.missing_censored_its import interrupted_series

ROOT = Path(__file__).resolve().parents[1]
AUDIT = json.loads((ROOT/"docs/audits/small_many_validation.json").read_text())


def test_flags_equal_the_fixed_audit():
    p = AUDIT["passed"]
    assert AUDIT["criterion_commit"] == "ac2f34c"
    assert ss.ITS_BOOTSTRAP_CONS_MIN_N == p["I6_min_n"] == 17 and ss.ITS_BOOTSTRAP_BB_MIN_N == p["I7_min_n"] == 19
    assert ss.ITS_BOOTSTRAP_BC_MIN_N == 20                         # I3 was the comparison arm
    assert spatial_eiv.GATED_MAX_ERROR_COVARIATES == {"g1": p["G1_gated_cap"], "g2": p["G2_gated_cap"]} == {"g1": 8, "g2": 7}
    assert spatial_eiv.VALIDATED_MAX_ERROR_COVARIATES == 5


def test_conservative_critical_values():
    rng = np.random.default_rng(63)
    X = mi.its_design(17, 9); y = X @ np.array([0, 0, 1, .2])+rng.normal(size=17)
    a = isc.its_bootstrap_t_cons(y, X, np.random.default_rng(1))[0]
    b = isc.its_bootstrap_t_bc(y, X, np.random.default_rng(1))[0]
    tq = stats.t.ppf(.95, 17-4-1)
    for ra, rb in zip(a, b):
        assert ra["upper"]-ra["lower"] >= rb["upper"]-rb["lower"]-1e-12
        assert ra["upper"]-ra["estimate"] >= tq*ra["se"]-1e-9


def test_engine_methods():
    rng = np.random.default_rng(2)
    y17 = np.r_[np.zeros(9), np.ones(8)]+rng.normal(size=17)*.5
    out = interrupted_series(y17, 9, method="bootstrap_t_cons")
    assert out["validated"] and out["audit"].endswith("small_many_validation.md")
    assert not interrupted_series(y17[:16], 8, method="bootstrap_t_cons")["validated"]
    assert not interrupted_series(y17, 9, method="bootstrap_t_bb")["validated"]          # 19+
    assert not interrupted_series(y17, 9, method="bootstrap_t_bc")["validated"]          # 20+


def test_gated_spatial_eiv():
    from tests.test_round46 import several
    for p, method in ((6, "g2"), (8, "g1"), (8, "g2")):
        f, long, coords, rhs = several(p)
        out = spatial_eiv.fit_spatial_eiv(f"y ~ {rhs}", f, long, method=method, coords=coords, fixed_variables=("y",))
        high = min(out["reliability"].values()) >= .8
        expect = high and p <= spatial_eiv.GATED_MAX_ERROR_COVARIATES[method]
        assert out["validated"] is expect


def test_rule_text_mirrored():
    from census import mcp_profiles
    for path in ("docs/agent_protocol.md", "census/mcp_instructions.py"):
        text = " ".join((ROOT/path).read_text().split())
        assert "bootstrap_t_cons" in text and "up to eight" in text and "Round 63" in text
    assert "bootstrap_t_cons" in mcp_profiles.CORE_INSTRUCTIONS and "Round 63" in mcp_profiles.CORE_INSTRUCTIONS
    assert "up to eight" in " ".join((ROOT/"docs/recipes/regression_sampling_error.md").read_text().split())
