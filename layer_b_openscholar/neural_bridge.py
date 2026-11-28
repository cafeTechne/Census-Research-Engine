# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 190: Tier 2 Neural Runtime Bridge & Diagnostics for isolated Layer B (zero census imports)."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Sequence

import numpy as np

from .local_index import SAMSUNG_EVO_MOUNT
from .vector_store import DEFAULT_NEURAL_MODEL, LocalVectorStore, resolve_vector_path

DEFAULT_SSD_NEURAL_VENV = SAMSUNG_EVO_MOUNT / "layer_b_openscholar" / "venv-neural" / "bin" / "python"
DEFAULT_SSD_HF_CACHE = SAMSUNG_EVO_MOUNT / "layer_b_openscholar" / "hf_cache"


class SubprocessNeuralEmbedder:
    """Delegates query embedding to the isolated SSD ``venv-neural`` Python (zero torch in caller)."""

    def __init__(
        self,
        model_name: str = DEFAULT_NEURAL_MODEL,
        dim: int = 384,
        venv_python: Optional[str | Path] = None,
        hf_home: Optional[str | Path] = None,
        runner: Optional[Callable[[list[str], Dict[str, str]], str]] = None,
    ) -> None:
        self.model_name = model_name
        self.dim = int(dim)
        self.venv_python = Path(venv_python) if venv_python is not None else DEFAULT_SSD_NEURAL_VENV
        self.hf_home = Path(hf_home) if hf_home is not None else DEFAULT_SSD_HF_CACHE
        self._runner = runner

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        items = list(texts)
        if not items:
            return np.zeros((0, self.dim), dtype=np.float32)
        code = (
            "import json, sys; "
            "from sentence_transformers import SentenceTransformer; "
            "m = SentenceTransformer(sys.argv[1], device='cpu'); "
            "vecs = m.encode(json.loads(sys.argv[2]), normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False); "
            "print(json.dumps(vecs.tolist()))"
        )
        cmd = [str(self.venv_python), "-c", code, self.model_name, json.dumps(items)]
        env = dict(os.environ, HF_HOME=str(self.hf_home))
        if self._runner is not None:
            raw = self._runner(cmd, env)
        else:
            proc = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True, timeout=60)
            raw = proc.stdout
        arr = np.asarray(json.loads(raw.strip().splitlines()[-1]), dtype=np.float32)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        self.dim = int(arr.shape[1])
        return arr


def neural_runtime_status(vector_db_path: Optional[str | Path] = None) -> Dict[str, Any]:
    """Report current interpreter neural capabilities, SSD venv-neural presence, and stored vector models."""
    torch_ok = importlib.util.find_spec("torch") is not None
    st_ok = importlib.util.find_spec("sentence_transformers") is not None
    tf_ok = importlib.util.find_spec("transformers") is not None
    ssd_venv_ok = DEFAULT_SSD_NEURAL_VENV.exists()

    vpath = resolve_vector_path(vector_db_path)
    models: Dict[str, int] = {}
    if vpath.exists():
        try:
            models = LocalVectorStore(db_path=vpath).model_counts()
        except Exception:
            models = {}
    neural_models = {k: v for k, v in models.items() if not k.startswith("hash_projection_")}

    return {
        "ok": True,
        "status": "exploratory_hypothesis_seed",
        "current_runtime": {
            "torch_available": torch_ok,
            "sentence_transformers_available": st_ok,
            "transformers_available": tf_ok,
            "neural_ready_in_current_python": bool(torch_ok and st_ok),
        },
        "ssd_venv_neural": {
            "path": str(DEFAULT_SSD_NEURAL_VENV),
            "exists": ssd_venv_ok,
        },
        "vector_store": {
            "db_path": str(vpath),
            "exists": vpath.exists(),
            "models": models,
            "neural_models": neural_models,
            "has_neural_embeddings": len(neural_models) > 0,
        },
    }
