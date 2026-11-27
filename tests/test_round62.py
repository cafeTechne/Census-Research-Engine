# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 62: binomial SCPC with stronger benchmarks, Theil T in larger samples, clipped six-group counties."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from census import pums_inequality as pq, scpc, segregation as sg

ROOT = Path(__file__).resolve().parents[1]
AUDIT = json.loads((ROOT/"docs/audits/leftover_failures_validation.json").read_text())


def test_flags_equal_the_fixed_audit():
    p = AUDIT["passed"]
    assert AUDIT["criterion_commit"] == "8f14e39"
    assert scpc.VALIDATED_RHO["binomial"] == tuple(r for r in (.15, .20) if p[f"binomial_SCPC{int(100*r)}"]) == (.15, .20)
    assert scpc.DEFAULT_RHO["binomial"] == .15
    assert p["theil_t_T1_8000"] is False and "theil_t" not in pq.REPAIRED
    assert p["clip_six"] == {"H_bc": "inf", "H_naive": None}
    assert sg.CLIP_RANGES[("theil_h", "bias_corrected", 6)] == (0., np.inf) and sg.CLIP_RANGES[("theil_h", "naive", 6)] is None


def test_binomial_scpc_default_validated():
    from tests.test_round58 import frame
    f, coords = frame()
    f["p"] = 1/(1+np.exp(-f.x)); f["T"] = 200.
    out = scpc.fit_scpc("p ~ x", f, "binomial", trials="T", coords=coords)
    assert out["validated"] and out["rho_bar"] == .15 and "p_value" in out["table"]


def test_clipped_six_groups_validated():
    from tests.test_round57 import county
    f, r, g = county(.9, groups=6, negative=True)
    out = sg.segregation_replicate(f, g, r)
    assert (out.clipped_replicates > 0).all() and out.validated.all()


def test_theil_note():
    from tests.test_round56 import frame
    df, _ = frame(n=3000)
    t = pq.pums_inequality(df, "PINCP")["table"].set_index("measure")
    assert not t.loc["theil_t", "validated"] and "8,000 households" in t.loc["theil_t", "note"]


def test_rule_text_mirrored():
    from census import mcp_profiles
    for path in ("docs/agent_protocol.md", "census/mcp_instructions.py"):
        text = " ".join((ROOT/path).read_text().split())
        assert "rho_bar .15" in text and "8,000 households" in text
    assert "binomial" in mcp_profiles.CORE_INSTRUCTIONS and "Rounds 58/62" in mcp_profiles.CORE_INSTRUCTIONS
    assert "Round 62" in (ROOT/"docs/recipes/segregation.md").read_text()
