from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _row(
    item_id: str,
    *,
    correct: bool,
    choice_index: int | None,
    vision_ms: float,
    end_to_end_ms: float,
    kept_groups: int,
    total_groups: int,
    parse_failure: bool = False,
    scorer_prepare_ms: float | None = None,
    scorer_keep_mask_ms: float | None = None,
) -> dict[str, object]:
    timing_ms: dict[str, float] = {
        "decode": 10.0,
        "processor": 5.0,
        "vision": vision_ms,
        "generate": end_to_end_ms - vision_ms - 15.0,
        "end_to_end": end_to_end_ms,
    }
    if scorer_prepare_ms is not None and scorer_keep_mask_ms is not None:
        timing_ms.update(
            {
                "scorer_prepare": scorer_prepare_ms,
                "scorer_keep_mask": scorer_keep_mask_ms,
                "scorer_total": scorer_prepare_ms + scorer_keep_mask_ms,
                "vision_excluding_scorer": max(0.0, vision_ms - scorer_keep_mask_ms),
            }
        )
    return {
        "item_id": item_id,
        "group": "short",
        "correct": correct,
        "parse_failure": parse_failure,
        "choice_index": choice_index,
        "timing_ms": timing_ms,
        "kept_groups": kept_groups,
        "total_groups": total_groups,
    }


def _run_analyzer(
    tmp_path: Path,
    *,
    sparse_end_to_end_ms: float,
) -> dict[str, Any]:
    dense_jsonl = tmp_path / "dense.jsonl"
    sparse_jsonl = tmp_path / "sparse.jsonl"
    dense_summary = tmp_path / "dense_summary.json"
    sparse_summary = tmp_path / "sparse_summary.json"
    output = tmp_path / "summary.json"
    paired = tmp_path / "paired.jsonl"

    _write_jsonl(
        dense_jsonl,
        [
            {"kind": "schema", "schema_version": "phase1_51v_sparse_v2"},
            _row(
                "a",
                correct=True,
                choice_index=0,
                vision_ms=40.0,
                end_to_end_ms=100.0,
                kept_groups=10,
                total_groups=10,
            ),
            _row(
                "b",
                correct=False,
                choice_index=1,
                vision_ms=40.0,
                end_to_end_ms=100.0,
                kept_groups=10,
                total_groups=10,
            ),
        ],
    )
    _write_jsonl(
        sparse_jsonl,
        [
            {"kind": "schema", "schema_version": "phase1_51v_sparse_v2"},
            _row(
                "a",
                correct=True,
                choice_index=0,
                vision_ms=20.0,
                end_to_end_ms=sparse_end_to_end_ms,
                kept_groups=5,
                total_groups=10,
            ),
            _row(
                "b",
                correct=False,
                choice_index=1,
                vision_ms=20.0,
                end_to_end_ms=sparse_end_to_end_ms,
                kept_groups=5,
                total_groups=10,
            ),
        ],
    )
    dense_summary.write_text(json.dumps({"manifest": "m", "frame_count": 8}) + "\n")
    sparse_summary.write_text(
        json.dumps(
            {
                "manifest": "m",
                "frame_count": 8,
                "vision_tower_layer": 2,
                "vision_tower_keep_rate": 0.5,
            }
        )
        + "\n"
    )

    subprocess.run(
        [
            sys.executable,
            "scripts/analyze_phase1_63_track_b_sparse.py",
            "--dense-jsonl",
            str(dense_jsonl),
            "--sparse-jsonl",
            str(sparse_jsonl),
            "--dense-summary",
            str(dense_summary),
            "--sparse-summary",
            str(sparse_summary),
            "--output",
            str(output),
            "--paired-items",
            str(paired),
            "--expected-items",
            "2",
            "--bucket-e2e-min-pass",
            "1",
            "--bucket-e2e-min-n",
            "1",
        ],
        check=True,
    )

    summary: dict[str, Any] = json.loads(output.read_text())
    assert len(paired.read_text().strip().splitlines()) == 2
    return summary


