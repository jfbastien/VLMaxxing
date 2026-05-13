from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.analyze_ov6_qwen_random_multiseed import analyze as analyze_random_multiseed
from scripts.analyze_ov6_tomato_motion import analyze as analyze_tomato_motion
from scripts.analyze_ov6_track_b import build_payload
from scripts.validate_ov3_calibration_arm_artifact import validate as validate_ov3_calibration_arm
from scripts.validate_track_b_arm_artifact import validate as validate_track_b_arm


def _write_arm(
    path: Path,
    *,
    rows: list[tuple[str, bool, int]],
    vision_ms: float = 10.0,
    e2e_ms: float = 100.0,
    codec_extract_s: float | None = None,
) -> None:
    path.mkdir(parents=True)
    with (path / "results.jsonl").open("w") as handle:
        for item_id, correct, choice_index in rows:
            handle.write(
                json.dumps(
                    {
                        "item_id": item_id,
                        "correct": correct,
                        "parse_failure": False,
                        "choice_index": choice_index,
                    }
                )
                + "\n"
            )
    (path / "summary.json").write_text(
        json.dumps(
            {
                "n_items": len(rows),
                "mean_dense_vision_ms": vision_ms,
                "mean_dense_end_to_end_ms": e2e_ms,
                "mean_effective_keep_rate": 0.5,
                "codec_extract_mean_s_per_item": codec_extract_s,
            }
        )
        + "\n"
    )


def _populate_minimal_ov6_tree(root: Path) -> None:
    n57 = root / "phase1_51V_ov6_n57"
    kr070 = root / "phase1_51V_ov6_n57_kr070_l2"
    l8 = root / "phase1_51V_ov6_n57_kr050_l8"
    dense_rows = [("a", True, 0), ("b", False, 1), ("c", True, 2)]
    magnitude_rows = [("a", True, 0), ("b", False, 1), ("c", False, 3)]
    random_rows = [("a", False, 1), ("b", True, 0), ("c", False, 3)]
    codec_rows = [("a", True, 0), ("b", True, 0), ("c", False, 3)]

    for base in (n57,):
        _write_arm(base / "dense", rows=dense_rows)
        _write_arm(base / "magnitude_norm_kr050", rows=magnitude_rows)
        _write_arm(base / "uniform_random_kr050", rows=random_rows)
        _write_arm(base / "codec_novel_coded_kr050", rows=codec_rows, codec_extract_s=2.0)
        _write_arm(base / "codec_motion_kr050", rows=codec_rows, codec_extract_s=2.0)
        _write_arm(base / "codec_residual_kr050", rows=codec_rows, codec_extract_s=2.0)

    for base in (kr070, l8):
        _write_arm(base / "magnitude_norm", rows=magnitude_rows)
        _write_arm(base / "codec_novel_coded", rows=codec_rows, codec_extract_s=2.0)
        _write_arm(base / "codec_motion", rows=codec_rows, codec_extract_s=2.0)
        _write_arm(base / "codec_residual", rows=codec_rows, codec_extract_s=2.0)


def test_ov6_track_b_audit_computes_paired_mcnemar_and_net_e2e(tmp_path: Path) -> None:
    _populate_minimal_ov6_tree(tmp_path)
    payload = build_payload(tmp_path)
    cell = next(c for c in payload["cells"] if c["label"] == "kr0.7_layer2_n57")

    codec = cell["arms"]["codec_novel_coded"]
    assert codec["accuracy"]["successes"] == 2
    assert codec["accuracy"]["n"] == 3
    assert codec["mean_e2e_ms_excluding_codec_extract"] == 100.0
    assert codec["mean_e2e_ms_including_codec_extract"] == 2100.0

    paired = cell["paired_comparisons"]["codec_novel_coded_vs_magnitude_norm"]
    assert paired["a_correct_b_wrong"] == 1
    assert paired["a_wrong_b_correct"] == 0
    assert paired["mcnemar_exact_p_two_sided"] == 1.0


def test_ov6_random_multiseed_flags_unstable_random_baseline(tmp_path: Path) -> None:
    rows_mag = [
        ("a", True, 0),
        ("b", True, 1),
        ("c", True, 2),
        ("d", False, 3),
    ]
    rows_seed1 = [
        ("a", True, 0),
        ("b", True, 1),
        ("c", False, 0),
        ("d", True, 3),
    ]
    rows_seed7 = [
        ("a", False, 1),
        ("b", False, 2),
        ("c", False, 3),
        ("d", False, 0),
    ]
    _write_arm(tmp_path / "magnitude_norm", rows=rows_mag)
    _write_arm(tmp_path / "uniform_random_seed1", rows=rows_seed1)
    _write_arm(tmp_path / "uniform_random_seed7", rows=rows_seed7)

    payload = analyze_random_multiseed(tmp_path)

    assert payload["magnitude_norm"]["accuracy"]["correct"] == 3
    assert payload["gate_status"]["seeds_random_ge_magnitude"] == 1
    assert payload["gate_status"]["n_seeds"] == 2
    assert payload["gate_status"]["passes_point_estimate_gate"] is False
    assert payload["gate_status"]["falsifying_seeds"] == ["uniform_random_seed7"]


