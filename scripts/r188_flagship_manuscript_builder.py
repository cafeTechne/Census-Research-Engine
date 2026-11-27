# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 188 (Track 2): Flagship Publishable Manuscript Builder.

Synthesizes all 11 pre-registered CDC WONDER (2018-2022) county mortality causes
across MI+OH (primary) and NY+PA (replication) alongside 4 ACS methodological pitfall
studies (SCPC vs HC3, KWW county rank widths, PUMA ecologic fallacy, BEA RPP spread)
into publication-grade PDF/SVG/PNG figures, LaTeX booktabs tables, manuscript.tex,
manuscript.md, references.bib, and a SHA-256 verified results bundle.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-r188")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from census.report_tables import results_bundle, verify_bundle

OUT_DIR = ROOT / "studies_output" / "r188_flagship_manuscript"
FIG_DIR = OUT_DIR / "figures"
TAB_DIR = OUT_DIR / "tables"
BUNDLE_DIR = OUT_DIR / "bundle"
DOCS_COPY = ROOT / "docs" / "studies" / "r188_flagship_manuscript.md"

CAUSE_LABELS = {
    "drug_overdose": "Drug Overdose",
    "firearm": "Firearm",
    "kidney_disease": "Kidney Disease",
    "unintentional_injury": "Unintentional Injury",
    "diabetes": "Diabetes",
    "clrd": "CLRD",
    "heart_disease": "Heart Disease",
    "liver_disease": "Liver Disease",
    "alcohol_induced": "Alcohol-Induced",
    "suicide": "Suicide",
    "stroke": "Stroke",
}


def _load_json(rel: str) -> Dict[str, Any]:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def collect_11_causes() -> List[Dict[str, Any]]:
    """Aggregate all 11 WONDER causes across MI+OH and NY+PA from verified summaries."""
    sources = [
        ("studies_output/r144_wonder_bym2_qba/summary.json", ["heart_disease", "drug_overdose"], False),
        ("studies_output/r156_layer_a_stroke/summary.json", ["stroke"], True),
        ("studies_output/r168_wonder_suicide_diabetes/summary.json", ["suicide", "diabetes"], False),
        ("studies_output/r173_wonder_clrd_liver/summary.json", ["clrd", "liver_disease"], False),
        ("studies_output/r178_wonder_kidney_firearm/summary.json", ["kidney_disease", "firearm"], False),
        ("studies_output/r183_wonder_alcohol_injury/summary.json", ["alcohol_induced", "unintentional_injury"], False),
    ]
    rows: List[Dict[str, Any]] = []
    for rel, causes, flat_region in sources:
        data = _load_json(rel)
        res = data["results"]
        for c in causes:
            mi = res["MI_OH"] if flat_region else res[f"MI_OH_{c}"]
            ny = res["NY_PA"] if flat_region else res[f"NY_PA_{c}"]
            rows.append({
                "cause": c,
                "label": CAUSE_LABELS[c],
                "mi_n": int(mi["n_counties"]),
                "mi_rr": float(mi["q4_vs_q1_poverty_rr"]),
                "mi_lo": float(mi["q4_vs_q1_rr_ci90"][0]),
                "mi_hi": float(mi["q4_vs_q1_rr_ci90"][1]),
                "mi_eval": float(mi.get("e_value_limit", mi.get("e_value_ci", 1.0))),
                "mi_phi": float(mi["bym2_phi"]),
                "mi_raw_iqr": float(mi["raw_smr_iqr"]),
                "mi_sm_iqr": float(mi["smoothed_rr_iqr"]),
                "mi_p80": int(mi["high_exceedance_counties_p80"]),
                "ny_n": int(ny["n_counties"]),
                "ny_rr": float(ny["q4_vs_q1_poverty_rr"]),
                "ny_lo": float(ny["q4_vs_q1_rr_ci90"][0]),
                "ny_hi": float(ny["q4_vs_q1_rr_ci90"][1]),
                "ny_eval": float(ny.get("e_value_limit", ny.get("e_value_ci", 1.0))),
                "ny_phi": float(ny["bym2_phi"]),
                "ny_raw_iqr": float(ny["raw_smr_iqr"]),
                "ny_sm_iqr": float(ny["smoothed_rr_iqr"]),
                "ny_p80": int(ny["high_exceedance_counties_p80"]),
            })
    rows.sort(key=lambda r: r["mi_rr"], reverse=True)
    return rows


