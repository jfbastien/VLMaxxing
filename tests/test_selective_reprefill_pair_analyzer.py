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
        },
        {
            "item_id": "videomme:short:001-3",
            "q_index": 2,
            "choice": "C",
            "correct": True,
            "response": "自动",
            "elapsed_ms": 250.0,
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
            "--label",
            "toy",
        ],
        check=True,
    )

    metrics = json.loads(output.read_text())
    assert metrics["paired_correctness_diffs"] == 1
    assert metrics["paired_choice_diffs"] == 1
    assert metrics["pathological_follow_up_hits"] == 2
    assert metrics["pathological_q3_hits"] == 1
    assert metrics["session_follow_up_median_ms"] == 225.0
    assert metrics["baseline_follow_up_median_ms"] == 950.0
    assert metrics["baseline_all_query_median_ms"] == 1000.0
    assert metrics["speedup_follow_up_median_cold_over_session"] == 950.0 / 225.0
    assert metrics["speedup_all_query_median_cold_over_session_follow_up"] == 1000.0 / 225.0
    assert metrics["q_index_breakdown"]["q3"]["pathological_hits"] == 1
