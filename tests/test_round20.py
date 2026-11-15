# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 20: age standardization (A1), fit_eiv (A2), covariate reliability notes (A3)."""

import copy
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

import numpy as np
import pandas as pd
from scipy.stats import chi2

from census import standardize as stdz
from census.analysis import analysis_frame, attach_replicates
from census.api import CensusAPIClient
from census.data_integrity import BundledDataIntegrityError
from census.manifest import create_manifest, manifest_hash, run_manifest, validate_manifest
from census.models import covariate_reliability, fit_eiv, fit_replicate
from census.results import IncompleteReplicatesError
from census.variance import REPLICATE_COLUMNS

BANDS = [[0, 17], [18, 34], [35, 64], [65, 74], [75, None]]


class TestStandardPopulation(unittest.TestCase):
    def test_us2000_total_and_published_weights(self):
        rows = stdz.standard_population("us2000")
        self.assertEqual(sum(p for _, _, p in rows), 274_633_642)
        self.assertEqual(rows[-1], (85, None, 4_259_173))
        w = stdz.standard_weights(BANDS)
        self.assertAlmostEqual(sum(w), 1.0, places=12)
        # NCHS 2000 standard per million: 65-74 = 66,037; 75-84 + 85+ = 44,842 + 15,508
        self.assertAlmostEqual(w[3], 0.066037, places=5)
        self.assertAlmostEqual(w[4], 0.060350, places=5)
        info = stdz.standard_info("us2000")
        self.assertIn("seer.cancer.gov", info["source"])
        self.assertEqual(len(info["csv_sha256"]), 64)

    def test_partial_bands_are_renormalized(self):
        w = stdz.standard_weights([[18, 64], [65, None]])
        self.assertAlmostEqual(sum(w), 1.0, places=12)
        self.assertGreater(w[0], w[1])

    def test_band_validation(self):
        for bad, msg in (([], "non-empty"), ([[0, 17], [19, None]], "contiguous"),
                         ([[0, None], [18, 30]], "only the last"), ([[0, 89]], "ends above"),
                         ([[-1, 5]], "non-negative"), ([[5, 3]], "hi must")):
            with self.assertRaisesRegex(ValueError, msg):
                stdz.standard_weights(bad)
        with self.assertRaisesRegex(ValueError, "unknown standard"):
            stdz.standard_weights(BANDS, "world")

    def test_tampered_table_is_refused(self):
        d = tempfile.mkdtemp()
        try:
            for f in ("us2000.csv", "us2000.json"):
                shutil.copy(os.path.join(stdz.standard_dir(), f), d)
            with open(os.path.join(d, "us2000.csv"), "a", encoding="utf-8") as fh:
                fh.write("86,86,1\n")
            stdz._load.cache_clear()
            with mock.patch.object(stdz, "standard_dir", return_value=d):
                with self.assertRaises(BundledDataIntegrityError):
                    stdz.standard_weights(BANDS)
        finally:
            stdz._load.cache_clear()
            shutil.rmtree(d, ignore_errors=True)

    def test_direct_standardize(self):
        cases = np.array([[1, 0], [10, 5]], float)
        pops = np.array([[100, 0], [200, 50]], float)
        r = stdz.direct_standardize(cases, pops, [0.25, 0.75])
        self.assertAlmostEqual(r[0], 0.25 * 0.01 + 0.75 * 0.05)
        self.assertTrue(np.isnan(r[1]))  # empty band: undefined
        with self.assertRaisesRegex(ValueError, "sum to"):
            stdz.direct_standardize(cases, pops, [0.5, 0.6])

    def test_fay_feuer_reduces_to_exact_poisson_for_one_band(self):
        x, n = 12, 5000
        out = stdz.age_adjusted_interval([x], [n], [1.0], 0.95)
        self.assertAlmostEqual(out["lower"], chi2.ppf(0.025, 2 * x) / (2 * n), places=12)
        self.assertAlmostEqual(out["upper"], chi2.ppf(0.975, 2 * (x + 1)) / (2 * n), places=12)
        self.assertEqual(stdz.age_adjusted_interval([0], [n], [1.0])["lower"], 0.0)


def _band_frame(n=6, seed=3):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({"GEOID": [f"26001{i:06d}" for i in range(n)]})
    for b in range(2):
        den = rng.integers(200, 900, n)
        df[f"B18101_{2 * b + 3:03d}E"] = den
        df[f"B18101_{2 * b + 3:03d}M"] = 40
        df[f"B18101_{2 * b + 4:03d}E"] = (den * rng.uniform(0.05, 0.3, n)).round()
        df[f"B18101_{2 * b + 4:03d}M"] = 20
    return df


