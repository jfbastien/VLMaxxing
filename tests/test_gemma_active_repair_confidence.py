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
        "paired_row_key": item_id,
        "benchmark": "test_benchmark",
        "group": "test_group",
        "answer_index": 0,
        "cell_type": "test_cell",
        "correctness_transition": transition,
        "dense_choice": 0,
        "dense_correct": dense_correct,
        "dense_parse_failure": False,
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
            "--min-harmed-retried",
            "1",
            "--min-auc-lower-ci",
            "0.5",
            "--n-bootstrap",
            "20",
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
    assert payload["risk_auc_harmed_lower_margin_ci95"]["bootstrap_unit"] == "item_id_cluster"
    assert payload["risk_auc_harmed_lower_margin_ci95"]["n_bootstrap"] == 20
    assert payload["pooled_status"]["analysis_role"] == "per_arm_primary"
    assert payload["baseline_no_retry"]["policy_label"] == "no_retry_composed_only"
    assert payload["baseline_retry_all"]["policy_label"] == "retry_all_dense"
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
    assert "duplicate row key ('test_cell', 'dupe')" in completed.stderr


def test_active_repair_confidence_allows_same_items_across_cell_types(tmp_path: Path) -> None:
    first_path = tmp_path / "first.jsonl"
    second_path = tmp_path / "second.jsonl"
    output = tmp_path / "analysis.json"
    first = _row(
        "same-item",
        transition="harmed",
        dense_correct=True,
        composed_correct=False,
        margin=0.1,
    )
    second = _row(
        "same-item",
        transition="preserved_correct",
        dense_correct=True,
        composed_correct=True,
        margin=2.0,
    )
    second["cell_type"] = "other_cell"
    _write_jsonl(first_path, [first])
    _write_jsonl(second_path, [second])

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_active_repair_confidence.py",
            "--paired-items",
            str(first_path),
            "--paired-items",
            str(second_path),
            "--output",
            str(output),
            "--min-harmed-retried",
            "1",
            "--min-auc-lower-ci",
            "0.5",
            "--n-bootstrap",
            "20",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(output.read_text())
    assert payload["n_items"] == 2
    assert payload["risk_auc_harmed_lower_margin_ci95"]["unique_item_count"] == 1
    assert payload["pooled_status"]["analysis_role"] == "supportive_pooled"
    assert payload["pooled_status"]["supportive_only"]
    assert "pooled_reuses_item_ids" in payload["pooled_status"]["warnings"]
    assert "per_arm_underpowered_or_missing_class" in payload["pooled_status"]["warnings"]
    assert {row["cell_type"] for row in payload["per_cell_type_auc"]} == {
        "other_cell",
        "test_cell",
    }


def test_active_repair_confidence_marks_multi_source_without_cell_type_as_supportive(
    tmp_path: Path,
) -> None:
    first_path = tmp_path / "first.jsonl"
    second_path = tmp_path / "second.jsonl"
    output = tmp_path / "analysis.json"
    first = _row(
        "first-item",
        transition="harmed",
        dense_correct=True,
        composed_correct=False,
        margin=0.1,
    )
    second = _row(
        "second-item",
        transition="preserved_correct",
        dense_correct=True,
        composed_correct=True,
        margin=2.0,
    )
    first.pop("cell_type")
    second.pop("cell_type")
    _write_jsonl(first_path, [first])
    _write_jsonl(second_path, [second])

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_active_repair_confidence.py",
            "--paired-items",
            str(first_path),
            "--paired-items",
            str(second_path),
            "--output",
            str(output),
            "--min-harmed-retried",
            "1",
            "--min-auc-lower-ci",
            "0.5",
            "--n-bootstrap",
            "20",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(output.read_text())
    assert payload["pooled_status"]["analysis_role"] == "supportive_pooled"
    assert payload["pooled_status"]["supportive_only"]
    assert payload["pooled_status"]["cell_type_count"] == 0
    assert payload["pooled_status"]["group_count"] == 2
    assert "pooled_supportive_only_multiple_sources" in payload["pooled_status"]["warnings"]


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
            "--min-harmed-retried",
            "1",
            "--min-auc-lower-ci",
            "0.5",
            "--n-bootstrap",
            "20",
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


