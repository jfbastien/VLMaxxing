from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _write_cell(path: Path, *, frame_count: int, actual_minus_predicted: float) -> None:
    path.write_text(
        json.dumps(
            {
                "n_paired_items": 60,
                "pass_complete_pairing": True,
                "pass_format": True,
                "pass_fidelity": True,
                "pass_sparse_vision": True,
                "pass_e2e_positive": True,
                "pass_ceiling_explained": abs(actual_minus_predicted) <= 0.05,
                "all": {
                    "accuracy_delta_sparse_minus_dense": -0.01,
                    "accuracy_delta_sparse_minus_dense_ci95": [-0.03, 0.02],
                    "vision_reduction": 0.45,
                    "vision_share_dense": 0.20,
                    "actual_e2e_speedup_dense_over_sparse": 1.10,
                    "predicted_e2e_speedup_from_vision_only": 1.08,
                    "actual_minus_predicted_e2e_speedup": actual_minus_predicted,
                    "mean_keep_rate": 0.5,
                },
                "frame_count": frame_count,
            }
        )
        + "\n"
    )


def test_scaling_summary_aggregates_track_b_cells(tmp_path: Path) -> None:
    cell16 = tmp_path / "pair_summary_16f.json"
    cell32 = tmp_path / "pair_summary_32f.json"
    output = tmp_path / "scaling_summary.json"
    _write_cell(cell16, frame_count=16, actual_minus_predicted=0.02)
    _write_cell(cell32, frame_count=32, actual_minus_predicted=-0.04)

    subprocess.run(
        [
            sys.executable,
            "scripts/summarize_phase1_63_track_b_scaling.py",
            "--cell",
            "32",
            str(cell32),
            "--cell",
            "16",
            str(cell16),
            "--output",
            str(output),
        ],
        check=True,
    )

    summary = json.loads(output.read_text())
    assert summary["phase"] == "1.63E"
    assert summary["complete"] is True
    assert summary["headline_pass"] is True
    assert summary["frame_counts"] == [16, 32]
    assert summary["headline_frame_counts"] == [16, 32]
    assert summary["max_abs_actual_minus_predicted"] == 0.04
    assert summary["headline_max_abs_actual_minus_predicted"] == 0.04


def test_scaling_summary_can_exclude_reference_from_headline_gate(tmp_path: Path) -> None:
    reference = tmp_path / "pair_summary_8f.json"
    cell16 = tmp_path / "pair_summary_16f.json"
    output = tmp_path / "scaling_summary.json"
    _write_cell(reference, frame_count=8, actual_minus_predicted=0.20)
    _write_cell(cell16, frame_count=16, actual_minus_predicted=0.02)

    subprocess.run(
        [
            sys.executable,
            "scripts/summarize_phase1_63_track_b_scaling.py",
            "--cell",
            "8",
            str(reference),
            "--cell",
            "16",
            str(cell16),
            "--reference-frame-count",
            "8",
            "--output",
            str(output),
        ],
        check=True,
    )

    summary = json.loads(output.read_text())
    assert summary["frame_counts"] == [8, 16]
    assert summary["reference_frame_counts"] == [8]
    assert summary["headline_frame_counts"] == [16]
    assert summary["headline_pass"] is True
    assert summary["max_abs_actual_minus_predicted"] == 0.20
    assert summary["headline_max_abs_actual_minus_predicted"] == 0.02
