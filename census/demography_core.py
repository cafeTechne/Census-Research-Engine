# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 101 frozen core: demographic estimation tools (backlog N78; Moultrie et al., *Tools for Demographic
Estimation*, IUSSP 2013, chapters 1 and 31-35; Shryock and Siegel; Chiang 1984; Arriaga 1984).

Q1 age-data quality (counts by single year of age):
- Whipple's index: 500 sum_{a in 25, 30, ..., 60} P_a / sum_{a=23}^{62} P_a (100 = no heaping on 0 and 5; 500 = all).
- Myers' blended index: S1(d) = sum_{k=0}^{6} P_{10+d+10k}, S2(d) = sum_{k=0}^{6} P_{20+d+10k}; blended
  B(d) = (d+1) S1(d) + (9-d) S2(d); index = 0.5 sum_d |100 B(d)/sum B - 10| (0 = none; 90 = all on one digit).
- UN age-sex accuracy index from 5-year groups 0-4 ... 70-74: sex ratio score = mean |SR_x - SR_{x+5}|; age ratio
  score (each sex) = mean over 5-9 ... 65-69 of |100 * 2 P_x / (P_{x-5} + P_{x+5}) - 100|; index = 3 SRS + ARS_m +
  ARS_f.
L1 abridged life table on age bands (start ages; last band open): m_x = D_x / PY_x; a_0 and a_1 (band 1-4) from
Coale-Demeny (both sexes averaged): m_0 >= .107: a_0 = .34, a_1 = 1.3565; otherwise a_0 = .049 + 2.742 m_0,
a_1 = 1.5865 - 2.167 m_0; other closed bands a = n/2; open band L = l/m. q = n m / (1 + (n - a) m).
Chiang II variance (Poisson deaths): var(q_x) = q_x^2 (1 - q_x) / D_x; var(e_i) = sum_{x>=i, closed}
l_x^2 [(1 - a_x/n_x) n_x + e_{x+n}]^2 var(q_x) / l_i^2 + (l_w / l_i)^2 var(m_w) / m_w^4 (open band w,
var(m) = D / PY^2).
L2 Arriaga decomposition of e_0(2) - e_0(1) into band contributions (direct + indirect; open band
l_x^1/l_0 (T_x^2/l_x^2 - T_x^1/l_x^1)); by cause: band contribution x (m2_xc - m1_xc) / (m2_x - m1_x).
M1 census-survival net migration: net_x = P2_{x+t} - S_x P1_x with S_x = L_{x+t}/L_x for the census interval t.
"""
from typing import Dict, Optional, Sequence

import numpy as np
from scipy import stats

Z90 = stats.norm.ppf(.95)


def whipple(pop_by_age: Dict[int, float]) -> float:
    num = sum(pop_by_age.get(a, 0) for a in range(25, 61, 5))
    den = sum(pop_by_age.get(a, 0) for a in range(23, 63))
    return float(500*num/den)


def myers(pop_by_age: Dict[int, float]) -> float:
    B = []
    for d in range(10):
        s1 = sum(pop_by_age.get(10+d+10*k, 0) for k in range(7))
        s2 = sum(pop_by_age.get(20+d+10*k, 0) for k in range(7))
        B.append((d+1)*s1+(9-d)*s2)
    B = np.array(B, float)
    return float(.5*np.sum(np.abs(100*B/B.sum()-10)))


def un_accuracy(males5: Sequence[float], females5: Sequence[float]) -> Dict[str, float]:
    """5-year groups 0-4 ... 70-74 (15 values each)."""
    m = np.asarray(males5, float); f = np.asarray(females5, float)
    sr = 100*m/f
    srs = float(np.mean(np.abs(np.diff(sr))))
    ars = lambda p: float(np.mean(np.abs(100*2*p[1:-1]/(p[:-2]+p[2:])-100)))  # noqa: E731
    am, af = ars(m), ars(f)
    return dict(sex_ratio_score=srs, age_ratio_male=am, age_ratio_female=af, index=3*srs+am+af)


def life_table(starts: Sequence[float], deaths, person_years, level: float = .90) -> Dict[str, np.ndarray]:
    x = np.asarray(starts, float); D = np.asarray(deaths, float); PY = np.asarray(person_years, float)
    k = len(x); n = np.r_[np.diff(x), np.inf]
    m = D/PY
    a = n/2
    if x[0] == 0 and n[0] == 1:
        m0 = m[0]
        a[0] = .34 if m0 >= .107 else .049+2.742*m0
        if k > 1 and x[1] == 1 and n[1] == 4:
            a[1] = 1.3565 if m0 >= .107 else 1.5865-2.167*m0
    q = np.ones(k); q[:-1] = np.clip(n[:-1]*m[:-1]/(1+(n[:-1]-a[:-1])*m[:-1]), 0, 1)
    l = np.ones(k); l[1:] = np.cumprod(1-q[:-1])
    d = l*q
    L = np.empty(k); L[:-1] = n[:-1]*np.r_[l[1:]]+a[:-1]*d[:-1]; L[-1] = l[-1]/m[-1]
    T = np.cumsum(L[::-1])[::-1]; e = T/l
    vq = np.where(D[:-1] > 0, q[:-1]**2*(1-q[:-1])/np.maximum(D[:-1], 1e-12), 0.0)
    ve = np.zeros(k)
    open_term = l[-1]**2*(D[-1]/PY[-1]**2)/m[-1]**4
    for i in range(k):
        s = 0.0
        for j in range(i, k-1):
            s += l[j]**2*((1-a[j]/n[j])*n[j]+e[j+1])**2*vq[j]
        ve[i] = (s+open_term)/l[i]**2
    se = np.sqrt(ve)
    return dict(x=x, n=n, m=m, a=a, q=q, l=l, d=d, L=L, T=T, e=e, se_e=se, lower=e-Z90*se, upper=e+Z90*se)


def arriaga(lt1: Dict[str, np.ndarray], lt2: Dict[str, np.ndarray]) -> np.ndarray:
    """Band contributions to e0(2) - e0(1) (radix l0 = 1)."""
    l1, l2, L1, L2, T2, T1 = lt1["l"], lt2["l"], lt1["L"], lt2["L"], lt2["T"], lt1["T"]
    k = len(l1); out = np.zeros(k)
    for x in range(k-1):
        out[x] = l1[x]*(L2[x]/l2[x]-L1[x]/l1[x]) + T2[x+1]*(l1[x]/l2[x]-l1[x+1]/l2[x+1])
    out[-1] = l1[-1]*(T2[-1]/l2[-1]-T1[-1]/l1[-1])
    return out


def arriaga_by_cause(contrib: np.ndarray, m1: np.ndarray, m2: np.ndarray, m1c: np.ndarray, m2c: np.ndarray) -> np.ndarray:
    """contrib (bands), m1/m2 (bands), m1c/m2c (bands x causes) -> (bands x causes)."""
    dm = (m2-m1)[:, None]
    with np.errstate(divide="ignore", invalid="ignore"):
        share = np.where(np.abs(dm) > 0, (m2c-m1c)/dm, 0.0)
    return contrib[:, None]*share


def census_survival_net_migration(p1: Sequence[float], p2: Sequence[float], L: Sequence[float]) -> np.ndarray:
    """p1 at census 1 and p2 at census 2 by age groups of width equal to the interval; L the matching life-table nLx
    (same groups). net for cohort aged x at census 1 = p2[x+1] - (L[x+1]/L[x]) p1[x]."""
    p1 = np.asarray(p1, float); p2 = np.asarray(p2, float); L = np.asarray(L, float)
    return p2[1:]-(L[1:]/L[:-1])*p1[:-1]
