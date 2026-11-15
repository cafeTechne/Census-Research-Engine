# Held-out split-tract apportionment re-test: registration (Round 22)

Pre-registered hypothesis: **split targets that hold at least 95% of their parent
tract's 2010 population behave like 1:1 targets.**

Held-out states: Ohio (39) and Pennsylvania (42), excluding Michigan and New York.
ACS 2015–2019 B18101 crude disability prevalence on 2010 tracts, apportioned with
2010 block-population masses to 2020 tracts, compared against ACS 2016–2020 native
tract estimates. z=(apportioned-native)/sqrt(se_apportioned²+se_native²).

Fixed criterion: median |z| among split targets with parent share >=0.95 divided
by the 1:1 median |z| <=1.25. Empty/undefined comparisons fail. Other share bands
and merged/complex targets are descriptive. No seeds or acceptance criteria may
be changed after inspecting the held-out results. The engine's default remains
split=missing regardless of this result. Add opt-in dominant only on PASSED.

Status: registered before running. The execution replaces this file with the
registered design, full results, decision and pre-run commit identity.

Command: `.venv/bin/python scripts/rate_apportionment_validation.py --states 39 42 --parent-share-min 0.95 --out docs/audits/rate_apportionment_retest.md`
