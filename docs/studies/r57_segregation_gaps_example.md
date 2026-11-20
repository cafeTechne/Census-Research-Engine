# Round 57 exploratory example: race/ethnicity segregation with group-quarters tracts excluded, MI/NY 2024

**Status: exploratory example, not a registered study. Author self-review, not independent.**

**Inputs.** `scripts/r57_segregation_gaps_example.py` reads cached files with HTTP blocked:
- the 2024 B03002 tract VRE files (MI, NY);
- cached 2024 tract API responses for B26001 (group-quarters population) and B01003 (total population).

Defaults: bias-corrected indices, negative replicates clipped. Outputs are archived at
`/tmp/r57_example_outputs.tar.gz` (sha256 `f54b5375…730b68ad`).

## Validated counties with the Round 57 ranges (Theil H, 145 counties)

| Design | Validated | Counties with clipped replicates | Of those validated | Round 52 example |
| :--- | ---: | ---: | ---: | ---: |
| Black vs non-Black | 114 | 24 | 22 | 102 |
| Four groups | 130 | 43 | 42 | 88 |
| Six groups | 56 | 63 | 0 | not offered |

The clipped-replicate ranges now extend above .50, so 12 more Black–non-Black and 42 more four-group counties are
validated. Six-group counties with a clipped replicate stay exploratory. Clipping was not tested with six groups,
and six-group designs have many small cells (63 of 145 counties have a negative replicate).

## Group-quarters tracts

126 MI/NY tracts have a group-quarters share of at least .5 (B26001 / B01003). Leaving them out changes the
counties that topped Round 52's list:

| County | Black–non-Black H, all tracts | Without group-quarters tracts | Four-group H, all | Without |
| :--- | :--- | :--- | :--- | :--- |
| Wyoming, NY | 0.519 | 0.040 | 0.225 | 0.044 |
| Greene, NY | 0.426 | 0.131 | 0.154 | 0.047 |
| Chippewa, MI | 0.586 (exploratory) | 0.250 (exploratory) | 0.202 | 0.080 |

Their high values came from prison tracts. Residential segregation there is low. A study of residential
segregation should register the exclusion (`args.group_quarters`).

## Same-release county contrast

Black–non-Black H, Wayne minus Oakland (MI): 0.164 (90% CI 0.148–0.179), validated. Same-release county contrasts
are validated since Round 57, except for corrected D.

## Limits

Exploratory and descriptive. The group-quarters rule (share ≥ .5) is one reasonable threshold, not a validated
quantity. Clipped six-group counties are not validated.
