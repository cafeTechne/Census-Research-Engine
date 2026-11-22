# SPDX-License-Identifier: AGPL-3.0-or-later
"""Stratified analysis: Mantel-Haenszel pooling, homogeneity, confounding vs effect modification and additive
interaction (Round 83; backlog N60; Foundations of Epidemiology chapters 7-8).

Validation: ``docs/audits/stratified_validation.md`` (criterion ``stratified_validation_criterion.md``); computation
is the frozen core :mod:`census.stratified_core`.
- Validated: MH pooled RR, OR, RD and IRR for counts (.877-.906 down to 5 expected cases per stratum and arm);
  MH pooled RR, OR, RD on PUMS with SDR replicate weights (.881-.909 from 300 records in the smallest stratum);
  RERI by delta (.895-) and bootstrap (.887-) for counts and by SDR for PUMS (.891-); Breslow-Day-Tarone
  homogeneity of ORs (size .102-.114 at .10).
- Exploratory: the Woolf-type RR homogeneity test (too conservative with many sparse strata, size .032-.113) and
  the PUMS replicate Wald homogeneity test (liberal with four strata, size .099-.151). Their p-values are reported
  with a flag; the effect-modification label then rests on Breslow-Day (OR) or is marked exploratory.
- The confounder / effect-modifier / neither label (book Table 8-5, 10% change rule) is descriptive, not a test.
"""
from typing import Any, Dict, Optional, Sequence

import numpy as np
import pandas as pd

from . import stratified_core as sc

AUDIT = "docs/audits/stratified_validation.md"
VALIDATED = {"mh_counts": True, "mh_pums": True, "reri_counts": True, "reri_pums": True,
             "breslow_day": True, "woolf": False, "pums_wald": False}
ROLE_NOTE = ("Classification follows Foundations of Epidemiology Table 8-5: stratum measures that differ "
             "(homogeneity p <= .10) with the crude between them indicate an effect modifier (report each stratum); "
             "otherwise a crude-to-adjusted change above 10% indicates a confounder (report the adjusted measure). "
             "It is descriptive, not a test. It is an associational label (10% rule): a causal diagram, not the change "
             "in estimate, decides whether to adjust, because associational rules can recommend adjusting for a "
             "collider (Hernán and Robins 7.4; Round 89: estimate_effect(dag=...) or the manifest dag block).")


def _label(crude, pooled, strata, p_hom, measure):
    het = bool(p_hom is not None and np.isfinite(p_hom) and p_hom <= .10)
    return sc.classify(float(crude), float(pooled), np.asarray(strata, float), het)


def stratified_counts(frame: pd.DataFrame, stratum: str, cases_exposed: str, total_exposed: str,
                      cases_unexposed: str, total_unexposed: str, person_time: bool = False,
                      level: float = .90) -> Dict[str, Any]:
    """Counts by stratum (one row per stratum): MH pooled measures, crude, stratum measures, homogeneity and the
    classification. ``person_time``: the totals are person-time (gives the MH rate ratio)."""
    f = frame[[stratum, cases_exposed, total_exposed, cases_unexposed, total_unexposed]].dropna()
    if len(f) < 2:
        raise ValueError("at least two strata are needed")
    a, n1, c, n0 = (f[k].to_numpy(float) for k in (cases_exposed, total_exposed, cases_unexposed, total_unexposed))
    if (a < 0).any() or (c < 0).any() or (n1 <= 0).any() or (n0 <= 0).any():
        raise ValueError("cases must be non-negative and totals positive")
    strata = f[stratum].astype(str).tolist()
    notes = [ROLE_NOTE]
    if person_time:
        r = sc.mh_rate_ratio(a, n1, c, n0, level)
        rates = (a/n1)/(c/n0)
        crude_irr = (a.sum()/n1.sum())/(c.sum()/n0.sum())
        return dict(measure="rate_ratio", pooled={k: float(v) for k, v in r.items()}, crude=float(crude_irr),
                    strata=dict(zip(strata, map(float, rates))), validated=VALIDATED["mh_counts"], notes=notes,
                    audit=AUDIT)
    if ((a > n1) | (c > n0)).any():
        raise ValueError("cases cannot exceed totals")
    b, d = n1-a, n0-c
    pooled = sc.mh_pooled(a, b, c, d, level)
    cr = sc.crude(a, b, c, d); sm = sc.stratum_measures(a, b, c, d)
    bd_stat, bd_p, _ = sc.breslow_day_tarone(a, b, c, d, pooled["or"]["estimate"])
    w_stat, w_p, _ = sc.woolf_rr(a, b, c, d, pooled["rr"]["estimate"])
    hom = {"or": dict(test="Breslow-Day-Tarone", statistic=float(bd_stat), p=float(bd_p), validated=True),
           "rr": dict(test="Woolf-type", statistic=float(w_stat), p=float(w_p), validated=False)}
    labels = {"or": _label(cr["or"], pooled["or"]["estimate"], sm["or"], bd_p, "or"),
              "rr": _label(cr["rr"], pooled["rr"]["estimate"], sm["rr"], w_p, "rr")}
    notes.append("The RR homogeneity test (Woolf-type) is exploratory (too conservative with sparse strata); the OR "
                 "homogeneity test (Breslow-Day-Tarone) is validated.")
    from .bias_analysis_core import e_value as _ev  # Round 86
    for m in ("rr", "or"):
        x = pooled[m]
        pooled[m]["e_value"] = _ev(float(x["estimate"]), float(x["lower"]), float(x["upper"]),
                                   "rr" if m == "rr" else "or", float(c.sum()/n0.sum()) if m == "or" else None)["e_value"]
    return dict(measure="risk", pooled={m: {k: float(v) for k, v in x.items()} for m, x in pooled.items()},
                crude={k: float(v) for k, v in cr.items()},
                strata={m: dict(zip(strata, map(float, v))) for m, v in sm.items()}, homogeneity=hom,
                classification=labels, classification_basis="associational (10% rule)",
                validated=VALIDATED["mh_counts"], notes=notes, audit=AUDIT)


