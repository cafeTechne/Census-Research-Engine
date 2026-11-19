# Round 50 exploratory example: county poverty and income segregation in MI/NY

**Status: exploratory example, not a registered study. Author self-review, not independent.**

**Inputs.** `scripts/r50_segregation_example.py` reads the cached 2024 five-year tract VRE files for
B17001 and B19001 (MI and NY) with HTTP blocked, and runs `census.segregation_replicate` with its
defaults. Since Round 50 every default is bias-corrected. Only county rows are written. The outputs
are archived at `/tmp/r50_example_outputs.tar.gz` (sha256 `e98c938f…221f16f9`).

**Designs.**
- **Poverty, two groups:** below poverty (B17001_002) vs at or above (B17001_031).
- **Income, three groups:** households with income below $35k, $35k–99,999 and $100k or more. The B19001
  bands are summed, and their replicates are summed band by band.

**Refused counties.** Five counties per design have at least one tract with a negative replicate
estimate in the published VRE file. The engine refuses them under its strict policy (no clipping), so
they are left out:
- Poverty: Albany, Bronx, Dutchess, Kings and Sullivan.
- Income: Bronx, Genesee, Kalamazoo, Kings and Wayne.

This is backlog issue N20.

| Design | Index | Counties | Validated, Round 28 gate | Validated, Round 50 gate | Median noise level |
| :--- | :--- | ---: | ---: | ---: | ---: |
| Poverty | D, isolation, H | 140 | 0 | 132 | 0.27 |
| Income | three-group H | 140 | 1 | 132 | 0.20 |

The eight counties that are not validated have fewer than five populated tracts. They are the same
eight that the validation excluded.

**Highest poverty segregation (Theil H, bias-corrected, 90% interval):**

| County | H |
| :--- | :--- |
| Washtenaw, MI | 0.190 (0.169, 0.210) |
| Rockland, NY | 0.186 (0.155, 0.217) |
| Schenectady, NY | 0.149 (0.121, 0.177) |
| Orange, NY | 0.142 (0.119, 0.165) |
| Onondaga, NY | 0.141 (0.118, 0.163) |

**Selected counties (poverty; noise level in brackets):**

| County | D | Isolation of the poor | H |
| :--- | :--- | :--- | :--- |
| Wayne, MI (0.33) | 0.383 (0.364, 0.401) | 0.308 (0.292, 0.324) | 0.128 (0.111, 0.146) |
| Washtenaw, MI (0.33) | 0.432 (0.407, 0.457) | 0.306 (0.284, 0.328) | 0.190 (0.169, 0.210) |
| New York, NY (0.30) | 0.322 (0.299, 0.346) | 0.242 (0.229, 0.255) | 0.097 (0.083, 0.111) |
| Erie, NY (0.33) | 0.345 (0.317, 0.373) | 0.222 (0.208, 0.236) | 0.108 (0.091, 0.125) |

**Income, three groups.** The highest H values are Washtenaw (0.104), New York (0.092), Schenectady
(0.088), Monroe (0.087) and Westchester (0.085).

**What the switch to the bias-corrected D does.** Naive D is larger than corrected D by a median of
0.020 (10th–90th percentile 0.003–0.044). That is more than half of the median SE (0.035): sampling
noise inflates naive D, which is why it failed the realistic-error validation.

**Limits.**
- These describe the segregation of the poor and of income groups among the observed tracts. They are
  ACS sampling intervals only, not causal or superpopulation statements.
- The validation used these same group structures. Race and ethnicity groups were not validated (N21).
- Washtenaw's high value probably reflects student tracts around Ann Arbor, where poverty status
  counts students living off campus. This is an interpretation, not a finding of this example.
