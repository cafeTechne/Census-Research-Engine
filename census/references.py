# SPDX-License-Identifier: AGPL-3.0-or-later
"""Method attribution: the published sources behind every engine method (Round 88; backlog N70).

Each source has an id, a kind (``paper``, ``book``, ``software``, ``data``, ``documentation``) and either the
pre-formatted text used in manifest methods sections (kept byte-identical) or structured fields. ``TOOL_SOURCES``
maps every MCP tool to the sources it rests on, each with a role:
- ``method``: papers that define the method the tool computes;
- ``guidance``: textbooks whose guidance shaped how the engine applies it;
- ``data``: data products the tool reads;
- ``software``: libraries whose algorithms the tool calls;
- ``validation``: the engine's own audit that validated (or failed) the method.
Entries marked ``verified=False`` were recorded from memory and should be checked before publication; outputs say
so. A test requires every registered tool to have an entry and every cited id to exist.
"""
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .manifest.schema import REFERENCES as _MANIFEST_TEXT

ROLES = ("method", "guidance", "data", "software", "validation")


def _src(kind, authors, year, title, container="", publisher="", volume="", pages="", doi="", url="",
         verified=True, note=""):
    return dict(kind=kind, authors=authors, year=year, title=title, container=container, publisher=publisher,
                volume=volume, pages=pages, doi=doi, url=url, verified=verified, note=note)