def stratified_pums(y: np.ndarray, e: np.ndarray, s: np.ndarray, W: np.ndarray, strata: Sequence[Any],
                    level: float = .90) -> Dict[str, Any]:
    """PUMS records (0/1 outcome y, 0/1 exposure e, stratum codes s, weight matrix W = full then 80 replicates)."""
    est, hom, sm, cr = sc.mh_replicate(np.asarray(y), np.asarray(e), np.asarray(s), np.asarray(W, float), list(strata), level)
    labels = {m: _label(cr[m], est[m]["estimate"], sm[m], hom[m]["p"], m) for m in ("rr", "or", "rd")}
    counts = {str(k): int((np.asarray(s) == k).sum()) for k in strata}
    notes = [ROLE_NOTE, "Homogeneity tests on PUMS (replicate Wald) are exploratory: they rejected too often with four "
             "strata (size up to .151 at .10); the classification label is therefore exploratory."]
    if min(counts.values()) < 300:
        notes.append(f"A stratum has fewer than 300 records ({min(counts.values())}); validation started at 300.")
    return dict(pooled=est, crude={k: float(v) for k, v in cr.items()},
                strata={m: dict(zip(map(str, strata), map(float, v))) for m, v in sm.items()},
                homogeneity={m: dict(h, test="replicate Wald", validated=False) for m, h in hom.items()},
                classification=labels, classification_basis="associational (10% rule)", records=counts,
                validated=VALIDATED["mh_pums"] and min(counts.values()) >= 300, notes=notes, audit=AUDIT)


def additive_interaction(cases: Optional[Sequence[float]] = None, totals: Optional[Sequence[float]] = None,
                         risks: Optional[np.ndarray] = None, level: float = .90, seed: int = 20282383) -> Dict[str, Any]:
    """RERI, AP and S for two binary factors. Counts: ``cases`` and ``totals`` for cells (00, 10, 01, 11);
    PUMS: ``risks`` (81, 4) weighted cell risks (full sample then replicates)."""
    if risks is not None:
        r = np.asarray(risks, float)
        out = sc.reri(r[0], reps=r[1:], level=level)
        basis = "SDR replicate SE"
    else:
        out = sc.reri_counts(np.asarray(cases, float), np.asarray(totals, float), level=level,
                             rng=np.random.default_rng(seed))
        basis = "delta method (bootstrap percentile interval also given)"
    res = {k: float(v) for k, v in out.items()}
    res.update(basis=basis, validated=True, audit=AUDIT,
               note="RERI > 0 means the joint effect exceeds the sum of the separate effects on the risk-difference "
                    "scale (additive interaction); report it with the multiplicative (ratio) results.")
    return res
