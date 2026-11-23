# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 95: YPLL and aberration detection."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from census import surveillance as sv
from census import surveillance_core as sc

ROOT = Path(__file__).resolve().parents[1]
B = [(0, 0), (1, 4), (5, 14), (15, 24), (25, 34), (35, 44), (45, 54), (55, 64), (65, 74), (75, 84), (85, None)]


def test_ypll_grouped_method_by_hand():
    d = [10, 2, 3, 20, 30, 40, 80, 150, 300, 500, 800]; n = [1e4, 4e4, 1e5, 1e5, 1e5, 1e5, 1e5, 1e5, 8e4, 5e4, 2e4]
    r = sc.ypll(d, n, B, 75)
    assert r["ypll"] == pytest.approx(10*74.5+2*72+3*65+20*55+30*45+40*35+80*25+150*15+300*5)
    assert r["lower"] < r["adjusted_rate"] < r["upper"]
    assert sc.ypll(d, n, B, 65)["ypll"] < r["ypll"]
    with pytest.raises(ValueError, match="boundary"):
        sc.ypll(d, n, B, 70)


def test_bounds_and_table():
    d = np.array([0, 2, 3, 20, 30, 40, 80, 150, 300, 500, 800.]); n = np.full(11, 1e5)
    s = np.zeros(11, bool); s[0] = True
    b = sc.ypll_bounds(d, s, n, B, 75)
    assert b["ypll_upper"]-b["ypll_lower"] == pytest.approx(8*74.5)
    f = pd.DataFrame([dict(GEOID="x", **{f"d{i}": v for i, v in enumerate(d)}, **{f"n{i}": 1e5 for i in range(11)},
                           **{f"s{i}": bool(s[i]) for i in range(11)})])
    t = sv.ypll_table(f, [f"d{i}" for i in range(11)], [f"n{i}" for i in range(11)], B, 75,
                      suppressed_columns=[f"s{i}" for i in range(11)])
    assert "ypll" not in t.columns and t.ypll_lower.iloc[0] < t.ypll_upper.iloc[0]
    assert not bool(t.validated.iloc[0]) and t.suppressed_bands.iloc[0] == 1


def test_flags():
    h = sc.historical_limits([10, 11, 10, 12, 11, 15], .5)
    assert h["flag"] == "high" and h["upper_limit"] < 15
    assert sc.historical_limits([10, 11, 10, 12, 11, 11], .5)["flag"] == "none"
    assert sc.ears_c2([10, 11, 9, 10, 11, 10, 9, 10, 11, 20])["flag"] == "high"
    with pytest.raises(ValueError):
        sc.ears_c2([1, 2, 3])
    a = sv.aberration([2017, 2018, 2019, 2021, 2022, 2023], [10, 11, 10, 12, 11, 15], [.5]*6)
    assert a["flag"] == "high" and any("skips years" in n for n in a["notes"]) and a["validated"]


def test_validated_flags_match_audit():
    out = json.loads((ROOT/"docs/audits/surveillance_validation.json").read_text())["outcome"]
    assert sv.VALIDATED == {"ypll": out["Y1"]["passed"], "historical_limits": out["A1"]["passed"],
                            "ears_c2": out["A2"]["passed"]}


@pytest.mark.skipif(not (ROOT/"external_data/wonder/ucd/2018-2022/national_age_sex/all_causes.tsv").exists(),
                    reason="owner's WONDER exports not present")
def test_wonder_national_export():
    r = sv.ypll_from_wonder(str(ROOT/"external_data/wonder/ucd/2018-2022/national_age_sex/all_causes.tsv"))
    assert 5000 < r["adjusted_rate"] < 10000 and r["years"] == [2018, 2019, 2020, 2021, 2022]
    s = sv.ypll_from_wonder(str(ROOT/"external_data/wonder/ucd/2018-2022/national_age_sex/alcohol_induced.tsv"))
    assert "adjusted_rate" not in s and s["adjusted_rate_lower"] <= s["adjusted_rate_upper"] and not s["validated"]


def test_joinpoint_aberration_option():
    from census.workflows_inference import joinpoint
    years = list(range(2008, 2023)); pop = [1e6]*15
    counts = [200]*14+[400]
    r = joinpoint(years=years, counts=counts, population=pop, aberration="historical_limits")
    assert r["success"] and r["aberration"]["flag"] == "high" and "Latest year 2022" in r["summary"]


def test_deviation_chart(tmp_path):
    p = sv.deviation_chart(["a", "b"], [.8, 1.6], [.85, .85], [1.15, 1.15], str(tmp_path/"c.png"))
    assert Path(p).stat().st_size > 1000