SOURCES: Dict[str, Dict[str, Any]] = {
    # ---- textbooks whose guidance shaped the engine (docs/literature/)
    "bovbjerg2020": _src("book", "Bovbjerg, M.L.", 2020, "Foundations of Epidemiology", publisher="Oregon State University",
                         url="https://open.oregonstate.education/epidemiology/",
                         note="CC BY-NC 4.0; guidance for Rounds 82-87 (docs/literature/foundations_of_epidemiology.md)"),
    "hernan_robins2020": _src("book", "Hernán, M.A. & Robins, J.M.", 2020, "Causal Inference: What If",
                              publisher="Chapman & Hall/CRC, Boca Raton",
                              url="https://www.hsph.harvard.edu/miguel-hernan/causal-inference-book/",
                              note="draft of 10 November 2019 used; guidance for Rounds 89-91 "
                                   "(docs/literature/hernan_robins_what_if.md)"),
    "walker2023": _src("book", "Walker, K.", 2023, "Analyzing US Census Data: Methods, Maps, and Models in R",
                       publisher="CRC Press, Boca Raton", url="https://walker-data.com/census-r/",
                       note="online edition used; guidance for Rounds 92-93 "
                            "(docs/literature/walker_analyzing_us_census_data.md)"),
    # ---- methods
    "greenland_robins1985": _src("paper", "Greenland, S. & Robins, J.M.", 1985,
                                 "Estimation of a common effect parameter from sparse follow-up data", "Biometrics",
                                 volume="41", pages="55-68"),
    "rbg1986": _src("paper", "Robins, J., Breslow, N. & Greenland, S.", 1986,
                    "Estimators of the Mantel-Haenszel variance consistent in both sparse data and large-strata "
                    "limiting models", "Biometrics", volume="42", pages="311-323"),
    "mantel_haenszel1959": _src("paper", "Mantel, N. & Haenszel, W.", 1959,
                                "Statistical aspects of the analysis of data from retrospective studies of disease",
                                "Journal of the National Cancer Institute", volume="22", pages="719-748"),
    "tarone1985": _src("paper", "Tarone, R.E.", 1985, "On heterogeneity tests based on efficient scores", "Biometrika",
                       volume="72", pages="91-95"),
    "rothman1976": _src("paper", "Rothman, K.J.", 1976, "The estimation of synergy or antagonism",
                        "American Journal of Epidemiology", volume="103", pages="506-511"),
    "vanderweele_ding2017": _src("paper", "VanderWeele, T.J. & Ding, P.", 2017,
                                 "Sensitivity analysis in observational research: introducing the E-value",
                                 "Annals of Internal Medicine", volume="167", pages="268-274", doi="10.7326/M16-2607"),
    "lash_fox_fink2009": _src("book", "Lash, T.L., Fox, M.P. & Fink, A.K.", 2009,
                              "Applying Quantitative Bias Analysis to Epidemiologic Data", publisher="Springer, New York"),
    "kim2000": _src("paper", "Kim, H.-J., Fay, M.P., Feuer, E.J. & Midthune, D.N.", 2000,
                    "Permutation tests for joinpoint regression with applications to cancer rates",
                    "Statistics in Medicine", volume="19", pages="335-351"),
    "tiwari2006": _src("paper", "Tiwari, R.C., Clegg, L.X. & Zou, Z.", 2006,
                       "Efficient interval estimation for age-adjusted cancer rates",
                       "Statistical Methods in Medical Research", volume="15", pages="547-569"),
    "fay_feuer1997": _src("paper", "Fay, M.P. & Feuer, E.J.", 1997,
                          "Confidence intervals for directly standardized rates: a method based on the gamma "
                          "distribution", "Statistics in Medicine", volume="16", pages="791-801"),
    "callaway_santanna2021": _src("paper", "Callaway, B. & Sant'Anna, P.H.C.", 2021,
                                  "Difference-in-differences with multiple time periods", "Journal of Econometrics",
                                  volume="225", pages="200-230", doi="10.1016/j.jeconom.2020.12.001"),
    "sun_abraham2021": _src("paper", "Sun, L. & Abraham, S.", 2021,
                            "Estimating dynamic treatment effects in event studies with heterogeneous treatment effects",
                            "Journal of Econometrics", volume="225", pages="175-199",
                            doi="10.1016/j.jeconom.2020.09.006"),
    "goodman_bacon2021": _src("paper", "Goodman-Bacon, A.", 2021,
                              "Difference-in-differences with variation in treatment timing", "Journal of Econometrics",
                              volume="225", pages="254-277"),
    "abadie2010": _src("paper", "Abadie, A., Diamond, A. & Hainmueller, J.", 2010,
                       "Synthetic control methods for comparative case studies: estimating the effect of California's "
                       "tobacco control program", "Journal of the American Statistical Association", volume="105",
                       pages="493-505", doi="10.1198/jasa.2009.ap08746"),
    "chernozhukov2021": _src("paper", "Chernozhukov, V., Wüthrich, K. & Zhu, Y.", 2021,
                             "An exact and robust conformal inference method for counterfactual and synthetic controls",
                             "Journal of the American Statistical Association", volume="116", pages="1849-1864"),
    "oaxaca1973": _src("paper", "Oaxaca, R.", 1973, "Male-female wage differentials in urban labor markets",
                       "International Economic Review", volume="14", pages="693-709"),
    "blinder1973": _src("paper", "Blinder, A.S.", 1973, "Wage discrimination: reduced form and structural estimates",
                        "Journal of Human Resources", volume="8", pages="436-455"),
    "neumark1988": _src("paper", "Neumark, D.", 1988,
                        "Employers' discriminatory behavior and the estimation of wage discrimination",
                        "Journal of Human Resources", volume="23", pages="279-295"),
    "jann2008": _src("paper", "Jann, B.", 2008, "The Blinder-Oaxaca decomposition for linear regression models",
                     "The Stata Journal", volume="8", pages="453-479"),
    "yun2005": _src("paper", "Yun, M.-S.", 2005, "A simple solution to the identification problem in detailed wage "
                    "decompositions", "Economic Inquiry", volume="43", pages="766-772"),
    "fairlie2005": _src("paper", "Fairlie, R.W.", 2005, "An extension of the Blinder-Oaxaca decomposition technique to "
                        "logit and probit models", "Journal of Economic and Social Measurement", volume="30",
                        pages="305-316"),
    "fay_herriot1979": _src("paper", "Fay, R.E. & Herriot, R.A.", 1979, "Estimates of income for small places: an "
                            "application of James-Stein procedures to census data",
                            "Journal of the American Statistical Association", volume="74", pages="269-277"),
    "rao_yu1994": _src("paper", "Rao, J.N.K. & Yu, M.", 1994, "Small-area estimation by combining time-series and "
                       "cross-sectional data", "Canadian Journal of Statistics", volume="22", pages="511-528"),
    "hadam2020": _src("paper", "Hadam, S., Würz, N. & Kreutzmann, A.-K.", 2020, "Estimating regional unemployment "
                      "with mobile network data for functional urban areas in Germany", "working paper",
                      verified=False, note="arcsine Fay-Herriot (Round 80, census/sae_extensions_core.py); title and outlet "
                      "recorded from memory"),
    "kulldorff1997": _src("paper", "Kulldorff, M.", 1997, "A spatial scan statistic",
                          "Communications in Statistics - Theory and Methods", volume="26", pages="1481-1496"),
    "pearl2009": _src("book", "Pearl, J.", 2009, "Causality: Models, Reasoning, and Inference (2nd ed.)",
                      publisher="Cambridge University Press, Cambridge"),
    "lauritzen1990": _src("paper", "Lauritzen, S.L., Dawid, A.P., Larsen, B.N. & Leimer, H.-G.", 1990,
                          "Independence properties of directed Markov fields", "Networks", volume="20", pages="491-505"),
    "li_morgan_zaslavsky2018": _src("paper", "Li, F., Morgan, K.L. & Zaslavsky, A.M.", 2018, "Balancing covariates via "
                                    "propensity score weighting", "Journal of the American Statistical Association",
                                    volume="113", pages="390-400", doi="10.1080/01621459.2016.1260466"),
    "lunceford_davidian2004": _src("paper", "Lunceford, J.K. & Davidian, M.", 2004, "Stratification and weighting via "
                                   "the propensity score in estimation of causal treatment effects: a comparative "
                                   "study", "Statistics in Medicine", volume="23", pages="2937-2960"),
    "cole_hernan2008": _src("paper", "Cole, S.R. & Hernán, M.A.", 2008, "Constructing inverse probability weights for "
                            "marginal structural models", "American Journal of Epidemiology", volume="168",
                            pages="656-664", doi="10.1093/aje/kwn164"),
    "brunsdon1996": _src("paper", "Brunsdon, C., Fotheringham, A.S. & Charlton, M.E.", 1996, "Geographically weighted "
                         "regression: a method for exploring spatial nonstationarity", "Geographical Analysis",
                         volume="28", pages="281-298"),
    "assuncao2006": _src("paper", "Assunção, R.M., Neves, M.C., Câmara, G. & da Costa Freitas, C.", 2006, "Efficient "
                         "regionalization techniques for socio-economic geographical units using minimum spanning trees",
                         "International Journal of Geographical Information Science", volume="20", pages="797-811"),
    "who2013": _src("book", "World Health Organization", 2013, "Handbook on Health Inequality Monitoring: With a Special "
                    "Focus on Low- and Middle-Income Countries", publisher="WHO, Geneva",
                    url="https://www.who.int/publications/i/item/9789241548632",
                    note="guidance for Round 94 (docs/literature/who_health_inequality_monitoring.md)"),
    "cdc_ss1000": _src("book", "Centers for Disease Control and Prevention", 2012, "Principles of Epidemiology in Public "
                       "Health Practice: An Introduction to Applied Epidemiology and Biostatistics (3rd ed., SS1000)",
                       publisher="U.S. Department of Health and Human Services, Atlanta",
                       url="https://archive.cdc.gov/www_cdc_gov/csels/dsepd/ss1978/index.html", verified=False,
                       note="guidance for Round 95 (docs/literature/cdc_principles_of_epidemiology.md); URL to verify"),
    "hutwagner2003": _src("paper", "Hutwagner, L., Thompson, W., Seeman, G.M. & Treadwell, T.", 2003, "The bioterrorism "
                          "preparedness and response Early Aberration Reporting System (EARS)", "Journal of Urban Health",
                          volume="80", pages="i89-i96"),
    "besag1991": _src("paper", "Besag, J., York, J. & Mollié, A.", 1991, "Bayesian image restoration, with two "
                      "applications in spatial statistics", "Annals of the Institute of Statistical Mathematics",
                      volume="43", pages="1-20"),
    "riebler2016": _src("paper", "Riebler, A., Sørbye, S.H., Simpson, D. & Rue, H.", 2016, "An intuitive Bayesian "
                        "spatial model for disease mapping that accounts for scaling", "Statistical Methods in Medical "
                        "Research", volume="25", pages="1145-1165"),
    "moraga2023": _src("book", "Moraga, P.", 2023, "Spatial Statistics for Data Science: Theory and Practice with R",
                       publisher="Chapman & Hall/CRC, Boca Raton", url="https://www.paulamoraga.com/book-spatial/",
                       note="guidance for Rounds 96-97 (docs/literature/moraga_spatial_statistics.md)"),
    "roberts2017": _src("paper", "Roberts, D.R. et al.", 2017, "Cross-validation strategies for data with temporal, "
                        "spatial, hierarchical, or phylogenetic structure", "Ecography", volume="40", pages="913-929"),
    "openshaw1984": _src("book", "Openshaw, S.", 1984, "The Modifiable Areal Unit Problem (CATMOG 38)",
                         publisher="Geo Books, Norwich"),
    "cct2014": _src("paper", "Calonico, S., Cattaneo, M.D. & Titiunik, R.", 2014, "Robust nonparametric confidence "
                    "intervals for regression-discontinuity designs", "Econometrica", volume="82", pages="2295-2326"),
    "ik2012": _src("paper", "Imbens, G. & Kalyanaraman, K.", 2012, "Optimal bandwidth choice for the regression "
                   "discontinuity estimator", "Review of Economic Studies", volume="79", pages="933-959"),
    "mccrary2008": _src("paper", "McCrary, J.", 2008, "Manipulation of the running variable in the regression "
                        "discontinuity design: a density test", "Journal of Econometrics", volume="142", pages="698-714"),
    "card_dobkin_maestas2008": _src("paper", "Card, D., Dobkin, C. & Maestas, N.", 2008, "The impact of nearly universal "
                                    "insurance coverage on health care utilization: evidence from Medicare",
                                    "American Economic Review", volume="98", pages="2242-2258"),
    "cunningham2021": _src("book", "Cunningham, S.", 2021, "Causal Inference: The Mixtape",
                           publisher="Yale University Press, New Haven", url="https://mixtape.scunning.com/",
                           note="2018 draft used; guidance for Rounds 98-99 (docs/literature/cunningham_mixtape.md)"),
    "muller_watson2022": _src("paper", "Müller, U.K. & Watson, M.W.", 2022, "Spatial correlation robust inference",
                              "Econometrica", volume="90", pages="2901-2935"),
    "prasad_rao1990": _src("paper", "Prasad, N.G.N. & Rao, J.N.K.", 1990, "The estimation of the mean squared error of "
                           "small-area estimators", "Journal of the American Statistical Association", volume="85",
                           pages="163-171"),
    "rubin1987": _src("book", "Rubin, D.B.", 1987, "Multiple Imputation for Nonresponse in Surveys",
                      publisher="Wiley, New York"),
    "rao_scott1984": _src("paper", "Rao, J.N.K. & Scott, A.J.", 1984, "On chi-squared tests for multiway contingency "
                          "tables with cell proportions estimated from survey data", "The Annals of Statistics",
                          volume="12", pages="46-60"),
    "korn_graubard1998": _src("paper", "Korn, E.L. & Graubard, B.I.", 1998, "Confidence intervals for proportions with "
                              "small expected number of positive counts estimated from survey data",
                              "Survey Methodology", volume="24", pages="193-201"),
    "fay_train1995": _src("paper", "Fay, R.E. & Train, G.F.", 1995, "Aspects of survey and model-based postcensal "
                          "estimation of income and poverty characteristics for states and counties",
                          "Proceedings of the Section on Government Statistics, American Statistical Association",
                          pages="154-159", note="successive difference replication (SDR) weights"),
    "moran1950": _src("paper", "Moran, P.A.P.", 1950, "Notes on continuous stochastic phenomena", "Biometrika",
                      volume="37", pages="17-23"),
    "anselin1995": _src("paper", "Anselin, L.", 1995, "Local indicators of spatial association - LISA",
                        "Geographical Analysis", volume="27", pages="93-115"),
    "kenward_roger1997": _src("paper", "Kenward, M.G. & Roger, J.H.", 1997, "Small sample inference for fixed effects "
                              "from restricted maximum likelihood", "Biometrics", volume="53", pages="983-997"),
    "anderson_rubin1949": _src("paper", "Anderson, T.W. & Rubin, H.", 1949, "Estimation of the parameters of a single "
                               "equation in a complete system of stochastic equations",
                               "Annals of Mathematical Statistics", volume="20", pages="46-63"),
    "robins_hernan_brumback2000": _src("paper", "Robins, J.M., Hernán, M.A. & Brumback, B.", 2000, "Marginal "
                                       "structural models and causal inference in epidemiology", "Epidemiology",
                                       volume="11", pages="550-560"),
    "hartung_knapp2001": _src("paper", "Hartung, J. & Knapp, G.", 2001, "On tests of the overall treatment effect in "
                              "meta-analysis with normally distributed responses", "Statistics in Medicine",
                              volume="20", pages="1771-1782"),
    "paule_mandel1982": _src("paper", "Paule, R.C. & Mandel, J.", 1982, "Consensus values and weighting factors",
                             "Journal of Research of the National Bureau of Standards", volume="87", pages="377-385"),
    "schuirmann1987": _src("paper", "Schuirmann, D.J.", 1987, "A comparison of the two one-sided tests procedure and "
                           "the power approach for assessing the equivalence of average bioavailability",
                           "Journal of Pharmacokinetics and Biopharmaceutics", volume="15", pages="657-680"),
    "bland_altman1986": _src("paper", "Bland, J.M. & Altman, D.G.", 1986, "Statistical methods for assessing agreement "
                             "between two methods of clinical measurement", "The Lancet", volume="327", pages="307-310"),
    "cohen1960": _src("paper", "Cohen, J.", 1960, "A coefficient of agreement for nominal scales",
                      "Educational and Psychological Measurement", volume="20", pages="37-46"),
    "cronbach1951": _src("paper", "Cronbach, L.J.", 1951, "Coefficient alpha and the internal structure of tests",
                         "Psychometrika", volume="16", pages="297-334"),
    "klein_wright2020": _src("paper", "Klein, M., Wright, T. & Wieczorek, J.", 2020, "A joint confidence region for an "
                             "overall ranking of populations", "Journal of the Royal Statistical Society Series C",
                             volume="69", pages="589-606"),
    "bootstrap_efron1993": _src("book", "Efron, B. & Tibshirani, R.J.", 1993, "An Introduction to the Bootstrap",
                                publisher="Chapman & Hall, New York"),
    "spatial_lesage2009": _src("book", "LeSage, J. & Pace, R.K.", 2009, "Introduction to Spatial Econometrics",
                               publisher="CRC Press, Boca Raton"),
    # ---- software
    "scipy": _src("software", "Virtanen, P. et al.", 2020, "SciPy 1.0: fundamental algorithms for scientific computing "
                  "in Python", "Nature Methods", volume="17", pages="261-272", doi="10.1038/s41592-019-0686-2"),
    "pysal": _src("software", "Rey, S.J. & Anselin, L.", 2007, "PySAL: a Python library of spatial analytical methods",
                  "The Review of Regional Studies", volume="37", pages="5-27"),
    # ---- data and documentation
    "acs_pums": _src("documentation", "U.S. Census Bureau", 2021, "Understanding and Using the American Community "
                     "Survey Public Use Microdata Sample Files: What Data Users Need to Know",
                     publisher="U.S. Government Publishing Office, Washington, DC",
                     url="https://www.census.gov/programs-surveys/acs/library/handbooks/pums.html"),
    "census_api": _src("data", "U.S. Census Bureau", 2024, "Census Data API", url="https://www.census.gov/data/developers.html"),
    "decennial2020": _src("data", "U.S. Census Bureau", 2021, "2020 Census Redistricting Data (P.L. 94-171) and "
                          "Demographic and Housing Characteristics File", url="https://www.census.gov/programs-surveys/decennial-census.html"),
    "tiger": _src("data", "U.S. Census Bureau", 2024, "TIGER/Line Shapefiles and cartographic boundary files",
                  url="https://www.census.gov/geographies/mapping-files.html"),
    "cdc_wonder": _src("data", "Centers for Disease Control and Prevention, National Center for Health Statistics", 2024,
                       "CDC WONDER: Underlying and Multiple Cause of Death files (manual exports)",
                       url="https://wonder.cdc.gov/"),
    "cdc_places": _src("data", "Centers for Disease Control and Prevention", 2024, "PLACES: Local Data for Better Health",
                       url="https://www.cdc.gov/places/"),
    "chr": _src("data", "University of Wisconsin Population Health Institute", 2025, "County Health Rankings & Roadmaps",
                url="https://www.countyhealthrankings.org/"),
    "usaleep": _src("data", "National Center for Health Statistics", 2018, "U.S. Small-Area Life Expectancy Estimates "
                    "Project (USALEEP)", url="https://www.cdc.gov/nchs/nvss/usaleep/usaleep.html"),
    "bea_rpp": _src("data", "U.S. Bureau of Economic Analysis", 2024, "Regional Price Parities by State and Metro Area",
                    url="https://www.bea.gov/data/prices-inflation/regional-price-parities-state-and-metro-area"),
    "bls_cpi_rs": _src("data", "U.S. Bureau of Labor Statistics", 2024, "Consumer Price Index Retroactive Series "
                       "(R-CPI-U-RS)", url="https://www.bls.gov/cpi/research-series/r-cpi-u-rs-home.htm"),
    "pep": _src("data", "U.S. Census Bureau", 2025, "Population Estimates Program: county population totals and "
                "characteristics (vintages 2019 and 2024)", url="https://www.census.gov/programs-surveys/popest.html"),
    "lodes": _src("data", "U.S. Census Bureau", 2024, "LEHD Origin-Destination Employment Statistics (LODES8)",
                  url="https://lehd.ces.census.gov/data/"),
    "acs_flows": _src("data", "U.S. Census Bureau", 2022, "American Community Survey county-to-county migration flows",
                      url="https://www.census.gov/topics/population/migration/guidance/county-to-county-migration-flows.html"),
    "cbp_ers": _src("data", "U.S. Census Bureau; USDA Economic Research Service", 2024, "County Business Patterns; "
                    "ERS county typology codes and Rural-Urban Continuum Codes",
                    url="https://www.census.gov/programs-surveys/cbp.html"),
}

