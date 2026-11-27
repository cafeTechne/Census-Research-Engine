# SPDX-License-Identifier: AGPL-3.0-or-later
"""Standalone Layer B prototype: Semantic Scholar + OpenScholar_Reranker upstream hypothesis workspace."""
from .handoff import build_dossier, write_dossier
from .reranker import OpenScholarReranker
from .s2_client import SemanticScholarClient

__all__ = ["SemanticScholarClient", "OpenScholarReranker", "build_dossier", "write_dossier"]
