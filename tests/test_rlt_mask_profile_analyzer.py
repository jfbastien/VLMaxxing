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
) -> dict[str, Any]:
    return {
        "kind": "item",
        "schema_version": "rlt_mask_profile_v1",
        "item_id": f"synthetic:{kind}",
        "item_meta": {"source": source, "synthetic_kind": kind},
        "keep_rate": keep_rate,
        "pixel_novelty_jaccard": jaccard,
        "floor_active": False,
        "floor_active_token_count": 0,
        "threshold_active_token_count": 1,
    }


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
