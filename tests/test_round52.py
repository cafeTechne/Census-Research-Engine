# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 52: segregation with race/ethnicity groups, 4-5 groups, period contrasts, OH/PA (flags = audit)."""
import gzip
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from census import segregation as sg
from census.simulation import make_replicates, replicate_long

ROOT = Path(__file__).resolve().parents[1]
AUDIT = json.loads((ROOT/"docs/audits/segregation_groups_validation.json").read_text())
NAMES = {"D": "dissimilarity", "I": "isolation", "H": "theil_h"}


def _script():
    spec = importlib.util.spec_from_file_location("sgv", ROOT/"scripts/segregation_groups_validation.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def _top(x):
    return np.inf if x == "inf" else x


def test_ranges_equal_combined_audit():
    assert AUDIT["criterion_commit"] == "b19696b"
    n = {"two": 2, "four": 4, "five": 5}
    for key, procs in AUDIT["passed"].items():
        if key == "contrast":
            continue
        for proc, top in procs.items():
            name = NAMES[proc[0]]; variant = "naive" if proc.endswith("naive") else "bias_corrected"
            span = sg.REALISTIC_RANGES[(name, variant, n[key])]
            if top is None:
                assert span is None
            else:
                if (name, variant, n[key]) == ("dissimilarity", "bias_corrected", 2):
                    assert span[1] == .75 and _top(top) == 1.0   # Round 66 narrowed D on TX geometry
                else:
                    assert span[1] == _top(top)
                # Round 50 lower bound .15 kept for variants that failed Round 28 (corrected D)
                assert span[0] == (.15 if (name, variant) == ("dissimilarity", "bias_corrected") else 0.)
    # three groups stay at Round 50; six or more groups have no range
    assert sg.REALISTIC_RANGES[("theil_h", "bias_corrected", 3)] == (0., .50)
    assert not any(k[2] > 6 for k in sg.REALISTIC_RANGES)   # six groups since Round 57
    assert sg.MAX_VALIDATED_MEDIAN_CV == max(s[1] for s in sg.REALISTIC_RANGES.values() if s)
    # Round 51 clipped ranges never exceed the new two-group ranges
    for k, span in sg.CLIP_RANGES.items():
        if span is not None:
            # Round 57 extended the clipped ranges above .50; they stay within the unclipped ranges
            assert sg.REALISTIC_RANGES[k] is not None and span[1] <= sg.REALISTIC_RANGES[k][1]


def test_contrast_ranges_equal_audit():
    for proc, top in AUDIT["passed"]["contrast"].items():
        name = NAMES[proc[0]]; variant = "naive" if proc.endswith("naive") else "bias_corrected"
        assert sg.CONTRAST_RANGES[(name, variant)] == (0., _top(top))


def test_truth_file_and_pre_run_tallies():
    with gzip.open(ROOT/"docs/audits/segregation_groups_counts.csv.gz", "rt") as fh:
        df = pd.read_csv(fh, dtype={"GEOID": str, "county": str})
    assert df.groupby("release").size().to_dict() == {2019: 7731, 2024: 15028}
    d24 = df[df.release == 2024]
    # nonblack is every B03002 component except Black; nonhisp the published 002 line
    comp = d24[["white", "asian", "hisp", "other"]].sum(axis=1)
    assert (d24.nonblack >= comp - 1e-6).all() and (d24[["black", "nonblack", "nonhisp"]] >= 0).all().all()
    bins = {d: v["noise_bins"] for d, v in AUDIT["designs"].items()}
    assert sum(bins["black2"]) == 137 and sum(bins["pov_ohpa"]) == 146
    s = _script()
    assert s.NEG_RHO["race5"] == -.2 and s.NEG_RHO["black2"] == -.3


def test_combination_rule():
    s = _script()
    # a bin counts only if every judging design passes; unjudged bins before the first judged one are included
    comb, top = s.combine({"a": [None, True, True, None, None, None], "b": [None, None, True, False, None, None]},
                          ["a", "b"])
    assert comb == [None, True, True, False, None, None] and top == .50
    assert s.range_top([None, None, True, True, True, True]) == "inf"
    assert s.range_top([None, True, None, True, None, None]) == .30


def county(cv, groups=2, tracts=8, seed=52):
    rng = np.random.default_rng(seed)
    counts = rng.integers(60, 900, (tracts, groups)).astype(float)
    ids = [f"36061{i:06}" for i in range(1, tracts+1)]
    signs = rng.choice([-1., 1.], (tracts, groups, 80))
    reps = counts[:, :, None]*(1+cv/2*signs)    # 4/80 sum of squares = (cv * count)^2; non-negative for cv < 2
    names = [chr(97+g) for g in range(groups)]
    f = pd.DataFrame(counts, columns=names); f.insert(0, "GEOID", ids); f["Year"] = 2024
    r = replicate_long(ids, names, counts, reps); r["Year"] = 2024
    return f, r, names


def test_gate_at_high_noise_and_naive_variants():
    f, r, g = county(.8)
    out = sg.segregation_replicate(f, g, r).set_index("statistic")
    assert out.noise_level.between(.75, 1.).all()
    # Round 66: bias-corrected D now ends at .75 (failed on TX counties); isolation and H stay validated here
    assert not out.loc["dissimilarity", "validated"] and out.drop("dissimilarity").validated.all()
    naive = sg.segregation_replicate(f, g, r, bias_correction=False)
    assert not naive.validated.any()
    f, r, g = county(1.2)
    out = sg.segregation_replicate(f, g, r).set_index("statistic")
    assert out.validated.to_dict() == {"dissimilarity": False, "isolation": True, "theil_h": False}
    for k in (4, 5):
        f, r, g = county(1.2, groups=k)
        assert sg.segregation_replicate(f, g, r).validated.all()
    f, r, g = county(.3, groups=7)   # six groups validated since Round 57
    assert not sg.segregation_replicate(f, g, r).validated.any()


def test_infinite_noise_never_validated():
    f, r, g = county(.3)
    f.loc[:4, "a"] = 0.; r.loc[(r.variable == "a") & r.GEOID.isin(f.GEOID[:5]), [c for c in r if c.startswith("rep_")]] = 0.
    r.loc[(r.variable == "a") & r.GEOID.isin(f.GEOID[:5]), "estimate"] = 0.
    out = sg.segregation_replicate(f, g, r)
    assert np.isinf(out.noise_level).all() and not out.validated.any()


def two_releases(cv19, cv24):
    rows, reps = [], []
    for year, cv in ((2019, cv19), (2024, cv24)):
        f, r, g = county(cv, seed=year)
        f["Year"] = year; r["Year"] = year
        rows.append(f); reps.append(r)
    return pd.concat(rows, ignore_index=True), pd.concat(reps, ignore_index=True), g


def test_cross_release_contrast_gate():
    f, r, g = two_releases(.3, .4)
    res = sg.segregation_replicate(f, g, r)
    t = sg.segregation_test(res, "theil_h", "36061", release=2024, compare_release=2019)
    assert t["validated"] is True and t["se"] == pytest.approx(np.hypot(*res[res.statistic == "theil_h"].se))
    f, r, g = two_releases(.3, .6)       # both rows validated, larger noise .6 outside the contrast range
    res = sg.segregation_replicate(f, g, r)
    assert res.validated.all()
    t = sg.segregation_test(res, "theil_h", "36061", release=2024, compare_release=2019)
    assert t["validated"] is False and "cross-release" in t["confirmatory_refusal"]
    # same-release one-area test unaffected
    assert sg.segregation_test(res, "theil_h", "36061", null_value=.1, release=2024)["validated"] is True


def test_rule_text_mirrored():
    from census import mcp_profiles
    proto = (ROOT/"docs/agent_protocol.md").read_text()
    recipe = (ROOT/"docs/recipes/segregation.md").read_text()
    server = (ROOT/"census/mcp_instructions.py").read_text()
    for text in (proto, recipe, mcp_profiles.CORE_INSTRUCTIONS, server):
        flat = " ".join(text.split())
        assert "Round 52" in flat or "Rounds 50/52" in flat
    for text in (proto, recipe):
        assert "below .30 for naive isolation/H" not in text and "Race groups and contrasts were not in the" not in text
        assert "infinite noise level" in text.lower() or "An infinite noise level" in text
    assert "naive isolation/H exploratory" in mcp_profiles.CORE_INSTRUCTIONS
