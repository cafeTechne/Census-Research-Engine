# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 101: demographic estimation tools."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from census import demography as dg
from census import demography_core as dc

ROOT = Path(__file__).resolve().parents[1]
STARTS = [0, 1, 5, 15, 25, 35, 45, 55, 65, 75, 85]
RATES = np.array([550, 24, 13, 80, 130, 200, 380, 850, 1700, 4000, 13000])/1e5
PY = np.array([1, 4, 10, 10, 10, 10, 10, 10, 10, 10, 8])*1e6


def test_age_indices_exact():
    u = {a: 100 for a in range(100)}
    assert dc.whipple(u) == pytest.approx(100) and dc.myers(u) == pytest.approx(0)
    h = {a: (100 if a % 5 == 0 else 0) for a in range(100)}
    assert dc.whipple(h) == pytest.approx(500)
    z = {a: (100 if a % 10 == 0 else 0) for a in range(100)}
    assert dc.myers(z) == pytest.approx(90)
    un = dc.un_accuracy([100]*15, [100]*15)
    assert un["index"] == pytest.approx(0)


def test_life_table_and_arriaga():
    lt = dc.life_table(STARTS, RATES*PY, PY)
    assert 75 < lt["e"][0] < 85 and (np.diff(lt["l"]) <= 0).all() and lt["se_e"][0] > 0
    lt2 = dc.life_table(STARTS, .9*RATES*PY, PY)
    c = dc.arriaga(lt, lt2)
    assert c.sum() == pytest.approx(lt2["e"][0]-lt["e"][0], abs=1e-10)
    byc = dc.arriaga_by_cause(c, lt["m"], lt2["m"], np.column_stack([.5*lt["m"], .5*lt["m"]]),
                              np.column_stack([.5*lt2["m"], .5*lt2["m"]]))
    assert byc.sum() == pytest.approx(c.sum())


def test_census_survival_identity():
    L = np.array([9.9, 9.8, 9.6, 9.0, 7.5]); p1 = np.array([100., 90, 80, 70, 60])
    p2 = np.r_[50, (L[1:]/L[:-1])*p1[:-1]]
    assert np.allclose(dc.census_survival_net_migration(p1, p2, L), 0)


def test_validated_flag_matches_audit():
    out = json.loads((ROOT/"docs/audits/demography_validation.json").read_text())["outcome"]["L1"]
    assert dg.VALIDATED["life_table"] is (out["passed"] or out["gated"])


def test_pums_age_quality_replicates():
    rng = np.random.default_rng(1); n = 5000
    df = pd.DataFrame({"AGEP": rng.integers(0, 90, n), "SEX": rng.integers(1, 3, n), "PWGTP": 10.0})
    for i in range(1, 81):
        df[f"PWGTP{i}"] = 10.0*(1+.3*rng.standard_normal(n))
    q = dg.age_quality_pums(df)
    assert 80 < q["whipple"] < 120 and q["whipple_se"] > 0 and q["myers"] >= 0


@pytest.mark.skipif(not (ROOT/"external_data/wonder/ucd/2018-2022/national_age_sex/all_causes.tsv").exists(),
                    reason="owner's WONDER exports not present")
def test_wonder_life_table():
    r = dg.life_table_from_wonder(str(ROOT/"external_data/wonder/ucd/2018-2022/national_age_sex/all_causes.tsv"))
    assert 76 < r["e0"] < 80 and r["e0_lower"] < r["e0"] < r["e0_upper"]
