# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 89: causal question specification (target trial, causal diagram, backdoor checks)."""
import itertools
import json

import numpy as np
import pandas as pd
import pytest

from census import causal_spec as cs

FIG = {  # Hernán and Robins, What If (2020 draft), chapters 7 and 18
    "7.1_confounding": ["L -> A", "L -> Y", "A -> Y"],
    "7.2_unmeasured_via_L": ["U -> L", "U -> Y", "L -> A", "A -> Y"],
    "7.4_m_bias": ["U1 -> A", "U1 -> L", "U2 -> L", "U2 -> Y", "A -> Y"],
    "18.1_collider": ["A -> L", "Y -> L", "A -> Y"],
    "18.2_collider_descendant": ["A -> L", "Y -> L", "L -> C", "A -> Y"],
    "18.4_mediator": ["A -> L", "L -> Y", "A -> Y"],
    "instrument": ["Z -> A", "U -> A", "U -> Y", "A -> Y"],
}


def rep(name, adjust):
    return cs.dag_report({"edges": FIG[name], "treatment": "A", "outcome": "Y"}, adjust)


@pytest.mark.parametrize("name,adjust,sufficient", [
    ("7.1_confounding", ["L"], True), ("7.1_confounding", [], False),
    ("7.2_unmeasured_via_L", ["L"], True),
    ("7.4_m_bias", [], True), ("7.4_m_bias", ["L"], False),
    ("18.1_collider", [], True), ("18.1_collider", ["L"], False),
    ("18.2_collider_descendant", ["C"], False),
    ("18.4_mediator", ["L"], False), ("18.4_mediator", [], True),
])
def test_book_figures(name, adjust, sufficient):
    assert rep(name, adjust)["check"]["sufficient"] is sufficient


def test_reasons_are_named():
    assert rep("7.4_m_bias", ["L"])["check"]["colliders_opened"] == ["L"]
    assert rep("18.4_mediator", ["L"])["check"]["mediators"] == ["L"]
    assert rep("18.1_collider", ["L"])["check"]["treatment_descendants"] == ["L"]
    assert rep("7.1_confounding", [])["check"]["open_backdoor_paths"] == ["A <- L -> Y"]
    r = rep("instrument", ["Z"])
    assert r["check"]["instruments"] == ["Z"] and r["minimal_adjustment_sets"] == [] and "identification" in r


def test_minimal_sets():
    assert rep("7.1_confounding", None)["minimal_adjustment_sets"] == [["L"]]
    assert rep("7.4_m_bias", None)["minimal_adjustment_sets"] == [[]]
    # Pearl (2009) Figure 3.4-style: two minimal sets
    g = {"edges": ["Z1 -> Z3", "Z2 -> Z3", "Z1 -> X", "Z3 -> X", "Z3 -> Y", "Z2 -> Y", "X -> W", "W -> Y"],
         "treatment": "X", "outcome": "Y"}
    sets = cs.dag_report(g)["minimal_adjustment_sets"]
    assert ["Z1", "Z3"] in sets and ["Z2", "Z3"] in sets and ["Z3"] not in sets


def test_parse_errors():
    with pytest.raises(cs.DagError, match="cycle"):
        cs.parse_dag(["A -> B", "B -> C", "C -> A"])
    with pytest.raises(cs.DagError):
        cs.parse_dag(["A - B"])
    with pytest.raises(cs.DagError, match="no directed path"):
        cs.dag_report({"edges": ["Y -> A"], "treatment": "A", "outcome": "Y"})
    assert cs.parse_dag(["A -> B -> C"])["B"] == {"C"}


def _random_dag(rng, n, p):
    names = [f"V{i}" for i in range(n)]
    edges = [f"{names[i]} -> {names[j]}" for i in range(n) for j in range(i+1, n) if rng.random() < p]
    return cs.parse_dag(edges, names), names


def test_d_separation_matches_path_enumeration():
    rng = np.random.default_rng(20282889)
    checked = 0
    for _ in range(150):
        g, names = _random_dag(rng, int(rng.integers(4, 8)), .4)
        for x, y in itertools.combinations(names, 2):
            for k in range(3):
                for z in itertools.combinations([n for n in names if n not in (x, y)], k):
                    z = set(z)
                    by_paths = not any(cs.path_open(g, p, z) for p in cs.paths(g, x, y))
                    assert cs.d_separated(g, [x], [y], z) == by_paths, (g, x, y, z)
                    checked += 1
    assert checked > 3000


