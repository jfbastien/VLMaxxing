from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from pytest import MonkeyPatch

import scripts.run_rlt_followup_queue as queue


def test_prefill_kernel_command_uses_paper_grade_controls(tmp_path: Path) -> None:
    command = queue._prefill_kernel_benchmark_command(
        artifact_dir=tmp_path,
        model_path=tmp_path / "model",
        rss_guard_mb=8123,
    )

    assert "--warm-all-shapes" in command
    assert "--shuffle" in command
    assert command[command.index("--rss-guard-mb") + 1] == "8123"


def test_phase_passed_cvision_requires_sparse_induced_parse_gate_only() -> None:
    base: dict[str, Any] = {
        "pass_complete_pairing": True,
        "pass_fidelity": True,
        "pass_sparse_vision": True,
        "pass_e2e_positive": True,
        "pass_bucket_e2e_positive": True,
        "pass_parse_failure_delta": True,
        "pass_parse_failure_rate": True,
        "pass_ceiling_explained": True,
    }
    assert queue._phase_passed_cvision(base)

    candidate = dict(base)
    candidate["pass_parse_failure_delta"] = False
    assert not queue._phase_passed_cvision(candidate)

    for key in ("pass_parse_failure_rate", "pass_ceiling_explained"):
        candidate = dict(base)
        candidate[key] = False
        assert queue._phase_passed_cvision(candidate)


def test_run_command_group_stops_after_first_failure(monkeypatch: MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], *, allow_failure: bool = False) -> dict[str, Any]:
        calls.append(command)
        return {
            "command": command,
            "returncode": 7 if command == ["fail"] else 0,
            "elapsed_seconds": 0.0,
            "stdout_tail": "",
            "stderr_tail": "",
        }

    monkeypatch.setattr(queue, "_run", fake_run)
    results = queue._run_command_group([["ok"], ["fail"], ["stale_analyzer"]])

    assert [result["returncode"] for result in results] == [0, 7]
    assert calls == [["ok"], ["fail"]]


def test_expansion_requires_video_mme_rlt_gate(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_rlt_followup_queue.py",
            "--run-cvision-expansion",
            "--dry-run",
            "--summary",
            str(tmp_path / "summary.json"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "--run-cvision-expansion requires --run-cvision-rlt" in completed.stderr


def test_cvision_commands_can_reuse_dense_and_set_keep_rate(tmp_path: Path) -> None:
    commands = queue._cvision_commands(
        artifact_dir=tmp_path,
        manifest=Path("manifest.toml"),
        model_path=Path("model"),
        frame_count=8,
        n_items=30,
        rss_guard_mb=9000,
        label="cvision_rlt_tomato_kr030",
        expected_items=30,
        score_mode="rlt_topk",
        keep_rate=0.3,
        dense_source_label="cvision_rlt_tomato",
        include_dense_command=False,
    )

    assert len(commands) == 2
    sparse, analyze = commands
    assert sparse[sparse.index("--vision-tower-keep-rate") + 1] == "0.3"
    assert str(tmp_path / "cvision_rlt_tomato_dense.jsonl") in analyze
    assert str(tmp_path / "cvision_rlt_tomato_kr030_analysis.json") in analyze


def test_composition_command_uses_rlt_for_admission_and_cvision(tmp_path: Path) -> None:
    run_command, analyze_command = queue._gemma_composition_commands(
        artifact_dir=tmp_path,
        manifest=Path("manifest.toml"),
        model_path=Path("model"),
        frame_count=8,
        n_items=30,
        rss_guard_mb=9000,
        label="composition_rlt_videomme",
    )

    assert run_command[run_command.index("--prune-placeholders") + 1] == "rlt"
    assert run_command[run_command.index("--vision-tower-score-mode") + 1] == "rlt_topk"
    assert run_command[run_command.index("--prefill-step-size") + 1] == "1500"
    assert analyze_command[analyze_command.index("--cell-type") + 1] == "h3b_admission"
