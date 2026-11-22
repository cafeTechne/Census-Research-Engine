# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 83 frozen core: stratified analysis, Mantel-Haenszel pooling and additive interaction (backlog N60).

Per stratum k a 2 x 2 table: a = exposed cases, b = exposed non-cases, c = unexposed cases, d = unexposed
non-cases (n1 = a + b, n0 = c + d, N = n1 + n0, M1 = a + c); for person-time data a, c are cases and t1, t0
person-time. Arrays may carry leading batch axes; strata are the last axis.

MH1 (counts; Greenland and Robins 1985; Robins, Breslow and Greenland 1986):
- RR_MH = sum(a n0/N) / sum(c n1/N); var log RR = sum((n1 n0 M1 - a c N)/N^2) / (R S).
- OR_MH = sum(a d/N) / sum(b c/N); RBG variance of log OR.
- RD_MH = sum((a n0 - c n1)/N) / sum(n1 n0/N); var = sum((a b n0^3 + c d n1^3)/(n1 n0 N^2)) / (sum n1 n0/N)^2.
- IRR_MH = sum(a t0/T) / sum(c t1/T); var log = sum(M1 t1 t0/T^2) / (R S).
Normal intervals (log scale for ratios).
MH2 (PUMS): the same point estimators on weighted cell totals; SE from the 80 SDR replicate weights,
var = 4/80 sum(theta_r - theta)^2 on the analysis scale.
H1 homogeneity: counts - Breslow-Day statistic with Tarone's correction for the OR, Woolf-type
sum w_k (log RR_k - log RR_MH)^2 (w = 1 / var log RR_k, 0.5 added to every cell of a stratum with a zero cell) for
the RR; chi-square with K - 1 df. PUMS - Wald test that the stratum log measures are equal, using their SDR
covariance; chi-square with K - 1 df.
A1 additive interaction (two binary factors; cells 00, 10, 01, 11 with risks p): RERI = RR11 - RR10 - RR01 + 1,
AP = RERI / RR11, S = (RR11 - 1) / (RR10 + RR01 - 2). Delta method on the log risks (counts: var log p =
(1 - p)/(n p); PUMS: SDR covariance). A1b: counts - parametric binomial bootstrap percentile interval for RERI.
"""
import numpy as np
from scipy import stats

REP = 4/80


def _z(level):
    return stats.norm.ppf(.5+level/2)


def mh_pooled(a, b, c, d, level=.90):
    """MH1: pooled RR, OR and RD with Greenland-Robins / RBG variances. Returns {measure: dict(est, se, lower,
    upper)}; se on the log scale for RR/OR."""
    a, b, c, d = (np.asarray(x, float) for x in (a, b, c, d))
    n1, n0 = a+b, c+d; N = n1+n0; M1 = a+c
    z = _z(level)
    with np.errstate(divide="ignore", invalid="ignore"):
        R = (a*n0/N).sum(-1); S = (c*n1/N).sum(-1)
        rr = R/S
        v_rr = ((n1*n0*M1-a*c*N)/N**2).sum(-1)/(R*S)
        P = (a+d)/N; Q = (b+c)/N; Ro = a*d/N; So = b*c/N
        Rs, Ss = Ro.sum(-1), So.sum(-1)
        orr = Rs/Ss
        v_or = (P*Ro).sum(-1)/(2*Rs**2)+(P*So+Q*Ro).sum(-1)/(2*Rs*Ss)+(Q*So).sum(-1)/(2*Ss**2)
        W = (n1*n0/N).sum(-1)
        rd = ((a*n0-c*n1)/N).sum(-1)/W
        v_rd = ((a*b*n0**3+c*d*n1**3)/(n1*n0*N**2)).sum(-1)/W**2
    out = {}
    for name, est, v, log in (("rr", rr, v_rr, True), ("or", orr, v_or, True), ("rd", rd, v_rd, False)):
        se = np.sqrt(v)
        if log:
            lo, hi = est*np.exp(-z*se), est*np.exp(z*se)
        else:
            lo, hi = est-z*se, est+z*se
        out[name] = dict(estimate=est, se=se, lower=lo, upper=hi)
    return out


def mh_rate_ratio(a, t1, c, t0, level=.90):
    """MH1 for person-time: pooled incidence rate ratio."""
    a, t1, c, t0 = (np.asarray(x, float) for x in (a, t1, c, t0))
    T = t1+t0; M1 = a+c
    with np.errstate(divide="ignore", invalid="ignore"):
        R = (a*t0/T).sum(-1); S = (c*t1/T).sum(-1)
        irr = R/S; se = np.sqrt((M1*t1*t0/T**2).sum(-1)/(R*S))
    z = _z(level)
    return dict(estimate=irr, se=se, lower=irr*np.exp(-z*se), upper=irr*np.exp(z*se))


def crude(a, b, c, d):
    """Crude (collapsed) RR, OR and RD."""
    A, B, C, D = (np.asarray(x, float).sum(-1) for x in (a, b, c, d))
    with np.errstate(divide="ignore", invalid="ignore"):
        return dict(rr=(A/(A+B))/(C/(C+D)), **{"or": A*D/(B*C)}, rd=A/(A+B)-C/(C+D))


def stratum_measures(a, b, c, d):
    """Stratum-specific RR, OR and RD (no continuity correction)."""
    a, b, c, d = (np.asarray(x, float) for x in (a, b, c, d))
    with np.errstate(divide="ignore", invalid="ignore"):
        return dict(rr=(a/(a+b))/(c/(c+d)), **{"or": a*d/(b*c)}, rd=a/(a+b)-c/(c+d))


def breslow_day_tarone(a, b, c, d, or_mh=None):
    """H1 for the OR: Breslow-Day statistic with Tarone's correction; returns (statistic, p, df)."""
    a, b, c, d = (np.asarray(x, float) for x in (a, b, c, d))
    if or_mh is None:
        or_mh = mh_pooled(a, b, c, d)["or"]["estimate"]
    psi = np.asarray(or_mh)[..., None]
    n1, n0, m1 = a+b, c+d, a+c
    # E solves (E (n0 - m1 + E)) / ((n1 - E)(m1 - E)) = psi: quadratic in E
    A = psi-1
    B = -(psi*(n1+m1)+(n0-m1))
    C = psi*n1*m1
    with np.errstate(divide="ignore", invalid="ignore"):
        disc = np.sqrt(np.maximum(B**2-4*A*C, 0))
        r1 = np.where(np.abs(A) < 1e-12, -C/B, (-B-disc)/(2*A))
        r2 = np.where(np.abs(A) < 1e-12, -C/B, (-B+disc)/(2*A))
        lo, hi = np.maximum(0, m1-n0), np.minimum(n1, m1)
        E = np.where((r1 >= lo-1e-9) & (r1 <= hi+1e-9), r1, r2)
        V = 1/(1/E+1/(n1-E)+1/(m1-E)+1/(n0-m1+E))
        V = np.where(np.isfinite(V) & (V > 0), V, np.nan)
        bd = np.nansum((a-E)**2/V, axis=-1)
        tarone = np.nansum(a-E, axis=-1)**2/np.nansum(V, axis=-1)
    stat = bd-tarone
    df = np.sum(np.isfinite(V), axis=-1)-1
    return stat, stats.chi2.sf(stat, np.maximum(df, 1)), df