def test_track_b_analyzer_reports_sparse_vision_and_ceiling(tmp_path: Path) -> None:
    summary = _run_analyzer(tmp_path, sparse_end_to_end_ms=80.0)
    all_summary = summary["all"]
    assert summary["n_paired_items"] == 2
    assert summary["pass_complete_pairing"] is True
    assert all_summary["accuracy_delta_sparse_minus_dense"] == 0.0
    assert all_summary["mean_keep_rate"] == 0.5
    assert all_summary["vision_reduction"] == 0.5
    assert all_summary["actual_e2e_speedup_dense_over_sparse"] == 1.25
    assert all_summary["actual_e2e_speedup_dense_over_sparse_ci95"] == [1.25, 1.25]
    assert summary["pass_fidelity"] is True
    assert summary["pass_sparse_vision"] is True
    assert summary["pass_e2e_positive"] is True
    assert summary["bucket_e2e_passing_groups"] == ["short"]
    assert summary["pass_bucket_e2e_positive"] is True
    assert summary["pass_parse_failure_delta"] is True
    assert summary["pass_parse_failure_rate"] is True


def test_track_b_analyzer_does_not_hide_e2e_boundary(tmp_path: Path) -> None:
    summary = _run_analyzer(tmp_path, sparse_end_to_end_ms=198.0)
    all_summary = summary["all"]
    assert all_summary["actual_e2e_speedup_dense_over_sparse"] < 1.03
    assert summary["pass_fidelity"] is True
    assert summary["pass_sparse_vision"] is True
    assert summary["pass_e2e_positive"] is False
    assert summary["pass_bucket_e2e_positive"] is False


def test_track_b_analyzer_reports_sparse_parse_failure_delta(tmp_path: Path) -> None:
    dense_jsonl = tmp_path / "dense.jsonl"
    sparse_jsonl = tmp_path / "sparse.jsonl"
    dense_summary = tmp_path / "dense_summary.json"
    sparse_summary = tmp_path / "sparse_summary.json"
    output = tmp_path / "summary.json"

    dense_rows: list[dict[str, object]] = [
        {"kind": "schema", "schema_version": "phase1_63g_gemma_track_b_v5"},
        _row(
            "a",
            correct=True,
            choice_index=0,
            vision_ms=40.0,
            end_to_end_ms=100.0,
            kept_groups=10,
            total_groups=10,
        ),
    ]
    sparse_row = _row(
        "a",
        correct=False,
        choice_index=0,
        vision_ms=20.0,
        end_to_end_ms=80.0,
        kept_groups=5,
        total_groups=10,
    )
    sparse_row["parse_failure"] = True
    sparse_rows: list[dict[str, object]] = [
        {"kind": "schema", "schema_version": "phase1_63g_gemma_track_b_v5"},
        sparse_row,
    ]
    _write_jsonl(dense_jsonl, dense_rows)
    _write_jsonl(sparse_jsonl, sparse_rows)
    dense_summary.write_text(json.dumps({"manifest": "m", "frame_count": 8}) + "\n")
    sparse_summary.write_text(
        json.dumps({"manifest": "m", "frame_count": 8, "vision_tower_keep_rate": 0.5}) + "\n"
    )

    subprocess.run(
        [
            sys.executable,
            "scripts/analyze_phase1_63_track_b_sparse.py",
            "--dense-jsonl",
            str(dense_jsonl),
            "--sparse-jsonl",
            str(sparse_jsonl),
            "--dense-summary",
            str(dense_summary),
            "--sparse-summary",
            str(sparse_summary),
            "--output",
            str(output),
            "--expected-items",
            "1",
            "--parse-failure-delta-max",
            "0",
            "--bucket-e2e-min-pass",
            "1",
            "--bucket-e2e-min-n",
            "1",
        ],
        check=True,
    )

    summary: dict[str, Any] = json.loads(output.read_text())
    assert summary["all"]["parse_failure_delta_sparse_minus_dense"] == 1
    assert summary["pass_parse_failure_delta"] is False