# Existing manifest citations: text kept byte-identical (methods text and goldens depend on it).
for _k, _text in _MANIFEST_TEXT.items():
    SOURCES.setdefault(_k, dict(kind="paper", text=_text, verified=True))
for _k in ("acs", "vre", "design", "testing"):
    SOURCES[_k]["kind"] = "documentation"
SOURCES["statsmodels"]["kind"] = "software"


def _audit(name):
    return (f"audit:docs/audits/{name}", "validation")


ACS = [("acs", "data"), ("census_api", "data")]
MOE = [("acs", "method"), ("testing", "method"), ("walker2023", "guidance")]
REP = [("vre", "method"), ("design", "method")]
PUMS = [("acs_pums", "data"), ("fay_train1995", "method"), ("walker2023", "guidance")]
EPI = [("bovbjerg2020", "guidance")]
CAUSAL = [("hernan_robins2020", "guidance")]
GEO = [("tiger", "data"), ("walker2023", "guidance")]

TOOL_SOURCES: Dict[str, List[Tuple[str, str]]] = {
    # discovery and extraction
    **{t: ACS for t in ("list_states", "list_vintages", "list_places", "list_counties", "list_tracts", "list_zctas",
                        "search_tables", "list_variables", "describe_variable", "fetch_table_data", "query_data_profile",
                        "plan_extraction", "batch_download", "download_table", "replay_extraction", "generate_codebook",
                        "cache_import", "check_variable_concordance", "draft_crosswalk_override",
                        "record_crosswalk_review", "draft_rule_override", "record_rule_review", "validate_crosswalks",
                        "check_replicate_availability")},
    "get_recipe": [("acs", "guidance"), *EPI, *CAUSAL, ("walker2023", "guidance")],
    "get_research_protocol": [("acs", "guidance"), *EPI, *CAUSAL],
    "run_validation": [*ACS, _audit("validation_report.md")],
    "verify_proposition": [*ACS, ("testing", "method")],
    # estimates, MOEs and comparisons
    "calculate_cv": MOE, "calculate_significance": MOE, "derive_estimate": MOE,
    "aggregate_geographies": MOE, "median_from_distribution": [*MOE, ("design", "method")],
    "batch_significance": [*MOE, ("holm", "method"), ("bh", "method")],
    "minimum_detectable_difference": MOE,
    "reliability_profile": [*MOE, ("bovbjerg2020", "guidance")],
    "trend_test": [*MOE, ("fisher", "method")],
    "adjust_inflation": [("bls_cpi_rs", "data")], "adjust_for_place": [("bea_rpp", "data"), ("bls_cpi_rs", "data")],
    "place_adjust_frame": [("bea_rpp", "data"), ("bls_cpi_rs", "data")],
    "apportion_tracts": [("decennial2020", "data"), *GEO, _audit("rate_apportionment_validation.md")],
    "custom_area_mapping": [("decennial2020", "data"), *GEO],
    # analysis frames and models
    "build_analysis_frame": [*ACS, *REP, ("cbp_ers", "data"), ("chr", "data"), ("pep", "data"), ("lodes", "data"),
                             ("acs_flows", "data"), ("walker2023", "guidance")],
    "fit_model": [*REP, ("statsmodels", "software"), ("fuller", "method"), ("carroll", "method"), ("simex", "method"),
                  ("fay_herriot1979", "method"), ("muller_watson2022", "method"), ("cluster_im", "method"),
                  ("bovbjerg2020", "guidance"), _audit("inference_validation.md"), _audit("epi_measures_validation.md")],
    "compare_groups": [*REP, ("statsmodels", "software"), ("holm", "method"), _audit("omnibus_validation.md")],
    "correlation_matrix": [*REP, ("fisher", "method"), ("scipy", "software")],
    "rank_areas": [*MOE, ("klein_wright2020", "method"), _audit("ranking_validation.md")],
    "build_index": [*REP, ("cronbach1951", "method"), _audit("index_validation.md")],
    "check_agreement": [("bland_altman1986", "method"), ("cohen1960", "method"), _audit("agreement_validation.md")],
    "combine_estimates": [("paule_mandel1982", "method"), ("hartung_knapp2001", "method"), ("schuirmann1987", "method"),
                          _audit("evidence_validation.md")],
    "estimate_effect": [*CAUSAL, ("pearl2009", "method"), ("lauritzen1990", "method"), ("li_morgan_zaslavsky2018", "method"),
                        ("lunceford_davidian2004", "method"), ("anderson_rubin1949", "method"), ("statsmodels", "software"),
                        _audit("causal_validation.md"), _audit("causal_robustness_validation.md"),
                        _audit("positivity_validation.md")],
    "small_area_estimates": [("rao_yu1994", "method"), ("hadam2020", "method"),
                             _audit("sae_extensions_validation.md")],
    "spatial_small_area_estimates": [("pysal", "software"), *GEO],
    "multilevel_model": [("kenward_roger1997", "method"), ("statsmodels", "software"), _audit("methods73_validation.md")],
    "difference_in_differences": [*CAUSAL, ("callaway_santanna2021", "method"), ("sun_abraham2021", "method"),
                                  ("goodman_bacon2021", "method"), ("robins_hernan_brumback2000", "method"),
                                  ("cole_hernan2008", "method"), _audit("policy_validation.md"),
                                  _audit("msm_validation.md")],
    "interrupted_series": [("bootstrap_efron1993", "method"), _audit("missing_censored_its_validation.md")],
    "joinpoint": [("kim2000", "method"), ("tiwari2006", "method"), ("fay_feuer1997", "method"), *EPI,
                  ("cdc_ss1000", "guidance"), ("hutwagner2003", "method"), _audit("joinpoint_validation.md"),
                  _audit("surveillance_validation.md")],
    "disparity_measures": [("harper_lynch", "method"), ("pearcy_keppel", "method"), ("kitagawa", "method"), *EPI,
                           ("who2013", "guidance"), *REP, _audit("disparity_validation.md"),
                           _audit("inequality_monitoring_validation.md")],
    "stratified_analysis": [("mantel_haenszel1959", "method"), ("greenland_robins1985", "method"),
                            ("rbg1986", "method"), ("breslow", "method"), ("tarone1985", "method"),
                            ("rothman1976", "method"), *EPI, *CAUSAL, *PUMS, _audit("stratified_validation.md")],
    "designation_accuracy": [("fay_herriot1979", "method"), ("hadam2020", "method"), *EPI,
                             _audit("designation_validation.md")],
    "bias_analysis": [("vanderweele_ding2017", "method"), ("lash_fox_fink2009", "method"), *EPI, *CAUSAL,
                      _audit("bias_analysis_validation.md")],
    "decompose_gap": [("oaxaca1973", "method"), ("blinder1973", "method"), ("neumark1988", "method"),
                      ("jann2008", "method"), ("yun2005", "method"), ("fairlie2005", "method"), *PUMS,
                      _audit("decomposition_validation.md")],
    "spatial_scan": [("kulldorff1997", "method"), ("chr", "data"), *GEO, _audit("scan_validation.md")],
    # PUMS
    "pums_tabulate": [*PUMS, _audit("pums_tests_validation.md")],
    "pums_regression": [*PUMS, ("statsmodels", "software"), *EPI, _audit("pums_models_validation.md"),
                        _audit("epi_measures_validation.md"), _audit("ecologic_validation.md")],
    "test_association": [*PUMS, ("rao_scott1984", "method"), ("korn_graubard1998", "method"),
                         _audit("pums_tests_validation.md")],
    # spatial and maps
    "get_boundaries": GEO, "make_map": GEO, "make_web_map": GEO,
    "spatial_autocorrelation": [("moran1950", "method"), ("anselin1995", "method"), ("pysal", "software"), *GEO,
                                _audit("lisa_validation.md")],
    "spatial_model": [("brunsdon1996", "method"), ("assuncao2006", "method"), ("besag1991", "method"),
                      ("riebler2016", "method"), ("roberts2017", "method"), ("openshaw1984", "method"),
                      ("moraga2023", "guidance"), *GEO, ("scipy", "software"),
                      _audit("spatial_models_validation.md"), _audit("disease_mapping_validation.md"),
                      _audit("model_assessment_validation.md")],
    "regression_discontinuity": [("cct2014", "method"), ("ik2012", "method"), ("mccrary2008", "method"),
                                 ("card_dobkin_maestas2008", "method"), ("cunningham2021", "guidance"), *PUMS,
                                 _audit("rdd_validation.md")],
    "spatial_regression": [("spatial_lesage2009", "method"), ("pysal", "software"), *GEO,
                           _audit("spatial_regression_validation.md")],
    # health and context sources
    "list_health_sources": [("cdc_places", "data"), ("chr", "data"), ("usaleep", "data"), ("cdc_wonder", "data"),
                            ("pep", "data"), ("lodes", "data"), ("acs_flows", "data")],
    # reporting and manifests
    "make_figure": [("acs", "guidance")], "make_table": [("acs", "guidance"), *EPI],
    "make_results_bundle": [("acs", "guidance"), *EPI],
    "create_manifest": [("acs", "guidance"), *EPI, *CAUSAL], "run_manifest": [("acs", "guidance"), *REP, *EPI],
    "run_variant": [("acs", "guidance"), *REP],
}


