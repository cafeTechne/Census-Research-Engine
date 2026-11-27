# Post-v0.115.0 Implementation Plan: Tracks (A), (B), and (C)

**Date:** 2026-11-26  
**Baseline:** `v0.115.0` (`d9d6dee`) + R120 cancer surveillance study & manifest fixes (`641fa47`).  
**Execution order:** Track (A) → Track (B) → Track (C).  
**Standing rules:** Validation first; no AI attribution; no secrets logged/committed; no raw WONDER 1–9 counts; legacy manifest goldens (`run_golden.py`) remain byte-identical.

---

## Track (A) — Real-Data Stress-Test of Remaining Manifest Methods (4.1)

**Goal:** Flush out real-data manifest-runner bugs in the remaining 9 Rounds 104–114 manifest methods (`estimate_effect`, `stratified`, `rdd`, `joinpoint`, `demography`, `difference_in_differences`, `interrupted_series`, `combine_estimates`, `bias_analysis`), just as the R120 study caught 4 bugs in `disease_map`, `spatial_scan`, `agreement`, and `methods_text`.

### Explicit steps
1. **Audit every `_run_*`, `_stat_*`, and `_check_*` handler** for the 9 remaining methods in `census/manifest/methods.py` against the actual return dictionaries of their underlying library functions (`causal.py`, `stratified.py`, `rdd.py`, `joinpoint.py`, `demography.py`, `did.py`, `missing_censored_its.py`, `evidence.py`, `bias_analysis.py`) — specifically checking key-name mismatches (like `validated` vs `confirmatory`/`validated_p`), external-variable handling, and real-frame edge cases.
2. **Fix every integration bug found** in `census/manifest/methods.py` without changing validated statistical estimators or breaking `run_golden.py`.
3. **Run an end-to-end real-data multi-method stress study** using already-cached local data (zero manual downloads):
   - **Pre-registered manifest:** `examples/manifests/r121_mi_ny_multimethod_audit.json` (exercising `estimate_effect` with DAG/causal spec, `bias_analysis` E-value, `combine_estimates` pooling MI/NY & OH/PA R120 cancer poverty slopes, and `stratified` / `rdd` / `joinpoint` / `demography` / `difference_in_differences` / `interrupted_series` via offline end-to-end `run_manifest` integration tests).
   - **Regression suite:** `tests/test_track_a_manifest_parity.py` running full `run_manifest` (manifest JSON → `run.json`, `methods.md`, `references.bib`, `bundle.json`, Holm hypotheses) across all 9 methods so no key mismatch can ever regress.

### Acceptance criteria
- Every one of the 9 methods completes end-to-end through `run_manifest` with clean JSON serialization, non-empty hypothesis statistics, and accurate `confirmatory` vs `exploratory` gating.
- `tests/test_track_a_manifest_parity.py` passes offline; `scripts/run_golden.py` stays byte-identical.

---

## Track (B) — Bundle `references.bib` Polish & Release Housekeeping (4.2 + 4.3)

**Goal:** Make every manifest bundle emit a publication-ready `references.bib` alongside `methods.md`, and sync `STATUS.md` / `ROADMAP_BACKLOG.md` to reflect `v0.115.0` tagged and pushed.

### Explicit steps
1. **Add `manifest_citations(manifest, results=None)`** in `census/manifest/methods_text.py` returning the deduplicated ordered list of citation keys used in `methods.md` (both legacy `REFERENCES` keys and `census.references.SOURCES` keys).
2. **Auto-emit `bundle/references.bib`** in the bundle writer (`census/report_tables.py` / `census/manifest/run.py`), rendering valid BibTeX entries via `census.references.bibtex()` for every resolved citation key (with a clean fallback for legacy keys) and recording `references.bib` in `bundle.json` (only when emitting modern bundles or preserving `run_golden.py` byte-identity — verified explicitly!).
3. **Release housekeeping (4.3):**
   - Update `STATUS.md` and `ROADMAP_BACKLOG.md` to record `v0.115.0` as tagged & pushed (with a placeholder note for the Zenodo DOI once minted) and log the R120 cancer surveillance study + post-hoc without-NYC finding.
   - Verify `scripts/release_hygiene_check.py` passes cleanly.
   - Add regression tests in `tests/test_track_b_bibtex_bundle.py`.

### Acceptance criteria
- Running `run_manifest` writes a valid, non-empty `bundle/references.bib` containing `@article`/`@book`/`@misc` entries matching the methods used.
- `scripts/release_hygiene_check.py` passes (`ok: true`); all packaging and manifest tests pass.

---

## Track (C) — Layer B: OpenScholar (Semantic Scholar API + `OpenScholar_Reranker`) Upstream Hypothesis-Generation Prototype

**Goal:** Build a strictly isolated, standalone Layer B prototype (`layer_b_openscholar/`) for **upstream literature search, gap finding, and candidate hypothesis generation** before pre-registration — keeping zero LLM/GPU/vector-store dependencies inside `census/` (per `research_architecture_living_document_v11.docx`).

### Architecture & separation of concerns
- **Location:** `layer_b_openscholar/` (self-contained directory with its own `README.md`, `requirements.txt`, and `tests/`; **zero imports from or into `census/`**).
- **Mode 1 (immediate, no 700 GB download):**
  1. **Query & retrieval (`s2_client.py`):** Queries the Semantic Scholar Graph API (`paper/search`, `paper/{id}/references`, `paper/{id}/citations`) using `S2_API_KEY` from the environment (generic User-Agent, never sending personal email, polite retry/backoff, local JSON/SQLite disk cache).
  2. **Reranking (`reranker.py`):** Scores retrieved titles + abstracts against the research query using Hugging Face **`OpenScholar/OpenScholar_Reranker`** (fine-tuned `bge-reranker-large`, 0.6B params — runs on CPU or ~2 GB VRAM!) when `sentence-transformers` / `transformers` + `torch` are installed, with a deterministic **BM25 lexical fallback** when ML extras aren't installed so the pipeline works everywhere and is 100% unit-testable offline.
  3. **Gap-finding & pre-registration handoff (`handoff.py`):** Produces a traceable **Literature Dossier** (`dossier.json`, `references.bib`, `hypothesis_seeds.md`) containing:
     - Ranked papers with immutable Semantic Scholar `paperId`, DOI, year, citation count, reranker score, and exact abstract/passage snippets;
     - Structured gap prompts & candidate hypothesis records explicitly tagged `status: "exploratory_hypothesis_seed"` (never confirmatory truth);
     - A ready-to-edit **Census Research Engine manifest stub** linking the dossier's SHA-256 and DOIs into the manifest's `protocol.literature_dossier` metadata.
- **Mode 2 (optional future upgrade):** If Mode 1 proves valuable in real studies, build a **domain-scoped local datastore** (epidemiology, demography, spatial statistics: ~5–20 GB on SSD) rather than indexing the full 700 GB multi-discipline corpus on a spinning HDD.

### Acceptance criteria
- Standalone CLI (`python -m layer_b_openscholar search "..." --out ...`) runs offline with a fixture/mock client and online when `S2_API_KEY` is set.
- Emits valid `dossier.json`, `references.bib`, and `hypothesis_seeds.md` with deterministic SHA-256 provenance.
- Full offline unit tests pass (`pytest -q layer_b_openscholar/tests/`) with zero impact on `census/` dependencies or tests.
