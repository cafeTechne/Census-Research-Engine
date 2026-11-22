# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 86: quantitative bias analysis (E-values, misclassification, both directions)."""
import json
from pathlib import Path

import numpy as np
import pytest

from census import bias_analysis as ba, bias_analysis_core as bc

ROOT = Path(__file__).resolve().parents[1]
AUDIT = json.loads((ROOT/"docs/audits/bias_analysis_validation.json").read_text())


def test_flags_equal_the_audit():
    assert ba.VALIDATED["probabilistic_misclassification"] == AUDIT["passed"]["P1"] is False
    assert ba.VALIDATED["e_value"] is True
    assert "Committed before the full run" in (ROOT/"docs/audits/bias_analysis_validation_criterion.md").read_text()


def test_e_values_published_example():
    # VanderWeele and Ding (2017), Ann Intern Med: RR 3.9 (95% CI 1.8-8.7) -> E-values 7.26 and 3.00
    r = bc.e_value(3.9, 1.8, 8.7)
    assert r["e_value"] == pytest.approx(7.26, abs=.005) and r["e_value_limit"] == pytest.approx(3.0, abs=1e-9)
    assert bc.e_value(1.2, .9, 1.6)["e_value_limit"] == 1.0
    assert bc.e_value(.8)["e_value"] == pytest.approx(bc.e_value(1.25)["e_value"])
    assert bc.e_value(4.0, measure="or", prevalence=.3)["estimate_rr_scale"] == pytest.approx(2.0)
    assert bc.e_value(4.0, measure="or", prevalence=.05)["estimate_rr_scale"] == pytest.approx(4.0)


def test_simple_correction_inverts_misclassification():
    # true table: exposed 200/2000 cases, unexposed 100/2000; nondifferential outcome Se .8, Sp .9
    a_t, c_t, n = 200., 100., 2000.
    a = .8*a_t+.1*(n-a_t); c = .8*c_t+.1*(n-c_t)
    A, B, C, D = bc.corrected_table(a, n-a, c, n-c, .8, .9, "outcome")
    assert A == pytest.approx(a_t) and C == pytest.approx(c_t)
    r = ba.misclassification(a, n-a, c, n-c, .8, .9, sd=.02, draws=4000)
    assert r["corrected"]["rr"] == pytest.approx(2.0) and r["observed"]["rr"] < 2.0
    assert "probabilistic" in r and r["validated"] is False
    with pytest.raises(ValueError, match="impossible"):
        ba.misclassification(10, 1990, 10, 1990, .8, .9)


def test_tool_and_both_directions():
    from census import workflows_inference as wi
    out = wi.bias_analysis("e_value", estimate=1.4, lower=1.1, upper=1.8)
    assert out["success"] and out["e_value"] > 1
    out = wi.bias_analysis("misclassification", table=[360, 1640, 280, 1720], sensitivity=.8, specificity=.9)
    assert out["success"] and out["corrected"]["rr"] > out["observed"]["rr"]
    assert not wi.bias_analysis("nope")["success"]
    assert ba.both_directions(1.3, 1.1, "income")["difference"] == pytest.approx(.2)
