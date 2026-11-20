# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 51: negative replicate estimates (segregation clipping, SMR accept; flags = audit, manifests opt in)."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from census import segregation as sg
from census import standardize as sd
from census.manifest import methods
from census.results import IncompleteReplicatesError
from census.simulation import make_replicates, replicate_long
from census.variance import REPLICATE_COLUMNS

ROOT = Path(__file__).resolve().parents[1]
AUDIT = json.loads((ROOT/"docs/audits/negative_replicates_validation.json").read_text())
NAMES = {"D": "dissimilarity", "I": "isolation", "H": "theil_h"}
R = list(REPLICATE_COLUMNS)


def test_clip_ranges_equal_audit():
    assert AUDIT["criterion_commit"] == "2837bfb"
    n = {"two": 2, "three": 3}
    seen = 0
    for design, procs in AUDIT["passed"]["segregation_clip"].items():
        for proc, top in procs.items():
            name = NAMES[proc[0]]; variant = "naive" if proc.endswith("naive") else "bias_corrected"
            span = sg.CLIP_RANGES[(name, variant, n[design])]
            if top is None:
                assert span is None
            else:
                assert span is not None and span[1] == pytest.approx(top)
                # never wider than Round 50, same engine lower bound
                assert span[0] == sg.REALISTIC_RANGES[(name, variant, n[design])][0]
                assert span[1] <= sg.REALISTIC_RANGES[(name, variant, n[design])][1]
            seen += 1
    assert seen == len(sg.CLIP_RANGES) == 8
    assert sg.DEFAULT_NEGATIVE_REPLICATES == "clip"
    # the audit's stress test produced negative replicates
    for design in ("two", "three"):
        assert min(AUDIT["segregation"][design]["share_cells_with_negative_replicate"].values()) > .02


def test_smr_flags_equal_audit():
    assert sd.SMR_NEGATIVE_REPLICATES_VALIDATED == AUDIT["passed"]["smr"] == {"accept": True, "clip": True}
    assert sd.DEFAULT_SMR_NEGATIVE_REPLICATES == "accept"
    assert all(row["negative_draw_share"] > .3 for row in AUDIT["smr"].values())


def county(cv=.25, tracts=8, seed=51, negative=True):
    rng = np.random.default_rng(seed)
    counts = np.column_stack((rng.integers(80, 400, tracts), rng.integers(300, 1200, tracts))).astype(float)
    ids = [f"36047{i:06}" for i in range(1, tracts+1)]
    reps = make_replicates(counts, cv*counts, rng)
    if negative:
        reps[0, 0, :3] = [-4., -1., -7.]
    f = pd.DataFrame({"GEOID": ids, "Year": 2024, "a": counts[:, 0], "b": counts[:, 1]})
    r = replicate_long(ids, ["a", "b"], counts, reps); r["Year"] = 2024
    return f, r


def test_segregation_clips_by_default_and_validates_bias_corrected_only():
    f, r = county()
    out = sg.segregation_replicate(f, ["a", "b"], r).set_index("statistic")
    assert (out.clipped_replicates == 3).all() and out.bias_correction.all()
    assert out.noise_level.between(.15, .5).all() and out.validated.all()
    assert all(any("set to zero before the index refits" in n for n in ns) for ns in out.notes)
    naive = sg.segregation_replicate(f, ["a", "b"], r, bias_correction=False).set_index("statistic")
    # naive isolation/H failed with clipped cells (Round 51) and, since Round 52, without them too
    assert not naive.validated.any()
    assert any("lacks passing coverage validation" in n for n in naive.loc["isolation", "notes"])
    with pytest.raises(IncompleteReplicatesError, match="strict policy"):
        sg.segregation_replicate(f, ["a", "b"], r, negative_replicates="refuse")
    with pytest.raises(ValueError, match="negative_replicates"):
        sg.segregation_replicate(f, ["a", "b"], r, negative_replicates="drop")


