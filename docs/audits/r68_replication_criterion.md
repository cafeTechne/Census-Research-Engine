# Round 68 criterion: replication E (shares of life-expectancy variation)

Committed before the model was fitted. Author self-review, not independent. Frozen with `validate_pins`:
`scripts/r68_le_variance_replication.py` and this file.

**Seen before this commit:** the data counts only (`--fetch-only`): 65,662 tracts, 3,020 counties, 48 states plus
DC. These match the paper's counts exactly, which supports the assumption that it used USALEEP 2010–2015 with
every tract that has an `e(0)`. No variance or share was computed.

## Target (published headline only; the paper is not open access)

Boing et al. (2020), *PNAS* 117(30):17688–17694: of the total geographic variation in life expectancy at birth,
70.4% is attributed to tracts, 10.7% to counties and 19.0% to states.

## Specification

- Three-level REML random-intercept null model of `e(0)` in years: e0 = μ + u_state + v_county + e_tract
  (statsmodels `MixedLM`, groups = state, county variance component).
- Assumed model form, since the paper's methods could not be read: a null three-level model on the years scale.
  The report states this assumption.

## Rule

- **Replicated:** every share is within ±5 percentage points of the published value **and** the order is
  tract > state > county.
- **Partly replicated:** the order holds, but some share is off by more than 5 points.
- **Not replicated:** otherwise.
- **Secondary (descriptive):** the same model for ln(e0), plus two-level models (tract in county; tract in state).
