# SPDX-License-Identifier: AGPL-3.0-or-later
"""PLAN_ROUND_19 A1-A2: tract harmonization in manifests and replicate apportionment.

Offline: a toy panel crosses the 2010 -> 2020 tract redraw (one tract kept, one split
0.4 / 0.6). The crosswalk and the Census VRE files are synthetic; no network.
"""

import os
import shutil
import tempfile
import unittest
from unittest import mock

import numpy as np
import pandas as pd

from census import tract_harmonization as th
from census.api import CensusAPIClient
from census.manifest import run_manifest, validate_manifest

REP_COLS = [f"rep_{i}" for i in range(1, 81)]
ST, CO = "26", "001"
OLD = {"000100": 1.0, "000200": 1.0}  # 2010 tracts
NEW = ("000100", "000201", "000202")  # 2020 tracts: 000100 unchanged; 000200 -> 000201 (0.4), 000202 (0.6)
SPLIT = {("000100", "000100"): 1.0, ("000200", "000201"): 0.4, ("000200", "000202"): 0.6}


def toy_crosswalk(direction="2010_to_2020"):
    rows = [{"source_geoid": ST + CO + s, "target_geoid": ST + CO + t, "weight": w, "part_area": w}
            for (s, t), w in SPLIT.items()]
    cw = pd.DataFrame(rows)
    cw.attrs.update(weight_type="housing_units", direction=direction, fallbacks={}, notes=["toy crosswalk"],
                    source={"url": "test://toy"})
    return cw


def values(year, tracts):
    """agg income and households per tract (2019 on 2010 tracts, 2024 on 2020 tracts)."""
    n = len(tracts)
    agg = np.linspace(6e7, 9e7, n) * (1.2 if year == 2024 else 1.0)
    hh = np.linspace(1000, 1500, n).round()
    return {"B19025_001": agg.round(), "B19001_001": hh}


def tracts_for(year):
    return list(OLD) if year < 2020 else list(NEW)


def payload(table, year):
    tracts = tracts_for(year)
    cols = {c: v for c, v in values(year, tracts).items() if c.startswith(table)}
    header = ["GEO_ID", "NAME"] + [f"{c}{s}" for c in cols for s in ("E", "EA", "M", "MA")] + \
        ["state", "county", "tract"]
    rows = [header]
    for i, t in enumerate(tracts):
        vals = []
        for est in cols.values():
            vals += [f"{est[i]:.0f}", None, f"{max(est[i] * 0.05, 1):.0f}", None]
        rows.append([f"1400000US{ST}{CO}{t}", f"Tract {t}"] + vals + [ST, CO, t])
    return rows


class TractClient(CensusAPIClient):
    def __init__(self):
        super().__init__(api_key="", cache=None)

    def fetch(self, year, state_code, table_code, geo_level="place", **kwargs):  # type: ignore[override]
        self.last_error = None
        return payload(table_code, year)

    def fetch_variable_metadata(self, year, table_code, dataset=None):  # type: ignore[override]
        return {}


def fake_vre(table, year, geo_level, state_code=None, client=None, **kw):
    """Replicates with perfectly correlated deviations within a release (worst case for independence)."""
    tracts = tracts_for(year)
    parts = []
    for code, est in values(year, tracts).items():
        if not code.startswith(table):
            continue
        shift = np.linspace(-0.02, 0.02, 80)  # same relative shift for every tract: correlation 1
        reps = est[:, None] * (1 + shift[None, :])
        part = pd.DataFrame({"GEOID": [ST + CO + t for t in tracts], "NAME": tracts, "variable": code,
                             "estimate": est, "moe": est * 0.05})
        parts.append(pd.concat([part, pd.DataFrame(reps, columns=REP_COLS)], axis=1))
    out = pd.concat(parts, ignore_index=True)
    out.attrs.update(table=table, year=year, summary_level="140", state_code=state_code,
                     source_url=f"https://example.invalid/{year}/140/{table}.csv.zip",
                     sha256=f"sha-{table}-{year}", moe_check={"passed": True})
    return out


def manifest(**changes):
    m = {
        "schema_version": 1, "title": "Toy tract change", "authors": ["agent:test"],
        "created": "2026-11-14T00:00:00Z", "releases": [2019, 2024],
        "geography": {"level": "tract", "state": ST, "harmonize_tracts_to": 2020},
        "variables": [{"name": "agg", "ref": "2024:B19025_001"}, {"name": "hh", "ref": "2024:B19001_001"}],
        "derivations": [{"name": "mean_inc", "op": "ratio", "num": "agg", "den": "hh"}],
        "replicates": {"source": "census_vre"},
        "analyses": [{"id": "m1", "method": "fit_replicate", "formula": "mean_inc ~ C(Year)",
                      "args": {"model": "ols", "target": "these_areas"}}],
        "hypotheses": [{"id": "H1", "analysis": "m1", "statistic": "coefficient", "term": "C(Year)[T.2024]",
                        "direction": "greater"}],
    }
    m.update(changes)
    return m