def test_track_b_analyzer_rejects_missing_schema(tmp_path: Path) -> None:
    dense_jsonl = tmp_path / "dense.jsonl"
    sparse_jsonl = tmp_path / "sparse.jsonl"
    dense_summary = tmp_path / "dense_summary.json"
    sparse_summary = tmp_path / "sparse_summary.json"
    output = tmp_path / "summary.json"

    _write_jsonl(
        dense_jsonl,
        [
            _row(
                "a",
                correct=True,
                choice_index=0,
                vision_ms=40.0,
                end_to_end_ms=100.0,
                kept_groups=10,
                total_groups=10,
            )
        ],
    )
    _write_jsonl(
        sparse_jsonl,
        [
            {"kind": "schema", "schema_version": "phase1_63g_gemma_track_b_v5"},
            _row(
                "a",
                correct=True,
                choice_index=0,
                vision_ms=20.0,
                end_to_end_ms=80.0,
                kept_groups=5,
                total_groups=10,
            ),
        ],
    )
    dense_summary.write_text(json.dumps({"manifest": "m", "frame_count": 8}) + "\n")
    sparse_summary.write_text(
        json.dumps({"manifest": "m", "frame_count": 8, "vision_tower_keep_rate": 0.5}) + "\n"
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_phase1_63_track_b_sparse.py",
            "--dense-jsonl",
            str(dense_jsonl),
            "--sparse-jsonl",
            str(sparse_jsonl),
            "--dense-summary",
            str(dense_summary),
            "--sparse-summary",
            str(sparse_summary),
            "--output",
            str(output),
            "--expected-items",
            "1",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "missing schema row" in completed.stderr


def test_track_b_analyzer_requires_v5_scorer_timings_when_requested(tmp_path: Path) -> None:
    summary = _run_analyzer(tmp_path, sparse_end_to_end_ms=80.0)
    assert summary["dense_schema_version"] == "phase1_51v_sparse_v2"

    output = tmp_path / "strict_summary.json"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_phase1_63_track_b_sparse.py",
            "--dense-jsonl",
            str(tmp_path / "dense.jsonl"),
            "--sparse-jsonl",
            str(tmp_path / "sparse.jsonl"),
            "--dense-summary",
            str(tmp_path / "dense_summary.json"),
            "--sparse-summary",
            str(tmp_path / "sparse_summary.json"),
            "--output",
            str(output),
            "--expected-items",
            "2",
            "--require-schema-version",
            "phase1_63g_gemma_track_b_v5",
            "--require-scorer-timings",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "does not match required" in completed.stderr


def test_track_b_analyzer_parse_failure_rate_blocks_equal_failures(tmp_path: Path) -> None:
    dense_jsonl = tmp_path / "dense.jsonl"
    sparse_jsonl = tmp_path / "sparse.jsonl"
    dense_summary = tmp_path / "dense_summary.json"
    sparse_summary = tmp_path / "sparse_summary.json"
    output = tmp_path / "summary.json"
    rows = [
        _row(
            "a",
            correct=False,
            choice_index=None,
            parse_failure=True,
            vision_ms=40.0,
            end_to_end_ms=100.0,
            kept_groups=10,
            total_groups=10,
        )
    ]
    _write_jsonl(
        dense_jsonl,
        [{"kind": "schema", "schema_version": "phase1_63g_gemma_track_b_v5"}, *rows],
    )
    _write_jsonl(
        sparse_jsonl,
        [
            {"kind": "schema", "schema_version": "phase1_63g_gemma_track_b_v5"},
            _row(
                "a",
                correct=False,
                choice_index=None,
                parse_failure=True,
                vision_ms=20.0,
                end_to_end_ms=80.0,
                kept_groups=5,
                total_groups=10,
            ),
        ],
    )
    dense_summary.write_text(json.dumps({"manifest": "m", "frame_count": 8}) + "\n")
    sparse_summary.write_text(
        json.dumps({"manifest": "m", "frame_count": 8, "vision_tower_keep_rate": 0.5}) + "\n"
    )

    subprocess.run(
        [
            sys.executable,
            "scripts/analyze_phase1_63_track_b_sparse.py",
            "--dense-jsonl",
            str(dense_jsonl),
            "--sparse-jsonl",
            str(sparse_jsonl),
            "--dense-summary",
            str(dense_summary),
            "--sparse-summary",
            str(sparse_summary),
            "--output",
            str(output),
            "--expected-items",
            "1",
            "--bucket-e2e-min-pass",
            "1",
            "--bucket-e2e-min-n",
            "1",
            "--parse-failure-max-fraction",
            "0.25",
        ],
        check=True,
    )

    summary: dict[str, Any] = json.loads(output.read_text())
    assert summary["all"]["choice_agreement"] == 0.0
    assert summary["all"]["choice_agreement_denominator"] == 0
    assert summary["pass_parse_failure_delta"] is True
    assert summary["pass_parse_failure_rate"] is False
