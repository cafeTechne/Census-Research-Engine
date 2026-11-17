# Spatial cluster validation (Round 26)

90% coverage >=0.86 in all six cells, each candidate separately

Criterion commit: `46ec2ec`. No seeds, designs or criteria changed.

| Candidate | Design | Range km | Coverage | MC SE | Mean width / HC3 range 0 | Failed |
|:---|:---|---:|---:|---:|---:|---:|
| C1-8 | linear | 0 | 0.8950 | 0.0069 | 1.075 | 0 |
| C1-12 | linear | 0 | 0.9005 | 0.0067 | 1.039 | 0 |
| C2-8 | linear | 0 | 0.9115 | 0.0064 | 1.222 | 0 |
| C3-12 | linear | 0 | 0.9075 | 0.0065 | 1.081 | 0 |
| C1-8 | linear | 50 | 0.8620 | 0.0077 | 1.390 | 0 |
| C1-12 | linear | 50 | 0.8570 | 0.0078 | 1.323 | 0 |
| C2-8 | linear | 50 | 0.8960 | 0.0068 | 1.436 | 0 |
| C3-12 | linear | 50 | 0.8815 | 0.0072 | 1.426 | 0 |
| C1-8 | linear | 100 | 0.8000 | 0.0089 | 1.821 | 0 |
| C1-12 | linear | 100 | 0.7730 | 0.0094 | 1.695 | 0 |
| C2-8 | linear | 100 | 0.8860 | 0.0071 | 1.661 | 0 |
| C3-12 | linear | 100 | 0.8235 | 0.0085 | 1.893 | 0 |
| C1-8 | binomial | 0 | 0.8640 | 0.0077 | 1.009 | 0 |
| C1-12 | binomial | 0 | 0.8590 | 0.0078 | 0.969 | 0 |
| C2-8 | binomial | 0 | 0.8965 | 0.0068 | 1.091 | 0 |
| C3-12 | binomial | 0 | 0.8870 | 0.0071 | 1.027 | 0 |
| C1-8 | binomial | 50 | 0.8455 | 0.0081 | 1.130 | 0 |
| C1-12 | binomial | 50 | 0.8380 | 0.0082 | 1.076 | 0 |
| C2-8 | binomial | 50 | 0.8895 | 0.0070 | 1.146 | 0 |
| C3-12 | binomial | 50 | 0.8760 | 0.0074 | 1.148 | 0 |
| C1-8 | binomial | 100 | 0.8010 | 0.0089 | 1.272 | 0 |
| C1-12 | binomial | 100 | 0.7790 | 0.0093 | 1.190 | 0 |
| C2-8 | binomial | 100 | 0.8895 | 0.0070 | 1.304 | 0 |
| C3-12 | binomial | 100 | 0.8295 | 0.0084 | 1.289 | 0 |

Candidate outcomes: C1-8: FAIL, C1-12: FAIL, C2-8: PASS, C3-12: FAIL.

Default: C2-8.

Clusters: fixed 50-restart projected-point k-means, minimum five counties. Assignments and boundary provenance in JSON.
C3 uses bracketed endpoint inversion of the restricted test for widths; disconnected confidence sets are not characterized.
Failed fits, singular covariance or unbracketed bootstrap intervals count as non-coverage; none are dropped from the denominator.

References: Bester, Conley & Hansen (2011), J Econometrics 165:137–151; Ibragimov & Müller (2010), JBES 28:453–468;
[Kline & Santos (2012), Score2-Wald](https://eml.berkeley.edu/~pkline/papers/ScoreFinal_web.pdf).
