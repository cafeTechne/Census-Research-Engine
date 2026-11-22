# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 77: joinpoint regression and age-adjusted rate ratios."""
import json
from pathlib import Path

import numpy as np
import pytest

from census import joinpoint as jp, joinpoint_core as jc

ROOT = Path(__file__).resolve().parents[1]
AUDIT = json.loads((ROOT/"docs/audits/joinpoint_validation.json").read_text())


def _series(n=24, seed=1):
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    mu = np.log(5000)+np.where(t < 12, .02*t, .24+.1*(t-12))
    return list(range(1999, 1999+n)), rng.poisson(np.exp(mu)).tolist()


def test_flags_equal_the_audit():
    assert {k: bool(v) for k, v in jp.VALIDATED.items()} == AUDIT["passed"]
    assert AUDIT["permutations"] == 999 and AUDIT["draws"]["joinpoint"] == 1000
    assert "Committed before the full run" in (ROOT/"docs/audits/joinpoint_validation_criterion.md").read_text()


def test_noiseless_recovery_and_configs():
    assert len(jc.configs(15, 1)) == 11 and jc.max_feasible(15) == 4
    x = np.arange(20.)
    y = np.where(x < 10, .01*x, .1+.05*(x-10))
    f = jc.fit(x, y, np.ones(20)*1000, 1)
    assert f["cfg"].tolist() == [10]
    a = jc.apc_intervals(f)
    assert a["apc"] == pytest.approx(100*(np.exp([.01, .05])-1))


def test_joinpoint_finds_the_break_and_flags():
    years, counts = _series()
    r = jp.joinpoint(years, counts=counts, population=[3e8]*24, permutations=499, bootstrap=199)
    assert r["n_joinpoints"] >= 1 and any(abs(j-2011) <= 1 for j in r["joinpoints"])
    assert r["validated"] == {"selection": True, "apc": False, "aapc": False}
    assert any("exploratory" in n for n in r["notes"]) and any("interrupted_series" in n for n in r["notes"])


def test_refusals():
    years, counts = _series()
    with pytest.raises(ValueError, match="five-year"):
        jp.joinpoint(years, counts=counts, population=[3e8]*24, product="5-year")
    bad = list(counts); bad[3] = np.nan
    with pytest.raises(ValueError, match="complete years"):
        jp.joinpoint(years, counts=bad, population=[3e8]*24)
    with pytest.raises(ValueError, match="increasing"):
        jp.joinpoint(years[::-1], counts=counts, population=[3e8]*24)
    short = jp.joinpoint(years[:10], counts=counts[:10], population=[3e8]*10, permutations=99, bootstrap=99)
    assert not short["validated"]["selection"]


def test_rate_ratio():
    r = jp.age_adjusted_rate_ratio([10, 20, 30], [1e4]*3, [5, 10, 20], [1e4]*3, [1, 1, 1])
    assert r["method"] == "tiwari" and r["validated"] and r["ci_lower"] < r["ratio"] < r["ci_upper"]
    assert r["ratio"] == pytest.approx(60/35)


def test_tool():
    from census import workflows_inference as wi
    years, counts = _series()
    out = wi.joinpoint(years=years, counts=counts, population=[3e8]*24)
    assert out["success"] and "joinpoint" in out["summary"] and out["segments"]
    assert not wi.joinpoint(years=years, counts=counts, population=[3e8]*24, product="5-year")["success"]
