# Round 26: spatial-cluster criterion fixed before the full run

Each of C1-8, C1-12, C2-8 and C3-12 passes independently iff nominal 90% coverage
is >=0.86 in **all six** cells. Exactly 2,000 draws per cell. Seeds 20261126+cell,
ordered linear 0/50/100 km, binomial 0/50/100 km. Failures count as non-coverage;
no failed draw is removed from the denominator. No seed, design or criterion may
change after the first full run. Smoke runs of <=20 draws/cell write no audits.

The exact Round 22 setup/draw functions were extracted from the original inline
loop in scripts/spatial_hac_validation.py, with RNG order unchanged. 145 cached
MI/NY representative points, exponential fields with diagonal jitter 1e-10;
linear 1+0.5x+e; binomial logit=-2.6+0.3x+0.15e; lognormal trials drawn once per
cell (median 3900, log SD 1, rounded, minimum 50). Outcome RNG is independent
of the bootstrap RNG (SeedSequence [20261126,cell,draw,3]). No downloads.

Cluster labels: use spatial_hac.unit_coordinates points (representative points,
as in Round 22), projected EPSG:5070 with pyproj. Fifty kmeans2 kmeans++ seeded
restarts, 100 Lloyd iterations each, seed 20261126; choose lowest SSE among
solutions with >=5 members, labels canonicalized by projected centroid x/y.
This resolves the plan's 'centroids' wording in favor of its explicit reuse of
unit_coordinates and the same county points. Assignment is fixed before draws.

C1: grouped-score CR1 G/(G-1)*(n-1)/(n-k), t(G-1) interval. C2: fit each cluster
separately, use mean slopes and sd/sqrt(G), t(G-1); any failed cluster invalidates
the draw. The same unrestricted binomial fit as Round 22 is used; HC3 is the
comparison, not Pearson X2. Widths are divided by the mean independent HC3 width
in the same design's range-0 cell. Width averages are over finite intervals;
failed-interval counts are reported separately and still count as non-coverage.

C3: 999 equiprobable Webb six-point weights (+/-sqrt(1/2), +/-1, +/-sqrt(3/2)),
one weight per cluster. Linear: restricted OLS residuals, full bootstrap OLS
refit and CR1 studentization computed by exact grouped-matrix identities.
Binomial: Kline-Santos restricted Score2-Wald (restricted score numerator,
unrestricted Hessian and unrestricted score studentization). Both use two-sided
p=(1+#(|t*|>=|t|))/1000; reject p<.10. Binomial nuisance parameters are refit under
each candidate null with a logit offset. This specifies the score-bootstrap
variant before outcomes are simulated; it is not the later WCL modification.

C3 widths invert that same test using fixed bootstrap weights within a draw.
Bracket endpoints about the unrestricted slope: start with
se_CR1*t(.95,G-1), allow 20 bracket doublings, then 24 bisections per endpoint.
Unbracketed/undefined intervals count as failed draws/non-coverage. No characterization of possibly disconnected confidence sets is claimed.

Default: smallest mean binomial/100-km interval width among passing candidates;
exact ties favor C1, then candidate ID. If all fail, no confirmatory default or
production engine is promoted. For the explicitly exploratory post hoc exercise,
use the pre-selected diagnostic C1-8; its choice must not depend on observed
coverage or the study's significance. Do not change registered study outputs.

Full runs require these exact scripts and this criterion in a named, pushed
commit. Audit results must be committed afterward.
