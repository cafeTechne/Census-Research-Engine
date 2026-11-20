# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 64: the agent routing contract in docs/agent_routing.md, run on offline fixtures."""
import asyncio
import re
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd
import pytest

import mcp_server
from census import mcp_profiles as mp, workflows_inference as wi

ROOT = Path(__file__).resolve().parents[1]
ROWS = {}
for line in (ROOT/"docs/agent_routing.md").read_text().splitlines():
    m = re.match(r"\| (R\d+) \| .*? \| (core|full) \| `(\w+)[^|]*\| ([^|]+) \| (\w+) \|$", line)
    if m:
        ROWS[m.group(1)] = dict(profile=m.group(2), tool=m.group(3), expected=m.group(4).strip(), guidance=m.group(5))
REGISTERED = {t.name for t in asyncio.run(mcp_server.mcp.list_tools())}


def _frame(tmp_path):
    from tests.test_round58 import frame
    f, coords = frame()
    f["p"] = 1/(1+np.exp(-f.x)); f["T"] = 200.
    p = tmp_path/"f.csv"; f.to_csv(p, index=False)
    return str(p), f, coords


def _scpc(tmp_path, **kw):
    p, _, coords = _frame(tmp_path)
    with mock.patch("census.small_spatial.frame_coordinates", return_value=coords):
        return wi.fit_model(p, **kw)


def _censored(tmp_path):
    rng = np.random.default_rng(64)
    n = 300; x = rng.normal(size=n); E = rng.uniform(50, 500, n)
    mu = E*np.exp(-3+.4*x); y = rng.negative_binomial(5, 5/(5+mu)).astype(float)
    hid = (y >= 1) & (y <= 9)
    p = tmp_path/"c.csv"; pd.DataFrame(dict(y=np.where(hid, np.nan, y), x=x, E=E, hid=hid)).to_csv(p, index=False)
    return str(p)


def _eiv(p, method):
    from census import spatial_eiv
    from tests.test_round46 import several
    f, long, coords, rhs = several(p)
    return spatial_eiv.fit_spatial_eiv(f"y ~ {rhs}", f, long, method=method, coords=coords, fixed_variables=("y",))


def _series(n):
    rng = np.random.default_rng(7)
    k = n//2
    return list(np.r_[np.zeros(k), np.ones(n-k)]+.05*np.arange(n)+rng.normal(size=n)*.4), list(range(2023-n, 2023)), 2023-n+k


def _ineq(measure):
    from census import pums_inequality as pq
    from tests.test_round56 import frame
    t = pq.pums_inequality(frame(n=3000)[0], "PINCP")["table"].set_index("measure")
    return dict(success=True, validated=bool(t.loc[measure, "validated"]))


CALLS = {
    "R1": lambda t: mcp_server.calculate_significance(14.1, 1.2, 11.0, 1.1),
    "R2": lambda t: wi.fit_model(_frame(t)[0], "y ~ x"),
    "R3": lambda t: _scpc(t, formula="y ~ x", spatial="scpc"),
    "R4": lambda t: _scpc(t, formula="p ~ x", model="binomial", trials="T", spatial="scpc"),
    "R5": lambda t: __import__("census.scpc", fromlist=["x"]).fit_scpc(
        "p ~ x", _frame(t)[1], "binomial", trials="T", coords=_frame(t)[2], rho_bar=.10) | dict(success=True),
    "R6": lambda t: wi.fit_model(_frame(t)[0], "c ~ x", model="negbin", exposure="E"),
    "R7": lambda t: wi.fit_model(_censored(t), "y ~ x", model="negbin", exposure="E", censored="hid"),
    "R8": lambda t: _eiv(6, "g1") | dict(success=True),
    "R9": lambda t: _eiv(9, "g2") | dict(success=True),
    "R10": lambda t: (lambda v, y, b: wi.interrupted_series(values=v, years=y, interruption_year=b))(*_series(18)),
    "R11": lambda t: (lambda v, y, b: wi.interrupted_series(values=v, years=y, interruption_year=b))(*_series(15)),
    "R12": lambda t: wi.interrupted_series(values=[14.1, 13.6, 13.0, 12.2, 11.8], years=[2013, 2015, 2018, 2020, 2023],
                                           interruption_year=2018),
    "R13": lambda t: mcp_server.trend_test([2013, 2018, 2023], [14.1, 13.0, 11.8], [0.4, 0.4, 0.3]),
    "R14": lambda t: _ineq("gini"),
    "R15": lambda t: _ineq("theil_t"),
}


def test_contract_rows_match_the_runners():
    assert sorted(ROWS) == sorted(CALLS) and len(ROWS) == 15


@pytest.mark.parametrize("rid", sorted(CALLS, key=lambda r: int(r[1:])))
def test_routing_row(rid, tmp_path):
    row = ROWS[rid]
    assert row["tool"] in REGISTERED
    assert row["tool"] in mp.tools_for(row["profile"], sorted(REGISTERED))
    guide = (ROOT/f"docs/recipes/{row['guidance']}.md").read_text()
    assert row["tool"] in guide or row["tool"] in mcp_server.INSTRUCTIONS
    out = CALLS[rid](tmp_path)
    exp = row["expected"]
    ok = out.get("success", "error_code" not in out)   # some older tools omit success on success
    if exp.startswith("refused"):
        assert ok is False
        return
    assert ok is True, out
    if exp == "validated":
        assert out["validated"] is True, out
    elif exp == "exploratory":
        assert out["validated"] is False, out
    else:
        assert exp == "answered"


def test_core_text_names_only_reachable_tools():
    """Core-style profiles may name a tool outside the profile only as "<tool> [full]" or next to "full profile"."""
    for profile in mp.CORE_STYLE_PROFILES:
        have = set(mp.tools_for(profile, sorted(REGISTERED)))
        texts = re.split(r"\n(?=\d+\. )", mp.CORE_INSTRUCTIONS) + [mp.DESCRIPTION_OVERRIDES[t] for t in have
                                                                   if t in mp.DESCRIPTION_OVERRIDES]
        for text in texts:
            outside = {n for n in re.findall(r"\b[a-z_]+\b", text) if n in REGISTERED and n not in have}
            unmarked = {n for n in outside if f"{n} [full]" not in text}
            assert not unmarked or "full profile" in text, (profile, unmarked, text[:120])


def test_rule_text_generated_from_protocol():
    import subprocess, sys
    assert subprocess.run([sys.executable, str(ROOT/"scripts/sync_rule_text.py"), "--check"]).returncode == 0
    proto = (ROOT/"docs/agent_protocol.md").read_text()
    assert proto.count("<!-- mcp-rules:A -->") >= 15 and "<!-- mcp-rules:B -->" in proto