def collect_pitfalls() -> Dict[str, Any]:
    r136 = _load_json("studies_output/r136_pums_ineq_ecologic/summary.json")
    r137 = _load_json("studies_output/r137_spatial_inference/summary.json")
    r139 = _load_json("studies_output/r139_county_ranking/summary.json")
    r141 = _load_json("studies_output/r141_deprivation_rpp/summary.json")
    return {
        "scpc": {
            "MI_NY_ratio": float(r137["MI_NY"]["ba_plus_slope"]["width_ratio_scpc_vs_hc3"]),
            "OH_PA_ratio": float(r137["OH_PA"]["ba_plus_slope"]["width_ratio_scpc_vs_hc3"]),
        },
        "kww": {
            st: {
                "n": int(d["n_counties"]),
                "indiv_width": float(d["median_individual_rank_width"]),
                "joint_width": float(d["median_joint_rank_width"]),
                "surely_top_decile": int(d["surely_top_decile_counties"]),
            }
            for st, d in r139["states"].items()
        },
        "ecologic": {
            "MI_within": float(r136["MI_26"]["ecologic_logit"]["within"]["estimate"]),
            "MI_between": float(r136["MI_26"]["ecologic_logit"]["between"]["estimate"]),
            "OH_within": float(r136["OH_39"]["ecologic_logit"]["within"]["estimate"]),
            "OH_between": float(r136["OH_39"]["ecologic_logit"]["between"]["estimate"]),
        },
        "rpp": {
            "nominal_spread": float(r141["state_nominal_pci_spread"]),
            "real_spread": float(r141["state_real_pci_spread"]),
            "pct_change": round(
                (float(r141["state_real_pci_spread"]) - float(r141["state_nominal_pci_spread"]))
                / float(r141["state_nominal_pci_spread"]) * 100.0,
                1,
            ),
        },
    }


def _save_fig(fig: plt.Figure, stem: str) -> List[str]:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for ext in ("pdf", "svg", "png"):
        p = FIG_DIR / f"{stem}.{ext}"
        fig.savefig(p, dpi=300, bbox_inches="tight")
        out.append(str(p))
    plt.close(fig)
    return out


