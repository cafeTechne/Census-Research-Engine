# Layer B Tier 2 Neural RAG Benchmark (Round 186 / N127)

- **Timestamp (UTC):** `2026-11-27T14:46:44.560294+00:00`
- **Status:** `exploratory_hypothesis_seed` (isolated Layer B; zero `census/` imports)
- **Corpus (`index.sqlite`):** `2631` deduplicated papers
- **Passages (`passages.sqlite`):** `1148` passages across `67` documents
- **Vectors (`vectors.sqlite`):** `{'BAAI/bge-small-en-v1.5': 2631, 'hash_projection_d256': 2631}`
- **Neural Embedder:** `BAAI/bge-small-en-v1.5` (`active=True`)

## Latency & Ranking Overlap Across 5 Domain Queries

| Query | Lexical (ms) | Hash 3-way (ms) | Neural BGE 3-way (ms) | Jaccard(Hash, Lex) | Jaccard(Neural, Lex) |
| --- | ---: | ---: | ---: | ---: | ---: |
| county mortality spatial autocorrelation small area estimati | 14.81 | 79.84 | 54.81 | 0.6 | 0.4545 |
| PUMA ecologic fallacy microdata aggregation bias American Co | 16.28 | 32.39 | 159.99 | 0.7778 | 0.4545 |
| regional price parity cost of living poverty measurement BEA | 26.47 | 90.48 | 72.3 | 0.4545 | 0.6 |
| race residential segregation dissimilarity isolation index c | 51.81 | 87.67 | 97.31 | 0.7778 | 0.7778 |
| opioid overdose suicide despair mortality rural urban socioe | 12.74 | 62.11 | 62.54 | 0.4545 | 0.6 |

## Top-3 Retrieved Papers per Query (Neural BGE 3-way vs. Lexical)

### Query: `county mortality spatial autocorrelation small area estimation BYM2`
- **Lexical BM25 top-3:**
  - Small Area Estimation for Demographic Analysis
  - Dengue fever mapping in Bangladesh: A spatial modeling approach
  - Small area disease mapping of cancer incidence in British Columbia using Bayesian spatial models and the smallareamapp R Package
- **Neural BGE 3-way top-3:**
  - Multivariate spatial hierarchical Bayesian empirical likelihood methods for small area estimation
  - Small Area Estimation for Demographic Analysis
  - Are continuous models better than areal models for spatial disease mapping with a large number of small areas?

### Query: `PUMA ecologic fallacy microdata aggregation bias American Community Survey`
- **Lexical BM25 top-3:**
  - Ecologic versus individual-level sources of bias in ecologic estimates of contextual health effects
  - Revisiting Robinson: The perils of individualistic and ecologic fallacy
  - Designs for the combination of group- and individual-level data
- **Neural BGE 3-way top-3:**
  - Ecologic versus individual-level sources of bias in ecologic estimates of contextual health effects
  - Designs for the combination of group- and individual-level data
  - Generating synthetic microdata to estimate small area statistics in the American Community Survey

### Query: `regional price parity cost of living poverty measurement BEA`
- **Lexical BM25 top-3:**
  - Migration and regional factors affecting the wages of Asian American men
  - Institutional Fault Lines and the Poverty Paradox: Gender Parity, Ecological Depletion, and the Limits of Growth Led Poverty Reduction in South Asia
  - Poverty Indicators at Local Level: Definitions, Comparisons in Real Terms and Small Area Estimation Methods
- **Neural BGE 3-way top-3:**
  - Poverty Indicators at Local Level: Definitions, Comparisons in Real Terms and Small Area Estimation Methods
  - Recent Advances in Small Area Estimation of Economic and Poverty Indicators using Traditional and Alternative Data
  - Institutional Fault Lines and the Poverty Paradox: Gender Parity, Ecological Depletion, and the Limits of Growth Led Poverty Reduction in South Asia

### Query: `race residential segregation dissimilarity isolation index census tract`
- **Lexical BM25 top-3:**
  - Race/Ethnicity, Socioeconomic Status, Residential Segregation, and Spatial Variation in Noise Exposure in the Contiguous United States
  - Relationship between Residential Segregation, Later-Life Cognition, and Incident Dementia across Race/Ethnicity
  - Racial Segregation, Transportation, and Unemployment Rates in the United States
- **Neural BGE 3-way top-3:**
  - Measuring Residential Segregation With the ACS: How the Margin of Error Affects the Dissimilarity Index
  - Racial Segregation, Transportation, and Unemployment Rates in the United States
  - Segregation, turnover, and neighborhood connections : assessing the role of family structure

### Query: `opioid overdose suicide despair mortality rural urban socioeconomic`
- **Lexical BM25 top-3:**
  - Deaths of Despair Among Cancer Survivors in Rural/Urban Appalachia (2000-2022)
  - Deaths of Despair: A Scoping Review on the Social Determinants of Drug Overdose, Alcohol-Related Liver Disease and Suicide
  - Rural–Urban Suicide Mortality Disparities in High-Burden U.S. States: An Intersectional Analysis
- **Neural BGE 3-way top-3:**
  - Deaths of Despair Among Cancer Survivors in Rural/Urban Appalachia (2000-2022)
  - Rural–Urban Suicide Mortality Disparities in High-Burden U.S. States: An Intersectional Analysis
  - Deaths of Despair: A Scoping Review on the Social Determinants of Drug Overdose, Alcohol-Related Liver Disease and Suicide
