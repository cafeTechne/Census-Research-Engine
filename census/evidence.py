# SPDX-License-Identifier: AGPL-3.0-or-later
"""Combining evidence across studies or replications (Round 38).

Validated by ``docs/audits/evidence_validation.md`` (criterion 3edd5f4):
- pooled effect: Paule-Mandel tau^2 with the Hartung-Knapp-Sidik-Jonkman interval passed for 2 and 4
  studies (.885-.911) and fell short at 8 with heterogeneity (.855); the fixed-effect interval is
  valid only when the studies share one effect (.884-.898; .44-.72 with heterogeneity);
  DerSimonian-Laird under-covered with heterogeneity (.82-.84) and is not offered as validated.
- TOST equivalence: size at the margin <= .046 (nominal .05).
- z-test power and minimum detectable effects: within .008 of simulation.
"""
from typing import Any, Dict, Optional, Sequence

import numpy as np

from . import evidence_core as ev

AUDIT = "docs/audits/evidence_validation.md"
HKSJ_VALIDATED_MAX_K = 4


def combine_estimates(estimates: Sequence[float], ses: Sequence[float], *, method: str = "hksj",
                      assume_homogeneous: bool = False, labels: Optional[Sequence[str]] = None,
                      level: float = 0.90) -> Dict[str, Any]:
    """Pool estimates of one effect. ``assume_homogeneous`` must be declared in advance to use the
    fixed-effect interval as validated."""
    if method not in ("hksj", "fixed", "dl"):
        raise ValueError("method must be 'hksj' (default), 'fixed' or 'dl'")
    from . import small_spatial as ss
    from . import small_spatial_core as ssc
    theta, se = np.asarray(estimates, float), np.asarray(ses, float)
    k = len(theta)
    truncated = method == "hksj" and k > HKSJ_VALIDATED_MAX_K
    if truncated:
        t = ssc.hksj_truncated(theta, se, level)
        out = dict(ev.pooled(theta, se, "hksj", level), estimate=t["estimate"], se=t["se"], lower=t["lower"],
                   upper=t["upper"], variance_factor=t["q"], method="hksj_truncated")
    else:
        out = ev.pooled(theta, se, method, level)
    het = ev.heterogeneity(theta, se)
    if method == "hksj":
        validated = k <= ss.HKSJ_TRUNCATED_MAX_K
        why = None if validated else (f"HKSJ validated for up to {ss.HKSJ_TRUNCATED_MAX_K} studies "
                                      "(truncated variance factor above 4)")
    elif method == "fixed":
        validated = assume_homogeneous
        why = None if validated else "the fixed-effect interval is valid only if the studies share one effect (declare assume_homogeneous in advance)"
    else:
        validated, why = False, "DerSimonian-Laird under-covered with heterogeneity"
    notes = [f"{k} estimates; Q = {het['Q']:.3g} (p = {het['p']:.3g}), I² = {het['I2']:.0%}. With few studies, "
             "heterogeneity tests have little power: absence of evidence is not homogeneity."]
    if truncated:
        notes.append(f"More than {HKSJ_VALIDATED_MAX_K} estimates: Hartung-Knapp variance factor truncated at 1 "
                     f"(Round 48, {ss.AUDIT}; plain HKSJ under-covered at 8 with heterogeneity in Round 38).")
    if why:
        notes.append("EXPLORATORY: "+why+f" ({AUDIT}).")
    return dict(pooled=out, heterogeneity=het, k=k, validated=validated,
                studies=[dict(label=(labels[i] if labels else str(i)), estimate=float(theta[i]), se=float(se[i])) for i in range(k)],
                notes=notes, audit=AUDIT)


def equivalence(est1: float, se1: float, est2: float, se2: float, margin: float, alpha: float = 0.05) -> Dict[str, Any]:
    """TOST: are two independent estimates within +-margin of each other? (validated)"""
    if not margin > 0:
        raise ValueError("margin must be positive and set before seeing the estimates")
    out = ev.tost(est1, se1, est2, se2, margin, alpha)
    out.update(validated=True, audit=AUDIT)
    return out


def power(se: float, effect: Optional[float] = None, target_power: float = 0.80, alpha: float = 0.10) -> Dict[str, Any]:
    """Power of a two-sided z test for ``effect`` given its SE, or the minimum detectable effect."""
    if not se > 0:
        raise ValueError("se must be positive")
    out: Dict[str, Any] = dict(se=se, alpha=alpha, validated=True, audit=AUDIT)
    if effect is not None:
        out["power"] = ev.power_z(effect, se, alpha)
    out["minimum_detectable_effect"] = ev.mde_z(se, target_power, alpha)
    out["target_power"] = target_power
    return out
