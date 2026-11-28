# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 191: LaTeX lint verification & zero-CDN offline interactive 11-cause mortality atlas companion."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from census.report_tables import lint_latex

OUT_DIR = ROOT / "studies_output" / "r188_flagship_manuscript"
DASHBOARD_PATH = OUT_DIR / "dashboard.html"
SUMMARY_MD = ROOT / "docs" / "studies" / "r191_interactive_atlas_summary.md"


def build_companion() -> dict:
    summary = json.loads((OUT_DIR / "summary.json").read_text(encoding="utf-8"))
    causes = summary["causes"]
    pitfalls = summary["pitfalls"]

    tex_files = [
        OUT_DIR / "tables" / "table1_11cause_atlas.tex",
        OUT_DIR / "tables" / "table2_methodological_pitfalls.tex",
        OUT_DIR / "manuscript.tex",
    ]
    lint_results = {
        p.name: lint_latex(p.read_text(encoding="utf-8"))
        for p in tex_files
    }
    all_lint_ok = all(r["ok"] for r in lint_results.values())

    causes_json = json.dumps(causes)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>11-Cause US County Mortality Spatial Atlas &amp; Methodological Pitfalls (Round 188/191)</title>
<style>
  body {{ font-family: system-ui, -apple-system, sans-serif; margin: 2rem auto; max-width: 1120px; color: #1a1a1a; line-height: 1.5; }}
  h1, h2 {{ color: #0b3c5d; }}
  .meta {{ background: #f4f7fa; border-left: 4px solid #0072B2; padding: 0.75rem 1rem; margin-bottom: 1.5rem; font-size: 0.92rem; }}
  table {{ width: 100%; border-collapse: collapse; margin: 1rem 0 2rem; font-size: 0.9rem; }}
  th, td {{ border-bottom: 1px solid #ddd; padding: 0.5rem 0.6rem; text-align: right; }}
  th:first-child, td:first-child {{ text-align: left; }}
  th {{ background: #eef3f8; cursor: pointer; user-select: none; }}
  tr:hover {{ background: #f9fbfd; }}
  .pos {{ color: #b33a00; font-weight: 600; }}
  .inv {{ color: #0072B2; font-weight: 600; }}
  .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 1rem; margin: 1rem 0 2rem; }}
  .card {{ border: 1px solid #d7e0ea; border-radius: 6px; padding: 0.9rem 1rem; background: #fafcfe; }}
  .card h3 {{ margin: 0 0 0.4rem; font-size: 0.95rem; color: #0b3c5d; }}
  .metric {{ font-size: 1.35rem; font-weight: 700; color: #D55E00; }}
</style>
</head>
<body>
<h1>11-Cause US County Mortality Spatial Atlas &amp; Methodological Pitfalls</h1>
<div class="meta">
  <strong>Pre-Registered Layer A Synthesis (Rounds 188 &amp; 191)</strong> &middot;
  CDC WONDER 2018&ndash;2022 (MI+OH primary vs. NY+PA replication) + ACS 2020&ndash;2024 VRE + BEA 2023 RPP &middot;
  Zero CDN dependencies &middot; Zero raw sub-national 1&ndash;9 counts.
</div>

<h2>1. Four Empirical Methodological Pitfalls</h2>
<div class="cards">
  <div class="card"><h3>Spatial Inference (R137)</h3><div class="metric">{pitfalls["scpc"]["MI_NY_ratio"]:.2f}x &ndash; {pitfalls["scpc"]["OH_PA_ratio"]:.2f}x</div><div>SCPC vs. HC3 90% CI widening</div></div>
  <div class="card"><h3>County Rankings (R139)</h3><div class="metric">2 / 300</div><div>Counties certifiably top-decile (KWW joint width 45&ndash;64)</div></div>
  <div class="card"><h3>PUMA Ecologic Bias (R136)</h3><div class="metric">~10x</div><div>Between-PUMA ({pitfalls["ecologic"]["MI_between"]:.2f}, {pitfalls["ecologic"]["OH_between"]:.2f}) vs. within ({pitfalls["ecologic"]["MI_within"]:.2f}, {pitfalls["ecologic"]["OH_within"]:.2f})</div></div>
  <div class="card"><h3>BEA RPP Spread (R141)</h3><div class="metric">{pitfalls["rpp"]["pct_change"]}%</div><div>4-state PCI spread ${pitfalls["rpp"]["nominal_spread"]:,.0f} &rarr; ${pitfalls["rpp"]["real_spread"]:,.0f}</div></div>
</div>

<h2>2. Interactive 11-Cause County Mortality Table (Click Headers to Sort)</h2>
<table id="atlas">
  <thead>
    <tr>
      <th data-k="label">Cause of Death</th>
      <th data-k="mi_rr">MI+OH Q4/Q1 RR</th>
      <th data-k="mi_eval">MI+OH E-val</th>
      <th data-k="mi_phi">MI+OH &phi;</th>
      <th data-k="ny_rr">NY+PA Q4/Q1 RR</th>
      <th data-k="ny_eval">NY+PA E-val</th>
      <th data-k="ny_phi">NY+PA &phi;</th>
    </tr>
  </thead>
  <tbody></tbody>
</table>

<script>
const DATA = {causes_json};
let sortKey = "mi_rr", sortAsc = false;
function render() {{
  const rows = [...DATA].sort((a, b) => {{
    const va = a[sortKey], vb = b[sortKey];
    if (typeof va === "string") return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
    return sortAsc ? va - vb : vb - va;
  }});
  const tb = document.querySelector("#atlas tbody");
  tb.innerHTML = rows.map(r => `<tr>
    <td>${{r.label}}</td>
    <td class="${{r.mi_rr >= 1 ? 'pos' : 'inv'}}">${{r.mi_rr.toFixed(2)}} (${{r.mi_lo.toFixed(2)}}-${{r.mi_hi.toFixed(2)}})</td>
    <td>${{r.mi_eval.toFixed(2)}}</td>
    <td>${{r.mi_phi.toFixed(2)}}</td>
    <td class="${{r.ny_rr >= 1 ? 'pos' : 'inv'}}">${{r.ny_rr.toFixed(2)}} (${{r.ny_lo.toFixed(2)}}-${{r.ny_hi.toFixed(2)}})</td>
    <td>${{r.ny_eval.toFixed(2)}}</td>
    <td>${{r.ny_phi.toFixed(2)}}</td>
  </tr>`).join("");
}}
document.querySelectorAll("#atlas th").forEach(th => th.addEventListener("click", () => {{
  const k = th.dataset.k;
  sortAsc = (sortKey === k) ? !sortAsc : false;
  sortKey = k;
  render();
}}));
render();
</script>
</body>
</html>
"""
    DASHBOARD_PATH.write_text(html, encoding="utf-8")

    md_lines = [
        "# Round 191: Interactive 11-Cause Mortality Atlas Companion & LaTeX Verification",
        "",
        f"- **LaTeX Structural Lint (`census.report_tables.lint_latex`):** `ok={all_lint_ok}` across `{len(tex_files)}` `.tex` files (`table1_11cause_atlas.tex`, `table2_methodological_pitfalls.tex`, `manuscript.tex`).",
        "- **Offline Interactive Dashboard:** `studies_output/r188_flagship_manuscript/dashboard.html` (zero external CDN requests; client-side sortable across all 11 CDC WONDER mortality causes + 4 methodological pitfall cards).",
        "- **Governance:** Zero raw sub-national 1–9 counts emitted.",
    ]
    SUMMARY_MD.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return {"ok": all_lint_ok, "lint_results": lint_results, "dashboard": str(DASHBOARD_PATH), "summary_md": str(SUMMARY_MD)}


if __name__ == "__main__":
    rep = build_companion()
    print(json.dumps(rep, indent=2))
    raise SystemExit(0 if rep["ok"] else 1)
