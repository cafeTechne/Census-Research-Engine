# Round 55 demonstration: short interrupted series and estimated reference populations

**Status: demonstration on simulated inputs, not a data example or a study. Author self-review, not
independent.**

**Why a demonstration.** Each statistical round normally ends with an exploratory MI/NY example. Here no suitable
real input is available offline:
- **Interrupted series:** overlapping five-year ACS releases are autocorrelated by construction, and an annual
  WONDER series would need new manual exports from the owner.
- **SMR reference populations:** WONDER reference person-years are fixed Census estimates, not ACS estimates.

`scripts/r55_demonstration.py` therefore shows the engine output on fixed-seed simulated inputs. Outputs are
archived at `/tmp/r55_example_outputs.tar.gz` (sha256 `5e30cdd9…c87044bd`).

## A 22-point annual series

AR(1) errors with φ = .5; true level change 1 and slope change .2; interruption at point 12.

| Method | Level change (90% interval) | Slope change | Validated at 22 points |
| :--- | :--- | :--- | :--- |
| bootstrap_t_bc (Round 55) | 0.92 (−1.45 to 3.42) | 0.45 (−0.77 to 1.47) | yes (20+) |
| bootstrap_t (Round 48) | 0.92 (−1.49 to 3.46) | 0.45 (−0.55 to 1.32) | no (30+) |
| reml | 0.92 (−1.25 to 3.09) | 0.45 (−0.16 to 1.06) | no |
| ewc | −0.37 (−1.83 to 1.08) | 0.39 (−0.10 to 0.87) | no (failed) |
| ar1 (Round 42) | −0.31 (−2.09 to 1.48) | 0.24 (−0.12 to 0.59) | no (failed) |

The validated interval is the widest of the AR(1)-based ones. With 22 points and this much autocorrelation, an
honest interval cannot distinguish a level change of 1 from none. The narrower REML interval for the slope
change is the kind that under-covered (.79–.88 in Round 48).

## An SMR with an estimated reference population

A study area with 150 observed deaths; five bands with reference deaths of 40–600; reference person-years with
CV .05.

| Reference | SMR | 90% interval |
| :--- | :--- | :--- |
| Person-years fixed | 0.679 | 0.588 to 0.783 |
| Person-years with CV .05 (`reference_population_se`) | 0.679 | 0.584 to 0.789 |

The interval widens by about 5%. At state-level ACS CVs (around .02) the change would be negligible, which is
consistent with the validation: intervals without the term also covered .863 or more.
