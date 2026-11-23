# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 101: demographic estimation tools (backlog N78; Moultrie et al., *Tools for Demographic Estimation*, IUSSP
2013): age-data quality indices, abridged life tables with Chiang II standard errors, the Arriaga decomposition of a
life-expectancy difference by age and cause, and census-survival net migration.

Validation (``docs/audits/demography_validation.md``; criterion tag ``criterion-r101``): life-table e0 and e65
intervals covered .895-.910 with 50,000 to 5 million person-years (validated). The indices, the decomposition and
census-survival migration are exact computations (checked in tests).
"""
import io
from typing import Any, Dict, Mapping, Optional, Sequence

import numpy as np
import pandas as pd

from . import demography_core as dc

AUDIT = "docs/audits/demography_validation.md"
VALIDATED = {"life_table": True}
WONDER_BANDS = [("<1", 0), ("1-4", 1), ("5-14", 5), ("15-24", 15), ("25-34", 25), ("35-44", 35), ("45-54", 45),
                ("55-64", 55), ("65-74", 65), ("75-84", 75), ("85+", 85)]


def age_quality(pop_by_age: Mapping[int, float], males5: Optional[Sequence[float]] = None,
                females5: Optional[Sequence[float]] = None) -> Dict[str, Any]:
    out = dict(whipple=dc.whipple(dict(pop_by_age)), myers=dc.myers(dict(pop_by_age)))
    if males5 is not None and females5 is not None:
        out["un_age_sex_accuracy"] = dc.un_accuracy(males5, females5)
    out["notes"] = ["Whipple: 100 = no preference for ages ending in 0 or 5 (UN: <105 highly accurate, >175 very "
                    "rough). Myers: 0 = no digit preference (range 0-90). UN index < 20 accurate, > 40 inaccurate."]
    return out


def _five_year(pop_by_age: Mapping[int, float]):
    return [sum(pop_by_age.get(a+i, 0) for i in range(5)) for a in range(0, 75, 5)]


def age_quality_pums(df: pd.DataFrame, age: str = "AGEP", sex: str = "SEX", weight: str = "PWGTP") -> Dict[str, Any]:
    """Indices from PUMS person records with SDR replicate standard errors (columns <weight>1..80)."""
    reps = [f"{weight}{i}" for i in range(1, 81)]

    def compute(w):
        s = pd.Series(w, index=df.index).groupby(df[age].astype(int)).sum().to_dict()
        m = pd.Series(np.where(df[sex].astype(int) == 1, w, 0), index=df.index).groupby(df[age].astype(int)).sum().to_dict()
        f = pd.Series(np.where(df[sex].astype(int) == 2, w, 0), index=df.index).groupby(df[age].astype(int)).sum().to_dict()
        un = dc.un_accuracy(_five_year(m), _five_year(f))["index"]
        return np.array([dc.whipple(s), dc.myers(s), un])
    full = compute(df[weight].to_numpy(float))
    R = np.array([compute(df[c].to_numpy(float)) for c in reps]) if all(c in df for c in reps) else None
    se = np.sqrt(4/80*np.sum((R-full)**2, 0)) if R is not None else np.full(3, np.nan)
    return dict(whipple=float(full[0]), whipple_se=float(se[0]), myers=float(full[1]), myers_se=float(se[1]),
                un_age_sex_accuracy=float(full[2]), un_se=float(se[2]),
                notes=["PUMS ages are top-coded and partly allocated; heaping in survey ages is usually small. Replicate "
                       "SEs (SDR)."])


def _wonder_bands(path: str) -> pd.DataFrame:
    """Deaths and person-years by WONDER band (sexes summed) from a national age x sex export; suppressed cells
    (1-9 deaths) are returned as 0 with a count of suppressed cells."""
    from .surveillance import _age_label
    from .vital_records import _split_footer
    text = open(path, "rb").read().decode("utf-8-sig")
    body, _ = _split_footer(text)
    src = pd.read_csv(io.StringIO("\n".join(body)), sep="\t", dtype=str, keep_default_na=False)
    if "Notes" in src:
        src = src[src.Notes.str.strip() != "Total"]
    age = next(c for c in ("Ten-Year Age Groups", "Ten-Year Age Group") if c in src)
    src = src.assign(a=src[age].map(_age_label))
    src = src[src.a.isin([b for b, _ in WONDER_BANDS])]
    num = lambda s: pd.to_numeric(s.str.replace(",", ""), errors="coerce")  # noqa: E731
    d = num(src.Deaths); supp = d.isna() | ((d >= 1) & (d <= 9))
    g = src.assign(d=d.where(~supp, 0), n=num(src.Population), k=supp.astype(int)).groupby("a")[["d", "n", "k"]].sum()
    g = g.reindex([b for b, _ in WONDER_BANDS])
    if g[["d", "n"]].isna().any().any():
        raise ValueError(f"{path}: the export lacks an age band")
    return g


def life_table_from_wonder(path: str, level: float = .90) -> Dict[str, Any]:
    g = _wonder_bands(path)
    if g.k.sum():
        raise ValueError("suppressed cells in an all-cause export: a life table needs every band")
    lt = dc.life_table([s for _, s in WONDER_BANDS], g.d.to_numpy(), g.n.to_numpy(), level)
    return dict(table=pd.DataFrame({"age": [b for b, _ in WONDER_BANDS], "m": lt["m"], "q": lt["q"], "l": lt["l"],
                                    "L": lt["L"], "e": lt["e"], "se_e": lt["se_e"], "lower": lt["lower"],
                                    "upper": lt["upper"]}),
                e0=float(lt["e"][0]), e0_lower=float(lt["lower"][0]), e0_upper=float(lt["upper"][0]),
                validated=VALIDATED["life_table"], raw=lt, bands=g, audit=AUDIT)


def arriaga_from_wonder(all1: str, all2: str, causes1: Mapping[str, str], causes2: Mapping[str, str]) -> Dict[str, Any]:
    """e0 change from period 1 to 2 decomposed by age band and by cause (listed causes plus 'other')."""
    a, b = life_table_from_wonder(all1), life_table_from_wonder(all2)
    contrib = dc.arriaga(a["raw"], b["raw"])
    names = list(causes1)
    if set(names) != set(causes2):
        raise ValueError("cause lists differ between periods")
    supp = 0
    m1c, m2c = [], []
    for nm in names:
        g1, g2 = _wonder_bands(causes1[nm]), _wonder_bands(causes2[nm])
        supp += int(g1.k.sum()+g2.k.sum())
        m1c.append(g1.d.to_numpy()/a["bands"].n.to_numpy()); m2c.append(g2.d.to_numpy()/b["bands"].n.to_numpy())
    m1c, m2c = np.array(m1c).T, np.array(m2c).T
    m1, m2 = a["raw"]["m"], b["raw"]["m"]
    other1, other2 = m1-m1c.sum(1), m2-m2c.sum(1)
    by = dc.arriaga_by_cause(contrib, m1, m2, np.column_stack([m1c, other1]), np.column_stack([m2c, other2]))
    table = pd.DataFrame(by, columns=names+["other"], index=[b_ for b_, _ in WONDER_BANDS])
    notes = [f"Arriaga (1984) decomposition; causes may overlap if the listed causes are not mutually exclusive "
             f"(then 'other' is not a remainder)."]
    if supp:
        notes.append(f"{supp} suppressed national cause-by-age cells (1-9 deaths) counted as 0 (each changes a band's "
                     "rate by under 10 deaths).")
    return dict(e0_1=a["e0"], e0_2=b["e0"], difference=float(b["e0"]-a["e0"]), by_age=pd.Series(contrib, index=table.index),
                by_age_cause=table, notes=notes, audit=AUDIT)


census_survival_net_migration = dc.census_survival_net_migration