class TestValidation(unittest.TestCase):
    def errors(self, **changes):
        return [e for e in validate_manifest(manifest(**changes), resolve=False) if "harmonize" in e]

    def test_valid(self):
        self.assertEqual(self.errors(), [])

    def test_refusals(self):
        geo = manifest()["geography"]
        self.assertTrue(self.errors(geography=dict(geo, harmonize_tracts_to=2000)))
        self.assertTrue(self.errors(geography=dict(geo, harmonize_tracts_to=True)))
        self.assertTrue(self.errors(geography={"level": "county", "state": ST, "harmonize_tracts_to": 2020}))
        self.assertTrue(self.errors(geography={"level": "tract", "states": ["09", "26"], "harmonize_tracts_to": 2020}))
        median = manifest()["variables"] + [{"name": "med", "ref": "2024:B19013_001"}]
        self.assertTrue(any("cannot be apportioned" in e for e in self.errors(variables=median)))


class TestReplicateApportionment(unittest.TestCase):
    def setUp(self):
        self.reps = fake_vre("B19025", 2019, "tract").drop(columns=["NAME", "variable", "moe"])
        self.cw = toy_crosswalk()

    def test_matches_estimate_apportionment(self):
        out = th.apportion_replicates(self.reps, "B19025_001", self.cw).set_index("GEOID")
        wide = pd.DataFrame({"GEOID": self.reps["GEOID"], "Year": 2019,
                             "B19025_001E": self.reps["estimate"], "B19025_001M": self.reps["estimate"] * 0.05})
        est, _ = th.harmonize_wide(wide, {"agg": "B19025_001"}, 2020, {"housing_units": self.cw})
        est = est.set_index("GEOID")
        for g in out.index:
            self.assertAlmostEqual(out.loc[g, "estimate"], est.loc[g, "B19025_001E"], places=6)

    def test_weight_one_target_keeps_source_replicates(self):
        out = th.apportion_replicates(self.reps, "B19025_001", self.cw).set_index("GEOID")
        src = self.reps.set_index("GEOID")
        np.testing.assert_allclose(out.loc[ST + CO + "000100", REP_COLS].to_numpy(float),
                                   src.loc[ST + CO + "000100", REP_COLS].to_numpy(float))

    def test_split_scales_replicate_deviations(self):
        out = th.apportion_replicates(self.reps, "B19025_001", self.cw).set_index("GEOID")
        src = self.reps.set_index("GEOID").loc[ST + CO + "000200"]
        dev_src = src[REP_COLS].to_numpy(float) - src["estimate"]
        dev = out.loc[ST + CO + "000201", REP_COLS].to_numpy(float) - out.loc[ST + CO + "000201", "estimate"]
        np.testing.assert_allclose(dev, 0.4 * dev_src)

    def test_merging_correlated_sources_exceeds_independence_approximation(self):
        # Two sources merged into one target: the replicate SE carries their covariance.
        cw = pd.DataFrame({"source_geoid": [ST + CO + "000100", ST + CO + "000200"],
                           "target_geoid": [ST + CO + "009900"] * 2, "weight": [1.0, 1.0], "part_area": [1.0, 1.0]})
        out = th.apportion_replicates(self.reps, "B19025_001", cw).iloc[0]
        se_rep = np.sqrt(4 / 80 * ((out[REP_COLS].to_numpy(float) - out["estimate"]) ** 2).sum())
        src = self.reps.set_index("GEOID")
        se_each = [np.sqrt(4 / 80 * ((src.loc[g, REP_COLS].to_numpy(float) - src.loc[g, "estimate"]) ** 2).sum())
                   for g in src.index]
        self.assertAlmostEqual(se_rep, sum(se_each), delta=1e-6 * se_rep)  # correlation 1: SEs add
        self.assertGreater(se_rep, np.sqrt(sum(s ** 2 for s in se_each)) * 1.3)


class TestManifestRun(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)

    def run_m(self, m):
        with mock.patch("census.replicate.fetch_vre", side_effect=fake_vre), \
                mock.patch.object(th, "crosswalks", side_effect=lambda target, states, kinds: {
                    k: toy_crosswalk() for k in kinds}):
            return run_manifest(m, os.path.join(self.dir, "run"), client=TractClient(), use_cache=False)

    def test_run_harmonizes_estimates_and_replicates(self):
        res = self.run_m(manifest())
        self.assertEqual(res["analysis_status"], "confirmatory", res["deviations"])
        frame = res["frame"]
        self.assertEqual(sorted(frame.loc[frame["Year"] == 2019, "GEOID"]), [ST + CO + t for t in NEW])
        f19 = frame[frame["Year"] == 2019].set_index("GEOID")
        agg_old = values(2019, list(OLD))["B19025_001"]
        self.assertAlmostEqual(f19.loc[ST + CO + "000201", "agg"], 0.4 * agg_old[1], places=3)
        reps = res["replicates"]
        self.assertEqual(reps["apportioned_releases"], [2019])
        check = reps["apportioned_estimate_check"]
        self.assertTrue(all(v["max_rel_diff"] < 1e-9 for v in check.values()), check)
        methods = open(os.path.join(self.dir, "run", "bundle", "methods.md"), encoding="utf-8").read()
        self.assertIn("Tract harmonization (pre-registered)", methods)
        self.assertIn("apportioned with the same weights", methods)

    def test_crosswalk_failure_is_a_blocking_deviation(self):
        with mock.patch("census.replicate.fetch_vre", side_effect=fake_vre), \
                mock.patch.object(th, "crosswalks", side_effect=OSError("block data unavailable")):
            res = run_manifest(manifest(), os.path.join(self.dir, "fail"), client=TractClient(), use_cache=False)
        self.assertEqual(res["analysis_status"], "confirmatory_incomplete")
        self.assertIn("harmonization_failed", [d["kind"] for d in res["deviations"]])


if __name__ == "__main__":
    unittest.main()