def test_backdoor_matches_brute_force_on_random_dags():
    rng = np.random.default_rng(20282890)
    for _ in range(80):
        g, names = _random_dag(rng, 6, .45)
        t, y = names[1], names[-1]
        if y not in cs.descendants(g, [t]):
            continue
        desc = cs.descendants(g, [t])
        for k in range(3):
            for z in itertools.combinations([n for n in names if n not in (t, y)], k):
                z = set(z)
                brute = not (z & desc) and not any(cs.path_open(g, p, z) for p in cs.backdoor_paths(g, t, y))
                assert cs.check_adjustment(g, t, y, z)["sufficient"] == brute


def test_formula_adjustment():
    assert cs.formula_adjustment("Y ~ A + L + C(M) + L:A", "A") == ("Y", ["L", "M"])
    with pytest.raises(cs.DagError):
        cs.formula_adjustment("Y ~ L", "A")


TRIAL = {"eligibility": "MI counties 2019", "intervention": "expand Medicaid in 2019", "comparator": "no expansion",
         "time_zero": "2019-01-01", "outcome": "uninsured rate", "follow_up": "2019-2023", "contrast": "average_effect",
         "target": "these_areas"}


def test_trial_errors_and_warnings():
    assert cs.trial_errors(TRIAL) == []
    assert any("time_zero" in e for e in cs.trial_errors({k: v for k, v in TRIAL.items() if k != "time_zero"}))
    assert cs.trial_errors({**TRIAL, "target": "everyone"})
    assert cs.trial_errors({**TRIAL, "bogus": 1})
    assert any("not an intervention" in w for w in cs.trial_warnings(None, "poverty_rate"))
    assert any("versions" in w for w in cs.trial_warnings({**TRIAL}, "poverty_rate"))
    assert cs.trial_warnings({**TRIAL, "versions": "an income transfer of $X"}, "poverty_rate") == []
    a = cs.assess(treatment="policy")
    assert a["label"].startswith("associational")


def test_manifest_errors_and_methods_text():
    from census.manifest.causal_block import causal_errors, causal_methods
    m = {"analyses": [{"id": "a1", "formula": "Y ~ A + L"}],
         "dag": {"edges": FIG["7.4_m_bias"], "treatment": "A", "outcome": "Y"}, "causal_question": TRIAL}
    errs = causal_errors(m)
    assert errs and "collider" in errs[0] and "a1" in errs[0]
    assert causal_errors({**m, "exploratory": True}) == []
    good = {**m, "analyses": [{"id": "a1", "formula": "Y ~ A"}]}
    assert causal_errors(good) == []
    lines, cites = [], []
    causal_methods(good, lines, cites)
    text = "\n".join(lines)
    assert "target trial" in text and "blocks every backdoor path" in text and cites == ["hernan_robins"]
    assert causal_errors({"analyses": [], "dag": {"edges": ["A -> B", "B -> A"], "treatment": "A", "outcome": "B"}})


def test_manifest_without_blocks_unchanged():
    from census.manifest.causal_block import causal_errors, causal_methods
    lines = []
    causal_methods({"analyses": []}, lines, [])
    assert lines == [] and causal_errors({"analyses": []}) == []


def test_estimate_effect_tool_assessment(tmp_path):
    from census.workflows_inference import estimate_effect
    rng = np.random.default_rng(5)
    n = 400
    L = rng.normal(size=n); A = (L + rng.normal(size=n) > 0).astype(int); Y = A + L + rng.normal(size=n)
    p = tmp_path/"f.csv"
    pd.DataFrame({"GEOID": [f"{i:05d}" for i in range(n)], "A": A, "L": L, "M": rng.normal(size=n), "Y": Y}).to_csv(p, index=False)
    r = estimate_effect(str(p), "treatment", "Y", treatment="A", confounders=["L"])
    assert r["success"] and "associational" in r["summary"] and r["causal_assessment"]["label"].startswith("associational")
    r = estimate_effect(str(p), "treatment", "Y", treatment="A", confounders=["L"], causal_question=TRIAL,
                        dag={"edges": FIG["7.1_confounding"], "outcome": "Y"})
    assert r["success"] and r["causal_assessment"]["problems"] == [] and "associational" not in r["summary"]
    r = estimate_effect(str(p), "treatment", "Y", treatment="A", confounders=["L", "M"], causal_question=TRIAL,
                        dag={"edges": ["L -> A", "L -> Y", "A -> M", "M -> Y", "A -> Y"], "outcome": "Y"})
    assert "CAUSAL SPECIFICATION PROBLEMS" in r["summary"] and "mediator" in r["summary"]


def test_stratified_label_is_associational():
    from census.stratified import ROLE_NOTE
    assert "associational" in ROLE_NOTE and "collider" in ROLE_NOTE


def test_sources_registered():
    from census.references import tool_entries
    ids = {s for s, _ in tool_entries("estimate_effect")}
    assert {"pearl2009", "lauritzen1990", "hernan_robins2020"} <= ids
