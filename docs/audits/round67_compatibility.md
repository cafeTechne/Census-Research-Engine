# Round 67 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round67`, branch `phase67/nc-ice`, based on
defaultBranch `e75a41b`.

## Pre-registration

- The plan (`e75a41b`, on defaultBranch) stated S's pass rule and C's slope rule before any run.
- **Deviation 2:** the criterion file committed at `daa1d15` was a placeholder, because a tool error kept the
  drafted text from being written. S ran against `daa1d15` under the plan's rule and the frozen script docstring.
  The full criterion text, with S's result recorded in it, was committed at `14b78b2` before any
  life-expectancy–ICE association was computed. C ran against `14b78b2`.

## Results

- **C: partly replicated.** 5 of 6 slopes meet the rule. The OLS slope for ICE Income + Race misses: ratio 1.13,
  and its HC3 interval does not reach 0.135.
- **S:** SCPC fails at 100 km on NC tracts (.7535 at ρ̄ .05, .8145 at .10) and passes at 0 and 20 km. HC3 fails
  badly (.12–.26).

## Behaviour change

- `census.scpc.fit_scpc`: results on 11-digit (tract) GEOIDs are `validated: false`, with a Round 67 note. County
  results are unchanged.
- Rule text mirrored (protocol and generated MCP text, regression recipe).

## Acceptance

- Goldens: byte-identical.
- New tests: `tests/test_round67.py` (3).
- Full suite: 2161 passed, 37 skipped; 0 failures.
