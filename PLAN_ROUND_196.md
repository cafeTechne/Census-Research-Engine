# Plan — Round 196 (N130): Subprocess Neural Query Bridge from `.venv` to SSD `venv-neural` (`v0.192.0`)

## 1. Strategic Objective
Allow Layer B's `LocalVectorStore` and `query_hybrid_rag()` to search stored `BAAI/bge-small-en-v1.5` vectors even when invoked from Layer A's lightweight `.venv` (which has zero PyTorch dependencies), via a clean, opt-in `SubprocessNeuralEmbedder` in `layer_b_openscholar/neural_bridge.py` that delegates single-query encoding to the isolated SSD `venv-neural` interpreter.

## 2. Exact File Contracts
1. `layer_b_openscholar/neural_bridge.py`: Add `SubprocessNeuralEmbedder(model_name, venv_python=..., hf_home=...)` implementing the `Embedder` protocol (`dim`, `model_name`, `embed(texts)`), returning L2-normalized `np.float32` vectors via JSON stdout from the isolated `venv-neural` Python.
2. `layer_b_openscholar/rag.py`: When `vector_model` requests a neural model (or when neural vectors exist in `vectors.sqlite`) and `sentence_transformers` is not installed in the current interpreter, optionally instantiate `SubprocessNeuralEmbedder` if `DEFAULT_SSD_NEURAL_VENV` exists and `allow_subprocess_neural=True`.
3. `tests/test_round196.py` & `docs/audits/round196_compatibility.md`.

## 3. Acceptance Gates
1. `pytest -q tests/test_round196.py layer_b_openscholar/tests/` passes with 0 failures (using an injectable fake subprocess runner for fast offline unit testing).
2. Zero `census` imports in `layer_b_openscholar/`.

## 4. Iteration Log
- *2026-11-27:* Plan drafted and `ROADMAP_BACKLOG.md` updated with `N128–N135`.
