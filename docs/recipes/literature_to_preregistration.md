# Recipe: Literature Discovery to Pre-Registered Layer A Manifest (Layer B → Layer A)

Use this workflow to go from exploratory upstream literature search (isolated Layer B) to a frozen, confirmatory Layer A pre-registered manifest **without** leaking exploratory text into confirmatory inference.

## Architectural Boundary
- **Layer B (`layer_b_openscholar/`)** is strictly isolated from `census/` (zero imports in either direction). Every Layer B output is tagged `status: "exploratory_hypothesis_seed"`.
- **Human Epistemic Review Gate:** A human researcher must review the seed scaffold, choose the exact validated Layer A method and estimand, and explicitly register the manifest before running confirmatory analyses.

## Steps

1. **Seed or query the offline SSD FTS5 corpus (Layer B):**
   - Online + index: `python -m layer_b_openscholar search "<topic>" --source multi --also-index --out studies_output/layer_b_dossier`
   - Offline SSD index: `python -m layer_b_openscholar local-search "<topic>" --out studies_output/layer_b_dossier`
2. **Identify under-studied `(geography x method x recency)` cells (Layer B):**
   - `python -m layer_b_openscholar gap-matrix "<topic>" --out studies_output/layer_b_dossier/gap_matrix.json`
3. **Draft an exploratory pre-registration seed scaffold (Layer B):**
   - `python -m layer_b_openscholar draft-seed "<topic>" --geography county --method spatial_bym2 --out studies_output/layer_b_seed`
   - Validate provenance and generate a Layer A parameter template via `layer_b_openscholar.handoff_bridge.validate_and_bridge_seed(...)` or the Layer B MCP tool `validate_handoff_seed`.
4. **Human review & Layer A method verification:**
   - Call Layer A MCP `list_manifest_methods()` to confirm the candidate method is **validated** (not exploratory-only) and check its required arguments.
   - Verify geography, ACS 5-year vintage, and non-overlapping release rules (`get_recipe("preregistered")`).
5. **Register and execute the frozen Layer A manifest:**
   - Call `create_manifest(...)` to write and SHA-256 hash the frozen manifest.
   - Call `run_manifest(manifest_path=...)` to execute confirmatory tests and emit the publication bundle (with automatic `references.bib`).
6. **Verify the publication bundle:**
   - Call `verify_bundle(bundle_dir=...)` (MCP) or `python -m census verify-bundle <bundle_dir>` (CLI).