ASR = {"name": "asr", "op": "age_standardized", "as_percent": True, "weights": [0.3, 0.7],
       "groups": [{"num": "n0", "den": "d0"}, {"num": "n1", "den": "d1"}]}
VARS = {"d0": "B18101_003", "n0": "B18101_004", "d1": "B18101_005", "n1": "B18101_006"}


class TestAgeStandardizedDerivation(unittest.TestCase):
    def test_estimate_and_exact_replicate_se(self):
        df = _band_frame()
        frame = analysis_frame(df, variables=VARS, derive=[ASR])
        exp = 100 * (0.3 * df["B18101_004E"] / df["B18101_003E"] + 0.7 * df["B18101_006E"] / df["B18101_005E"])
        np.testing.assert_allclose(frame["asr"], exp)
        self.assertTrue((frame["asr_method"] == "age_standardized").all())
        rng = np.random.default_rng(0)
        parts = []
        reps = {}
        for name, code in VARS.items():
            est = df[f"{code}E"].to_numpy(float)
            r = est[:, None] + rng.normal(0, 5, (len(df), 80))
            reps[name] = r
            parts.append(pd.DataFrame({"GEOID": df["GEOID"], "variable": name, "estimate": est,
                                       **dict(zip(REPLICATE_COLUMNS, r.T))}))
        long = pd.concat(parts, ignore_index=True)
        out, rl = attach_replicates(frame, long, variables={k: k for k in VARS}, derive=[ASR])
        rep_asr = 100 * (0.3 * reps["n0"] / reps["d0"] + 0.7 * reps["n1"] / reps["d1"])
        se = np.sqrt(4 / 80 * ((rep_asr - exp.to_numpy()[:, None]) ** 2).sum(axis=1))
        np.testing.assert_allclose(out["asr_se"], se, rtol=1e-10)
        self.assertTrue((out["asr_method"] == "replicate").all())

    def test_standard_and_bands_without_weights(self):
        df = _band_frame()
        spec = dict(ASR, weights=None, standard="us2000", bands=[[0, 17], [18, None]])
        frame = analysis_frame(df, variables=VARS, derive=[spec])
        w = stdz.standard_weights([[0, 17], [18, None]])
        exp = 100 * (w[0] * df["B18101_004E"] / df["B18101_003E"] + w[1] * df["B18101_006E"] / df["B18101_005E"])
        np.testing.assert_allclose(frame["asr"], exp)


# --------------------------------------------------------------------------- manifests

N = 40


def _payload(table_code):
    rng = np.random.default_rng(11)
    if table_code == "B18101":
        codes = ["B18101_003", "B18101_004", "B18101_006", "B18101_007"]
        den = rng.integers(300, 900, (N, 2))
        num = (den * rng.uniform(0.05, 0.25, (N, 2))).round()
        vals = np.column_stack([den[:, 0], num[:, 0], den[:, 1], num[:, 1]])
        moes = np.full_like(vals, 25.0, dtype=float)
    else:
        codes = ["B17001_001", "B17001_002"]
        tot = rng.integers(1500, 5000, N)
        pov = (tot * rng.uniform(0.05, 0.4, N)).round()
        vals, moes = np.column_stack([tot, pov]), np.column_stack([np.full(N, 150.0), np.full(N, 90.0)])
    header = ["GEO_ID", "NAME"] + [c + s for c in codes for s in ("E", "EA", "M", "MA")] + ["state", "county", "tract"]
    rows = [header]
    for i in range(N):
        tract = f"{(i + 1) * 100:06d}"
        cells = []
        for j in range(len(codes)):
            cells += [f"{vals[i, j]:.0f}", None, f"{moes[i, j]:.0f}", None]
        rows.append([f"1400000US26001{tract}", f"Tract {i + 1}"] + cells + ["26", "001", tract])
    return rows


class FakeClient(CensusAPIClient):
    def __init__(self):
        super().__init__(api_key="", cache=None)

    def fetch(self, year, table_code, dataset=None, **kwargs):  # type: ignore[override]
        self.last_error = None
        return _payload(table_code)

    def fetch_variable_metadata(self, year, table_code, dataset=None):  # type: ignore[override]
        return {}