def woolf_rr(a, b, c, d, rr_mh=None):
    """H1 for the RR: sum w_k (log RR_k - log RR_MH)^2, 0.5 added to every cell of a stratum with a zero cell."""
    a, b, c, d = (np.asarray(x, float) for x in (a, b, c, d))
    if rr_mh is None:
        rr_mh = mh_pooled(a, b, c, d)["rr"]["estimate"]
    zero = (np.minimum(np.minimum(a, b), np.minimum(c, d)) == 0)
    aa, bb, cc, dd = (x+.5*zero for x in (a, b, c, d))
    lrr = np.log((aa/(aa+bb))/(cc/(cc+dd)))
    v = 1/aa-1/(aa+bb)+1/cc-1/(cc+dd)
    stat = (((lrr-np.log(np.asarray(rr_mh))[..., None])**2)/v).sum(-1)
    df = a.shape[-1]-1
    return stat, stats.chi2.sf(stat, df), df


def weighted_cells(y, e, s, W, strata):
    """MH2 inputs: weighted cell totals (columns of W: full sample then replicates) per stratum.
    y, e: 0/1 arrays; s: stratum codes; strata: ordered codes. Returns a, b, c, d with shape (R, K)."""
    out = []
    for cond in ((e == 1) & (y == 1), (e == 1) & (y == 0), (e == 0) & (y == 1), (e == 0) & (y == 0)):
        out.append(np.stack([W[cond & (s == k)].sum(axis=0) for k in strata], axis=-1))
    return out


