# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 110 tests: joinpoint and demography manifest methods, and validation-first non-promotion of S3/W2."""
import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd

from census import inequality_monitoring as im
from census import staggered as stg
from census.manifest import load_manifest, validate_manifest
from census.manifest.methods import METHODS, _run_demography, _run_joinpoint, _stat_demography, _stat_joinpoint
from tests.test_manifest import EXAMPLE

ROOT = Path(__file__).resolve().parents[1]


def test_round110_audit_failed_candidates_not_promoted():
    audit = json.loads((ROOT / "docs/audits/repairs110_validation.json").read_text())
    assert audit["verdicts"]["S3"] is False
    assert audit["verdicts"]["W2-mdm"] is False
    assert audit["verdicts"]["W2-mdb"] is False
    assert im.VALIDATED["mdm_w"] is False and im.VALIDATED["mdb_w"] is False
    assert "joinpoint" in METHODS and "demography" in METHODS
    assert len(METHODS) >= 24


def test_manifest_joinpoint_and_demography():
    # Schema validation for joinpoint
    m = copy.deepcopy(load_manifest(EXAMPLE))
    m["analyses"] = [{"id": "j1", "method": "joinpoint", "year": "income", "counts": "pop", "population": "pop"}]
    m["hypotheses"] = [{"id": "h1", "analysis": "j1", "statistic": "aapc", "direction": "two-sided"}]
    assert validate_manifest(m, resolve=False) == []

    # Schema validation for demography
    m2 = copy.deepcopy(load_manifest(EXAMPLE))
    m2["analyses"] = [{"id": "d1", "method": "demography", "age_start": "income", "deaths": "pop", "population": "pop"}]
    m2["hypotheses"] = [{"id": "h1", "analysis": "d1", "statistic": "e0", "direction": "two-sided"}]
    assert validate_manifest(m2, resolve=False) == []

    # Direct runner + extractor for joinpoint
    rng = np.random.default_rng(11001)
    years = list(range(2005, 2023))
    x = np.arange(len(years), dtype=float)
    counts = np.maximum(rng.poisson(400.0 * np.exp(-0.02 * x)), 1)
    df_j = pd.DataFrame({"yr": years, "d": counts, "n": np.full(len(years), 100000.0)})
    rj = _run_joinpoint({"year": "yr", "counts": "d", "population": "n"},
                        {"max_joinpoints": 1, "permutations": 199, "bootstrap": 100},
                        df_j, 0.90, None, None, {})
    sj = _stat_joinpoint({"statistic": "aapc", "null_value": 0.0}, rj)
    assert sj["ci_lower"] < sj["estimate"] < sj["ci_upper"] and "confirmatory_refusal" not in sj

    # Direct runner + extractor for demography (Chiang II life table)
    ages = [0, 1, 5, 15, 25, 35, 45, 55, 65, 75, 85]
    deaths = [200, 35, 50, 340, 580, 850, 1600, 3600, 5600, 6800, 8500]
    pop = [37000, 150000, 410000, 430000, 450000, 430000, 410000, 420000, 330000, 160000, 65000]
    df_d = pd.DataFrame({"age": ages, "d": deaths, "n": pop})
    rd = _run_demography({"age_start": "age", "deaths": "d", "population": "n"}, {}, df_d, 0.90, None, None, {})
    sd0 = _stat_demography({"statistic": "e0", "null_value": 75.0}, rd)
    sd65 = _stat_demography({"statistic": "e65", "null_value": 15.0}, rd)
    assert 60.0 < sd0["estimate"] < 90.0 and sd0["ci_lower"] < sd0["estimate"] < sd0["ci_upper"]
    assert 10.0 < sd65["estimate"] < 30.0 and "confirmatory_refusal" not in sd0