def _manifest(**over):
    m = {
        "schema_version": 1, "title": "R20 test", "authors": ["agent:claude"], "created": "2026-11-14T00:00:00Z",
        "releases": [2024], "geography": {"level": "tract", "state": "26", "codes": ["001"]},
        "variables": [{"name": "d0", "ref": "2024:B18101_003"}, {"name": "n0", "ref": "2024:B18101_004"},
                      {"name": "d1", "ref": "2024:B18101_006"}, {"name": "n1", "ref": "2024:B18101_007"},
                      {"name": "pov_tot", "ref": "2024:B17001_001"}, {"name": "pov_n", "ref": "2024:B17001_002"}],
        "derivations": [
            {"name": "asr", "op": "age_standardized", "as_percent": True, "standard": "us2000",
             "bands": [[0, 4], [5, 17]], "groups": [{"num": "n0", "den": "d0"}, {"num": "n1", "den": "d1"}]},
            {"name": "pov_rate", "op": "proportion", "num": "pov_n", "den": "pov_tot", "as_percent": True}],
        "missing": "complete_case", "confidence_level": 0.90, "correction": {"method": "holm", "family": "all"},
        "analyses": [{"id": "m1", "method": "fit_eiv", "formula": "asr ~ pov_rate", "replicates": "required"}],
        "hypotheses": [{"id": "H1", "statement": "s", "analysis": "m1", "statistic": "coefficient",
                        "term": "pov_rate", "direction": "greater"}],
    }
    m.update(over)
    return m


def _replicates(frame, names, seed=5):
    rng = np.random.default_rng(seed)
    parts = []
    for v in names:
        est = frame[v].to_numpy(float)
        r = est[:, None] + rng.normal(0, 1, (len(frame), 80)) * np.maximum(est, 1)[:, None] * 0.02
        parts.append(pd.DataFrame({"GEOID": frame["GEOID"], "Year": 2024, "variable": v, "estimate": est,
                                   **dict(zip(REPLICATE_COLUMNS, r.T))}))
    return pd.concat(parts, ignore_index=True)


