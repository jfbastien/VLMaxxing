from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path
from typing import Any

import pytest

from scripts.analyze_ov6_qwen_kr070_random_control import analyze, main

ROOT_NAME = "m5_ov6_qwen_n57_kr070_l2_random_control"
MANIFEST = "research/benchmark_manifests/videomme_short_present_v1_n57.toml"
MODEL = "/Users/example/models/Qwen2.5-VL-7B-Instruct-4bit"
SPARSE_ARMS = (
    "magnitude_norm",
    "codec_novel_coded",
    "uniform_random_seed1",
    "uniform_random_seed7",
    "uniform_random_seed42",
    "uniform_random_seed100",
)
ITEM_IDS = [str(item_id) for item_id in tomllib.loads(Path(MANIFEST).read_text())["item_ids"]]


def _correct(n_correct: int, *, n: int = 57) -> list[bool]:
    return [index < n_correct for index in range(n)]


def _summary(
    *,
    n: int,
    arm: str,
    score_mode: str | None,
    score_seed: int | None = None,
    codec_runtime_source: str | None = None,
    effective_keep_rate: float = 0.6875,
) -> dict[str, Any]:
    patched = arm != "dense"
    summary: dict[str, Any] = {
        "n_items": n,
        "manifest": MANIFEST,
        "model_path": MODEL,
        "frame_count": 8,
        "max_tokens": 32,
        "vision_tower_patched": patched,
        "vision_tower_layer": 2 if patched else None,
        "vision_tower_keep_rate": 0.70 if patched else None,
        "score_mode": score_mode,
        "score_seed": score_seed,
        "codec_score_source": "novel_coded" if arm == "codec_novel_coded" else None,
        "mean_effective_keep_rate": effective_keep_rate if patched else 1.0,
        "mean_dense_vision_ms": 1000.0,
        "mean_dense_end_to_end_ms": 3000.0,
        "mean_end_to_end_including_codec_score_runtime_ms": 3000.0,
        "generated_at": "2026-05-29T00:00:00Z",
        "git_commit": "abc123",
        "git_dirty": False,
        "git_dirty_scope": "test fixture",
    }
    if arm == "codec_novel_coded":
        summary.update(
            {
                "codec_score_runtime_source": codec_runtime_source or "sidecar",
                "codec_score_sidecar_geometry": "qwen_merged_groups_v1",
                "codec_sidecar_load_mean_s_per_item": 0.001,
            }
        )
    else:
        summary["codec_score_runtime_source"] = None
    return summary