def test_active_repair_confidence_applies_retry_cap_and_external_baseline(
    tmp_path: Path,
) -> None:
    paired = tmp_path / "paired.jsonl"
    baseline = tmp_path / "baseline.jsonl"
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
        ],
    )
    paired_rows = [json.loads(line) for line in paired.read_text(encoding="utf-8").splitlines()]
    for row in paired_rows:
        row["dense_end_to_end_ms"] = 200.0
    _write_jsonl(paired, paired_rows)
    baseline_rows = [
        _row(
            "harmed-low",
            transition="preserved_correct",
            dense_correct=True,
            composed_correct=True,
            margin=3.0,
        ),
        _row(
            "safe-high",
            transition="preserved_correct",
            dense_correct=True,
            composed_correct=True,
            margin=4.0,
        ),
    ]
    for row in baseline_rows:
        row["composed_end_to_end_ms"] = 90.0
        for field in list(row):
            if "confidence" in field or "margin" in field:
                del row[field]
    _write_jsonl(baseline, baseline_rows)

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_active_repair_confidence.py",
            "--paired-items",
            str(paired),
            "--baseline-paired-items",
            str(baseline),
            "--output",
            str(output),
            "--quality-delta-floor",
            "-0.01",
            "--min-speedup",
            "1.0",
            "--max-retry-rate",
            "0.50",
            "--min-harmed-retried",
            "1",
            "--min-auc-lower-ci",
            "0.5",
            "--n-bootstrap",
            "20",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(output.read_text())
    assert payload["comparison_baseline"]["speedup_dense_over_baseline"] > 1.0
    assert payload["comparison_baseline"]["baseline_confidence_capture_ms_subtracted"] == 0.0
    assert payload["viable_threshold_count"] >= 1
    best = payload["best_viable_by_speedup"]
    assert best["retry_rate"] <= 0.5
    assert best["active_speedup_vs_baseline"] >= 1.0


def test_active_repair_confidence_rejects_mismatched_external_baseline(
    tmp_path: Path,
) -> None:
    paired = tmp_path / "paired.jsonl"
    baseline = tmp_path / "baseline.jsonl"
    output = tmp_path / "analysis.json"
    _write_jsonl(
        paired,
        [
            _row(
                "active-a",
                transition="harmed",
                dense_correct=True,
                composed_correct=False,
                margin=0.1,
            )
        ],
    )
    _write_jsonl(
        baseline,
        [
            _row(
                "different-a",
                transition="preserved_correct",
                dense_correct=True,
                composed_correct=True,
                margin=3.0,
            )
        ],
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_active_repair_confidence.py",
            "--paired-items",
            str(paired),
            "--baseline-paired-items",
            str(baseline),
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "baseline-paired-items item set does not match active paired rows" in completed.stderr


def test_active_repair_confidence_rejects_reference_mismatched_external_baseline(
    tmp_path: Path,
) -> None:
    paired = tmp_path / "paired.jsonl"
    baseline = tmp_path / "baseline.jsonl"
    output = tmp_path / "analysis.json"
    _write_jsonl(
        paired,
        [
            _row(
                "same-item",
                transition="harmed",
                dense_correct=True,
                composed_correct=False,
                margin=0.1,
            )
        ],
    )
    baseline_row = _row(
        "same-item",
        transition="preserved_correct",
        dense_correct=True,
        composed_correct=True,
        margin=3.0,
    )
    baseline_row["answer_index"] = 1
    _write_jsonl(baseline, [baseline_row])

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_active_repair_confidence.py",
            "--paired-items",
            str(paired),
            "--baseline-paired-items",
            str(baseline),
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "baseline-paired-items reference fields do not match active paired rows" in (
        completed.stderr
    )


def test_active_repair_confidence_subtracts_optional_baseline_confidence_capture(
    tmp_path: Path,
) -> None:
    paired = tmp_path / "paired.jsonl"
    baseline = tmp_path / "baseline.jsonl"
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
        ],
    )
    baseline_rows = [
        _row(
            "harmed-low",
            transition="preserved_correct",
            dense_correct=True,
            composed_correct=True,
            margin=3.0,
        ),
        _row(
            "safe-high",
            transition="preserved_correct",
            dense_correct=True,
            composed_correct=True,
            margin=4.0,
        ),
    ]
    for row in baseline_rows:
        row["composed_end_to_end_ms"] = 90.0
        row["composed_first_generated_confidence_capture_ms"] = 7.0
    _write_jsonl(baseline, baseline_rows)

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_active_repair_confidence.py",
            "--paired-items",
            str(paired),
            "--baseline-paired-items",
            str(baseline),
            "--output",
            str(output),
            "--min-harmed-retried",
            "1",
            "--min-auc-lower-ci",
            "0.5",
            "--n-bootstrap",
            "20",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(output.read_text())
    assert payload["comparison_baseline"]["baseline_total_raw_ms"] == 180.0
    assert payload["comparison_baseline"]["baseline_confidence_capture_ms_subtracted"] == 14.0
    assert payload["comparison_baseline"]["baseline_total_ms"] == 166.0
    assert payload["comparison_baseline"]["dense_total_raw_ms"] == 200.0
    assert payload["comparison_baseline"]["dense_confidence_capture_ms_subtracted"] == 10.0
    assert payload["comparison_baseline"]["dense_total_ms"] == 190.0
