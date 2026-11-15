# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 21: external health sources (CDC PLACES connector), manifest external variables,
fit_eiv fixed outcomes and GEOID-prefix clusters (PLAN_ROUND_21 B1-B4). Offline."""

import io
import json
import os
import shutil
import tempfile
import unittest
import warnings
from unittest import mock

import numpy as np
import pandas as pd

from census import health_sources as hs
from census.analysis import analysis_frame
from census.manifest import create_manifest, run_manifest, validate_manifest
from census.models import fit_eiv
from census.results import IncompleteReplicatesError
from tests.test_round20 import N, FakeClient, _manifest, _replicates, _sim

TRACTS = [f"26001{(i + 1) * 100:06d}" for i in range(N)]


def _places_csv(geoids, measure="DISABILITY", seed=2, value_type="Crude prevalence", extra_rows=()):
    rng = np.random.default_rng(seed)
    v = rng.uniform(15, 40, len(geoids)).round(1)
    rows = ["year,stateabbr,locationid,measureid,data_value_type,data_value,low_confidence_limit,"
            "high_confidence_limit"]
    rows += [f"2023,MI,{g},{measure},{value_type},{a},{a - 2.0:.1f},{a + 2.0:.1f}" for g, a in zip(geoids, v)]
    rows += list(extra_rows)
    return ("\n".join(rows) + "\n").encode()


class FakeFetch:
    def __init__(self, geoids=TRACTS, fail=False, **kw):
        self.geoids, self.fail, self.kw, self.urls = geoids, fail, kw, []

    def __call__(self, url):
        self.urls.append(url)
        if self.fail:
            raise hs.HealthSourceError("network down")
        if "/api/views/" in url:
            return json.dumps({"rowsUpdatedAt": 1764844763}).encode()
        return _places_csv(self.geoids, **self.kw)


class HealthCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        env = mock.patch.dict(os.environ, {"CENSUS_HEALTH_DIR": os.path.join(self.dir, "health")})
        env.start()
        self.addCleanup(env.stop)


class TestPlacesConnector(HealthCase):
    def test_parse_se_from_interval_and_value_type(self):
        rows = pd.read_csv(io.BytesIO(_places_csv(TRACTS[:3], extra_rows=[
            f"2023,MI,{TRACTS[0]},DISABILITY,Age-adjusted prevalence,1,0,2"])), dtype=str)
        out = hs.parse_places(rows, "tract", {"DISABILITY": "dis"})
        self.assertEqual(list(out["GEOID"]), sorted(TRACTS[:3]))
        self.assertTrue(np.allclose(out["dis_se"], 4.0 / (2 * hs.Z95)))
        self.assertTrue(np.allclose(out["dis_ci_upper"] - out["dis"], 2.0))

    def test_parse_refuses_malformed_and_duplicates(self):
        bad = pd.read_csv(io.BytesIO(_places_csv(["2600100"])), dtype=str)
        with self.assertRaisesRegex(hs.HealthSourceError, "malformed"):
            hs.parse_places(bad, "tract", {"DISABILITY": "dis"})
        dup = pd.read_csv(io.BytesIO(_places_csv([TRACTS[0], TRACTS[0]])), dtype=str)
        with self.assertRaisesRegex(hs.HealthSourceError, "duplicated"):
            hs.parse_places(dup, "tract", {"DISABILITY": "dis"})
        text = _places_csv(TRACTS[:1]).decode()
        nonnum = pd.read_csv(io.StringIO(text.replace(text.splitlines()[1].split(",")[5], "abc", 1)), dtype=str)
        with self.assertRaisesRegex(hs.HealthSourceError, "non-numeric"):
            hs.parse_places(nonnum, "tract", {"DISABILITY": "dis"})

    def test_fetch_caches_with_sidecar_and_detects_tampering(self):
        f = FakeFetch()
        got = hs.fetch_places(2025, "tract", ["26"], ["DISABILITY"], fetch=f)
        self.assertEqual(got["dataset"], "cwsq-ngmh")
        self.assertEqual(got["rows_updated_at"], 1764844763)
        self.assertEqual(len(got["rows"]), N)
        url = f.urls[0]
        self.assertIn("data.cdc.gov/resource/cwsq-ngmh.csv", url)
        self.assertIn("stateabbr+in%28%27MI%27%29", url)
        self.assertNotIn("$$app_token", url)
        rec = got["files"][0]
        with open(rec["path"], "rb") as fh:
            self.assertEqual(hs._sha256(fh.read()), rec["sha256"])
        n_calls = len(f.urls)
        again = hs.fetch_places(2025, "tract", ["26"], ["DISABILITY"], fetch=f)
        self.assertEqual(len(f.urls), n_calls)  # served from the cache
        self.assertEqual(again["files"][0]["sha256"], rec["sha256"])
        self.assertIn("datavaluetypeid%3D%27CrdPrv%27", url)
        with open(rec["path"], "ab") as fh:  # a corrupted cache file is fetched again, never used
            fh.write(b"x")
        third = hs.fetch_places(2025, "tract", ["26"], ["DISABILITY"], fetch=f)
        self.assertGreater(len(f.urls), n_calls)
        self.assertEqual(third["files"][0]["sha256"], rec["sha256"])

    def test_revision_stamp_belongs_to_the_download(self):
        stamps = iter([111, 222])

        def fetch(url):
            if "/api/views/" in url:
                return json.dumps({"rowsUpdatedAt": next(stamps)}).encode()
            return _places_csv(TRACTS)

        first = hs.fetch_places(2025, "tract", ["26"], ["DISABILITY"], fetch=fetch)
        self.assertEqual(first["rows_updated_at"], 111)
        cached = hs.fetch_places(2025, "tract", ["26"], ["DISABILITY"], fetch=fetch)
        self.assertEqual(cached["rows_updated_at"], 111)  # pages and stamp both from the cache
        os.remove(first["files"][0]["path"])
        fresh = hs.fetch_places(2025, "tract", ["26"], ["DISABILITY"], fetch=fetch)
        self.assertEqual(fresh["rows_updated_at"], 222)  # fresh pages: fresh stamp

        def fail_meta(url):
            if "/api/views/" in url:
                raise hs.HealthSourceError("down")
            return _places_csv(TRACTS)

        os.remove(first["files"][0]["path"])
        self.assertIsNone(hs.fetch_places(2025, "tract", ["26"], ["DISABILITY"], fetch=fail_meta)["rows_updated_at"])

    def test_offline_refuses_and_html_is_not_cached(self):
        with mock.patch.dict(os.environ, {"CENSUS_HEALTH_OFFLINE": "1"}):
            with self.assertRaisesRegex(hs.HealthSourceError, "OFFLINE"):
                hs.fetch_places(2025, "tract", ["26"], ["DISABILITY"], fetch=FakeFetch())
        with self.assertRaisesRegex(hs.HealthSourceError, "HTML"):
            hs.fetch_places(2025, "tract", ["36"], ["DISABILITY"], fetch=lambda u: b"<!DOCTYPE html><p>busy")
        self.assertFalse(any(p.endswith(".csv") for _, _, fs in os.walk(self.dir) for p in fs))

    def test_paging(self):
        calls = []

        def fetch(url):
            calls.append(url)
            if "/api/views/" in url:
                return b"{}"
            off = int(url.split("offset=")[1].split("&")[0]) if "offset=" in url else 0
            return _places_csv(TRACTS[off:off + 10])

        with mock.patch.object(hs, "PAGE_SIZE", 10):
            got = hs.fetch_places(2025, "tract", ["26"], ["DISABILITY"], fetch=fetch)
        self.assertEqual(len(got["rows"]), N)
        self.assertEqual(len(got["files"]), N // 10 + 1)

    def test_registry_validation(self):
        geo = {"level": "tract", "states": ["26"]}
        ok = [{"name": "dis", "source": "places", "release": 2025, "measure": "DISABILITY"}]
        self.assertEqual(hs.validate_external(ok, geo, [2024], ["x"]), [])
        cases = [
            ([dict(ok[0], source="brfss")], geo, [2024], "unknown external source"),
            ([dict(ok[0], release=2019)], geo, [2024], "release 2019 not registered"),
            ([dict(ok[0], measure="FLU")], geo, [2024], "not a places measure"),
            ([dict(ok[0], extra=1)], geo, [2024], "unknown keys"),
            ([dict(ok[0], name="x")], geo, [2024], "already a variable"),
            (ok, {"level": "block group", "states": ["26"]}, [2024], "no dataset for geography level"),
            (ok, geo, [2019], "values are on 2020 tracts"),
            (ok, {"level": "tract", "state": "all"}, [2024], "needs geography.state"),
            (ok, dict(geo, harmonize_tracts_to=2010), [2024], "harmonize_tracts_to is 2010"),
            (ok, dict(geo, harmonize_tracts_to=2020), [2019, 2024], "single ACS release"),
            (ok + [dict(ok[0], name="dis2")], geo, [2024], "name each measure once"),
            (ok, geo, [2008], "2000 Census tracts"),
        ]
        for entries, g, rel, msg in cases:
            errs = hs.validate_external(entries, g, rel, ["x"])
            self.assertTrue(any(msg in e for e in errs), (msg, errs))
        self.assertEqual(hs.validate_external(ok, dict(geo, harmonize_tracts_to=2020), [2019], []), [])

    def test_circularity_overlap(self):
        self.assertEqual(hs.circularity_overlap("places", ["B25044"]), {})
        hit = hs.circularity_overlap("places", ["B17001", "B15002", "B25044"])
        self.assertEqual(hit["education"], ["B15002"])
        self.assertIn("B17001", hit["poverty (county level in the model)"])


def _ext_manifest(formula="places_dis ~ asr + pov_rate", measure="DIABETES", term=None, **over):
    m = _manifest(**over)
    m["external"] = [{"name": "places_dis", "source": "places", "release": 2025, "measure": measure}]
    m["analyses"] = [{"id": "m1", "method": "fit_eiv", "formula": formula, "replicates": "required"}]
    m["hypotheses"][0]["term"] = term or formula.split("~")[1].split("+")[0].strip()
    return m


class TestManifestExternal(HealthCase):
    def test_validation(self):
        self.assertEqual(validate_manifest(_ext_manifest(), resolve=False), [])
        cases = [
            (_ext_manifest("asr ~ places_dis"), "may only be the outcome"),
            (_ext_manifest("places_dis + asr ~ pov_rate"), "may only be the outcome"),
            (_ext_manifest(aggregation={"mapping": {TRACTS[0]: "a"}}), "cannot be combined with aggregation"),
        ]
        m = _ext_manifest()
        m["analyses"] = [{"id": "c", "method": "correlation_matrix", "variables": ["places_dis", "pov_rate"]}]
        m["hypotheses"] = [{"id": "H1", "analysis": "c", "statistic": "correlation",
                            "variables": ["places_dis", "pov_rate"]}]
        cases.append((m, "can only be the outcome"))
        m = _ext_manifest()
        m["derivations"].append({"name": "gap", "op": "difference", "num": "places_dis", "den": "asr"})
        cases.append((m, "'places_dis' is not an earlier"))
        m = _ext_manifest()
        m["analyses"][0]["method"] = "fit_replicate"
        m["analyses"][0]["args"] = {"target": "these_areas"}
        cases.append((m, "target 'these_areas'"))
        for bad_cluster in ("county", "GEOID.str[:12]", 5):
            m = _ext_manifest()
            m["analyses"][0]["args"] = {"cluster": bad_cluster}
            cases.append((m, "args.cluster"))
        for man, msg in cases:
            errs = validate_manifest(man, resolve=False)
            self.assertTrue(any(msg in e for e in errs), (msg, errs))
        m = _ext_manifest()
        m["analyses"][0]["args"] = {"cluster": "GEOID.str[:5]"}
        self.assertEqual(validate_manifest(m, resolve=False), [])

    def test_create_notes_circularity(self):
        # a control from the model's inputs: allowed, noted
        res = create_manifest(_ext_manifest(), resolve=False)
        self.assertTrue(res["valid"], res["errors"])
        self.assertTrue(any("CIRCULARITY" in n and "B17001" in n for n in res["notes"]), res["notes"])
        self.assertTrue(any("measures the ACS lacks" in n for n in res["notes"]))
        m = _ext_manifest("places_dis ~ asr")  # B18101 measures disability, not composition: generic note only
        res = create_manifest(m, resolve=False)
        self.assertFalse(any("CIRCULARITY" in n for n in res["notes"]), res["notes"])
        self.assertTrue(any("model-based" in n and "only through their correlation" in n for n in res["notes"]))

    def test_rule_r2_tested_model_input(self):
        m = _ext_manifest(term="pov_rate")
        errs = validate_manifest(m, resolve=False)
        self.assertTrue(any("CIRCULARITY R2" in e and "B17001" in e for e in errs), errs)
        m["hypotheses"][0]["circularity_justification"] = "short"
        self.assertTrue(any("CIRCULARITY R2" in e for e in validate_manifest(m, resolve=False)))
        m["hypotheses"][0]["circularity_justification"] = "Testing how far CDC's model reproduces the poverty gradient."
        res = create_manifest(m, resolve=False)
        self.assertTrue(res["valid"], res["errors"])
        self.assertTrue(any("given for ['H1']" in n for n in res["notes"]), res["notes"])
        from census.manifest import methods_section
        self.assertIn("Circularity justification (pre-registered)", methods_section(m))

    def test_rule_r1_same_construct(self):
        # PLACES disability as the outcome of a determinant model: refused, with the rule's text
        m = _ext_manifest("places_dis ~ pov_rate", measure="DISABILITY")
        errs = validate_manifest(m, resolve=False)
        self.assertTrue(any("CIRCULARITY R1" in e and "B18101" in e and "such as diabetes" in e for e in errs), errs)
        # a comparison with the ACS measure, testing only it: allowed (Part 1's design)
        ok = _ext_manifest("places_dis ~ asr + pov_rate", measure="DISABILITY")
        res = create_manifest(ok, resolve=False)
        self.assertTrue(res["valid"], res["errors"])
        self.assertTrue(any("MEASUREMENT COMPARISON" in n for n in res["notes"]), res["notes"])
        # ... but a determinant tested inside the comparison model is refused
        bad = _ext_manifest("places_dis ~ asr + pov_rate", measure="DISABILITY", term="pov_rate")
        errs = validate_manifest(bad, resolve=False)
        self.assertTrue(any("CIRCULARITY R1" in e and "only that comparison" in e for e in errs), errs)

    def test_part1_study_manifest_still_valid(self):
        path = os.path.join(os.path.dirname(__file__), "..", "examples", "manifests",
                            "r21_mi_ny_places_disability_validation.json")
        with open(path, encoding="utf-8") as f:
            m = json.load(f)
        self.assertEqual(validate_manifest(m, resolve=False), [])

    def _run(self, m, fetch, name="run"):
        os.environ["CENSUS_HEALTH_DIR"] = os.path.join(self.dir, "health_" + name)  # restored by setUp's patch
        m = create_manifest(m, resolve=False).get("manifest") or m
        probe = run_manifest(m, os.path.join(self.dir, name + "_probe"), client=FakeClient(), use_cache=False,
                             external_fetch=fetch)
        reps = _replicates(probe["frame"], ["d0", "n0", "d1", "n1", "pov_tot", "pov_n"])
        return run_manifest(m, os.path.join(self.dir, name), client=FakeClient(), use_cache=False, replicates=reps,
                            external_fetch=fetch)

    def test_run_end_to_end(self):
        res = self._run(_ext_manifest(), FakeFetch(measure="DIABETES"))
        self.assertTrue(res["success"], res["deviations"])
        ext = res["external"]
        self.assertEqual(ext["join"]["matched_units"], N)
        self.assertEqual(ext["sources"][0]["rows_updated_at"], 1764844763)
        self.assertEqual(len(ext["sources"][0]["files"][0]["sha256"]), 64)
        m1 = res["results"]["m1"]
        self.assertEqual(m1.diagnostics["replicates_declared_fixed"], ["places_dis"])
        out = os.path.join(self.dir, "run", "bundle")
        with open(os.path.join(out, "methods.md"), encoding="utf-8") as f:
            methods = f.read()
        self.assertIn("External variable `places_dis`: CDC PLACES", methods)
        self.assertIn("held fixed in the replicate design rows", methods)
        self.assertIn("sandwich SEs treating units as independent", methods)
        self.assertIn("Circularity", methods)
        with open(os.path.join(out, "results", "run.json"), encoding="utf-8") as f:
            run = json.load(f)
        self.assertEqual(run["external"]["join"]["matched_units"], N)
        frame = pd.read_parquet(os.path.join(self.dir, "run", run["analysed_data"]["analysis_frame"]["path"])) \
            if run["analysed_data"]["analysis_frame"]["path"].endswith(".parquet") else None
        if frame is not None:
            self.assertIn("places_dis_se", frame.columns)

    def test_join_failure_and_download_failure_block(self):
        res = self._run(_ext_manifest(), FakeFetch(geoids=TRACTS[: N // 2], measure="DIABETES"), name="half")
        self.assertFalse(res["success"])
        self.assertIn("external_join_failed", [d["kind"] for d in res["deviations"]])
        res = self._run(_ext_manifest(), FakeFetch(fail=True, measure="DIABETES"), name="fail")
        kinds = [d["kind"] for d in res["deviations"]]
        self.assertIn("external_unavailable", kinds)
        self.assertIn("analysis_not_run", kinds)
        self.assertEqual(res["analysis_status"], "confirmatory_incomplete")


class TestFitEivFixedAndClusters(unittest.TestCase):
    def test_fixed_external_outcome(self):
        frame, reps = _sim(n=1200, rho=0.0)
        reps = reps[reps["variable"] != "y"]
        with self.assertRaises(IncompleteReplicatesError):
            fit_eiv("y ~ x", frame, reps, replicate_policy="strict")
        res = fit_eiv("y ~ x", frame, reps, replicate_policy="strict", fixed_variables=["y"])
        x = res.coefficients.set_index("term").loc["x"]
        self.assertLess(abs(x["estimate"] - 2.0), 4 * x["se_total"])
        self.assertEqual(res.diagnostics["replicates_declared_fixed"], ["y"])
        with self.assertRaisesRegex(ValueError, "only the outcome"):
            fit_eiv("y ~ x", frame, reps, fixed_variables=["x"])

    def test_geoid_prefix_cluster_equals_column(self):
        frame, reps = _sim(n=900)
        frame["GEOID"] = [f"{i % 30:05d}{i:06d}" for i in range(len(frame))]
        reps["GEOID"] = np.tile(frame["GEOID"].to_numpy(), 2)
        frame["county"] = frame["GEOID"].str[:5]
        a = fit_eiv("y ~ x", frame, reps, cluster="county").coefficients
        b = fit_eiv("y ~ x", frame, reps, cluster="GEOID.str[:5]").coefficients
        self.assertTrue(np.allclose(a["se_total"], b["se_total"]))
        clus = fit_eiv("y ~ x", frame, reps, cluster="GEOID.str[:5]")
        self.assertEqual(clus.diagnostics["clusters"]["groups"], 30)
        self.assertFalse(any("units independent" in n for n in clus.notes))
        self.assertIn("x", clus.diagnostics["se_total_independent"])
        with self.assertRaisesRegex(ValueError, "neither a frame column"):
            fit_eiv("y ~ x", frame, reps, cluster="tract")


class TestAnalysisFrameNoFragmentation(unittest.TestCase):
    def test_many_variables_no_performance_warning(self):
        n, k = 30, 60
        rng = np.random.default_rng(0)
        data = {"GEOID": [f"{i:011d}" for i in range(n)], "Year": 2024}
        for j in range(k):
            data[f"B01001_{j + 1:03d}E"] = rng.integers(10, 100, n)
            data[f"B01001_{j + 1:03d}M"] = 5
        df = pd.DataFrame(data)
        with warnings.catch_warnings():
            warnings.simplefilter("error", pd.errors.PerformanceWarning)
            out = analysis_frame(df, derive=[{"name": "share", "op": "proportion", "num": "B01001_002",
                                              "den": "B01001_001"}])
        self.assertIn("share_se", out.columns)
        self.assertEqual(len(out), n)
        df["NAME"] = "x"
        kept = analysis_frame(df, variables=["B01001_001"], keep_columns=["NAME"])
        self.assertEqual(list(kept.columns).count("NAME"), 1)


if __name__ == "__main__":
    unittest.main()