# Tools whose module keeps its own reference list (texts shown verbatim in those tools' provenance).
MODULE_REFERENCES = {"small_area_estimates": "sae", "designation_accuracy": "sae", "spatial_small_area_estimates": "sae_spatial",
                     "multilevel_model": "multilevel", "difference_in_differences": "did"}

ENGINE_CITATION = ("cafeTechne. Census Research Engine. Zenodo concept DOI "
                   "10.5281/zenodo.23925301 (cite the version DOI of the release used; see CITATION.cff).")


def _module_ids(tool: str) -> List[str]:
    mod = MODULE_REFERENCES.get(tool)
    if not mod:
        return []
    import importlib
    refs = getattr(importlib.import_module(f"census.{mod}"), "REFERENCES", [])
    ids = []
    for i, text in enumerate(refs):
        sid = f"{mod}:{i}"
        SOURCES.setdefault(sid, dict(kind="paper", text=str(text), verified=True))
        ids.append(sid)
    return ids


def tool_entries(name: str) -> List[Tuple[str, str]]:
    """(source id, role) pairs for a tool, including its module's own reference list."""
    entries = list(TOOL_SOURCES.get(name, []))
    entries += [(sid, "method") for sid in _module_ids(name) if (sid, "method") not in entries]
    return entries


def citation_text(sid: str) -> str:
    """The source formatted in the engine's citation style (manifest entries keep their original text)."""
    s = SOURCES[sid]
    if "text" in s:
        return s["text"]
    parts = [f"{s['authors']} ({s['year']}). {s['title']}."]
    if s.get("container"):
        vol = f" {s['volume']}" if s.get("volume") else ""
        pages = f":{s['pages']}" if s.get("pages") else ""
        parts.append(f" {s['container']}{vol}{pages}.")
    if s.get("publisher"):
        parts.append(f" {s['publisher']}.")
    if s.get("doi"):
        parts.append(f" doi:{s['doi']}.")
    elif s.get("url"):
        parts.append(f" {s['url']}")
    text = "".join(parts)
    if not s.get("verified", True):
        text += " [details to verify]"
    return text


