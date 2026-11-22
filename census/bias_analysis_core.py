# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 86 frozen core: quantitative bias analysis (backlog N63; Foundations of Epidemiology chapters 6-7).

E1 E-values (VanderWeele and Ding 2017): for a risk or rate ratio RR >= 1, E = RR + sqrt(RR (RR - 1)); for RR < 1
use 1 / RR. The E-value of the confidence limit nearest the null is computed the same way, and is 1 when the
interval includes 1. Odds ratios: with outcome prevalence above 10% the ratio is first converted with
RR ~ sqrt(OR) (VanderWeele 2017); otherwise OR ~ RR. Standardized mean differences d: RR ~ exp(0.91 d).

M1 misclassification of a 2 x 2 table (Lash, Fox and MacLehose 2009, 2021):
- outcome misclassification: within exposure group g with n_g persons and a*_g observed cases, the corrected cases
  are A_g = (a*_g - (1 - Sp_g) n_g) / (Se_g + Sp_g - 1); nondifferential when Se, Sp are equal across groups;
- exposure misclassification: within outcome group (cases, non-cases) with m persons and e* observed exposed,
  E = (e* - (1 - Sp) m) / (Se + Sp - 1).
Simple correction: fixed Se, Sp. Probabilistic analysis: Se, Sp drawn from beta priors (mean, sd); draws giving
impossible (non-positive or over-full) corrected cells are discarded and their share reported; each kept draw adds
conventional random error, log(theta) - z * se(theta_corrected) with z ~ N(0, 1); the 90% simulation interval is the
5th and 95th percentiles. Measures: risk ratio and odds ratio.
"""
import numpy as np
from scipy import stats


def e_value_rr(rr):
    rr = np.asarray(rr, float)
    r = np.where(rr < 1, 1/rr, rr)
    return r+np.sqrt(r*(r-1))


def e_value(estimate, lower=None, upper=None, measure="rr", prevalence=None):
    """E1: E-values of the estimate and of the confidence limit nearest the null."""
    conv = lambda x: x  # noqa: E731
    note = None
    if measure == "or":
        if prevalence is None or prevalence > .10:
            conv = np.sqrt
            note = "odds ratio converted with RR ~ sqrt(OR) (outcome prevalence above 10% or not given)"
        else:
            note = "rare outcome: OR ~ RR"
    elif measure == "smd":
        conv = lambda d: np.exp(.91*np.asarray(d, float))  # noqa: E731
        note = "standardized mean difference converted with RR ~ exp(0.91 d)"
    elif measure not in ("rr", "irr", "pr", "hr"):
        raise ValueError("measure must be rr, irr, pr, hr, or or smd")
    est = float(conv(estimate))
    out = dict(e_value=float(e_value_rr(est)), estimate_rr_scale=est, note=note)
    if lower is not None and upper is not None:
        lo, hi = float(conv(lower)), float(conv(upper))
        if lo <= 1 <= hi:
            out["e_value_limit"] = 1.0
        else:
            out["e_value_limit"] = float(e_value_rr(lo if est > 1 else hi))
    return out


def _correct(obs, total, se, sp):
    with np.errstate(divide="ignore", invalid="ignore"):
        return (obs-(1-sp)*total)/(se+sp-1)


def corrected_table(a, b, c, d, se, sp, kind="outcome"):
    """Simple correction. a, b: exposed cases, non-cases; c, d: unexposed cases, non-cases.
    ``kind`` "outcome": se/sp are (exposed, unexposed) pairs or scalars for case classification;
    "exposure": (cases, non-cases) pairs or scalars for exposure classification. Returns corrected (A, B, C, D)."""
    se = np.broadcast_to(np.asarray(se, float), (2,)+np.shape(np.asarray(se, float))[1:]) if np.ndim(se) else np.array([se, se], float)
    sp = np.broadcast_to(np.asarray(sp, float), (2,)+np.shape(np.asarray(sp, float))[1:]) if np.ndim(sp) else np.array([sp, sp], float)
    a, b, c, d = (np.asarray(x, float) for x in (a, b, c, d))
    if kind == "outcome":
        A = _correct(a, a+b, se[0], sp[0]); C = _correct(c, c+d, se[1], sp[1])
        return A, (a+b)-A, C, (c+d)-C
    if kind == "exposure":
        A = _correct(a, a+c, se[0], sp[0]); B = _correct(b, b+d, se[1], sp[1])
        return A, B, (a+c)-A, (b+d)-B
    raise ValueError("kind must be outcome or exposure")


def _measures(A, B, C, D):
    with np.errstate(divide="ignore", invalid="ignore"):
        rr = (A/(A+B))/(C/(C+D)); orr = A*D/(B*C)
        se_lrr = np.sqrt(1/A-1/(A+B)+1/C-1/(C+D)); se_lor = np.sqrt(1/A+1/B+1/C+1/D)
    return dict(rr=(rr, se_lrr), **{"or": (orr, se_lor)})


def beta_params(mean, sd):
    v = sd**2
    k = mean*(1-mean)/v-1
    return mean*k, (1-mean)*k


def probabilistic(a, b, c, d, se_prior, sp_prior, kind="outcome", draws=5000, level=.90, rng=None,
                  differential=False):
    """Probabilistic bias analysis. Priors are (mean, sd) beta priors; with ``differential`` the priors are pairs
    ((mean, sd) for group 1, (mean, sd) for group 2), drawn independently; otherwise one draw serves both groups.
    Returns per measure the median and simulation interval (systematic + random error), the systematic-only
    interval, and the share of discarded draws."""
    rng = rng if rng is not None else np.random.default_rng()

    def draw(prior):
        if differential:
            return np.stack([rng.beta(*beta_params(*p), draws) for p in prior])
        x = rng.beta(*beta_params(*prior), draws)
        return np.stack([x, x])
    se = draw(se_prior); sp = draw(sp_prior)
    A, B, C, D = corrected_table(a, b, c, d, se, sp, kind)
    ok = (A > 0) & (B > 0) & (C > 0) & (D > 0)
    q = [(1-level)/2, (1+level)/2]
    out = dict(discarded=float(1-ok.mean()))
    m = _measures(A[ok], B[ok], C[ok], D[ok])
    z = rng.standard_normal(int(ok.sum()))
    for name, (est, se_l) in m.items():
        sysq = np.quantile(np.log(est), [.5]+q)
        tot = np.quantile(np.log(est)-z*se_l, q)
        out[name] = dict(median=float(np.exp(sysq[0])), systematic_lower=float(np.exp(sysq[1])),
                         systematic_upper=float(np.exp(sysq[2])), lower=float(np.exp(tot[0])), upper=float(np.exp(tot[1])))
    return out


def both_directions(fit_with, fit_without):
    """B1: report the estimate with and without a covariable of uncertain causal direction (no new inference)."""
    return dict(with_covariable=fit_with, without_covariable=fit_without,
                difference=None if fit_with is None or fit_without is None else fit_with-fit_without)
