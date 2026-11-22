# Round 89 plan: causal question specification (target trial and causal diagram)

**Goal.** Backlog N65 (Hernán and Robins, *Causal Inference: What If*, chapters 3, 6–8, 18 and 22; mapping in
`docs/literature/hernan_robins_what_if.md`). A causal estimate means something only for a stated causal question:
- a well-defined intervention, specified as a target trial;
- an adjustment set justified by a causal diagram, not by associational rules.

Today the causal tools and the marginal measures run on any exposure, and Round 83 labels confounders with the 10%
change rule. That rule can recommend adjusting for a collider (M-bias, the book's Figure 7.4). Version 0.85.0. Branch
`phase89/causal-spec`. No new estimators: the checks are graph algorithms with exact answers.

## 1. Target-trial specification

- **A `causal_question` block for manifests and causal tools** (`estimate_effect`, DiD, the marginal measures when
  called "causal"), with these fields:
  - `eligibility` (population and time);
  - `intervention` and `comparator`, each with the versions that matter (Hernán's "sufficiently well-defined");
  - `time_zero`;
  - `outcome` and `follow_up`;
  - `contrast` (average treatment effect or effect in the treated);
  - `target`: super-population or these areas, explained as in chapter 10.3.
- **Without the block,** causal tools still run but label results "associational (no causal question specified)",
  and the methods text says so.
- **Social exposures** (poverty rate, income, race composition, education share) get a well-defined-intervention
  warning (chapter 3.4): the result is not the effect of an intervention unless the specification names one.

## 2. Causal diagram (DAG) checks

- **A `dag` block:** directed edges among manifest variables, plus unmeasured nodes (`U_*`). The engine checks it is
  acyclic.
- **D-separation and the backdoor criterion** for the declared treatment and outcome (Pearl). For a formula's
  adjustment set the engine reports, with the path:
  - whether every backdoor path is blocked;
  - whether a collider, a mediator, a descendant of treatment or an instrument is adjusted for.
- **Minimal sufficient adjustment sets** are enumerated when the DAG is small (≤ 20 nodes).
- **Confirmatory manifests with a DAG** refuse a formula whose adjustment set is not sufficient or includes a
  collider, mediator or descendant of treatment. Exploratory manifests get warnings.
- **Round 83's classification label** is renamed "associational label (10% rule)", with a note that the DAG decides
  adjustment.

## 3. Validation (numeric, exact)

- `tests` reproduce the book's examples:
  - Figures 7.1–7.4 and 7.7 (confounding, M-bias), with the adjustment verdicts the book gives;
  - Figures 18.1–18.4 (collider, its descendant, a variable affected by treatment, a mediator);
  - a published DAGitty example with known minimal adjustment sets.
- There is no simulation criterion; the d-separation code is also cross-checked against brute-force enumeration
  of paths on random small DAGs.

## 4. Engine, docs and acceptance

- `census/causal_spec.py`, used by manifest validation and by the causal tools.
- Recipe `causal` gains "State the causal question first" and "Draw the diagram".
- The protocol and MCP rules (chapter 3 language) are mirrored together.
- STATUS, CHANGELOG, compatibility audit, tests, goldens, suite.
  - Registered manifests have no `dag`, so goldens are expected byte-identical except for methods-text labels;
    any change is documented.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Target-trial block | done | manifests, `estimate_effect`, `difference_in_differences` |
| DAG checks | done | d-separation, backdoor, minimal sets, reasons |
| Book-figure tests | done | Figures 7.1–7.4, 18.1–18.4; random-DAG cross-checks |
| Engine, docs | done | recipe `causal`, protocol rule, sources |
| Goldens, suite | see audit | `round89_compatibility.md` |
| Exceptions | 3 | see audit |
