# Recipe: Publication Bundle & Citation Integrity Verification

Use this workflow after generating a study bundle (`make_results_bundle` or `run_manifest`) to verify cryptographic integrity, BibTeX completeness, and LaTeX syntax before sharing or archiving a manuscript.

## Steps

1. **Generate the bundle:**
   - From a registered manifest: `run_manifest(manifest_path=...)` writes `bundle/bundle.json`, `bundle/methods.md`, `bundle/references.bib`, and LaTeX/CSV tables.
   - From exploratory tables/figures: `make_results_bundle(...)`.
2. **Run automated bundle verification:**
   - Via MCP: `verify_bundle(bundle_dir="<path/to/bundle>")`
   - Via CLI: `python -m census verify-bundle <path/to/bundle>`
   - Via Python: `census.report_tables.verify_bundle("<path/to/bundle>")`
3. **Inspect what `verify_bundle` enforces:**
   - Every artifact listed in `bundle.json` exists and matches its recorded SHA-256 digest.
   - No unexpected or unlisted files were injected into the bundle directory.
   - `methods.md` and `references.bib` are non-empty and every cited key resolves cleanly.
   - All `.tex` tables have balanced LaTeX environments (`\begin{...}` / `\end{...}`).
4. **Archive or cite:**
   - Only publish bundles with `ok: true` and `errors: []`.
   - Record the manifest SHA-256 and `bundle.json` digest in your study report (`docs/studies/`).
