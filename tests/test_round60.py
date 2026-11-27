# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 60: transformed SDR intervals for PUMS inequality measures (flags = audit)."""
import json
from pathlib import Path

import numpy as np
import pytest
from scipy.stats import norm

from census import pums_inequality as pq, pums_inequality_core as pc

ROOT = Path(__file__).resolve().parents[1]
AUDIT = json.loads((ROOT/"docs/audits/pums_inequality_repair_validation.json").read_text())


def test_flags_equal_the_fixed_audit():
    assert AUDIT["criterion_commit"] == "60a3b06"
    p = AUDIT["passed"]
    for m, v in p.items():
        if v["procedure"] is None:
            assert m not in pq.REPAIRED
        else:
            assert v["procedure"] == "T1" and pq.REPAIRED[m] == v["min_records"]
    assert "theil_t" not in pq.REPAIRED and pq.REPAIRED == {"atkinson_1": None, "atkinson_0.5": 7000, "top10_share": 7000}


def test_transformed_summary_by_hand():
    rng = np.random.default_rng(60)
    th = np.r_[.3, .3+.02*rng.standard_normal(80)]
    s = pc.transformed_summary(th, "logit")
    lg = np.log(th/(1-th)); se = np.sqrt(.05*np.sum((lg[1:]-lg[0])**2)); z = norm.ppf(.95)
    assert s["lower"] == pytest.approx(1/(1+np.exp(-(lg[0]-z*se)))) and s["estimate"] == .3
    assert 0 < s["lower"] < .3 < s["upper"] < 1
    s2 = pc.transformed_summary(th, "log")
    assert s2["upper"]/.3 == pytest.approx(.3/s2["lower"])                    # symmetric on the log scale
    assert pc.bias_corrected(th) == pytest.approx(th[0]-4*(th[1:].mean()-th[0]))
    with pytest.raises(ValueError):
        pc.transformed_summary(np.r_[1.2, th[1:]], "logit")


def test_engine_gate():
    from tests.test_round56 import frame
    df, _ = frame(n=3000)
    t = pq.pums_inequality(df, "PINCP")["table"].set_index("measure")
    assert t.loc["atkinson_1", "validated"] and t.loc["atkinson_1", "interval"] == "logit"
    assert not t.loc["top10_share", "validated"] and "7000" in t.loc["top10_share", "note"]
    assert not t.loc["theil_t", "validated"] and t.loc["theil_t", "interval"] == "normal"
    big, _ = frame(n=8000)
    t = pq.pums_inequality(big, "PINCP")["table"].set_index("measure")
    assert t.loc["top10_share", "validated"] and t.loc["atkinson_0.5", "validated"]


def test_rule_text_mirrored():
    from census import mcp_profiles
    for path in ("docs/agent_protocol.md", "census/mcp_instructions.py", "docs/recipes/pums_tests.md"):
        text = " ".join((ROOT/path).read_text().split())
        assert "Round 60" in text and "7,000" in text
    assert "Round 60" in mcp_profiles.CORE_INSTRUCTIONS
