from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _row(
    item_id: str,
    *,
    transition: str,
    dense_correct: bool,
    composed_correct: bool,
    margin: float,
) -> dict[str, object]:
    return {
        "item_id": item_id,
        "cell_type": "test_cell",
        "correctness_transition": transition,
        "dense_correct": dense_correct,
        "composed_correct": composed_correct,
        "dense_end_to_end_ms": 100.0,
        "composed_end_to_end_ms": 50.0,
        "dense_first_generated_confidence_capture_ms": 5.0,
        "composed_first_generated_confidence_capture_ms": 2.0,
        "composed_first_generated_candidate_top2_margin": margin,
    }


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_active_repair_confidence_sweeps_thresholds(tmp_path: Path) -> None:
    paired = tmp_path / "paired.jsonl"
    output = tmp_path / "analysis.json"
    _write_jsonl(
        paired,
        [
            _row(
                "harmed-low",
                transition="harmed",
                dense_correct=True,
                composed_correct=False,
                margin=0.1,
            ),
            _row(
                "safe-high",
                transition="preserved_correct",
                dense_correct=True,
                composed_correct=True,
                margin=2.0,
            ),
            _row(
                "wrong-low",
                transition="unchanged_wrong",
                dense_correct=False,
                composed_correct=False,
                margin=0.2,
            ),
        ],
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_active_repair_confidence.py",
            "--paired-items",
            str(paired),
            "--output",
            str(output),
            "--quality-delta-floor",
            "-0.01",
            "--min-speedup",
            "1.0",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(output.read_text())
    assert payload["n_items"] == 3
    assert payload["cell_types"] == ["test_cell"]
    assert payload["source_paths"] == [str(paired)]
    assert payload["harmed_count"] == 1
    assert payload["risk_auc_harmed_lower_margin"] == 1.0
    assert payload["viable_threshold_count"] >= 1
    best = payload["best_viable_by_speedup"]
    assert best["harmed_retried"] == 1
    assert best["accuracy_delta_vs_dense"] >= -0.01
    assert best["speedup_dense_over_active"] > 1.0
    assert best["speedup_composed_over_active"] < 1.0
    assert best["active_total_ms"] == 245.0
    assert best["dense_total_ms"] == 285.0
    assert best["dense_confidence_capture_ms_subtracted"] == 15.0
    assert best["composed_confidence_capture_ms_charged"] == 6.0


def test_active_repair_confidence_requires_margin(tmp_path: Path) -> None:
    paired = tmp_path / "paired.jsonl"
    output = tmp_path / "analysis.json"
    _write_jsonl(
        paired,
        [
            {
                "item_id": "missing",
                "correctness_transition": "harmed",
                "dense_correct": True,
                "composed_correct": False,
                "dense_end_to_end_ms": 100.0,
                "composed_end_to_end_ms": 50.0,
            }
        ],
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_active_repair_confidence.py",
            "--paired-items",
            str(paired),
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "missing composed_first_generated_candidate_top2_margin" in completed.stderr


def test_active_repair_confidence_rejects_nonfinite_timing(tmp_path: Path) -> None:
    paired = tmp_path / "paired.jsonl"
    output = tmp_path / "analysis.json"
    row = _row(
        "bad-timing",
        transition="harmed",
        dense_correct=True,
        composed_correct=False,
        margin=0.1,
    )
    row["dense_end_to_end_ms"] = float("nan")
    _write_jsonl(paired, [row])

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_active_repair_confidence.py",
            "--paired-items",
            str(paired),
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "non-finite dense_end_to_end_ms" in completed.stderr


def test_active_repair_confidence_rejects_duplicate_item_ids(tmp_path: Path) -> None:
    paired = tmp_path / "paired.jsonl"
    output = tmp_path / "analysis.json"
    _write_jsonl(
        paired,
        [
            _row(
                "dupe",
                transition="harmed",
                dense_correct=True,
                composed_correct=False,
                margin=0.1,
            ),
            _row(
                "dupe",
                transition="preserved_correct",
                dense_correct=True,
                composed_correct=True,
                margin=2.0,
            ),
        ],
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_active_repair_confidence.py",
            "--paired-items",
            str(paired),
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "duplicate item_id 'dupe'" in completed.stderr


def test_active_repair_confidence_rejects_mixed_cell_types(tmp_path: Path) -> None:
    paired = tmp_path / "paired.jsonl"
    output = tmp_path / "analysis.json"
    first = _row(
        "first",
        transition="harmed",
        dense_correct=True,
        composed_correct=False,
        margin=0.1,
    )
    second = _row(
        "second",
        transition="preserved_correct",
        dense_correct=True,
        composed_correct=True,
        margin=2.0,
    )
    second["cell_type"] = "other_cell"
    _write_jsonl(paired, [first, second])

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_active_repair_confidence.py",
            "--paired-items",
            str(paired),
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "paired rows must have one cell_type" in completed.stderr


def test_active_repair_confidence_rejects_nonfinite_thresholds(tmp_path: Path) -> None:
    paired = tmp_path / "paired.jsonl"
    output = tmp_path / "analysis.json"
    _write_jsonl(
        paired,
        [
            _row(
                "harmed-low",
                transition="harmed",
                dense_correct=True,
                composed_correct=False,
                margin=0.1,
            )
        ],
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_active_repair_confidence.py",
            "--paired-items",
            str(paired),
            "--output",
            str(output),
            "--quality-delta-floor",
            "nan",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "--quality-delta-floor must be finite" in completed.stderr


def test_active_repair_confidence_does_not_count_no_retry_as_viable(tmp_path: Path) -> None:
    paired = tmp_path / "paired.jsonl"
    output = tmp_path / "analysis.json"
    _write_jsonl(
        paired,
        [
            _row(
                "safe-a",
                transition="preserved_correct",
                dense_correct=True,
                composed_correct=True,
                margin=1.0,
            ),
            _row(
                "safe-b",
                transition="preserved_correct",
                dense_correct=True,
                composed_correct=True,
                margin=2.0,
            ),
        ],
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_active_repair_confidence.py",
            "--paired-items",
            str(paired),
            "--output",
            str(output),
            "--quality-delta-floor",
            "-0.01",
            "--min-speedup",
            "1.0",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(output.read_text())
    assert payload["harmed_count"] == 0
    assert payload["viable_threshold_count"] == 0
    assert payload["best_viable_by_speedup"] is None
