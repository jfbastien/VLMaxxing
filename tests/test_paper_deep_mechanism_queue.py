from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any, cast

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

queue = cast(Any, importlib.import_module("run_paper_deep_mechanism_queue"))


def test_deep_mechanism_queue_startup_dirty_path_filter() -> None:
    assert queue._is_allowed_startup_dirty_path(
        Path(
            "research/experiments/2026/artifacts/"
            "phase1_63E_track_b_frame_scaling/pair_summary_16f.json"
        )
    )
    assert queue._is_allowed_startup_dirty_path(
        Path("research/experiments/2026/artifacts/paper_deep_mechanism_queue_status.json")
    )
    assert not queue._is_allowed_startup_dirty_path(Path("scripts/run_phase1_63G_gemma_track_b.py"))


def test_gate_phase_163e_reports_scaling_verdict(tmp_path: Path) -> None:
    artifact_dir = tmp_path
    (artifact_dir / "scaling_summary.json").write_text(
        json.dumps(
            {
                "complete": True,
                "headline_pass": True,
                "n_cells": 2,
                "frame_counts": [16, 32],
                "max_abs_actual_minus_predicted": 0.04,
                "cells": [
                    {
                        "frame_count": 16,
                        "n_paired_items": 60,
                        "accuracy_delta": -0.01,
                        "vision_reduction": 0.40,
                        "actual_e2e_speedup": 1.07,
                        "predicted_e2e_speedup": 1.06,
                        "actual_minus_predicted": 0.01,
                        "pass_fidelity": True,
                        "pass_sparse_vision": True,
                        "pass_e2e_positive": True,
                        "pass_ceiling_explained": True,
                    },
                    {
                        "frame_count": 32,
                        "n_paired_items": 60,
                        "accuracy_delta": -0.02,
                        "vision_reduction": 0.50,
                        "actual_e2e_speedup": 1.15,
                        "predicted_e2e_speedup": 1.12,
                        "actual_minus_predicted": 0.03,
                        "pass_fidelity": True,
                        "pass_sparse_vision": True,
                        "pass_e2e_positive": True,
                        "pass_ceiling_explained": True,
                    },
                ],
            }
        )
        + "\n"
    )

    gate = queue._gate_phase_163e(artifact_dir)

    assert gate["headline_pass"] is True
    assert gate["frame_counts"] == [16, 32]
    assert gate["max_abs_actual_minus_predicted"] == 0.04
    assert gate["cells"][1]["frame_count"] == 32


def test_gate_phase_165_reports_predictor_metrics(tmp_path: Path) -> None:
    artifact_dir = tmp_path
    (artifact_dir / "prediction_summary.json").write_text(
        json.dumps(
            {
                "n_loaded_rows": 240,
                "n_scored_rows": 180,
                "n_unique_scored_prompts": 150,
                "n_stable_rows": 100,
                "n_drift_rows": 80,
                "auc_stability_from_dense_margin": 0.72,
                "mean_margin_stable": 2.4,
                "mean_margin_drift": 0.8,
                "safe_filter": {
                    "threshold": 1.5,
                    "precision_stable": 0.96,
                    "coverage": 0.31,
                },
                "pass_margin_signal": True,
                "pass_safe_filter": True,
            }
        )
        + "\n"
    )

    gate = queue._gate_phase_165(artifact_dir)

    assert gate["n_scored_rows"] == 180
    assert gate["auc_stability_from_dense_margin"] == 0.72
    assert gate["safe_filter_precision_stable"] == 0.96
    assert gate["pass_margin_signal"] is True
    assert gate["pass_safe_filter"] is True
