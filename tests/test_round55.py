# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 55: short interrupted series and SMRs with estimated reference populations (flags = audit)."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from census import its_small_core as isc, mci_core as mi, small_spatial as ss, standardize as sd
from census.missing_censored_its import interrupted_series

ROOT = Path(__file__).resolve().parents[1]
AUDIT = json.loads((ROOT/"docs/audits/short_series_reference_validation.json").read_text())


def test_flags_equal_the_fixed_audit():
    p = AUDIT["passed"]
    assert AUDIT["criterion_commit"] == "dd6d6b7"
    assert ss.ITS_BOOTSTRAP_BC_MIN_N == p["I3_min_n"] == 20
    assert p["I4_min_n"] is None and ss.ITS_EWC_VALIDATED is False
    assert ss.ITS_BOOTSTRAP_MIN_N == 30 and p["I2_min_n"] == 25          # comparison arm; threshold kept at 30
    assert sd.SMR_REFERENCE_POPULATION_VALIDATED is p["R1"] is True


def test_ewc_terms_and_variance():
    assert [isc.ewc_terms(n) for n in (15, 20, 25, 30)] == [2, 3, 3, 4]
    rng = np.random.default_rng(55)
    X = mi.its_design(24, 13); y = X @ np.array([0, 0, 1, .2])+rng.normal(size=24)
    r = isc.its_ewc(y, X)
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    assert r[0]["estimate"] == pytest.approx(b[2]) and r[1]["estimate"] == pytest.approx(b[3])
    assert r[0]["df"] == 3 and r[0]["upper"] > r[0]["lower"]


def test_bias_corrected_bootstrap_engine():
    rng = np.random.default_rng(1)
    y = np.r_[np.zeros(11), np.ones(11)]+rng.normal(size=22)*.5
    out = interrupted_series(y, 11, method="bootstrap_t_bc")
    assert out["validated"] and out["phi_bias_corrected"] == pytest.approx(min(.95, out["phi"]+(1+3*out["phi"])/22))
    assert out["audit"].endswith("short_series_reference_validation.md")
    assert not interrupted_series(y[:19], 9, method="bootstrap_t_bc")["validated"]      # below 20 points
    assert not interrupted_series(y, 11, method="bootstrap_t")["validated"]              # plain: 30+
    ewc = interrupted_series(y, 11, method="ewc")
    assert not ewc["validated"] and any("EWC .61-.72" in n for n in ewc["notes"])


def smr(**kw):
    obs = pd.Series([130], index=["26001"])
    pop = pd.DataFrame([[2000., 1000.]], index=obs.index)
    rates = np.array([.01, .1]); D = np.array([400, 800])
    return sd.indirect_standardize(obs, pop, rates, None, reference_counts=D, **kw).iloc[0], rates, D


def test_reference_population_variance():
    base, rates, D = smr()
    se = np.array([1000., 400.])
    row, _, _ = smr(reference_population_se=se)
    E_b = np.array([2000*.01, 1000*.1]); w = E_b/E_b.sum()
    P = D/rates
    extra = np.sum(w**2*(se/P)**2)
    assert row.se_log_smr**2 == pytest.approx(base.se_log_smr**2+extra)
    assert any("survey estimates" in n for n in row.notes) and not any("treated as fixed" in n for n in row.notes)
    with pytest.raises(ValueError, match="requires reference_counts"):
        sd.indirect_standardize(pd.Series([5], index=["x"]), pd.DataFrame([[10., 10.]], index=["x"]), rates, None,
                                reference_population_se=se)


def test_manifest_arg_checked():
    from census.manifest import methods
    errors = []
    a = {"id": "smr", "observed": "o", "population_bands": ["a", "b"], "reference_rates": [.01, .1],
         "reference_counts": [400, 800], "reference_source": "x", "args": {"reference_population_se": [1000, 400]}}
    ctx = dict(a=a, errors=errors, names={"o", "a", "b"}, ext_names=set(), manifest={}, i=0)
    methods._check_smr("before_spatial", ctx)
    assert not any("reference_population_se" in e for e in errors), errors
    a2 = {**a, "reference_counts": None, "args": {"reference_population_se": [1000, 400]}}
    errors2 = []
    methods._check_smr("before_spatial", dict(ctx, a=a2, errors=errors2))
    assert any("reference_population_se" in e for e in errors2)


def test_rule_text_mirrored():
    from census import mcp_profiles
    for path in ("docs/agent_protocol.md", "census/mcp_instructions.py"):
        text = " ".join((ROOT/path).read_text().split())
        assert "bootstrap_t_bc" in text and "reference_population_se" in text
    assert "bootstrap_t_bc" in mcp_profiles.CORE_INSTRUCTIONS
    assert "reference_population_se" in (ROOT/"docs/recipes/health_inequality.md").read_text()