def mh_replicate(y, e, s, W, strata, level=.90):
    """MH2: MH point estimates on weighted totals; SDR SEs; plus stratum measures and the replicate homogeneity
    Wald tests (log RR, log OR, RD)."""
    a, b, c, d = weighted_cells(y, e, s, W, strata)
    pooled = mh_pooled(a, b, c, d)
    z = _z(level)
    out = {}
    for m, log in (("rr", True), ("or", True), ("rd", False)):
        est = pooled[m]["estimate"]
        t = np.log(est) if log else est
        se = float(np.sqrt(REP*((t[1:]-t[0])**2).sum()))
        e0 = float(est[0])
        lo, hi = ((e0*np.exp(-z*se), e0*np.exp(z*se)) if log else (e0-z*se, e0+z*se))
        out[m] = dict(estimate=e0, se=se, lower=float(lo), upper=float(hi))
    sm = stratum_measures(a, b, c, d)
    hom = {}
    for m, log in (("rr", True), ("or", True), ("rd", False)):
        t = np.log(sm[m]) if log else sm[m]  # (R, K)
        K = t.shape[1]
        C = np.hstack([np.eye(K-1), -np.ones((K-1, 1))])  # differences from the last stratum
        dv = t@C.T
        dev = dv[1:]-dv[0]
        V = REP*dev.T@dev
        try:
            stat = float(dv[0]@np.linalg.solve(V, dv[0]))
        except np.linalg.LinAlgError:
            stat = np.nan
        hom[m] = dict(statistic=stat, df=K-1, p=float(stats.chi2.sf(stat, K-1)) if np.isfinite(stat) else np.nan)
    return out, hom, {k: v[0] for k, v in sm.items()}, {k: v[0] for k, v in crude(a, b, c, d).items()}


def reri(p, var_logp=None, level=.90, reps=None):
    """A1: RERI, AP and S from cell risks p = (p00, p10, p01, p11) (last axis). Delta-method SE for RERI from
    independent var log p (counts) or from replicate risks ``reps`` (R, 4) (PUMS, SDR)."""
    p = np.asarray(p, float)
    rr10, rr01, rr11 = p[..., 1]/p[..., 0], p[..., 2]/p[..., 0], p[..., 3]/p[..., 0]
    r = rr11-rr10-rr01+1
    with np.errstate(divide="ignore", invalid="ignore"):
        ap = r/rr11; s = (rr11-1)/(rr10+rr01-2)
    z = _z(level)
    if reps is not None:
        rp = np.asarray(reps, float)
        rr = rp[:, 3]/rp[:, 0]-rp[:, 1]/rp[:, 0]-rp[:, 2]/rp[:, 0]+1
        se = np.sqrt(REP*((rr-r)**2).sum())
    else:
        g = np.stack([-rr11+rr10+rr01, -rr10, -rr01, rr11], axis=-1)  # d RERI / d log p_ij
        se = np.sqrt((g**2*np.asarray(var_logp, float)).sum(-1))
    return dict(reri=r, se=se, lower=r-z*se, upper=r+z*se, ap=ap, s=s)


def reri_counts(cases, n, level=.90, B=999, rng=None):
    """A1 (delta) and A1b (parametric binomial bootstrap percentile) for counts: cases, n shape (..., 4)."""
    cases, n = np.asarray(cases, float), np.asarray(n, float)
    p = cases/n
    with np.errstate(divide="ignore", invalid="ignore"):
        v = (1-p)/(n*p)
    res = reri(p, v, level)
    rng = rng if rng is not None else np.random.default_rng()
    pb = rng.binomial(np.broadcast_to(n[..., None, :], n.shape[:-1]+(B, 4)).astype(int),
                      np.broadcast_to(p[..., None, :], p.shape[:-1]+(B, 4)))/n[..., None, :]
    with np.errstate(divide="ignore", invalid="ignore"):
        rb = pb[..., 3]/pb[..., 0]-pb[..., 1]/pb[..., 0]-pb[..., 2]/pb[..., 0]+1
    q = [(1-level)/2, (1+level)/2]
    lo, hi = np.nanquantile(rb, q, axis=-1)
    res.update(boot_lower=lo, boot_upper=hi)
    return res


def classify(crude_est, adjusted, strata_est, heterogeneous, change=.10):
    """Book Table 8-5 (descriptive, not a test): 'effect_modifier' if stratum measures are heterogeneous (H1) and the
    crude lies between them; 'confounder' if not heterogeneous and |adjusted/crude - 1| > change (ratios) or the
    relative change exceeds ``change`` (differences); otherwise 'neither'."""
    lo, hi = np.nanmin(strata_est), np.nanmax(strata_est)
    between = lo <= crude_est <= hi
    if heterogeneous and between:
        return "effect_modifier"
    rel = abs(adjusted/crude_est-1) if crude_est not in (0,) else np.inf
    if not heterogeneous and rel > change:
        return "confounder"
    return "neither"
