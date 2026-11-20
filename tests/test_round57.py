# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 57: segregation gaps (clipped race designs above .50, six groups, same-release contrasts, group quarters)."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from census import segregation as sg
from census.manifest import methods
from census.simulation import replicate_long

ROOT = Path(__file__).resolve().parents[1]
AUDIT = json.loads((ROOT/"docs/audits/segregation_gaps_validation.json").read_text())
NAMES = {"D": "dissimilarity", "I": "isolation", "H": "theil_h"}


def _top(x):
    return np.inf if x == "inf" else x


def test_ranges_equal_audit():
    p = AUDIT["passed"]
    assert AUDIT["criterion_commit"] == "8bcad0b"
    for key, n in (("clip_two", 2), ("clip_four", 4), ("clip_five", 5)):
        for proc, top in p[key].items():
            name = NAMES[proc[0]]; variant = "naive" if proc.endswith("naive") else "bias_corrected"
            span = sg.CLIP_RANGES[(name, variant, n)]
            unclipped = sg.REALISTIC_RANGES[(name, variant, n)]
            if top is None or unclipped is None:
                assert span is None
            else:
                assert span[1] == min(_top(top), unclipped[1]) and span[0] == unclipped[0]
    for proc, top in p["six"].items():
        variant = "naive" if proc.endswith("naive") else "bias_corrected"
        span = sg.REALISTIC_RANGES[("theil_h", variant, 6)]
        assert (span is None) if top is None else span == (0., _top(top))
    for proc, top in p["same_release_contrast"].items():
        name = NAMES[proc[0]]; variant = "naive" if proc.endswith("naive") else "bias_corrected"
        span = sg.SAME_RELEASE_CONTRAST_RANGES[(name, variant)]
        assert (span is None) if top is None else span == (0., _top(top))
    assert sg.SAME_RELEASE_CONTRAST_RANGES[("dissimilarity", "bias_corrected")] is None


def county(cv, geo="36061", groups=2, tracts=8, seed=57, negative=False):
    rng = np.random.default_rng(seed)
    counts = rng.integers(60, 900, (tracts, groups)).astype(float)
    ids = [f"{geo}{i:06}" for i in range(1, tracts+1)]
    signs = rng.choice([-1., 1.], (tracts, groups, 80))
    reps = counts[:, :, None]*(1+cv/2*signs)
    if negative:
        reps[0, 0, :2] = [-3., -1.]
    names = [chr(97+g) for g in range(groups)]
    f = pd.DataFrame(counts, columns=names); f.insert(0, "GEOID", ids); f["Year"] = 2024
    r = replicate_long(ids, names, counts, reps); r["Year"] = 2024
    return f, r, names


def test_clipped_counties_validated_above_half():
    f, r, g = county(.6, negative=True)
    out = sg.segregation_replicate(f, g, r).set_index("statistic")
    assert (out.clipped_replicates > 0).all() and out.noise_level.between(.5, .75).all()
    assert out.validated.to_dict() == {"dissimilarity": False, "isolation": True, "theil_h": True}
    f, r, g = county(.8, groups=4, negative=True)
    assert sg.segregation_replicate(f, g, r).validated.all()


def test_same_release_contrast_gate():
    f1, r1, g = county(.3, geo="36061", seed=1); f2, r2, _ = county(.35, geo="36047", seed=2)
    res = sg.segregation_replicate(pd.concat([f1, f2]), g, pd.concat([r1, r2]))
    t = sg.segregation_test(res, "theil_h", "36061", compare_geoid="36047")
    assert t["validated"] is True
    d = sg.segregation_test(res, "dissimilarity", "36061", compare_geoid="36047")
    assert d["validated"] is False and "same-release county contrast" in d["confirmatory_refusal"]
    f3, r3, _ = county(.6, geo="36005", seed=3)
    res = sg.segregation_replicate(pd.concat([f1, f3]), g, pd.concat([r1, r3]))
    assert sg.segregation_test(res, "theil_h", "36061", compare_geoid="36005")["validated"] is False


def test_group_quarters_exclusion():
    f, r, g = county(.3)
    f["gq"] = 0.; f["total"] = f[g].sum(axis=1); f.loc[0, "gq"] = .8*f.loc[0, "total"]
    excl = sg.group_quarters_tracts(f, "gq", "total", .5)
    assert excl == [f.GEOID[0]]
    out = sg.segregation_replicate(f, g, r, exclude_tracts=excl)
    assert (out.tracts == 7).all() and all(any("exclude_tracts" in n for n in ns) for ns in out.notes)
    full = sg.segregation_replicate(f, g, r)
    assert not np.allclose(full.estimate, out.estimate)
    with pytest.raises(ValueError, match="max_share"):
        sg.group_quarters_tracts(f, "gq", "total", 0)
    a = {"groups": g, "within": "county"}
    run = methods._run_segregation(a, {"group_quarters": {"gq": "gq", "total": "total", "max_share": .5}}, f, .90, r, None, {})
    pd.testing.assert_series_equal(run.estimate, out.estimate)
    errors = []
    methods._check_segregation("before_spatial", dict(a={**a, "args": {"group_quarters": {"gq": "zz", "total": "total"}}},
                                                      manifest={"geography": {"level": "tract"}}, errors=errors,
                                                      names={"a", "b", "gq", "total"}))
    assert any("group_quarters" in e for e in errors)
    text = methods._text_segregation({"groups": g, "args": {"group_quarters": {"gq": "gq", "total": "total"}}},
                                     methods.METHODS["segregation"].text[0])
    assert "group-quarters share" in text


def test_rule_text_mirrored():
    from census import mcp_profiles
    for path in ("docs/agent_protocol.md", "docs/recipes/segregation.md", "mcp_server.py"):
        text = " ".join((ROOT/path).read_text().split())
        assert "Round 57" in text and "group" in text.lower()
    assert "group_quarters" in mcp_profiles.CORE_INSTRUCTIONS
    assert "validated for the bias-corrected versions below .50 only" not in (ROOT/"docs/recipes/segregation.md").read_text()