def test_ov6_tomato_motion_audit_reports_boundary_gate(tmp_path: Path) -> None:
    rows_dense = [("a", True, 0), ("b", True, 1), ("c", False, 2), ("d", False, 3)]
    rows_mag = [("a", False, 2), ("b", True, 1), ("c", False, 2), ("d", False, 3)]
    rows_codec = [("a", True, 0), ("b", False, 2), ("c", True, 1), ("d", False, 3)]
    rows_sparse_floor = [("a", False, 2), ("b", True, 1), ("c", False, 2), ("d", False, 3)]

    _write_arm(tmp_path / "dense", rows=rows_dense)
    _write_arm(tmp_path / "magnitude_norm", rows=rows_mag)
    _write_arm(tmp_path / "uniform_random", rows=rows_sparse_floor)
    _write_arm(tmp_path / "codec_novel_coded", rows=rows_codec, codec_extract_s=1.5)
    _write_arm(tmp_path / "codec_motion", rows=rows_codec, codec_extract_s=1.5)
    _write_arm(tmp_path / "codec_residual", rows=rows_sparse_floor, codec_extract_s=1.5)

    payload = analyze_tomato_motion(tmp_path)

    assert payload["arms"]["codec_novel_coded"]["accuracy"]["correct"] == 2
    assert payload["arms"]["magnitude_norm"]["accuracy"]["correct"] == 1
    assert payload["gate_status"]["codec_novel_coded_ge_magnitude_norm"] is True
    paired = payload["paired_comparisons"]["codec_novel_coded_vs_magnitude_norm"]
    assert paired["candidate_correct_baseline_wrong"] == 2
    assert paired["candidate_wrong_baseline_correct"] == 1


def test_track_b_artifact_validator_rejects_stale_config(tmp_path: Path) -> None:
    arm_dir = tmp_path / "arm"
    _write_arm(arm_dir, rows=[("a", True, 0)])
    summary_path = arm_dir / "summary.json"
    summary = json.loads(summary_path.read_text())
    summary.update(
        {
            "manifest": "manifest.toml",
            "model_path": "/models/qwen",
            "frame_count": 8,
            "max_tokens": 32,
            "vision_tower_patched": True,
            "vision_tower_layer": 2,
            "vision_tower_keep_rate": 0.7,
            "score_mode": "magnitude_norm",
            "score_seed": None,
            "codec_score_source": None,
            "generated_at": "2026-05-13T00:00:00Z",
            "git_commit": "abc",
            "git_dirty": False,
            "git_dirty_scope": "test",
        }
    )
    summary_path.write_text(json.dumps(summary) + "\n")

    with pytest.raises(ValueError, match="vision_tower_keep_rate mismatch"):
        validate_track_b_arm(
            SimpleNamespace(
                arm_dir=arm_dir,
                manifest="manifest.toml",
                model_path="/models/qwen",
                frame_count=8,
                max_tokens=32,
                n_items=1,
                vision_tower_layer=2,
                vision_tower_keep_rate=0.5,
                score_mode="magnitude_norm",
                score_seed=42,
                codec_score_source=None,
            )
        )


def test_ov3_calibration_validator_rejects_dirty_artifact(tmp_path: Path) -> None:
    arm_dir = tmp_path / "novel_coded"
    arm_dir.mkdir()
    (arm_dir / "results.jsonl").write_text(json.dumps({"item_id": "a"}) + "\n")
    (arm_dir / "precompute_cache.json").write_text("{}\n")
    (arm_dir / "summary.json").write_text(
        json.dumps(
            {
                "n_items": 1,
                "codec_score_source": "novel_coded",
                "frame_count": 8,
                "calibration_mode": "pooled",
                "calibration_source": "live-pixel",
                "environment": {
                    "git_sha": "not-current",
                    "git_dirty": True,
                },
            }
        )
        + "\n"
    )

    with pytest.raises(ValueError, match="git_sha mismatch|dirty tree"):
        validate_ov3_calibration_arm(
            SimpleNamespace(
                arm_dir=arm_dir,
                codec_score_source="novel_coded",
                frame_count=8,
                calibration_mode="pooled",
                calibration_source="live-pixel",
            )
        )
