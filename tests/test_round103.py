# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 103: agent access (demography_analysis, disparity_measures/spatial_model extensions), routing and hygiene."""
import asyncio
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import mcp_server
from census import mcp_profiles as mp, references as ref, workflows_geo as wg, workflows_inference as wi

ROOT = Path(__file__).resolve().parents[1]


def _write_wonder(path: Path, scale: float = 1.0, suppress_first: bool = False) -> str:
    bands = [
        ("< 1 year", 20000, 3700000), ("1-4 years", 3500, 15000000), ("5-14 years", 5000, 41000000),
        ("15-24 years", 34000, 43000000), ("25-34 years", 58000, 45000000), ("35-44 years", 85000, 43000000),
        ("45-54 years", 160000, 41000000), ("55-64 years", 360000, 42000000), ("65-74 years", 560000, 33000000),
        ("75-84 years", 680000, 16000000), ("85+ years", 850000, 6500000),
    ]
    lines = ["Notes\tTen-Year Age Groups\tGender\tDeaths\tPopulation"]
    for idx, (label, d, n) in enumerate(bands):
        dd = int(round(d * scale))
        if suppress_first and idx == 0:
            lines.append(f"\t{label}\tMale\tSuppressed\t{n // 2}")
            lines.append(f"\t{label}\tFemale\tSuppressed\t{n - n // 2}")
        else:
            lines.append(f"\t{label}\tMale\t{dd // 2}\t{n // 2}")
            lines.append(f"\t{label}\tFemale\t{dd - dd // 2}\t{n - n // 2}")
    lines += ["---", "Dataset: Underlying Cause of Death, 2018-2022",
              "Query Parameters:", "Group By: Ten-Year Age Groups; Gender",
              "Year/Month: 2018; 2019; 2020; 2021; 2022"]
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def test_demography_analysis_life_table_and_arriaga(tmp_path):
    p1 = _write_wonder(tmp_path / "all1.tsv", scale=1.0)
    p2 = _write_wonder(tmp_path / "all2.tsv", scale=0.9)
    c1 = _write_wonder(tmp_path / "c1.tsv", scale=0.3)
    c2 = _write_wonder(tmp_path / "c2.tsv", scale=0.25)

    lt = wi.demography_analysis("life_table", input_path=p1, output_path=str(tmp_path / "lt.csv"))
    assert lt["success"] is True and lt["validated"] is True
    assert 70 < lt["e0"] < 85 and lt["e0_lower"] < lt["e0"] < lt["e0_upper"]
    assert Path(lt["output_path"]).exists()

    arr = wi.demography_analysis("arriaga", input_path=p1, comparison_path=p2,
                                 causes={"heart": c1}, comparison_causes={"heart": c2})
    assert arr["success"] is True and arr["validated"] is True
    assert arr["difference"] > 0
    assert sum(arr["by_cause"].values()) == pytest.approx(arr["difference"], abs=1e-6)


def test_demography_analysis_age_quality_and_migration(tmp_path):
    counts = {str(a): 100.0 for a in range(100)}
    q = wi.demography_analysis("age_quality", pop_by_age=counts, males5=[100.0] * 15, females5=[100.0] * 15)
    assert q["success"] is True and q["validated"] is True
    assert q["whipple"] == pytest.approx(100.0) and q["myers"] == pytest.approx(0.0)

    rng = np.random.default_rng(103)
    n = 1000
    df = pd.DataFrame({"AGEP": rng.integers(0, 90, n), "SEX": rng.integers(1, 3, n), "PWGTP": 10.0})
    for i in range(1, 81):
        df[f"PWGTP{i}"] = 10.0 * (1.0 + 0.2 * rng.standard_normal(n))
    pp = tmp_path / "pums.parquet"; df.to_parquet(pp, index=False)
    qp = wi.demography_analysis("age_quality", input_path=str(pp))
    assert qp["success"] is True and qp["validated"] is True and qp["whipple_se"] > 0

    L = [9.9, 9.8, 9.6, 9.0, 7.5]
    p1 = [100.0, 90.0, 80.0, 70.0, 60.0]
    p2 = [50.0] + [L[i + 1] / L[i] * p1[i] for i in range(4)]
    mig = wi.demography_analysis("survival_migration", pop1=p1, pop2=p2, life_table_L=L)
    assert mig["success"] is True and mig["validated"] is False
    assert mig["total_net_migration"] == pytest.approx(0.0, abs=1e-9)


