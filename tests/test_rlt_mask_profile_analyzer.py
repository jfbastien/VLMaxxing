from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def _schema() -> dict[str, Any]:
    return {
        "kind": "schema",
        "schema_version": "rlt_mask_profile_v1",
        "run_hash": "test",
        "artifact_payload": {},
    }


def _row(
    kind: str,
    keep_rate: float,
    jaccard: float | None,
    *,
    source: str = "synthetic",
    feature_scorer_jaccard: float | None = None,
    feature_scorer_ms: float | None = None,
    threshold_sweep: list[dict[str, float]] | None = None,
) -> dict[str, Any]:
    row = {
        "kind": "item",
        "schema_version": "rlt_mask_profile_v1",
        "item_id": f"synthetic:{kind}",
        "item_meta": {"source": source, "synthetic_kind": kind},
        "frame_count": 8,
        "mask_config": {"tubelet_size": 2},
        "keep_rate": keep_rate,
        "mask_compute_ms": 10.0,
        "pixel_novelty_jaccard": jaccard,
        "floor_active": False,
        "floor_active_token_count": 0,
        "threshold_active_token_count": 1,
    }
    if threshold_sweep is not None:
        row["threshold_sweep"] = threshold_sweep
    if feature_scorer_jaccard is not None:
        row["feature_scorer_jaccard"] = feature_scorer_jaccard
    if feature_scorer_ms is not None:
        row["feature_scorer_ms"] = feature_scorer_ms
    return row