def _rows(
    correct: list[bool],
    *,
    parse_failure_at: int | None = None,
    item_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    ids = item_ids or ITEM_IDS
    if len(correct) > len(ids):
        raise ValueError("test fixture has more correctness rows than item ids")
    rows = []
    for index, is_correct in enumerate(correct):
        rows.append(
            {
                "item_id": ids[index],
                "correct": is_correct,
                "choice_index": int(is_correct),
                "parse_failure": parse_failure_at == index,
            }
        )
    return rows


def _write_arm(root: Path, arm: str, correct: list[bool], **summary_overrides: Any) -> None:
    arm_dir = root / arm
    arm_dir.mkdir(parents=True)
    if arm == "dense":
        score_mode = None
        score_seed = None
    elif arm == "magnitude_norm":
        score_mode = "magnitude_norm"
        score_seed = None
    elif arm == "codec_novel_coded":
        score_mode = "codec_grid"
        score_seed = None
    else:
        score_mode = "uniform_random"
        score_seed = int(arm.removeprefix("uniform_random_seed"))
    summary = _summary(n=len(correct), arm=arm, score_mode=score_mode, score_seed=score_seed)
    summary.update(summary_overrides)
    arm_dir.joinpath("summary.json").write_text(json.dumps(summary) + "\n")
    arm_dir.joinpath("results.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in _rows(correct))
    )


def _write_fixture(
    tmp_path: Path,
    *,
    codec: list[bool],
    randoms: dict[int, list[bool]],
) -> Path:
    root = tmp_path / ROOT_NAME
    root.mkdir()
    root.joinpath("clean_control_run_marker.json").write_text(
        json.dumps(
            {
                "schema": "ov6_qwen_kr070_random_control_run_v1",
                "generated_at": "2026-05-29T00:00:00Z",
                "git_commit": "abc123",
                "preregistration": (
                    "research/experiments/2026/2026-05-26-qwen-kr070-random-control-prereg.md"
                ),
                "wrapper": "scripts/run_ov6_m5_qwen_kr070_random_control.sh",
                "root": ROOT_NAME,
                "manifest": MANIFEST,
                "model": "Qwen2.5-VL-7B-Instruct-4bit",
                "frame_count": "8",
                "layer": "2",
                "configured_keep_rate": "0.70",
                "seeds": "1 7 42 100",
            }
        )
        + "\n"
    )
    dense = [True] * len(codec)
    magnitude = [index < max(0, sum(codec) - 1) for index in range(len(codec))]
    _write_arm(root, "dense", dense)
    _write_arm(root, "magnitude_norm", magnitude)
    _write_arm(root, "codec_novel_coded", codec)
    for seed in (1, 7, 42, 100):
        _write_arm(root, f"uniform_random_seed{seed}", randoms[seed])
    return root


def test_random_control_analyzer_happy_path_emits_required_comparisons(tmp_path: Path) -> None:
    root = _write_fixture(
        tmp_path,
        codec=_correct(35),
        randoms={
            1: _correct(35),
            7: _correct(31),
            42: _correct(30),
            100: _correct(34),
        },
    )

    payload = analyze(root)

    assert payload["schema"] == "codec_vs_random_multiseed_audit_v1"
    assert set(payload["paired_comparisons"]) == {
        "codec_novel_coded_vs_uniform_random_seed1",
        "codec_novel_coded_vs_uniform_random_seed7",
        "codec_novel_coded_vs_uniform_random_seed42",
        "codec_novel_coded_vs_uniform_random_seed100",
    }
    assert payload["gate_status"]["passes_positive_gate"] is True


def test_random_control_analyzer_missing_seed_hard_fails(tmp_path: Path) -> None:
    root = _write_fixture(
        tmp_path,
        codec=_correct(35),
        randoms={
            1: _correct(31),
            7: _correct(31),
            42: _correct(31),
            100: _correct(31),
        },
    )
    for child in (root / "uniform_random_seed100").iterdir():
        child.unlink()
    (root / "uniform_random_seed100").rmdir()

    with pytest.raises(FileNotFoundError):
        analyze(root)


def test_random_control_analyzer_missing_wrapper_marker_hard_fails(tmp_path: Path) -> None:
    root = _write_fixture(
        tmp_path,
        codec=_correct(35),
        randoms={
            1: _correct(31),
            7: _correct(31),
            42: _correct(31),
            100: _correct(31),
        },
    )
    (root / "clean_control_run_marker.json").unlink()

    with pytest.raises(FileNotFoundError):
        analyze(root)


def test_random_control_analyzer_marker_commit_mismatch_hard_fails(tmp_path: Path) -> None:
    root = _write_fixture(
        tmp_path,
        codec=_correct(35),
        randoms={
            1: _correct(31),
            7: _correct(31),
            42: _correct(31),
            100: _correct(31),
        },
    )
    marker = json.loads((root / "clean_control_run_marker.json").read_text())
    marker["git_commit"] = "other-commit"
    (root / "clean_control_run_marker.json").write_text(json.dumps(marker) + "\n")

    with pytest.raises(ValueError, match="dense git_commit"):
        analyze(root)


def test_random_control_analyzer_partial_manifest_hard_fails(tmp_path: Path) -> None:
    root = tmp_path / ROOT_NAME
    root.mkdir()
    root.joinpath("clean_control_run_marker.json").write_text(
        json.dumps(
            {
                "schema": "ov6_qwen_kr070_random_control_run_v1",
                "git_commit": "abc123",
                "preregistration": (
                    "research/experiments/2026/2026-05-26-qwen-kr070-random-control-prereg.md"
                ),
                "wrapper": "scripts/run_ov6_m5_qwen_kr070_random_control.sh",
                "root": ROOT_NAME,
                "manifest": MANIFEST,
                "model": "Qwen2.5-VL-7B-Instruct-4bit",
                "frame_count": "8",
                "layer": "2",
                "configured_keep_rate": "0.70",
                "seeds": "1 7 42 100",
            }
        )
        + "\n"
    )
    partial = [True, True, True, False, False, False]
    _write_arm(root, "dense", partial)
    _write_arm(root, "magnitude_norm", partial)
    _write_arm(root, "codec_novel_coded", partial)
    for seed in (1, 7, 42, 100):
        _write_arm(root, f"uniform_random_seed{seed}", partial)

    with pytest.raises(ValueError, match="dense n_items"):
        analyze(root)


def test_random_control_analyzer_seed_mismatch_hard_fails(tmp_path: Path) -> None:
    root = _write_fixture(
        tmp_path,
        codec=_correct(35),
        randoms={
            1: _correct(31),
            7: _correct(31),
            42: _correct(31),
            100: _correct(31),
        },
    )
    path = root / "uniform_random_seed42" / "summary.json"
    summary = json.loads(path.read_text())
    summary["score_seed"] = 7
    path.write_text(json.dumps(summary) + "\n")

    with pytest.raises(ValueError, match="uniform_random_seed42 score_seed"):
        analyze(root)


def test_random_control_analyzer_item_order_mismatch_hard_fails(tmp_path: Path) -> None:
    root = _write_fixture(
        tmp_path,
        codec=_correct(35),
        randoms={
            1: _correct(31),
            7: _correct(31),
            42: _correct(31),
            100: _correct(31),
        },
    )
    rows = [
        json.loads(line)
        for line in (root / "uniform_random_seed7" / "results.jsonl").read_text().splitlines()
    ]
    rows[0]["item_id"], rows[1]["item_id"] = rows[1]["item_id"], rows[0]["item_id"]
    (root / "uniform_random_seed7" / "results.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows)
    )

    with pytest.raises(ValueError, match="ordered item_ids"):
        analyze(root)


def test_random_control_analyzer_correct_n_wrong_item_ids_hard_fails(tmp_path: Path) -> None:
    root = _write_fixture(
        tmp_path,
        codec=_correct(35),
        randoms={
            1: _correct(31),
            7: _correct(31),
            42: _correct(31),
            100: _correct(31),
        },
    )
    rows = [
        json.loads(line) for line in (root / "dense" / "results.jsonl").read_text().splitlines()
    ]
    rows[0]["item_id"] = "wrong-item"
    (root / "dense" / "results.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))

    with pytest.raises(ValueError, match="ordered item_ids"):
        analyze(root)


def test_random_control_analyzer_parse_failure_hard_fails(tmp_path: Path) -> None:
    root = _write_fixture(
        tmp_path,
        codec=_correct(35),
        randoms={
            1: _correct(31),
            7: _correct(31),
            42: _correct(31),
            100: _correct(31),
        },
    )
    rows = _rows(_correct(35), parse_failure_at=2)
    (root / "codec_novel_coded" / "results.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows)
    )

    with pytest.raises(ValueError, match="parse failures"):
        analyze(root)


def test_random_control_analyzer_dirty_artifact_hard_fails(tmp_path: Path) -> None:
    root = _write_fixture(
        tmp_path,
        codec=_correct(35),
        randoms={
            1: _correct(31),
            7: _correct(31),
            42: _correct(31),
            100: _correct(31),
        },
    )
    path = root / "codec_novel_coded" / "summary.json"
    summary = json.loads(path.read_text())
    summary["git_dirty"] = True
    path.write_text(json.dumps(summary) + "\n")

    with pytest.raises(ValueError, match="dirty git tree"):
        analyze(root)


def test_random_control_analyzer_rejects_live_pyav_codec_arm(tmp_path: Path) -> None:
    root = _write_fixture(
        tmp_path,
        codec=_correct(35),
        randoms={
            1: _correct(31),
            7: _correct(31),
            42: _correct(31),
            100: _correct(31),
        },
    )
    path = root / "codec_novel_coded" / "summary.json"
    summary = json.loads(path.read_text())
    summary["codec_score_runtime_source"] = "live_pyav"
    path.write_text(json.dumps(summary) + "\n")

    with pytest.raises(ValueError, match="codec_score_runtime_source"):
        analyze(root)


def test_random_control_analyzer_effective_keep_rate_mismatch_hard_fails(
    tmp_path: Path,
) -> None:
    root = _write_fixture(
        tmp_path,
        codec=_correct(35),
        randoms={
            1: _correct(31),
            7: _correct(31),
            42: _correct(31),
            100: _correct(31),
        },
    )
    path = root / "uniform_random_seed1" / "summary.json"
    summary = json.loads(path.read_text())
    summary["mean_effective_keep_rate"] = 0.5
    path.write_text(json.dumps(summary) + "\n")

    with pytest.raises(ValueError, match="effective keep-rate mismatch"):
        analyze(root)


def test_random_control_analyzer_falsified_gate(tmp_path: Path) -> None:
    root = _write_fixture(
        tmp_path,
        codec=_correct(24),
        randoms={
            1: _correct(35),
            7: _correct(30),
            42: _correct(31),
            100: _correct(29),
        },
    )

    payload = analyze(root)

    assert payload["gate_status"]["passes_positive_gate"] is False
    assert payload["gate_status"]["falsified"] is True
    assert payload["gate_status"]["inconclusive"] is False


def test_random_control_analyzer_inconclusive_boundary(tmp_path: Path) -> None:
    root = _write_fixture(
        tmp_path,
        codec=_correct(35),
        randoms={
            1: _correct(38),
            7: _correct(34),
            42: _correct(34),
            100: _correct(34),
        },
    )

    payload = analyze(root)

    assert payload["gate_status"]["passes_positive_gate"] is False
    assert payload["gate_status"]["falsified"] is False
    assert payload["gate_status"]["inconclusive"] is True


def test_random_control_markdown_reports_gate_without_overclaim(tmp_path: Path) -> None:
    root = _write_fixture(
        tmp_path,
        codec=_correct(35),
        randoms={
            1: _correct(35),
            7: _correct(31),
            42: _correct(30),
            100: _correct(34),
        },
    )
    out_json = tmp_path / "audit.json"
    out_md = tmp_path / "audit.md"

    old_argv = sys.argv
    try:
        sys.argv = [
            "analyze",
            "--root",
            str(root),
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
        ]
        main()
    finally:
        sys.argv = old_argv

    text = out_md.read_text()
    assert "Gate result:" in text
    assert "broad codec superiority" in text
    assert "significant" not in text.lower()
