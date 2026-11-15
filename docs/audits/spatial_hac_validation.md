# Spatial HAC validation (Round 22)

Fixed design: 145 Michigan/New York county representative points (2020 boundaries); 2,000 simulations per cell, seed 20261122 + cell index (linear then binomial, ranges 0/50/100 km). Independent Gaussian covariate/error fields with exponential covariance and diagonal jitter 1e-10. Linear y=1+0.5x+e; binomial logit(p)=-2.6+0.3x+u, SD(u)=0.15, lognormal trials drawn once per cell (median 3900, log-SD 1, minimum 50). 90% normal Wald intervals.

The linear estimator calls the internal sandwich directly: fit_eiv requires ACS replicates even when measurement error is zero. The GLM uses the same explicitly tested binomial scores/bread as fit_replicate, fitting once per draw. Independent comparators: OLS HC0 and GLM Pearson X2. Invalid covariance fits count as noncoverage. PSD failures with positive diagonal are retained.

**Pre-set acceptance:** coverage >= 0.86 at cutoff 150 km in all six cells. **FAILED**. No seeds, design or criteria changed.

**Consequence:** spatial_se is exploratory only; confirmatory manifests refuse it. The low birth weight study must be registered without spatial SEs.

| Design | Range km | Cutoff km | Coverage | MC SE | Mean SE / empirical SD | Non-PSD share | Failed |
| :--- | ---: | :--- | ---: | ---: | ---: | ---: | ---: |
| linear | 0 | independent | 0.8845 | 0.0071 | 0.9832 | 0.0000 | 0 |
| linear | 0 | 50 | 0.8885 | 0.0070 | 0.9880 | 0.0000 | 0 |
| linear | 0 | 100 | 0.8810 | 0.0072 | 0.9763 | 0.0000 | 0 |
| linear | 0 | 150 | 0.8735 | 0.0074 | 0.9585 | 0.0000 | 0 |
| linear | 0 | 200 | 0.8615 | 0.0077 | 0.9368 | 0.0000 | 0 |
| linear | 50 | independent | 0.7320 | 0.0099 | 0.6917 | 0.0000 | 0 |
| linear | 50 | 50 | 0.7705 | 0.0094 | 0.7394 | 0.0000 | 0 |
| linear | 50 | 100 | 0.8130 | 0.0087 | 0.8091 | 0.0000 | 0 |
| linear | 50 | 150 | 0.8170 | 0.0086 | 0.8239 | 0.0000 | 0 |
| linear | 50 | 200 | 0.8105 | 0.0088 | 0.8191 | 0.0000 | 0 |
| linear | 100 | independent | 0.5440 | 0.0111 | 0.4555 | 0.0000 | 0 |
| linear | 100 | 50 | 0.5935 | 0.0110 | 0.5092 | 0.0000 | 0 |
| linear | 100 | 100 | 0.6795 | 0.0104 | 0.6196 | 0.0000 | 0 |
| linear | 100 | 150 | 0.7070 | 0.0102 | 0.6663 | 0.0000 | 0 |
| linear | 100 | 200 | 0.7185 | 0.0101 | 0.6799 | 0.0000 | 0 |
| binomial | 0 | independent | 0.7280 | 0.0100 | 0.6628 | 0.0000 | 0 |
| binomial | 0 | 50 | 0.8565 | 0.0078 | 0.9130 | 0.0000 | 0 |
| binomial | 0 | 100 | 0.8485 | 0.0080 | 0.8949 | 0.0000 | 0 |
| binomial | 0 | 150 | 0.8345 | 0.0083 | 0.8751 | 0.0000 | 0 |
| binomial | 0 | 200 | 0.8230 | 0.0085 | 0.8548 | 0.0000 | 0 |
| binomial | 50 | independent | 0.6100 | 0.0109 | 0.5456 | 0.0000 | 0 |
| binomial | 50 | 50 | 0.7725 | 0.0094 | 0.7656 | 0.0000 | 0 |
| binomial | 50 | 100 | 0.7850 | 0.0092 | 0.7930 | 0.0000 | 0 |
| binomial | 50 | 150 | 0.7835 | 0.0092 | 0.7932 | 0.0000 | 0 |
| binomial | 50 | 200 | 0.7735 | 0.0094 | 0.7837 | 0.0000 | 0 |
| binomial | 100 | independent | 0.5330 | 0.0112 | 0.4370 | 0.0000 | 0 |
| binomial | 100 | 50 | 0.6625 | 0.0106 | 0.6004 | 0.0000 | 0 |
| binomial | 100 | 100 | 0.7075 | 0.0102 | 0.6629 | 0.0000 | 0 |
| binomial | 100 | 150 | 0.7285 | 0.0099 | 0.6893 | 0.0000 | 0 |
| binomial | 100 | 200 | 0.7290 | 0.0099 | 0.6945 | 0.0000 | 0 |

Boundary provenance: `{"boundary_year": 2020, "files": [{"cache_path": ".cache/geo/2020/cb_2020_us_county_500k.zip", "sha256": "1a45c87a5a0c322514c9d5c9ebcba5eb9df313bd38962f6db56107ba0ccacc6f", "source_url": "https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_us_county_500k.zip"}], "level": "county"}`.

Reproduce: `OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/spatial_hac_validation.py`.
