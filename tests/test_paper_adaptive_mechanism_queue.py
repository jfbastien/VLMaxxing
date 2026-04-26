from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any, cast

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

queue = cast(Any, importlib.import_module("run_paper_adaptive_mechanism_queue"))


def test_gate_phase_130ac_flags_helpful_activation() -> None:
    summary = {
        "accuracy_delta_streaming_minus_cold": -0.08,
        "accuracy_delta_streaming_minus_cold_ci95": [-0.14, -0.01],
        "amortized_speedup_cold_over_streaming": 2.4,
        "streaming_parse_failures": 0,
        "streaming_degenerate_count": 0,
        "n_paired_queries": 171,
        "n_paired_sessions": 57,
        "streaming_follow_up_vision_pruning_active_fraction": 0.95,
        "streaming_follow_up_all_image_tokens_reused_fraction": 0.0,
        "streaming_follow_up_mean_image_tokens_recomputed": 128.0,
    }

    gate = queue._gate_phase_130ac(summary)

    assert gate["pass_complete_pairing"] is True
    assert gate["pass_activation"] is True
    assert gate["pass_helpful_rescue"] is True
    assert gate["evidence_hurtful"] is False
    assert gate["mechanism_outcome"] == "helpful"


def test_gate_phase_130ac_flags_hurtful_activation() -> None:
    summary = {
        "accuracy_delta_streaming_minus_cold": -0.22,
        "accuracy_delta_streaming_minus_cold_ci95": [-0.30, -0.11],
        "amortized_speedup_cold_over_streaming": 2.1,
        "streaming_parse_failures": 0,
        "streaming_degenerate_count": 0,
        "n_paired_queries": 171,
        "n_paired_sessions": 57,
        "streaming_follow_up_vision_pruning_active_fraction": 1.0,
        "streaming_follow_up_all_image_tokens_reused_fraction": 0.0,
        "streaming_follow_up_mean_image_tokens_recomputed": 64.0,
    }

    gate = queue._gate_phase_130ac(summary)

    assert gate["pass_activation"] is True
    assert gate["pass_helpful_rescue"] is False
    assert gate["evidence_hurtful"] is True
    assert gate["mechanism_outcome"] == "hurtful"


def test_gate_phase_130ad_compares_against_reference(tmp_path: Path) -> None:
    reference = {
        "accuracy_delta_streaming_minus_cold": -0.0585,
        "accuracy_delta_streaming_minus_cold_ci95": [-0.117, 0.0],
    }
    reference_path = tmp_path / "reference_pair_summary.json"
    reference_path.write_text(json.dumps(reference) + "\n")

    old_reference_path = queue.PHASE130W_REFERENCE_PAIR_SUMMARY
    queue.PHASE130W_REFERENCE_PAIR_SUMMARY = reference_path
    try:
        summary = {
            "accuracy_delta_streaming_minus_cold": -0.06,
            "accuracy_delta_streaming_minus_cold_ci95": [-0.12, 0.01],
            "amortized_speedup_cold_over_streaming": 2.8,
            "streaming_parse_failures": 0,
            "streaming_degenerate_count": 0,
            "n_paired_queries": 171,
            "n_paired_sessions": 57,
            "streaming_follow_up_vision_pruning_active_fraction": 0.0,
            "streaming_follow_up_all_image_tokens_reused_fraction": 1.0,
        }

        gate = queue._gate_phase_130ad(summary)
    finally:
        queue.PHASE130W_REFERENCE_PAIR_SUMMARY = old_reference_path

    assert gate["pass_complete_pairing"] is True
    assert gate["pass_repro_delta"] is True
    assert gate["pass_repro_ci"] is True
    assert gate["pass_mechanism"] is True


def test_phase155f_gate_profiles_pin_preregistered_values() -> None:
    assert queue.PHASE155F_GATE_PROFILES == {
        "1.55F-medium": {
            "correctness_limit": 2,
            "choice_limit": 3,
            "q3_pathological_limit": 1,
            "follow_up_pathological_limit": 2,
            "max_rss_gb": 5.5,
            "min_speedup": 15.0,
            "strict_correctness_limit": 0,
            "strict_choice_limit": 0,
            "baseline_accuracy_floor": 0.40,
        },
        "1.55F-long": {
            "correctness_limit": 2,
            "choice_limit": 3,
            "q3_pathological_limit": 1,
            "follow_up_pathological_limit": 2,
            "max_rss_gb": 5.5,
            "min_speedup": 16.0,
            "strict_correctness_limit": 0,
            "strict_choice_limit": 0,
            "baseline_accuracy_floor": 0.30,
        },
        "1.55F-32f": {
            "correctness_limit": 2,
            "choice_limit": 3,
            "q3_pathological_limit": 1,
            "follow_up_pathological_limit": 2,
            "max_rss_gb": 6.0,
            "min_speedup": 30.0,
            "strict_correctness_limit": 0,
            "strict_choice_limit": 0,
            "baseline_accuracy_floor": 0.40,
        },
    }


def test_gate_phase_155j_uses_same_class_speedup() -> None:
    pair_metrics = {
        "paired_correctness_diffs": 0,
        "paired_choice_diffs": 0,
        "pathological_follow_up_hits": 0,
        "pathological_q3_hits": 0,
        "speedup_follow_up_median_cold_over_session": 8.2,
        "speedup_all_query_median_cold_over_session_follow_up": 8.5,
        "session_follow_up_median_ms": 1000.0,
    }
    summary = {
        "peak_rss_gb": 4.2,
        "temperature": 0.7,
        "top_p": 0.95,
        "min_p": 0.0,
        "baseline": {"accuracy": 0.8},
        "session": {"accuracy": 15 / 21, "n_correct": 15},
    }

    gate = queue._gate_phase_155j(pair_metrics, summary)

    assert gate["pass_fidelity"] is True
    assert gate["pass_exact_match"] is True
    assert gate["pass_same_class_speed"] is True
    assert gate["pass_session_floor"] is True
    assert gate["sampler"] == {"temperature": 0.7, "top_p": 0.95, "min_p": 0.0}


def test_gate_phase_155j_rejects_low_session_floor() -> None:
    pair_metrics = {
        "paired_correctness_diffs": 0,
        "paired_choice_diffs": 0,
        "pathological_follow_up_hits": 0,
        "pathological_q3_hits": 0,
        "speedup_follow_up_median_cold_over_session": 8.2,
        "speedup_all_query_median_cold_over_session_follow_up": 8.5,
        "session_follow_up_median_ms": 1000.0,
    }
    summary = {
        "peak_rss_gb": 4.2,
        "temperature": 0.7,
        "top_p": 0.95,
        "min_p": 0.0,
        "baseline": {"accuracy": 0.8},
        "session": {"accuracy": 13 / 21, "n_correct": 13},
    }

    gate = queue._gate_phase_155j(pair_metrics, summary)

    assert gate["pass_fidelity"] is True
    assert gate["pass_session_floor"] is False