def _write_profile(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(_schema(), sort_keys=True) + "\n")
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _run_analyzer(tmp_path: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    profile = tmp_path / "profile.jsonl"
    output = tmp_path / "analysis.json"
    _write_profile(profile, rows)
    subprocess.run(
        [
            sys.executable,
            "scripts/analyze_rlt_mask_profile.py",
            "--profile-jsonl",
            str(profile),
            "--output",
            str(output),
        ],
        check=True,
    )
    payload: dict[str, Any] = json.loads(output.read_text(encoding="utf-8"))
    return payload


def test_rlt_profile_analyzer_stops_on_failed_positive_control(tmp_path: Path) -> None:
    payload = _run_analyzer(
        tmp_path,
        [
            _row("fixed_camera_positive", 0.75, 0.4),
            _row("exact_static", 0.25, 0.4),
            _row("camera_pan", 1.0, 0.4),
        ],
    )

    assert payload["positive_control_pass"] is False
    assert any(
        decision["reason"] == "positive_control_reduction_failed"
        for decision in payload["decisions"]
    )
    assert "RLT-2G" in payload["skip_phases"]


def test_rlt_profile_analyzer_stops_on_failed_real_positive_control(tmp_path: Path) -> None:
    payload = _run_analyzer(
        tmp_path,
        [
            _row("fixed_camera_positive", 0.25, 0.4),
            _row("fixed_camera_positive", 0.75, 0.4, source="clip"),
            _row("exact_static", 0.25, 0.4),
            _row("all_motion", 1.0, 0.4),
        ],
    )

    assert payload["real_positive_control_pass"] is False
    assert any(
        decision["reason"] == "real_positive_control_reduction_failed"
        for decision in payload["decisions"]
    )
    assert "RLT-2G" in payload["skip_phases"]


def test_rlt_profile_analyzer_stops_on_failed_synthetic_gate(tmp_path: Path) -> None:
    payload = _run_analyzer(
        tmp_path,
        [
            _row("exact_static", 0.50, 0.4),
            _row("single_frame_repeat", 0.25, 0.4),
            _row("all_motion", 1.0, 0.4),
        ],
    )

    assert payload["synthetic_gate_pass"] is False
    assert any(
        decision["reason"] == "synthetic_mask_gate_failed" for decision in payload["decisions"]
    )
    assert "RLT-3G-B" in payload["skip_phases"]


def test_rlt_profile_analyzer_stops_on_missing_synthetic_gate(tmp_path: Path) -> None:
    payload = _run_analyzer(
        tmp_path,
        [
            _row("exact_static", 0.25, 0.4),
            _row("all_motion", 1.0, 0.4),
        ],
    )

    assert payload["synthetic_gate_pass"] is False
    assert payload["synthetic_gate_checks"]["single_frame_repeat"]["present"] is False
    assert any(
        decision["reason"] == "synthetic_mask_gate_failed" for decision in payload["decisions"]
    )
    assert "RLT-2G" in payload["skip_phases"]


def test_rlt_profile_analyzer_detects_pixel_novelty_co_cover(tmp_path: Path) -> None:
    payload = _run_analyzer(
        tmp_path,
        [
            _row("fixed_camera_positive", 0.25, 0.96, source="manifest"),
            _row("exact_static", 0.25, 0.97, source="manifest"),
            _row("camera_pan", 1.0, 0.95, source="manifest"),
        ],
    )

    assert payload["strong_co_cover_null"] is True
    assert any(
        decision["reason"] == "rlt_pixel_novelty_strong_co_cover"
        for decision in payload["decisions"]
    )
    assert "RLT-5Q" in payload["skip_phases"]


def test_rlt_profile_analyzer_keeps_synthetic_co_cover_diagnostic(tmp_path: Path) -> None:
    payload = _run_analyzer(
        tmp_path,
        [
            _row("fixed_camera_positive", 0.25, 0.96),
            _row("exact_static", 0.25, 0.97),
            _row("camera_pan", 1.0, 0.95),
        ],
    )

    assert payload["synthetic_co_cover_diagnostic"] is True
    assert payload["strong_co_cover_null"] is False
    assert all(
        decision["reason"] != "rlt_pixel_novelty_strong_co_cover"
        for decision in payload["decisions"]
    )


def test_rlt_profile_analyzer_gates_co_cover_on_real_rows_only(tmp_path: Path) -> None:
    payload = _run_analyzer(
        tmp_path,
        [
            _row("exact_static", 0.25, 1.0),
            _row("single_frame_repeat", 0.25, 1.0),
            _row("all_motion", 1.0, 1.0),
            _row("fixed_camera_positive", 0.25, 1.0),
            _row("fixed_camera_positive", 0.25, 0.77, source="manifest"),
        ],
    )

    assert payload["mean_pixel_novelty_jaccard"] > 0.90
    assert payload["mean_pixel_novelty_jaccard_real"] == 0.77
    assert payload["co_cover_null"] is False
    assert payload["strong_co_cover_null"] is False
    assert all(
        decision["reason"] != "rlt_pixel_novelty_co_cover" for decision in payload["decisions"]
    )


def test_rlt_profile_analyzer_skips_h15b_when_feature_prior_fails(
    tmp_path: Path,
) -> None:
    payload = _run_analyzer(
        tmp_path,
        [
            _row(
                "fixed_camera_positive",
                0.25,
                0.4,
                source="manifest",
                feature_scorer_jaccard=0.79,
                feature_scorer_ms=100.0,
            ),
            _row(
                "exact_static",
                0.25,
                0.4,
                source="manifest",
                feature_scorer_jaccard=0.78,
                feature_scorer_ms=100.0,
            ),
            _row(
                "all_motion",
                1.0,
                0.4,
                source="manifest",
                feature_scorer_jaccard=0.79,
                feature_scorer_ms=100.0,
            ),
        ],
    )

    assert payload["h1_5_feature_prior_present"] is True
    assert payload["h1_5_feature_prior_pass"] is False
    assert any(
        decision["reason"] == "feature_prior_mechanism_failed" for decision in payload["decisions"]
    )
    assert "RLT-1.5b" in payload["skip_phases"]


def test_rlt_profile_analyzer_accepts_h15_mechanism_when_feature_prior_passes(
    tmp_path: Path,
) -> None:
    payload = _run_analyzer(
        tmp_path,
        [
            _row(
                "fixed_camera_positive",
                0.25,
                0.4,
                source="manifest",
                feature_scorer_jaccard=0.82,
                feature_scorer_ms=100.0,
            ),
            _row(
                "exact_static",
                0.25,
                0.4,
                source="manifest",
                feature_scorer_jaccard=0.83,
                feature_scorer_ms=100.0,
            ),
            _row(
                "all_motion",
                1.0,
                0.4,
                source="manifest",
                feature_scorer_jaccard=0.84,
                feature_scorer_ms=100.0,
            ),
        ],
    )

    assert payload["h1_5_feature_prior_present"] is True
    assert payload["h1_5_feature_prior_pass"] is True
    assert all(
        decision["reason"] != "feature_prior_mechanism_failed" for decision in payload["decisions"]
    )


def test_rlt_profile_analyzer_accepts_monotonic_threshold_sweep(tmp_path: Path) -> None:
    payload = _run_analyzer(
        tmp_path,
        [
            _row(
                "exact_static",
                0.25,
                0.4,
                threshold_sweep=[
                    {"threshold": 0.05, "keep_rate": 0.50},
                    {"threshold": 0.10, "keep_rate": 0.25},
                    {"threshold": 0.20, "keep_rate": 0.25},
                ],
            ),
            _row("single_frame_repeat", 0.25, 0.4),
            _row("all_motion", 1.0, 0.4),
            _row("fixed_camera_positive", 0.25, 0.4),
        ],
    )

    assert payload["threshold_monotonicity_present"] is True
    assert payload["threshold_monotonicity_pass"] is True
    assert all(
        decision["reason"] != "threshold_monotonicity_failed" for decision in payload["decisions"]
    )


def test_rlt_profile_analyzer_stops_on_nonmonotonic_threshold_sweep(tmp_path: Path) -> None:
    payload = _run_analyzer(
        tmp_path,
        [
            _row(
                "exact_static",
                0.25,
                0.4,
                threshold_sweep=[
                    {"threshold": 0.05, "keep_rate": 0.25},
                    {"threshold": 0.10, "keep_rate": 0.40},
                ],
            ),
            _row("single_frame_repeat", 0.25, 0.4),
            _row("all_motion", 1.0, 0.4),
            _row("fixed_camera_positive", 0.25, 0.4),
        ],
    )

    assert payload["threshold_monotonicity_pass"] is False
    assert any(
        decision["reason"] == "threshold_monotonicity_failed" for decision in payload["decisions"]
    )
