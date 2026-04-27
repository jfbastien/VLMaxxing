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
    assert queue._is_allowed_startup_dirty_path(
        Path(
            "research/experiments/2026/artifacts/"
            "phase1_55K_adaptive_temperature_sweep/t0p7/pair_metrics_k1_n7.json"
        )
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
                "headline_frame_counts": [16, 32],
                "reference_frame_counts": [],
                "max_abs_actual_minus_predicted": 0.04,
                "headline_max_abs_actual_minus_predicted": 0.04,
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
                "n_loaded_rows_raw": 342,
                "n_selected_rows": 220,
                "n_scored_rows": 180,
                "n_rejected_logit_choice_mismatch": 40,
                "n_train_rows": 144,
                "n_test_rows": 36,
                "n_unique_scored_prompts": 150,
                "n_stable_rows": 100,
                "n_drift_rows": 80,
                "source_counts": {
                    "1.30AC-cache-invalidated-negative": 100,
                    "1.30AD-cache-reuse-negative": 80,
                },
                "q_index_counts": {"1": 90, "2": 90},
                "test_auc_stability_from_dense_margin": 0.72,
                "test_auc_stability_from_dense_margin_ci95": [0.61, 0.82],
                "mean_margin_stable": 2.4,
                "mean_margin_drift": 0.8,
                "train_safe_filter": {
                    "threshold": 1.5,
                    "precision_stable": 0.96,
                    "coverage": 0.31,
                },
                "test_safe_filter_at_train_threshold": {
                    "threshold": 1.5,
                    "precision_stable": 0.93,
                    "coverage": 0.25,
                },
                "pass_class_presence": True,
                "pass_margin_signal": True,
                "pass_safe_filter": True,
            }
        )
        + "\n"
    )

    gate = queue._gate_phase_165(artifact_dir)

    assert gate["n_scored_rows"] == 180
    assert gate["n_rejected_logit_choice_mismatch"] == 40
    assert gate["test_auc_stability_from_dense_margin"] == 0.72
    assert gate["test_auc_stability_from_dense_margin_ci95"] == [0.61, 0.82]
    assert gate["train_safe_filter_precision_stable"] == 0.96
    assert gate["test_safe_filter_precision_stable"] == 0.93
    assert gate["pass_class_presence"] is True
    assert gate["pass_margin_signal"] is True
    assert gate["pass_safe_filter"] is True


def test_gate_phase_155f_stage_timing_reports_mechanism(tmp_path: Path) -> None:
    artifact_dir = tmp_path
    (artifact_dir / "stage_timing_summary.json").write_text(
        json.dumps(
            {
                "q3_fixed_over_adaptive_speedup": 20.0,
                "q3_tail_token_reduction": 0.99,
                "pass_mechanism": True,
                "pass_tail_work": True,
                "adaptive": {"q_index": {"q3": {"median_elapsed_ms": 600.0}}},
                "fixed_k1": {"q_index": {"q3": {"median_elapsed_ms": 12000.0}}},
            }
        )
        + "\n"
    )

    gate = queue._gate_phase_155f_stage_timing(artifact_dir)

    assert gate["q3_fixed_over_adaptive_speedup"] == 20.0
    assert gate["adaptive_q3"]["median_elapsed_ms"] == 600.0
    assert gate["pass_mechanism"] is True


def test_gate_phase_155k_reports_temperature_sweep(tmp_path: Path) -> None:
    artifact_dir = tmp_path
    (artifact_dir / "temperature_sweep_summary.json").write_text(
        json.dumps(
            {
                "n_cells": 2,
                "temperatures": [0.0, 0.7],
                "pass_sampler_stability": True,
                "strict_exact_match_temperatures": [0.0],
                "cells": [
                    {
                        "temperature": 0.0,
                        "paired_correctness_diffs": 0,
                        "paired_choice_diffs": 0,
                        "speedup_all_query_median_cold_over_session_follow_up": 24.9,
                    },
                    {
                        "temperature": 0.7,
                        "paired_correctness_diffs": 1,
                        "paired_choice_diffs": 1,
                        "speedup_all_query_median_cold_over_session_follow_up": 18.0,
                    },
                ],
            }
        )
        + "\n"
    )

    gate = queue._gate_phase_155k(artifact_dir)

    assert gate["pass_sampler_stability"] is True
    assert gate["temperatures"] == [0.0, 0.7]


def test_gate_phase_130af_reports_boundary_attribution(tmp_path: Path) -> None:
    artifact_dir = tmp_path
    (artifact_dir / "attribution_summary.json").write_text(
        json.dumps(
            {
                "common_pair_rows": 171,
                "accuracy_delta_gap": 0.0,
                "any_drift_set_overlap": {
                    "left_count": 30,
                    "right_count": 30,
                    "intersection_count": 12,
                    "left_only_count": 18,
                    "right_only_count": 18,
                    "jaccard": 0.25,
                },
                "cache_reuse": {
                    "streaming_summary": {"follow_up_vision_pruning_active_fraction": 0.0}
                },
                "cache_invalidated": {
                    "streaming_summary": {"follow_up_vision_pruning_active_fraction": 1.0}
                },
                "pass_complete_overlap": True,
                "pass_same_net_delta": True,
                "pass_mechanism_contrast": True,
                "pass_row_set_nonidentity": True,
            }
        )
        + "\n"
    )

    gate = queue._gate_phase_130af(artifact_dir)

    assert gate["pass_same_net_delta"] is True
    assert gate["pass_mechanism_contrast"] is True
    assert gate["any_drift_set_overlap"]["jaccard"] == 0.25
