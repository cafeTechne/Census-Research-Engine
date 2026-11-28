# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 203 tests: spatial_model(allow_disconnected=True) & top-level census exports."""
from __future__ import annotations

import inspect

import census
from census.workflows_geo import spatial_model


def test_r203_exports_and_spatial_model_signature():
    assert callable(census.confounding_adjustment_screen)
    assert callable(census.lint_latex)
    assert callable(census.compile_latex_pdf)
    assert callable(census.verify_bundle)
    sig = inspect.signature(spatial_model)
    assert "allow_disconnected" in sig.parameters
    assert sig.parameters["allow_disconnected"].default is False
