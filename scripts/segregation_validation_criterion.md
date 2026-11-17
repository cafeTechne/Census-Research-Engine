# Fixed Round 28 segregation criterion

Eight cells: tract count 20/100 × true D .2/.5 × group-count CV .15/.30,
1,000 draws, seed 20261129 + index in that nesting order. Each index D,
isolation and H is judged separately, for naive and bias-corrected estimates.
Nominal 90% normal-interval coverage must be >= .86 in every CV .15 cell.
CV .30 is informational. Default corrected if it passes, otherwise naive; if
neither passes, that index is exploratory only. No post-run retuning.

Truth is fixed once/cell: lognormal tract totals (log median 4000, log-SD 1),
rounded to positive multiples of 20 in matched pairs. Each pair has equal
population and group-one shares (.5+D/2, .5-D/2). This fixes D exactly and gives
integer true counts. Group two is the remainder. There are n/2 independently
drawn matched pairs, not redrawn populations per simulation. H and isolation
truths are computed directly from those counts.

Each draw adds independent Gaussian errors with SE = CV × true group counts.
All 80 replicates use census.simulation.make_replicates around those observed
counts, with the same SEs. Any negative full count or replicate, or any undefined
index, counts as noncoverage for all versions; never clip, redraw or discard it
from the denominator. SE = sqrt(4/80 sum (Ir-I)^2), about the raw full-sample
estimate. Corrected point = I - 4(mean(Ir)-I), for all three indices, using that
same SE. No clipping of corrected points/intervals. Bias, empirical SD and mean
SE/empirical SD use valid draws and are informational. Coverage uses all draws.

This experiment has two groups. Multigroup H is implemented mathematically and
tested by reference but remains exploratory absent a separate coverage study.
Within-release county differences use replicate differences before taking the
variance; cross-release variances add only for non-overlapping five-year periods.
These contrasts are not additional simulation cells. One-area null_value must be
explicit. Contrast orientation is first county/release minus comparison. The
hypothesis selectors are release and compare_release, with geoid/compare_geoid;
multiple releases require an explicit release selector.

Freeze this script and criterion in a commit and push before full execution.
Smoke draws <=20/cell, no audit writes. Do not change the DGP, seeds, criterion
or failed results after a full run.
