# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 21 Part 2: enforced circularity rule, USALEEP and County Health Rankings connectors, rate
apportionment, WONDER export reader, fit_eiv cluster jackknife, diverging maps, run_variant and the
MCP guidance (PLAN_ROUND_21 sections 10-13). Offline."""

import hashlib
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

import numpy as np
import pandas as pd

from census import health_sources as hs
from census import vital_records as vr
from census.manifest import create_manifest, validate_manifest
from census.models import fit_eiv
from tests.test_round20 import _manifest, _sim


def _usaleep_csv(rows):
    out = ['"Tract ID","STATE2KX","CNTY2KX","TRACT2KX","e(0)","se(e(0))","Abridged life table flag"']
    out += [f"{g},{g[:2]},{g[2:5]},{g[5:]},{e},{s},{f}" for g, e, s, f in rows]
    return ("\n".join(out) + "\n").encode()


def _chr_csv(counties, code="v127", flag_col=True):
    names = ["State FIPS Code", "County FIPS Code", "5-digit FIPS Code", "State Abbreviation", "Name",
             "Release Year", f"{code} raw value", f"{code} numerator", f"{code} denominator", f"{code} CI low",
             f"{code} CI high"] + ([f"{code} flag"] if flag_col else [])
    codes = ["statecode", "countycode", "fipscode", "state", "county", "year", f"{code}_rawvalue",
             f"{code}_numerator", f"{code}_denominator", f"{code}_cilow", f"{code}_cihigh"] + \
        ([f"{code}_flag"] if flag_col else [])
    lines = [",".join(names), ",".join(codes), "00,000,00000,US,United States,2025,350,1,1,349,351" +
             (",0" if flag_col else "")]
    for fips, v, flag in counties:
        st, co = fips[:2], fips[2:]
        val = "" if flag == 2 else str(v)
        lo, hi = ("", "") if flag == 2 else (str(v - 19.6), str(v + 19.6))
        lines.append(f"{st},{co},{fips},MI,County {co},2025,{val},100,30000,{lo},{hi}" + (f",{flag}" if flag_col else ""))
    lines.append("26,000,26000,MI,Michigan,2025,400,1,1,399,401" + (",0" if flag_col else ""))
    return ("\n".join(lines) + "\n").encode()


WONDER = '''"Notes"\t"County"\t"County Code"\tDeaths\tPopulation\tCrude Rate\tAge Adjusted Rate\tAge Adjusted Rate Standard Error
\t"Alpha County, MI"\t"26001"\t150\t30000\t500.0\t420.5\t35.1
\t"Beta County, MI"\t"26003"\tSuppressed\t5000\tSuppressed\tSuppressed\tSuppressed
\t"Gamma County, MI"\t"26005"\t15\t6000\t250.0 (Unreliable)\t230.0 (Unreliable)\t60.2
"Total"\t\t\t170\t41000\t414.6\t400.0\t30.0
"---"
"Dataset: Underlying Cause of Death, 2018-2023, Single Race"
"Query Parameters:"
"States: Michigan (26)"
"Ten-Year Age Groups: < 1 year; 1-4 years; 5-14 years; 15-24 years; 25-34 years; 35-44 years; 45-54 years; 55-64 years; 65-74 years"
"Year/Month: 2020; 2021; 2022"
"Group By: County"
"---"
"Help: See https://wonder.cdc.gov/wonder/help/ucd-expanded.html for more information."
"---"
"Query Date: Nov 15, 2026 10:00:00 AM"
'''


class Tmp(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        env = mock.patch.dict(os.environ, {"CENSUS_HEALTH_DIR": os.path.join(self.dir, "health")})
        env.start()
        self.addCleanup(env.stop)


class TestUsaleep(Tmp):
    ROWS = [("26001970100", 78.1, 1.25, 3), ("26001970400", 74.5, 1.55, 1), ("26001970500", 75.6, 1.25, 2)]

    def test_parse_drops_fully_predicted(self):
        rows = pd.read_csv(pd.io.common.BytesIO(_usaleep_csv(self.ROWS)), dtype=str)
        out, rec = hs.parse_usaleep(rows, "le")
        self.assertEqual(list(out["GEOID"]), ["26001970100", "26001970400"])
        self.assertEqual(rec["dropped_fully_predicted"], 1)
        self.assertEqual(rec["flag_counts"], {3: 1, 1: 1, 2: 1})
        keep, rec = hs.parse_usaleep(rows, "le", include_predicted=True)
        self.assertEqual(len(keep), 3)
        bad = rows.copy()
        bad.loc[0, "Tract ID"] = "2600197"
        with self.assertRaisesRegex(hs.HealthSourceError, "malformed"):
            hs.parse_usaleep(bad, "le")

    def test_fetch_cache_and_missing_states(self):
        urls = []

        def fetch(u):
            urls.append(u)
            return _usaleep_csv(self.ROWS)

        got = hs.fetch_usaleep(["26"], fetch=fetch)
        self.assertEqual(urls, ["https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/NVSS/USALEEP/CSV/MI_A.CSV"])
        self.assertEqual(len(got["files"][0]["sha256"]), 64)
        hs.fetch_usaleep(["26"], fetch=fetch)
        self.assertEqual(len(urls), 1)  # cached
        # New York: the state file plus New York City's own file
        ny = {"NY_A": [("36001000100", 78.0, 1.0, 3)], "NYC_A": [("36005000200", 84.1, 3.2, 3)]}
        got = hs.fetch_usaleep(["36"], fetch=lambda u: _usaleep_csv(ny[u.rsplit("/", 1)[1][:-4]]))
        self.assertEqual(sorted(got["rows"]["Tract ID"]), ["36001000100", "36005000200"])
        self.assertIn("NYC", got["dataset"])
        with self.assertRaisesRegex(hs.HealthSourceError, "outside state"):
            hs.fetch_usaleep(["55"], fetch=lambda u: _usaleep_csv(self.ROWS), cache_dir=tempfile.mkdtemp())

    def test_load_external_native_and_apportioned(self):
        e = {"name": "le", "source": "usaleep", "release": 2018, "measure": "E0"}
        wide, prov = hs.load_external([e], "tract", ["26"], fetch=lambda u: _usaleep_csv(self.ROWS))
        self.assertEqual(len(wide), 2)
        self.assertEqual(prov[0]["predicted"]["dropped_fully_predicted"], 1)
        self.assertEqual(prov[0]["kinds"], {"E0": "partly_model_based"})
        cw = pd.DataFrame({"source_geoid": ["26001970100", "26001970400"],
                           "target_geoid": ["26001970100", "26001970100"], "mass": [3000.0, 1000.0]})
        wide, prov = hs.load_external([dict(e, apportion_to=2020)], "tract", ["26"],
                                      fetch=lambda u: _usaleep_csv(self.ROWS), crosswalk=cw)
        self.assertAlmostEqual(float(wide["le"].iloc[0]), (3 * 78.1 + 74.5) / 4)
        self.assertIn("apportionment", prov[0])


class TestApportion(unittest.TestCase):
    def test_types_values_se_and_split_policy(self):
        vals = pd.DataFrame({"GEOID": ["a", "b", "c", "d"], "v": [10.0, 20.0, 30.0, np.nan],
                             "v_se": [1.0, 2.0, 3.0, np.nan]})
        cw = pd.DataFrame({"source_geoid": ["a", "b", "b", "c", "c", "d"],
                           "target_geoid": ["T1", "T2", "T3", "T3", "T4", "T4"],
                           "mass": [100.0, 50.0, 50.0, 100.0, 95.0, 5.0]})
        kinds = hs.target_relationships(cw)
        self.assertEqual(kinds.to_dict(), {"T1": "1:1", "T2": "split", "T3": "merged/complex",
                                           "T4": "merged/complex"})
        out, rec = hs.apportion_rates(vals, "v", cw)
        o = out.set_index("GEOID")
        self.assertEqual(o.loc["T1", "v"], 10.0)
        self.assertTrue(np.isnan(o.loc["T2", "v"]))  # split child: missing by default
        self.assertAlmostEqual(o.loc["T3", "v"], (50 * 20 + 100 * 30) / 150)
        self.assertAlmostEqual(o.loc["T3", "v_se"], np.sqrt((50 / 150) ** 2 * 4 + (100 / 150) ** 2 * 9))
        self.assertAlmostEqual(o.loc["T4", "v"], 30.0)  # 95% covered >= 0.9
        self.assertEqual(rec["split_targets_left_missing"], 1)
        self.assertIn("left missing", rec["method"])
        self.assertNotIn("inherits", rec["method"])
        out, rec = hs.apportion_rates(vals, "v", cw, split="inherit", min_coverage=0.99)
        self.assertIn("NOT validated", rec["method"])
        o = out.set_index("GEOID")
        self.assertEqual(o.loc["T2", "v"], 20.0)
        self.assertTrue(np.isnan(o.loc["T4", "v"]))  # below coverage
        with self.assertRaises(ValueError):
            hs.apportion_rates(vals, "v", cw, split="borrow")


class TestCHR(Tmp):
    def test_parse(self):
        raw = _chr_csv([("26001", 400.0, 0), ("26003", 0, 2), ("36001", 300.0, 1)])
        out = hs.parse_chr(raw, {"v127": "pm"}, ["26"])
        self.assertEqual(list(out["GEOID"]), ["26001", "26003"])  # US, state and other-state rows dropped
        o = out.set_index("GEOID")
        self.assertAlmostEqual(o.loc["26001", "pm_se"], 39.2 / (2 * hs.Z95))
        self.assertTrue(np.isnan(o.loc["26003", "pm"]))
        self.assertEqual(o.loc["26003", "pm_flag"], 2)
        self.assertEqual(o.loc["26001", "pm_denominator"], 30000)
        both = hs.parse_chr(raw, {"v127": "pm"})
        self.assertEqual(both.set_index("GEOID").loc["36001", "pm_flag"], 1)
        with self.assertRaisesRegex(hs.HealthSourceError, "code"):
            hs.parse_chr(b"a,b\n1,2\n3,4\n", {"v127": "pm"})
        with self.assertRaisesRegex(hs.HealthSourceError, "no column"):
            hs.parse_chr(raw, {"v001": "yp"})
        bad = raw.replace(b",400.0,", b",abc,")
        with self.assertRaisesRegex(hs.HealthSourceError, "non-numeric"):
            hs.parse_chr(bad, {"v127": "pm"})

    def test_load_external_cached(self):
        calls = []

        def fetch(u):
            calls.append(u)
            return _chr_csv([("26001", 400.0, 0)])

        e = {"name": "pm", "source": "chr", "release": 2025, "measure": "v127"}
        wide, prov = hs.load_external([e], "county", ["26"], fetch=fetch)
        self.assertEqual(float(wide["pm"].iloc[0]), 400.0)
        self.assertEqual(prov[0]["kinds"], {"v127": "direct"})
        self.assertIn("County Health Rankings", prov[0]["citation"])
        hs.load_external([e], "county", ["26"], fetch=fetch)
        self.assertEqual(len(calls), 1)


class TestValidateNewSources(unittest.TestCase):
    def test_entries(self):
        tract = {"level": "tract", "states": ["26"]}
        county = {"level": "county", "states": ["26"]}
        le = {"name": "le", "source": "usaleep", "release": 2018, "measure": "E0"}
        self.assertEqual(hs.validate_external([le], tract, [2015], []), [])
        errs = hs.validate_external([le], tract, [2024], [])
        self.assertTrue(any("2010 tracts" in e and "apportion_to 2020" in e for e in errs), errs)
        self.assertEqual(hs.validate_external([dict(le, apportion_to=2020)], tract, [2024], []), [])
        self.assertTrue(hs.validate_external([dict(le, apportion_to=2010)], tract, [2015], []))
        self.assertTrue(hs.validate_external([dict(le, min_coverage=0.9)], tract, [2015], []))
        self.assertTrue(hs.validate_external([dict(le, split="inherit")], tract, [2015], []))
        self.assertEqual(hs.validate_external([dict(le, apportion_to=2020, split="inherit")], tract, [2024], []), [])
        self.assertTrue(hs.validate_external([le], county, [2015], []))  # tract only
        pm = {"name": "pm", "source": "chr", "release": 2025, "measure": "v127"}
        self.assertEqual(hs.validate_external([pm], county, [2022], []), [])
        errs = hs.validate_external([dict(pm, measure="v069")], county, [2022], [])
        self.assertTrue(any("ACS-derived" in e and "B15003" in e for e in errs), errs)
        self.assertTrue(hs.validate_external([pm], tract, [2022], []))
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        p1, p2 = os.path.join(d, "heart.txt"), os.path.join(d, "cancer.txt")
        for p, txt in ((p1, WONDER), (p2, WONDER.replace("150", "151"))):
            with open(p, "w", encoding="utf-8") as f:
                f.write(txt)
        sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()  # noqa: E731
        w = {"name": "d", "source": "wonder", "measure": "deaths", "file": p1, "sha256": sha(p1)}
        self.assertEqual(hs.validate_external([w], county, [2022], []), [])
        # two exports with the same measure (two causes of death) are allowed
        w2 = dict(w, name="d2", file=p2, sha256=sha(p2))
        self.assertEqual(hs.validate_external([w, w2], county, [2022], []), [])
        self.assertTrue(any("name each measure once" in e
                            for e in hs.validate_external([w, dict(w, name="d3")], county, [2022], [])))
        self.assertTrue(hs.validate_external([dict(w, sha256="abc")], county, [2022], []))
        errs = hs.validate_external([dict(w, sha256="0" * 64)], county, [2022], [])
        self.assertTrue(any("not the pinned" in e for e in errs), errs)  # checked before registration
        errs = hs.validate_external([dict(w, file="no/such/export.txt")], county, [2022], [])
        self.assertTrue(any("not found" in e and "repository root" in e for e in errs), errs)
        self.assertTrue(hs.validate_external([w], tract, [2022], []))
        self.assertTrue(hs.validate_external([{k: v for k, v in w.items() if k != "file"}], county, [2022], []))
        # a malformed apportion_to is reported, not raised
        for bad in ("x", [2020], True):
            errs = hs.validate_external([dict(le, apportion_to=bad)], tract, [2024], [])
            self.assertTrue(any("apportion_to must be 2020" in e for e in errs), errs)

    def test_registry_summary(self):
        reg = hs.registry_summary()
        self.assertIn("such as diabetes", reg["rule"])
        self.assertEqual(set(reg["sources"]), {"places", "usaleep", "chr", "wonder"})
        self.assertIn("B18101", reg["sources"]["places"]["measures"]["DISABILITY"]["acs_equivalent"])
        self.assertNotIn("acs_equivalent", reg["sources"]["places"]["measures"]["DIABETES"])
        json.dumps(reg)
        with self.assertRaises(ValueError):
            hs.registry_summary("brfss")


def _county_manifest(external, formula, term):
    m = _manifest()
    m["geography"] = {"level": "county", "states": ["26"]}
    m["external"] = [external]
    m["analyses"] = [{"id": "m1", "method": "fit_eiv", "formula": formula, "replicates": "required"}]
    m["hypotheses"][0]["term"] = term
    return m


class TestRuleAcrossSources(unittest.TestCase):
    def test_chr(self):
        direct = {"name": "pm", "source": "chr", "release": 2025, "measure": "v127"}
        m = _county_manifest(direct, "pm ~ pov_rate + asr", "pov_rate")
        res = create_manifest(m, resolve=False)
        self.assertTrue(res["valid"], res["errors"])
        self.assertTrue(any("direct external estimate" in n for n in res["notes"]), res["notes"])
        diab = dict(direct, name="diab", measure="v060")
        errs = validate_manifest(_county_manifest(diab, "diab ~ pov_rate + asr", "pov_rate"), resolve=False)
        self.assertTrue(any("CIRCULARITY R2" in e for e in errs), errs)
        dis = dict(direct, name="cdis", measure="v180")
        errs = validate_manifest(_county_manifest(dis, "cdis ~ pov_rate", "pov_rate"), resolve=False)
        self.assertTrue(any("CIRCULARITY R1" in e for e in errs), errs)

    def test_usaleep_education_term(self):
        m = _manifest(releases=[2015])
        m["variables"] += [{"name": "ed_tot", "ref": "2015:B15002_001"}, {"name": "ed_ba", "ref": "2015:B15002_015"}]
        for v in m["variables"]:
            v["ref"] = "2015:" + v["ref"].split(":")[1]
        m["derivations"].append({"name": "pct_ba", "op": "proportion", "num": "ed_ba", "den": "ed_tot"})
        m["external"] = [{"name": "le", "source": "usaleep", "release": 2018, "measure": "E0"}]
        m["analyses"] = [{"id": "m1", "method": "fit_eiv", "formula": "le ~ pct_ba + pov_rate", "replicates": "required"}]
        m["hypotheses"][0]["term"] = "pct_ba"
        errs = validate_manifest(m, resolve=False)
        self.assertTrue(any("CIRCULARITY R2" in e and "education" in e for e in errs), errs)
        m["hypotheses"][0]["term"] = "pov_rate"  # poverty is not a USALEEP model input
        self.assertEqual(validate_manifest(m, resolve=False), [])


class TestWonder(Tmp):
    def _file(self, text=WONDER):
        p = os.path.join(self.dir, "export.txt")
        with open(p, "w", encoding="utf-8", newline="") as f:  # hash the exact bytes on Windows too
            f.write(text)
        return p, hashlib.sha256(text.encode()).hexdigest()

    def test_read(self):
        p, _ = self._file()
        exp = vr.read_wonder_export(p)
        r = exp["rows"].set_index("GEOID")
        self.assertEqual(list(r.index), ["26001", "26003", "26005"])  # Total dropped
        self.assertTrue(r.loc["26003", "deaths_suppressed"])
        self.assertTrue(np.isnan(r.loc["26003", "deaths"]))
        self.assertEqual((r.loc["26003", "deaths_lower_bound"], r.loc["26003", "deaths_upper_bound"]), (1, 9))
        self.assertTrue(r.loc["26005", "unreliable"])
        self.assertFalse(r.loc["26001", "unreliable"])
        self.assertAlmostEqual(r.loc["26001", "crude_rate_se"], 500.0 / np.sqrt(150))
        self.assertEqual(exp["footer"]["dataset"], "Underlying Cause of Death, 2018-2023, Single Race")
        self.assertEqual(exp["footer"]["parameters"]["Year/Month"], "2020; 2021; 2022")
        self.assertEqual(exp["footer"]["query_date"], "Nov 15, 2026 10:00:00 AM")

    def test_zero_deaths_keep_finite_se(self):
        p, sha = self._file(WONDER.replace("\t15\t6000\t250.0 (Unreliable)", "\t0\t6000\t0.0 (Unreliable)"))
        r = vr.read_wonder_export(p)["rows"].set_index("GEOID")
        self.assertAlmostEqual(r.loc["26005", "crude_rate_se"], 1e5 / 6000)
        out, _ = vr.load_wonder_measure(p, sha, "deaths", "d")
        self.assertEqual(out.set_index("GEOID").loc["26005", "d_se"], 1.0)

    def test_garwood(self):
        lo, hi = vr.garwood_interval(np.array([0.0, 10.0]))
        self.assertAlmostEqual(lo[0], 0.0)
        self.assertAlmostEqual(hi[0], 3.6889, places=3)
        self.assertAlmostEqual(lo[1], 4.7954, places=3)
        self.assertAlmostEqual(hi[1], 18.3904, places=3)

    def test_refusals_and_measure(self):
        p, sha = self._file()
        out, rec = vr.load_wonder_measure(p, sha, "age_adjusted_rate", "aa")
        self.assertEqual(out.set_index("GEOID").loc["26001", "aa_se"], 35.1)
        self.assertEqual(list(out["aa_flag"]), [0, 2, 1])
        self.assertEqual(rec["suppressed_units"], 1)
        with self.assertRaisesRegex(vr.WonderExportError, "pinned"):
            vr.load_wonder_measure(p, "0" * 64, "deaths", "d")
        p2, sha2 = self._file(WONDER.split('"---"')[0])
        with self.assertRaisesRegex(vr.WonderExportError, "footer"):
            vr.load_wonder_measure(p2, sha2, "deaths", "d")
        no_se = WONDER.replace("\tAge Adjusted Rate Standard Error", "").replace("\t35.1", "") \
            .replace("\tSuppressed\n", "\n", 1).replace("\t60.2", "").replace("\t30.0", "")
        p3, sha3 = self._file(no_se)
        with self.assertRaisesRegex(vr.WonderExportError, "Standard Error"):
            vr.load_wonder_measure(p3, sha3, "age_adjusted_rate", "aa")
        out, _ = vr.load_wonder_measure(p3, sha3, "deaths", "d")
        self.assertEqual(out.set_index("GEOID").loc["26003", "d_upper_bound"], 9)

    def test_via_load_external(self):
        p, sha = self._file()
        e = {"name": "aa", "source": "wonder", "measure": "age_adjusted_rate", "file": p, "sha256": sha}
        wide, prov = hs.load_external([e], "county", ["26"])
        self.assertEqual(len(wide), 3)
        self.assertEqual(prov[0]["files"][0]["sha256"], sha)
        self.assertEqual(prov[0]["kinds"], {"age_adjusted_rate": "direct"})


class TestJackknife(unittest.TestCase):
    def _data(self):
        frame, reps = _sim(n=600)
        frame["GEOID"] = [f"{i % 24:05d}{i:06d}" for i in range(len(frame))]
        reps["GEOID"] = np.tile(frame["GEOID"].to_numpy(), len(reps) // len(frame))
        return frame, reps

    def test_matches_manual_delete_one(self):
        frame, reps = self._data()
        res = fit_eiv("y ~ x", frame, reps, cluster="GEOID.str[:5]", cluster_se="jackknife")
        groups = frame["GEOID"].str[:5]
        bs = []
        for g in sorted(groups.unique()):
            keep = set(frame.loc[groups != g, "GEOID"])
            r = fit_eiv("y ~ x", frame[frame.GEOID.isin(keep)], reps[reps.GEOID.isin(keep)])
            bs.append(r.coefficients.set_index("term")["estimate"].to_numpy())
        bs = np.array(bs)
        G = len(bs)
        se = np.sqrt((G - 1) / G * ((bs - bs.mean(axis=0)) ** 2).sum(axis=0))
        self.assertTrue(np.allclose(res.coefficients["se_total"].to_numpy(), se, rtol=1e-8))
        self.assertIn("x", res.diagnostics["se_total_cr1"])
        self.assertTrue(any("jackknife" in n for n in res.notes))

    def test_cluster_fixed_effects_and_errors(self):
        frame, reps = self._data()
        frame["cty"] = frame["GEOID"].str[:5]
        res = fit_eiv("y ~ x + C(cty)", frame, reps, cluster="GEOID.str[:5]", cluster_se="jackknife")
        jk = res.coefficients.set_index("term")["se_total"]
        cr1 = pd.Series(res.diagnostics["se_total_cr1"])
        self.assertTrue(np.isfinite(jk["x"]))
        # deleting the reference county must not inflate the intercept (collinear refit left out)
        self.assertLess(jk["Intercept"], 1.5 * cr1["Intercept"])
        with self.assertRaisesRegex(ValueError, "needs cluster"):
            fit_eiv("y ~ x", frame, reps, cluster_se="jackknife")
        with self.assertRaisesRegex(ValueError, "cluster_se"):
            fit_eiv("y ~ x", frame, reps, cluster="GEOID.str[:5]", cluster_se="cr2")

    def test_manifest_arg(self):
        from tests.test_round21 import _ext_manifest
        m = _ext_manifest()
        m["analyses"][0]["args"] = {"cluster": "GEOID.str[:5]", "cluster_se": "jackknife"}
        self.assertEqual(validate_manifest(m, resolve=False), [])
        m["analyses"][0]["args"] = {"cluster_se": "jackknife"}
        self.assertTrue(any("cluster_se" in e for e in validate_manifest(m, resolve=False)))


class TestJoinLimitPerSource(unittest.TestCase):
    def test_per_variable_shares_and_limits(self):
        frame = pd.DataFrame({"GEOID": [f"{i:011d}" for i in range(10)], "x": 1.0})
        ext = pd.DataFrame({"GEOID": frame["GEOID"], "le": [1.0] * 8 + [np.nan] * 2, "diab": 1.0})
        _, rec = hs.join_external(frame, ext, ["le", "diab"], ["x"])
        self.assertEqual(rec["missing_share_by_variable"], {"le": 0.2, "diab": 0.0})
        lims = hs.join_limit([{"name": "le", "source": "usaleep"}, {"name": "diab", "source": "places"}])
        self.assertEqual(lims, {"le": 0.25, "diab": 0.05})  # USALEEP keeps its own limit when combined


class TestDiverging(unittest.TestCase):
    def test_breaks(self):
        from census.maps import class_breaks, diverging_breaks
        x = np.r_[np.linspace(-4, 4, 99), 50.0]
        b = diverging_breaks(x, k=5)
        self.assertEqual(len(b), 5)
        self.assertAlmostEqual(b[1] + b[2], 0.0, places=9)  # symmetric about 0: middle class straddles it
        self.assertEqual(b[-1], 50.0)  # the outlier lands in the top class
        self.assertTrue(np.allclose(class_breaks(x, "diverging", 5), b))
        self.assertTrue(np.allclose(diverging_breaks(x + 10, 4, center=10)[:3] - 10,
                                    diverging_breaks(x, 4)[:3]))


class TestRunVariant(unittest.TestCase):
    def test_variant_on_synthetic_run(self):
        from census.manifest import run_variant
        from tests.test_round21 import FakeFetch, TestManifestExternal, _ext_manifest
        case = TestManifestExternal("test_run_end_to_end")
        case.setUp()
        try:
            res = case._run(_ext_manifest(), FakeFetch(measure="DIABETES"))
            self.assertTrue(res["success"], res["deviations"])
            run_dir = os.path.join(case.dir, "run")
            out = run_variant(run_dir, "m1", formula="places_dis ~ asr", drop_prefixes=["26001000"])
            self.assertEqual(out["analysis_status"], "exploratory")
            self.assertTrue(os.path.exists(out["path"]))
            self.assertEqual(out["variant"]["formula"], "places_dis ~ asr")
            self.assertLess(out["units"], len(pd.read_parquet(os.path.join(run_dir, "analysed",
                                                                           "analysis_frame.parquet"))))
            with self.assertRaisesRegex(ValueError, "not in the manifest"):
                run_variant(run_dir, "m9")
            with self.assertRaisesRegex(ValueError, "label"):
                run_variant(run_dir, "m1", label="../../x")
            runjson = os.path.join(run_dir, "bundle", "results", "run.json")
            saved = open(runjson, encoding="utf-8").read()
            bad = json.loads(saved)
            bad["analysed_data"]["replicates"] = {"error": "write failed"}
            with open(runjson, "w", encoding="utf-8") as f:
                json.dump(bad, f)
            with self.assertRaisesRegex(ValueError, "no analysed replicates"):
                run_variant(run_dir, "m1")
            from census.workflows_inference import run_variant as tool
            self.assertFalse(tool(run_dir, "m1")["success"])
            with open(runjson, "w", encoding="utf-8") as f:
                f.write(saved)
            with open(os.path.join(run_dir, "analysed", "analysis_frame.parquet"), "ab") as f:
                f.write(b"x")
            with self.assertRaisesRegex(ValueError, "does not match run.json"):
                run_variant(run_dir, "m1")
        finally:
            case.doCleanups()


class TestMcpGuidance(unittest.TestCase):
    def test_instructions_recipe_and_tool(self):
        import mcp_server
        from census import mcp_profiles, recipes, workflows_inference
        sentence = "measures the ACS lacks, such as"
        self.assertIn(sentence, mcp_server.INSTRUCTIONS.replace("\n", " "))
        self.assertIn("B18101", mcp_server.INSTRUCTIONS)
        self.assertIn("such as diabetes", mcp_profiles.CORE_INSTRUCTIONS.replace("\n", " "))
        r = recipes.get_recipe("external_health_outcome")
        self.assertTrue(r["success"])
        self.assertIn("such as diabetes", r["steps"])
        out = workflows_inference.list_health_sources()
        self.assertTrue(out["success"])
        self.assertIn("such as diabetes", out["summary"])
        self.assertFalse(workflows_inference.list_health_sources("brfss")["success"])
        with open(os.path.join(os.path.dirname(__file__), "..", "docs", "agent_protocol.md"), encoding="utf-8") as f:
            self.assertIn("## 16. External health data", f.read())
        self.assertTrue(callable(mcp_server.list_health_sources) and callable(mcp_server.run_variant))


if __name__ == "__main__":
    unittest.main()