def _bib_authors(a: str) -> str:
    import re
    if "," not in a or ";" in a:
        return "{" + a + "}"  # corporate author(s)
    a = a.replace(" et al.", " and others").replace(" & ", " and ")
    return re.sub(r"\.,\s+(?=[A-ZÀ-Ý][^,]*,)", ". and ", a)


def _tex(v: str) -> str:
    return v.replace("&", r"\&").replace("%", r"\%").replace("#", r"\#").replace("_", r"\_")


def bibtex(sid: str) -> str:
    s = SOURCES[sid]
    if "text" in s:
        return "@misc{%s,\n  note = {%s}\n}" % (sid.replace(":", "_"), _tex(s["text"].replace("{", "").replace("}", "")))
    kind = {"paper": "article", "book": "book", "software": "article", "data": "misc", "documentation": "misc"}[s["kind"]]
    if s["kind"] == "book" and s.get("container"):
        kind = "incollection"
    fields = [("author", _bib_authors(s["authors"])), ("year", str(s["year"])), ("title", s["title"])]
    if s.get("container"):
        fields.append(("booktitle" if kind == "incollection" else "journal", s["container"]))
    for k in ("volume", "pages", "publisher", "doi", "url"):
        if s.get(k):
            fields.append((k, s[k].replace("-", "--") if k == "pages" else s[k]))
    if not s.get("verified", True):
        fields.append(("note", "details to verify"))
    return "@%s{%s,\n%s\n}" % (kind, sid.replace(":", "_"),
                                 ",\n".join(f"  {k} = {{{v if k in ('url', 'doi', 'author') else _tex(v)}}}" for k, v in fields))


