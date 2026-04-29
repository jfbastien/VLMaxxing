from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def test_selective_reprefill_pair_analyzer_surfaces_pathology_and_speed(tmp_path: Path) -> None:
    session_jsonl = tmp_path / "session.jsonl"
    baseline_jsonl = tmp_path / "baseline.jsonl"
    output = tmp_path / "pair_metrics.json"
    paired_queries = tmp_path / "paired_queries.jsonl"

    session_rows = [
        {
            "item_id": "videomme:short:001-1",
            "q_index": 0,
            "choice": "A",
            "correct": True,
            "response": "A",
            "elapsed_ms": 1000.0,
        },
        {
            "item_id": "videomme:short:001-2",
            "q_index": 1,
            "choice": "B",
            "correct": False,
            "response": "addCriterion",
            "elapsed_ms": 200.0,
            "base_cache_build_ms": 50.0,
            "cache_source": "reprefill_k=1",
        },
        {
            "item_id": "videomme:short:001-3",
            "q_index": 2,
            "choice": "C",
            "correct": True,
            "response": "自动",
            "elapsed_ms": 250.0,
            "base_cache_build_ms": 50.0,
            "cache_source": "reprefill_k=1",
        },
    ]
    baseline_rows = [
        {
            "item_id": "videomme:short:001-1",
            "q_index": 0,
            "choice": "A",
            "correct": True,
            "response": "A",
            "elapsed_ms": 1100.0,
        },
        {
            "item_id": "videomme:short:001-2",
            "q_index": 1,
            "choice": "D",
            "correct": True,
            "response": "D",
            "elapsed_ms": 1000.0,
        },
        {
            "item_id": "videomme:short:001-3",
            "q_index": 2,
            "choice": "C",
            "correct": True,
            "response": "C",
            "elapsed_ms": 900.0,
        },
    ]
    _write_jsonl(session_jsonl, session_rows)
    _write_jsonl(baseline_jsonl, baseline_rows)

    subprocess.run(
        [
            sys.executable,
            "scripts/analyze_selective_reprefill_pairs.py",
            "--session-jsonl",
            str(session_jsonl),
            "--baseline-jsonl",
            str(baseline_jsonl),
            "--output",
            str(output),
            "--paired-queries",
            str(paired_queries),
            "--label",
            "toy",
            "--n-resamples",
            "200",
            "--seed",
            "0",
        ],
        check=True,
    )

    metrics = json.loads(output.read_text())
    paired_rows = [
        json.loads(line) for line in paired_queries.read_text().splitlines() if line.strip()
    ]
    assert len(paired_rows) == 3
    assert metrics["n_sessions"] == 1
    assert metrics["session_n_correct"] == 2
    assert metrics["baseline_n_correct"] == 3
    assert metrics["session_accuracy"] == 2 / 3
    assert metrics["baseline_accuracy"] == 1.0
    assert metrics["paired_correctness_diffs"] == 1
    assert metrics["paired_choice_diffs"] == 1
    assert metrics["pathological_follow_up_hits"] == 2
    assert metrics["pathological_q3_hits"] == 1
    assert (
        metrics["accuracy_delta_session_minus_baseline_ci95"][0]
        <= metrics["accuracy_delta_session_minus_baseline"]
        <= metrics["accuracy_delta_session_minus_baseline_ci95"][1]
    )
    assert (
        metrics["follow_up_accuracy_delta_session_minus_baseline_ci95"][0]
        <= metrics["follow_up_accuracy_delta_session_minus_baseline"]
        <= metrics["follow_up_accuracy_delta_session_minus_baseline_ci95"][1]
    )
    assert (
        metrics["q3_accuracy_delta_session_minus_baseline_ci95"][0]
        <= metrics["q3_accuracy_delta_session_minus_baseline"]
        <= metrics["q3_accuracy_delta_session_minus_baseline_ci95"][1]
    )
    assert metrics["session_follow_up_median_ms"] == 225.0
    assert metrics["session_follow_up_setup_amortized_median_ms"] == 250.0
    assert metrics["baseline_follow_up_median_ms"] == 950.0
    assert metrics["baseline_all_query_median_ms"] == 1000.0
    assert metrics["n_follow_up_rows_with_cache_build_ms"] == 2
    assert metrics["n_sessions_with_cache_build_ms"] == 1
    assert metrics["session_cache_build_total_median_ms"] == 50.0
    assert metrics["session_total_median_ms_including_cache_build"] == 1500.0
    assert metrics["baseline_total_median_ms"] == 3000.0
    assert metrics["speedup_follow_up_median_cold_over_session"] == 950.0 / 225.0
    assert metrics["speedup_all_query_median_cold_over_session_follow_up"] == 1000.0 / 225.0
    assert metrics["speedup_follow_up_median_cold_over_session_setup_amortized"] == 950.0 / 250.0
    assert (
        metrics["speedup_all_query_median_cold_over_session_follow_up_setup_amortized"]
        == 1000.0 / 250.0
    )
    assert metrics["speedup_session_total_median_cold_over_session_including_cache_build"] == 2.0
    assert metrics["q_index_breakdown"]["q3"]["pathological_hits"] == 1


def test_selective_reprefill_pair_analyzer_leaves_setup_metrics_empty_without_setup(
    tmp_path: Path,
) -> None:
    session_jsonl = tmp_path / "session.jsonl"
    baseline_jsonl = tmp_path / "baseline.jsonl"
    output = tmp_path / "pair_metrics.json"
    session_rows = [
        {
            "item_id": "videomme:short:001-1",
            "q_index": 0,
            "choice": "A",
            "correct": True,
            "response": "A",
            "elapsed_ms": 100.0,
        },
        {
            "item_id": "videomme:short:001-2",
            "q_index": 1,
            "choice": "B",
            "correct": True,
            "response": "B",
            "elapsed_ms": 20.0,
        },
    ]
    baseline_rows = [
        {
            "item_id": "videomme:short:001-1",
            "q_index": 0,
            "choice": "A",
            "correct": True,
            "response": "A",
            "elapsed_ms": 120.0,
        },
        {
            "item_id": "videomme:short:001-2",
            "q_index": 1,
            "choice": "B",
            "correct": True,
            "response": "B",
            "elapsed_ms": 80.0,
        },
    ]
    _write_jsonl(session_jsonl, session_rows)
    _write_jsonl(baseline_jsonl, baseline_rows)

    subprocess.run(
        [
            sys.executable,
            "scripts/analyze_selective_reprefill_pairs.py",
            "--session-jsonl",
            str(session_jsonl),
            "--baseline-jsonl",
            str(baseline_jsonl),
            "--output",
            str(output),
            "--n-resamples",
            "20",
        ],
        check=True,
    )

    metrics = json.loads(output.read_text())
    assert metrics["n_follow_up_rows_with_cache_build_ms"] == 0
    assert metrics["n_sessions_with_cache_build_ms"] == 0
    assert metrics["session_follow_up_setup_amortized_median_ms"] is None
    assert metrics["session_cache_build_total_median_ms"] is None
    assert metrics["session_total_median_ms_including_cache_build"] is None
    assert metrics["baseline_total_median_ms"] is None
    assert metrics["speedup_session_total_median_cold_over_session_including_cache_build"] is None