def build_figures(causes: List[Dict[str, Any]], pitfalls: Dict[str, Any]) -> Dict[str, List[str]]:
    plt.rcParams.update({"font.size": 9.5, "axes.spines.top": False, "axes.spines.right": False})
    c_mi, c_ny = "#0072B2", "#D55E00"

    # Figure 1: Paired Forest Plot (11 causes, MI+OH vs NY+PA)
    fig, ax = plt.subplots(figsize=(8.6, 5.8))
    y = np.arange(len(causes))[::-1]
    off = 0.16
    ax.axvline(1.0, color="#666666", linestyle="--", linewidth=1.0, zorder=1)
    for yi, r in zip(y, causes):
        ax.errorbar(
            r["mi_rr"], yi + off,
            xerr=[[r["mi_rr"] - r["mi_lo"]], [r["mi_hi"] - r["mi_rr"]]],
            fmt="o", color=c_mi, capsize=3, markersize=5.5,
            label="MI+OH (Primary, n<=171)" if yi == y[0] else None,
        )
        ax.errorbar(
            r["ny_rr"], yi - off,
            xerr=[[r["ny_rr"] - r["ny_lo"]], [r["ny_hi"] - r["ny_rr"]]],
            fmt="s", color=c_ny, capsize=3, markersize=5.5,
            label="NY+PA (Replication, n<=129)" if yi == y[0] else None,
        )
        ax.text(
            max(r["mi_hi"], r["ny_hi"]) + 0.04, yi,
            f"E={r['mi_eval']:.2f} / {r['ny_eval']:.2f}",
            va="center", fontsize=7.8, color="#333333",
        )
    ax.set_yticks(y)
    ax.set_yticklabels([r["label"] for r in causes])
    ax.set_xlabel("Q4 vs. Q1 County Poverty Crude Rate Ratio (90% CI); E = E-value lower bound (MI+OH / NY+PA)")
    ax.set_title("11-Cause County Mortality Poverty Gradients: Primary (MI+OH) vs. Replication (NY+PA), 2018–2022")
    ax.set_xlim(0.65, 2.85)
    ax.legend(frameon=False, loc="lower right")
    f1 = _save_fig(fig, "fig1_mortality_poverty_forest")

    # Figure 2: BYM2 Shrinkage (Raw SMR IQR vs Smoothed RR IQR) + Spatial Mixing phi
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.4, 5.2), sharey=True)
    y = np.arange(len(causes))[::-1]
    for yi, r in zip(y, causes):
        ax1.plot([r["mi_sm_iqr"], r["mi_raw_iqr"]], [yi + 0.14, yi + 0.14], color=c_mi, lw=1.6)
        ax1.scatter(r["mi_raw_iqr"], yi + 0.14, color=c_mi, facecolors="white", s=34, zorder=3,
                    label="Raw SMR IQR (MI+OH)" if yi == y[0] else None)
        ax1.scatter(r["mi_sm_iqr"], yi + 0.14, color=c_mi, s=34, zorder=4,
                    label="BYM2 Smoothed IQR (MI+OH)" if yi == y[0] else None)
        ax1.plot([r["ny_sm_iqr"], r["ny_raw_iqr"]], [yi - 0.14, yi - 0.14], color=c_ny, lw=1.6)
        ax1.scatter(r["ny_raw_iqr"], yi - 0.14, color=c_ny, facecolors="white", marker="s", s=32, zorder=3,
                    label="Raw SMR IQR (NY+PA)" if yi == y[0] else None)
        ax1.scatter(r["ny_sm_iqr"], yi - 0.14, color=c_ny, marker="s", s=32, zorder=4,
                    label="BYM2 Smoothed IQR (NY+PA)" if yi == y[0] else None)

        ax2.barh(yi + 0.16, r["mi_phi"], height=0.28, color=c_mi, alpha=0.88,
                 label="MI+OH" if yi == y[0] else None)
        ax2.barh(yi - 0.16, r["ny_phi"], height=0.28, color=c_ny, alpha=0.88,
                 label="NY+PA" if yi == y[0] else None)
    ax1.set_yticks(y)
    ax1.set_yticklabels([r["label"] for r in causes])
    ax1.set_xlabel("Interquartile Range (IQR) of County Mortality Risk")
    ax1.set_title("(A) BYM2 (B3) Variance Shrinkage: Raw vs. Smoothed IQR")
    ax1.legend(frameon=False, fontsize=7.5, loc="lower right")
    ax2.set_xlim(0.0, 1.05)
    ax2.set_xlabel(r"BYM2 Spatial Mixing Parameter ($\phi$)")
    ax2.set_title(r"(B) Structured Spatial Share ($\phi$)")
    ax2.legend(frameon=False, fontsize=8.0, loc="lower right")
    fig.tight_layout()
    f2 = _save_fig(fig, "fig2_bym2_shrinkage_spatial")

    # Figure 3: 4-Panel Methodological Pitfalls Benchmark
    fig, axes = plt.subplots(2, 2, figsize=(9.6, 6.8))
    # Panel A: SCPC vs HC3
    ax = axes[0, 0]
    ax.bar(["MI+NY\n(n=145)", "OH+PA\n(n=155)"],
           [pitfalls["scpc"]["MI_NY_ratio"], pitfalls["scpc"]["OH_PA_ratio"]],
           color=[c_mi, c_ny], width=0.5)
    ax.axhline(1.0, color="#666666", linestyle="--", lw=1.0)
    for i, v in enumerate([pitfalls["scpc"]["MI_NY_ratio"], pitfalls["scpc"]["OH_PA_ratio"]]):
        ax.text(i, v + 0.04, f"{v:.2f}x", ha="center", fontweight="bold")
    ax.set_ylim(0, 1.8)
    ax.set_ylabel("90% CI Width Ratio (SCPC / HC3)")
    ax.set_title("(A) Spatial Dependence Widens CIs (R137)")

    # Panel B: KWW Rank Interval Widths
    ax = axes[0, 1]
    st_order = [("26", "MI"), ("36", "NY"), ("39", "OH"), ("42", "PA")]
    x = np.arange(len(st_order))
    indiv = [pitfalls["kww"][s]["indiv_width"] for s, _ in st_order]
    joint = [pitfalls["kww"][s]["joint_width"] for s, _ in st_order]
    ax.bar(x - 0.18, indiv, width=0.34, color=c_mi, label="Individual KWW")
    ax.bar(x + 0.18, joint, width=0.34, color=c_ny, label="Joint KWW")
    ax.set_xticks(x)
    ax.set_xticklabels([lbl for _, lbl in st_order])
    ax.set_ylabel("Median 90% Rank Interval Width")
    ax.set_title("(B) County Rank Uncertainty (2/300 Top-Decile, R139)")
    ax.legend(frameon=False, fontsize=8.0)

    # Panel C: PUMA Ecologic Fallacy
    ax = axes[1, 0]
    x = np.arange(2)
    within = [pitfalls["ecologic"]["MI_within"], pitfalls["ecologic"]["OH_within"]]
    between = [pitfalls["ecologic"]["MI_between"], pitfalls["ecologic"]["OH_between"]]
    ax.bar(x - 0.18, within, width=0.34, color=c_mi, label="Within-PUMA (Individual)")
    ax.bar(x + 0.18, between, width=0.34, color=c_ny, label="Between-PUMA (Ecologic)")
    for i, (w, b) in enumerate(zip(within, between)):
        ax.text(i - 0.18, w + 0.35, f"{w:.2f}", ha="center", fontsize=8.2)
        ax.text(i + 0.18, b + 0.35, f"{b:.2f}", ha="center", fontsize=8.2)
    ax.set_xticks(x)
    ax.set_xticklabels(["Michigan\n(68 PUMAs)", "Ohio\n(90 PUMAs)"])
    ax.set_ylabel("Log-Odds Slope (Poverty ~ BA+)")
    ax.set_ylim(0, 14.5)
    ax.set_title("(C) ~10x PUMA Ecologic Inflation (R136)")
    ax.legend(frameon=False, fontsize=8.0)

    # Panel D: BEA RPP Income Spread
    ax = axes[1, 1]
    vals = [pitfalls["rpp"]["nominal_spread"], pitfalls["rpp"]["real_spread"]]
    ax.bar(["Nominal PCI\nSpread", "BEA RPP Real\nPCI Spread"], vals, color=[c_ny, c_mi], width=0.5)
    for i, v in enumerate(vals):
        ax.text(i, v + 120, f"${v:,.0f}", ha="center", fontweight="bold")
    ax.set_ylim(0, 4600)
    ax.set_ylabel("4-State Inter-State Median Spread (USD)")
    ax.set_title(f"(D) BEA RPP Compression ({pitfalls['rpp']['pct_change']}%, R141)")
    fig.tight_layout()
    f3 = _save_fig(fig, "fig3_methodological_pitfalls")

    return {"fig1": f1, "fig2": f2, "fig3": f3}