def test_clipped_refits_use_zero_and_noise_uses_unclipped():
    f, r = county()
    out = sg.segregation_replicate(f, ["a", "b"], r).set_index("statistic")
    r2 = r.copy(); m = r2[R] < 0; r2[R] = r2[R].mask(m, 0.)
    same = sg.segregation_replicate(f, ["a", "b"], r2).set_index("statistic")
    assert np.allclose(out[R].to_numpy(float), same[R].to_numpy(float))   # identical refits
    assert np.allclose(out.estimate, same.estimate) and np.allclose(out.se, same.se)
    assert not np.allclose(out.max_count_cv, same.max_count_cv)             # count SEs from the unclipped values
    cube = np.stack([r[r.variable == g][R].to_numpy(float) for g in ("a", "b")], axis=2)
    counts = f[["a", "b"]].to_numpy(float)
    se = np.sqrt(.05*((cube-counts[:, None, :])**2).sum(axis=1))
    assert out.noise_level.iloc[0] == pytest.approx(sg.noise_level(counts, se))


def test_no_negative_replicates_unchanged():
    f, r = county(negative=False)
    a = sg.segregation_replicate(f, ["a", "b"], r)
    b = sg.segregation_replicate(f, ["a", "b"], r, negative_replicates="refuse")
    assert (a.clipped_replicates == 0).all()
    pd.testing.assert_frame_equal(a, b)


def smr_inputs(negative=True):
    rates = np.array([.0005, .001, .003, .01, .04])
    pop = np.full((1, 5), 2000.)
    rng = np.random.default_rng(9)
    reps = pop[:, :, None]+300*rng.standard_normal((1, 5, 80))
    if negative:
        reps[0, 0, :2] = [-150., -20.]
    obs = pd.Series([140], index=["36047"])
    return obs, pd.DataFrame(pop, index=obs.index), rates, reps


def test_smr_accepts_negative_band_replicates_by_default():
    obs, pop, rates, reps = smr_inputs()
    out = sd.indirect_standardize(obs, pop, rates, reps)
    assert any("used as published" in n for n in out.notes.iloc[0])
    clip = sd.indirect_standardize(obs, pop, rates, reps, negative_replicates="clip")
    assert any("set to zero" in n for n in clip.notes.iloc[0])
    assert out.se_log_smr.iloc[0] != clip.se_log_smr.iloc[0]
    with pytest.raises(ValueError, match="nonnegative"):
        sd.indirect_standardize(obs, pop, rates, reps, negative_replicates="refuse")
    bad = reps.copy(); bad[0, :, 0] = -5000.          # nonpositive replicate expected count still refused
    with pytest.raises(ValueError, match="replicate expected counts must be positive"):
        sd.indirect_standardize(obs, pop, rates, bad)
    obs, pop, rates, reps = smr_inputs(negative=False)
    a = sd.indirect_standardize(obs, pop, rates, reps); b = sd.indirect_standardize(obs, pop, rates, reps, negative_replicates="refuse")
    pd.testing.assert_frame_equal(a, b)


def test_manifests_keep_strict_policy_unless_opted_in():
    f, r = county()
    a = {"groups": ["a", "b"], "within": "county"}
    with pytest.raises(IncompleteReplicatesError, match="strict policy"):
        methods._run_segregation(a, {}, f, .90, r, None, {})
    out = methods._run_segregation(a, {"negative_replicates": "clip"}, f, .90, r, None, {})
    assert (out.clipped_replicates == 3).all()

    def check(args):
        errors = []
        ctx = dict(a={**a, "args": args}, manifest={"geography": {"level": "tract"}}, errors=errors, names={"a", "b"})
        methods._check_segregation("before_spatial", ctx)
        return errors
    assert check({"negative_replicates": "clip"}) == []
    assert any("negative_replicates" in e for e in check({"negative_replicates": "accept"}))
    text = methods._text_segregation({"groups": ["a", "b"], "args": {"negative_replicates": "clip"}},
                                     methods.METHODS["segregation"].text[0])
    assert "set to zero before the refits" in text and "no negative-count clipping" not in text
    assert "no negative-count clipping" in methods._text_segregation({"groups": ["a", "b"]}, methods.METHODS["segregation"].text[0])
    assert "used as published" in methods._text_smr({"args": {"negative_replicates": "accept"}}, "T.")


def test_rule_text_mirrored():
    from census import mcp_profiles
    proto = (ROOT/"docs/agent_protocol.md").read_text()
    recipe = (ROOT/"docs/recipes/segregation.md").read_text()
    smr = (ROOT/"docs/recipes/health_inequality.md").read_text()
    for text in (proto, recipe, mcp_profiles.CORE_INSTRUCTIONS):
        assert "Round 51" in text and "clip" in text
    for text in (proto, smr):
        assert "used as published" in text
    assert "Counties with a negative replicate estimate are refused" not in proto
    assert "refused under\n   the pre-specified validation domain" not in smr