def test_demography_analysis_ypll_validated_and_suppressed(tmp_path):
    p_ok = _write_wonder(tmp_path / "ypll_ok.tsv")
    r_ok = wi.demography_analysis("ypll", input_path=p_ok, end_age=75)
    assert r_ok["success"] is True and r_ok["validated"] is True and r_ok["adjusted_rate"] > 0

    p_sup = _write_wonder(tmp_path / "ypll_sup.tsv", suppress_first=True)
    r_sup = wi.demography_analysis("ypll", input_path=p_sup, end_age=75)
    assert r_sup["success"] is True and r_sup["validated"] is False
    assert r_sup["adjusted_rate_lower"] < r_sup["adjusted_rate_upper"]
    assert "adjusted_rate" not in r_sup

    tbl_df = pd.DataFrame({
        "GEOID": ["26001", "26003"],
        "d1": [15, 0], "d2": [25, 30],
        "p1": [50000, 50000], "p2": [50000, 50000],
        "s1": [False, True], "s2": [False, False],
    })
    tp = tmp_path / "ypll_tbl.csv"; tbl_df.to_csv(tp, index=False)
    r_tbl = wi.demography_analysis("ypll", input_path=str(tp), death_columns=["d1", "d2"],
                                   population_columns=["p1", "p2"], bands=[[15, 24], [25, 34]],
                                   suppressed_columns=["s1", "s2"], end_age=75)
    assert r_tbl["success"] is True and r_tbl["validated"] is False
    assert r_tbl["rows"][0]["validated"] is True and r_tbl["rows"][1]["validated"] is False


def test_disparity_measures_who_extensions(tmp_path):
    df = pd.DataFrame({
        "GEOID": ["26001", "26003", "26005"],
        "r_lo_a": [0.10, 0.12, 0.14], "r_lo_a_se": [0.01, 0.01, 0.08],
        "r_hi_a": [0.20, 0.22, 0.24], "r_hi_a_se": [0.02, 0.02, 0.02],
        "lvl": [10.0, 20.0, 30.0], "lvl_lower": [8.0, 18.0, 28.0], "lvl_upper": [12.0, 22.0, 32.0],
        "ineq": [2.0, 5.0, 9.0], "ineq_lower": [1.0, 3.0, 7.0], "ineq_upper": [3.0, 7.0, 11.0],
    })
    p = tmp_path / "who_ext.csv"; df.to_csv(p, index=False)

    dd = wi.disparity_measures(str(p), kind="double_disaggregation",
                               cells={"low_inc": {"grp_a": "r_lo_a"}, "high_inc": {"grp_a": "r_hi_a"}})
    assert dd["success"] is True and dd["validated"] is False and len(dd["rows"]) == 6
    assert any(not r["reliable"] for r in dd["rows"])

    pq = wi.disparity_measures(str(p), kind="priority_quadrants", level_col="lvl", inequality_col="ineq")
    assert pq["success"] is True and pq["validated"] is False and len(pq["rows"]) == 3
    assert any(r["priority"] == "high: worse level and larger inequality" for r in pq["rows"])


def test_spatial_model_diversity(tmp_path):
    rng = np.random.default_rng(1030)
    geoids = ["26001", "26003", "26005"]
    df = pd.DataFrame({"GEOID": geoids, "s1": [0.5, 0.7, 0.34], "s2": [0.3, 0.2, 0.33], "s3": [0.2, 0.1, 0.33]})
    rep_rows = []
    for col in ("s1", "s2", "s3"):
        for i, gid in enumerate(geoids):
            base = float(df.loc[i, col])
            row = {"GEOID": gid, "variable": col}
            for r in range(1, 81):
                row[f"rep_{r}"] = max(0.01, base + 0.02 * rng.standard_normal())
            rep_rows.append(row)
    fp = tmp_path / "div.csv"; rp = tmp_path / "div_reps.parquet"
    df.to_csv(fp, index=False); pd.DataFrame(rep_rows).to_parquet(rp, index=False)
    out = wg.spatial_model(str(fp), kind="diversity", groups=["s1", "s2", "s3"],
                           replicates_path=str(rp), output_path=str(tmp_path / "div_out.csv"))
    assert out["success"] is True and out["validated"] is False
    assert Path(out["output_path"]).exists() and len(out["preview"]) == 3


def test_tool_registration_cli_and_attribution():
    tools = {t.name for t in asyncio.run(mcp_server.mcp.list_tools())}
    assert len(tools) == 81 and "demography_analysis" in tools
    assert len(mp.tools_for("core", sorted(tools))) == 16
    assert "demography_analysis" in ref.TOOL_SOURCES
    res = subprocess.run(
        [sys.executable, "-m", "census", "tool", "demography_analysis",
         json.dumps({"kind": "age_quality", "pop_by_age": {str(a): 100 for a in range(100)}}), "--json"],
        capture_output=True, text=True, check=False,
    )
    assert res.returncode == 0, res.stderr
    payload = json.loads(res.stdout)
    assert payload["success"] is True and payload["validated"] is True and "method_sources" in payload

    cite = subprocess.run(
        [sys.executable, "-m", "census", "cite", "--tool", "demography_analysis"],
        capture_output=True, text=True, check=False,
    )
    assert cite.returncode == 0 and "Chiang" in cite.stdout and "Fay" in cite.stdout
