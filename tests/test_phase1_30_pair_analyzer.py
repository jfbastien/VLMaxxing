from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def test_phase1_30_pair_analyzer_reports_follow_up_activity(tmp_path: Path) -> None:
    cold_jsonl = tmp_path / "cold.jsonl"
    streaming_jsonl = tmp_path / "streaming.jsonl"
    cold_summary = tmp_path / "cold_summary.json"
    streaming_summary = tmp_path / "streaming_summary.json"
    pair_summary = tmp_path / "pair_summary.json"
    per_clip_buckets = tmp_path / "per_clip_buckets.json"
    paired_queries = tmp_path / "paired_queries.jsonl"

    common_rows = [
        {
            "seed_item_id": "videomme:short:001-1",
            "session_id": "videomme:short:001-1",
            "video_id": "001",
            "duration": "short",
            "split": "dev",
            "item_id": "videomme:short:001-1",
            "q_index": 0,
            "correct": True,
            "choice": "A",
            "parse_failure": False,
            "response": "A",
            "end_to_end_ms": 1000.0,
        },
        {
            "seed_item_id": "videomme:short:001-1",
            "session_id": "videomme:short:001-1",
            "video_id": "001",
            "duration": "short",
            "split": "dev",
            "item_id": "videomme:short:001-2",
            "q_index": 1,
            "correct": True,
            "choice": "B",
            "parse_failure": False,
            "response": "B",
            "end_to_end_ms": 900.0,
        },
        {
            "seed_item_id": "videomme:short:001-1",
            "session_id": "videomme:short:001-1",
            "video_id": "001",
            "duration": "short",
            "split": "dev",
            "item_id": "videomme:short:001-3",
            "q_index": 2,
            "correct": False,
            "choice": "C",
            "parse_failure": False,
            "response": "C",
            "end_to_end_ms": 800.0,
        },
    ]
    cold_rows = [dict(row) for row in common_rows]
    streaming_rows = [dict(row) for row in common_rows]
    streaming_rows[1].update(
        {
            "image_token_count": 8,
            "image_tokens_recomputed": 0,
            "vision_pruning_active": False,
            "end_to_end_ms": 200.0,
        }
    )
    streaming_rows[2].update(
        {
            "image_token_count": 8,
            "image_tokens_recomputed": 4,
            "vision_pruning_active": True,
            "parse_failure": True,
            "response": "addCriterion",
            "end_to_end_ms": 250.0,
        }
    )

    _write_jsonl(cold_jsonl, cold_rows)
    _write_jsonl(streaming_jsonl, streaming_rows)
    cold_summary.write_text(
        json.dumps({"all_queries": {"accuracy": 2 / 3}, "parse_failures": 0}) + "\n"
    )
    streaming_summary.write_text(
        json.dumps({"all_queries": {"accuracy": 2 / 3}, "parse_failures": 1}) + "\n"
    )

    subprocess.run(
        [
            sys.executable,
            "scripts/analyze_phase1_30_scaleout_streaming_pair.py",
            "--cold-jsonl",
            str(cold_jsonl),
            "--streaming-jsonl",
            str(streaming_jsonl),
            "--cold-summary",
            str(cold_summary),
            "--streaming-summary",
            str(streaming_summary),
            "--pair-summary",
            str(pair_summary),
            "--per-clip-buckets",
            str(per_clip_buckets),
            "--paired-queries",
            str(paired_queries),
            "--n-resamples",
            "200",
            "--seed",
            "0",
        ],
        check=True,
    )

    summary = json.loads(pair_summary.read_text())
    assert summary["n_paired_sessions"] == 1
    assert (
        summary["accuracy_delta_streaming_minus_cold_ci95"][0]
        <= summary["accuracy_delta_streaming_minus_cold"]
        <= summary["accuracy_delta_streaming_minus_cold_ci95"][1]
    )
    assert summary["q0_accuracy_delta_streaming_minus_cold"] == 0.0
    assert summary["q0_n_paired_queries"] == 1
    assert summary["follow_up_n_paired_queries"] == 2
    assert (
        summary["follow_up_accuracy_delta_streaming_minus_cold_ci95"][0]
        <= summary["follow_up_accuracy_delta_streaming_minus_cold"]
        <= summary["follow_up_accuracy_delta_streaming_minus_cold_ci95"][1]
    )
    assert summary["streaming_follow_up_n"] == 2
    assert summary["streaming_parse_failures"] == 1
    assert summary["streaming_parse_failure_fraction"] == 1 / 3
    assert summary["streaming_follow_up_vision_pruning_active_count"] == 1
    assert summary["streaming_follow_up_vision_pruning_active_fraction"] == 0.5
    assert summary["streaming_follow_up_all_image_tokens_reused_count"] == 1
    assert summary["streaming_follow_up_all_image_tokens_reused_fraction"] == 0.5
    assert summary["streaming_degenerate_count"] == 1
