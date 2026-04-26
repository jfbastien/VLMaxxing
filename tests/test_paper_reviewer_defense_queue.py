from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any, cast

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

queue = cast(Any, importlib.import_module("run_paper_reviewer_defense_queue"))


def test_gate_phase_162d_uses_4f_as_primary(tmp_path: Path) -> None:
    artifact_dir = tmp_path
    frame4 = {
        "outcome": "low_fps_rejected",
        "n_paired_queries": 171,
        "n_paired_sessions": 57,
        "pass_complete_pairing": True,
        "pass_format": True,
        "all": {
            "accuracy_delta_candidate_minus_reference": -0.12,
            "accuracy_delta_candidate_minus_reference_ci95": [-0.18, -0.05],
            "reference_accuracy": 0.50,
            "candidate_accuracy": 0.38,
            "speedup_reference_over_candidate": 1.8,
        },
        "first_queries": {"accuracy_delta_candidate_minus_reference": -0.05},
        "follow_ups": {"accuracy_delta_candidate_minus_reference": -0.15},
    }
    frame2 = {
        **frame4,
        "outcome": "format_invalid",
        "pass_complete_pairing": False,
        "pass_format": False,
    }
    (artifact_dir / "lowfps_4f_vs_8f_summary.json").write_text(json.dumps(frame4) + "\n")
    (artifact_dir / "lowfps_2f_vs_8f_summary.json").write_text(json.dumps(frame2) + "\n")

    gate = queue._gate_phase_162d(artifact_dir)

    assert gate["primary_outcome"] == "low_fps_rejected"
    assert gate["pass_format"] is True
    assert gate["secondary_pass_format"] is False
    assert gate["pass_complete_pairing"] is True
    assert gate["secondary_pass_complete_pairing"] is False


def test_gate_phase_163_reports_track_b_metrics(tmp_path: Path) -> None:
    artifact_dir = tmp_path
    (artifact_dir / "pair_summary.json").write_text(
        json.dumps(
            {
                "n_paired_items": 60,
                "pass_complete_pairing": True,
                "pass_format": True,
                "pass_fidelity": True,
                "pass_sparse_vision": True,
                "pass_ceiling_explained": True,
                "all": {
                    "accuracy_delta_sparse_minus_dense": -0.02,
                    "accuracy_delta_sparse_minus_dense_ci95": [-0.05, 0.02],
                    "choice_agreement": 0.95,
                    "mean_keep_rate": 0.5,
                    "vision_reduction": 0.4,
                    "vision_speedup_dense_over_sparse": 1.67,
                    "actual_e2e_speedup_dense_over_sparse": 1.06,
                    "predicted_e2e_speedup_from_vision_only": 1.05,
                    "actual_minus_predicted_e2e_speedup": 0.01,
                },
            }
        )
        + "\n"
    )

    gate = queue._gate_phase_163(artifact_dir)

    assert gate["n_paired_items"] == 60
    assert gate["pass_fidelity"] is True
    assert gate["pass_sparse_vision"] is True
    assert gate["pass_e2e_positive"] is True
    assert gate["pass_ceiling_explained"] is True


def test_gate_phase_157g_records_cross_arch_verdict(tmp_path: Path) -> None:
    artifact_dir = tmp_path
    (artifact_dir / "summary.json").write_text(
        json.dumps(
            {
                "complete": True,
                "missing": [],
                "cells": [
                    {
                        "group": "short",
                        "frame_count": 8,
                        "static_mean_cos": 0.75,
                    }
                ],
                "cross_arch": {
                    "complete": True,
                    "matched_geometry": False,
                    "matched_threshold": 0.05,
                    "exceeded_threshold": [{"group": "short", "frame_count": 8}],
                },
            }
        )
        + "\n"
    )

    gate = queue._gate_phase_157g(artifact_dir)

    assert gate["complete"] is True
    assert gate["cross_arch_complete"] is True
    assert gate["matched_geometry"] is False
    assert gate["matched_threshold"] == 0.05
    assert gate["exceeded_threshold"] == [{"group": "short", "frame_count": 8}]
