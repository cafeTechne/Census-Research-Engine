# Round 50 compatibility and acceptance

Author self-review, not independent; implemented by the maintainer agent at the owner's request.
Worktree `/tmp/census-round50`, branch `phase50/segregation-realistic`, based on defaultBranch `bef63d8`.

## Frozen validation (criterion `686d121`, pushed before the full run; 2,000 draws per cell)

**Setup.**
- Truth: the 2024 MI/NY tract counts and published SEs: 137 counties with five or more populated
  tracts.
- Observed counts and replicates: Gamma-copula draws, with replicate SD = SE/2.
- Cells: two groups (poverty) and three groups (household income) × group error correlation 0 and −.3.

**Acceptance.** A noise bin passes when, in both ρ cells, the mean county coverage is ≥ .86 and at least
90% of its counties cover ≥ .80. Bins need five or more counties to be judged.

| Index | Validated noise range | Bin mean coverage | Lowest county |
| :--- | :--- | :--- | :--- |
| D naive (Round 28 default) | none | .713–.870 | .214 |
| D bias-corrected | to .50 | .870–.921 | .827 |
| Isolation bias-corrected | to .50 | .883–.920 | .858 |
| Isolation naive | to .30 | .779–.873 | .433 |
| H bias-corrected | to .50 | .925–.968 | .863 |
| H naive | to .30 | .786–.898 | .520 |
| Three-group H bias-corrected | to .50 (all three judged bins) | .944–.999 | .900 |
| Three-group H naive | none | .560–.889 | .307 |

No draws failed. Naive D fails because sampling noise inflates it: its median absolute bias is .021–.024, against .0005–.0028 for the corrected indices.

**Changes made after the smoke runs, before freezing** (recorded in the criterion):
- **Replicate SD.** The plan said SD = SE, which makes the 4/80 formula estimate 4·SE². It is now SE/2.
- **Rounding.** Draws are rounded to whole counts, which avoids a Gamma-shape underflow.
- **Judging.** All six two-group variants are judged.

**Noise level.** The plan's "median tract group CV" became the largest, over groups, of the median tract
CV. The plan's pooled median would put every MI/NY county below .30, because the large group dominates it.

## Engine

`census/segregation.py`:
- **Defaults.** `DEFAULT_BIAS_CORRECTION` is now bias-corrected for D as well. The criterion set the
  default to the variant with the widest validated range.
- **Gate.** `REALISTIC_RANGES` holds the validated range for each (index, variant, number of groups).
  `MAX_VALIDATED_MEDIAN_CV = .50` and `MIN_VALIDATED_TRACTS = 5`.
- **New functions.** `noise_level` and `variant_validated`.
- **Output.** `segregation_replicate` adds a `noise_level` column. A row is validated in the Round 28
  range (max CV ≤ .15) or in its Round 50 range.

**Engine restrictions stricter than the criterion.**
- Corrected D and naive isolation and H failed Round 28 at CV .15, so their ranges start at .15.
- The validation excluded counties with fewer than five populated tracts, so the engine requires five.

**Manifests.** `_check_segregation` uses `variant_validated`, so three-group bias-corrected H can be
confirmatory. Manifest text lists the new defaults. No registered manifest uses segregation.

**Tests.** Seven Round 28 tests asserted the old default or gate. They were updated, with comments, to
keep their intent: naive D still exercises the Round 28 range, and patched ranges exercise the refusal
paths.

**Rule text.** Mirrored in `agent_protocol.md`, `docs/recipes/segregation.md` and the MCP core
instructions.

## Goldens and suite

Both goldens are byte-identical to Round 49 (`schema_r50`/`run_r50`); no golden case uses segregation. Suite: 2058 passed, 37 skipped, 63 subtests; 0 failures (8 new tests in `tests/test_round50.py`; 7 Round 28 tests updated).
