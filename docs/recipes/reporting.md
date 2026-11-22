# Reporting: tables, maps, codebooks and results bundles

Goal: turn results into publication outputs with their provenance.

1. **Tables:** `make_table(kind="descriptive", input_path=<frame>, variables=[...])` writes LaTeX (booktabs),
   Markdown and CSV. `kind="comparison"` takes a `batch_significance` output.
2. **Maps:** `make_map(...)` writes PDF, SVG, EPS and PNG, with a values CSV, caption and provenance. See recipe
   `spatial_patterns`.
3. **Codebooks:** `generate_codebook(table_code, year)` gives each variable's code, label, concept, universe and
   unit. For panels, use `batch_download(include_codebook=True)`.
4. **Exploratory bundle:**
   - save each tool result with `python -m census tool ... --save PATH`;
   - then call `make_results_bundle(output_dir, results={name: path}, figure_paths=[...], inputs=[...])`;
   - it writes the results JSON, figures, `methods.md` and `bundle.json`, with SHA-256 hashes and the data
     citation;
   - failed steps are refused unless `allow_failed_results=True`, which lists them as failed.
5. **Pre-registered analyses:** these already produce their bundle through `run_manifest` (recipe `preregistered`).
   Label anything else exploratory.
6. In every output, report estimates with 90% MOEs or the interval the tool used, and its validation flag.
