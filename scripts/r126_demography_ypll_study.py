#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 126: Pre-registered national Chiang II life tables, Arriaga sex-gap decomposition, and YPLL-75 (WONDER 2018-2022)."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from census import demography_core as dc
from census.demography import life_table_from_wonder
from census.surveillance import ypll_from_wonder

PROTOCOL = {
    "round": 126,
    "title": "US National Life Expectancy (Chiang II), Female-Male Arriaga Decomposition, and Cause-Specific YPLL-75 (WONDER 2018-2022)",
    "source_dir": "external_data/wonder/ucd/2018-2022/national_age_sex",
    "causes": ["all_causes", "cancer", "heart_disease", "drug_overdose"],
    "confidence_level": 0.90,
    "ypll_end_age": 75,
}

AGE_START_MAP = {
    "1": 0, "1-4": 1, "5-14": 5, "15-24": 15, "25-34": 25, "35-44": 35,
    "45-54": 45, "55-64": 55, "65-74": 65, "75-84": 75, "85+": 85,
}


def protocol_hash() -> str:
    return hashlib.sha256(json.dumps(PROTOCOL, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _load_sex_bands(path: Path, sex_code: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep="\t", dtype=str)
    sub = df[(df["Notes"].isna() | (df["Notes"] == "")) & (df["Sex Code"] == sex_code)].copy()
    sub["age_start"] = sub["Ten-Year Age Groups Code"].map(AGE_START_MAP)
    sub = sub.dropna(subset=["age_start"]).copy()
    sub["age_start"] = sub["age_start"].astype(int)
    sub["deaths"] = pd.to_numeric(sub["Deaths"], errors="coerce")
    sub["population"] = pd.to_numeric(sub["Population"], errors="coerce")
    return sub.sort_values("age_start")[["age_start", "deaths", "population"]].reset_index(drop=True)


def main() -> None:
    base = Path(PROTOCOL["source_dir"])
    all_path = base / "all_causes.tsv"

    lt_total = life_table_from_wonder(str(all_path), level=PROTOCOL["confidence_level"])
    f_df = _load_sex_bands(all_path, "F")
    m_df = _load_sex_bands(all_path, "M")
    ages = m_df["age_start"].to_numpy(float)

    lt_f = dc.life_table(ages, f_df["deaths"].to_numpy(float), f_df["population"].to_numpy(float), level=0.90)
    lt_m = dc.life_table(ages, m_df["deaths"].to_numpy(float), m_df["population"].to_numpy(float), level=0.90)
    arr = dc.arriaga(lt_m, lt_f)
    e0_m, e0_f = float(lt_m["e"][0]), float(lt_f["e"][0])
    idx65 = int(np.where(ages == 65)[0][0])
    e65_m, e65_f = float(lt_m["e"][idx65]), float(lt_f["e"][idx65])
    by_age = arr["by_age"] if isinstance(arr, dict) and "by_age" in arr else np.asarray(arr, float)
    delta_by_age = {int(a): float(v) for a, v in zip(ages, by_age)}

    ypll_by_cause: Dict[str, Any] = {}
    for cause in PROTOCOL["causes"]:
        y = ypll_from_wonder(str(base / f"{cause}.tsv"), end=PROTOCOL["ypll_end_age"], level=0.90)
        ypll_by_cause[cause] = {
            "age_adjusted_rate_per_100k": float(y["adjusted_rate"]),
            "lower": float(y["lower"]),
            "upper": float(y["upper"]),
            "crude_rate_per_100k": float(y["crude_rate"]),
            "validated": bool(y.get("validated", True)),
        }

    lt_tbl = lt_total["table"]
    row65 = lt_tbl[lt_tbl["age"].astype(str).str.startswith("65")].iloc[0]
    summary = {
        "protocol": PROTOCOL,
        "protocol_sha256": protocol_hash(),
        "total_life_table": {
            "e0": float(lt_total["e0"]),
            "e0_ci": [float(lt_total["e0_lower"]), float(lt_total["e0_upper"])],
            "e65": float(row65["e"]),
            "e65_ci": [float(row65["lower"]), float(row65["upper"])],
            "validated": bool(lt_total["validated"]),
        },
        "sex_life_tables": {
            "female": {"e0": e0_f, "e0_ci": [float(lt_f["lower"][0]), float(lt_f["upper"][0])],
                       "e65": e65_f, "e65_ci": [float(lt_f["lower"][idx65]), float(lt_f["upper"][idx65])]},
            "male": {"e0": e0_m, "e0_ci": [float(lt_m["lower"][0]), float(lt_m["upper"][0])],
                     "e65": e65_m, "e65_ci": [float(lt_m["lower"][idx65]), float(lt_m["upper"][idx65])]},
        },
        "arriaga_female_minus_male": {
            "total_gap_years": float(e0_f - e0_m),
            "arriaga_sum_years": float(np.sum(by_age)),
            "additivity_error": float(abs(np.sum(by_age) - (e0_f - e0_m))),
            "by_age_start": delta_by_age,
        },
        "ypll_75_by_cause": ypll_by_cause,
    }
    out_dir = Path("studies_output/r126_demography_ypll")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