def sources_for_tool(name: str) -> List[Dict[str, Any]]:
    """``method_sources`` for a tool result: [{id, role, citation} or {role: validation, audit}]."""
    out = []
    for sid, role in tool_entries(name):
        if sid.startswith("audit:"):
            out.append({"role": role, "audit": sid[len("audit:"):]})
        else:
            out.append({"id": sid, "role": role, "citation": citation_text(sid)})
    return out


def attach(name: str, result: Any) -> Any:
    """A copy of a successful tool result dict with ``method_sources`` added (the MCP and CLI tool boundaries call
    this; failures and non-dict results pass through unchanged, and the original dict is never mutated)."""
    if isinstance(result, dict) and result.get("success", True) is not False and "method_sources" not in result \
            and applies_methods(name):
        return {**result, "method_sources": sources_for_tool(name)}
    return result


def applies_methods(name: str) -> bool:
    """True for tools with method or guidance sources; pure discovery/extraction tools (data sources only) get no
    method_sources, which keeps their frequent results small for local models (their data citation is in provenance)."""
    return any(role in ("method", "guidance") for _, role in tool_entries(name))


def attributed(fn):
    """Wrap a tool function so its successful results carry ``method_sources``."""
    from functools import wraps

    @wraps(fn)
    def wrapped(*args, **kwargs):
        return attach(fn.__name__, fn(*args, **kwargs))
    return wrapped


