# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 50: segregation under realistic ACS error (flags = audit, noise-level gate, rule text)."""
import gzip
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from census import segregation as sg
from census.simulation import make_replicates, replicate_long
from census.variance import REPLICATE_COLUMNS

ROOT = Path(__file__).resolve().parents[1]
AUDIT = json.loads((ROOT/"docs/audits/segregation_realistic_validation.json").read_text())
NAMES = {"D": "dissimilarity", "I": "isolation", "H": "theil_h"}


def _script():
    spec = importlib.util.spec_from_file_location("srv", ROOT/"scripts/segregation_realistic_validation.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def test_ranges_equal_audit():
    assert AUDIT["criterion_commit"] == "686d121"
    n = {"two": 2, "three": 3}
    for design, procs in AUDIT["passed"].items():
        for proc, top in procs.items():
            name = NAMES[proc[0]]; variant = "naive" if proc.endswith("naive") else "bias_corrected"
            span = sg.REALISTIC_RANGES[(name, variant, n[design])]
            if top is None:
                assert span is None
            elif design == "two" and variant == "naive":
                assert span is None      # Round 52: naive isolation/H failed race groups at .15-.50
            elif design == "two":
                assert span[1] >= top    # Round 52 widened the two-group ranges (tests/test_round52.py)
            else:
                assert span is not None and span[1] == pytest.approx(top)
                # Variants that failed Round 28 at CV .15 start at .15 (conservative engine restriction).
                r28 = sg.SEGREGATION_VALIDATED[name][variant]
                assert span[0] == (0. if r28 or n[design] == 3 else .15)
    assert sg.MAX_VALIDATED_MEDIAN_CV == max(s[1] for s in sg.REALISTIC_RANGES.values() if s)
    # Defaults: the variant with the widest validated range.
    assert sg.DEFAULT_BIAS_CORRECTION == {"dissimilarity": True, "isolation": True, "theil_h": True}


def test_counts_file_matches_criterion_tally():
    with gzip.open(ROOT/"docs/audits/segregation_realistic_counts.csv.gz", "rt") as fh:
        df = pd.read_csv(fh, dtype={"GEOID": str, "county": str})
    assert len(df) == 8414 and df.county.nunique() == 145
    assert (df.drop(columns=["GEOID", "county"]) >= 0).all().all()
    assert AUDIT["designs"]["two"]["noise_bins"] == [0, 88, 49, 0]
    assert AUDIT["designs"]["three"]["noise_bins"] == [9, 117, 11, 0]


def test_noise_level_definition():
    counts = np.array([[10., 90.], [20., 80.], [0., 50.], [0., 0.]])
    se = np.array([[3., 9.], [4., 8.], [2., 5.], [0., 0.]])
    # populated tracts: first three; group CVs (.3, .2, inf) and (.1, .1, .1) -> medians .3 and .1
    assert sg.noise_level(counts, se) == pytest.approx(.3)
    assert sg.noise_level(np.zeros((2, 2)), np.zeros((2, 2))) == np.inf


def test_gamma_copula_moments_and_rounding():
    srv = _script()
    rng = np.random.default_rng(0)
    mean = np.tile([[200., 50.]], (40000, 1)); sd = np.tile([[40., 20.]], (40000, 1))
    x = srv.gamma_copula(rng, mean, sd, -.3)
    assert (x >= 0).all() and np.all(x == np.rint(x))
    assert x.mean(axis=0) == pytest.approx([200, 50], rel=.01)
    assert x.std(axis=0) == pytest.approx([40, 20], rel=.03)
    assert np.corrcoef(x.T)[0, 1] < -.2
    assert np.all(srv.gamma_copula(rng, np.zeros((3, 2)), np.ones((3, 2)), 0.) == 0)


def county(cv, tracts=8, seed=50, alternating=False):
    rng = np.random.default_rng(seed)
    counts = np.column_stack((rng.integers(80, 400, tracts), rng.integers(300, 1200, tracts))).astype(float)
    ids = [f"36061{i:06}" for i in range(1, tracts+1)]
    if alternating:   # deviations +/- SE/2 (4/80 sum = SE^2) with random signs: non-negative at high CV
        signs = rng.choice([-1., 1.], (tracts, 2, 80))
        reps = counts[:, :, None]*(1+cv/2*signs)
    else:
        reps = make_replicates(counts, cv*counts, rng)
    f = pd.DataFrame({"GEOID": ids, "Year": 2024, "a": counts[:, 0], "b": counts[:, 1]})
    r = replicate_long(ids, ["a", "b"], counts, reps); r["Year"] = 2024
    return f, r


def test_gate_validates_realistic_noise_with_defaults():
    f, r = county(.25)
    out = sg.segregation_replicate(f, ["a", "b"], r).set_index("statistic")
    assert out.bias_correction.all() and out.validated.all()
    assert (out.max_count_cv > .15).all() and (out.noise_level.between(.15, .5)).all()
    naive = sg.segregation_replicate(f, ["a", "b"], r, bias_correction=False).set_index("statistic")
    assert not naive.loc["dissimilarity", "validated"]          # naive D failed realistic error
    # Round 50 validated naive isolation/H at .15-.30; Round 52 race groups failed them there.
    assert not naive.loc["isolation", "validated"] and not naive.loc["theil_h", "validated"]
    assert any("outside the Rounds 50/52 validated range none" in n for n in naive.loc["dissimilarity", "notes"])


def test_gate_refuses_beyond_range_and_small_counties():
    # Round 52 widened the ranges: D and H to 1.0, isolation any finite noise level.
    f, r = county(1.2, seed=7, alternating=True)
    out = sg.segregation_replicate(f, ["a", "b"], r).set_index("statistic")
    assert (out.noise_level >= 1.).all() and out.validated.tolist() == [False, True, False]
    t = sg.segregation_test(out.reset_index(), "theil_h", "36061", null_value=.1)
    assert t["validated"] is False and "noise range" in t["confirmatory_refusal"]
    f, r = county(.25, tracts=4)
    small = sg.segregation_replicate(f, ["a", "b"], r)
    assert not small.validated.any() and all(any("populated tract" in n for n in ns) for ns in small.notes)


def test_three_group_h_validated_four_groups_not():
    rng = np.random.default_rng(3)
    counts = rng.integers(100, 600, (8, 4)).astype(float)
    ids = [f"36061{i:06}" for i in range(1, 9)]
    reps = make_replicates(counts, .2*counts, rng)
    f = pd.DataFrame(counts, columns=list("abcd")); f.insert(0, "GEOID", ids); f["Year"] = 2024
    r = replicate_long(ids, list("abcd"), counts, reps); r["Year"] = 2024
    three = sg.segregation_replicate(f, list("abc"), r[r.variable != "d"])
    assert three.statistic.tolist() == ["theil_h"] and three.validated.all()
    assert not sg.segregation_replicate(f, list("abc"), r[r.variable != "d"], bias_correction=False).validated.any()
    # Round 52: bias-corrected four- and five-group H validated (race groups); naive and six+ groups not.
    assert sg.segregation_replicate(f, list("abcd"), r).validated.all()
    assert sg.variant_validated("theil_h", "bias_corrected", 3) and not sg.variant_validated("theil_h", "naive", 3)
    assert sg.variant_validated("theil_h", "bias_corrected", 4) and not sg.variant_validated("theil_h", "bias_corrected", 7)  # six groups: Round 57


def test_rule_text_mirrored():
    from census import mcp_profiles
    proto = (ROOT/"docs/agent_protocol.md").read_text()
    recipe = (ROOT/"docs/recipes/segregation.md").read_text()
    for text in (proto, recipe, mcp_profiles.CORE_INSTRUCTIONS):
        assert "noise level" in text and ".50" in text
    for text in (proto, recipe):
        assert "multigroup H stays exploratory" not in text and "Round 50" in text
    assert "CV above .15 is exploratory only (most real ones)" not in mcp_profiles.CORE_INSTRUCTIONS