def build_tables(causes: List[Dict[str, Any]], pitfalls: Dict[str, Any]) -> Dict[str, str]:
    TAB_DIR.mkdir(parents=True, exist_ok=True)

    # Table 1: 11-Cause Mortality Atlas (LaTeX booktabs + Markdown)
    t1_tex_lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{Eleven-Cause County Mortality Poverty Gradients (Q4/Q1 Crude RR, 90\% CI), E-Value Bounds, and BYM2 (B3) Spatial Smoothing Across MI+OH and NY+PA, 2018--2022.}",
        r"\label{tab:11cause_atlas}",
        r"\begin{tabular}{lrrrrrr}",
        r"\toprule",
        r"Cause of Death & MI+OH RR (90\% CI) & MI+OH $E_{\text{CI}}$ & MI+OH $\phi$ & NY+PA RR (90\% CI) & NY+PA $E_{\text{CI}}$ & NY+PA $\phi$ \\",
        r"\midrule",
    ]
    t1_md_lines = [
        "| Cause of Death | MI+OH RR (90% CI) | MI+OH E-val | MI+OH phi | NY+PA RR (90% CI) | NY+PA E-val | NY+PA phi |",
        "| --- | --- | ---: | ---: | --- | ---: | ---: |",
    ]
    for r in causes:
        mi_s = f"{r['mi_rr']:.2f} ({r['mi_lo']:.2f}--{r['mi_hi']:.2f})"
        ny_s = f"{r['ny_rr']:.2f} ({r['ny_lo']:.2f}--{r['ny_hi']:.2f})"
        t1_tex_lines.append(
            f"{r['label']} & {mi_s} & {r['mi_eval']:.2f} & {r['mi_phi']:.2f} & {ny_s} & {r['ny_eval']:.2f} & {r['ny_phi']:.2f} \\\\"
        )
        t1_md_lines.append(
            f"| {r['label']} | {mi_s.replace('--', '-')} | {r['mi_eval']:.2f} | {r['mi_phi']:.2f} | {ny_s.replace('--', '-')} | {r['ny_eval']:.2f} | {r['ny_phi']:.2f} |"
        )
    t1_tex_lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    t1_tex_path = TAB_DIR / "table1_11cause_atlas.tex"
    t1_md_path = TAB_DIR / "table1_11cause_atlas.md"
    t1_tex_path.write_text("\n".join(t1_tex_lines) + "\n", encoding="utf-8")
    t1_md_path.write_text("\n".join(t1_md_lines) + "\n", encoding="utf-8")

    # Table 2: Methodological Pitfalls Benchmark (LaTeX booktabs + Markdown)
    t2_rows = [
        ("Spatial autocorrelation (R137)", "HC3 robust SEs", "SCPC spatial CIs ($\\bar{\\rho}=0.05$)",
         f"CIs widen {pitfalls['scpc']['MI_NY_ratio']:.2f}x (MI+NY) and {pitfalls['scpc']['OH_PA_ratio']:.2f}x (OH+PA)"),
        ("County ranking (R139)", "Unadjusted point ranks", "KWW individual & joint rank sets",
         "Median joint width 45--64 ranks; only 2/300 certifiably top-decile"),
        ("Ecologic aggregation (R136)", "PUMA-level ecologic logit", "Within- vs. between-PUMA PUMS logit",
         f"Between-PUMA slope ({pitfalls['ecologic']['MI_between']:.2f}, {pitfalls['ecologic']['OH_between']:.2f}) ~10x within ({pitfalls['ecologic']['MI_within']:.2f}, {pitfalls['ecologic']['OH_within']:.2f})"),
        ("Regional cost of living (R141)", "Nominal ACS per-capita income", "BEA 2023 RPP-adjusted real PCI",
         f"4-state spread narrows from \\${pitfalls['rpp']['nominal_spread']:,.0f} to \\${pitfalls['rpp']['real_spread']:,.0f} ({pitfalls['rpp']['pct_change']}%)"),
    ]
    t2_tex_lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{Empirical Magnitude of Four Common Methodological Pitfalls in US County and PUMA Surveillance.}",
        r"\label{tab:method_pitfalls}",
        r"\begin{tabular}{llll}",
        r"\toprule",
        r"Methodological Domain & Naive Practice & Validated Layer A Method & Empirical Finding \\",
        r"\midrule",
    ]
    t2_md_lines = [
        "| Methodological Domain | Naive Practice | Validated Layer A Method | Empirical Finding |",
        "| --- | --- | --- | --- |",
    ]
    for dom, naive, val, find in t2_rows:
        t2_tex_lines.append(f"{dom} & {naive} & {val} & {find} \\\\")
        t2_md_lines.append(f"| {dom} | {naive} | {val.replace('$', '')} | {find.replace(r'\$', '$')} |")
    t2_tex_lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    t2_tex_path = TAB_DIR / "table2_methodological_pitfalls.tex"
    t2_md_path = TAB_DIR / "table2_methodological_pitfalls.md"
    t2_tex_path.write_text("\n".join(t2_tex_lines) + "\n", encoding="utf-8")
    t2_md_path.write_text("\n".join(t2_md_lines) + "\n", encoding="utf-8")

    return {
        "table1_tex": str(t1_tex_path),
        "table1_md": str(t1_md_path),
        "table2_tex": str(t2_tex_path),
        "table2_md": str(t2_md_path),
    }