def cite(ids: Iterable[str], fmt: str = "text") -> str:
    """Formatted references (``text`` or ``bibtex``) for source ids, de-duplicated, in the given order."""
    seen = list(dict.fromkeys(i for i in ids if i in SOURCES))
    if fmt == "bibtex":
        return "\n\n".join(bibtex(i) for i in seen)+"\n"
    return "\n".join(f"- {citation_text(i)}" for i in seen)+"\n"


def tool_reference(name: str, fmt: str = "text") -> str:
    """References for one tool, grouped by role (the ``python -m census cite --tool`` output)."""
    entries = tool_entries(name)
    if fmt == "bibtex":
        return cite([sid for sid, _ in entries if not sid.startswith("audit:")], "bibtex")
    return render_sources({r: [sid for sid, role in entries if role == r] for r in ROLES})


ROLE_HEADINGS = {"method": "Methods", "guidance": "Guidance texts", "data": "Data", "software": "Software",
                 "validation": "Engine validation audits"}


def render_sources(by_role: Mapping[str, Sequence[str]], heading: str = "") -> str:
    """Markdown list of sources by role; audits are listed by path; the engine's own citation comes last."""
    lines = [heading, ""] if heading else []
    for role in ROLES:
        ids = [i for i in by_role.get(role) or [] if i.startswith("audit:") or i in SOURCES]
        if not ids:
            continue
        lines.append(f"**{ROLE_HEADINGS[role]}**")
        lines.append("")
        lines += [f"- `{i[len('audit:'):]}`" if i.startswith("audit:") else f"- {citation_text(i)}" for i in ids]
        lines.append("")
    lines += ["**Engine**", "", f"- {ENGINE_CITATION}", ""]
    return "\n".join(lines)


def collect(results: Iterable[Mapping[str, Any]]) -> Dict[str, List[str]]:
    """Source ids by role from saved tool results (their ``method_sources``)."""
    by_role: Dict[str, List[str]] = {r: [] for r in ROLES}
    for res in results:
        for s in (res or {}).get("method_sources") or []:
            key = s.get("id") or ("audit:"+s["audit"] if s.get("audit") else None)
            if key and key not in by_role[s["role"]]:
                by_role[s["role"]].append(key)
    return by_role