class TestManifestRound20(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_create_fills_weights_and_hash_fixes_them(self):
        m = _manifest()
        res = create_manifest(m, path=os.path.join(self.dir, "m.json"))
        self.assertTrue(res["valid"], res["errors"])
        self.assertEqual(res["filled"][0]["derivation"], 0)
        w = stdz.standard_weights([[0, 4], [5, 17]])
        self.assertEqual(res["manifest"]["derivations"][0]["weights"], w)
        self.assertTrue(any("weights were omitted" in n for n in res["notes"]))
        with open(res["path"], encoding="utf-8") as f:
            written = json.load(f)
        self.assertEqual(manifest_hash(written), res["hash"])
        # a filled manifest validates as is
        self.assertEqual(validate_manifest(written, resolve=False), [])

    def test_validation_errors(self):
        cases = [
            (lambda d: d.pop("standard"), "'standard' is required"),
            (lambda d: d.update(standard="world"), "unknown standard"),
            (lambda d: d.update(bands=[[0, 4]]), "1 bands for 2 groups"),
            (lambda d: d.update(bands=[[0, 4], [6, 17]]), "contiguous"),
            (lambda d: d.update(weights=[0.5, 0.5]), "do not match"),
            (lambda d: d.update(standard="custom"), "needs explicit 'weights'"),
            (lambda d: d.update(groups=[{"num": "n0"}, {"num": "n1", "den": "d1"}]), "needs 'num' and 'den'"),
            (lambda d: d.update(groups=[{"num": "n0", "den": "zz"}, {"num": "n1", "den": "d1"}]),
             "'zz' is not an earlier"),
            (lambda d: d.update(num="n0"), "takes 'groups', not 'num'"),
        ]
        for mutate, msg in cases:
            m = _manifest()
            mutate(m["derivations"][0])
            errs = validate_manifest(m, resolve=False)
            self.assertTrue(any(msg in e for e in errs), (msg, errs))
        m = _manifest()
        m["derivations"][0].update(standard="custom", weights=[0.4, 0.6])
        self.assertEqual(validate_manifest(m, resolve=False), [])
        m = _manifest(aggregation={"mapping": {"26001000100": "a"}})
        self.assertTrue(any("cannot be combined with aggregation" in e for e in validate_manifest(m, resolve=False)))

    def test_fit_eiv_validation(self):
        m = _manifest()
        m["analyses"][0]["args"] = {"target": "these_areas"}
        self.assertTrue(any("fit_eiv takes no 'target'" in e for e in validate_manifest(m, resolve=False)))
        m = _manifest()
        m["analyses"][0].pop("replicates")
        self.assertTrue(any("fit_eiv needs replicates" in e for e in validate_manifest(m, resolve=False)))
        m = _manifest()
        m["analyses"][0]["args"] = {"model": "poisson"}
        self.assertTrue(any("'ols' or 'wls'" in e for e in validate_manifest(m, resolve=False)))

    def test_run_end_to_end(self):
        m = create_manifest(_manifest())["manifest"]
        probe = run_manifest(m, os.path.join(self.dir, "probe"), client=FakeClient(), use_cache=False)
        frame = probe["frame"]
        reps = _replicates(frame, ["d0", "n0", "d1", "n1", "pov_tot", "pov_n"])
        res = run_manifest(m, os.path.join(self.dir, "run"), client=FakeClient(), use_cache=False, replicates=reps)
        self.assertTrue(res["success"], res["deviations"])
        self.assertEqual(res["deviations"], [])
        out = res["frame"]
        self.assertTrue((out["asr_method"] == "replicate").all())
        with open(os.path.join(self.dir, "run", "bundle", "methods.md"), encoding="utf-8") as f:
            methods = f.read()
        self.assertIn("directly age-standardized rate", methods)
        self.assertIn(stdz.standard_info()["csv_sha256"], methods)
        self.assertIn("moment-corrected least squares", methods)
        with open(os.path.join(self.dir, "run", "bundle", "results", "m1.json"), encoding="utf-8") as f:
            m1 = json.load(f)
        self.assertEqual(m1["method"], "fit_eiv")
        with open(os.path.join(self.dir, "run", "bundle", "results", "hypotheses.json"), encoding="utf-8") as f:
            hyps = json.load(f)
        self.assertEqual(hyps["rows"][0]["id"], "H1")
        self.assertIsNotNone(hyps["rows"][0]["estimate"])


# --------------------------------------------------------------------------- fit_eiv


def _sim(n=3000, rel=0.7, rho=-0.5, seed=1, beta=2.0):
    rng = np.random.default_rng(seed)
    x = rng.normal(10, 3, n)
    g = rng.integers(0, 2, n)
    s2x = rng.uniform(0.2, 1.8, n) * 9 * (1 - rel) / rel
    s2y = rng.uniform(0.5, 1.5, n) * 4
    z1 = rng.standard_normal(n)
    z2 = rho * z1 + np.sqrt(1 - rho**2) * rng.standard_normal(n)
    xo = x + np.sqrt(s2x) * z1
    yo = 1 + beta * x + 0.5 * g + rng.normal(0, 2, n) + np.sqrt(s2y) * z2
    Z1 = rng.standard_normal((n, 80))
    Z2 = rho * Z1 + np.sqrt(1 - rho**2) * rng.standard_normal((n, 80))
    geo = [f"{i:011d}" for i in range(n)]
    frame = pd.DataFrame({"GEOID": geo, "x": xo, "x_se": np.sqrt(s2x), "y": yo, "y_se": np.sqrt(s2y),
                          "g": g.astype(str), "w": rng.uniform(0.5, 2, n)})
    xr = xo[:, None] + np.sqrt(s2x / 4)[:, None] * Z1
    yr = yo[:, None] + np.sqrt(s2y / 4)[:, None] * Z2
    reps = pd.concat([
        pd.DataFrame({"GEOID": geo, "variable": "x", "estimate": xo, **dict(zip(REPLICATE_COLUMNS, xr.T))}),
        pd.DataFrame({"GEOID": geo, "variable": "y", "estimate": yo, **dict(zip(REPLICATE_COLUMNS, yr.T))}),
    ], ignore_index=True)
    return frame, reps


class TestFitEiv(unittest.TestCase):
    def test_removes_attenuation_and_correlated_error_bias(self):
        frame, reps = _sim()
        res = fit_eiv("y ~ x + C(g)", frame, reps)
        c = res.coefficients.set_index("term")
        self.assertLess(abs(c.loc["x", "estimate"] - 2.0), 3 * c.loc["x", "se_total"])
        self.assertLess(c.loc["x", "naive_estimate"], 1.4)  # attenuated (rel 0.7: 1.4) and pulled down by rho < 0
        self.assertEqual(res.method, "fit_eiv")
        self.assertNotIn("C(g)[T.1]", res.diagnostics["reliability"])  # factors are error-free
        self.assertEqual(res.diagnostics["noisy_terms"], ["x"])
        self.assertAlmostEqual(res.diagnostics["reliability"]["x"], 0.7, delta=0.05)
        self.assertAlmostEqual(res.diagnostics["outcome_error_correlation"]["x"], -0.5, delta=0.05)
        self.assertEqual(c.loc["x", "ci_upper"] - c.loc["x", "estimate"],
                         c.loc["x", "estimate"] - c.loc["x", "ci_lower"])

    def test_without_error_equals_ols(self):
        frame, reps = _sim(n=300)
        flat = reps.copy()
        for col in REPLICATE_COLUMNS:
            flat[col] = flat["estimate"]
        res = fit_eiv("y ~ x + C(g)", frame, flat)
        c = res.coefficients.set_index("term")
        np.testing.assert_allclose(c["estimate"], c["naive_estimate"], rtol=1e-10)

    def test_interaction_and_transform_columns_get_their_own_error(self):
        frame, reps = _sim(n=1500)
        res = fit_eiv("y ~ x * C(g) + I(x ** 2)", frame, reps)
        self.assertEqual(set(res.diagnostics["noisy_terms"]), {"x", "x:C(g)[T.1]", "I(x ** 2)"})

    def test_wls_and_refusals(self):
        frame, reps = _sim(n=500)
        res = fit_eiv("y ~ x", frame, reps, model="wls", weights="w")
        self.assertEqual(res.model_type, "wls")
        with self.assertRaisesRegex(ValueError, "needs replicates"):
            fit_eiv("y ~ x", frame, None)
        with self.assertRaisesRegex(ValueError, "supports models"):
            fit_eiv("y ~ x", frame, reps, model="poisson")
        with self.assertRaisesRegex(ValueError, "error-free"):
            fit_eiv("y ~ x", frame, reps, model="wls", weights="x")
        noisy = reps.copy()
        sel = noisy["variable"] == "x"
        noisy.loc[sel, REPLICATE_COLUMNS] = noisy.loc[sel, ["estimate"]].to_numpy() + np.random.default_rng(0) \
            .normal(0, 40, (int(sel.sum()), 80))
        with self.assertRaisesRegex(ValueError, "not positive definite"):
            fit_eiv("y ~ x", frame, noisy)

    def test_strict_policy_refuses_missing_rows(self):
        frame, reps = _sim(n=200)
        part = reps[~((reps["variable"] == "x") & (reps["GEOID"] == frame["GEOID"].iloc[0]))]
        with self.assertRaises(IncompleteReplicatesError):
            fit_eiv("y ~ x", frame, part, replicate_policy="strict")
        res = fit_eiv("y ~ x", frame, part)  # flag: recorded
        self.assertIn("replicates_incomplete", res.diagnostics)


class TestReliabilityNote(unittest.TestCase):
    def test_fit_replicate_notes_low_and_uneven_reliability(self):
        frame, reps = _sim(n=600, rel=0.7)
        res = fit_replicate("y ~ x * C(g)", frame, reps)
        rel = res.diagnostics["covariate_reliability"]
        self.assertIn("x", rel["low"])
        self.assertTrue(any("fit_eiv" in n for n in res.notes))
        frame, reps = _sim(n=600, rel=0.99)
        res = fit_replicate("y ~ x", frame, reps)
        self.assertEqual(res.diagnostics["covariate_reliability"]["low"], [])
        self.assertFalse(any("COVARIATE MEASUREMENT ERROR" in n for n in res.notes))

    def test_uneven_groups(self):
        frame, reps = _sim(n=2000, rel=0.97)
        sel = (reps["variable"] == "x") & reps["GEOID"].isin(frame.loc[frame["g"] == "1", "GEOID"])
        dev = reps.loc[sel, REPLICATE_COLUMNS].to_numpy() - reps.loc[sel, ["estimate"]].to_numpy()
        reps.loc[sel, REPLICATE_COLUMNS] = reps.loc[sel, ["estimate"]].to_numpy() + 3 * dev
        mats = {"x": reps[reps["variable"] == "x"].set_index("GEOID").loc[frame["GEOID"], REPLICATE_COLUMNS]
                .to_numpy(float)}
        rel = covariate_reliability("y ~ x * C(g)", frame, mats)
        self.assertIn("x", rel["uneven"])
        g = rel["by_group"]["x"]["g"]
        self.assertGreater(g["0"] - g["1"], 0.1)


if __name__ == "__main__":
    unittest.main()