def build_bibtex_and_manuscript(
    causes: List[Dict[str, Any]],
    pitfalls: Dict[str, Any],
    tables: Dict[str, str],
) -> Dict[str, str]:
    bib = """@article{riebler2016bym2,
  title = {An intuitive Bayesian spatial model for disease mapping that accounts for scaling},
  author = {Riebler, Andrea and S{\\o}rbye, Sigrunn H. and Simpson, Daniel and Rue, H{\\aa}vard},
  journal = {Statistical Methods in Medical Research},
  year = {2016},
  volume = {25},
  number = {4},
  pages = {1145--1165},
  doi = {10.1177/0962280216660421}
}

@article{vanderweele2017evalue,
  title = {Sensitivity Analysis in Observational Research: Introducing the E-Value},
  author = {VanderWeele, Tyler J. and Ding, Peng},
  journal = {Annals of Internal Medicine},
  year = {2017},
  volume = {167},
  number = {4},
  pages = {268--274},
  doi = {10.7326/M16-2607}
}

@article{muller2022scpc,
  title = {Spatial Correlation Robust Inference},
  author = {M{\\"u}ller, Ulrich K. and Watson, Mark W.},
  journal = {Econometrica},
  year = {2022},
  volume = {90},
  number = {6},
  pages = {2901--2935},
  doi = {10.3982/ECTA19465}
}

@article{mogstad2024kww,
  title = {Inference for Ranks with Applications to Mobility across Neighbourhoods and Academic Achievement across Countries},
  author = {Mogstad, Magne and Romano, Joseph P. and Shaikh, Azeem M. and Wilhelm, Daniel},
  journal = {Review of Economic Studies},
  year = {2024},
  volume = {91},
  number = {1},
  pages = {476--518},
  doi = {10.1093/restud/rdad006}
}

@misc{census_acs_2020_2024,
  title = {American Community Survey 5-Year Data (2020--2024) and Variance Replicate Estimates},
  author = {{U.S. Census Bureau}},
  year = {2025}
}

@misc{cdc_wonder_2018_2022,
  title = {CDC WONDER Underlying Cause of Death, 2018--2022, Single Race},
  author = {{Centers for Disease Control and Prevention, National Center for Health Statistics}},
  year = {2024}
}
"""
    bib_path = OUT_DIR / "references.bib"
    bib_path.write_text(bib, encoding="utf-8")

    n_mi_gt1 = sum(1 for r in causes if r["mi_lo"] > 1.0)
    n_ny_gt1 = sum(1 for r in causes if r["ny_lo"] > 1.0)
    n_ny_lt1 = sum(1 for r in causes if r["ny_hi"] < 1.0)
    t1_md = Path(tables["table1_md"]).read_text(encoding="utf-8")
    t2_md = Path(tables["table2_md"]).read_text(encoding="utf-8")

    md = f"""# Spatial Dependence, Small-Area Shrinkage, and Ecologic Confounding in US County Mortality Surveillance: An 11-Cause Pre-Registered Analysis Across Four Industrial-Midwest and Northeast States, 2018–2022

**Study Status:** Pre-registered Layer A confirmatory synthesis (`Round 188`, offline reproducible; zero automated WONDER access; zero raw sub-national 1–9 counts emitted).

## Abstract

**Background:** County-level mortality surveillance routinely links American Community Survey (ACS) socioeconomic indicators to vital statistics, yet standard workflows often ignore spatial autocorrelation, small-area instability, ranking uncertainty, ecologic aggregation bias, and regional price differences.

**Methods:** Using a pre-registered, cryptographically verified Layer A statistical engine, we analyzed 2018–2022 CDC WONDER county mortality across **11 leading causes of death** (`heart_disease`, `drug_overdose`, `stroke`, `suicide`, `diabetes`, `clrd`, `liver_disease`, `kidney_disease`, `firearm`, `alcohol_induced`, and `unintentional_injury`) in Michigan and Ohio (primary, up to 171 counties) with out-of-region replication in New York and Pennsylvania (up to 129 counties), linked to 2020–2024 ACS 5-year estimates and 2023 BEA Regional Price Parities. We fit validated Besag-York-Mollié (BYM2, `B3`) spatial models, computed Q4/Q1 poverty crude rate ratios (90% CIs) and VanderWeele–Ding E-values, and quantified four methodological pitfalls (SCPC vs. HC3 spatial inference, KWW county ranking sets, PUMA microdata ecologic decomposition, and BEA RPP income adjustment).

**Results:** In MI+OH, all **{n_mi_gt1}/11** mortality causes showed elevated mortality in high-poverty (Q4) versus low-poverty (Q1) counties, led by drug overdose (`RR = 2.31`, 90% CI `2.25–2.37`, `E_CI = 3.93`) and firearm mortality (`RR = 2.08`, 90% CI `2.00–2.15`, `E_CI = 3.42`). In NY+PA replication, **{n_ny_gt1}/11** causes remained positively associated with poverty (including drug overdose `RR = 1.34`, firearm `RR = 1.41`, diabetes `RR = 1.16`, alcohol-induced `RR = 1.12`, unintentional injury `RR = 1.06`), whereas **{n_ny_lt1}/11** chronic/suicide causes inverted (`RR < 1.0`), reflecting dense, high-poverty but lower-mortality urban counties (e.g., NYC boroughs) versus older rural counties. BYM2 spatial mixing $\\phi$ was high (`0.50–0.95` in 21/22 cause-region models), and BYM2 smoothing shrank raw SMR IQRs across causes. Methodological benchmarks showed SCPC widens 90% CIs by `1.46x–1.52x` over HC3, KWW joint rank widths span `45–64` ranks (only `2/300` counties certifiably top-decile), between-PUMA ecologic slopes inflate individual microdata slopes by `~10x`, and BEA RPP compresses 4-state median income spread by `-46.8%`.

**Conclusions:** Robust county health surveillance requires paired out-of-region replication, BYM2 small-area smoothing, spatial-correlation-robust inference, explicit rank uncertainty, and microdata validation against ecologic confounding.

## 1. Eleven-Cause County Mortality Atlas (Table 1)

{t1_md}

*Figures:* `figures/fig1_mortality_poverty_forest.pdf` (paired forest plot with E-values) and `figures/fig2_bym2_shrinkage_spatial.pdf` (BYM2 IQR shrinkage and spatial mixing $\\phi$).

## 2. Empirical Methodological Pitfalls Benchmark (Table 2)

{t2_md}

*Figure:* `figures/fig3_methodological_pitfalls.pdf` (4-panel naive vs. validated comparison).

## 3. Reproducibility & Governance

- All inputs derive from local, manually exported CDC WONDER 2018–2022 tables and cached 2020–2024 ACS 5-year / 2019–2023 PUMS extracts.
- Zero raw sub-national counts of 1–9 are printed or stored in any table, figure, or narrative.
- Bundle cryptographic verification (`verify_bundle`) seals SHA-256 digests of all tables, methods text, and `references.bib`.
"""
    md_path = OUT_DIR / "manuscript.md"
    md_path.write_text(md, encoding="utf-8")
    DOCS_COPY.parent.mkdir(parents=True, exist_ok=True)
    DOCS_COPY.write_text(md, encoding="utf-8")

    tex = r"""\documentclass[11pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage{booktabs}
\usepackage{graphicx}
\usepackage{amsmath}
\usepackage{hyperref}

\title{Spatial Dependence, Small-Area Shrinkage, and Ecologic Confounding in US County Mortality Surveillance: An 11-Cause Pre-Registered Analysis Across Four Industrial-Midwest and Northeast States, 2018--2022}
\author{Pre-Registered Layer A Research Synthesis (Round 188)}
\date{November 2026}

\begin{document}
\maketitle

\begin{abstract}
County-level mortality surveillance routinely links American Community Survey (ACS) socioeconomic indicators to vital statistics, yet standard pipelines often ignore spatial autocorrelation, small-area variance instability, ranking uncertainty, ecologic aggregation bias, and regional cost-of-living differences. Across 11 leading causes of death (2018--2022 CDC WONDER) in Michigan and Ohio (primary, $n \le 171$ counties) and New York and Pennsylvania (replication, $n \le 129$ counties), all 11 causes exhibit elevated mortality in high-poverty MI+OH counties (led by drug overdose RR $= 2.31$ and firearm RR $= 2.08$), while 6 chronic/suicide causes invert in NY+PA due to urban-rural confounding. Validated BYM2 (\texttt{B3}) smoothing stabilizes raw SMRs ($\phi \in [0.50, 0.95]$ in 21/22 models). Companion methodological benchmarks confirm SCPC widens 90\% CIs by $1.46\times$--$1.52\times$ over HC3, KWW joint rank intervals span 45--64 ranks (only 2/300 counties certifiably top-decile), between-PUMA ecologic slopes inflate individual microdata slopes by $\sim 10\times$, and BEA RPP compresses 4-state median income spread by $-46.8\%$.
\end{abstract}

\section{Eleven-Cause County Mortality Atlas}
\input{tables/table1_11cause_atlas.tex}

\begin{figure}[htbp]
\centering
\includegraphics[width=0.95\linewidth]{figures/fig1_mortality_poverty_forest.pdf}
\caption{Paired MI+OH vs.\ NY+PA Q4/Q1 county poverty crude rate ratios (90\% CIs) and E-value lower bounds across 11 causes of death, 2018--2022.}
\end{figure}

\begin{figure}[htbp]
\centering
\includegraphics[width=0.98\linewidth]{figures/fig2_bym2_shrinkage_spatial.pdf}
\caption{BYM2 (\texttt{B3}) variance shrinkage (raw SMR IQR vs.\ smoothed RR IQR) and spatial mixing $\phi$ across 11 causes and both regions.}
\end{figure}

\section{Methodological Pitfalls in Surveillance Inference}
\input{tables/table2_methodological_pitfalls.tex}

\begin{figure}[htbp]
\centering
\includegraphics[width=0.95\linewidth]{figures/fig3_methodological_pitfalls.pdf}
\caption{Empirical magnitude of four common surveillance pitfalls: SCPC vs.\ HC3 spatial inference, KWW rank uncertainty, PUMA ecologic inflation, and BEA RPP income-spread compression.}
\end{figure}

\bibliographystyle{plain}
\bibliography{references}
\end{document}
"""
    tex_path = OUT_DIR / "manuscript.tex"
    tex_path.write_text(tex, encoding="utf-8")

    return {"bib": str(bib_path), "md": str(md_path), "tex": str(tex_path), "docs_copy": str(DOCS_COPY)}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    causes = collect_11_causes()
    pitfalls = collect_pitfalls()
    figs = build_figures(causes, pitfalls)
    tabs = build_tables(causes, pitfalls)
    docs = build_bibtex_and_manuscript(causes, pitfalls, tabs)

    summary_payload = {
        "round": 188,
        "title": "Flagship 11-Cause County Mortality Spatial Atlas & Methodological Pitfalls Manuscript",
        "cause_count": len(causes),
        "causes": causes,
        "pitfalls": pitfalls,
        "figures": figs,
        "tables": tabs,
        "documents": docs,
    }
    summary_path = OUT_DIR / "summary.json"
    summary_path.write_text(json.dumps(summary_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if BUNDLE_DIR.exists():
        shutil.rmtree(BUNDLE_DIR)
    methods_md = (
        f"# {summary_payload['title']}\n\n"
        "Pre-registered Layer A synthesis of 11 CDC WONDER (2018-2022) county mortality causes "
        "across MI+OH (primary) and NY+PA (replication) using validated BYM2 (B3) spatial smoothing, "
        "VanderWeele-Ding E-values, SCPC spatial inference, KWW county ranking sets, PUMA microdata "
        "ecologic decomposition, and BEA 2023 Regional Price Parities.\n"
    )
    refs_bib = Path(docs["bib"]).read_text(encoding="utf-8")
    results_bundle(
        str(BUNDLE_DIR),
        methods=methods_md,
        results={"causes": causes, "pitfalls": pitfalls},
        provenance={"round": 188, "cause_count": len(causes)},
        citation="CDC WONDER UCD 2018-2022 (local manual exports); ACS 5-Year 2020-2024 VRE; PUMS 2019-2023; BEA 2023 RPP.",
        references={"references.bib": refs_bib},
    )
    ver = verify_bundle(str(BUNDLE_DIR))
    summary_payload["bundle_verification"] = ver
    summary_path.write_text(json.dumps(summary_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ver["ok"], "cause_count": len(causes), "bundle_verification": ver}, indent=2))
    return 0 if ver["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
